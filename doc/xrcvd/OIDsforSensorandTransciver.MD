# Sensor and Transceiver Info Monitoring Requirement
## Overall Requirement
As shown in the following diagram, we need to collect sensor and transceiver infomation from SFP into Sonic database and then into snmpagent.

- The new Xcvrd in platform monitor container should peroidally pull the new DOM sensor info to state DB. The finallized DB to be used to cache telemetry data is to be determined.

- Xcvrd should monitor the interrupt of new sfp plg-in event. When an event is triggered, the transceiver info should be retrived and updated in DB. At the initial implemenation, we can peroidally pull the new transceiver info until the new interrput is implemented too in this project.

- The snmpagent should subscribe to TRANSCEIVER keys in state DB and pull the sensor and transceiver info to SNMP MIBs when there is a change.

- The initial implemenation can get the data requiued via the dictionary returned by port_eeprom_data_string_pretty() API in sfputil. The API retrieve all EEPROM data block for each interface and then parse the whole data block. A potential opmization is to add new API in sfputil, which just retrives and parses the necessary data via the correspoding offset and size.

![alt text](SensorMonitor.PNG)

## Proposed State DB Schema
### Keyname:  TRANSCEIVER_INFO:[InterfaceName]
#### Fields: Type, HardwareVersion, SerialNum, ManufactureName, ModelName 
#### Example:
- TRANSCEIVER_INFO|Ethernet0
    - Type: (transciever type) # E.g. Xcvr
    - HardwareVersion: A1
    - SerialNum: WW5062F
    - ManufactureName: FINISAR CORP
    - ModelName: FCBN410QD3C02
### Keyname:  TRANSCEIVER_DOM_SENSOR:[InterfaceName]
#### Fields: Raw sendor values
#### Example:
- TRANSCEIVER_DOM_SENSOR|Ethernet0
    - Temperature: rawdata
    - Voltage: rawdata
    - RX1Power: rawdata # in dbm
    - RX2Power: rawdata
    - RX3Power: rawdata
    - RX4Power: rawdata
    - TX1Bias: rawdata  # in mA
    - TX2Bias: rawdata
    - TX3Bias: rawdata
    - TX4Bias: rawdata
    - TX1Power: rawdata # in dbm
    - TX2Power: rawdata
    - TX3Power: rawdata
    - TX4Power: rawdata



## Transceiver requirements (ENTITY-MIB)

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |   |
| 1.3.6.1.2.1.47.1.1.1.1.2. index | entPhysicalDescr | Show interfaces alias | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7. index | entPhysicalName | skipped |"" |
| 1.3.6.1.2.1.47.1.1.1.1.8. index | entPhysicalHardwareVersion | Vendor Rev in CLI or sfputil | A1 |
| 1.3.6.1.2.1.47.1.1.1.1.9. index | entPhysicalFirmwareVersion | Skipped | ""  |
| 1.3.6.1.2.1.47.1.1.1.1.10.index | entPhysicalSoftwareRevision | Skipped | ""  |
| 1.3.6.1.2.1.47.1.1.1.1.11.index | entPhysicalSerialNum | Vendor SN in CLI or sfputil | WW5062F |
| 1.3.6.1.2.1.47.1.1.1.1.12.index | entPhysicalMfgName | Vendor Name in CLI or sfputil | FINISAR CORP |
| 1.3.6.1.2.1.47.1.1.1.1.13.index | entPhysicalModelName | Vendor PN in CLI or sfputil| FCBN410QD3C02 |

ifindex is the ifindex in https://github.com/Azure/sonic-py-swsssdk/blob/master/src/swsssdk/port_util.py#L19

| Interface | Proposed index to use |
| --- | --- |
| Ethernet[X] | Ifindex \* 1000 |

- An example as reference (assume that interface Ethernet100's alias is Ethernet29) :

| OID | SNMP counter | Value |
| --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |
| 1.3.6.1.2.1.47.1.1.1.1.2.101000 | entPhysicalDescr | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7.101000 | entPhysicalName | |
| 1.3.6.1.2.1.47.1.1.1.1.8.101000 | entPhysicalHardwareVersion | A |
| 1.3.6.1.2.1.47.1.1.1.1.9.101000 | entPhysicalFirmwareVersion |   |
| 1.3.6.1.2.1.47.1.1.1.1.10.101000 | entPhysicalSoftwareRevision |   |
| 1.3.6.1.2.1.47.1.1.1.1.11.101000 | entPhysicalSerialNum | 40714F20112 |
| 1.3.6.1.2.1.47.1.1.1.1.12.101000 | entPhysicalMfgName | AOI |
| 1.3.6.1.2.1.47.1.1.1.1.13.101000 | entPhysicalModelName | AQOA9N09ADLN0720 |


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
| DOM RX Power Sensor for Ethernet[X]/[LANEID] | Ifindex \* 1000  + LANEID \* 10 + 1 |
| DOM TX Bias Sensor for Ethernet[X]/[LANEID] | Ifindex \* 1000  + LANEID \* 10 + 2 |
| DOM TX Power Sensor for Ethernet[X]/[LANEID] | Ifindex \* 1000  + LANEID \* 10 + 3 |
| DOM Temperature Sensor for Ethernet[X] | Ifindex \* 1000  + 1 |
| DOM Voltage Sensor for Ethernet[X] | Ifindex \* 1000 + 2 |

- An example as reference:

| OID | SNMP counter | Sensor 1 RX Power | Sensor 2 TX Bias Sensor | Sensor 3 Temperature | Sensor 4 Voltage |
| --- | --- | --- | --- | --- | --- |
| 1.3.6.1.2.1.99.1.1 | entPhySensorTable |   |   |   |   |
| 1.3.6.1.2.1.99.1.1.1 | entPhySensorEntry |   |   |   |   |
| Raw values in command output for DOM |   | -0.97dBm | 4.44mA | 25.39 | 3.37 Volts |
| Index used |   | 101011 | 101012 | 101001 | 101002 |
| 1.3.6.1.2.1.99.1.1.1.1.index | entPhySensorType |  6   (i.e.  watts according to EntitySensorDataType) | 5 (i.e.  amperes according to EntitySensorDataType) |  8   (i.e.  Celsius according to EntitySensorDataType) |  6   (i.e.  voltsDC according to EntitySensorDataType) |
| 1.3.6.1.2.1.99.1.1.1.2.index | entPhySensorScale |  8  (i.e.  milli according to EntitySensorDataScale) |  8  (i.e.  milli according to EntitySensorDataScale) |  9  (i.e.  units according to EntitySensorDataScale) |  9  (i.e.  units according to EntitySensorDataScale) |
| 1.3.6.1.2.1.99.1.1.1.3.index | entPhySensorPrecision |  4 | 2 | 1 | 2 |
| 1.3.6.1.2.1.99.1.1.1.4.index | entPhySensorValue | 7998 | 444 | 25.4 | 337 |
| 1.3.6.1.2.1.47.1.1.1.1.2.index | entPhysicalDescr | DOM RX Power Sensor for Ethernet29/1 | DOM RX Power Sensor for Ethernet29/1 | DOM Temperature Sensor for Ethernet29 | DOM Voltage Sensor for Ethernet29 |

Note: Enum definition:   [https://tools.ietf.org/html/rfc3433](https://tools.ietf.org/html/rfc3433)
