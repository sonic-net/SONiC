# OpenConfig support for interfaces
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
| 0.1 | 09/05/2019  |   Justine Jose, Tejaswi Goel, Arthi Sivanantham  | Initial version  |

# About this Manual
This document provides information about the northbound interface details for handling VLAN, PortChannel, Loopback interfaces and design approach for supporting "clear counters" commands.

# Scope
This document covers the "configuration" and "show" commands supported for VLAN, PortChannel and Loopback interfaces based on OpenConfig yang and the associated unit-test cases. It does not include the protocol design or protocol implementation details.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| VLAN                     | Virtual Local Area Network          |
| LAG                      | Link aggregation                    |
| LACP                     | Link Aggregation Control Protocol   |

# 1 Feature Overview
Add support for Ethernet, VLAN, Loopback and PortChannel create/set/get via CLI, REST and gNMI using openconfig-interfaces.yang and sonic-mgmt-framework container.

## 1.1 Requirements
Provide management framework capabilities to handle:
### ETHERNET
- MTU, IPv4 / IPv6, sflow, admin-status, description, nat-zone, <br />
  spanning-tree, switchport, channel-group and udld configuration
- Associated show commands
- Support clearing Ethernet counter values displayed by the "show interface" commands. <br />
  User will be able to clear counters for all interfaces or given interface type or given interface name.

### VLAN
- VLAN creation and deletion
- MTU configuration
- IPv4 / IPv6 address configuration
- IPv4 / IPv6 address removal
- Addition of tagged / un-tagged ports to VLAN
- Removal of tagged / un-tagged ports from VLAN
- Associated show commands

### PortChannel
- PortChannel creation and deletion
- Addition of ports to PortChannel
- Removal of ports from PortChannel
- MTU, admin-status and IP address configuration
- Min-links, mode, LACP fallback and interval configuration during creation of PortChannel
- Associated show commands
- Support clearing PortChannel counter values.

### Loopback
- Loopback creation and deletion
- IPv4 / IPv6 address configuration
- IPv4 / IPv6 address removal
- Associated show commands

### 1.1.1 Functional Requirements
1. Provide management framework support to existing SONiC capabilities with respect to Ethernet, VLAN, Loopback and PortChannel.
2. Clear Counters support for Ethernet and PortChannel interfaces.

### 1.1.2 Configuration and Management Requirements
- CLI configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

## 1.2 Design Overview

### 1.2.1 Basic Approach
1. Provide transformer methods in sonic-mgmt-framework container for handling Ethernet, VLAN, PortChannel and Loopback.
2. The "clear counters" commands to be used for getting snapshot of COUNTERS table into COUNTERS_BACKUP table in COUNTERS_DB. Saved counter values establish a baseline upon which subsequent "show interface" commands counter values are calculated.

### 1.2.2 Container
All code changes will be done in management-framework container

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure VLAN, PortChannel and Loopback interface via CLI, gNMI and REST interfaces
## 2.2 Functional Description
1. Provide CLI, gNMI and REST support for VLAN, PortChannel and Loopback related commands handling.
2. Provide CLI/REST/gNMI commands to reset interface statistics.

# 3 Design
## 3.1 Overview
### VLAN
Enhancing the management framework backend code and transformer methods to add support for VLAN handling

### PORTCHANNEL
Enhancing the management framework backend code and transformer methods to add support for PortChannel interface handling.<br>
To support PortChannel GETs, data is fetched from 3 different places:
1. PortChannel data from LAG_TABLE and LAB_MEMBER_TABLE
2. LACP data from Teamd
3. PortChannel Counters information from COUNTER DB

LACP protocol stack runs in `teamd` docker and `teamdctl` utility is used to fetch LACP data. To service north bound request from clients, we use `docker exec teamd ***` command in mgmt-framework docker (similar approach to SONiC click command) to get the required data.

PortChannel link information and counters are obtained from REDIS DB using common app implemented by transformer.


Configuration of LACP protocol parameters (LACP interval, mode, MAC, priority) using management framework is **not supported** due to the following limitations:

- No support for LACP protocol specific configurations in SONiC. For example, on creating port channels and adding members to it, “teammgrd” daemon (in SONiC code base):
1.      Reads user configuration from CONFIG DB
2.      Spawns an instance of libteamd (open source package for LACP protocol stack) with the given user configurations and a couple of default LACP options.

Now to support protocol specific configurations we would need to enhance:
1.      REDIS CONFIG DB PORTCHANNEL Table schema
2.      Code changes in “teammgrd” to read these protocol specific configs and to use “teamdctl” control utility to configure the above-mentioned configs to an already running "teamd" daemon.

- `teamd` supports only a few options (not LACP-specific) to be configured via `teamdctl` utility. This could be overcome by enhancing `teamd` to support configuration of LACP parameters.

Due to the above mentioned reasons, LACP **protocol specific configuration is not supported** in the initial release.

### LOOPBACK
Enhancing the management framework backend code and transformer methods to add support for loopback handling

### Clear Counters support for PortChannel and Ethernet Interfaces
1. Enhancing the management framework backend to support clearing of interface statistics. When user issues "clear counters" command, the current snapshot of COUNTERS table will be stored into a new table COUNTERS_BACKUP, with an extra key for each interface to store time stamp when counters were cleared.
2. For "show interface" commands, counter values will be calculated by doing a diff between the COUNTERS & COUNTERS_BACKUP tables.
3. In contrast, click CLI "sonic-clear counters" command stores counter values from COUNTERS table into a **file** ( "/tmp/portstat<uid>" ) using python's pickle module, but we plan to go with a different approach of storing counter values in Redis DB to keep the backend code less complex.

## 3.2 DB Changes

### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB
1. Will be adding a new table COUNTERS_BACKUP to save counter values and last reset time per interface.
2. Will be reading data from COUNTERS_PORT_NAME_MAP and COUNTERS tables.

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A
## 3.6 User Interface
### 3.6.1 Data Models
#### List of yang models required for VLAN interface management.
1. [openconfig-if-interfaces.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang)
2. [openconfig-if-ethernet.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ethernet.yang)
3. [openconfig-if-ip.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ip.yang)
4. [sonic-vlan.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/sonic/sonic-vlan.yang)


#### List of yang models required for PortChannel interface management:
1. [openconfig-if-aggregate.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-aggregate.yang)
2. [openconfig-interfaces.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang)
3. [openconfig-lacp.yang](https://github.com/openconfig/public/blob/master/release/models/lacp/openconfig-lacp.yang)
4. [sonic-portchannel-interface.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/src/cvl/testdata/schema/sonic-portchannel-interface.yang)
5. [sonic-portchannel.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/src/cvl/testdata/schema/sonic-portchannel.yang)

#### List of yang models required for Loopback interface management:
1. [openconfig-if-interfaces.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang)
2. [openconfig-if-ip.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ip.yang)


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
          |     |  +--rw oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |     |  +--rw oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:trunk-vlans*      union
+         |     +--ro oc-vlan:state
          |        +--ro oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |        +--ro oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:trunk-vlans*      union
          +--rw oc-if-aggregate:aggregation
+         |  +--rw oc-vlan:switched-vlan
+         |     +--rw oc-vlan:config
          |     |  +--rw oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |     |  +--rw oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |     |  +--rw oc-vlan:trunk-vlans*      union
+         |     +--ro oc-vlan:state
          |        +--ro oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
          |        +--ro oc-vlan:native-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:access-vlan?      oc-vlan-types:vlan-id
+         |        +--ro oc-vlan:trunk-vlans*      union
          +--rw subinterfaces
+            +--rw subinterface* [index]
+               +--rw index         -> ../config/index
+               +--rw oc-ip:ipv4
+               |  +--rw oc-ip:addresses
+               |  |  +--rw oc-ip:address* [ip]
+               |  |     +--rw oc-ip:ip        -> ../config/ip
+               |  |     +--rw oc-ip:config
+               |  |     |  +--rw oc-ip:ip?              oc-inet:ipv4-address
+               |  |     |  +--rw oc-ip:prefix-length?   uint8
+               |  |     +--ro oc-ip:state
+               |  |     |  +--ro oc-ip:ip?              oc-inet:ipv4-address
+               |  |     |  +--ro oc-ip:prefix-length?   uint8
+               +--rw oc-ip:ipv6
+                  +--rw oc-ip:addresses
+                  |  +--rw oc-ip:address* [ip]
+                  |     +--rw oc-ip:ip        -> ../config/ip
+                  |     +--rw oc-ip:config
+                  |     |  +--rw oc-ip:ip?              oc-inet:ipv6-address
+                  |     |  +--rw oc-ip:prefix-length    uint8
+                  |     +--ro oc-ip:state
+                  |     |  +--ro oc-ip:ip?              oc-inet:ipv6-address
+                  |     |  +--ro oc-ip:prefix-length    uint8
+         +--rw oc-eth:ethernet
+         |  +--rw oc-eth:config
          |  |  +--rw oc-eth:mac-address?           oc-yang:mac-address
          |  |  +--rw oc-eth:auto-negotiate?        boolean
          |  |  +--rw oc-eth:duplex-mode?           enumeration
          |  |  +--rw oc-eth:port-speed?            identityref
          |  |  +--rw oc-eth:enable-flow-control?   boolean
+         |  |  +--rw oc-lag:aggregate-id?          -> /oc-if:interfaces/interface/name
+         |  +--ro oc-eth:state
          |  |  +--ro oc-eth:mac-address?              oc-yang:mac-address
          |  |  +--ro oc-eth:auto-negotiate?           boolean
          |  |  +--ro oc-eth:duplex-mode?              enumeration
          |  |  +--ro oc-eth:port-speed?               identityref
          |  |  +--ro oc-eth:enable-flow-control?      boolean
          |  |  +--ro oc-eth:hw-mac-address?           oc-yang:mac-address
          |  |  +--ro oc-eth:negotiated-duplex-mode?   enumeration
          |  |  +--ro oc-eth:negotiated-port-speed?    identityref
+         |  |  +--ro oc-lag:aggregate-id?             -> /oc-if:interfaces/interface/name
+         +--rw oc-lag:aggregation
+         |  +--rw oc-lag:config
+         |  |  +--rw oc-lag:lag-type?    aggregation-type
+         |  |  +--rw oc-lag:min-links?   uint16
+         |  |  +--rw if-agmnt:fallback?  boolean  //Augmented
+         |  |  +--rw if-agmnt:fast-rate? boolean  //Augmented
+         |  +--ro oc-lag:state
+         |  |  +--ro oc-lag:lag-type?    aggregation-type
+         |  |  +--ro oc-lag:min-links?   uint16
          |  |  +--ro oc-lag:lag-speed?   uint32
+         |  |  +--ro oc-lag:member*      oc-if:base-interface-ref
+         |  |  +--ro if-agmnt:fallback?  boolean  //Augmented
+         |  |  +--ro if-agmnt:fast-rate? boolean  //Augmented
```

#### List of yang models required for Clear Counters support:
1. [sonic-interface.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/sonic/sonic-interface.yang)
```diff
module: sonic-interface
    +--rw sonic-interface
       +--rw INTERFACE
          +--rw INTERFACE_LIST* [portname]
          |  +--rw portname    -> /prt:sonic-port/PORT/PORT_LIST/ifname
          |  +--rw vrf-name?   string
          +--rw INTERFACE_IPADDR_LIST* [portname ip_prefix]
             +--rw portname     -> /prt:sonic-port/PORT/PORT_LIST/ifname
             +--rw ip_prefix    inet:ip-prefix

+  rpcs:
+    +---x clear_counters
+       +---w input
+       |  +---w interface-param?   string
+       +--ro output
+          +--ro status?   int32
+          +--ro status-detail?   string

```
### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands

#### 3.6.2.1.1 VLAN
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
#### MTU Configuration
`mtu <mtu-val>`
```
sonic(conf-if-vlan20)# mtu 2500
sonic(conf-if-vlan20)# no mtu
```
#### MTU Removal
`no mtu <mtu-val>` --> Reset to default
```
sonic(conf-if-vlan20)# no mtu
```
#### IPv4 address configuration
`ip address <IPv4-address with prefix>`
```
sonic(conf-if-vlan20)# ip address 2.2.2.2/24
```
#### IPv4 address removal
`no ip address <IPv4-address>`
```
sonic(conf-if-vlan20)# no ip address 2.2.2.2
```
#### IPv6 address configuration
`ipv6 address <IPv6-address with prefix>`
```
sonic(conf-if-vlan20)# ipv6 address a::b/64
```
#### IPv6 address removal
`no ipv6 address <IPv6-address>`
```
sonic(conf-if-vlan20)# no ipv6 address a::b
```
#### Trunk VLAN addition to Member Port (Ethernet / Port-Channel)
`switchport trunk allowed Vlan <vlan_list>`
```
sonic(conf-if-Ethernet4)# switchport trunk allowed Vlan 20-22,40
sonic(conf-if-po4)# switchport trunk allowed Vlan 50,40
```
#### Trunk VLAN removal from Member Port (Ethernet / Port-Channel)
`no switchport trunk allowed Vlan <vlan_list>`
```
sonic(conf-if-Ethernet4)# no switchport trunk allowed Vlan 20-22,40
sonic(conf-if-po4)# no switchport trunk allowed Vlan 50,40
```
#### Access VLAN addition to Member Port (Ethernet / Port-Channel)
`switchport access Vlan <vlan-id>`
```
sonic(conf-if-Ethernet4)# switchport access Vlan 5
sonic(conf-if-po4)# switchport access Vlan 5
```
#### Access VLAN removal from Member Port (Ethernet / Port-Channel)
`no switchport access Vlan`
```
sonic(conf-if-Ethernet4)# no switchport access Vlan
sonic(conf-if-po4)# no switchport access Vlan
```
#### 3.6.2.1.2 PORTCHANNEL
#### Create a PortChannel
`interface PortChannel <channel-number> [mode <active | on>] [ min-links <value> ] [fallback] [fast_rate] `<br>
- *Supported channel-number range: 0-9999*<br>
- *Supported Min links range: 1-255*<br>
- Default values:<br>
   admin status - UP<br>
   MTU - 9100<br>
   mode - active<br>
   min-links - 0<br>
   fallback - disabled<br>
   fast_rate - disabled<br>
```
sonic(config)# interface PortChannel 1 mode active min-links 2 fallback
```
```
sonic(config)# interface PortChannel 2 mode active fallback
```
```
sonic(config)# interface PortChannel 3 mode on min-links 3
```
```
sonic(config)# interface PortChannel 4 mode active fast_rate
```

#### Configure MTU
`mtu <mtu-val>`
```
sonic(conf-if-po1)# mtu 9000
```
#### MTU Removal
`no mtu` --> Reset to default value of 9100
```
sonic(conf-if-po1)# no mtu
```
#### Enable PortChannel
`no shutdown`
```
sonic(conf-if-po1)# no shutdown
```
#### Disable PortChannel
`shutdown`
```
sonic(conf-if-po1)# shutdown
```
#### Configures an IPv4 address
`ip address <ip-address/mask>`
```
sonic(conf-if-po1)# ip address 2.2.2.2/24
```
#### Remove IPv4 address
`no ip address <ip-address>`
```
sonic(conf-if-po1)# no ip address 2.2.2.2
```
#### Configure an IPv6 address
`ipv6 address <ipv6-address/mask>`
```
sonic(conf-if-po1)# ipv6 address a::e/64
```
#### Remove IPv6 address
`no ipv6 address <ipv6-address>`
```
sonic(conf-if-po1)# no ipv6 address a::e
```
#### Add port member
`channel-group <channel-number>`
```
sonic(config)# interface Ethernet4
sonic(conf-if-Ethernet4)# channel-group 1
```
#### Remove a port member
`no channel-group`
```
sonic(conf-if-Ethernet4)# no channel-group
```
#### Delete a PortChannel
`no interface PortChannel <channel-number>`
```
sonic(config)# no interface PortChannel 1
```
#### Clear counters commands
#### Clear all interface counters
`clear counters interface all` <br>
```
sonic# clear ?
  counters      Clear counters
sonic# clear counters interface ?
  Ethernet      Clear Ethernet interface counters
  PortChannel   Clear PortChannel interface counters
  all           Clear all interface counters
```
#### Clear counters for given interface type
`clear counters interface Ethernet`
`clear counters interface PortChannel`
```
sonic# clear counters interface Ethernet

Clear all Ethernet interface counters [confirm y/N]: y

sonic#
```
#### Clear counters for given interface
`clear counters interface Ethernet <port-id>` <br>
`clear counters interface PortChannel <channel-id>`
```
sonic# clear counters interface Ethernet ?
  Unsigned integer  Physical interface(Multiples of 4)
sonic# clear counters interface Ethernet 0
Clear counters on Ethernet0 [confirm y/N]: y

sonic#

sonic# clear counters interface PortChannel ?
  <0-9999>  PortChannel identifier
sonic# clear counters interface PortChannel 1

Clear counters on PortChannel1 [confirm y/N]: y

sonic#
```
#### 3.6.2.1.1 LOOPBACK
#### LOOPBACK Creation
`interface loopback <lo-id>`
```
sonic(config)# interface loopback 5
```
#### LOOPBACK Deletion
`no interface loopback <lo-id>`
```
sonic(config)# no interface loopback 5
```
#### Configures an IPv4 address
`ip address <ip-address/mask>`
```
sonic(conf-if-lo1)# ip address 2.2.2.2/24
```
#### Remove IPv4 address
`no ip address <ip-address>`
```
sonic(conf-if-lo1)# no ip address 2.2.2.2
```
#### Configure an IPv6 address
`ipv6 address <ipv6-address/mask>`
```
sonic(conf-if-lo1)# ipv6 address a::e/64
```
#### Remove IPv6 address
`no ipv6 address <ipv6-address>`
```
sonic(conf-if-lo1)# no ipv6 address a::e
```

#### 3.6.2.2 Show Commands
#### 3.6.2.2.1 VLAN
- sonic-vlan.yang is used for CLI #show commands.
#### Display VLAN Members detail
`show Vlan`
```
Q: A - Access (Untagged), T - Tagged
    NUM       Status       Q Ports
    5         Active       T Ethernet24
    10        Inactive
    20        Inactive     A PortChannel20
```
#### Display specific VLAN Members detail
`show Vlan <vlan-id>`
```
sonic# show Vlan 5
Q: A - Access (Untagged), T - Tagged
    NUM    Status     Q Ports
    5      Active     T Ethernet24
                      T PortChannel10
                      A Ethernet20
```
#### Display VLAN information
`show interface Vlan`
```
sonic# show interface Vlan
Vlan10 is up, line protocol is up
IP MTU 2500 bytes
IPv4 address is 10.0.0.20/31
Mode of IPv4 address assignment: MANUAL
Mode of IPv6 address assignment: not-set

Vlan20 is up, line protocol is down
IP MTU 5500 bytes
Mode of IPv4 address assignment: not-set
IPv6 address is a::b/64
Mode of IPv6 address assignment: MANUAL
```
#### Display specific VLAN Information
`show interface Vlan <vlan-id>`
```sonic# show interface Vlan 10
Vlan10 is up, line protocol is up
IP MTU 2500 bytes
IPv4 address is 10.0.0.20/31
Mode of IPv4 address assignment: MANUAL
IPv6 address is a::b/64
Mode of IPv6 address assignment: MANUAL
```
#### 3.6.2.2.2 PORTCHANNEL
#### Display summary information about PortChannels
- sonic-portchannel.yang and teamd used for CLI #show commands.
`show PortChannel summary`
```
sonic# show PortChannel summary
Flags: D - Down
       U - Up

---------------------------------------------------------------------------
Group   PortChannel            Type    Protocol    Member Ports
---------------------------------------------------------------------------
1       PortChannel1    (D)     Eth      LACP       Ethernet56(D)
                                                    Ethernet60(U)
10      PortChannel10   (U)     Eth      LACP       Ethernet40(D)
12      PortChannel12   (D)     Eth      NONE       Ethernet48(D)
111     PortChannel111  (D)     Eth      LACP

```
#### Show PortChannel Interface status and configuration
`show interface PortChannel` - Display details about all PortChannels.
<br>
`show interface PortChannel <id>` - Display details about a specific PortChannel.
```
sonic# show interface PortChannel 1
PortChannel 1 is up, line protocol is up, mode LACP
Fallback: Enabled
MTU 1532 bytes
Minimum number of links to bring PortChannel up is 1
LACP mode ACTIVE, interval SLOW, priority 65535, address 90:b1:1c:f4:a8:7e
Members in this channel: Ethernet56(Selected)
LACP Actor port 56  address 90:b1:1c:f4:a8:7e key 1
LACP Partner port 0  address 00:00:00:00:00:00 key 0
Last clearing of "show interface" counters: 2019-12-06 21:23:20
Input statistics:
        6224 packets, 1787177 octets
        2855 Multicasts, 3369 Broadcasts, 0 Unicasts
        0 error, 3 discarded
Output statistics:
        74169 packets, 10678293 octets
        70186 Multicasts, 3983 Broadcasts, 0 Unicasts
        0 error, 0 discarded
```

```
sonic# show interface PortChannel 2
PortChannel2 is up, line protocol is down, mode Static
Minimum number of links to bring PortChannel up is 1
MTU 9100
sonic#

```

```
sonic# show interface PortChannel 5
PortChannel5 is up, line protocol is down, mode LACP
Minimum number of links to bring PortChannel up is 1
Fallback: Disabled
MTU 9100
LACP mode ACTIVE interval FAST priority 65535 address 90:b1:1c:f4:aa:b2

sonic#

```

#### 3.6.2.2.3 LOOPBACK
#### Display specific LOOPBACK Information
`show interface Loopback <lo-id>`
```sonic# show interface Vlan 10
Loopback10 is up
IPv4 address is 10.0.0.20/31
Mode of IPv4 address assignment: MANUAL
IPv6 address is a::b/64
Mode of IPv6 address assignment: MANUAL
```
#### 3.2.2.3 Debug Commands
N/A

#### 3.2.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support
#### VLAN
**PATCH**
- `/openconfig-interfaces:interfaces/ interface={name}`
- `/openconfig-interfaces:interfaces/ interface={name}/config/mtu`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/addresses/address={ip}`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/addresses/address={ip}`


**DELETE**
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/interface={name}`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/addresses/address={ip}`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/addresses/address={ip}`

**GET**
- `/openconfig-interfaces:interfaces/ interface={name}/state/[admin-status | mtu | oper-status]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/State/[access-vlan | trunk-vlans]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/State/[access-vlan | trunk-vlans]`

#### PORTCHANNEL
**PATCH**
- Create a PortChannel: `/openconfig-interfaces:interfaces/interface={name}/config`
- Set min-links/mode/lacp fallback/lacp interval: `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/config/[min-links|lag-type|openconfig-interfaces-ext:fallback|openconfig-interfaces-ext:fast_rate]`
- Set MTU/admin-status: `/openconfig-interfaces:interfaces/interface={name}/config/[admin-status|mtu]`
- Set IP: `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address={ip}/config`
- Add member: `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/config/openconfig-if-aggregate:aggregate-id`

**DELETE**
- Delete a PortChannel: `/openconfig-interfaces:interfaces/interface={name}`
- Remove member: `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/config/openconfig-if-aggregate:aggregate-id`

**GET**
Get PortChannel details: 
- `/openconfig-interfaces:interfaces/interface={name}`
- `/openconfig-interfaces:interfaces/interface={name}/state/[mtu|admin-status|oper-status]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/state/[min-links|member|lag-type]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/state/[dell-intf-augments:fallback|dell-intf-augments:fast_rate]`

#### LOOPBACK
**PATCH**
- `/openconfig-interfaces:interfaces/interface={name}/config`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/addresses/address={ip}`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/addresses/address={ip}`

**DELETE**
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv4/addresses/address={ip}`
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface={index}/openconfig-if-ip:ipv6/addresses/address={ip}`
- `/openconfig-interfaces:interfaces/interface={name}`

**GET**
- `/openconfig-interfaces:interfaces/ interface={name}`

##### Clear interface statistics
- rpc_sonic_interface_clear_counters: `sonic-interface:clear_counters`

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
#### Configuration and Show via CLI
#### VLAN
| Test Name | Test Description |
| :------ | :----- |
| Create VLAN | Verify VLAN is configured |
| Configure MTU for VLAN | Verify MTU is configured |
| Remove MTU for VLAN | Verify MTU is reset to default |
| Configure access VLAN  | Verify access VLAN is configured |
| Configure trunk VLAN with access VLAN Id | Error should be thrown |
| Configure access VLAN again | Verify access VLAN is present |
| Configure IPv4 address for VLAN | Verify IPv4 address is configured |
| Configure IPv6 address for VLAN | Verify IPv6 address is configured |
| Remove IPv4 address from VLAN | Verify IPv4 address is removed |
| Remove IPv6 address from VLAN | Verify IPv6 address is removed |
| Configure trunk VLAN to physical and port-channel | Verify trunk VLAN is configured |
| Configure access VLAN with trunk VLAN Id | Error should be thrown |
| Configure trunk VLAN again | Verify trunk VLAN is present |
| Remove access VLAN | Verify access VLAN is removed |
| Remove trunk VLAN | Verify trunk VLANs are removed |
| Delete an Invalid VLAN | Error should be thrown |
| Delete the VLAN | Verify the VLAN is deleted |

#### PORTCHANNEL
| Test Name | Test Description |
| :------ | :----- |
| Create PortChannel | Verify PortChannel is configured <br> Verify error returned if PortChannel ID out of supported range |
| Configure min-links | Verify min-links is configured <br> Verify error returned if min-links value out of supported range |
| Remove min-links config | Verify min-links reset to default value |
| Configure MTU, admin-status| Verify MTU, admin-status configured |
| Configure Mode | Verify Mode configured using "show interface PortChannel" command |
| Configure Fallback | Verify Fallback configured using "show interface PortChannel" command |
| Configure Fast Rate | Verify Fast Rate configured using "show interface PortChannel" command |
| Configure IPv4 address | Verify IPv4 address configured |
| Configure IPv6 address | Verify IPv6 address configured |
| Add ports to PortChannel| Verify Port added using "show PortChannel" command |
| Remove IPv4 address from PortChannel | Verify IPv4 address is removed |
| Remove IPv6 address from PortChannel | Verify IPv6 address is removed |
| Remove ports from PortChannel| Verify Port removed using "show PortChannel summary command" <br> Verify error returned if given PortChannel does not exist |
| Delete PortChannel| Verify PortChannnel removed using "show PortChannel summary command" and "teamshow" command |

#### LOOPBACK
| Test Name | Test Description |
| :------ | :----- |
| Create Loopback | Verify Loopback is configured |
| Configure IPv4 address | Verify IPv4 address is configured |
| Configure IPv6 address | Verify IPv6 address is configured |
| Remove IPv4 address from Loopback | Verify IPv4 address is removed |
| Remove IPv6 address from Loopback | Verify IPv6 address is removed |
| Delete Loopback | Verify the Loopback is deleted |

#### Clear Counters
The following test cases will be tested using CLI/REST/gNMI management interfaces.

| Test Name | Test Description |
| :------ | :----- |
| View current interface stats using "show interface counters" | Verify counters values displayed for active ports |
| Clear all interfaces stats | Verify there is a COUNTERS_BACKUP table in COUNTERS_DB |
| View current interface stats using "show interface counters" | Verify counters values are updated |
| Clear interface stats for all Ethernet interfaces | Verify counters values updated in COUNTERS_BACKUP table |
| View current stats using "show interface Ethernet" | Verify counters values updated  |
| Clear interface stats for all PortChannel interfaces | Verify counters values updated in COUNTERS_BACKUP table |
| View current stats using "show interface PortChannel" | Verify counters values updated  |
| Clear interface stats for given Ethernet interface | Verify counters values updated in COUNTERS_BACKUP table |
| View current stats using "show interface Ethernet <port-id>" | Verify counters values updated |
| Clear interface stats for given PortChannel interface | Verify counters values updated in COUNTERS_BACKUP table |
| View current stats using "show interface PortChannel <channel-id>" | Verify counters values updated |

#### Configuration and GET via gNMI and REST
- Verify the OpenConfig command paths in section 3.6.3 <br>
- Verify the JSON response for GET requests

# 10 Internal Design Information
N/A
