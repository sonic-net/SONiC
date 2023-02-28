# Overlay ECMP with BFD monitoring
## High Level Design Document
### Rev 1.5

# Table of Contents

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Usecase](#11-usecase)
    * [1.2 Functional requirements](#12-functional-requirements)
    * [1.3 CLI requirements](#13-cli-requirements)
    * [1.4 Warm Restart requirements ](#14-warm-restart-requirements)
    * [1.5 Scaling requirements ](#15-scaling-requirements)
    * [1.6 SAI requirements ](#16-sai-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
    * [2.2 App DB](#22-app-db)
    * [2.3 Module Interaction](#23-module-interaction)
    * [2.4 Orchestration Agent](#24-orchestration-agent)
    * [2.5 Monitoring and Health](#25-monitoring-and-health)
    * [2.6 BGP](#26-bgp)
    * [2.7 CLI](#27-cli)
    * [2.8 Test Plan](#28-test-plan)

###### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/09/2021  |     Prince Sunny   | Initial version                   |
| 1.0 | 09/13/2021  |     Prince Sunny   | Revised based on review comments  |
| 1.1 | 10/08/2021  |     Prince Sunny   | BFD section seperated             |
| 1.2 | 10/18/2021  |     Prince Sunny/Shi Su   | Test Plan added            |
| 1.3 | 11/01/2021  |     Prince Sunny  | IPv6 test cases added              |
| 1.4 | 12/03/2021  |     Prince Sunny  | Added scaling section, extra test cases  |
| 1.5 | 04/11/2022  |     Prince Sunny  | Test plan for Health monitoring |
| 1.6 | 04/23/2022  |     Storm Liang  | Update 2.6 BGP secion & add Test plan for BGP |

# About this Manual
This document provides general information about the Vxlan Overlay ECMP feature implementation in SONiC with BFD support. This is an extension to the existing VNET Vxlan support as defined in the [Vxlan HLD](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md)


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

Below diagram captures the use-case. In this, ToR is a Tier0 device and Leaf is a Tier1 device. Vxlan tunnel is established from Leaf (Tier1) to a VTEP endpoint. ToR (Tier0), Spine (Tier3) are transit devices. 


![](https://github.com/sonic-net/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_UseCase.png)

### Packet flow

- The packets destined to the Tunnel Enpoint shall be Vxlan encapsulated by the Leaf (Tier1).
- Return packet from the Tunnel Endpoint (LBs) back to Leaf may or may not be Vxlan encapsualted.
- Some flows e.g. BFD over Vxlan shall require decapsulating Vxlan packets at Leaf. 

## 1.2 Functional requirements

At a high level the following should be supported:

- Configure ECMP with Tunnel Nexthops (IPv4 and IPv6)
- Support IPv6 tunnel that can support both IPv4 and IPv6 traffic 
- Tunnel Endpoint monitoring via BFD
- Add/Withdraw Nexthop based on Tunnel or Endpoint health

## 1.3 CLI requirements
- User should be able to show the Vnet routes
- This is an enhancement to existing show command

## 1.4 Warm Restart requirements
No special handling for Warm restart support.

## 1.5 Scaling requirements
At a minimum level, the following are the estimated scale numbers

| Item                     | Expected value              |
|--------------------------|-----------------------------|
| ECMP groups              | 512                         |
| ECMP group member        | 128                         |
| Tunnel (Overlay) routes  | 16k                         |
| Tunnel endpoints         | 4k                          |
| BFD monitoring           | 4k                          |

## 1.6 SAI requirements
In addition to supporting Overlay ECMP (TUNNEL APIs) and BFD (HW OFFLOAD), the platform must support the following SAI attributes
| API                   | 
|--------------------------|
| SAI_SWITCH_ATTR_VXLAN_DEFAULT_ROUTER_MAC              |
| SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT        |


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
{% raw %} # ignore this line please
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}}  
    "endpoint": {{ip_address1},{ip_address2},...} 
    "endpoint_monitor": {{ip_address1},{ip_address2},...} (OPTIONAL) 
    "mac_address":{{mac_address1},{mac_address2},...} (OPTIONAL)  
    "vni": {{vni1},{vni2},...} (OPTIONAL) 
    "weight": {{w1},{w2},...} (OPTIONAL) 
    “profile”: {{profile_name}} (OPTIONAL) 
{% endraw %} # ignore this line please
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

## 2.3 Module Interaction

Overlay routes can be programmed via RestAPI or gNMI/gRPC interface which is not described in this document. A highlevel module interaction is shown below

![](https://github.com/sonic-net/SONiC/blob/master/images/vxlan_hld/OverlayEcmp_ModuleInteraction.png)

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

### Bfd HW offload

This design requires endpoint health monitoring by setting BFD sessions via HW offload. Details of BFD orchagent and HW offloading is captured in this [document](https://github.com/sonic-net/SONiC/blob/master/doc/bfd/BFD%20HW%20Offload%20HLD.md)


## 2.5 Monitoring and Health

The routes are programmed based on the health of tunnel endpoints. It is possible that a tunnel endpoint health is monitored via another dedicated “monitoring” endpoint. Implementation shall enforce a “keep-alive” mechanism to monitor the health of end point and withdraw or reinstall the route when the endpoint is inactive or active respectively.
When an endpoint is deemed unhealthy, router shall perform the following actions:
1.	Remove the nexthop from the ECMP path. If all endpoints are down, the route shall be withdrawn.
2.	If 50% of the nexthops are down, an alert shall be generated.

## 2.6 BGP

Advertise VNET routes

VnetOrch shall create an entry in STATE_DB for the active overlay routes eligible to be advertised by BGP to peers. Based on the health of overlay nexthop, the entry shall be added or removed. 

```
STATE_DB|ADVERTISE_NETWORK_TABLE|{{ip_prefix}}
    "profile": {{profile_name}}
```

The above entry shall be subscribed for by bgpcfgd and advertised by the “network” command. 

For example:
```
router bgp 1
 address-family ipv4 unicast
  network 10.0.0.0/8  route-map FROM_SDN_SLB_ROUTES_RM
 exit-address-family
```
Notes: Currently, only one profile_name is supported

This configuration example says that network 10.0.0.0/8 will be announced to all neighbors. FRR bgpd doesn’t care about IGP routes when announcing its routes. 
The profile would be transformed to route-map and associated with IP prefix. 

Application shall create a profile in APP_DB, which would be associated to the IP prefix when advertised by "network" command. 

```
APPL_DB:BGP_PROFILE_TABLE:{{profile_name}}
    "community_id": {{community_string}}
```

The above entry shall be subscribed for by bgpcfgd and created/updated by "route-map" command. 

For example:
```
route-map FROM_SDN_SLB_ROUTES_RM permit 100
 set community 1234:1235
```

Below will go through several use cases by manipulating tables. 

### Use case A: To advertise route 10.0.0.0/8 with community id "1234:1235" 
Step 1: add/update one route-map entry in the state db. 
```
APPL_DB:BGP_PROFILE_TABLE:FROM_SDN_SLB_ROUTES
    "community_id": "1234:1235"
```

Example command to add this entry 
```
sonic-db-cli APPL_DB HSET "BGP_PROFILE_TABLE:FROM_SDN_SLB_ROUTES" "community_id" "1234:1235"
```
 
Step 2: add route entry in the state db 
```
STATE_DB|ADVERTISE_NETWORK_TABLE|10.0.0.0/8
    "profile": "FROM_SDN_SLB_ROUTES"
```
Example command to add this entry 
```
sonic-db-cli STATE_DB HSET "ADVERTISE_NETWORK_TABLE|10.0.0.0/8" "profile" "FROM_SDN_SLB_ROUTES"
```

### Use case B: To advertise route 10.0.0.0/8 without community id (without profile)
Step 1: add route entry in the state db 
```
STATE_DB|ADVERTISE_NETWORK_TABLE|10.0.0.0/8
    "": ""
```
Example command to add this entry 
```
sonic-db-cli STATE_DB HSET "ADVERTISE_NETWORK_TABLE|10.0.0.0/8" "" ""
```

### Use case C: 10.0.0.0/8 with community id "1234:1235",  re advertise route 10.0.0.0/8 with new community id "1234:1236" 
Step 1: add/update one route-map entry in the state db. 
```
APPL_DB:BGP_PROFILE_TABLE:FROM_SDN_SLB_ROUTES
    "community_id": "1234:1236"
```

Example command to add this entry 
```
sonic-db-cli APPL_DB HSET "BGP_PROFILE_TABLE:FROM_SDN_SLB_ROUTES" "community_id" "1234:1236"
```

### Use case D: To remove route 10.0.0.0/8 with community id "1234:1235" 
Step 1: Delete the route entry in the state db. 

~~STATE_DB|ADVERTISE_NETWORK_TABLE|10.0.0.0/8~~

Example command to delete this entry 
```
sonic-db-cli STATE_DB DEL "ADVERTISE_NETWORK_TABLE|10.0.0.0/8"
```

Notes: the BGP_PROFILE_TABLE table need to be removed explicitly, there is no ref-count in the bgpcfgd layer.

## 2.7 CLI

The following commands shall be modified/added :

```
	- show vnet routes all
	- show vnet routes tunnel
```

Config commands for VNET, VNET Routes and BFD session is not considered in this design. This shall be added later based on requirement. 

## 2.8 Test Plan

Pre-requisite:

Create VNET and Vxlan tunnel as an below:

```
{ 
    "VXLAN_TUNNEL": {
        "tunnel_v4": {
            "src_ip": "10.1.0.32"
        }
    },

    "VNET": {
        "Vnet_3000": {
            "vxlan_tunnel": "tunnel_v4",
            "vni": "3000",
            "scope": "default"
        }
    }
}
```
Similarly for IPv6 tunnels

```
{ 
    "VXLAN_TUNNEL": {
        "tunnel_v6": {
            "src_ip": "fc00:1::32"
        }
    },

    "VNET": {
        "Vnet_3001": {
            "vxlan_tunnel": "tunnel_v6",
            "vni": "3001",
            "scope": "default"
        }
    }
}
```

Note: It can be safely assumed that only one type of tunnel exists - i.e, either IPv4 or IPv6 for this use-case

For ```default``` scope, no need to associate interfaces to a VNET

VNET tunnel routes must be created as shown in the example below

```
[
    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3000:100.100.2.1/32": { 
        "endpoint": "1.1.1.2", 
        "endpoint_monitor": "1.1.2.2"
    } 
]
```

With IPv6 tunnels, prefixes can be either IPv4 or IPv6

```
[
    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3001:100.100.2.1/32": { 
        "endpoint": "fc02:1000::1", 
        "endpoint_monitor": "fc02:1000::2"
    },
    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3001:20c0:a820:0:80::/64": { 
        "endpoint": "fc02:1001::1", 
        "endpoint_monitor": "fc02:1001::2"
    }
]
```

### Test Cases

### 2.8.1 Overlay ECMP 

It is assumed that the endpoint IPs may not have exact match underlay route but may have an LPM underlay route or a default route. Test must consider both IPv4 and IPv6 traffic for routes configured as example shown above

| Step | Goal | Expected results |
|-|-|-|
|Create a tunnel route to a single endpoint a. Send packets to the route prefix dst| Tunnel route create |  Packets are received only at endpoint a |
|Set the tunnel route to another endpoint b. Send packets to the route prefix dst | Tunnel route set | Packets are received only at endpoint b |
|Remove the tunnel route. Send packets to the route prefix dst | Tunnel route remove |  Packets are not received at any ports with dst IP of b |
|Create tunnel route 1 with two endpoints A = {a1, a2}. Send multiple packets (varying tuple) to the route 1's prefix dst. | ECMP route create | Packets are received at both a1 and a2 |
|Create tunnel route 2 to endpoint group A Send multiple packets (varying tuple) to route 2’s prefix dst | ECMP route create | Packets are received at both a1 and a2 |
|Set tunnel route 2 to endpoint group B = {b1, b2}. Send packets to route 2’s prefix dst | ECMP route set | Packets are received at either b1 or b2 |
|Send packets to route 1’s prefix dst. By removing route 2 from group A, no change expected to route 1 | NHG modify | Packets are received at either a1 or a2 |
|Set tunnel route 2 to single endpoint b1. Send packets to route 2’s prefix dst | NHG modify | Packets are recieved at b1 only |
|Set tunnel route 2 to shared endpoints a1 and b1. Send packets to route 2’s prefix dst | NHG modify | Packets are recieved at a1 or b1 |
|Remove tunnel route 2. Send packets to route 2’s prefix dst | ECMP route remove | Packets are not recieved at any ports with dst IP of a1 or b1 |
|Set tunnel route 3 to endpoint group C = {c1, c2, c3}. Ensure c1, c2, and c3 matches to underlay default route. Send 10000 pkt with random hash to route 3's prefix dst | NHG distribution | Packets are distributed equally across c1, c2 and c3 |
|Modify the underlay default route nexthop/s. Send packets to route 3's prefix dst | Underlay ECMP | No change to packet distribution. Packets are distributed equally across c1, c2 and c3 |
|Remove the underlay default route. | Underlay ECMP | Packets are not recieved at c1, c2 or c3 |
|Re-add the underlay default route. | Underlay ECMP | Packets are equally recieved at c1, c2 or c3 |
|Bring down one of the port-channels. | Underlay ECMP | Packets are equally recieved at c1, c2 or c3 |
|Create a more specific underlay route to c1. | Underlay ECMP | Verify c1 packets are received only on the c1's nexthop interface |
|Create tunnel route 4 to endpoint group A Send packets (fixed tuple) to route 4’s prefix dst | Vxlan Entropy | Verify Vxlan entropy|
|Change the udp src port of original packet to route 4’s prefix dst | Vxlan Entropy | Verify Vxlan entropy is changed|
|Change the udp dst port of original packet to route 4’s prefix dst | Vxlan Entropy | Verify Vxlan entropy is changed|
|Change the src ip of original packet to route 4’s prefix dst | Vxlan Entropy | Verify Vxlan entropy is changed|
|Create/Delete overlay routes to 16k with unique endpoints upto 4k | CRM  | Verify crm resourse for route (ipv4/ipv6) and nexthop (ipv4/ipv6) |
|Create/Delete overlay nexthop groups upto 512  | CRM  | Verify crm resourse for nexthop_group |
|Create/Delete overlay nexthop group members upto 128  | CRM  | Verify crm resourse for nexthop_group_member |

### 2.8.2 BFD and health monitoring

Health monitoring requires 'endpoint_monitor' and 'advertise_prefix' attributes to be provided. 

Reference tables

**Config_DB**
```
{
    "VNET|Vnet_3000": {
        "vxlan_tunnel": "tunnel_v4",
        "vni": "3000",
        "scope": "default",
        "advertise_prefix": "true",
     }
     
     "VNET|Vnet_3001": {
            "vxlan_tunnel": "tunnel_v6",
            "vni": "3001",
            "scope": "default",
	    "advertise_prefix": "true"
     }
}
```

**APP_DB**
```
[
    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3000:100.100.2.1/32": { 
        "endpoint": "1.1.1.2", 
        "endpoint_monitor": "1.1.2.2"
        "profile": "FROM_SDN_SLB_ROUTES"
     }
    
    "BFD_SESSION:default:default:1.1.2.2": {
        "multihop": "true",
        "local_addr": "10.1.0.32"
     }
     
    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3001:2000::1/128": { 
        "endpoint": "fc02:1000::1", 
        "endpoint_monitor": "fc02:1000::2"
        "profile": "FROM_SDN_SLB_ROUTES"
     }
     
    "BFD_SESSION:default:default:fc02:1000::2": {
        "multihop": "true",
        "local_addr": "fc00:1::32"
     }

    "BGP_PROFILE_TABLE:FROM_SDN_SLB_ROUTES": {
        "community_id": "1234:1236"
     }
]
```

**STATE_DB**
```
{
    "ADVERTISE_NETWORK_TABLE|100.100.2.1/32": {
        "profile": "FROM_SDN_SLB_ROUTES"
     }
     
    "BFD_SESSION_TABLE|default|default|1.1.2.2": {
       "state":"Up"
     }
     
    "ADVERTISE_NETWORK_TABLE|2000::1/128": {
        "profile": "FROM_SDN_SLB_ROUTES"
     }
     
     "BFD_SESSION_TABLE|default|default|fc02:1000::2": {
       "state":"Down"
     }
}
```
The below cases are executed first for IPv4 and repeat the same for IPv6.

| Step | Goal | Expected results |
|-|-|-|
| Create a tunnel route to a single endpoint a and monitor a'. Set BFD state a' to UP. Send packets to the route prefix dst| Tunnel route create and BFD functions  |  Packets are received only at endpoint a. BFD session for endpoint a' is up. Verify advertise table is present  |
| Set the tunnel route to another endpoint b and monitor b'. Set BFD state for b' to UP. Send packets to the route prefix dst  | Tunnel route set and BFD functions  | Packets are received only at endpoint b. BFD session for b' is created and the state is up. BFD session for endpoint a' is removed   |
| Remove the created tunnel route. Send packets to the route prefix dst. | Tunne route remove function and BFD | Packets are not received at any ports. BFD session for endpoint b' is removed. Verify advertise table is removed  |
| Create tunnel route 1 to two endpoints A = {a1, a2}. Set BFD state for a1' and a2' to UP. Send multiple packets (varying tuple) to the route 1's prefix dst. | ECMP route create with BFD | Packets are received at both a1 and a2. All BFD session states are UP |
| Create tunnel route 2 to endpoint group A. Send multiple packets (varying tuple) to route 2’s prefix dst | ECMP route create with BFD | Packets are received at both a1 and a2 |
| Set tunnel route 2 to endpoint group B = {b1, b2}. Set BFD state for b1' and b2' to UP. Send multiple packets (varying tuple) to route 2’s prefix dst | ECMP route set with BFD | Packets are received at both b1 and b2. All BFD session states are UP |
| Set tunnel route 2 to shared endpoints a1 and b1 with monitor a1' and b1'. Send packets to route 2’s prefix dst | NHG modify with BFD | Packets are recieved at a1 or b1. Nexthop group and the corresponding BFD sessions for endpoint group B are removed. ALL BFD sessions states are UP. |
| Remove tunnel route 2. Send packets to route 2’s prefix dst | ECMP route remove with BFD | Packets are not recieved at any ports with dst IP of a1 or b1. Unused BFD sessions are removed. Verify advertise table is removed |
| Set BFD state for a1' to UP and a2' to Down. Send multiple packets (varying tuple) to the route 1's prefix dst. | Health state change | Packets are received only at endpoint a1. Verify advertise table is present |
| Set BFD state for a1' to Down. Send packets to the route 1's prefix dst. | Health state change  | Packets are not received at any ports. Verify advertise table is removed |
| Set BFD state for a2' to UP. Send packets to the route 1's prefix dst. | Health state change  | Packets are received only at endpoint a2. Verify advertise table is present |
| Set BFD state for a1' to UP. Send multiple packets (varying tuple) to the route 1's prefix dst. | Health state change  | Packets are received at both a1 and a2. Verify advertise table is present |
| Set BFD state for a1' to Down and a2' to Down. Send multiple packets (varying tuple) to the route 1's prefix dst. | Health state change  | Packets are not received at any ports. Verify advertise table is removed | 
| Remove tunnel route 1. Send multiple packets (varying tuple) to the route 1's prefix dst. | Route remove with BFD down  | Packets are not received at any ports. BFD sessions are removed. Verify advertise table is removed | 
|Create/Delete overlay routes to 4k with unique endpoints upto 4k | BFD Scaling  | Verify all 4k BFD sessions are succesfully created and sessions alive |

### 2.8.3 BGP advertising
The below cases are executed first for IPv4 and repeat the same for IPv6. 
| Step | Goal | Expected results |
|-|-|-|
| Create a tunnel route and advertise the tunnel route to all neighbor without community id | BGP | ALL BGP neighbors can recieve the advertised BGP routes |
| Create a tunnel route and advertise the tunnel route to all neighbor with community id | BGP | ALL BGP neighbors can recieve the advertised BGP routes with community id |
| Update a tunnel route and advertise the tunnel route to all neighbor with new community id | BGP | ALL BGP neighbors can recieve the advertised BGP routes with new community id |
| Create a tunnel route and advertise the tunnel route to all neighbor with BGP profile, but create the profile later| BGP | ALL BGP neighbors can recieve the advertised BGP routes without community id first, after the profile table created, the community id would be added and all BGP neighbors can recieve this update and associate the community id with the route |
| Delete a tunnel route | BGP | ALL BGP neighbors can remove the previously advertised BGP routes |
| Create 4k tunnel routes and advertise all tunnel routes to all neighbor with community id | BGP scale | ALL BGP neighbors can recieve 4k advertised BGP routes with community id and record the time |
| Updat BGP_PROFILE_TABLE with new community id for 4k tunnel routes and advertise all tunnel routes to all neighbor with new community id | BGP scale | ALL BGP neighbors can recieve 4k advertised BGP routes with new community id and record the time |
