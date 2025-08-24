# OpenConfig support for Platform features

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 08/24/2025  | Anukul Verma | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration/management of Platform features in SONiC corresponding to openconfig-platform.yang module and its sub-modules.

# Scope
- This document describes the high level design of OpenConfig configuration/management of Platform features via gNMI/REST in SONiC.
- This does not cover the SONiC KLISH CLI.
- Openconfig-platform.yang version latest from openconfig yang repo is considered.
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
           +--ro physical-channels
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
- CPU_STATS

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

### 3.3.2 Supported XPaths
The following OpenConfig XPaths are supported for platform components:

#### 3.3.2.1 Component Container
- `/openconfig-platform:components`
- `/openconfig-platform:components/component={name}`
- `/openconfig-platform:components/component={name}/config`
- `/openconfig-platform:components/component={name}/config/name`

#### 3.3.2.2 Component State Information
- `/openconfig-platform:components/component={name}/state`
- `/openconfig-platform:components/component={name}/state/name`
- `/openconfig-platform:components/component={name}/state/type`
- `/openconfig-platform:components/component={name}/state/id`
- `/openconfig-platform:components/component={name}/state/description`
- `/openconfig-platform:components/component={name}/state/mfg-name`
- `/openconfig-platform:components/component={name}/state/mfg-date`
- `/openconfig-platform:components/component={name}/state/hardware-version`
- `/openconfig-platform:components/component={name}/state/serial-no`
- `/openconfig-platform:components/component={name}/state/part-no`
- `/openconfig-platform:components/component={name}/state/oper-status`
- `/openconfig-platform:components/component={name}/state/parent`
- `/openconfig-platform:components/component={name}/state/location`
- `/openconfig-platform:components/component={name}/state/removable`
- `/openconfig-platform:components/component={name}/state/empty`
- `/openconfig-platform:components/component={name}/state/model-name`

#### 3.3.2.3 Memory Information
- `/openconfig-platform:components/component={name}/state/memory`
- `/openconfig-platform:components/component={name}/state/memory/available`
- `/openconfig-platform:components/component={name}/state/memory/utilized`

#### 3.3.2.4 Temperature Information
- `/openconfig-platform:components/component={name}/state/temperature`
- `/openconfig-platform:components/component={name}/state/temperature/instant`
- `/openconfig-platform:components/component={name}/state/temperature/min`
- `/openconfig-platform:components/component={name}/state/temperature/max`
- `/openconfig-platform:components/component={name}/state/temperature/alarm-status`
- `/openconfig-platform:components/component={name}/state/temperature/alarm-threshold`

#### 3.3.2.5 Power Supply Information
- `/openconfig-platform:components/component={name}/power-supply`
- `/openconfig-platform:components/component={name}/power-supply/state`
- `/openconfig-platform:components/component={name}/power-supply/state/capacity`
- `/openconfig-platform:components/component={name}/power-supply/state/enabled`

#### 3.3.2.6 Fan Information
- `/openconfig-platform:components/component={name}/fan`
- `/openconfig-platform:components/component={name}/fan/state`
- `/openconfig-platform:components/component={name}/fan/state/speed`

#### 3.3.2.7 CPU Information
- `/openconfig-platform:components/component={name}/cpu`
- `/openconfig-platform:components/component={name}/cpu/utilization`
- `/openconfig-platform:components/component={name}/cpu/utilization/state`
- `/openconfig-platform:components/component={name}/cpu/utilization/state/instant`
- `/openconfig-platform:components/component={name}/cpu/utilization/state/avg`
- `/openconfig-platform:components/component={name}/cpu/utilization/state/min`
- `/openconfig-platform:components/component={name}/cpu/utilization/state/max`

#### 3.3.2.8 Transceiver Information
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/enabled`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/form-factor-preconf`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/present`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/form-factor`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/connector-type`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/vendor-rev`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/serial-no`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/date-code`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/supply-voltage`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/thresholds`
- `/openconfig-platform:components/component={name}/openconfig-platform-transceiver:transceiver/physical-channels`

### 3.3.3 Database Table and Field Mapping
The following table shows the mapping between OpenConfig YANG paths and SONiC STATE DB tables and fields:

#### 3.3.3.1 Component Basic Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/id` | PHYSICAL_ENTITY_INFO | position_in_parent | All |
| `/components/component/state/part-no` | EEPROM_INFO | 0x22 | Chassis/EEPROM |
| `/components/component/state/serial-no` | EEPROM_INFO, TRANSCEIVER_INFO | 0x23, serial | Chassis/EEPROM, Transceiver |
| `/components/component/state/mfg-date` | EEPROM_INFO | 0x25 | Chassis/EEPROM |
| `/components/component/state/hardware-version` | EEPROM_INFO, TRANSCEIVER_INFO | 0x27, hardware_rev | Chassis/EEPROM, Transceiver |
| `/components/component/state/description` | Static/Computed | - | All |
| `/components/component/state/mfg-name` | EEPROM_INFO, TRANSCEIVER_INFO | 0x2b, manufacturer | Chassis/EEPROM, Transceiver |
| `/components/component/state/location` | PHYSICAL_ENTITY_INFO | parent_name | All |
| `/components/component/state/parent` | PHYSICAL_ENTITY_INFO | parent_name | All |
| `/components/component/state/empty` | Computed | - | All |
| `/components/component/state/removable` | Computed | - | All |
| `/components/component/state/oper-status` | Computed | status, presence | All |
| `/components/component/state/type` | Computed | - | All |
| `/components/component/state/model-name` | CPU_STATS, TRANSCEIVER_INFO | model_name, model | CPU, Transceiver |

#### 3.3.3.2 Memory Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/memory/available` | MEMORY_STATS, MOUNT_POINTS | 1K-blocks | Memory, Disk |
| `/components/component/state/memory/utilized` | MEMORY_STATS, MOUNT_POINTS | Used | Memory, Disk |

#### 3.3.3.3 Temperature Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/state/temperature/instant` | TEMPERATURE_INFO | temperature | Temperature |
| `/components/component/state/temperature/min` | TEMPERATURE_INFO | minimum_temperature | Temperature |
| `/components/component/state/temperature/max` | TEMPERATURE_INFO | maximum_temperature | Temperature |
| `/components/component/state/temperature/alarm-status` | TEMPERATURE_INFO | warning_status | Temperature |
| `/components/component/state/temperature/alarm-threshold` | TEMPERATURE_INFO | critical_high_threshold | Temperature |

#### 3.3.3.4 Power Supply Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/power-supply/state/capacity` | PSU_INFO | max_power | PSU |
| `/components/component/power-supply/state/enabled` | PSU_INFO | status | PSU |

#### 3.3.3.5 Fan Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/fan/state/speed` | FAN_INFO | speed | Fan |

#### 3.3.3.6 CPU Information Mapping

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Component Types |
|---------------------|----------------|----------------|-----------------|
| `/components/component/cpu/utilization/state/instant` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/avg` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/min` | CPU_STATS | load | CPU |
| `/components/component/cpu/utilization/state/max` | CPU_STATS | load | CPU |

#### 3.3.3.7 Transceiver Information Mapping

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

### 3.3.4 Component Type to DB Table Mapping

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

### 3.3.5 Transceiver Threshold Field Mapping

| Threshold Type | Critical High | Critical Low | Warning High | Warning Low |
|---------------|---------------|--------------|--------------|-------------|
| Output Power | txpowerhighalarm | txpowerlowalarm | txpowerhighwarning | txpowerlowwarning |
| Input Power | rxpowerhighalarm | rxpowerlowalarm | rxpowerhighwarning | rxpowerlowwarning |
| Laser Bias Current | txbiashighalarm | txbiaslowalarm | txbiashighwarning | txbiaslowwarning |
| Supply Voltage | vcchighalarm | vcclowalarm | vcchighwarning | vcclowwarning |
| Temperature | temphighalarm | templowalarm | temphighwarning | templowwarning |

### 3.3.6 Supported Component Types
#### 3.3.6.1 Chassis Component
- **YANG Key Pattern**: "chassis *"
- **OpenConfig Type**: CHASSIS
- **Primary DB Tables**: EEPROM_INFO, CHASSIS_INFO
- **Supported Fields**: Basic chassis information from EEPROM including serial number, part number, manufacturer, manufacture date, hardware version
- **Example Key**: "Chassis"

#### 3.3.6.2 CPU Component
- **YANG Key Pattern**: "CPU*"
- **OpenConfig Type**: CPU
- **Primary DB Tables**: CPU_STATS
- **Supported Fields**: CPU utilization statistics, model name, vendor information
- **Real-time Metrics**: Instant, average, min, max CPU utilization from load field
- **Example Key**: "CPU0"

#### 3.3.6.3 EEPROM Component
- **YANG Key Pattern**: "System Eeprom"
- **OpenConfig Type**: SENSOR
- **Primary DB Tables**: EEPROM_INFO
- **Supported Fields**: Product name (0x21), part number (0x22), serial number (0x23), manufacture date (0x25), label revision (0x27), platform name (0x28), manufacturer (0x2b), vendor (0x2d), service tag (0x2f)
- **Example Key**: "System Eeprom"

#### 3.3.6.4 Memory Components
- **YANG Key Pattern**: "*Memory"
- **OpenConfig Type**: Computed based on memory type
- **Primary DB Tables**: MEMORY_STATS
- **Supported Memory Types**:
  - Physical Memory
  - Buffer Memory
  - Swap Memory
  - Cached Memory
  - Virtual Memory
  - Shared Memory
- **Supported Fields**: Available memory (1K-blocks), utilized memory (Used)
- **Example Keys**: "Physical Memory", "Buffer Memory"

#### 3.3.6.5 Disk Component
- **YANG Key Pattern**: "/"
- **OpenConfig Type**: STORAGE
- **Primary DB Tables**: MOUNT_POINTS
- **Supported Fields**: Available space (1K-blocks), used space (Used), filesystem type (Type), filesystem name (Filesystem)
- **Example Key**: "/"

#### 3.3.6.6 Power Supply (PSU) Component
- **YANG Key Pattern**: "PSU *"
- **OpenConfig Type**: POWER_SUPPLY
- **Primary DB Tables**: PSU_INFO
- **Supported Fields**: PSU capacity (max_power), operational status (status), enabled state
- **Example Keys**: "PSU 1", "PSU 2"

#### 3.3.6.7 Fan Component
- **YANG Key Pattern**: "*fan*"
- **OpenConfig Type**: FAN
- **Primary DB Tables**: FAN_INFO
- **Supported Fields**: Fan speed (speed), operational status
- **Fan Types**: Chassis fans, PSU fans (PSU*.fan*)
- **Example Keys**: "fan1", "PSU1.fan1"

#### 3.3.6.8 Fantray Component
- **YANG Key Pattern**: "fantray*"
- **OpenConfig Type**: FAN_TRAY
- **Primary DB Tables**: FAN_DRAWER_INFO
- **Supported Fields**: Fan tray information and status
- **Example Keys**: "fantray1", "fantray2"

#### 3.3.6.9 Temperature Component
- **YANG Key Pattern**: Various sensor names
- **OpenConfig Type**: SENSOR
- **Primary DB Tables**: TEMPERATURE_INFO
- **Supported Fields**: 
  - Instant temperature (temperature)
  - Minimum temperature (minimum_temperature)
  - Maximum temperature (maximum_temperature)
  - Alarm status (warning_status)
  - Alarm threshold (critical_high_threshold)
- **Example Keys**: "temp1", "cpu-thermal", "psu1-temp"

#### 3.3.6.10 Transceiver Component
- **YANG Key Pattern**: "Ethernet*"
- **OpenConfig Type**: TRANSCEIVER
- **Primary DB Tables**: TRANSCEIVER_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_DOM_THRESHOLD
- **Supported Fields**:
  - Basic Info: presence, form factor, connector type, vendor revision, serial number, date code
  - DOM Data: supply voltage, temperature, optical power levels, laser bias current
  - Thresholds: Critical and warning thresholds for all DOM parameters
  - Physical Channels: Per-lane optical power and bias current measurements
- **Form Factor Support**: OSFP, QSFP, QSFP28, QSFP56, OTHER
- **Connector Types**: LC_CONNECTOR, MPO_CONNECTOR, AOC_CONNECTOR, DAC_CONNECTOR, SC_CONNECTOR
- **Example Keys**: "Ethernet0", "Ethernet1/1", "Ethernet100"

### 3.3.7 REST API Support
#### 3.3.7.1 GET Operations
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

### 3.3.8 gNMI Support
#### 3.3.8.1 Capabilities
The gNMI server exposes platform component capabilities through the standard capabilities RPC.

#### 3.3.8.2 Get Operations
Full support for gNMI Get operations on all supported platform component paths.

#### 3.3.8.3 Subscribe Operations
Support for gNMI Subscribe operations for real-time monitoring of:
- Temperature readings
- CPU utilization
- Memory usage
- Fan speeds
- Power supply status
- Transceiver DOM data

## 3.4 Implementation Details
### 3.4.1 Database Mapping
The transformer maps OpenConfig platform model to SONiC STATE DB tables:

#### 3.4.1.1 Component Metadata Mapping
- Component basic information from PHYSICAL_ENTITY_INFO table
- Chassis/EEPROM information from EEPROM_INFO table
- Component relationships (parent-child) from PHYSICAL_ENTITY_INFO

#### 3.4.1.2 Telemetry Data Mapping
- Temperature data from TEMPERATURE_INFO table
- Memory statistics from MEMORY_STATS table
- Disk usage from MOUNT_POINTS table
- CPU information from CPU_STATS table
- PSU data from PSU_INFO table
- Fan data from FAN_INFO and FAN_DRAWER_INFO tables

#### 3.4.1.3 Transceiver Data Mapping
- Basic transceiver info from TRANSCEIVER_INFO table
- DOM sensor data from TRANSCEIVER_DOM_SENSOR table
- Threshold data from TRANSCEIVER_DOM_THRESHOLD table

### 3.4.2 Component Type Detection
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

### 3.4.3 Error Handling
- Graceful handling of missing components
- Appropriate error responses for unsupported operations
- Validation of component types and availability
- Database connection error handling
- Data conversion error handling

# 4 Testing
## 4.1 Unit Tests
Comprehensive unit tests are implemented in `platform_openconfig_test.go` covering:
- Individual component type testing
- Database interaction validation
- Error condition handling
- Data transformation verification

## 4.2 Integration Tests
- REST API endpoint testing
- gNMI operations validation
- End-to-end platform monitoring scenarios

# 5 Limitations
1. Read-only operations - platform components are primarily for monitoring
2. Some advanced transceiver features may not be fully supported
3. Platform-specific component availability depends on hardware support
4. Real-time data accuracy depends on underlying platform drivers

# 6 Future Enhancements
1. Support for additional component types as they become available
2. Enhanced alarm and notification mechanisms
3. Historical data collection and trending
4. Advanced diagnostic capabilities
5. Configuration support for configurable platform components

# 7 References
1. [OpenConfig Platform YANG Models](https://github.com/openconfig/public/tree/master/release/models/platform)
2. [SONiC Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)
3. [OpenConfig gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
