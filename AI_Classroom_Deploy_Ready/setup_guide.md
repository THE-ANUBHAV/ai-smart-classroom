# Setup Guide — Smart Classroom IoT System

## Quick Start (3 Steps)

### Step 1: Install Python Dependencies
```bash
cd "c:\AI- Classroom"
pip install -r requirements.txt
```

### Step 2: Boot A.E.G.I.S. Core
Simply double-click the **`Start_AEGIS.bat`** file in your project folder!

*This will automatically launch the Flask server, run a cool terminal animation, and open the live dashboard in your browser.*
You'll see:
```
════════════════════════════════════════════════════════
  AI-Powered Smart Classroom Analytics System
  Team-8 | GLA University | B.Tech CSE (AI-ML)
════════════════════════════════════════════════════════
[DB] Database initialized successfully
[ML] Training on 2000 samples...
[ML] Score model R²: 0.95+
[ML] Level classifier accuracy: 0.90+
[SERVER] Ready! Dashboard: http://localhost:5000
```

### Step 3: Open Dashboard
Go to **http://localhost:5000** in your browser.
- Without ESP32 → Dashboard runs in **SIM MODE** (yellow badge)
- With ESP32 connected → Auto-switches to **LIVE MODE** (green badge)

---

## ESP32 Hardware Setup

### Prerequisites
1. Install [Arduino IDE](https://www.arduino.cc/en/software) (v2.x recommended)
2. Add ESP32 Board Support:
   - Arduino IDE → File → Preferences
   - Additional Board URLs: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Tools → Board → Boards Manager → Search "ESP32" → Install

### Install Arduino Libraries
Via Arduino IDE Library Manager (Tools → Manage Libraries):
1. **DHT sensor library** by Adafruit
2. **ArduinoJson** by Benoit Blanchon (v6.x)
3. **Adafruit Unified Sensor** (dependency for DHT)

### Configure the Firmware
1. Open `esp32_firmware/smart_classroom.ino` in Arduino IDE
2. **Edit these lines** at the top:

```cpp
const char* WIFI_SSID     = "YOUR_WIFI_NAME";     // Your WiFi network
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // Your WiFi password
const char* SERVER_IP     = "192.168.X.X";         // Your laptop's IP
const char* ESP_ID        = "ESP32-01";            // "ESP32-01" or "ESP32-02"
const char* ROOM          = "Room A101";           // Classroom assignment
```

3. **Set the SERVER_IP**:
   - If running locally: Use your laptop's IP (e.g., `192.168.1.105`)
   - If deploying to Render: Use your Render URL (e.g., `smartclassroom.onrender.com`) without `http://`

> **Note on ThingWorx & Render**: 
> If you deploy the backend to Render, Render **cannot** connect to a local private IP like `172.16.78.20`. Your ThingWorx server MUST be publicly accessible over the internet, or you must run this backend locally on the college intranet.

### Flash the ESP32
1. Connect ESP32 via USB
2. Arduino IDE → Tools → Board → "ESP32 Dev Module"
3. Tools → Port → Select the COM port (e.g., COM3)
4. Click Upload (→)
5. Open Serial Monitor (115200 baud) to see sensor output

### For Second ESP32
- Same firmware, but change:
  - `ESP_ID = "ESP32-02"`
  - `ROOM = "Room B205"` (or whichever room)

---

## Sensor Placement in Classroom

```
┌──────────────────────────────────────────┐
│               CLASSROOM                   │
│                                          │
│  [PIR-1]                      [PIR-3]   │
│  Left wall                   Right wall  │
│                                          │
│              [PIR-2]                     │
│            Center/Front                   │
│                                          │
│  [ESP32 + DHT11 + Sound + MQ-135]       │
│  Teacher's desk area                     │
│                                          │
│            [STUDENTS]                    │
│                                          │
└──────────────────────────────────────────┘
└──────────────────────────────────────────┘
```

---

---

## Cloud Access (Using Ngrok - Recommended)

Since your ThingWorx database is on a private college IP (`172.16.78.20`), you **cannot** easily deploy your backend to Render. The best solution is to run the Flask server locally on your laptop (which is on the college network) and expose it to the internet using **Ngrok**.

### 1. Run the Flask Server
Make sure you are connected to the college network and run the server on your laptop:
```bash
python app.py
```

### 2. Start Ngrok
Open a **new** command prompt window and run:
```bash
ngrok http 5000
```
*Ngrok will generate a public "Forwarding" URL (e.g., `https://a1b2c3d4.ngrok-free.app`).*

### 3. Update ESP32 Code
Open `smart_classroom.ino` and change the `SERVER_IP` to your Ngrok URL:
```cpp
const char* SERVER_IP = "a1b2c3d4.ngrok-free.app"; // No http://
```

### Why this is the best method:
- Your laptop can securely talk to the private ThingWorx database at `172.16.78.20`.
- The ESP32 can send data from anywhere using the public Ngrok URL.
- You can open the Dashboard on any device (phone, evaluator's laptop) using the Ngrok URL.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ESP32 can't connect to WiFi | Check SSID/password. Ensure 2.4GHz network (ESP32 doesn't support 5GHz) |
| ESP32 can't reach server | Verify SERVER_IP is correct. Both devices must be on same network |
| DHT11 reads NaN | Check wiring. Add 10kΩ pull-up resistor on DATA pin |
| Sound sensor reads 0 | Adjust potentiometer on KY-038 module |
| MQ-135 reads very high | Needs 24-48h burn-in. High readings initially are normal |
| Dashboard stuck on SIM mode | Ensure Flask server is running. Check browser console for WS errors |
| PIR always HIGH | Wait 60s for calibration. Adjust sensitivity potentiometer |
| Browser shows offline | Server and browser must use same URL (localhost:5000) |

---

## Network Setup Options

### Option A: College WiFi
- Both ESP32 and laptop connect to college WiFi
- Note: Some college networks block device-to-device communication
- If blocked, use Option B

### Option B: Phone Hotspot
- Create hotspot on your phone
- Connect both ESP32 and laptop to this hotspot
- More reliable for demo day

### Option C: Laptop Hotspot
- Windows → Settings → Network → Mobile Hotspot
- Connect ESP32 to this hotspot
- Server runs on localhost, ESP32 sends to laptop IP

---

## Project Demo Checklist

- [ ] Flask server running on laptop
- [ ] ESP32-01 flashed and connected
- [ ] ESP32-02 flashed and connected (optional)
- [ ] Dashboard shows 🟢 LIVE MODE
- [ ] Sensor data updating in real-time
- [ ] Switch between rooms in dropdown
- [ ] Show Historical Analytics page
- [ ] Show Engagement Reports with AI insights
- [ ] Show Environment Monitor with gauges
- [ ] Show Alerts when thresholds exceeded
- [ ] Demo event injection in Settings
- [ ] Show Export JSON functionality
- [ ] Explain ML model (formula + Random Forest hybrid)
