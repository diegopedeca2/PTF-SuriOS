"""PFT-SuriOS SPRINT 2: local DETECTOR radar data bridge.

ESP32-S3 wiring:
    GPIO16 (RX) <- WROOM GPIO25 (TX)
    GPIO17 (TX) -> WROOM GPIO26 (RX)
"""

from machine import UART
import time


UART_ID = 1
UART_BAUD = 115200
UART_RX_PIN = 16
UART_TX_PIN = 17
LINE_BUFFER_SIZE = 96
HEARTBEAT_INTERVAL_MS = 1000
REPORT_INTERVAL_MS = 5000
RADAR_TARGET_COUNT = 3


uart = UART(
    UART_ID,
    baudrate=UART_BAUD,
    bits=8,
    parity=None,
    stop=1,
    timeout=0,
    timeout_char=0,
    tx=UART_TX_PIN,
    rx=UART_RX_PIN,
)

rx_buffer = bytearray()
discarding_line = False
tx_sequence = 0
tx_count = 0
rx_count = 0
error_count = 0
radar_packet_count = 0
radar_error_count = 0
radar_missing_packets = 0
last_radar_sequence = None
radar_targets = [(0, 0, 0)] * RADAR_TARGET_COUNT
last_tx_at = time.ticks_ms()
last_report_at = last_tx_at


def send_line(line):
    global tx_count
    uart.write(line + "\n")
    tx_count += 1
    print("S3_TX=" + line)


def handle_radar_line(line):
    global radar_packet_count
    global radar_error_count, radar_missing_packets, last_radar_sequence
    global radar_targets

    parts = line.split(",")
    if len(parts) != 13:
        radar_error_count += 1
        print("S3_RADAR_ERROR=field_count")
        return

    try:
        values = [int(value) for value in parts[2:]]
    except Exception:
        radar_error_count += 1
        print("S3_RADAR_ERROR=number")
        return

    version = values[0]
    sequence = values[1] & 0xFF
    if version != 1:
        radar_error_count += 1
        print("S3_RADAR_ERROR=version_{}".format(version))
        return

    if last_radar_sequence is not None:
        delta = (sequence - last_radar_sequence + 256) % 256
        if delta == 0 or delta > 127:
            radar_error_count += 1
            print("S3_RADAR_ERROR=sequence_{}".format(sequence))
            return
        radar_missing_packets += delta - 1
    last_radar_sequence = sequence

    parsed_targets = []
    for index in range(RADAR_TARGET_COUNT):
        base = 2 + index * 3
        parsed_targets.append((values[base], values[base + 1], values[base + 2]))

    radar_targets = parsed_targets
    radar_packet_count += 1
    print("S3_RADAR seq={} targets={}".format(sequence, radar_targets))


def handle_line(line):
    global rx_count, error_count

    if line.startswith("WROOM,RADAR,"):
        handle_radar_line(line)
        return

    if (
        line.startswith("WROOM,HELLO,")
        or line.startswith("WROOM,ACK,")
        or line == "WROOM,PONG"
    ):
        rx_count += 1
        print("S3_RX=" + line)
    else:
        error_count += 1
        print("S3_RX_ERROR=" + line)


def poll_uart():
    global rx_buffer, discarding_line, error_count

    data = uart.read()
    if not data:
        return

    for value in data:
        if value == 13:
            continue

        if value == 10:
            if not discarding_line and rx_buffer:
                try:
                    handle_line(bytes(rx_buffer).decode())
                except Exception:
                    error_count += 1
                    print("S3_RX_ERROR=decode")
            rx_buffer = bytearray()
            discarding_line = False
            continue

        if discarding_line:
            continue

        if len(rx_buffer) + 1 >= LINE_BUFFER_SIZE:
            error_count += 1
            rx_buffer = bytearray()
            discarding_line = True
            continue

        rx_buffer.append(value)


print("PFT SPRINT 2 LOCAL DETECTOR UART TEST")
print("S3 UART{} RX={} TX={} baud={}".format(
    UART_ID, UART_RX_PIN, UART_TX_PIN, UART_BAUD
))

while True:
    now = time.ticks_ms()
    poll_uart()

    if time.ticks_diff(now, last_tx_at) >= HEARTBEAT_INTERVAL_MS:
        send_line("S3,HELLO,{}".format(tx_sequence))
        tx_sequence += 1
        last_tx_at = now

    if time.ticks_diff(now, last_report_at) >= REPORT_INTERVAL_MS:
        print("S3_STATS tx={} rx={} radar={} missing={} errors={} radar_errors={}".format(
            tx_count,
            rx_count,
            radar_packet_count,
            radar_missing_packets,
            error_count,
            radar_error_count
        ))
        last_report_at = now

    time.sleep_ms(10)
