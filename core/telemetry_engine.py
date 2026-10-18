"""Motor de procesamiento y cálculo de telemetría para banco de pruebas de motores de cohete.

Este módulo implementa la lógica de cálculo desacoplada de la interfaz gráfica (sin dependencias de PyQt),
incluyendo calibración de tara, filtrado por umbral de ruido, integración temporal de impulso,
detección de pérdida de paquetes y estadísticas globales.
"""

# Importa el sistema de logging para registrar eventos, advertencias y errores del motor.
import logging
# Importa time para obtener timestamps del sistema y calcular tiempos relativos entre lecturas.
import time
# Importa deque para mantener una ventana deslizante de muestras recientes con tamaño fijo.
from collections import deque
# Importa dataclass para crear clases con inicialización automática y almacenamiento estructurado.
from dataclasses import dataclass
# Importa List y Optional para tipar colecciones y valores nulos con claridad.
from typing import List, Optional

# Importa NumPy para aplicar filtros robustos como la mediana sobre la ventana de lecturas.
import numpy as np

# Importa constantes de calibración y umbral global del proyecto.
from config.constants import FILTER_WINDOW_SIZE, GRAVITY, THRUST_THRESHOLD
# Importa los tipos y función de clasificación del motor para convertir impulso en categoría NAR.
from core.motor_classifier import MotorClassification, clasificar_motor

# Crea el logger específico de este módulo para poder rastrear eventos de depuración y advertencias.
logger = logging.getLogger(__name__)


@dataclass
class ProcessedReading:
    """Datos procesados de una lectura individual de telemetría.

    Attributes:
        timestamp: Tiempo transcurrido en segundos desde el inicio de la prueba.
        thrust_n: Empuje neto filtrado en Newtons (N).
        thrust_kg: Empuje neto en kilogramos-fuerza (kgf).
        impulse_ns: Impulso total acumulado en Newtons-segundo (N·s).
        impulse_kgs: Impulso total acumulado en kilogramos-segundo (kg·s).
        classification: Clasificación NAR correspondiente al impulso acumulado.
        rssi: Intensidad de señal recibida en dBm (-999 si no aplica).
        seq: Número de secuencia incremental del paquete recibido.
    """

    # Almacena el instante relativo de la muestra dentro de la sesión actual.
    timestamp: float
    # Guarda el empuje neto filtrado y ajustado a la tara, medido en Newton.
    thrust_n: float
    # Guarda el empuje expresado en kilogramos-fuerza para mostrarlo en unidades más humanas.
    thrust_kg: float
    # Guarda el impulso acumulado hasta este punto, en Newton-segundo.
    impulse_ns: float
    # Guarda el impulso acumulado convertido a kilogramos-segundo.
    impulse_kgs: float
    # Guarda la categoría obtenida por la clasificación NAR según el impulso total.
    classification: MotorClassification
    # Guarda la intensidad de la señal recibida del paquete si está disponible.
    rssi: int
    # Guarda el número secuencial del paquete que originó esta lectura.
    seq: int


@dataclass
class TelemetryStats:
    """Resumen estadístico del estado acumulado de la telemetría del motor.

    Attributes:
        max_thrust_n: Empuje máximo registrado en Newtons (N).
        max_thrust_kg: Empuje máximo registrado en kilogramos-fuerza (kgf).
        total_impulse_ns: Impulso total acumulado en Newtons-segundo (N·s).
        total_impulse_kgs: Impulso total acumulado en kilogramos-segundo (kg·s).
        classification: Clasificación NAR basada en el impulso total acumulado.
        lost_packets: Cantidad de paquetes de telemetría perdidos detectados por secuencia.
        data_points: Número total de muestras de datos registradas.
    """

    # Almacena el valor máximo de empuje registrado durante la sesión, en Newton.
    max_thrust_n: float
    # Guarda el valor máximo de empuje convertido a kilogramos-fuerza.
    max_thrust_kg: float
    # Guarda el impulso total acumulado en Newton-segundo durante el rango analizado.
    total_impulse_ns: float
    # Guarda el impulso total acumulado convertido a kilogramos-segundo.
    total_impulse_kgs: float
    # Guarda la clasificación NAR resultante del impulso calculado.
    classification: MotorClassification
    # Guarda la cantidad total de paquetes perdidos detectados por huecos en secuencia.
    lost_packets: int
    # Guarda la cantidad de puntos de muestra incluidos en la estadística.
    data_points: int


class TelemetryEngine:
    """Motor de cálculo y gestión de datos de telemetría para banco de pruebas.

    Encapsula el estado de las series temporales, el cómputo de impulso acumulado,
    la compensación por tara, la conmutación de unidades de visualización y el seguimiento
    de continuidad en los paquetes recibidos.
    """

    # Define el constructor de la clase, inicializando el estado interno y validando parámetros.
    def __init__(
        self,
        thrust_threshold: float = THRUST_THRESHOLD,
        filter_window_size: int = FILTER_WINDOW_SIZE,
    ) -> None:
        """Inicializa una nueva instancia del motor de telemetría.

        Args:
            thrust_threshold: Umbral mínimo de empuje en Newtons para filtrar
                ruido basal de la celda de carga. Por defecto THRUST_THRESHOLD.
        """
        # Verifica que el tamaño de la ventana de filtrado sea válido: positivo e impar.
        if filter_window_size < 1 or filter_window_size % 2 == 0:
            # Lanza un error para evitar configuraciones que puedan distorsionar la mediana.
            raise ValueError("filter_window_size debe ser un entero impar positivo.")

        # Guarda el nivel mínimo que se considerará como empuje real y no ruido.
        self.thrust_threshold: float = thrust_threshold
        # Guarda la cantidad de muestras usadas en el filtro por mediana.
        self.filter_window_size: int = filter_window_size
        # Guarda los instantes temporales de cada lectura en segundos desde el inicio.
        self.time_data: List[float] = []
        # Guarda los valores de empuje filtrados en Newtons por muestra.
        self.thrust_n: List[float] = []
        # Guarda el impulso acumulado en cada instante, en Newton-segundo.
        self.impulse_data: List[float] = []
        # Mantiene la ventana móvil de lecturas crudas para aplicar mediana en cada ciclo.
        self.raw_readings: deque[float] = deque(maxlen=filter_window_size)
        # Guarda todo el historial bruto para cálculo posterior de tara.
        self.raw_history: List[float] = []
        # Guarda el offset compensado por la tara de la celda de carga.
        self.tare_offset: float = 0.0
        # Guarda el instante de inicio de la prueba o None si aún no se ha inicializado.
        self.start_time: Optional[float] = None
        # Guarda el último número de secuencia recibido para detectar pérdidas.
        self.last_seq: int = -1
        # Guarda la cantidad total de paquetes faltantes detectados.
        self.lost_packets: int = 0
        # Indica si la visualización activa debe mostrarse en kilogramos-fuerza o Newtons.
        self.is_kg: bool = False

    # Procesa una lectura nueva del sensor y devuelve un registro ya limpio y clasificado.
    def process_reading(self, newtons: float, seq: int, rssi: int) -> ProcessedReading:
        """Procesa una muestra de telemetría cruda y actualiza las series temporales.

        Calcula el tiempo transcurrido desde el inicio, detecta paquetes faltantes a partir
        del número de secuencia, aplica la compensación de tara y el umbral de ruido, e
        integra numéricamente el impulso acumulado.

        Args:
            newtons: Medición de fuerza bruta en Newtons proveniente del sensor.
            seq: Identificador secuencial del paquete de datos.
            rssi: Nivel de potencia de señal recibida en dBm (-999 para conexión alámbrica).

        Returns:
            ProcessedReading: Objeto con los datos procesados, convertidos y clasificados.
        """
        # Obtiene el timestamp actual del sistema para medir el tiempo relativo de la prueba.
        now = time.time()
        # Si aún no hay inicio de medición, establece el momento actual como referencia.
        if self.start_time is None:
            self.start_time = now
        # Calcula el tiempo transcurrido desde el inicio de la prueba.
        t = now - self.start_time

        # Monitoreo de pérdidas de paquetes según número de secuencia.
        if self.last_seq != -1 and seq > self.last_seq + 1:
            # Calcula cuántos paquetes faltan entre la última secuencia y la nueva.
            diff = seq - self.last_seq - 1
            # Acumula los paquetes perdidos en el estadístico general del motor.
            self.lost_packets += diff
            # Registra la pérdida para facilitar la depuración durante la prueba.
            logger.warning(
                "Salto de secuencia detectado: %d -> %d (+%d paquetes perdidos)",
                self.last_seq,
                seq,
                diff,
            )
        # Actualiza el último número de secuencia para continuar detectando huecos futuros.
        self.last_seq = seq

        # La tara se conserva en señal firmada. abs() aquí convertiría ruido
        # negativo en empuje positivo y crearía picos artificiales.
        # Añade la medición cruda a la ventana de filtrado reciente.
        self.raw_readings.append(newtons)
        # Añade la lectura cruda al historial completo para poder recalcular la tara.
        self.raw_history.append(newtons)
        # Aplica la mediana sobre la ventana reciente para reducir picos causados por ruido puntual.
        filtered_newtons = float(np.median(self.raw_readings))
        # Resta la tara para compensar el offset de la celda de carga.
        compensated_newtons = filtered_newtons - self.tare_offset
        # Evita empujes negativos, porque no tienen sentido físico en esta medición.
        thrust_clean = max(0.0, compensated_newtons)
        # Si el valor está por debajo del umbral, lo considera ruido y lo pone a cero.
        if thrust_clean < self.thrust_threshold:
            thrust_clean = 0.0

        # Guarda el instante temporal de esta muestra.
        self.time_data.append(t)
        # Guarda el empuje limpio asociado a este instante.
        self.thrust_n.append(thrust_clean)

        # Integración numérica de impulso (N·s) usando el método de suma trapezoidal incremental.
        if len(self.thrust_n) >= 2:
            # Calcula el intervalo de tiempo entre la muestra actual y la anterior.
            dt = self.time_data[-1] - self.time_data[-2]
            # Evita intervalos temporales negativos por errores de reloj o ordenación.
            if dt < 0.0:
                dt = 0.0
            # Obtiene el impulso previo acumulado hasta la muestra anterior.
            prev_imp = self.impulse_data[-1] if self.impulse_data else 0.0
            # Suma el nuevo aporte de impulso = empuje × intervalo de tiempo.
            current_impulse_ns = prev_imp + thrust_clean * dt
            # Guarda el impulso acumulado actualizado.
            self.impulse_data.append(current_impulse_ns)
        else:
            # En la primera muestra, el impulso acumulado aún es cero.
            current_impulse_ns = 0.0
            # Guarda este valor inicial para mantener la serie consistente.
            self.impulse_data.append(0.0)

        # Conversiones de unidades físicas y clasificación NAR.
        # Convierte el empuje a kilogramos-fuerza dividiendo por la gravedad estándar.
        thrust_kg = thrust_clean / GRAVITY
        # Convierte el impulso acumulado a kilogramos-segundo para visualización equivalente.
        current_impulse_kgs = current_impulse_ns / GRAVITY
        # Clasifica el motor según el impulso total acumulado en este instante.
        classification = clasificar_motor(current_impulse_ns)

        # Devuelve un objeto con todos los resultados procesados y listos para la UI.
        return ProcessedReading(
            timestamp=t,
            thrust_n=thrust_clean,
            thrust_kg=thrust_kg,
            impulse_ns=current_impulse_ns,
            impulse_kgs=current_impulse_kgs,
            classification=classification,
            rssi=rssi,
            seq=seq,
        )

    # Ajusta la tara de la celda según la mediana de las últimas muestras.
    def tare(self) -> None:
        """Establece la tara con la mediana de las últimas 10 lecturas crudas.

        Requiere más de 5 muestras para obtener una referencia robusta al ruido.
        """
        # Solo calcula tara si hay suficientes muestras históricas para que la estimación sea estable.
        if len(self.raw_history) > 5:
            # Usa la mediana de las últimas 10 lecturas para compensar ruido sin exagerar cambios puntuales.
            self.tare_offset = float(np.median(self.raw_history[-10:]))
            # Limpia la ventana de filtrado para comenzar a medir con el nuevo offset.
            self.raw_readings.clear()
            # Registra el valor de tara calculado para trazabilidad.
            logger.info("Tara establecida en: %.4f N", self.tare_offset)
        else:
            # El sistema no tiene suficiente evidencia para ajustar la tara con fiabilidad.
            logger.warning("Muestras insuficientes para tara (se requieren más de 5 lecturas).")

    # Reinicia el estado completo del motor y deja todo listo para una nueva prueba.
    def clear(self) -> None:
        """Reinicia todos los datos acumulados, marcas temporales y contadores de la prueba."""
        # Borra las marcas temporales de medición.
        self.time_data.clear()
        # Borra la serie de empuje para empezar sin histórico previo.
        self.thrust_n.clear()
        # Borra la serie de impulso acumulado para reiniciar la cuenta.
        self.impulse_data.clear()
        # Borra la ventana temporal de filtro para iniciar con una lectura limpia.
        self.raw_readings.clear()
        # Borra el historial completo de lecturas crudas para eliminar la tara previa.
        self.raw_history.clear()
        # Restablece la compensación de tara a cero.
        self.tare_offset = 0.0
        # Reinicia el instante de referencia para comenzar el conteo desde cero.
        self.start_time = None
        # Reinicia la última secuencia recibida para no interpretar datos viejos como continuidad.
        self.last_seq = -1
        # Reinicia el conteo de paquetes perdidos al valor inicial.
        self.lost_packets = 0
        # Registra que el estado de la telemetría fue reiniciado correctamente.
        logger.info("Datos del motor de telemetría reiniciados.")

    # Cambia la unidad de visualización activa entre Newtons y kilogramos-fuerza.
    def toggle_unit(self) -> bool:
        """Alterna el estado de visualización entre kilogramos-fuerza y Newtons.

        Returns:
            bool: True si la unidad activa es kilogramos, False si es Newtons.
        """
        # Invierte el estado booleano actual de orientación de unidades.
        self.is_kg = not self.is_kg
        # Registra el cambio de unidad para depuración.
        logger.debug("Unidad conmutada: is_kg=%s", self.is_kg)
        # Devuelve el nuevo estado para que la UI o el llamador lo use inmediatamente.
        return self.is_kg

    # Calcula un resumen estadístico válido para un rango temporal concreto.
    def get_trim_stats(self, t_start: float, t_end: float) -> TelemetryStats:
        """Calcula y devuelve las estadisticas consolidadas de un rango de tiempo.

        Args:
            t_start: Tiempo de inicio en segundos.
            t_end: Tiempo de fin en segundos.

        Returns:
            TelemetryStats con los datos exclusivos del rango seleccionado.
        """
        # Si no hay datos o el rango es inválido, devuelve un resultado nulo sin errores.
        if not self.time_data or t_start >= t_end:
            # Devuelve un objeto vacío con clasificación base en cero.
            return TelemetryStats(0.0, 0.0, 0.0, 0.0, clasificar_motor(0.0), 0, 0)

        # Selecciona solo los índices cuyas marcas temporales quedan dentro del intervalo pedido.
        indices = [i for i, t in enumerate(self.time_data) if t_start <= t <= t_end]
        # Si no hay ninguna muestra dentro del rango, devuelve un resultado vacío.
        if not indices:
            # Devuelve un objeto estadístico base con valores en cero.
            return TelemetryStats(0.0, 0.0, 0.0, 0.0, clasificar_motor(0.0), 0, 0)

        # Extrae el empuje del rango seleccionado para calcular su máximo absoluto.
        trimmed_thrust = [self.thrust_n[i] for i in indices]
        # Obtiene el máximo empuje para ese tramo temporal.
        max_thrust_n = max(trimmed_thrust) if trimmed_thrust else 0.0
        # Convierte el máximo empuje a kilogramos-fuerza para la representación alternativa.
        max_thrust_kg = max_thrust_n / GRAVITY

        # Calcular impulso numericamente en el rango.
        # Inicializa el impulso acumulado del segmento seleccionado.
        total_impulse_ns = 0.0
        # Guarda el instante previo durante la iteración para calcular el delta de tiempo.
        prev_t = None
        # Itera sobre cada muestra del rango para integrar el impulso por intervalos.
        for i in indices:
            # Toma el tiempo de la muestra actual.
            t = self.time_data[i]
            # Toma el empuje actual de la muestra.
            n = self.thrust_n[i]
            # Si existe una muestra previa, calcula el intervalo de tiempo y acumula el impulso.
            if prev_t is not None:
                dt = t - prev_t
                total_impulse_ns += n * dt
            # Actualiza el instante previo para la siguiente muestra.
            prev_t = t

        # Convierte el impulso total del rango a kilogramos-segundo.
        total_impulse_kgs = total_impulse_ns / GRAVITY
        # Clasifica el impulso del rango con la misma lógica que la sesión completa.
        classification = clasificar_motor(total_impulse_ns)

        # Devuelve un resumen específico para ese intervalo.
        return TelemetryStats(
            max_thrust_n=max_thrust_n,
            max_thrust_kg=max_thrust_kg,
            total_impulse_ns=total_impulse_ns,
            total_impulse_kgs=total_impulse_kgs,
            classification=classification,
            lost_packets=0,
            data_points=len(indices),
        )

    # Calcula el resumen completo de la sesión actual de telemetría.
    def get_stats(self) -> TelemetryStats:
        """Calcula y devuelve las estadísticas consolidadas de la sesión actual de telemetría.

        Returns:
            TelemetryStats: Objeto con empuje máximo, impulso total, clasificación NAR,
            paquetes perdidos y número de puntos registrados.
        """
        # Si ya hay datos registrados, calcula las métricas reales de la sesión.
        if self.thrust_n:
            # Obtiene el empuje máximo observado en toda la serie.
            max_thrust_n = max(self.thrust_n)
            # Convierte el valor máximo a kilogramos-fuerza para visualización alternativa.
            max_thrust_kg = max_thrust_n / GRAVITY
            # Recupera el impulso acumulado total hasta el último punto medido.
            total_impulse_ns = self.impulse_data[-1] if self.impulse_data else 0.0
            # Convierte el impulso total a kilogramos-segundo.
            total_impulse_kgs = total_impulse_ns / GRAVITY
            # Clasifica la sesión según el impulso total final acumulado.
            classification = clasificar_motor(total_impulse_ns)
        else:
            # Si no hay muestras, mantiene todos los valores en cero y clasifica como nulo.
            max_thrust_n = 0.0
            max_thrust_kg = 0.0
            total_impulse_ns = 0.0
            total_impulse_kgs = 0.0
            classification = clasificar_motor(0.0)

        # Devuelve el resumen final con todos los campos completos y coherentes.
        return TelemetryStats(
            max_thrust_n=max_thrust_n,
            max_thrust_kg=max_thrust_kg,
            total_impulse_ns=total_impulse_ns,
            total_impulse_kgs=total_impulse_kgs,
            classification=classification,
            lost_packets=self.lost_packets,
            data_points=len(self.thrust_n),
        )

    # Propiedad que devuelve el factor para convertir Newtons a la unidad activa actualmente.
    @property
    def unit_factor(self) -> float:
        """Factor multiplicativo para convertir Newtons a la unidad activa (1/GRAVITY para kg, 1.0 para N)."""
        # Si la unidad activa es kgf, divide entre gravedad; si es Newton, conserva 1.0.
        return (1.0 / GRAVITY) if self.is_kg else 1.0

    # Propiedad que expone la serie temporal completa de tiempos medidos.
    @property
    def time_series(self) -> List[float]:
        """Serie temporal acumulada de lecturas en segundos."""
        # Devuelve la lista de tiempos transcurridos desde el inicio de la sesión.
        return self.time_data

    # Propiedad que expone la serie de empuje acumulada en Newtons.
    @property
    def thrust_series(self) -> List[float]:
        """Serie de empuje acumulada en Newtons."""
        # Devuelve la lista de empujes filtrados y limpios registrados por la sesión.
        return self.thrust_n

    # Propiedad que expone la serie de impulso acumulado en Newton-segundo.
    @property
    def impulse_series(self) -> List[float]:
        """Serie de impulso acumulada en Newtons-segundo."""
        # Devuelve la lista de impulsos acumulados a cada instante.
        return self.impulse_data
