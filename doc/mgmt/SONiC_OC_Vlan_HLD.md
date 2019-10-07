# VLAN
Layer 2 Forwarding Enhancements.
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
This document provides general information about VLAN configuration in SONiC using the management framework.

# Scope
Covers Northbound interface for the VLAN feature, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| VLAN                      | Virtual Local Area Network         |

# 1 Feature Overview

Provide management framework capabilities to handle:
- VLAN creation and deletion
- Addition of tagged/un-tagged ports to vlan
- Removal of tagged/un-tagged ports from vlan
- Associated show commands.

## 1.1 Requirements

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
Manage/configure Vlan interface via CLI, gNMI and Rest interfaces
## 2.2 Functional Description
Provide CLI, gNMI and REST support for Vlan related commands handling

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to add support for Vlan handling

## 3.2 User Interface
### 3.2.1 Data Models
**openconfig-vlan.yang** (Config for Set Op and State for Get Op)

- ``/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/[config | state]/[interface-mode | access-vlan | trunk-vlans]``

Exception - "native-vlan" is not supported in the above config and state containers.

**openconfig-interfaces.yang** (Get Support)

- ``/openconfig-interfaces:interfaces/ interface={name}/state/[admin-status | oper-status | mtu]``

Note - SONiC doesn't support other attributes for VLAN Interface.


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
#### Display VLAN details
`show Vlan`
```
Q: A - Access (Untagged), T - Tagged
    NUM       Status       Q Ports
    5         Active       T Ethernet24
    10        Inactive
    20        Inactive     A Ethernet4
```
#### Display specific VLAN details
`show Vlan <vlan-id>`
```
sonic# show Vlan 5
Q: A - Access (Untagged), T - Tagged
    NUM    Status     Q Ports
    5      Active     T Ethernet24
                      A Ethernet20
```
#### 3.2.2.3 Debug Commands
N/A

#### 3.2.2.4 IS-CLI Compliance
N/A

### 3.2.3 REST API Support

**PATCH**
- `/openconfig-interfaces:interfaces/ interface={name}`
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
- Create VLAN A, verify it using CLI, gNMI and Rest.
- Add an untagged-port to VLAN A, verify it using CLI, gNMI and Rest.
- Create VLAN B, verify it using CLI, gNMI and Rest.
- Add 2 tagged-ports to VLAN B, verify it using CLI, gNMI and Rest.
- Remove un-tagged port from VLAN A, verify it using CLI, gNMI and Rest.
- Remove all the tagged-ports from VLAN B, verify it using CLI, gNMI and Rest.
- Delete VLAN, verify it using CLI, gNMI and Rest.

# 10 Internal Design Information
N/A
