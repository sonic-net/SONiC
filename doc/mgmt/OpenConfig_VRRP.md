# OpenConfig support for VRRP

# High Level Design Document

#### Rev 0.1

# Table of Contents

- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
- [1 Feature Overview](#1-feature-overview)
  - [1.1 Requirements](#11-requirements)
  - [1.2 Design Overview](#12-design-overview)
  - [1.3 Architecture](#13-architecture)
- [2 User Interface](#2-user-interface)
  - [2.1 Data Models](#21-data-models)
  - [2.2 Database Table and Field Mapping](#22-database-table-and-field-mapping)
  - [2.3 gNMI Support](#23-gnmi-support)
- [3 Testing](#3-testing)
- [4 Limitations](#4-limitations)

# List of Tables

- [Table 1: Abbreviations](#table-1-abbreviations)

# Revision

| Rev | Date |  Author | Change Description |
| - | - | - | - |
| 0.1 | 11/25/2026 | Balachander Rajarathinam (Nokia) <br /> Sriniketh J (Nokia) | Initial version |

# About this Manual

This document provides the high level design for OpenConfig support of VRRP in SONiC. It covers the VRRP groups of the `openconfig-if-ip` model, IPv4 and IPv6, on routed VLAN and sub-interface addresses, plus the VRRP state and counters added under `openconfig-if-ip-vrrp-ext`.

# Scope

This document covers the `vrrp` container under the following address paths, for `ipv4` and `ipv6`:

- `/openconfig-interfaces:interfaces/interface[name=<ifname>]/subinterfaces/subinterface[index=<idx>]/openconfig-if-ip:<ipv4|ipv6>/addresses/address[ip=<ip>]/vrrp`
- `/openconfig-interfaces:interfaces/interface[name=<ifname>]/openconfig-vlan:routed-vlan/openconfig-if-ip:<ipv4|ipv6>/addresses/address[ip=<ip>]/vrrp`

Covered operations:

- VRRP group creation, modification and deletion (`config`)
- VRRP group state and counters (`state`)
- VRRP Interface tracking (`interface-tracking`)
- gNMI Get, Set, Delete and Subscribe

# Definition/Abbreviation

### Table 1: Abbreviations

| **Term**  | **Definition** |
|-----------|----------------|
| VRRP      | Virtual Router Redundancy Protocol |
| VRID      | Virtual Router Identifier |
| VIP       | Virtual IP address of a VRRP group |
| CVL       | Config Validation Library |
| FRR       | Free Range Routing |

# 1 Feature Overview

OpenConfig VRRP support for SONiC.

```
  +--rw vrrp
     +--rw vrrp-group* [virtual-router-id]
        +--rw virtual-router-id   -> ../config/virtual-router-id
        +--rw config
        |  +--rw virtual-router-id?        uint8
        |  +--rw virtual-address*          oc-inet:ip-address
        |  +--rw priority?                 uint8
        |  +--rw preempt?                  boolean
        |  +--rw preempt-delay?            uint16
        |  +--rw advertisement-interval?   uint16
        +--ro state
        |  +--ro virtual-router-id?        uint8
        |  +--ro virtual-address*          oc-inet:ip-address
        |  +--ro priority?                 uint8
        |  +--ro preempt?                  boolean
        |  +--ro preempt-delay?            uint16
        |  +--ro advertisement-interval?   uint16
        |  +--ro current-priority?         uint8
        |  +--ro vrrp-state?               vrrp-state-type        (ext)
        |  +--ro counters                                         (ext)
        |     +--ro advertisements-sent?            counter64
        |     +--ro advertisements-received?        counter64
        |     +--ro state-transitions?              counter64
        |     +--ro gratuitous-arp-sent?            counter64     (ipv4 only)
        |     +--ro neighbor-advertisements-sent?   counter64     (ipv6 only)
        +--rw interface-tracking
           +--rw config
           |  +--rw track-interface*      -> /interfaces/interface/name
           |  +--rw priority-decrement?   uint8
           +--ro state
              +--ro track-interface*      -> /interfaces/interface/name
              +--ro priority-decrement?   uint8
```

## 1.1 Requirements

### 1.1.1 Functional Requirements

1. Create, update, replace and delete VRRP groups for IPv4 and IPv6 on routed VLAN and sub-interface addresses.
1. Support `virtual-address`, `priority`, `preempt`, `preempt-delay`, `advertisement-interval` and `interface-tracking` (`track-interface`, `priority-decrement`).
1. Serve `state` with the configured values plus `current-priority`, `vrrp-state` and counters from STATE_DB.

### 1.1.2 Configuration and Management Requirements

GET `/config`, `/state` and `interface-tracking`, whole or down to a single leaf, for one VRRP group or all groups of the interface.

## 1.2 Design Overview

A transformer handles SET, GET and Subscribe for the `vrrp` container. Writes go to CONFIG_DB only, and `frrcfgd` applies them to `vrrpd`. Operational data is read from frr and populated in STATE_DB.

## 1.3 Architecture

```
gNMI Client
        |
  translib + transformer infra
        |
  <routed_vlan|subintf>_<ipv4|ipv6>_vrrp_xfmr
        |-- SET / GET config        --> CONFIG_DB  VRRP | VRRP6
        |-- SET / GET tracking      --> CONFIG_DB  VRRP_TRACK | VRRP6_TRACK
        |-- GET state, counters     --> STATE_DB   VRRP_STATE_TABLE | VRRP6_STATE_TABLE
```

# 2 User Interface

## 2.1 Data Models

| Model | Purpose |
| :---- | :------ |
| `openconfig-if-ip` | Standard OpenConfig VRRP model |
| `openconfig-if-ip-vrrp-ext` | New. Adds `vrrp-state` and `counters` to `vrrp-group/state` for routed VLAN and sub-interface, IPv4 and IPv6 |
| `openconfig-interfaces-annot` | SONiC annotation binding the subtree and transformers |
| `openconfig-interfaces-deviation` | Marks deviations that are not supported |

## 2.2 Database Table and Field Mapping

### 2.2.1 VRRP Group Configuration

**Database Table:** `VRRP` (IPv4), `VRRP6` (IPv6) (CONFIG_DB)
**Key Pattern:** `VRRP|<ifname>|<vrid>`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|----------------------|----------------|----------------|
| `/virtual-router-id` (key) | `VRRP`, `VRRP6` | key, `vid` |
| `/config/virtual-router-id` | `VRRP`, `VRRP6` | `vid` |
| `/config/virtual-address` | `VRRP`, `VRRP6` | `vip@` |
| `/config/priority` | `VRRP`, `VRRP6` | `priority` |
| `/config/preempt` | `VRRP`, `VRRP6` | `preempt` (`enabled`/`disabled`) |
| `/config/preempt-delay` | `VRRP`, `VRRP6` | `preempt_delay` |
| `/config/advertisement-interval` | `VRRP`, `VRRP6` | `adv_interval` (centiseconds to seconds) |

### 2.2.2 Interface Tracking

**Database Table:** `VRRP_TRACK` (IPv4), `VRRP6_TRACK` (IPv6) (CONFIG_DB)
**Key Pattern:** `VRRP_TRACK|<ifname>|<vrid>|<track-ifname>`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|----------------------|----------------|----------------|
| `/interface-tracking/config/track-interface` | `VRRP_TRACK`, `VRRP6_TRACK` | key component `<track-ifname>` |
| `/interface-tracking/config/priority-decrement` | `VRRP_TRACK`, `VRRP6_TRACK` | `priority_decrement` |
| `/interface-tracking/state/*` | `VRRP_TRACK`, `VRRP6_TRACK` | same as config |

### 2.2.3 VRRP Group State

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|----------------------|----------------|----------------|
| `/state/virtual-router-id`, `virtual-address`, `priority`, `preempt`, `preempt-delay`, `advertisement-interval` | `VRRP`, `VRRP6` (CONFIG_DB) |  |
| `/state/current-priority` | `VRRP_STATE_TABLE`, `VRRP6_STATE_TABLE` (STATE_DB) | `effective_priority` |
| `/state/vrrp-state` | `VRRP_STATE_TABLE`, `VRRP6_STATE_TABLE` | `state` |
| `/state/counters/*` | `VRRP_STATE_TABLE`, `VRRP6_STATE_TABLE` |  |

### 2.2.4 Unsupported

| Item | Behavior |
| :--- | :------- |
| `config/accept-mode`, `state/accept-mode` | Not in the schema, GET, SET and DELETE fail |
| `config/virtual-link-local`, `state/virtual-link-local` (IPv6) | Not in the schema, GET, SET and DELETE fail |
| REPLACE of `config/virtual-router-id` | `NotSupported` |

## 2.3 gNMI Support

### 2.3.1 GET

Supported on `config`, `state` and `interface-tracking`, down to a single leaf.

```
gnmic get -p /openconfig-interfaces:interfaces/interface[name=Vlan100]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=50.0.0.1]/vrrp/vrrp-group[virtual-router-id=25]/state
```

### 2.3.2 SET

Supported (update, replace, delete) on `config` and `interface-tracking/config` paths.

```
gnmic set --update-path /openconfig-interfaces:interfaces/interface[name=Vlan100]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=50.0.0.1]/vrrp/vrrp-group[virtual-router-id=25]/config/priority --update-value 120
```

### 2.3.3 DELETE

Supported on a `vrrp-group` and on the leaves below. Deleting a leaf writes the value shown.

| Path | DB change |
| :--- | :-------- |
| `vrrp-group` | Remove `VRRP`/`VRRP6` key and all track keys of the group |
| `/config/priority` | `priority` = `100` |
| `/config/preempt` | `preempt` = `true` |
| `/config/preempt-delay` | `preempt_delay` = `0` |
| `/config/advertisement-interval` | `adv_interval` = `1` |
| `/config/virtual-address` | `vip@` = empty |
| `/interface-tracking/config/priority-decrement` | `priority_decrement` = `0` on all track keys of the group |
| `/interface-tracking/config/track-interface` | Remove all track keys of the group |

# 3 Testing

Tests are added in `interfaces_openconfig_test.go` and cover, for IPv4 and IPv6 on routed VLAN and L3 interfaces:

- GET of `config`, `state`, FSM state, counters and `interface-tracking`
- PATCH of leaves and of the `config` and `interface-tracking/config` containers
- DELETE of leaves to defaults
- `accept-mode` and `virtual-link-local` rejected
- `address[ip]` key validation
- VIP subnet validation
- Interface address removal blocked by a VIP, and allowed when it does not own a VIP
- REPLACE of `virtual-router-id` rejected

# 4 Limitations

- `accept-mode` not supported
- `virtual-link-local` not supported
