# 🚀 A.E.G.I.S. Deployment Guide
**Team-8 | GLA University | B.Tech CSE (AI-ML)**

This guide walks you through deploying the Smart Classroom backend to Render and flashing both ESP32 boards step-by-step.

---

## Part 1 — Deploy to GitHub

### Step 1: Install Git (if not already installed)
Download from: https://git-scm.com/downloads  
After install, open a terminal and verify: `git --version`

### Step 2: Create a GitHub Repository
1. Go to https://github.com and sign in.
2. Click **New Repository**.
3. Name it: `ai-smart-classroom`
4. Set to **Public** (required for free Render hosting).
5. Click **Create Repository**.

### Step 3: Upload your project
Open a terminal in your project folder (`AI_Classroom_Deploy_Ready`) and run:

```bash
git init
git add .
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/ai-smart-classroom.git
git push -u origin main
```

> **Tip:** Replace `YOUR-USERNAME` with your GitHub username.

---

## Part 2 — Deploy to Render

### Step 4: Create a Render account
Sign up at https://render.com (free tier works fine).

### Step 5: Create a New Web Service
1. On the Render dashboard, click **New → Web Service**.
2. Connect your GitHub account and select your `ai-smart-classroom` repository.
3. Fill in these settings:

| Setting | Value |
|---|---|
| **Name** | `ai-smart-classroom` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 1 --threads 100 --bind 0.0.0.0:$PORT app:app` |
| **Plan** | Free |

4. Click **Create Web Service** and wait ~3-5 minutes for the first build.

### Step 6: Verify Deployment
Once deployed, your app URL will look like:  
`https://ai-smart-classroom.onrender.com`

Test it in your browser:
```
https://ai-smart-classroom.onrender.com/api/health
```

You should see:
```json
{"status": "ok", "server": "SmartClassroom-API", ...}
```

---

## Part 3 — Configure ESP32 Boards

### Step 7: Install Arduino IDE
Download Arduino IDE 2.x from: https://www.arduino.cc/en/software

Install the following libraries via **Tools → Manage Libraries**:
- `DHT sensor library` by Adafruit
- `ArduinoJson` by Benoit Blanchon

Install ESP32 board support via **File → Preferences → Additional Boards Manager URLs**:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```
Then go to **Tools → Board → Boards Manager** and install `esp32`.

### Step 8: Flash ESP32 Node 1 (Environment — Front of Class)
1. Open `esp32_firmware/esp32_node1_env.ino` in Arduino IDE.
2. At the top of the file, find the **★★★ CHANGE THESE THREE LINES** section:
```cpp
#define WIFI_SSID       "TP-Link_7AE6"
#define WIFI_PASSWORD   "36144044"
#define FLASK_SERVER_URL "https://ai-smart-classroom.onrender.com/api/sensor-data"
```
3. Replace the Render URL with your actual Render app URL.
4. Connect your first ESP32 via USB.
5. In Arduino IDE: **Tools → Board → ESP32 Dev Module**, select correct **Port**.
6. Click **Upload** (→ button).
7. Open **Serial Monitor** (baud rate: **115200**) and watch for:
   ```
   [WiFi] Connected! IP: 192.168.x.x
   [HTTP] ✓ Flask: OK
   ```

### Step 9: Flash ESP32 Node 2 (Motion — Back of Class)
1. Open `esp32_firmware/esp32_node2_motion.ino` in Arduino IDE.
2. At the top, find the **★★★ CHANGE THESE THREE LINES** section:
```cpp
#define WIFI_SSID      "TP-Link_7AE6"
#define WIFI_PASSWORD  "36144044"
#define SERVER_URL     "https://ai-smart-classroom.onrender.com/api/sensor-data"
```
3. Replace the Render URL with your actual Render app URL.
4. Connect your second ESP32 and upload the same way.
5. Open Serial Monitor (115200 baud) and watch for:
   ```
   [Node2] PIR: 0/0/0 | Motion: 0% | AQ: 42
   [HTTP] ✓ Flask: OK
   ```

---

## Part 4 — Verify Live Data Flow

### Step 10: Open the Live Dashboard
Go to your Render URL in a browser:
```
https://ai-smart-classroom.onrender.com
```
Click **▶ INITIATE NEURAL LINK** to boot the A.E.G.I.S. HUD.  
In Settings → IoT Device Connection, set **Input Mode** to `WEBSOCKET` and click **🔌 Connect**.

You should see the sensor gauges updating every 5 seconds as your ESP32 boards send data!

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Render build fails | Check `requirements.txt` — no special characters or blank lines |
| `/api/health` gives 502 | App is still cold-starting — wait 60 seconds and retry |
| ESP32 shows `[HTTP] ✗ Flask error: -1` | Check your WiFi credentials and Render URL — must be HTTPS on Render |
| Dashboard shows no data | Check Settings → Input Mode is set to `WEBSOCKET` |
| PIR sensors triggering randomly | Normal for first 10 seconds — PIR needs warm-up time |
| Serial Monitor shows garbage | Make sure baud rate is set to **115200** |

---

## Quick Reference

| Endpoint | Purpose |
|---|---|
| `GET /` | Main A.E.G.I.S. dashboard |
| `GET /api/health` | Health check |
| `POST /api/sensor-data` | ESP32 data ingestion |
| `GET /api/readings` | Historical readings |
| `GET /api/alerts` | Alert history |
| `GET /api/devices` | Connected ESP32 list |

**Serial Monitor Baud Rate:** `115200`
