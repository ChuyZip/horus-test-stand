"""Constantes globales del sistema de telemetría de banco de pruebas Horus."""

import os

# Constantes físicas y de cálculo de propulsión
GRAVITY: float = 9.80665
"""Aceleración de la gravedad estándar en m/s² para conversión entre Newtons y kilogramos-fuerza."""

THRUST_THRESHOLD: float = 2.0
"""Umbral de empuje en Newtons para filtrar ruido de la celda de carga e iniciar integración de impulso."""

FILTER_WINDOW_SIZE: int = 5
"""Cantidad impar de muestras usadas por el filtro de mediana contra picos aislados."""

# Parámetros de comunicación serie
DEFAULT_BAUDRATE: int = 115200
"""Velocidad en baudios por defecto para la interfaz serie."""

RECONNECT_INTERVAL_MS: int = 3000
"""Intervalo de espera en milisegundos para reintentar la conexión serie."""

# Modos de comunicación
MODE_CABLE: str = "cable"
"""Modo de enlace alámbrico mediante cable directo o RS-485."""

MODE_LORA: str = "lora"
"""Modo de enlace inalámbrico de largo alcance LoRa."""

# Tamaños de paquetes de datos binarios (en bytes)
PACKET_SIZE_CABLE: int = 8
"""Tamaño de paquete binario en modo cable: float (4B) empuje + uint32 (4B) secuencia = 8 bytes."""

PACKET_SIZE_LORA: int = 9
"""Tamaño de paquete binario en modo LoRa: float (4B) empuje + uint32 (4B) secuencia + int8 (1B) rssi = 9 bytes."""

# Archivo de configuración
CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".horus_config.json")
"""Ruta al archivo de configuración de usuario en formato JSON."""

# Paleta de colores temáticos — Estilo Yaqui (Sonora, México)
# Inspirada en: tierra del desierto, fuego ceremonial, turquesa,
# ocre/dorado, nopal verde y atardeceres sobre la Sierra del Bacatete.

THEME_BG: str = "#1a120b"
"""Fondo principal — tierra oscura del desierto nocturno."""

THEME_CYAN: str = "#40c4aa"
"""Turquesa ceremonial — piedra turquesa Yaqui, datos primarios de empuje."""

THEME_GREEN: str = "#6dbf4a"
"""Verde nopal — crecimiento, conexión activa, impulso acumulado."""

THEME_RED: str = "#c4342d"
"""Rojo Pascola — fuego de la danza del venado, alarma y parada."""

THEME_ORANGE: str = "#e8922f"
"""Naranja atardecer — empuje máximo, sol sobre el desierto de Sonora."""

THEME_PINK: str = "#d4567a"
"""Rosa bugambilia — clasificación de motor NAR."""

THEME_PURPLE: str = "#9b7ec8"
"""Púrpura crepuscular — señal LoRa y RSSI."""

THEME_WARN_ORANGE: str = "#d4753a"
"""Ocre cálido — paquetes perdidos y advertencias."""

# Colores secundarios para componentes UI
THEME_PANEL_BG: str = "#261c13"
"""Fondo de tarjetas KPI — arcilla oscura."""

THEME_BUTTON_BG: str = "#2e2118"
"""Fondo de botones — madera de mezquite."""

THEME_BORDER: str = "#5a4535"
"""Bordes — fibra de palma tejida."""

THEME_TEXT_MUTED: str = "#c8b8a0"
"""Texto secundario — arena del desierto."""

# Colores de acento para gráficas
THEME_GRAPH_BG: str = "#1a120b"
"""Fondo de gráficas — mismo que fondo principal."""

THEME_GRID: str = "#3a2a1e"
"""Líneas de cuadrícula — surcos en la tierra."""

THEME_ACCENT_GOLD: str = "#d4a843"
"""Dorado sol — acento decorativo, bordes activos."""
