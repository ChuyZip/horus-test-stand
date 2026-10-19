"""Vista principal de telemetría y prueba en vivo de motor cohete.

Implementa:
- 4 Tarjetas KPI de telemetría (Pico N, Impulso N·s, Empuje actual N, Tiempo s).
- Columna de control rápido con máquina de estados estricta:
    * Botón [📋 Muestra]: Formulario de caracterización previo obligatorio.
    * Botón [▶ Iniciar]: Secuencia con conteo regresivo y disparo.
    * Botón [⏹ Detener]: Fin ordenado de adquisición.
    * Botón [🔄 Reiniciar]: Puesta a cero de la instrumentación.
- 3 Gráficas aceleradas pyqtgraph en 2 columnas:
    * Columna Izquierda: Señal analógica de celda (V vs s) + Impulso acumulado (N·s vs s).
    * Columna Derecha: Empuje del motor (N vs s) a altura completa con marcado dinámico de pico y línea de ignición.
- Detección de saturación ADC y cálculo balístico completo al terminar (Isp, empuje promedio, Nakka).
- Guardado automático en base de datos SQLite y exportación a CSV.
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
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from comunicacion.base import CanalDAQ
from comunicacion.simulador import SimuladorMotorCohete
from core.balistica import MetricasBalisticas, calcular_metricas_balisticas
from core.procesador_senal import ProcesadorSenal
from datos.gestor_db import EnsayoMetadata, GestorBD
from estilo.tema import (
    COLOR_ACENTO_CRITICO,
    COLOR_AMBAR,
    COLOR_BORDE_NORMAL,
    COLOR_BORDE_TENUE,
    COLOR_CIAN,
    COLOR_FONDO_PRINCIPAL,
    COLOR_PANEL_CLARO,
    COLOR_PANEL_MEDIO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
    COLOR_VERDE_NEON,
    EstadoInstrumentacion,
)
from ui.dialogos.dialogo_muestra import DialogoMuestra
from ui.dialogos.dialogo_resultados import DialogoResultados

pg.setConfigOption("background", COLOR_FONDO_PRINCIPAL)
pg.setConfigOption("foreground", COLOR_TEXTO_PRINCIPAL)
pg.setConfigOptions(antialias=True)


class TarjetaKPIExacta(QFrame):
    """Tarjeta de telemetría idéntica a la estación de instrumentación."""

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
    """Vista de telemetría en vivo con máquina de estados, gráficas e integración DAQ."""

    estado_cambiado = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Módulos centrales
        self.procesador = ProcesadorSenal(factor_n_por_v=1000.0, alfa_filtro=0.15)
        self.canal_daq: CanalDAQ = SimuladorMotorCohete(frecuencia_hz=200.0)
        self.gestor_bd = GestorBD()

        # Metadatos del ensayo en curso
        self.meta_actual: Optional[EnsayoMetadata] = None
        self._tiempo_ignicion_detectado: Optional[float] = None

        # Búferes circulares de alta velocidad
        self.max_muestras = 6000
        self.buf_tiempo = deque(maxlen=self.max_muestras)
        self.buf_empuje_filt = deque(maxlen=self.max_muestras)
        self.buf_volt_crudo = deque(maxlen=self.max_muestras)
        self.buf_volt_filt = deque(maxlen=self.max_muestras)
        self.buf_impulso = deque(maxlen=self.max_muestras)

        self.empuje_pico_actual = 0.0
        self.tiempo_pico_actual = 0.0

        self._cola_nuevas_muestras: list[tuple[float, float]] = []

        self._construir_ui()
        self._conectar_canal_daq()
        self._actualizar_botones_por_estado(EstadoInstrumentacion.LISTO)

        # Timer de renderizado gráfico a 60 FPS
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

        # Columna de controles de la máquina de estados
        col_botones = QVBoxLayout()
        col_botones.setSpacing(4)

        self.btn_muestra = QPushButton("📋 CARACTERIZAR MUESTRA")
        self.btn_muestra.setStyleSheet(
            f"background: #1C3B68; color: #FFFFFF; border: 1px solid {COLOR_CIAN}; border-radius: 6px; padding: 5px 12px; font-weight: 800; font-size: 11px;"
        )
        self.btn_muestra.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_muestra.clicked.connect(self._abrir_formulario_muestra)

        self.btn_iniciar = QPushButton("▶ INICIAR SIMULACIÓN")
        self.btn_iniciar.setObjectName("BtnIniciarSim")
        self.btn_iniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_iniciar.clicked.connect(self._al_hacer_clic_iniciar)

        self.btn_detener = QPushButton("⏹ DETENER")
        self.btn_detener.setObjectName("BtnDetenerSim")
        self.btn_detener.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detener.clicked.connect(self._al_hacer_clic_detener)

        self.btn_reiniciar = QPushButton("🔄 REINICIAR")
        self.btn_reiniciar.setObjectName("BtnReiniciarSim")
        self.btn_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reiniciar.clicked.connect(self.reiniciar_datos)

        col_botones.addWidget(self.btn_muestra)
        col_botones.addWidget(self.btn_iniciar)
        col_botones.addWidget(self.btn_detener)
        col_botones.addWidget(self.btn_reiniciar)

        fila_superior.addLayout(col_botones)
        layout_principal.addLayout(fila_superior)

        # -------------------------------------------------------------
        # 2. ÁREA DE GRÁFICAS EN 2 COLUMNAS
        # -------------------------------------------------------------
        layout_graficas = QHBoxLayout()
        layout_graficas.setSpacing(10)

        estilo_eje = {"color": COLOR_TEXTO_SECUNDARIO, "font-size": "10px", "font-weight": "bold"}

        # COLUMNA IZQUIERDA: Voltaje (Arriba) e Impulso (Abajo)
        col_izq = QVBoxLayout()
        col_izq.setSpacing(8)

        # Gráfica 1: Tensión de celda (V vs s)
        self.plot_voltaje = pg.PlotWidget()
        self._estilizar_plot(self.plot_voltaje, "SEÑAL ANALÓGICA DE CELDA (V vs s)")
        self.plot_voltaje.setLabel("left", "Voltaje", units="V", **estilo_eje)
        self.plot_voltaje.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        pen_cruda = pg.mkPen(color=QColor(255, 255, 255, 110), width=1.3, style=Qt.PenStyle.DotLine)
        self.curva_volt_cruda = self.plot_voltaje.plot(pen=pen_cruda, name="Cruda")

        pen_filt = pg.mkPen(color=COLOR_CIAN, width=2.2)
        self.curva_volt_filt = self.plot_voltaje.plot(pen=pen_filt, name="Filtrada")

        col_izq.addWidget(self.plot_voltaje, 1)

        # Checkbox para alternar señal cruda
        self.chk_mostrar_cruda = QCheckBox("Mostrar señal cruda punteada")
        self.chk_mostrar_cruda.setChecked(True)
        self.chk_mostrar_cruda.toggled.connect(self.curva_volt_cruda.setVisible)
        col_izq.addWidget(self.chk_mostrar_cruda)

        # Gráfica 2: Impulso acumulado (N·s vs s)
        self.plot_impulso = pg.PlotWidget()
        self._estilizar_plot(self.plot_impulso, "IMPULSO ACUMULADO - REGLA TRAPEZOIDAL (N·s vs s)")
        self.plot_impulso.setLabel("left", "Impulso", units="N·s", **estilo_eje)
        self.plot_impulso.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        self.curva_impulso = self.plot_impulso.plot(
            pen=pg.mkPen(color=COLOR_AMBAR, width=2.4),
            fillLevel=0.0,
            fillBrush=pg.mkBrush(255, 145, 0, 55),
            name="Impulso Acumulado",
        )
        col_izq.addWidget(self.plot_impulso, 1)

        layout_graficas.addLayout(col_izq, 46)

        # COLUMNA DERECHA: Empuje del motor (N vs s) a altura completa
        col_der = QVBoxLayout()
        col_der.setSpacing(0)

        self.plot_empuje = pg.PlotWidget()
        self._estilizar_plot(self.plot_empuje, "EMPUJE DEL MOTOR (N vs s)")
        self.plot_empuje.setLabel("left", "Empuje", units="N", **estilo_eje)
        self.plot_empuje.setLabel("bottom", "Tiempo", units="s", **estilo_eje)

        self.curva_empuje = self.plot_empuje.plot(
            pen=pg.mkPen(color="#FFFFFF", width=2.6),
            fillLevel=0.0,
            fillBrush=pg.mkBrush(31, 27, 78, 140),
            name="Empuje",
        )

        # Línea vertical indicadora del instante de ignición
        self.linea_ignicion = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            pen=pg.mkPen(color="#FF5252", width=1.5, style=Qt.PenStyle.DashLine),
            label="Ignición",
            labelOpts={"position": 0.85, "color": "#FF5252", "fill": (31, 27, 78, 200)},
        )
        self.linea_ignicion.hide()
        self.plot_empuje.addItem(self.linea_ignicion)

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

    def _conectar_canal_daq(self) -> None:
        self.canal_daq.nueva_muestra.connect(self._recibir_muestra)
        self.canal_daq.estado_cambiado.connect(self._al_cambiar_estado)
        self.canal_daq.alerta_seguridad.connect(self._alerta_seguridad)
        self.canal_daq.simulacion_finalizada.connect(self._al_finalizar_ensayo)

    def _actualizar_botones_por_estado(self, estado: EstadoInstrumentacion) -> None:
        """Control estricto de transiciones y habilitación de botones."""
        if estado == EstadoInstrumentacion.LISTO:
            self.btn_muestra.setEnabled(True)
            self.btn_iniciar.setEnabled(self.meta_actual is not None)
            self.btn_detener.setEnabled(False)
            self.btn_reiniciar.setEnabled(True)
            if self.meta_actual:
                self.btn_iniciar.setText("▶ INICIAR ENSAYO")
            else:
                self.btn_iniciar.setText("▶ (Requiere Muestra)")

        elif estado in (EstadoInstrumentacion.ARMADO, EstadoInstrumentacion.CUENTA_REGRESIVA):
            self.btn_muestra.setEnabled(False)
            self.btn_iniciar.setEnabled(False)
            self.btn_detener.setEnabled(True)
            self.btn_reiniciar.setEnabled(False)

        elif estado == EstadoInstrumentacion.GRABANDO:
            self.btn_muestra.setEnabled(False)
            self.btn_iniciar.setEnabled(False)
            self.btn_detener.setEnabled(True)
            self.btn_reiniciar.setEnabled(False)

        elif estado in (EstadoInstrumentacion.TERMINADO, EstadoInstrumentacion.ABORTADO):
            self.btn_muestra.setEnabled(True)
            self.btn_iniciar.setEnabled(False)
            self.btn_detener.setEnabled(False)
            self.btn_reiniciar.setEnabled(True)

    def _abrir_formulario_muestra(self) -> None:
        dlg = DialogoMuestra(self)
        if dlg.exec():
            self.meta_actual = dlg.metadata_resultado
            QMessageBox.information(
                self,
                "Muestra Registrada",
                f"Ensayo '{self.meta_actual.codigo_ensayo}' preparado.\nEl sistema ya está listo para armar e iniciar.",
            )
            self._actualizar_botones_por_estado(EstadoInstrumentacion.LISTO)

    def _al_hacer_clic_iniciar(self) -> None:
        if not self.meta_actual:
            self._abrir_formulario_muestra()
            if not self.meta_actual:
                return

        if not self.canal_daq.isRunning():
            self.reiniciar_datos(preservar_meta=True)
            self.canal_daq.iniciar_adquisicion()

    def _al_hacer_clic_detener(self) -> None:
        if self.canal_daq.isRunning():
            self.canal_daq.detener_adquisicion()
            self._al_finalizar_ensayo()

    def _recibir_muestra(self, t: float, v: float) -> None:
        self._cola_nuevas_muestras.append((t, v))

    def _al_cambiar_estado(self, estado: object) -> None:
        if isinstance(estado, EstadoInstrumentacion):
            self._actualizar_botones_por_estado(estado)
        self.estado_cambiado.emit(estado)

    def _alerta_seguridad(self, mensaje: str) -> None:
        QMessageBox.warning(self, "Alerta de Seguridad DAQ", mensaje)

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

            # Detección del instante de ignición (primera vez que supera 15 N)
            if self._tiempo_ignicion_detectado is None and m.empuje_filtrado >= 15.0:
                self._tiempo_ignicion_detectado = m.tiempo
                self.linea_ignicion.setValue(m.tiempo)
                self.linea_ignicion.show()

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

        # 1. Empuje del motor
        self.curva_empuje.setData(arr_t, arr_f)

        if self.empuje_pico_actual > 10.0:
            self.marcador_pico.setData(x=[self.tiempo_pico_actual], y=[self.empuje_pico_actual])
            self.etiqueta_pico.setText(
                f"PICO: {self.empuje_pico_actual:,.1f} N @ {self.tiempo_pico_actual:.2f}s"
            )
            self.etiqueta_pico.setPos(self.tiempo_pico_actual, self.empuje_pico_actual)
            self.marcador_pico.show()
            self.etiqueta_pico.show()

        # 2. Tensión celda
        if self.chk_mostrar_cruda.isChecked():
            self.curva_volt_cruda.setData(arr_t, arr_vc)
        self.curva_volt_filt.setData(arr_t, arr_vf)

        # 3. Impulso acumulado
        self.curva_impulso.setData(arr_t, arr_imp)

        # 4. Tarjetas KPI
        if ultima_m is not None:
            self.card_pico.actualizar(f"{self.empuje_pico_actual:,.1f}")
            self.card_impulso.actualizar(f"{ultima_m.impulso_acumulado:,.2f}")
            self.card_actual.actualizar(f"{max(0.0, ultima_m.empuje_filtrado):,.1f}")
            self.card_tiempo.actualizar(f"{ultima_m.tiempo:.2f}")

    def _al_finalizar_ensayo(self) -> None:
        self.estado_cambiado.emit(EstadoInstrumentacion.TERMINADO)
        self._actualizar_botones_por_estado(EstadoInstrumentacion.TERMINADO)

        if not self.buf_tiempo or len(self.buf_tiempo) < 10:
            return

        # Metadatos predeterminados si no se completó la ficha previa
        if not self.meta_actual:
            self.meta_actual = EnsayoMetadata(
                codigo_ensayo="ENSAYO-AUTO",
                operadores="Operador HSL",
                masa_propelente_g=200.0,
            )

        # Cálculo de fórmulas balísticas avanzadas
        metricas = calcular_metricas_balisticas(
            tiempos=list(self.buf_tiempo),
            empujes=list(self.buf_empuje_filt),
            masa_propelente_g=self.meta_actual.masa_propelente_g,
            diam_ext_mm=self.meta_actual.diam_ext_mm,
            diam_int_mm=self.meta_actual.diam_int_mm,
        )

        # Función de exportación para el diálogo
        def exportar_callback(ruta_csv: str) -> None:
            ensayo_id = self.gestor_bd.guardar_ensayo(
                meta=self.meta_actual,
                tiempos=list(self.buf_tiempo),
                voltajes=list(self.buf_volt_crudo),
                empujes=list(self.buf_empuje_filt),
                impulsos=list(self.buf_impulso),
            )
            self.gestor_bd.exportar_csv(ensayo_id, ruta_csv)

        dlg = DialogoResultados(self.meta_actual, metricas, gestor_bd_fn=exportar_callback, parent=self)
        dlg.guardado_solicitado.connect(self._guardar_en_bd)
        dlg.exec()

    def _guardar_en_bd(self, meta: EnsayoMetadata, clase_ajustada: str) -> None:
        meta.clase_nakka = clase_ajustada
        try:
            ensayo_id = self.gestor_bd.guardar_ensayo(
                meta=meta,
                tiempos=list(self.buf_tiempo),
                voltajes=list(self.buf_volt_crudo),
                empujes=list(self.buf_empuje_filt),
                impulsos=list(self.buf_impulso),
            )
            QMessageBox.information(
                self,
                "Base de Datos SQLite",
                f"Ensayo '{meta.codigo_ensayo}' guardado exitosamente con ID #{ensayo_id}.\nYa está disponible en la pestaña de Historial.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error de Guardado", f"No se pudo guardar en SQLite: {e}")

    def reiniciar_datos(self, preservar_meta: bool = False) -> None:
        if self.canal_daq.isRunning():
            self.canal_daq.detener_adquisicion()

        if not preservar_meta:
            self.meta_actual = None

        self._cola_nuevas_muestras.clear()
        self.buf_tiempo.clear()
        self.buf_empuje_filt.clear()
        self.buf_volt_crudo.clear()
        self.buf_volt_filt.clear()
        self.buf_impulso.clear()

        self.empuje_pico_actual = 0.0
        self.tiempo_pico_actual = 0.0
        self._tiempo_ignicion_detectado = None

        self.procesador.reiniciar()

        self.curva_empuje.clear()
        self.curva_volt_cruda.clear()
        self.curva_volt_filt.clear()
        self.curva_impulso.clear()
        self.marcador_pico.clear()
        self.marcador_pico.hide()
        self.etiqueta_pico.hide()
        self.linea_ignicion.hide()

        self.card_pico.actualizar("0.0")
        self.card_impulso.actualizar("0.00")
        self.card_actual.actualizar("0.0")
        self.card_tiempo.actualizar("0.00")

        self.estado_cambiado.emit(EstadoInstrumentacion.LISTO)
        self._actualizar_botones_por_estado(EstadoInstrumentacion.LISTO)

    def abortar_inmediato(self) -> None:
        self.canal_daq.abortar()
        self.estado_cambiado.emit(EstadoInstrumentacion.ABORTADO)
        self._actualizar_botones_por_estado(EstadoInstrumentacion.ABORTADO)
