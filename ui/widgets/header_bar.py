"""
Widget de la barra de encabezado (Header).
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from ui.utils import resource_path

class HeaderBar(QWidget):
    """
    Barra de encabezado superior con el logo y el estado de la conexión.
    """
    def __init__(self, parent=None) -> None:
        """
        Inicializa la barra de encabezado.
        
        Args:
            parent: Widget padre.
        """
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye la interfaz del encabezado."""
        hdr = QHBoxLayout(self)
        hdr.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_logo = QLabel()
        pix = QPixmap(resource_path("HorusSlogan.png"))
        if not pix.isNull():
            self.lbl_logo.setPixmap(pix.scaledToHeight(52, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_logo.setText("HORUS SPACE LAB")
            self.lbl_logo.setStyleSheet("color:#40c4aa;font-size:22px;font-weight:bold;")

        lbl_sys = QLabel("SISTEMA DE TELEMETRÍA  //  BANCO DE PRUEBAS")
        lbl_sys.setStyleSheet("color:#5566aa;font-size:11px;letter-spacing:3px;")
        
        self.lbl_status = QLabel("● DESCONECTADO")
        self.lbl_status.setStyleSheet("color:#c4342d;font-size:11px;font-weight:bold;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        hdr.addWidget(self.lbl_logo)
        hdr.addSpacing(16)
        hdr.addWidget(lbl_sys)
        hdr.addStretch()
        hdr.addWidget(self.lbl_status)

    def set_connected(self, connected: bool) -> None:
        """
        Actualiza el estado visual de la conexión.
        
        Args:
            connected: Si está conectado o no.
        """
        if connected:
            self.lbl_status.setText("● CONECTADO")
            self.lbl_status.setStyleSheet("color:#6dbf4a;font-size:11px;font-weight:bold;")
        else:
            self.lbl_status.setText("● DESCONECTADO")
            self.lbl_status.setStyleSheet("color:#c4342d;font-size:11px;font-weight:bold;")
