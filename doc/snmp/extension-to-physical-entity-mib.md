# SONiC Entity MIB Extension #

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Kebo Liu      | Initial version                   |
 | 0.2 |             |      Junchao Chen  | Fix community review comment      |



## 1. Overview 

The Entity MIB contains several groups of MIB objects, currently SONiC only implemented part of the entityPhysical group following RFC2737. The group contains a single table called "entPhysicalTable" to identify the physical components of the system. The MIB objects of "entityPhysical" group listed as below:

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

Thermalctl daemon, Xcvrd, psud, are collecting physical device info to state DB, now we have PSU_INFO tale, FAN_INFO table, and TEMPERATURE_INFO table which can provide information for MIB entries.

Thermal sensors MIB info will come from TEMPERATURE_INFO, FAN_INFO will feed to FAN MIB entries and PSU_INFO will be the source of the PSU related entries.

The current already implemented cable and cable DOM sensors getting data from tables(TRANSCEIVER_INFO and TRANSCEIVER_DOM_SENSOR) which maintained by xcvrd.

### 4.1 entPhysicalParentRelPos implementation

entPhysicalParentRelPos is a mib object that reflect the relative position of a physical entity in its parent entity. In current implementation, there are following issues:

1. There is no position information in current platform API. Take fan as an example, now fan objects are saved as an list in chassis object, but the list index cannot reflect the physical fan position. There might be two problems, one is that the list can be initialized with arbitrary order, the other is that the order might change when remove/insert a fan object.
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

A new database table will be added to store the position information. The new table will be discussed in section 4.3.

### 4.2 entPhysicalContainedIn implementation

According to RFC, entPhysicalContainedIn indicates the sub ID of the parent physical entity for a physical entity. Now platform API uses a hierarchy structure to store platform devices. This hierarchy structure can be used for entPhysicalContainedIn implementation.

The parent device name will be saved to the database(see section 4.3). Snmp agent will use the parent device name to retrieve the parent sub ID and fill it to entPhysicalContainedIn field.

### 4.3 Adding new table to state DB to store physical entity relationship

A new table PHYSICAL_RELATION_INFO will be added:

	; Defines information to store physical entity relationship
	key                     = PHYSICAL_RELATION_INFO|object_name   ; name of the entity object
	; field                 = value
	position_in_parent      = INTEGER                              ; physical position in parent device
	parent_name             = STRING                               ; name of parent device

The data of this table will be collected by thermalctld, psud and xcvrd.

### 4.4 entPhysicalIndex implementation

For transceivers and its DOM sensors, there is already rule to generate entPhysicalIndex for them. For new entity such as FAN, PSU, the entPhysicalIndex generating rule is described below:

```
For fan drawer:
entPhysicalIndex = 500000000 + entPhysicalParentRelPos * 1000000

For fan:
entPhysicalIndex = entPhysicalContainedIn + 20020 + entPhysicalParentRelPos

For fan tachometers:
entPhysicalIndex = entPhysicalContainedIn + 10000

For PSU:
entPhysicalIndex = 600000000 + entPhysicalParentRelPos * 1000000

For PSU fan:
entPhysicalIndex = entPhysicalContainedIn + 20020 + entPhysicalParentRelPos

For PSU fan tachometers:
entPhysicalIndex = entPhysicalContainedIn + 10000 + entPhysicalParentRelPos

For PSU temperature:
entPhysicalIndex = entPhysicalContainedIn + 40011

For PSU power:
entPhysicalIndex = entPhysicalContainedIn + 40030

For PSU current:
entPhysicalIndex = entPhysicalContainedIn + 40040

For PSU voltage:
entPhysicalIndex = entPhysicalContainedIn + 40050

For chassis management:
entPhysicalIndex = 200000000

For chassis thermal:
entPhysicalIndex = 200000000 + 100000 + entPhysicalParentRelPos
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
