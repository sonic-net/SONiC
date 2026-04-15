# OpenConfig support for Platform components

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [1 Feature Overview](#1-feature-overview)
  * [2 Functionality](#2-functionality)  
  * [3 Design](#3-design)
  * [4 Testing](#4-testing)
  * [5 Limitations](#5-limitations)
  * [6 Future Enhancements](#6-future-enhancements)
  * [7 References](#7-references)

# List of Tables
  * [Table 1: Abbreviations](#table-1-abbreviations) 
  * [Table 2: Component Basic Information Mapping](#component-basic-information-mapping) 
  * [Table 3: Temperature Information Mapping](#temperature-information-mapping) 
  * [Table 4: Power Supply Information Mapping](#power-supply-information-mapping) 
  * [Table 5: Fan Information Mapping](#fan-information-mapping) 
  * [Table 6: CPU Information Mapping](#cpu-information-mapping) 
  * [Table 7: Transceiver Information Mapping](#transceiver-information-mapping) 
  * [Table 8: Component Type to DB Table Mapping](#component-type-to-db-table-mapping) 
  * [Table 9: Transceiver Threshold Field Mapping](#334-transceiver-threshold-field-mapping) 

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 08/24/2025  | Anukul Verma | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig monitoring of Platform components in SONiC corresponding to openconfig-platform.yang module and its sub-modules.

# Scope
- This document describes the high level design of OpenConfig monitoring of Platform components via gNMI/REST in SONiC.
- This does not cover the SONiC KLISH CLI.
- Openconfig-platform.yang version latest from openconfig yang repo is considered.
- Previous implementation supported only EEPROM component using Custom app approach (pfm_app.go). This new implementation uses common app (transformer) approach and extends support to all listed component types.
- Supported attributes in OpenConfig YANG tree:
```
module: openconfig-platform
  +--rw components
     +--rw component* [name]
        +--rw name                   -> ../config/name
        +--rw config
        |  +--rw name?   string
        +--ro state
        |  +--ro name?               string
        |  +--ro type?               union
        |  x--ro id?                 string
        |  x--ro location?           string
        |  +--ro description?        string
        |  +--ro mfg-name?           string
        |  +--ro mfg-date?           oc-yang:date
        |  +--ro hardware-version?   string
        |  +--ro serial-no?          string
        |  +--ro part-no?            string
        |  +--ro model-name          string
        |  +--ro removable?          boolean
        |  +--ro oper-status?        identityref
        |  +--ro empty?              boolean
        |  +--ro parent?             -> ../../../component/config/name
        |  +--ro temperature
        |  |  +--ro instant?           decimal64
        |  |  +--ro min?               decimal64
        |  |  +--ro max?               decimal64
        |  |  +--ro alarm-status?      boolean
        |  |  +--ro oc-platform-ext:critical-high-threshold?   decimal64
        |  |  +--ro oc-platform-ext:critical-low-threshold?    decimal64
        +--rw power-supply
        |  +--ro state
        |     +--ro oc-platform-psu:enabled?          boolean
        |     +--ro oc-platform-psu:capacity?         oc-types:ieeefloat32
        |     +--ro oc-platform-psu:input-voltage?    oc-types:ieeefloat32
        |     +--ro oc-platform-psu:input-current?    oc-types:ieeefloat32
        |     +--ro oc-platform-psu:output-voltage?   oc-types:ieeefloat32
        |     +--ro oc-platform-psu:output-current?   oc-types:ieeefloat32
        |     +--ro oc-platform-psu:output-power?     oc-types:ieeefloat32
        +--rw fan
        |  +--ro state
        |     +--ro oc-fan:speed?                      uint32
        |     +--ro oc-platform-ext:speed-percentage?   uint32
        |     +--ro oc-platform-ext:direction?           enumeration
        +--rw cpu
        |  +--rw config
        |  +--ro state
        |  +--rw oc-cpu:utilization
        |     +--ro oc-cpu:state
        |        +--ro oc-cpu:instant?    oc-types:percentage
        |        +--ro oc-cpu:avg?        oc-types:percentage
        |        +--ro oc-cpu:min?        oc-types:percentage
        |        +--ro oc-cpu:max?        oc-types:percentage
        |        +--ro oc-cpu:interval?   oc-types:stat-interval
        +--rw port
        |  +--rw oc-port:breakout-mode
        |     +--rw oc-port:groups
        |        +--rw oc-port:group* [index]
        |           +--rw oc-port:index     -> ../config/index
        |           +--rw oc-port:config
        |           |  +--rw oc-port:index?                    uint8
        |           |  +--rw oc-port:num-breakouts?            uint8
        |           |  +--rw oc-port:breakout-speed?           identityref
        |           |  +--rw oc-port:num-physical-channels?    uint8
        |           +--ro oc-port:state
        |              +--ro oc-port:index?                    uint8
        |              +--ro oc-port:num-breakouts?            uint8
        |              +--ro oc-port:breakout-speed?           identityref
        |              +--ro oc-port:num-physical-channels?    uint8
        +--rw oc-transceiver:transceiver
           +--ro oc-transceiver:state
           |  +--ro oc-transceiver:enabled?               boolean
           |  +--ro oc-transceiver:form-factor-preconf?   identityref
           |  +--ro oc-transceiver:present?               enumeration
           |  +--ro oc-transceiver:form-factor?           identityref
           |  +--ro oc-transceiver:connector-type?        identityref
           |  +--ro oc-transceiver:vendor-rev?            string
           |  +--ro oc-transceiver:serial-no?             string
           |  +--ro oc-transceiver:date-code?             oc-yang:date-and-time
           |  +--ro oc-transceiver:supply-voltage
           |     +--ro oc-transceiver:instant?    decimal64
           +--rw oc-transceiver:physical-channels
           |  +--rw oc-transceiver:channel* [index]
           |     +--rw oc-transceiver:index     -> ../config/index
           |     +--ro oc-transceiver:state
           |        +--ro oc-transceiver:index?                        uint16
           |        +--ro oc-transceiver:description?                  string
           |        +--ro oc-transceiver:output-power
           |        |  +--ro oc-transceiver:instant?   decimal64
           |        +--ro oc-transceiver:input-power
           |        |  +--ro oc-transceiver:instant?   decimal64
           |        +--ro oc-transceiver:laser-bias-current
           |           +--ro oc-transceiver:instant?   decimal64
           +--rw oc-transceiver:thresholds
              +--ro oc-transceiver:threshold* [severity]
                 +--ro oc-transceiver:severity    -> ../state/severity
                 +--ro oc-transceiver:state
                    +--ro oc-transceiver:severity?                   identityref
                    +--ro oc-transceiver:module-temperature-upper?    decimal64
                    +--ro oc-transceiver:module-temperature-lower?   decimal64
                    +--ro oc-transceiver:output-power-upper?         decimal64
                    +--ro oc-transceiver:output-power-lower?         decimal64
                    +--ro oc-transceiver:input-power-upper?          decimal64
                    +--ro oc-transceiver:input-power-lower?          decimal64
                    +--ro oc-transceiver:laser-bias-current-upper?   decimal64
                    +--ro oc-transceiver:laser-bias-current-lower?   decimal64
                    +--ro oc-transceiver:supply-voltage-upper?       decimal64
                    +--ro oc-transceiver:supply-voltage-lower?       decimal64
```

# Definition/Abbreviation
### Table 1: Abbreviations

| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| PSU                      | Power Supply Unit |
| DOM                      | Digital Optical Monitoring |
| EEPROM                   | Electrically Erasable Programmable Read-Only Memory |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig Platform YANG models.
2. Implement transformer support for Openconfig platform model to have following supports:
    - Get Platform component state attributes via REST and gNMI.
    - Subscribe Platform component attributes for telemetry via gNMI.
3. Add support for following Platform component types:
    * chassis
    * cpu
    * eeprom (System EEPROM)
    * power-supply (PSU)
    * fan
    * fantray
    * temperature
    * transceiver
    * port (breakout-mode configuration)
4. Support for platform component state information including:
    * Basic component information (name, type, description, manufacturer, etc.)
    * Operational status and health monitoring
    * Temperature monitoring with thresholds and alarm status
    * CPU utilization statistics
    * Power supply capacity and status
    * Fan speed monitoring
    * Transceiver information and DOM (Digital Optical Monitoring) data
    * Port breakout-mode configuration (Dynamic Port Breakout)

### 1.1.2 Configuration and Management Requirements
The Platform module is primarily read-only (monitoring). Get and Subscribe operations are supported via REST and gNMI for all component types. Set operations (PATCH/DELETE) are supported only for port breakout-mode configuration (Dynamic Port Breakout). All other platform component paths will return an error if a Set operation is attempted.

### 1.1.3 Scalability Requirements
The maximum number of components depends on the hardware platform capabilities and the number of physical components present in the system.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports a management framework for REST and gNMI operations. This feature adds support for OpenConfig based YANG models using transformer based implementation for Platform features. Get and Subscribe operations are supported for all component types. Set operations (PATCH/DELETE) are supported only for port breakout-mode (Dynamic Port Breakout) configuration path.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform GET operations on the supported YANG paths.
2. gNMI client with support for capabilities, get and subscribe based on the supported YANG models.
3. Platform monitoring and health management through standardized OpenConfig interfaces.
4. Integration with network management systems for comprehensive platform visibility.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
The following existing CONFIG DB table is utilized for port breakout-mode configuration:
- BREAKOUT_CFG (used for Dynamic Port Breakout; stores `brkout_mode` field per parent port)

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
The following existing STATE DB tables are utilized for platform component information:
- EEPROM_INFO
- PHYSICAL_ENTITY_INFO
- TEMPERATURE_INFO
- TRANSCEIVER_INFO
- TRANSCEIVER_DOM_THRESHOLD
- TRANSCEIVER_DOM_SENSOR
- PSU_INFO
- FAN_INFO
- FAN_DRAWER_INFO
- CHASSIS_INFO
- CPU_STATS (new table; sonic-host-services will have changes to populate this)

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
The following existing COUNTER DB table is utilized for chassis utilization resource information:
- CRM|STATS (used for fib4, fib6, and lpm resource utilization via crm_stats_ipv4_route_used, crm_stats_ipv4_route_available, crm_stats_ipv6_route_used, crm_stats_ipv6_route_available fields)

## 3.3 User Interface
### 3.3.1 Data Models
Openconfig-platform.yang and its submodules will be used as user interfacing models:
- openconfig-platform.yang
- openconfig-platform-psu.yang
- openconfig-platform-fan.yang
- openconfig-platform-transceiver.yang
- openconfig-platform-cpu.yang
- openconfig-platform-common.yang
- openconfig-platform-types.yang
- openconfig-platform-ext.yang (extensions for fan speed-percentage and direction)
- openconfig-platform-port.yang (port breakout-mode configuration)
- openconfig-platform-annotation.yang
- openconfig-platform-deviation.yang

### 3.3.2 Database Table and Field Mapping
The following sections provide detailed mapping between OpenConfig YANG paths and SONiC STATE DB tables and fields for each component type.

#### 3.3.2.1 Chassis Component Mapping
**Database Table:** CHASSIS_INFO  
**Key Pattern:** "chassis *" (e.g., "chassis 1")  
**Component Type:** openconfig-platform-types:CHASSIS

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: CHASSIS |
| `/components/component/state/description` | - | - | Fixed: "Chassis component" |
| `/components/component/state/serial-no` | CHASSIS_INFO | serial |
| `/components/component/state/hardware-version` | CHASSIS_INFO | revision |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/state/model-name` | CHASSIS_INFO | model |

#### 3.3.2.2 CPU Component Mapping  
**Database Table:** CPU_STATS  
**Key Pattern:** "CPU*" (e.g., "CPU0")  
**Component Type:** openconfig-platform-types:CPU

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/type` | - | - | Fixed: CPU |
| `/components/component/state/description` | CPU_STATS | vendor_id, model_name | Derived: "{vendor_id}: {model_name}" |
| `/components/component/state/model-name` | CPU_STATS | model_name | CPU model information |
| `/components/component/state/mfg-name` | CPU_STATS | vendor_id | CPU vendor identifier |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/cpu/utilization/state/instant` | CPU_STATS | load | Last value from load JSON array (most recent sample) |
| `/components/component/cpu/utilization/state/avg` | CPU_STATS | load | Average of all samples in load JSON array over the interval |
| `/components/component/cpu/utilization/state/min` | CPU_STATS | load | Minimum of all samples in load JSON array over the interval |
| `/components/component/cpu/utilization/state/max` | CPU_STATS | load | Maximum of all samples in load JSON array over the interval |
| `/components/component/cpu/utilization/state/interval` | - | - | Fixed: 60000000000 ns (60 seconds). The load field is a JSON array of CPU load samples collected over this 1-minute window. |

#### 3.3.2.3 EEPROM Component Mapping
**Database Table:** EEPROM_INFO  
**Key Pattern:** "System Eeprom"  
**Component Type:** openconfig-platform-types:SENSOR

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/id` | EEPROM_INFO | 0x21 | Product name |
| `/components/component/state/name` | - | - | Fixed: "System Eeprom" |
| `/components/component/state/type` | - | - | Fixed: SENSOR |
| `/components/component/state/description` | EEPROM_INFO | 0x28 | Platform name |
| `/components/component/state/part-no` | EEPROM_INFO | 0x22 | Product part number |
| `/components/component/state/serial-no` | EEPROM_INFO | 0x23 | Serial number (fallback: 0x2f Service Tag) |
| `/components/component/state/mfg-date` | EEPROM_INFO | 0x25 | Manufacturing date |
| `/components/component/state/hardware-version` | EEPROM_INFO | 0x27 | Label revision |
| `/components/component/state/mfg-name` | EEPROM_INFO | 0x2b | Manufacturer name (fallback: 0x2d Vendor) |
| `/components/component/state/location` | - | - | Fixed: "Slot 1" |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |

#### 3.3.2.4 Power Supply (PSU) Component Mapping
**Database Table:** PSU_INFO  
**Key Pattern:** "PSU*" (e.g., "PSU 1", "PSU 2")  
**Component Type:** openconfig-platform-types:POWER_SUPPLY

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: POWER_SUPPLY |
| `/components/component/state/description` | - | - | Same as component key |
| `/components/component/state/serial-no` | PSU_INFO | serial | Serial number |
| `/components/component/state/hardware-version` | PSU_INFO | revision | Hardware revision |
| `/components/component/state/model-name` | PSU_INFO | model | Model name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Usually chassis |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | PSU_INFO | presence, status | Derived from presence + status fields |
| `/components/component/state/empty` | PSU_INFO | presence | Negation of presence field |
| `/components/component/state/removable` | PSU_INFO | is_replaceable | From is_replaceable field |
| `/components/component/power-supply/state/capacity` | PSU_INFO | max_power | Maximum power capacity (ieeefloat32) |
| `/components/component/power-supply/state/enabled` | PSU_INFO | presence, status | Derived from oper-status (true if ACTIVE) |
| `/components/component/power-supply/state/input-voltage` | PSU_INFO | input_voltage | Input voltage (ieeefloat32) |
| `/components/component/power-supply/state/input-current` | PSU_INFO | input_current | Input current (ieeefloat32) |
| `/components/component/power-supply/state/output-voltage` | PSU_INFO | voltage | Output voltage (ieeefloat32) |
| `/components/component/power-supply/state/output-current` | PSU_INFO | current | Output current (ieeefloat32) |
| `/components/component/power-supply/state/output-power` | PSU_INFO | power | Output power (ieeefloat32) |

#### 3.3.2.5 Fan Component Mapping
**Database Table:** FAN_INFO  
**Key Pattern:** "fantray\*.fan\*" or "PSU\*.fan\*" (e.g., "fantray1.fan1", "PSU1.fan1")  
**Component Type:** openconfig-platform-types:FAN

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: FAN |
| `/components/component/state/description` | - | - | Same as component key |
| `/components/component/state/serial-no` | FAN_INFO | serial | Serial number |
| `/components/component/state/model-name` | FAN_INFO | model | Model name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | FAN_INFO | presence, status | Derived from presence + status fields |
| `/components/component/state/empty` | FAN_INFO | presence | Negation of presence field |
| `/components/component/state/removable` | FAN_INFO | is_replaceable | From is_replaceable field |
| `/components/component/fan/state/speed` | FAN_INFO | speed_in_rpm | Fan speed in RPM |
| `/components/component/fan/state/speed-percentage` | FAN_INFO | speed | Fan speed as percentage |
| `/components/component/fan/state/direction` | FAN_INFO | direction | Fan airflow direction |

#### 3.3.2.6 Fan Tray Component Mapping
**Database Table:** FAN_DRAWER_INFO  
**Key Pattern:** "fantray*" (e.g., "fantray1", "fantray2")  
**Component Type:** openconfig-platform-types:FAN_TRAY

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: FAN_TRAY |
| `/components/component/state/description` | - | - | Same as component key |
| `/components/component/state/serial-no` | FAN_DRAWER_INFO | serial | Serial number |
| `/components/component/state/model-name` | FAN_DRAWER_INFO | model | Model name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Usually chassis |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | FAN_DRAWER_INFO | presence, status | Derived from presence + status fields |
| `/components/component/state/empty` | FAN_DRAWER_INFO | presence | Negation of presence field |
| `/components/component/state/removable` | FAN_DRAWER_INFO | is_replaceable | From is_replaceable field |

#### 3.3.2.7 Temperature Component Mapping
**Database Table:** TEMPERATURE_INFO  
**Key Pattern:** Various sensor names (e.g., "temp1", "cpu-thermal", "NPU0_TEMP_0")  
**Component Type:** openconfig-platform-types:SENSOR

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: SENSOR |
| `/components/component/state/description` | - | - | Derived: "Temperature Sensor - {key}" |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | TEMPERATURE_INFO | is_replaceable | From is_replaceable field |
| `/components/component/state/temperature/instant` | TEMPERATURE_INFO | temperature | Current temperature reading |
| `/components/component/state/temperature/min` | TEMPERATURE_INFO | minimum_temperature | Minimum temperature recorded since system boot (maintained by platform thermalctld) |
| `/components/component/state/temperature/max` | TEMPERATURE_INFO | maximum_temperature | Maximum temperature recorded since system boot (maintained by platform thermalctld) |
| `/components/component/state/temperature/alarm-status` | TEMPERATURE_INFO | warning_status | Temperature alarm status |
| `/components/component/state/temperature/critical-high-threshold` | TEMPERATURE_INFO | critical_high_threshold | Critical high threshold (oc-platform-ext) |
| `/components/component/state/temperature/critical-low-threshold` | TEMPERATURE_INFO | critical_low_threshold | Critical low threshold (oc-platform-ext) |

#### 3.3.2.8 Transceiver Component Mapping
**Database Tables:** TRANSCEIVER_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_DOM_THRESHOLD  
**Key Pattern:** "Ethernet*" (e.g., "Ethernet0", "Ethernet1/1")  
**Component Type:** openconfig-platform-types:TRANSCEIVER

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: TRANSCEIVER |
| `/components/component/state/description` | TRANSCEIVER_INFO | type | Derived: "Transceiver {key} - Type: {type}" |
| `/components/component/state/serial-no` | TRANSCEIVER_INFO | serial | Serial number |
| `/components/component/state/hardware-version` | TRANSCEIVER_INFO | hardware_rev | Hardware revision |
| `/components/component/state/mfg-name` | TRANSCEIVER_INFO | manufacturer | Manufacturer name |
| `/components/component/state/model-name` | TRANSCEIVER_INFO | model | Model name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | TRANSCEIVER_INFO | is_replaceable | From is_replaceable field |

##### Transceiver State Information

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/transceiver/state/enabled` | - | - | Fixed: true (assumed enabled if present in table) |
| `/transceiver/state/form-factor-preconf` | TRANSCEIVER_INFO | type | Mapped to OC form factor identity (e.g., QSFP28, OSFP) |
| `/transceiver/state/present` | - | - | Fixed: "PRESENT" (assumed present if in table) |
| `/transceiver/state/form-factor` | TRANSCEIVER_INFO | type | Mapped to OC form factor identity (e.g., QSFP28, OSFP) |
| `/transceiver/state/connector-type` | TRANSCEIVER_INFO | connector | Mapped to OC connector type identity (e.g., LC, MPO) |
| `/transceiver/state/vendor-rev` | TRANSCEIVER_INFO | vendor_rev | Vendor revision |
| `/transceiver/state/serial-no` | TRANSCEIVER_INFO | serial | Serial number |
| `/transceiver/state/date-code` | TRANSCEIVER_INFO | vendor_date | Manufacturing date code |
| `/transceiver/state/supply-voltage/instant` | TRANSCEIVER_DOM_SENSOR | voltage | Supply voltage |

##### Transceiver Thresholds

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/transceiver/thresholds/threshold[severity=WARNING]/state/output-power-upper` | TRANSCEIVER_DOM_THRESHOLD | txpowerhighwarning | TX power high warning |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/output-power-lower` | TRANSCEIVER_DOM_THRESHOLD | txpowerlowwarning | TX power low warning |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/output-power-upper` | TRANSCEIVER_DOM_THRESHOLD | txpowerhighalarm | TX power high alarm |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/output-power-lower` | TRANSCEIVER_DOM_THRESHOLD | txpowerlowalarm | TX power low alarm |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/input-power-upper` | TRANSCEIVER_DOM_THRESHOLD | rxpowerhighwarning | RX power high warning |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/input-power-lower` | TRANSCEIVER_DOM_THRESHOLD | rxpowerlowwarning | RX power low warning |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/input-power-upper` | TRANSCEIVER_DOM_THRESHOLD | rxpowerhighalarm | RX power high alarm |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/input-power-lower` | TRANSCEIVER_DOM_THRESHOLD | rxpowerlowalarm | RX power low alarm |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/laser-bias-current-upper` | TRANSCEIVER_DOM_THRESHOLD | txbiashighwarning | TX bias high warning |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/laser-bias-current-lower` | TRANSCEIVER_DOM_THRESHOLD | txbiaslowwarning | TX bias low warning |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/laser-bias-current-upper` | TRANSCEIVER_DOM_THRESHOLD | txbiashighalarm | TX bias high alarm |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/laser-bias-current-lower` | TRANSCEIVER_DOM_THRESHOLD | txbiaslowalarm | TX bias low alarm |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/supply-voltage-upper` | TRANSCEIVER_DOM_THRESHOLD | vcchighwarning | Voltage high warning |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/supply-voltage-lower` | TRANSCEIVER_DOM_THRESHOLD | vcclowwarning | Voltage low warning |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/supply-voltage-upper` | TRANSCEIVER_DOM_THRESHOLD | vcchighalarm | Voltage high alarm |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/supply-voltage-lower` | TRANSCEIVER_DOM_THRESHOLD | vcclowalarm | Voltage low alarm |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/module-temperature-upper` | TRANSCEIVER_DOM_THRESHOLD | temphighwarning | Temperature high warning |
| `/transceiver/thresholds/threshold[severity=WARNING]/state/module-temperature-lower` | TRANSCEIVER_DOM_THRESHOLD | templowwarning | Temperature low warning |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/module-temperature-upper` | TRANSCEIVER_DOM_THRESHOLD | temphighalarm | Temperature high alarm |
| `/transceiver/thresholds/threshold[severity=CRITICAL]/state/module-temperature-lower` | TRANSCEIVER_DOM_THRESHOLD | templowalarm | Temperature low alarm |

##### Transceiver Physical Channels

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/transceiver/physical-channels/channel[index=N]/state/index` | - | - | Channel index (0-based) |
| `/transceiver/physical-channels/channel[index=N]/state/description` | - | - | Channel description |
| `/transceiver/physical-channels/channel[index=N]/state/input-power/instant` | TRANSCEIVER_DOM_SENSOR | rx{N}power | RX power for channel N |
| `/transceiver/physical-channels/channel[index=N]/state/output-power/instant` | TRANSCEIVER_DOM_SENSOR | tx{N}power | TX power for channel N |
| `/transceiver/physical-channels/channel[index=N]/state/laser-bias-current/instant` | TRANSCEIVER_DOM_SENSOR | tx{N}bias | TX bias current for channel N |

#### 3.3.2.9 Chassis Utilization Resources Mapping
**Database Table:** CRM|STATS (COUNTERS_DB)  
**Key Pattern:** "chassis *" (parent chassis component)  
**Supported Resources:** fib4, fib6, lpm

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/chassis/utilization/resources/resource[name=fib4]/state/name` | - | - | Fixed: "fib4" |
| `/components/component/chassis/utilization/resources/resource[name=fib4]/state/used` | CRM\|STATS | crm_stats_ipv4_route_used | IPv4 routes used |
| `/components/component/chassis/utilization/resources/resource[name=fib4]/state/free` | CRM\|STATS | crm_stats_ipv4_route_available | IPv4 routes available |
| `/components/component/chassis/utilization/resources/resource[name=fib6]/state/name` | - | - | Fixed: "fib6" |
| `/components/component/chassis/utilization/resources/resource[name=fib6]/state/used` | CRM\|STATS | crm_stats_ipv6_route_used | IPv6 routes used |
| `/components/component/chassis/utilization/resources/resource[name=fib6]/state/free` | CRM\|STATS | crm_stats_ipv6_route_available | IPv6 routes available |
| `/components/component/chassis/utilization/resources/resource[name=lpm]/state/name` | - | - | Fixed: "lpm" |
| `/components/component/chassis/utilization/resources/resource[name=lpm]/state/used` | CRM\|STATS | crm_stats_ipv4_route_used + crm_stats_ipv6_route_used | Sum of IPv4 and IPv6 routes used |
| `/components/component/chassis/utilization/resources/resource[name=lpm]/state/free` | CRM\|STATS | crm_stats_ipv4_route_available + crm_stats_ipv6_route_available | Sum of IPv4 and IPv6 routes available |

#### 3.3.2.10 Port Breakout-Mode Mapping
**Database Table:** BREAKOUT_CFG (CONFIG_DB)  
**Key Pattern:** Parent port name (e.g., "Ethernet0", "Ethernet4")  
**Transformer:** Subtree transformer `pfm_breakout_config_xfmr` (in `xfmr_breakout.go`)

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/port/breakout-mode/groups/group[index=0]/config/num-breakouts` | BREAKOUT_CFG | brkout_mode | Extracted from mode string (e.g., "4" from "4x25G[4x25G]") |
| `/components/component/port/breakout-mode/groups/group[index=0]/config/breakout-speed` | BREAKOUT_CFG | brkout_mode | Extracted speed identity (e.g., SPEED_25GB from "4x25G[4x25G]") |
| `/components/component/port/breakout-mode/groups/group[index=0]/config/num-physical-channels` | BREAKOUT_CFG | brkout_mode | Extracted from mode string |
| `/components/component/port/breakout-mode/groups/group[index=0]/state/num-breakouts` | BREAKOUT_CFG | brkout_mode | Same as config (read from DB) |
| `/components/component/port/breakout-mode/groups/group[index=0]/state/breakout-speed` | BREAKOUT_CFG | brkout_mode | Same as config (read from DB) |
| `/components/component/port/breakout-mode/groups/group[index=0]/state/num-physical-channels` | BREAKOUT_CFG | brkout_mode | Same as config (read from DB) |

**Supported Operations:**
- **GET:** Returns current breakout-mode configuration from BREAKOUT_CFG table.
- **PATCH:** Triggers Dynamic Port Breakout (DPB). Deletes existing child ports and creates new ports based on the new breakout mode. Requires `num-breakouts`, `breakout-speed`, and `num-physical-channels` in the request body. Only group index 0 is supported.
- **DELETE:** Restores the port to its default breakout mode.

**Limitations:**
- Only a single group (index 0) is supported.
- The `num-physical-channels` leaf in the config is marked as `not-supported` in the deviation module since it is derived from the breakout mode.

### 3.3.4 REST API Support
#### 3.3.4.1 GET Operations
Supported at various levels (read-only):
- Component list level: `/openconfig-platform:components`
- Individual component level: `/openconfig-platform:components/component={name}`
- Specific state information: `/openconfig-platform:components/component={name}/state/{leaf}`

Sample GET output for chassis component:
```json
{
  "openconfig-platform:component": [
    {
      "config": {
        "name": "chassis 1"
      },
      "name": "chassis 1",
      "state": {
        "description": "Chassis component",
        "empty": false,
        "hardware-version": "0.20",
        "model-name": "8102-64H-O",
        "name": "chassis 1",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "removable": false,
        "serial-no": "CSNH5T5PHAE",
        "type": "openconfig-platform-types:CHASSIS"
      }
    }
  ]
}

```

Sample GET output for CPU component with utilization:
```json
{
  "openconfig-platform:component": [
    {
      "config": {
        "name": "CPU0"
      },
      "cpu": {
        "openconfig-platform-cpu:utilization": {
          "state": {
            "avg": 8,
            "instant": 1,
            "interval": "60000000000",
            "max": 19,
            "min": 1
          }
        }
      },
      "name": "CPU0",
      "state": {
        "description": "GenuineIntel: VXR",
        "empty": false,
        "mfg-name": "GenuineIntel",
        "model-name": "VXR",
        "name": "CPU0",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "removable": false,
        "type": "openconfig-platform-types:CPU"
      }
    }
  ]
}
```

Sample GET output for PSU component:
```json
{
  "openconfig-platform:component": [
    {
      "config": {
        "name": "PSU 1"
      },
      "name": "PSU 1",
      "power-supply": {
        "state": {
          "openconfig-platform-psu:enabled": false
        }
      },
      "state": {
        "description": "PSU 1",
        "empty": true,
        "location": "1",
        "name": "PSU 1",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "parent": "chassis 1",
        "removable": true,
        "type": "openconfig-platform-types:POWER_SUPPLY"
      }
    }
  ]
}
```

Sample GET output for Temperature sensor:
```json
{
  "openconfig-platform:component": [
    {
      "config": {
        "name": "NPU0_TEMP_0"
      },
      "name": "NPU0_TEMP_0",
      "state": {
        "description": "Temperature Sensor - NPU0_TEMP_0",
        "empty": false,
        "location": "23",
        "name": "NPU0_TEMP_0",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "parent": "chassis 1",
        "removable": false,
        "temperature": {
          "alarm-status": false,
          "instant": "35",
          "max": "35",
          "min": "0",
          "openconfig-platform-ext:critical-high-threshold": "102",
          "openconfig-platform-ext:critical-low-threshold": "-10"
        },
        "type": "openconfig-platform-types:SENSOR"
      }
    }
  ]
}
```

Sample GET output for Transceiver component:
```json
{
  "openconfig-platform:component": [
    {
      "config": {
        "name": "Ethernet0"
      },
      "name": "Ethernet0",
      "openconfig-platform-transceiver:transceiver": {
        "state": {
          "date-code": "2017-08-27",
          "enabled": true,
          "form-factor": "openconfig-transport-types:QSFP28",
          "form-factor-preconf": "openconfig-transport-types:QSFP28",
          "present": "PRESENT",
          "serial-no": "APF21340584-A",
          "vendor-rev": "A"
        },
        "thresholds": {
          "threshold": [
            {
              "severity": "openconfig-alarm-types:CRITICAL",
              "state": {
                "input-power-lower": "0",
                "input-power-upper": "0",
                "laser-bias-current-lower": "0",
                "laser-bias-current-upper": "0",
                "module-temperature-lower": "0",
                "module-temperature-upper": "0",
                "output-power-lower": "0",
                "output-power-upper": "0",
                "severity": "openconfig-alarm-types:CRITICAL",
                "supply-voltage-lower": "0",
                "supply-voltage-upper": "0"
              }
            },
            {
              "severity": "openconfig-alarm-types:WARNING",
              "state": {
                "input-power-lower": "0",
                "input-power-upper": "0",
                "laser-bias-current-lower": "0",
                "laser-bias-current-upper": "0",
                "module-temperature-lower": "0",
                "module-temperature-upper": "0",
                "output-power-lower": "0",
                "output-power-upper": "0",
                "severity": "openconfig-alarm-types:WARNING",
                "supply-voltage-lower": "0",
                "supply-voltage-upper": "0"
              }
            }
          ]
        }
      },
      "state": {
        "description": "Transceiver Ethernet0 - Type: QSFP28 or later",
        "empty": false,
        "mfg-name": "CISCO-AMPHENOL",
        "model-name": "NDAAFF-C401",
        "name": "Ethernet0",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "removable": true,
        "serial-no": "APF21340584-A",
        "type": "openconfig-platform-types:TRANSCEIVER"
      }
    }
  ]
}
```

#### 3.3.4.2 SET Operations
Set operations are **not supported** for platform component state paths. All component state data is read-only information sourced from STATE DB tables.

**Exception - Port Breakout-Mode:** PATCH and DELETE operations are supported on the port breakout-mode configuration path for Dynamic Port Breakout:
- `PATCH /openconfig-platform:components/component={name}/port/breakout-mode` — Triggers DPB with the specified breakout configuration.
- `DELETE /openconfig-platform:components/component={name}/port/breakout-mode` — Restores the port to its default breakout mode.

### 3.3.5 gNMI Support
#### 3.3.5.1 Capabilities
The gNMI server exposes platform component capabilities through the standard capabilities RPC.

#### 3.3.5.2 Get Operations
Full support for gNMI Get operations on all supported platform component paths.

#### 3.3.5.3 Set Operations
gNMI Set operations are **not supported** for platform component state paths. All component state data is read-only information.

**Exception - Port Breakout-Mode:** gNMI Set (update/delete) operations are supported on the port breakout-mode path for Dynamic Port Breakout, same as REST SET operations described above.

#### 3.3.5.4 Subscribe Operations
Support for gNMI Subscribe operations for real-time monitoring of:
- Temperature readings
- CPU utilization
- Fan speeds
- Power supply status
- Transceiver DOM data

- Example for Power supply oper-status subscribe on-change stream mode

```json
{
  "source": "172.29.93.21:27117",
  "subscription-name": "default-1758089936",
  "timestamp": 1758089932057031339,
  "time": "2025-09-17T11:48:52.057031339+05:30",
  "prefix": "openconfig-platform:components/component[name=PSU 1]/state",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "oper-status",
      "values": {
        "oper-status": "INACTIVE"
      }
    }
  ]
}

{
  "sync-response": true
}

{
  "source": "172.29.93.21:27117",
  "subscription-name": "default-1758089936",
  "timestamp": 1758089943763134718,
  "time": "2025-09-17T11:49:03.763134718+05:30",
  "prefix": "openconfig-platform:components/component[name=PSU 1]/state",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "oper-status",
      "values": {
        "oper-status": "ACTIVE"
      }
    }
  ]
}
```

#### 3.3.5.5 Wildcard Subscription Support

The platform module supports wildcard (`*`) subscriptions, allowing clients to subscribe to all instances of a component type without enumerating individual keys.

**Some example supported wildcard xpaths:**

| Wildcard Path | Description |
|---|---|
| `/components/component[name=*.fan*]` | All fan components |
| `/components/component[name=PSU *]` | All power supply units |
| `/components/component[name=TEMPERATURE:*]` | All temperature sensors |

## 3.4 Implementation Details
### 3.4.1 Component Type Detection
Component types are determined based on YANG key patterns:

| Key Pattern | Component Type | Example Keys |
|-------------|----------------|--------------|
| "chassis *" | Chassis | "chassis 1" |
| "CPU*" | CPU | "CPU0", "CPU1" |
| "System Eeprom" | EEPROM | "System Eeprom" |
| "PSU*" | PSU | "PSU 1", "PSU 2" |
| "fantray\*.fan\*" or "PSU\*.fan\*" | Fan | "fantray1.fan1", "PSU1.fan1" |
| "fantray*" | Fantray | "fantray1", "fantray2" |
| "Ethernet*" (state paths) | Transceiver | "Ethernet0", "Ethernet4" |
| "Ethernet*" (breakout-mode path) | Port | "Ethernet0", "Ethernet4" |
| Others | Temperature | "temp1", "cpu-thermal", "NPU0_TEMP_0" |

### 3.4.2 Error Handling
- Graceful handling of missing components
- Appropriate error responses for unsupported operations
- Validation of component types and availability
- Database connection error handling
- Data conversion error handling

# 4 Testing
## 4.1 Unit Tests
Comprehensive unit tests covering:
- Individual component type functionality validation
- Database interaction and data retrieval verification
- Error condition handling and edge cases
- Data transformation and format validation
- Component type detection logic
- OpenConfig YANG path mapping verification

## 4.2 Integration Tests
- REST API endpoint testing
- gNMI operations validation
- End-to-end platform monitoring scenarios

# 5 Limitations
1. Platform component state is read-only (monitoring only); only port breakout-mode supports Set operations
2. Platform-specific component availability depends on hardware support
3. Real-time data accuracy depends on underlying platform drivers
4. Port breakout-mode supports only a single group (index 0)

# 6 Future Enhancements
1. Support for additional component types as they become available
2. Configuration support for configurable platform components

# 7 References
1. [OpenConfig Platform YANG Models](https://github.com/openconfig/public/tree/master/release/models/platform)
2. [SONiC Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)
3. [OpenConfig gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
