"""Minimal ST7796S driver for the PFT-SuriOS S3 firmware."""

from machine import Pin, SPI
import math
import time


SPI_CLOCK = 12
SPI_MOSI = 11
TFT_RST = 14
TFT_DC = 9
TFT_CS = 10
WIDTH = 480
HEIGHT = 320
EMBLEM_FILE = "brotherhood_emblem_pipgreendim.bin"


def rgb565(red, green, blue):
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


BLACK = rgb565(0, 0, 0)
WHITE = rgb565(255, 255, 255)
GREEN = rgb565(102, 255, 102)
GREEN_BRIGHT = rgb565(102, 255, 153)
GREEN_DIM = rgb565(45, 125, 65)
GREEN_DARK = rgb565(10, 42, 19)
GREEN_EMBLEM_DARK = rgb565(5, 22, 10)
BLUE = rgb565(51, 170, 255)
RED = rgb565(255, 77, 77)
YELLOW = rgb565(255, 200, 87)
CYAN = BLUE


FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
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

        # Indexed off-screen map for the Watch Ultra style radar view.
        self.radar_buffer = bytearray(360 * 248)
        self.radar_batch = bytearray(360 * 2 * 8)
        self.radar_batch_view = memoryview(self.radar_batch)
        self.radar_dirty = bytearray(64 * 72 * 2)
        self.radar_dirty_view = memoryview(self.radar_dirty)
        self.radar_frame_started = False
        self.radar_previous_needle = None
        self.radar_previous_targets = []
        self.radar_status = None

    def command(self, command, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes((command,)))
        if data:
            self.dc.value(1)
            self.spi.write(data)
        self.cs.value(1)

    def init(self):
        self.rst.value(0)
        time.sleep_ms(30)
        self.rst.value(1)
        time.sleep_ms(120)
        self.command(0x01)
        time.sleep_ms(120)
        self.command(0x11)
        time.sleep_ms(120)
        self.command(0xF0, b"\xC3")
        self.command(0xF0, b"\x96")
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
        # Normal colour polarity: black stays black and green stays green.
        self.command(0x20)
        self.command(0x29)
        time.sleep_ms(20)

    def set_window(self, x0, y0, x1, y1):
        self.command(0x2A, bytes((x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)))
        self.command(0x2B, bytes((y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF)))
        self.command(0x2C)

    def fill_rect(self, x, y, width, height, color):
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

    def text(self, x, y, text, color, scale=2):
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
                        self.fill_rect(cursor + column * scale, y + row * scale, scale, scale, color)
            cursor += 6 * scale

    def up_arrow(self, center_x, top, color):
        head_width = 90
        head_height = 60
        for row in range(head_height):
            half_width = (row * head_width) // (2 * head_height)
            self.fill_rect(center_x - half_width, top + row, half_width * 2 + 1, 1, color)
        self.fill_rect(center_x - 14, top + head_height, 28, 80, color)

    def show_boot_screen(self):
        self.fill(BLACK)
        self.fill_rect(0, 0, WIDTH, 24, CYAN)
        self.fill_rect(0, HEIGHT - 24, WIDTH, 24, RED)
        self.fill_rect(8, 8, 4, 40, GREEN)
        self.fill_rect(8, 8, 40, 4, GREEN)
        self.text(20, 5, "PFT-SURIOS", BLACK, 2)
        self.text(20, HEIGHT - 19, "READY", WHITE, 2)
        self.up_arrow(110, 75, YELLOW)
        self.text(70, 185, "UP", WHITE, 3)
        self.text(230, 105, "TFT", WHITE, 4)
        self.text(230, 155, "READY", GREEN, 3)

    def draw_target_view(self, x, y, width, height, targets):
        self.fill_rect(x, y, width, 2, CYAN)
        self.fill_rect(x, y + height - 2, width, 2, CYAN)
        self.fill_rect(x, y, 2, height, CYAN)
        self.fill_rect(x + width - 2, y, 2, height, CYAN)

        center_x = x + width // 2
        origin_y = y + height - 10
        self.fill_rect(center_x, y + 4, 2, height - 14, CYAN)
        self.fill_rect(center_x - 4, origin_y - 2, 8, 4, WHITE)

        for flags, target_x, target_y in targets:
            if not flags:
                continue
            bounded_x = max(-6000, min(6000, target_x))
            bounded_y = max(0, min(6000, target_y))
            target_px = center_x + (bounded_x * (width // 2 - 10)) // 6000
            target_py = origin_y - (bounded_y * (height - 20)) // 6000
            color = YELLOW if flags == 3 else GREEN
            self.fill_rect(target_px - 3, target_py - 3, 7, 7, color)

    def show_runtime(self, active_tool, radar_packets, uart_rx, errors, ble_clients, targets):
        self.fill(BLACK)
        self.fill_rect(0, 0, WIDTH, 28, CYAN)
        self.fill_rect(0, HEIGHT - 24, WIDTH, 24, GREEN)
        self.text(20, 6, "PFT-SURIOS", BLACK, 2)
        self.text(20, 44, "RUNTIME", WHITE, 3)
        self.text(20, 88, "TOOL " + active_tool, YELLOW, 2)
        self.text(20, 122, "PACKETS {}".format(radar_packets), WHITE, 2)
        self.text(20, 156, "UART RX {}".format(uart_rx), WHITE, 2)
        self.text(20, 190, "BLE {}".format(ble_clients), WHITE, 2)
        self.text(20, 224, "ERR {}".format(errors), WHITE, 2)
        active_count = 0
        for flags, _, _ in targets:
            if flags:
                active_count += 1
        self.text(20, 258, "TARGETS {}".format(active_count), WHITE, 2)
        self.text(286, 44, "RADAR", WHITE, 2)
        self.draw_target_view(270, 70, 190, 210, targets)
        self.text(20, HEIGHT - 19, "READY", BLACK, 2)

    def _map_clear(self):
        for index in range(len(self.radar_buffer)):
            self.radar_buffer[index] = 0

    def _map_emblem(self):
        try:
            with open(EMBLEM_FILE, "rb") as emblem_file:
                for row in range(213):
                    pixels = emblem_file.read(180)
                    for column in range(len(pixels)):
                        level = pixels[column]
                        if level:
                            # Centered in the radar area, behind the grid.
                            self._map_pixel(90 + column, 10 + row, 7 if level == 1 else 6)
        except OSError:
            # The display remains usable if the optional branding asset is absent.
            return

    def _map_pixel(self, x, y, color_index):
        if 0 <= x < 360 and 0 <= y < 248:
            self.radar_buffer[y * 360 + x] = color_index

    def _map_line(self, x0, y0, x1, y1, color_index):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            self._map_pixel(x0, y0, color_index)
            if x0 == x1 and y0 == y1:
                return
            twice_error = 2 * error
            if twice_error >= dy:
                error += dy
                x0 += sx
            if twice_error <= dx:
                error += dx
                y0 += sy

    def _map_arc(self, origin_x, origin_y, radius, color_index):
        previous_x = None
        previous_y = None
        for step in range(49):
            angle = (-60.0 + (120.0 * step / 48.0)) * 0.01745329252
            point_x = origin_x + int(math.sin(angle) * radius)
            point_y = origin_y - int(math.cos(angle) * radius)
            if previous_x is not None:
                self._map_line(previous_x, previous_y, point_x, point_y, color_index)
            previous_x = point_x
            previous_y = point_y

    def _flush_radar_map(self):
        palette = (BLACK, BLUE, GREEN_DIM, GREEN_BRIGHT, RED, YELLOW, GREEN_DARK, GREEN_EMBLEM_DARK)
        for batch_start in range(0, 248, 8):
            row_count = min(8, 248 - batch_start)
            self.set_window(60, 42 + batch_start, 419, 42 + batch_start + row_count - 1)
            self.cs.value(0)
            self.dc.value(1)
            for local_row in range(row_count):
                row_offset = (batch_start + local_row) * 360
                batch_offset = local_row * 720
                for column_index in range(360):
                    color = palette[self.radar_buffer[row_offset + column_index]]
                    byte_offset = batch_offset + column_index * 2
                    self.radar_batch[byte_offset] = color >> 8
                    self.radar_batch[byte_offset + 1] = color & 0xFF
            self.spi.write(self.radar_batch_view[:row_count * 720])
            self.cs.value(1)

    def _flush_map_rect(self, x0, y0, x1, y1):
        """Restore a small indexed rectangle from the static radar map."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(359, x1)
        y1 = min(247, y1)
        width = x1 - x0 + 1
        height = y1 - y0 + 1
        if width <= 0 or height <= 0:
            return
        if width > 64 or height > 72:
            self._flush_radar_map()
            return

        palette = (BLACK, BLUE, GREEN_DIM, GREEN_BRIGHT, RED, YELLOW, GREEN_DARK, GREEN_EMBLEM_DARK)
        for row in range(height):
            source_offset = (y0 + row) * 360 + x0
            target_offset = row * width * 2
            for column in range(width):
                color = palette[self.radar_buffer[source_offset + column]]
                byte_offset = target_offset + column * 2
                self.radar_dirty[byte_offset] = color >> 8
                self.radar_dirty[byte_offset + 1] = color & 0xFF

        self.set_window(60 + x0, 42 + y0, 60 + x1, 42 + y1)
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(self.radar_dirty_view[:width * height * 2])
        self.cs.value(1)

    def _needle_segment(self, wave_fraction):
        angle = (-60.0 + 120.0 * wave_fraction) * 0.01745329252
        inner_radius = 124
        outer_radius = 178
        return (
            180 + int(math.sin(angle) * inner_radius),
            238 - int(math.cos(angle) * inner_radius),
            180 + int(math.sin(angle) * outer_radius),
            238 - int(math.cos(angle) * outer_radius),
        )

    def _needle_bounds(self, needle):
        x0, y0, x1, y1 = needle
        return min(x0, x1) - 2, min(y0, y1) - 2, max(x0, x1) + 2, max(y0, y1) + 2

    def _dynamic_pixel(self, width, x, y, color):
        if 0 <= x < width and 0 <= y < 72:
            offset = (y * width + x) * 2
            self.radar_dirty[offset] = color >> 8
            self.radar_dirty[offset + 1] = color & 0xFF

    def _dynamic_line(self, width, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            self._dynamic_pixel(width, x0, y0, color)
            self._dynamic_pixel(width, x0 + 1, y0, color)
            if x0 == x1 and y0 == y1:
                return
            twice_error = 2 * error
            if twice_error >= dy:
                error += dy
                x0 += sx
            if twice_error <= dx:
                error += dx
                y0 += sy

    def _draw_needle(self, needle):
        x0, y0, x1, y1 = needle
        bounds = self._needle_bounds(needle)
        box_x0, box_y0, box_x1, box_y1 = bounds
        box_x0 = max(0, box_x0)
        box_y0 = max(0, box_y0)
        box_x1 = min(359, box_x1)
        box_y1 = min(247, box_y1)
        width = box_x1 - box_x0 + 1
        height = box_y1 - box_y0 + 1
        if width <= 0 or height <= 0 or width > 64 or height > 72:
            return

        palette = (BLACK, BLUE, GREEN_DIM, GREEN_BRIGHT, RED, YELLOW, GREEN_DARK, GREEN_EMBLEM_DARK)
        for row in range(height):
            source_offset = (box_y0 + row) * 360 + box_x0
            target_offset = row * width * 2
            for column in range(width):
                color = palette[self.radar_buffer[source_offset + column]]
                byte_offset = target_offset + column * 2
                self.radar_dirty[byte_offset] = color >> 8
                self.radar_dirty[byte_offset + 1] = color & 0xFF

        self._dynamic_line(width, x0 - box_x0, y0 - box_y0, x1 - box_x0, y1 - box_y0, GREEN_BRIGHT)
        self.set_window(60 + box_x0, 42 + box_y0, 60 + box_x1, 42 + box_y1)
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(self.radar_dirty_view[:width * height * 2])
        self.cs.value(1)

    def _visible_target_points(self, targets):
        points = []
        for flags, target_x, target_y in targets:
            if not flags:
                continue
            distance = math.sqrt(target_x * target_x + target_y * target_y)
            bearing = math.atan2(target_x, target_y) * 57.2957795
            if target_y < 0 or distance > 6000 or abs(bearing) > 60:
                continue
            points.append((180 + int((target_x / 6000.0) * 178), 238 - int((target_y / 6000.0) * 178)))
        return points

    def _draw_target_marker(self, point):
        point_x, point_y = point
        self.fill_rect(60 + point_x - 3, 42 + point_y - 3, 7, 7, RED)

    def show_radar_frame(self, targets, sequence, missing_packets, wave_fraction, status):
        """Draw the Watch Ultra radar with a static map and live target markers."""
        if not self.radar_frame_started:
            self.fill(BLACK)
            self._map_clear()
            self._map_emblem()
            for distance in range(1, 7):
                self._map_arc(180, 238, (178 * distance) // 6, 1)
            left_angle = -60.0 * 0.01745329252
            right_angle = 60.0 * 0.01745329252
            self._map_line(180, 238, 180 + int(math.sin(left_angle) * 178), 238 - int(math.cos(left_angle) * 178), 1)
            self._map_line(180, 238, 180 + int(math.sin(right_angle) * 178), 238 - int(math.cos(right_angle) * 178), 1)
            self._map_line(180, 238, 180, 60, 2)
            for marker_y in range(235, 242):
                for marker_x in range(177, 184):
                    self._map_pixel(marker_x, marker_y, 3)
            self._flush_radar_map()
            self.radar_frame_started = True

        if status != self.radar_status:
            self.fill_rect(0, 0, WIDTH, 40, BLACK)
            self.text(12, 8, "SURIOS RADAR", GREEN_BRIGHT, 2)
            self.text(326, 8, status, WHITE, 1)
            self.radar_status = status

        for point_x, point_y in self.radar_previous_targets:
            self._flush_map_rect(point_x - 4, point_y - 4, point_x + 4, point_y + 4)

        current_targets = self._visible_target_points(targets)
        for point in current_targets:
            self._draw_target_marker(point)
        self.radar_previous_needle = None
        self.radar_previous_targets = current_targets
