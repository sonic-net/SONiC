# OpenConfig Model Support for SONiC Syslog TLS

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
 * [4.1 Supported Syslog TLS Leaves](#41-supported-syslog-tls-leaves)
 * [4.2 Existing Remote-Server Leaves Unchanged](#42-existing-remote-server-leaves-unchanged)
 * [4.3 Unsupported](#43-unsupported)
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
| 0.1 | 11/16/2026 | Malavika Unnikrishnan | Initial UMF mapping for OpenConfig syslog TLS |

# About this Manual
This document is the UMF increment to [OpenConfig_System.md](OpenConfig_System.md) logging. It maps OpenConfig syslog TLS leaves on a remote server onto CONFIG_DB / STATE_DB `SYSLOG_SERVER`.

It does not describe native rsyslog, Certz, or CLI.

OpenConfig xpath root:

```
/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]
```

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture |
| OpenConfig_System.md | Existing OpenConfig system / logging mapping |

# Scope
- **In scope:** REST and gNMI Get, Set, Delete, and Subscribe for `transport-security`, `tls-profile-id`, and operational `pins-oper-transport-security` on an existing remote-server list entry.
- **Out of scope:** host/port/VRF/selector mapping already in OpenConfig_System.md; gNSI Certz profile install; native rsyslog renderer; `SYSLOG_SSL_PROFILE` (removed from the native schema).
- Supported attributes added to the OpenConfig logging tree:

```
module: openconfig-system
  +--rw system
     +--rw logging
        +--rw remote-servers
           +--rw remote-server* [host]
              +--rw config
              |  +--rw transport-security?   boolean
              |  +--rw tls-profile-id?       string
              +--ro state
                 +--ro transport-security?   boolean
                 +--ro tls-profile-id?       string
                 +--ro google-pins-system:pins-oper-transport-security?   enumeration
```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term** | **Definition** |
|----------|----------------|
| UMF | Unified Management Framework (translib + transformers) |
| gNMI | gRPC Network Management Interface |

# 1 Feature Overview
## 1.1 Requirements
1. Write OpenConfig `transport-security` to `SYSLOG_SERVER.transport_security` as requested intent.
2. Write OpenConfig `tls-profile-id` to `SYSLOG_SERVER.tls_profile_id`.
3. Do **not** force `protocol=tls` when `transport-security=true`. Native TLS also requires `tls_profile_id` and `tls_permitted_peers`; OpenConfig has no permitted-peers leaf.
4. `transport-security=false` pins `protocol=udp`.
5. Report applied outcome on `google-pins-system:pins-oper-transport-security` from STATE_DB.
6. Do not model `SYSLOG_SSL_PROFILE` over OpenConfig.

## 1.2 Design Overview
Field transformers on the existing `SYSLOG_SERVER` remote-server list. No new Redis table. Code is in `sonic-mgmt-common` (`xfmr_system_logging_tls.go` plus annotations in `openconfig-system-annotation.json`).

# 2 Functionality
A controller sets TLS intent on a remote syslog server. GET of `transport-security` returns the requested flag. GET of `pins-oper-transport-security` returns whether rsyslog actually applied TLS.

# 3 Design
## 3.1 Overview
Same UMF path as other `openconfig-system` logging leaves.

### 3.1.1 UMF Translation
| Artifact | Role |
|----------|------|
| `openconfig-system-annotation.json` | field bindings on remote-server config/state |
| `openconfig-system-logging.yang` | `transport-security`, `tls-profile-id` |
| `google-pins-system.yang` | `pins-oper-transport-security` state extension |
| `xfmr_system_logging_tls.go` | YangToDb / DbToYang for the TLS flag and oper leaf |

### 3.1.2 Mapping Rules and Exceptions
| Rule | Detail |
|------|--------|
| Intent vs protocol | Writing `transport-security=true` records `transport_security=true` only. It does not set `protocol=tls`. |
| Disable | Writing `transport-security=false` sets `transport_security=false` and `protocol=udp`. |
| GET of intent | Prefers `transport_security`; falls back to `protocol=tls` if the alias is absent. |
| Oper state | `pins-oper-transport-security` is STATE_DB only (`applied_transport_security` / `failure_reason`). Values: `NONE`, `ENABLED`, `NO_CERTIFICATE`, `INVALID_CERTIFICATE`. Other native failures map to `NONE` (TLS is not active). |
| Profiles | Certz profiles are not OpenConfig ssl-profiles. UMF stores `tls_profile_id` as a string; it does not install certificates. |
| Permitted peers | No OpenConfig leaf. UMF does not write `tls_permitted_peers`. |

## 3.2 DB Changes
No new tables. UMF reads/writes `SYSLOG_SERVER` fields `transport_security`, `tls_profile_id`, and (on disable) `protocol`. Oper GET reads STATE_DB `SYSLOG_SERVER` `applied_transport_security` and `failure_reason`.

# 4 OpenConfig to SONiC Mapping Table

## 4.1 Supported Syslog TLS Leaves

| OpenConfig YANG Node | Extension | DB Name | Table:Field | Notes |
|----------------------|-----------|---------|-------------|-------|
| `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` | | CONFIG_DB | `SYSLOG_SERVER.transport_security` | requested intent; `sys_logging_transport_security_xfmr` |
| `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/state/transport-security` | | CONFIG_DB | `SYSLOG_SERVER.transport_security` | same xfmr; fallback to `protocol=tls` |
| `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/tls-profile-id` | | CONFIG_DB | `SYSLOG_SERVER.tls_profile_id` | plain field annotation |
| `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/state/tls-profile-id` | | CONFIG_DB | `SYSLOG_SERVER.tls_profile_id` | |
| `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/state/google-pins-system:pins-oper-transport-security` | google-pins-system | STATE_DB | `SYSLOG_SERVER.applied_transport_security` (+ `failure_reason`) | `sys_logging_pins_oper_transport_security_xfmr` |

## 4.2 Existing Remote-Server Leaves Unchanged

Host, source-address, network-instance, remote-port, and selectors remain as in OpenConfig_System.md (`server_address`, `source`, `vrf`, `port`, facility/severity).

## 4.3 Unsupported
| Item | Result |
|------|--------|
| OpenConfig ssl-profile / `SYSLOG_SSL_PROFILE` | not modeled |
| OpenConfig permitted-peers | no leaf; UMF does not write `tls_permitted_peers` |
| Forcing `protocol=tls` from `transport-security=true` | not done |

# 5 User Interface
## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| openconfig-system-logging.yang | sonic-mgmt-common | TLS config leaves |
| google-pins-system.yang | sonic-mgmt-common | oper transport-security |
| openconfig-system-annotation.json | sonic-mgmt-common | UMF bindings |

## 5.2 REST API Support
PATCH intent:

```
PATCH /restconf/data/openconfig-system:system/logging/remote-servers/remote-server=<host>/config/transport-security
{"openconfig-system:transport-security": true}
```

Result: `SYSLOG_SERVER|<host>` field `transport_security=true`. `protocol` is unchanged unless the value is `false`.

GET oper:

```
GET /restconf/data/openconfig-system:system/logging/remote-servers/remote-server=<host>/state/google-pins-system:pins-oper-transport-security
```

## 5.3 gNMI Support
Get, Set, Delete, and Subscribe on the leaves in [Section 4.1](#41-supported-syslog-tls-leaves).

# 6 Error Handling
| Condition | Result |
|-----------|--------|
| SET of `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` with a non-boolean | transformer error |
| DELETE `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` | clears the alias field |
| Oper GET before rsyslog has written STATE_DB | leaf omitted |

# 7 Unit Test Cases
## 7.1 Functional
1. PATCH `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` = `true` writes `transport_security=true` and does not set `protocol=tls`.
2. PATCH `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` = `false` writes `transport_security=false` and `protocol=udp`.
3. PATCH `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/tls-profile-id` writes `SYSLOG_SERVER.tls_profile_id`.
4. GET `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/config/transport-security` matches the alias (or `protocol=tls` fallback).
5. GET `/openconfig-system:system/logging/remote-servers/remote-server[host=<host>]/state/google-pins-system:pins-oper-transport-security` maps STATE_DB applied / failure_reason.

## 7.2 Negative
1. Non-boolean `transport-security` is rejected.
2. UMF does not create `SYSLOG_SSL_PROFILE` rows.
