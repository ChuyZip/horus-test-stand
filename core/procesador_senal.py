"""Procesamiento digital de señales para el banco de pruebas de motores cohete.

Provee:
- Filtro digital IIR exponencial (pasabajas recursivo de primer orden) configurable por frecuencia de corte.
- Calibración de señal de celda de carga de Voltios a Newtons (N/V) con soporte de tara.
- Cálculo de impulso acumulado en tiempo real mediante integración numérica trapezoidal.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class MuestraProcesada:
    """Estructura optimizada de datos procesados por muestra."""

    tiempo: float
    voltaje_crudo: float
    voltaje_filtrado: float
    empuje_crudo: float
    empuje_filtrado: float
    impulso_acumulado: float
    empuje_maximo: float
    tiempo_pico: float


@dataclass
class MuestraPreTrigger:
    """Muestra individual capturada en la ventana previa a la ignición."""

    tiempo: float
    voltaje_crudo: float
    voltaje_filtrado: float
    empuje_crudo: float
    empuje_filtrado: float


class BuferPreTrigger:
    """Búfer circular de tamaño fijo (deque) para almacenar telemetría previa a la ignición.

    Permite capturar la línea base, tara dinámica, ruido térmico del ADC y estado
    de reposo durante los estados ARMADO y CUENTA REGRESIVA. Al dispararse la ignición,
    vuelca todas sus muestras asignándoles marcas de tiempo negativas relativas
    al instante T-0 (ej. de -1.00 s a 0.00 s).
    """

    def __init__(self, frecuencia_hz: float = 200.0, tiempo_pretrigger_s: float = 1.0) -> None:
        self.frecuencia_hz = max(1.0, float(frecuencia_hz))
        self.tiempo_pretrigger_s = max(0.05, float(tiempo_pretrigger_s))
        self.maxlen = max(1, int(self.frecuencia_hz * self.tiempo_pretrigger_s))
        self._buffer: deque[MuestraPreTrigger] = deque(maxlen=self.maxlen)

    def agregar(
        self,
        tiempo: float,
        voltaje_crudo: float,
        voltaje_filtrado: float,
        empuje_crudo: float,
        empuje_filtrado: float,
    ) -> None:
        """Agrega una muestra continua al búfer circular."""
        self._buffer.append(
            MuestraPreTrigger(
                tiempo=float(tiempo),
                voltaje_crudo=float(voltaje_crudo),
                voltaje_filtrado=float(voltaje_filtrado),
                empuje_crudo=float(empuje_crudo),
                empuje_filtrado=float(empuje_filtrado),
            )
        )

    def volcar(self, tiempo_ignicion: float) -> list[MuestraPreTrigger]:
        """Extrae las muestras con marcas de tiempo relativas negativas respecto a la ignición.

        Ejemplo: Si tiempo_ignicion = 1.00 s y una muestra previa tiene tiempo = 0.20 s,
        su tiempo relativo en la lista volcada será -0.80 s.
        """
        muestras_relativas: list[MuestraPreTrigger] = []
        for m in self._buffer:
            t_rel = round(m.tiempo - tiempo_ignicion, 4)
            muestras_relativas.append(
                MuestraPreTrigger(
                    tiempo=t_rel,
                    voltaje_crudo=m.voltaje_crudo,
                    voltaje_filtrado=m.voltaje_filtrado,
                    empuje_crudo=m.empuje_crudo,
                    empuje_filtrado=m.empuje_filtrado,
                )
            )
        return muestras_relativas

    def reiniciar(self) -> None:
        """Limpia el contenido del búfer circular."""
        self._buffer.clear()

    @property
    def cantidad_muestras(self) -> int:
        return len(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)


class FiltroIIRExponencial:
    """Filtro digital IIR pasabajas de primer orden (suavizado exponencial recursivo).

    Ecuación en diferencias:
        y[k] = alpha * x[k] + (1 - alpha) * y[k-1]
    donde alpha = (2*pi*fc/fs) / (1 + 2*pi*fc/fs)
    """

    def __init__(self, alfa: float = 0.15, fc: Optional[float] = None, fs: float = 200.0) -> None:
        self.fs = fs
        self.fc = fc
        self.alfa = alfa
        if fc is not None and fs > 0:
            self.configurar_frecuencia_corte(fc, fs)

        self._y_prev: Optional[float] = None

    def configurar_frecuencia_corte(self, fc: float, fs: float = 200.0) -> None:
        """Calcula el factor alpha a partir de la frecuencia de corte (Hz) y de muestreo."""
        self.fc = fc
        self.fs = fs
        w = 2.0 * math.pi * fc / fs
        # Mapeo bilineal / aproximación exponencial
        self.alfa = max(0.001, min(1.0, w / (1.0 + w)))

    def configurar_alfa(self, alfa: float) -> None:
        """Asigna directamente el coeficiente de ponderación alpha (0 < alpha <= 1)."""
        self.alfa = max(0.001, min(1.0, float(alfa)))

    def filtrar(self, valor: float) -> float:
        """Procesa una muestra individual en tiempo real."""
        if self._y_prev is None:
            # Inicialización suave sin escalón artificial
            self._y_prev = valor
            return valor

        salida = self.alfa * valor + (1.0 - self.alfa) * self._y_prev
        self._y_prev = salida
        return salida

    def reiniciar(self) -> None:
        """Borra la memoria histórica del filtro."""
        self._y_prev = None


class CalibradorFuerza:
    """Conversor y calibrador de transductor de fuerza de Voltaje a Newtons."""

    def __init__(self, factor_n_por_v: float = 1000.0, offset_voltaje: float = 0.0) -> None:
        self.factor_n_por_v = factor_n_por_v
        self.offset_voltaje = offset_voltaje

    def tarar(self, voltaje_actual: float) -> None:
        """Establece la tensión de reposo actual como cero de referencia (Tara)."""
        self.offset_voltaje = voltaje_actual

    def voltaje_a_newtons(self, voltaje: float) -> float:
        """Transforma una lectura de tensión a fuerza en Newtons."""
        fuerza = (voltaje - self.offset_voltaje) * self.factor_n_por_v
        return max(0.0, fuerza) if abs(fuerza) < 0.05 else fuerza

    def newtons_a_kgf(self, newtons: float) -> float:
        """Convierte Newtons a kilogramos-fuerza (kgf)."""
        return newtons / 9.80665


class IntegradorImpulso:
    """Integrador numérico en tiempo real por regla trapezoidal para impulso total (N·s)."""

    def __init__(self, umbral_ruido_n: float = 0.5) -> None:
        self.umbral_ruido_n = umbral_ruido_n
        self.impulso_acumulado: float = 0.0
        self.empuje_maximo: float = 0.0
        self.tiempo_pico: float = 0.0

        self._t_prev: Optional[float] = None
        self._f_prev: Optional[float] = None

    def actualizar(self, tiempo: float, empuje: float) -> float:
        """Integra el empuje si supera el umbral y actualiza las métricas de pico."""
        # Filtrado de zona muerta para evitar integrar ruido térmico en reposo
        f_efectivo = empuje if empuje > self.umbral_ruido_n else 0.0

        if self._t_prev is not None and self._f_prev is not None:
            dt = tiempo - self._t_prev
            if dt > 0:
                # Regla trapezoidal: Area = dt * (f_k + f_{k-1}) / 2
                delta_impulso = 0.5 * (f_efectivo + self._f_prev) * dt
                self.impulso_acumulado += delta_impulso

        self._t_prev = tiempo
        self._f_prev = f_efectivo

        # Registro de empuje máximo
        if empuje > self.empuje_maximo:
            self.empuje_maximo = empuje
            self.tiempo_pico = tiempo

        return self.impulso_acumulado

    def reiniciar(self) -> None:
        """Reinicia el acumulador de impulso y los registros de pico."""
        self.impulso_acumulado = 0.0
        self.empuje_maximo = 0.0
        self.tiempo_pico = 0.0
        self._t_prev = None
        self._f_prev = None


class ProcesadorSenal:
    """Coordinador de instrumentación científica para telemetría de bancos de prueba."""

    def __init__(
        self,
        factor_n_por_v: float = 1000.0,
        alfa_filtro: float = 0.18,
        umbral_ruido_n: float = 1.0,
        frecuencia_hz: float = 200.0,
        tiempo_pretrigger_s: float = 1.0,
    ) -> None:
        self.filtro = FiltroIIRExponencial(alfa=alfa_filtro, fs=frecuencia_hz)
        self.calibrador = CalibradorFuerza(factor_n_por_v=factor_n_por_v)
        self.integrador = IntegradorImpulso(umbral_ruido_n=umbral_ruido_n)
        self.bufer_pretrigger = BuferPreTrigger(
            frecuencia_hz=frecuencia_hz, tiempo_pretrigger_s=tiempo_pretrigger_s
        )

    def procesar_muestra(self, tiempo: float, voltaje_crudo: float) -> MuestraProcesada:
        """Ejecuta la canalización completa de procesamiento en una muestra (tiempo, V)."""
        voltaje_filtrado = self.filtro.filtrar(voltaje_crudo)

        empuje_crudo = self.calibrador.voltaje_a_newtons(voltaje_crudo)
        empuje_filtrado = self.calibrador.voltaje_a_newtons(voltaje_filtrado)

        impulso = self.integrador.actualizar(tiempo, empuje_filtrado)

        return MuestraProcesada(
            tiempo=tiempo,
            voltaje_crudo=voltaje_crudo,
            voltaje_filtrado=voltaje_filtrado,
            empuje_crudo=empuje_crudo,
            empuje_filtrado=empuje_filtrado,
            impulso_acumulado=impulso,
            empuje_maximo=self.integrador.empuje_maximo,
            tiempo_pico=self.integrador.tiempo_pico,
        )

    def procesar_lote(
        self, tiempos: np.ndarray, voltajes: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Procesa arreglos NumPy de datos para análisis acelerado o post-procesamiento."""
        n = len(tiempos)
        v_filt = np.zeros(n, dtype=np.float64)
        f_crudo = np.zeros(n, dtype=np.float64)
        f_filt = np.zeros(n, dtype=np.float64)
        imp = np.zeros(n, dtype=np.float64)

        self.reiniciar()
        for i in range(n):
            m = self.procesar_muestra(float(tiempos[i]), float(voltajes[i]))
            v_filt[i] = m.voltaje_filtrado
            f_crudo[i] = m.empuje_crudo
            f_filt[i] = m.empuje_filtrado
            imp[i] = m.impulso_acumulado

        return {
            "tiempo": tiempos,
            "voltaje_crudo": voltajes,
            "voltaje_filtrado": v_filt,
            "empuje_crudo": f_crudo,
            "empuje_filtrado": f_filt,
            "impulso": imp,
        }

    def reiniciar(self) -> None:
        """Limpia el estado interno para comenzar un nuevo ensayo."""
        self.filtro.reiniciar()
        self.integrador.reiniciar()
        self.bufer_pretrigger.reiniciar()
