"""Simulador de telemetría en tiempo real de prueba estática de motor cohete.

Genera una curva de combustión sintética hiperrealista a 200 Hz con:
- Fase de reposo inicial
- Transitorio de ignición rápida con pico inicial de presurización
- Meseta de empuje sostenido con turbulencia y ruido acústico de combustión
- Transición regresiva y corte de cámara
- Estado de reposo post-combustión
"""

from __future__ import annotations

import math
import random
import time
from typing import Optional

from PySide6.QtCore import QMutex, QMutexLocker
from comunicacion.base import CanalDAQ
from estilo.tema import EstadoInstrumentacion


class SimuladorMotorCohete(CanalDAQ):
    """Hilo generador de telemetría sintética de alta fidelidad (200 Hz)."""

    def __init__(
        self,
        frecuencia_hz: float = 200.0,
        voltaje_pico_v: float = 1.95,
        voltaje_meseta_v: float = 1.48,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.frecuencia_hz = frecuencia_hz
        self.dt = 1.0 / frecuencia_hz
        self.voltaje_pico_v = voltaje_pico_v
        self.voltaje_meseta_v = voltaje_meseta_v

        self._activo = False
        self._abortado = False
        self._mutex = QMutex()

        # Parámetros temporales de la curva de empuje (segundos)
        self.t_inicio_ignicion = 1.00
        self.t_pico = 1.25
        self.t_inicio_meseta = 1.45
        self.t_fin_meseta = 3.80
        self.t_corte_total = 4.50
        self.t_duracion_total = 5.50

    def run(self) -> None:
        """Ciclo de ejecución en hilo separado a 200 Hz."""
        with QMutexLocker(self._mutex):
            self._activo = True
            self._abortado = False

        self.estado_cambiado.emit(EstadoInstrumentacion.ARMADO)
        time.sleep(0.3)

        if not self._activo:
            return

        self.estado_cambiado.emit(EstadoInstrumentacion.CUENTA_REGRESIVA)
        time.sleep(0.7)

        tiempo_simulado = 0.0
        fase_grabacion_iniciada = False

        # Bucle de alta precisión temporal con compensación de deriva
        t_referencia_real = time.perf_counter()

        while True:
            with QMutexLocker(self._mutex):
                if not self._activo:
                    break
                if self._abortado:
                    self.estado_cambiado.emit(EstadoInstrumentacion.ABORTADO)
                    # En abortar, corte inmediato a cero
                    self.nueva_muestra.emit(tiempo_simulado, 0.0)
                    break

            # Cambio de estado al comenzar la ignición física
            if tiempo_simulado >= self.t_inicio_ignicion and not fase_grabacion_iniciada:
                fase_grabacion_iniciada = True
                self.estado_cambiado.emit(EstadoInstrumentacion.GRABANDO)

            # Generación de la señal de combustión
            voltaje = self._calcular_voltaje_sintetico(tiempo_simulado)
            self.nueva_muestra.emit(round(tiempo_simulado, 4), voltaje)

            # Avance del tiempo simulado
            tiempo_simulado += self.dt

            # Condición de fin de prueba
            if tiempo_simulado >= self.t_duracion_total:
                self.estado_cambiado.emit(EstadoInstrumentacion.TERMINADO)
                self.simulacion_finalizada.emit()
                break

            # Sincronización temporal con el reloj de pared para mantener 200 Hz estables
            t_objetivo = t_referencia_real + tiempo_simulado
            tiempo_espera = t_objetivo - time.perf_counter()
            if tiempo_espera > 0.001:
                time.sleep(tiempo_espera)

        with QMutexLocker(self._mutex):
            self._activo = False

    def _calcular_voltaje_sintetico(self, t: float) -> float:
        """Modela la respuesta física de presión de cámara y transductor de carga."""
        # Ruido de fondo basal térmico del amplificador HX711/ADC
        ruido_base = random.gauss(0.0, 0.004)

        if t < self.t_inicio_ignicion:
            # 1. Reposo antes de ignición
            return max(0.0, 0.01 + ruido_base)

        elif t < self.t_pico:
            # 2. Subida abrupta de presurización de cámara
            tau = (t - self.t_inicio_ignicion) / (self.t_pico - self.t_inicio_ignicion)
            # Curva de subida sigmoide pronunciada
            factor_subida = 1.0 / (1.0 + math.exp(-12.0 * (tau - 0.45)))
            voltaje_nominal = self.voltaje_pico_v * factor_subida
            # Ruido de encendido del grano
            ruido = random.gauss(0.0, 0.02 * factor_subida)
            return max(0.0, voltaje_nominal + ruido)

        elif t < self.t_inicio_meseta:
            # 3. Transición del pico de presurización a meseta de combustión
            tau = (t - self.t_pico) / (self.t_inicio_meseta - self.t_pico)
            voltaje_nominal = (
                self.voltaje_pico_v
                - (self.voltaje_pico_v - self.voltaje_meseta_v) * (1.0 - math.cos(math.pi * tau)) / 2.0
            )
            ruido = random.gauss(0.0, 0.035)
            return max(0.0, voltaje_nominal + ruido)

        elif t < self.t_fin_meseta:
            # 4. Meseta sostenida con inestabilidades acústicas de combustión a 200 Hz
            tau = (t - self.t_inicio_meseta) / (self.t_fin_meseta - self.t_inicio_meseta)
            # Leve comportamiento ligeramente regresivo natural
            voltaje_nominal = self.voltaje_meseta_v * (1.0 - 0.08 * tau)
            # Componentes de frecuencia de combustión (armónicos a ~25 Hz y ~80 Hz)
            armonico1 = 0.045 * math.sin(2.0 * math.pi * 24.5 * t)
            armonico2 = 0.025 * math.cos(2.0 * math.pi * 78.0 * t)
            ruido_estocastico = random.gauss(0.0, 0.04)
            return max(0.0, voltaje_nominal + armonico1 + armonico2 + ruido_estocastico)

        elif t < self.t_corte_total:
            # 5. Agotamiento del propelente y caída regresiva rápida
            tau = (t - self.t_fin_meseta) / (self.t_corte_total - self.t_fin_meseta)
            factor_caida = 0.5 * (1.0 + math.cos(math.pi * tau))
            voltaje_nominal = (self.voltaje_meseta_v * 0.92) * factor_caida
            ruido = random.gauss(0.0, 0.025 * factor_caida)
            return max(0.0, voltaje_nominal + ruido)

        else:
            # 6. Post-combustión / Enfriamiento del motor
            return max(0.0, 0.01 + ruido_base)

    def iniciar_simulacion(self) -> None:
        """Arranca la secuencia de prueba en un hilo dedicado."""
        if not self.isRunning():
            self.start()

    def abortar(self) -> None:
        """Comando de seguridad prioritario: corta la prueba inmediatamente."""
        with QMutexLocker(self._mutex):
            self._abortado = True
            self._activo = False

    def iniciar_adquisicion(self) -> None:
        """Alias para interfaz normalizada CanalDAQ."""
        self.iniciar_simulacion()

    def detener(self) -> None:
        """Detiene de forma controlada la secuencia de simulación."""
        with QMutexLocker(self._mutex):
            self._activo = False

    def detener_adquisicion(self) -> None:
        """Alias para interfaz normalizada CanalDAQ."""
        self.detener()

