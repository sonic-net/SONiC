# Feature Name
Openconfig support for Management Interface via openconfig-interfaces.yang.
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/09/2019  |   Ravi Vasanthm     | Initial version                   |

# About this Manual
This document provides general information about openconfig support for Management interface handling in SONIC.

# Scope
This document describes the high level design of openconfig support for Management interface handling feature. Call out any related design that is not covered by this document

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| MGMT Intf                     | Management Interface                     |

# 1 Feature Overview
Currently SONIC does not support managing/configuring Management interface parameters via CLI, REST and GNMI. As part of this feature will be providing config set/get and status get support for Management interface via openconfig-interfaces.yang.

## 1.1 Requirements

![](http://10.59.132.240:9009/projects/csg_sonic/documentation/graphics/templates/test1.png)

### 1.1.1 Functional Requirements

1. Provide CLI, REST and GNMI support for configuring and displaying management interface attributes.
2. Enhance existing implementation of interfaces yang to include management interface handling.
3. Enhance existing top level show commands for interfaces to include management interface details too.


### 1.1.2 Configuration and Management Requirements
1. Provide CLI/GNMI/REST support for configuring Management interface attributes.
2. Provide CLI/GNMI/REST support for show Management  interface attributes/parameters.


### 1.1.3 Scalability Requirements
N/A
### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
Will be enhancing the management framework management backed code and transformer methods to add support for Management interface Handling.


### 1.2.2 Container
All code changes will be done in management-framework container.

### 1.2.3 SAI Overview
 N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure management interface via GNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide GNMI and REST support for get/set of Management interface attributes and CLI config and show commands to manage Management interface.

# 3 Design
## 3.1 Overview
1. Transformer common app owns the openconfig-interface.yang models (which  means no separate app module required for interfaces yang objects handling) Will be deleting the existing interface app module.
2. Provide annotations for required objects in interfaces and respective augmented models so that transformer core and common app will take care of handling interfaces objects.
3. Provide transformer methods as per the annotations defined for interfaces and respective augmented models to take care of model specific logics and validations.

## 3.2 DB Changes
N/A
### 3.2.1 CONFIG DB
No changes to database schema's just populate/read Config DB.
### 3.2.2 APP DB
No changes to database schema's just read APP DB for getting interface attributes.
### 3.2.3 STATE DB
No changes to database schema's just read state DB for getting interface state details.
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB
No changes to database schema's just read COUNTER DB for getting interface counters information.

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
N/A.

## 3.4 SyncD
N/A.

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models
Can be reference to YANG if applicable. Also cover GNMI here.
List of yang models will be need to add support for management interface management.
1. openconfig-if-ethernet.yang
2. openconfig-if-ip.yang
3. openconfig-interfaces.yang

Supported yang objects and attributes:

module: openconfig-interfaces

    +--rw interfaces
       +--rw interface* [name]
          +--rw name                   -> ../config/name
          +--rw config
          |  +--rw name?            string
          |  +--rw type             identityref
          |  +--rw mtu?             uint16
          |  +--rw description?     string
          |  +--rw enabled?         boolean
          +--ro state
          |  +--ro name?            string
          |  +--ro type             identityref
          |  +--ro mtu?             uint16
          |  +--ro description?     string
          |  +--ro enabled?         boolean
          |  +--ro ifindex?         uint32
          |  +--ro admin-status     enumeration
          |  +--ro oper-status      enumeration
          |  +--ro counters
          |  |  +--ro in-octets?             oc-yang:counter64
          |  |  +--ro in-pkts?               oc-yang:counter64
          |  |  +--ro in-unicast-pkts?       oc-yang:counter64
          |  |  +--ro in-broadcast-pkts?     oc-yang:counter64
          |  |  +--ro in-multicast-pkts?     oc-yang:counter64
          |  |  +--ro in-discards?           oc-yang:counter64
          |  |  +--ro in-errors?             oc-yang:counter64
          |  |  +--ro out-octets?            oc-yang:counter64
          |  |  +--ro out-pkts?              oc-yang:counter64
          |  |  +--ro out-unicast-pkts?      oc-yang:counter64
          |  |  +--ro out-broadcast-pkts?    oc-yang:counter64
          |  |  +--ro out-multicast-pkts?    oc-yang:counter64
          |  |  +--ro out-discards?          oc-yang:counter64
          |  |  +--ro out-errors?            oc-yang:counter64
          +--rw subinterfaces
          |  +--rw subinterface* [index]
          |     +--rw index           -> ../config/index
          |     +--rw oc-ip:ipv4
          |     |  +--rw oc-ip:addresses
          |     |  |  +--rw oc-ip:address* [ip]
          |     |  |     +--rw oc-ip:ip        -> ../config/ip
          |     |  |     +--rw oc-ip:config
          |     |  |     |  +--rw oc-ip:ip?              oc-inet:ipv4-address
          |     |  |     |  +--rw oc-ip:prefix-length?   uint8
          |     |  |     +--ro oc-ip:state
          |     |  |     |  +--ro oc-ip:ip?              oc-inet:ipv4-address
          |     |  |     |  +--ro oc-ip:prefix-length?   uint8
          |     +--rw oc-ip:ipv6
          |        +--rw oc-ip:addresses
          |        |  +--rw oc-ip:address* [ip]
          |        |     +--rw oc-ip:ip        -> ../config/ip
          |        |     +--rw oc-ip:config
          |        |     |  +--rw oc-ip:ip?              oc-inet:ipv6-address
          |        |     |  +--rw oc-ip:prefix-length    uint8
          |        |     +--ro oc-ip:state
          |        |     |  +--ro oc-ip:ip?              oc-inet:ipv6-address
          |        |     |  +--ro oc-ip:prefix-length    uint8
          +--rw oc-eth:ethernet
          |  +--rw oc-eth:config
          |  |  +--rw oc-eth:auto-negotiate?        boolean
          |  |  +--rw oc-eth:port-speed?            identityref
          |  +--ro oc-eth:state
          |  |  +--rw oc-eth:auto-negotiate?        boolean
          |  |  +--ro oc-eth:port-speed?               identityref


### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
1. interface Management <Interface Id>
  CLI -> Interface syntax and output
  sonic(config)# interface
  Ethernet    Interface commands
  Management  Management Interface commands

sonic(config)# interface Management
  Unsigned integer  Management interface

sonic(config)# interface Management 0
  <cr>

sonic(config)# interface Management 0
sonic(conf-if-eth0)#
  autoneg      Configure autoneg
  description  Textual description
  ip           Interface Internet Protocol config commands
  ipv6         Interface Internet Protocol config commands
  mtu          Configure MTU
  no           Negate a command or set its defaults
  shutdown     Disable the interface
  speed        Configure speed

Note: To configure management interface, select  Management subcommand under config->interface command and provide the interface id(integer, for eth0 its 0 and so on). Once provided the interface ID, cli banner shows which management interface view user is at (sonic(conf-if-eth0)#). CLI backend/GNMI/REST clients should use actual interface names(eth<x>) for configuring or show.

2. shutdown
shutdown | no shutdown — Activates or deactivates an interface.
3. mtu
mtu <val> | no mtu — Configures the maximum transmission unit (MTU) size of the interface in bytes.
4. description
description <string> | no description — Provides a text-based description of an interface.
5. ip address
ip address <ip-address with mask> | no ip address <ip-address> — Configures an IPv4 address of the interface.
6. ipv6 address
ipv6 address <ipv6-address with mask> | no ipv6 address <ipv6-address> — Configures the IPv6 address of the interface.
7. speed
speed <10|100|1000 MBPS> | no speed - Configures speed of the management interface.
8. autoneg
on/off - auto negotiation mode  on/off

#### 3.6.2.2 Show Commands
1. show interface Management — Displays details about Management interface (eth0).
##### CLI's list which need's to be enhanced to add Management interface details>
1. show interface status - Need to add eth0 interface as part of interfaces status list.
2. show interface counters - - Need to add eth0 interface as part of interfaces counters list.
#### 3.6.2.3 Debug Commands
N/A
#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support

# 4 Flow Diagrams
N/A

# 5 Error Handling
Provide details about incorporating error handling feature into the design and functionality of this feature.

# 6 Serviceability and Debug
N/A

# 7 Warm Boot Support
N/A

# 8 Scalability
N/A.

# 9 Unit Test
1. Validate interfaces/interface/config enabled, mtu and description attributes get/set via GNMI and REST
2. Validate interfaces/interface/state enabled, mtu and description attributes get via GNMI and REST
3. Validate interfaces/interface/subinterface/subinterface/[ipv4|ipv6]/config ip attribute get/set via GNMI and REST.
4. Validate interfaces/interface/subinterface/subinterface/[ipv4|ipv6]/state ip attribute get/set via GNMI and REST.
5. Validate interfaces/interface/ethernet/config autoneg and speed attributes get/set via GNMI and REST.
6. Validate interfaces/interface/ethernet/state autoneg and speed attributes get/set via GNMI and REST.
7. Validate CLI command's listed above (section 3.6.2 CLI)

# 10 Internal Design Information
Internal BRCM information to be removed before sharing with the community.
