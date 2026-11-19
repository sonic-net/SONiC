# OpenConfig Model Support for SONiC VRRP (IPv4 and IPv6)

# High Level Design Document
#### Rev 0.2

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
 * [4.1 Bases](#41-bases)
 * [4.2 IPv6 subinterface (full paths)](#42-ipv6-subinterface-full-paths)
 * [4.3 IPv4 subinterface (full paths)](#43-ipv4-subinterface-full-paths)
 * [4.4 IPv6 routed-vlan / SVI (full paths)](#44-ipv6-routed-vlan--svi-full-paths)
 * [4.5 IPv4 routed-vlan / SVI (full paths)](#45-ipv4-routed-vlan--svi-full-paths)
 * [4.6 Deviations / notes](#46-deviations--notes)
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
| 0.2 | 11/18/2026 | Malavika Unnikrishnan | Cover IPv4, routed-vlan, and remaining OC VRRP leaves |

# About this Manual
This document is the UMF (transformer) design for OpenConfig VRRP. It describes how `openconfig-if-ip` `vrrp-group` on IPv4/IPv6 subinterfaces and routed-vlan / SVI is translated to CONFIG_DB `VRRP` / `VRRP_TRACK` and `VRRP6` / `VRRP6_TRACK` over REST and gNMI.

It does not describe native VRRP, FRR, or CLI.

OpenConfig xpath bases are listed in [Section 4.1](#41-bases).

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture (REST, gNMI, translib, transformers) |
| OpenConfig_Interfaces.md | Parent Ethernet / IPv6 address tree |

# Scope
- **In scope:** REST and gNMI Get, Set (POST/PUT/PATCH), Delete, and Subscribe on the four `vrrp-group` bases and suffixes in [Section 4](#4-openconfig-to-sonic-mapping-table).
- **Out of scope:** native VRRP dataplane, FRR, and KLISH/click CLI.
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
2. Map OpenConfig IPv4 `vrrp-group` onto CONFIG_DB `VRRP|{interface}|{vrid}` and `VRRP_TRACK|{interface}|{vrid}|{track_if}`.
3. Support both subinterface and `openconfig-vlan:routed-vlan` (SVI) anchors.
4. Support Get, Patch, Put, Post, Delete, and Subscribe for the suffixes in [Section 4](#4-openconfig-to-sonic-mapping-table).
5. Merge IPv6 `virtual-address` and `virtual-link-local` into the same native `vip` leaf-list.
6. Translate OpenConfig boolean `preempt` to native `enabled` / `disabled`.
7. Translate OpenConfig `priority-decrement` to native `priority_increment`.
8. Map `preempt-delay`, `advertisement-interval`, and `accept-mode` onto CONFIG_DB.
9. Enable/disable is presence of the `VRRP` / `VRRP6` row. UMF does not write `FEATURE|*`.

## 1.2 Design Overview
Field transformers on all four `vrrp-group` bases, plus an interface-tracking subtree. No new Redis tables. Code is in `sonic-mgmt-common`. CVL schema is `sonic-vrrp.yang`.

# 2 Functionality
A REST or gNMI client reads and writes IPv4 and IPv6 VRRP under an existing L3 address on a subinterface or routed VLAN. Strict leaf GET returns the mapped CONFIG_DB value.

# 3 Design
## 3.1 Overview
OpenConfig YANG → annotation → `xfmr_vrrp.go` → CONFIG_DB, following the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

### 3.1.1 UMF Translation
| Artifact | Role |
|----------|------|
| `openconfig-if-ip-vrrp-annot.yang` | Full-path field transformers on all four `vrrp-group` bases |
| `xfmr_vrrp.go` | YangToDb / DbToYang / Subscribe |
| `sonic-vrrp.yang` | CVL for `VRRP` / `VRRP_TRACK` / `VRRP6` / `VRRP6_TRACK` |

### 3.1.2 Mapping Rules and Exceptions
| Rule | Detail |
|------|--------|
| Placement | VRRP is under the IPv4 or IPv6 **address** on a subinterface or routed-vlan. List key is `virtual-router-id`. |
| VIP type | OpenConfig `virtual-address` / `virtual-link-local` are `oc-inet:ip-address` (no CIDR). UMF stores native prefixes (`/32` IPv4, `/128` IPv6). |
| VIP merge | IPv6 global and link-local share Redis `vip@`. SET of one list preserves the other. |
| Preempt | OpenConfig `true`/`false` → CONFIG_DB `enabled`/`disabled`. |
| Advertisement interval | OC centiseconds / 100 → native `adv_interval` seconds (1..40). |
| Tracking | One OpenConfig container expands to N `VRRP_TRACK` or `VRRP6_TRACK` rows. `priority-decrement` is stored as `priority_increment`. |
| Enable | Creating a `VRRP` or `VRRP6` row enables the group. UMF never writes `FEATURE|*`. |

## 3.2 DB Changes
No new tables. UMF writes `VRRP` / `VRRP6` fields `vid`, `priority`, `preempt`, `preempt_delay`, `accept_mode`, `adv_interval`, `vip`, and `VRRP_TRACK` / `VRRP6_TRACK` `priority_increment`. It does not SET `version` or `admin_status`.

# 4 OpenConfig to SONiC Mapping Table

IPv4 OpenConfig maps to CONFIG_DB `VRRP` / `VRRP_TRACK`. IPv6 OpenConfig maps to `VRRP6` / `VRRP6_TRACK`.

## 4.1 Bases

| Family | Anchor | Full OpenConfig base | CONFIG_DB |
|--------|--------|----------------------|-----------|
| IPv4 | subinterface | `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]` | `VRRP` / `VRRP_TRACK` |
| IPv6 | subinterface | `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]` | `VRRP6` / `VRRP6_TRACK` |
| IPv4 | routed-vlan / SVI | `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]` | `VRRP` / `VRRP_TRACK` |
| IPv6 | routed-vlan / SVI | `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]` | `VRRP6` / `VRRP6_TRACK` |

## 4.2 IPv6 subinterface (full paths)

### IPv6 subinterface

Base: `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]`

| OpenConfig YANG Node | Field transformer | DB Name | Table:Field | Notes |
|----------------------|-------------------|---------|-------------|-------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` | CONFIG_DB | VRRP or VRRP6 key `{if}|{vrid}` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/virtual-router-id` | `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` | CONFIG_DB | key `{vrid}` / `vid` | list key; `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-router-id`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-router-id` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` | CONFIG_DB | `VRRP6.vid` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-address` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` | CONFIG_DB | `VRRP6.vip@` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` | CONFIG_DB | `VRRP6.priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt` | `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` | CONFIG_DB | `VRRP6.preempt` | OC bool → `enabled`/`disabled`; `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt-delay`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt-delay` | `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` | CONFIG_DB | `VRRP6.preempt_delay` | 0..3600 seconds; `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/accept-mode` | `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` | CONFIG_DB | `VRRP6.accept_mode` | OC bool → `true`/`false`; `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/advertisement-interval`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/advertisement-interval` | `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` | CONFIG_DB | `VRRP6.adv_interval` | OC centiseconds / 100 → native seconds 1..40; `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/track-interface`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/track-interface` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) | CONFIG_DB | `VRRP6_TRACK` or `VRRP6_TRACK` key `{if}|{vrid}|{track_if}` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/priority-decrement`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/priority-decrement` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` | CONFIG_DB | `VRRP6.priority_increment` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/current-priority` | `DbToYang_vrrp_current_priority_xfmr` | CONFIG_DB | `VRRP6.priority` | GET mirrors configured priority; `DbToYang_vrrp_current_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-link-local`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-link-local` | `YangToDb_vrrp_virtual_link_local_xfmr` / `DbToYang_vrrp_virtual_link_local_xfmr` | CONFIG_DB | `VRRP6.vip@` `fe80:` | IPv6 only; `YangToDb_vrrp_virtual_link_local_xfmr` / `DbToYang_vrrp_virtual_link_local_xfmr` |

## 4.3 IPv4 subinterface (full paths)

### IPv4 subinterface

Base: `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]`

| OpenConfig YANG Node | Field transformer | DB Name | Table:Field | Notes |
|----------------------|-------------------|---------|-------------|-------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` | CONFIG_DB | VRRP or VRRP6 key `{if}|{vrid}` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/virtual-router-id` | `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` | CONFIG_DB | key `{vrid}` / `vid` | list key; `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-router-id`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-router-id` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` | CONFIG_DB | `VRRP.vid` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-address` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` | CONFIG_DB | `VRRP.vip@` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` | CONFIG_DB | `VRRP.priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt` | `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` | CONFIG_DB | `VRRP.preempt` | OC bool → `enabled`/`disabled`; `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt-delay`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt-delay` | `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` | CONFIG_DB | `VRRP.preempt_delay` | 0..3600 seconds; `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/accept-mode` | `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` | CONFIG_DB | `VRRP.accept_mode` | OC bool → `true`/`false`; `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/advertisement-interval`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/advertisement-interval` | `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` | CONFIG_DB | `VRRP.adv_interval` | OC centiseconds / 100 → native seconds 1..40; `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/track-interface`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/track-interface` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) | CONFIG_DB | `VRRP_TRACK` or `VRRP_TRACK` key `{if}|{vrid}|{track_if}` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/priority-decrement`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/priority-decrement` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` | CONFIG_DB | `VRRP.priority_increment` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/current-priority` | `DbToYang_vrrp_current_priority_xfmr` | CONFIG_DB | `VRRP.priority` | GET mirrors configured priority; `DbToYang_vrrp_current_priority_xfmr` |

## 4.4 IPv6 routed-vlan / SVI (full paths)

### IPv6 routed-vlan

Base: `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]`

| OpenConfig YANG Node | Field transformer | DB Name | Table:Field | Notes |
|----------------------|-------------------|---------|-------------|-------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` | CONFIG_DB | VRRP or VRRP6 key `{if}|{vrid}` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/virtual-router-id` | `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` | CONFIG_DB | key `{vrid}` / `vid` | list key; `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-router-id`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-router-id` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` | CONFIG_DB | `VRRP6.vid` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-address` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` | CONFIG_DB | `VRRP6.vip@` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` | CONFIG_DB | `VRRP6.priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt` | `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` | CONFIG_DB | `VRRP6.preempt` | OC bool → `enabled`/`disabled`; `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt-delay`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt-delay` | `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` | CONFIG_DB | `VRRP6.preempt_delay` | 0..3600 seconds; `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/accept-mode` | `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` | CONFIG_DB | `VRRP6.accept_mode` | OC bool → `true`/`false`; `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/advertisement-interval`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/advertisement-interval` | `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` | CONFIG_DB | `VRRP6.adv_interval` | OC centiseconds / 100 → native seconds 1..40; `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/track-interface`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/track-interface` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) | CONFIG_DB | `VRRP6_TRACK` or `VRRP6_TRACK` key `{if}|{vrid}|{track_if}` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/priority-decrement`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/priority-decrement` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` | CONFIG_DB | `VRRP6.priority_increment` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/current-priority` | `DbToYang_vrrp_current_priority_xfmr` | CONFIG_DB | `VRRP6.priority` | GET mirrors configured priority; `DbToYang_vrrp_current_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-link-local`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-link-local` | `YangToDb_vrrp_virtual_link_local_xfmr` / `DbToYang_vrrp_virtual_link_local_xfmr` | CONFIG_DB | `VRRP6.vip@` `fe80:` | IPv6 only; `YangToDb_vrrp_virtual_link_local_xfmr` / `DbToYang_vrrp_virtual_link_local_xfmr` |

## 4.5 IPv4 routed-vlan / SVI (full paths)

### IPv4 routed-vlan

Base: `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]`

| OpenConfig YANG Node | Field transformer | DB Name | Table:Field | Notes |
|----------------------|-------------------|---------|-------------|-------|
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` | CONFIG_DB | VRRP or VRRP6 key `{if}|{vrid}` | subtree/table `vrrp_table_xfmr` + `YangToDb_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/virtual-router-id` | `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` | CONFIG_DB | key `{vrid}` / `vid` | list key; `YangToDb_vrrp_group_key_xfmr` / `DbToYang_vrrp_group_key_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-router-id`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-router-id` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` | CONFIG_DB | `VRRP.vid` | `YangToDb_vrrp_virtual_router_id_xfmr` / `DbToYang_vrrp_virtual_router_id_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/virtual-address` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` | CONFIG_DB | `VRRP.vip@` | `YangToDb_vrrp_virtual_address_xfmr` / `DbToYang_vrrp_virtual_address_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` | CONFIG_DB | `VRRP.priority` | `YangToDb_vrrp_priority_xfmr` / `DbToYang_vrrp_priority_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt` | `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` | CONFIG_DB | `VRRP.preempt` | OC bool → `enabled`/`disabled`; `YangToDb_vrrp_preempt_xfmr` / `DbToYang_vrrp_preempt_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt-delay`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/preempt-delay` | `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` | CONFIG_DB | `VRRP.preempt_delay` | 0..3600 seconds; `YangToDb_vrrp_preempt_delay_xfmr` / `DbToYang_vrrp_preempt_delay_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/accept-mode`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/accept-mode` | `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` | CONFIG_DB | `VRRP.accept_mode` | OC bool → `true`/`false`; `YangToDb_vrrp_accept_mode_xfmr` / `DbToYang_vrrp_accept_mode_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/advertisement-interval`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/advertisement-interval` | `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` | CONFIG_DB | `VRRP.adv_interval` | OC centiseconds / 100 → native seconds 1..40; `YangToDb_vrrp_advertisement_interval_xfmr` / `DbToYang_vrrp_advertisement_interval_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/track-interface`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/track-interface` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) | CONFIG_DB | `VRRP_TRACK` or `VRRP_TRACK` key `{if}|{vrid}|{track_if}` | `YangToDb_vrrp_track_interface_xfmr` / `DbToYang_vrrp_track_interface_xfmr` (via `vrrp_interface_tracking_xfmr`) |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config/priority-decrement`<br>`/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/state/priority-decrement` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` | CONFIG_DB | `VRRP.priority_increment` | `YangToDb_vrrp_priority_decrement_xfmr` / `DbToYang_vrrp_priority_decrement_xfmr` |
| `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/state/current-priority` | `DbToYang_vrrp_current_priority_xfmr` | CONFIG_DB | `VRRP.priority` | GET mirrors configured priority; `DbToYang_vrrp_current_priority_xfmr` |

## 4.6 Deviations / notes

| Item | Result |
|------|--------|
| `advertisement-interval` | OC units are centiseconds; native `adv_interval` is seconds 1..40. SET must be a multiple of 100. |
| `current-priority` | GET mirrors configured `priority` until APPL_DB current priority is available. |
| `accept_mode` | Stored in CONFIG_DB. Native `frrcfgd` does not yet emit FRR accept-mode. |
| `virtual-link-local` | IPv6 only. |

# 5 User Interface
## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| openconfig-if-ip.yang | openconfig/public | VRRP grouping under IPv4 and IPv6 addresses |
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

PATCH IPv4 subinterface priority:

```
PATCH /restconf/data/openconfig-interfaces:interfaces/interface=Ethernet64/subinterfaces/subinterface=0/openconfig-if-ip:ipv4/addresses/address=10.10.10.1/vrrp/vrrp-group=3/config/priority
{"openconfig-if-ip:priority": 150}
```

Result: `VRRP|Ethernet64|3` field `priority=150`.

PATCH routed-vlan IPv6 priority:

```
PATCH /restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address=2001:db8:100::1/vrrp/vrrp-group=2/config/priority
{"openconfig-if-ip:priority": 140}
```

Result: `VRRP6|Vlan100|2` field `priority=140`.

## 5.3 gNMI Support
Get, Set (Update/Replace), Delete, and Subscribe on the paths in [Section 4](#4-openconfig-to-sonic-mapping-table). SET payloads use JSON_IETF, for example `{"openconfig-if-ip:priority": 120}`.

# 6 Error Handling
| Condition | Result |
|-----------|--------|
| `advertisement-interval` not a multiple of 100 centiseconds, or outside 1..40 seconds | InvalidArgs |
| `preempt-delay` greater than 3600 | InvalidArgs |
| `preempt` / `accept-mode` value that is not a boolean | transformer error |
| `virtual-link-local` on an IPv4 `vrrp-group` | not-supported |
| VIP that is not an IP address of the matching family | transformer / CVL error |

# 7 Unit Test Cases
## 7.1 Functional
1. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority` writes `VRRP6.priority`.
2. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/preempt` = `false` writes `preempt=disabled`.
3. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address` writes `vip@` global `/128` and preserves existing link-local.
4. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-link-local` merges `fe80:` into `vip@` and preserves globals.
5. PUT `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/interface-tracking/config` creates `VRRP6_TRACK` with `priority_increment`.
6. DELETE `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/virtual-address` strips globals only.
7. GET of each supported leaf matches CONFIG_DB.

8. PUT IPv4 subinterface `/openconfig-interfaces:interfaces/interface[name=<if>]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses/address[ip=<v4>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority` writes `VRRP.priority`.
9. PUT routed-vlan IPv6 `/openconfig-interfaces:interfaces/interface[name=<if>]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=<v6>]/vrrp/vrrp-group[virtual-router-id=<id>]/config/priority` writes `VRRP6.priority`.
10. PUT `/config/preempt-delay` writes `preempt_delay`. PUT `/config/accept-mode` writes `accept_mode`. PUT `/config/advertisement-interval` 200 writes `adv_interval=2`.

## 7.2 Negative
1. SET of `/config/virtual-link-local` on an IPv4 `vrrp-group` is rejected.
2. SET of `/config/advertisement-interval` that is not a multiple of 100 centiseconds is rejected.
