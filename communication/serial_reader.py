"""
Módulo de lectura de puerto serie para la telemetría del banco de pruebas.

Proporciona la clase SerialReader que procesa de manera asíncrona mediante un QThread
los paquetes binarios entrantes según el protocolo de conexión seleccionado.
"""
from __future__ import annotations

# Importa logging para registrar eventos, mensajes de depuración y errores del lector serie.
import logging
# Importa struct para desempaquetar paquetes binarios según el formato del protocolo usado.
import struct
# Importa Optional para indicar que la conexión serial puede no estar creada todavía.
from typing import Optional

# Importa QThread y pyqtSignal para crear el hilo de Qt y emitir eventos hacia la interfaz.
from PyQt6.QtCore import QThread, pyqtSignal
# Importa pyserial para abrir, leer y escribir en puertos serie del hardware.
import serial

# Importa la configuración del protocolo actual, la constante RSSI no disponible y los enums del sistema.
from communication.protocols import (
    PROTOCOL_CONFIGS,
    RSSI_NOT_AVAILABLE,
    ConnectionMode,
    ProtocolConfig,
)

# Crea el logger propio del módulo para poder filtrar mensajes de lectura y conexión.
logger = logging.getLogger(__name__)


# Define la clase principal que corre en un hilo separado y lee la telemetría del puerto serie.
class SerialReader(QThread):
    """
    Hilo de lectura asíncrona para comunicación serie con el banco de pruebas.

    Lee los paquetes binarios enviados por el microcontrolador (por cable o LoRa),
    los deserializa según la configuración del protocolo y emite señales con los datos
    recibidos o cuando se produce una desconexión.
    """

    # Señal emitida cuando llega una lectura normal de empuje del motor con secuencia y RSSI.
    data_received = pyqtSignal(float, int, int)
    # Señal emitida cuando llega un paquete de caracterización con peso, voltaje y conteo.
    characterization_received = pyqtSignal(float, float, int, int)
    # Señal emitida cuando se cierra el puerto o el hilo termina por desconexión.
    disconnected = pyqtSignal()

    # Constructor: prepara la configuración del puerto, velocidad y protocolo para esta conexión.
    def __init__(
        self,
        port: str,
        baudrate: int,
        mode: ConnectionMode | str = ConnectionMode.CABLE,
    ) -> None:
        """
        Inicializa el lector serie con el puerto, velocidad y modo especificados.

        Args:
            port: Identificador del puerto serie (ej. 'COM3' o '/dev/ttyUSB0').
            baudrate: Velocidad de transmisión en baudios (ej. 115200).
            mode: Modo de conexión (ConnectionMode o cadena 'cable'/'lora').
        """
        # Llama al constructor de QThread para que este objeto se ejecute como hilo de Qt.
        super().__init__()
        # Guarda el puerto físico que se usará para leer datos del sensor o módulo.
        self.port: str = port
        # Guarda la velocidad de comunicación serial configurada para ese puerto.
        self.baudrate: int = baudrate
        # Convierte el modo recibido a un valor del enum ConnectionMode si viene como texto.
        self.mode: ConnectionMode = (
            mode if isinstance(mode, ConnectionMode) else ConnectionMode(mode)
        )
        # Selecciona la configuración del protocolo concreto para el modo elegido.
        self.protocol_config: ProtocolConfig = PROTOCOL_CONFIGS[self.mode]
        # Indica si el hilo debe seguir ejecutándose o detenerse.
        self.running: bool = False
        # Guarda la instancia del objeto serial abierto; puede ser None si aún no hay conexión.
        self.ser: Optional[serial.Serial] = None

    # Método principal del hilo: abre el puerto, lee paquetes y los manda a la capa de procesamiento.
    def run(self) -> None:
        """
        Ejecuta el bucle principal de lectura y decodificación de paquetes del puerto serie.

        Se conecta al puerto, lee datos binarios en bloques según el tamaño definido en
        ProtocolConfig, valida los rangos de empuje y secuencia, y emite la señal
        data_received. Al finalizar o ante un error, emite la señal disconnected.
        """
        # Obtiene el tamaño exacto de cada paquete según el protocolo activo.
        pkt_size: int = self.protocol_config.packet_size
        # Obtiene el formato struct que define la organización de bytes del paquete.
        struct_format: str = self.protocol_config.struct_format
        # Indica si en ese protocolo se incluye la medida de RSSI junto con el empuje.
        has_rssi: bool = self.protocol_config.has_rssi
        # Indica si este protocolo corresponde a un paquete de caracterización y no a telemetría estándar.
        is_characterization: bool = self.protocol_config.is_characterization

        try:
            # Abre el puerto serie con el nombre, velocidad y timeout configurados.
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            # Pone el hilo en estado activo para entrar al bucle de lectura.
            self.running = True
            # Registra la conexión exitosa con información útil para el usuario o depuración.
            logger.info(
                "Conexión serie establecida en %s a %d baudios (modo: %s)",
                self.port,
                self.baudrate,
                self.mode.value,
            )
            # Crea un buffer de bytes para ir acumulando tramos incompletos hasta formar un paquete completo.
            buf = bytearray()
            # Buclea mientras el puerto siga activo y el hilo no haya sido detenido.
            while self.running:
                try:
                    # Calcula cuántos bytes hay pendientes por leer en el buffer del sistema.
                    waiting = self.ser.in_waiting if self.ser.is_open else 0
                    # Lee ese número de bytes o al menos un byte para no bloquear el hilo.
                    chunk = self.ser.read(waiting or 1)
                except (serial.SerialException, OSError) as e:
                    # Si falla la lectura del puerto, se registra y se termina la lectura.
                    logger.error("Error al leer del puerto serie %s: %s", self.port, e)
                    break

                # Si llegó algún dato, se añade al buffer para procesarlo posteriormente.
                if chunk:
                    buf.extend(chunk)

                # Mientras el buffer tenga suficientes bytes para completar un paquete, se procesa.
                while len(buf) >= pkt_size:
                    # Toma el primer paquete completo y lo elimina del buffer.
                    raw = buf[:pkt_size]
                    buf = buf[pkt_size:]
                    try:
                        # Si el protocolo es de caracterización, desempaca el formato específico.
                        if is_characterization:
                            weight_kg, voltage_mv, raw_count, seq = struct.unpack(struct_format, raw)
                            # Emite la señal para la vista o lógica dedicada a la caracterización.
                            self.characterization_received.emit(
                                float(weight_kg),
                                float(voltage_mv),
                                int(raw_count),
                                int(seq),
                            )
                            # No sigue con la lógica normal de empuje porque es otro tipo de paquete.
                            continue
                        # Si el protocolo incluye RSSI, lo desempaca junto con el empuje y la secuencia.
                        elif has_rssi:
                            newtons, seq, rssi = struct.unpack(struct_format, raw)
                        # Si el protocolo no incluye RSSI, se deja ese valor como indicador no disponible.
                        else:
                            newtons, seq = struct.unpack(struct_format, raw)
                            rssi = RSSI_NOT_AVAILABLE

                        # Valida que el valor de empuje y la secuencia estén dentro de rangos plausibles.
                        if -500.0 < newtons < 5000.0 and seq < 1_000_000:
                            # Si todo es válido, emite la lectura normal para el motor de telemetría.
                            self.data_received.emit(float(newtons), int(seq), int(rssi))
                        else:
                            # Si el paquete está fuera de rango, se descarta para evitar corrupción de datos.
                            logger.warning(
                                "Paquete descartado por valores fuera de rango: N=%.2f, seq=%d",
                                newtons,
                                seq,
                            )
                    except struct.error as e:
                        # Si falla el desempaquetado, se registra el problema y se ignora ese paquete.
                        logger.warning("Error al deserializar paquete binario: %s", e)
        except serial.SerialException as e:
            # Si falla la apertura del puerto, se registra el error de conexión.
            logger.error("Error al abrir puerto serie %s: %s", self.port, e)
        except Exception as e:
            # Captura errores inesperados para no dejar el hilo sin controlar.
            logger.exception("Error inesperado en SerialReader: %s", e)
        finally:
            # Asegura que el hilo quede detenido aunque termine por error o desconexión.
            self.running = False
            # Si el puerto aún está abierto, lo cierra para liberar recursos del sistema.
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception as e:
                    logger.debug("Error al cerrar puerto serie en finalización: %s", e)
            # Emite la señal de desconexión para que la UI actualice su estado visual.
            self.disconnected.emit()
            # Registra el cierre final del puerto para trazabilidad.
            logger.info("Puerto serie %s desconectado.", self.port)

    # Método para mandar un comando textual al microcontrolador conectado en el puerto serie.
    def send_command(self, char: str) -> None:
        """
        Envía un comando de texto o caracter al microcontrolador a través del puerto serie.

        Args:
            char: Carácter o comando a transmitir.
        """
        # Solo intenta escribir si el puerto está realmente abierto y disponible.
        if self.ser and self.ser.is_open:
            try:
                # Codifica el texto como bytes y lo envía por el canal serie.
                self.ser.write(char.encode())
                # Registra el comando enviado en modo de depuración.
                logger.debug("Comando enviado: %s", char)
            except (serial.SerialException, OSError) as e:
                # Si la escritura falla, informa claramente el problema.
                logger.error("Error al enviar comando '%s': %s", char, e)
        else:
            # Si no hay conexión activa, no puede enviarse nada y se registra el aviso.
            logger.warning("No se pudo enviar comando '%s': puerto serie no abierto", char)

    # Método para detener el hilo de forma ordenada y cerrar el puerto sin dejarlo colgado.
    def stop(self) -> None:
        """Detiene el hilo de lectura y cierra la conexión del puerto serie."""
        # Marca el hilo como detenido para que el bucle principal termine.
        self.running = False
        # Si aún queda el puerto abierto, lo cierra para liberar recursos.
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except (serial.SerialException, OSError) as e:
                logger.error("Error al cerrar el puerto serie durante stop(): %s", e)
        # Espera a que el hilo termine realmente antes de continuar.
        self.wait()
