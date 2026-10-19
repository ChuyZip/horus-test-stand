"""Vista de calibración de transductor y celda de carga con ajuste lineal R².

Implementa:
- Procedimiento de calibración multipunto con pesas patrón conocidas (kg ↔ N ↔ V).
- Regresión lineal por mínimos cuadrados ordinarios (cálculo de pendiente m, offset b y R²).
- Gráfica interactiva en pyqtgraph con puntos medidos y recta ajustada.
- Registro de fecha, temperatura y alertas por baja correlación (R² < 0.998).
- Persistencia de factores de calibración en archivo de configuración JSON.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from estilo.tema import (
    COLOR_AMBAR,
    COLOR_BORDE_NORMAL,
    COLOR_CIAN,
    COLOR_FONDO_PRINCIPAL,
    COLOR_PANEL_CLARO,
    COLOR_PANEL_MEDIO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
    COLOR_VERDE_NEON,
)

GRAVEDAD = 9.80665


class VistaCalibracion(QWidget):
    """Panel de calibración científica con cálculo de factor N/V y regresión R²."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ruta_config = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "calibracion.json",
        )

        self._construir_ui()
        self._cargar_calibracion_existente()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Encabezado
        fila_tit = QHBoxLayout()
        vbox_tit = QVBoxLayout()
        vbox_tit.setSpacing(2)

        lbl_tit = QLabel("⚖️ CALIBRACIÓN DE CELDA DE CARGA Y TRANSDUCTORES")
        lbl_tit.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 900; letter-spacing: 1px;"
        )
        lbl_sub = QLabel("Ajuste lineal multipunto Voltaje (V) ↔ Fuerza (N) con pesas patrón y cálculo de R².")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 11px;")
        vbox_tit.addWidget(lbl_tit)
        vbox_tit.addWidget(lbl_sub)
        fila_tit.addLayout(vbox_tit)
        fila_tit.addStretch()

        self.lbl_estado_cal = QLabel("Estado: Calibración Predeterminada")
        self.lbl_estado_cal.setStyleSheet(
            f"color: {COLOR_CIAN}; font-size: 12px; font-weight: 700; background: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px 12px;"
        )
        fila_tit.addWidget(self.lbl_estado_cal)
        layout.addLayout(fila_tit)

        # Contenedor central: Columna izquierda (Tabla y Controles) y Columna derecha (Gráfica)
        fila_cuerpo = QHBoxLayout()
        fila_cuerpo.setSpacing(12)

        # COLUMNA IZQUIERDA: TABLA Y PARÁMETROS
        panel_izq = QFrame()
        panel_izq.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px;"
        )
        vbox_izq = QVBoxLayout(panel_izq)
        vbox_izq.setContentsMargins(10, 10, 10, 10)
        vbox_izq.setSpacing(8)

        lbl_sec1 = QLabel("PUNTOS DE CALIBRACIÓN CON PESAS PATRÓN")
        lbl_sec1.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;")
        vbox_izq.addWidget(lbl_sec1)

        # Tabla de puntos
        self.tabla_puntos = QTableWidget()
        self.tabla_puntos.setColumnCount(3)
        self.tabla_puntos.setHorizontalHeaderLabels(["Masa (kg)", "Fuerza (N)", "Voltaje (V)"])
        self.tabla_puntos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_puntos.verticalHeader().setVisible(False)
        self.tabla_puntos.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: transparent;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: none;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PANEL_CLARO};
                color: {COLOR_TEXTO_SECUNDARIO};
                font-weight: 800;
                font-size: 11px;
                border: none;
                padding: 4px;
            }}
            """
        )
        vbox_izq.addWidget(self.tabla_puntos, 1)

        # Botones para tabla
        fila_btn_tabla = QHBoxLayout()
        self.btn_agregar = QPushButton("➕ Agregar Punto")
        self.btn_agregar.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px 12px; font-weight: 700; font-size: 11px;"
        )
        self.btn_agregar.clicked.connect(self._agregar_fila_defecto)

        self.btn_quitar = QPushButton("🗑️ Quitar Punto")
        self.btn_quitar.setStyleSheet(
            "background: rgba(255, 255, 255, 0.06); color: rgba(255, 255, 255, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 6px 12px; font-size: 11px;"
        )
        self.btn_quitar.clicked.connect(self._quitar_fila_seleccionada)

        self.btn_ajustar = QPushButton("📐 Calcular Ajuste R²")
        self.btn_ajustar.setStyleSheet(
            f"background: #1C3B68; color: #FFFFFF; border: 1px solid {COLOR_CIAN}; border-radius: 6px; padding: 6px 14px; font-weight: 800; font-size: 11px;"
        )
        self.btn_ajustar.clicked.connect(self._calcular_regresion_lineal)

        fila_btn_tabla.addWidget(self.btn_agregar)
        fila_btn_tabla.addWidget(self.btn_quitar)
        fila_btn_tabla.addStretch()
        fila_btn_tabla.addWidget(self.btn_ajustar)
        vbox_izq.addLayout(fila_btn_tabla)

        # Panel de Resultados de la Regresión
        panel_kpi_cal = QFrame()
        panel_kpi_cal.setStyleSheet(
            f"background-color: {COLOR_PANEL_CLARO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px;"
        )
        vbox_kpi = QVBoxLayout(panel_kpi_cal)
        vbox_kpi.setSpacing(4)

        self.lbl_sensibilidad = QLabel("Sensibilidad (Pendiente m): 1000.00 N/V")
        self.lbl_sensibilidad.setStyleSheet(f"color: {COLOR_VERDE_NEON}; font-size: 12px; font-weight: 800;")
        self.lbl_offset = QLabel("Offset de Reposo (b): 0.00 N")
        self.lbl_offset.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700;")
        self.lbl_r2 = QLabel("Coeficiente R²: 1.0000 (Ajuste Ideal)")
        self.lbl_r2.setStyleSheet(f"color: {COLOR_AMBAR}; font-size: 11px; font-weight: 800;")

        vbox_kpi.addWidget(self.lbl_sensibilidad)
        vbox_kpi.addWidget(self.lbl_offset)
        vbox_kpi.addWidget(self.lbl_r2)
        vbox_izq.addWidget(panel_kpi_cal)

        # Botón para guardar y aplicar
        self.btn_guardar_cal = QPushButton("💾 Guardar y Aplicar Calibración")
        self.btn_guardar_cal.setStyleSheet(
            f"background: #007A3D; color: #FFFFFF; border: 1px solid {COLOR_VERDE_NEON}; border-radius: 6px; padding: 8px 16px; font-weight: 800; font-size: 12px;"
        )
        self.btn_guardar_cal.clicked.connect(self._guardar_calibracion)
        vbox_izq.addWidget(self.btn_guardar_cal)

        fila_cuerpo.addWidget(panel_izq, 45)

        # COLUMNA DERECHA: GRÁFICA DE CALIBRACIÓN
        panel_der = QFrame()
        panel_der.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px;"
        )
        vbox_der = QVBoxLayout(panel_der)
        vbox_der.setContentsMargins(8, 8, 8, 8)

        self.plot_cal = pg.PlotWidget()
        self.plot_cal.setBackground(COLOR_FONDO_PRINCIPAL)
        self.plot_cal.showGrid(x=True, y=True, alpha=0.12)
        self.plot_cal.getAxis("bottom").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))
        self.plot_cal.getAxis("left").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))
        self.plot_cal.setTitle(
            "<span style='color:#FFFFFF; font-weight:800; font-size:10pt; letter-spacing:0.8px;'>CURVA DE CALIBRACIÓN: VOLTAJE vs. FUERZA</span>"
        )
        self.plot_cal.setLabel("bottom", "Voltaje Medido", units="V", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})
        self.plot_cal.setLabel("left", "Fuerza Aplicada", units="N", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})

        # Puntos medidos
        self.scatter_puntos = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen(color="#FFFFFF", width=2),
            brush=pg.mkBrush(COLOR_CIAN),
            symbol="o",
            name="Puntos Medidos",
        )
        self.plot_cal.addItem(self.scatter_puntos)

        # Recta de regresión
        self.curva_ajuste = self.plot_cal.plot(
            pen=pg.mkPen(color=COLOR_VERDE_NEON, width=2.0, style=Qt.PenStyle.DashLine),
            name="Ajuste Lineal",
        )

        vbox_der.addWidget(self.plot_cal)
        fila_cuerpo.addWidget(panel_der, 55)

        layout.addLayout(fila_cuerpo, 1)

    def _agregar_fila(self, masa_kg: float, voltaje_v: float) -> None:
        fuerza_n = masa_kg * GRAVEDAD
        row = self.tabla_puntos.rowCount()
        self.tabla_puntos.insertRow(row)

        item_masa = QTableWidgetItem(f"{masa_kg:.3f}")
        item_fuerza = QTableWidgetItem(f"{fuerza_n:.2f}")
        item_fuerza.setFlags(item_fuerza.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item_volt = QTableWidgetItem(f"{voltaje_v:.4f}")

        self.tabla_puntos.setItem(row, 0, item_masa)
        self.tabla_puntos.setItem(row, 1, item_fuerza)
        self.tabla_puntos.setItem(row, 2, item_volt)

    def _agregar_fila_defecto(self) -> None:
        self._agregar_fila(1.0, 0.01)

    def _quitar_fila_seleccionada(self) -> None:
        row = self.tabla_puntos.currentRow()
        if row >= 0:
            self.tabla_puntos.removeRow(row)

    def _calcular_regresion_lineal(self) -> None:
        n_filas = self.tabla_puntos.rowCount()
        if n_filas < 2:
            QMessageBox.warning(self, "Puntos insuficientes", "Se requieren al menos 2 puntos para calcular la regresión lineal.")
            return

        voltajes = []
        fuerzas = []

        for r in range(n_filas):
            try:
                m_kg = float(self.tabla_puntos.item(r, 0).text())
                f_n = m_kg * GRAVEDAD
                self.tabla_puntos.item(r, 1).setText(f"{f_n:.2f}")
                v = float(self.tabla_puntos.item(r, 2).text())
                voltajes.append(v)
                fuerzas.append(f_n)
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Error de datos", f"Verifica que los valores de la fila {r+1} sean números válidos.")
                return

        x = np.array(voltajes, dtype=np.float64)
        y = np.array(fuerzas, dtype=np.float64)

        # Regresión por mínimos cuadrados ordinarios: y = m*x + b
        A = np.vstack([x, np.ones(len(x))]).T
        m, b = np.linalg.lstsq(A, y, rcond=None)[0]

        # Coeficiente de determinación R^2
        y_pred = m * x + b
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
        r2 = max(0.0, min(1.0, float(r2)))

        self.lbl_sensibilidad.setText(f"Sensibilidad (Pendiente m): {m:,.2f} N/V")
        self.lbl_offset.setText(f"Offset de Reposo (b): {b:,.2f} N")
        self.lbl_r2.setText(f"Coeficiente R²: {r2:.4f}" + (" (Excelente)" if r2 >= 0.998 else " (¡Advertencia: Revisa los puntos!)"))

        # Actualizar gráfica
        puntos = [{"pos": (float(x[i]), float(y[i]))} for i in range(len(x))]
        self.scatter_puntos.setData(puntos)

        x_line = np.linspace(min(x) * 0.9, max(x) * 1.1, 50)
        y_line = m * x_line + b
        self.curva_ajuste.setData(x_line, y_line)

        self.m_actual = m
        self.b_actual = b
        self.r2_actual = r2

    def _guardar_calibracion(self) -> None:
        if not hasattr(self, "m_actual"):
            self._calcular_regresion_lineal()
            if not hasattr(self, "m_actual"):
                return

        os.makedirs(os.path.dirname(self.ruta_config), exist_ok=True)
        datos_cal = {
            "factor_n_por_v": round(float(self.m_actual), 4),
            "offset_n": round(float(self.b_actual), 4),
            "r2": round(float(self.r2_actual), 5),
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "num_puntos": self.tabla_puntos.rowCount(),
        }

        try:
            with open(self.ruta_config, "w", encoding="utf-8") as f:
                json.dump(datos_cal, f, indent=4)
            self.lbl_estado_cal.setText(f"Calibrado: {datos_cal['fecha']}")
            QMessageBox.information(
                self,
                "Calibración Guardada",
                f"Factores de calibración guardados exitosamente:\nSensibilidad: {self.m_actual:,.2f} N/V\nR²: {self.r2_actual:.4f}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la calibración: {e}")

    def _cargar_calibracion_existente(self) -> None:
        # Puntos iniciales sugeridos
        puntos_base = [(0.0, 0.0), (1.0, 0.0098), (5.0, 0.0491), (10.0, 0.0981)]
        for m, v in puntos_base:
            self._agregar_fila(m, v)
        self._calcular_regresion_lineal()
