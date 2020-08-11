# SONiC Entity MIB Extension #

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Kebo Liu      | Initial version                   |



## 1. Overview 

The Entity MIB contains several groups of MIB objects, currently SONiC only implemented part of the entityPhysical group following RFC2737. The group contains a single table called "entPhysicalTable" to indentify the pysical components of the system. The MIB objects of "entityPhysical" group listed as below:

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

Now only physical entities as transceivers and it's DOM sensors(Temp, voltage, rx power, tx power and tx bias) are implemented, with snmpwalk can fetch the MIB info:

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

Also plan to add more physical entities such as thermal sensors, fan, and it's tachometers; PSU, PSU fan, and some sensors contained in PSU.

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

### 4.1 Adding more data to state DB

As mentioned in Section 3, currently lack the implementation of "entPhysicalContainedIn" object, and also there is no such kind of info stored in the state DB. A "contained_in_device" device will be added to the current tables, e.g., extended TEMPERATURE_INFO with the new field:

	; Defines information for a thermal object
	key                     = TEMPERATURE_INFO|object_name   ; name of the thermal object(CPU, ASIC, optical modules...)
	; field                 = value
	temperature             = FLOAT                          ; current temperature value
	timestamp               = STRING                         ; timestamp for the temperature fetched
	high_threshold          = FLOAT                          ; temperature high threshold
	critical_high_threshold = FLOAT                          ; temperature critical high threshold
	low_threshold           = FLOAT                          ; temperature low threshold
	critical_low_threshold  = FLOAT                          ; temperature critical low threshold
	warning_status          = BOOLEAN                        ; temperature warning status
	contained_in_device     = STRING                         ; name of the device which contains this sensor

To have this kind info available we need to extend the current platform API, can add a new function "get_contained_in_device_name" to DeviceBase class, this function will return the name of the device which it is contained in. This new field will be populated to state DB by related PMON daemons.

	class DeviceBase(object):
	    """
	    Abstract base class for interfacing with a generic type of platform
	    peripheral device
	    """

	    def get_contained_in_device_name(self):
		"""
		Retrieves The name of the device which contains this component
		Returns:
		    string: The name of the device
		"""
		raise NotImplementedError

## 5. Entity MIB extension test

### 5.1 Unit test

SNMP unit test for sensors (https://github.com/Azure/sonic-snmpagent/blob/master/tests/test_sensor.py) will be extended to cover all the new added MIB objects and physical components.

### 5.2 Community regression test

New test cases will be added to cover the new MIB entries:

1. Get temp sensor MIB info and cross-check with the TEMPERATURE_INFO table.
2. Get fan MIB info and cross-check with the FAN_INFO table.
3. Get PSU related MIB info and cross-check with PSU_INFO and related tables
3. Remove/Add DB entries from related tables to see whether MIB info can be correctly updated.

