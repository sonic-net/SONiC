# OpenConfig Model Support for SONiC VRRP (IPv6)

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
 * [4.1 Supported IPv6 VRRP Leaves](#41-supported-ipv6-vrrp-leaves)
 * [4.2 Unsupported OpenConfig VRRP Leaves](#42-unsupported-openconfig-vrrp-leaves)
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
| 0.1 | 11/16/2026 | Malavika Unnikrishnan | Initial UMF mapping for OpenConfig IPv6 VRRP |

# About this Manual
This document is the UMF (transformer) design for OpenConfig IPv6 VRRP. It describes how `openconfig-if-ip` `vrrp-group` is translated to CONFIG_DB `VRRP6` / `VRRP6_TRACK` over REST and gNMI.

It does not describe native VRRP, FRR, or CLI.

OpenConfig xpath root:

```
/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]
```

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture (REST, gNMI, translib, transformers) |
| OpenConfig_Interfaces.md | Parent Ethernet / IPv6 address tree |

# Scope
- **In scope:** REST and gNMI Get, Set (POST/PUT/PATCH), Delete, and Subscribe on the five IPv6 VRRP leaves in [Section 4.1](#41-supported-ipv6-vrrp-leaves).
- **Out of scope:** native VRRP dataplane, FRR, KLISH/click CLI, IPv4 OpenConfig VRRP, and the OpenConfig leaves in [Section 4.2](#42-unsupported-openconfig-vrrp-leaves).
- Supported attributes in the OpenConfig YANG tree:

```
module: openconfig-if-ip
  +--rw interfaces
     +--rw interface* [name]
        +--rw subinterfaces
           +--rw subinterface* [index]
              +--rw oc-ip:ipv6
                 +--rw oc-ip:addresses
                    +--rw oc-ip:address* [ip]
                       +--rw oc-ip:vrrp
                          +--rw oc-ip:vrrp-group* [virtual-router-id]
                             +--rw oc-ip:virtual-router-id    -> ../config/virtual-router-id
                             +--rw oc-ip:config
                             |  +--rw oc-ip:virtual-router-id?   uint8
                             |  +--rw oc-ip:virtual-address*     oc-inet:ip-address
                             |  +--rw oc-ip:priority?            uint8
                             |  +--rw oc-ip:preempt?             boolean
                             |  +--rw oc-ip:virtual-link-local?  oc-inet:ip-address
                             +--ro oc-ip:state
                             |  +--ro oc-ip:virtual-router-id?   uint8
                             |  +--ro oc-ip:virtual-address*     oc-inet:ip-address
                             |  +--ro oc-ip:priority?            uint8
                             |  +--ro oc-ip:preempt?             boolean
                             |  +--ro oc-ip:virtual-link-local?  oc-inet:ip-address
                             +--rw oc-ip:interface-tracking
                                +--rw oc-ip:config
                                |  +--rw oc-ip:track-interface*      string
                                |  +--rw oc-ip:priority-decrement?   uint8
                                +--ro oc-ip:state
                                   +--ro oc-ip:track-interface*      string
                                   +--ro oc-ip:priority-decrement?   uint8
```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term** | **Definition** |
|----------|----------------|
| YANG | Yet Another Next Generation |
| gNMI | gRPC Network Management Interface |
| UMF | Unified Management Framework (translib + transformers) |
| VRID | Virtual Router Identifier |

# 1 Feature Overview
## 1.1 Requirements
1. Map OpenConfig IPv6 `vrrp-group` onto CONFIG_DB `VRRP6|{interface}|{vrid}` and `VRRP6_TRACK|{interface}|{vrid}|{track_if}`.
2. Support Get, Patch, Put, Post, Delete, and Subscribe for the five scoped leaves.
3. Merge global `virtual-address` and `virtual-link-local` into the same native `vip` leaf-list.
4. Translate OpenConfig boolean `preempt` to native `enabled` / `disabled`.
5. Translate OpenConfig `priority-decrement` to native `priority_increment`.
6. Mark IPv4 OpenConfig VRRP and the leaves in [Section 4.2](#42-unsupported-openconfig-vrrp-leaves) as not-supported.
7. Enable/disable is presence of the `VRRP6` row. UMF does not write `FEATURE|*`.

## 1.2 Design Overview
A subtree transformer on `vrrp-group` plus field transformers for the five leaves. No new Redis tables. Code is in the Management Framework / gnmi containers (`sonic-mgmt-common`). CVL schema for the rows UMF writes is `sonic-vrrp.yang`.

# 2 Functionality
A REST or gNMI client reads and writes IPv6 VRRP under an existing L3 IPv6 address. Strict leaf GET returns the mapped CONFIG_DB value.

# 3 Design
## 3.1 Overview
OpenConfig YANG → annotation → `xfmr_vrrp.go` → CONFIG_DB, following the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

### 3.1.1 UMF Translation
| Artifact | Role |
|----------|------|
| `openconfig-if-ip-vrrp-annot.yang` | table / field / subtree bindings |
| `xfmr_vrrp.go` | YangToDb / DbToYang / Subscribe |
| `openconfig-interfaces-deviation.yang` | IPv4 `vrrp` remains not-supported; IPv6 `vrrp` is enabled |
| `sonic-vrrp.yang` | CVL for `VRRP6` / `VRRP6_TRACK` rows the transformer writes |

### 3.1.2 Mapping Rules and Exceptions
| Rule | Detail |
|------|--------|
| Placement | VRRP is under the IPv6 **address**, not under the subinterface. List key is `virtual-router-id`. |
| VIP type | OpenConfig `virtual-address` / `virtual-link-local` are `oc-inet:ip-address` (no CIDR). UMF stores native prefixes (`/128` for globals). |
| VIP merge | Global and link-local share Redis `vip@`. SET of one list preserves the other. DELETE of one list keeps the other. Link-local detection is `fe80:`. |
| Preempt | OpenConfig `true`/`false` → CONFIG_DB `enabled`/`disabled`. |
| Tracking | One OpenConfig container expands to N `VRRP6_TRACK` rows. `priority-decrement` is stored as `priority_increment`. |
| Enable | Creating a `VRRP6` row enables the group. UMF never writes `FEATURE|*`. |

## 3.2 DB Changes
No new tables. UMF writes a subset of existing `VRRP6` / `VRRP6_TRACK` fields: `vid`, `priority`, `preempt`, `vip`, `priority_increment`. It does not SET or GET `adv_interval`, `version`, `admin_status`, or `preempt_delay`.

# 4 OpenConfig to SONiC Mapping Table

## 4.1 Supported IPv6 VRRP Leaves

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]` | | CONFIG_DB | `VRRP6` key `{if}\|{vrid}` | subtree `vrrp_group_xfmr`; table `vrrp_table_xfmr`; key `vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-router-id` | | CONFIG_DB | `VRRP6.vid` | key component; also stored as field `vid` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-router-id` | | CONFIG_DB | `VRRP6.vid` | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority` | | CONFIG_DB | `VRRP6.priority` | uint8 1..254; `vrrp_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/priority` | | CONFIG_DB | `VRRP6.priority` | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt` | | CONFIG_DB | `VRRP6.preempt` | OC bool → `enabled`/`disabled` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt` | | CONFIG_DB | `VRRP6.preempt` | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address` | | CONFIG_DB | `VRRP6.vip` (`vip@` in Redis) | non–link-local entries |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-address` | | CONFIG_DB | `VRRP6.vip` (`vip@` in Redis) | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-link-local` | | CONFIG_DB | `VRRP6.vip` (`vip@` in Redis) | `fe80:` entry merged into the same leaf-list |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-link-local` | | CONFIG_DB | `VRRP6.vip` (`vip@` in Redis) | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking` | | CONFIG_DB | `VRRP6_TRACK` | subtree `vrrp_interface_tracking_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/track-interface` | | CONFIG_DB | `VRRP6_TRACK` key `{if}\|{vrid}\|{track_if}` | leaf-list of interface names |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/track-interface` | | CONFIG_DB | `VRRP6_TRACK` key `{if}\|{vrid}\|{track_if}` | |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/priority-decrement` | | CONFIG_DB | `VRRP6_TRACK.priority_increment` | name differs from OpenConfig |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/priority-decrement` | | CONFIG_DB | `VRRP6_TRACK.priority_increment` | |

## 4.2 Unsupported OpenConfig VRRP Leaves

| OpenConfig YANG Node | Result |
|----------------------|--------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/accept-mode` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt-delay` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt-delay` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/advertisement-interval` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/advertisement-interval` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/current-priority` | not-supported |

# 5 User Interface
## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| openconfig-if-ip.yang | openconfig/public | VRRP grouping under IPv6 address |
| openconfig-if-ip-vrrp-annot.yang | sonic-mgmt-common | UMF bindings |
| sonic-vrrp.yang | sonic-yang-models | CVL for rows UMF writes |

## 5.2 REST API Support
GET priority:

```
GET /restconf/data/openconfig-interfaces:interfaces/interface=Ethernet64/subinterfaces/subinterface=0/openconfig-if-ip:ipv6/addresses/address=2001:db8::1/vrrp/vrrp-group=1/config/priority
```

PATCH preempt:

```
PATCH /restconf/data/openconfig-interfaces:interfaces/interface=Ethernet64/subinterfaces/subinterface=0/openconfig-if-ip:ipv6/addresses/address=2001:db8::1/vrrp/vrrp-group=1/config/preempt
{"openconfig-if-ip:preempt": false}
```

Result: `VRRP6|Ethernet64|1` field `preempt=disabled`.

PATCH virtual-address:

```
PATCH /restconf/data/openconfig-interfaces:interfaces/interface=Ethernet64/subinterfaces/subinterface=0/openconfig-if-ip:ipv6/addresses/address=2001:db8::1/vrrp/vrrp-group=1/config/virtual-address
{"openconfig-if-ip:virtual-address": ["2001:db8::10"]}
```

Result: `vip@` includes `2001:db8::10/128` and any existing `fe80:` entry.

## 5.3 gNMI Support
Get, Set (Update/Replace), Delete, and Subscribe on the paths in [Section 4.1](#41-supported-ipv6-vrrp-leaves). SET payloads use JSON_IETF, for example `{"openconfig-if-ip:priority": 120}`.

# 6 Error Handling
| Condition | Result |
|-----------|--------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp` | not-supported |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`, `preempt-delay`, or `advertisement-interval` SET | not-supported |
| `preempt` value that is not a boolean | transformer error |
| VIP that is not an IPv6 address | transformer / CVL error |

# 7 Unit Test Cases
## 7.1 Functional
1. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority` writes `VRRP6.priority`.
2. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt` = `false` writes `preempt=disabled`.
3. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address` writes `vip@` global `/128` and preserves existing link-local.
4. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-link-local` merges `fe80:` into `vip@` and preserves globals.
5. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config` creates `VRRP6_TRACK` with `priority_increment`.
6. DELETE `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address` strips globals only.
7. GET of each supported leaf matches CONFIG_DB.

## 7.2 Negative
1. SET of `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp` is rejected.
2. SET of `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`, `preempt-delay`, or `advertisement-interval` is not-supported.
