# OpenConfig support for LACP components

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [1 Feature Overview](#1-feature-overview)
  * [2 Functionality](#2-functionality)  
  * [3 Design](#3-design)
  * [4 Testing](#4-testing)
  * [5 References](#7-references)

# List of Tables
  * [Table 1: Abbreviations](#table-1-abbreviations) 

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 01/23/2026  | Neha Das | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration and telemetry support for the Link Aggregation Control Protocol (LACP) for managing aggregate interfaces in SONiC.

# Scope
- This document describes the high level design of OpenConfig LACP via gNMI/REST in SONiC.
- This does not cover the SONiC KLISH CLI.
- Openconfig-lacp.yang version latest from Openconfig yang repo is considered.
- Supported attributes in OpenConfig YANG tree:
```
module: openconfig-lacp
+--rw lacp
  +--rw interfaces
     +--rw interface* [name]
        +--rw name                   -> ../config/name
        +--rw config
        |  +--rw name?               string
        |  +--rw interval?           lacp-period-type
        |  +--rw fallback?           boolean
        |  +--rw lacp-mode?          lacp-activity-type	
        |  +--rw system-id-mac?      oc-yang:mac-address
        +--ro state
        |  +--rw name?               string
        |  +--rw interval?           lacp-period-type
        |  +--rw fallback?           boolean
        |  +--rw lacp-mode?          lacp-activity-type	
        |  +--rw system-id-mac?      oc-yang:mac-address
        +--rw members
           |  +--rw member* [interface]
           |     +--rw interface     -> ../config/interface
           |     +--ro state
           |        +--ro interface       oc-if:base-interface-ref	
           |        +--ro activity        lacp-activity-type
           |        +--ro timeout         lacp-timeout-type	
           |        +--ro synchronization lacp-synchronization-type
           |        +--ro aggregatable    boolean
           |        +--ro collecting      boolean
           |        +--ro distributing    boolean
           |        +--ro system-id       oc-yang:mac-address	
           |        +--ro oper-key      	uint16
           |        +--ro partner-id      oc-yang:mac-address
           |        +--ro partner-key     uint16
           |        +--ro counters
           |        |  +--ro lacp-in-pkts?   counter64
           |        |  +--ro lacp-out-pkts?  counter64
           |        |  +--ro lacp-rx-errors? counter64
```

# Definition/Abbreviation
### Table 1: Abbreviations

| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |


# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig LACP YANG model.
2. Implement transformer support for Openconfig LACP model for the following requirements:  
    Configure/Set LACP attributes.  
    Subscribe and Get LACP attributes for telemetry.
3. Works in conjunction with the OpenConfig interfaces and aggregate interfaces models.

### 1.1.2 Configuration and Management Requirements
The LACP configuration/management can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration or un-supported node is accessed.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports framework for Get, Set and Subscribe through gNMI. This feature adds support for OpenConfig YANG models using transformer based implementation for LACP features.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. gNMI client with support for capabilities, get and subscribe based on the supported YANG models.
2. Integration with network management systems for comprehensive platform visibility.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
The following existing Config DB tables are utilized for LACP information:
- PORTCHANNEL

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
The following existing STATE DB tables are utilized for LACP information:
- LAG_MEMBER_TABLE
- LAG_TABLE

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
Openconfig-lacp.yang will be used as user interfacing models.

### 3.3.2 Database Table and Field Mapping
The following sections provide detailed mapping between OpenConfig YANG paths and SONiC STATE DB tables and fields.

#### 3.3.2.1 LACP Configuration
**Database Table:** CONFIG_DB | PORTCHANNEL  
**Key Pattern:** "PortChannel*" (e.g., "PortChannel1")  

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|---------------------|----------------|----------------|
| `/lacp/interfaces/interface/config/interval` | PORTCHANNEL | fast_rate |
| `/lacp/interfaces/interface/config/fallback` | PORTCHANNEL | fallback |
| `/lacp/interfaces/interface/config/lacp-mode` | PORTCHANNEL | active |
| `/lacp/interfaces/interface/config/system-id-mac` | PORTCHANNEL | system_id |

#### 3.3.2.2 LACP State
**Database Table:** STATE_DB | LAG_TABLE 
**Key Pattern:** "PortChannel*" (e.g., "PortChannel1") 

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|---------------------|----------------|----------------|
| `/lacp/interfaces/interface/state/interval` | LAG_TABLE | runner.fast_rate |
| `/lacp/interfaces/interface/state/fallback` | LAG_TABLE | runner.fallback |
| `/lacp/interfaces/interface/state/lacp-mode` | LAG_TABLE | runner.active |
| `/lacp/interfaces/interface/state/system-id-mac` | LAG_TABLE | team_device.ifinfo.dev_addr |

#### 3.3.2.3 LACP Member State
**Database Table:** STATE_DB | LAG_MEMBER_TABLE  
**Key Pattern:** "PortChannel*|Ethernet*" (e.g., "PortChannel1|Ethernet0")  

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|---------------------|----------------|----------------|
| `/lacp/interfaces/interface/members/member/state/oper-key` | LAG_MEMBER_TABLE | runner.actor_lacpdu_info.key |
| `/lacp/interfaces/interface/members/member/state/system-id` | LAG_MEMBER_TABLE | runner.actor_lacpdu_info.system |
| `/lacp/interfaces/interface/members/member/state/partner-id` | LAG_MEMBER_TABLE | runner.partner_lacpdu_info.system |
| `/lacp/interfaces/interface/members/member/state/partner-key` | LAG_MEMBER_TABLE | runner.partner_lacpdu_info.key |
| `/lacp/interfaces/interface/members/member/state/activity` |  | lacp-activity-type:PASSIVE |
| `/lacp/interfaces/interface/members/member/state/timeout` |  | lacp-timeout-type:SHORT |
| `/lacp/interfaces/interface/members/member/state/aggregatable` |  | false |
| `/lacp/interfaces/interface/members/member/state/synchronization` |  | lacp-synchronization-type:OUT_SYNC |
| `/lacp/interfaces/interface/members/member/state/collecting` |  | false |
| `/lacp/interfaces/interface/members/member/state/distributing` |  | false |
| `/lacp/interfaces/interface/members/member/state/counters/lacp-in-pkts` | LAG_MEMBER_TABLE | runner.counters.lacp-in-packets |
| `/lacp/interfaces/interface/members/member/state/counters/lacp-out-pkts` | LAG_MEMBER_TABLE | runner.counters.lacp-out-packets |
| `/lacp/interfaces/interface/members/member/state/counters/lacp-rx-errors` | LAG_MEMBER_TABLE | runner.counters.lacp-rx-errors |


### 3.3.3 gNMI Support
### 3.3.2 gNMI Support
#### 3.3.2.1 GET
Supported
#### 3.3.2.2 SET
Supported
#### 3.3.2.3 DELETE
Supported

### 3.3.3 gNMI Subscription Support
#### 3.3.3.1 On Change
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 127.0.0.1:8080 -query_type s -streaming_type ON_CHANGE -v 0 -target OC-YANG -q /openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/config
```
#### 3.3.3.2 SAMPLE
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 127.0.0.1:8080  -query_type s -streaming_type SAMPLE -target OC-YANG -q /openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/config -heartbeat_interval 20
```
#### 3.3.3.4 Target Defined
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 127.0.0.1:8080 -query_type s -target OC-YANG -q /openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/config
```
Example Output:
```
{
  "OC-YANG": {
    "openconfig-lacp:lacp": {
      "interfaces": {
        "interface": {
          "PortChannel1": {
            "config": {
              "fallback": true,
              "interval": SLOW,
              "lacp-mode": "PASSIVE",
              "name": "PortChannel1",
              "system-id-mac": "00:00:00:00:00:80"
            }
          }
        }
      }
    }
  }
}

```


# 4 Testing
## 4.1 Unit Tests
Comprehensive unit tests covering:
- Verification of configuration
- Database interaction and data retrieval verification
- Error condition handling and edge cases
- Data transformation and format validation
- OpenConfig YANG path mapping verification

## 4.2 Integration Tests
- REST API endpoint testing
- gNMI operations validation

# 5 References
1. [OpenConfig LACP YANG Models](https://github.com/openconfig/public/tree/master/release/models/lacp)
2. [SONiC Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)
3. [OpenConfig gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
