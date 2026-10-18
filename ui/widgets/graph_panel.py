"""
Widget de paneles de graficos con soporte de modo recorte.
"""
import logging
from bisect import bisect_left
from math import hypot
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
import pyqtgraph as pg

logger = logging.getLogger(__name__)


class GraphPanel(QWidget):
    """
    Panel de visualizacion de graficos de empuje e impulso en tiempo real.
    Incluye soporte para modo recorte mediante LinearRegionItem de pyqtgraph.
    """

    trim_range_changed = pyqtSignal(float, float)

    def __init__(self, parent=None) -> None:
        """Inicializa los graficos."""
        super().__init__(parent)
        self._trim_region: pg.LinearRegionItem | None = None
        self._thrust_series: list[tuple[str, list[float], list[float]]] = []
        self._impulse_series: list[tuple[str, list[float], list[float]]] = []
        self._thrust_unit = "N"
        self._impulse_unit = "N*s"
        self._hover_proxies: list[pg.SignalProxy] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Construye los graficos usando pyqtgraph."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        gr = QHBoxLayout()
        gr.setContentsMargins(0, 0, 0, 0)

        self.graph_thrust = pg.PlotWidget()
        self.graph_impulse = pg.PlotWidget()

        self._style_graph(self.graph_thrust, "Tiempo (s)", "Empuje (N)", "#40c4aa")
        self._style_graph(self.graph_impulse, "Tiempo (s)", "Impulso (N\u00b7s)", "#6dbf4a")

        self.curve_thrust = self.graph_thrust.plot(name="Ensayo A", pen=pg.mkPen("#40c4aa", width=2))
        self.curve_impulse = self.graph_impulse.plot(name="Ensayo A", pen=pg.mkPen("#6dbf4a", width=2))
        self.curve_thrust_b = self.graph_thrust.plot(name="Ensayo B", pen=pg.mkPen("#e8922f", width=2))
        self.curve_impulse_b = self.graph_impulse.plot(name="Ensayo B", pen=pg.mkPen("#d4567a", width=2))

        self._hover_overlays: dict[str, tuple[pg.InfiniteLine, pg.InfiniteLine, pg.TextItem]] = {}
        self._install_hover_feedback(self.graph_thrust, "thrust")
        self._install_hover_feedback(self.graph_impulse, "impulse")

        gr.addWidget(self.graph_thrust, 3)
        gr.addWidget(self.graph_impulse, 2)
        outer.addLayout(gr)

    def _style_graph(self, gw: pg.PlotWidget, xlabel: str, ylabel: str, color: str) -> None:
        """Aplica estilo visual al widget del grafico."""
        gw.setBackground("#1a120b")
        gw.showGrid(x=True, y=True, alpha=0.12)
        gw.setLabel("left", ylabel, color=color)
        gw.setLabel("bottom", xlabel, color="#8a7a6a")

    def show_legends(self) -> None:
        """Muestra las leyendas en las graficas (solo para analisis)."""
        if not getattr(self, "_legends_shown", False):
            self.graph_thrust.addLegend(offset=(10, 10))
            self.graph_impulse.addLegend(offset=(10, 10))
            self._legends_shown = True

    def update_thrust(self, time_data: list[float], thrust_data: list[float]) -> None:
        """Actualiza el grafico de empuje con nuevos datos."""
        self.curve_thrust.setData(time_data, thrust_data)
        self._thrust_series = [("Ensayo", time_data, thrust_data)]

    def set_y_labels(self, is_kg: bool) -> None:
        """Actualiza las etiquetas del eje Y segun la unidad seleccionada."""
        if is_kg:
            self.graph_thrust.setLabel("left", "Empuje (kg)", color="#40c4aa")
            self.graph_impulse.setLabel("left", "Impulso (kg·s)", color="#6dbf4a")
            self._thrust_unit = "kg"
            self._impulse_unit = "kg*s"
        else:
            self.graph_thrust.setLabel("left", "Empuje (N)", color="#40c4aa")
            self.graph_impulse.setLabel("left", "Impulso (N·s)", color="#6dbf4a")
            self._thrust_unit = "N"
            self._impulse_unit = "N*s"

    def update_impulse(self, time_data: list[float], impulse_data: list[float]) -> None:
        """Actualiza el grafico de impulso con nuevos datos."""
        self.curve_impulse.setData(time_data, impulse_data)
        self._impulse_series = [("Ensayo", time_data, impulse_data)]

    def update_comparison(
        self,
        time_a: list[float],
        thrust_a: list[float],
        impulse_a: list[float],
        time_b: list[float] | None = None,
        thrust_b: list[float] | None = None,
        impulse_b: list[float] | None = None,
    ) -> None:
        """Muestra uno o dos ensayos superpuestos para comparacion posterior."""
        self.curve_thrust.setData(time_a, thrust_a)
        self.curve_impulse.setData(time_a, impulse_a)
        self.curve_thrust_b.setData(time_b or [], thrust_b or [])
        self.curve_impulse_b.setData(time_b or [], impulse_b or [])
        self._thrust_series = [("Ensayo A", time_a, thrust_a)]
        self._impulse_series = [("Ensayo A", time_a, impulse_a)]
        if time_b and thrust_b and impulse_b:
            self._thrust_series.append(("Ensayo B", time_b, thrust_b))
            self._impulse_series.append(("Ensayo B", time_b, impulse_b))

    def clear(self) -> None:
        """Limpia ambos graficos y reactiva el seguimiento automatico."""
        self.curve_thrust.setData([], [])
        self.curve_impulse.setData([], [])
        self.curve_thrust_b.setData([], [])
        self.curve_impulse_b.setData([], [])
        self._thrust_series.clear()
        self._impulse_series.clear()
        for overlay in self._hover_overlays.values():
            for item in overlay:
                item.hide()
        self.graph_thrust.enableAutoRange()
        self.graph_impulse.enableAutoRange()

    def set_interaction(self, enabled: bool) -> None:
        """Habilita o deshabilita el zoom y paneo manual."""
        self.graph_thrust.setMouseEnabled(x=enabled, y=enabled)
        self.graph_impulse.setMouseEnabled(x=enabled, y=enabled)
        if not enabled:
            # Si deshabilitamos el raton (ej. durante grabación), forzamos auto-rango
            self.graph_thrust.enableAutoRange()
            self.graph_impulse.enableAutoRange()

    # ── Trim mode ──────────────────────────────────────────────────────────────

    def enable_trim_mode(self, t_min: float = 0.0, t_max: float = 10.0) -> None:
        """
        Activa el modo recorte mostrando un LinearRegionItem arrastrable sobre la grafica.

        El region emitira trim_range_changed cada vez que el usuario mueva las lineas.

        Args:
            t_min: Limite izquierdo inicial de la region de recorte.
            t_max: Limite derecho inicial de la region de recorte.
        """
        if self._trim_region is not None:
            return  # ya activo

        # Calcular posicion inicial: 25%-75% del rango visible
        span = t_max - t_min if t_max > t_min else 10.0
        r0 = t_min + span * 0.25
        r1 = t_min + span * 0.75

        self._trim_region = pg.LinearRegionItem(
            values=[r0, r1],
            brush=pg.mkBrush(0, 255, 136, 30),
            pen=pg.mkPen("#6dbf4a", width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            movable=True,
        )
        self._trim_region.sigRegionChanged.connect(self._on_region_changed)
        self.graph_thrust.addItem(self._trim_region)

        # Emitir estado inicial
        self.trim_range_changed.emit(r0, r1)
        logger.info("Modo recorte activado: [%.2f, %.2f]", r0, r1)

    def disable_trim_mode(self) -> None:
        """Desactiva el modo recorte y elimina el LinearRegionItem."""
        if self._trim_region is not None:
            self.graph_thrust.removeItem(self._trim_region)
            self._trim_region = None
            logger.info("Modo recorte desactivado.")

    def get_trim_range(self) -> tuple[float, float]:
        """
        Retorna el rango de tiempo actualmente seleccionado.

        Returns:
            Tupla (t_start, t_end) en segundos. Si no hay region activa, retorna (0, 0).
        """
        if self._trim_region is None:
            return (0.0, 0.0)
        region = self._trim_region.getRegion()
        return (float(region[0]), float(region[1]))

    def _on_region_changed(self) -> None:
        """Slot interno: emite trim_range_changed cuando el usuario mueve la region."""
        if self._trim_region is not None:
            t0, t1 = self._trim_region.getRegion()
            self.trim_range_changed.emit(float(t0), float(t1))

    def _install_hover_feedback(self, graph: pg.PlotWidget, series_kind: str) -> None:
        """Agrega una cruz y etiqueta que aparecen al acercarse a una muestra."""
        vertical = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#ffffff", width=1))
        horizontal = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#ffffff", width=1))
        label = pg.TextItem(anchor=(0, 1), color="#ffffff")
        for item in (vertical, horizontal, label):
            graph.addItem(item, ignoreBounds=True)
            item.hide()
        self._hover_overlays[series_kind] = (vertical, horizontal, label)
        self._hover_proxies.append(pg.SignalProxy(
            graph.scene().sigMouseMoved,
            rateLimit=60,
            slot=lambda event: self._on_mouse_moved(graph, series_kind, event),
        ))

    def _on_mouse_moved(self, graph: pg.PlotWidget, series_kind: str, event) -> None:
        mouse_pos = event[0]
        overlay = self._hover_overlays[series_kind]
        if not graph.sceneBoundingRect().contains(mouse_pos):
            self._hide_hover_overlay(overlay)
            return

        view_box = graph.getPlotItem().vb
        view_pos = view_box.mapSceneToView(mouse_pos)
        series = self._thrust_series if series_kind == "thrust" else self._impulse_series
        nearest = self._nearest_visible_point(series, view_pos.x(), mouse_pos, view_box)
        if nearest is None:
            self._hide_hover_overlay(overlay)
            return

        name, x_value, y_value = nearest
        vertical, horizontal, label = overlay
        vertical.setPos(x_value)
        horizontal.setPos(y_value)
        unit = self._thrust_unit if series_kind == "thrust" else self._impulse_unit
        metric = "Empuje" if series_kind == "thrust" else "Impulso"
        label.setText(f"{name}\nt: {x_value:.3f} s\n{metric}: {y_value:.3f} {unit}", color="#ffffff")
        label.setPos(x_value, y_value)
        for item in overlay:
            item.show()

    @staticmethod
    def _nearest_visible_point(series, target_x: float, mouse_pos, view_box):
        closest = None
        closest_distance = 16.0
        for name, x_values, y_values in series:
            if not x_values:
                continue
            index = bisect_left(x_values, target_x)
            for candidate in (index - 1, index):
                if not 0 <= candidate < len(x_values):
                    continue
                point_pos = view_box.mapViewToScene(
                    pg.Point(float(x_values[candidate]), float(y_values[candidate]))
                )
                distance = hypot(mouse_pos.x() - point_pos.x(), mouse_pos.y() - point_pos.y())
                if distance <= closest_distance:
                    closest_distance = distance
                    closest = (name, x_values[candidate], y_values[candidate])
        return closest

    @staticmethod
    def _hide_hover_overlay(overlay) -> None:
        for item in overlay:
            item.hide()
