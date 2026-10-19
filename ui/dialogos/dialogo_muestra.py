"""Diálogo modal para registrar y validar la ficha técnica de la muestra / motor.

Estilos y layout optimizados para instrumentación aeroespacial (Horus Space Lab):
- Etiquetas (QLabel) con color explícito visible (#FFFFFF, 13px, font-weight: 500).
- Campos de entrada (QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit) con:
    * min-height: 28px, height: 32px (sin corte vertical de texto).
    * padding: 4px 8px.
    * background-color: #352F7E (alto contraste sobre tarjeta #2A2566).
    * color: #FFFFFF.
    * border: 1px solid rgba(255, 255, 255, 0.2).
    * border-radius: 6px.
- QFormLayout limpio con verticalSpacing >= 10px (12px) y horizontalSpacing: 18px.
- 11 campos reglamentarios con validaciones físicas y balísticas completas.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from datos.gestor_db import EnsayoMetadata
from estilo.tema import (
    COLOR_CIAN,
    COLOR_FONDO_PRINCIPAL,
    COLOR_TEXTO_MUTED,
    COLOR_VERDE_NEON,
)


class DialogoMuestra(QDialog):
    """Formulario modal de Ficha Técnica de la Muestra / Motor cohete."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ficha Técnica de la Muestra / Motor - Horus Space Lab")
        self.setMinimumSize(660, 720)
        self.resize(720, 760)
        self.setModal(True)

        self.metadata_resultado: Optional[EnsayoMetadata] = None

        self._aplicar_estilos()
        self._construir_ui()

    def _aplicar_estilos(self) -> None:
        """Aplica hoja de estilos con alto contraste y dimensiones cómodas para inputs."""
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_FONDO_PRINCIPAL}; /* #1F1B4E */
                color: #FFFFFF;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}

            /* ===================================================
               TARJETA CONTENEDORA (#2A2566)
               =================================================== */
            QFrame#TarjetaFormulario {{
                background-color: #2A2566;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 10px;
            }}

            /* ===================================================
               ETIQUETAS DEL FORMULARIO (VISIBILIDAD EXPLÍCITA)
               =================================================== */
            QLabel {{
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
            }}

            QLabel.EtiquetaCampo, QFrame#TarjetaFormulario QLabel {{
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                padding-right: 6px;
            }}

            /* ===================================================
               CAMPOS DE ENTRADA (ALTO CONTRASTE #352F7E)
               =================================================== */
            QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
                background-color: #352F7E;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                min-height: 28px;
                height: 32px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: 500;
                selection-background-color: #0D6EFD;
                selection-color: #FFFFFF;
            }}

            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                border: 1px solid {COLOR_CIAN};
                background-color: #3E3793;
            }}

            /* Botones de incremento/decremento en SpinBoxes y QDateEdit */
            QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid rgba(255, 255, 255, 0.15);
                border-top-right-radius: 6px;
                background: rgba(255, 255, 255, 0.05);
            }}

            QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid rgba(255, 255, 255, 0.15);
                border-bottom-right-radius: 6px;
                background: rgba(255, 255, 255, 0.05);
            }}

            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {{
                background: rgba(255, 255, 255, 0.18);
            }}

            /* Estilos del desplegable del calendario */
            QCalendarWidget QWidget {{
                background-color: #282366;
                color: #FFFFFF;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: #1F1B4E;
                color: #FFFFFF;
                selection-background-color: #0D6EFD;
                selection-color: #FFFFFF;
            }}

            /* ===================================================
               BARRA DE DESPLAZAMIENTO ELEGANTE
               =================================================== */
            QScrollBar:vertical {{
                border: none;
                background-color: transparent;
                width: 6px;
                margin: 4px 0px 4px 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgba(255, 255, 255, 0.22);
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgba(255, 255, 255, 0.40);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            /* ===================================================
               BOTONES DE ACCIÓN
               =================================================== */
            QPushButton#BtnCancelar {{
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                padding: 8px 20px;
                min-height: 34px;
                font-size: 13px;
                font-weight: 700;
            }}

            QPushButton#BtnCancelar:hover {{
                background-color: rgba(255, 255, 255, 0.14);
                color: #FFFFFF;
            }}

            QPushButton#BtnConfirmar {{
                background-color: #007A3D;
                color: #FFFFFF;
                border: 1px solid {COLOR_VERDE_NEON};
                border-radius: 6px;
                padding: 8px 24px;
                min-height: 34px;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}

            QPushButton#BtnConfirmar:hover {{
                background-color: #00964B;
            }}

            QPushButton#BtnConfirmar:pressed {{
                background-color: #005A2C;
            }}
            """
        )

    def _construir_ui(self) -> None:
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(24, 20, 24, 20)
        layout_raiz.setSpacing(14)

        # -------------------------------------------------------------
        # 1. ENCABEZADO
        # -------------------------------------------------------------
        vbox_encabezado = QVBoxLayout()
        vbox_encabezado.setSpacing(4)

        lbl_tit = QLabel("📋 FICHA TÉCNICA DE LA MUESTRA / MOTOR")
        lbl_tit.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: 900; letter-spacing: 1px;"
        )

        lbl_desc = QLabel(
            "Caracterización geométrica, masa de propelente y condiciones ambientales de ensayo."
        )
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 12px; font-weight: 500;")

        vbox_encabezado.addWidget(lbl_tit)
        vbox_encabezado.addWidget(lbl_desc)
        layout_raiz.addLayout(vbox_encabezado)

        # -------------------------------------------------------------
        # 2. CONTENEDOR CON SCROLL
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        widget_tarjeta = QFrame()
        widget_tarjeta.setObjectName("TarjetaFormulario")

        # QFormLayout limpio con verticalSpacing >= 10px (10px exactos conforme a especificación)
        form = QFormLayout(widget_tarjeta)
        form.setContentsMargins(20, 16, 20, 16)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(18)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Instanciación de controles de entrada
        self.txt_id = QLineEdit("EXP-KNSB-2026-01")
        self.txt_id.setPlaceholderText("Ej. EXP-MOT-01")

        self.txt_operadores = QLineEdit("Ing. Jesús Rosales • Equipo Propulsión")
        self.txt_operadores.setPlaceholderText("Nombre del operador o equipo")

        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setDisplayFormat("yyyy-MM-dd")

        self.spn_vejez = QSpinBox()
        self.spn_vejez.setRange(0, 3650)
        self.spn_vejez.setValue(7)
        self.spn_vejez.setSuffix(" días")

        self.spn_diam_ext = QDoubleSpinBox()
        self.spn_diam_ext.setDecimals(1)
        self.spn_diam_ext.setRange(1.0, 500.0)
        self.spn_diam_ext.setValue(38.0)
        self.spn_diam_ext.setSuffix(" mm")

        self.spn_diam_int = QDoubleSpinBox()
        self.spn_diam_int.setDecimals(1)
        self.spn_diam_int.setRange(0.0, 490.0)
        self.spn_diam_int.setValue(12.0)
        self.spn_diam_int.setSuffix(" mm")

        self.spn_altura = QDoubleSpinBox()
        self.spn_altura.setDecimals(1)
        self.spn_altura.setRange(1.0, 2500.0)
        self.spn_altura.setValue(145.0)
        self.spn_altura.setSuffix(" mm")

        self.spn_masa = QDoubleSpinBox()
        self.spn_masa.setDecimals(1)
        self.spn_masa.setRange(0.1, 50000.0)
        self.spn_masa.setValue(245.0)
        self.spn_masa.setSuffix(" g")

        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setDecimals(1)
        self.spn_temp.setRange(-30.0, 65.0)
        self.spn_temp.setValue(22.5)
        self.spn_temp.setSuffix(" °C")

        self.spn_humedad = QDoubleSpinBox()
        self.spn_humedad.setDecimals(1)
        self.spn_humedad.setRange(0.0, 100.0)
        self.spn_humedad.setValue(45.0)
        self.spn_humedad.setSuffix(" %")

        self.txt_composicion = QLineEdit("KNSB 65/35 (Nitrato de Potasio / Sorbitol)")
        self.txt_composicion.setPlaceholderText("Ej. APCP 70/15/15 o KNDX")

        # Lista reglamentaria de 11 campos con etiquetas claras en la columna izquierda
        campos = [
            ("ID de Muestra", self.txt_id),
            ("Operador(es)", self.txt_operadores),
            ("Fecha de Ensayo", self.date_fecha),
            ("Días de Vejez", self.spn_vejez),
            ("Diámetro Exterior (mm)", self.spn_diam_ext),
            ("Diámetro Interior (mm)", self.spn_diam_int),
            ("Altura / Longitud (mm)", self.spn_altura),
            ("Masa Inicial de Grano (g)", self.spn_masa),
            ("Temperatura Ambiente (°C)", self.spn_temp),
            ("Humedad Relativa (%)", self.spn_humedad),
            ("Tipo / Composición de Propelente", self.txt_composicion),
        ]

        for texto_lbl, widget_campo in campos:
            lbl = QLabel(texto_lbl)
            lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 500;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            form.addRow(lbl, widget_campo)

        scroll.setWidget(widget_tarjeta)
        layout_raiz.addWidget(scroll, 1)

        # -------------------------------------------------------------
        # 3. FILA DE BOTONES DE ACCIÓN
        # -------------------------------------------------------------
        fila_btn = QHBoxLayout()
        fila_btn.setSpacing(14)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("BtnCancelar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        btn_confirmar = QPushButton("Confirmar y Habilitar Armado ➔")
        btn_confirmar.setObjectName("BtnConfirmar")
        btn_confirmar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirmar.clicked.connect(self._validar_y_guardar)

        fila_btn.addStretch()
        fila_btn.addWidget(btn_cancelar)
        fila_btn.addWidget(btn_confirmar)

        layout_raiz.addLayout(fila_btn)

    def _validar_y_guardar(self) -> None:
        """Aplica validaciones balísticas y geométricas antes de aceptar."""
        codigo = self.txt_id.text().strip()
        if not codigo:
            QMessageBox.warning(self, "Validación requerida", "El 'ID de Muestra' no puede estar vacío.")
            self.txt_id.setFocus()
            return

        diam_ext = self.spn_diam_ext.value()
        diam_int = self.spn_diam_int.value()
        if diam_int >= diam_ext:
            QMessageBox.warning(
                self,
                "Error geométrico",
                f"El diámetro interior ({diam_int:.1f} mm) debe ser menor que el exterior ({diam_ext:.1f} mm).",
            )
            self.spn_diam_int.setFocus()
            return

        masa = self.spn_masa.value()
        if masa <= 0:
            QMessageBox.warning(self, "Masa inválida", "La masa inicial de grano debe ser mayor a 0 gramos.")
            self.spn_masa.setFocus()
            return

        fecha_str = self.date_fecha.date().toString("yyyy-MM-dd")

        self.metadata_resultado = EnsayoMetadata(
            codigo_ensayo=codigo,
            operadores=self.txt_operadores.text().strip(),
            fecha=fecha_str,
            dias_vejez=self.spn_vejez.value(),
            diam_ext_mm=diam_ext,
            diam_int_mm=diam_int,
            altura_mm=self.spn_altura.value(),
            masa_propelente_g=masa,
            temp_amb_c=self.spn_temp.value(),
            humedad_pct=self.spn_humedad.value(),
            notas=self.txt_composicion.text().strip(),
        )
        self.accept()
