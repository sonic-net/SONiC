# ARP/NDP get support

Implement geti/clear support for ARP/NDP using CLI/REST/gNMI SONiC management framework interfaces.

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
| Rev |     Date   |      Author             | Change Description                           |
|:---:|:----------:|:-----------------------:|----------------------------------------------|
| 0.1 | 09/10/2019 | Venkatesan Mahalingam   | Initial version                              |
| 0.2 | 11/21/2019 | Syed Obaid Amin         | Added details for clear ip/ipv6 arp/neighbors|

# About this Manual
This document provides general information about getting and clearing ARP and NDP
entries in SONiC Management Framework.

# Scope
Covers Northbound get/clear  for the ARP/NDP feature, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| ARP                      | Address Resolution Protocol         |
| NDP                      | Neighbor Discovery Protocol         |

# 1 Feature Overview

Provide Management Framework functionality to get and clear ARP and neighbors table.

## 1.1 Requirements

![](http://10.59.132.240:9009/projects/csg_sonic/documentation/graphics/templates/test1.png)

### 1.1.1 Functional Requirements

Provide a Management Framework based implementation of following commands:
- show ip arp
- show ipv6 Neighbors
- clear ip arp
- clear ipv6 neighbors

The functionality should match the existing Click-based host interface provided by SONiC or IS-CLI (Industry Standard CLI)

### 1.1.2 Configuration and Management Requirements
 - Implement ARP/NDP CLI show/clear commands
 - REST get support for ARP/NDP
 - gNMI get support for ARP/NDP

### 1.1.3 Scalability Requirements
### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
In SONiC the neighbors' information is stored in NEIGH_TABLE of APPL_DB. The neighbor_sync process resolves mac address for neighbors using libnl and stores that information in NEIGH_TABLE. Also any static neighbor entry, made using Linux tools like "ip or arp", is also reflected in NEIGH_TABLE.
The 'show' commands leverages NEIGH_TABLE to show ARP/NDP entries. For clearing ARP/NDP tables, we use linux tools like 'ip'. The neighbor sync process then eventually updates
the NEIGH_TABLE and removes corresponding entries from it. The linux tool is invoked using RPC sent from the Northbound API  that clears the Linux neighbors cache using following commands:

For ipv4:
```
All entries:
 sudo ip -4 -s -s neigh flush all

Specific entry:
 sudo ip -4 neigh del <ip> dev <interface name>
```

For ipv6:
```
All entries:
 sudo ip -6 -s -s neigh flush all

Specific entry:
 sudo ip -6 neigh del <ip> dev <interface name>
```
NOTE: To execute these commands, the docker image should be running in the **privileged** mode.

This triggers neighbor sync process of SONiC and eventually the corresponding entries in NEIGH_TABLE get deleted.

Without any argument both commands will show or flush the complete ARP/NDP table.  However, a user can specify interface, IP or MAC address (in case of show only) to show or clear corresponding neighbor entries only. Help information and syntax details are provided if the command is preceded with '?'.

### 1.2.2 Container
This feature is implemented within the Management Framework container.

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
-      |        +--ro is-router?            empty
-      |        +--ro neighbor-state?       enumeration
```
Also sonic yang (sonic-neighbor.yang) is defined for fetching all entries from the NEIGH_TABLE and
for the RPC for clearing ARP/NDP entries:

```diff
module: sonic-neighbor
    +--rw sonic-neighbor
       +--ro NEIGH_TABLE
          +--ro NEIGH_TABLE_LIST* [ifname ip]
             +--ro ifname    union
             +--ro ip        inet:ip-prefix
             +--ro neigh?    yang:mac-address
             +--ro family?   enumeration

  rpcs:
    +---x clear-neighbors
       +---w input
       |  +---w force?    boolean
       |  +---w family?   enumeration
       |  +---w (option)?
       |     +--:(ip)
       |     |  +---w ip?       inet:ip-prefix
       |     +--:(ifname)
       |        +---w ifname?   union
       +--ro output
          +--ro response?   string
```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
##### 3.6.2.1.1 `clear ip arp`
Syntax:

`
clear ip arp [interface { Ethernet <port> | PortChannel <id> | Vlan <id> | Management <id> }] [<A.B.C.D>] [force]
`

The command returns a non-empty string in case of any error; for e.g. if the interface is not found or the IP address is not available in ARP or NDP table.

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/PortChannel/VLAN/Management*| This option clears the ARP entries matching the interface.
| A.B.C.D | This options clears the ARP entries matching the particular IP

\*The Management interface translates to "eth" internally. For e.g. "clear ip arp inerface Management 0" will flush the entries learnt on interface "eth0".

Command Mode: User EXEC
Example:
```
sonic# clear ip arp

sonic#

sonic# clear ip arp 192.168.1.1

sonic#

sonic# clear ipv6 neighbors Ethernet 0

sonic#
```

##### 3.6.2.1.2 `clear ipv6 neighbors`
Syntax:

`
clear ipv6 neighbors [interface { Ethernet <port> | PortChannel <id> | Vlan <id> | Management <id> }] [<A::B>] [force]
`

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/PortChannel/VLAN/Management*| This option clears the neighbors' entries matching the interface.
| A::B | This options clears the neighbors' entries matching the particular IPv6 address.

Command Mode: User EXEC

Example:
```
sonic# clear ipv6 neighbors

sonic#

sonic# clear ipv6 neighbors 20::2

sonic#

sonic# clear ipv6 neighbors Ethernet 0

sonic#
```
#### 3.6.2.2 Show Commands
The following CLI commands dump the output of internal ARP/NDP entries from APP_DB with various options (filters), for example, filter based on L3 interface, no. of ARP/NDP entries present in the system (summary), filter based on IP address and MAC address..etc.
##### 3.6.2.2.1 show ip arp
Syntax

show ip arp [interface { Ethernet ``<port>`` [summary]  | PortChannel ``<id>`` [summary]  | Vlan ``<id>`` [summary] |Management ``<id>`` [summary]}]  [<A.B.C.D>] [mac-address ``<mac>``] [summary] [vrf ``<vrf name>``]

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/PortChannel/VLAN/Management* | This option dumps the ARPs matching the particular interface and summary option provides the no. of ARP entries matching the particular interface.
| A.B.C.D | This options dumps the ARP entry matching the particular IP
| mac-address | This options dumps the ARP entry matching the particular MAC Address|
| summary | This provides the count of ARP entries present in the system|
| vrf | show ARP entries belong to the given VRF name

Command Mode: User EXEC

Example:
````
sonic# show ip arp
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   Vlan20            Ethernet0
20.0.0.5       00:11:22:33:44:55   Vlan20            Ethernet0

sonic# show ip arp interface Vlan 20
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
-------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   Vlan20            Ethernet0
20.0.0.5       00:11:22:33:44:55   Vlan20            Ethernet0

sonic# show ip arp 20.0.0.2
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
-------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   Vlan20            Ethernet0

sonic# show ip arp mac-address 90:b1:1c:f4:9d:ba
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   Vlan20            Ethernet0

sonic# show ip arp vrf Vrf_1
------------------------------------------------------------------------
Address        Hardware address    Interface         Egress Interface
------------------------------------------------------------------------
20.0.0.2       90:b1:1c:f4:9d:ba   Vlan20            Ethernet0
20.0.0.5       00:11:22:33:44:55   Vlan20            Ethernet0


sonic# show ip arp summary
---------------
Total Entries
---------------
     2
````
##### 3.6.2.2.2 show ipv6 neighbors
show ipv6 neighbors [interface { Ethernet ``<port>`` [summary]  | PortChannel ``<id>`` [summary]  | Vlan ``<id>`` [summary] }]  [<A::B>] [mac-address ``<mac>``] [summary] [vrf ``<vrf name>``]

Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| interface Ethernet/PortChannel/VLAN/Management* |This option dumps the neighbors matching the particular interface and summary option provides the no. of neighbor entries matching the particular interface.
| A::B |This options dumps the neighbor entry matching the particular IP
| mac-address |This options dumps the neighbor entry matching the particular MAC Address|
| summary |This provides the count of neighbor entries present in the system|
| vrf | show ARP entries belong to the given VRF name

Command Mode: User EXEC

Example:
````
sonic# show ipv6 neighbors
------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address   Interface          Egress Interface
------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba  Vlan20             Ethernet0
fe80::92b1:1cff:fef4:9d5d     90:b1:1c:f4:9d:5d  Ethernet0             -
fe80::92b1:1cff:fef4:9dba     90:b1:1c:f4:9d:ba  Vlan20             Ethernet0

sonic# show ipv6 neighbors 20::2
-------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address    Interface         Egress Interface
-------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba   Vlan20            Ethernet0

sonic# show ipv6 neighbors mac-address 90:b1:1c:f4:9d:ba
------------------------------------------------------------------------------------
IPv6 Address                  Hardware Address    Interface         Egress Interface
------------------------------------------------------------------------------------
20::2                         90:b1:1c:f4:9d:ba   Vlan20            Ethernet0

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
| show ip arp interface { Ethernet/PortChannel/Vlan/Management } |IS-CLI drop-in replace | | |
|show ip arp interface { Ethernet/PortChannel/Vlan/Management } summary  | IS-CLI drop-in replace | | |
|show ip arp <A.B.C.D>  | IS-CLI drop-in replace | | |
|show ip arp mac-address-value | IS-CLI drop-in replace | | |
| | | | |
|show ipv6 neighbors |IS-CLI drop-in replace | | |
| show ipv6 neighbors summary | IS-CLI drop-in replace |  | |
| show ipv6 neighbors interface { Ethernet/PortChannel/Vlan/Management } |IS-CLI drop-in replace | | |
|show ipv6 neighbors interface { Ethernet/PortChannel/Vlan/Management } summary  | IS-CLI drop-in replace | | |
|show ipv6 neighbors ``<A::B>``  | IS-CLI drop-in replace | | |
|show ip arp mac-address ``<mac>`` | SONiC | | In order to match ARP command options, having mac-address based filter for this command as well|
|clear ip arp |IS-CLI drop-in replace | | |
|clear ip arp interface { Ehternet/PortChannel/Vlan/Management} |IS-CLI drop-in replace | | |
|clear ip arp ``<A.B.C.D>``  | IS-CLI drop-in replace | | |
| | | | |
|clear ipv6 neighbors |IS-CLI drop-in replace | | |
|clear ipv6 neighbors interface { Ethernet/PortChannel/Vlan/Management} |IS-CLI drop-in replace | | |
|clear ipv6 neighbors ``<A::B>``  | IS-CLI drop-in replace | | |


### 3.6.3 REST API Support
#### 3.6.3.1 GET
##### Get all support for both ARPs and Neighbors
/restconf/data/sonic-neigh:sonic-neigh/NEIGH_TABLE

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

2) Verify whether "show ip arp interface { Ethernet/PortChannel/Vlan/Management }" provides the dump of the ARPs learnt on the particular interface

3) Verify whether "show ip arp interface { Ethernet/PortChannel/Vlan/Management } summary" option provides the no. of ARPs learnt on the particular interface

4) Verify whether "show ip arp summary" option provides the no. of ARPs learnt in the system

5) Verify whether "show ip arp <A.B.C.D> " option provides the ARP entry matching the particular IP.

6) Verify whether "show ip arp mac-address" option provides the ARP entries matching the particular MAC.

7) Verify whether "show ip arp vrf"  option provides the ARP entries matching the given VRF name.

#### NDP test cases:
1) Verify whether "show ipv6 neighbors" command dumps all the neighbor entries

2) Verify whether "show ipv6 neighbors interface { Ethernet/PortChannel/Vlan/Management }" provides the dump of the neighbors learnt on the particular interface

3) Verify whether "show ipv6 neighbors interface { Ethernet/PortChannel/Vlan/Management } summary" option provides the no. of neighbors learnt on the particular interface

4) Verify whether "show ipv6 neighbors summary" option provides the no. of neighbors learnt in the system

5) Verify whether "show ipv6 neighbors <A.B.C.D> " option provides the neighbor entry matching the particular IP.

6) Verify whether "show ipv6 neighbors mac-address" option provides the neighbor entries matching the particular MAC.

7) Verify whether "show ipv6 neighbors vrf"  option provides the NDP entries matching the given VRF name.

#### clear test cases:
1) Verify whether "clear ip arp" command clears all the ARP entries

2) Verify whether "clear ip arp interface { ethernet/port-channel/vlan }" clears the ARPs learnt on the particular interface

3) Verify whether "clear ip arp <A.B.C.D> " clears the ARP entry matching the particular IP.

4) Verify whether "clear ipv6 neighbors" command clears all the neighbors entries

5) Verify whether "clear ipv6 neighbors interface {Ethernet/PortChannel/Vlan/Management}" clears the neighbor's learnt on the particular interface

6) Verify whether "clear ipv6 neighbors <A::B>" clears the neighbor entry matching the particular IP.
