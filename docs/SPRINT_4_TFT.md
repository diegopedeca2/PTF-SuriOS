# SPRINT 4 TFT — Validación e integración básica

**Proyecto:** PFT-SuriOS V0
**Fecha de cierre:** 2026-10-27
**Estado:** CERRADO — validado físicamente

## Resultado

La pantalla EstarDyn TFT de 3,5 pulgadas quedó validada e integrada de forma
básica con el ESP32-S3:

- Retroiluminación BL funcionando conectada al raíl 3V3.
- SPI operativo con GPIO12 (SCL), GPIO11 (SDA/MOSI), GPIO14 (RST), GPIO9
  (DC) y GPIO10 (CS).
- Resolución 480 × 320 en orientación horizontal.
- Colores, texto, flecha de orientación y estabilidad comprobados.
- Arranque en frío validado.
- Firmware UART/BLE del S3 conservado y ampliado con inicialización TFT
  protegida.
- El WROOM y el radar no se modificaron durante la validación TFT.

## Última prueba visual

Se mostró correctamente el emblema Brotherhood sobre fondo negro con el texto
`AD VICTORIAM` en verde.

Archivos:

- `firmware/SPRINT_4_TFT/s3/tft_display.py`
- `firmware/SPRINT_4_TFT/s3/tft_orientation_test.py`
- `firmware/SPRINT_4_TFT/s3/tft_asset_test.py`
- `assets/branding/brotherhood/brotherhood_emblem_pipgreen_ad_victoriam_480x320.png`

## Firmware desplegado

El `main.py` del S3 quedó integrado con `tft_display.py`. La inicialización de
la pantalla está protegida: si la TFT falla, el firmware continúa con UART y
BLE.

El resultado detallado y el cableado están en:

`firmware/SPRINT_4_TFT/RESULTADOS.md`
