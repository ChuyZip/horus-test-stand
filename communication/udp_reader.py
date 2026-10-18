"""
Módulo de lectura UDP para la conexión por WiFi del banco de pruebas.

Implementa un QThread que actúa como servidor UDP para recibir la telemetría
desde el ESP32, y mantiene la IP del cliente para enviar comandos de vuelta.
"""

import socket
import struct
import logging
from PyQt6.QtCore import pyqtSignal, QThread

from communication.protocols import ConnectionMode, PROTOCOL_CONFIGS, RSSI_NOT_AVAILABLE

logger = logging.getLogger(__name__)


class UdpReader(QThread):
    """
    Hilo de lectura para comunicación WiFi mediante protocolo UDP.
    
    Abre un socket en un puerto local y escucha paquetes de telemetría.
    Guarda la dirección IP del remitente para poder enviar comandos de vuelta
    (bidireccionalidad básica).
    """

    data_received = pyqtSignal(float, int, int)
    characterization_received = pyqtSignal(float, float, int, int)
    disconnected = pyqtSignal()

    def __init__(
        self,
        port: int = 8888,
        mode: ConnectionMode = ConnectionMode.WIFI,
    ) -> None:
        """
        Inicializa el lector UDP.

        Args:
            port: Puerto UDP donde escuchará el servidor.
        """
        super().__init__()
        self.port = port
        self.running = False
        self.sock: socket.socket | None = None
        self.last_client_addr = None
        self.config = PROTOCOL_CONFIGS[mode]

    def run(self) -> None:
        """Bucle principal de escucha UDP."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Vincular a todas las interfaces en el puerto especificado
            self.sock.bind(('0.0.0.0', self.port))
            # Timeout corto para permitir revisar el flag 'running' y no bloquear
            self.sock.settimeout(0.5)
            self.running = True
            
            logger.info("Escuchando UDP (WiFi) en el puerto %d", self.port)

            while self.running:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    self.last_client_addr = addr  # Guardar para enviar respuestas

                    # UDP conserva los limites del datagrama, por lo que un paquete
                    # extendido de 16 bytes se puede reconocer sin ambiguedad.
                    if len(data) == 16:
                        weight_kg, voltage_mv, raw_count, seq = struct.unpack("<ffiI", data)
                        self.characterization_received.emit(
                            float(weight_kg),
                            float(voltage_mv),
                            int(raw_count),
                            int(seq),
                        )
                    elif len(data) >= self.config.packet_size:
                        raw = data[:self.config.packet_size]
                        if self.config.is_characterization:
                            weight_kg, voltage_mv, raw_count, seq = struct.unpack(
                                self.config.struct_format, raw
                            )
                            self.characterization_received.emit(
                                float(weight_kg),
                                float(voltage_mv),
                                int(raw_count),
                                int(seq),
                            )
                        else:
                            newtons, seq = struct.unpack(self.config.struct_format, raw)
                            self.data_received.emit(float(newtons), int(seq), RSSI_NOT_AVAILABLE)
                except socket.timeout:
                    continue
        except Exception as e:
            logger.error("Error en UdpReader: %s", e)
        finally:
            self.disconnected.emit()

    def send_command(self, char: str) -> None:
        """
        Envía un comando (carácter) de vuelta al último cliente que envió datos.

        Args:
            char: Carácter o string a enviar (ej. 'S', 'T', 'F').
        """
        if self.sock and self.last_client_addr:
            try:
                self.sock.sendto(char.encode(), self.last_client_addr)
                logger.debug("Comando '%s' enviado a %s", char, self.last_client_addr)
            except Exception as e:
                logger.error("Error enviando comando por UDP: %s", e)

    def stop(self) -> None:
        """Detiene el hilo y cierra el socket."""
        self.running = False
        self.wait()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
