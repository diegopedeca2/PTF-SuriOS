"""PFT-SuriOS SPRINT 4: standalone ST7796S TFT orientation test.

This file is intentionally independent from the existing S3 UART/BLE firmware.
It uses the wiring already assigned to the TFT:

    GPIO12 -> SCL/SPI clock
    GPIO11 -> SDA/SPI MOSI
    GPIO14 -> RST
    GPIO9  -> DC
    GPIO10 -> CS
    3V3    -> VCC and BL
    GND    -> GND

SDA-D on the display header remains unused.
"""

from machine import Pin, SPI
import time


SPI_CLOCK = 12
SPI_MOSI = 11
TFT_RST = 14
TFT_DC = 9
TFT_CS = 10

WIDTH = 480
HEIGHT = 320


def rgb565(red, green, blue):
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


BLACK = rgb565(0, 0, 0)
WHITE = rgb565(255, 255, 255)
RED = rgb565(255, 40, 40)
GREEN = rgb565(40, 255, 100)
BLUE = rgb565(40, 120, 255)
CYAN = rgb565(20, 220, 220)
YELLOW = rgb565(255, 220, 40)


FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}


class ST7796S:
    def __init__(self):
        self.cs = Pin(TFT_CS, Pin.OUT)
        self.dc = Pin(TFT_DC, Pin.OUT)
        self.rst = Pin(TFT_RST, Pin.OUT)
        self.cs.value(1)
        self.dc.value(1)
        self.rst.value(1)

        try:
            self.spi = SPI(
                2,
                baudrate=40_000_000,
                polarity=0,
                phase=0,
                bits=8,
                firstbit=SPI.MSB,
                sck=Pin(SPI_CLOCK),
                mosi=Pin(SPI_MOSI),
            )
            self.spi_bus = 2
        except Exception:
            self.spi = SPI(
                1,
                baudrate=40_000_000,
                polarity=0,
                phase=0,
                bits=8,
                firstbit=SPI.MSB,
                sck=Pin(SPI_CLOCK),
                mosi=Pin(SPI_MOSI),
            )
            self.spi_bus = 1

    def command(self, command, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes((command,)))
        if data:
            self.dc.value(1)
            self.spi.write(data)
        self.cs.value(1)

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(30)
        self.rst.value(1)
        time.sleep_ms(120)

    def init(self):
        self.reset()
        self.command(0x01)
        time.sleep_ms(120)
        self.command(0x11)
        time.sleep_ms(120)

        self.command(0xF0, b"\xC3")
        self.command(0xF0, b"\x96")
        # 0x28 = landscape orientation with BGR colour order.
        self.command(0x36, b"\x28")
        self.command(0x3A, b"\x55")
        self.command(0xB4, b"\x01")
        self.command(0xB6, b"\x80\x02\x3B")
        self.command(0xE8, b"\x40\x8A\x00\x00\x29\x19\xA5\x33")
        self.command(0xC1, b"\x06")
        self.command(0xC2, b"\xA7")
        self.command(0xC5, b"\x18")
        self.command(0xE0, b"\xF0\x09\x0B\x06\x04\x15\x2F\x54\x42\x3C\x17\x14\x18\x1B")
        self.command(0xE1, b"\xE0\x09\x0B\x06\x04\x03\x2B\x43\x42\x3B\x16\x14\x17\x1B")
        self.command(0xF0, b"\x3C")
        self.command(0xF0, b"\x69")
        self.command(0x20)
        self.command(0x29)
        time.sleep_ms(20)

    def set_window(self, x0, y0, x1, y1):
        self.command(0x2A, bytes((x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)))
        self.command(0x2B, bytes((y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF)))
        self.command(0x2C)

    def fill_rect(self, x, y, width, height, color):
        if width <= 0 or height <= 0:
            return
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0
        if x + width > WIDTH:
            width = WIDTH - x
        if y + height > HEIGHT:
            height = HEIGHT - y
        if width <= 0 or height <= 0:
            return

        self.set_window(x, y, x + width - 1, y + height - 1)
        row = bytes((color >> 8, color & 0xFF)) * width
        self.cs.value(0)
        self.dc.value(1)
        for _ in range(height):
            self.spi.write(row)
        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, WIDTH, HEIGHT, color)

    def draw_text(self, x, y, text, color, scale=2):
        cursor = x
        for character in text:
            if character == " ":
                cursor += 6 * scale
                continue
            glyph = FONT.get(character)
            if glyph is None:
                cursor += 6 * scale
                continue
            for row, bits in enumerate(glyph):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        self.fill_rect(
                            cursor + column * scale,
                            y + row * scale,
                            scale,
                            scale,
                            color,
                        )
            cursor += 6 * scale

    def draw_up_arrow(self, center_x, top, head_width, head_height, shaft_width, shaft_height, color):
        for row in range(head_height):
            half_width = (row * head_width) // (2 * head_height)
            self.fill_rect(center_x - half_width, top + row, half_width * 2 + 1, 1, color)
        shaft_top = top + head_height
        self.fill_rect(
            center_x - shaft_width // 2,
            shaft_top,
            shaft_width,
            shaft_height,
            color,
        )


def draw_test_screen(display):
    display.fill(BLACK)

    # Orientation markers: top is cyan, bottom is red, and the corner is green.
    display.fill_rect(0, 0, WIDTH, 24, CYAN)
    display.fill_rect(0, HEIGHT - 24, WIDTH, 24, RED)
    display.fill_rect(8, 8, 4, 40, GREEN)
    display.fill_rect(8, 8, 40, 4, GREEN)

    display.draw_text(20, 5, "TOP", BLACK, 2)
    display.draw_text(20, HEIGHT - 19, "BOTTOM", WHITE, 2)

    # The arrow head must point towards TOP when the selected orientation is correct.
    display.draw_up_arrow(120, 75, 100, 70, 30, 100, YELLOW)
    display.draw_text(76, 185, "UP", WHITE, 3)

    display.draw_text(230, 92, "LANDSCAPE", WHITE, 3)
    display.draw_text(230, 125, "480 X 320", WHITE, 3)

    # Simple colour patches for RGB/BGR and pixel stability checks.
    patch_y = 205
    for index, color in enumerate((RED, GREEN, BLUE, WHITE)):
        display.fill_rect(230 + index * 48, patch_y, 36, 36, color)


print("PFT SPRINT 4 TFT TEST START")
display = ST7796S()
print("TFT SPI bus={} SCK={} MOSI={} CS={} DC={} RST={}".format(
    display.spi_bus, SPI_CLOCK, SPI_MOSI, TFT_CS, TFT_DC, TFT_RST
))
display.init()
draw_test_screen(display)
print("TFT_TEST_DONE orientation=landscape width=480 height=320")
