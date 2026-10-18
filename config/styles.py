"""Estilos visuales y hojas de estilo QSS — Tema Yaqui.

Inspirado en la cultura Yaqui de Sonora, México:
tierra del desierto, turquesa ceremonial, fuego Pascola,
nopal verde, atardeceres dorados sobre la Sierra del Bacatete.
"""

from config.constants import (
    THEME_BG,
    THEME_BORDER,
    THEME_BUTTON_BG,
    THEME_CYAN,
    THEME_GREEN,
    THEME_PANEL_BG,
    THEME_RED,
    THEME_TEXT_MUTED,
    THEME_ACCENT_GOLD,
)

MAIN_STYLESHEET: str = f"""
QMainWindow, QWidget {{
    background: {THEME_BG};
}}
QLabel {{
    color: {THEME_TEXT_MUTED};
    font-family: 'Segoe UI', 'Courier New', monospace;
}}
QPushButton {{
    background: {THEME_BUTTON_BG};
    color: {THEME_TEXT_MUTED};
    border-radius: 5px;
    padding: 8px 16px;
    font-weight: bold;
    font-family: 'Segoe UI', 'Courier New', monospace;
    border: 1px solid {THEME_BORDER};
}}
QPushButton:hover {{
    background: #3d2e22;
    border-color: {THEME_ACCENT_GOLD};
}}
QPushButton:pressed {{
    background: #1a120b;
    border-color: {THEME_ACCENT_GOLD}aa;
}}
QComboBox {{
    background: {THEME_BUTTON_BG};
    color: {THEME_TEXT_MUTED};
    padding: 6px;
    border: 1px solid {THEME_BORDER};
    border-radius: 4px;
    font-family: 'Segoe UI', 'Courier New', monospace;
}}
QComboBox:hover {{
    border-color: {THEME_ACCENT_GOLD};
}}
QComboBox QAbstractItemView {{
    background: {THEME_PANEL_BG};
    color: {THEME_TEXT_MUTED};
    selection-background-color: #3d2e22;
    selection-color: {THEME_ACCENT_GOLD};
}}
QToolTip {{
    background: {THEME_PANEL_BG};
    color: {THEME_TEXT_MUTED};
    border: 1px solid {THEME_BORDER};
    padding: 4px;
    border-radius: 3px;
}}
"""
"""Hoja de estilo principal — Tema Yaqui aplicado a toda la interfaz."""


def start_button_style() -> str:
    """Botón START — verde nopal sobre tierra."""
    return f"background: #1e2e16; color: {THEME_GREEN}; border-color: {THEME_GREEN}66;"


def stop_button_style() -> str:
    """Botón STOP — rojo Pascola, fuego ceremonial."""
    return f"background: #2e1614; color: {THEME_RED}; border-color: {THEME_RED}66;"


def unit_button_style() -> str:
    """Botón de unidades — turquesa ceremonial."""
    return f"background: #1a2e2a; color: {THEME_CYAN}; border-color: {THEME_CYAN}66;"


def arm_button_style() -> str:
    """Botón ARM — dorado sol, precaución."""
    return f"background: #2e2510; color: {THEME_ACCENT_GOLD}; border: 2px solid {THEME_ACCENT_GOLD}88; padding: 10px 24px;"


def fire_button_enabled_style() -> str:
    """Botón FIRE habilitado — rojo fuego vivo."""
    return f"background: #4a1510; color: {THEME_RED}; border: 2px solid {THEME_RED}; padding: 10px 24px;"


def fire_button_disabled_style() -> str:
    """Botón FIRE deshabilitado — ceniza apagada."""
    return "background: #1a1210; color: #4a3a30; border: 2px solid #4a3a3044; padding: 10px 24px;"


def connected_status_style() -> str:
    """Estado conectado — verde nopal brillante."""
    return f"color: {THEME_GREEN}; font-size: 11px; font-weight: bold;"


def disconnected_status_style() -> str:
    """Estado desconectado — rojo Pascola."""
    return f"color: {THEME_RED}; font-size: 11px; font-weight: bold;"


def kpi_card_style(accent_color: str = THEME_CYAN) -> str:
    """Tarjeta KPI — arcilla con borde de acento translúcido."""
    return f"background: {THEME_PANEL_BG}; border: 1px solid {accent_color}44; border-radius: 8px;"
