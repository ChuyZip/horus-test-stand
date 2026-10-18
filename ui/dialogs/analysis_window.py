"""Ventana para analizar ensayos de telemetria guardados en CSV."""

import os

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.constants import GRAVITY
from config.styles import MAIN_STYLESHEET
from persistence.csv_loader import CsvTelemetryData, load_telemetry_csv
from ui.widgets.graph_panel import GraphPanel
from ui.widgets.kpi_card import KpiCard


class CsvAnalysisWindow(QMainWindow):
    """Muestra y resume la telemetria contenida en un archivo CSV."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Horus Space Lab - Analisis de telemetria")
        self.resize(1180, 720)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._data_a: CsvTelemetryData | None = None
        self._data_b: CsvTelemetryData | None = None
        self._is_kg = False
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        toolbar = QHBoxLayout()
        self.btn_open_a = QPushButton("CARGAR ENSAYO A")
        self.btn_open_a.setStyleSheet("background:#2e2510;color:#40c4aa;border-color:#40c4aa44;")
        self.btn_open_a.clicked.connect(lambda: self._select_csv("A"))
        self.btn_open_b = QPushButton("CARGAR ENSAYO B")
        self.btn_open_b.setStyleSheet("background:#3d2a10;color:#e8922f;border-color:#e8922f44;")
        self.btn_open_b.clicked.connect(lambda: self._select_csv("B"))
        self.btn_unit = QPushButton("UNIDAD: N")
        self.btn_unit.setStyleSheet("background:#2e2118;color:#40c4aa;border-color:#40c4aa44;")
        self.btn_unit.clicked.connect(self._toggle_unit)
        self.lbl_file_a = QLabel("ENSAYO A: sin archivo")
        self.lbl_file_a.setStyleSheet("color:#40c4aa;font-size:11px;")
        self.lbl_file_b = QLabel("ENSAYO B: sin archivo")
        self.lbl_file_b.setStyleSheet("color:#e8922f;font-size:11px;")
        self.lbl_file_a.setWordWrap(True)
        self.lbl_file_b.setWordWrap(True)

        toolbar.addWidget(self.btn_open_a)
        toolbar.addWidget(self.btn_open_b)
        toolbar.addWidget(self.btn_unit)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.lbl_file_a, 1)
        toolbar.addWidget(self.lbl_file_b, 1)
        layout.addLayout(toolbar)

        kpis = QHBoxLayout()
        self.kpi_max_a = KpiCard(
            "MAX A", "N", "#40c4aa", "Empuje maximo del ensayo A, usado como referencia."
        )
        self.kpi_max_b = KpiCard(
            "MAX B", "N", "#e8922f", "Empuje maximo del ensayo B, el candidato a comparar."
        )
        self.kpi_max_change = KpiCard(
            "CAMBIO MAX", "%", "#ffffff", "Variacion porcentual del empuje maximo de B respecto a A."
        )
        self.kpi_impulse_a = KpiCard(
            "IMPULSO A", "Ns", "#6dbf4a", "Impulso total acumulado del ensayo A."
        )
        self.kpi_impulse_b = KpiCard(
            "IMPULSO B", "Ns", "#c4342d", "Impulso total acumulado del ensayo B."
        )
        self.kpi_impulse_change = KpiCard(
            "CAMBIO IMP", "%", "#ffffff", "Variacion porcentual del impulso total de B respecto a A."
        )
        for kpi in [
            self.kpi_max_a,
            self.kpi_max_b,
            self.kpi_max_change,
            self.kpi_impulse_a,
            self.kpi_impulse_b,
            self.kpi_impulse_change,
        ]:
            kpis.addWidget(kpi)
        layout.addLayout(kpis)

        self.graph_panel = GraphPanel()
        self.graph_panel.show_legends()
        layout.addWidget(self.graph_panel, 1)

    def _select_csv(self, slot: str) -> None:
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir telemetria", "", "CSV (*.csv)")
        if filepath:
            self.load_file(filepath, slot)

    def load_file(self, filepath: str, slot: str = "A") -> None:
        """Carga un CSV en el ensayo A o B y actualiza la comparacion."""
        try:
            data = load_telemetry_csv(filepath)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "No se pudo abrir el CSV", str(error))
            return

        if slot == "B":
            self._data_b = data
            self.lbl_file_b.setText(f"ENSAYO B: {os.path.basename(filepath)}")
        else:
            self._data_a = data
            self.lbl_file_a.setText(f"ENSAYO A: {os.path.basename(filepath)}")
        self._refresh_analysis()

    def _toggle_unit(self) -> None:
        self._is_kg = not self._is_kg
        self.btn_unit.setText("UNIDAD: kg" if self._is_kg else "UNIDAD: N")
        self.graph_panel.set_y_labels(self._is_kg)
        if self._data_a:
            self._refresh_analysis()

    def _refresh_analysis(self) -> None:
        if self._data_a is None:
            return

        factor = 1.0 / GRAVITY if self._is_kg else 1.0
        max_a = max(self._data_a.thrust_n)
        impulse_a = self._data_a.impulse_ns[-1]
        self.kpi_max_a.set_value(max_a * factor)
        self.kpi_impulse_a.set_value(impulse_a * factor)

        if self._data_b:
            max_b = max(self._data_b.thrust_n)
            impulse_b = self._data_b.impulse_ns[-1]
            self.kpi_max_b.set_value(max_b * factor)
            self.kpi_impulse_b.set_value(impulse_b * factor)
            self.kpi_max_change.set_value(_percent_change(max_a, max_b))
            self.kpi_impulse_change.set_value(_percent_change(impulse_a, impulse_b))
        else:
            self.kpi_max_b.reset()
            self.kpi_impulse_b.reset()
            self.kpi_max_change.reset()
            self.kpi_impulse_change.reset()

        unit = "kg" if self._is_kg else "N"
        impulse_unit = "kg*s" if self._is_kg else "N*s"
        for kpi in [self.kpi_max_a, self.kpi_max_b]:
            kpi.lbl_unit.setText(unit)
        for kpi in [self.kpi_impulse_a, self.kpi_impulse_b]:
            kpi.lbl_unit.setText(impulse_unit)

        self.graph_panel.update_comparison(
            self._data_a.time_data,
            [value * factor for value in self._data_a.thrust_n],
            [value * factor for value in self._data_a.impulse_ns],
            self._data_b.time_data if self._data_b else None,
            [value * factor for value in self._data_b.thrust_n] if self._data_b else None,
            [value * factor for value in self._data_b.impulse_ns] if self._data_b else None,
        )
        self.graph_panel.graph_thrust.enableAutoRange()
        self.graph_panel.graph_impulse.enableAutoRange()


def _percent_change(reference: float, candidate: float) -> str:
    """Devuelve la mejora porcentual del ensayo B frente al ensayo A."""
    if reference == 0.0:
        return "—"
    return f"{(candidate - reference) / reference * 100.0:+.1f}"
