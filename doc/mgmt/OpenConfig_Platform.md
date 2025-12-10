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
  * [Table 3: Memory Information Mapping](#memory-information-mapping) 
  * [Table 4: Temperature Information Mapping](#temperature-information-mapping) 
  * [Table 5: Power Supply Information Mapping](#power-supply-information-mapping) 
  * [Table 6: Fan Information Mapping](#fan-information-mapping) 
  * [Table 7: CPU Information Mapping](#cpu-information-mapping) 
  * [Table 8: Transceiver Information Mapping](#transceiver-information-mapping) 
  * [Table 9: Component Type to DB Table Mapping](#component-type-to-db-table-mapping) 
  * [Table 10: Transceiver Threshold Field Mapping](#334-transceiver-threshold-field-mapping) 

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 08/24/2025  | Anukul Verma | Initial version                   |
| 0.2 | 12/10/2025  | Neha Das | Added integrated-circuit and PCIE components   |

# About this Manual
This document provides general information about the OpenConfig configuration/management of Platform components in SONiC corresponding to openconfig-platform.yang module and its sub-modules.

# Scope
- This document describes the high level design of OpenConfig configuration/management of Platform components via gNMI/REST in SONiC.
- This does not cover the SONiC KLISH CLI.
- Openconfig-platform.yang version latest from openconfig yang repo is considered.
- Currently only EEPROM component is supported using Custom app approach (pfm_app.go). New implementation will be done using common app approach.
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
        |  |  +--ro alarm-threshold?   uint32
        |  +--ro memory
        |     +--ro available?   uint64
        |     +--ro utilized?    uint64
        |  +--ro pcie
        |     +--ro fatal-errors
        |        +--ro total-errors?                   oc-yang:counter64 
        |        +--ro undefined-errors?               oc-yang:counter64
        |        +--ro data-link-errors?               oc-yang:counter64
        |        +--ro surprise-down-errors?           oc-yang:counter64
        |        +--ro poisoned-tlp-errors?            oc-yang:counter64
        |        +--ro flow-control-protocol-errors?   oc-yang:counter64
        |        +--ro completion-timeout-errors?      oc-yang:counter64
        |        +--ro completion-abort-errors?        oc-yang:counter64
        |        +--ro unexpected-completion-errors?   oc-yang:counter64
        |        +--ro receiver-overflow-errors?       oc-yang:counter64
        |        +--ro malformed-tlp-errors?           oc-yang:counter64
        |        +--ro ecrc-errors?                    oc-yang:counter64
        |        +--ro unsupported-request-errors?     oc-yang:counter64
        |        +--ro acs-violation-errors?           oc-yang:counter64
        |        +--ro internal-errors?                oc-yang:counter64
        |        +--ro blocked-tlp-errors?             oc-yang:counter64
        |        +--ro atomic-op-blocked-errors?       oc-yang:counter64
        |        +--ro tlp-prefix-blocked-errors?      oc-yang:counter64
        |     +--ro non-fatal-errors?
        |        +--ro total-errors?                   oc-yang:counter64 
        |        +--ro undefined-errors?               oc-yang:counter64
        |        +--ro data-link-errors?               oc-yang:counter64
        |        +--ro surprise-down-errors?           oc-yang:counter64
        |        +--ro poisoned-tlp-errors?            oc-yang:counter64
        |        +--ro flow-control-protocol-errors?   oc-yang:counter64
        |        +--ro completion-timeout-errors?      oc-yang:counter64
        |        +--ro completion-abort-errors?        oc-yang:counter64
        |        +--ro unexpected-completion-errors?   oc-yang:counter64
        |        +--ro receiver-overflow-errors?       oc-yang:counter64
        |        +--ro malformed-tlp-errors?           oc-yang:counter64
        |        +--ro ecrc-errors?                    oc-yang:counter64
        |        +--ro unsupported-request-errors?     oc-yang:counter64
        |        +--ro acs-violation-errors?           oc-yang:counter64
        |        +--ro internal-errors?                oc-yang:counter64
        |        +--ro blocked-tlp-errors?             oc-yang:counter64
        |        +--ro atomic-op-blocked-errors?       oc-yang:counter64
        |        +--ro tlp-prefix-blocked-errors?      oc-yang:counter64
        |     +--ro correctable-errors?
        |        +--ro total-errors?                   oc-yang:counter64 
        |        +--ro receiver-errors?                oc-yang:counter64
        |        +--ro bad-tlp-errors?                 oc-yang:counter64
        |        +--ro bad-dllp-errors?                oc-yang:counter64
        |        +--ro relay-rollover-errors?          oc-yang:counter64
        |        +--ro replay-timeout-errors?          oc-yang:counter64
        |        +--ro advisory-non-fatal-errors?      oc-yang:counter64
        |        +--ro internal-errors?                oc-yang:counter64
        |        +--ro hdr-log-overflow-errors?        oc-yang:counter64
        +--rw power-supply
        |  +--ro state
        |     +--ro oc-platform-psu:enabled?    boolean
        |     +--ro oc-platform-psu:capacity?   oc-types:ieeefloat32
        +--rw fan
        |  +--ro state
        |     +--ro oc-fan:speed?   uint32
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
           |     +--ro oc-transceiver:avg?        decimal64
           |     +--ro oc-transceiver:min?        decimal64
           |     +--ro oc-transceiver:max?        decimal64
           |     +--ro oc-transceiver:interval?   oc-types:stat-interval
           |     +--ro oc-transceiver:min-time?   oc-types:timeticks64
           |     +--ro oc-transceiver:max-time?   oc-types:timeticks64
           +--rw oc-transceiver:physical-channels
           |  +--rw oc-transceiver:channel* [index]
           |     +--rw oc-transceiver:index     -> ../config/index
           |     +--ro oc-transceiver:state
           |        +--ro oc-transceiver:index?                        uint16
           |        +--ro oc-transceiver:associated-optical-channel?   -> /oc-platform:components/component/name
           |        +--ro oc-transceiver:description?                  string
           |        +--ro oc-transceiver:tx-laser?                     boolean
           |        +--ro oc-transceiver:target-output-power?          decimal64
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
                    +--ro oc-transceiver:laser-temperature-upper?    decimal64
                    +--ro oc-transceiver:laser-temperature-lower?    decimal64
                    +--ro oc-transceiver:output-power-upper?         decimal64
                    +--ro oc-transceiver:output-power-lower?         decimal64
                    +--ro oc-transceiver:input-power-upper?          decimal64
                    +--ro oc-transceiver:input-power-lower?          decimal64
                    +--ro oc-transceiver:laser-bias-current-upper?   decimal64
                    +--ro oc-transceiver:laser-bias-current-lower?   decimal64
                    +--ro oc-transceiver:supply-voltage-upper?       decimal64
                    +--ro oc-transceiver:supply-voltage-lower?       decimal64
                    +--ro oc-transceiver:module-temperature-lower?   decimal64
                    +--ro oc-transceiver:module-temperature-upper?   decimal64
        +--rw integrated-circuit
        |  +--rw config
        |     +--rw oc-p4rt:node-id                      uint64
        |  +--ro state
        |     +--rw oc-p4rt:node-id                      uint64
        |  +--ro oc-ic:memory
        |     +--ro oc-ic:state
        |        +--ro oc-ic:corrected-parity-errors?    uint64
        |        +--ro oc-ic:total-parity-errors?        uint64
        |  +--ro oc-ppc:pipeline-counters
        |     +--ro oc-ppc:drop
        |        +--ro oc-ppc:lookup-block
        |           +--ro oc-ppc:state
        |              +--ro oc-ppc:no-route?            oc-yang:counter64
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
    Configure/Set Platform component attributes.  
    Subscribe Platform component attributes for telemetry.
3. Add support for following Platform component types:
    * chassis
    * cpu
    * eeprom (System EEPROM)
    * memory (Physical, Buffer, Swap, Cached, Virtual, Shared)
    * disk
    * power-supply (PSU)
    * fan
    * fantray
    * temperature
    * transceiver
    * integrated-circuit
    * pcie
4. Support for platform component state information including:
    * Basic component information (name, type, description, manufacturer, etc.)
    * Operational status and health monitoring
    * Temperature monitoring with thresholds and alarm status
    * Memory utilization statistics
    * CPU utilization statistics
    * Power supply capacity and status
    * Fan speed monitoring
    * Transceiver information and DOM (Digital Optical Monitoring) data
    * Integrated Circuit configuration and telemetry
    * PCIE error telemetry monitoring

### 1.1.2 Configuration and Management Requirements
The Platform configuration/management can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration or un-supported node is accessed.

### 1.1.3 Scalability Requirements
The maximum number of components depends on the hardware platform capabilities and the number of physical components present in the system.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports framework for Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation for Platform features.

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
There are no changes to CONFIG DB schema definition.

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
The following existing STATE DB tables are utilized for platform component information:
- EEPROM_INFO
- MEMORY_STATS
- PHYSICAL_ENTITY_INFO
- TEMPERATURE_INFO
- TRANSCEIVER_INFO
- TRANSCEIVER_DOM_THRESHOLD
- TRANSCEIVER_DOM_SENSOR
- MOUNT_POINTS
- PSU_INFO
- FAN_INFO
- FAN_DRAWER_INFO
- CHASSIS_INFO
- CPU_STATS (new table will be added to support this)
- NODE_CFG
- NODE_INFO
- PCIE_DEVICE

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

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
- openconfig-platform-annotation.yang
- openconfig-platform-deviation.yang
- openconfig-platform-ext.yang
- openconfig-platform-integrated-circuit.yang
- openconfig-platform-pipeline-counters.yang
- openconfig-p4rt.yang (for node-id)

### 3.3.2 Database Table and Field Mapping
The following sections provide detailed mapping between OpenConfig YANG paths and SONiC STATE DB tables and fields for each component type.

#### 3.3.2.1 Chassis Component Mapping
**Database Table:** CHASSIS_INFO  
**Key Pattern:** "chassis *" (e.g., "chassis 1")  
**Component Type:** openconfig-platform-types:CHASSIS

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/type` | - | - | Fixed: CHASSIS |
| `/components/component/state/description` | - | - | Static description |
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
| `/components/component/state/description` | - | - | Static description |
| `/components/component/state/model-name` | CPU_STATS | model_name | CPU model information |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/cpu/utilization/state/instant` | CPU_STATS | load | Current CPU load |
| `/components/component/cpu/utilization/state/avg` | CPU_STATS | load | Calculated average |
| `/components/component/cpu/utilization/state/min` | CPU_STATS | load | Calculated minimum |
| `/components/component/cpu/utilization/state/max` | CPU_STATS | load | Calculated maximum |

#### 3.3.2.3 EEPROM Component Mapping
**Database Table:** EEPROM_INFO  
**Key Pattern:** "System Eeprom"  
**Component Type:** openconfig-platform-types:STORAGE

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/id` | - | - | Fixed: "System Eeprom" |
| `/components/component/state/name` | - | - | Same as id |
| `/components/component/state/type` | - | - | Fixed: STORAGE |
| `/components/component/state/description` | - | - | Static description |
| `/components/component/state/part-no` | EEPROM_INFO | 0x22 | Product part number |
| `/components/component/state/serial-no` | EEPROM_INFO | 0x23 | Serial number |
| `/components/component/state/mfg-date` | EEPROM_INFO | 0x25 | Manufacturing date |
| `/components/component/state/hardware-version` | EEPROM_INFO | 0x27 | Hardware revision |
| `/components/component/state/mfg-name` | EEPROM_INFO | 0x2b | Manufacturer name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Usually chassis |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | parent_name | Location information |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |

#### 3.3.2.4 Memory Component Mapping
**Database Table:** MEMORY_STATS  
**Key Patterns:** "*Memory" (e.g., "Physical Memory", "Buffer Memory", "Swap Memory", "Cached Memory", "Virtual Memory", "Shared Memory")  
**Component Type:** openconfig-platform-types:STORAGE

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/id` | - | Component key | Generated from memory key |
| `/components/component/state/name` | - | Component key | Same as id |
| `/components/component/state/type` | - | - | Fixed: STORAGE |
| `/components/component/state/description` | - | - | Memory type description |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/state/memory/available` | MEMORY_STATS | 1K-blocks | Available memory in bytes |
| `/components/component/state/memory/utilized` | MEMORY_STATS | Used | Used memory in bytes |

#### 3.3.2.5 Disk Component Mapping
**Database Table:** MOUNT_POINTS  
**Key Pattern:** "/" (root filesystem)  
**Component Type:** openconfig-platform-types:STORAGE

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/id` | - | - | Fixed: "Disk" |
| `/components/component/state/name` | - | - | Same as id |
| `/components/component/state/type` | - | - | Fixed: STORAGE |
| `/components/component/state/description` | - | - | Static description |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/state/memory/available` | MOUNT_POINTS | 1K-blocks | Available disk space |
| `/components/component/state/memory/utilized` | MOUNT_POINTS | Used | Used disk space |

#### 3.3.2.6 Power Supply (PSU) Component Mapping
**Database Table:** PSU_INFO  
**Key Pattern:** "PSU *" (e.g., "PSU 1", "PSU 2")  
**Component Type:** openconfig-platform-types:POWER_SUPPLY

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: POWER_SUPPLY |
| `/components/component/state/description` | - | - | PSU description |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Usually chassis |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | PSU_INFO | status | Operational status |
| `/components/component/state/empty` | - | - | Calculated from status |
| `/components/component/state/removable` | - | - | Fixed: true |
| `/components/component/power-supply/state/capacity` | PSU_INFO | max_power | Maximum power capacity |
| `/components/component/power-supply/state/enabled` | PSU_INFO | status | PSU enabled status |

#### 3.3.2.7 Fan Component Mapping
**Database Table:** FAN_INFO  
**Key Pattern:** "*fan*" (e.g., "fan1", "PSU1.fan1")  
**Component Type:** openconfig-platform-types:FAN

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: FAN |
| `/components/component/state/description` | - | - | Fan description |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | FAN_INFO | status | Operational status |
| `/components/component/state/empty` | - | - | Calculated from status |
| `/components/component/state/removable` | - | - | Fixed: true |
| `/components/component/fan/state/speed` | FAN_INFO | speed | Fan speed in RPM |

#### 3.3.2.8 Fan Tray Component Mapping
**Database Table:** FAN_DRAWER_INFO  
**Key Pattern:** "fantray*" (e.g., "fantray1", "fantray2")  
**Component Type:** openconfig-platform-types:FAN

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: FANTRAY |
| `/components/component/state/description` | - | - | Fan tray description |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Usually chassis |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | FAN_DRAWER_INFO | status | Operational status |
| `/components/component/state/empty` | - | - | Calculated from status |
| `/components/component/state/removable` | - | - | Fixed: true |

#### 3.3.2.9 Temperature Component Mapping
**Database Table:** TEMPERATURE_INFO  
**Key Pattern:** Various sensor names (e.g., "temp1", "cpu-thermal", "NPU0_TEMP_0")  
**Component Type:** openconfig-platform-types:SENSOR

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: SENSOR |
| `/components/component/state/description` | - | - | Temperature sensor description |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | - | - | Fixed: ACTIVE |
| `/components/component/state/empty` | - | - | Fixed: false |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/state/temperature/instant` | TEMPERATURE_INFO | temperature | Current temperature |
| `/components/component/state/temperature/min` | TEMPERATURE_INFO | minimum_temperature | Minimum temperature |
| `/components/component/state/temperature/max` | TEMPERATURE_INFO | maximum_temperature | Maximum temperature |
| `/components/component/state/temperature/alarm-status` | TEMPERATURE_INFO | warning_status | Temperature alarm status |
| `/components/component/state/temperature/alarm-threshold` | TEMPERATURE_INFO | critical_high_threshold | Critical threshold |

#### 3.3.2.10 Transceiver Component Mapping
**Database Tables:** TRANSCEIVER_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_DOM_THRESHOLD  
**Key Pattern:** "Ethernet*" (e.g., "Ethernet0", "Ethernet1/1")  
**Component Type:** openconfig-platform-types:TRANSCEIVER

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/name` | - | Component key | Name |
| `/components/component/state/type` | - | - | Fixed: TRANSCEIVER |
| `/components/component/state/description` | - | - | Transceiver description |
| `/components/component/state/serial-no` | TRANSCEIVER_INFO | serial | Serial number |
| `/components/component/state/hardware-version` | TRANSCEIVER_INFO | hardware_rev | Hardware revision |
| `/components/component/state/mfg-name` | TRANSCEIVER_INFO | manufacturer | Manufacturer name |
| `/components/component/state/model-name` | TRANSCEIVER_INFO | model | Model name |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | position_in_parent | Location information |
| `/components/component/state/oper-status` | TRANSCEIVER_INFO | presence | Operational status |
| `/components/component/state/empty` | TRANSCEIVER_INFO | presence | Calculated from presence |
| `/components/component/state/removable` | - | - | Fixed: true |

##### Transceiver State Information

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/transceiver/state/enabled` | TRANSCEIVER_INFO | presence | Enabled status |
| `/transceiver/state/form-factor-preconf` | TRANSCEIVER_INFO | ext_identifier | Pre-configured form factor |
| `/transceiver/state/present` | TRANSCEIVER_INFO | presence | Presence status |
| `/transceiver/state/form-factor` | TRANSCEIVER_INFO | ext_identifier | Current form factor |
| `/transceiver/state/connector-type` | TRANSCEIVER_INFO | connector | Connector type |
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

#### 3.3.2.11 Integrated-Circuit Component Mapping
**Database Table:** NODE_CFG and NODE_INFO  
**Key Pattern:** "integrated_circuit*" (e.g., "integrated_circuit0")  
**Component Type:** openconfig-platform-types:INTEGRATED_CIRCUIT

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/components/component/state/type` | - | - | Fixed: INTEGRATED_CIRCUIT |
| `/components/component/state/description` | - | - | Static description |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | Parent component |
| `/components/component/state/removable` | - | - | Fixed: false |
| `/components/component/integrated-circuit/config/node-id` | NODE_CFG | node-id | Device ID |
| `/components/component/integrated-circuit/state/node-id` | NODE_INFO | node-id | Device ID |
| `/components/component/memory/state/corrected-parity-errors` |  |  |  |
| `/components/component/memory/state/total-parity-errors` |  |  |  |

### 3.3.4 REST API Support
#### 3.3.4.1 GET Operations
Supported at various levels:
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

Sample GET output for Memory component:
```json
{
  "openconfig-platform:components/component": {
    "openconfig-platform:component": [
      {
        "config": {
          "name": "Physical Memory"
        },
        "name": "Physical Memory",
        "state": {
          "description": "Physical Memory",
          "empty": false,
          "memory": {
            "available": "20014612",
            "utilized": "6550668"
          },
          "name": "Physical Memory",
          "oper-status": "openconfig-platform-types:ACTIVE",
          "type": "openconfig-platform-types:STORAGE"
        }
      }
    ]
  }
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
          "alarm-threshold": 102,
          "instant": "35",
          "max": "35",
          "min": "0"
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

### 3.3.5 gNMI Support
#### 3.3.5.1 Capabilities
The gNMI server exposes platform component capabilities through the standard capabilities RPC.

#### 3.3.5.2 Get Operations
Full support for gNMI Get operations on all supported platform component paths.

#### 3.3.5.3 Subscribe Operations
Support for gNMI Subscribe operations for real-time monitoring of:
- Temperature readings
- CPU utilization
- Memory usage
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
## 3.4 Implementation Details
### 3.4.1 Component Type Detection
Component types are determined based on YANG key patterns:

| Key Pattern | Component Type | Example Keys |
|-------------|----------------|--------------|
| "chassis *" | Chassis | "chassis 1" |
| "CPU*" | CPU | "CPU0", "CPU1" |
| "System Eeprom" | EEPROM | "System Eeprom" |
| "*Memory" | Memory | "Physical Memory", "Buffer Memory", "Swap Memory", "Cached Memory", "Virtual Memory", "Shared Memory" |
| "/" | Disk | "/dev/vda3" |
| "PSU *" | PSU | "PSU 1", "PSU 2" |
| "*fan*" | Fan | "fan1", "PSU1.fan1" |
| "fantray*" | Fantray | "fantray1", "fantray2" |
| "Ethernet*" | Transceiver | "Ethernet0", "Ethernet4" |
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
1. Read-only operations - platform components are primarily for monitoring
2. Platform-specific component availability depends on hardware support
3. Real-time data accuracy depends on underlying platform drivers

# 6 Future Enhancements
1. Support for additional component types as they become available
2. Configuration support for configurable platform components

# 7 References
1. [OpenConfig Platform YANG Models](https://github.com/openconfig/public/tree/master/release/models/platform)
2. [SONiC Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)
3. [OpenConfig gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
