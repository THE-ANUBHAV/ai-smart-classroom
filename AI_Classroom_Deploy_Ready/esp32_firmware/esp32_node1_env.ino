/*
 * ================================================================
 *  ESP32 NODE 1 — Environment Sensors
 *  A.E.G.I.S. Smart Classroom | Team-8 | GLA University
 *
 *  Sensors on this board:
 *    - DHT11  → Temperature & Humidity  (GPIO 15)
 *    - Sound  → KY-037/038 Analog       (GPIO 34)
 *    - Light  → LDR Analog              (GPIO 35)
 *
 *  This board sends data to:
 *    - Flask Dashboard (Render / Local) — for ML & live UI
 * ================================================================
 */

#include <ArduinoJson.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>

// ================================================================
//  ★★★  CHANGE THESE THREE LINES BEFORE UPLOADING  ★★★
// ================================================================

#define WIFI_SSID "TP-Link_7AE6" // ← Your WiFi name
#define WIFI_PASSWORD "36144044" // ← Your WiFi password
#define FLASK_SERVER_URL                                                       \
  "https://ai-smart-classroom.onrender.com/api/sensor-data"
// ↑ Paste your Render URL here
//   OR use local IP while testing:
//   "http://192.168.x.x:5000/api/sensor-data"

// ================================================================
//  Device Identity — no need to change these
// ================================================================
#define ESP_ID "ESP32-01"
#define ROOM "Room A101"

// ================================================================
//  Pin definitions — match your wiring
// ================================================================
#define DHT_PIN 15
#define DHT_TYPE DHT11
#define SOUND_PIN 34 // ADC1 — must use 32-39 when WiFi is on
#define LDR_PIN 35   // ADC1

// ================================================================
//  Timing
// ================================================================
#define SEND_INTERVAL_MS 5000 // Send every 5 seconds

// ================================================================
//  Globals
// ================================================================
DHT dht(DHT_PIN, DHT_TYPE);

// ================================================================
//  SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==========================================");
  Serial.println("  A.E.G.I.S. Node 1 — Environment");
  Serial.println("  Team-8 | GLA University");
  Serial.println("==========================================");

  dht.begin();

  // Connect to WiFi
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[WiFi] Connected! IP: %s\n",
                WiFi.localIP().toString().c_str());
  Serial.printf("[HTTP] Target: %s\n\n", FLASK_SERVER_URL);
}

// ================================================================
//  MAIN LOOP
// ================================================================
void loop() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int soundRaw = analogRead(SOUND_PIN);
  int lightRaw = analogRead(LDR_PIN);

  // Convert raw sound ADC → approximate dB
  float soundDb = (float)map(soundRaw, 0, 4095, 30, 90);

  // Debug output — open Serial Monitor at 115200 baud to see this
  Serial.printf("[Node1] Temp: %.1f°C | Hum: %.1f%% | Sound: %.0f dB (raw %d) "
                "| Light: %d\n",
                temperature, humidity, soundDb, soundRaw, lightRaw);

  // Push to Flask dashboard (primary — always enabled)
  pushToFlask(temperature, humidity, soundDb, soundRaw, lightRaw);

  delay(SEND_INTERVAL_MS);
}

// ================================================================
//  Send data to Flask Dashboard (Render URL or Local IP)
// ================================================================
void pushToFlask(float temp, float hum, float soundDb, int soundRaw,
                 int lightRaw) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi lost — skipping send");
    return;
  }

  HTTPClient http;
  http.begin(FLASK_SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000); // 8-second timeout for Render cold starts

  StaticJsonDocument<256> doc;
  doc["esp_id"] = ESP_ID;
  doc["room"] = ROOM;
  if (!isnan(temp))
    doc["temperature"] = round(temp * 10.0) / 10.0;
  if (!isnan(hum))
    doc["humidity"] = round(hum * 10.0) / 10.0;
  doc["sound_level"] = soundDb;
  doc["sound_raw"] = soundRaw;
  doc["ldr_value"] = lightRaw;

  String payload;
  serializeJson(doc, payload);

  int code = http.POST(payload);
  if (code == 200) {
    Serial.println("[HTTP] ✓ Flask: OK");
  } else {
    Serial.printf("[HTTP] ✗ Flask error: %d\n", code);
  }
  http.end();
}
