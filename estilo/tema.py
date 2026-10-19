"""Constantes de color y hoja de estilo QSS global para Horus Space Lab.

Fiel a la instrumentación aeroespacial de la estación de control:
- Fondo profundo: #1F1B4E
- Paneles y tarjetas: #282366 y #352F7E
- Acento y aborto: #BF3938
- Telemetría activa: #00E676 (verde neón), #00E5FF (cian), #FF9100 (ámbar impulso)
- Bordes: rgba(255, 255, 255, 0.12)
"""

from enum import Enum

# ==============================================================================
# PALETA DE COLORES CIENTÍFICA
# ==============================================================================
COLOR_FONDO_PRINCIPAL = "#1F1B4E"
COLOR_PANEL_MEDIO = "#282366"
COLOR_PANEL_CLARO = "#352F7E"
COLOR_PANEL_HOVER = "#3E3793"

COLOR_TEXTO_PRINCIPAL = "#FFFFFF"
COLOR_TEXTO_SECUNDARIO = "rgba(255, 255, 255, 0.75)"
COLOR_TEXTO_MUTED = "rgba(255, 255, 255, 0.50)"

COLOR_BORDE_NORMAL = "rgba(255, 255, 255, 0.14)"
COLOR_BORDE_TENUE = "rgba(255, 255, 255, 0.08)"

# Colores de telemetría funcional
COLOR_ACENTO_CRITICO = "#BF3938"      # Rojo aborto / Detener
COLOR_VERDE_NEON = "#00E676"          # Pico N, Empuje actual, Iniciar
COLOR_CIAN = "#00E5FF"                # Tensión celda (V), Tiempo
COLOR_AMBAR = "#FF9100"               # Impulso acumulado (N·s)
COLOR_AZUL_ACCION = "#0D6EFD"         # Reiniciar, Tab activo


# ==============================================================================
# ESTADOS DEL SISTEMA DE PRUEBA
# ==============================================================================
class EstadoInstrumentacion(Enum):
    """Estados operacionales con código de color e icono para la interfaz."""

    LISTO = ("Listo", "🟢", COLOR_VERDE_NEON)
    ARMADO = ("Armado", "🟡", "#FFD600")
    CUENTA_REGRESIVA = ("Cuenta regresiva", "🟠", "#FF6D00")
    GRABANDO = ("Grabando", "🔴", COLOR_ACENTO_CRITICO)
    TERMINADO = ("Terminado", "🔵", "#2979FF")
    ABORTADO = ("Abortado", "🛑", "#FF4D4D")

    def __init__(self, etiqueta: str, icono: str, color: str):
        self.etiqueta = etiqueta
        self.icono = icono
        self.color = color

    @property
    def texto_completo(self) -> str:
        return f"{self.icono} {self.etiqueta}"


# ==============================================================================
# HOJA DE ESTILOS QSS CENTRALIZADA
# ==============================================================================
def obtener_hoja_estilos_qss() -> str:
    """Retorna la hoja de estilo global optimizada para instrumentación científica."""
    return f"""
    QMainWindow, QWidget#VentanaPrincipal {{
        background-color: {COLOR_FONDO_PRINCIPAL};
        color: {COLOR_TEXTO_PRINCIPAL};
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    QWidget {{
        background-color: transparent;
        color: {COLOR_TEXTO_PRINCIPAL};
    }}

    /* ==========================================
       BARRA SUPERIOR (HEADER)
       ========================================== */
    QFrame#BarraSuperior {{
        background-color: #191542;
        border-bottom: 1px solid {COLOR_BORDE_NORMAL};
        min-height: 60px;
        max-height: 60px;
    }}

    QLabel#TituloApp {{
        color: #FFFFFF;
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 1.2px;
    }}

    QLabel#SubtituloApp {{
        color: rgba(255, 255, 255, 0.70);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}

    /* Pestañas horizontales de navegación */
    QPushButton.TabNav {{
        background-color: transparent;
        color: rgba(255, 255, 255, 0.85);
        font-size: 11px;
        font-weight: 700;
        padding: 5px 10px;
        border: 1px solid transparent;
        border-radius: 6px;
    }}

    QPushButton.TabNav:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        color: #FFFFFF;
    }}

    QPushButton.TabNav[activo="true"] {{
        background-color: #0D6EFD;
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }}

    /* Insignia de Estado Operacional */
    QFrame#BadgeEstado {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid #2979FF;
        border-radius: 14px;
        padding: 4px 12px;
        min-height: 26px;
    }}

    QLabel#TextoBadgeEstado {{
        color: #2979FF;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }}

    /* Botón Abortar Superior */
    QPushButton#BtnAbortarTop {{
        background-color: {COLOR_ACENTO_CRITICO};
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: 0.6px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 6px;
        padding: 5px 12px;
        min-height: 28px;
    }}

    QPushButton#BtnAbortarTop:hover {{
        background-color: #D44342;
    }}

    QPushButton#BtnAbortarTop:pressed {{
        background-color: #9E2E2D;
    }}

    /* ==========================================
       TARJETAS DE TELEMETRÍA (KPIS)
       ========================================== */
    QFrame.TarjetaKPI {{
        background-color: {COLOR_PANEL_MEDIO};
        border: 1px solid {COLOR_BORDE_NORMAL};
        border-radius: 8px;
    }}

    QLabel.TituloKPI {{
        color: {COLOR_TEXTO_MUTED};
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}

    QLabel.ValorKPI {{
        font-size: 24px;
        font-weight: 900;
        font-family: "Menlo", Consolas, monospace;
    }}

    QLabel.UnidadKPI {{
        font-size: 13px;
        font-weight: 800;
        padding-top: 4px;
    }}

    /* ==========================================
       BOTONES DE CONTROL (COLUMNA DERECHA)
       ========================================== */
    QPushButton#BtnIniciarSim {{
        background-color: #074B2A;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.8px;
        border: 1px solid {COLOR_VERDE_NEON};
        border-radius: 6px;
        padding: 6px 14px;
        min-height: 26px;
    }}
    QPushButton#BtnIniciarSim:hover {{
        background-color: #0B6B3C;
    }}

    QPushButton#BtnDetenerSim {{
        background-color: #5A1414;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.8px;
        border: 1px solid {COLOR_ACENTO_CRITICO};
        border-radius: 6px;
        padding: 6px 14px;
        min-height: 26px;
    }}
    QPushButton#BtnDetenerSim:hover {{
        background-color: #7B1B1B;
    }}

    QPushButton#BtnReiniciarSim {{
        background-color: #0B3A75;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.8px;
        border: 1px solid #2979FF;
        border-radius: 6px;
        padding: 6px 14px;
        min-height: 26px;
    }}
    QPushButton#BtnReiniciarSim:hover {{
        background-color: #1052A3;
    }}

    /* ==========================================
       CHECKBOXES CIENTÍFICOS
       ========================================== */
    QCheckBox {{
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 600;
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
        border-radius: 3px;
        border: 1px solid {COLOR_CIAN};
        background-color: rgba(0, 229, 255, 0.15);
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLOR_CIAN};
        image: none;
    }}

    /* ==========================================
       FORMULARIOS Y CAMPOS DE ENTRADA GLOBALES
       ========================================== */
    QDialog {{
        background-color: {COLOR_FONDO_PRINCIPAL};
        color: #FFFFFF;
    }}

    QLabel.EtiquetaCampo, QDialog QLabel {{
        color: #FFFFFF;
        font-size: 13px;
        font-weight: 500;
    }}

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
        background: rgba(255, 255, 255, 0.15);
    }}

    /* ==========================================
       FOOTER INFERIOR
       ========================================== */
    QLabel#FooterTexto {{
        color: {COLOR_TEXTO_MUTED};
        font-size: 11px;
        font-weight: 600;
        padding-left: 8px;
    }}
    """
