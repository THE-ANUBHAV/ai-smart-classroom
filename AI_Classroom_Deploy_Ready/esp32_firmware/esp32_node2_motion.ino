/*
 * ================================================================
 *  ESP32 NODE 2 — Motion & Air Quality Sensors
 *  A.E.G.I.S. Smart Classroom | Team-8 | GLA University
 *
 *  Sensors on this board:
 *    - PIR-1  HC-SR501 (Left Zone)    → GPIO 14
 *    - PIR-2  HC-SR501 (Centre Zone)  → GPIO 27
 *    - PIR-3  HC-SR501 (Right Zone)   → GPIO 26
 *    - MQ-135 Air Quality (Analog)    → GPIO 35
 *    - DHT11  Temperature/Humidity    → GPIO 4  (optional)
 *
 *  This board sends data to:
 *    1. Flask Dashboard (Render / Local) — for ML & live UI
 *    2. ThingWorx Cloud  — optional, disabled by default
 * ================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ================================================================
//  ★★★  CHANGE THESE THREE LINES BEFORE UPLOADING  ★★★
// ================================================================

#define WIFI_SSID    "GLA"                        // ← Your WiFi name
#define WIFI_PASSWORD "GLACAMPUS"                 // ← Your WiFi password
#define SERVER_URL   "https://YOUR-RENDER-APP.onrender.com/api/sensor-data"
                                                   // ↑ Paste your Render URL here
                                                   //   OR use local IP while testing:
                                                   //   "http://192.168.x.x:5000/api/sensor-data"

// ================================================================
//  Device Identity — no need to change these
// ================================================================
#define ESP_ID  "ESP32-02"
#define ROOM    "Room A101"

// ================================================================
//  DHT on Node 2 — set false if no DHT sensor on this board
//  When false, temperature & humidity are NOT sent — preventing
//  Node 2 from overwriting Node 1's real sensor values.
// ================================================================
#define HAS_DHT_NODE2 true

// ================================================================
//  ThingWorx — set to true only if you want direct TWX push
// ================================================================
#define USE_THINGWORX false

#if USE_THINGWORX
  #define TWX_SERVER  "http://172.16.78.20:7080"
  #define TWX_APP_KEY "ab608e23-00b8-433c-8a2c-a5adb4593de6"
  #define TWX_THING   "project_esp32_thing_02"
#endif

// ================================================================
//  Pin definitions — match your wiring
// ================================================================
#define PIR1_PIN        14
#define PIR2_PIN        27
#define PIR3_PIN        26
#define MQ135_PIN       35    // ADC1 — analog air quality
#define LED_PIN          2    // Built-in LED for status blink

#if HAS_DHT_NODE2
  #define DHT_PIN  4
  #define DHT_TYPE DHT11
  DHT dht(DHT_PIN, DHT_TYPE);
#endif

// ================================================================
//  Timing
// ================================================================
#define SEND_INTERVAL_MS 5000   // Send every 5 seconds

// ================================================================
//  Globals
// ================================================================
unsigned long lastSendTime = 0;
int sendCount = 0;

// ================================================================
//  SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n==========================================");
  Serial.println("  A.E.G.I.S. Node 2 — Motion & Air");
  Serial.println("  Team-8 | GLA University");
  Serial.println("==========================================");

  pinMode(PIR1_PIN, INPUT);
  pinMode(PIR2_PIN, INPUT);
  pinMode(PIR3_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  #if HAS_DHT_NODE2
    dht.begin();
    Serial.println("[DHT] DHT sensor initialized on GPIO 4");
  #else
    Serial.println("[DHT] No DHT on Node 2 — temp/humidity NOT sent from this board");
  #endif

  // Connect to WiFi
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }
  digitalWrite(LED_PIN, LOW);
  Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
  Serial.printf("[HTTP] Target: %s\n", SERVER_URL);

  // PIR sensors need ~10s warm-up after power-on
  Serial.println("[PIR] Warming up (10 s)...");
  for (int i = 10; i > 0; i--) {
    Serial.printf("  %d...\n", i);
    delay(1000);
  }
  Serial.println("[INIT] Node 2 ready!\n");
}

// ================================================================
//  MAIN LOOP
// ================================================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Reconnecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    delay(3000);
    return;
  }

  if (millis() - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = millis();

    int pir1 = digitalRead(PIR1_PIN);
    int pir2 = digitalRead(PIR2_PIN);
    int pir3 = digitalRead(PIR3_PIN);

    int motionScore = (pir1 + pir2 + pir3) * 33;  // 0, 33, 66, or 99

    int airRaw    = analogRead(MQ135_PIN);
    int airQuality = map(airRaw, 0, 4095, 0, 500); // Map to 0-500 AQI proxy

    // Debug output — open Serial Monitor at 115200 baud to see this
    Serial.printf("[Node2 #%d] PIR: %d/%d/%d | Motion: %d%% | AQ: %d (raw %d)",
                  ++sendCount, pir1, pir2, pir3, motionScore, airQuality, airRaw);

    #if HAS_DHT_NODE2
      float temperature = dht.readTemperature();
      float humidity    = dht.readHumidity();
      if (!isnan(temperature)) Serial.printf(" | Temp: %.1f°C | Hum: %.1f%%", temperature, humidity);
      Serial.println();
      pushToFlask(pir1, pir2, pir3, airQuality, temperature, humidity);
    #else
      Serial.println();
      pushToFlask(pir1, pir2, pir3, airQuality, NAN, NAN);
    #endif

    // Optional: Push directly to ThingWorx
    #if USE_THINGWORX
      updateThingWorxProperty("pir1",         pir1 ? "true" : "false");
      updateThingWorxProperty("pir2",         pir2 ? "true" : "false");
      updateThingWorxProperty("pir3",         pir3 ? "true" : "false");
      updateThingWorxProperty("motion_score", String(motionScore));
      updateThingWorxProperty("air_quality",  String(airRaw));
      #if HAS_DHT_NODE2
        if (!isnan(temperature)) {
          updateThingWorxProperty("temperature_back", String(temperature));
          updateThingWorxProperty("humidity_back",    String(humidity));
        }
      #endif
    #endif

    // Blink LED to confirm a successful cycle
    digitalWrite(LED_PIN, HIGH); delay(80); digitalWrite(LED_PIN, LOW);
  }
}

// ================================================================
//  Send data to Flask Dashboard (Render URL or Local IP)
//  Only sends temp/humidity if HAS_DHT_NODE2 is true AND values
//  are valid — preventing overwriting Node 1's real readings.
// ================================================================
void pushToFlask(int p1, int p2, int p3, int airQuality, float temp, float hum) {
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);  // 8-second timeout for Render cold starts

  StaticJsonDocument<256> doc;
  doc["esp_id"]      = ESP_ID;
  doc["room"]        = ROOM;
  doc["pir1"]        = p1;
  doc["pir2"]        = p2;
  doc["pir3"]        = p3;
  doc["air_quality"] = airQuality;

  // Only include temp/humidity if DHT is present on this board AND reading is valid
  if (!isnan(temp)) doc["temperature"] = round(temp * 10.0) / 10.0;
  if (!isnan(hum))  doc["humidity"]    = round(hum  * 10.0) / 10.0;

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

// ================================================================
//  ThingWorx property update (only compiled if USE_THINGWORX true)
// ================================================================
#if USE_THINGWORX
void updateThingWorxProperty(String propName, String value) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  String url = String(TWX_SERVER) + "/Thingworx/Things/" + TWX_THING + "/Properties/" + propName;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("appKey", TWX_APP_KEY);
  http.addHeader("Accept", "application/json");
  String body = "{\"" + propName + "\":" + value + "}";
  int code = http.PUT(body);
  Serial.printf("[TWX] %s → %d\n", propName.c_str(), code);
  http.end();
  delay(300);
}
#endif
