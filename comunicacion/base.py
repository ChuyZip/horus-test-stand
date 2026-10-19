"""Interfaz base abstracta para canales de adquisición de datos (DAQ).

Define las señales y contratos para backends intercambiables:
- Modo SIMULACIÓN (sintético a 200 Hz)
- Modo SERIAL (comunicación física con microcontrolador ESP32)
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QThread, Signal


class CanalDAQ(QThread):
    """Clase base para cualquier fuente de telemetría de banco de pruebas."""

    # Señales normalizadas para la interfaz gráfica
    nueva_muestra = Signal(float, float)        # (tiempo_s, voltaje_v)
    estado_cambiado = Signal(object)            # EstadoInstrumentacion
    alerta_seguridad = Signal(str)              # Mensaje de advertencia o falla
    simulacion_finalizada = Signal()

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)

    def iniciar_adquisicion(self) -> None:
        """Arranca el hilo de captura o simulación."""
        raise NotImplementedError

    def detener_adquisicion(self) -> None:
        """Detiene ordenadamente el canal de datos."""
        raise NotImplementedError

    def abortar(self) -> None:
        """Parada de emergencia prioritaria (corte relé / señal a cero)."""
        raise NotImplementedError

    def tarar(self) -> None:
        """Comando de puesta a cero del transductor."""
        pass

    def armar(self) -> None:
        """Prepara el sistema y habilita circuito de ignición."""
        pass

    def disparar(self) -> None:
        """Ejecuta la secuencia de ignición."""
        pass
