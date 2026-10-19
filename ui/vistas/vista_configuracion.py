"""Vista de configuración del sistema DAQ, enlace serie y parámetros de filtrado.

Implementa:
- Selección interactiva entre modo SIMULACIÓN y HARDWARE REAL (ESP32).
- Escaneo y selección de puertos serie (/dev/cu.usb*, COM*) con baudrate configurable.
- Ajuste de frecuencia de muestreo (Hz), umbrales de ignición y pre-trigger.
- Parámetros del filtro digital IIR (frecuencia de corte fc y factor alpha).
- Persistencia de preferencias en formato JSON.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from comunicacion.driver_serial import DriverSerialESP32
from estilo.tema import (
    COLOR_BORDE_NORMAL,
    COLOR_CIAN,
    COLOR_FONDO_PRINCIPAL,
    COLOR_PANEL_CLARO,
    COLOR_PANEL_MEDIO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_PRINCIPAL,
    COLOR_TEXTO_SECUNDARIO,
    COLOR_VERDE_NEON,
)


class VistaConfiguracion(QWidget):
    """Panel de configuración centralizada de hardware y adquisición."""

    configuracion_guardada = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ruta_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "daq_config.json",
        )

        self._construir_ui()
        self._cargar_configuracion()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Encabezado
        vbox_tit = QVBoxLayout()
        vbox_tit.setSpacing(2)
        lbl_tit = QLabel("⚙️ CONFIGURACIÓN DEL SISTEMA Y TELEMETRÍA")
        lbl_tit.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 900; letter-spacing: 1px;"
        )
        lbl_desc = QLabel("Parámetros de enlaces de comunicación, tasa de muestreo, filtros IIR y pre-trigger.")
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 11px;")
        vbox_tit.addWidget(lbl_tit)
        vbox_tit.addWidget(lbl_desc)
        layout.addLayout(vbox_tit)

        # Fila de tarjetas: Hardware / Comunicaciones a la izquierda, Filtros y DAQ a la derecha
        fila_tarjetas = QHBoxLayout()
        fila_tarjetas.setSpacing(14)

        # ------------------------------------
        # TARJETA 1: CANAL DE TELEMETRÍA Y PUERTOS
        # ------------------------------------
        t1 = QFrame()
        t1.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px; padding: 12px;"
        )
        vbox_t1 = QVBoxLayout(t1)
        vbox_t1.setSpacing(12)

        lbl_t1_tit = QLabel("CANAL DE TELEMETRÍA (BACKEND)")
        lbl_t1_tit.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;")
        vbox_t1.addWidget(lbl_t1_tit)

        self.rb_simulacion = QRadioButton("Modo SIMULACIÓN (Curva sintética a 200 Hz)")
        self.rb_simulacion.setChecked(True)
        self.rb_simulacion.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12px;")

        self.rb_hardware = QRadioButton("Modo HARDWARE REAL (Microcontrolador ESP32)")
        self.rb_hardware.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12px;")

        vbox_t1.addWidget(self.rb_simulacion)
        vbox_t1.addWidget(self.rb_hardware)

        # Grid de parámetros serie
        grid_serie = QGridLayout()
        grid_serie.setSpacing(10)

        grid_serie.addWidget(QLabel("Puerto Serie:"), 0, 0)
        fila_puerto = QHBoxLayout()
        self.cb_puerto = QComboBox()
        self.cb_puerto.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        btn_refresh_puertos = QPushButton("🔄")
        btn_refresh_puertos.setToolTip("Escanear puertos serie conectados")
        btn_refresh_puertos.setFixedWidth(36)
        btn_refresh_puertos.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF;")
        btn_refresh_puertos.clicked.connect(self._escanear_puertos)
        fila_puerto.addWidget(self.cb_puerto)
        fila_puerto.addWidget(btn_refresh_puertos)
        grid_serie.addLayout(fila_puerto, 0, 1)

        grid_serie.addWidget(QLabel("Baudrate:"), 1, 0)
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["115200", "230400", "460800", "921600"])
        self.cb_baud.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        grid_serie.addWidget(self.cb_baud, 1, 1)

        vbox_t1.addLayout(grid_serie)
        vbox_t1.addStretch()
        fila_tarjetas.addWidget(t1, 1)

        # ------------------------------------
        # TARJETA 2: PARÁMETROS DAQ Y FILTRO IIR
        # ------------------------------------
        t2 = QFrame()
        t2.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 8px; padding: 12px;"
        )
        vbox_t2 = QVBoxLayout(t2)
        vbox_t2.setSpacing(12)

        lbl_t2_tit = QLabel("PARÁMETROS DE MUESTREO Y FILTRO DIGITAL")
        lbl_t2_tit.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;")
        vbox_t2.addWidget(lbl_t2_tit)

        grid_daq = QGridLayout()
        grid_daq.setSpacing(10)

        grid_daq.addWidget(QLabel("Frecuencia Muestreo:"), 0, 0)
        self.spn_fs = QSpinBox()
        self.spn_fs.setRange(50, 1000)
        self.spn_fs.setValue(200)
        self.spn_fs.setSuffix(" Hz")
        self.spn_fs.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        grid_daq.addWidget(self.spn_fs, 0, 1)

        grid_daq.addWidget(QLabel("Filtro IIR (Frec. Corte):"), 1, 0)
        self.spn_fc = QDoubleSpinBox()
        self.spn_fc.setRange(1.0, 100.0)
        self.spn_fc.setValue(15.0)
        self.spn_fc.setSuffix(" Hz")
        self.spn_fc.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        grid_daq.addWidget(self.spn_fc, 1, 1)

        grid_daq.addWidget(QLabel("Pre-trigger (Buffer):"), 2, 0)
        self.spn_pretrigger = QDoubleSpinBox()
        self.spn_pretrigger.setRange(0.5, 10.0)
        self.spn_pretrigger.setValue(2.0)
        self.spn_pretrigger.setSuffix(" s")
        self.spn_pretrigger.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        grid_daq.addWidget(self.spn_pretrigger, 2, 1)

        grid_daq.addWidget(QLabel("Umbral Ignición:"), 3, 0)
        self.spn_umbral_ign = QDoubleSpinBox()
        self.spn_umbral_ign.setRange(1.0, 50.0)
        self.spn_umbral_ign.setValue(15.0)
        self.spn_umbral_ign.setSuffix(" N")
        self.spn_umbral_ign.setStyleSheet(f"background: {COLOR_PANEL_CLARO}; color: #FFFFFF; padding: 5px;")
        grid_daq.addWidget(self.spn_umbral_ign, 3, 1)

        vbox_t2.addLayout(grid_daq)
        vbox_t2.addStretch()
        fila_tarjetas.addWidget(t2, 1)

        layout.addLayout(fila_tarjetas)

        # Botón Guardar al pie
        fila_btn = QHBoxLayout()
        self.btn_guardar = QPushButton("💾 Guardar y Aplicar Configuración")
        self.btn_guardar.setStyleSheet(
            f"background: #007A3D; color: #FFFFFF; border: 1px solid {COLOR_VERDE_NEON}; border-radius: 6px; padding: 8px 24px; font-weight: 800; font-size: 13px;"
        )
        self.btn_guardar.clicked.connect(self._guardar_configuracion)
        fila_btn.addStretch()
        fila_btn.addWidget(self.btn_guardar)
        layout.addLayout(fila_btn)

        layout.addStretch()

        self._escanear_puertos()

    def _escanear_puertos(self) -> None:
        puertos = DriverSerialESP32.listar_puertos_disponibles()
        self.cb_puerto.clear()
        if puertos:
            self.cb_puerto.addItems(puertos)
        else:
            self.cb_puerto.addItem("No se detectaron puertos serie")

    def _guardar_configuracion(self) -> None:
        cfg = {
            "modo": "simulacion" if self.rb_simulacion.isChecked() else "serial",
            "puerto": self.cb_puerto.currentText(),
            "baudrate": int(self.cb_baud.currentText()),
            "fs_hz": self.spn_fs.value(),
            "fc_hz": self.spn_fc.value(),
            "pretrigger_s": self.spn_pretrigger.value(),
            "umbral_ignicion_n": self.spn_umbral_ign.value(),
        }

        os.makedirs(os.path.dirname(self.ruta_cfg), exist_ok=True)
        try:
            with open(self.ruta_cfg, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            self.configuracion_guardada.emit(cfg)
            QMessageBox.information(self, "Configuración Aplicada", "Los parámetros del sistema se han guardado exitosamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración: {e}")

    def _cargar_configuracion(self) -> None:
        if os.path.exists(self.ruta_cfg):
            try:
                with open(self.ruta_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("modo") == "serial":
                    self.rb_hardware.setChecked(True)
                else:
                    self.rb_simulacion.setChecked(True)

                self.spn_fs.setValue(cfg.get("fs_hz", 200))
                self.spn_fc.setValue(cfg.get("fc_hz", 15.0))
                self.spn_pretrigger.setValue(cfg.get("pretrigger_s", 2.0))
                self.spn_umbral_ign.setValue(cfg.get("umbral_ignicion_n", 15.0))
            except Exception:
                pass
