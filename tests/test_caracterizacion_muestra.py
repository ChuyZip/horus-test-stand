"""Pruebas unitarias para la ventana modal de datos de la muestra, persistencia y exportación."""

import os
import subprocess
import sys

from datos.gestor_db import EnsayoMetadata, GestorBD


def test_ensayo_metadata_nuevos_campos():
    meta = EnsayoMetadata(
        codigo_ensayo="TEST-01",
        operadores="Operador Test",
    )
    assert meta.geometria_grano == "BATES (Cilíndrico con núcleo perforado)"
    assert meta.cluster_motores == "1x (Motor individual / Monomotor)"
    assert meta.num_motores == 1

    # Verificación con cluster dual
    meta.cluster_motores = "2x (Cluster dual)"
    assert meta.num_motores == 2

    # Verificación con cluster personalizado
    meta.cluster_motores = "Personalizado (6x)"
    assert meta.num_motores == 6

    # Verificación con int directo
    meta.cluster_motores = 4
    assert meta.num_motores == 4


def test_gestor_bd_persistencia_y_csv(tmp_path):
    ruta_db = os.path.join(tmp_path, "test_ensayos.db")
    gestor = GestorBD(ruta_db=ruta_db)

    meta = EnsayoMetadata(
        codigo_ensayo="EXP-CLUSTER-01",
        operadores="Equipo HSL",
        geometria_grano="Finocyl (Núcleo estrellado / aletas)",
        cluster_motores="3x (Cluster triangular)",
        masa_propelente_g=350.0,
        diam_ext_mm=45.0,
        diam_int_mm=15.0,
        altura_mm=180.0,
    )

    tiempos = [0.0, 0.1, 0.2]
    voltajes = [0.0, 1.5, 0.0]
    empujes = [0.0, 120.0, 0.0]
    impulsos = [0.0, 6.0, 12.0]

    ensayo_id = gestor.guardar_ensayo(meta, tiempos, voltajes, empujes, impulsos)
    assert ensayo_id > 0

    ensayos = gestor.obtener_todos_ensayos()
    assert len(ensayos) == 1
    guardado = ensayos[0]
    assert guardado["codigo_ensayo"] == "EXP-CLUSTER-01"
    assert guardado["geometria_grano"] == "Finocyl (Núcleo estrellado / aletas)"
    assert guardado["cluster_motores"] == "3x (Cluster triangular)"

    # Exportación CSV y validación de cabecera
    ruta_csv = os.path.join(tmp_path, "reporte_test.csv")
    gestor.exportar_csv(ensayo_id, ruta_csv)
    assert os.path.exists(ruta_csv)

    with open(ruta_csv, mode="r", encoding="utf-8") as f:
        lineas = f.readlines()

    lineas_texto = "".join(lineas)
    assert "# Geometria Grano,Finocyl (Núcleo estrellado / aletas)" in lineas_texto
    assert "# Cluster Motores,3x (Cluster triangular)" in lineas_texto


def test_dialogo_muestra_y_vista_prueba_ui():
    """Ejecuta las pruebas de interfaz gráfica en subproceso aislado."""
    codigo_script = """
import sys
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from ui.dialogos.dialogo_muestra import DialogoMuestra, GEOMETRIAS_GRANO, CONFIGURACIONES_CLUSTER, ESTILO_BORDE_ERROR
from ui.vistas.vista_prueba import VistaPrueba

dlg = DialogoMuestra()
assert dlg.windowTitle() == "Ficha Técnica de la Muestra / Motor - Horus Space Lab"
assert dlg.minimumHeight() >= 760

# Verificar opciones de geometría de grano y valor por defecto
assert dlg.combo_geometria.count() == len(GEOMETRIAS_GRANO)
assert dlg.combo_geometria.currentText() == "BATES (Cilíndrico con núcleo perforado)"
for op in [
    "BATES (Cilíndrico con núcleo perforado)",
    "Finocyl (Núcleo estrellado / aletas)",
    "End-Burning (Combustión frontal / cigarrillo)",
    "C-Slot (Ranura en C)",
    "Moon Burner (Núcleo excéntrico)",
    "Tubular / Externo-Interno",
]:
    assert dlg.combo_geometria.findText(op) >= 0

# Verificar configuración cluster y valor por defecto
assert dlg.combo_cluster.count() == len(CONFIGURACIONES_CLUSTER)
assert dlg.combo_cluster.currentText() == "1x (Motor individual / Monomotor)"
assert dlg.spn_cluster_personalizado.isHidden()

# Selección de personalizado activa el spinbox
dlg.combo_cluster.setCurrentText("Personalizado (con número de motores activos)")
assert not dlg.spn_cluster_personalizado.isHidden()
dlg.spn_cluster_personalizado.setValue(6)
assert dlg._obtener_valor_cluster() == "Personalizado (6x)"

# Validación exitosa y guardado en dataclass y dict
dlg.txt_id.setText("EXP-MODAL-TEST")
dlg.combo_geometria.setCurrentText("Moon Burner (Núcleo excéntrico)")
dlg._validar_y_guardar()

assert dlg.metadata_resultado is not None
assert dlg.metadata_resultado.codigo_ensayo == "EXP-MODAL-TEST"
assert dlg.metadata_resultado.geometria_grano == "Moon Burner (Núcleo excéntrico)"
assert dlg.metadata_resultado.cluster_motores == "Personalizado (6x)"
assert dlg.datos["geometria_grano"] == "Moon Burner (Núcleo excéntrico)"
assert dlg.datos["cluster_motores"] == "Personalizado (6x)"

# Verificar texto actualizado del botón en VistaPrueba
vista = VistaPrueba()
assert vista.btn_muestra.text() == "📋 DATOS DE LA MUESTRA"

# ==============================================================
# VALIDACIÓN ESTRICTA DE FORMULARIO Y RESTAURACIÓN DE ESTILOS
# ==============================================================
dlg2 = DialogoMuestra()

# 1. Vaciar ID de Muestra y Operadores
dlg2.txt_id.setText("   ")
dlg2.txt_operadores.setText("")
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("ID de Muestra" in e for e in errores)
assert any("Operador(es)" in e for e in errores)
assert dlg2.txt_id.styleSheet() == ESTILO_BORDE_ERROR
assert dlg2.txt_operadores.styleSheet() == ESTILO_BORDE_ERROR

# Al escribir en txt_id se debe limpiar el borde rojo inmediatamente
dlg2.txt_id.setText("EXP-VALID-01")
assert dlg2.txt_id.styleSheet() == ""

# 2. Validación de Fecha de Ensayo corrupta (ej. '2026--21')
dlg2.txt_operadores.setText("Operador")
dlg2.date_fecha.findChild(type(dlg2.date_fecha.lineEdit())).setCursorPosition(7)
dlg2.date_fecha.findChild(type(dlg2.date_fecha.lineEdit())).backspace()
dlg2.date_fecha.findChild(type(dlg2.date_fecha.lineEdit())).backspace()
assert dlg2.date_fecha.text() == "2026--21"

valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Fecha de Ensayo" in e for e in errores)
assert dlg2.date_fecha.styleSheet() == ESTILO_BORDE_ERROR

# Restaurar fecha válida
from PySide6.QtCore import QDate
dlg2.date_fecha.setDate(QDate.currentDate())
assert dlg2.date_fecha.text() == QDate.currentDate().toString("yyyy-MM-dd")

# 3. Validación de spinbox vacío o corrupto con solo sufijo de unidad
dlg2.spn_diam_ext.lineEdit().setText(" mm")
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Diámetro Exterior" in e for e in errores)
assert dlg2.spn_diam_ext.styleSheet() == ESTILO_BORDE_ERROR

dlg2.spn_diam_ext.setValue(20.0)
assert dlg2.spn_diam_ext.styleSheet() == ""

dlg2.spn_vejez.lineEdit().setText("días")
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Días de Vejez" in e for e in errores)
assert dlg2.spn_vejez.styleSheet() == ESTILO_BORDE_ERROR

dlg2.spn_vejez.setValue(10)
assert dlg2.spn_vejez.styleSheet() == ""

# 4. Validación de Diámetro Interior >= Diámetro Exterior
dlg2.spn_diam_ext.setValue(20.0)
dlg2.spn_diam_int.setValue(25.0)
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Diámetro Interior" in e for e in errores)
assert dlg2.spn_diam_int.styleSheet() == ESTILO_BORDE_ERROR

# Al corregir diámetro se limpia
dlg2.spn_diam_int.setValue(10.0)
assert dlg2.spn_diam_int.styleSheet() == ""

# 5. Validación de Masa <= 0 y Altura <= 0
dlg2.spn_masa.setValue(0.0)
dlg2.spn_altura.setValue(0.0)
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Masa Inicial" in e for e in errores)
assert any("Altura / Longitud" in e for e in errores)
assert dlg2.spn_masa.styleSheet() == ESTILO_BORDE_ERROR
assert dlg2.spn_altura.styleSheet() == ESTILO_BORDE_ERROR

dlg2.spn_masa.setValue(150.0)
dlg2.spn_altura.setValue(100.0)
assert dlg2.spn_masa.styleSheet() == ""
assert dlg2.spn_altura.styleSheet() == ""

# 6. Validación de Tipo / Composición de Propelente
dlg2.txt_composicion.setText("   ")
valido, errores = dlg2.validar_formulario()
assert not valido
assert any("Composición de Propelente" in e for e in errores)
assert dlg2.txt_composicion.styleSheet() == ESTILO_BORDE_ERROR

dlg2.txt_composicion.setText("KNSB 65/35")
assert dlg2.txt_composicion.styleSheet() == ""

# 7. Formulario completamente válido
valido, errores = dlg2.validar_formulario()
assert valido
assert len(errores) == 0

print("UI_TEST_OK")
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_script],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, f"Error en test UI: {resultado.stderr}"
    assert "UI_TEST_OK" in resultado.stdout
