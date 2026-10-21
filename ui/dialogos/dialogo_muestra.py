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
- QFormLayout limpio con verticalSpacing: 10px y horizontalSpacing: 18px.
- Contenedor en QScrollArea con barra horizontal desactivada y barra vertical estilizada.
- Validación estricta con retroalimentación visual inmediata (borde rojo #BF3938) y alerta oscura.
- 13 campos reglamentarios (incluyendo Geometría de Grano y Cluster de Motores).
"""

from __future__ import annotations

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
        self.spn_diam_ext.setSuffix(" mm")

        self.spn_diam_int = QDoubleSpinBox()
        self.spn_diam_int.setDecimals(1)
        self.spn_diam_int.setRange(0.0, 490.0)
        self.spn_diam_int.setValue(12.0)
        self.spn_diam_int.setSuffix(" mm")

        self.spn_altura = QDoubleSpinBox()
        self.spn_altura.setDecimals(1)
        self.spn_altura.setRange(0.0, 2500.0)
        self.spn_altura.setValue(145.0)
        self.spn_altura.setSuffix(" mm")

        self.spn_masa = QDoubleSpinBox()
        self.spn_masa.setDecimals(1)
        self.spn_masa.setRange(0.0, 50000.0)
        self.spn_masa.setValue(245.0)
        self.spn_masa.setSuffix(" g")

        self.spn_temp = QDoubleSpinBox()
        self.spn_temp.setDecimals(1)
        self.spn_temp.setRange(-50.0, 80.0)
        self.spn_temp.setValue(22.5)
        self.spn_temp.setSuffix(" °C")

        self.spn_humedad = QDoubleSpinBox()
        self.spn_humedad.setDecimals(1)
        self.spn_humedad.setRange(0.0, 100.0)
        self.spn_humedad.setValue(45.0)
        self.spn_humedad.setSuffix(" %")

        self.txt_composicion = QLineEdit("KNSB 65/35 (Nitrato de Potasio / Sorbitol)")
        self.txt_composicion.setPlaceholderText("Ej. APCP 70/15/15 o KNDX")

        # Conectar eventos de cambio para restaurar estilo normal al interactuar
        self._conectar_senales_limpieza()

        # Lista reglamentaria de 13 campos con etiquetas claras en la columna izquierda
        campos = [
            ("ID de Muestra", self.txt_id),
            ("Operador(es)", self.txt_operadores),
            ("Fecha de Ensayo", self.date_fecha),
            ("Días de Vejez", self.spn_vejez),
            ("Tipo de Geometría de Grano", self.combo_geometria),
            ("Configuración Cluster de Motores", widget_cluster),
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

    def _conectar_senales_limpieza(self) -> None:
        """Conecta eventos de edición para restaurar el borde normal al interactuar con el campo."""
        self.txt_id.textChanged.connect(lambda: self._limpiar_campo(self.txt_id))
        self.txt_operadores.textChanged.connect(lambda: self._limpiar_campo(self.txt_operadores))
        self.date_fecha.dateChanged.connect(lambda: self._limpiar_campo(self.date_fecha))
        self.spn_vejez.valueChanged.connect(lambda: self._limpiar_campo(self.spn_vejez))
        self.combo_geometria.currentTextChanged.connect(lambda: self._limpiar_campo(self.combo_geometria))
        self.combo_cluster.currentTextChanged.connect(lambda: self._limpiar_campo(self.combo_cluster))
        self.spn_cluster_personalizado.valueChanged.connect(lambda: self._limpiar_campo(self.spn_cluster_personalizado))
        self.spn_diam_ext.valueChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_ext), self._limpiar_campo(self.spn_diam_int))
        )
        self.spn_diam_int.valueChanged.connect(
            lambda: (self._limpiar_campo(self.spn_diam_int), self._limpiar_campo(self.spn_diam_ext))
        )
        self.spn_altura.valueChanged.connect(lambda: self._limpiar_campo(self.spn_altura))
        self.spn_masa.valueChanged.connect(lambda: self._limpiar_campo(self.spn_masa))
        self.spn_temp.valueChanged.connect(lambda: self._limpiar_campo(self.spn_temp))
        self.spn_humedad.valueChanged.connect(lambda: self._limpiar_campo(self.spn_humedad))
        self.txt_composicion.textChanged.connect(lambda: self._limpiar_campo(self.txt_composicion))

    def _limpiar_campo(self, widget: QWidget) -> None:
        """Restaura el estilo y borde translúcido normal de un control específico."""
        if widget in self._campos_con_error:
            widget.setStyleSheet("")
            self._campos_con_error.discard(widget)

    def _obtener_valor_cluster(self) -> str:
        """Determina el descriptor del cluster según la opción seleccionada."""
        texto = self.combo_cluster.currentText()
        if "Personalizado" in texto:
            return f"Personalizado ({self.spn_cluster_personalizado.value()}x)"
        return texto

    def obtener_datos(self) -> dict[str, Any]:
        """Retorna los datos del formulario como diccionario serializable."""
        if self.metadata_resultado:
            return asdict(self.metadata_resultado)
        return {
            "codigo_ensayo": self.txt_id.text().strip(),
            "operadores": self.txt_operadores.text().strip(),
            "fecha": self.date_fecha.date().toString("yyyy-MM-dd"),
            "dias_vejez": self.spn_vejez.value(),
            "diam_ext_mm": self.spn_diam_ext.value(),
            "diam_int_mm": self.spn_diam_int.value(),
            "altura_mm": self.spn_altura.value(),
            "masa_propelente_g": self.spn_masa.value(),
            "temp_amb_c": self.spn_temp.value(),
            "humedad_pct": self.spn_humedad.value(),
            "geometria_grano": self.combo_geometria.currentText(),
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
            f = QDate.fromString(meta.fecha[:10], "yyyy-MM-dd")
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

        # 1. ID de Muestra: No debe estar vacío o con solo espacios en blanco
        if not self.txt_id.text().strip():
            errores.append("ID de Muestra")
            campos_invalidos.append(self.txt_id)

        # 2. Operador(es): No debe estar vacío
        if not self.txt_operadores.text().strip():
            errores.append("Operador(es)")
            campos_invalidos.append(self.txt_operadores)

        # 3. Fecha de Ensayo: Debe tener una fecha válida seleccionada
        fecha = self.date_fecha.date()
        if not fecha.isValid() or fecha.isNull():
            errores.append("Fecha de Ensayo")
            campos_invalidos.append(self.date_fecha)

        # 4. Días de Vejez: Debe tener un valor numérico válido (>= 0)
        if self.spn_vejez.value() < 0:
            errores.append("Días de Vejez (debe ser mayor o igual a 0)")
            campos_invalidos.append(self.spn_vejez)

        # 5. Tipo de Geometría de Grano: Opción seleccionada no vacía
        if not self.combo_geometria.currentText().strip():
            errores.append("Tipo de Geometría de Grano")
            campos_invalidos.append(self.combo_geometria)

        # 6. Configuración Cluster de Motores: Opción seleccionada no vacía
        texto_cluster = self.combo_cluster.currentText().strip()
        if not texto_cluster:
            errores.append("Configuración Cluster de Motores")
            campos_invalidos.append(self.combo_cluster)
        elif "Personalizado" in texto_cluster and self.spn_cluster_personalizado.value() <= 0:
            errores.append("Configuración Cluster de Motores (número de motores debe ser mayor a 0)")
            campos_invalidos.append(self.spn_cluster_personalizado)

        # 7. Diámetro Exterior (mm): Debe ser mayor a 0
        diam_ext = self.spn_diam_ext.value()
        if diam_ext <= 0.0:
            errores.append("Diámetro Exterior (mm) (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_diam_ext)

        # 8. Diámetro Interior (mm): >= 0 y estrictamente menor que Diámetro Exterior
        diam_int = self.spn_diam_int.value()
        if diam_int < 0.0:
            errores.append("Diámetro Interior (mm) (debe ser mayor o igual a 0)")
            campos_invalidos.append(self.spn_diam_int)
        elif diam_ext > 0.0 and diam_int >= diam_ext:
            errores.append(
                f"Diámetro Interior ({diam_int:.1f} mm) debe ser estrictamente menor que Diámetro Exterior ({diam_ext:.1f} mm)"
            )
            campos_invalidos.append(self.spn_diam_int)

        # 9. Altura / Longitud (mm): Debe ser mayor a 0
        if self.spn_altura.value() <= 0.0:
            errores.append("Altura / Longitud (mm) (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_altura)

        # 10. Masa Inicial de Grano (g): Debe ser mayor a 0
        if self.spn_masa.value() <= 0.0:
            errores.append("Masa Inicial de Grano (g) (debe ser mayor a 0)")
            campos_invalidos.append(self.spn_masa)

        # 11. Temperatura Ambiente (°C): Valor numérico definido
        temp_val = self.spn_temp.value()
        if temp_val is None or temp_val < -50.0 or temp_val > 80.0:
            errores.append("Temperatura Ambiente (°C)")
            campos_invalidos.append(self.spn_temp)

        # 12. Humedad Relativa (%): Valor entre 0% y 100%
        hum_val = self.spn_humedad.value()
        if hum_val < 0.0 or hum_val > 100.0:
            errores.append("Humedad Relativa (%) (debe estar entre 0% y 100%)")
            campos_invalidos.append(self.spn_humedad)

        # 13. Tipo / Composición de Propelente: No debe estar vacío
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
        msg_box.setWindowTitle("Validación Requerida - Horus Space Lab")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        lista_parametros = "\n".join(f"  • {err}" for err in errores)
        mensaje = (
            "⚠️ No es posible habilitar el armado del banco. "
            "Faltan los siguientes parámetros obligatorios:\n\n"
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

        fecha_str = self.date_fecha.date().toString("yyyy-MM-dd")

        self.metadata_resultado = EnsayoMetadata(
            codigo_ensayo=self.txt_id.text().strip(),
            operadores=self.txt_operadores.text().strip(),
            fecha=fecha_str,
            dias_vejez=self.spn_vejez.value(),
            diam_ext_mm=self.spn_diam_ext.value(),
            diam_int_mm=self.spn_diam_int.value(),
            altura_mm=self.spn_altura.value(),
            masa_propelente_g=self.spn_masa.value(),
            temp_amb_c=self.spn_temp.value(),
            humedad_pct=self.spn_humedad.value(),
            geometria_grano=self.combo_geometria.currentText(),
            cluster_motores=self._obtener_valor_cluster(),
            notas=self.txt_composicion.text().strip(),
        )
        self.accept()
