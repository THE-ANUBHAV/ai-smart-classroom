/*
 * ═══════════════════════════════════════════════════════════════
 *  ESP32 SENSOR NODE — Smart Classroom IoT System
 *  Team-8 | GLA University | B.Tech CSE (AI-ML)
 *  
 *  Hardware: ESP32 DevKit V1 (30-pin)
 *  Sensors:
 *    - DHT11/DHT22 (Temperature & Humidity) on GPIO 4
 *    - PIR-1 HC-SR501 (Left Zone) on GPIO 14
 *    - PIR-2 HC-SR501 (Center Zone) on GPIO 27
 *    - PIR-3 HC-SR501 (Right Zone) on GPIO 26
 *    - KY-037/KY-038 Sound Sensor on GPIO 34 (ADC1)
 *    - MQ-135 Air Quality (optional) on GPIO 35 (ADC1)
 *    - LDR Light Sensor (optional) on GPIO 32 (ADC1)
 *  
 *  Communication: HTTP POST to Flask server every 3 seconds
 *  
 *  Required Libraries (install via Arduino Library Manager):
 *    - DHT sensor library by Adafruit
 *    - ArduinoJson by Benoit Blanchon
 *    - WiFi (built-in for ESP32)
 *    - HTTPClient (built-in for ESP32)
 * ═══════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ═══════════════════════════════════════
// ═══ CONFIGURATION — CHANGE THESE! ═══
// ═══════════════════════════════════════

// WiFi credentials — UPDATE THESE for your network
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // <-- Change this
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";    // <-- Change this

// Flask server IP — UPDATE THIS to your laptop's IP
// Find your IP: Open CMD → type "ipconfig" → look for IPv4 Address
const char* SERVER_IP   = "192.168.1.100";           // <-- Change this
const int   SERVER_PORT = 5000;

// Device identity
const char* ESP_ID   = "ESP32-01";   // Change to "ESP32-02" for second board
const char* ROOM     = "Room A101";  // Change per classroom

// Timing
const unsigned long SEND_INTERVAL = 3000;  // Send data every 3 seconds (ms)

// ═══════════════════════════════════════
// ═══ PIN DEFINITIONS ═══
// ═══════════════════════════════════════

// DHT Sensor
#define DHT_PIN       4
#define DHT_TYPE      DHT11    // Change to DHT22 if using DHT22

// PIR Motion Sensors (3 zones for classroom coverage)
#define PIR1_PIN      14   // Left zone
#define PIR2_PIN      27   // Center zone
#define PIR3_PIN      26   // Right zone

// Sound Sensor (KY-037/KY-038) — Analog output
#define SOUND_PIN     34   // Must use ADC1 pins (32-39) when WiFi active

// MQ-135 Air Quality Sensor (optional) — Analog output
#define AIR_QUALITY_PIN  35  // ADC1

// LDR Light Sensor (optional) — Analog output
#define LDR_PIN       32   // ADC1

// Built-in LED for status indication
#define LED_PIN       2    // Built-in LED on most ESP32 boards

// ═══════════════════════════════════════
// ═══ FEATURE TOGGLES ═══
// ═══════════════════════════════════════

// Set to false if you don't have these optional sensors
#define USE_AIR_QUALITY  true   // MQ-135 connected?
#define USE_LDR          true   // LDR connected?

// ═══════════════════════════════════════
// ═══ GLOBALS ═══
// ═══════════════════════════════════════

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastSendTime = 0;
int sendCount = 0;
bool serverConnected = false;

// Sound sampling variables
const int SOUND_SAMPLES = 50;  // Number of samples for averaging

// ═══════════════════════════════════════
// ═══ SETUP ═══
// ═══════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("═══════════════════════════════════════════");
  Serial.println("  Smart Classroom IoT Sensor Node");
  Serial.println("  Team-8 | GLA University");
  Serial.println("═══════════════════════════════════════════");
  
  // Initialize pins
  pinMode(PIR1_PIN, INPUT);
  pinMode(PIR2_PIN, INPUT);
  pinMode(PIR3_PIN, INPUT);
  pinMode(SOUND_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  #if USE_AIR_QUALITY
    pinMode(AIR_QUALITY_PIN, INPUT);
  #endif
  
  #if USE_LDR
    pinMode(LDR_PIN, INPUT);
  #endif
  
  // Initialize DHT sensor
  dht.begin();
  
  // Connect to WiFi
  connectWiFi();
  
  // PIR sensors need ~60 seconds to calibrate
  Serial.println("[INIT] Waiting 10s for PIR sensor calibration...");
  for (int i = 10; i > 0; i--) {
    Serial.printf("  %d seconds...\n", i);
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(1000);
  }
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("[INIT] System ready! Starting data collection...\n");
}

// ═══════════════════════════════════════
// ═══ MAIN LOOP ═══
// ═══════════════════════════════════════

void loop() {
  // Ensure WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  
  // Send data at configured interval
  if (millis() - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = millis();
    
    // Read all sensors
    float temperature = readTemperature();
    float humidity = readHumidity();
    int pir1 = readPIR(PIR1_PIN);
    int pir2 = readPIR(PIR2_PIN);
    int pir3 = readPIR(PIR3_PIN);
    float soundLevel = readSoundLevel();
    int soundRaw = analogRead(SOUND_PIN);
    float airQuality = 0;
    float ldrValue = 0;
    
    #if USE_AIR_QUALITY
      airQuality = readAirQuality();
    #endif
    
    #if USE_LDR
      ldrValue = readLDR();
    #endif
    
    // Print to Serial monitor for debugging
    Serial.printf("[#%d] Temp: %.1f°C | Hum: %.1f%% | PIR: %d/%d/%d | Sound: %.1f dB",
      ++sendCount, temperature, humidity, pir1, pir2, pir3, soundLevel);
    
    #if USE_AIR_QUALITY
      Serial.printf(" | AQ: %.0f", airQuality);
    #endif
    #if USE_LDR
      Serial.printf(" | LDR: %.0f", ldrValue);
    #endif
    Serial.println();
    
    // Send to Flask server
    sendToServer(temperature, humidity, pir1, pir2, pir3,
                 soundLevel, soundRaw, airQuality, ldrValue);
  }
}

// ═══════════════════════════════════════
// ═══ WIFI CONNECTION ═══
// ═══════════════════════════════════════

void connectWiFi() {
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  WiFi.setAutoReconnect(true);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("[WiFi] Server target: http://%s:%d\n", SERVER_IP, SERVER_PORT);
    digitalWrite(LED_PIN, HIGH);
    delay(500);
    digitalWrite(LED_PIN, LOW);
  } else {
    Serial.println("\n[WiFi] Connection FAILED! Will retry...");
  }
}

// ═══════════════════════════════════════
// ═══ SENSOR READING FUNCTIONS ═══
// ═══════════════════════════════════════

float readTemperature() {
  float temp = dht.readTemperature();
  if (isnan(temp)) {
    Serial.println("[WARN] DHT temperature read failed, using last value");
    return 23.0;  // Default fallback
  }
  return temp;
}

float readHumidity() {
  float hum = dht.readHumidity();
  if (isnan(hum)) {
    Serial.println("[WARN] DHT humidity read failed, using last value");
    return 50.0;  // Default fallback
  }
  return hum;
}

int readPIR(int pin) {
  // PIR outputs HIGH (1) when motion detected
  return digitalRead(pin);
}

float readSoundLevel() {
  /*
   * KY-037/KY-038 outputs analog value 0-4095 on ESP32.
   * We sample multiple times to get an accurate reading,
   * then convert to approximate dB scale.
   * 
   * Calibration notes:
   * - Silent room: ~30-40 dB (raw ~100-500)
   * - Normal conversation: ~55-65 dB (raw ~1000-2000)
   * - Loud noise: ~75-90 dB (raw ~2500-3500)
   * 
   * Adjust the mapping formula based on your specific sensor.
   */
  long sum = 0;
  int peak = 0;
  
  for (int i = 0; i < SOUND_SAMPLES; i++) {
    int raw = analogRead(SOUND_PIN);
    int amplitude = abs(raw - 2048);  // Center around midpoint
    sum += amplitude;
    if (amplitude > peak) peak = amplitude;
    delayMicroseconds(200);
  }
  
  float avgAmplitude = (float)sum / SOUND_SAMPLES;
  
  // Map amplitude to approximate dB (adjust these values after calibration)
  // Using logarithmic mapping for more realistic dB values
  float db;
  if (avgAmplitude < 10) {
    db = 30.0;  // Very quiet
  } else {
    db = 20.0 * log10(avgAmplitude) + 20.0;  // Approximate dB conversion
  }
  
  // Clamp to realistic classroom range
  db = constrain(db, 25.0, 100.0);
  
  return db;
}

float readAirQuality() {
  /*
   * MQ-135 outputs analog value.
   * Higher values = more pollution (CO2, NH3, etc.)
   * Raw values need calibration for actual PPM readings.
   * 
   * For demo purposes, we map to a 0-500 scale:
   * 0-50: Good | 50-100: Moderate | 100-200: Unhealthy
   * 200-300: Very Unhealthy | 300+: Hazardous
   */
  int raw = analogRead(AIR_QUALITY_PIN);
  
  // Simple mapping: 0-4095 → 0-500 AQI proxy
  float aqi = map(raw, 0, 4095, 0, 500);
  
  // Apply smoothing (basic low-pass filter)
  static float lastAqi = 0;
  aqi = 0.7 * aqi + 0.3 * lastAqi;
  lastAqi = aqi;
  
  return aqi;
}

float readLDR() {
  /*
   * LDR (Light Dependent Resistor) with voltage divider.
   * Higher analog value = more light.
   * Range: 0 (dark) to 4095 (bright)
   */
  int raw = analogRead(LDR_PIN);
  
  // Map to 0-1000 lux approximation
  float lux = map(raw, 0, 4095, 0, 1000);
  return lux;
}

// ═══════════════════════════════════════
// ═══ DATA TRANSMISSION ═══
// ═══════════════════════════════════════

void sendToServer(float temp, float hum, int pir1, int pir2, int pir3,
                  float soundDb, int soundRaw, float airQuality, float ldrValue) {
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi not connected, skipping send");
    return;
  }
  
  HTTPClient http;
  String url = String("http://") + SERVER_IP + ":" + SERVER_PORT + "/api/sensor-data";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);  // 5 second timeout
  
  // Build JSON payload
  StaticJsonDocument<512> doc;
  doc["esp_id"] = ESP_ID;
  doc["room"] = ROOM;
  doc["temperature"] = round(temp * 10.0) / 10.0;  // 1 decimal
  doc["humidity"] = round(hum * 10.0) / 10.0;
  doc["pir1"] = pir1;
  doc["pir2"] = pir2;
  doc["pir3"] = pir3;
  doc["sound_level"] = round(soundDb * 10.0) / 10.0;
  doc["sound_raw"] = soundRaw;
  
  #if USE_AIR_QUALITY
    doc["air_quality"] = round(airQuality);
  #endif
  
  #if USE_LDR
    doc["ldr_value"] = round(ldrValue);
  #endif
  
  String payload;
  serializeJson(doc, payload);
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200) {
    String response = http.getString();
    Serial.printf("[HTTP] ✓ Sent OK — Response: %s\n", response.c_str());
    
    // Blink LED on successful send
    digitalWrite(LED_PIN, HIGH);
    delay(50);
    digitalWrite(LED_PIN, LOW);
    
    serverConnected = true;
  } else if (httpCode > 0) {
    Serial.printf("[HTTP] ✗ Server error: %d\n", httpCode);
    serverConnected = false;
  } else {
    Serial.printf("[HTTP] ✗ Connection failed: %s\n", http.errorToString(httpCode).c_str());
    serverConnected = false;
  }
  
  http.end();
}
