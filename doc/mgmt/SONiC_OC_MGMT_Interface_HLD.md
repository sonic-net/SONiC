# Feature Name
OpenConfig support for Physical and Management interfaces via openconfig-interfaces.yang.
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
| 0.2 | 07/08/2019  |   Ravi Vasanthm     | Included information about rate utilization counters and rate interval data                   |

# About this Manual
This document provides general information about OpenConfig support for Physical and Management interfaces handling in SONiC.

# Scope
This document describes the high level design of OpenConfig support for Physical and Management interfaces handling feature.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| MGMT Intf                     | Management Interface                     |

# 1 Feature Overview
This feature will provide config set/get and status get support for Physical and Management interfaces according to the openconfig-interfaces.yang data model via CLI, REST, and gNMI.

https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/openconfig-interfaces.yang

## 1.1 Requirements


### 1.1.1 Functional Requirements

1. Provide CLI, REST and gNMI support for configuring and displaying physical and management interfaces attributes.
2. Enhance existing implementation of interfaces OpenConfig YANG to include physical and management interfaces handling.
3. Enhance existing top level show commands for interfaces to include physical and management interfaces details too.


### 1.1.2 Configuration and Management Requirements
1. Provide CLI/gNMI/REST support for configuring Physical and Management interfaces attributes.
2. Provide CLI/gNMI/REST support for show Physical and Management  interfaces attributes/parameters.


### 1.1.3 Scalability Requirements
N/A
### 1.1.4 Warm Boot Requirements
N/A
## 1.2 Design Overview
### 1.2.1 Basic Approach
Will be enhancing the management framework backend and transformer methods to add support for Physical and  Management interfaces Handling.


### 1.2.2 Container
All code changes will be done in management-framework container.

### 1.2.3 SAI Overview
 N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure physical and management interfaces via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide gNMI and REST support for get/set of Physical and Management interfaces attributes and CLI config and show commands to manage Management and physical interfaces.

# 3 Design
## 3.1 Overview
1. Transformer common app owns the openconfig-interface.yang models (which  means no separate app module required for interfaces YANG objects handling). Will be deleting the existing interface app module.
2. Provide annotations for required objects in interfaces and respective augmented models (openconfig-if-ethernet.yang and openconfig-if-ip.yang) so that transformer core and common app will take care of handling interfaces objects.
3. Provide transformer methods as per the annotations defined for openconfig-interfaces.yang and respective augmented models (openconfig-if-ethernet.yang and openconfig-if-ip.yang) to take care of model specific logic and validations.

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
N/A
### 3.3.2 Other Process
N/A.

## 3.4 SyncD
N/A.

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models
Can be reference to YANG if applicable. Also cover gNMI here.
List of YANG models will be need to add support for physical and management interfaces.
1. openconfig-if-ethernet.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/openconfig-if-ethernet.yang)
2. openconfig-if-ip.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/openconfig-if-ip.yang)
3. openconfig-interfaces.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/openconfig-interfaces.yang)
4. openconfig-interfaces-ext.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/mgmt-intf-support/models/yang/openconfig-interfaces-ext.yang)
5. sonic-mgmt-port.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/mgmt-intf-support/models/yang/sonic/sonic-mgmt-port.yang)
6. sonic-mgmt-interface.yang (https://github.com/project-arlo/sonic-mgmt-framework/blob/mgmt-intf-support/models/yang/sonic/sonic-mgmt-interface.yang)

Supported YANG objects and attributes:
```diff
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
          |  +--ro oc-intf-ext:rate-interval?         uint32
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
          |  |  +--ro oc-intf-ext:in-octets-per-second?    decimal64
          |  |  +--ro oc-intf-ext:in-pkts-per-second?      decimal64
          |  |  +--ro oc-intf-ext:in-bits-per-second?      decimal64
          |  |  +--ro oc-intf-ext:in-utilization?          oc-types:percentage
          |  |  +--ro oc-intf-ext:out-octets-per-second?   decimal64
          |  |  +--ro oc-intf-ext:out-pkts-per-second?     decimal64
          |  |  +--ro oc-intf-ext:out-bits-per-second?     decimal64
          |  |  +--ro oc-intf-ext:out-utilization?         oc-types:percentage
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

```
### Interface Counters RPC
```
module:sonic-counters
rpcs:
   +---x interface_counters
   |  +--ro output
   |     +--ro status?          int32
   |     +--ro status-detail?   string
   |     +--ro interfaces
   |        +--ro interface* [name]
   |           +--ro name     string
   |           +--ro state
   |              +--ro oper-status?   string
   |              +--ro counters
   |                 +--ro in-octets?               uint64
   |                 +--ro in-pkts?                 uint64
   |                 +--ro in-discards?             uint64
   |                 +--ro in-errors?               uint64
   |                 +--ro in-oversize-frames?      uint64
   |                 +--ro in-octets-per-second?    decimal64
   |                 +--ro in-pkts-per-second?      decimal64
   |                 +--ro in-bits-per-second?      decimal64
   |                 +--ro in-utilization?          oc-types:percentage
   |                 +--ro out-octets?              uint64
   |                 +--ro out-pkts?                uint64
   |                 +--ro out-discards?            uint64
   |                 +--ro out-errors?              uint64
   |                 +--ro out-oversize-frames?     uint64
   |                 +--ro out-octets-per-second?   decimal64
   |                 +--ro out-pkts-per-second?     decimal64
   |                 +--ro out-bits-per-second?     decimal64
   |                 +--ro out-utilization?         oc-types:percentage
```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
```
  sonic(config)# interface ?
  Ethernet    Interface commands
  Management  Management Interface commands

  sonic(config)# interface Management ?
      Management interface (0..0)


  sonic(config)# interface Management 0
  sonic(conf-if-eth0)#
    autoneg      Configure autoneg
    description  Textual description
    end          Exit to the exec Mode
    exit         Exit from current mode
    ip           Interface Internet Protocol config commands
    ipv6         Interface Internet Protocol config commands
    mtu          Configure MTU
    no           Negate a command or set its defaults
    shutdown     Disable the interface
    speed        Configure speed
```

Note: To configure management interface, select  Management subcommand under config->interface command and provide the interface id(for eth0 ID is 0).

# shutdown
`shutdown | no shutdown` — Activate or deactivate an interface.
```
SONiC(config)# interface Management 0
SONiC(conf-if-eth0)# no shutdown
Success
SONiC(conf-if-eth0)# shutdown
Success
```
# mtu
mtu <val> | no mtu — Configures the maximum transmission unit (MTU) size of the interface in bytes.
```
SONiC(config)# interface Management 0
SONiC(conf-if-eth0)# mtu 2500
Success
SONiC(conf-if-eth0)# no mtu
Success
```
# description
description <string> | no description — Provides a text-based description of an interface.
```
sonic(conf-if-eth0)# description "Management0"
Success
sonic(conf-if-eth0)# no description
Success
```
# ip address
ip address <ip-address with mask> | no ip address <ip-address> — Configures an IPv4 address of the interface.
```
SONiC(config)# interface Management 0
SONiC(conf-if-eth0)# ip address 2.2.2.2/24
Success
SONiC(conf-if-eth0)# no ip address 2.2.2.2
Success
```
# ipv6 address
ipv6 address <ipv6-address with mask> | no ipv6 address <ipv6-address> — Configures the IPv6 address of the interface.
```
SONiC(config)# interface Management 0
SONiC(conf-if-eth0)# ipv6 address a::e/64
Success
SONiC(conf-if-eth0)# no ipv6 address a::e
Success
```
# speed
Port speed config of the interface (10/100/1000/10000/25000/40000/100000/auto)
```
sonic(conf-if-eth0)# speed 100
Success
sonic(conf-if-eth0)# no speed
Success
```
# autoneg
on|off  Autoneg config of the interface (on/off)
```
sonic(conf-if-eth0)# autoneg on
Success
sonic(conf-if-eth0)# autoneg off
Success
sonic(conf-if-eth0)# no autoneg
Success
```
#### 3.6.2.2 Show Commands
1. show interface Management — Displays details about Management interface (eth0).
```
# show interface Management 0
eth0 is up, line protocol is up
Hardware is Eth
Interface index is 11
IPV4 address is 44.2.3.4/24
Mode of IPV4 address assignment: MANUAL
IPV6 address is a::e/64
Mode of IPV6 address assignment: MANUAL
IP MTU 1500 bytes
LineSpeed 1000MB, Auto-negotiation on
Input statistics:
        0 packets, 0 octets
        0 Multicasts, 0 Broadcasts, 0 Unicasts
        0 error, 0 discarded
Output statistics:
        0 packets, 0 octets
        0 Multicasts, 0 Broadcasts, 0 Unicasts
        0 error, 0 discarded
```
2. show interface Ethernet 64 - display details about interface Ethernet64
```
sonic# show interface Ethernet 64
Ethernet64 is up, line protocol is up
Hardware is Eth
Mode of IPV4 address assignment: not-set
Mode of IPV6 address assignment: not-set
Interface IPv6 oper status: Disabled
IP MTU 9100 bytes
LineSpeed 25GB, Auto-negotiation off
Last clearing of "show interface" counters: 1970-01-01 00:00:00
30 seconds input rate 52 packets/sec, 84640 bits/sec, 10236 Bytes/sec
30 seconds output rate 45 packets/sec, 176760 bits/sec, 22432 Bytes/sec
Input statistics:
        6224 packets, 1787177 octets
        2855 Multicasts, 3369 Broadcasts, 0 Unicasts
        0 error, 3 discarded
Output statistics:
        74169 packets, 10678293 octets
        70186 Multicasts, 3983 Broadcasts, 0 Unicasts
        0 error, 0 discarded
```
##### CLI's list which need's to be enhanced to add Management interface details

1. show interface status - Displays a brief summary of the interfaces.

```
#show interface status
------------------------------------------------------------------------------------------
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             down           40GB           9100
Ethernet4           -                   up             up             40GB           9100
Ethernet8           -                   up             down           40GB           9100
Ethernet12          Ethernet12          up             down           40GB           9100
Ethernet16          -                   up             down           40GB           9100
Ethernet20          -                   up             down           40GB           9100
Ethernet24          -                   up             down           40GB           9100
```

2. show interface counters - Displays port statistics of all physical interfaces.

```
#show interface counters
------------------------------------------------------------------------------------------------
Interface      State     RX_OK     RX_ERR    RX_DRP    TX_OK     TX_ERR    TX_DRP
------------------------------------------------------------------------------------------------
Ethernet0      D         0         0         0         0         0         0
Ethernet4      U         1064      0         0         438       0         0
Ethernet8      D         0         0         0         0         0         0
Ethernet12     D         0         0         0         0         0         0
Ethernet16     D         0         0         0         0         0         0
Ethernet20     D         0         0         0         0         0         0
Ethernet24     D         0         0         0         0         0         0
Ethernet28     D         0         0         0         0         0         0
Ethernet32     U         431       0         0         438       0         0
Ethernet36     D         0         0         0         0         0         0
Ethernet40     D         0         0         0         0         0         0
```

3. show interface counters rate - Displays rate and utilization counters of all Ethernet and port channel
interfaces.

```
#show interface counters rate

-----------------------------------------------------------------------------------------------------------
Interface     Rate interval RX_MBPS   RX_MbPS  RX_PPS    RX_UTIl  TX_MBPS   TX_MbPS  TX_PPS     TX_UTIL(%)
              (seconds)     (MB/s)    (Mb/s)   (Pkts/s)   (%)     (MB/s)    (Mb/s)   (Pkts/s)   (%)
-----------------------------------------------------------------------------------------------------------
Ethernet0     10            0.00      0.00     0.00      0        0.00      0.00     0.00       0
Ethernet8     10            0.00      0.00     0.00      0        0.00      0.00     0.00       0
PortChannel1  10            0.00      0.00     0.00      0        0.00      0.00     0.00       0
PortChannel2  10            0.00      0.00     0.00      0        0.00      0.00     0.00       0
```
#### 3.6.2.3 Debug Commands
N/A
#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support
**GET**
- `/openconfig-interfaces:interfaces/interface={name}/state/openconfig-interfaces-ext:rate-interval`
```
Example Value
{
  "openconfig-interfaces-ext:rate-interval": 30
}
```

- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:in-octets-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:in-octets-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:in-pkts-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:in-pkts-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:in-bits-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:in-bits-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:in-utilization`
```
Example Value
{
  "openconfig-interfaces-ext:in-utilization": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:out-octets-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:out-octets-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:out-pkts-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:out-pkts-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:out-bits-per-second`
```
Example Value
{
  "openconfig-interfaces-ext:out-bits-per-second": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters/openconfig-interfaces-ext:out-utilization`
```
Example Value
{
  "openconfig-interfaces-ext:out-utilization": 0
}
```
- `/openconfig-interfaces:interfaces/interface={name}/state/counters`
```
Sample output:
{
  "openconfig-interfaces:counters": {
    "in-octets": 0,
    "in-pkts": 0,
    "in-unicast-pkts": 0,
    "in-broadcast-pkts": 0,
    "in-multicast-pkts": 0,
    "in-discards": 0,
    "in-errors": 0,
    "in-unknown-protos": 0,
    "in-fcs-errors": 0,
    "out-octets": 0,
    "out-pkts": 0,
    "out-unicast-pkts": 0,
    "out-broadcast-pkts": 0,
    "out-multicast-pkts": 0,
    "out-discards": 0,
    "out-errors": 0,
    "carrier-transitions": 0,
    "last-clear": 0,
    "openconfig-interfaces-ext:in-octets-per-second": 0,
    "openconfig-interfaces-ext:in-pkts-per-second": 0,
    "openconfig-interfaces-ext:in-bits-per-second": 0,
    "openconfig-interfaces-ext:in-utilization": 0,
    "openconfig-interfaces-ext:out-octets-per-second": 0,
    "openconfig-interfaces-ext:out-pkts-per-second": 0,
    "openconfig-interfaces-ext:out-bits-per-second": 0,
    "openconfig-interfaces-ext:out-utilization": 0
  }
}
```
##### Query interface COUNTERS
- rpc_sonic_counters_interface_counters: `sonic-counters:interface_counters`
```
Sample output:
{
  "sonic-counters:output": {
    "status": 0,
    "status-detail": "string",
    "interfaces": {
      "interface": [
        {
          "name": "string",
          "state": {
            "oper-status": "string",
            "counters": {
              "in-octets": 0,
              "in-pkts": 0,
              "in-discards": 0,
              "in-errors": 0,
              "in-oversize-frames": 0,
              "in-octets-per-second": 0,
              "in-pkts-per-second": 0,
              "in-bits-per-second": 0,
              "in-utilization": 0,
              "out-octets": 0,
              "out-pkts": 0,
              "out-discards": 0,
              "out-errors": 0,
              "out-oversize-frames": 0,
              "out-octets-per-second": 0,
              "out-pkts-per-second": 0,
              "out-bits-per-second": 0,
              "out-utilization": 0
            }
          }
        }
      ]
    }
  }
}
```
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
1. Validate interfaces/interface/config enabled, mtu and description attributes get/set via gNMI and REST
2. Validate interfaces/interface/state enabled, mtu and description attributes get via gNMI and REST
3. Validate interfaces/interface/subinterface/subinterface/[ipv4|ipv6]/config ip attribute get/set via gNMI and REST.
4. Validate interfaces/interface/subinterface/subinterface/[ipv4|ipv6]/state ip attribute get/set via gNMI and REST.
5. Validate interfaces/interface/ethernet/config autoneg and speed attributes get/set via gNMI and REST.
6. Validate interfaces/interface/ethernet/state autoneg and speed attributes get/set via gNMI and REST.
7. Validate CLI command's listed above (section 3.6.2 CLI)

# 10 Internal Design Information
Internal BRCM information to be removed before sharing with the community.
