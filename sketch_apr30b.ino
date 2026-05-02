/**
 * Healthcare Pharmaceuticals Ltd (HPL)
 * EasyLogic PM2100 - Modbus Serial Monitor Test (Enhanced with PF & THD)
 */

#include <ModbusMaster.h>

// --- Hardware Pins ---
#define RS485_DE_RE     4
#define RS485_RX        18
#define RS485_TX        17
#define MODBUS_SLAVE    1

// --- PM2100 Registers (32-bit Float) ---
#define REG_V_AVG    3019  // Average Voltage L-L
#define REG_I_AVG    3009  // Average Current
#define REG_POWER    3059  // Total Active Power (kW)
#define REG_ENERGY   2699  // Total Energy (kWh)
#define REG_FREQ     3109  // Frequency (Hz)
#define REG_PF_AVG   3083  // Average Power Factor
#define REG_THD_V1   21101 // THD Voltage Phase 1
#define REG_THD_I1   21125 // THD Current Phase 1

ModbusMaster node;

void preTransmission()  { digitalWrite(RS485_DE_RE, HIGH); }
void postTransmission() { delay(1); digitalWrite(RS485_DE_RE, LOW); }

float readModbusFloat(uint16_t reg) {
    uint8_t result = node.readHoldingRegisters(reg, 2);
    if (result == node.ku8MBSuccess) {
        uint32_t raw = ((uint32_t)node.getResponseBuffer(0) << 16) | node.getResponseBuffer(1);
        float val;
        memcpy(&val, &raw, 4);
        return val;
    } else {
        return NAN;
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(RS485_DE_RE, OUTPUT);
    digitalWrite(RS485_DE_RE, LOW);

    // Modbus Serial - PM2100 standard settings
    Serial2.begin(19200, SERIAL_8E1, RS485_RX, RS485_TX);
    
    node.begin(MODBUS_SLAVE, Serial2);
    node.preTransmission(preTransmission);
    node.postTransmission(postTransmission);

    Serial.println("HPL PM2100 Advanced Test Starting...");
}

void loop() {
    float voltage = readModbusFloat(REG_V_AVG);
    float current = readModbusFloat(REG_I_AVG);
    float power   = readModbusFloat(REG_POWER);
    float energy  = readModbusFloat(REG_ENERGY);
    float freq    = readModbusFloat(REG_FREQ);
    float pf      = readModbusFloat(REG_PF_AVG);
    float thdV    = readModbusFloat(REG_THD_V1);
    float thdI    = readModbusFloat(REG_THD_I1);

    Serial.println("\n--- PM2100 Reading ---");
    
    if (!isnan(voltage)) {
        Serial.print("Voltage (L-L): "); Serial.print(voltage); Serial.println(" V");
        Serial.print("Current (Avg): "); Serial.print(current); Serial.println(" A");
        Serial.print("Active Power:  "); Serial.print(power);   Serial.println(" kW");
        Serial.print("Total Energy:  "); Serial.print(energy);  Serial.println(" kWh");
        Serial.print("Frequency:     "); Serial.print(freq);    Serial.println(" Hz");
        
        // নতুন প্যারামিটার
        Serial.print("Power Factor:  "); Serial.println(pf);
        Serial.print("THD Voltage:   "); Serial.print(thdV);   Serial.println(" %");
        Serial.print("THD Current:   "); Serial.print(thdI);   Serial.println(" %");
    } else {
        Serial.println("Modbus Read Error! Check Wiring or ID.");
    }

    Serial.println("----------------------");
    delay(4000); 
}