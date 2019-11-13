# PortChannel
OpenConfig support for PortChannel interfaces

# High Level Design Document
#### Rev 0.3

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
| 0.3 | 09/09/2019  |   Tejaswi Goel, Arthi Sivanantham  | Initial version   |

# About this Manual
This document provides general information about OpenConfig support for PortChannel interfaces handling in SONiC.

# Scope
This document covers the "configuration" and "show" commands supported for PortChannel interfaces based on OpenConfig YANG, and the Unit test cases. It does not include the protocol design or protocol implementation details.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          LAG             | Link aggregation                    |
|          LACP            | Link Aggregation Control Protocol   |

# 1 Feature Overview
Add support for PortChannel create/set/get via CLI, REST and gNMI using openconfig-interfaces.yang data model and sonic-mgmt-framework container.

## 1.1 Requirements
Provide management framework capabilities to handle:
- PortChannel creation and deletion
- Addition of ports to PortChannel
- Removal of ports from PortChannel
- Configure min-links, MTU, admin-status, IP address and LACP fallback.
- Show PortChannel details

### 1.1.1 Functional Requirements
Provide management framework support to existing SONiC capabilities with respect to PortChannel.

### 1.1.2 Configuration and Management Requirements
- CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

### 1.1.3 Scalability Requirements
key scaling factors -N/A
### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview

### 1.2.1 Basic Approach
Provide transformer methods in sonic-mgmt-framework container for PortChannel handling.

### 1.2.2 Container
All code changes will be done in management-framework container.

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure PortChannel interface via gNMI, REST and CLI interfaces.
## 2.2 Functional Description
Provide CLI, gNMI and REST support PortChannel related commands handling.

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to add support for PortChannel interface handling.

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

## 3.2 DB Changes
N/A

### 3.2.1 CONFIG DB
No changes to CONFIG DB schema. 

### 3.2.2 APP DB
Will be reading LAG_TABLE and LAG_MEMBER_TABLE for show commands.

### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB
Will be reading COUNTERS table.

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
List SONiC YANG models required:
1. [sonic-portchannel-interface.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/src/cvl/testdata/schema/sonic-portchannel-interface.yang)
2. [sonic-portchannel.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/src/cvl/testdata/schema/sonic-portchannel.yang)

List of yang models required for PortChannel interface management:
1. [openconfig-if-aggregate.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-aggregate.yang) 
2. [openconfig-interfaces.yang](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang) 
3. [openconfig-lacp.yang](https://github.com/openconfig/public/blob/master/release/models/lacp/openconfig-lacp.yang) 

Supported OpenConfig YANG objects and attributes are _highlighted in green_:
```diff

module: openconfig-interfaces
+   +--rw interfaces
+      +--rw interface* [name]
+         +--rw name                   -> ../config/name
+         +--rw config
          |  +--rw name?            string
          |  +--rw type             identityref
+         |  +--rw mtu?             uint16
          |  +--rw loopback-mode?   boolean
          |  +--rw description?     string
+         |  +--rw enabled?         boolean
          |  +--rw oc-vlan:tpid?    identityref
+         +--ro state
+         |  +--ro name?            string
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
+         +--rw subinterfaces
+         |  +--rw subinterface* [index]
+         |     +--rw index           -> ../config/index
          |     +--rw config
          |     |  +--rw index?         uint32
          |     |  +--rw description?   string
          |     |  +--rw enabled?       boolean
          |     +--ro state
          |     |  +--ro index?          uint32
          |     |  +--ro description?    string
          |     |  +--ro enabled?        boolean
          |     |  +--ro name?           string
          |     |  +--ro ifindex?        uint32
          |     |  +--ro admin-status    enumeration
          |     |  +--ro oper-status     enumeration
          |     |  +--ro last-change?    oc-types:timeticks64
          |     |  +--ro logical?        boolean
+         |     |  +--ro counters
+         |     |     +--ro in-octets?             oc-yang:counter64
+         |     |     +--ro in-pkts?               oc-yang:counter64
+         |     |     +--ro in-unicast-pkts?       oc-yang:counter64
+         |     |     +--ro in-broadcast-pkts?     oc-yang:counter64
+         |     |     +--ro in-multicast-pkts?     oc-yang:counter64
+         |     |     +--ro in-discards?           oc-yang:counter64
+         |     |     +--ro in-errors?             oc-yang:counter64
          |     |     +--ro in-unknown-protos?     oc-yang:counter64
          |     |     +--ro in-fcs-errors?         oc-yang:counter64
+         |     |     +--ro out-octets?            oc-yang:counter64
+         |     |     +--ro out-pkts?              oc-yang:counter64
+         |     |     +--ro out-unicast-pkts?      oc-yang:counter64
+         |     |     +--ro out-broadcast-pkts?    oc-yang:counter64
+         |     |     +--ro out-multicast-pkts?    oc-yang:counter64
+         |     |     +--ro out-discards?          oc-yang:counter64
+         |     |     +--ro out-errors?            oc-yang:counter64
          |     |     +--ro carrier-transitions?   oc-yang:counter64
          |     |     +--ro last-clear?            oc-types:timeticks64
+         |     +--rw oc-ip:ipv4
+         |     |  +--rw oc-ip:addresses
+         |     |  |  +--rw oc-ip:address* [ip]
+         |     |  |     +--rw oc-ip:ip        -> ../config/ip
+         |     |  |     +--rw oc-ip:config
+         |     |  |     |  +--rw oc-ip:ip?              oc-inet:ipv4-address
+         |     |  |     |  +--rw oc-ip:prefix-length?   uint8
+         |     |  |     +--ro oc-ip:state
+         |     |  |     |  +--ro oc-ip:ip?              oc-inet:ipv4-address
+         |     |  |     |  +--ro oc-ip:prefix-length?   uint8
          |     |  |     |  +--ro oc-ip:origin?          ip-address-origin
+         |     +--rw oc-ip:ipv6
+         |        +--rw oc-ip:addresses
+         |        |  +--rw oc-ip:address* [ip]
+         |        |     +--rw oc-ip:ip        -> ../config/ip
+         |        |     +--rw oc-ip:config
+         |        |     |  +--rw oc-ip:ip?              oc-inet:ipv6-address
+         |        |     |  +--rw oc-ip:prefix-length    uint8
+         |        |     +--ro oc-ip:state
+         |        |     |  +--ro oc-ip:ip?              oc-inet:ipv6-address
+         |        |     |  +--ro oc-ip:prefix-length    uint8
          |        |     |  +--ro oc-ip:origin?          ip-address-origin
          |        |     |  +--ro oc-ip:status?          enumeration
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
          |  |  +--ro oc-eth:counters
          |  |  |  +--ro oc-eth:in-mac-control-frames?    oc-yang:counter64
          |  |  |  +--ro oc-eth:in-mac-pause-frames?      oc-yang:counter64
          |  |  |  +--ro oc-eth:in-oversize-frames?       oc-yang:counter64
          |  |  |  +--ro oc-eth:in-undersize-frames?      oc-yang:counter64
          |  |  |  +--ro oc-eth:in-jabber-frames?         oc-yang:counter64
          |  |  |  +--ro oc-eth:in-fragment-frames?       oc-yang:counter64
          |  |  |  +--ro oc-eth:in-8021q-frames?          oc-yang:counter64
          |  |  |  +--ro oc-eth:in-crc-errors?            oc-yang:counter64
          |  |  |  +--ro oc-eth:in-block-errors?          oc-yang:counter64
          |  |  |  +--ro oc-eth:out-mac-control-frames?   oc-yang:counter64
          |  |  |  +--ro oc-eth:out-mac-pause-frames?     oc-yang:counter64
          |  |  |  +--ro oc-eth:out-8021q-frames?         oc-yang:counter64
+         |  |  +--ro oc-lag:aggregate-id?             -> /oc-if:interfaces/interface/name
+         +--rw oc-lag:aggregation
+         |  +--rw oc-lag:config
          |  |  +--rw oc-lag:lag-type?    aggregation-type
+         |  |  +--rw oc-lag:min-links?   uint16
+         |  +--ro oc-lag:state
          |  |  +--ro oc-lag:lag-type?    aggregation-type
+         |  |  +--ro oc-lag:min-links?   uint16
          |  |  +--ro oc-lag:lag-speed?   uint32
+         |  |  +--ro oc-lag:member*      oc-if:base-interface-ref
+         |  |  +--ro if-agmnt:fallback?  boolean  //Augmented

```

**Note:** openconfig-if-aggregate.yang data model is augmented to support LACP Fallback.

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands

#### Create a PortChannel
`interface PortChannel <channel-number>`<br>
- *Supported channel-number range: 0-9999*<br>
- *By default, the admin status is UP and MTU is 9100*
```
sonic(config)# interface PortChannel 1
```
#### Configure min-links
`minimum-links <number>`
<br>
- *As per [teamd](https://www.systutorials.com/docs/linux/man/5-teamd.conf/), supported range: 1-255 & default value:0*
```
sonic(config)# interface PortChannel 1
sonic(conf-if-po1)# minimum-links 1
```
#### Remove min-links
`no minimum-links` --> Reset to default value of 0
```
sonic(conf-if-po1)# no minimum-links 
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
#### Enable Fallback
`fallback enable`<br>
- *By default, LACP fallback is disabled*
```
sonic(conf-if-po1)# fallback enable
```
#### Disable Fallback
`no fallback`
```
sonic(conf-if-po1)# no fallback
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
#### Configure the port mode for the link in a PortChannel
`channel-group <channel-number> mode [active|on]`
- active — Sets Channeling mode to Active
- on — Sets Channeling mode to static
```
sonic(conf-if-Ethernet4)# channel-group 1 mode active
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

#### 3.6.2.2 Show Commands

##### Display summary information about PortChannels
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
111     PortChannel111  (D)     Eth      LACP

```
### Show Interface status and configuration
`show interface PortChannel` - Display details about all PortChannels.
<br>
`show interface PortChannel <id>` - Display details about a specific PortChannel.
```
sonic# show interface PortChannel 1
PortChannel 1 is up, line protocol is down, mode LACP
Fallback: Enabled
MTU 1532 bytes, IP MTU 1500 bytes
Minimum number of links to bring PortChannel up is 1
LACP mode active, interval slow, priority 65535, address 90:b1:1c:f4:a8:7e
Members in this channel: Ethernet56
selected True
LACP Actor port 56  address 90:b1:1c:f4:a8:7e key 1
LACP Partner port 0  address 00:00:00:00:00:00 key 0
Input statistics:
        6224 packets, 1787177 octets
        2855 Multicasts, 3369 Broadcasts, 0 Unicasts
        0 error, 3 discarded
Output statistics:
        74169 packets, 10678293 octets
        70186 Multicasts, 3983 Broadcasts, 0 Unicasts
        0 error, 0 discarded
```

#### 3.6.2.3 Debug Commands
N/A

### 3.6.3 REST API Support

### **PATCH**
#### Create a PortChannel
- `/openconfig-interfaces:interfaces/interface={name}/config`
#### Set min-links
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/config/min-links`
#### Set MTU/admin-status
- `/openconfig-interfaces:interfaces/interface={name}/config/[admin-status|mtu]`
#### Set IP
- `/openconfig-interfaces:interfaces/interface={name}/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address={ip}/config`
#### Add member
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/config/openconfig-if-aggregate:aggregate-id`

### **DELETE**
#### Delete a PortChannel
- `/openconfig-interfaces:interfaces/interface={name}`
#### Remove member
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-ethernet:ethernet/config/openconfig-if-aggregate:aggregate-id`

### **GET**
#### Get PortChannel details
- `/openconfig-interfaces:interfaces/ interface={name}/state/[mtu|admin-status|oper-status]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/state/[min-links|member]`
- `/openconfig-interfaces:interfaces/interface={name}/openconfig-if-aggregate:aggregation/state/dell-intf-augments:fallback`

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

#### Configuration  and Show via CLI
| Test Name | Test Description |
| :------ | :----- |
| Create PortChannel | Verify PortChannel is configured <br> Verify error returned if PortChannel ID out of supported range |
| Configure min-links | Verify min-links is configured <br> Verify error returned if min-links value out of supported range |
| Remove min-links config | Verify min-links reset to default value |
| Configure MTU, admin-status| Verify MTU, admin-status configured |
| Configure Fallback | Verify Fallback configured |
| Configure IP address | Verify IP address configured |
| Add ports to PortChannel| Verify Port added using "show PortChannel summary command" |
| Remove ports from PortChannel| Verify Port removed using "show PortChannel summary command" <br> Verify error returned if given PortChannel does not exist |
| Delete PortChannel| Verify PortChannnel removed using "show PortChannel summary command" and "teamshow" command |

#### Configuration(PATCH) and GET via gNMI/REST

- Verify the OpenConfig command paths in section 3.6.3 <br> 
- Verify the JSON response for GET requests

# 10 Internal Design Information
N/A
