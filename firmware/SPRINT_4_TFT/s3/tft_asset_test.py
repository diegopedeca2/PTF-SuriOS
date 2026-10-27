"""Display the Brotherhood visual test asset on the ST7796S TFT."""

from tft_display import ST7796S


IMAGE_PATH = "brotherhood_emblem_pipgreen_ad_victoriam_480x320.rle565"
WIDTH = 480
HEIGHT = 320


display = ST7796S()
display.init()
display.set_window(0, 0, WIDTH - 1, HEIGHT - 1)

display.cs.value(0)
display.dc.value(1)
pixel_count = 0
with open(IMAGE_PATH, "rb") as image_file:
    while True:
        header = image_file.read(4)
        if not header:
            break
        count = header[0] | (header[1] << 8)
        pixel = bytes((header[2], header[3]))
        while count:
            batch = min(count, 1024)
            display.spi.write(pixel * batch)
            pixel_count += batch
            count -= batch
display.cs.value(1)

print("TFT_ASSET_DONE {}x320 pixels={}".format(WIDTH, pixel_count))
