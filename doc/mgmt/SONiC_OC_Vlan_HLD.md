# VLAN
Openconfig support for VLAN interfaces
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/05/2019  |   Justine Jose      | Initial version                   |

# About this Manual
This document provides information about the north bound interface details for VLANs.

# Scope
This document covers the "configuration" and "show" commands supported for VLANs based on openconfig yang
and unit-test cases. It does not include the protocol design or protocol implementation details.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| VLAN                      | Virtual Local Area Network         |

# 1 Feature Overview
Add support for VLAN create/set/get via CLI, REST and gNMI using openconfig-interfaces.yang and sonic-mgmt-framework container

## 1.1 Requirements
Provide management framework capabilities to handle:
- VLAN creation and deletion
- Addition of tagged/un-tagged ports to VLAN
- Removal of tagged/un-tagged ports from VLAN
- Associated show commands.

### 1.1.1 Functional Requirements

Provide management framework support to existing SONiC capabilities with respect to VLANs.

### 1.1.2 Configuration and Management Requirements
- IS-CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

## 1.2 Design Overview

### 1.2.1 Basic Approach
Provide transformer methods in sonic-mgmt-framework container for VLAN handling

### 1.2.2 Container
All code changes will be done in management-framework container

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure Vlan interface via CLI, gNMI and REST interfaces
## 2.2 Functional Description
Provide CLI, gNMI and REST support for VLAN related commands handling

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to add support for VLAN handling

## 3.2 User Interface
### 3.2.1 Data Models
List of yang models required for VLAN interface management.
1. [openconfig-if-interfaces.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang)
2. [openconfig-if-ethernet.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ethernet.yang)

Supported yang objects and attributes are highlighted in green:
```diff
module: openconfig-interfaces
+   +--rw interfaces
+      +--rw interface* [name]
+         +--rw name                   -> ../config/name
          +--rw config
          |  +--rw name?            string
          |  +--rw type             identityref
+         |  +--rw mtu?             uint16
          |  +--rw loopback-mode?   boolean
          |  +--rw description?     string
+         |  +--rw enabled?         boolean
          |  +--rw oc-vlan:tpid?    identityref
          +--ro state
          |  +--ro name?            string
          |  +--ro type             identityref
+         |  +--ro mtu?             uint16
          |  +--ro loopback-mode?   boolean
          |  +--ro description?     string
          |  +--ro enabled?         boolean
          |  +--ro ifindex?         uint32
+         |  +--ro admin-status     enumeration
+         |  +--ro oper-status      enumeration
          |  +--ro last-change?     oc-types:timeticks64
          |  +--ro logical?         boolean
          |  +--ro oc-vlan:tpid?    identityref
          +--rw hold-time
          |  +--rw config
          |  |  +--rw up?     uint32
          |  |  +--rw down?   uint32
          |  +--ro state
          |     +--ro up?     uint32
          |     +--ro down?   uint32
          +--rw oc-eth:ethernet
+         |  +--rw oc-vlan:switched-vlan
+         |     +--rw oc-vlan:config
+         |     |  +--rw oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |     |  +--rw oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:trunk-vlans*      union
+         |     +--ro oc-vlan:state
          |        +--ro oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |        +--ro oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:trunk-vlans*      union
```
### 3.2.2 CLI

#### 3.2.2.1 Configuration Commands

#### VLAN Creation
`interface Vlan <vlan-id>`
```
sonic(config)# interface Vlan 5
```
#### VLAN Deletion
`no interface Vlan <vlan-id>`
```
sonic(config)# no interface Vlan 5
```
#### Trunk VLAN addition to Member Port
`switchport trunk allowed Vlan <vlan-id>`
```
sonic(conf-if-Ethernet4)# switchport trunk allowed Vlan 5
```
#### Trunk VLAN removal from Member Port
`no switchport trunk allowed Vlan <vlan-id>`
```
sonic(conf-if-Ethernet4)# no switchport trunk allowed Vlan 5
```
#### Access VLAN addition to Member Port
`switchport access Vlan <vlan-id>`
```
sonic(conf-if-Ethernet4)# switchport access Vlan 5
```
#### Access VLAN removal from Member Port
`no switchport access Vlan`
```
sonic(conf-if-Ethernet4)# no switchport access Vlan
```

#### 3.2.2.2 Show Commands
#### Display VLAN Members detail
`show Vlan`
```
Q: A - Access (Untagged), T - Tagged
    NUM       Status       Q Ports
    5         Active       T Ethernet24
    10        Inactive
    20        Inactive     A Ethernet4
```
#### Display specific VLAN Members detail
`show Vlan <vlan-id>`
```
sonic# show Vlan 5
Q: A - Access (Untagged), T - Tagged
    NUM    Status     Q Ports
    5      Active     T Ethernet24
                      A Ethernet20
```
#### Display VLAN information
`show interface Vlan`
```
sonic# show interface Vlan
Vlan10 is up, line protocol is up
IP MTU 2500 bytes

Vlan20 is up, line protocol is down
IP MTU 5500 bytes
```
#### Display specific VLAN Information
`show interface Vlan <vlan-id>`
```sonic# show interface Vlan 10
Vlan10 is up, line protocol is up
IP MTU 2500 bytes
```


#### 3.2.2.3 Debug Commands
N/A

#### 3.2.2.4 IS-CLI Compliance
N/A

### 3.2.3 REST API Support

**PATCH**
- `/openconfig-interfaces:interfaces/ interface={name}`
- `/openconfig-interfaces:interfaces/ interface={name}/config/[enabled | mtu]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans | interface-mode]`


**DELETE**
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/ interface={name}`

**GET**
- `/openconfig-interfaces:interfaces/ interface={name}/state/[admin-status | mtu | oper-status]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/State/[access-vlan | trunk-vlans]`

# 4 Flow Diagrams
N/A

# 5 Error Handling
TBD

# 6 Serviceability and Debug
TBD

# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
- Create VLAN A, verify it using CLI, gNMI and REST.
- Configure MTU for VLAN A, verify it using CLI, gNMI and REST.
- Remove MTU for VLAN A, verify it using CLI, gNMI and REST.
- Add an untagged-port to VLAN A, verify it using CLI, gNMI and REST.
- Create VLAN B, verify it using CLI, gNMI and REST.
- Configure admin-status, verify it using CLI, gNMI and REST.
- Add 2 tagged-ports to VLAN B, verify it using CLI, gNMI and REST.
- Remove un-tagged port from VLAN A, verify it using CLI, gNMI and REST.
- Remove all the tagged-ports from VLAN B, verify it using CLI, gNMI and REST.
- Delete VLAN, verify it using CLI, gNMI and REST.

# 10 Internal Design Information
N/A
