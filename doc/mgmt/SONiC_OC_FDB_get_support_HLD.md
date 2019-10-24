
# FDB GET support

Implement GET support for FDB entries using CLI/REST/gNMI SONiC management framework interfaces.

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
| 0.1 | 09/10/2019  |  Venkatesan Mahalingam      | Initial version                   |

# About this Manual
This document provides general information about FDB management GET operation for FDB-table in SONiC.
# Scope
Covers Northbound GET request for the FDB entries, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| FDB                      | Forwarding Database


# 1 Feature Overview

The documents covers the FDB GET requests on (CLI/REST/gNMI) FDB-Table for fetching the data from the back-end to the user using SONiC managment framework.

## 1.1 Requirements
### 1.1.1 Functional Requirements

Provide management framework GET support to existing SONiC capabilities with respect to FDB.

### 1.1.2 Configuration and Management Requirements
 - Implement FDB CLI show Commands
 - REST GET support for FDB
 - gNMI GET support for FDB

### 1.1.3 Scalability Requirements
### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
### 1.2.2 Container
### 1.2.3 SAI Overview
# 2 Functionality
## 2.1 Target Deployment Use Cases
## 2.2 Functional Description
# 3 Design
## 3.1 Overview
## 3.2 DB Changes
### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
## 3.4 SyncD
## 3.5 SAI
## 3.6 User Interface
### 3.6.1 Data Models
The following OpenConfig YANG model is used to implement GET support for FDB entries.
[https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance-l2.yang#L292)
```
module: openconfig-network-instance
    +--rw network-instances
       +--rw network-instance* [name]
          +--rw name                       -> ../config/name
          +--rw fdb
          |  +--rw config
          |  |  +--rw mac-learning?      boolean
          |  |  +--rw mac-aging-time?    uint16
          |  |  +--rw maximum-entries?   uint16
          |  +--ro state
          |  |  +--ro mac-learning?      boolean
          |  |  +--ro mac-aging-time?    uint16
          |  |  +--ro maximum-entries?   uint16
          |  +--rw mac-table
          |     +--rw entries
          |        +--rw entry* [mac-address vlan]
          |           +--rw mac-address    -> ../config/mac-address
          |           +--rw vlan           -> ../config/vlan
          |           +--rw config
          |           |  +--rw mac-address?   yang:mac-address
          |           |  +--rw vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
          |           +--ro state
          |           |  +--ro mac-address?   yang:mac-address
          |           |  +--ro vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
          |           |  +--ro age?           uint64
          |           |  +--ro entry-type?    enumeration
          |           +--rw interface
          |              +--rw interface-ref
          |                 +--rw config
          |                 |  +--rw interface?      -> /oc-if:interfaces/interface/name
          |                 |  +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
          |                 +--ro state
          |                    +--ro interface?      -> /oc-if:interfaces/interface/name
          |                    +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
```
### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 Show Commands
The following CLI commands dump the output of internal FDB entries from STATE_DB with various options (filters), for example, filter based on MAC address, entry type (static/dynamic), VLAN interface, physical/port-channel interfaces and MAC address table count ..etc.
##### 3.6.2.2.1 show mac address-table
Syntax

show mac address-table [address ``<mac>`` | count | dynamic { address ``<mac>`` | vlan ``<id>`` | interface { Ethernet ``<id>`` | Port-channel ``<id>`` }} | interface { Ethernet ``<id>`` | Port-channel ``<id>`` } | static { address ``<mac>`` | vlan ``<id>`` | interface { Ethernet ``<id>`` | Port-channel ``<id>`` }} | vlan ``<id>`` }]

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| address `mac` | This option dumps the MACs matching the particular Mac
| count | This option provides the no. of MAC entries present in the system
| static | This option dumps the MAC entries matching the static entry type
| dynamic | This option dumps the MAC entries matching the dynamic entry type
| interface | This option dumps the MACs matching the particular physical/port-channel interface
| vlan | This option dumps the MACs matching the particular VLAN


Command Mode: User EXEC

Example:
````
sonic# show mac address-table
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1
20      00:11:22:33:44:55       static          Ethernet0
sonic#

sonic# show mac address-table count
MAC Entries for all vlans :
Dynamic Address Count :                  1
Static Address (User-defined) Count :    1
Total MAC Addresses in Use:              2
sonic#


sonic# show mac address-table address 00:11:22:33:44:55
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1
sonic#

sonic# show mac address-table dynamic
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1
sonic#

sonic# show mac address-table dynamic address 90:b1:1c:f4:9d:83
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1

sonic# show mac address-table vlan 1
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1

sonic# show mac address-table interface Ethernet 1
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1
sonic#

sonic# show mac address-table interface Ethernet 1
VlanId  Mac Address             Type            Interface
1       90:b1:1c:f4:9d:83       dynamic         Ethernet1
sonic#

sonic# show mac address-table static
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1
sonic#

sonic# show mac address-table static address 00:11:22:33:44:55
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1
sonic#

sonic# show mac address-table static vlan 20
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1

sonic# show mac address-table static interface Ethernet 1
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1
sonic#

sonic# show mac address-table vlan 20
VlanId  Mac Address             Type            Interface
20      00:11:22:33:44:55       static          Ethernet1
sonic#

````
#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
The following table maps SONIC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  – meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  – meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONIC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONIC.

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---:|:-----------:|:------------------:|-----------------------------------|
|show mac address-table |IS-CLI drop-in replace | | |
| show mac address-table count | IS-CLI drop-in replace |  | |
| show mac address-table address `mac` | IS-CLI drop-in replace |  | |
| show mac address-table dynamic  |IS-CLI drop-in replace | | |
| show mac address-table static } |IS-CLI drop-in replace | | |
| show mac address-table [interface { Ethernet/Port-channel } | IS-CLI drop-in replace | |
| show mac address-table [vlan ``<id>`` | IS-CLI drop-in replace | |



### 3.6.3 REST API Support
#### 3.6.3.1 GET
##### Get all support for MAC entries
- 'openconfig-network-instance:network-instances/network-instance={name}/fdb/mac-table/entries'

##### Get MAC entry with MAC address filter
- 'openconfig-network-instance:network-instances/network-instance={name}/fdb/mac-table/entries/entry={mac-address},{vlan}'



# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test
The following test cases will be tested using CLI/REST/GNMI management interfaces.
#### FDB test cases:
1) Verify whether "show mac address-table" command dumps all the MAC entries

2) Verify whether "show mac address-table count" command provides the no. of MAC entries present in the system

3) Verify whether "show mac address-table address `mac`" dumps the MACs matching the particular MAC

4) Verify whether "show mac address-table dynamic" dumps all the dynamic MACs and if the interface filter is given, dumps the MACs matching the particular interface.

5) Verify whether "show mac address-table static" dumps all the static MACs and if the interface filter is given, dumps the MACs matching the particular interface.

6) Verify whether "show mac address-table interface <ethernet/port-channel>" dumps the MACs matching particular interface.

7) Verify whether "show mac address-table vlan ``<id>``" dumps the MACs matching particular VLAN.


# 10 Internal Design Information
