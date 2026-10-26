"""PFT-SuriOS SPRINT 1: UART bidirectional diagnostic test.

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
last_tx_at = time.ticks_ms()
last_report_at = last_tx_at


def send_line(line):
    global tx_count
    uart.write(line + "\n")
    tx_count += 1
    print("S3_TX=" + line)


def handle_line(line):
    global rx_count, error_count

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


print("PFT SPRINT 1 S3 UART TEST")
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
        print("S3_STATS tx={} rx={} errors={}".format(
            tx_count, rx_count, error_count
        ))
        last_report_at = now

    time.sleep_ms(10)
