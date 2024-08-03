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
- Openconfig-system.yang version 2.1.0 - latest openconfig yang repo version is considered.
- Supported attributes in OpenConfig YANG tree:
  ```
  +--rw system
     +--rw config
     |  +--rw hostname?       oc-inet:domain-name
     |  +--rw login-banner?   string
     |  +--rw motd-banner?    string
     +--ro state
     |  +--ro current-datetime?               oc-yang:date-and-time
     |  +--ro up-time?                        oc-types:timeticks64
     |  +--ro boot-time?                      oc-types:timeticks64
     |  +--ro software-version?               string
     +--rw aaa
     |  +--rw authentication
     |  |  +--rw config
     |  |  |  +--rw authentication-method*   union
     |  +--rw authorization
     |  |  +--rw config
     |  |  |  +--rw authorization-method*   union
     |  +--rw accounting
     |  |  +--rw config
     |  |  |  +--rw accounting-method*   union
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
     |              |  +--rw name?      string
     |              |  +--rw address?   oc-inet:ip-address
     |              |  +--rw timeout?   uint16
     |              +--rw tacacs
     |              |  +--rw config
     |              |  |  +--rw port?                oc-inet:port-number
     |              |  |  +--rw secret-key?          oc-types:routing-password
     |              |  |  +--rw source-address?      oc-inet:ip-address
     |              +--rw radius
     |                 +--rw config
     |                 |  +--rw auth-port?             oc-inet:port-number
     |                 |  +--rw secret-key?            oc-types:routing-password
     |                 |  +--rw source-address?        oc-inet:ip-address
     |                 |  +--rw retransmit-attempts?   uint8
     +--rw logging
     |  +--rw remote-servers
     |  |  +--rw remote-server* [host]
     |  |     +--rw host         -> ../config/host
     |  |     +--rw config
     |  |     |  +--rw host?               oc-inet:host
     |  |     |  +--rw source-address?     oc-inet:ip-address
     |  |     |  +--rw network-instance?   oc-ni:network-instance-ref
     |  |     |  +--rw remote-port?        oc-inet:port-number
     +--rw processes
     |  +--ro process* [pid]
     |     +--ro pid      -> ../state/pid
     |     +--ro state
     |        +--ro pid?                  uint64
     |        +--ro name?                 string
     |        +--ro args*                 string
     |        +--ro cpu-utilization?      oc-types:percentage
     |        +--ro memory-utilization?   oc-types:percentage
     +--rw messages
     |  +--rw config
     |  |  +--rw severity?   oc-log:syslog-severity
     |  +--rw debug-entries
     |     +--rw debug-service* [service]
     |        +--rw service    -> ../config/service
     |        +--rw config
     |        |  +--rw service?   identityref
     |        |  +--rw enabled?   boolean
     +--rw ssh-server
     |  +--rw config
     |  |  +--rw timeout?            uint16
     +--rw clock
     |  +--rw config
     |  |  +--rw timezone-name?   timezone-name-type
     +--rw dns
     |  +--rw config
     |  |  +--rw search*   oc-inet:domain-name
     +--rw ntp
     |  +--rw config
     |  |  +--rw enabled?           boolean
     |  |  +--rw enable-ntp-auth?   boolean
     |  +--rw ntp-keys
     |  |  +--rw ntp-key* [key-id]
     |  |     +--rw key-id    -> ../config/key-id
     |  |     +--rw config
     |  |     |  +--rw key-id?      uint16
     |  |     |  +--rw key-type?    identityref
     |  |     |  +--rw key-value?   string
     |  +--rw servers
     |     +--rw server* [address]
     |        +--rw address    -> ../config/address
     |        +--rw config
     |        |  +--rw address?            oc-inet:host
     |        |  +--rw version?            uint8
     |        |  +--rw association-type?   enumeration
     |        |  +--rw iburst?             boolean
     |        |  +--rw key-id?      ->    ../../../ntp-keys/ntp-key/key-id
     |        |  +--rw network-instance?   oc-ni:network-instance-ref
     |        |  +--rw source-address?     oc-inet:ip-address

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
1. Provide support for OpenConfig System YANG models.
2. Implement transformer support for Openconfig system model to have following supports:  
    Configure/Set System attributes.  
    Get System attributes.  
    Delete System attributes.   
    Subscribe System attributes for telemetry.
3. Add support for following System features:
    * hostname
    * motd & login banner
    * current-datetime
    * boot-time & up-time
    * software-version
    * timezone
    * dns
    * ntp
    * ssh-server
    * logging
    * aaa
    * processes
    * messages

### 1.1.2 Configuration and Management Requirements
The System configuration/management can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration or un-supported node is accessed.

### 1.1.3 Scalability Requirements
NA

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports framework for Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation for System features.

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
For software-version, new table will be added, namely VERSION|SOFTWARE.

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
Openconfig-system.yang (2.1.0) and its submodules will be used as user interfacing models.  
We are updating openconfig-system yang version (0.7.0) in sonic with latest available openconfig version (2.1.0).  
Community PR [https://github.com/sonic-net/sonic-mgmt-common/pull/147]  
   * In this PR openconfig-system.yang and its submodules are updated to latest version available
   * Reference to openconfig-network-instance module is commented, as this module is yet to be supported in sonic

Main changes among these to openconfig versions are:
 * Feature wise major changes -
    * system/state -> uptime, software-version, last-configuration-timestamp nodes are added.
    * ntp -> source-address moved to per server list from global container. Also network-instance is included per server.
    * grpc-server -> Restructured completely, multiple server provision is added.
    * logging -> For remote-server, network-instance support is added. Files & VTY containers are added newly.
    * memory -> used and free leaves are added.
    * process -> uptime node is removed.

 * New features added in latest version -
    * license
    * mac-address
    * hashing
    * bootz
    * control-plane-traffic (copp)
    * resource utilization

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
8. Verify that operations supported for gNMI/REST works fine for login & motd banners.
9. Verify that operations supported for gNMI/REST works fine for up-time, boot-time, current-datetime & software-version.
10. Verify that operations supported for gNMI/REST works fine for processes nodes.

## 6.2 Negative Test Cases
1. Verify that any operation on unsupported nodes give a proper error.
2. Verify that invalid hostname configuration is not allowed.
3. Verify that invalid DNS nameserver configuration is not allowed.
4. Verify that invalid timezone-name is not allowed.
5. Verify that invalid NTP source address returns proper error.
6. Verify that AAA server source-address accepts only valid IP.
7. Verify that GET on processes with non-existing pid returns an empty data.
