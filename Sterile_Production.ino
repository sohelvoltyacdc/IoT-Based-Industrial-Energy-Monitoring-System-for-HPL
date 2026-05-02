/**
 * HPL Energy Monitoring - Warehouse
 * Device: Sterile_Production_Device_02
 * Sends data to Google Sheets (Main Dashboard + Daily History)
 */

#include <WiFiManager.h>
#include <ModbusMaster.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include "time.h"

// ================================================================
//  HARDWARE PINS
// ================================================================
#define RS485_DE_RE     4
#define RS485_RX        18
#define RS485_TX        17
#define MODBUS_SLAVE    1

// ================================================================
//  REGISTER MAP (0-based)
// ================================================================
#define REG_ENERGY      2699   // Total kWh

// ================================================================
//  GOOGLE SHEETS WEBHOOK
// ================================================================
const char* webhookUrl = "https://script.google.com/macros/s/AKfycbxEG7tbGN9vwa87WBBR383nqtxwtk5uwXBHVR8AJvwzC386D5lhLfsEalMcoezhHdAl/exec";
const char* deviceId = "Sterile_Production_Device_02";

// ================================================================
//  TIMING
// ================================================================
const unsigned long READ_INTERVAL_MS    = 5000;    // Read Modbus every 5 sec
const unsigned long TODAY_SEND_INTERVAL = 120000;  // Send Today's kWh every 2 min

// ================================================================
//  GLOBAL VARIABLES
// ================================================================
ModbusMaster node;
Preferences prefs;

float dailyBaseKWh    = 0.0;
float yesterdayKWh    = 0.0;
float currentTotalKWh = 0.0;
int   lastDay         = -1;
bool  yesterdaySent   = false;
unsigned long lastRead      = 0;
unsigned long lastTodaySend = 0;

// ================================================================
//  MODBUS FUNCTIONS
// ================================================================
float readModbusFloat(uint16_t reg) {
  uint8_t result = node.readHoldingRegisters(reg, 2);
  if (result != node.ku8MBSuccess) return NAN;
  uint32_t raw = ((uint32_t)node.getResponseBuffer(0) << 16) | node.getResponseBuffer(1);
  float val;
  memcpy(&val, &raw, 4);
  return val;
}

// ================================================================
//  GOOGLE SHEETS SENDER
// ================================================================
void sendToGoogleSheets(float todayKwh, float yesterdayKwh, float totalKwh) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[GS] WiFi not connected");
    return;
  }
  
  HTTPClient http;
  http.begin(webhookUrl);
  http.addHeader("Content-Type", "application/json");
  
  struct tm tm;
  char timestamp[32];
  if (getLocalTime(&tm)) {
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &tm);
  } else {
    strcpy(timestamp, "N/A");
  }
  
  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;
  doc["today_kwh"] = todayKwh;
  doc["yesterday_kwh"] = yesterdayKwh;
  doc["total_kwh"] = totalKwh;
  doc["timestamp"] = timestamp;
  
  char buffer[256];
  serializeJson(doc, buffer);
  
  Serial.printf("[GS] Sending: %s\n", buffer);
  
  int httpCode = http.POST(buffer);
  
  if (httpCode > 0) {
    Serial.printf("[GS] Success, code: %d\n", httpCode);
    Serial.printf("[GS] Response: %s\n", http.getString().c_str());
  } else {
    Serial.printf("[GS] Failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
}

// ================================================================
//  PREFERENCES (SAVE TO FLASH)
// ================================================================
void saveToPreferences() {
  prefs.begin("hpl_data", false);
  prefs.putFloat("dailyBase", dailyBaseKWh);
  prefs.putFloat("yesterday", yesterdayKWh);
  prefs.putInt("lastDay", lastDay);
  prefs.end();
}

void loadFromPreferences() {
  prefs.begin("hpl_data", false);
  dailyBaseKWh = prefs.getFloat("dailyBase", 0.0);
  yesterdayKWh = prefs.getFloat("yesterday", 0.0);
  lastDay      = prefs.getInt("lastDay", -1);
  prefs.end();
  Serial.printf("[LOAD] dailyBase: %.3f, yesterday: %.3f, lastDay: %d\n", 
                dailyBaseKWh, yesterdayKWh, lastDay);
}

// ================================================================
//  SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n=== HPL Warehouse Energy Monitor ===");
  Serial.printf("Device ID: %s\n", deviceId);
  
  // Watchdog
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = 15000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  
  // RS485
  pinMode(RS485_DE_RE, OUTPUT);
  digitalWrite(RS485_DE_RE, LOW);
  Serial2.begin(19200, SERIAL_8E1, RS485_RX, RS485_TX);
  node.begin(MODBUS_SLAVE, Serial2);
  node.preTransmission([]() { digitalWrite(RS485_DE_RE, HIGH); });
  node.postTransmission([]() { delay(2); digitalWrite(RS485_DE_RE, LOW); });
  
  // WiFi
  WiFiManager wm;
  wm.autoConnect("HPL_Warehouse_Node");
  Serial.println("[WiFi] Connected");
  
  // NTP (GMT+6)
  configTime(6 * 3600, 0, "pool.ntp.org", "time.google.com");
  
  struct tm tm;
  while (!getLocalTime(&tm)) {
    Serial.print(".");
    delay(1000);
  }
  Serial.println("\n[NTP] Time synced");
  
  loadFromPreferences();
  Serial.println("\n=== System Ready ===\n");
}

// ================================================================
//  LOOP
// ================================================================
void loop() {
  esp_task_wdt_reset();
  
  if (millis() - lastRead >= READ_INTERVAL_MS) {
    lastRead = millis();
    
    float kwh = readModbusFloat(REG_ENERGY);
    if (isnan(kwh)) {
      Serial.println("[WARN] Modbus read failed");
      return;
    }
    
    currentTotalKWh = kwh;
    
    struct tm tm;
    if (!getLocalTime(&tm)) return;
    
    int currentDay = tm.tm_mday;
    int hour = tm.tm_hour;
    int min = tm.tm_min;
    
    // First boot
    if (lastDay == -1) {
      lastDay = currentDay;
      dailyBaseKWh = currentTotalKWh;
      saveToPreferences();
      Serial.println("[INIT] First boot");
    }
    
    // Midnight reset
    if (currentDay != lastDay) {
      yesterdayKWh = currentTotalKWh - dailyBaseKWh;
      if (yesterdayKWh < 0) yesterdayKWh = 0;
      dailyBaseKWh = currentTotalKWh;
      lastDay = currentDay;
      yesterdaySent = false;
      saveToPreferences();
      Serial.printf("[MIDNIGHT] New day: %d, yesterday: %.3f kWh\n", lastDay, yesterdayKWh);
    }
    
    float todayUsage = currentTotalKWh - dailyBaseKWh;
    if (todayUsage < 0) todayUsage = 0;
    
    // Send Today's kWh every 2 minutes
    if (millis() - lastTodaySend >= TODAY_SEND_INTERVAL) {
      lastTodaySend = millis();
      sendToGoogleSheets(todayUsage, -1, currentTotalKWh);
      Serial.printf("[TODAY] %.3f kWh, Total: %.3f kWh\n", todayUsage, currentTotalKWh);
    }
    
    // Send Yesterday's kWh at 00:05 AM
    if (hour == 0 && min >= 5 && min <= 6 && !yesterdaySent) {
      yesterdaySent = true;
      sendToGoogleSheets(todayUsage, yesterdayKWh, currentTotalKWh);
      Serial.printf("[YESTERDAY] %.3f kWh sent\n", yesterdayKWh);
    }
    
    Serial.printf("[DEBUG] %02d:%02d:%02d | Total: %.3f | Today: %.3f | Yesterday: %.3f\n",
                  hour, min, tm.tm_sec, currentTotalKWh, todayUsage, yesterdayKWh);
  }
  
  delay(100);
}