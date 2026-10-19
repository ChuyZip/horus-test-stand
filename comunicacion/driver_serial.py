"""Driver de comunicación serial para microcontrolador ESP32 de Horus Space Lab.

Implementa:
- Detección automática y listado de puertos serie (/dev/cu.usb*, COM*).
- Hilo lector de alta velocidad a 200 Hz con parseo de tramas 'tiempo,voltaje'.
- Envío de comandos de control: ARM, DISARM, START, STOP, ABORT, TARE, FIRE, SET_RATE.
- Detección de saturación de ADC/sensor y alertas de seguridad.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import serial
import serial.tools.list_ports
from PySide6.QtCore import QMutex, QMutexLocker

from comunicacion.base import CanalDAQ
from estilo.tema import EstadoInstrumentacion


class DriverSerialESP32(CanalDAQ):
    """Canal de adquisición de hardware real mediante UART/USB Serial."""

    def __init__(
        self,
        puerto: str = "",
        baudrate: int = 115200,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.puerto = puerto
        self.baudrate = baudrate
        self.frecuencia_hz = 200.0

        self._activo = False
        self._mutex = QMutex()
        self._serial: Optional[serial.Serial] = None

    @staticmethod
    def listar_puertos_disponibles() -> list[str]:
        """Retorna los nombres de los puertos serie detectados en el sistema."""
        puertos = serial.tools.list_ports.comports()
        return [p.device for p in puertos]

    def conectar(self, puerto: str, baudrate: int = 115200) -> bool:
        """Abre la conexión con el microcontrolador ESP32."""
        self.puerto = puerto
        self.baudrate = baudrate
        try:
            self._serial = serial.Serial(
                port=self.puerto,
                baudrate=self.baudrate,
                timeout=0.5,
                write_timeout=0.5,
            )
            time.sleep(0.5)  # Tiempo de estabilización DTR/RTS
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            logging.info(f"Conectado a ESP32 en {self.puerto} a {self.baudrate} baudios.")
            return True
        except Exception as e:
            logging.error(f"Error al abrir puerto serie {self.puerto}: {e}")
            self.alerta_seguridad.emit(f"Error de conexión serie: {e}")
            return False

    def desconectar(self) -> None:
        """Cierra el puerto serie liberando el descriptor."""
        self.detener_adquisicion()
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

    def enviar_comando(self, comando: str) -> bool:
        """Transmite una orden en texto ASCII con salto de línea al microcontrolador."""
        if not self._serial or not self._serial.is_open:
            return False
        try:
            trama = f"{comando.strip()}\n".encode("utf-8")
            self._serial.write(trama)
            self._serial.flush()
            logging.info(f"Comando serie transmitido: {comando.strip()}")
            return True
        except Exception as e:
            logging.error(f"Falla de transmisión serial: {e}")
            self.alerta_seguridad.emit(f"Error de transmisión: {e}")
            return False

    def run(self) -> None:
        """Ciclo de lectura continua en hilo dedicado para recepción sin bloqueo."""
        if not self._serial or not self._serial.is_open:
            if not self.conectar(self.puerto, self.baudrate):
                return

        with QMutexLocker(self._mutex):
            self._activo = True

        self.enviar_comando(f"SET_RATE {int(self.frecuencia_hz)}")
        self.enviar_comando("START")
        self.estado_cambiado.emit(EstadoInstrumentacion.GRABANDO)

        while True:
            with QMutexLocker(self._mutex):
                if not self._activo:
                    break

            try:
                if self._serial.in_waiting > 0:
                    linea_cruda = self._serial.readline()
                    linea = linea_cruda.decode("utf-8", errors="ignore").strip()
                    if not linea:
                        continue

                    # Tramas esperadas: "tiempo_s,voltaje_v" o "t_ms,voltaje_mv"
                    partes = linea.split(",")
                    if len(partes) >= 2:
                        try:
                            t = float(partes[0].strip())
                            v = float(partes[1].strip())

                            # Alerta de saturación de sensor / ADC (ej: >= 4.95V en canal 5V)
                            if v >= 4.95:
                                self.alerta_seguridad.emit(f"¡PELIGRO! Saturación de ADC detectada: {v:.3f} V")

                            self.nueva_muestra.emit(t, v)
                        except ValueError:
                            # Trama de telemetría corrupta o mensaje informativo de depuración
                            logging.debug(f"Mensaje no numérico del ESP32: {linea}")
                else:
                    time.sleep(0.001)  # Ceder tiempo a la CPU

            except serial.SerialException as e:
                logging.error(f"Pérdida de enlace serie con el banco: {e}")
                self.alerta_seguridad.emit(f"DESCONEXIÓN: Enlace serie interrumpido: {e}")
                self.estado_cambiado.emit(EstadoInstrumentacion.ABORTADO)
                break
            except Exception as e:
                logging.error(f"Excepción en bucle serie: {e}")
                time.sleep(0.01)

        with QMutexLocker(self._mutex):
            self._activo = False

        self.enviar_comando("STOP")

    def iniciar_adquisicion(self) -> None:
        if not self.isRunning():
            self.start()

    def detener_adquisicion(self) -> None:
        with QMutexLocker(self._mutex):
            self._activo = False
        self.wait(1000)

    def abortar(self) -> None:
        """Comando de seguridad máxima: envía ABORT prioritario y corta."""
        self.enviar_comando("ABORT")
        self.estado_cambiado.emit(EstadoInstrumentacion.ABORTADO)
        with QMutexLocker(self._mutex):
            self._activo = False

    def tarar(self) -> None:
        self.enviar_comando("TARE")

    def armar(self) -> None:
        self.enviar_comando("ARM")
        self.estado_cambiado.emit(EstadoInstrumentacion.ARMADO)

    def disparar(self) -> None:
        self.enviar_comando("FIRE")
        self.estado_cambiado.emit(EstadoInstrumentacion.CUENTA_REGRESIVA)
