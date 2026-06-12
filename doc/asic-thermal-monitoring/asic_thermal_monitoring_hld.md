# ASIC thermal monitoring High Level Design
### Rev 0.2
## Table of Contents

## 1. Revision 
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
|v0.1 |01/10/2019  |Padmanabhan Narayanan | Initial version
|v0.2 |10/07/2020  |Padmanabhan Narayanan | Update based on review comments and addess Multi ASIC scenario.
|v0.3 |10/15/2020  |Padmanabhan Narayanan | Update Section 6.3 to indicate no change in thermalctld or Platform API definitions.

## 2. Scope
ASICs typically have multiple internal thermal sensors. This document describes the high level design of a poller for ASIC thermal sensors. It details how the poller may be configured and the export of thermal values from SAI to the state DB.

## 3. Definitions/Abbreviations

Definitions/Abbreviation|Description
------------------------|-----------
ASIC|Application Specific Integrated Circuit. In SONiC context ASIC refers to the NPU/MAC.
PCIe|Peripheral Component Interconnect express
SAI| Switch Abstraction Interface
SDK| Software Development Kit
NOS| Network Operating System

## 4. Overview

Networking switch platforms are populated with a number of thermal sensors which include exteral (i.e. onboard) as well as internal (those located within the component, e.g. CPU, ASIC, DIMM, Transceiver etc..) sensors. Readings from both the external as well as the internal sensors are essential inputs to the thermal/fan control algorithm so as to maintain optimal cooling. While drivers exist to retrive sensor values from onboard and other internal sensors, the ASIC based sensor values are currently retrieved thru the ASIC's SDK. SAI provides the following attributes to retrive the ASIC internal sensors:

|Attribute|Description|
|---|------|
|SAI_SWITCH_ATTR_MAX_NUMBER_OF_TEMP_SENSORS| Maximum number of temperature sensors available in the ASIC |
|SAI_SWITCH_ATTR_TEMP_LIST|List of temperature readings from all sensors|
|SAI_SWITCH_ATTR_AVERAGE_TEMP|The average of temperature readings over all sensors in the switch|
|SAI_SWITCH_ATTR_MAX_TEMP|The current value of the maximum temperature retrieved from the switch sensors|

A configurable ASIC sensors poller is introduced that periodically retrieves the ASIC internal sensor values via SAI APIs and populates the state DB. These values may be used by the thermal control functions (via the ThermalBase() platform APIs), SNMP/CLI or other Telemetry purposes.

## 5. Requirements

### 5.1 Functional Requirements

1. The ASIC sensors poller should be configurable using CONFIG DB (for each ASIC in a multi ASIC platform):
    * There should be a way to enable/disable the poller
    * The polling interval should be configurable (from 5 to 300 secs)
2. The retrieved values should be written to the STATE DB (of each ASIC's DB instance in a multi ASIC platform).
3. The ASIC internal sensor values retrieved should be useable by the Thermal Control infrastructure (https://github.com/sonic-net/SONiC/blob/master/thermal-control-design.md).

### 5.2 CLI requirements

"show platform temperature" should additionally display the ASIC internal sensors as well.

### 5.3 Platform API requirements

It should be possible to query the ASIC internal sensors using the ThermalBase() APIs

## 6. Module Design

### 6.1 DB and Schema changes

A new ASIC_SENSORS ConfigDB table entry would be added to each ASIC's database instance:
```
; Defines schema for ASIC sensors configuration attributes
key             = ASIC_SENSORS|ASIC_SENSORS_POLLER_STATUS   ; Poller admin status 
; field         = value
admin_status    = "enable"/"disable"

key             = ASIC_SENSORS|ASIC_SENSORS_POLLER_INTERVAL   ; Poller interval in seconds
; field         = value
interval        = 1*3DIGIT
```

IN each ASIC's stateDB instance, a new ASIC_TEMPERATORE_INFO table will be added to hold the ASIC internal temperatures:

```
; Defines thermal information for an ASIC
key                     = ASIC_TEMPERATURE_INFO
; field                 = value
average_temperature     = FLOAT                          ; current average temperature value
maximum_temperature     = FLOAT                          ; maximum temperature value
temperature_0           = FLOAT                          ; ASIC internal sensor 0 temperature value
...
temperature_N           = FLOAT                          ; ASIC internal sensor N temperature value
```

### 6.2 SwitchOrch changes

Apart from APP_SWITCH_TABLE_NAME, SwitchOrch will also be a consumer of CFG_ASIC_SENSORS_TABLE_NAME ("ASIC_SENSORS") to process changes to the poller configuration. A new SelectableTimer (sensorsPollerTimer) is introduced with a default of 10 seconds.

#### 6.2.1 Poller Configuration

* If the admin_status is enabled, the sensorsPollerTimer is started. If the poller is disabled, a flag is set so that upon the next timer callback, the timer is stopped.
* If there is any change in the polling interval, the sensorsPollerTimer is updated so that the new interval with take effect with the next timer callback.

#### 6.2.2 sensorsPollerTimer

In the timer callback, the following actions are performed:

* Handle change to timer disable : if the user disables the timer, timer is stopped.
* Handle change to the polling interval : reset the timer if the polling interval has changed
* Get SAI_SWITCH_ATTR_TEMP_LIST and update the ASIC_TEMPERATURE_INFO in the stateDB.
* If the ASIC SAI supports SAI_SWITCH_ATTR_AVERAGE_TEMP, query and update the average temperature field in the ASIC_TEMPERATURE_INFO table in the stateDB.
* If the ASIC SAI supports SAI_SWITCH_ATTR_MAX_TEMP, query and update the maximum_temperature field in the ASIC_TEMPERATURE_INFO table in the stateDB.

### 6.3 Platform changes to support ASIC Thermals

Platform owners typically provide the implementation for Thermals (https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/thermal_base.py). While there is no change in existing Platform API definitions, apart from external/CPU sensors, platform vendors should also include ASIC internal sensors in the _thermal_list[] of the Chassis / Module implementations.

Assuming a Multi ASIC Chassis with 3 ASICs, the thermal names could be:
ASIC0 Internal 0, ... ASIC0 Internal N0, ASIC1 Internal 0, ... ASIC1 Internal N1, ASIC2 Internal 0, ... ASIC2 Internal N2
where ASIC0, ASIC1 and ASIC2 have N0, N1 and N2 internal sensors respectively.

The implementation of the APIs get_high_threshold(), get_low_threshold(), get_high_critical_threshold(), get_name(), get_presence() etc.. are platform (ASIC) specific. The get_temperature() should retrieve the temperature from the ASIC_TEMPERATURE_INFO table of the stateDB from the concerned ASIC's DB instance (which is populated by the SwitchOrch poller as described [above](#62-switchorch-changes)).

The thermalctld's TemperatureUpdater::_refresh_temperature_status() retreives the temperatures of the ASIC internal sensors from the get_temperature() API - just as it would for any external sensor. Only that in the case of ASIC internal sensors, the get_temperature() API is going to retrieve and return the value from from ASIC_TEMPERATURE_INFO table. The thermalctld also updates these values to the TEMPERATURE_INFO table in the globalDB's stateDB. Thus, there is no change in the existing thermalctld infrastructure.

## 7 Virtual Switch

NA

## 8 Restrictions

1. Unlike external sensors, ASIC's internal sensors are retrievable only thru the SDK/SAI. The proposed design eliminates the need for pmon from having to make SAI calls. Considering that thermalctld's default UPDATE_INTERVAL is 60 seconds, the ASIC_SENSORS_POLLER_INTERVAL should ideally be set to an appropriate lower value for better convergence. 
2. A CLI is not currently defined for the poller configuration (for setting/getting the Poller admin state and interval configuration).

## 9 Unit Test cases
Unit test case one-liners are given below:

| #  | Test case synopsis   | Expected results |
|-------|----------------------|------------------|
|1| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_STATUS" "admin_status" to "enable" for a specific ASIC instance | Check that ASIC internal sensors are dumped periodically in the ASIC_TEMPERATURE_INFO of the ASIC's stateDB instance and to the globalDB's TEMPERATURE_INFO table
|2| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_STATUS" "admin_status" to "disable" for a specific ASIC instance | Check that the poller stops
|3| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_INTERVAL" "interval" to "30" for a specific ASIC instance | Check that the poller interval changes from the default 10 seconds
|4| Issue "show platform temperature" | Check that the ASIC interal temperatures are displayed for all the ASICs

## 10 Action items
