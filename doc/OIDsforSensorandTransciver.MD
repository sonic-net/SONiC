# Sensor and Transceiver Info Monitoring Requirement
## Overall Requirement
As shown in the following diagram, we need to collect sensor and transceiver infomation from SFP into Telemetry DB and then into snmpagent.
![alt text](https://github.com/Azure/SONiC/blob/gh-pages/doc/SensorMonitor.PNG)

## Proposed Telemetry DB Schema    
### Keyname:  COUNTERS:SENSOR:[IntefaceName]
Field: [SensorName] : [SensorValue]

Example: 
- COUNTERS:SENSOR:Ethernet0
    - Temperature: 20.1367C
    - Vcc: 3.3324Volts
    - RX1Power: -2.0426dBm
    - RX2Power: -1.8177dBm
    - RX3Power: -1.7921dBm
    - RX4Power: -1.8046dBm 
    - TX1Bias: 0.0800mA
    - TX2Bias: 0.0940mA
    - TX3Bias: 0.1000mA
    - TX4Bias: 0.1260mA
    
### Keyname:  COUNTERS:TRANSCEIVER:[IntefaceName]
Fields: Descr, Name, HardwareVersion, FirmwareVersion ,SoftwareRevision, SerialNum, MfgName ,ModelName and their values
Example:
- COUNTERS:TRANSCEIVER:Ethernet0
    - Descr: Xcvr for Ethernet29
    - Name: Ethernet29
    - HardwareVersion: A1
    - FirmwareVersion:
    - SoftwareRevision:
    - SerialNum: WW5062F
    - MfgName: FINISAR CORP
    - ModelName: FCBN410QD3C02

## Transceiver requirements (ENTITY-MIB)

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |   |
| 1.3.6.1.2.1.47.1.1.1.1.2. ifindex | entPhysicalDescr | Show interfaces alias | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7. ifindex | entPhysicalName | Show interfaces alias | Ethernet29/1 |
| 1.3.6.1.2.1.47.1.1.1.1.8. ifindex | entPhysicalHardwareVersion | Vendor Rev in CLI | A1 |
| 1.3.6.1.2.1.47.1.1.1.1.9. ifindex | entPhysicalFirmwareVersion | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.10.ifindex | entPhysicalSoftwareRevision | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.11.ifindex | entPhysicalSerialNum | Vendor SN in CLI | WW5062F |
| 1.3.6.1.2.1.47.1.1.1.1.12.ifindex | entPhysicalMfgName | Vendor Name in CLI | FINISAR CORP |
| 1.3.6.1.2.1.47.1.1.1.1.13.ifindex | entPhysicalModelName | Vendor PN in CLI | FCBN410QD3C02 |

- An example as reference:

| OID | SNMP counter | Value |
| --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |
| 1.3.6.1.2.1.47.1.1.1.1.2. 100329100 | entPhysicalDescr | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7. 100329210 | entPhysicalName |   |
| 1.3.6.1.2.1.47.1.1.1.1.8. 100329210 | entPhysicalHardwareVersion | A |
| 1.3.6.1.2.1.47.1.1.1.1.9. 100329210 | entPhysicalFirmwareVersion |   |
| 1.3.6.1.2.1.47.1.1.1.1.10. 100329210 | entPhysicalSoftwareRevision |   |
| 1.3.6.1.2.1.47.1.1.1.1.11. 100329210 | entPhysicalSerialNum | 40714F20112 |
| 1.3.6.1.2.1.47.1.1.1.1.12. 100329210 | entPhysicalMfgName | AOI |
| 1.3.6.1.2.1.47.1.1.1.1.13. 100329210 | entPhysicalModelName | AQOA9N09ADLN0720 |

## Sensor requirements (ENTITY-SENSOR-MIB)

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.99.1.1 | entPhySensorTable |   |   |
| 1.3.6.1.2.1.99.1.1.1 | entPhySensorEntry |   |   |
| 1.3.6.1.2.1.99.1.1.1.1.index | entPhySensorType | In CLI: E.g.RX1Power: -0.97dBm | 6 |
| 1.3.6.1.2.1.99.1.1.1.2.index | entPhySensorScale | Same as above | 8 |
| 1.3.6.1.2.1.99.1.1.1.3.index | entPhySensorPrecision | Same as above | 4 |
| 1.3.6.1.2.1.99.1.1.1.4.index | entPhySensorValue | Same as above | 7998 |
| 1.3.6.1.2.1.47.1.1.1.1.2.index | entPhysicalDescr | Show interfaces alias | DOM RX Power Sensor for DOM RX Power Sensor for Ethernet29/1 |

- All sensors to be added in MIB and the index to use:

| Sensor to collect | Proposed index to use |
| --- | --- |
| DOM RX Power Sensor for Ethernet[X]/[LANEID] | Ifindex \* 1000 + 200 + (LANEID - 1) \* 10 + 3 |
| DOM TX Bias Sensor for Ethernet[X]/[LANEID] | Ifindex \* 1000 + 200 + (LANEID - 1) \* 10 + 1 |
| DOM Temperature Sensor for Ethernet[X] | Ifindex \* 1000 + 200 + 1 |
| DOM Voltage Sensor for Ethernet[X] | Ifindex \* 1000 + 200 + 2 |

- An example as reference:

| OID | SNMP counter | Sensor 1 RX Power | Sensor 2 TX Bias Sensor | Sensor 3 Temperature | Sensor 4 Voltage |
| --- | --- | --- | --- | --- | --- |
| 1.3.6.1.2.1.99.1.1 | entPhySensorTable |   |   |   |   |
| 1.3.6.1.2.1.99.1.1.1 | entPhySensorEntry |   |   |   |   |
| Raw values in command output for DOM |   | -0.97dBm | 4.44mA | 25.39 | 3.37 Volts |
| Index used |   | 100329213 | 100329221 | 100329201 | 100329202 |
| 1.3.6.1.2.1.99.1.1.1.1.index | entPhySensorType |  6   (i.e.  watts according to EntitySensorDataType) | 5 (i.e.  amperes according to EntitySensorDataType) |  8   (i.e.  Celsius according to EntitySensorDataType) |  6   (i.e.  voltsDC according to EntitySensorDataType) |
| 1.3.6.1.2.1.99.1.1.1.2.index | entPhySensorScale |  8  (i.e.  milli according to EntitySensorDataScale) |  8  (i.e.  milli according to EntitySensorDataScale) |  9  (i.e.  units according to EntitySensorDataScale) |  9  (i.e.  units according to EntitySensorDataScale) |
| 1.3.6.1.2.1.99.1.1.1.3.index | entPhySensorPrecision |  4 | 2 | 1 | 2 |
| 1.3.6.1.2.1.99.1.1.1.4.index | entPhySensorValue | 7998 | 444 | 25.4 | 337 |
| 1.3.6.1.2.1.47.1.1.1.1.2.index | entPhysicalDescr | DOM RX Power Sensor for Ethernet29/1 | DOM RX Power Sensor for Ethernet29/1 | DOM Temperature Sensor for Ethernet29 | DOM Voltage Sensor for Ethernet29 |

Note: Enum definition:   [https://tools.ietf.org/html/rfc3433](https://tools.ietf.org/html/rfc3433)
