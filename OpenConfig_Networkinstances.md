# OpenConfig support for Network Instances

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
      * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
      * [1.1.3 Scalability Requirements](#113-scalability-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)
      * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
      * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author                | Change Description                |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 12/02/2025  | Venkata Krishna Rao G       | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of Network Instances in SONiC.

# Scope
- This document describes the high level design of OpenConfig configuration of Network Instances via REST and gNMI in SONiC.
- This does not cover the SONiC KLISH CLI.
- This covers network instance configuration including BGP protocol support, table connections, and route aggregation.
- This does not cover gNMI subscription.
- Supported attributes in OpenConfig YANG tree:
  ```  
  module: openconfig-network-instance
  +--rw network-instances
     +--rw network-instance* [name]
        +--rw name                                        -> ../config/name
        +--rw config
        |  +--rw name?   string
        |  +--rw type    identityref
        +--ro state
        |  +--ro name?   string
        |  +--ro type    identityref
        +--rw table-connections
        |  +--rw table-connection* [src-protocol dst-protocol address-family]
        |     +--rw src-protocol      -> ../config/src-protocol
        |     +--rw dst-protocol      -> ../config/dst-protocol
        |     +--rw address-family    -> ../config/address-family
        |     +--rw config
        |     |  +--rw src-protocol?     -> ../../../../tables/table/config/protocol
        |     |  +--rw address-family?   -> ../../../../tables/table[protocol=current()/../src-protocol]/config/address-family
        |     |  +--rw dst-protocol?     -> ../../../../tables/table/config/protocol
        |     |  +--rw import-policy*    -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        |     +--ro state
        |        +--ro src-protocol?     -> ../../../../tables/table/config/protocol
        |        +--ro address-family?   -> ../../../../tables/table[protocol=current()/../src-protocol]/config/address-family
        |        +--ro dst-protocol?     -> ../../../../tables/table/config/protocol
        |        +--ro import-policy*    -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        +--rw tables
        |  +--rw table* [protocol address-family]
        |     +--rw protocol          -> ../config/protocol
        |     +--rw address-family    -> ../config/address-family
        |     +--rw config
        |     |  +--rw protocol?         -> ../../../../protocols/protocol/config/identifier
        |     |  +--rw address-family?   identityref
        |     +--ro state
        |        +--ro protocol?         -> ../../../../protocols/protocol/config/identifier
        |        +--ro address-family?   identityref
        +--rw protocols
        |  +--rw protocol* [identifier name]
        |     +--rw identifier          -> ../config/identifier
        |     +--rw name                -> ../config/name
        |     +--rw config
        |     |  +--rw identifier?   identityref
        |     |  +--rw name?         string
        |     +--ro state
        |     |  +--ro identifier?   identityref
        |     |  +--ro name?         string
        |     +--rw local-aggregates
        |     |  +--rw aggregate* [prefix]
        |     |     +--rw prefix    -> ../config/prefix
        |     |     +--rw config
        |     |     |  +--rw prefix?                                 inet:ip-prefix
        |     |     |  +--rw oc-network-instance-ext:summary-only?   boolean
        |     |     +--ro state
        |     |        +--ro prefix?                                 inet:ip-prefix
        |     |        +--ro oc-network-instance-ext:summary-only?   boolean
        |     +--rw bgp
        |        +--rw global
        |        |  +--rw config
        |        |  |  +--rw as                                                         oc-inet:as-number
        |        |  |  +--rw router-id?                                                 oc-yang:dotted-quad
        |        |  |  +--rw oc-network-instance-ext:enable-default-ipv4-unicast-afi?   boolean
        |        |  |  +--rw oc-network-instance-ext:max-dynamic-neighbor-prefixes?     uint16
        |        |  +--ro state
        |        |  |  +--ro as                                                         oc-inet:as-number
        |        |  |  +--ro router-id?                                                 oc-yang:dotted-quad
        |        |  |  +--ro oc-network-instance-ext:enable-default-ipv4-unicast-afi?   boolean
        |        |  |  +--ro oc-network-instance-ext:max-dynamic-neighbor-prefixes?     uint16
        |        |  +--rw graceful-restart
        |        |  |  +--rw config
        |        |  |  |  +--rw enabled?                                     boolean
        |        |  |  |  +--rw restart-time?                                uint16
        |        |  |  |  +--rw stale-routes-time?                           uint16
        |        |  |  |  +--rw oc-network-instance-ext:preserve-fw-state?   boolean
        |        |  |  +--ro state
        |        |  |     +--ro enabled?                                     boolean
        |        |  |     +--ro restart-time?                                uint16
        |        |  |     +--ro stale-routes-time?                           uint16
        |        |  |     +--ro oc-network-instance-ext:preserve-fw-state?   boolean
        |        |  +--rw use-multiple-paths
        |        |  |  +--rw config
        |        |  |  +--ro state
        |        |  |  +--rw ebgp
        |        |  |     +--rw config
        |        |  |     |  +--rw allow-multiple-as?   boolean
        |        |  |     +--ro state
        |        |  |        +--ro allow-multiple-as?   boolean
        |        |  +--rw route-selection-options
        |        |  |  +--rw config
        |        |  |  |  +--rw external-compare-router-id?                     boolean
        |        |  |  |  +--rw oc-network-instance-ext:network-import-check?   boolean
        |        |  |  +--ro state
        |        |  |     +--ro external-compare-router-id?                     boolean
        |        |  |     +--ro oc-network-instance-ext:network-import-check?   boolean
        |        |  +--rw afi-safis
        |        |  |  +--rw afi-safi* [afi-safi-name]
        |        |  |     +--rw afi-safi-name                       -> ../config/afi-safi-name
        |        |  |     +--rw config
        |        |  |     |  +--rw afi-safi-name?                           identityref
        |        |  |     |  +--rw enabled?                                 boolean
        |        |  |     |  +--rw oc-network-instance-ext:import-policy*   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        |        |  |     +--ro state
        |        |  |     |  +--ro afi-safi-name?                           identityref
        |        |  |     |  +--ro enabled?                                 boolean
        |        |  |     |  +--ro oc-network-instance-ext:import-policy*   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        |        |  |     +--rw use-multiple-paths
        |        |  |     |  +--rw config
        |        |  |     |  +--ro state
        |        |  |     |  +--rw ebgp
        |        |  |     |  |  +--rw config
        |        |  |     |  |  |  +--rw maximum-paths?   uint32
        |        |  |     |  |  +--ro state
        |        |  |     |  |     +--ro maximum-paths?   uint32
        |        |  |     |  +--rw ibgp
        |        |  |     |     +--rw config
        |        |  |     |     |  +--rw maximum-paths?   uint32
        |        |  |     |     +--ro state
        |        |  |     |        +--ro maximum-paths?   uint32
        |        |  |     +--rw oc-network-instance-ext:networks
        |        |  |        +--rw oc-network-instance-ext:network* [prefix]
        |        |  |           +--rw oc-network-instance-ext:prefix    -> ../config/prefix
        |        |  |           +--rw oc-network-instance-ext:config
        |        |  |           |  +--rw oc-network-instance-ext:prefix?   inet:ip-prefix
        |        |  |           +--ro oc-network-instance-ext:state
        |        |  |              +--ro oc-network-instance-ext:prefix?   inet:ip-prefix
        |        |  +--rw dynamic-neighbor-prefixes
        |        |  |  +--rw dynamic-neighbor-prefix* [prefix]
        |        |  |     +--rw prefix    -> ../config/prefix
        |        |  |     +--rw config
        |        |  |     |  +--rw prefix?       oc-inet:ip-prefix
        |        |  |     |  +--rw peer-group?   -> ../../../../../peer-groups/peer-group/config/peer-group-name
        |        |  |     +--ro state
        |        |  |        +--ro prefix?       oc-inet:ip-prefix
        |        |  |        +--ro peer-group?   -> ../../../../../peer-groups/peer-group/config/peer-group-name
        |        |  +--rw apply-policy
        |        |  |  +--rw config
        |        |  |  |  +--rw oc-network-instance-ext:ebgp-requires-policy?   boolean
        |        |  |  +--ro state
        |        |  |     +--ro oc-network-instance-ext:ebgp-requires-policy?   boolean
        |        |  +--rw oc-network-instance-ext:logging-options
        |        |  |  +--rw oc-network-instance-ext:config
        |        |  |  |  +--rw oc-network-instance-ext:log-neighbor-state-changes?   boolean
        |        |  |  +--ro oc-network-instance-ext:state
        |        |  |     +--ro oc-network-instance-ext:log-neighbor-state-changes?   boolean
        |        |  +--rw oc-network-instance-ext:timers
        |        |     +--rw oc-network-instance-ext:config
        |        |     |  +--rw oc-network-instance-ext:hold-time?            uint16
        |        |     |  +--rw oc-network-instance-ext:keepalive-interval?   uint16
        |        |     +--ro oc-network-instance-ext:state
        |        |        +--ro oc-network-instance-ext:hold-time?            uint16
        |        |        +--ro oc-network-instance-ext:keepalive-interval?   uint16
        |        +--rw neighbors
        |        |  +--rw neighbor* [neighbor-address]
        |        |     +--rw neighbor-address    -> ../config/neighbor-address
        |        |     +--rw config
        |        |     |  +--rw peer-group?         -> ../../../../peer-groups/peer-group/peer-group-name
        |        |     |  +--rw neighbor-address?   union
        |        |     |  +--rw peer-as?            oc-inet:as-number
        |        |     |  +--rw description?        string
        |        |     +--ro state
        |        |     |  +--ro peer-group?         -> ../../../../peer-groups/peer-group/peer-group-name
        |        |     |  +--ro neighbor-address?   union
        |        |     |  +--ro peer-as?            oc-inet:as-number
        |        |     |  +--ro description?        string
        |        |     +--rw timers
        |        |     |  +--rw config
        |        |     |  |  +--rw hold-time?            uint16
        |        |     |  |  +--rw keepalive-interval?   uint16
        |        |     |  +--ro state
        |        |     |     +--ro hold-time?            uint16
        |        |     |     +--ro keepalive-interval?   uint16
        |        |     +--rw afi-safis
        |        |     |  +--rw afi-safi* [afi-safi-name]
        |        |     |     +--rw afi-safi-name           -> ../config/afi-safi-name
        |        |     |     +--rw config
        |        |     |     |  +--rw afi-safi-name?         identityref
        |        |     |     |  +--rw enabled?               boolean
        |        |     |     +--ro state
        |        |     |     |  +--ro afi-safi-name?         identityref
        |        |     |     |  +--ro enabled?               boolean
        |        |     +--rw enable-bfd
        |        |        +--rw config
        |        |        |  +--rw enabled?                       boolean
        |        |        |  +--rw desired-minimum-tx-interval?   uint32
        |        |        |  +--rw required-minimum-receive?      uint32
        |        |        |  +--rw detection-multiplier?          uint8
        |        |        +--ro state
        |        |           +--ro enabled?                       boolean
        |        |           +--ro desired-minimum-tx-interval?   uint32
        |        |           +--ro required-minimum-receive?      uint32
        |        |           +--ro detection-multiplier?          uint8
        |        +--rw peer-groups
        |        |  +--rw peer-group* [peer-group-name]
        |        |     +--rw peer-group-name     -> ../config/peer-group-name
        |        |     +--rw config
        |        |     |  +--rw peer-group-name?   string
        |        |     |  +--rw peer-type?         oc-bgp-types:peer-type
        |        |     +--ro state
        |        |     |  +--ro peer-group-name?   string
        |        |     |  +--ro peer-type?         oc-bgp-types:peer-type
        |        |     +--rw timers
        |        |     |  +--rw config
        |        |     |  |  +--rw connect-retry?        uint16
        |        |     |  |  +--rw hold-time?            uint16
        |        |     |  |  +--rw keepalive-interval?   uint16
        |        |     |  +--ro state
        |        |     |     +--ro connect-retry?        uint16
        |        |     |     +--ro hold-time?            uint16
        |        |     |     +--ro keepalive-interval?   uint16
        |        |     +--rw transport
        |        |     |  +--rw config
        |        |     |  |  +--rw local-address?   union
        |        |     |  +--ro state
        |        |     |     +--ro local-address?   union
        |        |     +--rw graceful-restart
        |        |     |  +--rw config
        |        |     |  |  +--rw enabled?   boolean
        |        |     |  +--ro state
        |        |     |     +--ro enabled?   boolean
        |        |     +--rw ebgp-multihop
        |        |     |  +--rw config
        |        |     |  |  +--rw enabled?        boolean
        |        |     |  |  +--rw multihop-ttl?   uint8
        |        |     |  +--ro state
        |        |     |     +--ro enabled?        boolean
        |        |     |     +--ro multihop-ttl?   uint8
        |        |     +--rw afi-safis
        |        |     |  +--rw afi-safi* [afi-safi-name]
        |        |     |     +--rw afi-safi-name    -> ../config/afi-safi-name
        |        |     |     +--rw config
        |        |     |     |  +--rw afi-safi-name?                                          identityref
        |        |     |     |  +--rw oc-network-instance-ext:soft-reconfiguration-inbound?   boolean
        |        |     |     +--ro state
        |        |     |     |  +--ro afi-safi-name?                                          identityref
        |        |     |     |  +--ro oc-network-instance-ext:soft-reconfiguration-inbound?   boolean
        |        |     |     +--rw add-paths
        |        |     |     |  +--rw config
        |        |     |     |  |  +--rw send?   boolean
        |        |     |     |  +--ro state
        |        |     |     |     +--ro send?   boolean
        |        |     |     +--rw apply-policy
        |        |     |        +--rw config
        |        |     |        |  +--rw import-policy*   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        |        |     |        +--ro state
        |        |     |           +--ro import-policy*   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
        |        |     +--rw enable-bfd
        |        |        +--rw config
        |        |        |  +--rw enabled?                       boolean
        |        |        |  +--rw desired-minimum-tx-interval?   uint32
        |        |        |  +--rw required-minimum-receive?      uint32
        |        |        |  +--rw detection-multiplier?          uint8
        |        |        +--ro state
        |        |           +--ro enabled?                       boolean
        |        |           +--ro desired-minimum-tx-interval?   uint32
        |        |           +--ro required-minimum-receive?      uint32
        |        |           +--ro detection-multiplier?          uint8
  ```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| BGP                      | Border Gateway Protocol   |
| VRF                      | Virtual Routing and Forwarding   |
| AFI                      | Address Family Identifier   |
| SAFI                     | Subsequent Address Family Identifier   |
| BFD                      | Bidirectional Forwarding Detection   |
| AS                       | Autonomous System   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig network-instance YANG models.
2. Support network instance configuration including default VRF and named VRFs.
3. Support BGP protocol configuration within network instances:
   - BGP global configuration (AS number, router-id, graceful restart, timers)
   - BGP neighbor configuration (address, peer-as, timers, AFI-SAFIs, BFD)
   - BGP peer-group configuration (timers, transport, graceful-restart, ebgp-multihop, AFI-SAFIs, BFD)
   - AFI-SAFI configuration with multi-path settings
   - Dynamic neighbor prefixes
4. Support route aggregation (local-aggregates) configuration.
5. Support table connections for route redistribution between protocols.
6. Support routing tables configuration per address family.
7. Provide Get, Patch, and Delete operations via REST and gNMI.

### 1.1.2 Configuration and Management Requirements
The network instance configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.

### 1.1.3 Scalability Requirements
The maximum number of network instances depends on the platform capabilities and available resources.

## 1.2 Design Overview
### 1.2.1 Basic Approach
This feature provides support for OpenConfig based YANG models using transformer based implementation. SONiC FRR CLIs can be configured using unified mode via frrcfgd and frrcfgd reads the SONiC DBs and configures FRR CLIs using vtysh.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get and set based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
The following SONiC CONFIG DB schema definitions are used:
- BGP_GLOBALS
- BGP_GLOBALS_AF
- BGP_GLOBALS_AF_NETWORK
- BGP_GLOBALS_AF_AGGREGATE_ADDR
- BGP_NEIGHBOR
- BGP_NEIGHBOR_AF
- BGP_PEER_GROUP
- BGP_PEER_GROUP_AF

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
The OpenConfig network-instance YANG model is supported with extensions for SONiC-specific capabilities. Key models include:
- openconfig-network-instance.yang
- openconfig-network-instance-ext.yang (Openconfig extensions)
- openconfig-bgp.yang
- openconfig-bgp-types.yang
- openconfig-local-routing.yang

### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at all container and leaf levels.

Sample GET output for network instance with BGP configuration:
```json
{
  "openconfig-network-instance:network-instance": [
    {
      "name": "default",
      "config": {
        "name": "default",
        "type": "DEFAULT_INSTANCE"
      },
      "state": {
        "name": "default",
        "type": "DEFAULT_INSTANCE"
      },
      "protocols": {
        "protocol": [
          {
            "identifier": "BGP",
            "name": "bgp",
            "config": {
              "identifier": "BGP",
              "name": "bgp"
            },
            "bgp": {
              "global": {
                "config": {
                  "as": 65100,
                  "router-id": "10.10.10.1"
                },
                "state": {
                  "as": 65100,
                  "router-id": "10.10.10.1"
                }
              }
            }
          }
        ]
      }
    }
  ]
}
```

#### 3.3.2.2 SET
Supported at all container and leaf levels.

Sample PATCH for BGP global AS number:
```bash
curl -X PATCH -k "https://<device-ip>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/global/config/as" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:as": 65100}'
```

Sample PATCH for BGP neighbor:
```bash
curl -X PATCH -k "https://<device-ip>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/neighbors/neighbor=10.0.0.1" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:neighbor": [
      {
        "neighbor-address": "10.0.0.1",
        "config": {
          "neighbor-address": "10.0.0.1",
          "peer-as": 65200,
          "description": "BGP Neighbor"
        }
      }
    ]
  }'
```

#### 3.3.2.3 DELETE
Supported at all container and leaf levels.

Sample DELETE for BGP neighbor:
```bash
curl -X DELETE -k "https://<device-ip>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/neighbors/neighbor=10.0.0.1"
```

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
Supported

Sample gNMI GET request:
```bash
gnmi_get -xpath "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/config"
```

#### 3.3.3.2 SET
Supported

Sample gNMI SET request:
```bash
gnmi_set -update "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/config:@bgp_global.json"
```

#### 3.3.3.3 DELETE
Supported

Sample gNMI DELETE request:
```bash
gnmi_set -delete "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=10.0.0.1]"
```

# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and SONiC YANG:

## Network Instance Mapping
|   OpenConfig YANG                    |    SONiC YANG/DB Table        |
|--------------------------------------|-------------------------------|
|   network-instance/name              |      VRF/vrf_name             |
|   network-instance/type              |      VRF/type                 |

## BGP Global Mapping
|   OpenConfig YANG                    |    SONiC DB Table             |
|--------------------------------------|-------------------------------|
|   bgp/global/config/as               |      BGP_GLOBALS/local_asn    |
|   bgp/global/config/router-id        |      BGP_GLOBALS/router_id    |
|   bgp/global/graceful-restart/config/enabled        |      BGP_GLOBALS/graceful_restart/enabled    |
|   bgp/global/graceful-restart/config/restart-time   |      BGP_GLOBALS/graceful_restart/restart_time    |
|   bgp/global/timers/config/hold-time                |      BGP_GLOBALS/hold_time    |
|   bgp/global/timers/config/keepalive-interval       |      BGP_GLOBALS/keepalive_interval    |

## BGP Neighbor Mapping
|   OpenConfig YANG                              |    SONiC DB Table                    |
|------------------------------------------------|--------------------------------------|
|   bgp/neighbors/neighbor/config/neighbor-address    |      BGP_NEIGHBOR/neighbor_address    |
|   bgp/neighbors/neighbor/config/peer-as             |      BGP_NEIGHBOR/peer_asn            |
|   bgp/neighbors/neighbor/config/description         |      BGP_NEIGHBOR/description         |
|   bgp/neighbors/neighbor/timers/config/hold-time    |      BGP_NEIGHBOR/hold_time           |
|   bgp/neighbors/neighbor/enable-bfd/config/enabled  |      BGP_NEIGHBOR/bfd_enabled         |

## BGP Peer Group Mapping
|   OpenConfig YANG                                   |    SONiC DB Table                     |
|-----------------------------------------------------|---------------------------------------|
|   bgp/peer-groups/peer-group/config/peer-group-name |      BGP_PEER_GROUP/peer_group_name   |
|   bgp/peer-groups/peer-group/config/peer-type       |      BGP_PEER_GROUP/peer_type         |
|   bgp/peer-groups/peer-group/transport/config/local-address    |      BGP_PEER_GROUP/local_address     |
|   bgp/peer-groups/peer-group/ebgp-multihop/config/enabled      |      BGP_PEER_GROUP/ebgp_multihop_enabled    |
|   bgp/peer-groups/peer-group/ebgp-multihop/config/multihop-ttl |      BGP_PEER_GROUP/ebgp_multihop_ttl        |

## Local Aggregates Mapping
|   OpenConfig YANG                                   |    SONiC DB Table                            |
|-----------------------------------------------------|----------------------------------------------|
|   local-aggregates/aggregate/config/prefix          |      BGP_GLOBALS_AF_AGGREGATE_ADDR/ip_prefix |
|   local-aggregates/aggregate/config/summary-only    |      BGP_GLOBALS_AF_AGGREGATE_ADDR/summary_only |

# 5 Error Handling
Invalid configurations will report an error. Examples include:
- Invalid AS numbers
- Invalid IP addresses or prefixes
- Missing required fields
- Conflicting configurations

# 6 Unit Test Cases
## 6.1 Functional Test Cases
1. Verify GET, PATCH, and DELETE for network-instance name and type works via REST and gNMI.
2. Verify GET, PATCH, and DELETE for BGP global AS number works via REST and gNMI.
3. Verify GET, PATCH, and DELETE for BGP global router-id works via REST and gNMI.
4. Verify GET, PATCH, and DELETE for BGP graceful restart configuration works via REST and gNMI.
5. Verify GET, PATCH, and DELETE for BGP global timers works via REST and gNMI.
6. Verify GET, PATCH, and DELETE for BGP AFI-SAFI configuration works via REST and gNMI.
7. Verify GET, PATCH, and DELETE for BGP neighbor configuration works via REST and gNMI.
8. Verify GET, PATCH, and DELETE for BGP neighbor timers works via REST and gNMI.
9. Verify GET, PATCH, and DELETE for BGP neighbor AFI-SAFIs works via REST and gNMI.
10. Verify GET, PATCH, and DELETE for BGP neighbor BFD configuration works via REST and gNMI.
11. Verify GET, PATCH, and DELETE for BGP peer-group configuration works via REST and gNMI.
12. Verify GET, PATCH, and DELETE for BGP peer-group timers works via REST and gNMI.
13. Verify GET, PATCH, and DELETE for BGP peer-group transport configuration works via REST and gNMI.
14. Verify GET, PATCH, and DELETE for BGP peer-group graceful-restart works via REST and gNMI.
15. Verify GET, PATCH, and DELETE for BGP peer-group ebgp-multihop works via REST and gNMI.
16. Verify GET, PATCH, and DELETE for BGP peer-group AFI-SAFIs works via REST and gNMI.
17. Verify GET, PATCH, and DELETE for BGP peer-group BFD configuration works via REST and gNMI.
18. Verify GET, PATCH, and DELETE for local-aggregates configuration works via REST and gNMI.
19. Verify GET, PATCH, and DELETE for dynamic neighbor prefixes works via REST and gNMI.
20. Verify GET, PATCH, and DELETE for BGP multi-path configuration works via REST and gNMI.
21. Verify GET, PATCH, and DELETE for table connections works via REST and gNMI.
22. Verify multiple AFI-SAFI configurations can coexist.
23. Verify BGP neighbor can inherit configuration from peer-group.

## 6.2 Negative Test Cases
1. Verify that DELETE at network-instances container is not allowed.
2. Verify that invalid AS number configuration returns appropriate error.
3. Verify that invalid router-id configuration returns appropriate error.
4. Verify that invalid neighbor address returns appropriate error.
5. Verify that BGP configuration without AS number returns appropriate error.
6. Verify that duplicate neighbor addresses are rejected.
7. Verify that invalid AFI-SAFI name returns appropriate error.
8. Verify that invalid peer-group reference in neighbor returns appropriate error.
9. Verify that invalid BFD parameter values return appropriate errors.
10. Verify that conflicting timer values return appropriate errors.
11. Verify that invalid prefix format in local-aggregates returns error.
12. Verify that operations on non-existent network instance return appropriate error.
