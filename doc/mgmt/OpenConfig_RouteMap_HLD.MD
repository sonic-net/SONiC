# OpenConfig support for Route Map.

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
      * [3.3.1 REST API Support](#332-rest-api-support)
      * [3.3.2 gNMI Support](#333-gnmi-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
[Table 2: OC YANG SONiC YANG Mapping](#4-flow-diagrams)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 24/11/2025  | Raja Kushwah | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of Route Map in SONiC.

# Scope
- This document describes the high level design for configuring **routing policies (route-maps)** using **OpenConfig models** via **RESTCONF and gNMI**.

- This document does **not** cover the SONiC KLISH CLI.

- This document covers only **routing-policy configuration**, including:
  - **Route-map (policy-definition)**
  - **Statements (sequence numbers)**
  - **Match conditions** (prefix-set, community-set)
  - **BGP actions** (next-hop, community)
  - **On-match behavior** (NEXT / GOTO)

- Supported attributes in OpenConfig YANG tree:

<pre>
<b>module: openconfig-routing-policy</b>
+--rw routing-policy
   +--rw policy-definitions
   |  +--rw policy-definition* [name]
   |     +--rw name                     -> ../config/name
   |     +--rw config
   |     |  +--rw name?                 string
   |     |  +--rw description?          string
   |     +--rw statements
   |        +--rw statement* [name]
   |           +--rw name               -> ../config/name
   |           +--rw config
   |           |  +--rw name?                   string
   |           |  +--rw description?            string
   <b>|           |  +--rw policy-result?          enumeration (PERMIT | DENY)
   |           |  +--rw on-match-action?         enumeration (NEXT | GOTO)
   |           |  +--rw on-match-goto-statement? string</b>
   |           +--rw conditions
   <b>|           |  +--rw match-prefix-set
   |           |  |  +--rw config
   |           |  |     +--rw prefix-set?        string
   |           |  +--rw bgp-conditions
   |           |     +--rw match-community-set
   |           |        +--rw config
   |           |           +--rw community-set?   string</b>
   |           +--rw actions
   |              +--rw bgp-actions
                  +--rw config
   <b>               |  +--rw set-next-hop?        union (IPv4 / IPv6 / PREFER_GLOBAL)</b>
                  +--rw set-community
   <b>                  +--rw config
   |                    |  +--rw method?             (INLINE | REFERENCE)
   |                    |  +--rw options?            (ADD | REPLACE)
   |                    +--rw inline
   |                    |  +--rw config
   |                    |     +--rw communities*      string
   |                    +--rw reference
   |                       +--rw config
   |                          +--rw community-set-refs* string</b>

<b>module: openconfig-routing-policy (defined-sets)</b>
+--rw routing-policy
   +--rw defined-sets
      +--rw prefix-sets
      |  +--rw prefix-set* [name]
      |     +--rw name                -> ../config/name
      |     +--rw config
      |        +--rw name?            string
      +--rw bgp-defined-sets
         +--rw community-sets
            +--rw community-set* [name]
               +--rw name            -> ../config/name
               +--rw config
                  +--rw name?        string
                  +--rw community-member*   string
</pre>


# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | Representative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig routing-policy YANG models.
2. Configure/Set, GET, and Delete route-map (policy-definition) attributes.
3. Support creation, update, and deletion of route-map statements (sequence numbers).
4. Support configuration of match conditions, including prefix-sets and community-sets, via REST and gNMI.
5. Support configuration of BGP actions, including IPv4/IPv6 next-hop, prefer-global, and set-community (INLINE/REFERENCE).
6. Support on-match behaviors (NEXT and GOTO).
7. Support CVL custom validations to prevent unsupported or inconsistent routing-policy configurations.

### 1.1.2 Configuration and Management Requirements
Routing-policy (route-map), statement, match conditions, actions, prefix-sets, and community-sets can be configured via REST and gNMI.  
The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists in SONiC.


## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports routing-policy and route-map configurations through its native SONiC YANG models.  
This feature adds support for the corresponding OpenConfig routing-policy YANG models, using a transformer-based implementation instead of the translib infrastructure, enabling standardized route-map configuration via REST and gNMI.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get and set based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition.
### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface


# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and Community SONiC YANG:

### Route-Map (Policy Definition)
| OC YANG (openconfig-routing-policy.yang) | SONiC YANG (sonic-routing-policy.yang) |
|------------------------------------------|-----------------------------------------|
|                                          | *container ROUTE_MAP*                   |
| name                                     | route_map_name                          |
| config/name                              | route_map_name                          |
| config/description                       | description                              |

### Route-Map Statements (Sequence Numbers)
| OC YANG (openconfig-routing-policy.yang) | SONiC YANG (sonic-routing-policy.yang) |
|------------------------------------------|-----------------------------------------|
|                                          | *container ROUTE_MAP_SEQUENCE*          |
| statement/name                           | sequence_number                         |
| statement/config/name                    | sequence_number                         |
| statement/config/description             | description                              |
| statement/config/policy-result           | action (PERMIT/DENY)                    |
| statement/config/on-match-action         | on_match_action (NEXT/GOTO)             |
| statement/config/on-match-goto-statement | on_match_goto_seq                       |

### Match Conditions (Prefix-Sets)
| OC YANG (openconfig-routing-policy.yang) | SONiC YANG (sonic-prefix-list.yang)     |
|------------------------------------------|------------------------------------------|
|                                          | *container PREFIX_LIST*                  |
| match-prefix-set/config/prefix-set       | prefix_list_name                         |
| defined-sets/prefix-sets/prefix-set/name | prefix_list_name                         |
| prefix-set/config/name                   | prefix_list_name                         |

### Match Conditions (Community-Sets)
| OC YANG (openconfig-routing-policy.yang) | SONiC YANG (sonic-community-list.yang)  |
|------------------------------------------|------------------------------------------|
|                                          | *container COMMUNITY_LIST*              |
| match-community-set/config/community-set | community_list_name                     |
| community-sets/community-set/name        | community_list_name                     |
| community-set/config/community-member    | community_members                       |

### BGP Actions: Next-Hop
| OC YANG (openconfig-routing-policy.yang) | SONiC YANG (sonic-bgp.yang)            |
|------------------------------------------|-----------------------------------------|
|                                          | *container ROUTE_MAP_SET*              |
| bgp-actions/config/set-next-hop          | set_nexthop (IPv4/IPv6/PREFER_GLOBAL)  |

### BGP Actions: Set-Community (INLINE/REFERENCE)
| OC YANG (openconfig-routing-policy.yang)                | SONiC YANG (sonic-bgp.yang)               |
|---------------------------------------------------------|--------------------------------------------|
|                                                         | *container ROUTE_MAP_SET_COMMUNITY*        |
| set-community/config/method (INLINE/REFERENCE)          | method (INLINE/REFERENCE)                  |
| set-community/config/options (ADD/REPLACE)              | options (ADD/REPLACE)                      |
| set-community/inline/config/communities                 | inline_communities                         |
| set-community/reference/config/community-set-refs       | community_list_refs                        |


# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases (Route-Map)

1. Create and verify new route-map (policy-definition) using PUT, PATCH, POST and GET via REST/gNMI.
   - Create a new `policy-definition` with name and description.
   - Verify route-map presence and attributes via REST GET and gNMI Get.

2. Create and verify route-map statements (sequence numbers) using PUT, PATCH, POST and GET via REST/gNMI.
   - Add statements (e.g., 10, 20, 30) under an existing route-map.
   - Verify `config/name`, `description` and `policy-result` are correctly reflected.

3. Verify GET, PATCH, PUT, POST and DELETE for **policy-result** on route-map statements via REST/gNMI.
   - Configure `policy-result` (e.g., ACCEPT_ROUTE / REJECT_ROUTE or PERMIT/DENY as applicable).
   - Update and delete `policy-result` and verify the changes through REST and gNMI.

4. Verify configuration of **BGP next-hop actions** via REST/gNMI:
   - `set-next-hop` IPv4 (e.g., `7.7.7.7`)
   - `set-next-hop` IPv6 (e.g., `2004::7`)
   - `set-next-hop` = `PREFER_GLOBAL`
   - Confirm all are correctly stored and retrieved via GET (REST/gNMI).

5. Verify configuration of **set-community actions** via REST/gNMI:
   - Configure `set-community` with:
     - `method = INLINE` and `options = ADD` / `REPLACE`
     - `method = REFERENCE` with `community-set-refs`
   - Verify inline communities and referenced community-sets are properly reflected in GET.

6. Verify GET, PATCH, PUT, POST and DELETE for **prefix-sets** (IPv4/IPv6) via REST/gNMI.
   - Create prefix-sets (e.g., `DEFAULT-ROUTE`, `DEFAULT-ROUTE-V6`) with one or more prefixes.
   - Attach them via `match-prefix-set/config/prefix-set` to route-map statements.
   - Verify that deleting a prefix-set after detaching references works as expected.

7. Verify GET, PATCH, PUT, POST and DELETE for **community-sets** via REST/gNMI.
   - Create community-sets (e.g., `COMM-HOST-ROUTES`) with one or more communities.
   - Attach them via `match-community-set/config/community-set`.
   - Verify community-set modifications and deletion after references are removed.

8. Verify **on-match behavior** (NEXT / GOTO) on route-map statements via REST/gNMI.
   - Configure `on-match-action = NEXT` and confirm the next statement is evaluated.
   - Configure `on-match-action = GOTO` with `on-match-goto-statement` and confirm jump behavior is properly programmed and retrievable via GET.

9. Verify wild-card and subtree GETs for **all routing-policy objects** via REST/gNMI.
   - GET `/routing-policy/policy-definitions` to list all route-maps.
   - GET `/routing-policy/defined-sets` to list all prefix-sets and community-sets.
   - Confirm content matches individual GETs.

10. Verify gNMI subscription (ON_CHANGE, SAMPLE, TARGET_DEFINED) for route-map and defined-sets.
    - ON_CHANGE subscription on:
      - `policy-result`, `set-next-hop`, `on-match-action`, `on-match-goto-statement`
    - SAMPLE subscription on:
      - prefix-sets and community-sets trees
    - TARGET_DEFINED on:
      - `/routing-policy/policy-definitions` and `/routing-policy/defined-sets`
    - Confirm notifications are received as configuration changes occur.


## 6.2 Negative Test Cases
1.### 6.2.1 Negative Test – Invalid on-match-goto-statement Configuration

This test verifies that **on-match-goto-statement** is rejected when the route-map statement does **not** use `on-match-action = GOTO`.  
Any attempt to configure a GOTO jump without the correct action must fail with a CVL semantic validation error.

---

#### gNMI SET Request (Invalid)
```bash
gnmic -a 10.89.171.155:35049 -u cisco -p cisco123 --insecure \
--target OC-YANG -e json_ietf set \
--update-path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]/actions/config" \
--update-value '{
  "openconfig-routing-policy:config": {
    "policy-result": "ACCEPT_ROUTE",
    "on-match-goto-statement": 40
  }
}'


ERROR RESPONSE 

GOTO is only valid when on-match-action = GOTO

target '10.89.171.155:35049' set request failed: target '10.89.171.155:35049' SetRequest failed: 
rpc error: code = Unknown desc = Translib Redis Error: CVL Failure: 
1002: ErrCode[1002]: ErrDetails[Config Validation Semantic Error], 
Msg[Must expression validation failed], 
ConstraintErrMsg[on_match_goto_statement is only allowed when on_match_action is GOTO], 
Table[ROUTE_MAP:[ROUTE 10]], 
Field[on_match_goto_statement:40]
Error: one or more requests failed

