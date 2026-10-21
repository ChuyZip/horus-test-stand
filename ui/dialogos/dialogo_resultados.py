"""Diálogo modal de reporte consolidado de resultados balísticos post-ensayo."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.balistica import MetricasBalisticas
from datos.gestor_db import EnsayoMetadata
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


class DialogoResultados(QDialog):
    """Panel de presentación de métricas finales, guardado en SQLite y exportación CSV."""

    guardado_solicitado = Signal(object, str)  # (metadata_actualizada, clase_nakka_ajustada)

    def __init__(
        self,
        meta: EnsayoMetadata,
        metricas: MetricasBalisticas,
        gestor_bd_fn=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resultados Balísticos Consolidados - Horus Space Lab")
        self.setFixedSize(680, 520)
        self.setModal(True)

        self.meta = meta
        self.metricas = metricas
        self.gestor_bd_fn = gestor_bd_fn

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_FONDO_PRINCIPAL};
                color: {COLOR_TEXTO_PRINCIPAL};
            }}
            """
        )

        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Encabezado
        lbl_tit = QLabel("🚀 ANÁLISIS BALÍSTICO POST-ENSAYO")
        lbl_tit.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 17px; font-weight: 900; letter-spacing: 1.2px;"
        )
        geom = getattr(self.meta, "geometria_grano", "BATES")
        cluster = getattr(self.meta, "cluster_motores", "1x")
        lbl_sub = QLabel(
            f"Código: {self.meta.codigo_ensayo} • Operadores: {self.meta.operadores} • Grano: {geom} • Cluster: {cluster}"
        )
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 12px; font-weight: 600;")
        layout.addWidget(lbl_tit)
        layout.addWidget(lbl_sub)

        # Tarjeta central con cuadrícula de resultados
        tarjeta = QFrame()
        tarjeta.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 14px;"
        )
        grid = QGridLayout(tarjeta)
        grid.setSpacing(14)

        items_kpi = [
            ("EMPUJE MÁXIMO (F_max)", f"{self.metricas.empuje_pico_n:,.1f} N", "#FFFFFF"),
            ("TIEMPO DEL PICO (t_pico)", f"{self.metricas.tiempo_pico_s:.3f} s", COLOR_CIAN),
            ("EMPUJE PROMEDIO (F_bar)", f"{self.metricas.empuje_promedio_n:,.1f} N", COLOR_VERDE_NEON),
            ("TIEMPO DE QUEMADO (t_b)", f"{self.metricas.tiempo_quemado_s:.3f} s", COLOR_CIAN),
            ("IMPULSO TOTAL (I_tot)", f"{self.metricas.impulso_total_ns:,.2f} N·s", COLOR_AMBAR),
            ("IMPULSO ESPECÍFICO (Isp)", f"{self.metricas.isp_s:.1f} s", COLOR_VERDE_NEON),
            ("VELOCIDAD DE QUEMADO (r)", f"{self.metricas.velocidad_quemado_mm_s:.2f} mm/s", "#FFFFFF"),
        ]

        for i, (tit, val, col) in enumerate(items_kpi):
            r = i // 2
            c = (i % 2) * 2

            lbl_t = QLabel(tit)
            lbl_t.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(
                f"color: {col}; font-size: 18px; font-weight: 900; font-family: 'Menlo', Consolas, monospace;"
            )

            grid.addWidget(lbl_t, r * 2, c)
            grid.addWidget(lbl_v, r * 2 + 1, c)

        # Campo editable para clasificación Nakka
        r_nakka = 4
        lbl_nakka_tit = QLabel("CLASIFICACIÓN NAKKA / NAR (EDITABLE):")
        lbl_nakka_tit.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800;")
        self.txt_nakka = QLineEdit(f"{self.metricas.clase_nakka} ({self.metricas.porcentaje_clase}%)")
        self.txt_nakka.setStyleSheet(
            f"background-color: {COLOR_PANEL_CLARO}; color: {COLOR_AMBAR}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px 10px; font-weight: 800; font-size: 13px;"
        )

        grid.addWidget(lbl_nakka_tit, r_nakka * 2, 0)
        grid.addWidget(self.txt_nakka, r_nakka * 2 + 1, 0, 1, 3)

        layout.addWidget(tarjeta)

        # Botones de Acción
        fila_btn = QHBoxLayout()
        fila_btn.setSpacing(10)

        self.btn_exportar = QPushButton("📥 Exportar CSV...")
        self.btn_exportar.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px 16px; font-weight: 700;"
        )
        self.btn_exportar.clicked.connect(self._al_exportar_csv)

        self.btn_guardar_bd = QPushButton("💾 Guardar en Base de Datos")
        self.btn_guardar_bd.setStyleSheet(
            f"background: #007A3D; color: #FFFFFF; border: 1px solid {COLOR_VERDE_NEON}; border-radius: 6px; padding: 8px 20px; font-weight: 800; font-size: 13px;"
        )
        self.btn_guardar_bd.clicked.connect(self._al_guardar_bd)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.08); color: {COLOR_TEXTO_SECUNDARIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px 16px; font-weight: 700;"
        )
        self.btn_cerrar.clicked.connect(self.accept)

        fila_btn.addWidget(self.btn_exportar)
        fila_btn.addStretch()
        fila_btn.addWidget(self.btn_cerrar)
        fila_btn.addWidget(self.btn_guardar_bd)

        layout.addLayout(fila_btn)

    def _al_guardar_bd(self) -> None:
        self.meta.empuje_pico_n = self.metricas.empuje_pico_n
        self.meta.empuje_prom_n = self.metricas.empuje_promedio_n
        self.meta.impulso_total_ns = self.metricas.impulso_total_ns
        self.meta.isp_s = self.metricas.isp_s
        self.meta.tiempo_quemado_s = self.metricas.tiempo_quemado_s
        self.meta.velocidad_quemado_mm_s = self.metricas.velocidad_quemado_mm_s
        self.meta.clase_nakka = self.txt_nakka.text().strip()

        self.guardado_solicitado.emit(self.meta, self.meta.clase_nakka)
        self.btn_guardar_bd.setEnabled(False)
        self.btn_guardar_bd.setText("✅ Guardado en SQLite")

    def _al_exportar_csv(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Resultados a CSV",
            f"{self.meta.codigo_ensayo}_telemetria.csv",
            "Archivos CSV (*.csv)",
        )
        if ruta and self.gestor_bd_fn:
            try:
                self.gestor_bd_fn(ruta)
                QMessageBox.information(self, "Exportación Exitosa", f"Archivo generado correctamente en:\n{ruta}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")
