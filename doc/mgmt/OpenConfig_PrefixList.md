# OpenConfig Support for Prefix List

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
        * [3.3.1.1 Extension leaves (SONiC)](#3311-extension-leaves-sonic)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
  * [Table 1: Abbreviations](#table-1-abbreviations)
  * [Table 2: CONFIG_DB PREFIX / PREFIX_SET Mapping](#table-2-config_db-prefix--prefix_set-mapping)
  * [Table 3: OpenConfig to SONiC Mapping Table](#table-3-openconfig-to-sonic-mapping-table)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 07/22/2026  | Soumya Gargari, Anukul Verma | Initial version |

# About this Manual
This document provides general information about the OpenConfig configuration of prefix lists (defined prefix sets) in SONiC.

# Scope
- This document describes the high level design of prefix list configuration using OpenConfig models via REST and gNMI.
- This does not cover the SONiC KLISH CLI or legacy SONiC YANG-only configuration paths.
- Configuration is supported under:
  `/routing-policy/defined-sets/prefix-sets`
- Prefix sets and entries are mapped to the existing CONFIG_DB `PREFIX_SET` and `PREFIX` tables; no new DB schema is introduced.
- **`sequence-number` is mandatory** for every prefix entry on create, update, and replace. Requests without a sequence number are rejected. The SONiC native model defines `PREFIX_NOSEQ_LIST` for entries without explicit sequence numbers; that list is **not** exposed or populated through this OpenConfig transformer.
- Supported attributes in OpenConfig YANG tree:

<pre>
module: openconfig-routing-policy
  +--rw routing-policy
     +--rw defined-sets
        +--rw prefix-sets
           +--rw prefix-set* [name]
              +--rw name        -> ../config/name
              +--rw config
              |  +--rw name?                    string
              |  +--rw mode?                    enumeration (IPV4 | IPV6)
              |  +--rw oc-rp-ext:description?   string
              +--ro state
              |  +--ro name?                    string
              |  +--ro mode?                    enumeration
              |  +--ro oc-rp-ext:description?   string
              +--rw prefixes
                 +--rw prefix* [ip-prefix masklength-range]
                    +--rw ip-prefix           -> ../config/ip-prefix
                    +--rw masklength-range    -> ../config/masklength-range
                    +--rw config
                    |  +--rw ip-prefix                      oc-inet:ip-prefix
                    |  +--rw masklength-range?              string
                    |  +--rw oc-rp-ext:sequence-number?     uint32
                    |  +--rw oc-rp-ext:action?              enumeration (PERMIT | DENY)
                    +--ro state
                       +--ro ip-prefix                      oc-inet:ip-prefix
                       +--ro masklength-range?              string
                       +--ro oc-rp-ext:sequence-number?     uint32
                       +--ro oc-rp-ext:action?              enumeration
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format |
| REST                     | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface |
| PERMIT / DENY            | Prefix list match actions mapped to route filter permit or deny |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide OpenConfig YANG support for prefix sets and prefix entries.
2. Support create, read, update, and delete of prefix sets (`IPV4` / `IPV6` mode) and prefix entries via REST and gNMI.
3. Support PERMIT and DENY actions on prefix entries.
4. Enforce sequence-number ordering semantics via CONFIG_DB keys and cross-entry validation.
5. Normalize IPv4/IPv6 prefixes to canonical form on write; reject host-bit prefixes.

### 1.1.2 Configuration and Management Requirements
Prefix list configuration is done via REST and gNMI. Invalid configurations return an error. No new management methods are introduced beyond the Management Framework.

### 1.1.3 Scalability Requirements
Prefix list scale follows the existing CONFIG_DB `PREFIX` / `PREFIX_SET` schema and platform limits for the number of sets and entries per set.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC supports prefix lists through native CONFIG_DB and FRR. This feature adds OpenConfig `routing-policy/defined-sets/prefix-sets` support using a transformer-based implementation in *sonic-mgmt-common*.

### 1.2.2 Container
The feature is delivered in the *Management Framework* container (REST server and gNMI in *sonic-mgmt-common*).

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST clients performing GET, PUT, PATCH, POST, and DELETE on supported prefix-set YANG paths.
2. gNMI clients using get, set, and delete on the same OpenConfig paths.

# 3 Design
## 3.1 Overview
This HLD is aligned with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition. OpenConfig prefix sets map to existing `PREFIX_SET` and `PREFIX` tables.

#### Table 2: CONFIG_DB PREFIX / PREFIX_SET Mapping
| CONFIG_DB item | Value / format |
|----------------|----------------|
| Table `PREFIX_SET` | One row per prefix set name |
| Key `PREFIX_SET` | `{set-name}` e.g. `PrefixSet_1` |
| Field `mode` | `IPv4` or `IPv6` (from OpenConfig `IPV4` / `IPV6`) |
| Field `description` | Free-text description (from OpenConfig prefix-set `description`) |
| Table `PREFIX` | One row per prefix entry |
| Key `PREFIX` | `{set-name}\|{sequence-number}\|{canonical-ip-prefix}\|{masklength-range}` e.g. `PrefixSet_1\|10\|2001:db8::/32\|32..64` |
| Field `action` | `permit` or `deny` (from OpenConfig `PERMIT` / `DENY`) |
| Field `mode` | `IPv4` or `IPv6` (aligned with parent prefix set) |

Example:

```
PREFIX_SET|PrefixSet_1
  mode:        IPv6
  description: Test Prefix Set 1

PREFIX|PrefixSet_1|10|2001:db8::/32|32..64
  action: permit
  mode:   IPv6
```

The `ip-prefix` portion of the `PREFIX` key is always the **canonical** normalized address. OpenConfig `mode` uses `IPV4`/`IPV6`; CONFIG_DB stores `IPv4`/`IPv6`.

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
- openconfig-routing-policy.yang
- openconfig-routing-policy-ext.yang (SONiC; see [§3.3.1.1](#3311-extension-leaves-sonic))
- sonic-routing-policy-sets.yang

#### 3.3.1.1 Extension leaves (SONiC)
In SONiC, prefix-set `description` and prefix entry `sequence-number` and `action` are provided via **openconfig-routing-policy-ext.yang** (YANG prefix **`oc-rp-ext`**) today; the same leaves are proposed for the base **openconfig-routing-policy** model in the OpenConfig community repository.

<pre>
augment /routing-policy/defined-sets/prefix-sets/prefix-set/config
  - description
augment /routing-policy/defined-sets/prefix-sets/prefix-set/state
  - description
augment /routing-policy/defined-sets/prefix-sets/prefix-set/prefixes/prefix/config
  - sequence-number
  - action
augment /routing-policy/defined-sets/prefix-sets/prefix-set/prefixes/prefix/state
  - sequence-number
  - action
</pre>

### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at container, list, and leaf levels.

Sample GET on a prefix set with one IPv6 entry:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1" -H "accept: application/yang-data+json"
```

Sample GET on prefix entry state:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1/prefixes/prefix=2001:db8::/32,32..64/state" -H "accept: application/yang-data+json"
```

GET accepts either the canonical or equivalent non-canonical URI spelling of `ip-prefix` when it normalizes to the same CONFIG_DB key (e.g. `0::/64` and `::/64`).

#### 3.3.2.2 PUT
Supported. PUT on a prefix set replaces the targeted resource per RESTCONF rules.

Sample PUT to change prefix-set mode (IPv6):
```
curl -X PUT -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1/config/mode" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:mode\":\"IPV6\"}"
```

#### 3.3.2.3 POST
POST creates prefix sets or merges prefix entries into an existing set.

Sample POST to create an IPv4 prefix set:
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:prefix-set\":[{\"name\":\"PrefixSet_1\",\"config\":{\"name\":\"PrefixSet_1\",\"mode\":\"IPV4\",\"openconfig-routing-policy-ext:description\":\"Test Prefix Set 1\"}}]}"
```

Sample POST to create a prefix set with an IPv6 prefix entry (sequence number and action required):
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:prefix-set\":[{\"name\":\"PrefixSet_1\",\"config\":{\"name\":\"PrefixSet_1\",\"mode\":\"IPV6\"},\"prefixes\":{\"prefix\":[{\"ip-prefix\":\"2001:db8::/32\",\"masklength-range\":\"32..64\",\"config\":{\"ip-prefix\":\"2001:db8::/32\",\"masklength-range\":\"32..64\",\"openconfig-routing-policy-ext:sequence-number\":10,\"openconfig-routing-policy-ext:action\":\"PERMIT\"}}]}}]}"
```

#### 3.3.2.4 PATCH
Supported at leaf level (e.g. prefix `action`).

Sample PATCH to update action on an entry:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1/prefixes/prefix=2001:db8::/32,32..64/config/openconfig-routing-policy-ext:action" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy-ext:action\":\"DENY\"}"
```

PATCH that changes only `sequence-number` for an existing `(ip-prefix, masklength-range)` is rejected (sequence is part of the CONFIG_DB key).

#### 3.3.2.5 DELETE
Supported at prefix-set, prefix entry, and container levels.

Delete one prefix entry:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1/prefixes/prefix=2001:db8::/32,32..64" -H "accept: */*"
```

Delete entire prefix set (all entries):
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set=PrefixSet_1" -H "accept: */*"
```

DELETE on `.../config/sequence-number` or `.../state/sequence-number` alone is rejected. DELETE restrictions are described in [Translation Notes in §4](#4-openconfig-to-sonic-mapping-table).

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=PrefixSet_1]"
```

Leaf GET example (`mode`):
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=PrefixSet_1]/config/mode"
```

#### 3.3.3.2 SET
Create prefix set with nested prefix entry:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --update-path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=PrefixSet_1]" --update-value '{
  "config": {"name": "PrefixSet_1", "mode": "IPV6"},
  "prefixes": {"prefix": [{
    "ip-prefix": "2001:db8::/32",
    "masklength-range": "32..64",
    "config": {
      "ip-prefix": "2001:db8::/32",
      "masklength-range": "32..64",
      "openconfig-routing-policy-ext:sequence-number": 10,
      "openconfig-routing-policy-ext:action": "PERMIT"
    }
  }]}
}'
```

#### 3.3.3.3 DELETE
Delete a prefix entry:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --delete "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=PrefixSet_1]/prefixes/prefix[ip-prefix=2001:db8::/32][masklength-range=32..64]"
```

#### 3.3.3.4 SUBSCRIBE
Supported on supported config and state paths under `prefix-sets`.

On-change subscription on the prefix-sets container:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf sub --path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets" --stream-mode on-change
```

Sample subscription (periodic sample):
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf sub --path "/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets" --stream-mode sample --sample-interval 30s
```

# 4 OpenConfig to SONiC Mapping Table
Mapping attributes between OpenConfig YANG and CONFIG_DB `PREFIX_SET` / `PREFIX`:

#### Table 3: OpenConfig to SONiC Mapping Table

**Database tables:** `PREFIX_SET`, `PREFIX`  
**Key patterns:** `PREFIX_SET|{set-name}`; `PREFIX|{set-name}|{seq}|{canonical-ip-prefix}|{masklength-range}`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/routing-policy/defined-sets/prefix-sets/prefix-set/config/name` | PREFIX_SET | Key `{set-name}` | |
| `prefix-set/config/mode` | PREFIX_SET | mode | OpenConfig `IPV4`/`IPV6` → `IPv4`/`IPv6` |
| `prefix-set/config/description` | PREFIX_SET | description | |
| `../prefix-set/config/name` | PREFIX | Key component `{set-name}` | |
| `../prefixes/prefix/config/ip-prefix` | PREFIX | Key component `{canonical-ip-prefix}` | Normalized on write |
| `../prefixes/prefix/config/masklength-range` | PREFIX | Key component `{masklength-range}` | |
| `prefix/config/sequence-number` | PREFIX | Key component `{sequence-number}` | Mandatory on create/update/replace |
| `prefix/config/action` | PREFIX | action | `PERMIT`/`DENY` → `permit`/`deny` |
| `prefix/config/ip-prefix` (family) | PREFIX | mode | Must match prefix-set `mode` |

Translation Notes:
1. YANG list keys for `prefix` are `ip-prefix` and `masklength-range` only; `sequence-number` is stored in the CONFIG_DB key, not as a third list key.
2. **`sequence-number` is required** on create, update, and replace of a prefix entry. Missing sequence number returns: `Sequence number is mandatory for prefix entry. Please provide sequence number.` OpenConfig does **not** fall back to SONiC `PREFIX_NOSEQ_LIST`.
3. To change the sequence number for an entry, delete the whole prefix entry and recreate it with the desired sequence number. UPDATE/PATCH that changes sequence for the same `(ip-prefix, masklength-range)` is rejected (`same prefix is configured with different sequence`).
4. Two entries in the same set cannot share the same `(ip-prefix, masklength-range)` with different sequence numbers, or the same sequence number with different `(ip-prefix, masklength-range)`.
5. A single request must not include two prefix entries that normalize to the same `(ip-prefix, masklength-range)` (e.g. `0::/64` and `::/64` in one payload).
6. **Prefix normalization and validation:** IPv6 (and IPv4) prefixes are stored under canonical form in the CONFIG_DB key. GET and DELETE accept URI forms that normalize to the same key. Prefixes with host bits set (e.g. `192.168.1.1/24`, `2001:db8::1/64`) are rejected.
7. **`masklength-range`:** Empty is allowed. Single value `V` must equal prefix length `P`. Range `MIN..MAX` requires `MIN <= MAX` and prefix length `P` equal to `MIN` or `MAX`.
8. **Family alignment:** Entry `ip-prefix` address family must match the parent prefix-set `mode`.
9. **DELETE** on the `sequence-number` leaf alone is rejected (`sequence-number cannot be deleted in isolation; delete the whole prefix entry instead`).
10. Deleting the **last** prefix entry in a set also removes the `PREFIX_SET` row automatically.

Representative errors (non-exhaustive):

| Condition | Error (representative) |
|-----------|-------------------------|
| Missing sequence on create | `Sequence number is mandatory for prefix entry...` |
| Same prefix, different seq | `same prefix is configured with different sequence` |
| Same seq, different prefix | `Same sequence number is configured with different rule ...` |
| Duplicate spellings in one payload | `duplicate prefix entry in payload (multiple spellings of ...)` |
| Host bits set | `Prefix has host bits set: expected ..., got ...` |
| Family mismatch | `ip_prefix ... does not match prefix-set mode ...` |
| DELETE seq leaf | `sequence-number cannot be deleted in isolation...` |
| GET/DELETE unknown entry | `Prefix entry not found: ...` |

# 5 Error Handling
Invalid configurations and unsupported operations report an error with a descriptive message (see §4 Translation Notes).

# 6 Unit Test Cases
## 6.1 Functional Test Cases
1. Create, verify, and delete prefix sets and entries using POST, PUT, PATCH, GET, and DELETE via REST/gNMI.
2. Verify IPv4 and IPv6 prefix-set `mode` and prefix entries with PERMIT and DENY actions.
3. Verify IPv6 prefix normalization (e.g. `0::/64` stored and retrieved as `::/64`).
4. Verify GET and DELETE using canonical and non-canonical URI forms of the same prefix.
5. Verify deleting the last prefix entry removes both `PREFIX` and `PREFIX_SET` rows.
6. Verify PATCH on prefix `action` leaf.
7. Verify prefix-set `description` is stored in CONFIG_DB `PREFIX_SET` `description`.

## 6.2 Negative Test Cases
1. Verify missing `sequence-number` on create is rejected.
2. Verify host-bit prefixes are rejected for IPv4 and IPv6.
3. Verify IPv4 prefix in IPV6 set (and vice versa) is rejected.
4. Verify invalid `masklength-range` formats and inverted ranges are rejected.
5. Verify duplicate sequence or duplicate normalized prefix in the same set is rejected.
6. Verify duplicate prefix spellings in a single payload are rejected.
7. Verify DELETE on `sequence-number` leaf alone is rejected and the row remains.
8. Verify PATCH/UPDATE that changes only `sequence-number` for an existing entry is rejected.
