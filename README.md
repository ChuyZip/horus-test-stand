# Horus Space Lab - Banco de Pruebas de Motores Cohete 2026

Estación de control, adquisición de datos (DAQ) y análisis balístico en tiempo real para bancos de pruebas estáticas de motores cohete experimentales (propelentes sólidos APCP, KNSB, KNDX y motores híbridos/líquidos).

---

## 🚀 Características Principales

- **Adquisición a 200 Hz y Renderizado a 60 FPS:** Interfaz gráfica nativa basada en **PySide6** y **pyqtgraph** con aceleración por hardware y refresco desacoplado mediante `QThread` y `QTimer`.
- **Doble Canal de Telemetría (Desacoplado):**
  - **Modo SIMULACIÓN:** Modelo físico sintético de combustión estocástica a 200 Hz (fase pre-ignición, pico transitorio de presurización, meseta con inestabilidades acústicas de cámara, caída regresiva y corte).
  - **Modo HARDWARE REAL (Serial ESP32):** Conexión UART/USB con microcontrolador ESP32 con comandos normalizados (`ARM`, `DISARM`, `FIRE`, `TARE`, `STOP`, `ABORT`, `SET_RATE`) y recepción de tramas a alta velocidad.
- **Filtro Digital IIR Configurable:** Filtro pasabajas recursivo de primer orden (suavizado exponencial $y[k] = \alpha \cdot x[k] + (1-\alpha) \cdot y[k-1]$) con ajuste por frecuencia de corte $f_c$ y de muestreo $f_s$.
- **Cálculo Balístico en Tiempo Real:** Integración numérica por regla trapezoidal para impulso total ($I_{\text{total}}$ en N·s) con supresión de zona muerta para evitar integrar derivas térmicas del sensor en reposo.
- **Métricas Balísticas Avanzadas:** Cálculo automático de empuje promedio ($\bar{F}$), tiempo de combustión ($t_b$), impulso específico ($I_{sp} = I_{\text{tot}} / (m_p \cdot g_0)$), velocidad de regresión de quemado ($r$) y clasificación internacional Nakka/NAR (Clases 1/4A hasta O).
- **Base de Datos SQLite Integrada (`datos/`):** Almacenamiento relacional automático de todos los ensayos, propiedades de la muestra y series temporales completas.
- **Historial y Superposición Multi-Ensayo:** Tabla con búsqueda interactiva, superposición simultánea de múltiples curvas de empuje con leyendas y gráfica de envejecimiento de propelente (Isp vs. Días de vejez).
- **Asistente de Calibración N/V:** Ajuste lineal multipunto por mínimos cuadrados ordinarios ($F = m \cdot V + b$) con verificación de bondad de ajuste $R^2 \ge 0.998$ y guardado persistente en JSON.
- **Seguridad Rigurosa:** Parada de emergencia permanente **ABORTAR [F12]**, detección de saturación de ADC/sensor ($V \ge 4.95\text{ V}$) y máquina de estados finita (Listo 🟢, Armado 🟡, Cuenta regresiva 🟠, Grabando 🔴, Terminado 🔵, Abortado 🛑).

---

## 📦 Estructura del Proyecto

```text
BancoDePruebas2026/
├── core/                       # Núcleo de cálculo científico
│   ├── procesador_senal.py     # Filtro IIR, calibración N/V e integrador trapezoidal
│   └── balistica.py            # Fórmulas de Isp, empuje promedio y clases Nakka/NAR
├── comunicacion/               # Capa de adquisición de datos (DAQ)
│   ├── base.py                 # Clase base abstracta CanalDAQ(QThread)
│   ├── simulador.py            # Generador sintético de curva de motor cohete (200 Hz)
│   └── driver_serial.py        # Driver serial para microcontrolador ESP32
├── datos/                      # Capa de persistencia y base de datos
│   └── gestor_db.py            # Gestor SQLite (horus_test_stand.db) y exportador CSV
├── estilo/                     # Sistema de diseño centralizado
│   └── tema.py                 # Paleta aeroespacial (#1F1B4E, #BF3938), QSS y estados
├── ui/                         # Interfaz gráfica PySide6
│   ├── main_window.py          # Ventana principal (Header, Tabs horizontales y Footer)
│   ├── dialogos/               # Diálogos modales
│   │   ├── dialogo_muestra.py  # Ficha técnica previa de la muestra de propelente
│   │   └── dialogo_resultados.py # Reporte balístico post-ensayo y exportación
│   └── vistas/                 # Vistas apiladas en QStackedWidget
│       ├── vista_prueba.py     # Vista de prueba en vivo (4 KPIs + 3 gráficas pyqtgraph)
│       ├── vista_historial.py  # Historial SQLite, superposición y gráfica vs vejez
│       ├── vista_calibracion.py# Asistente de pesas patrón y ajuste lineal R²
│       └── vista_configuracion.py # Parámetros DAQ, selección de puerto serie y filtros
├── assets/                     # Recursos gráficos y logo transparente
│   └── logo.png
├── main.py                     # Punto de entrada con auto-parche Cocoa para macOS
└── requirements.txt            # Dependencias del entorno virtual
```

---

## 🛠️ Instalación y Requisitos

- Python 3.9 o superior.
- macOS (Apple Silicon M1/M2/M3/M4 o Intel), Linux o Windows.

1. Clona el repositorio e ingresa a la carpeta:
```bash
git clone https://github.com/ChuyZip/horus-test-stand.git
cd horus-test-stand
```

2. Crea y activa un entorno virtual:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

---

## 🖥️ Ejecución

Para iniciar la aplicación de instrumentación:

```bash
python main.py
```

O directamente mediante el binario del entorno virtual:

```bash
.venv/bin/python main.py
```

---

## 🧪 Protocolo de Operación en el Banco de Pruebas

1. **Caracterización de Muestra:** Abre la pestaña `🚀 Prueba en Vivo` y haz clic en `[📋 CARACTERIZAR MUESTRA]`. Introduce las dimensiones del grano, masa de propelente en gramos y condiciones ambientales.
2. **Selección de Modo:**
   - Para ensayos de prueba / demostración: utiliza el **Modo SIMULACIÓN**.
   - Para pruebas reales en banco: ve a `⚙️ Configuración`, selecciona **Modo HARDWARE REAL**, elige el puerto serie del ESP32 (`/dev/cu.usb*`) y presiona `Guardar`.
3. **Inicio del Ensayo:** Pulsa `[▶ INICIAR ENSAYO]`. La telemetría comenzará a fluir a 200 Hz y la curva de empuje se trazará en tiempo real marcando el pico máximo y el tiempo de ignición.
4. **Resultados Balísticos y Guardado:** Al finalizar el quemado, el panel balístico mostrará el $I_{sp}$, empuje medio y clasificación Nakka, permitiendo guardar el registro en la base de datos **SQLite** y exportarlo a **CSV**.
5. **Análisis Histórico:** En la pestaña `📊 Historial / Comparar`, selecciona dos o más ensayos para superponer sus curvas y evaluar la reproducibilidad entre lotes de producción.
