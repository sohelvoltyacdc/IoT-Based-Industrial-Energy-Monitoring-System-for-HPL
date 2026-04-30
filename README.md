Description
This project is an advanced Industrial IoT (IIoT) Energy Monitoring System developed for Healthcare Pharmaceuticals Ltd (HPL). It monitors real-time electrical parameters from a 3-phase energy meter using an ESP32-S3 and transmits data to a ThingsBoard server.

Key Features
Real-time Monitoring: Tracks Average Voltage, Current, Active Power (kW), and Energy (kWh).

Daily Usage Calculation: Automatically calculates and resets "Today's kWh" and "Yesterday's kWh" at midnight.

Offline Data Preservation: Uses ESP32 Flash memory (Preferences) to save energy data, ensuring no data loss during internet outages.

Automatic Recovery: Automatically reconnects to WiFi and MQTT/ThingsBoard once the connection is restored.

Industrial Communication: Uses Modbus RS485 for reliable data fetching from energy meters.

Hardware Components
Microcontroller: ESP32-S3

Energy Meter: Modbus-enabled 3-Phase Smart Meter

Communication: RS485 to TTL Module (MAX485/MAX3485)

Status Indicator: Built-in WS2812 RGB LED for system status.

Software Stack
Framework: Arduino IDE / PlatformIO

IoT Platform: ThingsBoard (Professional Dashboard)

Libraries: WiFiManager, PubSubClient, ModbusMaster, ArduinoJson, Preferences
