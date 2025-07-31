# Overlay ECMP Enhancements

# Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Overview](#1-overview)
- [Schema Changes](#2-schema-changes)
    - [Config DB](#21-config-db)
    - [APP DB](#22-app-db)
    - [STATE DB](#23-state-db)
- [Enhancements](#3-enhancemernts)
    - [Vxlan tunnel Routes with Primary/seconday switch over](#31-vxlan-tunnel-routes-with-primaryseconday-switch-over)
    - [Custom monitoring for VTEP liveness detection.](#32-custom-monitoring-for-vtep-liveness-detection)
    - [BFD Tx, Rx interval parameter and support for directly connected nexthops.](#33-bfd-tx-rx-interval-parameter-and-support-for-directly-connected-nexthops)
- [Test Plan for the enhacements](#4-test-plan-for-the-enhacements)


# Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 08/01/2024  |     Shahzad Iqbal  | Initial version                   |


# Scope

This document provides general information about the new enhancement (alreaddy existing and some proposed) to the Vxlan Overlay ECMP feature in SONiC. This is an extension of the existing [Overlay ECMP with BFD monitoring](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Overlay%20ECMP%20with%20BFD.md) and only provides information about the enhancements in the existing design.


# Abbreviations

|                          |                 |
|--------------------------|-----------------| 
| NH                       | Next hop        |
| NHG                      |  Next hop Group |

# 1 Overview
The following enhacements are discussed in this document.
 1. Vxlan tunnel Routes with Primary/seconday switch over. 
 2. Custom monitoring instead of BFD for VTEP liveness detection.
 3. BFD Tx, Rx interval parameter and support for directly connected nexthops.

# 2 Schema Changes

The following are the schema changes. 

## 2.1 Config DB

A new optional field **overlay_dmac** has been added in the existing Vnet table.

```
VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "scope": {{"default"}} (OPTIONAL)
    "peer_list": {{vnet_name_list}} (OPTIONAL)
    "advertise_prefix": {{false}} (OPTIONAL)
    "overlay_dmac": {{MAC Address}} (OPTIONAL)  <<<< New Field
```


```
overlay_dmac                = MAC ADDR                    ; A MAC address which can be passed to the custom monitor table.
```    

## 2.2 APP DB


The following new fields have been added the **VNET_ROUTE_TUNNEL_TABLE**
 - Primary
 - rx_monitor_timer
 - tx_monitor_timer
 - check_directly_connected
 - monitoring
 - adv_prefix

```

VNET_ROUTE_TUNNEL_TABLE:/{/{vnet_name/}/}:/{/{prefix/}/}  
    “endpoint”: /{/{ip_address1/},/{ip_address2/},.../} 
    “endpoint_monitor”: /{/{ip_address1/},/{ip_address2/},.../} (OPTIONAL) 
    “mac_address”: /{/{mac_address1/},/{mac_address2/},.../} (OPTIONAL) 
    “monitoring”: /{/{“custom”/}/} (OPTIONAL)                                  <<<< New Field
    “vni”: /{/{vni1/},/{vni2/},.../} (OPTIONAL) 
    “weight”: /{/{w1/},/{w2/},.../} (OPTIONAL) 
    “profile”: /{/{profile_name/}/} (OPTIONAL) 
    “primary”: /{/{ip_address1/}, /{ip_address2/}/} (OPTIONAL)                   <<<< New Field    
    “profile”: /{/{profile_name/}/} (OPTIONAL)  
    “adv_prefix”: /{/{prefix/}/} (OPTIONAL)                                    <<<< New Field
    “rx_monitor_timer”: /{time in milliseconds/} (OPTIONAL)                  <<<< New Field
    “tx_monitor_timer”: /{time in milliseconds/} (OPTIONAL)                  <<<< New Field
    “check_directly_connected”: /{/{true|false/}/} (OPTIONAL)                  <<<< New Field
```


```
primary                  = ipv4/v6 address list      ; Primary endpoint to choose if specified (Optional) 
monitoring               = STRING                    ; A string tag to indicate custom monitoring be used instead of BFD.
rx_monitor_timer         = DIGITS                    ; time in Milliseconds for the monitor session Rx wait time.(Applicable to BFD only) (Optional) 
tx_monitor_timer         = DIGITS                    ; time in Milliseconds for the monitor session Tx internval.(Applicable to BFD only) (Optional) 
check_directly_connected = BOOLEAN                   ; Boolean used by the route creator to indicate if nexthops need to be checked for being directly connected.
adv_prefix               = IP-PREFIX                 ; PRefix value to be advertised instead of route prefix.
```

A new table **VNET_MONITOR_TABLE** has been added to send the endpoint information to the custom monitoring module.

```
VNET_MONITOR_TABLE:{{endpoint}}:{{ip_prefix}}  
    “packet_type”: {{vxlan}} (OPTIONAL) 
    “interval”: {{interval}} (OPTIONAL)  
    “multiplier”: {{detection multiplier}} (OPTIONAL) 
    “overlay_dmac”: {{mac_addr}}
```

```
packet_type              = STRING                    ; For custom monitoring this specifies the type of packet to be used. Currently only vxlan is supported. (Optional) 
interval                 = DIGITS                    ; Time in Milliseconds for the monitor session Tx packets. (Optional) 
multiplier               = DIGITS                    ; A multiplier factor for the RX detection interval. Rx detection interval = interval * multiplier (Optional) 
overlay_dmac             = MAC ADDR                  ; A MAC address value provided by VNET to be passed to the custom monitoring componenet.
```

## 2.3 STATE DB

A new table in state DB is being added to recieve the response form the custom monitoring module to indicate endpoint liveness.

```
VNET_MONITOR_TABLE|{{endpoint}}|{{ip_addr}}  
    "state": {{up/down}} 
```
```
state                    = STRING                    ; up/down indicating the livness of the nexthop.
```


# 3 Enhancements

## 3.1 Vxlan tunnel Routes with Primary/seconday switch over. 

The primary/backup endpoint behavior is required for some application scenarios. The controller can specify the primary endpoints while providing a list of endpoints and endpoint monitoring IPs. If primary endpoints are provided, Sonic shall install route to only the primary endpoints. A multi-hop regular (non-encapsulated) BFD session is established with all endpoint monitoring IPs and in the event of all sessions going down with primary endpoint monitoring IP, implementation shall fallback to backup endpoints.  

In the event of primary endpoint BFD sessions comes back, Sonic shall re-install the route to point to primary nexthops.  The primary endpoints can be updated via the route update and implementation shall dynamically shift the route back to configured primary endpoints. All the rest of the implementation shall remain same.  
The Orchagent would be responsible for handling of Primary/backup routes if primary endpoints are specified. In the case where no Primary endpoints are specified, the orchagent behavior would treat the route as an ordinary overlay-ECMP route with monitoring.

when primary endpoints are specified the following behavior is adopted. 

- Monitoring sessions shall be programmed for both primary and secondary endpoints. 
- The presence of a primary endpoints in the active Nexthop group shall be decided by its monitor session state. When a primary endpoint’s BFD session goes Down, it will be removed from the active Nexthop Group. 
- If multiple primary endpoints are programmed, the secondary endpoint’s will not associated with the route unless all primary endpoints go down.  
- Once the last primary endpoint goes down, The route would switch to the secondary endpoint ECMP group based on BFD state. 
- When running with secondary endpoints, if one primary comes back Up, the route nexthop would switch to primarynexthop group. 

The following diagram depicts the scenario where Endpoint 1 and 2 are primary in a tunnel route and Endpoint 3 and 4 are backup. The active endpoints 1 and 2 are indicated with green line.

![](https://github.com/sonic-net/SONiC/blob/22e06c87939f49ee72687cf2972f83a526c67b30/images/vxlan_hld/OverlayEcmp_priorty.png)


### 3.1.1 Behaviour example

| Scenario |     Before state change    |       State change       | Result                 | Description|
|:--------:|:--------------------------:|:------------------------:|:----------------------:|:-----------|
| Single primary-secondary switchover. Endpoint list = [A, A’], Primary[A] | NH=[A]  | A went Down  | NH=[A’]  | NH has a single primary endpoint which upon failing is replaced by the single Backup endpoint. |
| Single primary recovery. Endpoint list = [A, A’] Primary[A] | NH=[A’]  | A is back up  | NH=[A]  | NH has a single backup endpoint which upon recovery of primary is replaced.  |
| Single primary backup Failure. Endpoint list = [A, A’].  Primary[A]| NH=[A’] A is DOWN | A’ goes Down  | NH=[]  | No active Endpoint results in route being removed.  |
| Multiple primary backups. Single primary failure.  Endpoint list = [A, B, C, A’, B’, C’]  Primary = [A, B, C] | NH = [A, B, C]  | A goes Down  | NH=[B, C]  | One of the primaries goes down. The others stay active.  |
| Multiple primary backups. Multiple primary failure. Endpoint list = [A, B, C, A’, A’, B’, C’] Primary = [A, B, C]  | NH = [B, C]  | B goes Down. A already Down. | NH=[C]  | 2 of the primaries goes down. The 3rd stay active. NH group is updated.  |
| Multiple primary backups.  All primary failure. Endpoint list = [A, B, C, A’, A’, B’, C’] Primary = [A, B, C]  | NH = [C]  | C goes Down. A,B already Down  | NH=[A’, B’, C’]  | All the primaries are down. The backup endpoints are added to the NH group.  |
| Multiple primary backups. Backup Failure. Endpoint list = [A, B, C, A’, A’, B’, C’] Primary = [A, B, C]  | NH = [A’, B’, C’]  | C’ goes Down. A, B, C already Down  | NH=[A’, B’]  | All the primaries are down. Failure of a backup endpoint shall result in its removal from NH.  |
| Multiple primary backups. Single primary recovery. Endpoint list = [A, B, C, A’, A’, B’, C’] Primary = [A, B, C]  | NH = [A’, B’, C’]  | A is Up. B, C still Down  | NH=[A]  | Primary takes precedence and is added to the NH. All the backups are removed.  |
| Multiple primary backups. Multiple primary recovery. Endpoint list = [A, B, C, A’, A’, B’, C’] Primary = [A, B, C]  | NH = [A]  | A is Up. B, C also come up  | NH=[A, B, C]  | Primary endpoints take precedence and are added to the NH.  |
 

## 3.2 Custom monitoring for VTEP liveness detection.
In the orignal design of Overlay-ECMP, BFD was used for livness detection fo VTEP. But BFD may not be supported by all types of VTEPs. In some cases a user may want to use their own custom protocol for livness detection. This enhacement allows for such a mechanism. The Orchagent creates an entry in the VNET_MONITOR_TABLE in APP DB if it recieves the "monitoring" = "custom" attribute in the VNET_ROUTE_TUNNEL_TABLE entry. The orchaagent then listens on VNET_MONITOR_TABLE in the STATE DB to monitor the livness of the VTEP.
The optional overlay_dmac field is  provided in the VNET table and is passed to the custom monitor via VNET_MONITOR_TABLE in APP DB.

The following module interaction diagram shows how the custom monitoring routes are handled.

![](https://github.com/sonic-net/SONiC/blob/5299343e188ef8f09e3abce234a0d5ed65a76feb/images/vxlan_hld/overlay-ecmp-module-interaction-with-custom-monitoring.png)


## 3.3 BFD Tx, Rx interval parameter and support for directly connected nexthops
 For [Smart Switch](https://github.com/kperumalbfn/SONiC/blob/kperumal/bfd/doc/smart-switch/BFD/SmartSwitchDpuLivenessUsingBfd.md) certian enhacements are required to distribute traffic to the connected DPUs. Some of these nexthop DPU would be directly connected to the NPU while others may not be. In addition, the BFD Tx and Rx interval also needs to be made configurable. Due to this reason the existing Overlay-ECMP implementation would not work for Smart Switch routes. To accommodate these needs, the following enhancements are proposed.
 
 - Add support for changing BFD Tx and Rx intervals for each route. 

 - Check nexthop in the ARP table to determine if a DPU is directly connected and employ regular ECMP route instead of Vxlan ECMP route. 

 For this puropose three new attributes are being added to the **VNET_ROUTE_TUNNEL_TABLE** as shown in the Schema update.
 - **tx_monitor_timer**
 - **rx_monitor_timer**
 - **check_directly_connected**

The Tx and Rx monitor timer attributes are intended for BFD sessions and would not be used to change the behavior of VNET-monitor sessions. The orchagent shall pass this monitor timer attributes to the BfdOrch at the time of BFD session creation. These values will not be passed to the custom monitor table in this phase of implementation. During route update if these values are updated, the Orchagent shall remove and recreate the BFD session. 

The check_directly_connected can be set to true or false. This is intended for the Smart Switch implementation and would be used by the Orchagent to check if any of the next hops are directly connected to the switch.  

Since  Smart Switch uses primary/secondary route model, it must ensure that all the next hops in either primary or secondary set must be direct connected. e.g. a primary set of two next hops where one is directly connected cannot be supported. Similarly, a secondary set of two next hops where one is directly connected is also not supported. If such a configuration is applied, this would result in failure. 

The Orchagent shall check all the next hops in the ARP table to verify if directly connected. For such next hops, a regular encamp route shall be employed instead of a tunnel route. This regular ECMP route would be updated based on the BFD liveness as is done for a regular vxlan ECMP route. 


# 4 Test Plan for the enhacements.

The below cases are executed first for IPv4 and repeat the same for IPv6.

| Step | Goal | Expected results |
|-|-|-|
| Create a tunnel route to a single endpoint A with prefix P1 and advertise prefix P. Establish the vnet monitor session. Send packets to the route prefix P1 | Test creation of tunnel route | Encapsulated packets should arrive at A. using syslog verify that prefix P is advertised. | 
| Add 3 more endpoints B, C, D to the tunnel route.  set A,B as primary. Establish vnet monitor sessions for the endpoints. Send packets. |  Update the tunnel | Encapsulated packets should arrive at A and B only. | 
| Bring down the vnet monitor session for A | Verify Switch over | Encapsulated packets should arrive at  B only. | 
| Bring up the vnet monitor session for A | Verify recovery | Encapsulated packets should arrive at a and B only. | 
| Bring down the vnet monitor session for A and B | Switch over to secondary | Encapsulated packets should arrive at C and D only. | 
| Bring down the vnet monitor session for C. | Secondary update | Encapsulated packets should arrive at D only. | 
| Bring up the vnet monitor session for C. | Secondary update | Encapsulated packets should arrive at C and D again. | 
| Bring up the vnet monitor session for A. | Switchover to primary | Encapsulated packets should arrive at A only. | 
| Bring up the vnet monitor session for B as well. | Primary distribution | Encapsulated packets should arrive at A and B only. | 
| Modify Route: Swap C, D as primary, A,B becomes secondary | Modify route should result in A, B being the next hops as the monitor sessions for C, D is down. | | Encapsulated packets should arrive at A and B only. | 
| Establish monitor sessions for C,D | Switchover to primary endpoints C, D | Encapsulated packets should arrive at C and D only. |
| Replace A,B,C,D with A’,B’,C’,D’  with A’,B’ as primary. | Verify endpoint replacement | Tunnel should go down | 
| Establish A’, B’ monitor sessions. Send traffic. | Verify tunnel bring up after replacement | Encapsulated packets should arrive at A’ and B’ only. | 
| Add a second tunnel route P2 with adv_prefix P and endpoints E, F, G, H (E, F primary) Establish vnet monitoring sessions for E, F, G, and H. send traffic on for P1 | 2 routes with same adv_prefix. | Encapsulated traffic should arrive on E,F. Ensure that P is still advertised. |  
| Remove tunnel route with prefix P1 | Route advertisement of P is unaffected | Ensure that P is still advertised by checking syslog for the absence of advertisement removal message of P. | 
| Consecutively add/ remove P1 multiple times | Route advertisement of P is unaffected | Ensure that P is still advertised by checking syslog for the absence of advertisement removal message of P. | 
| Remove P2 while P1 is already removed | Route advertisement for P should stop. | Ensure that P is no longer advertised by checking syslog message. | 
| Create a tunnel route with 1 primary and 1 secondary endpoint with bfd. Primary is directly connected. |Test creation of tunnel route | Encapsulated packets should arrive at primary. using syslog verify that prefix P is advertised. |
| Perform switch over testing by starting-stopping BFD sessions. | Switchover single next hop |Encapsulated packets should arrive at an active endpoint. using syslog verify that prefix P is advertised. |
| Create a tunnel route with 2 primary and 2 secondary endpoints with bfd. Primary is directly connected. |Test creation of tunnel route |Encapsulated packets should arrive at primary. using syslog verify that prefix P is advertised. |
| Perform switch over testing by starting-stopping BFD sessions. |Switchover from 2 to 1 next hop and vice versa with both directly and non-directly connected next hop. | Encapsulated packets should arrive at active endpoints. using syslog verify that prefix P is advertised. |
| Create a tunnel route with 2 primary and 2 secondary endpoints with bfd. one primary and one secondary is directly connected. |Test failure |Route creation should fail. |
| Create a tunnel route with 2 primary and 2 secondary endpoints with bfd. Secondary is directly connected. Change BFD tx and RX intervals. |BFD intervals change test | Verify BFD packet rate change. |


# TODO

Based on the community suggestions, the VNET_MONITOR_TABLE key should be enhanced to include the vnet name in the next iteration.