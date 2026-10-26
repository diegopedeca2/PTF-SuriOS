# SPRINT 2 — DETECTOR local en ESP32-S3

**Proyecto:** PFT-SuriOS V0
**Fecha:** 2026-10-26
**Estado:** FASE DE DATOS COMPLETADA — TFT pendiente

## Objetivo

Preparar la ejecución local de `DETECTOR` en el ESP32-S3 utilizando los datos
del radar HLK-LD2450 procesados por el ESP32-WROOM.

La pantalla TFT todavía no está disponible, por lo que este sprint valida el
transporte y la decodificación de objetivos, no la representación visual.

## Relación con PIP-SuriOS

Las herramientas existentes se localizaron en `D:\WristOS\app`:

- `DetectorScreen.kt` representa los objetivos del radar.
- `RadarPacket.kt` define el paquete de radar de 17 bytes usado por la app.
- `MapTerrainScreen.kt` depende de mapas MBTiles y ubicación del teléfono.
- `PrsTrackingScreen.kt` y `BleScanner.kt` dependen de escaneo BLE y lógica
  Android.

Por ello, `DETECTOR` es la primera herramienta adecuada para ejecutar
localmente en el S3. `MAP - TERRAIN` y `P.R.S.` seguirán inicialmente ligados
al móvil, mientras se diseña qué información debe mostrar el S3.

## Implementación

Los archivos están separados de los del SPRINT 1:

- [Firmware SPRINT 2 del WROOM](../firmware/SPRINT_2_DETECTOR/wroom/src/main.cpp)
- [Programa SPRINT 2 del S3](../firmware/SPRINT_2_DETECTOR/s3/main.py)

El WROOM conserva:

- UART2 del radar en GPIO16/GPIO17 a 256000 baudios.
- UART1 del enlace en GPIO26 RX/GPIO25 TX a 115200 baudios.
- BLE del radar para la aplicación existente.
- Mensajes de diagnóstico y contadores.

Además, envía una línea por cada paquete de radar:

```text
WROOM,RADAR,version,secuencia,flags1,x1,y1,flags2,x2,y2,flags3,x3,y3
```

Los campos `flags` mantienen la semántica de la aplicación PIP-SuriOS:

- `0`: objetivo inactivo.
- `1`: objetivo en movimiento.
- `3`: objetivo retenido.

El S3 valida la versión, la secuencia, los campos numéricos y las pérdidas de
paquetes. Conserva los tres objetivos en `radar_targets`, listos para que una
futura pantalla los represente.

## Validaciones realizadas

1. El WROOM SPRINT 2 compiló correctamente.
2. El S3 SPRINT 2 arrancó con el firmware anterior del WROOM y mantuvo la
   comunicación de diagnóstico.
3. Tras actualizar el WROOM, el S3 recibió paquetes `WROOM,RADAR` sin errores.
4. Con un objetivo físico delante del radar se observaron 105 paquetes con
   objetivo durante una captura de aproximadamente 7 segundos.

Ejemplo real recibido por el S3:

```text
S3_RADAR seq=243 targets=[(1, 246, 707), (0, 0, 0), (0, 0, 0)]
```

Estadísticas observadas:

```text
S3_STATS ... radar_errors=0
S3_STATS ... missing=0 errors=0 radar_errors=0
LD2450 ... valid_targets=1
PFT_STATS ... errors=0
```

Los contadores `tx`, `rx` y `radar` son acumulativos desde el reinicio de
cada placa; la captura indicada fue una ventana de observación, no un reinicio
de los contadores.

## Pendiente

- Identificar la TFT cuando esté disponible.
- Confirmar tensión, retroiluminación, controlador y modo SPI.
- Diseñar la pantalla local de `DETECTOR`.
- Integrar los cinco botones con antirrebote.
- Definir qué datos de `MAP - TERRAIN` y `P.R.S.` deben intercambiarse con el
  móvil.
- Diseñar y probar el enlace BLE entre S3 y Galaxy A56.

No se ha realizado ningún cableado de pantalla ni se han utilizado GPIO
adicionales del S3.
