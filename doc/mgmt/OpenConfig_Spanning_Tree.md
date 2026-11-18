# OpenConfig Model Support for SONiC RSTP

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
 * [1.2 Design Overview](#12-design-overview)
 * [2 Functionality](#2-functionality)
 * [3 Design](#3-design)
 * [3.1 Overview](#31-overview)
 * [3.1.1 UMF Translation](#311-umf-translation)
 * [3.1.2 Mapping Rules and Exceptions](#312-mapping-rules-and-exceptions)
 * [3.2 DB Changes](#32-db-changes)
 * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
 * [4.1 Global / RSTP Instance](#41-global--rstp-instance)
 * [4.2 RSTP Interfaces](#42-rstp-interfaces)
 * [4.3 Common Interfaces](#43-common-interfaces)
 * [4.4 Operational State](#44-operational-state)
 * [4.5 Unsupported](#45-unsupported)
 * [5 User Interface](#5-user-interface)
 * [5.1 Data Models](#51-data-models)
 * [5.2 REST API Support](#52-rest-api-support)
 * [5.3 gNMI Support](#53-gnmi-support)
 * [6 Error Handling](#6-error-handling)
 * [7 Unit Test Cases](#7-unit-test-cases)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

OpenConfig to SONiC mapping tables: [Section 4](#4-openconfig-to-sonic-mapping-table)

# Revision
| Rev | Date | Author | Change Description |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 11/16/2026 | Malavika Unnikrishnan | Initial UMF mapping for OpenConfig RSTP |

# About this Manual
This document is the UMF (transformer) design for OpenConfig spanning-tree **RSTP**. It maps `/openconfig-spanning-tree:stp` onto existing CONFIG_DB `STP` / `STP_PORT` and APPL_DB `STP_RSTP_*` tables.

It is mapping only. It does not add native RSTP leaves, daemons, or CLI.

OpenConfig xpath root:

```
/openconfig-spanning-tree:stp
```

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture |

# Scope
- **In scope:** REST and gNMI Get, Set, Delete, and Subscribe for RSTP enable, timers, bridge priority, and the port leaves in [Section 4](#4-openconfig-to-sonic-mapping-table).
- **Out of scope:** MSTP, rapid-pvst, native STP daemon design, and the not-supported leaves in [Section 4.5](#45-unsupported).
- Supported attributes in the OpenConfig YANG tree:

```
module: openconfig-spanning-tree
  +--rw stp
     +--rw global
     |  +--rw config
     |  |  +--rw enabled-protocol*   identityref
     |  +--ro state
     |     +--ro enabled-protocol*   identityref
     +--rw rstp
     |  +--rw config
     |  |  +--rw hello-time?         uint8
     |  |  +--rw max-age?            uint8
     |  |  +--rw forwarding-delay?   uint8
     |  |  +--rw bridge-priority?    oc-stp-types:stp-bridge-priority-type
     |  +--ro state
     |  |  +--ro hello-time?         uint8
     |  |  +--ro max-age?            uint8
     |  |  +--ro forwarding-delay?   uint8
     |  |  +--ro bridge-priority?    oc-stp-types:stp-bridge-priority-type
     |  |  +--ro bridge-address?     oc-yang:mac-address
     |  |  +--ro designated-root-priority?   oc-stp-types:stp-bridge-priority-type
     |  |  +--ro designated-root-address?    oc-yang:mac-address
     |  |  +--ro root-port?          uint16
     |  |  +--ro root-cost?          uint32
     |  |  +--ro hold-time?          uint8
     |  +--rw interfaces
     |     +--rw interface* [name]
     |        +--rw name      -> ../config/name
     |        +--rw config
     |        |  +--rw name?            oc-if:base-interface-ref
     |        |  +--rw cost?            uint32
     |        |  +--rw port-priority?   oc-stp-types:stp-port-priority-type
     |        +--ro state
     |           +--ro name?            oc-if:base-interface-ref
     |           +--ro cost?            uint32
     |           +--ro port-priority?   oc-stp-types:stp-port-priority-type
     |           +--ro port-num?        uint16
     |           +--ro role?            identityref
     |           +--ro port-state?      identityref
     |           +--ro designated-*     ...
     +--rw interfaces
        +--rw interface* [name]
           +--rw name      -> ../config/name
           +--rw config
           |  +--rw name?         oc-if:base-interface-ref
           |  +--rw edge-port?    identityref
           |  +--rw link-type?    enumeration
           |  +--rw guard?        enumeration
           |  +--rw bpdu-guard?   boolean
           +--ro state
              +--ro name?         oc-if:base-interface-ref
              +--ro edge-port?    identityref
              +--ro link-type?    enumeration
              +--ro guard?        enumeration
              +--ro bpdu-guard?   boolean
```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term** | **Definition** |
|----------|----------------|
| UMF | Unified Management Framework (translib + transformers) |
| RSTP | Rapid Spanning Tree Protocol |

# 1 Feature Overview
## 1.1 Requirements
1. Map OpenConfig RSTP onto existing `STP|GLOBAL` and `STP_PORT|<if>` CONFIG_DB rows.
2. Enable/disable uses protocol CONFIG_DB (`mode=rstp`). UMF never writes `FEATURE|*`.
3. Accept only identity `RSTP` in `enabled-protocol`.
4. Map timers and bridge-priority on `/openconfig-spanning-tree:stp/rstp/config`.
5. Map cost / port-priority on `/openconfig-spanning-tree:stp/rstp/interfaces`. Map edge-port / link-type / guard / bpdu-guard on `/openconfig-spanning-tree:stp/interfaces`.
6. Reject `EDGE_AUTO` and guard `LOOP`.
7. Mark MSTP, rapid-pvst, and the leaves in [Section 4.5](#45-unsupported) as not-supported.
8. State GET reads APPL_DB `STP_RSTP_INST_TABLE` / `STP_RSTP_PORT_TABLE` when those rows exist.

## 1.2 Design Overview
One subtree transformer (`stp_xfmr`) on `/openconfig-spanning-tree:stp`. Mapping only onto native STP tables already owned by the RSTP implementation. No new Redis tables and no new native yang leaves from UMF.

# 2 Functionality
A REST or gNMI client enables RSTP, sets hello-time / max-age / forwarding-delay / bridge-priority, and sets per-port cost, priority, edge, link-type, root-guard, and bpdu-guard. GET returns CONFIG_DB for config leaves and APPL_DB for operational role/state when present.

# 3 Design
## 3.1 Overview
OpenConfig YANG → `openconfig-spanning-tree-annotation.json` → `xfmr_stp.go` → CONFIG_DB / APPL_DB.

### 3.1.1 UMF Translation
| Artifact | Role |
|----------|------|
| `openconfig-spanning-tree-annotation.json` | subtree on `/openconfig-spanning-tree:stp`; not-supported on MSTP / rapid-pvst / unused leaves |
| `xfmr_stp.go` | YangToDb / DbToYang / Subscribe |

### 3.1.2 Mapping Rules and Exceptions
| Rule | Detail |
|------|--------|
| Enable | `enabled-protocol` containing `RSTP` writes `STP|GLOBAL mode=rstp` plus default timers if absent. |
| Disable | Empty `enabled-protocol`, DELETE `/openconfig-spanning-tree:stp`, DELETE `/openconfig-spanning-tree:stp/rstp`, or DELETE `enabled-protocol` deletes `STP|GLOBAL` and `STP_PORT` rows. UMF does not write `FEATURE|*`. |
| RSTP-only | Any other `enabled-protocol` identity is rejected. GET is silent (empty tree) when `mode` is not `rstp`. |
| Timer DELETE | DELETE of a timer leaf restores the UMF default (`hello-time=2`, `max-age=20`, `forwarding-delay=15`, `bridge-priority=32768`), it does not disable RSTP. DELETE `/openconfig-spanning-tree:stp/rstp/config` resets those timers only. |
| Port split | Cost and port-priority are under `/openconfig-spanning-tree:stp/rstp/interfaces`. Edge, link-type, guard, and bpdu-guard are under `/openconfig-spanning-tree:stp/interfaces`. Both write `STP_PORT|<if>`. |
| Enums | `edge-port` `EDGE_ENABLE`/`EDGE_DISABLE` → `edge_port` true/false. `EDGE_AUTO` is rejected. `link-type` `P2P`/`SHARED` → `point-to-point`/`shared`. `guard` `ROOT`/`NONE` → `root_guard` true/false. `LOOP` is rejected. |
| First port PATCH | Creating an `STP_PORT` row may set `enabled=true` so the native table has a complete key. |

## 3.2 DB Changes
No new tables.

| DB | Table | Written / read by UMF |
|----|-------|------------------------|
| CONFIG_DB | `STP\|GLOBAL` | write/read `mode`, `hello_time`, `max_age`, `forward_delay`, `priority` |
| CONFIG_DB | `STP_PORT\|<if>` | write/read `enabled`, `path_cost`, `priority`, `edge_port`, `link_type`, `root_guard`, `bpdu_guard` |
| APPL_DB | `STP_RSTP_INST_TABLE:0` | read-only state |
| APPL_DB | `STP_RSTP_PORT_TABLE:<if>` | read-only state |

# 4 OpenConfig to SONiC Mapping Table

## 4.1 Global / RSTP Instance

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| `/openconfig-spanning-tree:stp` | | CONFIG_DB | subtree `stp_xfmr` | |
| `/openconfig-spanning-tree:stp/global/config/enabled-protocol` | | CONFIG_DB | `STP\|GLOBAL.mode` | `RSTP` → `rstp`; empty/DELETE disables |
| `/openconfig-spanning-tree:stp/global/state/enabled-protocol` | | CONFIG_DB | `STP\|GLOBAL.mode` | |
| `/openconfig-spanning-tree:stp/rstp/config/hello-time` | | CONFIG_DB | `STP\|GLOBAL.hello_time` | default 2 on DELETE |
| `/openconfig-spanning-tree:stp/rstp/state/hello-time` | | CONFIG_DB | `STP\|GLOBAL.hello_time` | |
| `/openconfig-spanning-tree:stp/rstp/config/max-age` | | CONFIG_DB | `STP\|GLOBAL.max_age` | default 20 on DELETE |
| `/openconfig-spanning-tree:stp/rstp/state/max-age` | | CONFIG_DB | `STP\|GLOBAL.max_age` | |
| `/openconfig-spanning-tree:stp/rstp/config/forwarding-delay` | | CONFIG_DB | `STP\|GLOBAL.forward_delay` | default 15 on DELETE |
| `/openconfig-spanning-tree:stp/rstp/state/forwarding-delay` | | CONFIG_DB | `STP\|GLOBAL.forward_delay` | |
| `/openconfig-spanning-tree:stp/rstp/config/bridge-priority` | | CONFIG_DB | `STP\|GLOBAL.priority` | default 32768 on DELETE |
| `/openconfig-spanning-tree:stp/rstp/state/bridge-priority` | | CONFIG_DB | `STP\|GLOBAL.priority` | |

## 4.2 RSTP Interfaces

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/config/name` | | CONFIG_DB | `STP_PORT` key | |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/config/cost` | | CONFIG_DB | `STP_PORT.path_cost` | |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/cost` | | CONFIG_DB | `STP_PORT.path_cost` | |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/config/port-priority` | | CONFIG_DB | `STP_PORT.priority` | |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/port-priority` | | CONFIG_DB | `STP_PORT.priority` | |

## 4.3 Common Interfaces

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/edge-port` | | CONFIG_DB | `STP_PORT.edge_port` | `EDGE_ENABLE`/`EDGE_DISABLE` only |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/state/edge-port` | | CONFIG_DB | `STP_PORT.edge_port` | |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/link-type` | | CONFIG_DB | `STP_PORT.link_type` | `P2P` → `point-to-point`; `SHARED` → `shared` |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/state/link-type` | | CONFIG_DB | `STP_PORT.link_type` | |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/guard` | | CONFIG_DB | `STP_PORT.root_guard` | `ROOT`/`NONE` only |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/state/guard` | | CONFIG_DB | `STP_PORT.root_guard` | |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/bpdu-guard` | | CONFIG_DB | `STP_PORT.bpdu_guard` | boolean |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/state/bpdu-guard` | | CONFIG_DB | `STP_PORT.bpdu_guard` | |

## 4.4 Operational State

Read from APPL_DB when the native daemon has populated the row. Missing APPL_DB is not treated as a config failure.

| OpenConfig YANG Node | DB Name | Table:Field |
|----------------------|---------|-------------|
| `/openconfig-spanning-tree:stp/rstp/state/bridge-address` | APPL_DB | `STP_RSTP_INST_TABLE.bridge_address` |
| `/openconfig-spanning-tree:stp/rstp/state/designated-root-priority` | APPL_DB | `STP_RSTP_INST_TABLE.root_address` |
| `/openconfig-spanning-tree:stp/rstp/state/designated-root-address` | APPL_DB | `STP_RSTP_INST_TABLE.root_address` |
| `/openconfig-spanning-tree:stp/rstp/state/root-cost` | APPL_DB | `STP_RSTP_INST_TABLE.root_path_cost` |
| `/openconfig-spanning-tree:stp/rstp/state/hold-time` | APPL_DB | `STP_RSTP_INST_TABLE.hold_time` |
| `/openconfig-spanning-tree:stp/rstp/state/root-port` | APPL_DB | `STP_RSTP_INST_TABLE.root_port` → port number from `STP_RSTP_PORT_TABLE` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/role` | APPL_DB | `STP_RSTP_PORT_TABLE.role` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/port-state` | APPL_DB | `STP_RSTP_PORT_TABLE.port_state` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/port-num` | APPL_DB | `STP_RSTP_PORT_TABLE.port_number` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/designated-root-address` | APPL_DB | `STP_RSTP_PORT_TABLE.desig_root` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/designated-bridge-address` | APPL_DB | `STP_RSTP_PORT_TABLE.desig_bridge` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/designated-cost` | APPL_DB | `STP_RSTP_PORT_TABLE.desig_cost` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/designated-port-num` | APPL_DB | `STP_RSTP_PORT_TABLE.desig_port` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/forward-transisitions` | APPL_DB | `STP_RSTP_PORT_TABLE.fwd_transitions` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/counters/bpdu-sent` | APPL_DB | `STP_RSTP_PORT_TABLE.bpdu_sent` |
| `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/state/counters/bpdu-received` | APPL_DB | `STP_RSTP_PORT_TABLE.bpdu_received` |

## 4.5 Unsupported

| OpenConfig YANG Node | Result |
|----------------------|--------|
| `/openconfig-spanning-tree:stp/mstp` | not-supported |
| `/openconfig-spanning-tree:stp/rapid-pvst` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/bridge-assurance` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/bridge-assurance` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/etherchannel-misconfig-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/etherchannel-misconfig-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/bpduguard-timeout-recovery` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/bpduguard-timeout-recovery` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/loop-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/loop-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/bpdu-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/bpdu-guard` | not-supported |
| `/openconfig-spanning-tree:stp/global/config/bpdu-filter` | not-supported |
| `/openconfig-spanning-tree:stp/global/state/bpdu-filter` | not-supported |
| `/openconfig-spanning-tree:stp/rstp/config/hold-count` | not-supported |
| `/openconfig-spanning-tree:stp/rstp/state/hold-count` | not-supported |
| `/openconfig-spanning-tree:stp/rstp/state/topology-changes` | not-supported |
| `/openconfig-spanning-tree:stp/rstp/state/last-topology-change` | not-supported |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/bpdu-filter` | not-supported |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/state/bpdu-filter` | not-supported |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/edge-port` = `EDGE_AUTO` | InvalidArgs |
| `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/guard` = `LOOP` | InvalidArgs |
| `/openconfig-spanning-tree:stp/global/config/enabled-protocol` other than `RSTP` | InvalidArgs |

# 5 User Interface
## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| openconfig-spanning-tree.yang | openconfig/public | RSTP tree |
| openconfig-spanning-tree-annotation.json | sonic-mgmt-common | UMF bindings and not-supported deviations |

## 5.2 REST API Support
Enable RSTP:

```
PATCH /restconf/data/openconfig-spanning-tree:stp/global/config/enabled-protocol
{"openconfig-spanning-tree:enabled-protocol": ["RSTP"]}
```

Result: `STP|GLOBAL mode=rstp`.

PATCH hello-time:

```
PATCH /restconf/data/openconfig-spanning-tree:stp/rstp/config/hello-time
{"openconfig-spanning-tree:hello-time": 1}
```

Result: `STP|GLOBAL hello_time=1`.

## 5.3 gNMI Support
Get, Set, Delete, and Subscribe on the supported paths in [Section 4](#4-openconfig-to-sonic-mapping-table). Subscribe maps Redis fields to YANG leaf names (`hello_time` → `hello-time`, `path_cost` → `cost`, `root_guard` → `guard`).

# 6 Error Handling
| Condition | Result |
|-----------|--------|
| `enabled-protocol` other than RSTP | InvalidArgs |
| Timer / port SET while RSTP is not enabled | InvalidArgs (`set enabled-protocol to RSTP first`) |
| `EDGE_AUTO` | InvalidArgs |
| `guard LOOP` | InvalidArgs |
| `/openconfig-spanning-tree:stp/mstp` or `/openconfig-spanning-tree:stp/rapid-pvst` | not-supported |
| Unknown interface GET | NotFound |

# 7 Unit Test Cases
## 7.1 Functional
1. PATCH `/openconfig-spanning-tree:stp/global/config/enabled-protocol` = `RSTP` writes `STP|GLOBAL mode=rstp`.
2. PATCH `/openconfig-spanning-tree:stp/rstp/config/hello-time`, `/openconfig-spanning-tree:stp/rstp/config/max-age`, `/openconfig-spanning-tree:stp/rstp/config/forwarding-delay`, `/openconfig-spanning-tree:stp/rstp/config/bridge-priority` write the matching GLOBAL fields.
3. PATCH `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/config/cost` / `/openconfig-spanning-tree:stp/rstp/interfaces/interface[name=<if>]/config/port-priority` write `STP_PORT`.
4. PATCH `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/edge-port`, `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/link-type`, `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/guard` = `ROOT`, `/openconfig-spanning-tree:stp/interfaces/interface[name=<if>]/config/bpdu-guard` write `STP_PORT`.
5. GET of `/openconfig-spanning-tree:stp/rstp/config/bridge-priority` and `/openconfig-spanning-tree:stp/rstp/config/hello-time` matches CONFIG_DB.
6. DELETE of a timer leaf restores the default without deleting `STP|GLOBAL`.

## 7.2 Negative
1. Non-RSTP `enabled-protocol` is rejected.
2. `EDGE_AUTO` is rejected.
3. `guard LOOP` is rejected.
4. SET of `/openconfig-spanning-tree:stp/mstp` or `/openconfig-spanning-tree:stp/rapid-pvst` is not-supported.
5. GET of an unknown ifname returns NotFound.
