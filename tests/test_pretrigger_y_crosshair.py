"""Pruebas unitarias y de integración para el búfer pre-trigger y la mira/tooltip interactiva."""

import os
import subprocess
import sys
import numpy as np

from core.procesador_senal import BuferPreTrigger, MuestraPreTrigger, ProcesadorSenal


def test_bufer_pretrigger_basico():
    """Verifica la capacidad, adición y vaciado con marcas de tiempo relativas negativas."""
    # 200 Hz y 0.5 s -> 100 muestras de capacidad
    bufer = BuferPreTrigger(frecuencia_hz=200.0, tiempo_pretrigger_s=0.5)
    assert bufer.maxlen == 100
    assert len(bufer) == 0

    # Llenar con 50 muestras a 200 Hz (dt = 0.005 s) desde t = 0.0 a 0.245 s
    for i in range(50):
        t = i * 0.005
        bufer.agregar(
            tiempo=t,
            voltaje_crudo=0.01 + (i * 0.0001),
            voltaje_filtrado=0.01 + (i * 0.0001),
            empuje_crudo=1.0,
            empuje_filtrado=1.0,
        )

    assert len(bufer) == 50

    # Supongamos que a t = 0.25 s se detecta la ignición
    t_ignicion = 0.25
    muestras_volcadas = bufer.volcar(tiempo_ignicion=t_ignicion)
    assert len(muestras_volcadas) == 50

    # Todas las muestras deben tener tiempos relativos negativos
    for m in muestras_volcadas:
        assert m.tiempo < 0.0
        assert m.empuje_filtrado == 1.0

    # La última muestra (índice 49, t = 0.245) debe tener tiempo = 0.245 - 0.250 = -0.005 s
    assert abs(muestras_volcadas[-1].tiempo - (-0.005)) < 1e-4
    # La primera muestra (índice 0, t = 0.0) debe tener tiempo = 0.0 - 0.250 = -0.250 s
    assert abs(muestras_volcadas[0].tiempo - (-0.250)) < 1e-4

    # Reiniciar búfer
    bufer.reiniciar()
    assert len(bufer) == 0


def test_bufer_pretrigger_desborde_circular():
    """Verifica que al sobrepasar maxlen, las muestras más viejas se descarten."""
    bufer = BuferPreTrigger(frecuencia_hz=10.0, tiempo_pretrigger_s=1.0)
    assert bufer.maxlen == 10

    # Insertar 15 muestras
    for i in range(15):
        bufer.agregar(
            tiempo=float(i),
            voltaje_crudo=float(i),
            voltaje_filtrado=float(i),
            empuje_crudo=float(i * 10),
            empuje_filtrado=float(i * 10),
        )

    assert len(bufer) == 10
    # Las muestras deben ser de 5 a 14
    muestras = bufer.volcar(tiempo_ignicion=15.0)
    assert len(muestras) == 10
    # Primera muestra conservada fue i=5 -> t_rel = 5 - 15 = -10.0
    assert abs(muestras[0].tiempo - (-10.0)) < 1e-4
    # Última muestra conservada fue i=14 -> t_rel = 14 - 15 = -1.0
    assert abs(muestras[-1].tiempo - (-1.0)) < 1e-4


def test_procesador_senal_con_bufer_pretrigger():
    """Verifica que ProcesadorSenal integre correctamente BuferPreTrigger y lo reinicie."""
    proc = ProcesadorSenal(frecuencia_hz=200.0, tiempo_pretrigger_s=1.0)
    assert hasattr(proc, "bufer_pretrigger")
    assert proc.bufer_pretrigger.maxlen == 200

    proc.bufer_pretrigger.agregar(0.1, 0.01, 0.01, 0.0, 0.0)
    assert len(proc.bufer_pretrigger) == 1

    proc.reiniciar()
    assert len(proc.bufer_pretrigger) == 0


def test_vista_prueba_pretrigger_y_crosshair_ui():
    """Verifica en proceso Qt aislado la integración de pre-trigger y crosshair interactivo en VistaPrueba."""
    codigo_script = """
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from estilo.tema import EstadoInstrumentacion

app = QApplication.instance() or QApplication([])

from ui.vistas.vista_prueba import VistaPrueba

vista = VistaPrueba()

# 1. Comprobar existencia y configuración de miras y tooltips
assert hasattr(vista, "crosshair_v_empuje")
assert hasattr(vista, "crosshair_h_empuje")
assert hasattr(vista, "tooltip_empuje")

assert hasattr(vista, "crosshair_v_voltaje")
assert hasattr(vista, "crosshair_h_voltaje")
assert hasattr(vista, "tooltip_voltaje")

assert hasattr(vista, "crosshair_v_impulso")
assert hasattr(vista, "crosshair_h_impulso")
assert hasattr(vista, "tooltip_impulso")

# Inicialmente deben estar ocultos
assert not vista.crosshair_v_empuje.isVisible()
assert not vista.crosshair_h_empuje.isVisible()
assert not vista.tooltip_empuje.isVisible()
assert not vista.linea_ignicion.isVisible()

# 2. Simular recepción de datos basales durante ARMADO y CUENTA REGRESIVA
vista._al_cambiar_estado(EstadoInstrumentacion.ARMADO)
assert vista._estado_actual == EstadoInstrumentacion.ARMADO

# Enviar 100 muestras basales (0.5 s a 200 Hz) con empuje bajo (1.0 N)
for i in range(100):
    t = i * 0.005
    v = 0.001  # Voltaje de reposo
    vista._recibir_muestra(t, v)

vista._actualizar_graficas_y_metricas()

# Como el empuje < 15 N, no debe haber disparado la ignición aún
assert not vista._ignicion_confirmada
assert len(vista.bufer_pretrigger) == 100
assert len(vista.buf_tiempo) == 0  # No volcadas todavía

# 3. Simular muestra de disparo de ignición (empuje sube abruptamente)
t_disparo = 0.505
v_disparo = 0.300  # 300 mV -> ~45 N filtrados (supera con holgura el umbral de 15 N)
vista._recibir_muestra(t_disparo, v_disparo)
vista._actualizar_graficas_y_metricas()

# Debe haberse confirmado la ignición
assert vista._ignicion_confirmada
assert vista.linea_ignicion.isVisible()
assert vista.linea_ignicion.value() == 0.0

# El registro de la prueba debe contener ahora las 100 muestras pre-trigger + 1 muestra T-0
assert len(vista.buf_tiempo) == 101

# Las primeras 100 muestras deben ser negativas
tiempos = list(vista.buf_tiempo)
for idx, t_pre in enumerate(tiempos[:100]):
    assert t_pre < 0.0, f"Muestra {idx} tiene tiempo {t_pre} >= 0.0 (tiempos[:5]={tiempos[:5]}, ultimos={tiempos[95:105]})"

# La muestra 101 debe ser exactamente t = 0.0
assert tiempos[100] == 0.0, f"Muestra 100 tiene tiempo {tiempos[100]} != 0.0"

# El impulso en pre-trigger debe ser 0.0
impulsos = list(vista.buf_impulso)
for imp_pre in impulsos[:100]:
    assert imp_pre == 0.0

# 4. Probar Mira y Tooltip Interactivo (Crosshair)
# Mover cursor dentro del ViewBox de Empuje
vb = vista.plot_empuje.plotItem.vb
# Obtener un punto dentro del rectángulo de escena del ViewBox
rect = vb.sceneBoundingRect()
punto_escena = QPointF(rect.center().x(), rect.center().y())

vista._al_mover_cursor(punto_escena, "empuje")
assert vista.crosshair_v_empuje.isVisible()
assert vista.crosshair_h_empuje.isVisible()
assert vista.tooltip_empuje.isVisible()
# Comprobar formato del texto
assert "Tiempo:" in vista.tooltip_empuje.toPlainText() or "Tiempo:" in str(vista.tooltip_empuje.textItem.toHtml())
assert "Empuje:" in vista.tooltip_empuje.toPlainText() or "Empuje:" in str(vista.tooltip_empuje.textItem.toHtml())

# Probar en Voltaje
vb_v = vista.plot_voltaje.plotItem.vb
rect_v = vb_v.sceneBoundingRect()
punto_v = QPointF(rect_v.center().x(), rect_v.center().y())
vista._al_mover_cursor(punto_v, "voltaje")
assert vista.crosshair_v_voltaje.isVisible()
assert vista.crosshair_h_voltaje.isVisible()
assert vista.tooltip_voltaje.isVisible()
assert "V_raw:" in str(vista.tooltip_voltaje.textItem.toHtml())

# Probar en Impulso
vb_i = vista.plot_impulso.plotItem.vb
rect_i = vb_i.sceneBoundingRect()
punto_i = QPointF(rect_i.center().x(), rect_i.center().y())
vista._al_mover_cursor(punto_i, "impulso")
assert vista.crosshair_v_impulso.isVisible()
assert vista.crosshair_h_impulso.isVisible()
assert vista.tooltip_impulso.isVisible()
assert "Impulso:" in str(vista.tooltip_impulso.textItem.toHtml())

# Cursor fuera del ViewBox debe ocultar la mira
punto_fuera = QPointF(-1000.0, -1000.0)
vista._al_mover_cursor(punto_fuera, "empuje")
assert not vista.crosshair_v_empuje.isVisible()
assert not vista.tooltip_empuje.isVisible()

# 5. Reiniciar datos y verificar restablecimiento total
vista.reiniciar_datos()
assert not vista._ignicion_confirmada
assert len(vista.bufer_pretrigger) == 0
assert len(vista.buf_tiempo) == 0
assert not vista.linea_ignicion.isVisible()
assert not vista.crosshair_v_empuje.isVisible()

print("PRETRIGGER_CROSSHAIR_TEST_OK")
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_script],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"Error en test UI: {resultado.stderr}"
    assert "PRETRIGGER_CROSSHAIR_TEST_OK" in resultado.stdout


def test_simulador_pretrigger_end_to_end():
    """Verifica el flujo completo de telemetría sintética con pre-trigger, detección T-0 y métricas."""
    codigo_script = """
import sys
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from comunicacion.simulador import SimuladorMotorCohete
from ui.vistas.vista_prueba import VistaPrueba
from core.balistica import calcular_metricas_balisticas

sim = SimuladorMotorCohete(frecuencia_hz=200.0)
vista = VistaPrueba()

# Generar 2.0 segundos de telemetría sintética (1.0 s reposo + 1.0 s combustión a 200 Hz)
# 400 muestras en total
dt = 0.005
for i in range(400):
    t = round(i * dt, 4)
    v = sim._calcular_voltaje_sintetico(t)
    vista._recibir_muestra(t, v)

vista._actualizar_graficas_y_metricas()

# 1. Verificar que la ignición fue detectada
assert vista._ignicion_confirmada
assert vista.linea_ignicion.value() == 0.0

# 2. Verificar que existen muestras con tiempo negativo (pre-trigger)
tiempos = list(vista.buf_tiempo)
muestras_pre = [t for t in tiempos if t < 0.0]
assert len(muestras_pre) >= 190  # Alrededor de 200 muestras (1.0 s)

# El tiempo de la primera muestra pre-trigger debe ser aprox -1.0 s
assert -1.05 <= muestras_pre[0] <= -0.95

# 3. Verificar que existe una muestra exactamente en t = 0.0 s
assert 0.0 in tiempos

# 4. Verificar muestras con tiempo positivo (fase de combustión)
muestras_post = [t for t in tiempos if t > 0.0]
assert len(muestras_post) > 100

# 5. El empuje pico debe ser cercano a 1950 N (1.95 V * 1000 N/V)
assert vista.empuje_pico_actual > 1500.0

# 6. Cálculo de métricas balísticas con datos que contienen pre-trigger
metricas = calcular_metricas_balisticas(
    tiempos=list(vista.buf_tiempo),
    empujes=list(vista.buf_empuje_filt),
    masa_propelente_g=300.0,
)
assert metricas.empuje_pico_n > 1500.0
assert metricas.impulso_total_ns > 0.0
assert metricas.clase_nakka != "N/A"

print("END_TO_END_OK")
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_script],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"Error en test end-to-end: {resultado.stderr}"
    assert "END_TO_END_OK" in resultado.stdout

