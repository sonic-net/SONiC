# SONiC IP/LAG Incremental Update

# Table of Contents
* [Revision](#revision)
* [About](#about)
* [Requirements Overview](#1-requirements-overview)
* [Database Design](#2-database-design)
* [Daemon Design](#3-daemon-design)
* [Flow](#4-flow)
* [Test](#5-test)

##### Revision
| Rev |  Date   |       Author       | Change Description |
|:---:|:-------:|:------------------:|:------------------:|
| 0.1 | 2018-09 |   Shuotian Cheng   | Initial Version    |

# About
This document provides the general information about basic SONiC incremental configuration support including IP addresses configuration changes, MTU configuration changes, and port channel configuration changes.

# 1. Requirements Overview
## 1.1 Functional Requirements
#### Phase #0
- Should be able to boot directly into working state given a working minigraph:
  1. All IPs are assigned correctly to each router interfaces
  2. All port channel interfaces are created with correct members enslaved
  3. All configured ports are set to admin status UP
  4. All configured ports are set to desired MTU
#### Phase #1
- Should not have static front panel interface configurations in `/etc/network/interfaces` file
- Should not have static teamd configurations in `/etc/teamd/` folder.
- Should be able to use command line to execute incremental updates including:
  1. Bring up/down all ports/port channels
  2. Assign/remove IPs towards non-LAG-member front panel ports, and port channels
  3. Change ports/port channels MTU
  4. Create/remove port channels
  5. Add/remove members of port channels
- Should be able to restart docker swss and the system recovers to the state before the restart

*Note:*
1. *Conflicting configurations that cannot be directly resolved are **NOT** supported in this phrase, including:*
  - *removing a port channel with existing IPs (IPs need to be removed before removing the port channel)*
  - *moving a port with IP into a port channel*
  - *assign an IP to a port channel member*
  - *adding/removing non-existing ports towards port channels, etc.*
2. *Port channel and port channel members' admin status are set separately, indicating that a port channel's admin status DOWN will NOT affect its members' admin status to be brought down.*
3. *By default, the admin status is UP and MTU is 9100.*
4. *A member port will inherit its port channel's MTU. However, the value will be automatically reset to its original one after it is removed from the port channel.*
#### Phase #2
- Should be able to move loopback interface out of `/etc/network/interfaces` file and managed by `portmgrd`.
- Should be able to restart docker teamd and all port channel configurations are reapplied. During the restart, all existing port channels will be removed from both control plane and data plane, and new configurations will be used to create use ones.

*Note:*
*The reason of moving this request into phase 2 is due to unrelated issues encountered while removing and recreating router interfaces, including IPv6 neighbor removal and potential SAI implementation issues.*

#### Future Work
TBD

## 1.2 Orchagent Requirements
The gap that orchagent daemon needs to fill is mostly related to MTU:
- Should be able to change router interface MTU
- Should be able to change LAG MTU

## 1.3 \*-syncd Requirements
- `portsyncd`: Should not be responsible for setting admin status and MTU. Should write 'state' -> 'ok' when associated netdev is created.
- `teamsyncd`: Should write 'state' -> 'ok' when associated netdev is created.
## 1.4 \*-mgrd Requirements
- `portmgrd`: Should be responsible port for admin status and MTU configuration changes. Related tables: `PORT`
- `intfsmgrd`: Should be responsible for port/port channel/VLAN IP configuraton changes. Related tables: `PORT_INTERFACE`, `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE`.
- `teammgrd`: Should be responsible for port channel and port channel member configuration changes. Related tables: `PORTCHANNEL` AND `PORTCHANNEL_MEMBER`.

## 1.4 Utility Requirements
```
config interface <interface_name> add ip <ip_address>
config interface <interface_name> remove ip <ip_address>
config interface <interface_name> mtu <mtu_value>

config port_channel add <port_channel_name> --min_links <min_links> --fall_back <true|false>
config port_channel remove <port_channel_name>
config port_channel member add <port_channel_name> <port_name>
config port_channel member remove <port_channel_name> <port_name>
```

# 2. Database Design
## 2.1 CONF_DB
> Theorem: Each configuration table can have one and only one manager daemon associated with it.
#### 2.1.1 PORT Table
```
PORT|{{port_name}}
  "admin_status": {{UP|DOWN}}
  "mtu": {{mtu_value}}
```
#### 2.1.2 INTERFACE Table
```
INTERFACE|{{port_name}}|{{IP}}
```
#### 2.1.3 PORTCHANNEL Table
```
PORTCHANNEL|{{port_channel_name}}
  "admin_status": {{UP|DOWN}}
  "mtu": {{mtu_value}}
  "min_links": {{min_links_value}}
  "fall_back": {{true|false}}
```
##### Schema
```
; Defines schema for port channel configuration attributes
key           = PORTCHANNEL:name          ; port channel configuration
; field       = value
admin_status  = "down" / "up"             ; admin status
MTU           = 1*4DIGIT                  ; mtu
MIN_LINKS     = 1*2DIGIT                  ; min links
FALL_BACK     = "false" / "true"          ; fall back
```
#### 2.1.4 PORTCHANNEL_INTERFACE Table
```
PORTCHANNEL_INTERFACE|{{port_channel_name}}|{{IP}}
```
##### Schema
```
; Defines schema for port channel member configuration attributes
key           = PORTCHANNEL:port_channel_name:member          ; port channel member configuration
```
#### 2.1.5 PORTCHANNEL_MEMBER Table
```
PORTCHANNEL_MEMBER|{{port_channel_name}}|{{port_name}}
```

# 3. Daemon Design
## 3.1 `orchagent`
- When LAG MTU is updated, all LAG members' MTUs are updated.
- When port/LAG MTU is updated, the associated router interface MTU is updated.
- If a port is part of a port channel, MTU will not be applied.
## 3.2 `portmgrd`
- Monitor `PORT` configuration table
- Should be responsible for admin status changes and MTU changes
## 3.3 `intfmgrd`
- Monitor `PORT_INTERFACE`,  `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE` configuration tables
- Should be responsible for IP changes
- Should listen to state database changes to detect port channels creation and removal
## 3.4 `teammgrd`
- Monitor `PORTCHANNEL` and `PORTCHANNEL_MEMBER` configuration tables
- Should be responsible for port channel changes and member changes
- Should listen to state database changes to detect port channel members creation and removal
- Should revert port configurations (admin status and MTU) after the port is removed from port channel

# 4. Flow
## 4.1 Admin Status/MTU Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/master/images/admin_status_mtu_configuration_flow.png)
## 4.2 Port Channel and Member Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/master/images/port_channel_member_configuration_flow.png)
## 4.3 IP Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/master/images/ip_configuration_flow.png)
## 4.4 Device Start Flow
![Image](https://github.com/stcheng/SONiC/blob/master/images/device_start_flow.png)
## 4.5 Docker swss Restart
TBD
## 4.6 Docker teamd Restart
TBD

# 5. Test
## 5.1 Virtual Switch Test
## 5.2 Integration Ansible Test
- Docker swss restart test
- Docker teamd restart test
