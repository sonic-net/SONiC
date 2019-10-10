Feature Name
# Draft Version - SONiC FRR-BGP Extended Unified Configuration Management Framework
## High Level Design Document
### Rev 0.1

## Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [Table 1: Abbreviations](#table-1-abbreviations)
  * [1 Feature Overview](#1-feature-overview)
      * [1.1 Requirements](#11-requirements)
        * [1.1.1 Functional Requirements](#111-functional-requirements)
        * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
        * [1.1.3 Scalability Requirements](#113-scalability-requirements)
        * [1.1.4 Warm Boot Requirements](#114-warmboot-requirements)
      * [1.2 Design Overview](#12-design-overview)
          * [1.2.1 Basic Approach](#121-basic-approach)
          * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
    * [3.3 SwSS Design](#33-swss-design)
    * [3.4 SyncD](#34-syncd)
    * [3.5 SAI](#35-sai)
    * [3.6 User Interface](#36-user-interface)
      * [3.6.1 Data Models](#361-data-models)
      * [3.6.2 CLI](#362-cli)
          * [3.6.2.1 Configuration Commands](#3621-configuration-command)
          * [3.6.2.2 Show Commands](#3622-show-command)
          * [3.6.2.3 Debug Commands](#3623-debug-command)
          * [3.6.2.4 IS-CLI Compliance](#3624-is-cli-compliance)
      * [3.6.3 REST API Support](#363-rest-api-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
    * [4.1 Configuration Sequence](#41-configuration-sequence)
    * [4.2 CLI Show Command Sequence](#42-cli-show-command-sequence)
      * [4.2.1 CLI Show Sequence - config only](#421-cli-show-sequence-config-only)
      * [4.2.2 CLI Show Sequence - State/Statistics](#422-cli-show-sequence-state-statistics)
    * [4.3 REST Get Sequence](#43-rest-get-sequence)
      * [4.3.1 REST Get Sequence - config only](#431-rest-get-sequence-config-only)
      * [4.3.2 REST Get Sequence - State/Statistics](#432-rest-get-sequence-state-statistics)
  * [5 Error Handling](#6-error-handling)
  * [6 Serviceability and Debug](#7-serviceability-and-debug)
  * [7 Warm Boot Support](#8-warm-boot-support)
  * [8 Scalability](#9-scalability)
  * [9 Unit Test](#10-unit-test)
  * [APPENDIX](#APPENDIX)


## List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

## Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/25/2019  | Karthikeyan Arumugam | Initial version                 |

## About this Manual
This document provides general information about the implementation of Extended Unified Configuration and Management framework support for FRR-BGP feature in SONiC.
## Scope
This document describes the high level design of FRR-BGP Extended Unified Configuration and Management feature.

## Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| FRR                      | Free Range Routing Stack            |
| CVL                      | Config Validation Library           |
| VRF                      | Virtual routing forwarding          |
| RIB                      | Routing Information Base            |
| PBR                      | Policy based routing                |
| NBI                      | North Bound Interface               |



# 1 Feature Overview

This feature extends and provides unified configuration and management capability for FRR-BGP features used in SONiC. This allows the user to configure & manage FRR-BGP using SONiC Management Framework with Open Config data models via REST, gNMI and also provides access via SONiC Management Framework CLI as well.


## 1.1 Requirements


### 1.1.1 Functional Requirements

  1. Extend Unified mode for full FRR-BGP config and management in SONiC
  2. Extend sonic-cfggen, bgpcfgd and integrate with FRR-BGP for features supported in SONiC
  3. Support for retrieval of FRR-BGP state and statistics information
  4. For backward compatibility retain access to FRR UI (vtysh) for managing features that are NOT in conflict with SONiC features

### 1.1.2 Configuration and Management Requirements

1. Support Open Config data models for BGP config and Management
2. Provide IS-CLI/gNMI/REST support for config and management of FRR-BGP features used in SONIC
3. Enhance with Custom YANG models for features used in BGP that are not supported via Open Config data model
4. Define ABNF schema for BGP features used in SONiC

### 1.1.3 Scalability Requirements
N/A

### 1.1.4 Warm Boot Requirements
As state and statistics information is retrieved from FRR-BGP on demand there is no Warm Boot specific requirements for this feature.

## 1.2 Design Overview
SONiC FRR-BGP Extended Unified config and management capability makes use of Management framework to implement the backend and transformer methods to support Open Config data models for BGP and route policy feature. The backend converts the incoming request to Redis ABNF schema format and writes the configuration to Redis DB. Then from DB events, bgpcfgd will configure FRR-BGP using FRR CLI commands.
It also uses management framework's transformer methods to do syntactic and semantic validation of the requests using ABNF JSON before writing them into the Redis DB.

### 1.2.1 Basic Approach

* This enhancement takes comprehensive approach to support BGP features used in SONiC:
	* Standard based YANG models and custom YANG models
	* Open API spec
	* Industry standard CLI
	* Config Validation
* REST server, gNMI server, Transformer methods - all in Go
* Marshalling and unmarshalling using YGOT
* Redis updated using CAS(Check-and-Set) trans. (No locking, No rollback)
* Config Validation by using YANG model from ABNF schema

### 1.2.2 Container

There will be changes in following containers,
* sonic-mgmt-framework
* sonic-frr

### 1.2.3 SAI Overview
N/A - software feature


# 2 Functionality
## 2.1 Target Deployment Use Cases
Configure and manage FRR-BGP via gNMI, REST and CLI interfaces using SONiC Management Framework.

## 2.2 Functional Description
Provide GNMI and REST support for config get/set, state get and statistics get,  CLI config and show commands for FRR-BGP features used in SONiC.


# 3 Design
## 3.1 Overview
The extended unified config and management framework for FRR-BGP in SONiC is represented in below diagram.

![FRR-BGP Unified Mgmt Framework](images/FRR-BGP-Unified-mgmt-frmwrk.png)

1. Transformer common app owns the Open config data models related to BGP (which means no separate app module required for handling BGP yang objects).

    * openconfig-network-instance.yang
    * openconfig-bgp.yang
    * openconfig-bgp-global.yang
    * openconfig-bgp-neighbor.yang
    * openconfig-bgp-peer-group.yang
    * openconfig-routing-policy.yang
    * openconfig-bgp-policy.yang
    * openconfig-rib-bgp.yang

2. Provide annotations for required objects so that transformer core and common app will take care of handling them.

3. Provide transformer methods as per the annotations defined to take care of model specific logics and validations.

4. Define SONiC YANG and Redis ABNF schema for the supported Open Config BGP models & objects.

5. In bgpcfgd register for Redis DB events for the BGP and other related objects, so as to translate the Redis DB events to FRR-BGP CLI commands to configure FRR-BGP.

6. Update frr.conf.j2 template for new FRR-BGP configurations supported in SONiC which will be used by sonic-cfggen to generate frr.conf file.


## 3.2 DB Changes
Following section describes the changes to DB.

### 3.2.1 CONFIG DB
> [TODO] Add the DB schema

Added new tables to configure following information:

  * BGP router configurations
  * BGP neighbor configurations
  * BGP address-family configurations
  * BGP template configurations
  * BGP community configurations
  * Route policy configurations
> [TODO] Add any other tables added to DB

Enhance following tables to configure additional attributes:

  * BGP Neighbor table

#### 3.2.1.1 Add a BGP_INST_TABLE in CONFIG_DB
```JSON
;Defines BGP routing instance table
;
;Status: stable

key                   = BGP_INST_TABLE:vrf_name ;
local_asn             = uint32 ; Local ASN for the BGP instance
router_id             = \*IPv4prefix ; Router ID IPv4 address
load_balance_mp_relax = "true" / "false" ;
grace_restart         = "true" / "false" ;
```

#### 3.2.1.2 Enhance BGP_NEIGHBOR table in CONFIG_DB
> [TODO] check current BGP neighbor table definition and update for any additions to existing table.

```JSON
;Defines BGP neighbor table
;
;Status: stable

key               = BGP_NEIGHBOR:vrf_name:IPprefix ;
IPprefix          = IPv4Prefix / IPv6prefix ;
local_asn         = uint32 ; Local ASN for the BGP neighbor
descr             = 1*64VCHAR ; BGP neighbor description
ebgp_mhop_count   = uint8 ; EBGP multihop count
peer_asn          = uint32 ; Remote ASN
admin             = "true" / "false" ; Neighbor admin status
keepalive_intvl   = uint16 ; keepalive interval
hold_time         = uint16 ; hold time
local_address     = IPprefix ; local IP address
peer_group        = 1*64VCHAR ; peer group name
```
#### 3.2.1.3 Add BGP_NEIGHBOR_AF table in CONFIG_DB
```JSON
;Defines BGP Neighbor table at an address family level
;
;Status: stable

key           = BGP_NEIGHBOR_AF:vrf_name:prefix:af ;
admin         = "true" / "false" ; Neighbor admin status
allow_asin    = uint8 ;  Number of occurences of ASN
route_map     = 1*64VCHAR ; route map filter to apply for this neighbor
direction     = "in" / "out" ; direction to apply for this route map
```

#### 3.2.1.4 Add BGP_PEER_GROUP table in CONFIG_DB
> [TODO] check if there is any existing peer group DB.

```JSON
;Defines BGP peer group table
;
;Status: stable

key              = BGP_PEER_GROUP:vrf_name:peer_group_name ;
peer_group_name  = 1*64VCHAR ; alias name for the peer group template, must be unique
local_asn        = 1\*10DIGIT ; Local ASN for the BGP peer group
descr             = 1*64VCHAR ; BGP peer group description
ebgp_mhop_count   = uint8 ; EBGP multihop count
peer_asn          = uint32 ; Remote ASN
admin             = "true" / "false" ; Peer group admin status
keepalive_intvl   = uint16 ; keepalive interval
hold_time         = uint16 ; hold time
local_address     = IPprefix ; local IP address
```
#### 3.2.1.5 Add BGP_AF_PEER_GROUP table in CONFIG_DB
> [TODO] check if there is any existing peer group DB.

```JSON
;Defines BGP per address family peer group table
;
;Status: stable

key               = BGP_AF_PEER_GROUP:vrf_name:af:peer_group_name ;
af                = "IPv4" / "IPv6"  ; address family
peer_group_name   = 1*64VCHAR ; alias name for the peer group template, must be unique
admin             = "true" / "false" ; Peer group admin status
allow_asin        = uint8 ;  Number of occurences of ASN
route_map         = 1*64VCHAR ; route map filter to apply for this peer group
direction         = "in" / "out" ; direction to apply for this route map
```

#### 3.2.1.6 Add BGP_AF table in CONFIG_DB
```JSON
;Defines BGP Address family table
;
;Status: stable

key           = BGP_AF:vrf_name:af ;
af            = "IPv4" / "IPv6"  ; address family
source        = "connected" / "static" ; route types to redistribute
route_map     = 1*64VCHAR ; route map filter to apply for redistribute
```

#### 3.2.1.7 Add BGP_LISTEN_PREFIX table in CONFIG_DB
```JSON
;Defines BGP Listen Prefix table
;
;Status: stable

key             = BGP_AF:vrf_name:IPprefix ;
peer_group_name = 1*64VCHAR ; Peer group this listen prefix is associated with
```

### 3.2.2 APP DB
N/A

### 3.2.3 STATE DB
No changes to State DB, State and statistics information will be retrieved directly from FRR-BGP through bgpcfgd.

### 3.2.4 ASIC DB
N/A

### 3.2.5 COUNTER DB
N/A

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent
No changes to Orch agent.

### 3.3.2 Other Process

#### 3.3.2.1 FRR Template Changes

FRR template must be enhanced to contain FRR-BGP related configuration that are supported via FRR-BGP extended unified config management framework.

On startup sonic-cfggen will use frr.conf.j2 to generate frr.conf file. The generated frr.conf with all SONiC supported configurations will look like the following:
> [TODO] - update the FRR-BGP CLI's now supported via frr.conf.j2 Template

## 3.4 SyncD
No changes to SyncD

## 3.5 SAI
No changes to SAI APIs.

## 3.6 User Interface
### 3.6.1 Data Models
List of  Open-config yang models required for FRR-BGP Unified Configuration and Management are,

    1) openconfig-network-instance.yang

    2) openconfig-bgp.yang

    3) openconfig-bgp-global.yang

    4) openconfig-bgp-neighbor.yang

    5) openconfig-bgp-peer-group.yang

    6) openconfig-routing-policy.yang

    7) openconfig-bgp-policy.yang

    8) openconfig-rib-bgp.yang

Supported yang objects and attributes:

> [TODO] - update the supported YANG objects tree under each model


### 3.6.2 CLI
  1. For all configuration commands, the CLI request is converted to a corresponding REST client SDK request based on the Open Config data model that was generated by the Swagger generator, and is given to the REST server.

  2. From there on it will follow the same path as a REST config request for create, update and delete operations.

  3. The Swagger generated REST server handles all the REST requests from the client SDK and invokes a common handler for all the create, update, replace, delete and get operations along with path and payload. This common handler converts all the requests into Transformer arguments and invokes the corresponding Transformer APIs.

  4. For show commands, the CLI request is converted to a corresponding REST client SDK get request based on Open Config data model's config or state object on a case by case basis.

  5. For show commands that requires retrieval of the data that doesn't contain any state information (information only based on the configuration), the backend callback will fetch the data from CONFIG_DB.

  6. For show commands that requires retrieval of state or statistics information the backend callback will fetch the data from FRR-BGP.

  7. State/stats information is retried from FRR-BGP by issuing a show command to FRR BGP container and the output is returned in JSON format.

  8. At transformer this JSON output is now converted back to corresponding OC objects and returned to the caller.

  9. For CLI show, the output returned in object format is then translated back to CLI Jinga template for output display in CLI.


#### 3.6.2.1 Configuration Commands

##### 3.6.2.1.1 BGP Router mode commands

|Command Description |CLI Command      |
|:-----------------|:---------------|
|Enable BGP routing instance |sonic(config)# router bgp \<local_asn> [vrf \<vrf_name>] |
|Override configured BGP router-id |sonic(config-router-bgp-\<local-asn>)# router-id \<IPv4> |
|Configure default best path selection |sonic(config-router)# bgp bestpath as-path multipath-relax|
|Configure graceful restart capability params |sonic(config-router)# bgp graceful-restart preserve-fw-state <br> sonic(config-router)# bgp graceful-restart restart-time <1-3600> <br> sonic(config-router)# bgp graceful-restart stalepath-time <1-3600>|
|Configure BGP IPv4/IPv6 neighbor |sonic(config-router)# neighbor \<IP\> local-as \<1-4294967295>|
|Configure BGP template |sonic(config-router)# template \<peer-group-name\>|
|Enter address family command mode|sonic(config-router)# address-family { ipv4 \| ipv6 } unicast|

##### 3.6.2.1.2 BGP Neighbor mode commands
|Command Description |CLI Command      |
|:-----------------|:---------------|
|Configure neighbor description|sonic(config-router-neighbor)#description \<string\>|
|Configure EBGP neighbors hop count |sonic(config-router-neighbor)#ebgp-multihop \<hop-count\>|
|Configure a BGP neighbor ASN|sonic(config-router-neighbor)#remote-as \<ASN\>|
|Administratively bring down a neighbor|sonic(config-router-neighbor)# shutdown|
|Configure BGP neighbor timers|sonic(config-router-neighbor)#timers \<keepalive-time\> \<hold-time\>|
|Configure source of routing updates|sonic(config-router-neighbor)#update-source \<IP-addr\>|
|Specify the peer-group template to inherit for this neighbor|sonic(config-router-neighbor)#inherit template \<peer-group\>|
|Specify address family for a BGP neighbor|sonic(config-router-neighbor)#address-family {ipv4 \| ipv6} unicast <br> sonic(config-router-neighbor)# address-family l2vpn evpn <br> |


##### 3.6.2.1.3 BGP Neighbor Address family mode commands
|Command Description |CLI Command    |
|:-----------------|:---------------|
|Activate a BGP neighor for a specific address family|sonic(config-router-neighbor-af)#activate|
|Config as-path acceptance with own ASN|sonic(config-router-neighbor-af)#allowas-in \<AS occurrence count\> |
|Specify route policy map to neighbor mapping|sonic(config-router-neighbor-af)#route-map \<name\> {in \| out} |

##### 3.6.2.1.4 BGP Template mode commands
|Command Description|CLI Command      |
|:-----------------|:---------------|
|Configure BGP template's description|sonic(config-router-template)#description \<string\>|
|Configure BGP template's EBGP hop count|sonic(config-router-template)#ebgp-multihop \<hop-count\>|
|Configure BGP template's remote ASN|sonic(config-router-template)#remote-as \<ASN\>|
|Configure BGP template's admin status|sonic(config-router-template)# shutdown|
|Configure BGP template's timers|sonic(config-router-template)#timers \<keepalive-time\> \<hold-time\>|
|Configure BGP template's source of routing updates|sonic(config-router-template)#update-source \<IP-addr\>|
|Configure BGP dynamic neighbors listen range|sonic(config-router-template)#listen \<prefix\> |
|Specify address family for a BGP neighbor template|sonic(config-router-template)#address-family {ipv4 \| ipv6} unicast <br> sonic(config-router-template)# address-family l2vpn evpn <br> |

##### 3.6.2.1.5 BGP Template Address family mode commands
|Command Description|CLI Command      |
|:-----------------|:---------------|
|Activate BGP template at an address family level|sonic(config-router-bgp-template-af)#  activate|
|Configure as-path acceptance with own ASN at BGP template address family level|sonic(config-router-bgp-template-af)#allowas-in \<AS occurrence count\>|
|Specify route policy map to BGP template mapping|sonic(config-router-bgp-template-af)#route-map \<name\> {in \| out} |

##### 3.6.2.1.6 BGP Router Address family mode commands
|Command Description|CLI Command      |
|:-----------------|:---------------|
|Configure route redistribution policy|sonic(config-router-bgpv4-af)# redistribute { static \| connected } [route-map \<route-map-name\>] <br> sonic(config-router-bgpv6-af)# redistribute { static \| connected } [route-map \<route-map-name\>] |

##### 3.6.2.1.7 Routing policy commands
|Command Description|CLI Command      |
|:-----------------|:---------------|
|Configure routing policy match criteria and associated actions|sonic(config)#route-map \<map-name\> { permit \| deny } \<sequence-number\> |
|Configure routing policy match criteria|sonic(config-route-map)# match as-path \<list\> <br> sonic(config-route-map)# match community \<list\> <br> sonic(config-route-map)# match ext-community \<list\> <br> sonic(config-route-map)# match interface \<intf-name\> <br> sonic(config-route-map)# match ip address prefix-list \<name\> <br> sonic(config-route-map)# match ipv6 address prefix-list \<name\> <br> sonic(config-route-map)# match metric \<val\> <br> sonic(config-route-map)# match route-type { internal \| external } <br> sonic(config-route-map)# match origin { egp \| igp \| incomplete } <br> sonic(config-route-map)# tag \<value\>|
|Configure routing policy actions|sonic(config-route-map)# set as-path prepend \<list\> <br> sonic(config-route-map)# set comm-list \<name\> { add \| del } <br> sonic(config-route-map)# set community \<options\> <br> sonic(config-route-map)# set ext-community <br> sonic(config-route-map)# set ip next-hop <br> sonic(config-route-map)# set ipv6 next-hop <br> sonic(config-route-map)# set local-preference \<val\> <br> sonic(config-route-map)# set metric \<val\> <br> sonic(config-route-map)#set origin { igp \| egp \| incomplete } <br> sonic(config-route-map)# set tag \<value\> |


#### 3.6.2.2 Show Commands
|Command Description|CLI Command      |
|:------------------|:-----------------|
|Display BGP neighbors|show ip bgp neighbors|
|Display BGP summary|show ip bgp summary|

> [TODO] - update the show command list.

#### 3.6.2.3 Debug Commands
N/A

#### 3.6.2.4 IS-CLI Compliance
> [TODO] - update this section with new IS-CLI to FRR CLI mapping to explain the differences.

The following table maps SONIC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  – meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  – meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONIC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONIC.

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---|:-----------|:------------------|:-----------------------------------|
| | | | |
| | | | |


**Deviations from IS-CLI:** If there is a deviation from IS-CLI, Please state the reason(s).

### 3.6.3 REST API Support

#### PATCH API
REST PATCH APIs are supported using the following openconfig BGP yang objects.
> [TODO] - Update this section for REST config path.

|Command description | OpenConfig Command Path |
|:---|:-----------|
|`Configure BGP router AS number`|`/network-instances/network-instance<vrf>/protocols<BGP,instance-id>/protocol/bgp/global/config/as=<local_asn>`|
|`Configure BGP router-id` |`/network-instances/network-instance/protocols/protocol/bgp/global/config/router-id=<IPv4>` |
|`Configure to allow ebgp multipath AS` |`/network-instances/network-instance/protocols/protocol/bgp/global/use-multiple-paths/ebgp/config/allow-multiple-as=<true\|false>` |
|`Configure protocol Graceful restart capability` |`network-instances/network-instance/protocols/protocol/bgp/global/graceful-restart/config/enabled=<true\|false>` |
|`Configure BGP neighbors local ASN` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/config/neighbor-address=<IP> local-as=<local_asn>` |
|`Configure BGP peer group local ASN` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/config/peer-group-name=<peer-group> local-as=<local_asn>` |
|`Configure BGP address family type` |`network-instances/network-instance/protocols/protocol/bgp/global/afi-safis/afi-safi/config/afi-safi-name=<IPV4_UNICAST\| IPV6_UNICAST \| L2VPN_EVPN>`|
|`Configure BGP neighbors description` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/config/neighbor-address=<IP> description=<string>` |
|`Enable EBGP Multihop count` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/ebgp-multihop/config/enabled=<true> multihop-ttl=<hop-cnt>` |
|`Configure BGP neighbors remote ASN` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/config/neighbor-address=<IP> peer-as=<remote_asn>` |
|`Configure BGP neighbor admin status` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/config/neighbor-address=<IP> enabled=<true>` |
|`Configure BGP neighbors timers` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/timers/config/neighbor-address=<IP> keepalive-interval= <keepalive intvl> hold-time = <hold-time>` |
|`Configure source address for BGP neighbor` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/transport/config/neighbor-address=<IP> local-address=<local-IP>` |
|`Configure template to inherit for a BGP neighbor` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/config/neighbor-address=<IP> peer-group=<peer-group>` |
|`Configure address family for a BGP neighbor` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/config/neighbor-address=<IP> afi-safi-name=<IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN>` |
|`Configure admin status for a given BGP neighbor and address family ` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/config/neighbor-address=<IP> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN} enabled=<true>` |
|`Configure ingress route filtering for a BGP neighbor` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/config/neighbor-address=<IP> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN}  import-policy= <route-map>` |
|`Configure egress route filtering for a BGP neighbor` |`network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/config/neighbor-address=<IP> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN}  export-policy= <route-map>` |
|`Configure ingress route filtering for a BGP peer group` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy import-policy= <route-map>` |
|`Configure egress route filtering for a BGP peer group` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy export-policy= <route-map>` |
|`Configure BGP template's description` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/config/peer-group-name=<peer-group> description=<string>` |
|`Enable EBGP Multihop count for a template` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/ebgp-multihop/config/peer-group-name=<peer-group> enabled=<true> multihop-ttl=<hop-cnt>` |
|`Configure BGP template's remote ASN` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/config/peer-group-name=<peer-group> peer-as=<remote_asn>` |
|`Configure BGP template's admin status` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/config/peer-group-name=<peer-group> enabled=<true>` |
|`Configure BGP template's timers` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/timers/config/peer-group-name=<peer-group> keepalive-interval=<keepalive intvl> hold-time=<hold-time>` |
|`Configure source address for BGP template` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/transport/config peer-group-name=<peer-group> local-address=<local-IP>` |
|`Configure Listen prefix to BGP template` |`network-instances/network-instance/protocols/protocol/bgp/global/dynamic-neighbor-prefixes/dynamic-neighbor-prefix/config/prefix=<prefix> peer-group=<peer-group>` |
|`Configure address family for a BGP template` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/config/peer-group-name=<peer-group> afi-safi-name=<IPV4_UNICAST  \| IPV6_UNICAST \| L2VPN_EVPN>` |
|`Configure admin status of BGP template at address family level` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/config/peer-group-name=<peer-group> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN} enabled=<true>` |
|`Configure ingress route filtering for a BGP peer group at an address family level` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/config/peer-group-name=<peer-group> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN} network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy/import-policy=<route-map>` |
|`Configure egress route filtering for a BGP peer group at an address family level` |`network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/config/peer-group-name=<peer-group> afi-safi-name={IPV4_UNICAST \| IPV6_UNICAST \| L2VPN_EVPN} network-instances/network-instance/protocols/protocol/bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy/export-policy=<route-map>` |
|`Configure route redistribution policy` |`network-instances/network-instance/table-connections/table-connection/config/src_protocol={connected \| static } dest_protocol=BGP address_family=IPv4_UNICAST import-policy=<route-map>` |
|`Configure route filtering Policy`|`routing-policy/policy-definitions/policy-definition/config/name=<name> routing-policy/policy-definitions/policy-definition/config/statements/statement/name=<seq> routing-policy/policy-definitions/policy-definition/config/statements/statement/action=<ACCEPT_ROUTE = permit> or <REJECT_ROUTE = deny>` |
|`Route filtering policy match as-path` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/bgp-conditions/match-as-path-set/config/as-path-set=<list> match-set-options-type=ALL` |
|`Route filtering policy match community` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/bgp-conditions/config/community-set/config/community-set-name=<string>` |
|`Route filtering policy match community list` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/bgp-conditions/config/ext-community-set=<list>` |
|`Route filtering policy match interface ` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/match-interface=<intf-name>` |
|`Route filtering policy match IPv4/IPv6 prefix-list ` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/match-prefix-set/config/prefix-set=<name> match-set-options=ANY` |
|`Route filtering policy match route type` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/bgp-conditions/config route-type={ INTERNAL \| EXTERNAL }` |
|`Route filtering policy match route origin` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/bgp-conditions/config/origin-eq= { IGP \| EGP \| INCOMPLETE }` |
|`Route filtering policy match Tag` |`routing-policy/policy-definitions/policy-definition/config/statements/statement/conditions/match-tag-set/config/tag-set=<value> match-set-options=ANY` |
|`Route filtering policy action prepend as-path list` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/bgp-actions/set-as-path-prepend/config/repeat-n = 2 asn=65100 asn=65101` |
|`Route filtering policy action set community options` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/bgp-actions/set-community/reference = /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/community-sets/community-set/community-set-name` |
|`Route filtering policy action set extended community options` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/bgp-actions/set-ext-community/reference=/oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/ext-community-sets/ext-community-set/ext-community-set-name` |
|`Route filtering policy action IPv4/IPv6 options` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/match-prefix-set/config/match-prefix-set=<> match-set-options=<>` |
|`Route filtering policy action set local preference` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/bgp-actions/config set-local-pref=<val>` |
|`Route filtering policy action set route origin` |`routing-policy/policy-definitions/policy-definition/statements/statement/actions/bgp-actions/config/set-route-origin=<val>` |
|`Route filtering policy action prefix list` |`routing-policy/defined-sets/prefix-sets/prefix-set/prefixes/config/name=<> mode=<> prefixes/prefix=<> ip-prefix=<> masklength-range=` |
|`Route filtering policy action set AS path list` |`routing-policy/defined-sets/bgp-defined-sets/as-path-sets/as-path-set/config/as-path-set-name=<name> as-path-set-member=<>` |


#### DELETE API
REST DELETE APIs are supported using the following openconfig BGP yang objects.
> [TODO] - Update this section for REST delete path.

|Command description | OpenConfig Command Path |
|:---|:-----------|
| | |
| | |
| | |

#### GET API
GET is supported using the following openconfig BGP yang objects.
> [TODO] - Update this section for REST GET path.

|Command description | OpenConfig Command Path |
|:---|:-----------|
| | |
| | |
| | |

# 4 Flow Diagrams

## 4.1 Configuration Sequence

![FRR-BGP-CONFIG-SEQUENCE](images/frr-bgp-config-sequence.jpg)

## 4.2 CLI Show Command Sequence
> [TBD] - Alternative design for CLI show is, from CLI renderer fetch DB get and convert it to Jinga template. This needs to be explored and updated accordingly.

### 4.2.1 CLI Show Sequence - Config information
![FRR-BGP-CLI-SHOW-SEQUENCE1](images/frr-bgp-cli-show-sequence11.jpg)

### 4.2.2 CLI Show Sequence - State/Statistics
![FRR-BGP-CLI-SHOW-SEQUENCE2](images/frr-bgp-cli-show-sequence22.jpg)

## 4.3 REST Get Sequence

### 4.3.1 REST Get Sequence - Config information
![FRR-BGP-REST-GET-SEQUENCE1](images/frr-bgp-rest-get-sequence1.jpg)

### 4.3.2 REST Get Sequence - State/Statistics
![FRR-BGP-REST-GET-SEQUENCE2](images/frr-bgp-rest-get-sequence2.jpg)

# 5 Error Handling

Validation is done at both north bound interface and against database schema. Appropriate error code is returned for invalid configuration or on failures due to a dependency. All application errors are logged into syslog.

# 6 Serviceability and Debug

  1. Tables added to CONFIG_DB for FRR-BGP unified management are accessible via table dump.
  2. Syslog messages are added at appropriate places to help trace a failure.
  3. Leverages existing debug mechanism & framework if any.

# 7 Warm Boot Support

This enhancement to FRR-BGP Unified management framework does not disrupt data plane traffic during warmboot. No special handling required for warmboot.

# 8 Scalability

Describe key scaling factor and considerations.
> [TODO] - Update this section based on how scaled configurations are dealt with.

# 9 Unit Test
List unit test cases added for this feature including warm boot.
> [TODO] - Update this section with all test information.

# 10 Appendix
