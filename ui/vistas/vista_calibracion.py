"""Vista de calibración de transductor y celda de carga para Horus Space Lab."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


class VistaCalibracion(QWidget):
    """Panel para caracterización y calibración de celda de carga y transductor de presión."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Encabezado
        lbl_titulo = QLabel("⚖️ CALIBRACIÓN DE CELDA DE CARGA Y TRANSDUCTORES")
        lbl_titulo.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 18px; font-weight: 800; letter-spacing: 1px;"
        )
        lbl_sub = QLabel(
            "Configura la relación lineal entre tensión analógica (V / mV) y fuerza en Newtons o kilogramos-fuerza."
        )
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 13px;")
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_sub)

        # Panel de parámetros de calibración
        tarjeta_params = QFrame()
        tarjeta_params.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 20px;"
        )
        grid = QGridLayout(tarjeta_params)
        grid.setSpacing(14)

        lbl_factor = QLabel("Factor de Sensibilidad (N / V):")
        lbl_factor.setStyleSheet(f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 13px; font-weight: 600;")
        txt_factor = QLineEdit("1000.00")
        txt_factor.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px;"
        )

        lbl_tara = QLabel("Tensión de Offset / Reposo (V):")
        lbl_tara.setStyleSheet(f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 13px; font-weight: 600;")
        txt_tara = QLineEdit("0.000")
        txt_tara.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px;"
        )

        btn_aplicar = QPushButton("Aplicar Calibración")
        btn_aplicar.setProperty("class", "BotonAccion")
        btn_tara = QPushButton("Tarar Cero Actual")
        btn_tara.setProperty("class", "BotonPrimario")

        grid.addWidget(lbl_factor, 0, 0)
        grid.addWidget(txt_factor, 0, 1)
        grid.addWidget(lbl_tara, 1, 0)
        grid.addWidget(txt_tara, 1, 1)

        fila_botones = QHBoxLayout()
        fila_botones.addWidget(btn_tara)
        fila_botones.addWidget(btn_aplicar)
        grid.addLayout(fila_botones, 2, 0, 1, 2)

        layout.addWidget(tarjeta_params)

        # Panel gráfico para curva de calibración V vs N
        panel_curva = QFrame()
        panel_curva.setStyleSheet(
            f"background-color: {COLOR_PANEL_CLARO}; border: 1px dashed {COLOR_BORDE_NORMAL}; border-radius: 10px;"
        )
        vbox_curva = QVBoxLayout(panel_curva)
        lbl_curva_info = QLabel("📊 Gráfica de respuesta y regresión lineal Voltaje vs. Fuerza")
        lbl_curva_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_curva_info.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 14px; font-weight: 600;")
        vbox_curva.addWidget(lbl_curva_info)

        layout.addWidget(panel_curva, 1)
