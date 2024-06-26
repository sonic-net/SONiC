# OpenConfig support for System features

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
      * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
      * [1.1.3 Scalability Requirements](#113-scalability-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)
      * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
      * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 06/21/2024  | Anukul Verma | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration/management of System features in SONiC corresponding to openconfig-system.yang module and its sub-modules.

# Scope
- This document describes the high level design of OpenConfig configuration/management of System features via gNMI/REST in SONiC.
- This does not cover the SONiC KLISH CLI.
- Openconfig-system.yang version (revision 2019-01-29) present in SONiC 202311 release is considered.
- Supported attributes in OpenConfig YANG tree:
  ```  
  module: openconfig-system
    +--rw system
       +--rw config
       |  +--rw hostname?       oc-inet:domain-name
       +--ro state
       |  +--ro hostname?           oc-inet:domain-name
       |  +--ro current-datetime?   oc-yang:date-and-time
       |  +--ro boot-time?          oc-types:timeticks64
       +--rw clock
       |  +--rw config
       |  |  +--rw timezone-name?   timezone-name-type
       |  +--ro state
       |     +--ro timezone-name?   timezone-name-type
       +--rw dns
       |  +--rw config
       |  |  +--rw search*   oc-inet:domain-name
       |  +--ro state
       |  |  +--ro search*   oc-inet:domain-name
       +--rw ntp
       |  +--rw config
       |  |  +--rw enabled?              boolean
       |  |  +--rw ntp-source-address?   oc-inet:ip-address
       |  |  +--rw enable-ntp-auth?      boolean
       |  +--ro state
       |  |  +--ro enabled?              boolean
       |  |  +--ro ntp-source-address?   oc-inet:ip-address
       |  |  +--ro enable-ntp-auth?      boolean
       |  +--rw ntp-keys
       |  |  +--rw ntp-key* [key-id]
       |  |     +--rw key-id    -> ../config/key-id
       |  |     +--rw config
       |  |     |  +--rw key-id?      uint16
       |  |     |  +--rw key-type?    identityref
       |  |     |  +--rw key-value?   string
       |  |     +--ro state
       |  |        +--ro key-id?      uint16
       |  |        +--ro key-type?    identityref
       |  |        +--ro key-value?   string
       |  +--rw servers
       |     +--rw server* [address]
       |        +--rw address    -> ../config/address
       |        +--rw config
       |        |  +--rw address?            oc-inet:host
       |        |  +--rw version?            uint8
       |        |  +--rw association-type?   enumeration
       |        |  +--rw iburst?             boolean
       |        +--ro state
       |           +--ro address?            oc-inet:host
       |           +--ro version?            uint8
       |           +--ro association-type?   enumeration
       |           +--ro iburst?             boolean
       +--rw ssh-server
       |  +--rw config
       |  |  +--rw timeout?            uint16
       |  +--ro state
       |     +--ro timeout?            uint16
       +--rw logging
       |  +--rw remote-servers
       |     +--rw remote-server* [host]
       |        +--rw host         -> ../config/host
       |        +--rw config
       |        |  +--rw host?             oc-inet:host
       |        |  +--rw source-address?   oc-inet:ip-address
       |        |  +--rw remote-port?      oc-inet:port-number
       |        +--ro state
       |        |  +--ro host?             oc-inet:host
       |        |  +--ro source-address?   oc-inet:ip-address
       |        |  +--ro remote-port?      oc-inet:port-number
       +--rw aaa
       |  +--rw config
       |  +--ro state
       |  +--rw authentication
       |  |  +--rw config
       |  |  |  +--rw authentication-method*   union
       |  |  +--ro state
       |  |  |  +--ro authentication-method*   union
       |  +--rw authorization
       |  |  +--rw config
       |  |  |  +--rw authorization-method*   union
       |  |  +--ro state
       |  |  |  +--ro authorization-method*   union
       |  +--rw accounting
       |  |  +--rw config
       |  |  |  +--rw accounting-method*   union
       |  |  +--ro state
       |  |  |  +--ro accounting-method*   union
       |  +--rw server-groups
       |     +--rw server-group* [name]
       |        +--rw name       -> ../config/name
       |        +--rw config
       |        |  +--rw name?   string
       |        |  +--rw type?   identityref
       |        +--ro state
       |        |  +--ro name?   string
       |        |  +--ro type?   identityref
       |        +--rw servers
       |           +--rw server* [address]
       |              +--rw address    -> ../config/address
       |              +--rw config
       |              |  +--rw address?   oc-inet:ip-address
       |              |  +--rw timeout?   uint16
       |              +--ro state
       |              |  +--ro address?               oc-inet:ip-address
       |              |  +--ro timeout?               uint16
       |              +--rw tacacs
       |              |  +--rw config
       |              |  |  +--rw port?             oc-inet:port-number
       |              |  |  +--rw secret-key?       oc-types:routing-password
       |              |  |  +--rw source-address?   oc-inet:ip-address
       |              |  +--ro state
       |              |     +--ro port?             oc-inet:port-number
       |              |     +--ro secret-key?       oc-types:routing-password
       |              |     +--ro source-address?   oc-inet:ip-address
       |              +--rw radius
       |                 +--rw config
       |                 |  +--rw auth-port?             oc-inet:port-number
       |                 |  +--rw secret-key?            oc-types:routing-password
       |                 |  +--rw source-address?        oc-inet:ip-address
       |                 |  +--rw retransmit-attempts?   uint8
       |                 +--ro state
       |                    +--ro auth-port?             oc-inet:port-number
       |                    +--ro secret-key?            oc-types:routing-password
       |                    +--ro source-address?        oc-inet:ip-address
       |                    +--ro retransmit-attempts?   uint8
       +--rw memory
       |  +--rw config
       |  +--ro state
       |     +--ro physical?   uint64
       |     +--ro reserved?   uint64
       +--ro cpus
       |  +--ro cpu* [index]
       |     +--ro index    -> ../state/index
       |     +--ro state
       |        +--ro index?                union
       |        +--ro total
       |        |  +--ro instant?    oc-types:percentage
       |        |  +--ro avg?        oc-types:percentage
       |        |  +--ro min?        oc-types:percentage
       |        |  +--ro max?        oc-types:percentage
       |        |  +--ro interval?   oc-types:stat-interval
       |        |  +--ro min-time?   oc-types:timeticks64
       |        |  +--ro max-time?   oc-types:timeticks64
       |        +--ro user
       |        |  +--ro instant?    oc-types:percentage
       |        |  +--ro avg?        oc-types:percentage
       |        |  +--ro min?        oc-types:percentage
       |        |  +--ro max?        oc-types:percentage
       |        |  +--ro interval?   oc-types:stat-interval
       |        |  +--ro min-time?   oc-types:timeticks64
       |        |  +--ro max-time?   oc-types:timeticks64
       |        +--ro kernel
       |        |  +--ro instant?    oc-types:percentage
       |        |  +--ro avg?        oc-types:percentage
       |        |  +--ro min?        oc-types:percentage
       |        |  +--ro max?        oc-types:percentage
       |        |  +--ro interval?   oc-types:stat-interval
       |        |  +--ro min-time?   oc-types:timeticks64
       |        |  +--ro max-time?   oc-types:timeticks64
       +--rw processes
       |  +--ro process* [pid]
       |     +--ro pid      -> ../state/pid
       |     +--ro state
       |        +--ro pid?                  uint64
       |        +--ro name?                 string
       |        +--ro args*                 string
       |        +--ro start-time?           uint64
       |        +--ro uptime?               oc-types:timeticks64
       |        +--ro cpu-usage-user?       oc-types:timeticks64
       |        +--ro cpu-usage-system?     oc-types:timeticks64
       |        +--ro cpu-utilization?      oc-types:percentage
       |        +--ro memory-usage?         uint64
       |        +--ro memory-utilization?   oc-types:percentage
       +--rw messages
          +--rw config
          |  +--rw severity?   oc-log:syslog-severity
          +--ro state
          |  +--ro severity?   oc-log:syslog-severity
          +--rw debug-entries
             +--rw debug-service* [service]
                +--rw service    -> ../config/service
                +--rw config
                |  +--rw service?   identityref
                |  +--rw enabled?   boolean
                +--ro state
                   +--ro service?   identityref
                   +--ro enabled?   boolean


# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig System YANG models.
2. Implement transformer support for Openconfig system model to have following supports:  
    Configure/Set System attributes.  
    Get System attributes.  
    Delete System attributes.  
    Subscribe System attributes for telemetry.  
3. Add support for following System features:  
    hostname  
    timezone  
    dns  
    ntp  
    ssh-server  
    logging  
    aaa 
    memory  
    cpu  
    processes  
    messages
### 1.1.2 Configuration and Management Requirements
The System configuration/management can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration or un-supported node is accessed.
### 1.1.3 Scalability Requirements
NA

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports System features configurations such as Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation for System features.
### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities, get, set and subscribe based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md]

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition.
### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.  
For CPU and Memory info we will add new tables, which will be periodically updated and used by mgmt-framework to send data to requesting clients (Similar as PROCESS_STATS). 
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
Openconfig-system.yang and its submodules will be used as user interfacing models.
### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported
#### 3.3.2.2 SET
Supported
#### 3.3.2.3 DELETE
Supported
### 3.3.3 gNMI Support
#### 3.3.3.1 GET
Supported  
Sample GET output for system/state container:
```
gnmic -a <ip:port> -u <user> -p <passwd> get --path "/openconfig-system:system"
[
 {
  "source": "<ip:port>",
  "timestamp": 1712673160649745928,
  "time": "2024-04-09T20:02:40.649745928+05:30",
  "updates": [
   {
    "Path": "openconfig-system:system",
    "values": {
      "openconfig-system:system": {
          "state": {
            "hostname": "mytest-hostname"
            "boot-time": "1712672712",
            "current-datetime": "2024-04-09T14:32:40Z+00:00"
          }
        }
    }
   }
  ]
 }
]
```
#### 3.3.3.2 SET
Supported  
Sample SET logs for system/config/hostname node:
```
gnmi_set -target_addr <ip:port> -update /openconfig-system:system/config/hostname:@./hostname-value.json -xpath_target OC-YANG
/openconfig-system:system/config/hostname
@./hostname-value.json
== setRequest:
prefix: <
  target: "OC-YANG"
>
update: <
  path: <
    origin: "openconfig-system"
    elem: <
      name: "system"
    >
    elem: <
      name: "config"
    >
    elem: <
      name: "hostname"
    >
  >
  val: <
    json_ietf_val: "{\"hostname\": \"mytest-hostname\"}"
  >
>

== setResponse:
prefix: <
  target: "OC-YANG"
>
response: <
  path: <
    origin: "openconfig-system"
    elem: <
      name: "openconfig-system:system"
    >
    elem: <
      name: "config"
    >
    elem: <
      name: "hostname"
    >
  >
  op: UPDATE
>
```
#### 3.3.3.3 DELETE
Supported
#### 3.3.3.4 SUBSCRIBE
Supported

# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and SONiC YANG:  

![openconfig to sonic mapping](images/Openconfig_system_SONiC_mapping.png)


# 5 Error Handling
Invalid configurations/operations will report an error.

# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Verify that operations supported for gNMI/REST works fine for hostname.
2. Verify that operations supported for gNMI/REST works fine for clock/timezone-name.
3. Verify that operations supported for gNMI/REST works fine for DNS nameserver.
4. Verify that operations supported for gNMI/REST works fine for NTP nodes.
5. Verify that operations supported for gNMI/REST works fine for ssh-server timeout.
6. Verify that operations supported for gNMI/REST works fine for logging and messages nodes.
7. Verify that operations supported for gNMI/REST works fine for AAA (TACACS & RADIUS) nodes.
8. Verify that operations supported for gNMI/REST works fine for memory nodes.
9. Verify that operations supported for gNMI/REST works fine for CPU nodes.
10. Verify that operations supported for gNMI/REST works fine for processes nodes.

## 6.2 Negative Test Cases
1. Verify that any operation on unsupported nodes give a proper error.
2. Verify that invalid hostname configuration is not allowed.
3. Verify that invalid DNS nameserver configuration is not allowed.
4. Verify that invalid timezone-name is not allowed.
5. Verify that invalid NTP source address returns proper error.
6. Verify that AAA server source-address accepts only valid IP.
7. Verify that GET on processes with non-existing pid returns an empty data.
8. Verify that invalid CPU index returns an empty data.
