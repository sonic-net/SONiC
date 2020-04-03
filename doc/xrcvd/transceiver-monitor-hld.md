# Transceiver and Sensor Monitoring HLD #

### Rev 0.1 ###

### Revision
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo      | Initial version                   |
 | 1.1 |             |      Liu Kebo      | update error event handling       |
## About This Manual ##

This document is intend to provide general information about the Transceiver and Sensor Monitoring implementation.
The requirement is described in [Sensor and Transceiver Info Monitoring Requirement.](https://github.com/Azure/SONiC/blob/gh-pages/doc/OIDsforSensorandTransciver.MD)


## 1. Xcvrd design ##

New Xcvrd in platform monitor container is designed to fetch the transceiver and DOM sensor information from the eeprom and then update the state db with these info. 

For the transceiver it's self, the type, serial number, hardware version, etc. will not change after plug in. The suitable way for transceiver information update can be triggered by transceiver plug in/out event.

The transceiver dom sensor information(temperature, power,voltage, etc.) can change frequently, these information need to be updated periodically, for now the time period temporarily set to 60s(see open question 1), this time period need to be adjusted according the later on test on all vendors platform.

If there is transceiver plug in or plug out, Xcvrd will response to the change event, write the new transceiver EEPROM into to state DB, or remove the staled info from the STATE_DB.

Transceiver error event will also be handled when it raised to Xcvrd, currently if transceiver on a error status which blocking EEPROM access, Xcvrd will stop updating and remove the transceiver DOM info from DB until it recovered from the error, in this period transceiver static info will be kept.  
 
### 1.1 State DB Schema ###

New Transceiver info table and transceiver DOM sensor table will be added to state DB to store the transceiver and DOM sensor information. 

#### 1.1.1 Transceiver info Table ####

	; Defines Transceiver information for a port
	key                          = TRANSCEIVER_INFO|ifname      ; information for SFP on port
	; field                      = value
	type                         = 1*255VCHAR                   ; type of sfp
	hardwarerev                  = 1*255VCHAR                   ; hardware version of sfp
	serialnum                    = 1*255VCHAR                   ; serial number of the sfp
	manufacturename              = 1*255VCHAR                   ; sfp venndor name
	modelname                    = 1*255VCHAR                   ; sfp model name
    vendor_oui                   = 1*255VCHAR                   ; vendor organizationally unique identifier
    vendor_date                  = 1*255VCHAR                   ; vendor's date code
    Connector                    = 1*255VCHAR                   ; connector type
    encoding                     = 1*255VCHAR                   ; serial encoding mechanism
    ext_identifier               = 1*255VCHAR                   ; additional infomation about the sfp
    ext_rateselect_compliance    = 1*255VCHAR                   ; additional rate select compliance information
    cable_type                   = 1*255VCHAR                   ; cable type
    cable_length                 = 1*255VCHAR                   ; cable length that supported
    specification_compliance     = 1*255VCHAR                   ; electronic or optical interfaces that supported
    nominal_bit_rate             = 1*255VCHAR                   ; nominal bit rate per channel

#### 1.1.2 Transceiver DOM sensor Table ####

	; Defines Transceiver DOM sensor information for a port
	key                     = TRANSCEIVER_DOM_SENSOR|ifname      ; information SFP DOM sensors on port
	temperature             = FLOAT                              ; temperature value in Celsius
	voltage                 = FLOAT                              ; voltage value
	rx1power                = FLOAT                              ; rx1 power in dbm
	rx2power                = FLOAT                              ; rx2 power in dbm
	rx3power                = FLOAT                              ; rx3 power in dbm
	rx4power                = FLOAT                              ; rx4 power in dbm
	tx1bias                 = FLOAT                              ; tx1 bias in mA
	tx2bias                 = FLOAT                              ; tx2 bias in mA
	tx3bias                 = FLOAT                              ; tx3 bias in mA
	tx4bias                 = FLOAT                              ; tx4 bias in mA
    temphighalarm           = FLOAT                              ; temperature high alarm threshold 
    temphighwarning         = FLOAT                              ; temperature high warning threshold
    templowalarm            = FLOAT                              ; temperature low alarm threshold
    templowwarning          = FLOAT                              ; temperature low warning threshold
    vcchighalarm            = FLOAT                              ; vcc high alarm threshold
    vcchighwarning          = FLOAT                              ; vcc high warning threshold
    vcclowalarm             = FLOAT                              ; vcc low alarm threshold
    vcclowwarning           = FLOAT                              ; vcc low warning threshold
    txpowerhighalarm        = FLOAT                              ; tx power high alarm threshold
    txpowerlowalarm         = FLOAT                              ; tx power low alarm threshold
    txpowerhighwarning      = FLOAT                              ; tx power high warning threshold
    txpowerlowwarning       = FLOAT                              ; tx power low alarm threshold
    rxpowerhighalarm        = FLOAT                              ; rx power high alarm threshold
    rxpowerlowalarm         = FLOAT                              ; rx power low alarm threshold
    rxpowerhighwarning      = FLOAT                              ; rx power high warning threshold
    rxpowerlowwarning       = FLOAT                              ; rx power low warning threshold
    txbiashighalarm         = FLOAT                              ; tx bias high alarm threshold
    txbiaslowalarm          = FLOAT                              ; tx bias low alarm threshold
    txbiashighwarning       = FLOAT                              ; tx bias high warning threshold
    txbiaslowwarning        = FLOAT                              ; tx bias low warning threshold

#### 1.1.# Transceiver Error Table ####

	; Defines Transceiver Error info for a port
	key                          = TRANSCEIVER_ERROR|ifname     ; Error information for SFP on port
	; field                      = value
	status                       = 1*255VCHAR                   ; code of the error status


### 1.2 Accessing EEPROM from platform container ###

Transceiver information EEPROM can be accessed via read sysfs files(e.g. `/sys/bus/i2c/devices/2-0048/hwmon/hwmon4/qsfp9_eeprom`) or other ways, this is upon vendor's own implementation. 

Transceiver EEPROM accessing can be achieved by legacy sfp plugin or new platform API, Xcvrd support both of these two methods. If platform API not yet implemented on some vendor's device, it will automatically fall back on sfp plugin.


### 1.3 Transceiver change event and vendor platform API###

#### 1.3.1 Transceiver change event ####

Currently 7 transceiver events are defined as below. The first two are for plug in and plug out, others to reflect various error status, vendors can add new error event if they feel need. 

    status='0' SFP removed,
    status='1' SFP inserted,
    status='2' I2C bus stuck,
    status='3' Bad eeprom,
    status='4' Unsupported cable,
    status='5' High Temperature,
    status='6' Bad cable.

#### 1.3.2 API to get Transceiver change event from platform ####

Xcvrd need to be triggered by transceiver change event to refresh the transceiver info table.

How to get this event is various on different platform, there is no common implementation available. 

##### 1.3.2.1 Transceiver change event API in plugin #####
In legacy sfp plugin a new API was defined to wait for this event in class `SfpUtilBase`: 

    @abc.abstractmethod
    def get_transceiver_change_event(self, timeout=0):
        """
	:param timeout: function will return success and a empty dict if no event in this period, default value is 0.
        :returns: Boolean, True if call successful, False if not; 
        dict for pysical port number and the SFP status, status '1' represent plug in, '0' represent plug out(eg. {'0': '1', '31':'0'})
        """
        return 

Each vendor need to implement this function in `SfpUtil` plugin.

##### 1.3.2.2 Transceiver change event API in new platform API #####
In new platform API, similar change event API also defined, this API is not only for SFP, but also for other devices:

    def get_change_event(self, timeout=0):
        """
        Returns a nested dictionary containing all devices which have
        experienced a change at chassis level

        Args:
            timeout: Timeout in milliseconds (optional). If timeout == 0,
                this method will block until a change is detected.

        Returns:
            (bool, dict):
                - True if call successful, False if not;
                - A nested dictionary where key is a device type,
                  value is a dictionary with key:value pairs in the format of
                  {'device_id':'device_event'}, 
                  where device_id is the device ID for this device and
                        device_event,
                             status='1' represents device inserted,
                             status='0' represents device removed.
                  Ex. {'fan':{'0':'0', '2':'1'}, 'sfp':{'11':'0'}}
                      indicates that fan 0 has been removed, fan 2
                      has been inserted and sfp 11 has been removed.

##### 1.3.2.3 Xcvrd wrapper for calling transceiver change event API #####
Xcvrd using a wrapper to call one of the above two APIs depends on the implementation status on a specific platform  to wait for the sfp plug in/out event, following example code showing how these APIs will be called:

    def _wrapper_get_transceiver_change_event(timeout):
	    if platform_chassis is not None:
	        try:
	            status, events =  platform_chassis.get_change_event(timeout)
	            sfp_events = events['sfp']
	            return status, sfp_events
	        except NotImplementedError:
	            pass
	    return platform_sfputil.get_transceiver_change_event(timeout)
                 
It's possible that when received the plug in/out event, the transceiver eeprom is not ready for reading, so need to give another try if first reading failed. 

#### 1.3.2 Transceiver plug in/out and error event implementation on Mellanox platform ####

On Mellanox platform the SFP events is exposed by mlnx SDK, the API will open a channel and listening to the SDK for the events. 

During the API init phase(waiting for the channel with SDK created), if Xcvrd called this API and it will return SYSTEM_NOT_READY event. 

If SDK failed due to some reason and channel closed, API will raised error(SYSTEM_FAIL) to Xcvrd.

### 1.4 Xcvrd daemon flow ###

Xcvrd will spawn a new process(sfp_state_update_task) to wait for the SFP plug in/out event, when event received, it will update the DB entries accordingly.

A thread will be started to periodically refresh the DOM sensor information.

In the main loop of the Xcvrd task, it periodically check the integrity the DB, if some SFP info missing, will be added back. 

Detailed flow as showed in below chart: 

![](https://github.com/keboliu/SONiC/blob/master/images/xcvrd-flow.svg)

#### 1.4.1 State machine of sfp\_state\_update\_task process ####

In the process of handling SFP change event, a state machine is defined to handle events(including SFP change events) reported from platform level.

        states definition
          - Initial state: INIT, before receive system ready or a normal event
          - Final state: EXIT
          - Other state: NORMAL, after received system-ready or a normal event
        
        events definition
          - SYSTEM_NOT_READY
          - SYSTEM_BECOME_READY
          - NORMAL_EVENT
            - sfp insertion/removal event
            - sfp error event
            - timeout returned by sfputil.get_change_event with status = true
          - SYSTEM_FAIL

        state transition
          State           event               next state
          INIT            SYSTEM NOT READY    INIT / EXIT
          INIT            SYSTEM FAIL         INIT / EXIT
          INIT            SYSTEM BECOME READY NORMAL
          NORMAL          SYSTEM BECOME READY NORMAL
          NORMAL          SYSTEM FAIL         INIT
          INIT/NORMAL     NORMAL EVENT        NORMAL
          NORMAL          SYSTEM NOT READY    INIT
          EXIT            -


![](https://github.com/keboliu/SONiC/blob/master/images/xcvrd_state_mahine.svg)

#### 1.4.2 Transceiver error events handling procedure ####

When error events(defined in section 1.3.1) received from some transceiver, the related interface will be added to the TRANSCEIVER_ERROR table, and DOM information will be removed from the DB. 

Before the DOM update thread update the DOM info, it will check the error table first, DOM info updating will be skipped if some port is in the error table. In the Xcvrd main task recovering missing interface info, same check will also be applied.

Currently no explicit "error clear event" is defined, a plug in event will be considered as port recovered from error(on Mellanox platform it does send out a plug in event when recovered from error). 

An explicit "error clear event" can be added if some vendor's platform do have this kind of event.

On transceiver plug in or plug out events, the port will be removed from the error table.     

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



      
