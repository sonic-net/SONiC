# Add support for BGP Community Sets using OpenConfig YANG

# High Level Design Document
#### Rev 0.2

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
    * [3.1.1 set_type Field Derivation](#311-set_type-field-derivation)
  * [3.2 DB Changes](#32-db-changes)
    * [3.2.1 CONFIG DB](#321-config-db)
    * [3.2.2 APP DB](#322-app-db)
    * [3.2.3 STATE DB](#323-state-db)
    * [3.2.4 ASIC DB](#324-asic-db)
    * [3.2.5 COUNTER DB](#325-counter-db)
  * [3.3 User Interface](#33-user-interface)
    * [3.3.1 REST API Support](#331-rest-api-support)
    * [3.3.2 gNMI Support](#332-gnmi-support)
* [4 Flow Diagrams](#4-flow-diagrams)
* [5 Error Handling](#5-error-handling)
* [6 Unit Test Cases](#6-unit-test-cases)
  * [6.1 Functional Test Cases](#61-functional-test-cases)
  * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
* [Table 1: Abbreviations](#table-1-abbreviations)
* [Table 2: OpenConfig YANG SONiC YANG Mapping](#table-2-openconfig-yang-sonic-yang-mapping)

# Revision

| Rev | Date | Author | Change Description |
|:---:|:----:|:------:|:-------------------|
| 0.1 | 01/28/2026 | Venkata Krishna Rao Gorrepati | Initial version |
| 0.2 | 08/03/2026 | Venkata Krishna Rao Gorrepati | Added set_type field derivation documentation |

# About this Manual
This document provides general information about the OpenConfig configuration of BGP Community Sets and Extended Community Sets in SONiC.

# Scope
* This document describes the high level design of configuration of BGP Community Sets using OpenConfig models via REST & gNMI.
* This does not cover the SONiC KLISH CLI.
* This covers only the BGP Community Set and Extended Community Set configuration within routing policies.
* Supported attributes in OpenConfig YANG tree:

```
module: openconfig-routing-policy
  +--rw routing-policy
     +--rw defined-sets
        +--rw oc-bgp-pol:bgp-defined-sets
           +--rw oc-bgp-pol:community-sets
           |  +--rw oc-bgp-pol:community-set* [community-set-name]
           |     +--rw oc-bgp-pol:community-set-name    -> ../config/community-set-name
           |     +--rw oc-bgp-pol:config
           |     |  +--rw oc-bgp-pol:community-set-name      string
           |     |  +--rw oc-bgp-pol:community-member*       union
           |     |  +--rw oc-bgp-pol:match-set-options?      oc-pol-types:match-set-options-type
           |     |  +--rw oc-rp-ext:action?                  action-type
           |     +--ro oc-bgp-pol:state
           |        +--ro oc-bgp-pol:community-set-name      string
           |        +--ro oc-bgp-pol:community-member*       union
           |        +--ro oc-bgp-pol:match-set-options?      oc-pol-types:match-set-options-type
           |        +--ro oc-rp-ext:action?                  action-type
           +--rw oc-bgp-pol:ext-community-sets
              +--rw oc-bgp-pol:ext-community-set* [ext-community-set-name]
                 +--rw oc-bgp-pol:ext-community-set-name    -> ../config/ext-community-set-name
                 +--rw oc-bgp-pol:config
                 |  +--rw oc-bgp-pol:ext-community-set-name?   string
                 |  +--rw oc-bgp-pol:ext-community-member*     union
                 |  +--rw oc-bgp-pol:match-set-options?        oc-pol-types:match-set-options-type
                 |  +--rw oc-rp-ext:action?                    action-type
                 +--ro oc-bgp-pol:state
                    +--ro oc-bgp-pol:ext-community-set-name?   string
                    +--ro oc-bgp-pol:ext-community-member*     union
                    +--ro oc-bgp-pol:match-set-options?        oc-pol-types:match-set-options-type
                    +--ro oc-rp-ext:action?                    action-type
```

* For `match-set-options` (mapped to CONFIG_DB `match_action`), only `ANY` and `ALL` are supported. The OpenConfig value `INVERT` is **not supported** and returns an error.

# Definition/Abbreviation

### Table 1: Abbreviations

| **Term** | **Meaning** |
|:---------|:------------|
| YANG | Yet Another Next Generation: modular language representing data structures in an XML tree format |
| REST | REpresentative State Transfer |
| gNMI | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data |
| XML | eXtensible Markup Language |
| BGP | Border Gateway Protocol |
| AS | Autonomous System |
| RT | Route Target |
| SoO | Site of Origin |

# 1 Feature Overview

## 1.1 Requirements

### 1.1.1 Functional Requirements

1. Provide support for OpenConfig YANG models for BGP routing policy community sets.
2. Configure/Set, GET, and Delete BGP Community Set attributes.
3. Configure/Set, GET, and Delete BGP Extended Community Set attributes.
4. Support standard BGP community formats (AS:NN) and well-known communities.
5. Support extended community formats (route-target, site-of-origin).
6. Support PERMIT/DENY action configuration for community sets.

### 1.1.2 Configuration and Management Requirements

The BGP Community Set configurations can be done via REST and gNMI. The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists.

## 1.2 Design Overview

### 1.2.1 Basic Approach

SONiC already supports routing policy configurations via REST and gNMI using SONiC based YANG models. This feature adds support for OpenConfig based YANG models for BGP Community Sets using transformer based implementation.

### 1.2.2 Container

The code changes for this feature are part of Management Framework container which includes the REST server and gNMI container for gNMI support in sonic-mgmt-common repository.

# 2 Functionality

## 2.1 Target Deployment Use Cases

1. REST client through which the user can perform PATCH, DELETE, POST, PUT, and GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get and set based on the supported YANG models.
3. Network administrators can define community-based routing policies for BGP route filtering and manipulation.
4. Service providers can implement traffic engineering using community attributes.

# 3 Design

## 3.1 Overview

This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md).

The implementation uses OpenConfig routing policy model (`openconfig-routing-policy`) with BGP policy extensions (`openconfig-bgp-policy`) and SONiC-specific extensions (`openconfig-routing-policy-ext`).

### 3.1.1 `set_type` Field Derivation

OpenConfig YANG does not define a `set_type` leaf. In SONiC, `set_type` is a native CONFIG_DB field with enumeration values `STANDARD` and `EXPANDED`. When community sets are configured via OpenConfig (REST/gNMI), the Management Framework transformer layer automatically derives and writes `set_type` to CONFIG_DB as part of the `community-member` field translation.

**SONiC YANG definition:**

```
leaf set_type {
    type enumeration {
        enum STANDARD;
        enum EXPANDED;
    }
    description "Community type";
}
```

**OpenConfig to CONFIG_DB mapping:**

The `community-member` leaf is mapped to CONFIG_DB field `community_member`. During Yang-to-Db translation, `set_type` is also written alongside `community_member`. There is no corresponding OpenConfig leaf and no Db-to-Yang mapping for `set_type`; it is not returned in OpenConfig GET responses.

**Derivation logic for BGP Community Sets:**

1. Each `community-member` value is parsed from the OpenConfig union type:
   * **Well-known communities** (`NO_EXPORT`, `NO_ADVERTISE`, `GRACEFUL_SHUTDOWN`, `NOPEER`) → mapped to SONiC strings (`no-export`, `no-advertise`, etc.) and treated as **STANDARD**.
   * **String members** → validated against `AS:NN` format (both parts in range 0–65535). Valid `AS:NN` values are **STANDARD**; strings that fail validation (e.g., regex patterns) are treated as **EXPANDED**.
   * **Uint32 members** → converted to decimal string; must be in range 0–65535 (**STANDARD**).

2. **Numeric community-set-name constraint**: If the community set name is a numeric string, additional checks apply **before** final `set_type` assignment:
   * Names **0–99**: If any member is expanded (`is_expanded=true`), the operation is **rejected with error** (`"Standard community set name [0-99] cannot have expanded community members"`). Expanded members never reach default derivation for these names.
   * Names **100–500**: Allowed; no error based on name alone.
   * Names outside **0–500** (when numeric): Rejected with error.

3. **Default derivation** (runs for all requests that pass the checks above):
   * If any member is in expanded format → `set_type` = **EXPANDED**
   * Otherwise → `set_type` = **STANDARD**

   This applies to **non-numeric names** and to **numeric names 0–99** that contain only standard members. For numeric names **0–99**, expanded members are rejected in step 2 and never reach this step.

   **Evaluation order summary:**

   | Set name | Member type | Result |
   |:---------|:------------|:-------|
   | Non-numeric (e.g., `PRIVATE_AS`) | Standard (`AS:NN`, well-known) | `STANDARD` |
   | Non-numeric | Expanded (regex/non-`AS:NN`) | `EXPANDED` |
   | Numeric **0–99** | Standard only | `STANDARD` |
   | Numeric **0–99** | Any expanded member | **Error** (rejected) |
   | Numeric **100–500** | Standard or expanded | `STANDARD` or `EXPANDED` based on members |

4. **Update immutability**: On update/replace, if an existing `set_type` is already stored in CONFIG_DB and the newly derived type differs, the operation is rejected with error: `"Community members type do not match existing set_type in DB"`.

**Derivation logic for Extended Community Sets:**

1. Each `ext-community-member` value is parsed:
   * Members with `route-target:` or `site-of-origin:` prefix → converted to SONiC format (`rt <value>`, `soo <value>`) and treated as **STANDARD**.
   * Members without these prefixes (e.g., regex patterns) → treated as **EXPANDED**.

2. The same numeric community-set-name constraints (0–99, 100–500), evaluation order, and update immutability rules apply. For numeric names **0–99**, expanded members are rejected before default derivation; for **100–500**, final `set_type` is determined by member format.

**Example CONFIG_DB entries after OpenConfig SET:**

Standard community set:
```
COMMUNITY_SET|PRIVATE_AS
{
  "name": "PRIVATE_AS",
  "community_member": ["65000:100", "65000:200"],
  "set_type": "STANDARD",
  "match_action": "ANY",
  "action": "permit"
}
```

Expanded community set (regex member):
```
COMMUNITY_SET|100
{
  "name": "100",
  "community_member": ["65000:.*"],
  "set_type": "EXPANDED",
  "match_action": "ANY",
  "action": "permit"
}
```

## 3.2 DB Changes

### 3.2.1 CONFIG DB

**COMMUNITY_SET Table**

```
COMMUNITY_SET|<community-set-name>
{
  "name": "<community-set-name>",
  "community_member": ["<community1>", "<community2>", ...],
  "set_type": "<STANDARD|EXPANDED>",
  "match_action": "<ANY|ALL>",
  "action": "<PERMIT|DENY>"
}
```

**Field Descriptions:**
* **name**: Unique identifier for the community set (key)
* **community_member**: List of BGP community values
  * Standard format: `AA:NN` (e.g., "65000:100")
  * Well-known: `no-export`, `no-advertise`, `graceful-shutdown`, `no-peer`
  * Regex patterns supported (requires EXPANDED set_type)
* **set_type**: Community set type, auto-derived by transformer (not configurable via OpenConfig)
  * `STANDARD`: Members are literal community values (AS:NN, well-known, or uint32)
  * `EXPANDED`: Members include regex patterns or non-standard formats
  * Derived automatically when `community-member` is configured; immutable on update
* **match_action**: How to match communities in the set. Mapped from OpenConfig `match-set-options`:
  * `ANY` → `ANY` (match if any member is present)
  * `ALL` → `ALL` (match if all members are present)
  * `INVERT` → **not supported**; configuration is rejected with error
* **action**: Policy action when matched (permit, deny)

**EXTENDED_COMMUNITY_SET Table**

```
EXTENDED_COMMUNITY_SET|<ext-community-set-name>
{
  "name": "<ext-community-set-name>",
  "community_member": ["<ext-community1>", "<ext-community2>", ...],
  "set_type": "<STANDARD|EXPANDED>",
  "match_action": "<ANY|ALL>",
  "action": "<PERMIT|DENY>"
}
```

**Field Descriptions:**
* **name**: Unique identifier for the extended community set (key)
* **community_member**: List of extended community values
  * Standard format: `rt <AS:NN>` (Route Target), `soo <AS:NN>` (Site of Origin)
  * Regex patterns supported (requires EXPANDED set_type)
* **set_type**: Extended community set type, auto-derived by transformer (not configurable via OpenConfig)
  * `STANDARD`: Members use `route-target:` or `site-of-origin:` prefix in OpenConfig (stored as `rt`/`soo` in CONFIG_DB)
  * `EXPANDED`: Members are regex patterns without standard prefixes
  * Derived automatically when `ext-community-member` is configured; immutable on update
* **match_action**: How to match communities in the set. Mapped from OpenConfig `match-set-options`:
  * `ANY` → `ANY` (match if any member is present)
  * `ALL` → `ALL` (match if all members are present)
  * `INVERT` → **not supported**; configuration is rejected with error
* **action**: Policy action when matched (permit, deny)

**Extended Community Formats (OpenConfig → CONFIG_DB mapping):**
* Route Target: `route-target:65000:100` → `rt 65000:100`
* Site of Origin: `site-of-origin:65000:200` → `soo 65000:200`

### 3.2.2 APP DB

There are no changes to APP DB schema definition.

### 3.2.3 STATE DB

There are no changes to STATE DB schema definition.

### 3.2.4 ASIC DB

There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB

There are no changes to COUNTER DB schema definition.

## 3.3 User Interface

### 3.3.1 REST API Support

#### 3.3.1.1 GET
 
Supported 

#### 3.3.1.2 PUT

Supported

#### 3.3.1.3 PATCH

Supported

#### 3.3.1.4 DELETE

Supported

### 3.3.2 gNMI Support

#### 3.3.2.1 GET

**Community set GET:**

```bash
gnmi_get -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath /openconfig-routing-policy:routing-policy/defined-sets/bgp-defined-sets/community-sets/community-set[community-set-name=PRIVATE_AS]/config
```

**Response:**

```
== getResponse:
notification: <
  timestamp: 1738090000000000000
  update: <
    path: <
      elem: <name: "openconfig-routing-policy:routing-policy">
      elem: <name: "defined-sets">
      elem: <name: "bgp-defined-sets">
      elem: <name: "community-sets">
      elem: <
        name: "community-set"
        key: <key: "community-set-name" value: "PRIVATE_AS">
      >
      elem: <name: "config">
    >
    val: <
      json_ietf_val: "{\"openconfig-bgp-policy:config\":{\"community-set-name\":\"PRIVATE_AS\",\"community-member\":[\"65000:100\",\"65000:200\"],\"openconfig-routing-policy-ext:action\":\"PERMIT\"}}"
    >
  >
>
```

#### 3.3.2.2 SET

**Community set SET:**

```bash
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -update /openconfig-routing-policy:routing-policy/defined-sets/bgp-defined-sets/community-sets/community-set[community-set-name=PRIVATE_AS]/config:@/tmp/community_set.json
```

**community_set.json:**
```json
{
  "openconfig-bgp-policy:config": {
    "community-set-name": "PRIVATE_AS",
    "community-member": ["65000:100", "65000:200", "65000:300"],
    "openconfig-routing-policy-ext:action": "PERMIT"
  }
}
```

#### 3.3.2.3 DELETE

**Community set DELETE:**

```bash
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -delete /openconfig-routing-policy:routing-policy/defined-sets/bgp-defined-sets/community-sets/community-set[community-set-name=PRIVATE_AS]
```

# 4 Flow Diagrams

### Table 2: OpenConfig YANG SONiC YANG Mapping

| **OpenConfig YANG Path** | **SONiC CONFIG_DB Table** | **SONiC Field** |
|:------------------------|:--------------------------|:----------------|
| /routing-policy/defined-sets/bgp-defined-sets/community-sets/community-set | COMMUNITY_SET | - |
| community-set-name | COMMUNITY_SET | name |
| community-member | COMMUNITY_SET | community_member |
| *(auto-derived, no OC leaf)* | COMMUNITY_SET | set_type |
| action (extension) | COMMUNITY_SET | action |
| match-set-options (`ANY`, `ALL`; `INVERT` not supported) | COMMUNITY_SET | match_action |

| **OpenConfig YANG Path** | **SONiC CONFIG_DB Table** | **SONiC Field** |
|:------------------------|:--------------------------|:----------------|
| /routing-policy/defined-sets/bgp-defined-sets/ext-community-sets/ext-community-set | EXTENDED_COMMUNITY_SET | - |
| ext-community-set-name | EXTENDED_COMMUNITY_SET | name |
| ext-community-member | EXTENDED_COMMUNITY_SET | community_member |
| *(auto-derived, no OC leaf)* | EXTENDED_COMMUNITY_SET | set_type |
| action (extension) | EXTENDED_COMMUNITY_SET | action |
| match-set-options (`ANY`, `ALL`; `INVERT` not supported) | EXTENDED_COMMUNITY_SET | match_action |

**Configuration Flow:**

```
User Input (REST/gNMI)
        ↓
Management Framework
        ↓
Translib Layer
        ↓
Transformer Layer (OpenConfig → CONFIG_DB field mapping):
  - Map community set key (community-set-name → name)
  - Translate community members and derive set_type
  - Translate action (PERMIT/DENY → permit/deny)
  - Translate match-set-options (ANY/ALL → match_action)
  - Map extended community set key (ext-community-set-name → name)
  - Translate extended community members and derive set_type
  - Translate extended community action and match-set-options
        ↓
CONFIG_DB (COMMUNITY_SET / EXTENDED_COMMUNITY_SET table)
        ↓
BGP Config Manager
        ↓
FRRouting (BGP Daemon)
```

# 5 Error Handling

Invalid configurations will report an error. Examples:

1. **Invalid community format**: Returns error if community format doesn't match `AS:NN` pattern and is not a valid expanded/regex format
2. **Duplicate community set name**: Returns error if attempting to create a community set with existing name
3. **Invalid action value**: Returns error if action is not PERMIT or DENY
4. **Empty community members**: Returns error if community-member list is empty
5. **Resource not found**: Returns 404 error for GET operations on non-existent community sets
6. **set_type mismatch on update**: Returns error if updated community members would change the existing `set_type` (e.g., changing from STANDARD members to regex/expanded members on an existing set)
7. **Numeric name constraint violation**: Returns error if community set name is numeric 0–99 but contains expanded/regex members, or if numeric name is outside 0–500 range
8. **Standard community set name with expanded members**: Returns error `"Standard community set name [0-99] cannot have expanded community members"`
9. **Delete at leaf level**: Returns error if attempting DELETE operation on individual community-member leaf (must delete entire community set)
10. **INVERT match-set-options**: Returns error if OpenConfig `match-set-options` is set to `INVERT`. Only `ANY` and `ALL` are supported for community and extended community sets.

**Example error response:**

```json
{
  "ietf-restconf:errors": {
    "error": [
      {
        "error-type": "application",
        "error-tag": "invalid-value",
        "error-message": "Invalid community format. Expected AS:NN format (e.g., 65000:100)"
      }
    ]
  }
}
```

# 6 Unit Test Cases

## 6.1 Functional Test Cases

1. Create, verify, and delete BGP Community Set using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
2. Create, verify, and delete BGP Extended Community Set using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
3. Verify GET, PATCH, PUT, POST and DELETE for community-member attribute works as expected via REST/gNMI.
4. Verify GET, PATCH, PUT, and DELETE for action attribute works as expected via REST/gNMI.
5. Verify standard community formats (AS:NN) are accepted and stored correctly.
6. Verify well-known communities (NO_EXPORT, NO_ADVERTISE, NO_EXPORT_SUBCONFED) are accepted.
7. Verify extended community formats (route-target, route-origin) are accepted and stored correctly.
8. Verify multiple community members can be added to a single community set.
9. Verify community set configuration persists across system reboot.
10. Verify regex patterns in community members are accepted and result in `set_type=EXPANDED` in CONFIG_DB.
11. Verify standard community members (AS:NN, well-known) result in `set_type=STANDARD` in CONFIG_DB.
12. Verify extended community members with `route-target:` / `site-of-origin:` prefix result in `set_type=STANDARD`.
13. Verify numeric community set name 0–99 with standard members is accepted; with expanded members is rejected.
14. Verify numeric community set name 100–500 with standard members results in `set_type=STANDARD`; with expanded members results in `set_type=EXPANDED`.

## 6.2 Negative Test Cases

1. Verify GET after DELETE returns a "Resource Not Found" error.
2. Verify creating a community set with invalid community format returns error.

```bash
curl -X PUT -k "https://switch/restconf/data/openconfig-routing-policy:routing-policy/defined-sets/bgp-defined-sets/community-sets/community-set=INVALID" -H "Content-Type: application/yang-data+json" -d '{
  "openconfig-bgp-policy:community-set": [{
    "community-set-name": "INVALID",
    "config": {
      "community-member": ["invalid_format"]
    }
  }]
}'
```

**Expected:** Error response indicating invalid community format.

3. Verify creating a community set with empty community-member list returns error.
4. Verify setting action to invalid value (not PERMIT or DENY) returns error.
5. Verify creating duplicate community set name returns error.
6. Verify invalid extended community format returns error.
7. Verify updating community members from STANDARD to EXPANDED format on an existing set returns set_type mismatch error.
8. Verify numeric community set name outside 0–500 range returns error.
9. Verify community set name 0–99 with regex/expanded community members returns error.
10. Verify setting `match-set-options` to `INVERT` returns error for both community and extended community sets.

