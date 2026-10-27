# SPRINT 5 — Integración final TFT y radar Watch Ultra

**Proyecto:** PFT-SuriOS V0
**Apertura:** 2026-10-27
**Cierre:** 2026-10-27
**Estado:** CERRADO — validado visualmente y documentado

## Alcance

Este sprint integra la pantalla EstarDyn TFT de 3,5 pulgadas en el ESP32-S3
N16R8 y reproduce en ella la vista funcional del radar Watch Ultra de WristOS.
No se modificó el firmware del ESP32-WROOM ni el protocolo del radar.

## Resultado final

- La TFT ST7796S muestra contenido generado por el S3 en orientación horizontal.
- La resolución lógica utilizada es **480 × 320 píxeles**; el panel se anuncia
  como 320 × 480 en orientación vertical.
- Se validaron colores, texto, estabilidad, arranque en frío y orientación.
- La retroiluminación BL funciona conectada a 3V3 en este módulo concreto.
- La escena final usa estética PIP de WristOS: fondo negro, paleta verde/azul,
  objetivos rojos y emblema Brotherhood atenuado.
- El radar muestra un cono de 120°, seis anillos de distancia y los objetivos
  reales recibidos desde el WROOM.
- Se eliminó el texto dinámico de cada lectura y la animación de aguja en la
  versión final para priorizar estabilidad y legibilidad.
- El usuario confirmó visualmente la versión final, incluido el ajuste de
  intensidad del emblema.

## Esquema de conexiones validado

### ESP32-S3 N16R8 → TFT EstarDyn ST7796S

| ESP32-S3 | TFT | Función |
|---|---|---|
| 3V3 | VCC | Alimentación de la lógica TFT |
| 3V3 | BL | Retroiluminación validada |
| GND | GND | Masa común |
| GPIO12 | SCL | SPI SCK |
| GPIO11 | SDA | SPI MOSI |
| GPIO14 | RST | Reset TFT |
| GPIO9 | DC | Datos/comandos |
| GPIO10 | CS | Chip select |
| Sin conexión | SDA-D | No utilizado en SPI |

La tensión medida en VCC fue de 3,31 V. BL no se conectó a un GPIO ni a PWM:
se validó directamente a 3V3 únicamente en esta unidad. La corriente interna
de la retroiluminación no se midió y no se generaliza este resultado a otros
módulos ST7796S.

### ESP32-WROOM → ESP32-S3

| ESP32-WROOM | ESP32-S3 | Función |
|---|---|---|
| GPIO25 TX | GPIO16 RX | UART WROOM → S3 |
| GPIO26 RX | GPIO17 TX | UART S3 → WROOM |
| GND | GND | Masa común |

UART: **115200 baudios, 8N1**.

### Radar HLK-LD2450 → ESP32-WROOM

| Radar HLK-LD2450 | ESP32-WROOM | Función |
|---|---|---|
| TX | GPIO16 / UART2 RX | Datos radar → WROOM |
| RX | GPIO17 / UART2 TX | Datos WROOM → radar |
| 5V | 5V/VIN | Alimentación radar |
| GND | GND | Masa común |

UART radar: **256000 baudios, 8N1**. Este cableado y el firmware del WROOM
quedan fuera de los cambios de este sprint.

## Firmware y artefactos

- S3 integrado: `firmware/SPRINT_3_BLE/s3/main.py`.
- Driver ST7796S: `firmware/SPRINT_4_TFT/s3/tft_display.py`.
- Máscara binaria del emblema para MicroPython:
  `firmware/SPRINT_4_TFT/s3/brotherhood_emblem_pipgreendim.bin`.
- Pruebas independientes:
  - `firmware/SPRINT_4_TFT/s3/tft_orientation_test.py`
  - `firmware/SPRINT_4_TFT/s3/tft_asset_test.py`
- Resultado detallado de la validación eléctrica y visual:
  `firmware/SPRINT_4_TFT/RESULTADOS.md`.

La inicialización TFT está protegida: si el driver o la pantalla fallan, el
S3 continúa con UART y BLE. El WROOM sigue siendo responsable del radar y de
su BLE existente.

## Auditoría realizada

- Sintaxis Python comprobada para `main.py` y `tft_display.py`.
- Firmware WROOM no modificado en este sprint.
- Enlace `S3,HELLO` / `WROOM,ACK` confirmado durante la integración.
- Paquetes `WROOM,RADAR` recibidos y representados en la TFT.
- Puertos utilizados durante las pruebas: WROOM COM4 y S3 COM5.
- No se incluyeron en el commit los ZIP de hardware ni archivos temporales de
  inspección.

## Criterios de finalización

- [x] Pantalla enciende con BL conectado a 3V3.
- [x] El S3 muestra contenido gráfico generado por firmware.
- [x] Colores y texto validados sin errores evidentes.
- [x] Orientación horizontal 480 × 320 validada.
- [x] Radar funcional con objetivos reales.
- [x] Integración sin modificar WROOM ni radar.
- [x] Esquema de conexiones incluido en la documentación.

## Fuera de alcance

Quedan para un sprint posterior la interfaz definitiva de PFT-SuriOS, los
botones físicos, el control PWM de BL y cualquier rediseño del protocolo del
radar o del firmware WROOM.
