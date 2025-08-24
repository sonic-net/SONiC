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
[Table 1: Abbreviations](#table-1-abbreviations) 
[Table 2: Component Basic Information Mapping](#component-basic-information-mapping) 
[Table 3: Memory Information Mapping](#memory-information-mapping) 
[Table 4: Temperature Information Mapping](#temperature-information-mapping) 
[Table 5: Power Supply Information Mapping](#power-supply-information-mapping) 
[Table 6: Fan Information Mapping](#fan-information-mapping) 
[Table 7: CPU Information Mapping](#cpu-information-mapping) 
[Table 8: Transceiver Information Mapping](#transceiver-information-mapping) 
[Table 9: Component Type to DB Table Mapping](#component-type-to-db-table-mapping) 
[Table 10: Transceiver Threshold Field Mapping](#334-transceiver-threshold-field-mapping) 

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 08/24/2025  | Anukul Verma | Initial version                   |

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
        +--rw name
        +--rw config
        |  +--rw name?
        +--ro state
        |  +--ro name?
        |  +--ro type?
        |  +--ro id?
        |  +--ro description?
        |  +--ro mfg-name?
        |  +--ro mfg-date?
        |  +--ro hardware-version?
        |  +--ro firmware-version?
        |  +--ro software-version?
        |  +--ro serial-no?
        |  +--ro part-no?
        |  +--ro oper-status?
        |  +--ro parent?
        |  +--ro location?
        |  +--ro removable?
        |  +--ro empty?
        |  +--ro memory
        |  |  +--ro available?
        |  |  +--ro utilized?
        |  +--ro temperature
        |     +--ro instant?
        |     +--ro avg?
        |     +--ro min?
        |     +--ro max?
        |     +--ro interval?
        |     +--ro min-time?
        |     +--ro max-time?
        |     +--ro alarm-status?
        |     +--ro alarm-threshold?
        +--rw chassis
        +--rw power-supply
        |  +--ro state
        |     +--ro capacity?
        |     +--ro enabled?
        +--rw fan
        |  +--ro state
        |     +--ro speed?
        +--rw cpu
        |  +--ro utilization
        |     +--ro state
        |        +--ro instant?
        |        +--ro avg?
        |        +--ro min?
        |        +--ro max?
        |        +--ro interval?
        |        +--ro min-time?
        |        +--ro max-time?
        +--rw openconfig-platform-transceiver:transceiver
           +--ro state
           |  +--ro enabled?
           |  +--ro form-factor-preconf?
           |  +--ro present?
           |  +--ro form-factor?
           |  +--ro connector-type?
           |  +--ro vendor-rev?
           |  +--ro serial-no?
           |  +--ro date-code?
           |  +--ro supply-voltage
           |     +--ro instant?
           +--ro thresholds
           |  +--ro threshold* [threshold-type]
           |     +--ro threshold-type
           |     +--ro state
           |        +--ro threshold-type?
           |        +--ro upper-critical?
           |        +--ro upper-warning?
           |        +--ro lower-warning?
           |        +--ro lower-critical?
           +--ro physical-channels
              +--ro channel* [index]
                 +--ro index
                 +--ro state
                 |  +--ro index?
                 |  +--ro description?
                 |  +--ro tx-laser?
                 |  +--ro output-power
                 |  |  +--ro instant?
                 |  |  +--ro avg?
                 |  |  +--ro min?
                 |  |  +--ro max?
                 |  |  +--ro interval?
                 |  |  +--ro min-time?
                 |  |  +--ro max-time?
                 |  +--ro input-power
                 |  |  +--ro instant?
                 |  |  +--ro avg?
                 |  |  +--ro min?
                 |  |  +--ro max?
                 |  |  +--ro interval?
                 |  |  +--ro min-time?
                 |  |  +--ro max-time?
                 |  +--ro laser-bias-current
                 |     +--ro instant?
                 |     +--ro avg?
                 |     +--ro min?
                 |     +--ro max?
                 |     +--ro interval?
                 |     +--ro min-time?
                 |     +--ro max-time?
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
4. Support for platform component state information including:
    * Basic component information (name, type, description, manufacturer, etc.)
    * Operational status and health monitoring
    * Temperature monitoring with thresholds and alarm status
    * Memory utilization statistics
    * CPU utilization statistics
    * Power supply capacity and status
    * Fan speed monitoring
    * Transceiver information and DOM (Digital Optical Monitoring) data

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
- CPU_STATS (new table will be added to support this)

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

### 3.3.2 Database Table and Field Mapping
The following table shows the mapping between OpenConfig YANG paths and SONiC STATE DB tables and fields:

#### 3.3.2.1 Component Basic Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/id` | - | - | All |
| `/components/component/state/part-no` | EEPROM_INFO | 0x22 | Chassis/EEPROM |
| `/components/component/state/serial-no` | EEPROM_INFO, TRANSCEIVER_INFO | 0x23, serial | Chassis/EEPROM, Transceiver |
| `/components/component/state/mfg-date` | EEPROM_INFO | 0x25 | Chassis/EEPROM |
| `/components/component/state/hardware-version` | EEPROM_INFO, TRANSCEIVER_INFO | 0x27, hardware_rev | Chassis/EEPROM, Transceiver |
| `/components/component/state/description` | - | - | All |
| `/components/component/state/mfg-name` | EEPROM_INFO, TRANSCEIVER_INFO | 0x2b, manufacturer | Chassis/EEPROM, Transceiver |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | parent_name | All |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | All |
| `/components/component/state/empty` | - | - | All |
| `/components/component/state/removable` | - | - | All |
| `/components/component/state/oper-status` | PSU_INFO, FAN_INFO, TRANSCEIVER_INFO | status, presence | PSU, Fan, Transceiver |
| `/components/component/state/type` | - | - | All |
| `/components/component/state/model-name` | CPU_STATS, TRANSCEIVER_INFO | model_name, model | CPU, Transceiver |

#### 3.3.2.2 Memory Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/memory/available` | MEMORY_STATS, MOUNT_POINTS | 1K-blocks | Memory, Disk |
| `/components/component/state/memory/utilized` | MEMORY_STATS, MOUNT_POINTS | Used | Memory, Disk |

#### 3.3.2.3 Temperature Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/temperature/instant` | TEMPERATURE_INFO | temperature | Temperature |
| `/components/component/state/temperature/min` | TEMPERATURE_INFO | minimum_temperature | Temperature |
| `/components/component/state/temperature/max` | TEMPERATURE_INFO | maximum_temperature | Temperature |
| `/components/component/state/temperature/alarm-status` | TEMPERATURE_INFO | warning_status | Temperature |
| `/components/component/state/temperature/alarm-threshold` | TEMPERATURE_INFO | critical_high_threshold | Temperature |

#### 3.3.2.4 Power Supply Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/power-supply/state/capacity` | PSU_INFO | max_power | PSU |
| `/components/component/power-supply/state/enabled` | PSU_INFO | status | PSU |

#### 3.3.2.5 Fan Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/fan/state/speed` | FAN_INFO | speed | Fan |

#### 3.3.2.6 CPU Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/cpu/utilization/state/instant` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/avg` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/min` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/max` | CPU_STATS | load | CPU |

#### 3.3.2.7 Transceiver Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/transceiver/state/enabled` | TRANSCEIVER_INFO | presence | Transceiver |
| `/transceiver/state/form-factor-preconf` | TRANSCEIVER_INFO | ext_identifier | Transceiver |
| `/transceiver/state/present` | TRANSCEIVER_INFO | presence | Transceiver |
| `/transceiver/state/form-factor` | TRANSCEIVER_INFO | ext_identifier | Transceiver |
| `/transceiver/state/connector-type` | TRANSCEIVER_INFO | connector | Transceiver |
| `/transceiver/state/vendor-rev` | TRANSCEIVER_INFO | vendor_rev | Transceiver |
| `/transceiver/state/serial-no` | TRANSCEIVER_INFO | serial | Transceiver |
| `/transceiver/state/date-code` | TRANSCEIVER_INFO | vendor_date | Transceiver |
| `/transceiver/state/supply-voltage/instant` | TRANSCEIVER_DOM_SENSOR | voltage | Transceiver |
| `/transceiver/thresholds` | TRANSCEIVER_DOM_THRESHOLD | Various threshold fields | Transceiver |
| `/transceiver/physical-channels` | TRANSCEIVER_DOM_SENSOR | rx power, tx power, tx bias | Transceiver |

### 3.3.3 Component Type to DB Table Mapping

| Component Type | Primary DB Tables | Key Pattern | Description |
|---------------|------------------|-------------|-------------|
| Chassis | EEPROM_INFO, CHASSIS_INFO | "chassis *" | Main chassis component |
| CPU | CPU_STATS | "CPU*" | CPU components |
| EEPROM | EEPROM_INFO | "System Eeprom" | System EEPROM information |
| Memory | MEMORY_STATS | "*Memory" | Memory components (Physical, Buffer, Swap, etc.) |
| Disk | MOUNT_POINTS | "/" | Disk/storage components |
| PSU | PSU_INFO | "PSU *" | Power supply units |
| Fan | FAN_INFO | "*fan*" | Fan components |
| Fantray | FAN_DRAWER_INFO | "fantray*" | Fan tray components |
| Temperature | TEMPERATURE_INFO | Various sensor names | Temperature sensors |
| Transceiver | TRANSCEIVER_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_DOM_THRESHOLD | "Ethernet*" | Transceiver modules |

### 3.3.4 Transceiver Threshold Field Mapping

| Threshold Type | Critical High | Critical Low | Warning High | Warning Low |
|---------------|---------------|--------------|--------------|-------------|
| Output Power | txpowerhighalarm | txpowerlowalarm | txpowerhighwarning | txpowerlowwarning |
| Input Power | rxpowerhighalarm | rxpowerlowalarm | rxpowerhighwarning | rxpowerlowwarning |
| Laser Bias Current | txbiashighalarm | txbiaslowalarm | txbiashighwarning | txbiaslowwarning |
| Supply Voltage | vcchighalarm | vcclowalarm | vcchighwarning | vcclowwarning |
| Temperature | temphighalarm | templowalarm | temphighwarning | templowwarning |

### 3.3.5 REST API Support
#### 3.3.5.1 GET Operations
Supported at various levels:
- Component list level: `/openconfig-platform:components`
- Individual component level: `/openconfig-platform:components/component={name}`
- Specific state information: `/openconfig-platform:components/component={name}/state/{leaf}`

Sample GET output for chassis component:
```json
{
  "openconfig-platform:component": [
    {
      "name": "Chassis",
      "state": {
        "name": "Chassis",
        "type": "openconfig-platform-types:CHASSIS",
        "description": "Main chassis component",
        "mfg-name": "Cisco",
        "part-no": "73-18971-01",
        "serial-no": "CAT2242L0CG",
        "mfg-date": "12/09/2021 20:08:48",
        "hardware-version": "1.0",
        "oper-status": "openconfig-platform-types:ACTIVE"
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
      "name": "CPU0",
      "state": {
        "name": "CPU0",
        "type": "openconfig-platform-types:CPU",
        "model-name": "Intel(R) Xeon(R) CPU E5-2680 v3"
      },
      "cpu": {
        "utilization": {
          "state": {
            "instant": 25,
            "avg": 30,
            "min": 10,
            "max": 80
          }
        }
      }
    }
  ]
}
```

Sample GET output for Memory component:
```json
{
  "openconfig-platform:component": [
    {
      "name": "Physical Memory",
      "state": {
        "name": "Physical Memory",
        "type": "openconfig-platform-types:STORAGE",
        "description": "Physical Memory component",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "memory": {
          "available": 8192000,
          "utilized": 2048000
        }
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
      "name": "PSU 1",
      "state": {
        "name": "PSU 1",
        "type": "openconfig-platform-types:POWER_SUPPLY",
        "description": "Power Supply Unit 1",
        "oper-status": "openconfig-platform-types:ACTIVE"
      },
      "power-supply": {
        "state": {
          "capacity": 1200.0,
          "enabled": true
        }
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
      "name": "temp1",
      "state": {
        "name": "temp1",
        "type": "openconfig-platform-types:SENSOR",
        "description": "Temperature sensor 1",
        "oper-status": "openconfig-platform-types:ACTIVE",
        "temperature": {
          "instant": 45.5,
          "min": 22.0,
          "max": 65.0,
          "alarm-status": false,
          "alarm-threshold": 85.0
        }
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
      "name": "Ethernet0",
      "state": {
        "name": "Ethernet0",
        "type": "openconfig-platform-types:TRANSCEIVER",
        "description": "Ethernet0 transceiver",
        "mfg-name": "Cisco",
        "part-no": "SFP-10G-SR",
        "serial-no": "ABC123456",
        "oper-status": "openconfig-platform-types:ACTIVE"
      },
      "openconfig-platform-transceiver:transceiver": {
        "state": {
          "enabled": true,
          "present": "PRESENT",
          "form-factor": "QSFP28",
          "connector-type": "LC_CONNECTOR",
          "vendor-rev": "1.0",
          "serial-no": "ABC123456",
          "date-code": "210405",
          "supply-voltage": {
            "instant": 3.3
          }
        }
      }
    }
  ]
}
```

### 3.3.6 gNMI Support
#### 3.3.6.1 Capabilities
The gNMI server exposes platform component capabilities through the standard capabilities RPC.

#### 3.3.6.2 Get Operations
Full support for gNMI Get operations on all supported platform component paths.

#### 3.3.6.3 Subscribe Operations
Support for gNMI Subscribe operations for real-time monitoring of:
- Temperature readings
- CPU utilization
- Memory usage
- Fan speeds
- Power supply status
- Transceiver DOM data

## 3.4 Implementation Details
### 3.4.1 Component Type Detection
Component types are determined based on YANG key patterns:

| Key Pattern | Component Type | Example Keys |
|-------------|----------------|--------------|
| "chassis *" | Chassis | "Chassis" |
| "CPU*" | CPU | "CPU0", "CPU1" |
| "System Eeprom" | EEPROM | "System Eeprom" |
| "*Memory" | Memory | "Physical Memory", "Buffer Memory" |
| "/" | Disk | "/" |
| "PSU *" | PSU | "PSU 1", "PSU 2" |
| "*fan*" | Fan | "fan1", "PSU1.fan1" |
| "fantray*" | Fantray | "fantray1", "fantray2" |
| "Ethernet*" | Transceiver | "Ethernet0", "Ethernet1/1" |
| Others | Temperature | "temp1", "cpu-thermal" |

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
