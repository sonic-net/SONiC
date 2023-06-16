# Transceiver and Sensor Monitoring HLD #

### Rev 0.1 ###

### Revision
 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo      | Initial version                   |
 | 1.1 |             |      Liu Kebo      | update error event handling       |
 | 1.2 |             |      Junchao Chen  | port config change handling       |
## About This Manual ##

This document is intend to provide general information about the Transceiver and Sensor Monitoring implementation.
The requirement is described in [Sensor and Transceiver Info Monitoring Requirement.](https://github.com/sonic-net/SONiC/blob/master/doc/xrcvd/OIDsforSensorandTransciver.MD)

## 1. Xcvrd design ##

New Xcvrd in platform monitor container is designed to fetch the transceiver and DOM sensor information from the eeprom and then update the state db with these info.

For the transceiver it's self, the type, serial number, hardware version, etc. will not change after plug in. The suitable way for transceiver information update can be triggered by transceiver plug in/out event.

The transceiver dom sensor information(temperature, power,voltage, etc.) can change frequently, these information need to be updated periodically, for now the time period temporarily set to 60s(see open question 1), this time period need to be adjusted according the later on test on all vendors platform.

If there is transceiver plug in or plug out, Xcvrd will respond to the change event, write the new transceiver EEPROM into to state DB, or remove the staled info from the STATE_DB.

Transceiver error event will also be handled when it raised to Xcvrd, currently if transceiver on a error status which blocking EEPROM access, Xcvrd will stop updating and remove the transceiver DOM info from DB until it recovered from the error, in this period transceiver static info will be kept.  

### 1.1 State DB Schema ###

New Transceiver info table and transceiver DOM sensor table will be added to state DB to store the transceiver and DOM sensor information. Transceiver status table will store the SFP status, plug in, plug out or in error status.

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

#### 1.1.3 Transceiver Status Table ####

        ; Defines Transceiver Status info for a port
        key                          = TRANSCEIVER_STATUS|ifname     ; Error information for SFP on port
        ; field                      = value
        status                       = 1*255VCHAR                    ; code of the SFP status (plug in, plug out)
        error                        = 1*255VCHAR                    ; SFP error (N/A or a string consisting of error descriptions joined by "|", like "error1 | error2" )

### 1.2 Accessing EEPROM from platform container ###

Transceiver EEPROM information can be accessed via reading sysfs files(e.g. `/sys/bus/i2c/devices/2-0048/hwmon/hwmon4/qsfp9_eeprom`) or other ways, this is upon vendor's own implementation.

### 1.3 Transceiver change event and vendor platform API ###

#### 1.3.1 Transceiver change event ####

Currently 7 transceiver events are defined as below.

    status='0' SFP removed,
    status='1' SFP inserted,
    status='2' I2C bus stuck,
    status='3' Bad eeprom,
    status='4' Unsupported cable,
    status='5' High Temperature,
    status='6' Bad cable.

However, multiple errors could exist at the same time. For example, a module can be unsupported cable and high temperature. The new transceiver event will be described in a bitmap as below:

    bit 32  : 0=SFP removed, 1=SFP inserted,
    bit 31  : 0=OK, 1=An error that blocks eeprom from being read,
    bit 30  : 0=OK, 1=I2C bus stuck,
    bit 29  : 0=OK, 1=Bad eeprom,
    bit 28  : 0=OK, 1=Unsupported cable,
    bit 27  : 0=OK, 1=High Temperature,
    bit 26  : 0=OK, 1=Bad cable.
    bit 17~25: reserved. Must be 0.
    bit 1~16: vendor specific errors.

    Define bit 32 as the least significant bit and bit 1 as the most significant bit.

The bit 32 represents whether the SFP module is inserted. Any error bit must be set along with this bit.

The bit 31 represents whether the error indicated by platform API will block the SFP module from being read or not. This bit must be set along with other error bits.

Vendor can extend this bitmap with more errors. However, some errors can be vendor specific, which means they won't occur on other vendors' platforms. The bitmap can grow rapidly and eventually run out of bits if all vendors insert vendor specific error codes to the bitmap.

This can be resolved by dividing the bitmap into two parts: one for generic errors and the other for vendor specific errors. The bits 17 ~ 30 represent the generic errors and bits 1 ~ 16 represent the vendor specific errors.

Xcvrd should parse the bitmap and set transceiver status table in database accordingly. The error descriptions is fetched in the following ways:

- For generic errors, they will be translated from error bits by looking up a pre-defined dictionary as xcvrd has the necessary knowledge.
- For vendor specific errors:
  - If the platform API `get_change_event` returns a dict called `sfp_error`, the content of the dict will be taken as the error descriptions.
  - Otherwise, the newly introduced platform API `get_error_description` will be called to fetch the descriptions.
  - For both case, the error descriptions should reflect the vendor specific errors only. If there are multiple errors, the error descriptions should be joined by "|".

For example, if the transceiver event bit map is 0x0F, the status field value should be "1" and the error field value should be "I2C bus stuck|Bad eeprom|Blocking error", indicating the SFP module is inserted with errors `I2C bus stuck` and `Bad eeprom` detected and at least one of the errors is blocking.

#### 1.3.2 API to get Transceiver change event from platform ####

Xcvrd need to be triggered by transceiver change event to refresh the transceiver info table.

How to get this event varies between different platforms. There is no common implementation available.

##### 1.3.2.2 Transceiver change event API in new platform API #####

In new platform API, similar change event API has also been defined and will be extended by adding `sfp_error` key. In case there is an error occurred, the platform API should reflect the error in the `sfp` key and can provide the error descriptions in `sfp_error` key.

The API is defined as below:

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
                  Ex1. {'fan':{'0':'0', '2':'1'}, 'sfp':{'11':'0'}}
                       indicates that fan 0 has been removed, fan 2
                       has been inserted and sfp 11 has been removed.
                  Ex2. {'sfp':{'11':'65537'}, 'sfp_error':{'11':<vendor specific error>}}
                      indicates SFP 11 has been inserted with a vendor specific error represented by bit 16.

##### 1.3.2.3 Xcvrd wrapper for calling transceiver change event API #####

Xcvrd uses a wrapper to call one of the above two APIs depends on the implementation status on a specific platform  to wait for the sfp plug in/out event, following example code showing how these APIs will be called:

    def _wrapper_get_transceiver_change_event(timeout):
        if platform_chassis is not None:
            try:
                status, events =  platform_chassis.get_change_event(timeout)
                sfp_events = events.get('sfp')
                sfp_errors = events.get('sfp_error')
                return status, sfp_events, sfp_errors
            except NotImplementedError:
                pass
        status, sfp_events = platform_sfputil.get_transceiver_change_event(timeout)
        return status, sfp_events, None

It's possible that when received the plug in/out event, the transceiver eeprom is not ready for reading, so need to give another try if first reading failed.

#### 1.3.2 API to get error description of an SFP module ####

##### 1.3.2.1 Platform API definition #####

A new platform API in class SFP is required for fetching the error status of the SFP module.

    def get_error_status(self)
        """
        Get error status of the SFP module
        Returns:
            string: represent the error
        """

##### 1.3.2.2 xcvrd wrapper #####

    def _wrapper_get_sfp_error_description(physical_port):
        if platform_chassis:
            try:
                return platform_chassis.get_sfp(physical_port).get_error_description()
            except NotImplementedError:
                pass
        return None

#### 1.3.3 Transceiver plug in/out and error event implementation on Mellanox platform ####

On Mellanox platform the SFP events is exposed by mlnx SDK, the API will open a channel and listening to the SDK for the events.

During the API init phase(waiting for the channel with SDK created), if Xcvrd called this API and it will return SYSTEM_NOT_READY event.

If SDK failed due to some reason and channel closed, API will raised error(SYSTEM_FAIL) to Xcvrd.

### 1.4 Xcvrd daemon flow ###

Xcvrd will spawn a new process(sfp_state_update_task) to wait for the SFP plug in/out event, when event received, it will update the DB entries accordingly.

A thread will be started to periodically refresh the DOM sensor information.

Detailed flow as showed in below chart:

![](https://github.com/sonic-net/SONiC/blob/d1159ca728112f10319fa47de4df89c445a27efc/images/transceiver_monitoring_hld/xcvrd_flow.svg)

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

When error events (defined in section 1.3.1) are received from a transceiver, the related interface's TRANSCEIVER_STATUS table will be updated with the error descriptions, and the DOM information will be removed from the database.

The DOM update thread will check the transceiver status table before updating the DOM information. The DOM info updating will be skipped for a port if there is a blocking error for the port in the table. The xcvrd main task will also perform the same check-and-skip logic before recovering the missing DOM information for a port.

Currently no explicit "error clear event" is defined, a plug in event will be considered as port recovered from error(on Mellanox platform it does send out a plug in event when recovered from error).

An explicit "error clear event" can be added if some vendor's platform supports this kind of event.

On transceiver plug in or plug out events, the port error status will be cleared.

#### 1.4.3 Port Mapping Information handling ####

xcvrd depends on port mapping information to update transceiver information to DB. Port mapping information contains following data:

- Logical port name list. E.g. ["Ethernet0", "Ethernet4" ...]
- Logical port name to physical port index mapping. E.g. {"Ethernet0": 1}
- Physical port index to logical port name mapping. E.g. {1: "Ethernet0"}
- Logical port name to ASIC ID mapping. This is useful for multi ASIC platforms.

Currently, xcvrd assumes that port mapping information is never changed, so it always read static port mapping information from platform.json/port_config.ini and save it to a global data structure. However, things changed since dynamic port breakout feature introduced. Port can be added/created on the fly, xcvrd cannot update transceiver information, DOM information and transceiver status information without knowing the ports change. This causes data in state db not aligned with config db. To address this issue, xcvrd should subscribe CONFIG_DB PORT table change and update port mapping information accordingly.

- Main process need not subscribe port configuration change.
- State machine process and DOM sensor update thread subscribe port configuration change and update local port mapping accordingly.

Port change event contains following data:

- ASIC index which indicates the DB namespace.
- Logical port name. Get from the key of PORT table. E.g, for key "PORT|Ethernet0", the logical port name is "Ethernet0".
- Physic port index. Get from "index" field of PORT table.
- Event type. Can be "Add" or "Remove".

As port mapping information might be updated during runtime, the global port mapping information cannot be shared properly among main process, state machine process and DOM sensor update thread. A possible solution is to use share memory between different processes, but it will introduce process level lock to many places which is hard to maintain. So, a simple solution is to store local port mapping information in main process, state machine process and DOM sensor update thread and update them according to port configuration change. In this case, no explicit lock is needed and we can keep the logic as simple as it is. Of course it takes more memory, but port mapping information would be very small which should not cause any memory issue.

##### 1.4.3.1 Subscribe CONFIG_DB PORT table change #####

SONiC has implemented a way to "select" data changes from redis. xcvrd should reuse this "select" infrastructure to listen CONFIG_DB PORT table change. The workflow is like:

1. For each ASIC namespace, create a selectable object which point to CONFIG_DB PORT table
2. Add each selectable object to the select queue
3. Select DB event in a while loop
4. If there is any selectable object ready for read, check:

    - Entry added, trigger a port change event with event type "Add"
    - Entry removed, trigger a port change event with event type "Remove"
    - Entry updated, if the port logical name to physical index mapping has been changed, trigger a port "Remove" and port "Add" event.

5. Update local port mapping

##### 1.4.3.2 Handle port change event in state machine process #####

Once a port configuration change detected, it should update local port mapping information first, and if it is a remove event, state machine task should remove transceiver information from table TRANSCEIVER_INFO, TRANSCEIVER_STATUS and TRANSCEIVER_DOM_SENSOR; if it is an add event, there could be 4 cases:

- Transceiver information is already in DB which means that a logical port with the same physical index already exists. Copy the data from DB and create a new entry to table TRANSCEIVER_DOM_INFO, TRANSCEIVER_STATUS_INFO and TRANSCEIVER_INFO whose key is the newly added logical port name.
- Transceiver information is not in DB and transceiver is present with no SFP error. Query transceiver information and DOM sensor information via platform API and update the data to table TRANSCEIVER_DOM_INFO, TRANSCEIVER_STATUS_INFO and TRANSCEIVER_INFO.
- Transceiver information is not in DB and transceiver is present with SFP error. If the SFP error does not block EEPROM reading, just query transceiver information and DOM sensor information via platform API and update the data to DB; otherwise, just update TRANSCEIVER_STATUS table with the error.
- Transceiver information is not in DB and transceiver is not present. Update TRANSCEIVER_STATUS only.

##### 1.4.3.2 Handle port change event in DOM sensor update thread #####

Once a port configuration change detected, it should update local port mapping information first and if it is a remove event, it should remove transceiver information from table TRANSCEIVER_DOM_SENSOR; if it is and add event, nothing else need to be done because new port in already in local port mapping and the DOM sensor information will be updated properly.

##### 1.4.3.3 Recover missing SFP information in DB #####

When a SFP insert event arrives to state machine process, it reads the SFP EEPROM. If the first read fails, it retries after 5 seconds. If it fails again, this SFP will be put into a retry queue. State machine process retries EEPROM reading for each item in the retry queue every iteration. It makes sure that xcvrd will not miss transceiver information in DB.

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

More detailed information about new table and new OIDs are described in [Sensor and Transceiver Info Monitoring Requirement](https://github.com/sonic-net/SONiC/blob/master/doc/xrcvd/OIDsforSensorandTransciver.MD#transceiver-requirements-entity-mib).

## 3. CLI change ##

### 3.1 Add a command to fetch the error status ###

#### 3.1.1 sfputil extension ####

The utility `sfputil` needs to be updated to extend to support fetching error status of SFP modules.
The CLI is like this:

    sfputil show error-status --fetch-from-hardware --port <port>

The error status can be fetched for

- A specific SFP module designated by --port argument
- or all SPF modules if --port isn't provided

By default, it will fetch the error status from `TRANSCEIVER_STATUS` in `STATE_DB`. It also supports fetching error status from low level component directly. In this case, it will call platform API `get_error_description` from the `pmon` docker.

The error status of each SPF module should be:

- `unplugged` if the module isn't plugged-in
- `OK` if the module is plugged in without any error
- Errors stored in `STATE_DB` or fetched from platform API.

The output of the command is like this:

    admin@sonic:~# sfputil show error-status --port Ethernet8
    Port       Error Status
    ---------  ------------------------------------
    Ethernet8  OK

    admin@sonic:~# sfputil show error-status
    Port         Error Status
    -----------  ----------------------------------------------
    Ethernet0    OK
    Ethernet4    OK
    Ethernet8    OK
    Ethernet12   OK
    Ethernet16   OK
    Ethernet20   OK
    Ethernet24   OK
    Ethernet28   OK
    Ethernet32   OK
    Ethernet36   OK
    Ethernet40   OK
    Ethernet44   Power budget exceeded
    Ethernet48   OK
    Ethernet52   OK
    Ethernet56   OK
    Ethernet60   OK
    Ethernet64   OK
    Ethernet68   OK
    Ethernet72   OK
    Ethernet76   OK
    Ethernet80   OK
    Ethernet84   OK
    Ethernet88   OK
    Ethernet92   OK
    Ethernet96   OK
    Ethernet100  OK
    Ethernet104  OK
    Ethernet108  OK
    Ethernet112  OK
    Ethernet116  OK
    Ethernet120  OK
    Ethernet124  OK
    Ethernet128  OK
    Ethernet132  OK
    Ethernet136  OK
    Ethernet140  OK
    Ethernet144  OK
    Ethernet148  OK
    Ethernet152  OK
    Ethernet156  OK
    Ethernet160  OK
    Ethernet164  OK
    Ethernet168  Unplugged
    Ethernet172  OK
    Ethernet176  OK
    Ethernet180  OK
    Ethernet184  OK
    Ethernet188  OK
    Ethernet192  OK
    Ethernet196  OK
    Ethernet200  OK
    Ethernet204  OK
    Ethernet208  OK
    Ethernet212  OK
    Ethernet216  OK
    Ethernet220  OK

#### 3.1.2 show interface transceiver wrapper ####

A wrapper command `show interface transceiver error-status` is also provided.

    show interface transceiver error-status --fetch-from-hardware <port>

The output is the same as that of `sfputil`.
