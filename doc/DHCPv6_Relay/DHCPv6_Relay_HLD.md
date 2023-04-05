# DHCP Relay for IPv6 HLD

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [DHCP Relay for IPv6 HLD](#dhcp-relay-for-ipv6-hld)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.1](#rev-01)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [List of Figures](#list-of-figures)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [1 Requirements Overview](#1-requirements-overview)
  - [1.1 Functional requirements](#11-functional-requirements)
  - [1.2 Configuration and Management Requirements](#12-configuration-and-management-requirements)
- [2 Modules design](#2-modules-design)
  - [2.1 DHCP Relay for IPv6 build and runtime dependencies](#21-dhcp-relay-for-ipv6-build-and-runtime-dependencies)
  - [2.2 DHCP Relay for IPv6 process in dhcp-relay container](#22-dhcp-relay-for-ipv6-process-in-dhcp-relay-container)
  - [2.3 DHCP Monitor](#23-dhcp-monitor)
- [3 CLI](#3-cli)
- [4 Init flow](#4-init-flow)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# List of Figures
* [DHCPv6 Diagram](#2-modules-design)
* [DHCPv6 init flow](#4-init-flow)

# Revision
| Rev | Date     | Author          | Change Description                 |
|:---:|:--------:|:---------------:|------------------------------------|
| 0.1 | 03/04    | Shlomi Bitton   | Initial version                    |

# About this Manual
This document provides an overview of the implementation and integration of DHCP Relay for IPv6 feature in SONiC.

# Scope
This document describes the high level design of the DHCP Relay for IPv6 feature in SONiC.

# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| DHCP          | Dynamic Host Configuration Protocol       |

# 1 Requirements Overview

## 1.1 Functional Requirements

DHCP Relay for IPv6 feature in SONiC should meet the following high-level functional requirements:

- Give the support for relaying DHCP packets from downstream networks to upstream networks using IPv6 addresses.
- Provide the functionality as a seperate process running on dhcp-relay docker container.
- Relaying messages to multiple unicast and multicast addresses.

## 1.2 Configuration and Management Requirements

- DHCPv6 trap should be enabled through the COPP manager when the DHCP relay feature is enabled and vice versa. 
- Downstream network is the VLAN interface with the relay configuration. Global IPv6 address is required to be configured on that interface. 
- Config DB schema should meet the following format:
```
{
"VLAN": {
  "Vlan1000": {
    "dhcp_servers": [
      "192.0.0.1", 
      "192.0.0.2", 
    ], 
    "dhcpv6_servers": [ 
      "21da:d3:0:2f3b::7", 
      "21da:d3:0:2f3b::6", 
    ], 
    "vlanid": "1000" 
    } 
  }
}
```

# 2 Modules design

![DHCPv6 Diagram](/doc/DHCPv6_Relay/diagram.png)

## 2.1 DHCP Relay for IPv6 build and runtime dependencies

The DHCP Relay for IPv6 feature, same as the IPv4 version, will be based on the open source project 'isc-dhcp'.

## 2.2 DHCP Relay for IPv6 process in dhcp-relay container

A new process will run in parallel to the other process for IPv4 support.
The new process will listen to DHCP packets for IPv6 and forward them to the relevant interface according to the configuration.
For example, from the configuration described on the previous section, the following daemon will start:
```
admin@sonic:/# /usr/sbin/dhcrelay -6 -d --name-alias-map-file /tmp/port-name-alias-map.txt -l Vlan1000 -u 21da:d3:0:2f3b::7%Ethernet28 -u 21da:d3:0:2f3b::6%Ethernet28
```

## 2.3 DHCP Monitor

The existing DHCP monitor will be enhanced in order to support monitoring for DHCP IPv6 as well.

## 3 CLI

The existing CLI will be enhanced to support configuring DHCP IPv6 along with the IPv4 support.

**config vlan dhcp_relay add**

Usage:
```
config vlan dhcp_relay add <vlan_id> <dhcp_relay_destination_ip>
```
Example:
```
admin@sonic:~$ sudo config vlan dhcp_relay add 1000 21da:d3:0:2f3b::7
Added DHCP relay destination address 21da:d3:0:2f3b::7 to Vlan1000
Restarting DHCP relay service...
```

**config vlan dhcp_relay delete**

Usage:
```
config vlan dhcp_relay del <vlan-id> <dhcp_relay_destination_ip>
```
Example:
```
admin@sonic:~$ sudo config vlan dhcp_relay del 1000 21da:d3:0:2f3b::7
Removed DHCP relay destination address 21da:d3:0:2f3b::7 from Vlan1000
Restarting DHCP relay service...
```

**show vlan brief**

Usage:
```
show vlan brief
```
Example:
```
admin@sonic:~$ show vlan brief
+-----------+----------------------+------------+----------------+-----------------------+-------------+
|   VLAN ID | IP Address           | Ports      | Port Tagging   | DHCP Helper Address   | Proxy ARP   |
+===========+======================+============+================+=======================+=============+
|      1000 | 21da:d3:0:2f3b::6/96 | Ethernet28 | untagged       | 21da:d3:0:2f3b::6     | disabled    |
|           |                      |            |                | 21da:d3:0:2f3b::7     |             |
+-----------+----------------------+------------+----------------+-----------------------+-------------+
```

## 4 Init flow

![DHCPv6 init flow](/doc/DHCPv6_Relay/init.svg)

