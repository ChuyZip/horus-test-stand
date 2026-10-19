"""Ventana de caracterizacion de la celda: peso, senal y cuentas HX711.

Incluye funcionalidades de:
- Captura en tiempo real de muestras de caracterizacion.
- Exportar CSV con los datos de la sesion.
- Cargar y analizar un CSV de caracterizacion previo.
- Recortar las graficas para exportar solo el rango de interes.
"""
from __future__ import annotations

import csv
import os
import time

import pyqtgraph as pg
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

from config.styles import MAIN_STYLESHEET
from ui.widgets.kpi_card import KpiCard


class VoltageCharacterizationWindow(QMainWindow):
    """Grafica la respuesta electrica de la celda mientras se aplican masas conocidas."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Horus Space Lab — Caracterizacion Volt/Kg")
        self.resize(1220, 820)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._start_time: float | None = None
        self._time_data: list[float] = []
        self._weight_data: list[float] = []
        self._voltage_data: list[float] = []
        self._raw_data: list[int] = []
        self._sequence_data: list[int] = []

        self._trim_active: bool = False
        self._trim_region: pg.LinearRegionItem | None = None

        self._build_ui()

    # ── Construccion de la interfaz ───────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ── Toolbar principal ────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        self.status = QLabel("Esperando paquete de caracterizacion de 16 bytes")
        self.status.setStyleSheet("color:#40c4aa;")

        btn_clear = QPushButton("⌫ LIMPIAR")
        btn_clear.clicked.connect(self.clear)

        btn_export = QPushButton("↓ CSV")
        btn_export.clicked.connect(self._export_csv)

        self.btn_analyze = QPushButton("📊 ANALIZAR")
        self.btn_analyze.setStyleSheet(
            "background:#2e2510;color:#40c4aa;border-color:#40c4aa44;"
        )
        self.btn_analyze.clicked.connect(self._load_csv_for_analysis)

        self.btn_trim = QPushButton("✂ RECORTAR")
        self.btn_trim.setStyleSheet(
            "background:#2e2118;color:#d4a843;border-color:#d4a84344;"
        )
        self.btn_trim.clicked.connect(self._toggle_trim_mode)

        toolbar.addWidget(self.status, 1)
        toolbar.addWidget(btn_clear)
        toolbar.addWidget(btn_export)
        toolbar.addWidget(self.btn_analyze)
        toolbar.addWidget(self.btn_trim)
        layout.addLayout(toolbar)

        # ── Trim toolbar (oculta por defecto) ────────────────────────────────
        self.trim_bar = QWidget()
        self.trim_bar.hide()
        trim_layout = QHBoxLayout(self.trim_bar)
        trim_layout.setContentsMargins(4, 4, 4, 4)

        lbl_trim = QLabel("✂  MODO RECORTE")
        lbl_trim.setStyleSheet(
            "color:#d4a843;font-size:10px;font-weight:bold;letter-spacing:2px;"
        )
        self.lbl_trim_range = QLabel("Arrastra las lineas para seleccionar el rango...")
        self.lbl_trim_range.setStyleSheet(
            "color:#40c4aa;font-size:11px;"
            "background:#261c13;padding:4px 10px;border-radius:4px;"
        )
        btn_trim_export = QPushButton("💾  Exportar recorte")
        btn_trim_export.setStyleSheet(
            "background:#1e2e16;color:#6dbf4a;border-color:#6dbf4a44;padding:6px 14px;"
        )
        btn_trim_export.clicked.connect(self._export_trim_csv)

        btn_trim_cancel = QPushButton("✕  Cancelar")
        btn_trim_cancel.setStyleSheet(
            "background:#2e1614;color:#c4342d;border-color:#c4342d44;padding:6px 14px;"
        )
        btn_trim_cancel.clicked.connect(self._cancel_trim_mode)

        trim_layout.addWidget(lbl_trim)
        trim_layout.addWidget(self.lbl_trim_range, 1)
        trim_layout.addWidget(btn_trim_export)
        trim_layout.addWidget(btn_trim_cancel)
        layout.addWidget(self.trim_bar)

        # ── KPIs ─────────────────────────────────────────────────────────────
        kpis = QHBoxLayout()
        self.kpi_voltage = KpiCard(
            "SENAL", "mV", "#40c4aa",
            "Senal calculada desde la lectura cruda del HX711.",
        )
        self.kpi_weight = KpiCard(
            "PESO", "kg", "#6dbf4a",
            "Peso reportado por el factor de calibracion activo en el microcontrolador.",
        )
        self.kpi_raw = KpiCard(
            "CRUDO", "cts", "#e8922f",
            "Cuentas ADC crudas leidas directamente desde el HX711.",
        )
        self.kpi_max_weight = KpiCard(
            "MAX PESO", "kg", "#6dbf4a",
            "Peso maximo registrado en la sesion o rango.",
        )
        self.kpi_max_voltage = KpiCard(
            "MAX SENAL", "mV", "#40c4aa",
            "Senal maxima registrada en la sesion o rango.",
        )
        self.kpi_samples = KpiCard(
            "MUESTRAS", "", "#b8a890",
            "Cantidad de puntos de datos capturados.",
        )
        for kpi in (
            self.kpi_voltage, self.kpi_weight, self.kpi_raw,
            self.kpi_max_weight, self.kpi_max_voltage, self.kpi_samples,
        ):
            kpis.addWidget(kpi)
        layout.addLayout(kpis)

        # ── Graficas ─────────────────────────────────────────────────────────
        self.graph_voltage = self._make_graph(
            "Voltaje vs tiempo", "Tiempo", "s", "Senal", "mV", "#40c4aa",
        )
        self.graph_weight = self._make_graph(
            "Peso vs tiempo", "Tiempo", "s", "Peso", "kg", "#6dbf4a",
        )
        self.graph_response = self._make_graph(
            "Respuesta de la celda", "Peso", "kg", "Senal", "mV", "#e8922f",
        )
        self.curve_voltage = self.graph_voltage.plot(pen=pg.mkPen("#40c4aa", width=2))
        self.curve_weight = self.graph_weight.plot(pen=pg.mkPen("#6dbf4a", width=2))
        self.curve_response = self.graph_response.plot(
            pen=pg.mkPen("#e8922f", width=1),
            symbol="o",
            symbolSize=5,
            symbolBrush="#e8922f",
        )
        layout.addWidget(self.graph_voltage, 1)
        layout.addWidget(self.graph_weight, 1)
        layout.addWidget(self.graph_response, 1)

    @staticmethod
    def _make_graph(
        title: str, x_label: str, x_units: str,
        y_label: str, y_units: str, color: str,
    ) -> pg.PlotWidget:
        graph = pg.PlotWidget(title=title)
        graph.setBackground("#1a120b")
        graph.showGrid(x=True, y=True, alpha=0.2)
        graph.setLabel("bottom", x_label, units=x_units, color="#c8b8a0")
        graph.setLabel("left", y_label, units=y_units, color=color)
        graph.getPlotItem().getAxis("bottom").setTextPen("#c8b8a0")
        graph.getPlotItem().getAxis("left").setTextPen(color)
        return graph

    # ── Captura en tiempo real ────────────────────────────────────────────────

    def add_sample(
        self, weight_kg: float, voltage_mv: float, raw_count: int, sequence: int,
    ) -> None:
        """Agrega una muestra recibida desde el paquete de caracterizacion."""
        now = time.monotonic()
        if self._start_time is None:
            self._start_time = now
        elapsed = now - self._start_time
        self._time_data.append(elapsed)
        self._weight_data.append(weight_kg)
        self._voltage_data.append(voltage_mv)
        self._raw_data.append(raw_count)
        self._sequence_data.append(sequence)

        self.kpi_voltage.set_value(voltage_mv, decimals=4)
        self.kpi_weight.set_value(weight_kg, decimals=4)
        self.kpi_raw.set_value(raw_count, decimals=0)
        self.status.setText(f"Recibiendo muestras — secuencia {sequence}")

        # Actualizar KPIs de maximos y muestras
        if not self._trim_active:
            self._update_stats_kpis()

        self.curve_voltage.setData(self._time_data, self._voltage_data)
        self.curve_weight.setData(self._time_data, self._weight_data)
        self.curve_response.setData(self._weight_data, self._voltage_data)

    def _update_stats_kpis(
        self,
        weight: list[float] | None = None,
        voltage: list[float] | None = None,
    ) -> None:
        """Actualiza los KPIs de estadisticas (max, muestras)."""
        w = weight if weight is not None else self._weight_data
        v = voltage if voltage is not None else self._voltage_data
        if w:
            self.kpi_max_weight.set_value(max(w), decimals=4)
        if v:
            self.kpi_max_voltage.set_value(max(v), decimals=4)
        self.kpi_samples.set_value(len(w), decimals=0)

    # ── Limpiar ───────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Reinicia la captura y las tres graficas de caracterizacion."""
        if self._trim_active:
            self._cancel_trim_mode()
        self._start_time = None
        self._time_data.clear()
        self._weight_data.clear()
        self._voltage_data.clear()
        self._raw_data.clear()
        self._sequence_data.clear()
        self.curve_voltage.clear()
        self.curve_weight.clear()
        self.curve_response.clear()
        for kpi in (
            self.kpi_voltage, self.kpi_weight, self.kpi_raw,
            self.kpi_max_weight, self.kpi_max_voltage, self.kpi_samples,
        ):
            kpi.reset()
        self.status.setText(
            "Captura limpia. Esperando paquete de caracterizacion de 16 bytes"
        )

    # ── Exportar CSV ──────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._time_data:
            QMessageBox.information(
                self, "Sin datos",
                "No hay muestras de caracterizacion para exportar.",
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar caracterizacion", "", "CSV (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        self._write_csv(
            path, self._time_data, self._weight_data,
            self._voltage_data, self._raw_data, self._sequence_data,
        )
        self.status.setText(f"Caracterizacion exportada: {path}")

    @staticmethod
    def _write_csv(
        path: str,
        time_d: list, weight_d: list, voltage_d: list,
        raw_d: list, seq_d: list,
    ) -> int:
        """Escribe los datos de caracterizacion en un CSV. Devuelve filas escritas."""
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Tiempo (s)", "Peso (kg)", "Voltaje (mV)",
                "Crudo (cts)", "Secuencia",
            ])
            rows = list(zip(time_d, weight_d, voltage_d, raw_d, seq_d))
            writer.writerows(rows)
        return len(rows)

    # ── Analizar CSV ──────────────────────────────────────────────────────────

    def _load_csv_for_analysis(self) -> None:
        """Carga un CSV de caracterizacion previo y lo grafica."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir CSV de caracterizacion", "", "CSV (*.csv)",
        )
        if not path:
            return

        try:
            time_d, weight_d, voltage_d, raw_d, seq_d = self._read_characterization_csv(path)
        except Exception as e:
            QMessageBox.critical(
                self, "Error al leer CSV",
                f"No se pudo cargar el archivo:\n{e}",
            )
            return

        # Reemplazar datos internos con los del archivo
        self.clear()
        self._time_data = time_d
        self._weight_data = weight_d
        self._voltage_data = voltage_d
        self._raw_data = raw_d
        self._sequence_data = seq_d

        # Graficar
        self.curve_voltage.setData(self._time_data, self._voltage_data)
        self.curve_weight.setData(self._time_data, self._weight_data)
        self.curve_response.setData(self._weight_data, self._voltage_data)

        # Actualizar KPIs
        if self._weight_data:
            self.kpi_weight.set_value(self._weight_data[-1], decimals=4)
        if self._voltage_data:
            self.kpi_voltage.set_value(self._voltage_data[-1], decimals=4)
        if self._raw_data:
            self.kpi_raw.set_value(self._raw_data[-1], decimals=0)
        self._update_stats_kpis()

        self.status.setText(
            f"CSV cargado: {os.path.basename(path)} "
            f"({len(self._time_data)} muestras)"
        )

        # Auto-rango
        self.graph_voltage.enableAutoRange()
        self.graph_weight.enableAutoRange()
        self.graph_response.enableAutoRange()

    @staticmethod
    def _read_characterization_csv(
        path: str,
    ) -> tuple[list[float], list[float], list[float], list[int], list[int]]:
        """Lee un CSV de caracterizacion y devuelve las columnas como listas."""
        time_d: list[float] = []
        weight_d: list[float] = []
        voltage_d: list[float] = []
        raw_d: list[int] = []
        seq_d: list[int] = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                raise ValueError("El archivo CSV esta vacio.")

            # Buscar columnas por nombre (flexibilidad)
            header_lower = [h.strip().lower() for h in header]
            col_map = {}
            for i, h in enumerate(header_lower):
                if "tiempo" in h or "time" in h:
                    col_map["time"] = i
                elif "peso" in h or "weight" in h or "kg" in h:
                    col_map["weight"] = i
                elif "volt" in h or "senal" in h or "mv" in h:
                    col_map["voltage"] = i
                elif "crudo" in h or "raw" in h or "cts" in h:
                    col_map["raw"] = i
                elif "sec" in h or "seq" in h:
                    col_map["seq"] = i

            if "time" not in col_map or "weight" not in col_map:
                raise ValueError(
                    "El CSV no tiene las columnas requeridas "
                    "(Tiempo, Peso como minimo)."
                )

            for row in reader:
                if not row:
                    continue
                try:
                    time_d.append(float(row[col_map["time"]]))
                    weight_d.append(float(row[col_map["weight"]]))
                    voltage_d.append(
                        float(row[col_map["voltage"]]) if "voltage" in col_map else 0.0
                    )
                    raw_d.append(
                        int(float(row[col_map["raw"]])) if "raw" in col_map else 0
                    )
                    seq_d.append(
                        int(float(row[col_map["seq"]])) if "seq" in col_map else 0
                    )
                except (ValueError, IndexError):
                    continue

        return time_d, weight_d, voltage_d, raw_d, seq_d

    # ── Recortar grafica ──────────────────────────────────────────────────────

    def _toggle_trim_mode(self) -> None:
        """Activa o desactiva el modo de recorte."""
        if self._trim_active:
            self._cancel_trim_mode()
        else:
            self._activate_trim_mode()

    def _activate_trim_mode(self) -> None:
        """Muestra las barras de recorte en la grafica de voltaje."""
        if not self._time_data:
            QMessageBox.information(
                self, "Sin datos",
                "Captura o carga datos primero para poder recortar.",
            )
            return

        self._trim_active = True
        t_min = self._time_data[0]
        t_max = self._time_data[-1]
        margin = (t_max - t_min) * 0.1

        self._trim_region = pg.LinearRegionItem(
            values=(t_min + margin, t_max - margin),
            brush=pg.mkBrush(255, 170, 0, 30),
        )
        self._trim_region.sigRegionChanged.connect(self._on_trim_changed)
        self.graph_voltage.addItem(self._trim_region)

        self.trim_bar.show()
        self.btn_trim.setText("✂ RECORTANDO...")
        self.btn_trim.setStyleSheet(
            "background:#3d2a10;color:#d4a843;border:2px solid #d4a843;"
        )
        self._on_trim_changed()

    def _cancel_trim_mode(self) -> None:
        """Desactiva el modo de recorte y restaura estadisticas globales."""
        self._trim_active = False
        if self._trim_region is not None:
            self.graph_voltage.removeItem(self._trim_region)
            self._trim_region = None
        self.trim_bar.hide()
        self.btn_trim.setText("✂ RECORTAR")
        self.btn_trim.setStyleSheet(
            "background:#2e2118;color:#d4a843;border-color:#d4a84344;"
        )
        # Restaurar KPIs globales
        self._update_stats_kpis()

    def _on_trim_changed(self) -> None:
        """Se llama cuando el usuario mueve las barras de recorte."""
        if self._trim_region is None:
            return
        t_start, t_end = self._trim_region.getRegion()
        duration = max(0.0, t_end - t_start)
        self.lbl_trim_range.setText(
            f"Recorte:  {t_start:.2f}s  →  {t_end:.2f}s  "
            f"({duration:.2f}s de duracion)"
        )

        # Calcular KPIs solo del rango seleccionado
        trimmed_w = []
        trimmed_v = []
        for i, t in enumerate(self._time_data):
            if t_start <= t <= t_end:
                trimmed_w.append(self._weight_data[i])
                trimmed_v.append(self._voltage_data[i])

        self._update_stats_kpis(weight=trimmed_w, voltage=trimmed_v)

    def _export_trim_csv(self) -> None:
        """Exporta solo el rango recortado a un nuevo CSV."""
        if self._trim_region is None:
            return
        t_start, t_end = self._trim_region.getRegion()
        if t_start >= t_end:
            QMessageBox.warning(
                self, "Rango invalido",
                "El rango de recorte no es valido.",
            )
            return

        # Filtrar datos por rango
        trim_t, trim_w, trim_v, trim_r, trim_s = [], [], [], [], []
        for i, t in enumerate(self._time_data):
            if t_start <= t <= t_end:
                trim_t.append(t - t_start)  # Tiempo relativo al inicio del recorte
                trim_w.append(self._weight_data[i])
                trim_v.append(self._voltage_data[i])
                trim_r.append(self._raw_data[i])
                trim_s.append(self._sequence_data[i])

        if not trim_t:
            QMessageBox.information(
                self, "Sin datos",
                "No hay muestras dentro del rango seleccionado.",
            )
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        default_name = os.path.join(
            os.path.expanduser("~"), f"recorte_voltkg_{ts}.csv",
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Exportar recorte [{t_start:.2f}s → {t_end:.2f}s]",
            default_name,
            "CSV (*.csv)",
        )
        if not path:
            return

        rows = self._write_csv(path, trim_t, trim_w, trim_v, trim_r, trim_s)
        QMessageBox.information(
            self, "Recorte exportado",
            f"Se exportaron {rows} filas al archivo:\n{path}",
        )
        self._cancel_trim_mode()
