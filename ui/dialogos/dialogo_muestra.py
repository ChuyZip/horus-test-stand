"""Diálogo modal para registrar y validar la ficha técnica de la muestra / motor.

Estilos y layout optimizados para instrumentación aeroespacial (Horus Space Lab):
- Etiquetas (QLabel) con color explícito visible (#FFFFFF, 13px, font-weight: 500).
- Campos de entrada (QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox) con:
    * min-height: 28px, height: 32px (sin corte vertical de texto).
    * padding: 4px 8px.
    * background-color: #352F7E (alto contraste sobre tarjeta #2A2566).
    * color: #FFFFFF.
    * border: 1px solid rgba(255, 255, 255, 0.2).
    * border-radius: 6px.
- Unidades métricas fijas a la derecha de los campos (no interfieren con el cursor ni con el texto editable).
- QFormLayout limpio con verticalSpacing: 10px y horizontalSpacing: 18px.
- Contenedor en QScrollArea con barra horizontal desactivada y barra vertical estilizada.
- Validación estricta contra campos vacíos, corruptos o incompletos con resaltado en rojo (#BF3938)
  y restauración reactiva inmediata en cuanto el usuario ingresa un valor válido.
- 13 campos reglamentarios (incluyendo Geometría de Grano y Cluster de Motores).
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    QSizePolicy,
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

GEOMETRIAS_GRANO = [
    "BATES (Cilíndrico con núcleo perforado)",
    "Finocyl (Núcleo estrellado / aletas)",
    "End-Burning (Combustión frontal / cigarrillo)",
    "C-Slot (Ranura en C)",
    "Moon Burner (Núcleo excéntrico)",
    "Tubular / Externo-Interno",
]

CONFIGURACIONES_CLUSTER = [
    "1x (Motor individual / Monomotor)",
    "2x (Cluster dual)",
    "3x (Cluster triangular)",
    "4x (Cluster cuádruple)",
    "Personalizado (con número de motores activos)",
]

# Estilo QSS para resaltar campos con error de validación
ESTILO_BORDE_ERROR = (
    "border: 1.5px solid #BF3938; background-color: #352F7E; color: #FFFFFF; border-radius: 6px;"
)


class DialogoMuestra(QDialog):
    """Formulario modal de Ficha Técnica de la Muestra / Motor cohete."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        meta_inicial: Optional[EnsayoMetadata] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ficha Técnica de la Muestra / Motor - Horus Space Lab")
        self.setMinimumSize(680, 760)
        self.resize(740, 820)
        self.setModal(True)

        self.metadata_resultado: Optional[EnsayoMetadata] = None
        self._meta_inicial = meta_inicial
        self._campos_con_error: set[QWidget] = set()

        self._aplicar_estilos()
        self._construir_ui()
        if self._meta_inicial:
            self._cargar_datos_iniciales(self._meta_inicial)

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
            QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
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

            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
                border: 1px solid {COLOR_CIAN};
                background-color: #3E3793;
            }}

            /* Estilos específicos de QComboBox */
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid rgba(255, 255, 255, 0.15);
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background: rgba(255, 255, 255, 0.05);
            }}

            QComboBox::drop-down:hover {{
                background: rgba(255, 255, 255, 0.18);
            }}

            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #FFFFFF;
                margin-right: 2px;
            }}

            QComboBox QAbstractItemView {{
                background-color: #2A2566;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                selection-background-color: #0D6EFD;
                selection-color: #FFFFFF;
                outline: none;
                padding: 4px;
            }}

            QComboBox QAbstractItemView::item {{
                min-height: 28px;
                padding: 4px 8px;
            }}

            QComboBox QAbstractItemView::item:hover {{
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

    def _crear_campo_con_unidad(self, widget: QWidget, unidad: str) -> QWidget:
        """Crea un contenedor con el campo editable y una etiqueta fija de unidad a la derecha."""
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(widget, 1)

        lbl_unidad = QLabel(unidad)
        lbl_unidad.setStyleSheet(
            "color: rgba(255, 255, 255, 0.75); font-size: 12px; font-weight: 700; min-width: 32px;"
        )
        lbl_unidad.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl_unidad)
        return contenedor

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
            "Caracterización geométrica, configuración cluster, masa de propelente y condiciones ambientales de ensayo."
        )
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXTO_MUTED}; font-size: 12px; font-weight: 500;")

        vbox_encabezado.addWidget(lbl_tit)
        vbox_encabezado.addWidget(lbl_desc)
        layout_raiz.addLayout(vbox_encabezado)

        # -------------------------------------------------------------
        # 2. CONTENEDOR CON SCROLL (SIN BARRA HORIZONTAL)
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: transparent;")

        widget_tarjeta = QFrame()
        widget_tarjeta.setObjectName("TarjetaFormulario")
        widget_tarjeta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # QFormLayout limpio con verticalSpacing: 10px y horizontalSpacing: 18px
        form = QFormLayout(widget_tarjeta)
        form.setContentsMargins(20, 16, 20, 16)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(18)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # -------------------------------------------------------------
        # INSTANCIACIÓN DE CONTROLES DE ENTRADA
        # -------------------------------------------------------------
        self.txt_id = QLineEdit("EXP-KNSB-2026-01")
        self.txt_id.setPlaceholderText("Ej. EXP-MOT-01")

        self.txt_operadores = QLineEdit("Ing. Jesús Rosales • Equipo Propulsión")
        self.txt_operadores.setPlaceholderText("Nombre del operador o equipo")

        # Fecha con calendario desplegable y formato estricto yyyy-MM-dd
        self.date_fecha = QDateEdit()
        self.date_fecha.setCalendarPopup(True)
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setDisplayFormat("yyyy-MM-dd")

        # Controles numéricos con rango amplio y sin sufijo interno para evitar textos residuales
        self.spn_vejez = QSpinBox()
        self.spn_vejez.setRange(0, 3650)
        self.spn_vejez.setValue(7)

        # Campo A: Tipo de Geometría de Grano (QComboBox estilizado)
        self.combo_geometria = QComboBox()
        self.combo_geometria.addItems(GEOMETRIAS_GRANO)
        self.combo_geometria.setCurrentText("BATES (Cilíndrico con núcleo perforado)")

        # Campo B: Configuración Cluster de Motores (QComboBox + QSpinBox descriptivo para personalizado)
        self.combo_cluster = QComboBox()
        self.combo_cluster.addItems(CONFIGURACIONES_CLUSTER)
        self.combo_cluster.setCurrentIndex(0)

        self.spn_cluster_personalizado = QSpinBox()
        self.spn_cluster_personalizado.setRange(1, 64)
        self.spn_cluster_personalizado.setValue(5)
        self.spn_cluster_personalizado.setPrefix("N = ")
        self.spn_cluster_personalizado.setSuffix(" motores")
        self.spn_cluster_personalizado.setVisible(False)

        def _al_cambiar_cluster(texto: str) -> None:
            self.spn_cluster_personalizado.setVisible("Personalizado" in texto)

        self.combo_cluster.currentTextChanged.connect(_al_cambiar_cluster)

        widget_cluster = QWidget()
        layout_cluster = QHBoxLayout(widget_cluster)
        layout_cluster.setContentsMargins(0, 0, 0, 0)
        layout_cluster.setSpacing(8)
        layout_cluster.addWidget(self.combo_cluster, 3)
        layout_cluster.addWidget(self.spn_cluster_personalizado, 2)

        self.spn_diam_ext = QDoubleSpinBox()
        self.spn_diam_ext.setDecimals(1)
        self.spn_diam_ext.setRange(0.0, 500.0)
        self.spn_diam_ext.setValue(38.0)

        self.spn_diam_int = QDoubleSpinBox()
        self.spn_diam_int.setDecimals(1)
        self.spn_diam_int.setRange(0.0, 490.0)
        self.spn_diam_int.setValue(12.0)

        self.spn_altura = QDoubleSpinBox()
        self.spn_altura.setDecimals(1)
        self.spn_altura.setRange(0.0, 2500.0)
        self.spn_altura.setValue(145.0)

        self.spn_masa = QDoubleSpinBox()
        self.spn_masa.setDecimals(1)
        self.spn_masa.setRange(0.0, 50000.0)
        self.spn_masa.setValue(245.0)

        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setDecimals(1)
        self.spn_temp.setRange(-50.0, 80.0)
        self.spn_temp.setValue(22.5)

        self.spn_humedad = QDoubleSpinBox()
        self.spn_humedad.setDecimals(1)
        self.spn_humedad.setRange(0.0, 100.0)
        self.spn_humedad.setValue(45.0)

        self.txt_composicion = QLineEdit("KNSB 65/35 (Nitrato de Potasio / Sorbitol)")
        self.txt_composicion.setPlaceholderText("Ej. APCP 70/15/15 o KNDX")

        # Conectar eventos de cambio para restaurar estilo normal al interactuar
        self._conectar_senales_limpieza()

        # Lista reglamentaria de 13 campos con etiquetas claras en la columna izquierda y unidades a la derecha
        campos = [
            ("ID de Muestra", self.txt_id),
            ("Operador(es)", self.txt_operadores),
            ("Fecha de Ensayo", self.date_fecha),
            ("Días de Vejez", self._crear_campo_con_unidad(self.spn_vejez, "días")),
            ("Tipo de Geometría de Grano", self.combo_geometria),
            ("Configuración Cluster de Motores", widget_cluster),
            ("Diámetro Exterior", self._crear_campo_con_unidad(self.spn_diam_ext, "mm")),
            ("Diámetro Interior", self._crear_campo_con_unidad(self.spn_diam_int, "mm")),
            ("Altura / Longitud", self._crear_campo_con_unidad(self.spn_altura, "mm")),
            ("Masa Inicial de Grano", self._crear_campo_con_unidad(self.spn_masa, "g")),
            ("Temperatura Ambiente", self._crear_campo_con_unidad(self.spn_temp, "°C")),
            ("Humedad Relativa", self._crear_campo_con_unidad(self.spn_humedad, "%")),
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

    def _conectar_senales_limpieza(self) -> None:
        """Conecta eventos de edición para restaurar el borde normal al interactuar con el campo."""
        self.txt_id.textChanged.connect(lambda: self._limpiar_campo(self.txt_id))
        self.txt_operadores.textChanged.connect(lambda: self._limpiar_campo(self.txt_operadores))

        self.date_fecha.dateChanged.connect(lambda: self._limpiar_campo(self.date_fecha))
        if hasattr(self.date_fecha, "lineEdit") and self.date_fecha.lineEdit():
            self.date_fecha.lineEdit().textEdited.connect(lambda: self._limpiar_campo(self.date_fecha))

        self.spn_vejez.textChanged.connect(lambda: self._limpiar_campo(self.spn_vejez))
        self.spn_vejez.valueChanged.connect(lambda: self._limpiar_campo(self.spn_vejez))

        self.combo_geometria.currentTextChanged.connect(lambda: self._limpiar_campo(self.combo_geometria))
        self.combo_cluster.currentTextChanged.connect(lambda: self._limpiar_campo(self.combo_cluster))

        self.spn_cluster_personalizado.textChanged.connect(lambda: self._limpiar_campo(self.spn_cluster_personalizado))
        self.spn_cluster_personalizado.valueChanged.connect(lambda: self._limpiar_campo(self.spn_cluster_personalizado))

        self.spn_diam_ext.textChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_ext), self._limpiar_campo(self.spn_diam_int))
        )
        self.spn_diam_ext.valueChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_ext), self._limpiar_campo(self.spn_diam_int))
        )

        self.spn_diam_int.textChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_int), self._limpiar_campo(self.spn_diam_ext))
        )
        self.spn_diam_int.valueChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_int), self._limpiar_campo(self.spn_diam_ext))
        )

        self.spn_altura.textChanged.connect(lambda: self._limpiar_campo(self.spn_altura))
        self.spn_altura.valueChanged.connect(lambda: self._limpiar_campo(self.spn_altura))

        self.spn_masa.textChanged.connect(lambda: self._limpiar_campo(self.spn_masa))
        self.spn_masa.valueChanged.connect(lambda: self._limpiar_campo(self.spn_masa))

        self.spn_temp.textChanged.connect(lambda: self._limpiar_campo(self.spn_temp))
        self.spn_temp.valueChanged.connect(lambda: self._limpiar_campo(self.spn_temp))

        self.spn_humedad.textChanged.connect(lambda: self._limpiar_campo(self.spn_humedad))
        self.spn_humedad.valueChanged.connect(lambda: self._limpiar_campo(self.spn_humedad))

        self.txt_composicion.textChanged.connect(lambda: self._limpiar_campo(self.txt_composicion))

    def _limpiar_campo(self, widget: QWidget) -> None:
        """Restaura el estilo y borde translúcido normal de un control específico."""
        if widget in self._campos_con_error:
            widget.setStyleSheet("")
            self._campos_con_error.discard(widget)

    @staticmethod
    def _extraer_valor_spinbox(spn: QSpinBox | QDoubleSpinBox) -> tuple[bool, float]:
        """Extrae el valor numérico asegurando que el campo no esté vacío ni corrupto con solo sufijos o texto.

        Returns:
            tuple[bool, float]: (es_valido, valor_numerico)
        """
        if hasattr(spn, "lineEdit") and spn.lineEdit():
            txt = spn.lineEdit().text().strip()
        else:
            txt = spn.cleanText().strip()

        if not txt:
            return (False, 0.0)

        # Buscar si contiene al menos un valor numérico válido (entero o decimal)
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", txt)
        if not match:
            return (False, 0.0)

        try:
            val = float(match.group(0).replace(",", "."))
            return (True, val)
        except ValueError:
            return (False, 0.0)

    def _obtener_valor_cluster(self) -> str:
        """Determina el descriptor del cluster según la opción seleccionada."""
        texto = self.combo_cluster.currentText().strip()
        if "Personalizado" in texto:
            ok, val = self._extraer_valor_spinbox(self.spn_cluster_personalizado)
            n = int(val) if ok and val > 0 else 5
            return f"Personalizado ({n}x)"
        return texto

    def obtener_datos(self) -> dict[str, Any]:
        """Retorna los datos del formulario como diccionario serializable."""
        if self.metadata_resultado:
            return asdict(self.metadata_resultado)

        raw_fecha = self.date_fecha.text().strip()
        qdate_parsed = QDate.fromString(raw_fecha, "yyyy-MM-dd")
        fecha_str = (
            qdate_parsed.toString("yyyy-MM-dd")
            if qdate_parsed.isValid()
            else self.date_fecha.date().toString("yyyy-MM-dd")
        )

        _, val_vejez = self._extraer_valor_spinbox(self.spn_vejez)
        _, val_ext = self._extraer_valor_spinbox(self.spn_diam_ext)
        _, val_int = self._extraer_valor_spinbox(self.spn_diam_int)
        _, val_altura = self._extraer_valor_spinbox(self.spn_altura)
        _, val_masa = self._extraer_valor_spinbox(self.spn_masa)
        _, val_temp = self._extraer_valor_spinbox(self.spn_temp)
        _, val_hum = self._extraer_valor_spinbox(self.spn_humedad)

        return {
            "codigo_ensayo": self.txt_id.text().strip(),
            "operadores": self.txt_operadores.text().strip(),
            "fecha": fecha_str,
            "dias_vejez": int(val_vejez),
            "diam_ext_mm": val_ext,
            "diam_int_mm": val_int,
            "altura_mm": val_altura,
            "masa_propelente_g": val_masa,
            "temp_amb_c": val_temp,
            "humedad_pct": val_hum,
            "geometria_grano": self.combo_geometria.currentText().strip(),
            "cluster_motores": self._obtener_valor_cluster(),
            "notas": self.txt_composicion.text().strip(),
        }

    @property
    def datos(self) -> dict[str, Any]:
        """Propiedad de conveniencia para acceder al diccionario de resultados."""
        return self.obtener_datos()

    def _cargar_datos_iniciales(self, meta: EnsayoMetadata) -> None:
        """Precarga los datos de un ensayo existente en los campos del formulario."""
        if meta.codigo_ensayo:
            self.txt_id.setText(meta.codigo_ensayo)
        if meta.operadores:
            self.txt_operadores.setText(meta.operadores)
        if meta.fecha:
            raw = meta.fecha[:10]
            f = QDate.fromString(raw, "yyyy-MM-dd")
            if f.isValid():
                self.date_fecha.setDate(f)
        self.spn_vejez.setValue(meta.dias_vejez)
        if meta.diam_ext_mm > 0:
            self.spn_diam_ext.setValue(meta.diam_ext_mm)
        if meta.diam_int_mm >= 0:
            self.spn_diam_int.setValue(meta.diam_int_mm)
        if meta.altura_mm > 0:
            self.spn_altura.setValue(meta.altura_mm)
        if meta.masa_propelente_g > 0:
            self.spn_masa.setValue(meta.masa_propelente_g)
        self.spn_temp.setValue(meta.temp_amb_c)
        self.spn_humedad.setValue(meta.humedad_pct)
        if meta.notas:
            self.txt_composicion.setText(meta.notas)

        # Geometría de grano
        idx_geom = self.combo_geometria.findText(meta.geometria_grano)
        if idx_geom >= 0:
            self.combo_geometria.setCurrentIndex(idx_geom)
        else:
            self.combo_geometria.setCurrentText(meta.geometria_grano)

        # Configuración cluster de motores
        cluster_str = str(meta.cluster_motores)
        idx_cluster = self.combo_cluster.findText(cluster_str)
        if idx_cluster >= 0:
            self.combo_cluster.setCurrentIndex(idx_cluster)
        elif "Personalizado" in cluster_str:
            self.combo_cluster.setCurrentIndex(4)
            self.spn_cluster_personalizado.setValue(meta.num_motores)

    def validar_formulario(self) -> tuple[bool, list[str]]:
        """Valida rigurosamente todos los campos conforme a las reglas balísticas y físicas.

        Returns:
            tuple[bool, list[str]]: (es_valido, lista_mensajes_faltantes)
        """
        errores: list[str] = []
        campos_invalidos: list[QWidget] = []

        # 1. ID de Muestra: texto no vacío (strip())
        if not self.txt_id.text().strip():
            errores.append("ID de Muestra")
            campos_invalidos.append(self.txt_id)

        # 2. Operador(es): texto no vacío
        if not self.txt_operadores.text().strip():
            errores.append("Operador(es)")
            campos_invalidos.append(self.txt_operadores)

        # 3. Fecha de Ensayo: fecha válida y no corrupta (ej. no permite '2026--21')
        raw_fecha = self.date_fecha.text().strip()
        es_fecha_formato = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", raw_fecha))
        qdate_parsed = QDate.fromString(raw_fecha, "yyyy-MM-dd") if es_fecha_formato else QDate()

        if not es_fecha_formato or not qdate_parsed.isValid() or not self.date_fecha.hasAcceptableInput():
            errores.append("Fecha de Ensayo (formato AAAA-MM-DD inválido o incompleto)")
            campos_invalidos.append(self.date_fecha)

        # 4. Días de Vejez: número entero >= 0 (no solo la palabra 'días' ni vacío)
        ok_vejez, val_vejez = self._extraer_valor_spinbox(self.spn_vejez)
        if not ok_vejez or val_vejez < 0:
            errores.append("Días de Vejez (debe ser un número >= 0)")
            campos_invalidos.append(self.spn_vejez)

        # 5. Tipo de Geometría de Grano: elemento seleccionado válido
        if not self.combo_geometria.currentText().strip():
            errores.append("Tipo de Geometría de Grano")
            campos_invalidos.append(self.combo_geometria)

        # 6. Configuración Cluster de Motores: elemento seleccionado válido
        texto_cluster = self.combo_cluster.currentText().strip()
        if not texto_cluster:
            errores.append("Configuración Cluster de Motores")
            campos_invalidos.append(self.combo_cluster)
        elif "Personalizado" in texto_cluster:
            ok_custom, val_custom = self._extraer_valor_spinbox(self.spn_cluster_personalizado)
            if not ok_custom or val_custom <= 0:
                errores.append("Configuración Cluster de Motores (número de motores debe ser mayor a 0)")
                campos_invalidos.append(self.spn_cluster_personalizado)

        # 7. Diámetro Exterior: número decimal > 0
        ok_ext, val_ext = self._extraer_valor_spinbox(self.spn_diam_ext)
        if not ok_ext or val_ext <= 0.0:
            errores.append("Diámetro Exterior (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_diam_ext)

        # 8. Diámetro Interior: número decimal >= 0 y estrictamente menor que Diámetro Exterior
        ok_int, val_int = self._extraer_valor_spinbox(self.spn_diam_int)
        if not ok_int or val_int < 0.0:
            errores.append("Diámetro Interior (debe ser mayor o igual a 0)")
            campos_invalidos.append(self.spn_diam_int)
        elif ok_ext and val_ext > 0.0 and val_int >= val_ext:
            errores.append(
                f"Diámetro Interior ({val_int:.1f} mm) debe ser menor al Diámetro Exterior ({val_ext:.1f} mm)"
            )
            campos_invalidos.append(self.spn_diam_int)

        # 9. Altura / Longitud: número decimal > 0
        ok_altura, val_altura = self._extraer_valor_spinbox(self.spn_altura)
        if not ok_altura or val_altura <= 0.0:
            errores.append("Altura / Longitud (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_altura)

        # 10. Masa Inicial de Grano: número decimal > 0
        ok_masa, val_masa = self._extraer_valor_spinbox(self.spn_masa)
        if not ok_masa or val_masa <= 0.0:
            errores.append("Masa Inicial de Grano (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_masa)

        # 11. Temperatura Ambiente: valor numérico válido
        ok_temp, val_temp = self._extraer_valor_spinbox(self.spn_temp)
        if not ok_temp or val_temp < -50.0 or val_temp > 80.0:
            errores.append("Temperatura Ambiente (debe ser un número válido)")
            campos_invalidos.append(self.spn_temp)

        # 12. Humedad Relativa: valor numérico entre 0 y 100
        ok_hum, val_hum = self._extraer_valor_spinbox(self.spn_humedad)
        if not ok_hum or val_hum < 0.0 or val_hum > 100.0:
            errores.append("Humedad Relativa (debe ser entre 0% y 100%)")
            campos_invalidos.append(self.spn_humedad)

        # 13. Tipo / Composición de Propelente: texto no vacío
        if not self.txt_composicion.text().strip():
            errores.append("Tipo / Composición de Propelente")
            campos_invalidos.append(self.txt_composicion)

        # Restaurar bordes normales de campos que ya se corrigieron
        for w in list(self._campos_con_error):
            if w not in campos_invalidos:
                self._limpiar_campo(w)

        # Aplicar borde rojo #BF3938 a los campos inválidos
        for w in campos_invalidos:
            w.setStyleSheet(ESTILO_BORDE_ERROR)
            self._campos_con_error.add(w)

        # Enfocar el primer campo inválido para guiar al usuario
        if campos_invalidos:
            campos_invalidos[0].setFocus()

        return (len(errores) == 0, errores)

    def _mostrar_alerta_validacion(self, errores: list[str]) -> None:
        """Muestra cuadro de diálogo de advertencia con estética oscura (#1F1B4E / #2A2566)."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Validación de Datos - Horus Space Lab")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        lista_parametros = "\n".join(f"  • {err}" for err in errores)
        mensaje = (
            "⚠️ No se puede guardar. Faltan los siguientes parámetros obligatorios:\n\n"
            f"{lista_parametros}"
        )
        msg_box.setText(mensaje)
        msg_box.setStyleSheet(
            f"""
            QMessageBox {{
                background-color: {COLOR_FONDO_PRINCIPAL};
                color: #FFFFFF;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            QLabel {{
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                line-height: 1.4;
                padding: 4px;
            }}
            QPushButton {{
                background-color: #007A3D;
                color: #FFFFFF;
                border: 1px solid {COLOR_VERDE_NEON};
                border-radius: 6px;
                padding: 6px 20px;
                font-weight: 800;
                font-size: 12px;
                min-height: 28px;
                min-width: 90px;
            }}
            QPushButton:hover {{
                background-color: #00964B;
            }}
            QPushButton:pressed {{
                background-color: #005A2C;
            }}
            """
        )
        msg_box.exec()

    def _validar_y_guardar(self) -> None:
        """Aplica validaciones estrictas antes de aceptar y habilitar el armado."""
        es_valido, errores = self.validar_formulario()
        if not es_valido:
            self._mostrar_alerta_validacion(errores)
            return

        raw_fecha = self.date_fecha.text().strip()
        qdate_parsed = QDate.fromString(raw_fecha, "yyyy-MM-dd")
        fecha_str = (
            qdate_parsed.toString("yyyy-MM-dd")
            if qdate_parsed.isValid()
            else self.date_fecha.date().toString("yyyy-MM-dd")
        )

        _, val_vejez = self._extraer_valor_spinbox(self.spn_vejez)
        _, val_ext = self._extraer_valor_spinbox(self.spn_diam_ext)
        _, val_int = self._extraer_valor_spinbox(self.spn_diam_int)
        _, val_altura = self._extraer_valor_spinbox(self.spn_altura)
        _, val_masa = self._extraer_valor_spinbox(self.spn_masa)
        _, val_temp = self._extraer_valor_spinbox(self.spn_temp)
        _, val_hum = self._extraer_valor_spinbox(self.spn_humedad)

        self.metadata_resultado = EnsayoMetadata(
            codigo_ensayo=self.txt_id.text().strip(),
            operadores=self.txt_operadores.text().strip(),
            fecha=fecha_str,
            dias_vejez=int(val_vejez),
            diam_ext_mm=val_ext,
            diam_int_mm=val_int,
            altura_mm=val_altura,
            masa_propelente_g=val_masa,
            temp_amb_c=val_temp,
            humedad_pct=val_hum,
            geometria_grano=self.combo_geometria.currentText().strip(),
            cluster_motores=self._obtener_valor_cluster(),
            notas=self.txt_composicion.text().strip(),
        )
        self.accept()
