# SONiC Entity MIB Extension #

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Kebo Liu      | Initial version                   |
 | 0.2 |             |      Junchao Chen  | Fix community review comment      |



## 1. Overview 

The Entity MIB contains several groups of MIB objects: entityPhysical group, entityLogical group and so on. Currently SONiC only implemented part of the entityPhysical group following RFC2737. Since entityPhysical group is mostly common used, this extension will focus on entityPhysical group and leave other groups for future implementation. The group entityPhysical contains a single table called "entPhysicalTable" to identify the physical components of the system. The MIB objects of "entityPhysical" group listed as below:

	EntPhysicalEntry ::= SEQUENCE {
		entPhysicalIndex          PhysicalIndex,
		entPhysicalDescr          SnmpAdminString,
		entPhysicalVendorType     AutonomousType,
		entPhysicalContainedIn    INTEGER,
		entPhysicalClass          PhysicalClass,
		entPhysicalParentRelPos   INTEGER,
		entPhysicalName           SnmpAdminString,
		entPhysicalHardwareRev    SnmpAdminString,
		entPhysicalFirmwareRev    SnmpAdminString,
		entPhysicalSoftwareRev    SnmpAdminString,
		entPhysicalSerialNum      SnmpAdminString,
		entPhysicalMfgName        SnmpAdminString,
		entPhysicalModelName      SnmpAdminString,
		entPhysicalAlias          SnmpAdminString,
		entPhysicalAssetID        SnmpAdminString,
		entPhysicalIsFRU          TruthValue
	}

Detailed information about the MIB objects inside entPhysicalTable can be found in section 3 of RFC2737

## 2. Current Entity MIB implementation in SONiC
Currently SONiC implemented part of the MIB objects in the table:

	entPhysicalDescr          SnmpAdminString,
	entPhysicalClass          PhysicalClass, 
	entPhysicalName           SnmpAdminString,
	entPhysicalHardwareRev    SnmpAdminString,
	entPhysicalFirmwareRev    SnmpAdminString,
	entPhysicalSoftwareRev    SnmpAdminString,
	entPhysicalSerialNum      SnmpAdminString,
	entPhysicalMfgName        SnmpAdminString,
	entPhysicalModelName      SnmpAdminString,

Now only physical entities as transceivers and its DOM sensors(Temp, voltage, rx power, tx power and tx bias) are implemented, with snmpwalk can fetch the MIB info:

	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1000 = STRING: "SFP/SFP+/SFP28 for Ethernet0"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1001 = STRING: "DOM Temperature Sensor for Ethernet0"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1002 = STRING: "DOM Voltage Sensor for Ethernet0"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1011 = STRING: "DOM RX Power Sensor for Ethernet0/1"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1012 = STRING: "DOM TX Bias Sensor for Ethernet0/1"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1013 = STRING: "DOM TX Power Sensor for Ethernet0/1"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1021 = STRING: "DOM RX Power Sensor for Ethernet0/2"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1022 = STRING: "DOM TX Bias Sensor for Ethernet0/2"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1023 = STRING: "DOM TX Power Sensor for Ethernet0/2"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1031 = STRING: "DOM RX Power Sensor for Ethernet0/3"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1032 = STRING: "DOM TX Bias Sensor for Ethernet0/3"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1033 = STRING: "DOM TX Power Sensor for Ethernet0/3"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1041 = STRING: "DOM RX Power Sensor for Ethernet0/4"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1042 = STRING: "DOM TX Bias Sensor for Ethernet0/4"
	SNMPv2-SMI::mib-2.47.1.1.1.1.2.1043 = STRING: "DOM TX Power Sensor for Ethernet0/4"

## 3. A new extension to Entity MIB implementation
This extension aims to implement all the objects in the entityPhysical group.

Also plan to add more physical entities such as thermal sensors, fan, and its tachometers; PSU, PSU fan, and some sensors contained in PSU.

Another thing need to highlight is that in the current implementation, "entPhysicalContainedIn" object is not implemented, so there is no way to reflect the physical location of the components, this time it will be amended, by this all the MIB entries can be organized in a hierarchy manner, see below chart:

	Chassis -
	         |--MGMT (Chassis)
	         |              |--CPU package Sensor/T(x) (Temperature sensor)
	         |              |--CPU Core Sensor/T(x) (Temperature sensor)
	         |              |--Board AMB temp/T(x) (Temperature sensor)
	         |              |--Ports AMB temp/T(x) (Temperature sensor)
	         |              |--ASIC (Switch device)
	         |                  |--ASIC/T(x) (Temperature sensor)
	         |--FAN(x) (Fan)
	         |              |-- FAN/F(y) (Fan sensor)
	         |--PS(x) (Power supply)
	         |              |-- FAN/F(y) (Fan sensor)
	         |              |-- power-mon/T(y) (Temperature sensor)
	         |              |-- power-mon/ VOLTAGE  (Voltage sensor)
	         |--Ethernet x/y … cable (Port module)
                            |--DOM Temperature Sensor for Ethernet(x)  (Temperature sensor)
                            |--DOM Voltage Sensor for Ethernet(x)  (Voltage sensor)
                            |--DOM RX Power Sensor for Ethernet(x)/(y) (Power sensor)
                            |--DOM TX Bias Sensor for Ethernet(x)/(y) (Bias sensor)


## 4. The data source of the MIB entries

Thermalctl daemon, xcvrd, psud, are collecting physical device info to state DB, now we have PSU_INFO tale, FAN_INFO table, and TEMPERATURE_INFO table which can provide information for MIB entries.

Thermal sensors MIB info will come from TEMPERATURE_INFO, FAN_INFO will feed to FAN MIB entries and PSU_INFO will be the source of the PSU related entries.

The current already implemented cable and cable DOM sensors getting data from tables(TRANSCEIVER_INFO and TRANSCEIVER_DOM_SENSOR) which is maintained by xcvrd.

### 4.1 entPhysicalParentRelPos implementation

entPhysicalParentRelPos is an indication of the relative position of this 'child' component among all its 'sibling' components. Sibling components are defined as entPhysicalEntries which share the same instance values of each of the entPhysicalContainedIn and entPhysicalClass objects.

In current SONiC implementation, there are following issues:

1. There is no position information in current platform API. Take fan as an example, now fan objects are saved as an list in chassis object, but the list index cannot reflect the physical fan position. There might be two problems, one is that the list can be initialized with arbitrary order, the other is that the order might change when remove/insert a fan to switch.
2. Now all thermal objects are stored in chassis object, but not all thermal objects are the directly children of chassis. For example, we have PSU thermal and SFP module thermal object whose parent device is not chassis.

In order to provide reliable data for entPhysicalParentRelPos, a few changes will be made in platform API.

First, a new API will be added to DeviceBase class for getting the relative position in parent device. See:

```python
class DeviceBase(object):
	def get_position_in_parent(self):
		"""
		Retrieves 1-based relative physical position in parent device
		Returns:
		    integer: The 1-based relative physical position in parent device
		"""
		raise NotImplementedError
```

Second, add thermal list for PsuBase and SfpBase to reflect the actual hierarchy. Vender should initialize thermal list for PSU and SFP properly. Thermal control daemon should also retrieve thermal objects from PSU and SFP.

```python
class PsuBase(device_base.DeviceBase):
    def __init__(self):
        self._thermal_list = []

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this PSU

        Returns:
            An integer, the number of thermals available on this PSU
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this PSU

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this PSU
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


class SfpBase(device_base.DeviceBase):
    def __init__(self):
        self._thermal_list = []

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this SFP

        Returns:
            An integer, the number of thermals available on this SFP
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this SFP

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this SFP
        """
        return self._thermal_list

    def get_thermal(self, index):
        """
        Retrieves thermal unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the thermal to
            retrieve

        Returns:
            An object derived from ThermalBase representing the specified thermal
        """
        thermal = None

        try:
            thermal = self._thermal_list[index]
        except IndexError:
            sys.stderr.write("THERMAL index {} out of range (0-{})\n".format(
                             index, len(self._thermal_list)-1))

        return thermal
```

A new database table will be added to store the position information. The new table will be discussed in section 4.4.

### 4.2 entPhysicalContainedIn implementation

According to RFC, entPhysicalContainedIn indicates the value of entPhysicalIndex for the physical entity which 'contains' this physical entity. A value of zero indicates this physical entity is not contained in any other physical entity. 

Now platform API uses a hierarchy structure to store platform devices. This hierarchy structure can be used for entPhysicalContainedIn implementation. For example, chassis object has a list of PSU objects, and PSU object has a list of PSU fan objects, we can deduce parent device based on such information and no new platform API is needed.

Thermalctld, psud, xcvrd will collect the parent device name and save the information to the database(see section 4.4). Snmp agent will use the parent device name to retrieve the parent sub ID and fill it to entPhysicalContainedIn field.

### 4.3 entPhysicalIsFRU implementation

The entPhysicalIsFRU object indicates whether or not this physical entity is considered a 'field replaceable unit' by the vendor. If this object contains the value 'true(1)' then this entPhysicalEntry identifies a field replaceable unit.  For all entPhysicalEntries which represent components that are permanently contained within a field replaceable unit, the value 'false(2)' should be returned for this object.

A new platform API DeviceBase.is_replaceable will be added to get such information. Vendor should override this method in order to support entPhysicalIsFRU.

```python
class DeviceBase(object):
	def is_replaceable(self):
		"""
		Indicate whether this device is replaceable.
		Returns:
		    bool: True if it is replaceable.
		"""
		raise NotImplementedError
```

A new field is_replaceable will be added to FAN_INFO, PSU_INFO and TRANSCEIVER_INFO table (See detail in section 4.4). Thermalctld, psud, xcvrd will collect this information and save it to database.

### 4.4 Database change

New fields 'current', 'power', 'is_replaceable' will be added to PSU_INFO table:

    ; Defines information for a psu
    key                     = PSU_INFO|psu_name              ; information for the psu
    ; field                 = value
    ...
    current                 = FLOAT                          ; current of the psu
    power                   = FLOAT                          ; power of the psu
    is_replaceable          = BOOLEAN                        ; indicate if the psu is replaceable

New field 'is_replaceable' will be added to FAN_INFO table:

    ; Defines information for a fan
    key                     = FAN_INFO|fan_name              ; information for the fan
    ; field                 = value
    ...
    is_replaceable          = BOOLEAN                        ; indicate if the fan is replaceable

New field 'is_replaceable' will be added to TEMPERATURE_INFO table:

    ; Defines information for a thermal object
    key                     = TEMPERATURE_INFO|object_name   ; name of the thermal object(CPU, ASIC, optical modules...)
    ; field                 = value
    ...
    is_replaceable          = BOOLEAN                        ; indicate if the thermal is replaceable

New field 'is_replaceable' will be added to TRANSCEIVER_INFO table:

    ; Defines Transceiver information for a port
    key                         = TRANSCEIVER_INFO|ifname    ; information for SFP on port
    ; field                     = value
    ...
    is_replaceable          = BOOLEAN                        ; indicate if the SFP is replaceable

Currently, we only store fan drawer name in FAN_INFO table and that is not enough to describe all the attributes of a fan drawer. A new table FAN_DRAWER_INFO will be added. Thermalctld is responsible for saving data to FAN_DRAWER_INFO table. See table definition:

    ; Defines information for a fan drawer
    key                     = FAN_DRAWER_INFO|object_name    ; name of the fan drawer object
    ; field                 = value
    presence                = BOOLEAN                        ; presence of the fan drawer
    model                   = STRING                         ; model name of the fan drawer
    serial                  = STRING                         ; serial number of the fan drawer
    status                  = BOOLEAN                        ; status of the fan drawer
    led_status              = STRING                         ; led status of the fan drawer
    is_replaceable          = BOOLEAN                        ; indicate if the fan drawer is replaceable

As discussed in section 4.1 and 4.2, we need more information in database to implement entPhysicalParentRelPos and entPhysicalContainedIn. There is an option that we could add these information to existing table such as PSU_INFO, FAN_INFO etc. However, as these two MIB objects are used to describe the relationship between physical entities and table like PSU_INFO is used for saving attributes of a physical entity, we prefer to store the relation info to a new table. A new table PHYSICAL_ENTITY_INFO will be added:

    ; Defines information to store physical entity relationship
    key                     = PHYSICAL_ENTITY_INFO|object_name   ; name of the entity object
    ; field                 = value
    position_in_parent      = INTEGER                            ; physical position in parent device
    parent_name             = STRING                             ; name of parent device

The data of PHYSICAL_ENTITY_INFO will be collected by thermalctld, psud and xcvrd.

### 4.4 entPhysicalIndex implementation

The existing rule for generating entPhysicalIndex is too simple. There is risk that two different entities might have the same entPhysicalIndex. Here we design a new rule for generating the entPhysicalIndex:

```
For non-port entity, the rule to generate entPhysicalIndex describes below:
The entPhysicalIndex is divided into 3 layers:
    1. Module layer which includes modules located on system (e.g. fan drawer, PSU)
    2. Device layer which includes system devices (e.g. fan )
    3. Sensor layer which includes system sensors (e.g. temperature sensor, fan sensor)
The entPhysicalIndex is a 9 digits number, and each digit describes below:
Digit 1: Module Type
Digit 2~3: Module Index
Digit 4~5: Device Type
Digit 6~7: Device Index
Digit 8: Sensor Type
Digit 9: Sensor Index

Module Type describes below:
2 - Management
5 - Fan Drawer
6 - PSU
Device Type describes below:
01 - PS
02 - Fan
24 - Power Monitor (temperature, power, current, voltage...)
99 - Chassis Thermals
Sensor Type describes below:
1 - Temperature
2 - Fan Tachometers
3 - Power
4 - Current
5 - Voltage

e.g. 501000000 means the first fan drawer, 502020100 means the first fan of the second fan drawer

As we are using ifindex to generate port entPhysicalIndex and ifindex might be a value larger than 99 which cannot be hold by 2 digits, we uses a different way to generate port entPhysicalIndex.

For port entity, the entPhysicalIndex is a 10 digits number, and each digit describes below:
Digit 1: 1
Digit 2~8: ifindex
Digit 9: Sensor Type
Digit 10: Sensor Index

Port Sensor Type describes below:
1 - Temperature
2 - TX Power
3 - RX Power
4 - TX BIAS
5 - Voltage
```

## 5. Entity MIB extension test

### 5.1 Unit test

SNMP unit test for sensors (https://github.com/Azure/sonic-snmpagent/blob/master/tests/test_sensor.py) will be extended to cover all the new added MIB objects and physical components.

### 5.2 Community regression test

New test cases will be added to cover the new MIB entries:

1. Get temp sensor MIB info and cross-check with the TEMPERATURE_INFO table.
2. Get fan MIB info and cross-check with the FAN_INFO table.
3. Get PSU related MIB info and cross-check with PSU_INFO and related tables
4. Remove/Add DB entries from related tables to see whether MIB info can be correctly updated.
5. Currently, each platform API is tested by sonic-mgmt, see [here](https://github.com/Azure/sonic-mgmt/tree/master/tests/platform_tests/api). We will add regression test case for each newly added platform API to verify them.
