# Circuit Wiring Diagram — Smart Classroom IoT System

## ESP32 Pin Connections

```
                    ┌─────────────────────────┐
                    │     ESP32 DevKit V1      │
                    │                          │
     DHT11 DATA ←──┤ GPIO 4          GPIO 14 ├──→ PIR-1 (Left Zone)
                    │                          │
                    │ GPIO 27                  ├──→ PIR-2 (Center Zone)
                    │                          │
                    │ GPIO 26                  ├──→ PIR-3 (Right Zone)
                    │                          │
   KY-038 A0   ←──┤ GPIO 34 (ADC1)           │
                    │                          │
   MQ-135 A0   ←──┤ GPIO 35 (ADC1)           │
                    │                          │
   LDR A0     ←──┤ GPIO 32 (ADC1)           │
                    │                          │
   Built-in LED ──┤ GPIO 2                   │
                    │                          │
                    │ 3V3              VIN/5V  │
                    │ GND              GND     │
                    └─────────────────────────┘
```

## Detailed Wiring for Each Sensor

### 1. DHT11/DHT22 — Temperature & Humidity
```
DHT11          ESP32
─────          ─────
VCC    ───→    3V3
DATA   ───→    GPIO 4
GND    ───→    GND

Note: Add a 10kΩ pull-up resistor between DATA and VCC (some modules have it built-in)
```

### 2. HC-SR501 PIR Motion Sensors (×3)
```
PIR-1 (Left)     ESP32          PIR-2 (Center)    ESP32         PIR-3 (Right)    ESP32
────────────     ─────          ──────────────    ─────         ─────────────    ─────
VCC   ───→       VIN (5V)      VCC   ───→        VIN (5V)     VCC   ───→       VIN (5V)
OUT   ───→       GPIO 14       OUT   ───→        GPIO 27      OUT   ───→       GPIO 26
GND   ───→       GND           GND   ───→        GND          GND   ───→       GND

⚠️ PIR sensors need 5V power (use VIN pin, NOT 3V3)
⚠️ PIR sensors need 30-60 seconds to calibrate after power-on
```

### 3. KY-037/KY-038 Sound Sensor
```
KY-038         ESP32
──────         ─────
VCC    ───→    3V3
A0     ───→    GPIO 34 (ADC1 — safe with WiFi)
GND    ───→    GND

Note: D0 (digital out) is optional — we use the analog output for dB readings
Adjust sensitivity with the onboard potentiometer
```

### 4. MQ-135 Air Quality Sensor (Optional)
```
MQ-135         ESP32
──────         ─────
VCC    ───→    VIN (5V)
A0     ───→    GPIO 35 (ADC1) — add 1kΩ resistor in series for protection
GND    ───→    GND

⚠️ MQ-135 heater needs 5V and draws significant current
⚠️ Needs 24-48 hour burn-in period for accurate readings
⚠️ Place a 1kΩ resistor between A0 and GPIO 35 to protect ESP32
```

### 5. LDR Light Sensor (Optional)
```
Voltage Divider Setup:

3V3 ──→ [LDR] ──┬── GPIO 32 (ADC1)
                  │
                  └── [10kΩ Resistor] ──→ GND

Higher reading = more light
```

## Breadboard Layout (2 boards)

### Board 1: Main Controller
```
┌─────────────────────────────────────────────┐
│  BREADBOARD 1                                │
│                                              │
│  [ESP32]  [DHT11]  [KY-038]  [MQ-135]      │
│                                              │
│  Power rails: 5V and 3.3V from ESP32        │
│  All GND connected to common ground rail     │
└─────────────────────────────────────────────┘
```

### Board 2: PIR Sensors (placed around classroom)
```
PIR-1 (Left wall)     PIR-2 (Center/Front)    PIR-3 (Right wall)
   ┌───┐                  ┌───┐                   ┌───┐
   │PIR│                  │PIR│                   │PIR│
   └─┬─┘                  └─┬─┘                   └─┬─┘
     │                      │                       │
     └── Long jumper wires to ESP32 board ──────────┘
```

## Important Notes

1. **ADC1 pins only**: GPIO 32, 33, 34, 35, 36, 39 — these work with WiFi active
2. **ADC2 pins**: GPIO 0, 2, 4, 12-15, 25-27 — DO NOT use for analog when WiFi is on
3. **Power**: ESP32 VIN provides 5V from USB. Use this for PIR and MQ-135
4. **Multiple sensors on 5V**: If current draw is too high, use external 5V supply
5. **2nd ESP32**: Wire identically, change ESP_ID to "ESP32-02" and ROOM in firmware
