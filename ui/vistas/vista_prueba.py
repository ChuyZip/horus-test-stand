"""Vista principal de telemetría y prueba en vivo de motor cohete.

Estructura idéntica a la estación de control de referencia:
- Fila superior:
    * 4 tarjetas de lectura rápida de telemetría:
        1. PICO DE EMPUJE MÁXIMO (Valor blanco, Unidad N verde neón)
        2. IMPULSO TOTAL (Valor blanco, Unidad N·s verde neón)
        3. EMPUJE ACTUAL (Valor verde neón, Unidad N verde neón)
        4. TIEMPO DE QUEMADO (Valor cian, Unidad s cian)
    * Columna de control con 3 botones de acción rápida:
        [▶ INICIAR SIMULACIÓN] (Verde)
        [⏹ DETENER] (Rojo)
        [🔄 REINICIAR] (Azul)
- Área gráfica inferior:
    * Columna izquierda (~46%):
        - Arriba: SEÑAL ANALÓGICA DE CELDA (V vs s) en cian + Checkbox "Mostrar señal cruda punteada"
        - Abajo: IMPULSO ACUMULADO - REGLA TRAPEZOIDAL (N·s vs s) en ámbar con relleno translúcido
    * Columna derecha (~54%):
        - EMPUJE DEL MOTOR (N vs s) en trazo blanco de alto contraste a altura completa con marcador dinámico de pico
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from comunicacion.simulador import SimuladorMotorCohete
from core.procesador_senal import ProcesadorSenal
from estilo.tema import (
    COLOR_ACENTO_CRITICO,
    COLOR_AMBAR,
    COLOR_BORDE_NORMAL,
    COLOR_BORDE_TENUE,
    COLOR_CIAN,
    COLOR_FONDO_PRINCIPAL,
    COLOR_PANEL_MEDIO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
    COLOR_VERDE_NEON,
    EstadoInstrumentacion,
)

pg.setConfigOption("background", COLOR_FONDO_PRINCIPAL)
pg.setConfigOption("foreground", COLOR_TEXTO_PRINCIPAL)
pg.setConfigOptions(antialias=True)


class TarjetaKPIExacta(QFrame):
    """Tarjeta de telemetría idéntica a la interfaz del banco de pruebas."""

    def __init__(
        self,
        titulo: str,
        unidad: str,
        color_valor: str = "#FFFFFF",
        color_unidad: str = COLOR_VERDE_NEON,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("class", "TarjetaKPI")
        self.unidad = unidad
        self.color_valor = color_valor
        self.color_unidad = color_unidad

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)

        self.lbl_titulo = QLabel(titulo.upper())
        self.lbl_titulo.setProperty("class", "TituloKPI")

        fila_valor = QHBoxLayout()
        fila_valor.setSpacing(6)

        self.lbl_valor = QLabel("0.0")
        self.lbl_valor.setStyleSheet(
            f"color: {self.color_valor}; font-size: 24px; font-weight: 900; font-family: 'Menlo', Consolas, monospace;"
        )

        self.lbl_unidad = QLabel(self.unidad)
        self.lbl_unidad.setStyleSheet(
            f"color: {self.color_unidad}; font-size: 13px; font-weight: 800; padding-top: 4px;"
        )

        fila_valor.addWidget(self.lbl_valor)
        fila_valor.addWidget(self.lbl_unidad)
        fila_valor.addStretch()

        layout.addWidget(self.lbl_titulo)
        layout.addLayout(fila_valor)

    def actualizar(self, valor_str: str) -> None:
        self.lbl_valor.setText(valor_str)


class VistaPrueba(QWidget):
    """Vista principal con disposición exacta de telemetría y 3 gráficas pyqtgraph."""

    estado_cambiado = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.procesador = ProcesadorSenal(factor_n_por_v=1000.0, alfa_filtro=0.15)
        self.simulador = SimuladorMotorCohete(frecuencia_hz=200.0)

        self.max_muestras = 4000
        self.buf_tiempo = deque(maxlen=self.max_muestras)
        self.buf_empuje_filt = deque(maxlen=self.max_muestras)
        self.buf_volt_crudo = deque(maxlen=self.max_muestras)
        self.buf_volt_filt = deque(maxlen=self.max_muestras)
        self.buf_impulso = deque(maxlen=self.max_muestras)

        self.empuje_pico_actual = 0.0
        self.tiempo_pico_actual = 0.0

        self._cola_nuevas_muestras: list[tuple[float, float]] = []

        self._construir_ui()
        self._conectar_senales()

        # Refresco visual estable a 60 FPS
        self.timer_render = QTimer(self)
        self.timer_render.setInterval(16)
        self.timer_render.timeout.connect(self._actualizar_graficas_y_metricas)
        self.timer_render.start()

    def _construir_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(14, 10, 14, 10)
        layout_principal.setSpacing(10)

        # -------------------------------------------------------------
        # 1. FILA SUPERIOR: 4 TARJETAS KPI + COLUMNA DE BOTONES
        # -------------------------------------------------------------
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(10)

        # 4 Tarjetas de lectura rápida
        self.card_pico = TarjetaKPIExacta(
            "Pico de Empuje Máximo", "N", color_valor="#FFFFFF", color_unidad=COLOR_VERDE_NEON
        )
        self.card_impulso = TarjetaKPIExacta(
            "Impulso Total", "N·s", color_valor="#FFFFFF", color_unidad=COLOR_VERDE_NEON
        )
        self.card_actual = TarjetaKPIExacta(
            "Empuje Actual", "N", color_valor=COLOR_VERDE_NEON, color_unidad=COLOR_VERDE_NEON
        )
        self.card_tiempo = TarjetaKPIExacta(
            "Tiempo de Quemado", "s", color_valor=COLOR_CIAN, color_unidad=COLOR_CIAN
        )

        fila_superior.addWidget(self.card_pico, 1)
        fila_superior.addWidget(self.card_impulso, 1)
        fila_superior.addWidget(self.card_actual, 1)
        fila_superior.addWidget(self.card_tiempo, 1)

        # Columna de 3 botones de control rápido
        col_botones = QVBoxLayout()
        col_botones.setSpacing(4)

        self.btn_iniciar = QPushButton("▶ INICIAR SIMULACIÓN")
        self.btn_iniciar.setObjectName("BtnIniciarSim")
        self.btn_iniciar.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_detener = QPushButton("⏹ DETENER")
        self.btn_detener.setObjectName("BtnDetenerSim")
        self.btn_detener.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_reiniciar = QPushButton("🔄 REINICIAR")
        self.btn_reiniciar.setObjectName("BtnReiniciarSim")
        self.btn_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)

        col_botones.addWidget(self.btn_iniciar)
        col_botones.addWidget(self.btn_detener)
        col_botones.addWidget(self.btn_reiniciar)

        fila_superior.addLayout(col_botones)
        layout_principal.addLayout(fila_superior)

        # -------------------------------------------------------------
        # 2. ÁREA DE GRÁFICAS: 2 COLUMNAS (IZQUIERDA: 2 PLOTS, DERECHA: EMPUJE)
        # -------------------------------------------------------------
        layout_graficas = QHBoxLayout()
        layout_graficas.setSpacing(10)

        estilo_eje = {"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px", "font-weight": "bold"}

        # ------------------------------------
        # COLUMNA IZQUIERDA (46% del ancho)
        # ------------------------------------
        col_izq = QVBoxLayout()
        col_izq.setSpacing(8)

        # a) Gráfica 1: SEÑAL ANALÓGICA DE CELDA (V vs s)
        self.plot_voltaje = pg.PlotWidget()
        self._estilizar_plot(self.plot_voltaje, "SEÑAL ANALÓGICA DE CELDA (V vs s)")
        self.plot_voltaje.setLabel("left", "Voltaje", units="V", **estilo_eje)
        self.plot_voltaje.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        pen_cruda = pg.mkPen(color=QColor(255, 255, 255, 110), width=1.3, style=Qt.PenStyle.DotLine)
        self.curva_volt_cruda = self.plot_voltaje.plot(pen=pen_cruda, name="Cruda")

        pen_filt = pg.mkPen(color=COLOR_CIAN, width=2.2)
        self.curva_volt_filt = self.plot_voltaje.plot(pen=pen_filt, name="Filtrada")

        col_izq.addWidget(self.plot_voltaje, 1)

        # Checkbox inmediatamente debajo del gráfico de voltaje
        self.chk_mostrar_cruda = QCheckBox("Mostrar señal cruda punteada")
        self.chk_mostrar_cruda.setChecked(True)
        self.chk_mostrar_cruda.toggled.connect(self._al_alternar_cruda)
        col_izq.addWidget(self.chk_mostrar_cruda)

        # b) Gráfica 2: IMPULSO ACUMULADO - REGLA TRAPEZOIDAL (N·s vs s)
        self.plot_impulso = pg.PlotWidget()
        self._estilizar_plot(self.plot_impulso, "IMPULSO ACUMULADO - REGLA TRAPEZOIDAL (N·s vs s)")
        self.plot_impulso.setLabel("left", "Impulso", units="N·s", **estilo_eje)
        self.plot_impulso.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        # Trazo ámbar con relleno translúcido característico
        self.curva_impulso = self.plot_impulso.plot(
            pen=pg.mkPen(color=COLOR_AMBAR, width=2.4),
            fillLevel=0.0,
            fillBrush=pg.mkBrush(255, 145, 0, 55),
            name="Impulso Acumulado",
        )
        col_izq.addWidget(self.plot_impulso, 1)

        layout_graficas.addLayout(col_izq, 46)

        # ------------------------------------
        # COLUMNA DERECHA (54% del ancho)
        # ------------------------------------
        col_der = QVBoxLayout()
        col_der.setSpacing(0)

        # c) Gráfica 3: EMPUJE DEL MOTOR (N vs s) - Altura completa
        self.plot_empuje = pg.PlotWidget()
        self._estilizar_plot(self.plot_empuje, "EMPUJE DEL MOTOR (N vs s)")
        self.plot_empuje.setLabel("left", "Empuje", units="N", **estilo_eje)
        self.plot_empuje.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        # Curva de combustión en blanco sólido de alto impacto
        self.curva_empuje = self.plot_empuje.plot(
            pen=pg.mkPen(color="#FFFFFF", width=2.6),
            fillLevel=0.0,
            fillBrush=pg.mkBrush(31, 27, 78, 140),
            name="Empuje",
        )

        # Marcador dinámico del pico de empuje
        self.marcador_pico = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen(color="#FFFFFF", width=2),
            brush=pg.mkBrush(COLOR_ACENTO_CRITICO),
            symbol="star",
        )
        self.plot_empuje.addItem(self.marcador_pico)

        self.etiqueta_pico = pg.TextItem(text="", color="#FFFFFF", anchor=(0.5, 1.3))
        fuente_pico = QFont()
        fuente_pico.setBold(True)
        fuente_pico.setPointSize(9)
        self.etiqueta_pico.setFont(fuente_pico)
        self.plot_empuje.addItem(self.etiqueta_pico)

        col_der.addWidget(self.plot_empuje, 1)
        layout_graficas.addLayout(col_der, 54)

        layout_principal.addLayout(layout_graficas, 1)

    def _estilizar_plot(self, plot: pg.PlotWidget, titulo: str) -> None:
        plot.setBackground(COLOR_FONDO_PRINCIPAL)
        plot.showGrid(x=True, y=True, alpha=0.12)
        plot.getAxis("bottom").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))
        plot.getAxis("left").setPen(pg.mkPen(color=(255, 255, 255, 35), width=1))

        if titulo:
            plot.setTitle(
                f"<span style='color:#FFFFFF; font-weight:800; font-size:10pt; letter-spacing:0.8px;'>{titulo}</span>"
            )

        plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def _conectar_senales(self) -> None:
        self.btn_iniciar.clicked.connect(self._al_hacer_clic_iniciar)
        self.btn_detener.clicked.connect(self._al_hacer_clic_detener)
        self.btn_reiniciar.clicked.connect(self.reiniciar_datos)

        self.simulador.nueva_muestra.connect(self._recibir_muestra_simulada)
        self.simulador.estado_cambiado.connect(self._al_cambiar_estado_simulador)
        self.simulador.simulacion_finalizada.connect(self._al_finalizar_simulador)

    def _al_hacer_clic_iniciar(self) -> None:
        if not self.simulador.isRunning():
            self.reiniciar_datos()
            self.simulador.iniciar_simulacion()

    def _al_hacer_clic_detener(self) -> None:
        if self.simulador.isRunning():
            self.simulador.detener()
            self.estado_cambiado.emit(EstadoInstrumentacion.TERMINADO)

    def _recibir_muestra_simulada(self, t: float, v: float) -> None:
        self._cola_nuevas_muestras.append((t, v))

    def _al_cambiar_estado_simulador(self, estado: object) -> None:
        self.estado_cambiado.emit(estado)

    def _al_finalizar_simulador(self) -> None:
        self.estado_cambiado.emit(EstadoInstrumentacion.TERMINADO)

    def _al_alternar_cruda(self, visible: bool) -> None:
        self.curva_volt_cruda.setVisible(visible)

    def _actualizar_graficas_y_metricas(self) -> None:
        if not self._cola_nuevas_muestras:
            return

        muestras = self._cola_nuevas_muestras
        self._cola_nuevas_muestras = []

        ultima_m = None
        for t, v in muestras:
            m = self.procesador.procesar_muestra(t, v)
            self.buf_tiempo.append(m.tiempo)
            self.buf_empuje_filt.append(m.empuje_filtrado)
            self.buf_volt_crudo.append(m.voltaje_crudo)
            self.buf_volt_filt.append(m.voltaje_filtrado)
            self.buf_impulso.append(m.impulso_acumulado)

            if m.empuje_filtrado > self.empuje_pico_actual:
                self.empuje_pico_actual = m.empuje_filtrado
                self.tiempo_pico_actual = m.tiempo

            ultima_m = m

        if not self.buf_tiempo:
            return

        arr_t = np.array(self.buf_tiempo)
        arr_f = np.array(self.buf_empuje_filt)
        arr_vc = np.array(self.buf_volt_crudo)
        arr_vf = np.array(self.buf_volt_filt)
        arr_imp = np.array(self.buf_impulso)

        # 1. Empuje del motor (columna derecha)
        self.curva_empuje.setData(arr_t, arr_f)

        if self.empuje_pico_actual > 10.0:
            self.marcador_pico.setData(x=[self.tiempo_pico_actual], y=[self.empuje_pico_actual])
            self.etiqueta_pico.setText(
                f"PICO: {self.empuje_pico_actual:,.1f} N @ {self.tiempo_pico_actual:.2f}s"
            )
            self.etiqueta_pico.setPos(self.tiempo_pico_actual, self.empuje_pico_actual)
            self.marcador_pico.show()
            self.etiqueta_pico.show()
        else:
            self.marcador_pico.clear()
            self.marcador_pico.hide()
            self.etiqueta_pico.hide()

        # 2. Tensión celda (columna izquierda superior)
        if self.chk_mostrar_cruda.isChecked():
            self.curva_volt_cruda.setData(arr_t, arr_vc)
        self.curva_volt_filt.setData(arr_t, arr_vf)

        # 3. Impulso acumulado (columna izquierda inferior)
        self.curva_impulso.setData(arr_t, arr_imp)

        # 4. Tarjetas KPI
        if ultima_m is not None:
            self.card_pico.actualizar(f"{self.empuje_pico_actual:,.1f}")
            self.card_impulso.actualizar(f"{ultima_m.impulso_acumulado:,.2f}")
            self.card_actual.actualizar(f"{max(0.0, ultima_m.empuje_filtrado):,.1f}")
            self.card_tiempo.actualizar(f"{ultima_m.tiempo:.2f}")

    def reiniciar_datos(self) -> None:
        if self.simulador.isRunning():
            self.simulador.detener()

        self._cola_nuevas_muestras.clear()
        self.buf_tiempo.clear()
        self.buf_empuje_filt.clear()
        self.buf_volt_crudo.clear()
        self.buf_volt_filt.clear()
        self.buf_impulso.clear()

        self.empuje_pico_actual = 0.0
        self.tiempo_pico_actual = 0.0

        self.procesador.reiniciar()

        self.curva_empuje.clear()
        self.curva_volt_cruda.clear()
        self.curva_volt_filt.clear()
        self.curva_impulso.clear()
        self.marcador_pico.clear()
        self.marcador_pico.hide()
        self.etiqueta_pico.hide()

        self.card_pico.actualizar("0.0")
        self.card_impulso.actualizar("0.00")
        self.card_actual.actualizar("0.0")
        self.card_tiempo.actualizar("0.00")

        self.estado_cambiado.emit(EstadoInstrumentacion.LISTO)

    def abortar_inmediato(self) -> None:
        self.simulador.abortar()
        self.estado_cambiado.emit(EstadoInstrumentacion.ABORTADO)
