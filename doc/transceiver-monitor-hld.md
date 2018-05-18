# Transceiver and Sensor Monitoring HLD #

### Rev 0.1 ###

### Revision
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo      | Initial version                   |

## About This Manual ##

This document is intend to provide general information about the Transceiver and Sensor Monitoring implementation.
The requirement is described in [Sensor and Transceiver Info Monitoring Requirement.](https://github.com/Azure/SONiC/blob/gh-pages/doc/OIDsforSensorandTransciver.MD)

## 1. Xcvrd design ##

New Xcvrd in platform monitor container need to periodically fetch the transceiver and DOM sensor information from the eeprom. For now the time period temporarily set to 5s, need to be adjusted according the later test.

If there is transceiver and sensor status change, Xcvrd will write the new status to state DB, to store these information a new transceiver table will be added.
 
### 1.1 State DB Schema ###

New Transceiver table will be added to state DB to store the transceiver and DOM sensor information. 

#### 1.1.1 Transceiver Table ####

	; Defines Transceiver and DOM sensor information for a port
	key                     = TRANSCEIVER_TABLE|ifname         ; configuration for watchdog on port
	; field                 = value
	type                    = 1*255VCHAR                       ; type of sfp
	hardwarerev             = 1*255VCHAR                       ; hardware version of sfp
	serialnum               = 1*255VCHAR                       ; serial number of the sfp
	manufacturename         = 1*255VCHAR                       ; sfp venndor name
	modelname               = 1*255VCHAR                       ; sfp model name
	temperature             = FLOAT                            ; temperature value in Celsius
	voltage                 = FLOAT                            ; voltage value
	rx1power                = FLOAT                            ; rx1 power in dbm
	rx2power                = FLOAT                            ; rx2 power in dbm
	rx3power                = FLOAT                            ; rx3 power in dbm
	rx4power                = FLOAT                            ; rx4 power in dbm
	tx1bias                 = FLOAT                            ; tx1 bias in mA
	tx2bias                 = FLOAT                            ; tx2 bias in mA
	tx3bias                 = FLOAT                            ; tx3 bias in mA
	tx4bias                 = FLOAT                            ; tx4 bias in mA

### 1.2 Local cache for Transceiver info ###

Xcvrd will maintain a local cache for the Transceiver and DOM status, after fetched the latest status, will compare to the local cache. TRANSCEIVER_TABLE will only be updates when there is status change 

### 1.3 Xcvrd daemon flow ###

Xcvrd retrieve transceiver and DOM sensor information periodically via the sfputil. 

If the value of some field changed compare to local cache, local cache will be updated and Xcvrd will update the TRANSCEIVER_TABLE.  

![](https://github.com/Azure/SONiC/blob/gh-pages/images/transceiver_monitoring_hld/xcvrd_flow.svg)



## 2. SNMP Agent Change ##

### 2.1 MIB tables extension ###

MIB table entPhysicalTable from [Entity MIB(RFC2737)](https://tools.ietf.org/html/rfc2737) need to be extended to support new OIDs.

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |   |
| 1.3.6.1.2.1.47.1.1.1.1.2. ifindex | entPhysicalDescr | Show interfaces alias | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7. ifindex | entPhysicalName | skipped | |
| 1.3.6.1.2.1.47.1.1.1.1.8. ifindex | entPhysicalHardwareVersion | Vendor Rev in CLI or sfputil | A1 |
| 1.3.6.1.2.1.47.1.1.1.1.9. ifindex | entPhysicalFirmwareVersion | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.10.ifindex | entPhysicalSoftwareRevision | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.11.ifindex | entPhysicalSerialNum | Vendor SN in CLI or sfputil | WW5062F |
| 1.3.6.1.2.1.47.1.1.1.1.12.ifindex | entPhysicalMfgName | Vendor Name in CLI or sfputil | FINISAR CORP |
| 1.3.6.1.2.1.47.1.1.1.1.13.ifindex | entPhysicalModelName | Vendor PN in CLI or sfputil| FCBN410QD3C02 |


Another entPhySensorTable which is defined in [Entity Sensor MIB(RFC3433)](https://tools.ietf.org/html/rfc3433) need to be new added.

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.99.1.1 | entPhySensorTable |   |   |
| 1.3.6.1.2.1.99.1.1.1 | entPhySensorEntry |   |   |
| 1.3.6.1.2.1.99.1.1.1.1.index | entPhySensorType | In CLI: E.g.RX1Power: -0.97dBm | 6 |
| 1.3.6.1.2.1.99.1.1.1.2.index | entPhySensorScale | Same as above | 8 |
| 1.3.6.1.2.1.99.1.1.1.3.index | entPhySensorPrecision | Same as above | 4 |
| 1.3.6.1.2.1.99.1.1.1.4.index | entPhySensorValue | Same as above | 7998 |
| 1.3.6.1.2.1.47.1.1.1.1.2.index | entPhysicalDescr | Show interfaces alias | DOM RX Power Sensor for DOM RX Power Sensor for Ethernet29/1 |


More detailed information about new table and new OIDs are described in [Sensor and Transceiver Info Monitoring Requirement](https://github.com/Azure/SONiC/blob/gh-pages/doc/OIDsforSensorandTransciver.MD#transceiver-requirements-entity-mib).

### 2.2 New connection to STATE_DB ###

To get the transceiver and dom sensor status, SNMP agent need to connect to STATE\_DB and fetch information from TRNASCEIVER_TABLE which will be updated by Xcvrd when this is status change.


## 3. Open Questions ##

1. split the TRANSCEIVER_TABLE to 2 tables, one is for transceiver which store the information needed by entPhysicalTable and another is for entPhySensorTable ?


     
