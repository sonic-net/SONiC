# ARP/NDP get support

Implement get support for ARP/NDP using CLI/REST/gNMI SONiC management framework interfaces.

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
| Rev |     Date    |       Author                | Change Description                |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 09/10/2019  |  Venkatesan Mahalingam      | Initial version                   |

# About this Manual
This document provides general information about the ARP and NDP management get interfaces in SONiC.
# Scope
Covers Northbound get interface for the ARP/NDP feature, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| ARP                      | Address Resolution Protocol         |
| NDP                      | Neighbor Discovery Protocol         |

# 1 Feature Overview

The documents covers the various ARP and NDP get interfaces (CLI/REST/gNMI) for fetching the data from the back-end to the user using SONiC managment framework.

## 1.1 Requirements

![](http://10.59.132.240:9009/projects/csg_sonic/documentation/graphics/templates/test1.png)

### 1.1.1 Functional Requirements

Provide management framework get support to existing SONiC capabilities with respect to ARP/NDP.

### 1.1.2 Configuration and Management Requirements
 - Implement ARP/NDP CLI show Commands
 - REST get support for ARP/NDP
 - gNMI get support for ARP/NDP

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
The following open config YANG model is used to implement get support for ARP/NDP entries.
[https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ip.yang#L1205](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ip.yang#L1205)

```diff
module: openconfig-if-ip
  augment /oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface:
    +--rw ipv4
       +--rw neighbors
       |  +--rw neighbor* [ip]
       |     +--rw ip        -> ../config/ip
-      |     +--rw config
-      |     |  +--rw ip?                   oc-inet:ipv4-address
-      |     |  +--rw link-layer-address    oc-yang:phys-address
       |     +--ro state
       |        +--ro ip?                   oc-inet:ipv4-address
       |        +--ro link-layer-address    oc-yang:phys-address
-      |        +--ro origin?               neighbor-origin
augment /oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface:
    +--rw ipv6
       +--rw neighbors
       |  +--rw neighbor* [ip]
       |     +--rw ip        -> ../config/ip
-      |     +--rw config
-      |     |  +--rw ip?                   oc-inet:ipv6-address
-      |     |  +--rw link-layer-address    oc-yang:phys-address
       |     +--ro state
       |        +--ro ip?                   oc-inet:ipv6-address
       |        +--ro link-layer-address    oc-yang:phys-address
-      |        +--ro origin?               neighbor-origin
-      |        +--ro is-router?            empty (Not supported by SONiC)
-      |        +--ro neighbor-state?       enumeration (Not supported by SONiC)
```
Also sonic yang (sonic-neigh.yang) is defined for fetching all entries from the neighbors table:
```diff
+--rw sonic-neigh
   +--ro NEIGH_TABLE
      +--ro NEIGH_TABLE_LIST* [ifname ip]
         +--ro ifname    string
         +--ro ip        inet:ip-prefix
         +--ro neigh?    yang:mac-address
         +--ro family?   enumeration
```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 Show Commands
The following CLI commands dump the output of internal ARP/NDP entries from APP_DB with various options (filters), for example, filter based on L3 interface, no. of ARP/NDP entries present in the system (summary), filter based on IP address and MAC address..etc.
##### 3.6.2.2.1 show ip arp
Syntax

show ip arp [interface { ethernet ``<port>`` [summary]  | port-channel ``<id>`` [summary]  | vlan ``<id>`` [summary] }]  [<A.B.C.D>] [mac-address ``<mac>``] [summary]

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/Port-channel/VLAN | This option dumps the ARPs matching the particular interface and summary option provides the no. of ARP entries matching the particular interface.
| A.B.C.B | This options dumps the ARP entry matching the particular IP
| mac-address | This options dumps the ARP entry matching the particular MAC Address|
| summary | This provides the count of ARP entries present in the system

Command Mode: User EXEC

Example:
````
sonic# show ip arp
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   vlan20            Ethernet0
20.0.0.5       00:11:22:33:44:55   vlan20            Ethernet0

sonic# sonic# show ip arp interface vlan 20
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
-------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   vlan20            Ethernet0
20.0.0.5       00:11:22:33:44:55   vlan20            Ethernet0

sonic# show ip arp 20.0.0.2
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
-------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   vlan20            Ethernet0

sonic# show ip arp mac-address 90:b1:1c:f4:9d:ba
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   vlan20            Ethernet0

sonic# show ip arp summary
---------------
Total Entries
---------------
     2
````
##### 3.6.2.2.2 show ipv6 neighbors
show ipv6 neighbors [interface { ethernet ``<port>`` [summary]  | port-channel ``<id>`` [summary]  | vlan ``<id>`` [summary] }]  [<A::B>] [mac-address ``<mac>``] [summary]

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/Port-channel/VLAN |This option dumps the neighbors matching the particular interface and summary option provides the no. of neighbor entries matching the particular interface.
| A::B |This options dumps the neighbor entry matching the particular IP
| mac-address |This options dumps the neighbor entry matching the particular MAC Address|
| summary |This provides the count of neighbor entries present in the system

Command Mode: User EXEC

Example:
````
sonic# show ipv6 neighbors
------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address   Interface          Egress Interface
------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba  vlan20             Ethernet0
fe80::92b1:1cff:fef4:9d5d     90:b1:1c:f4:9d:5d  Ethernet0             -
fe80::92b1:1cff:fef4:9dba     90:b1:1c:f4:9d:ba  vlan20             Ethernet0

sonic# show ipv6 neighbors 20::2
-------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address    Interface         Egress Interface
-------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba   vlan20            Ethernet0

sonic# show ipv6 neighbors mac-address 90:b1:1c:f4:9d:ba
------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address    Interface         Egress Interface
------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba   vlan20            Ethernet0

sonic# show ipv6 neighbors summary
-------------
Total Entries
-------------
     3
````
#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
The following table maps SONiC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  \u2013 meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  \u2013 meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONiC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONiC.

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---:|:-----------:|:------------------:|-----------------------------------|
|show ip arp |IS-CLI drop-in replace | | |
| show ip arp summary | IS-CLI drop-in replace |  | |
| show ip arp interface { ethernet/port-channel/vlan } |IS-CLI drop-in replace | | |
|show ip arp interface { ethernet/port-channel/vlan } summary  | IS-CLI drop-in replace | | |
|show ip arp <A.B.C.D>  | IS-CLI drop-in replace | | |
|show ip arp mac-address-value | IS-CLI drop-in replace | | |
| | | | |
|show ipv6 neighbors |IS-CLI drop-in replace | | |
| show ipv6 neighbors summary | IS-CLI drop-in replace |  | |
| show ipv6 neighbors interface { ethernet/port-channel/vlan } |IS-CLI drop-in replace | | |
|show ipv6 neighbors interface { ethernet/port-channel/vlan } summary  | IS-CLI drop-in replace | | |
|show ipv6 neighbors ``<A::B>``  | IS-CLI drop-in replace | | |
|show ip arp mac-address ``<mac>`` | SONiC | | In order to match ARP command options, having mac-address based filter for this command as well|

### 3.6.3 REST API Support
#### 3.6.3.1 GET
##### Get all support for both ARPs and Neighbors
/openconfig-interfaces:interfaces/interface

##### ARPs get for matching particular interface
/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/neighbors

##### ARP get for matching particular interface and IP
/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/neighbors/neighbor={ip}

##### IPv6 Neighbors get for matching particular interfaces
/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/neighbors

##### IPv6 Neighbors get for matching particular interfaces and IP
/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/neighbors/neighbor={ip}

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug
# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test
The following test cases will be tested using CLI/REST/gNMI management interfaces.
#### ARP test cases:
1) Verify whether "show ip arp" command dumps all the ARP entries

2) Verify whether "show ip arp interface { ethernet/port-channel/vlan }" provides the dump of the ARPs learnt on the particular interface

3) Verify whether "show ip arp interface { ethernet/port-channel/vlan } summary" option provides the no. of ARPs learnt on the particular interface

4) Verify whether "show ip arp summary" option provides the no. of ARPs learnt in the system

5) Verify whether "show ip arp <A.B.C.D> " option provides the ARP entry matching the particular IP.

6) Verify whether "show ip arp mac-address" option provides the ARP entries matching the particular MAC.

#### NDP test cases:
1) Verify whether "show ipv6 neighbors" command dumps all the neighbor entries

2) Verify whether "show ipv6 neighbors interface { ethernet/port-channel/vlan }" provides the dump of the neighbors learnt on the particular interface

3) Verify whether "show ipv6 neighbors interface { ethernet/port-channel/vlan } summary" option provides the no. of neighbors learnt on the particular interface

4) Verify whether "show ipv6 neighbors summary" option provides the no. of neighbors learnt in the system

5) Verify whether "show ipv6 neighbors <A.B.C.D> " option provides the neighbor entry matching the particular IP.

6) Verify whether "show ipv6 neighbors mac-address" option provides the neighbor entries matching the particular MAC.
