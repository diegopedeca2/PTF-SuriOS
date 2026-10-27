# PFT-SuriOS — SPRINT 4 TFT

## Resultado de validación

Fecha: 2026-10-27

La pantalla EstarDyn TFT de 3,5 pulgadas mostró correctamente contenido
generado por el ESP32-S3 mediante SPI.

Prueba ejecutada: `s3/tft_orientation_test.py`

Elementos observados:

- Retroiluminación blanca funcionando con BL conectado a 3V3.
- Texto `TOP`, `BOTTOM`, `LANDSCAPE` y `480 X 320`.
- Flecha orientable apuntando hacia la parte superior.
- Bloques de color rojo, verde, azul y blanco.
- Imagen estable durante la prueba.
- La imagen permaneció visible después del reinicio suave del S3.

## Cableado validado

| ESP32-S3 | TFT |
|---|---|
| 3V3 | VCC |
| 3V3 | BL |
| GND | GND |
| GPIO12 | SCL |
| GPIO11 | SDA / MOSI |
| GPIO14 | RST |
| GPIO9 | DC |
| GPIO10 | CS |
| Sin conexión | SDA-D |

Resolución probada: **480 x 320 en orientación horizontal**.

## Conservación del firmware existente

- El funcionamiento UART/BLE de `firmware/SPRINT_3_BLE/s3/main.py` se
  conservó.
- La prueba inicial se ejecutó como archivo independiente.
- Después se añadió una inicialización TFT protegida al `main.py`: si la
  pantalla falla, el firmware continúa con UART/BLE.
- La pantalla se inicializa desde `tft_display.py` al arrancar el S3.
- Se realizó un reinicio suave y el S3 siguió respondiendo por USB.
- Se validó un arranque en frío desconectando y reconectando el USB; la TFT
  volvió a mostrar el contenido de arranque correctamente.

## Integración básica validada

La pantalla muestra `PFT-SURIOS`, una flecha de orientación, `TFT READY` y
`READY` al arrancar junto con el firmware S3. La integración no usa ningún
GPIO del WROOM ni modifica el firmware del radar.

## Última prueba visual

Se preparó el asset de Brotherhood con fondo negro y el texto exacto
`AD VICTORIAM` en verde:

- PNG final: `assets/branding/brotherhood/brotherhood_emblem_pipgreen_ad_victoriam_480x320.png`
- Formato de transferencia TFT: `assets/branding/brotherhood/brotherhood_emblem_pipgreen_ad_victoriam_480x320.rle565`
- Resolución: **480 x 320**.
- Resultado visual confirmado en la TFT.

Durante esta prueba se detectó que `INVON` invertía negro y verde/magenta.
Se corrigió el driver a `INVOFF` (`0x20`) y se confirmó de nuevo el fondo
negro y el emblema verde.

## Estado final con WROOM

- Firmware `SPRINT_2_DETECTOR/wroom` compilado y cargado correctamente en
  COM4.
- S3 operativo en COM5 con la TFT conectada.
- Intercambio `S3,HELLO` / `WROOM,ACK` confirmado.
- La TFT mantuvo `PFT-SURIOS` y `READY` durante la comunicación.

## Observación eléctrica

BL funciona conectado al raíl 3V3 del ESP32-S3. No se conectó BL a ningún
GPIO. La corriente exacta de la retroiluminación todavía no se ha medido.
