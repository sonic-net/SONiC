# OpenConfig support for LACP

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
      * [3.3.4 gNMI Subscription Support](#334-gnmi-subscription-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  * [7 Limitations](#7-limitations)
  * [8 Dependencies](#8-dependencies)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)<br>
[Table 2: Deviations](#table-2-deviations)<br>
[Table 3: Interface config mapping](#table-3-interface-config-mapping)<br>
[Table 4: Interface state mapping](#table-4-interface-state-mapping)<br>
[Table 5: Member state mapping](#table-5-member-state-mapping)<br>
[Table 6: Actor state bits](#table-6-actor-state-bits)<br>
[Table 7: Subscription table mapping](#table-7-subscription-table-mapping)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 11/24/2026  | Varuna (Nokia)        | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration and operational state of LACP on PortChannel interfaces in SONiC.

# Scope
- This document describes the high level design of LACP configuration and LACP operational state of PortChannel interfaces using the `openconfig-lacp` model via REST and gNMI.
- This does not cover the SONiC KLISH CLI.
- This does not cover PortChannel creation, `min-links`, `lag-type`, `lag-speed` or member association, which are handled by the `openconfig-interfaces` / `openconfig-if-aggregate` models ([sonic-net/sonic-mgmt-common#241](https://github.com/sonic-net/sonic-mgmt-common/pull/241)).
- Supported attributes in OpenConfig YANG tree:

```
module: openconfig-lacp
  +--rw lacp
     +--rw interfaces
        +--rw interface* [name]
           +--rw name       -> ../config/name
           +--rw config
           |  +--rw name?               oc-if:base-interface-ref
           |  +--rw interval?           lacp-period-type
           |  +--rw system-id-mac?      oc-yang:mac-address
           |  +--rw fallback?           boolean
           +--ro state
           |  +--ro name?               oc-if:base-interface-ref
           |  +--ro interval?           lacp-period-type
           |  +--ro lacp-mode?          lacp-activity-type
           |  +--ro system-id-mac?      oc-yang:mac-address
           |  +--ro fallback?           boolean
           |  +--ro system-priority?    uint16
           +--rw members
              +--rw member* [interface]
                 +--rw interface    -> ../config/interface
                 +--ro state
                    +--ro interface?               oc-if:base-interface-ref
                    +--ro activity?                lacp-activity-type
                    +--ro timeout?                 lacp-timeout-type
                    +--ro synchronization?         lacp-synchronization-type
                    +--ro aggregatable?            boolean
                    +--ro collecting?              boolean
                    +--ro distributing?            boolean
                    +--ro system-id?               oc-yang:mac-address
                    +--ro oper-key?                uint16
                    +--ro partner-id?              oc-yang:mac-address
                    +--ro partner-key?             uint16
                    +--ro port-num?                uint16
                    +--ro partner-port-num?        uint16
                    +--ro counters
                       +--ro lacp-in-pkts?               oc-yang:counter64
                       +--ro lacp-out-pkts?              oc-yang:counter64
                       +--ro lacp-rx-errors?             oc-yang:counter64
```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST                     | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| LACP                     | Link Aggregation Control Protocol (IEEE 802.1AX) |
| LACPDU                   | LACP Protocol Data Unit |
| LAG                      | Link Aggregation Group; interchangeable with PortChannel |
| teamd / teammgrd         | SONiC LAG daemon and its CONFIG_DB manager |
| tlm_teamd                | teamd telemetry agent that publishes STATE_DB LAG tables |
| CVL                      | Config Validation Library |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for the OpenConfig LACP YANG model (`openconfig-lacp`).
2. Configure/Set, GET and Delete per-PortChannel LACP attributes under `/lacp/interfaces/interface[name]/config`: `interval`, `system-id-mac`, `fallback`.
3. GET per-PortChannel LACP operational state under `/lacp/interfaces/interface[name]/state`.
4. GET per-member LACP state and counters under `/lacp/interfaces/interface[name]/members/member[interface]/state`.
5. Support gNMI subscription: SAMPLE for all paths; ON_CHANGE for `interface/state/system-priority` and `member/state/partner-id`. `interface/state/system-priority` is the read-only operational value reported by teamd (`runner.sys_prio`); only the configurable `system-priority` leaves are removed by the deviation (see [Table 2](#table-2-deviations)).
6. DELETE removes only the fields owned by `openconfig-lacp` and does not remove the PortChannel entry when other fields (e.g. `admin_status`, `mtu`, `min_links`) are present.

### 1.1.2 Configuration and Management Requirements
The LACP configuration can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC configures LACP parameters of PortChannels through the CONFIG_DB `PORTCHANNEL` table (consumed by teammgrd) and reports LACP operational state through STATE_DB `LAG_TABLE` / `LAG_MEMBER_TABLE` (published by tlm_teamd). This feature adds transformer based support for the `openconfig-lacp` model that maps to the existing `PORTCHANNEL` fields `fast_rate`, `fallback` and `system_mac`, and to these STATE_DB tables. The feature is additive; existing transformers are not modified.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities, get, set and subscribe based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

The following files are added or modified in *sonic-mgmt-common*:

| File | Change |
|------|--------|
| `translib/transformer/xfmr_lacp.go` | New: subtree transformers |
| `translib/transformer/lacp_openconfig_test.go` | New: unit tests |
| `models/yang/annotations/openconfig-lacp-annot.yang` | New: transformer annotations |
| `models/yang/extensions/openconfig-lacp-deviation.yang` | New: deviations |
| `config/transformer/models_list` | Modified: register the annotation |

YANG annotations (`openconfig-lacp-annot.yang`):

| OpenConfig path | Annotation |
|-----------------|------------|
| `/lacp/config` | `db-name CONFIG_DB`, `subtree-transformer lacp_config_xfmr` |
| `/lacp/state` | `subtree-transformer lacp_state_xfmr` |
| `/lacp/interfaces` | `subtree-transformer lacp_intfs_xfmr` |
| `/lacp/interfaces/interface` | `db-name CONFIG_DB`, `table-name PORTCHANNEL` |
| `/lacp/interfaces/interface/state` | `db-name STATE_DB`, `table-name LAG_TABLE` |
| `/lacp/interfaces/interface/members/member` | `db-name STATE_DB`, `table-name LAG_MEMBER_TABLE` |

### Table 2: Deviations
| Path | Reason |
|------|--------|
| `/lacp/config/system-priority` | No global LACP system priority in SONiC |
| `/lacp/state/system-priority` | No global LACP system priority in SONiC |
| `/lacp/interfaces/interface/config/system-priority` | No CONFIG_DB `PORTCHANNEL` field in `sonic-portchannel.yang` and not consumed by teammgrd |
| `/lacp/interfaces/interface/config/lacp-mode` | No CONFIG_DB `PORTCHANNEL` field in `sonic-portchannel.yang` and not consumed by teammgrd |
| `/lacp/interfaces/interface/config/fallback-timeout` | No CONFIG_DB `PORTCHANNEL` field in `sonic-portchannel.yang` and not consumed by teammgrd |
| `/lacp/interfaces/interface/state/fallback-timeout` | Not published by tlm_teamd |

Transformer functions (`xfmr_lacp.go`):

| Function | Purpose |
|----------|---------|
| `YangToDb_lacp_config_xfmr`, `DbToYang_lacp_config_xfmr`, `Subscribe_lacp_config_xfmr` | Global `/lacp/config`; no DB mapping |
| `DbToYang_lacp_state_xfmr`, `Subscribe_lacp_state_xfmr` | Global `/lacp/state`; no DB mapping |
| `YangToDb_lacp_intfs_xfmr` | SET / DELETE of per-interface config into CONFIG_DB `PORTCHANNEL` |
| `DbToYang_lacp_intfs_xfmr` | GET of interface config, state and members |
| `Subscribe_lacp_intfs_xfmr` | Table/key/field mapping for subscribe and parent-existence checks |

SET semantics:
- Leaf-level SET (request URI ends with the leaf name): only that field is written.
- Container-level UPDATE: only leaves present in the payload are written.
- The target must be a PortChannel interface name; otherwise an error is returned.

DELETE semantics: for each PortChannel in the request, only the fields owned by this model (`system_mac`, `fast_rate`, `fallback`) are removed. If the entry contains only owned fields, the whole key is deleted; if it contains none, it is left untouched.

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition. The existing `PORTCHANNEL` fields `fast_rate`, `system_mac` and `fallback` are used.
### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition. The existing `LAG_TABLE` and `LAG_MEMBER_TABLE` entries published by tlm_teamd are used.
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
- Base model: `openconfig-lacp.yang` version 2.2.0 (already present in *sonic-mgmt-common*; includes `fallback` and `fallback-timeout`).
- Annotation: `openconfig-lacp-annot.yang`.
- Deviation: `openconfig-lacp-deviation.yang`.

### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at leaf level as well.
```
curl -X GET -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1" -H "accept: application/yang-data+json"
```
#### 3.3.2.2 SET
Supported at leaf level as well.
```
curl -X PUT -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1/config" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-lacp:config\":{\"name\":\"PortChannel1\",\"interval\":\"FAST\"}}"
```
#### 3.3.2.3 PATCH
Supported at leaf level as well.
Set LACP fast rate and system MAC:
```
curl -X PATCH -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1/config" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-lacp:config\":{\"name\":\"PortChannel1\",\"interval\":\"FAST\",\"system-id-mac\":\"00:11:22:33:44:55\"}}"
```
Result in CONFIG_DB: `PORTCHANNEL|PortChannel1  fast_rate=true system_mac=00:11:22:33:44:55`.

Enable fallback:
```
curl -X PATCH -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1/config/fallback" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-lacp:fallback\":true}"
```
Set the LACP system MAC:
```
curl -X PATCH -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1/config/system-id-mac" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-lacp:system-id-mac\":\"00:11:22:33:44:55\"}"
```
#### 3.3.2.4 DELETE
Supported at leaf level as well.
```
curl -X DELETE -k "https://<switch-ip>/restconf/data/openconfig-lacp:lacp/interfaces/interface=PortChannel1/config" -H "accept: */*"
```

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
Supported
```
gnmic -a <switch-ip>:<port> -u <user> -p <password> -e json_ietf get --path "/openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/members/member[interface=Ethernet0]/state"
```
#### 3.3.3.2 SET
Supported
#### 3.3.3.3 DELETE
Supported

### 3.3.4 gNMI Subscription Support
#### 3.3.4.1 On Change
Supported for `interface/state/system-priority` and `member/state/partner-id`.
```
gnmic -a <switch-ip>:<port> -u <user> -p <password> -e json_ietf subscribe --mode stream --stream-mode on_change --path "/openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/members/member[interface=Ethernet0]/state/partner-id"
```
#### 3.3.4.2 SAMPLE
Supported for all paths.
```
gnmic -a <switch-ip>:<port> -u <user> -p <password> -e json_ietf subscribe --mode stream --stream-mode sample --sample-interval 20s --path "/openconfig-lacp:lacp/interfaces/interface[name=PortChannel1]/state"
```

### Table 7: Subscription table mapping
| Target | Tables |
|--------|--------|
| `/lacp/interfaces`, `/lacp/interfaces/interface` | CONFIG_DB `PORTCHANNEL`, STATE_DB `LAG_TABLE`, `LAG_MEMBER_TABLE` |
| `.../interface/config[/...]` | CONFIG_DB `PORTCHANNEL` |
| `.../interface/state[/...]` | STATE_DB `LAG_TABLE` |
| `.../members[/...]` | STATE_DB `LAG_MEMBER_TABLE` |

For parent-existence checks only CONFIG_DB `PORTCHANNEL|<name>` is required, so config requests on a PortChannel with no members or that is operationally down succeed.

# 4 Flow Diagrams
```
 gNMI / REST client
        |
        v
 +------------------+       openconfig-lacp.yang (+ annotation, deviation)
 |     translib     |
 |   transformer    |
 |   xfmr_lacp.go   |
 +------------------+
     |          ^
 SET |          | GET / Subscribe
     v          |
 CONFIG_DB PORTCHANNEL       STATE_DB LAG_TABLE, LAG_MEMBER_TABLE
     |                                ^
     v                                |
  teammgrd  --->  teamd  --->  tlm_teamd
```

Mapping attributes between OpenConfig YANG and SONiC DB:

### Table 3: Interface config mapping
CONFIG_DB `PORTCHANNEL|<name>`:

|   OpenConfig YANG       |    sonic-portchannel YANG    | Encoding |
|-------------------------|------------------------------|----------|
|   interval              |      fast_rate               | `FAST` = `true`, `SLOW` = `false` |
|   system-id-mac         |      system_mac              | MAC address |
|   fallback              |      fallback                | `true` / `false` |
`system-id-mac` uses the same `system_mac` field as the CLI (`config interface sys-mac add|remove <PortChannel> <mac>`). teammgrd applies it as the LACP actor system MAC of the PortChannel.

### Table 4: Interface state mapping
STATE_DB `LAG_TABLE|<name>`:

|   OpenConfig YANG       |    STATE_DB field              |
|-------------------------|--------------------------------|
|   interval              |      runner.fast_rate          |
|   lacp-mode             |      runner.active             |
|   system-id-mac         |      team_device.ifinfo.dev_addr |
|   system-priority       |      runner.sys_prio           |
|   fallback              |      runner.fallback           |
### Table 5: Member state mapping
STATE_DB `LAG_MEMBER_TABLE|<portchannel>|<member>`:

|   OpenConfig YANG       |    STATE_DB field                         |
|-------------------------|-------------------------------------------|
|   interface             |      key component                        |
|   system-id             |      runner.actor_lacpdu_info.system      |
|   oper-key              |      runner.actor_lacpdu_info.key         |
|   port-num              |      runner.actor_lacpdu_info.port        |
|   partner-id            |      runner.partner_lacpdu_info.system    |
|   partner-key           |      runner.partner_lacpdu_info.key       |
|   partner-port-num      |      runner.partner_lacpdu_info.port      |
|   counters/lacp-in-pkts |      runner.statistics.lacpdu_rx_stats    |
|   counters/lacp-out-pkts |     runner.statistics.lacpdu_tx_stats    |
|   counters/lacp-rx-errors |    runner.statistics.lacpdu_illegal_pkts |

### Table 6: Actor state bits
`activity`, `timeout`, `aggregatable`, `synchronization`, `collecting` and `distributing` are decoded from `runner.actor_lacpdu_info.state` using the IEEE 802.1AX Actor_State bit definitions:

| Bit | Field | Bit set | Bit clear |
|-----|-------|---------|-----------|
| 0 | activity | `ACTIVE` | `PASSIVE` |
| 1 | timeout | `SHORT` | `LONG` |
| 2 | aggregatable | `true` | `false` |
| 3 | synchronization | `IN_SYNC` | `OUT_SYNC` |
| 4 | collecting | `true` | `false` |
| 5 | distributing | `true` | `false` |

# 5 Error Handling
Invalid configurations will report an error.

| Condition | Result |
|-----------|--------|
| Interface name is not a PortChannel | Invalid interface error |
| `PORTCHANNEL|<name>` does not exist | Resource not found |
| SET of `interface/config/system-priority`, `interface/config/lacp-mode` or `interface/config/fallback-timeout` | Rejected (not supported) |
| Member not present in `LAG_MEMBER_TABLE` | Resource not found |

# 6 Unit Test Cases
## 6.1 Functional Test Cases
1. Verify GET of `config/interval` FAST / SLOW from `fast_rate`.
2. Verify PATCH and GET of `config/fallback`; PATCH writes only `fallback`.
3. Verify GET of member state `aggregatable`, `collecting`, `distributing`, `oper-key`, `partner-key`, `system-id`, `partner-id`, and `timeout` LONG / SHORT from actor state bit 1.
4. Verify PATCH, GET and DELETE of LACP attributes via REST and gNMI on a device; verify with `teamdctl <PortChannel> state`.
5. Verify gNMI ON_CHANGE subscription to `member/state/partner-id` and SAMPLE subscription to `interface/state`.

## 6.2 Negative Test Cases
1. Verify SET of `interface/config/system-priority` returns an error.
2. Verify SET of `interface/config/lacp-mode` returns an error and does not write `active`.
3. Verify SET of `interface/config/fallback-timeout` returns an error and does not write `fallback_timeout`.
4. Verify GET on a non-existent PortChannel returns a "Resource Not Found" error.
5. Verify DELETE of `config` removes only LACP fields and keeps the PortChannel entry when other fields are present.

# 7 Limitations
- Global `/lacp/config|state/system-priority` and per-interface `interface/config/system-priority` are not supported; `interface/state/system-priority` is read-only from teamd.
- Per-interface `interface/config/lacp-mode` is not supported; `interface/state/lacp-mode` is read-only from teamd (`runner.active`).
- Per-interface `interface/config/fallback-timeout` and `interface/state/fallback-timeout` are not supported.
- Setting `system-id-mac` through OpenConfig only writes CONFIG_DB `system_mac`. For PortChannels that are EVPN Type-3 (MAC-based) Ethernet Segments, the FRR `evpn mh es-sys-mac` configuration done by the CLI is not performed; use the CLI for that case.
- `interface/state` and `members` are only populated when teamd has published `LAG_TABLE` / `LAG_MEMBER_TABLE` entries for the PortChannel.

# 8 Dependencies
| Repository | Change | Why | Status |
|------------|--------|-----|--------|
| sonic-buildimage (libteam) | teamd per-member LACP statistics `statistics.lacpdu_rx_stats`, `lacpdu_tx_stats`, `lacpdu_illegal_pkts` | Source of member counters | [sonic-buildimage#23380](https://github.com/sonic-net/sonic-buildimage/pull/23380) |
| sonic-swss (tlm_teamd) | Publish `runner.statistics.*` to `LAG_MEMBER_TABLE` | Required for member counters | To be raised |
