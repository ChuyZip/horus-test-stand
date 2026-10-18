# Horus Space Lab - Banco de Pruebas 2026

Aplicacion de escritorio para adquirir, visualizar y analizar telemetria de empuje en bancos de prueba de motores de cohete. Horus recibe muestras en tiempo real, muestra las curvas de empuje e impulso, guarda los ensayos en CSV y permite comparar dos corridas.

## Funciones principales

- Telemetria en tiempo real por cable, LoRa o WiFi/UDP.
- Grafica de empuje e impulso acumulado, con lectura de coordenadas al pasar el cursor sobre un punto.
- Filtro de mediana de 5 muestras para reducir picos aislados y umbral de empuje para evitar que el ruido se integre como impulso.
- Cambio entre Newtons y kilogramos-fuerza en la vista en vivo y en el analizador.
- Indicadores de empuje actual, maximo, impulso, clase NAR, senal y paquetes perdidos. Cada indicador incluye ayuda contextual.
- Tare de la celda de carga, recorte de intervalos y exportacion del rango seleccionado con impulso recalculado.
- Autoguardado CSV con carpeta seleccionable y persistente.
- Ventana `ANALIZAR` para cargar un ensayo A y un ensayo B, superponer sus curvas y calcular cambios porcentuales de empuje maximo e impulso.
- Ventana `VOLT/KG` para caracterizar la celda con voltaje en mV, peso y cuentas crudas del HX711, incluyendo curvas contra tiempo y respuesta voltaje-peso.
- Ignicion protegida: requiere armar el sistema y confirmar un codigo temporal de cuatro digitos antes de enviar `FIRE`.
- Pantalla de inicio con identidad de Horus Space Lab.

## Requisitos

- Python 3.9 o superior.
- Una celda de carga y su sistema de adquisicion configurados para enviar los paquetes de telemetria.

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

Para ejecutar las pruebas automatizadas:

```bash
python -m pytest -q
```

## Flujo de operacion

1. Inicia Horus y selecciona el modo de conexion: `Cable`, `LoRa` o `WiFi`.
2. Conecta la fuente de telemetria. En WiFi, Horus escucha por UDP en el puerto `8888`.
3. Usa `TARE` sin carga para establecer el cero de la medicion.
4. Inicia la adquisicion; el autoguardado creara un CSV en la carpeta elegida con `CARPETA CSV`.
5. Exporta el ensayo completo o activa el recorte para guardar solo una parte de la corrida.
6. Abre `ANALIZAR`, carga los CSV en A y B y revisa las curvas y las variaciones de rendimiento.
7. Para caracterizar la celda, abre `VOLT/KG` antes de conectar por serie; por WiFi, los datagramas extendidos de 16 bytes se detectan automaticamente.

## Formato de telemetria

Los paquetes binarios de telemetria contienen el empuje como `float` de 4 bytes y un numero de secuencia `uint32` de 4 bytes. El numero de secuencia permite detectar paquetes perdidos. En modo LoRa se agrega el RSSI.

Los CSV exportados incluyen tiempo, empuje en Newtons y kilogramos-fuerza. Los CSV de recorte tambien incluyen el impulso acumulado recalculado desde el inicio del intervalo elegido.

El modo `VOLT/KG` recibe el paquete extendido `<ffiI`: peso en kg, voltaje en mV, cuenta cruda del HX711 y secuencia. Sus CSV incluyen esas cinco columnas junto con el tiempo de captura.

## Estructura

```text
BancoDePruebas2026/
|- communication/  Lectores serie y UDP, protocolos de conexion
|- config/         Constantes, estilos, configuracion y clases NAR
|- core/           Procesamiento, filtrado, integracion y clasificacion
|- persistence/    Autoguardado, carga y exportacion CSV
|- ui/             Ventana principal, dialogos y widgets PyQt6
|- tests/          Pruebas automatizadas
|- main.py         Punto de entrada
`- requirements.txt
```

## Seguridad de ignicion

La confirmacion por codigo reduce activaciones accidentales, pero no reemplaza procedimientos fisicos de seguridad. Antes de armar el sistema, verifica el area de prueba, las conexiones, el relevador y que no haya personas dentro de la zona de riesgo.

## Empaquetado

Para PyInstaller, usa `main.py` como punto de entrada e incluye los recursos graficos del proyecto, como `HSL_transparent.png`.
