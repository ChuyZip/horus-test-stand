"""Vista de configuración general del banco de pruebas para Horus Space Lab."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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


class VistaConfiguracion(QWidget):
    """Panel para configuración de puertos, frecuencias de muestreo y almacenamiento."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Encabezado
        lbl_titulo = QLabel("⚙️ CONFIGURACIÓN DEL SISTEMA Y TELEMETRÍA")
        lbl_titulo.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 18px; font-weight: 800; letter-spacing: 1px;"
        )
        lbl_sub = QLabel(
            "Ajusta los parámetros de hardware, interfaces serie/LoRa/UDP, tasa de muestreo y filtros digitales."
        )
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 13px;")
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_sub)

        # Tarjeta de configuración de comunicaciones
        tarjeta_com = QFrame()
        tarjeta_com.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 20px;"
        )
        grid = QGridLayout(tarjeta_com)
        grid.setSpacing(14)

        lbl_tipo = QLabel("Modo de Enlace:")
        lbl_tipo.setStyleSheet(f"color: {COLOR_TEXTO_PRINCIPAL}; font-weight: 600;")
        cb_tipo = QComboBox()
        cb_tipo.addItems(["Simulación Sintética (200 Hz)", "Serial / Cable USB", "LoRa Telemetry 915 MHz", "WiFi / UDP Port 8888"])
        cb_tipo.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px;"
        )

        lbl_rate = QLabel("Tasa de Muestreo (Hz):")
        lbl_rate.setStyleSheet(f"color: {COLOR_TEXTO_PRINCIPAL}; font-weight: 600;")
        txt_rate = QLineEdit("200")
        txt_rate.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px;"
        )

        lbl_filtro = QLabel("Filtro IIR - Frecuencia de corte (Hz):")
        lbl_filtro.setStyleSheet(f"color: {COLOR_TEXTO_PRINCIPAL}; font-weight: 600;")
        txt_filtro = QLineEdit("15.0")
        txt_filtro.setStyleSheet(
            f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 6px;"
        )

        grid.addWidget(lbl_tipo, 0, 0)
        grid.addWidget(cb_tipo, 0, 1)
        grid.addWidget(lbl_rate, 1, 0)
        grid.addWidget(txt_rate, 1, 1)
        grid.addWidget(lbl_filtro, 2, 0)
        grid.addWidget(txt_filtro, 2, 1)

        layout.addWidget(tarjeta_com)

        # Botones de guardado
        fila_btn = QHBoxLayout()
        btn_guardar = QPushButton("Guardar Preferencias")
        btn_guardar.setProperty("class", "BotonAccion")
        fila_btn.addStretch()
        fila_btn.addWidget(btn_guardar)
        layout.addLayout(fila_btn)

        layout.addStretch()
