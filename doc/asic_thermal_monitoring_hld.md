# ASIC thermal monitoring High Level Design
### Rev 0.1
## Table of Contents

## 1. Revision 
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
|v0.1 |01/10/2019  |Padmanabhan Narayanan | Initial version

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

### 5.1 **Functional Requirements**

1. The ASIC sensors poller should be configurable (using CONFIG DB):
    * There should be a way to enable/disable the poller
    * The polling interval should be configurable (from 5 to 300 secs)
2. The retrieved values should be written to the STATE DB.

### 5.2 **CLI requirements**

"show platform temperature" should additionally display the ASIC internal sensors as well.

### 5.3 **Platform API requirements**

It should be possible to query the ASIC internal sensors using the ThermalBase() APIs

## 6. Module Design

### 6.1.1 **DB and Schema changes**

A new ASIC_SENSORS ConfigDB table entry would be added. 
```
; Defines schema for ASIC sensors configuration attributes
key             = ASIC_SENSORS|ASIC_SENSORS_POLLER_STATUS   ; Poller admin status 
; field         = value
admin_status    = "enable"/"disable"

key             = ASIC_SENSORS|ASIC_SENSORS_POLLER_INTERVAL   ; Poller interval in seconds
; field         = value
interval        = 1*3DIGIT
```

The TEMPERATORE_INFO stateDB table will be expanded to hold the ASIC internal temperatures. The object_name would be:
asic_<0..(n-1)>_ internal_<0..(N-1)> where "n" is the number of ASIC and "N" is the number of internal sensors on the ASIC.
...

A new ASIC_SENSORS stateDB table is added which captures the following additional details:

```
; Defines thermal information for an ASIC
key                     = ASIC_SENSORS|object_name   ; ASIC thermal object(asic_0, asic_1...)
; field                 = value
num_temperature_sensors = 2*DIGIT                        ; Maximum number of internal thermal sensors on this ASIC
average_temperature     = FLOAT                          ; current average temperature value
maximum_temperature     = FLOAT                          ; maximum temperature value
```

### 6.1.1 SwitchOrch changes

Apart from APP_SWITCH_TABLE_NAME, SwitchOrch will also be a consumer of CFG_ASIC_SENSORS_TABLE_NAME ("ASIC_SENSORS") to process changes to the poller configuration. A new SelectableTimer (sensorsPollerTimer) is introduced with a default of 10 seconds.

#### 6.1.1.1 Poller Configuration

* If the admin_status is enabled, the sensorsPollerTimer is started. If the poller is disabled, a flag is set so that upon the next timer callback, the timer is stopped.
* If there is any change in the polling interval, the sensorsPollerTimer is updated so that the new interval with take effect with the next timer callback.

#### 6.1.1.1 sensorsPollerTimer

In the timer callback, the following actions are performed:

* Handle change to timer disable : if the user disables the timer, timer is stopped.
* Handle change to the polling interval : reset the timer if the polling interval has changed
* Query SAI_SWITCH_ATTR_MAX_NUMBER_OF_TEMP_SENSORS and update the "num_temperature_sensors" field in the ASIC_SENSORS|asic_\<n\> table in the stateDB.
* Get SAI_SWITCH_ATTR_TEMP_LIST and update the TEMPERATURE_INFO in the stateDB. The sensors values are exported as asic_<0..(n-1)>_ internal_<0..(N-1)>
* If the ASIC SAI supports SAI_SWITCH_ATTR_AVERAGE_TEMP, query and update the average temperature field in the ASIC_SENSORS|asic_\<n\> table in the stateDB.
* If the ASIC SAI supports SAI_SWITCH_ATTR_MAX_TEMP, query and update the maximum_temperature field in the ASIC_SENSORS|asic_\<n\> table in the stateDB.

#### 6.1.2 Platform API 2.0 support

A new AsicBase class is defined that denotes a specific ASIC. The relevant snapshot of the AsicBase() definition is as follows:

```
class AsicBase(device_base.DeviceBase):
    """
    Abstract base class for ASIC
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "asic"

    # List of ThermalBase-derived objects representing all thermals
    # available on the asic
    _thermal_list = None

    def __init__(self):
            self._thermal_list = []

    ##############################################
    # THERMAL methods
    ##############################################

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this module

        Returns:
            An integer, the number of thermals available on this module
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this module

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this module
        """
        return self._thermal_list

    def get_thermal(self, index):
        """
        Retrieves thermal unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the thermal to
            retrieve

        Returns:
            An object dervied from ThermalBase representing the specified thermal
        """
        thermal = None

        try:
            thermal = self._thermal_list[index]
        except IndexError:
            sys.stderr.write("THERMAL index {} out of range (0-{})\n".format(
                             index, len(self._thermal_list)-1))

        return thermal

    def get_average_temperature(self):
        """
        Retrieves the average temperature reading from thermal

        Returns:
            A float number of average temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125
        """
        raise NotImplementedError

    def get_maximum_temperature(self):
        """
        Retrieves the maximum temperature reading from thermal

        Returns:
            A float number of average temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125
        """
        raise NotImplementedError

```

The chassis_base and module_base of the sonic_platform package now contain the following additional lists and methods:

```
    # List of AsicBase-derived objects representing all ASICs
    # available on the chassis/module
    _asic_list = []

    ##############################################
    # Asic methods
    ##############################################

    def get_num_asics(self):
        """
        Retrieves the number of ASICs available on this chassis/module

        Returns:
            An integer, the number of ASIC modules available on this chassis/module
        """
        return len(self._asic_list)

    def get_all_asics(self):
        """
        Retrieves all ASIC modules available on this chassis/module

        Returns:
            A list of objects derived from AsicBase representing all ASIC
            modules available on this chassis/module
        """
        return self._asic_list

    def get_asic(self, index):
        """
        Retrieves ASIC module represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the ASIC module to
            retrieve

        Returns:
            An object dervied from AsicBase representing the specified ASIC
            module
        """

```

The ThermalBase() implementation for ASIC sensors will return the latest values exported by the SwitchOrch to the stateDB's TEMPERATURE_INFO table.

## 7 **Virtual Switch**

NA

## 8 **Restrictions**

A CLI is not currently defined for the poller configuration (for setting/getting the Poller admin state and interval configuraiton).

## 9 **Unit Test cases**
Unit test case one-liners are given below:

| #  | Test case synopsis   | Expected results |
|-------|----------------------|------------------|
|1| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_STATUS" "admin_status" to "enable"   | Check that ASIC internal sensors are dumped periodically in the TEMPERATURE_INFO and the ASIC_SENSORS table
|2| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_STATUS" "admin_status" to "disable"  | Check that the poller stops
|3| Set "ASIC_SENSORS\|ASIC_SENSORS_POLLER_INTERVAL" "interval" to "30"  | Check that the poller interval changes from the default 10 seconds
|4| Issue "show platform temperature" | Check that the ASIC interal temperatures are displayed

## 10 **Action items**

