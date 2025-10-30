# Support for IPv4 and IPv6 VxLAN Tunnels in the same VNET
# High Level Design Document
### Rev 1.0
# Table of Contents
* [List of Tables](#list-of-tables)

 * [Revision](#revision)

* [Scope](#scope)

* [Definitions/Abbreviation](#definitionsabbreviation)

* [1 Requirements Overview](#1-requirements-overview)
* [1.1 Functional requirements](#11-functional-requirements)
* [1.2 Orchagent requirement](#12-orchagent-requirements)
* [1.3 CLI requirement](#13-cli-requirements)
* [2 Modules Design](#2-modules-design)
* [2.1 Config DB](#21-config-db)
* [2.2 Orchestration Agent](#23-orchestration-agent)
* [3 Configuration and Management](#3-configuration-and-management)
* [4 Example configuration](#4-example-configuration)

  ###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Sridhar Kulkarni   | Initial version                   |

# Scope
This document provides details to add dual stack support on Sonic for VxLAN tunnels in the same VNET (same VNI).
This new design allows a single VNET to have an IPv4-only Vxlan tunnel, IPv6-only Vxlan tunnel or both (dual-stack) coexisting.

# Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| VNI                      | Vxlan Network Identifier       |
| VTEP                     | Vxlan Tunnel End Point         |
| VRF                      | Virtual Routing and Forwarding |
| VNet                     | Virtual Network                |

# Overview
Currently, SONiC supports either an IPv4 or an IPv6 Vxlan tunnel in a VNET. Both IPv4 and IPv6 tunnels cannot co-exist. By adding dual-stack support, VxLan tunnel routes can be added under the same VNET/VRF for both IPv4 and IPv6 VTEPs. Traffic is encapsulated with IPv4 or IPv6 headers based on which route it takes.  
This is an extension to the existing [Vxlan feature on SONiC](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md).

# 1 Requirements Overview
## 1.1 Functional requirements
This section describes the SONiC requirements for dual-stack Vxlan feature. 

At a high level the following should be supported:
- Should allow both IPv4 and IPv6 Vxlan tunnel routes to co-exist in the same VNET
- Should be able to perform the role of Vxlan Tunnel End Point (VTEP) for IPv4 and IPv6 simulataneously 

## 1.2 Orchagent requirements
### Vxlan orchagent:
- Should be able to create NH tunnels with _src_interface_ 

### Vnet Route orchagent:
- Should be able to create IPv4 or IPv6 Vxlan tunnel routes based on the endpoint IP address provided in the configuration

## 1.3 CLI requirements
- User should be able to configure Vxlan tunnels and VTEPs (Overlay) by providing _src_interface_ parameter

```
config vxlan add <vxlan_name> <src_interface>
```

# 2 Modules Design
## 2.1 Config DB
#### 2.1.1 VXLAN Table
VXLAN_TUNNEL table will have following new optional fields. 

```
VXLAN_TUNNEL|{{tunnel_name}} 
    "src_ip"       : {{ip_address}} (Mandatory if src_interface is not provided)
    "dst_ip"       : {{ip_address}} (OPTIONAL)
    "src_interface": {{interface_name}} (Mandatory if src_ip is not provided)
```

When _src_interface_ is provided, IPv4 or IPv6 tunnel route is created based on the endpoint in tunnel route configuration. If _src_ip_ is provided, existing behaviour takes precedence, irrespective of _src_interface_ is provided or not

### 2.1.2 ConfigDB Schemas
```
; Defines schema for VXLAN Tunnel configuration attributes
key                                        = VXLAN_TUNNEL:name             ; Vxlan tunnel configuration
; field                                    = value
SRC_IP                                     = ipv4                          ; Ipv4 source address, lpbk address for tunnel term
DST_IP                                     = ipv4                          ; Ipv4 destination address, for P2P
SRC_INTERFACE                              = interface_name                ; src interface name, lpbk interface name for tunnel term

;value annotations
ipv4          = dec-octet "." dec-octet "." dec-octet "." dec-octet     
dec-octet     = DIGIT                     ; 0-9  
                  / %x31-39 DIGIT         ; 10-99  
                  / "1" 2DIGIT            ; 100-199  
                  / "2" %x30-34 DIGIT     ; 200-249
```

## 2.2 Orchestration Agent
### 2.2.1 VxlanOrch
Vxlan orch will be modified to be able to create co-existing IPv4 and IPv6 tunnels under the same Vnet and attach the same vni to both. It will also create relevant encap and decap mappers for both tunnels

### 2.2.2 VnetOrch/VnetRouteOrch
VnetRouteOrch is reponsible for programming VNET_ROUTE_TUNNEL_TABLE in SAI. Support will be added in VnetRouteOrch to lookup the appropriate IP address on the _src_interface_ and install routes for IPv4 and/or IPv6 tunnels based on the endpoint provided in the tunnel route configuration

# 3 Configuration and Management
## 3.1 YANG model
Yang model for [Vxlan tunnel](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang) will be enhanced to have _src_interface_ field

```
container sonic-vxlan {

        container VXLAN_TUNNEL {

            description "config db VXLAN_TUNNEL table";

            list VXLAN_TUNNEL_LIST {

                key "name";
                max-elements 2;

                leaf name {
                    type string;
                }

                leaf src_ip {
                    type inet:ip-address;
                }

                leaf dst_ip {
                    type inet:ip-address;
                }

                leaf src_interface {
                    type string;
                }
            }
        }
}
```

# 4 Example Configuration
Loopnac3 interface is configured with a private IPv4 and a link local IPv6 address
```
"LOOPBACK_INTERFACE": {
        "Loopback3": {},
        "Loopback3|172.17.0.9/32": {},
        "Loopback3|172:17:0::9/128": {},
}
```

VNET configuration remains unchanged.
Below example shows Vnet_1000 created and associated with vni `1000` and vxlan tunnel `Vxlan0`
```
"VNET": {
        "Vnet_1000": {
            "vni": "1000",
            "vxlan_tunnel": "Vxlan0",
            "src_mac": "12:34:56:78:9a:bc"
        }
    }
```

Below example shows two Vxlan tunnel routes using the same vni. One has IPv4 VTEP and other has IPv6 VTEP. Vxlan tunnel `Vxlan0` is created and src_interface is set to `Loopback3`. To install IPv4 route in SAI, VnetRouteOrch will use the IPv4 address of `Loopback3`, and for IPv6 tunnel route it will use the IPv6 address of `Loopback3`.

```
    "VNET_ROUTE_TUNNEL": {
        "Vnet_1000|10.1.0.12/32": {
            "endpoint": "134.33.50.191",
            "vni": "1000"
        },
        "Vnet_1000|10.1.1.15/32": {
            "endpoint": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "vni": "1000"
        }
    },
    "VXLAN_TUNNEL": {
        "Vxlan0": {
            "src_interface": "Loopback3"
        }
    }
```

