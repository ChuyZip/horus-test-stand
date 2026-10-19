"""Vista de historial y comparación de ensayos para Horus Space Lab."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from estilo.tema import (
    COLOR_BORDE_NORMAL,
    COLOR_CIAN,
    COLOR_PANEL_CLARO,
    COLOR_PANEL_MEDIO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
)


class VistaHistorial(QWidget):
    """Panel para cargar, superponer y comparar curvas de ensayos previos (A vs B)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Encabezado
        lbl_titulo = QLabel("📊 HISTORIAL Y COMPARACIÓN DE ENSAYOS")
        lbl_titulo.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 18px; font-weight: 800; letter-spacing: 1px;"
        )
        lbl_sub = QLabel(
            "Carga archivos CSV de ensayos para superponer curvas de empuje, calcular variaciones porcentuales y clasificar motores."
        )
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 13px;")
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_sub)

        # Fila de tarjetas para Ensayo A y Ensayo B
        fila_ensayos = QHBoxLayout()
        fila_ensayos.setSpacing(16)

        # Tarjeta Ensayo A
        tarjeta_a = QFrame()
        tarjeta_a.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 18px;"
        )
        vbox_a = QVBoxLayout(tarjeta_a)
        lbl_tag_a = QLabel("ENSAYO BASE (A)")
        lbl_tag_a.setStyleSheet(f"color: {COLOR_CIAN}; font-weight: 800; font-size: 14px;")
        lbl_desc_a = QLabel("Sin archivo seleccionado")
        lbl_desc_a.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 12px;")
        btn_cargar_a = QPushButton("Cargar CSV Ensayo A")
        btn_cargar_a.setProperty("class", "BotonPrimario")
        vbox_a.addWidget(lbl_tag_a)
        vbox_a.addWidget(lbl_desc_a)
        vbox_a.addStretch()
        vbox_a.addWidget(btn_cargar_a)
        fila_ensayos.addWidget(tarjeta_a)

        # Tarjeta Ensayo B
        tarjeta_b = QFrame()
        tarjeta_b.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 18px;"
        )
        vbox_b = QVBoxLayout(tarjeta_b)
        lbl_tag_b = QLabel("ENSAYO COMPARATIVO (B)")
        lbl_tag_b.setStyleSheet(f"color: #FFD600; font-weight: 800; font-size: 14px;")
        lbl_desc_b = QLabel("Sin archivo seleccionado")
        lbl_desc_b.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 12px;")
        btn_cargar_b = QPushButton("Cargar CSV Ensayo B")
        btn_cargar_b.setProperty("class", "BotonPrimario")
        vbox_b.addWidget(lbl_tag_b)
        vbox_b.addWidget(lbl_desc_b)
        vbox_b.addStretch()
        vbox_b.addWidget(btn_cargar_b)
        fila_ensayos.addWidget(tarjeta_b)

        layout.addLayout(fila_ensayos)

        # Panel central de vista previa de comparación
        panel_comparacion = QFrame()
        panel_comparacion.setStyleSheet(
            f"background-color: {COLOR_PANEL_CLARO}; border: 1px dashed {COLOR_BORDE_NORMAL}; border-radius: 10px;"
        )
        vbox_comp = QVBoxLayout(panel_comparacion)
        lbl_placeholder = QLabel("📈 Espacio para superposición de curvas y métricas diferenciales A/B")
        lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_placeholder.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 14px; font-weight: 600;")
        vbox_comp.addWidget(lbl_placeholder)
        layout.addWidget(panel_comparacion, 1)
