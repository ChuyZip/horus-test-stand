"""
Widget de la barra de controles.
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal
import serial.tools.list_ports

class ControlBar(QWidget):
    """
    Barra de herramientas con controles de conexión y acciones.
    """
    connect_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    unit_toggled = pyqtSignal()
    tare_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    export_requested = pyqtSignal()
    analysis_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """
        Inicializa la barra de controles.
        
        Args:
            parent: Widget padre.
        """
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye los botones y controles."""
        ctrl = QHBoxLayout(self)
        ctrl.setContentsMargins(0, 0, 0, 0)
        
        self.port_combo = QComboBox()
        
        self.btn_refresh = QPushButton("↺")
        self.btn_refresh.setFixedWidth(36)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        self.btn_refresh.clicked.connect(self.refresh_ports)
        
        self.btn_connect = QPushButton("⏚ CONECTAR")
        self.btn_connect.clicked.connect(self.connect_requested.emit)
        
        self.btn_start = QPushButton("▶ START")
        self.btn_start.setStyleSheet("background:#1e2e16;color:#6dbf4a;border-color:#6dbf4a44;")
        self.btn_start.clicked.connect(self.start_requested.emit)
        
        self.btn_stop = QPushButton("■ STOP")
        self.btn_stop.setStyleSheet("background:#2e1614;color:#c4342d;border-color:#c4342d44;")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        
        self.btn_unit = QPushButton("UNIDAD: N")
        self.btn_unit.setStyleSheet("background:#2e2118;color:#40c4aa;border-color:#40c4aa44;")
        self.btn_unit.clicked.connect(self.unit_toggled.emit)
        
        self.btn_tare = QPushButton("⊙ TARAR")
        self.btn_tare.clicked.connect(self.tare_requested.emit)
        
        self.btn_clear = QPushButton("⌫ LIMPIAR")
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        
        self.btn_export = QPushButton("↓ CSV")
        self.btn_export.clicked.connect(self.export_requested.emit)

        self.btn_analysis = QPushButton("ANALIZAR")
        self.btn_analysis.setStyleSheet("background:#2e2510;color:#40c4aa;border-color:#40c4aa44;")
        self.btn_analysis.clicked.connect(self.analysis_requested.emit)
        
        ctrl.addWidget(self.port_combo)
        ctrl.addWidget(self.btn_refresh)
        ctrl.addWidget(self.btn_connect)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addStretch()
        ctrl.addWidget(self.btn_unit)
        ctrl.addWidget(self.btn_tare)
        ctrl.addWidget(self.btn_clear)
        ctrl.addWidget(self.btn_export)
        ctrl.addWidget(self.btn_analysis)

        self.refresh_ports()

    def refresh_ports(self) -> None:
        """Actualiza la lista de puertos seriales disponibles."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_combo.addItem(p.device)

    def get_selected_port(self) -> str:
        """
        Obtiene el puerto serial seleccionado.
        
        Returns:
            str: El nombre del puerto seleccionado.
        """
        return self.port_combo.currentText()

    def set_start_stop_visible(self, visible: bool) -> None:
        """
        Muestra u oculta los botones de START/STOP.
        
        Args:
            visible: Verdadero para mostrar, falso para ocultar.
        """
        self.btn_start.setVisible(visible)
        self.btn_stop.setVisible(visible)

    def update_unit_label(self, is_kg: bool) -> None:
        """
        Actualiza el texto del botón de unidades.
        
        Args:
            is_kg: Verdadero si está en kg, falso si está en N.
        """
        self.btn_unit.setText("UNIDAD: kg" if is_kg else "UNIDAD: N")

    def set_wifi_mode(self, is_wifi: bool) -> None:
        """
        Ajusta la visibilidad de los controles de puerto según el modo WiFi.
        En modo WiFi, se oculta el combo de puertos seriales y el botón de recargar.
        """
        self.port_combo.setVisible(not is_wifi)
        self.btn_refresh.setVisible(not is_wifi)

    def set_recording_state(self, is_recording: bool) -> None:
        """
        Actualiza el estilo visual de los botones START y STOP
        para que sea evidente si el sistema esta grabando.
        """
        if is_recording:
            # Grabando: START deshabilitado y apagado, STOP en rojo brillante y activo
            self.btn_start.setEnabled(False)
            self.btn_start.setStyleSheet(
                "background:#1a120b;color:#4a3a30;border:1px solid #4a3a30;"
            )
            self.btn_stop.setEnabled(True)
            self.btn_stop.setStyleSheet(
                "background:#c4342d;color:#ffffff;border:2px solid #ffaaaa;font-weight:bold;"
            )
        else:
            # Detenido: START verde brillante y activo, STOP deshabilitado y apagado
            self.btn_start.setEnabled(True)
            self.btn_start.setStyleSheet(
                "background:#6dbf4a;color:#1a120b;border:2px solid #aaffaa;font-weight:bold;"
            )
            self.btn_stop.setEnabled(False)
            self.btn_stop.setStyleSheet(
                "background:#1a120b;color:#4a3a30;border:1px solid #4a3a30;"
            )
