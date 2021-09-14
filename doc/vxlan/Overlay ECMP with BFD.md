# Overlay ECMP with BFD monitoring
## High Level Design Document
### Rev 1.0

# Table of Contents

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Usecase](#11-usecase)
    * [1.2 Functional requirements](#12-functional-requirements)
    * [1.3 CLI requirements](#13-cli-requirements)
    * [1.4 Warm Restart requirements ](#14-warm-restart-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
    * [2.2 App DB](#22-app-db)
    * [2.3 Module Interaction](#23-module-interaction)
    * [2.4 Orchestration Agent](#24-orchestration-agent)
    * [2.5 Monitoring and Health](#25-monitoring-and-health)
    * [2.6 BGP](#26-bgp)
    * [2.7 CLI](#27-cli)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/09/2021  |     Prince Sunny   | Initial version                   |
| 1.0 | 09/13/2021  |     Prince Sunny   | Revised                           |

# About this Manual
This document provides general information about the Vxlan Overlay ECMP feature implementation in SONiC with BFD support. This is an extension to the existing VNET Vxlan support as defined in the [Vxlan HLD](https://github.com/Azure/SONiC/blob/master/doc/vxlan/Vxlan_hld.md)
# Scope
This document describes the high level design of the Overlay ECMP feature and associated BFD support. General BFD support and configurations are beyond the scope of this document. 

# Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| BFD                      | Bidirectional Forwarding Detection       |
| VNI                      | Vxlan Network Identifier       |
| VTEP                     | Vxlan Tunnel End Point         |
| VNet                     | Virtual Network                |

# 1 Requirements Overview

## 1.1 Usecase

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_UseCase.png)

## 1.2 Functional requirements

At a high level the following should be supported:

- Configure ECMP with Tunnel Nexthops (IPv4 and IPv6)
- Tunnel Endpoint monitoring via BFD
- Add/Withdraw Nexthop based on Tunnel or Endpoint health

## 1.3 CLI requirements
- User should be able to show the BFD session
- User should be able to show the Vnet routes

## 1.4 Warm Restart requirements
No special handling for Warm restart support.

# 2 Modules Design

The following are the schema changes. 

## 2.1 Config DB

Existing Vxlan and Vnet tables. 

### 2.1.1 VXLAN Table
```
VXLAN_TUNNEL|{{tunnel_name}} 
    "src_ip": {{ip_address}} 
    "dst_ip": {{ip_address}} (OPTIONAL)
```
### 2.1.2 VNET/Interface Table
```
VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "scope": {{"default"}} (OPTIONAL)
    "peer_list": {{vnet_name_list}} (OPTIONAL)
    "advertise_prefix": {{false}} (OPTIONAL)
```

## 2.2 APP DB

### VNET

The following are the changes for Vnet Route table

Existing:

``` 
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address}} 
    "mac_address":{{mac_address}} (OPTIONAL) 
    "vni": {{vni}}(OPTIONAL) 
```

Proposed:
```
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}}  
    "endpoint": {{ip_address1},{ip_address2},...} 
    "endpoint_monitor": {{ip_address1},{ip_address2},...} (OPTIONAL) 
    "mac_address":{{mac_address1},{mac_address2},...} (OPTIONAL)  
    "vni": {{vni1},{vni2},...} (OPTIONAL) 
    "weight": {{w1},{w2},...} (OPTIONAL) 
    “profile”: {{profile_name}} (OPTIONAL) 
```

```
key                      = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix 
; field                  = value 
ENDPOINT                 = list of ipv4 addresses    ; comma separated list of endpoints
ENDPOINT_MONITOR         = list of ipv4 addresses    ; comma separated list of endpoints, space for empty/no monitoring
MAC_ADDRESS              = 12HEXDIG                  ; Inner dst mac in encapsulated packet 
VNI                      = DIGITS                    ; VNI value in encapsulated packet 
WEIGHT                   = DIGITS                    ; Weights for the nexthops, comma separated (Optional) 
PROFILE                  = STRING                    ; profile name to be applied for this route, for community  
                                                       string etc (Optional) 
```

### BFD

```
BFD_SESSION:{{ifname}}:{{prefix}}  
    "tx_interval": {{interval}} (OPTIONAL) 
    "rx_interval": {{interval}} (OPTIONAL)  
    "multiplier": {{detection multiplier}} (OPTIONAL) 
    "shutdown": {{false}} 
    "multihop": {{false}} 
    "local_addr": {{ipv4/v6}} (OPTIONAL) 
    "type": {{string}} (active/passive..) 
; Defines APP DB schema to initiate BFD session.
```

## 2.3 Module Interaction

Overlay routes can be programmed via RestAPI or gNMI/gRPC interface which is not described in this document. A highlevel module interaction is shown below

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_ModuleInteraction.png)

## 2.4 Orchestration Agent
Following orchagents shall be modified. 

### VnetOrch

#### Requirements

- Vnetorch to add support to handle multiple endpoints for APP_VNET_RT_TUNNEL_TABLE_NAME based route task. 
- Reuse Nexthop tunnel based on the endpoint configuration. 
- If there is already the same endpoint exists, use that as member for Nexthop group. 
- Similar to above, reuse nexthop group, if multiple routes are programmed with the same set of nexthops. 
- Provide support for endpoint modification for a route prefix. Require SAI support for SET operation of routes. 
- Provide support for endpoint deletion for a route prefix. Orchagent shall check the existing entries and delete any tunnel/nexthop based on the new route update
- Ensure backward compatibility with single endpoint routes
- Use SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT for specifying weights to nexthop member
- Desirable to have per tunnel stats via sai_tunnel_stat_t 
 
#### Detailed flow

VnetOrch is one of the critical module for supporting overlay ecmp. VnetOrch subscribes to VNET and ROUTE updates from APP_DB.

When a new route update is processed by the add operation,  

1. VnetOrch checks the nexthop group and if it exists, reuse the group 
2. For a new nexthop group member, add the ECMP member and identify the corresponding monitoring IP address. Create a mapping between the monitoring IP and nexthop tunnel endpoint. 
3. Initiate a BFD session for the monitoring IP if it does not exist 
4. Based on the BFD implementation (BfdOrch vs Control plane BFD), subscribe to BFD state change, either directly as subject observer (similar to port oper state notifications in orchagent) or via STATEDB update. 
5. Based on the VNET global configuration to advertise prefixes, indicate to STATEDB if the prefix must be advertised by BGP/FRR only if there is atleast one active nexthop. Remove this entry if there are no active nexthops indicated by BFD session down so that the network pfx is no longer advertised.  

#### Monitoring Endpoint Mapping 

VNET_ROUTE_TUNNEL_TABLE can provide monitoring endpoint IPs which can be different from the tunnel termination endpoints. VnetOrch creates a mapping for such endpoints and based on the monitoring endpoint (MonEP1) health, proceed with adding/removing nexthop tunnel endpoint (EP1) from the ECMP group for the respective prefix. It is assumed that for one tunnel termination endpoint (EP1), there shall be only one corresponding monitoring endpoint (MonEP1).  

#### Pros of SWSS to handle route update based on tunnel nexthop health: 

- No significant changes, if BFD session management is HW offload via SAI notifications or Control Plane assisted. 
- Similar to NHFLAGS handling for existing route ECMP group 
- Better performance in re-programming routes in ASIC instead of separate process to monitor and modify each route prefix by updating DB entries 

### BfdOrch
Sonic shall offload the BFD session handling to hardware that has BFD capabilities.  A new module, BfdOrch shall be introduced to handle BFD session to monitoring endpoints and check the health of remote endpoints. BfdOrch shall offload the session initiation/sustenance to hardware via SAI APIs and gets the notifications of session state from SAI. The session state shall be updated in STATE_DB and to any other observer orchestration agents.  

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_BFD.png)

For offloading, the following shall be the SAI attributes programmed by BfdOrch.  

|  Attribute Type          |  Value                         |
|--------------------------|--------------------------------|
| SAI_BFD_SESSION_ATTR_TYPE | SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE  |
| SAI_BFD_SESSION_ATTR_OFFLOAD_TYPE | SAI_BFD_SESSION_OFFLOAD_TYPE_FULL |
| SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE | SAI_BFD_ENCAPSULATION_TYPE_NONE |
| SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS | Loopback0 IPv4 or v6 address |
| SAI_BFD_SESSION_ATTR_DST_IP_ADDRESS | Remote IPv4 or v6 address |
| SAI_BFD_SESSION_ATTR_MULTIHOP | True |

Sai shall notify via notification channel on the session state as one of sai_bfd_session_state_t. BfdOrch can listen on these notifications and update the StateDB for the session state.

The flow of BfdOrch is presented in the following figure. BfdOrch subscribes to the BFD_SESSION_TABLE of APPL_DB and send the corresponding request to program the BFD sessions to syncd accordingly. The BfdOrch also creates the STATE_DB entry of the BFD session which includes the BFD parameters and an initial state. Upon receiving bfd session state change notifications from syncd, BfdOrch update the STATE_DB field to update the BFD session state. 

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_BFD_Notification.png)

A Control Plane BFD approach is to use FRR BFD and enable bfdctl module. This shall be part of the Sonic BGP container. For the current usecase, the BFD hw offload is being considered and control plane BFD using FRR is not scoped in this document.

## 2.5 Monitoring and Health

The routes are programmed based on the health of tunnel endpoints. It is possible that a tunnel endpoint health is monitored via another dedicated “monitoring” endpoint. It is required to have a “keep-alive” mechanism to monitor the health of end point and withdraw or reinstall the route when the endpoint is inactive or active respectively.
When an endpoint is deemed unhealthy, router shall perform the following actions:
1.	Remove the nexthop from the ECMP path. If all endpoints are down, the route shall be withdrawn.
2.	If 50% of the nexthops are down, an alert shall be generated.

## 2.6 BGP

Advertise VNET routes
The overlay routes programmed on the device must be advertised to BGP peers. This can be achieved by the “network” command. 

For example:
```
router bgp 1
 address-family ipv4 unicast
  network 10.0.0.0/8
 exit-address-family
 ```

This configuration example says that network 10.0.0.0/8 will be announced to all neighbors. FRR bgpd doesn’t care about IGP routes when announcing its routes.


## 2.7 CLI

The following commands shall be modified/added :

```
	- show vnet routes all
	- show vnet routes tunnel
	- show bfd session <session name>
```

Config commands for VNET, VNET Routes and BFD session is not considered in this design. This shall be added later based on requirement. It is taken into consideration of future BFD enhancement to have the sessions created via config_db. 
