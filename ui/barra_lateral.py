"""Panel de navegación lateral para Horus Space Lab."""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from estilo.tema import (
    COLOR_BORDE_TENUE,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
)


class BarraLateral(QFrame):
    """Barra lateral de navegación para seleccionar las vistas operacionales."""

    vista_cambiada = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BarraLateral")
        self.botones_nav: list[QPushButton] = []
        self._indice_activo = 0
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 20, 14, 18)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. ENCABEZADO DE MARCA CON LOGO
        # -------------------------------------------------------------
        encabezado = QHBoxLayout()
        encabezado.setSpacing(12)

        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(46, 46)
        self.lbl_logo.setStyleSheet("border-radius: 23px; background: transparent;")

        # Cargar logo de Horus si existe
        ruta_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        if not os.path.exists(ruta_logo):
            ruta_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")

        if os.path.exists(ruta_logo):
            pixmap = QPixmap(ruta_logo).scaled(
                46,
                46,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_logo.setPixmap(pixmap)
        else:
            self.lbl_logo.setText("🚀")
            self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        encabezado.addWidget(self.lbl_logo)

        vbox_marca = QVBoxLayout()
        vbox_marca.setSpacing(2)

        lbl_nombre = QLabel("HORUS")
        lbl_nombre.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 900; letter-spacing: 2px;"
        )
        lbl_sub = QLabel("SPACE LAB")
        lbl_sub.setStyleSheet(
            f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;"
        )
        vbox_marca.addWidget(lbl_nombre)
        vbox_marca.addWidget(lbl_sub)
        encabezado.addLayout(vbox_marca)
        encabezado.addStretch()

        layout.addLayout(encabezado)

        # Divisor tenue
        divisor = QFrame()
        divisor.setFrameShape(QFrame.Shape.HLine)
        divisor.setStyleSheet(f"background-color: {COLOR_BORDE_TENUE}; max-height: 1px; border: none; margin: 10px 0;")
        layout.addWidget(divisor)

        # -------------------------------------------------------------
        # 2. BOTONES DE NAVEGACIÓN
        # -------------------------------------------------------------
        items_nav = [
            ("🚀  Prueba en Vivo", 0),
            ("📊  Historial / Comparar", 1),
            ("⚖️  Calibración N/V", 2),
            ("⚙️  Configuración", 3),
        ]

        for texto, idx in items_nav:
            btn = QPushButton(texto)
            btn.setProperty("class", "BotonNav")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("activo", "true" if idx == 0 else "false")
            btn.clicked.connect(lambda checked=False, i=idx: self._al_hacer_clic_nav(i))
            layout.addWidget(btn)
            self.botones_nav.append(btn)

        layout.addStretch()

        # -------------------------------------------------------------
        # 3. INFORMACIÓN DEL SISTEMA INFERIOR
        # -------------------------------------------------------------
        caja_info = QFrame()
        caja_info.setStyleSheet(
            f"background-color: rgba(255, 255, 255, 0.03); border: 1px solid {COLOR_BORDE_TENUE}; border-radius: 8px; padding: 10px;"
        )
        vbox_info = QVBoxLayout(caja_info)
        vbox_info.setContentsMargins(8, 8, 8, 8)
        vbox_info.setSpacing(3)

        lbl_motor = QLabel("BANCO DE PRUEBAS")
        lbl_motor.setStyleSheet(
            f"color: {COLOR_TEXTO_MUTED}; font-size: 9px; font-weight: 800; letter-spacing: 1px;"
        )
        lbl_core = QLabel("PySide6 • 200 Hz")
        lbl_core.setStyleSheet(
            f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 11px; font-weight: 600;"
        )
        lbl_version = QLabel("v2026.2 • macOS Native")
        lbl_version.setStyleSheet(
            f"color: {COLOR_TEXTO_MUTED}; font-size: 10px;"
        )

        vbox_info.addWidget(lbl_motor)
        vbox_info.addWidget(lbl_core)
        vbox_info.addWidget(lbl_version)
        layout.addWidget(caja_info)

    def _al_hacer_clic_nav(self, indice: int) -> None:
        """Maneja el clic en un botón de navegación y actualiza estilos."""
        if indice == self._indice_activo:
            return

        self._indice_activo = indice
        for i, btn in enumerate(self.botones_nav):
            esta_activo = i == indice
            btn.setProperty("activo", "true" if esta_activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.vista_cambiada.emit(indice)

    def seleccionar_vista(self, indice: int) -> None:
        """Permite cambiar la vista de forma programática."""
        self._al_hacer_clic_nav(indice)
