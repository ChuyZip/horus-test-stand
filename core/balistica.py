"""Cálculos balísticos y de propulsión para motores cohete experimentales.

Incluye:
- Clasificación de motores según estándar NAR/Tripoli/Nakka (Clases 1/4A hasta O).
- Tiempo de combustión efectivo, empuje promedio e impulso total.
- Impulso específico (Isp) a partir de masa de grano quemada.
- Espesor de pared (web thickness) y velocidad de regresión/quemado lineal (r).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence
import numpy as np

GRAVEDAD_ESTANDAR = 9.80665  # m/s^2


@dataclass
class MetricasBalisticas:
    """Consolidado de parámetros de rendimiento balístico de un ensayo."""

    empuje_pico_n: float
    tiempo_pico_s: float
    tiempo_inicio_s: float
    tiempo_fin_s: float
    tiempo_quemado_s: float
    empuje_promedio_n: float
    impulso_total_ns: float
    isp_s: float
    velocidad_quemado_mm_s: float
    clase_nakka: str
    porcentaje_clase: float


# Rangos de impulso total según estándar internacional NAR / Tripoli
TABLA_CLASES_NAR = [
    ("1/4A", 0.0, 0.625),
    ("1/2A", 0.625, 1.25),
    ("A", 1.25, 2.50),
    ("B", 2.50, 5.00),
    ("C", 5.00, 10.0),
    ("D", 10.0, 20.0),
    ("E", 20.0, 40.0),
    ("F", 40.0, 80.0),
    ("G", 80.0, 160.0),
    ("H", 160.0, 320.0),
    ("I", 320.0, 640.0),
    ("J", 640.0, 1280.0),
    ("K", 1280.0, 2560.0),
    ("L", 2560.0, 5120.0),
    ("M", 5120.0, 10240.0),
    ("N", 10240.0, 20480.0),
    ("O", 20480.0, 40960.0),
]


def clasificar_motor_nakka(impulso_total_ns: float) -> tuple[str, float]:
    """Determina la designación de clase NAR/Nakka y el porcentaje alcanzado."""
    if impulso_total_ns <= 0.0:
        return ("N/A", 0.0)

    for letra, minimo, maximo in TABLA_CLASES_NAR:
        if minimo <= impulso_total_ns < maximo:
            # Porcentaje relativo dentro del intervalo de la clase
            rango = maximo - minimo
            pct = ((impulso_total_ns - minimo) / rango) * 100.0 if rango > 0 else 0.0
            return (f"Clase {letra}", round(pct, 1))

    if impulso_total_ns >= 40960.0:
        return ("Clase >O (Super-Heavy)", 100.0)

    return ("Clase Micro", 0.0)


def calcular_metricas_balisticas(
    tiempos: Sequence[float],
    empujes: Sequence[float],
    masa_propelente_g: float,
    diam_ext_mm: float = 0.0,
    diam_int_mm: float = 0.0,
    umbral_empuje_n: float = 2.0,
) -> MetricasBalisticas:
    """Calcula todas las métricas balísticas oficiales a partir de la curva de empuje."""
    t_arr = np.array(tiempos, dtype=np.float64)
    f_arr = np.array(empujes, dtype=np.float64)

    if len(t_arr) < 2 or len(f_arr) < 2:
        return MetricasBalisticas(
            empuje_pico_n=0.0,
            tiempo_pico_s=0.0,
            tiempo_inicio_s=0.0,
            tiempo_fin_s=0.0,
            tiempo_quemado_s=0.0,
            empuje_promedio_n=0.0,
            impulso_total_ns=0.0,
            isp_s=0.0,
            velocidad_quemado_mm_s=0.0,
            clase_nakka="N/A",
            porcentaje_clase=0.0,
        )

    # 1. Empuje máximo y tiempo del pico
    idx_pico = int(np.argmax(f_arr))
    empuje_pico = float(f_arr[idx_pico])
    tiempo_pico = float(t_arr[idx_pico])

    # 2. Detección de ventana de combustión (corte al 5% del pico o umbral mínimo)
    umbral_combustion = max(umbral_empuje_n, empuje_pico * 0.05)
    indices_activos = np.where(f_arr >= umbral_combustion)[0]

    if len(indices_activos) > 1:
        idx_inicio = int(indices_activos[0])
        idx_fin = int(indices_activos[-1])
        t_inicio = float(t_arr[idx_inicio])
        t_fin = float(t_arr[idx_fin])
        t_comb = t_arr[idx_inicio : idx_fin + 1]
        f_comb = f_arr[idx_inicio : idx_fin + 1]
    elif len(indices_activos) == 1:
        idx = int(indices_activos[0])
        t_inicio = float(t_arr[idx])
        t_fin = float(t_arr[idx])
        t_comb = t_arr
        f_comb = f_arr
    else:
        t_inicio = float(t_arr[0])
        t_fin = float(t_arr[-1])
        t_comb = t_arr
        f_comb = f_arr

    tiempo_quemado = max(0.01, t_fin - t_inicio)

    # 3. Impulso total por regla trapezoidal
    # np.trapezoid en numpy 2.0+ o np.trapz en versiones previas
    if hasattr(np, "trapezoid"):
        impulso_total = float(np.trapezoid(f_comb, t_comb))
    else:
        impulso_total = float(np.trapz(f_comb, t_comb))

    impulso_total = max(0.0, impulso_total)

    # 4. Empuje promedio
    empuje_promedio = impulso_total / tiempo_quemado

    # 5. Impulso específico (Isp = Itot / (m_kg * g0))
    masa_kg = max(0.0001, masa_propelente_g / 1000.0)
    isp = impulso_total / (masa_kg * GRAVEDAD_ESTANDAR)

    # 6. Espesor de pared y velocidad de quemado (BATES / Tubular o Sólido)
    if diam_ext_mm > 0 and diam_int_mm >= 0 and diam_ext_mm > diam_int_mm:
        espesor_web_mm = (diam_ext_mm - diam_int_mm) / 2.0
    elif diam_ext_mm > 0:
        espesor_web_mm = diam_ext_mm / 2.0
    else:
        espesor_web_mm = 0.0

    velocidad_quemado = espesor_web_mm / tiempo_quemado if espesor_web_mm > 0 else 0.0

    # 7. Clasificación Nakka
    clase, pct = clasificar_motor_nakka(impulso_total)

    return MetricasBalisticas(
        empuje_pico_n=round(empuje_pico, 2),
        tiempo_pico_s=round(tiempo_pico, 3),
        tiempo_inicio_s=round(t_inicio, 3),
        tiempo_fin_s=round(t_fin, 3),
        tiempo_quemado_s=round(tiempo_quemado, 3),
        empuje_promedio_n=round(empuje_promedio, 2),
        impulso_total_ns=round(impulso_total, 2),
        isp_s=round(isp, 2),
        velocidad_quemado_mm_s=round(velocidad_quemado, 2),
        clase_nakka=clase,
        porcentaje_clase=pct,
    )
