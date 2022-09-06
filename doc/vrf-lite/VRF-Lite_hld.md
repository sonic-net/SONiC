
# VRF-Lite for SONiC High Level Design Document #


## Table of Content
- [VRF-Lite for SONiC High Level Design Document](#vrf-lite-for-sonic-high-level-design-document)
  - [Table of Content](#table-of-content)
    - [Revision History](#revision-history)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
    - [Introduction](#introduction)
      - [VRF-Lite](#vrf-lite)
    - [Architecture](#architecture)
    - [Features Description](#features-description)
    - [High-Level Design](#high-level-design)
      - [MPLS add Design](#mpls-add-design)
      - [Show VRF-Lite Table](#show-vrf-lite-table)
    - [Command Line Interface](#command-line-interface)
      - [Add/del CLI Commands](#adddel-cli-commands)
      - [Bind/unbind interface CLI Commands](#bindunbind-interface-cli-commands)
      - [Show CLI Command](#show-cli-command)
      - [Using vrf prefix](#using-vrf-prefix)
    - [SAI API](#sai-api)
    - [Warm Boot and Fast boot Require](#warm-boot-and-fast-boot-require)
    - [Restrictions/Limitations](#restrictionslimitations)
       - [Unit Testcases](unit-testcases)
### Revision History
[ⓒ xFlow Research Inc](https://xflowresearch.com/) 
|Revision No. | Change Description | Author| Contributor | Date |
---------|--------------|-----------|--------------|-----
| 0.1          | initial Version| [Muhammad Haris Azaz Khan](https://github.com/haris-khan1596) & [Khubaib Ahmad Qureshy](https://github.com/KhoobBabe) | [Rida Hanif](https://github.com/ridahanif96) |Sep 7, 2022|



### Scope

This document describes the high-level design of Virtual Routing and Forwarding-Lite features in SONiC.

### Definitions/Abbreviations

| Abbreviation | Description |
|:-------------|:------------|
| VRF          | Virtual Routing and Forwarding|
| MPLS         | Multi-Protocol Label Switching|
| VRF-LITE     | Virtual Routing and Forwarding without MPLS network|
| PE           | Provider Edge|
| LAN          | Local Area Network|
| WAN          | Wide Area Network|
| VPN          | Virtual Private Network |
| VLAN         | Virtual Local Area Network|
| L3           | Layer-3 |

### Overview
VRF-lite is a subset of the full VRF solution. In a VRF-lite solution, there are multiple IP networks sharing the same routers, but no MPLS core is involved. So, VRF-lite is just the customer edge router part of VRF, without the provider edge router part. 

VRF-lite facilitates multiple separate routing tables within a single router - one routing table associated with each of the customer VPNs connected to the device. Multiple VRF instances are defined within a router. One or more Layer 3 interfaces (VLAN) are associated with each VRF instance forming an isolated VRF routing  domain. A Layer 3 interface cannot belong to more than one VRF instance at any time.

### Introduction

VRF-Lite provides a reliable mechanism for a network administrator to maintain multiple virtual routers on the same device. The goal of providing isolation among different VPN instances is accomplished without the overhead of heavyweight protocols (such as MPLS) used in secure VPN technologies. Overlapping address spaces can be maintained among the different VPN instances. 

Central to VRF-Lite is the ability to maintain multiple VRF tables on the same Provider Edge (PE) Router. VRF-Lite uses multiple instances of a routing protocol such as OSPF or BGP to exchange route information for a VPN among peer PE routers. The VRF-Lite capable PE router maps an input customer interface to a unique VPN instance. The router maintains a different VRF table for each VPN instance on that PE router. Multiple input interfaces may also be associated with the same VRF on the router, if they connect to sites belonging to the same VPN. This input interface can be a physical interface or a virtual Ethernet interface on a port. It provides network isolation on a single device at Layer 3. 

Each VRF domain can use the same or overlapping network addresses, as they have independent routing tables. This separation of the routing tables prevents communication to Layer 3 interfaces in other VRF domains on the same device. Each Layer 3 interface belongs to exactly one VRF instance and traffic between two Layer 3 interfaces on the same VRF instance is allowed as normal. But by default, interfaces in other VRF instances are not reachable as no route exists between the interfaces unless explicitly configured via Inter-VRF routing.
#### VRF-Lite

As vrf-lite is a subcategory of vrf it will be present under the table of vrf 

![VRF-Lite diagram](images/vrf-lite_hld/VRF_Lite_example.png "Sample VRF-Lite Scenario")

**Figure 1: Sample VRF-Lite Scenario**


In the diagram, there are two virtual routers (VRF-A, VRF-B) established in a single physical router. This way Customer-A devices can communicate with each other, and customer B devices can communicate with each other. And customer A devices cannot communicate with the devices of Customer B. Customer A and B's traffic is segregated, and they cannot communicate with each other.
### Architecture
Existing architecture of [VRF](https://github.com/sonic-net/SONiC/blob/master/doc/vrf/sonic-vrf-hld.md) is used with slide modification for VRF-Lite support.

![VRF-Lite Architecture ](images/vrf-lite_hld/VRF_LITE_Arch.png "Architecture")

**Figure 2: Architecture**

In this improvement,  implementation of  a MPLS lookback  is done which checks if MPLS is enabled when we bind an interface to a vrf-lite. 

### Features Description
- Multiple IP networks share the same routers in a VRF-lite configuration, but there is 
no MPLS core. VRF-lite therefore only consists of the customer edge router portion of VRF, not the provider edge router portion.
- VRF-Lite is a hop-by-hop solution. That means each and every L3 device from one end to the other needs to be configured with VRF-Lite.
- Enterprises sometimes use this when they have multiple networks with the same IP addresses or certain segments that must travel through a firewall.

### High-Level Design
#### MPLS add Design
![Modification in MPLS add](images/vrf-lite_hld/modified_MPLS_add_vrflite.png "modification in MPLS add command")

**Figure 3: Sequence diagram of the modification in MPLS add command**

The SONiC CLI Command of “MPLS add” is slightly changed for Vrf-lite. The change is very minimal, we just introduce a simple check to verify whether the interface is added to Vrf-lite or not. If an interface is added to Vrf-lite the user is prompted with a message that you can not add MPLS to this interface as Vrf-lite does not support MPLS else, it is the same as mentioned in [MPLS hld](https://github.com/sonic-net/SONiC/blob/master/doc/mpls/MPLS_hld.md).
#### Show VRF-Lite Table
![Show VRF-Lite diagram](images/vrf-lite_hld/show_vrflite_design_diagram.png "Show VRF-Lite Sequence Diagram")

**Figure 4: Show VRF-Lite Sequence Diagram**
### Command Line Interface
#### Add/del CLI Commands
1. The ```add vrf-lite``` command will do the following:
   - Takes <vrflite_name> with the “Vrflite” prefix as input 
   - Add vrf-lite in the Vrf table in config_db.
```
//create a vrf-lite:
$ sudo config vrflite add <vrflite_name>
$ sudo config vrflite add Vrflite-blue
```
2. The ``del vrf-lite`` command will do the following:
   - get interface list belonging to Vrflite-blue from app_db
   - delete interface(s) IP addresses
   - unbind interfaces(s) from Vrflite-blue
   - delete Vrflite-blue from Vrf table in config_db
```
//remove a vrf-lite:
$ sudo config vrflite del <vrflite_name>
$ sudo config vrflite del Vrflite-blue
```
#### Bind/unbind interface CLI Commands
1. The ``interface vrflite bind`` command will do the following:
   - Read info from `config_db`
   - Check if IP addresses exist for Ethernet0. If yes, delete all IP addresses from the interface
   - Check if MPLS exists for Ethernet0. If yes, disable it.
   - Bind the interface to Vrflite-blue (it will eventually create Ethernet0 router interface)
```
//bind an interface to a vrf-lite
$ sudo config interface vrflite bind <interface_name> <vrflite_name>
$ sudo config interface vrflite bind Ethernet0 Vrflite-blue
```
2. The ``interface vrflite unbind`` command will do the following:
   - Read `config_db`
   - Check if IP addresses exist. If yes, delete all IP addresses from the interface
   - Delete all attributes, delete router interface(Ethernet0)
```
//unbind an interface from a vrf-lite
$ sudo config interface vrflite unbind <interface_name>
$ sudo config interface vrflite unbind Ethernet0
```
#### Show CLI Command
The `show vrflite` command gives the list of all the vrf-lite present in the Vrf table
```
//show all the vrf-lite tables
$ show vrflite [<vrflite_name>]
```
#### Using vrf prefix
Since VRF-lite is a subset of VRF, we can accomplish the same thing using the VRF command prefix. However, only vrflite must be specified when using the “Vrflite” prefix.

### SAI API
N/A
### Warm Boot and Fast boot Require
N/A
### Restrictions/Limitations
#### Unit Testcases
**Functional Test cases**
- Verify that the interface bind to vrf-lite has not MPLS enabled.
- Verify that MPLS will not be enabled when vrf-lite is binded to that interface.

**CLI Test cases**
- Verify `show vrflite` command will show only the Vrf-lite table.
- Verify `add/del` command of Vrflite command set will only add/delete Vrflite prefix Vrfs.
- Verify `add/del` command of Vrf command set will also add/delete Vrflite prefix Vrfs.
- Verify `bind/unbind` command of Vrflite command set can only bind/unbind Vrflite.
- Verify `unbind` command of Vrf command set can also unbind Vrflite.


