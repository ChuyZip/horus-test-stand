"""
Ventana principal — orquestador del sistema de telemetria Horus.
"""
import os
import time
import logging
from typing import Optional, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer

from config.constants import GRAVITY, THRUST_THRESHOLD, DEFAULT_BAUDRATE, RECONNECT_INTERVAL_MS
from config.styles import MAIN_STYLESHEET
from config.settings import AppSettings
from communication.protocols import ConnectionMode
from core.telemetry_engine import TelemetryEngine
from communication.serial_reader import SerialReader
from communication.udp_reader import UdpReader
from persistence.auto_saver import AutoSaver
from persistence.csv_exporter import export_telemetry_csv, export_trim_csv
from ui.widgets.kpi_card import KpiCard
from ui.widgets.header_bar import HeaderBar
from ui.widgets.control_bar import ControlBar
from ui.widgets.ignition_panel import IgnitionPanel
from ui.widgets.graph_panel import GraphPanel
from ui.widgets.trim_toolbar import TrimToolbar
from ui.dialogs.export_dialog import ExportConfirmDialog
from ui.dialogs.analysis_window import CsvAnalysisWindow
from ui.dialogs.voltage_characterization_window import VoltageCharacterizationWindow
from utils.paths import resource_path

logger = logging.getLogger(__name__)


class RocketDashboard(QMainWindow):
    """Ventana principal del orquestador para la telemetria del banco de pruebas."""

    def __init__(self) -> None:
        """Inicializa la ventana principal y compone todos los widgets."""
        super().__init__()
        self.setWindowTitle("Horus Space Lab \u2014 Telemetria de Banco de Pruebas")
        self.resize(1280, 860)
        self.setWindowIcon(QIcon(resource_path("favicon.ico")))
        self.setStyleSheet(MAIN_STYLESHEET)

        self.engine = TelemetryEngine()
        self.settings = AppSettings()
        self.settings.load()

        self.conn_mode: ConnectionMode = ConnectionMode.LORA
        self.auto_saver: Optional[AutoSaver] = None
        self.comm_thread: Optional[SerialReader | UdpReader] = None
        self.analysis_window: Optional[CsvAnalysisWindow] = None
        self.characterization_window: Optional[VoltageCharacterizationWindow] = None
        self._trim_active: bool = False

        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(RECONNECT_INTERVAL_MS)
        self.reconnect_timer.timeout.connect(self._try_reconnect)

        self._build_ui()
        self._connect_signals()

        if self.settings.get("last_port", ""):
            QTimer.singleShot(800, self._auto_reconnect)

    def _build_ui(self) -> None:
        """Construye la interfaz de usuario."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.header = HeaderBar()
        layout.addWidget(self.header)

        self.control_bar = ControlBar()
        self.control_bar.set_recording_state(False)
        layout.addWidget(self.control_bar)

        # Fila de KPIs
        kpi_layout = QHBoxLayout()
        self.kpi_thrust = KpiCard(
            "EMPUJE", "N", tooltip="Fuerza instantanea medida por la celda de carga."
        )
        self.kpi_max = KpiCard(
            "MAXIMO", "N", tooltip="Mayor empuje registrado durante el ensayo actual."
        )
        self.kpi_impulse = KpiCard(
            "IMPULSO", "Ns", tooltip="Empuje acumulado a lo largo del tiempo; mide la energia total entregada."
        )
        self.kpi_class = KpiCard(
            "CLASE", "", tooltip="Clase NAR calculada a partir del impulso total acumulado."
        )
        self.kpi_rssi = KpiCard(
            "SENAL", "dBm", tooltip="Intensidad de la senal LoRa recibida. Un valor mas cercano a cero es mejor."
        )
        self.kpi_lost_pkts = KpiCard(
            "PERDIDOS", "", tooltip="Paquetes de telemetria ausentes detectados por el numero de secuencia."
        )
        for kpi in [self.kpi_thrust, self.kpi_max, self.kpi_impulse,
                    self.kpi_class, self.kpi_rssi, self.kpi_lost_pkts]:
            kpi_layout.addWidget(kpi)
        layout.addLayout(kpi_layout)

        # Fila de modos + recorte
        mode_layout = QHBoxLayout()
        self.btn_mode_lora = QPushButton("Modo LoRa")
        self.btn_mode_cable = QPushButton("Modo Cable/RS-485")
        self.btn_mode_lora.clicked.connect(lambda: self._set_mode(ConnectionMode.LORA))
        self.btn_mode_cable.clicked.connect(lambda: self._set_mode(ConnectionMode.CABLE))

        self.btn_mode_wifi = QPushButton("Modo WiFi")
        self.btn_mode_wifi.clicked.connect(lambda: self._set_mode(ConnectionMode.WIFI))

        self.btn_voltage = QPushButton("VOLT/KG")
        self.btn_voltage.setStyleSheet(
            "background:#3d2a10;color:#e8922f;border-color:#e8922f44;"
        )
        self.btn_voltage.clicked.connect(self._open_characterization)

        self.btn_trim = QPushButton("\u2702 RECORTAR")
        self.btn_trim.setStyleSheet(
            "background:#2e2118;color:#d4a843;border-color:#d4a84344;"
        )
        self.btn_trim.clicked.connect(self._toggle_trim_mode)

        self.btn_choose_save_folder = QPushButton("CARPETA CSV")
        self.btn_choose_save_folder.setStyleSheet(
            "background:#2e2510;color:#40c4aa;border-color:#40c4aa44;"
        )
        self.btn_choose_save_folder.clicked.connect(self._choose_save_folder)

        self.lbl_savepath = QLabel("Autoguardando: NO ACTIVO")
        mode_layout.addWidget(self.btn_mode_lora)
        mode_layout.addWidget(self.btn_mode_cable)
        mode_layout.addWidget(self.btn_mode_wifi)
        mode_layout.addWidget(self.btn_voltage)
        mode_layout.addWidget(self.btn_trim)
        mode_layout.addWidget(self.btn_choose_save_folder)
        mode_layout.addStretch()
        mode_layout.addWidget(self.lbl_savepath)
        layout.addLayout(mode_layout)

        # Panel de graficos
        self.graph_panel = GraphPanel()
        layout.addWidget(self.graph_panel)

        # Trim toolbar (oculta por defecto)
        self.trim_toolbar = TrimToolbar()
        layout.addWidget(self.trim_toolbar)

        # Panel de ignicion
        self.ignition_panel = IgnitionPanel()
        layout.addWidget(self.ignition_panel)

        self._set_mode(ConnectionMode.LORA)

    def _connect_signals(self) -> None:
        """Conecta todas las senales de los widgets."""
        self.control_bar.connect_requested.connect(self._toggle_connection)
        self.control_bar.start_requested.connect(self._start_recording)
        self.control_bar.stop_requested.connect(self._stop_recording)
        self.control_bar.unit_toggled.connect(self._toggle_unit)
        self.control_bar.tare_requested.connect(self._tare)
        self.control_bar.clear_requested.connect(self._clear_data)
        self.control_bar.export_requested.connect(self._export_csv)
        self.control_bar.analysis_requested.connect(self._open_analysis)
        self.ignition_panel.fire_triggered.connect(self._fire)

        # Trim toolbar
        self.trim_toolbar.export_trim_requested.connect(self._export_trim_csv)
        self.trim_toolbar.cancel_trim_requested.connect(self._cancel_trim_mode)

        # Graph panel trim range
        self.graph_panel.trim_range_changed.connect(self._on_trim_range_changed)

    # ── Conexion ──────────────────────────────────────────────────────────────

    def _toggle_connection(self) -> None:
        """Alterna el estado de la conexion."""
        if self.comm_thread and self.comm_thread.isRunning():
            self.comm_thread.stop()
            self._on_disconnected(intentional=True)
        else:
            self._connect()

    def _connect(self) -> None:
        """Inicia la conexion de telemetria."""
        if self.conn_mode == ConnectionMode.WIFI:
            port_name = "UDP 8888"
            self.comm_thread = UdpReader(port=8888, mode=self.conn_mode)
        else:
            port_name = self.control_bar.get_selected_port()
            if not port_name or "No Ports" in port_name:
                logger.warning("No hay puertos disponibles para conectar.")
                return
            self.comm_thread = SerialReader(
                port=port_name, baudrate=DEFAULT_BAUDRATE, mode=self.conn_mode
            )

        try:
            self.comm_thread.data_received.connect(self._on_data)
            self.comm_thread.characterization_received.connect(self._on_characterization_data)
            self.comm_thread.disconnected.connect(
                lambda: self._on_disconnected(intentional=False)
            )
            self.comm_thread.start()
            self.header.set_connected(True)
            self.is_recording = False
            if self.conn_mode != ConnectionMode.CHARACTERIZATION:
                self._iniciar_autoguardado()
            logger.info("Conectado a %s.", port_name)
        except Exception as e:
            logger.error("Error al conectar con %s: %s", port_name, e)

    def _on_disconnected(self, intentional: bool = False) -> None:
        """Maneja la desconexion del dispositivo."""
        self.header.set_connected(False)
        self.is_recording = False
        if not intentional:
            self.reconnect_timer.start()
        logger.info("Desconectado. Intencional: %s", intentional)

    def _try_reconnect(self) -> None:
        self.reconnect_timer.stop()
        self._connect()

    def _auto_reconnect(self) -> None:
        self._connect()

    def _send_cmd(self, char: str) -> None:
        """Envia un comando al dispositivo serial."""
        if self.comm_thread and self.comm_thread.isRunning():
            self.comm_thread.send_command(char)
            logger.debug("Comando enviado: %s", char)

    def _on_characterization_data(
        self, weight_kg: float, voltage_mv: float, raw_count: int, sequence: int
    ) -> None:
        """Envía una muestra extendida a la ventana Volt/Kg."""
        if self.characterization_window is None:
            self._show_characterization_window()
        self.characterization_window.add_sample(weight_kg, voltage_mv, raw_count, sequence)

    def _show_characterization_window(self) -> None:
        if self.characterization_window is None:
            self.characterization_window = VoltageCharacterizationWindow(self)
            self.characterization_window.destroyed.connect(
                lambda: setattr(self, "characterization_window", None)
            )
        self.characterization_window.show()
        self.characterization_window.raise_()
        self.characterization_window.activateWindow()

    def _open_characterization(self) -> None:
        """Selecciona el protocolo de 16 bytes y abre sus graficas dedicadas."""
        if self.comm_thread and self.comm_thread.isRunning():
            QMessageBox.warning(
                self,
                "Desconecta primero",
                "Desconecta la telemetria actual antes de cambiar a Volt/Kg.",
            )
            return
        # En WiFi, UDP conserva el tamano del datagrama y reconoce los 16 bytes
        # automaticamente. En serie se requiere seleccionar este formato.
        if self.conn_mode != ConnectionMode.WIFI:
            self._set_mode(ConnectionMode.CHARACTERIZATION)
        self._show_characterization_window()

    # ── Grabacion ─────────────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        """Inicia la grabacion de datos."""
        self._clear_data()
        self.is_recording = True
        self.graph_panel.set_interaction(False)  # Bloquea zoom para forzar auto-scroll
        self.control_bar.set_recording_state(True)
        self._send_cmd("S")
        logger.info("Grabacion iniciada.")

    def _stop_recording(self) -> None:
        """Detiene la grabacion de datos."""
        self.is_recording = False
        self.graph_panel.set_interaction(True)   # Libera la grafica para poder explorar/recortar
        self.control_bar.set_recording_state(False)
        self._send_cmd("T")
        logger.info("Grabacion detenida.")

    # ── Autoguardado ──────────────────────────────────────────────────────────

    def _iniciar_autoguardado(self) -> None:
        """Configura e inicia el autoguardado de datos CSV."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        save_directory = self.settings.get(
            "autosave_directory",
            os.path.join(os.path.expanduser("~"), "Documents", "Horus Telemetria"),
        )
        filepath = os.path.join(save_directory, f"telemetria_{ts}.csv")
        self.auto_saver = AutoSaver(filepath)
        self.auto_saver.start()
        self.lbl_savepath.setText(f"Autoguardando: {filepath}")
        logger.info("Autoguardado iniciado en %s", filepath)

    def _choose_save_folder(self) -> None:
        """Permite elegir y recordar la carpeta para los CSV de autoguardado."""
        current_directory = self.settings.get(
            "autosave_directory", os.path.join(os.path.expanduser("~"), "Documents")
        )
        directory = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para CSV automaticos", current_directory
        )
        if not directory:
            return

        self.settings.set("autosave_directory", directory)
        self.lbl_savepath.setText(f"CSV automaticos: {directory}")
        logger.info("Carpeta de autoguardado actualizada a %s", directory)

    # ── Datos ────────────────────────────────────────────────────────────────

    def _on_data(self, newtons: float, seq: int, rssi: int) -> None:
        """Procesa un nuevo registro de datos entrantes."""
        if not getattr(self, "is_recording", False):
            return
        reading = self.engine.process_reading(newtons, seq, rssi)
        if self.auto_saver:
            self.auto_saver.add_row(reading.timestamp, reading.thrust_n, reading.impulse_ns)
        self._refresh_display(reading)

    def _refresh_display(self, reading: Any) -> None:
        """Actualiza KPIs y graficas."""
        if self._trim_active:
            # Si estamos en modo recorte, evitamos sobrescribir los KPIs,
            # pero igual actualizamos las series en las graficas.
            pass
        else:
            stats = self.engine.get_stats()
            thrust = reading.thrust_kg if self.engine.is_kg else reading.thrust_n
            max_thrust = stats.max_thrust_kg if self.engine.is_kg else stats.max_thrust_n
            impulse = reading.impulse_kgs if self.engine.is_kg else reading.impulse_ns

            self.kpi_thrust.set_value(thrust)
            self.kpi_max.set_value(max_thrust)
            self.kpi_impulse.set_value(impulse)
            self.kpi_class.set_value(
                f"{reading.classification.letter} ({reading.classification.percentage:.0f}%)"
            )
            if reading.rssi != -999:
                self.kpi_rssi.set_value(float(reading.rssi))

        thrust_series = [t * self.engine.unit_factor for t in self.engine.thrust_series]
        impulse_series = [i * self.engine.unit_factor for i in self.engine.impulse_series]
        self.graph_panel.update_thrust(self.engine.time_series, thrust_series)
        self.graph_panel.update_impulse(self.engine.time_series, impulse_series)

    def _on_trim_range_changed(self, t_start: float, t_end: float) -> None:
        """Se llama cuando el usuario mueve las barras de recorte."""
        self.trim_toolbar.update_range(t_start, t_end)

        # Calcular estadisticas exclusivas de este rango
        trim_stats = self.engine.get_trim_stats(t_start, t_end)
        
        max_thrust = trim_stats.max_thrust_kg if self.engine.is_kg else trim_stats.max_thrust_n
        impulse = trim_stats.total_impulse_kgs if self.engine.is_kg else trim_stats.total_impulse_ns
        
        # Actualizar KPIs temporalmente para el rango
        self.kpi_max.set_value(max_thrust)
        self.kpi_impulse.set_value(impulse)
        self.kpi_class.set_value(
            f"{trim_stats.classification.letter} ({trim_stats.classification.percentage:.0f}%)"
        )
        self.kpi_thrust.set_value(0.0) # Empuje instantaneo no tiene sentido en recorte

    # ── Controles ────────────────────────────────────────────────────────────

    def _tare(self) -> None:
        """Establece la tara usando las lecturas recientes del motor."""
        self.engine.tare()

    def _toggle_unit(self) -> None:
        self.engine.toggle_unit()
        self.control_bar.update_unit_label(self.engine.is_kg)
        self.graph_panel.set_y_labels(self.engine.is_kg)
        force_unit = "kg" if self.engine.is_kg else "N"
        impulse_unit = "kg*s" if self.engine.is_kg else "N*s"
        self.kpi_thrust.lbl_unit.setText(force_unit)
        self.kpi_max.lbl_unit.setText(force_unit)
        self.kpi_impulse.lbl_unit.setText(impulse_unit)
        self._refresh_display_from_engine()
        logger.info("Unidades cambiadas. Sistema actual en kg: %s", self.engine.is_kg)

    def _refresh_display_from_engine(self) -> None:
        """Redibuja series y KPIs existentes de forma segura tras cambiar unidad."""
        if not self.engine.time_series:
            return

        stats = self.engine.get_stats()
        factor = self.engine.unit_factor
        self.kpi_thrust.set_value(self.engine.thrust_series[-1] * factor)
        self.kpi_max.set_value(stats.max_thrust_n * factor)
        self.kpi_impulse.set_value(stats.total_impulse_ns * factor)
        self.kpi_class.set_value(
            f"{stats.classification.letter} ({stats.classification.percentage:.0f}%)"
        )
        self.graph_panel.update_thrust(
            self.engine.time_series, [value * factor for value in self.engine.thrust_series]
        )
        self.graph_panel.update_impulse(
            self.engine.time_series, [value * factor for value in self.engine.impulse_series]
        )

    def _clear_data(self) -> None:
        """Limpia datos, graficas y KPIs."""
        self.engine.clear()
        self.graph_panel.clear()
        for kpi in [self.kpi_thrust, self.kpi_max, self.kpi_impulse,
                    self.kpi_class, self.kpi_rssi, self.kpi_lost_pkts]:
            kpi.reset()

    def _set_mode(self, mode: ConnectionMode) -> None:
        """Cambia el modo de conexion."""
        self.conn_mode = mode
        is_lora = mode == ConnectionMode.LORA

        self.kpi_rssi.setVisible(is_lora)
        if hasattr(self.control_bar, "set_wifi_mode"):
            self.control_bar.set_wifi_mode(mode == ConnectionMode.WIFI)

        if self.ignition_panel.is_armed:
            self.ignition_panel.disarm()

    def _fire(self) -> None:
        """Envia FIRE solo despues de aprobar el codigo temporal del panel."""
        self._send_cmd("F")
        self._send_cmd("S")

    # ── Feature 1: Exportacion inteligente ──────────────────────────────────

    def _export_csv(self) -> None:
        """
        Exporta los datos de la sesion.

        Si hay un CSV autoguardado activo, muestra un dialogo de confirmacion.
        Si no hay sesion activa, abre un QFileDialog directamente.
        """
        if not self.engine.time_series:
            QMessageBox.information(self, "Sin datos", "No hay datos de telemetria para exportar.")
            return

        if self.auto_saver is not None:
            # Hay CSV autoguardado: mostrar dialogo de confirmacion
            dialog = ExportConfirmDialog(
                autosave_filepath=self.auto_saver.filepath,
                time_data=list(self.engine.time_series),
                thrust_data=list(self.engine.thrust_series),
                parent=self,
            )
            dialog.exec()
            if dialog.result_path:
                self.lbl_savepath.setText(f"Exportado: {dialog.result_path}")
        else:
            # Sin sesion activa: QFileDialog normal
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar CSV", "", "CSV (*.csv)"
            )
            if path:
                try:
                    export_telemetry_csv(
                        path,
                        list(self.engine.time_series),
                        list(self.engine.thrust_series),
                    )
                    logger.info("Datos exportados a %s", path)
                except Exception as e:
                    logger.error("Error exportando CSV: %s", e)

    def _open_analysis(self) -> None:
        """Abre la ventana de analisis para explorar archivos CSV guardados."""
        if self.analysis_window is None:
            self.analysis_window = CsvAnalysisWindow(self)
            self.analysis_window.destroyed.connect(lambda: setattr(self, "analysis_window", None))
        self.analysis_window.show()
        self.analysis_window.raise_()
        self.analysis_window.activateWindow()

    # ── Feature 2: Recorte de grafica ────────────────────────────────────────

    def _toggle_trim_mode(self) -> None:
        """Activa o desactiva el modo recorte de la grafica."""
        if self._trim_active:
            self._cancel_trim_mode()
        else:
            self._activate_trim_mode()

    def _activate_trim_mode(self) -> None:
        """Activa el modo recorte."""
        if not self.engine.time_series:
            QMessageBox.information(
                self, "Sin datos", "Captura datos primero para poder recortar."
            )
            return
        self._trim_active = True
        t_min = self.engine.time_series[0]
        t_max = self.engine.time_series[-1]
        self.graph_panel.enable_trim_mode(t_min, t_max)
        self.trim_toolbar.show()
        self.btn_trim.setText("\u2702 RECORTANDO...")
        self.btn_trim.setStyleSheet(
            "background:#3d2a10;color:#d4a843;border:2px solid #d4a843;"
        )
        logger.info("Modo recorte activado.")

    def _cancel_trim_mode(self) -> None:
        """Cancela el modo recorte sin exportar."""
        self._trim_active = False
        self.graph_panel.disable_trim_mode()
        self.trim_toolbar.hide()
        self.btn_trim.setText("\u2702 RECORTAR")
        self.btn_trim.setStyleSheet(
            "background:#2e2118;color:#d4a843;border-color:#d4a84344;"
        )
        # Restaurar KPIs a las estadisticas completas de la sesion
        stats = self.engine.get_stats()
        max_thrust = stats.max_thrust_kg if self.engine.is_kg else stats.max_thrust_n
        impulse = stats.total_impulse_kgs if self.engine.is_kg else stats.total_impulse_ns
        self.kpi_max.set_value(max_thrust)
        self.kpi_impulse.set_value(impulse)
        self.kpi_class.set_value(f"{stats.classification.letter} ({stats.classification.percentage:.0f}%)")
        
        logger.info("Modo recorte cancelado.")

    def _export_trim_csv(self) -> None:
        """Exporta el rango recortado a un nuevo archivo CSV."""
        t_start, t_end = self.graph_panel.get_trim_range()
        if t_start >= t_end:
            QMessageBox.warning(
                self, "Rango invalido",
                "El rango de recorte no es valido. Asegurate de que inicio < fin."
            )
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        default_name = os.path.join(
            os.path.expanduser("~"),
            f"recorte_{ts}.csv",
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Exportar recorte [{t_start:.2f}s \u2192 {t_end:.2f}s]",
            default_name,
            "CSV (*.csv)",
        )
        if not path:
            return

        try:
            rows = export_trim_csv(
                path,
                list(self.engine.time_series),
                list(self.engine.thrust_series),
                t_start,
                t_end,
            )
            QMessageBox.information(
                self,
                "Recorte exportado",
                f"Se exportaron {rows} filas al archivo:\n{path}",
            )
            self._cancel_trim_mode()
        except Exception as e:
            logger.error("Error exportando recorte: %s", e)
            QMessageBox.critical(self, "Error", f"No se pudo exportar el recorte:\n{e}")
