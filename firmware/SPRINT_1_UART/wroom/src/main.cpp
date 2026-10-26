#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_pm.h>

#include <cmath>
#include <cstdio>
#include <cstring>

// -----------------------------------------------------------------------------
// Hardware and protocol configuration
// -----------------------------------------------------------------------------

constexpr char BLE_NAME[] = "SuriOS Radar";
constexpr char BLE_SERVICE_UUID[] = "9e5d0001-7b3a-4c0f-91c2-245000000001";
constexpr char BLE_DATA_UUID[] = "9e5d0002-7b3a-4c0f-91c2-245000000001";
constexpr char BLE_CONTROL_UUID[] = "9e5d0003-7b3a-4c0f-91c2-245000000001";

constexpr uint8_t CONTROL_NORMAL = 0x00;
constexpr uint8_t CONTROL_ECO = 0x01;

// Standard ESP32 DevKit wiring used by this prototype:
//   LD2450 TX -> ESP32 GPIO16 (UART2 RX)
//   LD2450 RX -> ESP32 GPIO17 (UART2 TX)
//   LD2450 5V -> ESP32 5V/VIN
//   LD2450 GND -> ESP32 GND
constexpr int RADAR_RX_PIN = 16;
constexpr int RADAR_TX_PIN = 17;
constexpr uint32_t RADAR_BAUD = 256000;

// PFT-SuriOS SPRINT 1 link to the ESP32-S3:
//   WROOM GPIO25 (TX) -> S3 GPIO16 (RX)
//   WROOM GPIO26 (RX) <- S3 GPIO17 (TX)
constexpr int PFT_RX_PIN = 26;
constexpr int PFT_TX_PIN = 25;
constexpr uint32_t PFT_BAUD = 115200;
constexpr uint32_t PFT_HEARTBEAT_INTERVAL_MS = 1000;

// The watch UI maps positive x to the right side of the display. The LD2450's
// physical left/right convention is mirrored for this installation, so invert
// x before placing it in the watch packet. Set false if the sensor is mounted
// in the opposite orientation.
constexpr bool INVERT_X_FOR_WATCH = true;

constexpr int16_t FRONT_MIN_Y_MM = 0;
constexpr int16_t FRONT_MAX_Y_MM = 6000;
constexpr int16_t FRONT_MAX_ABS_X_MM = 6000;
constexpr float FRONT_HALF_BEAM_DEGREES = 60.0f;

constexpr uint8_t TARGET_CONFIRM_FRAMES = 2;
constexpr uint8_t TARGET_MAX_MISSES = 2;

constexpr uint8_t WATCH_PROTOCOL_VERSION = 1;
constexpr size_t WATCH_PACKET_SIZE = 17;
constexpr size_t TARGET_COUNT = 3;

constexpr size_t LD2450_FRAME_SIZE = 30;
constexpr uint8_t LD2450_HEADER[4] = {0xAA, 0xFF, 0x03, 0x00};
constexpr uint8_t LD2450_FOOTER[2] = {0x55, 0xCC};

constexpr uint8_t COMMAND_HEADER[4] = {0xFD, 0xFC, 0xFB, 0xFA};
constexpr uint8_t COMMAND_FOOTER[4] = {0x04, 0x03, 0x02, 0x01};

HardwareSerial radarSerial(2);
HardwareSerial pftSerial(1);
NimBLEServer* bleServer = nullptr;
NimBLECharacteristic* dataCharacteristic = nullptr;
NimBLECharacteristic* controlCharacteristic = nullptr;

uint8_t radarFrame[LD2450_FRAME_SIZE];
size_t radarFrameBytes = 0;
uint8_t packetSequence = 0;
uint32_t radarFrameCount = 0;
uint32_t lastRadarDebugAt = 0;
uint8_t lastValidTargetCount = 0;
bool ecoMode = false;
volatile bool pendingEcoModeChange = false;
volatile bool requestedEcoMode = false;

constexpr size_t PFT_RX_LINE_SIZE = 96;
char pftRxLine[PFT_RX_LINE_SIZE];
size_t pftRxLineBytes = 0;
bool pftDiscardingLine = false;
uint32_t pftTxCount = 0;
uint32_t pftRxCount = 0;
uint32_t pftErrorCount = 0;
uint32_t pftSequence = 0;
uint32_t lastPftHeartbeatAt = 0;
uint32_t lastPftStatsAt = 0;

struct TargetTrack {
    int16_t xMm = 0;
    int16_t yMm = 0;
    uint8_t confirmedFrames = 0;
    uint8_t missedFrames = 0;
    bool confirmed = false;
};

TargetTrack tracks[TARGET_COUNT];

// -----------------------------------------------------------------------------
// PFT-SuriOS ESP32-WROOM <-> ESP32-S3 diagnostic link
// -----------------------------------------------------------------------------

void sendPftLine(const char* line) {
    pftSerial.print(line);
    pftSerial.print('\n');
    ++pftTxCount;
}

void handlePftLine() {
    pftRxLine[pftRxLineBytes] = '\0';

    if (strncmp(pftRxLine, "S3,HELLO,", 9) == 0) {
        ++pftRxCount;
        char response[PFT_RX_LINE_SIZE];
        snprintf(
            response,
            sizeof(response),
            "WROOM,ACK,%s",
            pftRxLine + 9
        );
        sendPftLine(response);
        Serial.printf("PFT_RX=%s\n", pftRxLine);
        return;
    }

    if (strcmp(pftRxLine, "S3,PING") == 0) {
        ++pftRxCount;
        sendPftLine("WROOM,PONG");
        Serial.println("PFT_RX=S3,PING");
        return;
    }

    ++pftErrorCount;
    Serial.printf("PFT_RX_ERROR=%s\n", pftRxLine);
}

void pollPftLink() {
    while (pftSerial.available() > 0) {
        const char value = static_cast<char>(pftSerial.read());

        if (value == '\r') {
            continue;
        }

        if (value == '\n') {
            if (!pftDiscardingLine && pftRxLineBytes > 0) {
                handlePftLine();
            }
            pftRxLineBytes = 0;
            pftDiscardingLine = false;
            continue;
        }

        if (pftDiscardingLine) {
            continue;
        }

        if (pftRxLineBytes + 1 >= PFT_RX_LINE_SIZE) {
            ++pftErrorCount;
            pftRxLineBytes = 0;
            pftDiscardingLine = true;
            continue;
        }

        pftRxLine[pftRxLineBytes++] = value;
    }
}

void servicePftLink() {
    const uint32_t now = millis();
    if (lastPftHeartbeatAt == 0 ||
        now - lastPftHeartbeatAt >= PFT_HEARTBEAT_INTERVAL_MS) {
        char heartbeat[PFT_RX_LINE_SIZE];
        snprintf(
            heartbeat,
            sizeof(heartbeat),
            "WROOM,HELLO,%lu,frames=%lu,targets=%u",
            static_cast<unsigned long>(pftSequence++),
            static_cast<unsigned long>(radarFrameCount),
            lastValidTargetCount
        );
        sendPftLine(heartbeat);
        lastPftHeartbeatAt = now;
    }

    if (lastPftStatsAt == 0 || now - lastPftStatsAt >= 5000) {
        Serial.printf(
            "PFT_STATS tx=%lu rx=%lu errors=%lu\n",
            static_cast<unsigned long>(pftTxCount),
            static_cast<unsigned long>(pftRxCount),
            static_cast<unsigned long>(pftErrorCount)
        );
        lastPftStatsAt = now;
    }
}

// -----------------------------------------------------------------------------
// BLE server
// -----------------------------------------------------------------------------

class RadarServerCallbacks final : public NimBLEServerCallbacks {
public:
    void onConnect(NimBLEServer*, NimBLEConnInfo&) override {
        Serial.println("BLE client connected");
    }

    void onDisconnect(NimBLEServer*, NimBLEConnInfo&, int) override {
        Serial.println("BLE client disconnected");
        NimBLEDevice::getAdvertising()->start();
    }
};

class RadarControlCallbacks final : public NimBLECharacteristicCallbacks {
public:
    void onWrite(NimBLECharacteristic* characteristic, NimBLEConnInfo&) override {
        const std::string value = characteristic->getValue();
        if (value.empty()) {
            return;
        }

        if (static_cast<uint8_t>(value[0]) == CONTROL_ECO) {
            requestedEcoMode = true;
            pendingEcoModeChange = true;
        } else if (static_cast<uint8_t>(value[0]) == CONTROL_NORMAL) {
            requestedEcoMode = false;
            pendingEcoModeChange = true;
        }
    }
};

void setupBle() {
    NimBLEDevice::init(BLE_NAME);

    bleServer = NimBLEDevice::createServer();
    bleServer->setCallbacks(new RadarServerCallbacks());

    NimBLEService* service = bleServer->createService(BLE_SERVICE_UUID);
    dataCharacteristic = service->createCharacteristic(
        BLE_DATA_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    controlCharacteristic = service->createCharacteristic(
        BLE_CONTROL_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::NOTIFY
    );
    controlCharacteristic->setCallbacks(new RadarControlCallbacks());
    const uint8_t initialMode = CONTROL_NORMAL;
    controlCharacteristic->setValue(&initialMode, sizeof(initialMode));
    service->start();

    NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();
    advertising->setName(BLE_NAME);
    advertising->addServiceUUID(BLE_SERVICE_UUID);
    advertising->enableScanResponse(true);
    advertising->start();

    Serial.println("BLE advertising as SuriOS Radar");
}

void publishEcoMode() {
    if (controlCharacteristic == nullptr) {
        return;
    }

    const uint8_t mode = ecoMode ? CONTROL_ECO : CONTROL_NORMAL;
    controlCharacteristic->setValue(&mode, sizeof(mode));
    if (bleServer != nullptr && bleServer->getConnectedCount() > 0) {
        controlCharacteristic->notify();
    }
}

void configureEspPowerMode(bool enableEcoMode) {
    esp_pm_config_esp32_t config = {};
    config.max_freq_mhz = enableEcoMode ? 80 : 240;
    config.min_freq_mhz = 40;
    config.light_sleep_enable = enableEcoMode;

    const esp_err_t result = esp_pm_configure(&config);
    Serial.printf(
        "ESP_POWER_MODE=%s RESULT=%s\n",
        enableEcoMode ? "ECO_BLE" : "NORMAL",
        esp_err_to_name(result)
    );
}

void applyPendingEcoMode() {
    if (!pendingEcoModeChange) {
        return;
    }

    const bool nextEcoMode = requestedEcoMode;
    pendingEcoModeChange = false;
    if (ecoMode == nextEcoMode) {
        return;
    }

    ecoMode = nextEcoMode;
    configureEspPowerMode(ecoMode);
    publishEcoMode();
    Serial.printf(
        "RADAR_CONTROL=%s BLE=ON\n",
        ecoMode ? "ECO" : "NORMAL"
    );
}

// -----------------------------------------------------------------------------
// LD2450 configuration commands
// -----------------------------------------------------------------------------

void writeLe16(uint8_t* destination, int16_t value) {
    const uint16_t raw = static_cast<uint16_t>(value);
    destination[0] = static_cast<uint8_t>(raw & 0xFF);
    destination[1] = static_cast<uint8_t>((raw >> 8) & 0xFF);
}

void writeLe16Unsigned(uint8_t* destination, uint16_t value) {
    destination[0] = static_cast<uint8_t>(value & 0xFF);
    destination[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
}

void flushRadarInput() {
    while (radarSerial.available() > 0) {
        radarSerial.read();
    }
}

void sendRadarCommand(uint16_t command, const uint8_t* payload, size_t payloadLength) {
    const uint16_t frameLength = static_cast<uint16_t>(2 + payloadLength);

    radarSerial.write(COMMAND_HEADER, sizeof(COMMAND_HEADER));
    radarSerial.write(static_cast<uint8_t>(frameLength & 0xFF));
    radarSerial.write(static_cast<uint8_t>((frameLength >> 8) & 0xFF));
    radarSerial.write(static_cast<uint8_t>(command & 0xFF));
    radarSerial.write(static_cast<uint8_t>((command >> 8) & 0xFF));
    if (payload != nullptr && payloadLength > 0) {
        radarSerial.write(payload, payloadLength);
    }
    radarSerial.write(COMMAND_FOOTER, sizeof(COMMAND_FOOTER));
    radarSerial.flush();
}

bool waitForRadarAck(uint16_t command, uint32_t timeoutMs = 350) {
    uint8_t scan[32] = {};
    size_t scanLength = 0;
    const uint32_t deadline = millis() + timeoutMs;

    while (static_cast<int32_t>(deadline - millis()) > 0) {
        while (radarSerial.available() > 0) {
            const uint8_t value = static_cast<uint8_t>(radarSerial.read());
            if (scanLength < sizeof(scan)) {
                scan[scanLength++] = value;
            } else {
                memmove(scan, scan + 1, sizeof(scan) - 1);
                scan[sizeof(scan) - 1] = value;
            }

            for (size_t index = 0; index + 10 <= scanLength; ++index) {
                if (scan[index] != COMMAND_HEADER[0] ||
                    scan[index + 1] != COMMAND_HEADER[1] ||
                    scan[index + 2] != COMMAND_HEADER[2] ||
                    scan[index + 3] != COMMAND_HEADER[3]) {
                    continue;
                }

                const uint16_t responseCommand =
                    static_cast<uint16_t>(scan[index + 6]) |
                    (static_cast<uint16_t>(scan[index + 7]) << 8);
                const uint16_t expectedAckCommand = command | 0x0100;
                if (responseCommand != expectedAckCommand) {
                    continue;
                }

                // The LD2450 ACK uses 0x0000 for success and 0x0001 for failure.
                const bool success = scan[index + 8] == 0x00 && scan[index + 9] == 0x00;
                return success;
            }
        }
        delay(1);
    }

    return false;
}

bool sendRadarCommandAndWait(
    uint16_t command,
    const uint8_t* payload = nullptr,
    size_t payloadLength = 0
) {
    flushRadarInput();
    sendRadarCommand(command, payload, payloadLength);
    const bool success = waitForRadarAck(command);
    Serial.printf("LD2450 command 0x%04X: %s\n", command, success ? "OK" : "NO ACK");
    return success;
}

void configureRadar() {
    // The LD2450 must be put into configuration mode before other commands.
    // The region is a forward-facing rectangle: x=-6000..6000, y=0..6000 mm.
    // The firmware also applies the same front-cone checks to every frame.
    uint8_t region[26] = {};
    writeLe16Unsigned(region + 0, 1);       // Detect only the configured region.
    writeLe16(region + 2, -6000);            // Region 1 x1.
    writeLe16(region + 4, 0);               // Region 1 y1.
    writeLe16(region + 6, 6000);            // Region 1 x2.
    writeLe16(region + 8, 6000);            // Region 1 y2.

    const uint8_t enableConfiguration[2] = {0x01, 0x00};
    delay(500);
    sendRadarCommandAndWait(0x00FF, enableConfiguration, sizeof(enableConfiguration));
    sendRadarCommandAndWait(0x0090);        // Multi-target tracking.
    sendRadarCommandAndWait(0x00C2, region, sizeof(region));
    sendRadarCommandAndWait(0x00FE);        // Return to normal reporting mode.
    flushRadarInput();
}

// -----------------------------------------------------------------------------
// LD2450 frame decoding and filtering
// -----------------------------------------------------------------------------

int16_t decodeLd2450Signed(uint16_t raw) {
    const int16_t magnitude = static_cast<int16_t>(raw & 0x7FFF);
    return (raw & 0x8000) != 0 ? magnitude : static_cast<int16_t>(-magnitude);
}

uint16_t readLe16(const uint8_t* source) {
    return static_cast<uint16_t>(source[0]) |
           (static_cast<uint16_t>(source[1]) << 8);
}

bool isInFrontCone(int16_t xMm, int16_t yMm) {
    if (yMm <= FRONT_MIN_Y_MM || yMm > FRONT_MAX_Y_MM) {
        return false;
    }

    if (std::abs(static_cast<int32_t>(xMm)) > FRONT_MAX_ABS_X_MM) {
        return false;
    }

    const float angle = std::atan2(
        std::abs(static_cast<float>(xMm)),
        static_cast<float>(yMm)
    ) * 180.0f / PI;
    return angle <= FRONT_HALF_BEAM_DEGREES;
}

void resetTrack(TargetTrack& track) {
    track = TargetTrack{};
}

void updateTrack(TargetTrack& track, bool valid, int16_t xMm, int16_t yMm) {
    if (valid) {
        track.xMm = xMm;
        track.yMm = yMm;
        track.missedFrames = 0;

        if (!track.confirmed) {
            if (track.confirmedFrames < TARGET_CONFIRM_FRAMES) {
                ++track.confirmedFrames;
            }
            if (track.confirmedFrames >= TARGET_CONFIRM_FRAMES) {
                track.confirmed = true;
            }
        }
        return;
    }

    if (track.confirmed && track.missedFrames < TARGET_MAX_MISSES) {
        ++track.missedFrames;
        return;
    }

    resetTrack(track);
}

void writeWatchInt16(uint8_t* packet, size_t offset, int16_t value) {
    const uint16_t raw = static_cast<uint16_t>(value);
    packet[offset] = static_cast<uint8_t>(raw & 0xFF);
    packet[offset + 1] = static_cast<uint8_t>((raw >> 8) & 0xFF);
}

void publishWatchPacket() {
    if (dataCharacteristic == nullptr) {
        return;
    }

    uint8_t packet[WATCH_PACKET_SIZE] = {};
    packet[0] = WATCH_PROTOCOL_VERSION;
    packet[1] = packetSequence++;

    for (size_t index = 0; index < TARGET_COUNT; ++index) {
        const TargetTrack& track = tracks[index];
        const size_t offset = 2 + index * 5;

        if (!track.confirmed) {
            packet[offset] = 0;
            continue;
        }

        packet[offset] = track.missedFrames == 0 ? 1 : 3;
        writeWatchInt16(packet, offset + 1, track.xMm);
        writeWatchInt16(packet, offset + 3, track.yMm);
    }

    dataCharacteristic->notify(packet, sizeof(packet));
}

void processRadarFrame() {
    ++radarFrameCount;
    uint8_t validTargetCount = 0;

    for (size_t index = 0; index < TARGET_COUNT; ++index) {
        const size_t offset = 4 + index * 8;
        const int16_t sensorX = decodeLd2450Signed(readLe16(radarFrame + offset));
        const int16_t sensorY = decodeLd2450Signed(readLe16(radarFrame + offset + 2));
        const uint16_t distanceResolution = readLe16(radarFrame + offset + 6);

        const bool sensorSlotOccupied = distanceResolution != 0;
        const int16_t watchX = INVERT_X_FOR_WATCH ? static_cast<int16_t>(-sensorX) : sensorX;
        const bool valid = sensorSlotOccupied && isInFrontCone(sensorX, sensorY);
        if (valid) {
            ++validTargetCount;
        }
        updateTrack(tracks[index], valid, watchX, sensorY);
    }

    lastValidTargetCount = validTargetCount;

    publishWatchPacket();

    const uint32_t now = millis();
    if (now - lastRadarDebugAt >= 1000) {
        Serial.printf(
            "LD2450 frames=%lu valid_targets=%u BLE_clients=%d\n",
            static_cast<unsigned long>(radarFrameCount),
            validTargetCount,
            bleServer == nullptr ? 0 : bleServer->getConnectedCount()
        );
        lastRadarDebugAt = now;
    }
}

void resetRadarParser(uint8_t possibleHeaderByte) {
    radarFrameBytes = possibleHeaderByte == LD2450_HEADER[0] ? 1 : 0;
    if (radarFrameBytes == 1) {
        radarFrame[0] = possibleHeaderByte;
    }
}

void pollRadar() {
    while (radarSerial.available() > 0) {
        const uint8_t value = static_cast<uint8_t>(radarSerial.read());

        if (radarFrameBytes == 0) {
            resetRadarParser(value);
            continue;
        }

        radarFrame[radarFrameBytes++] = value;

        if (radarFrameBytes == 2 && value != LD2450_HEADER[1]) {
            resetRadarParser(value);
            continue;
        }
        if (radarFrameBytes == 3 && value != LD2450_HEADER[2]) {
            resetRadarParser(value);
            continue;
        }
        if (radarFrameBytes == 4 && value != LD2450_HEADER[3]) {
            resetRadarParser(value);
            continue;
        }

        if (radarFrameBytes < LD2450_FRAME_SIZE) {
            continue;
        }

        const bool validFooter = radarFrame[28] == LD2450_FOOTER[0] &&
                                 radarFrame[29] == LD2450_FOOTER[1];
        if (validFooter) {
            processRadarFrame();
        }
        resetRadarParser(0);
    }
}

// -----------------------------------------------------------------------------
// Arduino entry points
// -----------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println();
    Serial.println("SuriOS Radar firmware V0.1");

    radarSerial.begin(RADAR_BAUD, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);
    Serial.printf(
        "LD2450 UART2 RX=%d TX=%d baud=%lu\n",
        RADAR_RX_PIN,
        RADAR_TX_PIN,
        static_cast<unsigned long>(RADAR_BAUD)
    );

    pftSerial.begin(PFT_BAUD, SERIAL_8N1, PFT_RX_PIN, PFT_TX_PIN);
    Serial.printf(
        "PFT UART1 RX=%d TX=%d baud=%lu\n",
        PFT_RX_PIN,
        PFT_TX_PIN,
        static_cast<unsigned long>(PFT_BAUD)
    );

    setupBle();
    configureRadar();
}

void loop() {
    applyPendingEcoMode();

    pollPftLink();
    servicePftLink();

    if (ecoMode) {
        delay(10);
        return;
    }

    pollRadar();
    delay(1);
}
