# Add support for BGP Community Sets using OpenConfig YANG

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

## 3.2 DB Changes

### 3.2.1 CONFIG DB

**COMMUNITY_SET Table**

```
COMMUNITY_SET|<community-set-name>
{
  "name": "<community-set-name>",
  "community_member": ["<community1>", "<community2>", ...],
  "match_action": "<ANY|ALL>",
  "action": "<PERMIT|DENY>"
}
```

**Field Descriptions:**
* **name**: Unique identifier for the community set (key)
* **community_member**: List of BGP community values
  * Standard format: `AA:NN` (e.g., "65000:100")
  * Well-known: `NO_EXPORT`, `NO_ADVERTISE`, `NO_EXPORT_SUBCONFED`
  * Regex patterns supported
* **match_action**: How to match communities in the set (ANY, ALL)
* **action**: Policy action when matched (PERMIT, DENY)

**EXTENDED_COMMUNITY_SET Table**

```
EXTENDED_COMMUNITY_SET|<ext-community-set-name>
{
  "name": "<ext-community-set-name>",
  "community_member": ["<ext-community1>", "<ext-community2>", ...],
  "match_action": "<ANY|ALL>",
  "action": "<PERMIT|DENY>"
}
```

**Extended Community Formats:**
* Route Target: `route-target:65000:100`
* Route Origin: `route-origin:65000:200`

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
| action (extension) | COMMUNITY_SET | action |
| match-set-options | COMMUNITY_SET | match_action |

| **OpenConfig YANG Path** | **SONiC CONFIG_DB Table** | **SONiC Field** |
|:------------------------|:--------------------------|:----------------|
| /routing-policy/defined-sets/bgp-defined-sets/ext-community-sets/ext-community-set | EXTENDED_COMMUNITY_SET | - |
| ext-community-set-name | EXTENDED_COMMUNITY_SET | name |
| ext-community-member | EXTENDED_COMMUNITY_SET | community_member |
| action (extension) | EXTENDED_COMMUNITY_SET | action |
| match-set-options | EXTENDED_COMMUNITY_SET | match_action |

**Configuration Flow:**

```
User Input (REST/gNMI)
        ↓
Management Framework
        ↓
Translib Layer
        ↓
Transformer Functions:
  - rpol_community_set_key_xfmr
  - rpol_community_member_xfmr
  - rpol_community_action_xfmr
  - rpol_match_set_options_xfmr
        ↓
CONFIG_DB (COMMUNITY_SET table)
        ↓
BGP Config Manager (frrcfgd via vtysh)
        ↓
FRRouting (BGP Daemon)
```

# 5 Error Handling

Invalid configurations will report an error. Examples:

1. **Invalid community format**: Returns error if community format doesn't match `AS:NN` pattern
2. **Duplicate community set name**: Returns error if attempting to create a community set with existing name
3. **Invalid action value**: Returns error if action is not PERMIT or DENY
4. **Empty community members**: Returns error if community-member list is empty
5. **Resource not found**: Returns 404 error for GET operations on non-existent community sets

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
10. Verify regex patterns in community members are accepted.

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

