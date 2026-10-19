"""Ventana principal de la estación de telemetría y control de Horus Space Lab.

Disposición exacta de la interfaz de referencia:
- Barra superior horizontal (Header):
    * Logo circular de Horus Space Lab + "HORUS SPACE LAB" y subtítulo
    * 4 pestañas de navegación horizontales:
        [🚀 Prueba en Vivo] [📊 Historial / Comparar] [⚖️ Calibración] [⚙️ Configuración]
    * Indicador de "ESTADO DEL BANCO:" con cápsula badge dinámica
    * Botón de seguridad "🛑 ABORTAR [F12]"
- Contenedor central con QStackedWidget para las vistas
- Barra inferior sutil (Footer) con versión y estado de precisión
"""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from estilo.tema import (
    COLOR_BORDE_NORMAL,
    COLOR_FONDO_PRINCIPAL,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
    EstadoInstrumentacion,
)
from ui.vistas.vista_calibracion import VistaCalibracion
from ui.vistas.vista_configuracion import VistaConfiguracion
from ui.vistas.vista_historial import VistaHistorial
from ui.vistas.vista_prueba import VistaPrueba


class MainWindow(QMainWindow):
    """Ventana principal de la estación de adquisición y control de disparo."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Horus Space Lab - Banco de Pruebas de Motores Cohete")
        self.resize(1360, 850)
        self.setMinimumSize(1200, 720)

        self._estado_actual: EstadoInstrumentacion = EstadoInstrumentacion.TERMINADO
        self.botones_tab: list[QPushButton] = []
        self._indice_activo = 0

        self._asignar_icono_aplicacion()
        self._construir_ui()
        self._configurar_atajos_seguridad()

    def _asignar_icono_aplicacion(self) -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rutas = [
            os.path.join(base_dir, "assets", "logo.png"),
            os.path.join(base_dir, "logo.png"),
            os.path.join(base_dir, "HorusSlogan.png"),
            os.path.join(base_dir, "HorusSlogan.ico"),
        ]
        self.ruta_logo = None
        for r in rutas:
            if os.path.exists(r):
                self.setWindowIcon(QIcon(r))
                self.ruta_logo = r
                break

    def _construir_ui(self) -> None:
        widget_central = QWidget(self)
        widget_central.setObjectName("VentanaPrincipal")
        self.setCentralWidget(widget_central)

        layout_raiz = QVBoxLayout(widget_central)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        # -------------------------------------------------------------
        # 1. BARRA SUPERIOR PERSISTENTE (HEADER EXACTO)
        # -------------------------------------------------------------
        self.barra_superior = QFrame()
        self.barra_superior.setObjectName("BarraSuperior")
        layout_header = QHBoxLayout(self.barra_superior)
        layout_header.setContentsMargins(14, 6, 14, 6)
        layout_header.setSpacing(10)

        # Esquina izquierda: Logo circular + Títulos (sin restricción de ancho fijo)
        widget_marca = QWidget()
        widget_marca.setMinimumWidth(335)
        caja_marca = QHBoxLayout(widget_marca)
        caja_marca.setContentsMargins(0, 0, 0, 0)
        caja_marca.setSpacing(8)

        lbl_logo = QLabel()
        lbl_logo.setFixedSize(38, 38)
        lbl_logo.setStyleSheet("background: transparent; border-radius: 19px;")

        if self.ruta_logo and os.path.exists(self.ruta_logo):
            pix = QPixmap(self.ruta_logo).scaled(
                38,
                38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl_logo.setPixmap(pix)
        else:
            lbl_logo.setText("🚀")
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        caja_marca.addWidget(lbl_logo)

        vbox_titulos = QVBoxLayout()
        vbox_titulos.setSpacing(1)
        vbox_titulos.setContentsMargins(0, 0, 0, 0)

        lbl_tit = QLabel("HORUS SPACE LAB")
        lbl_tit.setObjectName("TituloApp")
        lbl_sub = QLabel("SISTEMA DE SEGURIDAD Y CONTROL DE DISPARO")
        lbl_sub.setObjectName("SubtituloApp")

        lbl_tit.setMinimumWidth(160)
        lbl_sub.setMinimumWidth(260)
        lbl_sub.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)

        vbox_titulos.addWidget(lbl_tit)
        vbox_titulos.addWidget(lbl_sub)
        caja_marca.addLayout(vbox_titulos)

        layout_header.addWidget(widget_marca)

        # Separador tenue
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); max-width: 1px; margin: 4px 6px;")
        layout_header.addWidget(sep)

        # Centro: Pestañas horizontales de navegación
        tabs_info = [
            ("🚀 Prueba en Vivo", 0),
            ("📊 Historial / Comparar", 1),
            ("⚖️ Calibración", 2),
            ("⚙️ Configuración", 3),
        ]

        for texto, idx in tabs_info:
            btn = QPushButton(texto)
            btn.setProperty("class", "TabNav")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("activo", "true" if idx == 0 else "false")
            btn.clicked.connect(lambda checked=False, i=idx: self.cambiar_vista(i))
            layout_header.addWidget(btn)
            self.botones_tab.append(btn)

        layout_header.addStretch(1)

        # Derecha: Estado del banco
        self.widget_estado = QWidget()
        self.widget_estado.setMinimumWidth(240)
        fila_estado = QHBoxLayout(self.widget_estado)
        fila_estado.setSpacing(8)
        fila_estado.setContentsMargins(0, 0, 0, 0)

        lbl_tag_estado = QLabel("ESTADO DEL BANCO:")
        lbl_tag_estado.setStyleSheet(
            f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 0.6px;"
        )
        lbl_tag_estado.setMinimumWidth(115)

        self.badge_estado = QFrame()
        self.badge_estado.setObjectName("BadgeEstado")
        self.badge_estado.setMinimumWidth(110)
        self.badge_estado.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout_badge = QHBoxLayout(self.badge_estado)
        layout_badge.setContentsMargins(0, 0, 0, 0)
        layout_badge.setSpacing(0)

        self.lbl_estado = QLabel(self._estado_actual.texto_completo)
        self.lbl_estado.setObjectName("TextoBadgeEstado")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout_badge.addWidget(self.lbl_estado)

        fila_estado.addWidget(lbl_tag_estado)
        fila_estado.addWidget(self.badge_estado)
        layout_header.addWidget(self.widget_estado)

        # Botón ABORTAR [F12]
        self.btn_abortar = QPushButton("🛑 ABORTAR [F12]")
        self.btn_abortar.setObjectName("BtnAbortarTop")
        self.btn_abortar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abortar.clicked.connect(self.ejecutar_aborto)
        layout_header.addWidget(self.btn_abortar)

        layout_raiz.addWidget(self.barra_superior)

        # -------------------------------------------------------------
        # 2. CONTENEDOR CENTRAL DE VISTAS (QStackedWidget)
        # -------------------------------------------------------------
        self.stack_vistas = QStackedWidget(self)

        self.vista_prueba = VistaPrueba(self)
        self.vista_historial = VistaHistorial(self)
        self.vista_calibracion = VistaCalibracion(self)
        self.vista_configuracion = VistaConfiguracion(self)

        self.stack_vistas.addWidget(self.vista_prueba)
        self.stack_vistas.addWidget(self.vista_historial)
        self.stack_vistas.addWidget(self.vista_calibracion)
        self.stack_vistas.addWidget(self.vista_configuracion)

        layout_raiz.addWidget(self.stack_vistas, 1)

        # -------------------------------------------------------------
        # 3. FOOTER INFERIOR
        # -------------------------------------------------------------
        footer = QFrame()
        footer.setStyleSheet(
            "background-color: #191542; border-top: 1px solid rgba(255, 255, 255, 0.08); min-height: 24px; max-height: 24px;"
        )
        layout_footer = QHBoxLayout(footer)
        layout_footer.setContentsMargins(14, 0, 14, 0)

        lbl_footer = QLabel("v2.4.0-Beta • PySide6 • Alta Precisión")
        lbl_footer.setObjectName("FooterTexto")
        layout_footer.addWidget(lbl_footer)
        layout_footer.addStretch()

        layout_raiz.addWidget(footer)

        # Conectar cambios de estado emitidos por la vista de prueba
        self.vista_prueba.estado_cambiado.connect(self.actualizar_estado)

        # Conectar cambios de configuración hacia la vista de prueba
        self.vista_configuracion.configuracion_guardada.connect(self._al_guardar_configuracion)

    def _configurar_atajos_seguridad(self) -> None:
        self.atajo_abortar = QShortcut(QKeySequence(Qt.Key.Key_F12), self)
        self.atajo_abortar.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.atajo_abortar.activated.connect(self.ejecutar_aborto)

    def cambiar_vista(self, indice: int) -> None:
        if indice == self._indice_activo:
            return

        self._indice_activo = indice
        for i, btn in enumerate(self.botones_tab):
            activo = i == indice
            btn.setProperty("activo", "true" if activo else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.stack_vistas.setCurrentIndex(indice)

        # Si entra a Historial, recargar tabla desde SQLite
        if indice == 1:
            self.vista_historial.recargar_tabla()

    def _al_guardar_configuracion(self, cfg: dict) -> None:
        modo = cfg.get("modo", "simulacion")
        if modo == "serial":
            puerto = cfg.get("puerto", "")
            baud = cfg.get("baudrate", 115200)
            from comunicacion.driver_serial import DriverSerialESP32
            self.vista_prueba.canal_daq = DriverSerialESP32(puerto=puerto, baudrate=baud)
        else:
            from comunicacion.simulador import SimuladorMotorCohete
            self.vista_prueba.canal_daq = SimuladorMotorCohete(frecuencia_hz=cfg.get("fs_hz", 200.0))

        self.vista_prueba._conectar_canal_daq()

    def actualizar_estado(self, nuevo_estado: object) -> None:
        if isinstance(nuevo_estado, EstadoInstrumentacion):
            self._estado_actual = nuevo_estado
        elif isinstance(nuevo_estado, str):
            for e in EstadoInstrumentacion:
                if e.name.lower() == nuevo_estado.lower() or e.etiqueta.lower() == nuevo_estado.lower():
                    self._estado_actual = e
                    break

        self.lbl_estado.setText(self._estado_actual.texto_completo)

        # Contraste optimizado según estado operacional
        color_borde = self._estado_actual.color
        color_fondo = "rgba(255, 255, 255, 0.05)"
        color_texto = self._estado_actual.color

        if self._estado_actual == EstadoInstrumentacion.ABORTADO:
            color_texto = "#FF4D4D"
            color_borde = "#BF3938"
            color_fondo = "rgba(191, 57, 56, 0.22)"

        self.lbl_estado.setStyleSheet(
            f"color: {color_texto}; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;"
        )
        self.badge_estado.setStyleSheet(
            f"""
            QFrame#BadgeEstado {{
                background-color: {color_fondo};
                border: 1px solid {color_borde};
                border-radius: 14px;
                padding: 4px 12px;
                min-height: 26px;
            }}
            """
        )

        # Ajuste dinámico de ancho mínimo para que ningún texto de estado se recorte
        ancho_texto = self.lbl_estado.fontMetrics().horizontalAdvance(self.lbl_estado.text())
        ancho_badge = max(110, ancho_texto + 26)
        self.badge_estado.setMinimumWidth(ancho_badge)
        if hasattr(self, "widget_estado"):
            self.widget_estado.setMinimumWidth(125 + ancho_badge)

    def ejecutar_aborto(self) -> None:
        self.actualizar_estado(EstadoInstrumentacion.ABORTADO)
        self.vista_prueba.abortar_inmediato()
