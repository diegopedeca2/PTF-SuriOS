# SPRINT 4 — DETECTOR local mediante el S3 sin pantalla TFT

**Proyecto:** PFT-SuriOS V0
**Fecha:** 2026-10-26
**Estado:** COMPLETADO — validado físicamente

## Objetivo

Integrar `DETECTOR` en el enlace ya validado del ESP32-S3, utilizando el
Galaxy A56 como pantalla provisional mientras la TFT y los botones físicos no
están disponibles.

## Decisiones de integración

- Se conserva la pantalla `DETECTOR` existente, que continúa usando el BLE
  directo del WROOM.
- Se añade una pantalla independiente `DETECTOR // S3`.
- La nueva pantalla usa `PftS3BleClient` y el mismo `RadarPacketCodec` de
  PIP-SuriOS.
- Al conectar, solicita al S3 la herramienta `DETECTOR` mediante
  `TOOL,DETECTOR`.
- Se muestran estado de conexión, recepción, secuencia, objetivos, paquetes
  perdidos y coordenadas.
- No se modifica el firmware del WROOM ni la UART del radar.

## Archivos principales

- `D:\WristOS\app\src\main\java\com\suri\pipsurios\ui\screens\PftS3DetectorScreen.kt`
- `D:\WristOS\app\src\main\java\com\suri\pipsurios\ui\screens\PftS3LinkScreen.kt`
- `D:\WristOS\app\src\main\java\com\suri\pipsurios\MainActivity.kt`

El acceso se encuentra en `TOOLS > PFT LINK // S3 > OPEN DETECTOR // S3`.

## Validación de software

- `:app:compileFullDebugKotlin`: correcto.
- `:app:assembleFullDebug`: correcto.
- APK instalado en el Galaxy A56 mediante ADB inalámbrico.
- Firmware del S3 utilizado: SPRINT 3 BLE ya validado.

## Validación física

1. La pantalla mostró el radar como conectado y recibiendo.
2. Al moverse delante de la antena apareció el objetivo.
3. El marcador `T1` mostró coordenadas cambiantes.
4. La comunicación BLE permaneció activa durante la prueba.

## Limitaciones pendientes

La TFT, los botones físicos y su asignación de GPIO todavía no están
disponibles. La pantalla A56 es una interfaz provisional para validar la
lógica de `DETECTOR`. Cuando llegue la TFT se deberá adaptar la presentación
visual y comprobar físicamente los botones, sin cambiar el protocolo ya
validado.

## Resultado

El SPRINT 4 queda **completado**. `DETECTOR` puede ejecutarse localmente en
el S3 y visualizarse en el A56 mediante la cadena:

```text
HLK-LD2450 → WROOM → UART → S3 → BLE → PIP-SuriOS
```
