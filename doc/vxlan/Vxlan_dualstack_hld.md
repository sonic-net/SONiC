# Support for IPv4 and IPv6 VxLAN Tunnels in the same VNET
# High Level Design Document
### Rev 1.0
# Table of Contents
* [Table of Contents](#table-of-contents)

* [Revision](#revision)

* [Scope](#scope)

* [Definitions/Abbreviation](#definitionsabbreviation)

* [1 Requirements Overview](#1-requirements-overview)
* [1.1 Functional requirements](#11-functional-requirements)
* [1.2 Orchagent requirement](#12-orchagent-requirements)
* [1.3 CLI requirements](#13-cli-requirements)
* [2 Modules Design](#2-modules-design)
* [2.1 Config DB](#21-config-db)
* [2.2 App DB](#22-app-db)
* [2.3 Orchestration Agent](#23-orchestration-agent)
* [3 Flows](#3-flows)
* [4 Test Plan](#4-test-plan)
* [5 Configuration and Management](#5-configuration-and-management)
* [6 Example configuration](#6-example-configuration)

  ###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 1.0 |             | Sridhar Kulkarni   | Initial version                   |

# Scope
This document provides details to add dual stack support on Sonic for VxLAN tunnels in the same VNET (same VNI).
This new design allows a single VNET to have an IPv4-only Vxlan tunnel, IPv6-only Vxlan tunnel or both (dual-stack) coexisting.

## Use Case
In some cases, separate overlay routes to individual destinations (VMs) in a Vnet are needed. Some destinations may be behind an IPv4 VTEP, while others may be behind an IPv6 VTEP. In such cases, one Vnet must support both IPv4 and IPv6 Vxlan tunnels.  
Consider the below diagram where Host 1 is a physical machine while VM1 and VM2 are VMs in a cloud and all three are in the same VNet. VM1 is hosted on a physical server with a public IPv4 address and VM2 is hosted on a server with a public IPv6 address. For Host1 to be able to communicate to both VM1 and VM2, there should be
1. IPv4 Vxlan tunnel from Sonic to VM1
2. IPv6 Vxlan tunnel from Sonic to VM2

Currently, Sonic supports either 1 or 2 but not both. The following design will add support for both 1 and 2 in the same VNet.

![](https://github.com/sridkulk/SONiC/blob/srkul/vxlandualstack/images/vxlan_hld/VxLAN_dualstack_usecase.png)

# Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| VNI                      | Vxlan Network Identifier       |
| VTEP                     | Vxlan Tunnel End Point         |
| VRF                      | Virtual Routing and Forwarding |
| VNet                     | Virtual Network                |

# Overview
Currently, SONiC supports either an IPv4 or an IPv6 Vxlan tunnel in a VNet. Both IPv4 and IPv6 tunnels cannot co-exist in one VNet. 
Consider the following VNet and Vxlan configuration:

```
"VNET": {
    "Vnet_1000": {
        "vni": "1000",
        "vxlan_tunnel": "Vxlan0",
        "src_mac": "12:34:56:78:9a:bc"
    }
},
"VXLAN_TUNNEL": {
    "Vxlan0": {
        "src_ip": "10.10.10.10"
    }
}
```

In the above example, Vxlan tunnel `Vxlan0` is configured with an IPv4 _src_ip_. This means that routes with only IPv4 remote VTEPs can be added under the VNET_ROUTE_TUNNEL configuration. Routes with IPv6 VTEPs cannot be aded with the above configuration. Similary, if Vxlan0 is configured with an IPv6 _src_ip_, tunnel routes with only IPv6 remote VTEPs are supported.  

By adding dual-stack support, Vxlan tunnel routes can be added under the same VNET/VRF for both IPv4 and IPv6 remote VTEPs at the same time. Traffic will be encapsulated with IPv4 or IPv6 headers based on which route it takes.  
This is an extension to the existing [Vxlan feature on SONiC](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md).

# 1 Requirements Overview
## 1.1 Functional requirements
This section describes the SONiC requirements for dual-stack Vxlan feature. 

At a high level the following should be supported:
- Should be able to support one IPv4 Vxlan tunnel and one IPv6 Vxlan tunnel in the same VNet
- Should allow both IPv4 and IPv6 Vxlan tunnel routes to co-exist in the same VNET
- Should be able to perform the role of Vxlan Tunnel End Point (VTEP) for IPv4 and IPv6 simulataneously for the same VNet

## 1.2 Orchagent requirements
### Vxlan Orchagent:
- No changes needed for Vxlan orchagent 

### Vnet Orchagent
- Should be able to associate one IPv4 Vxlan tunnel and one IPv6 Vxlan tunnel to the same VNet

### Vnet Route Orchagent:
- Should be able to create IPv4 or IPv6 Vxlan tunnel routes based on the endpoint IP address provided in the configuration

## 1.3 CLI requirements
- User should be able to configure Vnet with IPv4 and IPv6 Vxlan tunnels 

```
config vnet add <vnet_name> <vni> <vxlan_tunnel> <vxlan_tunnel_v6>
```

# 2 Modules Design
## 2.1 Config DB
### 2.1.1 VNET Table
VNET table will have a new optional field `vxlan_tunnel_v6`: 

```
VNET|{{vnet_name}} 
    "vxlan_tunnel"          : {{tunnel_name}}
    "vxlan_tunnel_v6"       : {{IPv6_tunnel_name}} (OPTIONAL)
    "vni"                   : {{vni}} 
    "scope"                 : {{default}} (OPTIONAL)
    "peer_list"             : {{vnet_name_list}} (OPTIONAL)
```

`vxlan_tunnel_v6` is an optional field. If provided, it should be the name of the Vxlan tunnel with an IPv6 _src_ip_

### 2.1.2 ConfigDB Schemas
```
; Defines schema for VXLAN Tunnel configuration attributes
key                                   = VNET:name                     ; Vnet name
; field                               = value
VXLAN_TUNNEL                          = tunnel_name                   ; refers to the Vxlan tunnel name
VXLAN_TUNNEL_V6                       = tunnel_name                   ; refers to the Vxlan tunnel name with IPv6 src IP
VNI                                   = DIGITS                        ; 1 to 16 million VNI values
SCOPE                                 = Vnet Scope                    ; Whether to use default or non-default VRF
PEER_LIST                             = \*vnet_name                   ; vnet names seperate by "," 
                                                                             (empty indicates no peering)
```

## 2.2 App DB
### 2.2.1 VNET Table
VrfMgrd will copy the VNET table contents from CONFIG DB to APP DB.
```
VNET|{{vnet_name}} 
    "vxlan_tunnel"          : {{tunnel_name}}
    "vxlan_tunnel_v6"       : {{IPv6_tunnel_name}} (OPTIONAL)
    "vni"                   : {{vni}} 
    "scope"                 : {{default}} (OPTIONAL)
    "peer_list"             : {{vnet_name_list}} (OPTIONAL)
```

### 2.2.2 VXLAN ROUTE TUNNEL table
No changes needed for the Vxlan route tunnel table. VnetOrch/VnetRouteOrch will be enhanced to create appropriate routes with IPv4 or IPv6 VTEPs based on the endpoint specified in the route.

### 2.2.3 App DB schemas
```
; Defines schema for VXLAN Tunnel configuration attributes
key                                   = VNET:name                     ; Vnet name
; field                               = value
VXLAN_TUNNEL                          = tunnel_name                   ; refers to the Vxlan tunnel name
VXLAN_TUNNEL_V6                       = tunnel_name                   ; refers to the Vxlan tunnel name with IPv6 src IP
VNI                                   = DIGITS                        ; 1 to 16 million VNI values
SCOPE                                 = Vnet Scope                    ; Whether to use default or non-default VRF
PEER_LIST                             = \*vnet_name                   ; vnet names seperate by "," 
                                                                             (empty indicates no peering)
```

## 2.3 Orchestration Agent
### 2.2.1 VxlanOrch
No changes needed for VxlanOrch

### 2.2.2 VnetOrch/VnetRouteOrch
Currently VNetOrch only refers to one Vxlan tunnel. It will be extended to reference two Vxlan tunnels. VnetRouteOrch is reponsible for reading VNET_ROUTE_TUNNEL_TABLE and creating routes in SAI. Support will be added in VnetRouteOrch to create the appropriate NH tunnel from Vxlan orch based on the endpoint IP. VnetRouteOrch will then use this NH tunnel to create routes in SAI.  
For example, when a Vxlan route is added with IPv4 endpoint, NH tunnel object will be created in SAI for the IPv4 Vxlan tunnel and will be used as the nexthop in the route. If a Vxlan route is added with IPv6 endpoint, NH tunnel object will be created in SAI for the IPv6 Vxlan tunnel and will be used as nexthop in the route.

# 3 Flows

![](https://github.com/sridkulk/SONiC/blob/srkul/vxlandualstack/images/vxlan_hld/Vnet_Vxlan_dualstack.png)

![](https://github.com/sridkulk/SONiC/blob/srkul/vxlandualstack/images/vxlan_hld/VNet_Vxlan_dualstack_update.png)
  
![](https://github.com/sridkulk/SONiC/blob/srkul/vxlandualstack/images/vxlan_hld/Vnet_dualstack_vxlan_route_create.png)

![](https://github.com/sridkulk/SONiC/blob/srkul/vxlandualstack/images/vxlan_hld/Vnet_dualstack_vxlan_route_delete.png)


## 4 Test Plan
### 4.1 Test Cases

| Step | Goal | Expected results |
|-|-|-|
| Create two Vxlan tunnels and provide IPv4 addressses as src ip for both. Create VNet and associate the two tunnels to it | VNet and dualstack Vxlan create | VNet creation must fail
| Create two Vxlan tunnels and provide IPv6 addressses as src ip for both. Create VNet and associate the two tunnels to it | VNet and dualstack Vxlan create | VNet creation must fail
| Create loopback intf with only IPv4 addr. Create Vxlan tunnel and provide loopback intf ip as src ip. Create VNet and associate the tunnel to it. Create tunnel route with IPv4 endpoint. Send traffic to dest | Vnet with only IPv4 tunnel | Traffic must be received at dest
| Create loopback intf with only IPv6 addr. Create Vxlan tunnel and provide loopback intf ip as src ip. Create VNet and associate the tunnel to it. Create tunnel route with IPv6 endpoint. Send traffic to dest | Vnet with only IPv6 tunnel | Traffic must be received at dest
| Create loopback interface with both IPv4 and IPv6 addr. Create one Vxlan tunnel with loopback IPv4 addr as src ip. Create another Vxlan tunnel with loopback IPv6 addr as src ip. Create VNet and associate both tunnels to it. Create tunnel routes with IPv4 and IPv6 endpoint. Send traffic to dest | Dual stack tunnel create | Both IPv4 and IPv6 dest must receive traffic
| Create loopback intf with only IPv4 addr. Create Vxlan tunnel and provide loopback intf ip as src ip. Create VNet and associate the tunnel to it. Add IPv6 addr to the loopback intf. Create another Vxlan tunnel with this IPv6 src_ip. Update Vnet with this Vxlan tunnel. Create IPv4 and IPv6 Vxlan tunnel routes. Send traffic to dest | Vxlan tunnel update after VNet create | Traffic must be received at dest


# 5 Configuration and Management
## 5.1 YANG model
Yang model for [VNet](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vnet.yang) will be enhanced to have a new field `vxlan_tunnel_v6` to specify IPv6 tunnel

```
container sonic-vnet {

    container VNET {

        description "config db VNET table";

        list VNET_LIST {

            key "name";

            leaf name {
                type string;
            }

            leaf vxlan_tunnel {
                mandatory true;
                description "A valid and active vxlan tunnel to be used with this vnet for traffic encapsulation.";
                type leafref {
                    path "/svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name";
                }
            }

            leaf vxlan_tunnel_v6 {
                description "A valid and active vxlan tunnel with IPv6 src_ip to be used with this vnet for IPv6 traffic encapsulation.";
                type leafref {
                    path "/svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name";
                }
            }

                leaf vni {
                mandatory true;
                description "A valid and unique vni which will become part of the encapsulated traffic header.";
                type stypes:vnid_type;
            }

            leaf peer_list {
                description "Set of peers";
                /* Values in leaf list are UNIQUE */
                type string;
            }

            leaf guid {
                description "An optional guid.";
                type string {
                    length 1..255;
                }
            }

            leaf scope {
                description "can only be default.";
                type string {
                    pattern "default" {
                        error-message "Invalid VRF name";
                    }
                }
            }

            leaf advertise_prefix {
                description "Flag to enable advertisement of route prefixes belonging to the Vnet.";
                type  boolean;
            }

            leaf overlay_dmac {
                description "Overlay Dest MAC address to be used by Vnet ping.";
                type yang:mac-address;
            }

            leaf src_mac {
                description "source mac address for the Vnet";
                type yang:mac-address;
            }
        }
    }
}
```

# 6 Example Configuration
## Config DB Objects
`Loopback3` interface is configured with a private IPv4 and a link local IPv6 address
```
"LOOPBACK_INTERFACE": {
        "Loopback3": {},
        "Loopback3|172.17.0.9/32": {},
        "Loopback3|172:17:0::9/128": {},
}
```

Two Vxlan tunnels are configured, one with IPv4 src_ip and another with IPv6 src_ip:
```
"VXLAN_TUNNEL": {
        "Vxlan0": {
            "src_ip": "172.17.0.9"
        },
        "Vxlan1": {
            "src_ip": "172:17:0::9"
        }
    }
```

Below example shows Vnet_1000 created and associated with vni `1000` and vxlan tunnel `Vxlan0` and IPv6 tunnel `Vxlan1`
```
"VNET": {
        "Vnet_1000": {
            "vni": "1000",
            "vxlan_tunnel": "Vxlan0",
            "vxlan_tunnel_v6": "Vxlan1",
            "src_mac": "12:34:56:78:9a:bc"
        }
    }
```

## App DB Objects
Below example shows two Vxlan tunnel routes using the same vni. One has IPv4 VTEP and other has IPv6 VTEP. To install IPv4 route in SAI, VnetRouteOrch will use the IPv4 Vxlan tunnel `Vxlan0` to create NH tunnel, and for IPv6 tunnel route it will use the IPv6 Vxlan tunnel `Vxlan1` to create NH tunnel

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
```

