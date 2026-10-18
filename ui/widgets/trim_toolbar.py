"""
Barra de herramientas del modo de recorte de grafica.

Aparece debajo de la grafica cuando el usuario activa el modo recorte,
mostrando el rango seleccionado y botones para exportar o cancelar.
"""

import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class TrimToolbar(QWidget):
    """
    Toolbar que se muestra durante el modo de recorte de grafica.

    Muestra el rango de tiempo seleccionado en tiempo real y proporciona
    acciones para exportar el recorte o cancelar la operacion.
    """

    export_trim_requested = pyqtSignal()
    cancel_trim_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """
        Inicializa la toolbar de recorte (inicialmente oculta).

        Args:
            parent: Widget padre opcional.
        """
        super().__init__(parent)
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        """Construye los elementos visuales de la toolbar."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        lbl_mode = QLabel("✂  MODO RECORTE")
        lbl_mode.setStyleSheet(
            "color:#d4a843;font-size:10px;font-weight:bold;letter-spacing:2px;"
        )

        self.lbl_range = QLabel("Selecciona un rango arrastrando las lineas en la grafica...")
        self.lbl_range.setStyleSheet(
            "color:#40c4aa;font-size:11px;"
            "background:#261c13;padding:4px 10px;border-radius:4px;"
        )

        self.btn_export = QPushButton("💾  Exportar recorte")
        self.btn_export.setStyleSheet(
            "background:#1e2e16;color:#6dbf4a;"
            "border-color:#6dbf4a44;padding:6px 14px;"
        )
        self.btn_export.clicked.connect(self.export_trim_requested.emit)

        self.btn_cancel = QPushButton("✕  Cancelar recorte")
        self.btn_cancel.setStyleSheet(
            "background:#2e1614;color:#c4342d;"
            "border-color:#c4342d44;padding:6px 14px;"
        )
        self.btn_cancel.clicked.connect(self.cancel_trim_requested.emit)

        layout.addWidget(lbl_mode)
        layout.addWidget(self.lbl_range, 1)
        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_cancel)

    def update_range(self, t_start: float, t_end: float) -> None:
        """
        Actualiza el label con el rango de tiempo seleccionado.

        Args:
            t_start: Tiempo de inicio del recorte en segundos.
            t_end: Tiempo de fin del recorte en segundos.
        """
        duration = max(0.0, t_end - t_start)
        self.lbl_range.setText(
            f"Recorte:  {t_start:.2f}s  →  {t_end:.2f}s  "
            f"({duration:.2f}s de duracion)"
        )
