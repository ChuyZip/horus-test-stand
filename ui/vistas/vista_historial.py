"""Vista de historial, superposición multi-ensayo y análisis de envejecimiento de propelente.

Implementa:
- Tabla interactiva conectada a base de datos SQLite con filtrado y búsqueda.
- Superposición simultánea de curvas de empuje en pyqtgraph con leyendas automáticas.
- Gráfica balística de Impulso / Isp vs. Días de Vejez del grano.
- Exportación a CSV y administración de ensayos guardados.
"""

from __future__ import annotations

from typing import Optional

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from datos.gestor_db import GestorBD
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

COLORES_SUPERPOSICION = [
    "#00E5FF",  # Cian
    "#FFD600",  # Amarillo
    "#FF4081",  # Rosa Neón
    "#00E676",  # Verde
    "#FFFFFF",  # Blanco
    "#FF6D00",  # Naranja
    "#7C4DFF",  # Púrpura
    "#18FFFF",  # Aqua
]


class VistaHistorial(QWidget):
    """Panel de análisis comparativo multi-ensayo con base de datos SQLite."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.gestor_bd = GestorBD()
        self.ensayos_cargados: list[dict] = []
        self._curvas_activas: dict[int, pg.PlotDataItem] = {}

        self._construir_ui()
        self.recargar_tabla()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. ENCABEZADO Y BARRA DE BÚSQUEDA
        # -------------------------------------------------------------
        fila_header = QHBoxLayout()
        fila_header.setSpacing(12)

        vbox_tit = QVBoxLayout()
        vbox_tit.setSpacing(2)
        lbl_tit = QLabel("📊 HISTORIAL Y COMPARACIÓN DE ENSAYOS")
        lbl_tit.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 900; letter-spacing: 1px;"
        )
        lbl_desc = QLabel("Superposición multi-curva, correlación con días de vejez y exportación CSV desde SQLite.")
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 11px;")
        vbox_tit.addWidget(lbl_tit)
        vbox_tit.addWidget(lbl_desc)
        fila_header.addLayout(vbox_tit)
        fila_header.addStretch()

        # Búsqueda
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Filtrar por código o fecha...")
        self.txt_buscar.setFixedWidth(240)
        self.txt_buscar.setStyleSheet(
            f"background: {COLOR_PANEL_MEDIO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px 12px; font-size: 12px;"
        )
        self.txt_buscar.textChanged.connect(self._al_filtrar_tabla)
        fila_header.addWidget(self.txt_buscar)

        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px 14px; font-weight: 700;"
        )
        btn_actualizar.clicked.connect(self.recargar_tabla)
        fila_header.addWidget(btn_actualizar)

        layout.addLayout(fila_header)

        # -------------------------------------------------------------
        # 2. CONTENEDOR DIVIDIDO (SPLITTER): TABLA ARRIBA / GRÁFICAS ABAJO
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background-color: rgba(255, 255, 255, 0.1); height: 4px; }")

        # PANEL SUPERIOR: TABLA DE ENSAYOS
        panel_tabla = QFrame()
        panel_tabla.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px;"
        )
        vbox_tabla = QVBoxLayout(panel_tabla)
        vbox_tabla.setContentsMargins(8, 8, 8, 8)
        vbox_tabla.setSpacing(6)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels([
            "Ver", "ID", "Código", "Fecha", "Operadores",
            "Vejez", "Pico (N)", "Impulso (N·s)", "Isp (s)", "Clase Nakka"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: transparent;
                gridline-color: rgba(255, 255, 255, 0.08);
                border: none;
                color: #FFFFFF;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PANEL_CLARO};
                color: {COLOR_TEXTO_SECUNDARIO};
                font-weight: 800;
                font-size: 11px;
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
                padding: 6px;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(13, 110, 253, 0.35);
            }}
            """
        )
        self.tabla.itemChanged.connect(self._al_cambiar_item_tabla)
        vbox_tabla.addWidget(self.tabla)

        # Barra de acciones de la tabla
        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(8)

        self.btn_exportar = QPushButton("📥 Exportar a CSV...")
        self.btn_exportar.setStyleSheet(
            f"background: #1C3B68; color: #FFFFFF; border: 1px solid {COLOR_CIAN}; border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px;"
        )
        self.btn_exportar.clicked.connect(self._exportar_seleccionado)

        self.btn_eliminar = QPushButton("🗑️ Eliminar Ensayo")
        self.btn_eliminar.setStyleSheet(
            "background: rgba(213, 0, 0, 0.15); color: #FF5252; border: 1px solid #FF5252; border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 11px;"
        )
        self.btn_eliminar.clicked.connect(self._eliminar_seleccionado)

        fila_acciones.addWidget(self.btn_exportar)
        fila_acciones.addWidget(self.btn_eliminar)
        fila_acciones.addStretch()

        self.lbl_info_seleccion = QLabel("Selecciona casillas 'Ver' para superponer curvas en la gráfica inferior.")
        self.lbl_info_seleccion.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 11px;")
        fila_acciones.addWidget(self.lbl_info_seleccion)

        vbox_tabla.addLayout(fila_acciones)
        splitter.addWidget(panel_tabla)

        # PANEL INFERIOR: 2 GRÁFICAS COMPARATIVAS
        panel_graficas = QFrame()
        panel_graficas.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px;"
        )
        hbox_graf = QHBoxLayout(panel_graficas)
        hbox_graf.setContentsMargins(8, 8, 8, 8)
        hbox_graf.setSpacing(10)

        # Gráfica A: Superposición de Curvas de Empuje (N vs s)
        self.plot_superposicion = pg.PlotWidget()
        self._estilizar_plot(self.plot_superposicion, "SUPERPOSICIÓN DE CURVAS DE EMPUJE (N vs s)")
        self.plot_superposicion.setLabel("left", "Empuje", units="N", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})
        self.plot_superposicion.setLabel("bottom", "Tiempo", units="s", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})
        self.leyenda_superposicion = self.plot_superposicion.addLegend(offset=(10, 10))
        hbox_graf.addWidget(self.plot_superposicion, 60)

        # Gráfica B: Correlación Impulso / Isp vs. Días de Vejez
        self.plot_vejez = pg.PlotWidget()
        self._estilizar_plot(self.plot_vejez, "RENDIMIENTO VS. DÍAS DE VEJEZ (Isp vs días)")
        self.plot_vejez.setLabel("left", "Isp Específico", units="s", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})
        self.plot_vejez.setLabel("bottom", "Días de Almacenamiento", units="días", **{"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px"})

        self.scatter_vejez = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(color="#FFFFFF", width=1.5),
            brush=pg.mkBrush(COLOR_VERDE_NEON),
            symbol="o",
        )
        self.plot_vejez.addItem(self.scatter_vejez)
        hbox_graf.addWidget(self.plot_vejez, 40)

        splitter.addWidget(panel_graficas)
        splitter.setSizes([260, 380])
        layout.addWidget(splitter, 1)

    def _estilizar_plot(self, plot: pg.PlotWidget, titulo: str) -> None:
        plot.setBackground(COLOR_FONDO_PRINCIPAL)
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.getAxis("bottom").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))
        plot.getAxis("left").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))
        plot.setTitle(
            f"<span style='color:#FFFFFF; font-weight:800; font-size:10pt; letter-spacing:0.8px;'>{titulo}</span>"
        )
        plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def recargar_tabla(self) -> None:
        """Carga la lista de ensayos desde la base de datos SQLite."""
        self.ensayos_cargados = self.gestor_bd.obtener_todos_ensayos()
        self._poblar_tabla(self.ensayos_cargados)
        self._actualizar_grafica_vejez(self.ensayos_cargados)

    def _poblar_tabla(self, lista_ensayos: list[dict]) -> None:
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(lista_ensayos))

        for row, e in enumerate(lista_ensayos):
            # Checkbox de visualización
            item_check = QTableWidgetItem()
            item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item_check.setCheckState(Qt.CheckState.Unchecked)
            item_check.setData(Qt.ItemDataRole.UserRole, e["id"])
            self.tabla.setItem(row, 0, item_check)

            campos = [
                str(e["id"]),
                str(e["codigo_ensayo"]),
                str(e["fecha"]),
                str(e["operadores"] or "N/A"),
                f"{e['dias_vejez']} d",
                f"{e['empuje_pico_n']:,.1f}",
                f"{e['impulso_total_ns']:,.1f}",
                f"{e['isp_s']:.1f}",
                str(e["clase_nakka"] or "N/A"),
            ]

            for col, val in enumerate(campos, start=1):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col in (1, 5, 8, 9) else Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(row, col, item)

        self.tabla.blockSignals(False)

    def _al_filtrar_tabla(self, texto: str) -> None:
        filtro = texto.strip().lower()
        if not filtro:
            for r in range(self.tabla.rowCount()):
                self.tabla.setRowHidden(r, False)
            return

        for r in range(self.tabla.rowCount()):
            codigo = self.tabla.item(r, 2).text().lower()
            fecha = self.tabla.item(r, 3).text().lower()
            operador = self.tabla.item(r, 4).text().lower()
            coincide = filtro in codigo or filtro in fecha or filtro in operador
            self.tabla.setRowHidden(r, not coincide)

    def _al_cambiar_item_tabla(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return

        ensayo_id = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._agregar_curva_superposicion(ensayo_id)
        else:
            self._remover_curva_superposicion(ensayo_id)

    def _agregar_curva_superposicion(self, ensayo_id: int) -> None:
        if ensayo_id in self._curvas_activas:
            return

        telemetria = self.gestor_bd.obtener_telemetria_ensayo(ensayo_id)
        if not telemetria["tiempo"]:
            return

        # Buscar nombre del ensayo
        nombre = f"Ensayo #{ensayo_id}"
        for e in self.ensayos_cargados:
            if e["id"] == ensayo_id:
                nombre = f"{e['codigo_ensayo']} ({e['clase_nakka']})"
                break

        # Asignar color secuencial
        idx_color = len(self._curvas_activas) % len(COLORES_SUPERPOSICION)
        color_hex = COLORES_SUPERPOSICION[idx_color]

        curva = self.plot_superposicion.plot(
            telemetria["tiempo"],
            telemetria["empuje"],
            pen=pg.mkPen(color=color_hex, width=2.0),
            name=nombre,
        )
        self._curvas_activas[ensayo_id] = curva

    def _remover_curva_superposicion(self, ensayo_id: int) -> None:
        if ensayo_id in self._curvas_activas:
            curva = self._curvas_activas.pop(ensayo_id)
            self.plot_superposicion.removeItem(curva)

    def _actualizar_grafica_vejez(self, ensayos: list[dict]) -> None:
        puntos = []
        for e in ensayos:
            if e.get("dias_vejez") is not None and e.get("isp_s") is not None and e["isp_s"] > 0:
                puntos.append({"pos": (float(e["dias_vejez"]), float(e["isp_s"]))})

        self.scatter_vejez.setData(puntos)

    def _exportar_seleccionado(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selección requerida", "Selecciona una fila de la tabla para exportar.")
            return

        item_id = self.tabla.item(fila, 1)
        if not item_id:
            return

        ensayo_id = int(item_id.text())
        codigo = self.tabla.item(fila, 2).text()

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Ensayo a CSV",
            f"{codigo}_exportado.csv",
            "Archivos CSV (*.csv)",
        )
        if ruta:
            try:
                self.gestor_bd.exportar_csv(ensayo_id, ruta)
                QMessageBox.information(self, "Exportación Exitosa", f"Archivo generado en:\n{ruta}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")

    def _eliminar_seleccionado(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Selección requerida", "Selecciona una fila para eliminar.")
            return

        item_id = self.tabla.item(fila, 1)
        if not item_id:
            return

        ensayo_id = int(item_id.text())
        codigo = self.tabla.item(fila, 2).text()

        confirm = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el ensayo '{codigo}' (ID #{ensayo_id}) y toda su telemetría?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self._remover_curva_superposicion(ensayo_id)
            self.gestor_bd.eliminar_ensayo(ensayo_id)
            self.recargar_tabla()
