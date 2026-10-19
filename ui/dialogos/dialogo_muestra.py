"""Diálogo modal para registrar y validar las características de la muestra previa al disparo."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from datos.gestor_db import EnsayoMetadata
from estilo.tema import (
    COLOR_ACENTO_CRITICO,
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


class DialogoMuestra(QDialog):
    """Formulario de validación de grano de propelente y condiciones ambientales."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Caracterización de la Muestra - Horus Space Lab")
        self.setFixedSize(620, 560)
        self.setModal(True)

        self.metadata_resultado: Optional[EnsayoMetadata] = None

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_FONDO_PRINCIPAL};
                color: {COLOR_TEXTO_PRINCIPAL};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {COLOR_PANEL_CLARO};
                color: #FFFFFF;
                border: 1px solid {COLOR_BORDE_NORMAL};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {COLOR_CIAN};
            }}
            QLabel {{
                color: {COLOR_TEXTO_SECUNDARIO};
                font-size: 12px;
                font-weight: 700;
            }}
            """
        )

        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Encabezado
        lbl_tit = QLabel("📋 FICHA TÉCNICA DE LA MUESTRA / MOTOR")
        lbl_tit.setStyleSheet(
            f"color: {COLOR_TEXTO_PRINCIPAL}; font-size: 16px; font-weight: 900; letter-spacing: 1px;"
        )
        lbl_desc = QLabel("Ingresa las propiedades del grano y condiciones ambientales antes de armar el sistema.")
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 11px;")
        layout.addWidget(lbl_tit)
        layout.addWidget(lbl_desc)

        # Contenedor del formulario
        tarjeta = QFrame()
        tarjeta.setStyleSheet(
            f"background-color: {COLOR_PANEL_MEDIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 10px; padding: 14px;"
        )
        grid = QGridLayout(tarjeta)
        grid.setSpacing(12)

        # Campos
        self.txt_codigo = QLineEdit("EXP-MOT-2026-01")
        self.txt_operadores = QLineEdit("Equipo de Propulsión HSL")

        self.spn_vejez = QSpinBox()
        self.spn_vejez.setRange(0, 3650)
        self.spn_vejez.setValue(7)
        self.spn_vejez.setSuffix(" días")

        self.spn_masa = QDoubleSpinBox()
        self.spn_masa.setRange(0.1, 50000.0)
        self.spn_masa.setValue(220.0)
        self.spn_masa.setSuffix(" g")

        self.spn_diam_ext = QDoubleSpinBox()
        self.spn_diam_ext.setRange(1.0, 500.0)
        self.spn_diam_ext.setValue(38.0)
        self.spn_diam_ext.setSuffix(" mm")

        self.spn_diam_int = QDoubleSpinBox()
        self.spn_diam_int.setRange(0.0, 490.0)
        self.spn_diam_int.setValue(12.0)
        self.spn_diam_int.setSuffix(" mm")

        self.spn_altura = QDoubleSpinBox()
        self.spn_altura.setRange(1.0, 2000.0)
        self.spn_altura.setValue(140.0)
        self.spn_altura.setSuffix(" mm")

        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setRange(-20.0, 60.0)
        self.spn_temp.setValue(22.0)
        self.spn_temp.setSuffix(" °C")

        self.spn_humedad = QDoubleSpinBox()
        self.spn_humedad.setRange(0.0, 100.0)
        self.spn_humedad.setValue(45.0)
        self.spn_humedad.setSuffix(" %")

        self.txt_notas = QLineEdit("Propelente KNSB formulación estándar 65/35")

        grid.addWidget(QLabel("Código Ensayo:"), 0, 0)
        grid.addWidget(self.txt_codigo, 0, 1)

        grid.addWidget(QLabel("Operador(es):"), 1, 0)
        grid.addWidget(self.txt_operadores, 1, 1)

        grid.addWidget(QLabel("Días de Vejez:"), 2, 0)
        grid.addWidget(self.spn_vejez, 2, 1)

        grid.addWidget(QLabel("Masa Propelente:"), 3, 0)
        grid.addWidget(self.spn_masa, 3, 1)

        grid.addWidget(QLabel("Diámetro Exterior:"), 4, 0)
        grid.addWidget(self.spn_diam_ext, 4, 1)

        grid.addWidget(QLabel("Diámetro Interior (Núcleo):"), 5, 0)
        grid.addWidget(self.spn_diam_int, 5, 1)

        grid.addWidget(QLabel("Longitud de Grano:"), 6, 0)
        grid.addWidget(self.spn_altura, 6, 1)

        grid.addWidget(QLabel("Temp. Ambiente:"), 7, 0)
        grid.addWidget(self.spn_temp, 7, 1)

        grid.addWidget(QLabel("Humedad Relativa:"), 8, 0)
        grid.addWidget(self.spn_humedad, 8, 1)

        grid.addWidget(QLabel("Notas / Formulación:"), 9, 0)
        grid.addWidget(self.txt_notas, 9, 1)

        layout.addWidget(tarjeta)

        # Botones de Acción
        fila_btn = QHBoxLayout()
        fila_btn.setSpacing(12)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.08); color: {COLOR_TEXTO_SECUNDARIO}; border: 1px solid {COLOR_BORDE_NORMAL}; border-radius: 6px; padding: 8px 18px; font-weight: 700;"
        )
        btn_cancelar.clicked.connect(self.reject)

        btn_confirmar = QPushButton("Confirmar y Habilitar Armado ➔")
        btn_confirmar.setStyleSheet(
            f"background: #007A3D; color: #FFFFFF; border: 1px solid {COLOR_VERDE_NEON}; border-radius: 6px; padding: 8px 22px; font-weight: 800; font-size: 13px;"
        )
        btn_confirmar.clicked.connect(self._validar_y_guardar)

        fila_btn.addStretch()
        fila_btn.addWidget(btn_cancelar)
        fila_btn.addWidget(btn_confirmar)
        layout.addLayout(fila_btn)

    def _validar_y_guardar(self) -> None:
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            QMessageBox.warning(self, "Validación requerida", "El código de ensayo no puede estar vacío.")
            return

        diam_ext = self.spn_diam_ext.value()
        diam_int = self.spn_diam_int.value()
        if diam_int >= diam_ext:
            QMessageBox.warning(
                self,
                "Error geométrico",
                f"El diámetro interior ({diam_int} mm) debe ser menor que el exterior ({diam_ext} mm).",
            )
            return

        masa = self.spn_masa.value()
        if masa <= 0:
            QMessageBox.warning(self, "Masa inválida", "La masa de propelente debe ser mayor a 0 gramos.")
            return

        self.metadata_resultado = EnsayoMetadata(
            codigo_ensayo=codigo,
            operadores=self.txt_operadores.text().strip(),
            dias_vejez=self.spn_vejez.value(),
            diam_ext_mm=diam_ext,
            diam_int_mm=diam_int,
            altura_mm=self.spn_altura.value(),
            masa_propelente_g=masa,
            temp_amb_c=self.spn_temp.value(),
            humedad_pct=self.spn_humedad.value(),
            notas=self.txt_notas.text().strip(),
        )
        self.accept()
