# SONiC IP/LAG Incremental Update

# Table of Contents
* [Revision](#revision)
* [About](#about)
* [Requirements Overview](#1-requirements-overview)
* [Database Design](#2-database-design)
* [Daemon Design](#3-daemon-design)
* [Flows](#4-flows)

##### Revision
| Rev |  Date   |       Author       | Change Description |
|:---:|:--------|:------------------:|--------------------|
| 0.1 | 2018-09 |   Shuotian Cheng   | Initial Version    |

# About
This document provides the general information about basic SONiC incremental configuration support including IP addresses configuration changes, and port channel configuration changes.

# 1. Requirements Overview
## 1.1 Functional Requirements
#### Phase #0
- Should be able to boot directly into working state given a working minigraph
1. All IPs are assigned correctly to each router interfaces
2. All port channel interfaces are created with correct members enslaved
3. All VLAN interfaces are created with correct members enslaved
4. All configured ports are set to admin status UP
5. All configured ports are set to desired MTU
#### Phase #1
- Should not have static front panel interface configurations in `/etc/network/interfaces` file
- Should not have static teamd configurations in `/etc/teamd/` folder.
- Should be able to use command line to execute incremental updates including:
1. Bring up/down all ports/port channels/VLANs
2. Assign/remove IPs towards non-LAG-member/non-VLAN-member front panel ports, and port channels
3. Create/remove port channels
4. Add/remove members of port channels
- Should be able to restart docker swss and the system recovers to the state before the restart

*Note:*
1. *Conflicting configurations that cannot be directly resolved are **NOT** supported in this phrase, including:*
- *moving a port with IP into a port channel*
- *assign an IP to a port channel member*
- *adding/removing non-existing ports towards port channels, etc.*
2. *Port channel and port channel members' admin status are controlled separately, indicating that a port channel's admin status DOWN will NOT affect its members' admin status to be brought down as well.*
3. *Admin status and MTU are must have attributes for ports and port channels, and the default values are UP and 9100.*
4. *MTU will be changed to the port channel's MTU once a port is enslaved into the port channel. However, the value will be automatically reset to its original one after the port is removed from the port channel.*
#### Phase #2
- Should be able to move loopback interface out of `/etc/network/interfaces` file and managed by `portmgrd`.
- Should be able to restart docker teamd and all port channel configurations are reapplied

*Note:*
*The reason of moving this request into phase 2 is due to unrelated issues encountered while removing and recreating router interfaces, including IPv6 removal and potential SAI implementation issues.*

#### Future Work
TBD
## 1.2 Orchagent Requirements
The gap that orchagent daemon needs to fill is mostly related to MTU:
- Should be able to change router interface MTU
- Should be able to change LAG MTU

## 1.3 \*-syncd Requirements
- `portsyncd`: Should not be listening to netlink message to get port admin status and MTU

## 1.4 \*-mgrd Requirements
- `portmgrd`: Should be responsible for admin status and MTU configuration changes. Related tables: `PORT`
- `intfsmgrd`: Should be responsible for port/port channel/VLAN IP configuraton changes. Related tables: `PORT_INTERFACE`, `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE`.
- `teammgrd`: Should be responsible for port channel and port channel member configuration changes. Related tables: `PORTCHANNEL` AND `PORTCHANNEL_MEMBER`.

## 1.4 Utility Requirements
```
config interface <interface_name> add ip <ip_address>
config interface <interface_name> remove ip <ip_address>
config interface <interface_name> mtu <mtu_value>

config port_channel add <port_channel_name>
config port_channel remove <port_channel_name>
config port_channel member add <port_channel_name> <port_name>
config port_channel member remove <port_channel_name> <port_name>
```

# 2. Database Design
## 2.1 CONF_DB
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
#### 2.1.4 PORTCHANNEL_INTERFACE Table
```
PORTCHANNEL_INTERFACE|{{port_channel_name}}|{{IP}}
```
#### 2.1.5 PORTCHANNEL_MEMBER Table
```
PORTCHANNEL_MEMBER|{{port_channel_name}}|{{port_name}}
```

# 3. Daemon Design
## 3.1 `orchagent`
- When LAG MTU is updated, all LAG members' MTUs are updated.
- When port/LAG MTU is updated, the associated router interface MTU is updated.
## 3.2 `portmgrd`
- Monitor `PORT` table
- Should be responsible for admin status changes and MTU changes
## 3.3 intfsyncd
- Monitor `PORT_INTERFACE`,  `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE` tables
- Should be responsible for IP changes
## 3.4 teamsyncd
- Monitor `PORTCHANNEL` and `PORTCHANNEL_MEMBER` tables
- Should be responsible for port channel changes and member changes

# 4. Flows
## 4.1 Admin Status/MTU Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/gh-pages/doc/admin_status.png)
## 4.2 Port Channel and Member Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/gh-pages/doc/port_channel.png)
## 4.3 IP Configuration Flow
![Image](https://github.com/stcheng/SONiC/blob/gh-pages/doc/ip.png)
## 4.4 Device Start Flow
![Image](https://github.com/stcheng/SONiC/blob/gh-pages/doc/device_start.png)
## 4.5 Docker swss Restart
TBD
## 4.6 Docker teamd Restart
TBD
