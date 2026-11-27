# OpenConfig support for VLAN

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
- [2 Functionality](#2-functionality)
  - [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
- [3 Design](#3-design)
  - [3.1 Overview](#31-overview)
  - [3.2 DB Changes](#32-db-changes)
  - [3.3 User Interface](#33-user-interface)
- [4 Testing](#4-testing)
- [5 References](#5-references)

# List of Tables

- [Table 1: Abbreviations](#table-1-abbreviations)

# Revision

| Rev |    Date    |  Author     | Change Description |
|:---:|:----------:|:-----------:|--------------------|
| 0.1 | 11/24/2026 | Sriniketh J | Initial version    |

# About this Manual

This document provides the high level design for OpenConfig support of VLANs in SONiC. It covers the `openconfig-vlan` model: VLAN configuration, operational state and VLAN membership.

# Scope

This document covers the following under `/openconfig-vlan:vlans`:

- VLAN creation, modification and deletion (`config`)
- VLAN operational state (`state`)
- VLAN member interfaces, read-only (`members`)
- gNMI Get, Set, Delete and Subscribe

The supported part of the `openconfig-vlan` tree is:

```
module: openconfig-vlan
  +--rw vlans
     +--rw vlan* [vlan-id]
        +--rw vlan-id     -> ../config/vlan-id
        +--rw config
        |  +--rw vlan-id?   uint16
        |  +--rw name?      string
        |  +--rw status?    enumeration
        +--ro state
        |  +--ro vlan-id?   uint16
        |  +--ro name?      string
        |  +--ro status?    enumeration
        +--ro members
           +--ro member* []
              +--ro state
                 +--ro interface?   string
```

Out of scope:

- SONiC doesn't have support for `native-vlan`

# Definition/Abbreviation

### Table 1: Abbreviations

| **Term**  | **Definition** |
|-----------|----------------|
| VLAN      | Virtual Local Area Network |
| YANG      | Yet Another Next Generation, a data modeling language |
| gNMI      | gRPC Network Management Interface |
| OC        | OpenConfig |
| xfmr      | Transformer, the translib callback mapping YANG paths to DB tables and back |
| CONFIG_DB | SONiC configuration database |
| APPL_DB   | SONiC application database, written by vlanmgrd |

# 1 Feature Overview

SONiC keeps VLAN intent in CONFIG_DB (`VLAN|VlanN`) and the programmed view in APPL_DB (`VLAN_TABLE:VlanN`, `VLAN_MEMBER_TABLE:VlanN:<ifname>`). This feature exposes them through the OpenConfig `openconfig-vlan` model.

## 1.1 Requirements

### 1.1.1 Functional Requirements

1. Create, update, replace and delete VLANs under `/openconfig-vlan:vlans`, for one VLAN or the whole list.
2. Accept VLAN ids 2-4094 only. Reject VLAN 1 and ids above 4094.
3. Map `config/status` (`ACTIVE`, `SUSPENDED`) to CONFIG_DB `admin_status` (`up`, `down`).
4. Serve `state` and `members` from APPL_DB so they reflect what is programmed.
5. Block deletion of a VLAN if it has members.
6. Reject SET on `state` and `members`.

### 1.1.2 Configuration and Management Requirements

1. GET `config`, `state` and `members`, whole or down to a single leaf, for one VLAN or all.
2. gNMI ON_CHANGE subscribe for `config`, `state` and `members`.
3. Leave an existing VLAN's `admin_status` unchanged when an unrelated leaf is updated.

## 1.2 Design Overview

### 1.2.1 Basic Approach

A single subtree transformer, `oc_vlans_xfmr`, is bound to `/openconfig-vlan:vlans` and implements SET, GET and Subscribe. Writes go to CONFIG_DB only. `vlanmgrd` reacts as it does for CLI-created VLANs and populates APPL_DB. The transformer never writes to APPL_DB.

### 1.2.2 Container

No new container or daemon. The transformer runs in the existing management container.

# 2 Functionality

## 2.1 Target Deployment Use Cases

1. A gNMI client creates, suspends and deletes VLANs.
2. A monitoring system reads VLAN state and membership, and subscribes to changes.
3. VLANs created through the CLI are visible through OpenConfig, and the reverse.

# 3 Design

## 3.1 Overview

```
gNMI Client
        |
  translib + transformer infra
        |
  oc_vlans_xfmr (subtree)
        |-- SET / GET config  --> CONFIG_DB  VLAN
        |-- GET state         --> APPL_DB    VLAN_TABLE
        |-- GET members       --> APPL_DB    VLAN_MEMBER_TABLE
        |-- delete            --> CONFIG_DB  VLAN_MEMBER
```

Behavior rules:

| Rule | Behavior |
| :--- | :------- |
| VLAN name | Always `Vlan<id>`. `config/name`, if given, must match. It is not stored separately |
| VLAN id | `config/vlan-id` must equal the list key. |
| Status | `ACTIVE`=`up`, `SUSPENDED`=`down`. On read, any value other than `down` (case-insensitive) is `ACTIVE`. |
| `admin_status` on update | Written when the VLAN is new, on REPLACE, or when status is in the payload or is the target leaf. Otherwise an existing value is preserved |
| Delete of a VLAN | Fails if CONFIG_DB `VLAN_MEMBER` has any `Vlan<id>\|*` key. Whole-tree delete is all-or-nothing |
| Delete of `config/status` | Resets to default by writing `admin_status=up` |
| GET existence | CONFIG_DB `VLAN` decides which VLANs exist. Keys not parsing as `Vlan<number>` are ignored |
| GET of state/members without an APPL_DB entry | Mixed request (for example whole VLAN): `config` returned, `state` and `members` omitted. Targeted `state` or `members` request: VLAN skipped, or `NotFound` if a specific VLAN was requested |

## 3.2 DB Changes

### 3.2.1 CONFIG DB

No schema change. The existing `VLAN` table is written. The `VLAN_MEMBER` table is read for the delete guard.

### 3.2.2 APP DB

No schema change. `VLAN_TABLE` and `VLAN_MEMBER_TABLE` are read only.

### 3.2.3 STATE DB

No changes.

### 3.2.4 ASIC DB

No changes.

### 3.2.5 COUNTER DB

No changes.

## 3.3 User Interface

### 3.3.1 Data Models

| Model | Purpose |
| :---- | :------ |
| `openconfig-vlan` | Standard OpenConfig VLAN model |
| `openconfig-vlan-annot` | SONiC annotation binding the subtree transformer |

### 3.3.2 Database Table and Field Mapping

All paths are under `/openconfig-vlan:vlans/vlan[vlan-id=<id>]`.

#### 3.3.2.1 VLAN Configuration

**Database Table:** `VLAN` (CONFIG_DB)
**Key Pattern:** `VLAN|Vlan<id>`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|----------------------|----------------|----------------|
| `/vlan-id` (key) | `VLAN` | `vlanid` |
| `/config/vlan-id` | `VLAN` | `vlanid` |
| `/config/name` | | derived (`Vlan<id>`) |
| `/config/status` | `VLAN` | `admin_status` (`ACTIVE`=`up`, `SUSPENDED`=`down`) |

#### 3.3.2.2 VLAN State

**Database Table:** `VLAN_TABLE` (APPL_DB)
**Key Pattern:** `VLAN_TABLE:Vlan<id>`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field |
|----------------------|----------------|----------------|
| `/state/vlan-id` | | derived from the CONFIG_DB `VLAN` entry |
| `/state/name` | | derived (`Vlan<id>`) |
| `/state/status` | `VLAN_TABLE` | `admin_status` |

#### 3.3.2.3 VLAN Members

**Database Table:** `VLAN_MEMBER_TABLE` (APPL_DB)
**Key Pattern:** `VLAN_MEMBER_TABLE:Vlan<id>:<ifname>`

| OpenConfig YANG Path | SONiC DB Table |
|----------------------|----------------|
| `/members/member[interface]/state/interface` | `VLAN_MEMBER_TABLE` |

#### 3.3.2.4 Unsupported

| Item | Behavior |
| :--- | :------- |
| SET on `state` or `members` | `NotSupported` |
| DELETE of `config/vlan-id` or `config/name` | `NotSupported` |
| VLAN membership configuration | Not in this tree |
| VLAN id 1 and ids above 4094 | Rejected, narrower than the YANG range to match SONiC |

### 3.3.3 gNMI Support

#### 3.3.3.1 GET

Supported on all paths in 3.3.2.

```
gnmic get -p /openconfig-vlan:vlans/vlan[vlan-id=10]/state
```

#### 3.3.3.2 SET

Supported (update, replace, delete) on `config` paths only.

```
gnmic set --update-path /openconfig-vlan:vlans/vlan[vlan-id=10]/config/status --update-value SUSPENDED
```

#### 3.3.3.3 DELETE

Supported on a VLAN, on the whole `vlans` container and on `config/status` (resets to `ACTIVE`). A VLAN that has members cannot be deleted.

### 3.3.4 gNMI Subscription Support

#### 3.3.4.1 On Change

Supported on `config`, `state` and `members`.

| Requested | DB        | Table               | Key                                      | Field                    |
| :-------- | :-------- | :------------------ | :--------------------------------------- | :----------------------- |
| config    | CONFIG_DB | `VLAN`              | `Vlan<id>` or `*`                        | `admin_status`→`status`  |
| state     | APPL_DB   | `VLAN_TABLE`        | `Vlan<id>` or `*`                        | `admin_status`→`status`  |
| members   | APPL_DB   | `VLAN_MEMBER_TABLE` | `Vlan<id>:*` or `*`, two key components  |                          |

#### 3.3.4.2 SAMPLE

Not supported.

#### 3.3.4.3 Target Defined

Not supported. ON_CHANGE only.

### 3.3.5 Error Handling

| Condition | Error |
| :-------- | :---- |
| VLAN id outside 2-4094 | `InvalidArgs` |
| `config/vlan-id` differs from key, or `config/name` is not `Vlan<id>` | `InvalidArgs` |
| Delete of a VLAN that has members | `InvalidArgs`: remove all members first |
| DELETE of `config/status` without a VLAN id | `InvalidArgs` |
| SET on `state` or `members`, DELETE of `config/vlan-id` or `config/name` | `NotSupported` |
| GET of a VLAN that does not exist, or has no APPL_DB entry for a `state` or `members` request | `NotFound` |
| CONFIG_DB or APPL_DB handle unavailable | `InternalError` |

# 4 Testing

Tests are added in `xfmr_vlan_test.go`.


# 5 References

- [OpenConfig VLAN YANG model](https://github.com/openconfig/public/blob/master/release/models/vlan/openconfig-vlan.yang)
- [OpenConfig gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
