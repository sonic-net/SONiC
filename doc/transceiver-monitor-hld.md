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

New Xcvrd in platform monitor container is designed to fetch the transceiver and DOM sensor information from the eeprom and then update the state db with these info. 

For the transceiver it's self, the type, serial number, hardware version, etc. will not change after plug in. The suitable way for transceiver information update can be triggered by transceiver plug in/out event.

The transceiver dom sensor information(temperature, power,voltage, etc.) can change frequently, these information need to be updated periodically, for now the time period temporarily set to 60s(see open question 1), this time period need to be adjusted according the later on test on all vendors platform.

If there is transceiver and sensor status change, Xcvrd will write the new status to state DB, to store these information some new tables will be added to STATE_DB.
 
### 1.1 State DB Schema ###

New Transceiver info table and transceiver DOM sensor table will be added to state DB to store the transceiver and DOM sensor information. 

#### 1.1.1 Transceiver info Table ####

	; Defines Transceiver information for a port
	key                     = TRANSCEIVER_INFO|ifname         ; configuration for watchdog on port
	; field                 = value
	type                    = 1*255VCHAR                       ; type of sfp
	hardwarerev             = 1*255VCHAR                       ; hardware version of sfp
	serialnum               = 1*255VCHAR                       ; serial number of the sfp
	manufacturename         = 1*255VCHAR                       ; sfp venndor name
	modelname               = 1*255VCHAR                       ; sfp model name

#### 1.1.2 Transceiver DOM sensor Table ####

	; Defines Transceiver DOM sensor information for a port
	key                     = TRANSCEIVER_DOM_SENSOR|ifname        ; configuration for watchdog on port
	temperature             = FLOAT                                      ; temperature value in Celsius
	voltage                 = FLOAT                                      ; voltage value
	rx1power                = FLOAT                                      ; rx1 power in dbm
	rx2power                = FLOAT                                      ; rx2 power in dbm
	rx3power                = FLOAT                                      ; rx3 power in dbm
	rx4power                = FLOAT                                      ; rx4 power in dbm
	tx1bias                 = FLOAT                                      ; tx1 bias in mA
	tx2bias                 = FLOAT                                      ; tx2 bias in mA
	tx3bias                 = FLOAT                                      ; tx3 bias in mA
	tx4bias                 = FLOAT                                      ; tx4 bias in mA


### 1.2 Access eeprom from platform container ###

Transceiver information eeprom can be accessed via read files(e.g. `/sys/bus/i2c/devices/2-0048/hwmon/hwmon4/qsfp9_eeprom`), different vendors may have these files under different folders, these folder need to be mounted to platform container so Xcvrd can access them. 


For the convenience of implementation and reduce the time consuming, need to do enhancement to the `SfpUtilBase` class:

1. `SfpUtilBase` internally should add the ability to read the eeprom and only pick up the interested bytes by given offset and number of bytes.

2. `SfpUtilBase` will provide APIs `get_eeprom_sfp_info_dict(self, port_num)` and `get_eeprom_dom_info_dict(self, port_num)` to return `eeprom_if_dict` and `eeprom_dom_dict` separately, the interested values of these two dict are defined  in section 1.1.1 and 1.1.2.  In these two APIs can pick up these values from eeprom by provide the corresponding offset and number of bytes. 


### 1.3 Transceiver plug in/out event ###

Xcvrd need to be triggered by transceiver plug in/out event to refresh the transceiver info table.

How to get this event is various on different platform, there is no common implementation available. 

Here we define a common platform API to wait for this event in class `SfpUtilBase`: 

    @abc.abstractmethod
    def get_transceiver_change_event(self, timeout=0):
        """
	:param timeout: function will return success and a empty dict if no event in this period, default value is 0.
        :returns: Boolean, True if call successful, False if not; 
        dict for pysical port number and the SFP status, status '1' represent plug in, '0' represent plug out(eg. {'0': '1', '31':'0'})
        """
        return 

Each vendor need to implement this function in `SfpUtil` plugin.

Xcvrd will call this API to wait for the sfp plug in/out event, following example code showing how this API will be called:

    while True:
        status, port_dict = platform_sfputil.get_transceiver_change_event()
        if(status):
            for key, value in port_dict.iteritems():
                print("SFP on port: %s" was %s" % (key, value))
                 
It's possible that when received the plug in/out event, the transceiver eeprom is not ready for reading, so need to give another try if first reading failed. 

#### 1.3.1 Transceiver plug in/out event implementation on mlnx platform ####

On mlnx platform the event is exposed by mlnx SDK which reside in syncd container. A dedicated daemon mlnx-sfpd is added to mlnx syncd container which will register to mlnx SDK and listen for the SFP plug/in out event.

When mlnx-sfpd get the event, it will populate it to STATE_DB. get_transceiver_change_event on mlnx platform will subscribe to STATE_DB and waiting for it.

Since xcvrd does not talk to mlnx-sfpd directly, need to have some mechanism to notify xcvrd when mlnx-sfpd fail, so xcvrd can handle accordingly. The intermediate will still be STATE_DB.

mnlx-sfpd will populate error when:

1. not able to get correct sfp change event from SDK
2. mlnx-sfpd itself failed for some reason.

mlnx-sfpd will have a liveness indication mechanisim to let xcvrd know that it is working or not. mlnx-sfpd use STATE_DB to convey it's liveness status to the outside.  
 
In the  mlnx implementation of 'get_transceiver_change_event',  it will check the STATE_DB to get the liveness status of mlnx-sfpd every time when being called, if mlnx-sfpd is not working anymore, it will return an error. Xcvrd will know that mlnx-sfpd failed by getting the error, as a result, it will stop polling the dom info and clean all the transceiver info in the DB.

### 1.4 Xcvrd daemon flow ###

Xcvrd will spawn a thread to wait for the SFP plug in/out event, when event received, it will update the DB entries accordingly.

A timer will be started to periodically refresh the DOM sensor information . 

Detailed flow as showed in below chart: 

![](https://github.com/Azure/SONiC/blob/gh-pages/images/transceiver_monitoring_hld/xcvrd_flow.svg)

## 2. SNMP Agent Change ##

### 2.1 MIB tables extension ###

MIB table entPhysicalTable from [Entity MIB(RFC2737)](https://tools.ietf.org/html/rfc2737) need to be extended to support new OIDs.

| OID | SNMP counter | Where to get the info in Sonic. | Example: |
| --- | --- | --- | --- |
| 1.3.6.1.2.1.47.1.1.1 | entPhysicalTable |   |   |
| 1.3.6.1.2.1.47.1.1.1.1 | entPhysicalEntry |   |   |
| 1.3.6.1.2.1.47.1.1.1.1.2. index | entPhysicalDescr | Show interfaces alias | Xcvr for Ethernet29 |
| 1.3.6.1.2.1.47.1.1.1.1.7. index | entPhysicalName | skipped | |
| 1.3.6.1.2.1.47.1.1.1.1.8. index | entPhysicalHardwareVersion | Vendor Rev in CLI or sfputil | A1 |
| 1.3.6.1.2.1.47.1.1.1.1.9. index | entPhysicalFirmwareVersion | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.10.index | entPhysicalSoftwareRevision | Skipped |   |
| 1.3.6.1.2.1.47.1.1.1.1.11.index | entPhysicalSerialNum | Vendor SN in CLI or sfputil | WW5062F |
| 1.3.6.1.2.1.47.1.1.1.1.12.index | entPhysicalMfgName | Vendor Name in CLI or sfputil | FINISAR CORP |
| 1.3.6.1.2.1.47.1.1.1.1.13.index | entPhysicalModelName | Vendor PN in CLI or sfputil| FCBN410QD3C02 |


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

1. DOM sensor polling period may need to be adjusted after collecting enough data on various platform.

      
