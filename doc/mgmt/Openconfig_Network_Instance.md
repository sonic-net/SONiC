# OpenConfig Model Support for SONiC Network Instance Feature

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Related Documents](#related-documents)
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
      * [3.1.1 SONiC Feature YANG and CONFIG_DB](#311-sonic-feature-yang-and-config_db)
      * [3.1.2 OpenConfig Modules](#312-openconfig-modules)
      * [3.1.3 UMF Translation (REST/gNMI to CONFIG_DB)](#313-umf-translation-restgnmi-to-config_db)
      * [3.1.4 FRR Programming](#314-frr-programming)
      * [3.1.5 OpenConfig Extensions](#315-openconfig-extensions)
      * [3.1.6 Mapping Table and Unit Tests](#316-mapping-table-and-unit-tests)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
  * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
    * [4.1 Network Instance](#41-network-instance)
    * [4.2 Interfaces](#42-interfaces)
    * [4.3 VLANs](#43-vlans)
    * [4.4 FDB](#44-fdb)
    * [4.5 Protocol](#45-protocol)
      * [4.5.1 Protocols Supported (Current Implementation)](#451-protocols-supported-current-implementation)
      * [4.5.2 Protocol Container Mapping](#452-protocol-container-mapping)
      * [4.5.3 Unsupported Protocol Identifiers](#453-unsupported-protocol-identifiers)
  * [5 User Interface](#5-user-interface)
    * [5.1 Data Models](#51-data-models)
    * [5.2 REST API Support](#52-rest-api-support)
      * [5.2.1 GET](#521-get)
      * [5.2.2 PUT](#522-put)
      * [5.2.3 POST](#523-post)
      * [5.2.4 PATCH](#524-patch)
      * [5.2.5 DELETE](#525-delete)
    * [5.3 gNMI Support](#53-gnmi-support)
      * [5.3.1 GET](#531-get)
      * [5.3.2 SET](#532-set)
      * [5.3.3 DELETE](#533-delete)
      * [5.3.4 SUBSCRIBE](#534-subscribe)
  * [6 Error Handling](#6-error-handling)
  * [7 Unit Test Cases](#7-unit-test-cases)
    * [7.1 Functional Test Cases](#71-functional-test-cases)
    * [7.2 Negative Test Cases](#72-negative-test-cases)


# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

[Table 2: Translation Flow Layers](#table-2-translation-flow-layers)

OpenConfig to SONiC mapping tables: [Section 4](#4-openconfig-to-sonic-mapping-table)


# Revision
| Rev | Date | Author | Change Description |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 12/02/2025 | Venkata Krishna Rao G, Anukul Verma | Initial version |

# About this Manual
This document provides general information about the OpenConfig configuration and management of network instances (VRFs) in SONiC corresponding to the openconfig-network-instance.yang module. It describes how OpenConfig models are translated to SONiC CONFIG_DB entries and operational state, and how configuration and state are returned over REST and gNMI.

Network instances are configured under:
/network-instances/network-instance

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture (REST, gNMI, translib, transformers) |
| Openconfig_BGP.md | BGP, local aggregates, and table connections (route redistribution) |
| OpenConfig_StaticRoute.md | Static routes under `protocol[identifier=STATIC][name=DEFAULT]/static-routes` |

# Scope
- This document describes the high level design of OpenConfig **Network Instance** configuration and operational retrieval in SONiC.
- **In scope:** REST and gNMI — Get, Set (POST/PUT/PATCH), Delete, and Subscribe on supported network-instance YANG paths.
- **Out of scope:** SONiC KLISH CLI; `/network-instances/network-instance/evpn/`; `/network-instances/network-instance/connection-points/`; nexthop-tracking; FIB install policy; protocol leaf-level configuration (see OpenConfig_StaticRoute.md and Openconfig_BGP.md).
- OpenConfig xpath root:
  `/network-instances/network-instance`
- Supported attributes in OpenConfig YANG tree (reflecting current UMF implementation):

```
module: openconfig-network-instance (+ openconfig-network-instance-ext)
+--rw network-instances
   +--rw network-instance* [name]
      +--rw name                                        -> ../config/name
      +--rw config
      |  +--rw name?   string
      |  +--rw type    identityref
      +--ro state
      |  +--ro name?   string
      |  +--ro type    identityref
      +--rw fdb
      |  +--rw config
      |  |  +--rw anycast-gateway-mac?   oc-yang:mac-address
      |  +--ro state
      |  |  +--ro anycast-gateway-mac?   oc-yang:mac-address
      |  +--rw mac-table
      |     +--rw entries
      |        +--rw entry* [mac-address vlan]
      |           +--rw mac-address    -> ../config/mac-address
      |           +--rw vlan           -> ../config/vlan
      |           +--rw config
      |           |  +--rw mac-address?   oc-yang:mac-address
      |           |  +--rw vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
      |           +--ro state
      |           |  +--ro mac-address?   oc-yang:mac-address
      |           |  +--ro vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
      |           |  +--ro entry-type?    enumeration
      |           +--rw interface
      |              +--rw interface-ref
      |                 +--rw config
      |                 |  +--rw interface?      -> /oc-if:interfaces/interface/name
      |                 |  +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
      |                 +--ro state
      |                    +--ro interface?      -> /oc-if:interfaces/interface/name
      |                    +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
      +--rw interfaces
      |  +--rw interface* [id]
      |     +--rw id        -> ../config/id
      |     +--rw config
      |     |  +--rw id?             oc-if:interface-id
      |     |  +--rw interface?      -> /oc-if:interfaces/interface/name
      |     |  +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
      |     +--ro state
      |        +--ro id?             oc-if:interface-id
      |        +--ro interface?      -> /oc-if:interfaces/interface/name
      |        +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
      +--rw vlans
      |  +--rw vlan* [vlan-id]
      |     +--rw vlan-id    -> ../config/vlan-id
      |     +--rw config
      |     |  +--rw vlan-id?                    oc-vlan-types:vlan-id
      |     |  +--rw name?                       string
      |     |  +--rw oc-network-instance-ext:static-anycast-gateway?     boolean
      |     +--ro state
      |     |  +--ro vlan-id?                    oc-vlan-types:vlan-id
      |     |  +--ro name?                       string
      |     |  +--ro oc-network-instance-ext:static-anycast-gateway?     boolean
      +--rw protocols
         +--rw protocol* [identifier name]
            +--rw identifier          -> ../config/identifier
            +--rw name                -> ../config/name
            +--rw config
            |  +--rw identifier?   identityref
            |  +--rw name?         string
            |  +--rw enabled?      boolean
            +--ro state
               +--ro identifier?   identityref
               +--ro name?         string
               +--ro enabled?      boolean
```

Extension leaves are documented in [Section 3.1.5 OpenConfig Extensions](#315-openconfig-extensions).

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term** | **Definition** |
|--------------------------|-------------------------------------|
| YANG | Yet Another Next Generation: modular language representing data structures in an XML tree format |
| gNMI | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data |
| VRF | Virtual Routing and Forwarding |
| FDB | Forwarding Database (MAC table) |
| BFD | Bidirectional Forwarding Detection |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig network-instance YANG models for core VRF configuration.
2. Support network instance configuration including default VRF and named VRFs (name, type).
3. Support network-instance interface bindings (physical, port-channel, VLAN, loopback, subinterface).
4. Support VLAN configuration within network instances (vlan-id, name, static-anycast-gateway).
5. Support FDB configuration and operational state (anycast-gateway-mac, MAC table entries).
6. Support the `protocols/protocol` container with exactly three protocol identifiers as of this release (see [Section 4.5.1](#451-protocols-supported-current-implementation)):
   - **STATIC** (`identifier=STATIC`, `name=DEFAULT`) — static routes under `static-routes`; full mapping in OpenConfig_StaticRoute.md
   - **BGP** (`identifier=BGP`, `name=bgp`) — BGP under `bgp`; full mapping in Openconfig_BGP.md
   - **LOCAL_AGGREGATE** (`identifier=LOCAL_AGGREGATE`, `name=bgp`) — BGP aggregate routes under `local-aggregates` as a **separate** protocol list entry; full mapping in Openconfig_BGP.md §4.6
7. Reject any other OpenConfig protocol identifier (for example OSPF, ISIS, PIM) with a validation error.
8. Provide Get, Patch, Put, Post, and Delete operations via REST and gNMI for in-scope nodes (see [Section 5](#5-rest-and-gnmi-examples)).

### 1.1.2 Configuration and Management Requirements
The network instance configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.

### 1.1.3 Scalability Requirements
The maximum number of network instances depends on the platform capabilities and available resources.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC exposes core network-instance configuration (VRF, interface bindings, VLANs, FDB) through OpenConfig YANG. UMF transformers translate REST/gNMI requests into existing CONFIG_DB entries. Protocol subtrees delegate to separate feature HLDs.

### 1.2.2 Container
Implementation changes are in **sonic-mgmt-common** (REST server in the Management Framework container and gNMI server in the gnmi container: annotations, transformers).

# 2 Functionality
## 2.1 Target Deployment Use Cases
All northbound clients configure and query network instances using OpenConfig YANG over REST or gNMI.

1. **REST clients** — GET, POST, PUT, PATCH, and DELETE on network-instance RESTCONF paths.
2. **gNMI clients** — Capabilities, Get, Set (update/delete), and Subscribe on network-instance gNMI paths.

# 3 Design
## 3.1 Overview
This HLD follows [Management Framework.md](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md). The design covers: SONiC feature YANG, OpenConfig modules, UMF translation, CONFIG_DB, mapping tables (Section 4), and unit tests (Section 7).

### 3.1.1 SONiC Feature YANG and CONFIG_DB
SONiC defines the southbound schema across multiple feature YANG modules:

| Item | Detail |
|------|--------|
| CONFIG_DB tables | `VRF`, `INTERFACE`, `LOOPBACK_INTERFACE`, `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE`, `VLAN_SUB_INTERFACE`, `VLAN`, `SAG` |
| Protocol tables | `STATIC_ROUTE`, `BGP_*`, `BGP_GLOBALS_AF_AGGREGATE_ADDR` — documented in OpenConfig_StaticRoute.md and Openconfig_BGP.md |

OpenConfig clients never write CONFIG_DB directly; UMF transformers populate these tables from OpenConfig payloads. A CONFIG_DB example is in [§3.2.1](#321-config-db).

### 3.1.2 OpenConfig Modules
| Module | Source | Role for network instance |
|--------|--------|---------------------------|
| [openconfig-network-instance.yang](https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance.yang) | openconfig/public | Base VRF, interfaces, VLANs, FDB, protocols container |
| [openconfig-vlan.yang](https://github.com/openconfig/public/blob/master/release/models/vlan/openconfig-vlan.yang) | openconfig/public | VLAN types and members |
| openconfig-network-instance-ext.yang | sonic-mgmt-common | `static-anycast-gateway` on VLAN config/state |
| openconfig-network-instance-annot.yang | sonic-mgmt-common | XPath to CONFIG_DB and operational state bindings |
| openconfig-network-instance-deviation.yang | sonic-mgmt-common | `not-supported` deviations for unsupported base OC leaves |

### 3.1.3 UMF Translation (REST/gNMI to CONFIG_DB)
OpenConfig SET/GET/SUBSCRIBE requests are handled by translib and the **transformer** common app. Annotation YANG defines xpath-to-DB bindings; network-instance transformers perform VRF validation, interface binding, VLAN, and FDB mapping.

![Management Framework Architecture diagram](images/Mgmt_Frmk_Arch.jpg)

*Figure: Management Framework architecture ([Management Framework.md](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)).*

#### Table 2: Translation Flow Layers

| Layer | Artifact | Role |
|-------|----------|------|
| **1. SONiC feature YANG** | `sonic-vrf.yang`, `sonic-vlan.yang`, interface YANG modules | CONFIG_DB schema for VRF, VLAN, interfaces |
| **2. OpenConfig modules** | `openconfig-network-instance.yang`, `openconfig-vlan.yang`, `openconfig-network-instance-ext.yang` | Northbound client model |
| **3. UMF annotations** | `openconfig-network-instance-annot.yang` | XPath → table/field/transformer binding |
| **4. UMF transformers** | Network-instance transformer | YangToDb / DbToYang / Subscribe for VRF, VLAN, FDB |
| **5. CONFIG_DB / STATE_DB / ASIC_DB** | `VRF`, `VLAN`, `INTERFACE`, FDB via ASIC_STATE | Runtime configuration and operational state |

Network-instance core configuration (VRF, interface bindings, VLANs) does not program FRR. Protocol subtrees delegate to separate transformers documented in OpenConfig_StaticRoute.md and Openconfig_BGP.md.

### 3.1.4 FRR Programming
Core network-instance configuration (VRF definition, interface bindings, VLANs, FDB) is **not** programmed to FRR by frrcfgd. BGP and static-route FRR programming are documented in Openconfig_BGP.md and OpenConfig_StaticRoute.md respectively.

### 3.1.5 OpenConfig Extensions
SONiC augments base OpenConfig VLAN `config`/`state` using `openconfig-network-instance-ext.yang`. Base OpenConfig FDB leaf `anycast-gateway-mac` (under `fdb/config` and `fdb/state`) is in scope but is **not** an extension leaf — it is defined in the base `openconfig-network-instance` model and documented in [§4.4](#44-fdb).

| Property | Value |
|----------|-------|
| Module | `openconfig-network-instance-ext.yang` |
| Prefix | `oc-network-instance-ext` |
| Namespace | `http://openconfig.net/yang/network-instance/sonic/extension` |

Extension leaf DB mappings are documented in [Section 4](#4-openconfig-to-sonic-mapping-table) only.

| OpenConfig YANG Node | Data type | Notes |
|----------------------|-----------|-------|
| **fdb/config** (base OpenConfig — not an extension) | | |
| anycast-gateway-mac | oc-yang:mac-address | Default network instance only; see [§4.4](#44-fdb) |
| **fdb/state** (base OpenConfig — not an extension) | | |
| anycast-gateway-mac | oc-yang:mac-address | GET symmetry with config |
| **vlans/vlan/config** | | |
| static-anycast-gateway | boolean | Default network instance only |
| **vlans/vlan/state** | | |
| static-anycast-gateway | boolean | GET symmetry with config |

BGP and other protocol extensions are documented in Openconfig_BGP.md §3.1.5.

### 3.1.6 Mapping Table and Unit Tests
- **OpenConfig → SONiC mapping:** [Section 4](#4-openconfig-to-sonic-mapping-table).
- **REST/gNMI examples:** [Section 5](#5-user-interface).
- **Unit tests:** [Section 7](#7-unit-test-cases).

## 3.2 DB Changes
OpenConfig network-instance core configuration uses existing CONFIG_DB, STATE_DB, APPL_DB, ASIC_DB, and COUNTERS_DB tables. No new tables are added.

### 3.2.1 CONFIG DB
The following SONiC CONFIG DB schema definitions are used by this document:
- VRF
- INTERFACE
- LOOPBACK_INTERFACE
- PORTCHANNEL_INTERFACE
- VLAN_INTERFACE
- VLAN_SUB_INTERFACE
- VLAN
- SAG

Protocol-specific tables (`STATIC_ROUTE`, `BGP_*`, `BGP_GLOBALS_AF_AGGREGATE_ADDR`) are documented in the respective protocol HLDs.

### 3.2.2 APP DB
- VRF (network instance operational state)

### 3.2.3 STATE DB
There are no STATE DB tables used for core network-instance configuration in this document.

### 3.2.4 ASIC DB
The following ASIC DB tables are read for FDB MAC table operational data:
- ASIC_STATE (SAI_OBJECT_TYPE_FDB_ENTRY and related bridge/port objects)

### 3.2.5 COUNTER DB
FDB MAC table GET resolves bridge port to interface name via `COUNTERS_PORT_NAME_MAP` and `COUNTERS_LAG_NAME_MAP` (read-only; no schema changes).


# 4 OpenConfig to SONiC Mapping Table

This section maps each leaf in the supported OpenConfig YANG tree (see [Scope](#scope)) to the corresponding SONiC CONFIG DB, STATE DB, APPL DB, ASIC DB, or COUNTERS DB table and field. **Key notation:**
- **OpenConfig YANG Node** — Parent container or list paths appear in **bold** on their own row; child leaves below use the leaf name only (relative to the parent path above). Extension augments omit the `oc-network-instance-ext:` prefix in paths and leaf names.
- **Extension** — `Yes` on extension leaves; blank on base OpenConfig leaves. Extension definitions are in [§3.1.5](#315-openconfig-extensions).
- **DB Name** — Redis database (`CONFIG_DB`, `STATE_DB`, `APPL_DB`, `ASIC_DB`, `COUNTERS_DB`, or `—` for derived values).
- **Table:Field** — SONiC table and field in `TABLE:field` form; table-only or `Derived` when the value is computed or encoded in the Redis key.
- `Derived` — value computed by a transformer or encoded in the Redis key; not stored as a dedicated DB field.
- **Parent containers** with `Derived` and no leaf mapping (for example `fdb/mac-table/entries`) are omitted except where noted; only **bold** parent path headers and mapped list entries or leaves are listed.
- Operational state leaves use `STATE_DB`, `APPL_DB`, `ASIC_DB`, or `COUNTERS_DB` (FDB interface resolution reads `COUNTERS_PORT_NAME_MAP` / `COUNTERS_LAG_NAME_MAP`).
- GET-only / subscribe-only subtrees (FDB MAC entries, interface `state`) are noted in the Notes column.
- Redis key formats are noted in the Notes column where the transformer defines a composite key.

## 4.1 Network Instance

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| **network-instance** | | CONFIG_DB | VRF | table `nwinst_tbl_xfmr`; key `nwinst_tbl_key_xfmr`; Redis key = network-instance name; top-level DELETE blocked; `default` DELETE blocked |
| **network-instance/config** | | | | |
| name | | CONFIG_DB | VRF:NULL | Via transformer; SET writes placeholder `NULL:NULL`; Redis key is list `name`; `config/name` must match list key `name` |
| type | | — | Derived | Via transformer; **not persisted on SET** (validation only); only `L3VRF` and `DEFAULT_INSTANCE` supported; `DEFAULT_INSTANCE` only when `name=default`; named VRFs require `name` prefix `Vrf` and `type=L3VRF` |
| **network-instance/state** | | APPL_DB | VRF | Operational state container |
| name | | APPL_DB | VRF | Via transformer |
| type | | APPL_DB | VRF | Via transformer; `default` → `DEFAULT_INSTANCE`; names prefixed with `Vrf` → `L3VRF` on GET |

## 4.2 Interfaces

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| **interfaces** | | | | |
| interface | | Derived | key component | table `nwinst_intf_table_xfmr`; key `nwinst_intf_key_xfmr`; path `DbToYangPath_nwinst_intf_path_xfmr`; tables: INTERFACE, LOOPBACK_INTERFACE, PORTCHANNEL_INTERFACE, VLAN_INTERFACE, VLAN_SUB_INTERFACE |
| **interfaces/interface/config** | | | | |
| interface | | CONFIG_DB | Derived:vrf_name | Via transformer; table resolved by interface type (`getIntfTableName`); underlying interface must exist; dotted `interface` value rejected |
| subinterface | | CONFIG_DB | VLAN_SUB_INTERFACE:vrf_name | Via transformer; subinterface index `0` not supported; when `subinterface` is set, `interface` field is mandatory |
| **interfaces/interface/state** | | | | |
| id | | Derived | — | GET/subscribe-only via `DbToYang_nwinst_intf_state_xfmr`; from list key |
| interface | | Derived | — | Via transformer; base name from id (strips `.index`) |
| subinterface | | Derived | — | Via transformer; parsed from id when dotted; subscribe via `Subscribe_nwinst_intf_state_xfmr` |


## 4.3 VLANs

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| **vlans** | | | | |
| vlan | | CONFIG_DB | VLAN | key `network_instance_vlan_key_xfmr`; Redis key: `Vlan{vlan-id}` |
| **vlans/vlan/config** | | | | |
| name | | — | Derived | Via transformer; validates `name == "Vlan"+vlan-id` on SET; not written to DB; GET derives from Redis key |
| static-anycast-gateway | | CONFIG_DB | VLAN_INTERFACE:static_anycast_gateway | Extension leaf; via `vlan_static_anycast_gateway_xfmr`; **default network instance only**; Redis key: `Vlan{vlan-id}` |
| vlan-id | | CONFIG_DB | VLAN:vlanid | Via transformer |
| **vlans/vlan/state** | | | | |
| name | | — | Derived | Via transformer |
| static-anycast-gateway | | CONFIG_DB | VLAN_INTERFACE:static_anycast_gateway | Extension leaf; via `DbToYang_vlan_static_anycast_gateway_xfmr`; GET symmetry with config |
| vlan-id | | CONFIG_DB | VLAN:vlanid | Via transformer |


## 4.4 FDB

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| **fdb/config** | | | | |
| anycast-gateway-mac | | CONFIG_DB | SAG:gateway_mac | Via transformer; key `anycast_gateway_mac_key_xfmr`; Redis key: `GLOBAL`; **only supported when `network-instance/name=default`** |
| **fdb/state** | | | | |
| anycast-gateway-mac | | CONFIG_DB | SAG:gateway_mac | Via transformer; GET symmetry with config |
| **fdb/mac-table/entries** | | | | |
| entry | | ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_FDB_ENTRY | Subtree `DbToYang_mac_table_entry_xfmr`; GET/subscribe-only; also reads COUNTERS_DB for interface resolution |
| **fdb/mac-table/entries/entry/state** | | | | |
| mac-address | | ASIC_DB | ASIC_STATE:Derived | Via transformer |
| vlan | | ASIC_DB | ASIC_STATE:Derived | Via transformer |
| entry-type | | ASIC_DB | ASIC_STATE:Derived | Via transformer |
| **fdb/mac-table/entries/entry/interface/interface-ref/state** | | | | |
| interface | | ASIC_DB | ASIC_STATE:Derived | Via transformer; port resolved via COUNTERS_DB name maps |


## 4.5 Protocol

The `protocols/protocol` list identifies a routing protocol instance within a network instance. Each entry is keyed by `(identifier, name)`. SONiC validates the identifier/name pair in `network_instance_protocol_key_xfmr`.

**As of the current implementation, only three protocol identifiers are supported.** Each maps to a distinct OpenConfig subtree and CONFIG_DB backing store. BGP configuration and local-aggregate configuration are **separate protocol list entries** — local aggregates are **not** configured under `protocol[identifier=BGP][name=bgp]/bgp`.

### 4.5.1 Protocols Supported (Current Implementation)

| # | Protocol identifier | Required `name` | OpenConfig subtree | Primary CONFIG_DB table(s) | Detailed HLD |
|---|---------------------|-----------------|--------------------|----------------------------|--------------|
| 1 | `STATIC` (or `openconfig-policy-types:STATIC`) | `DEFAULT` | `static-routes` | `STATIC_ROUTE` (virtual protocol table: `STATIC_PROTOCOL_TBL`) | OpenConfig_StaticRoute.md |
| 2 | `BGP` (or `openconfig-policy-types:BGP`) | `bgp` | `bgp` | `BGP_GLOBALS`, `BGP_NEIGHBOR`, `BGP_PEER_GROUP`, and related BGP tables | Openconfig_BGP.md |
| 3 | `LOCAL_AGGREGATE` (or `openconfig-policy-types:LOCAL_AGGREGATE`) | `bgp` | `local-aggregates` | `BGP_GLOBALS_AF_AGGREGATE_ADDR` (virtual protocol table: `LOCAL_AGGREGATE_TBL`) | Openconfig_BGP.md §4.6 |

#### 1. STATIC — static routes

- **OpenConfig path:** `/network-instances/network-instance[name=<vrf>]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/...`
- **CONFIG_DB:** `STATIC_ROUTE` (virtual protocol table: `STATIC_PROTOCOL_TBL`)
- **Leaf-level mapping:** OpenConfig_StaticRoute.md

#### 2. BGP — Border Gateway Protocol

- **OpenConfig path:** `/network-instances/network-instance[name=<vrf>]/protocols/protocol[identifier=BGP][name=bgp]/bgp/...`
- **CONFIG_DB:** `BGP_GLOBALS` and related BGP tables
- **Prerequisite:** Creating BGP configuration requires/resolves the `BGP_GLOBALS` row for the VRF.
- **Leaf-level mapping and FRR CLI:** Openconfig_BGP.md

#### 3. LOCAL_AGGREGATE — BGP aggregate routes

- **OpenConfig path:** `/network-instances/network-instance[name=<vrf>]/protocols/protocol[identifier=LOCAL_AGGREGATE][name=bgp]/local-aggregates/...`
- **Purpose:** Configure BGP aggregate (summary) routes for a VRF as a **separate** `protocols/protocol` entry (not nested under the BGP protocol container).
- **CONFIG_DB:** `BGP_GLOBALS_AF_AGGREGATE_ADDR`; Redis key format `vrf|afi_safi|ip_prefix`.
- **Prerequisite:** `BGP_GLOBALS` must exist for the VRF.
- **Leaf-level mapping and FRR CLI:** Openconfig_BGP.md §4.6.

#### Common protocol-level behavior

| Behavior | Detail |
|----------|--------|
| `protocols/protocol/config/enabled` | **Read-only** on SET/PATCH (`NotSupportedError`). On GET, always returned as `true` when the protocol instance is present (`DbToYang_nw_instance_protocol_enabled_xfmr`). Enable/disable is implied by presence of configuration in the backing CONFIG_DB table. |
| Identifier/name validation | Wrong `name` for a given `identifier` returns `InvalidArgsError` (for example `STATIC` with `name=bgp`, or `BGP` with `name=DEFAULT`). |
| gNMI subscribe reverse-mapping | `DbToYangPath_nw_instance_protocol_path_xfmr` maps `BGP_GLOBALS` → `(BGP, bgp)`, `STATIC_PROTOCOL_TBL` → `(STATIC, DEFAULT)`, `LOCAL_AGGREGATE_TBL` → `(LOCAL_AGGREGATE, bgp)`. |

### 4.5.2 Protocol Container Mapping

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| **protocols** | | | | |
| protocol | | — | Derived (key component) | table `network_instance_protocol_tbl_xfmr`; key `network_instance_protocol_key_xfmr`; path `DbToYangPath_nw_instance_protocol_path_xfmr` |
| **protocols/protocol/config** | | | | |
| identifier | | — | Derived | Key component; must be one of STATIC, BGP, LOCAL_AGGREGATE |
| name | | — | Derived | Key component; must match required name for the identifier (see §4.5.1) |
| enabled | | — | Derived | Via transformer; read-only on SET/PATCH (`NotSupportedError`); always `true` on GET when protocol instance exists |
| **protocols/protocol/state** | | | | |
| enabled | | — | Derived | Via transformer; always `true` on GET |
| **protocols/protocol** | | | | |
| static-routes | | CONFIG_DB | STATIC_ROUTE | Only valid when `identifier=STATIC`, `name=DEFAULT`; validate `validate_static_protocol` |
| bgp | | CONFIG_DB | BGP_GLOBALS | Only valid when `identifier=BGP`, `name=bgp`; validate `validate_bgp_protocol`; see Openconfig_BGP.md |
| local-aggregates | | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR | Only valid when `identifier=LOCAL_AGGREGATE`, `name=bgp`; validate `validate_local_aggregate_protocol`; see Openconfig_BGP.md §4.6 |


### 4.5.3 Unsupported Protocol Identifiers

OpenConfig defines additional protocol identifiers (for example `OSPF`, `ISIS`, `PIM`, `DIRECTLY_CONNECTED`, `LOCAL`). **None of these are supported** under `protocols/protocol` in the current SONiC implementation.

| Unsupported identifier | Result |
|------------------------|--------|
| Any identifier other than `STATIC`, `BGP`, or `LOCAL_AGGREGATE` | SET/PATCH/DELETE: `InvalidArgsError` from `network_instance_protocol_key_xfmr` or `network_instance_protocol_tbl_xfmr`. Both transformers implement `LOCAL_AGGREGATE` as well as BGP and STATIC; rejection messages still cite only BGP and STATIC (e.g. *"…only 'BGP' and 'STATIC' are supported"*). |
| `STATIC` with `name` ≠ `DEFAULT` | `InvalidArgsError` |
| `BGP` with `name` ≠ `bgp` | `InvalidArgsError` |
| `LOCAL_AGGREGATE` with `name` ≠ `bgp` | `InvalidArgsError` |
| `bgp` subtree under `identifier=STATIC` or `LOCAL_AGGREGATE` | Subtree validation skips or rejects (protocol-specific `validate_*_protocol` handlers) |
| `static-routes` under `identifier=BGP` or `LOCAL_AGGREGATE` | Same — cross-protocol subtree access is not allowed |

Route redistribution (`table-connections`) and operational `tables` are documented in Openconfig_BGP.md. The network-instance `evpn` container (`/network-instances/network-instance/evpn/`), `connection-points` container (`/network-instances/network-instance/connection-points/`), nexthop-tracking, and FIB install policy are **out of scope** for this HLD set.

# 5 User Interface

## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| sonic-vrf.yang | sonic-yang-models | VRF CONFIG_DB schema |
| sonic-vlan.yang | sonic-yang-models | VLAN CONFIG_DB schema |
| [openconfig-network-instance.yang](https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance.yang) | openconfig/public | Base network-instance container |
| [openconfig-vlan.yang](https://github.com/openconfig/public/blob/master/release/models/vlan/openconfig-vlan.yang) | openconfig/public | VLAN members and types |
| openconfig-network-instance-ext.yang | sonic-mgmt-common | `static-anycast-gateway` extension |

## 5.2 REST API Support

Examples below use paths validated by unit tests. RESTCONF URL encoding uses `=` separators; gNMI uses bracket notation (see §5.3).


#### Network Instance (VRF)

**GET** — single network instance

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf1" -H "accept: application/yang-data+json"
```

Sample GET output:
```json
{
  "openconfig-network-instance:network-instance": [
    {
      "name": "Vrf1",
      "config": {
        "name": "Vrf1",
        "type": "openconfig-network-instance-types:L3VRF"
      },
      "state": {
        "name": "Vrf1",
        "type": "openconfig-network-instance-types:L3VRF"
      }
    }
  ]
}
```

**GET** — all network instances

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances" -H "accept: application/yang-data+json"
```

**POST** — create named VRF

Sample POST request:
```
curl -X POST -k "https://<device>/restconf/data/openconfig-network-instance:network-instances" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:network-instance": [{
      "name": "Vrf1",
      "config": { "name": "Vrf1", "type": "L3VRF" }
    }]
  }'
```

**PUT** — create VRF at list entry

Sample PUT request:
```
curl -X PUT -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf3" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:network-instance": [{
      "name": "Vrf3",
      "config": { "name": "Vrf3", "type": "L3VRF" }
    }]
  }'
```

**PATCH** — update type (named VRF must stay L3VRF)

Sample PATCH request:
```
curl -X PATCH -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/config/type" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:type": "DEFAULT_INSTANCE"}'
```

**DELETE** — single VRF (not allowed for `default` or top-level container)

Sample DELETE request:
```
curl -X DELETE -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf1" -H "accept: */*"
```

#### Interface Bindings

**POST** — create VRF with subinterface binding

Sample POST request:
```
curl -X POST -k "https://<device>/restconf/data/openconfig-network-instance:network-instances" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:network-instance": [{
      "name": "Vrf4",
      "config": { "name": "Vrf4", "type": "L3VRF" },
      "interfaces": {
        "interface": [{
          "id": "Eth10.200",
          "config": { "id": "Eth10.200", "subinterface": 200, "interface": "Eth10" }
        }]
      }
    }]
  }'
```

**GET** — interface binding state

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf4/interfaces/interface=Eth10.200/state" -H "accept: application/yang-data+json"
```

Sample GET output:
```json
{
  "openconfig-network-instance:state": {
    "id": "Eth10.200",
    "subinterface": 200,
    "interface": "Eth10"
  }
}
```

**PATCH** — bind Ethernet port to VRF

Sample PATCH request:
```
curl -X PATCH -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=VrfTest1" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:network-instance": [{
      "name": "VrfTest1",
      "interfaces": {
        "interface": [{
          "id": "Ethernet20",
          "config": { "id": "Ethernet20", "interface": "Ethernet20" }
        }]
      }
    }]
  }'
```

**DELETE** — unbind interface from VRF

Sample DELETE request:
```
curl -X DELETE -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=VrfTest1/interfaces/interface=Ethernet20" -H "accept: */*"
```

#### VLANs

**POST** — create VLANs in network instance

Sample POST request:
```
curl -X POST -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/vlans" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:vlan": [{
      "vlan-id": 100,
      "config": { "vlan-id": 100, "name": "Vlan100" }
    }]
  }'
```

**GET** — single VLAN

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/vlans/vlan=100" -H "accept: application/yang-data+json"
```

Sample GET output:
```json
{
  "openconfig-network-instance:vlan": [{
    "vlan-id": 100,
    "config": { "vlan-id": 100, "name": "Vlan100" },
    "state": { "vlan-id": 100, "name": "Vlan100" }
  }]
}
```

**PUT** — create VLAN at list entry

Sample PUT request:
```
curl -X PUT -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/vlans/vlan=400" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:vlan": [{
      "vlan-id": 400,
      "config": { "vlan-id": 400, "name": "Vlan400" }
    }]
  }'
```

**DELETE** — single VLAN

Sample DELETE request:
```
curl -X DELETE -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/vlans/vlan=100" -H "accept: */*"
```

#### FDB (Anycast Gateway MAC)

**PUT** — configure anycast gateway MAC (default VRF only)

Sample PUT request:
```
curl -X PUT -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/fdb/config/anycast-gateway-mac" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:anycast-gateway-mac": "00:11:22:33:44:55"}'
```

**GET** — FDB container

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/fdb" -H "accept: application/yang-data+json"
```

Sample GET output:
```json
{
  "openconfig-network-instance:fdb": {
    "config": { "anycast-gateway-mac": "00:11:22:33:44:55" },
    "state": { "anycast-gateway-mac": "00:11:22:33:44:55" }
  }
}
```

**PATCH** — update anycast gateway MAC

Sample PATCH request:
```
curl -X PATCH -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/fdb/config" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:config": {"anycast-gateway-mac": "11:22:33:44:55:66"}}'
```

**DELETE** — anycast gateway MAC

Sample DELETE request:
```
curl -X DELETE -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/fdb/config/anycast-gateway-mac" -H "accept: */*"
```

## 5.3 gNMI Support

### 5.3.1 GET
```
gnmic -a <device>:<port> --insecure --target OC-YANG get \
  --path "/openconfig-network-instance:network-instances/network-instance[name=default]/config"
```

### 5.3.2 SET
```
gnmic -a <device>:<port> --insecure --target OC-YANG set \
  --update-path "/openconfig-network-instance:network-instances/network-instance[name=Vrf1]" \
  --update-value '{"openconfig-network-instance:network-instance":[{"name":"Vrf1","config":{"name":"Vrf1","type":"L3VRF"}}]}'
```

### 5.3.3 DELETE
```
gnmic -a <device>:<port> --insecure --target OC-YANG set \
  --delete "/openconfig-network-instance:network-instances/network-instance[name=Vrf1]"
```

### 5.3.4 SUBSCRIBE

Supported for subscribe-only operational subtrees in this document: `interfaces/interface/state` and `fdb/mac-table/entries`. Use `--target OC-YANG` (or `OC_YANG` per client convention). Wildcard keys (`*`) are supported where noted.

Sample subscription on FDB MAC table entries (SAMPLE stream; periodic telemetry path used by controller-agent `MacTable` dial-out):

```
gnmic -a <device>:<port> --insecure --target OC-YANG subscribe \
  --path "/openconfig-network-instance:network-instances/network-instance[name=default]/fdb/mac-table/entries" \
  --mode stream
```

Sample subscription on network-instance interface operational state (ON_CHANGE; VRF interface-binding updates):

```
gnmic -a <device>:<port> --insecure --target OC-YANG subscribe \
  --stream-mode on_change \
  --path "/openconfig-network-instance:network-instances/network-instance[name=default]/interfaces/interface[id=*]/state"
```

Sample ON_CHANGE notification (interface `state/id` after binding an interface to the VRF):

```
{
  "source": "<device>:<port>",
  "subscription-name": "default-<timestamp>",
  "timestamp": 1758089932057031339,
  "prefix": "openconfig-network-instance:network-instances/network-instance[name=default]/interfaces/interface[id=Ethernet0]/state",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "id",
      "values": {
        "id": "Ethernet0"
      }
    }
  ]
}
```

# 6 Error Handling
Invalid configurations will report an error. Examples include:

**Network instance (VRF):**
- DELETE top-level `/network-instances` → `NotSupportedError`
- DELETE `network-instance=default` → `InvalidArgsError` (*Deletion of 'default' network instance is not allowed*)
- Named VRF without `L3VRF` type or missing type on create → `InvalidArgsError` (*instanceType should be L3VRF*; requires `Vrf` name prefix)
- `default` create/update without `DEFAULT_INSTANCE` type → *Network Instance Not Found for 'default' with DEFAULT_INSTANCE type*
- `DEFAULT_INSTANCE` on non-`default` VRF → *DEFAULT_INSTANCE type is only supported for 'default' network instance*
- Unsupported `type` identity → *Only L3 VRF and DEFAULT_INSTANCE types are supported currently*
- `config/name` ≠ list key → configured name mismatch error

**Interfaces:**
- Interface GET/DELETE under wrong VRF → `NotFoundError` (*Interface … is bound to VRF 'X', not 'Y'*)
- Subinterface without `interface` leaf → *interface field is mandatory when subinterface is configured*
- Subinterface index `0` → *Sub-interface with 0 index is not supported*
- Dotted string in `config/interface` → *invalid interface format not supported*

**VLANs:**
- VLAN id missing in path → `NotFoundError`
- VLAN name ≠ `Vlan{vlan-id}` → *VLAN name does not match VLAN ID in path*
- VLAN id outside CVL range (2–4094) → `TranslibCVLFailure`
- `static-anycast-gateway` on non-`default` network instance → *Static anycast gateway is only supported for default network instance*

**FDB:**
- Anycast gateway MAC on non-`default` network instance → *Anycast gateway MAC is only supported for default network instance*
- Specific MAC+VLAN not found in ASIC FDB → not-found error

**Protocol container:**
- Unsupported protocol identifier or wrong `(identifier, name)` pair (see §4.5.3)
- PATCH/SET on `protocols/protocol/config/enabled` → `NotSupportedError` (*protocol enabled field is read-only*)

# 7 Unit Test Cases

## 7.1 Functional Test Cases
1. VRF CRUD: POST/PUT/PATCH/GET/DELETE named VRFs; list GET; PATCH `DEFAULT_INSTANCE` on `default`.
2. Interface bindings: bind Ethernet and subinterface to VRF (`vrf_name` in INTERFACE / VLAN_SUB_INTERFACE); GET `interfaces/interface/state`; DELETE unbind.
3. VLAN CRUD: POST multi-VLAN, PUT single, GET one/all, DELETE one/all in network instance.
4. VLAN `static-anycast-gateway`: PUT/GET/PATCH/DELETE on default VRF; POST VLAN with SAG in one request.
5. FDB `anycast-gateway-mac`: PUT/GET config+state, PATCH container, DELETE on default VRF only.
6. gNMI subscribe interface state: VRF rebinding and wildcard VRF filter.
7. Protocol container: `config/enabled` GET returns `true`; STATIC, BGP, and LOCAL_AGGREGATE delegate to correct backing tables.
8. LOCAL_AGGREGATE protocol entry is independent of BGP protocol entry (separate list keys).

## 7.2 Negative Test Cases
1. DELETE `/network-instances` container → `NotSupportedError`.
2. DELETE `network-instance=default` → `InvalidArgsError`.
3. POST named VRF with `DEFAULT_INSTANCE` or missing `type` → rejected.
4. Subinterface without `interface` leaf → rejected.
5. VLAN name mismatch or invalid VLAN id (CVL) → rejected.
6. Anycast gateway MAC or `static-anycast-gateway` on non-`default` VRF → rejected.
7. GET/DELETE interface under wrong VRF → `NotFoundError`.
8. PATCH `protocol/…/config/enabled` → `NotSupportedError`.
9. Unsupported protocol identifier (for example OSPF) or wrong `(identifier, name)` pair → validation error.
10. LOCAL_AGGREGATE configuration rejected when `BGP_GLOBALS` does not exist for the VRF.
