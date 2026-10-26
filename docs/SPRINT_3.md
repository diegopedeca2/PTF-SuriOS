# SPRINT 3 — Enlace BLE S3 ↔ aplicación móvil

**Proyecto:** PFT-SuriOS V0
**Fecha de inicio:** 2026-10-26
**Estado:** COMPLETADO — validado físicamente el 2026-10-26

## Objetivo

Preparar un enlace BLE independiente entre el ESP32-S3 y la aplicación PIP-
SuriOS del Galaxy A56, sin interferir con el BLE existente del WROOM ni con
la UART radar ↔ WROOM ↔ S3.

## Arquitectura elegida

- El S3 actúa como periférico BLE y servidor GATT.
- El Galaxy A56 actúa como central BLE y cliente GATT.
- El WROOM sigue siendo responsable del radar.
- El S3 recibe los objetivos por UART y puede cambiar la herramienta activa.
- `DETECTOR` puede funcionar localmente; `MAP - TERRAIN` y `P.R.S.` pueden
  recibir del móvil los datos que necesiten.

La documentación oficial de MicroPython 1.19.1 confirma que el ESP32 puede
trabajar como periférico BLE, servidor GATT, y registrar características con
lectura, escritura y notificaciones. También establece un tamaño inicial de
20 bytes para las características, por lo que los mensajes de control de esta
primera fase se mantienen cortos. [Documentación oficial de MicroPython 1.19.1](https://docs.micropython.org/en/v1.19.1/library/bluetooth.html)

## UUID del servicio S3

Estos UUID son distintos de los del WROOM (`9e5d0001...`):

```text
Servicio:       9e5d1001-7b3a-4c0f-91c2-245000000001
Eventos/TX:     9e5d1002-7b3a-4c0f-91c2-245000000001
Comandos/RX:    9e5d1003-7b3a-4c0f-91c2-245000000001
```

Nombre anunciado: `PFT-SuriOS S3`.

## Comandos iniciales

```text
PING
GET,STATUS
GET,TOOL
TOOL,DETECTOR
TOOL,MAP
TOOL,PRS
```

Respuestas iniciales:

```text
S3,PONG
S3,STAT,D,123,1
S3,TOOL,DETECTOR
S3,ERR,BAD_COMMAND
```

La cifra de `STAT` representa paquetes de radar recibidos y el último campo
representa clientes BLE conectados.

## Paquete binario de radar

Además de las respuestas de texto, el S3 notifica por la característica de
eventos un paquete de 17 bytes compatible con `RadarPacketCodec` de
PIP-SuriOS:

```text
byte 0: versión = 1
byte 1: secuencia
por cada uno de los 3 objetivos: flags, x_mm int16 little-endian,
                                  y_mm int16 little-endian
```

El paquete cabe en el tamaño inicial de 20 bytes de la característica BLE.
La aplicación lo decodifica y muestra la secuencia, el número de objetivos y
sus coordenadas.

## Código preparado

- [Servidor BLE S3](../firmware/SPRINT_3_BLE/s3/main.py)
- Cliente Android: `D:\WristOS\app\src\main\java\com\suri\pipsurios\pft\PftS3BleClient.kt`
- Pantalla de diagnóstico: `D:\WristOS\app\src\main\java\com\suri\pipsurios\ui\screens\PftS3LinkScreen.kt`

La pantalla aparece en `TOOLS > PFT LINK // S3` y permite enviar `PING`,
`STATUS`, `DETECTOR`, `MAP` y `P.R.S.`. También muestra las notificaciones de
radar recibidas por BLE. La variante `fullDebug` de PIP-SuriOS compila
correctamente y el APK de prueba se genera en:

`D:\WristOS\app\build\outputs\apk\full\debug\app-full-debug.apk`

El servidor BLE se cargó en el S3 y se reinició correctamente. Antes de
sobrescribir el archivo se guardó una copia local en:

`outputs/s3_main_before_sprint3_radar_ble_20261026.py`

El firmware del WROOM no se modificó en este SPRINT y la UART del radar no se
alteró.

## Validación física

Se realizaron las siguientes comprobaciones:

1. El APK actualizado se instaló en el Galaxy A56 mediante ADB inalámbrico.
2. La aplicación conectó al S3 y mostró `CONNECTED`.
3. `PING`, `STATUS` y la selección de `MAP`, `P.R.S.` y `DETECTOR`
   respondieron correctamente.
4. El A56 recibió paquetes binarios del radar por BLE. Al moverse delante de
   la antena aparecieron lecturas y coordenadas cambiantes.
5. Durante aproximadamente un minuto de movimiento repetido, la secuencia
   continuó avanzando, la conexión permaneció activa y no se observaron
   errores, reinicios ni desconexiones.
6. Las pruebas UART anteriores del SPRINT 1 y la detección de objetivos del
   SPRINT 2 se mantuvieron correctas: el radar siguió funcionando mientras el
   enlace entre placas estaba activo.

## Resultado y siguientes pasos

El SPRINT 3 queda **completado**. La cadena validada es:

```text
HLK-LD2450 → UART del WROOM → UART WROOM/S3 → BLE del S3 → PIP-SuriOS
```

`RadarBleClient` no se modificó y sigue reservado para el servicio BLE del
WROOM. El siguiente trabajo puede integrar esta conexión en las pantallas
reales de `DETECTOR`, `MAP - TERRAIN` y `P.R.S.`, además de la futura pantalla
TFT y los botones físicos.
