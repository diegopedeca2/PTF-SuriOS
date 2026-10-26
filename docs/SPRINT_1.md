# SPRINT 1 — Validación UART ESP32-WROOM ↔ ESP32-S3

**Proyecto:** PFT-SuriOS V0
**Fecha:** 2026-10-26
**Estado:** COMPLETADO

## Objetivo

Validar físicamente la comunicación UART bidireccional entre el ESP32-WROOM
que controla el radar HLK-LD2450 y el ESP32-S3 que actuará como controlador
de la interfaz del PFT, sin modificar la UART del radar.

## Cableado utilizado

| ESP32-WROOM | ESP32-S3 |
|---|---|
| GND | GND |
| GPIO25 TX | GPIO16 RX |
| GPIO26 RX | GPIO17 TX |

La UART del radar permaneció conectada al WROOM:

| Función | WROOM |
|---|---:|
| Radar RX | GPIO16 / UART2 RX |
| Radar TX | GPIO17 / UART2 TX |
| Velocidad | 256000 baudios, 8N1 |

## Inspección previa

El firmware activo del WROOM no era MicroPython. El volcado de flash contenía
Arduino/ESP-IDF, NimBLE-Arduino y el texto `SuriOS Radar firmware V0.1`.
El código fuente correspondiente se localizó en:

`D:\WristOS\_retired-radar-20261025\hardware-RADAR-PROTOYPE`

La fuente confirmaba que GPIO25 y GPIO26 no estaban usados. La UART del radar
se mantuvo en `HardwareSerial(2)` con GPIO16/GPIO17.

El S3 ejecutaba MicroPython v1.19.1 con un `main.py` de demostración RGB.

## Copias de seguridad

- [Backup completo del WROOM](../outputs/wroom_flash_backup_sprint1_20261026.bin)
  4 MiB — SHA-256:
  `69b66e8e3675560174a7445aa05c54925bb39d044b891b1778bb38d1b14a438b`
- [Backup completo del S3](../outputs/s3_flash_backup_sprint1_20261026.bin)
  16 MiB — SHA-256:
  `d73b6dd5a15e469a30629798664fb6e9e5c0ee30ef2679d75858d97a72b6fb15`

No se modificó `boot.py` del S3 ni se alteró la conexión del radar.

## Implementación

Los archivos de prueba están separados por dispositivo en
[`firmware/SPRINT_1_UART`](../firmware/SPRINT_1_UART):

- WROOM: `wroom/src/main.cpp`
- S3: `s3/main.py`

El WROOM utiliza UART1 a 115200 baudios, 8N1, con RX=26 y TX=25. Su servicio
es no bloqueante y:

- transmite `WROOM,HELLO,...` cada segundo;
- recibe `S3,HELLO,...`;
- responde `WROOM,ACK,...`;
- informa `PFT_STATS tx=... rx=... errors=...` por USB.

El S3 transmite `S3,HELLO,...` cada segundo y valida los mensajes `HELLO` y
`ACK` del WROOM.

La compilación del WROOM terminó correctamente. Solo se mantuvo una
advertencia preexistente de NimBLE sobre una función obsoleta.

## Incidencia corregida

La primera ejecución del programa del S3 terminó con:

`TypeError: can't convert Pin to int`

MicroPython v1.19.1 de esta placa requiere que los pines UART se pasen como
números enteros. Se corrigió `tx=17` y `rx=16`, sin cambiar el cableado.

## Resultados físicos

### Prueba bidireccional inicial

Durante una captura de aproximadamente 9 segundos se observaron:

- WROOM recibiendo `S3,HELLO,0` hasta `S3,HELLO,7`.
- S3 recibiendo `WROOM,HELLO,...` y `WROOM,ACK,0` hasta `WROOM,ACK,7`.
- `errors=0` en ambos dispositivos.
- El contador del radar continuó aumentando.

### Prueba de estabilidad de 60 segundos

Contadores observados al finalizar la prueba:

```text
WROOM: PFT_STATS tx=329 rx=129 errors=0
S3:    S3_STATS tx=129 rx=259 errors=0
Radar: LD2450 frames=2270 valid_targets=0 BLE_clients=0
```

Durante la ventana de captura se observaron 60 mensajes nuevos del S3 y 120
respuestas/mensajes del WROOM. No aparecieron `Traceback`, `Guru Meditation`,
reinicios inesperados ni errores de protocolo.

## Resultado final

Se cumplen los criterios de este sprint:

- S3 recibe mensajes del WROOM: **sí**.
- WROOM recibe mensajes del S3: **sí**.
- Comunicación repetida sin errores relevantes: **sí**.
- Radar funcionando simultáneamente: **sí**.
- Reinicios inesperados o conflictos observados: **no**.
- Código y resultados guardados en el repositorio: **sí**.

El S3 queda temporalmente con el `main.py` de diagnóstico UART. El programa
RGB anterior puede recuperarse utilizando el backup completo del S3.

La necesidad de mantener pulsado `BOOT` durante la carga depende del circuito
de auto-programación de la placa; no se elimina mediante el firmware de
usuario. El proyecto de prueba usa 115200 baudios para hacer la carga manual
más fiable.
