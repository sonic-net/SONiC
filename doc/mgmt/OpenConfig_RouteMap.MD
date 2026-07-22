# OpenConfig Support for Route Map.

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
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
      * [3.3.4 gNMI Subscription Support](#334-gnmi-subscription-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
[Table 2: OpenConfig YANG SONiC YANG Mapping](#4-flow-diagrams)

# Revision
| Rev |     Date    |       Author          | Change Description                                                                 |
|:---:|:-----------:|:---------------------:|------------------------------------------------------------------------------------|
| 0.1 | 24/11/2025  | Raja Kushwah          | Initial version                                                                    |
| 0.2 | 07/22/2026  | Raja Kushwah          | Addressed review comments: corrected SONiC YANG file names, container/field names, `policy-result` path; added REST/gNMI examples |


# About this Manual
This document provides general information about the OpenConfig configuration of Route Map (routing-policy) in SONiC.

# Scope
- This document describes the high-level design for configuring Route Maps (routing policies) using OpenConfig models via REST and gNMI. 
- This does not cover the SONiC KLISH CLI.
- In scope: route-map (policy-definition) and statements, their match conditions, BGP and protocol-agnostic set-actions, and flow control (`on-match-next`, `on-match-goto-statement`, `next-statement`).
- Out of scope: defined-sets (prefix-sets, community-sets, ext-community-sets, as-path-sets) are covered in a separate HLD; route-map match conditions only reference them by name (leafref).

- Supported attributes in the OpenConfig YANG tree (SONiC-extension leaves marked with `(ext)`):

```text
module: openconfig-routing-policy
+--rw routing-policy
   +--rw policy-definitions
      +--rw policy-definition* [name]
         +--rw name                     -> ../config/name
         +--rw config
         |  +--rw name?                 string
         +--rw statements
            +--rw statement* [name]
               +--rw name               -> ../config/name
               +--rw config
               |  +--rw name?                 string
               |  +--rw description?          string   (ext)
               +--rw conditions
               |  +--rw config
               |  |  +--rw call-policy?          leafref
               |  |  +--rw install-protocol-eq?  identityref (BGP | DIRECTLY_CONNECTED | STATIC)
               |  +--rw match-interface/config/interface?   leafref
               |  +--rw match-prefix-set/config/prefix-set?  leafref
               |  +--rw match-tag-set/config/tag-set?        leafref
               |  +--rw oc-bgp-pol:bgp-conditions
               |     +--rw config
               |     |  +--rw local-pref-eq?        uint32
               |     |  +--rw med-eq?               uint32
               |     |  +--rw origin-eq?            identityref (IGP | EGP | INCOMPLETE)
               |     |  +--rw match-nexthop-set?          leafref  (ext)
               |     |  +--rw match-src-network-instance? string   (ext)
               |     |  +--rw match-neighbor*             string   (ext, max 1)
               |     +--rw match-community-set/config/community-set?         leafref
               |     +--rw match-ext-community-set/config/ext-community-set? leafref
               |     +--rw match-as-path-set/config/as-path-set?             leafref
               +--rw actions
                  +--rw config
                  |  +--rw policy-result?           enumeration (ACCEPT_ROUTE | REJECT_ROUTE | NEXT_STATEMENT)
                  |  +--rw next-statement?          uint16   (ext)
                  |  +--rw on-match-next?           boolean  (ext)
                  |  +--rw on-match-goto-statement? uint16   (ext)
                  +--rw set-tag/config/mode?  enum (INLINE)
                  +--rw set-tag/inline/config/tag*  union (uint32)
                  +--rw oc-bgp-pol:bgp-actions
                     +--rw config
                     |  +--rw set-next-hop?      union (IPv4 | IPv6 | PREFER_GLOBAL)
                     |  +--rw set-local-pref?    uint32
                     |  +--rw set-med?           uint32
                     |  +--rw set-med-action?    enum (SET | ADD | SUBTRACT)
                     |  +--rw set-route-origin?  identityref (IGP | EGP | INCOMPLETE)
                     |  +--rw set-source-address? oc-inet:ip-address  (ext)
                     +--rw set-as-path-prepend/config
                     |  +--rw asn?          oc-inet:as-number
                     |  +--rw repeat-n?     uint8
                     |  +--rw asn-sequence? string   (ext)
                     +--rw set-community
                     |  +--rw config/method?   enum (INLINE | REFERENCE)
                     |  +--rw config/options?  enum (ADD)
                     |  +--rw inline/config/communities*         string
                     |  +--rw reference/config/community-set-refs* string
                     +--rw set-ext-community
                     |  +--rw config/method?   enum (INLINE | REFERENCE)
                     |  +--rw config/options?  enum (REPLACE)
                     |  +--rw inline/config/communities*             string
                     |  +--rw reference/config/ext-community-set-refs* string
                     +--rw oc-rp-ext:set-large-community  (ext)
                        +--rw config/method?   enum (INLINE)
                        +--rw config/options?  enum (ADD)
                        +--rw inline/config/large-communities* string
```

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |
| BGP                     | Border Gateway Protocol   |
| MED                     | Multi-Exit Discriminator   |
| VRF                     | Virtual Routing and Forwarding   |
| CVL                     | Config Validation Library   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig routing-policy YANG models for Route Map.
2. Configure/Set, GET, and Delete route-map (policy-definition) and statement (sequence-number) attributes.
3. Support configuration of match conditions: prefix-set, community-set, ext-community-set, as-path-set, tag, local-pref, MED, origin, install-protocol, and the SONiC-ext conditions (next-hop-set, source network-instance/VRF, neighbor).
4. Support configuration of BGP set-actions: next-hop (IPv4/IPv6/PREFER_GLOBAL), set-community (INLINE/REFERENCE), set-ext-community (INLINE/REFERENCE), set-large-community (INLINE), as-path prepend (asn / repeat-n / asn-sequence), local-pref, MED (SET/ADD/SUBTRACT), and route-origin; and the protocol-agnostic set-tag and set-source-address actions.
5. Support flow control: `on-match-next`, `on-match-goto-statement`, and `next-statement`.
6. Support CVL custom validations and transformer-level validations to prevent unsupported or inconsistent routing-policy configurations.

Note: Defined-sets (prefix-sets, community-sets, ext-community-sets, as-path-sets) are out of scope for this document and are covered in a separate HLD; route-map match conditions reference them via leafref only.

### 1.1.2 Configuration and Management Requirements
Routing-policy (route-map), statement, match conditions, and set-actions can be configured via REST and gNMI. The implementation returns an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists in SONiC.

### 1.1.3 Scalability Requirements
Route-map scale follows the existing CONFIG_DB ROUTE_MAP_SET / ROUTE_MAP schema and platform limits for the number of route-maps and the number of statements (and their match/set attributes) per route-map.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports route-map configuration through its native SONiC YANG model (`sonic-route-map.yang`). This feature adds support for the corresponding OpenConfig routing-policy YANG models (policy-definitions / statements) using a transformer-based implementation instead of translib infrastructure.

The route-map implementation lives in `xfmr_route_map.go` (under `sonic-mgmt-common/translib/transformer`): the statement key transformer (`routing_policy_statement_key_xfmr`, mapping OpenConfig `policy-definition[name]` + `statement[name]` to the SONiC `ROUTE_MAP|<name>|<stmt>` key) and the field transformers for all statement match/set/flow-control attributes.

The OpenConfig-to-SONiC mapping (table name, field name, key/field transformers) is declared via `sonic-ext` deviations in `openconfig-routing-policy-annot.yang`.

Note: The defined-set transformers (`xfmr_prefix_list.go`, `xfmr_bgp_community.go`, `xfmr_bgp_as_path_set.go`) and the `sonic-routing-policy-sets.yang` model are covered in the separate defined-sets HLD; route-map only references those sets by name.

### 1.2.2 Container
The code changes for this feature are part of the *Management Framework* container which includes the REST server, and the *gnmi* container for gNMI support, in the *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform PATCH, DELETE, POST, PUT, and GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get, set, and subscribe based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition. Route-maps use the existing tables:
- `ROUTE_MAP_SET` — route-map name registry (`ROUTE_MAP_SET|<name>`).
- `ROUTE_MAP` — per-statement match/set/flow-control fields (`ROUTE_MAP|<name>|<stmt_name>`), including the leafref fields that reference defined-sets (e.g. `match_prefix_set`, `match_community`, `match_as_path`).

Defined-set tables (`PREFIX_SET`/`PREFIX`, `COMMUNITY_SET`, `EXTENDED_COMMUNITY_SET`, `AS_PATH_SET`) are owned by the separate defined-sets HLD.

### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
The following examples show how the supported OpenConfig routing-policy objects can be configured and retrieved. The IP address, port, username, and password used are illustrative only.

### 3.3.1 Data Models
The OpenConfig YANG modules (openconfig-routing-policy.yang, openconfig-bgp-policy.yang) expose route maps under /routing-policy/policy-definitions/policy-definition, with their referenced prefix, community, AS-path, and tag sets under /routing-policy/defined-sets. The SONiC internal models sonic-route-map.yang and sonic-routing-policy-sets.yang are used in the transformer mapping to CONFIG_DB.

- openconfig-routing-policy.yang
- openconfig-bgp-policy.yang
- openconfig-routing-policy-ext.yang
- sonic-route-map.yang
- sonic-routing-policy-sets.yang

### 3.3.2 REST API Support
GET/PUT/POST/PATCH/DELETE are supported, including at leaf level.

#### 3.3.2.1 GET
Sample GET of a route-map statement with `policy-result`:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10" -H "accept: application/yang-data+json"
{"openconfig-routing-policy:statement":[{"name":"10","config":{"name":"10"},"actions":{"config":{"policy-result":"ACCEPT_ROUTE"}}}]}
```

#### 3.3.2.2 PUT
Sample PUT to create a route-map with a statement and `policy-result`:
```
curl -X PUT -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:policy-definition\":[{\"name\":\"ROUTE\",\"config\":{\"name\":\"ROUTE\"},\"statements\":{\"statement\":[{\"name\":\"10\",\"config\":{\"name\":\"10\"},\"actions\":{\"config\":{\"policy-result\":\"ACCEPT_ROUTE\"}}}]}}]}"
```

#### 3.3.2.3 POST
Sample POST to add a statement under an existing route-map:
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:statement\":[{\"name\":\"20\",\"config\":{\"name\":\"20\"},\"actions\":{\"config\":{\"policy-result\":\"REJECT_ROUTE\"}}}]}"
```

#### 3.3.2.4 PATCH
Sample PATCH to set the BGP next-hop action (IPv4) at leaf level:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10/actions/openconfig-bgp-policy:bgp-actions/config/set-next-hop" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-bgp-policy:set-next-hop\":\"7.7.7.7\"}"
```
Sample PATCH to attach a prefix-set as a match condition:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10/conditions/match-prefix-set/config/prefix-set" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-routing-policy:prefix-set\":\"DEFAULT-ROUTE\"}"
```
Sample PATCH to configure set-community (INLINE + ADD/additive):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10/actions/openconfig-bgp-policy:bgp-actions/set-community" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-bgp-policy:set-community\":{\"config\":{\"method\":\"INLINE\",\"options\":\"ADD\"},\"inline\":{\"config\":{\"communities\":[\"65001:100\"]}}}}"
```

#### 3.3.2.5 DELETE
Example DELETE of the next-hop action (leaf level):
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10/actions/openconfig-bgp-policy:bgp-actions/config/set-next-hop" -H "accept: */*"
```
Example DELETE of a single statement:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE/statements/statement=10" -H "accept: */*"
```
Example DELETE of the entire route-map:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition=ROUTE" -H "accept: */*"
```



### 3.3.3 gNMI Support
gNMI exposes `Get` and `Set` (with `replace`, `update`, and `delete` operations). The examples below were captured against a live target (`172.29.94.154:38575`). Note: for `Set`, target the parent `config` container (or the keyed list entry) and key the value by the container/list name.

#### 3.3.3.1 SET replace (create route-map, ≈ RESTCONF PUT)
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf set --replace-path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]" --replace-value '{"openconfig-routing-policy:policy-definition":[{"name":"ROUTE","config":{"name":"ROUTE"},"statements":{"statement":[{"name":"10","config":{"name":"10"},"actions":{"config":{"policy-result":"ACCEPT_ROUTE"}}}]}}]}'
```
Response:
```
{
  "source": "172.29.94.154:38575",
  "results": [
    {
      "operation": "REPLACE",
      "path": "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]"
    }
  ]
}
```

#### 3.3.3.2 SET update (add a statement, ≈ RESTCONF POST)
Add statement 20 by targeting the keyed list entry directly:
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf set --update-path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=20]" --update-value '{"openconfig-routing-policy:statement":[{"name":"20","config":{"name":"20"},"actions":{"config":{"policy-result":"REJECT_ROUTE"}}}]}'
```
Response:
```
{
  "source": "172.29.94.154:38575",
  "results": [
    {
      "operation": "UPDATE",
      "path": "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=20]"
    }
  ]
}
```

#### 3.3.3.3 SET update (modify a statement, ≈ RESTCONF PATCH)
Set the BGP IPv4 next-hop on statement 10:
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf set --update-path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]/actions/openconfig-bgp-policy:bgp-actions/config" --update-value '{"openconfig-bgp-policy:config":{"set-next-hop":"7.7.7.7"}}'
```
Response:
```
{
  "source": "172.29.94.154:38575",
  "results": [
    {
      "operation": "UPDATE",
      "path": "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]/actions/openconfig-bgp-policy:bgp-actions/config"
    }
  ]
}
```

#### 3.3.3.4 GET
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf get --path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]"
```
Response:
```
[
  {
    "source": "172.29.94.154:38575",
    "timestamp": 1784740156276162748,
    "time": "2026-07-22T22:39:16.276162748+05:30",
    "updates": [
      {
        "Path": "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]",
        "values": {
          "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition/statements/statement": {
            "openconfig-routing-policy:statement": [
              {
                "actions": {
                  "config": { "policy-result": "ACCEPT_ROUTE" },
                  "openconfig-bgp-policy:bgp-actions": {
                    "config": { "set-next-hop": "7.7.7.7" },
                    "state": { "set-next-hop": "7.7.7.7" }
                  },
                  "state": { "policy-result": "ACCEPT_ROUTE" }
                },
                "config": { "name": "10" },
                "name": "10",
                "state": { "name": "10" }
              }
            ]
          }
        }
      }
    ]
  }
]
```

#### 3.3.3.5 SET delete (≈ RESTCONF DELETE)
Delete the next-hop leaf:
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf set --delete "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]/actions/openconfig-bgp-policy:bgp-actions/config/set-next-hop"
```
Response:
```
{
  "source": "172.29.94.154:38575",
  "results": [
    {
      "operation": "DELETE",
      "path": "openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]/statements/statement[name=10]/actions/openconfig-bgp-policy:bgp-actions/config/set-next-hop"
    }
  ]
}
```

### 3.3.4 gNMI Subscription Support
#### 3.3.4.1 Once (ONCE mode)
One-shot snapshot of all route-map policy-definitions:
```
gnmic -a 172.29.94.154:38575 --insecure -e json_ietf subscribe --path "/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=ROUTE]" --target OC-YANG --mode once
```
Response (updates trimmed):
```
{
  "source": "172.29.94.154:38575",
  "subscription-name": "default-1784740796",
  "timestamp": 1784740796439311581,
  "time": "2026-07-22T22:49:56.439311581+05:30",
  "prefix": "openconfig-routing-policy:routing-policy/policy-definitions",
  "target": "OC-YANG",
  "updates": [
    { "Path": "policy-definition[name=ROUTE]/config/name", "values": { "policy-definition/config/name": "ROUTE" } },
    { "Path": "policy-definition[name=ROUTE]/statements/statement[name=10]/actions/config/policy-result", "values": { "policy-definition/statements/statement/actions/config/policy-result": "ACCEPT_ROUTE" } },
    { "Path": "policy-definition[name=ROUTE]/statements/statement[name=20]/actions/config/policy-result", "values": { "policy-definition/statements/statement/actions/config/policy-result": "REJECT_ROUTE" } }
  ]
}
```

# 4 OpenConfig to SONiC Mapping Table
Mapping attributes between OpenConfig YANG and the CONFIG_DB route-map tables. Route-map objects map to `sonic-route-map.yang` (tables `ROUTE_MAP_SET` and `ROUTE_MAP`). The SONiC table/field names correspond to the `sonic-ext` deviations declared in `openconfig-routing-policy-annot.yang`.

All OpenConfig paths below are relative to `/openconfig-routing-policy:routing-policy`.

### Table 3: OpenConfig to SONiC Mapping Table

#### 4.1 Route-Map name registry
**Database Table:** `ROUTE_MAP_SET`
**Key Pattern:** `{name}` (e.g. `ROUTE`)

| OpenConfig YANG Path                       | SONiC DB Table  | SONiC DB Field | Notes                          |
|--------------------------------------------|-----------------|----------------|--------------------------------|
| /policy-definitions/policy-definition/name | ROUTE_MAP_SET   | Key `{name}`   | Route-map name                 |
| ../policy-definition/config/name           | ROUTE_MAP_SET   | Key `{name}`   | Same as list key               |

#### 4.2 Route-Map statement (match / set / flow-control)
**Database Table:** `ROUTE_MAP`
**Key Pattern:** `{name}|{stmt_name}` (e.g. `ROUTE|10`)

| OpenConfig YANG Path                                                      | SONiC DB Table | SONiC DB Field                    | Notes                                                                 |
|---------------------------------------------------------------------------|----------------|-----------------------------------|-----------------------------------------------------------------------|
| .../statements/statement/name                                             | ROUTE_MAP      | Key `{stmt_name}`                 | Statement / sequence number (uint16, 1..65535)                        |
| .../statement/config/name                                                 | ROUTE_MAP      | Key `{stmt_name}`                 | Same as list key                                                      |
| .../statement/config/description (oc-rp-ext)                              | ROUTE_MAP      | description                       | Free-form statement description                                       |
| .../statement/actions/config/policy-result                               | ROUTE_MAP      | route_operation                   | `ACCEPT_ROUTE`→`permit`, `REJECT_ROUTE`→`deny`                        |
| .../statement/actions/config/next-statement (oc-rp-ext)                  | ROUTE_MAP      | next_statement                    | `continue <seq>` behavior                                             |
| .../statement/actions/config/on-match-next (oc-rp-ext)                   | ROUTE_MAP      | on_match_next                     | Boolean; default NEXT behavior                                        |
| .../statement/actions/config/on-match-goto-statement (oc-rp-ext)         | ROUTE_MAP      | on_match_goto_statement           | GOTO target; rejected when `on-match-next=true`                       |
| .../conditions/config/call-policy                                        | ROUTE_MAP      | call_route_map                    | Invoke another route-map                                             |
| .../conditions/config/install-protocol-eq                                | ROUTE_MAP      | match_protocol                    | Only `BGP`→`bgp`, `DIRECTLY_CONNECTED`→`connected`, `STATIC`→`static` |
| .../conditions/match-interface/config/interface                          | ROUTE_MAP      | match_interface                   | `subinterface` leaf is not supported                                  |
| .../conditions/match-prefix-set/config/prefix-set                        | ROUTE_MAP      | match_prefix_set / match_ipv6_prefix_set | Field chosen by referenced prefix-set `mode` (IPv4 vs IPv6)    |
| .../conditions/match-tag-set/config/tag-set                              | ROUTE_MAP      | match_tag                         | Single tag value                                                      |
| .../conditions/bgp-conditions/config/local-pref-eq                       | ROUTE_MAP      | match_local_pref                  | uint32                                                                |
| .../conditions/bgp-conditions/config/med-eq                              | ROUTE_MAP      | match_med                         | uint32                                                                |
| .../conditions/bgp-conditions/config/origin-eq                           | ROUTE_MAP      | match_origin                      | `IGP`/`EGP`/`INCOMPLETE`→`igp`/`egp`/`incomplete`                     |
| .../conditions/bgp-conditions/match-community-set/config/community-set    | ROUTE_MAP      | match_community                   | Leafref to COMMUNITY_SET                                              |
| .../conditions/bgp-conditions/match-ext-community-set/config/ext-community-set | ROUTE_MAP | match_ext_community               | Leafref to EXTENDED_COMMUNITY_SET                                     |
| .../conditions/bgp-conditions/config/ext-community-set                    | ROUTE_MAP      | match_ext_community               | Alias path; same field as match-ext-community-set                    |
| .../conditions/bgp-conditions/match-as-path-set/config/as-path-set        | ROUTE_MAP      | match_as_path                     | Leafref to AS_PATH_SET                                                |
| .../conditions/bgp-conditions/config/match-nexthop-set (oc-rp-ext)       | ROUTE_MAP      | match_next_hop_set                | Leafref to a prefix-set                                              |
| .../conditions/bgp-conditions/config/match-src-network-instance (oc-rp-ext) | ROUTE_MAP   | match_src_vrf                     | Source VRF; `default` for default VRF                                 |
| .../conditions/bgp-conditions/config/match-neighbor (oc-rp-ext)          | ROUTE_MAP      | match_neighbor@                   | Leaf-list, max 1 entry (SONiC limitation)                             |
| .../actions/bgp-actions/config/set-next-hop                              | ROUTE_MAP      | set_next_hop / set_ipv6_next_hop_global / set_ipv6_next_hop_prefer_global | Union split by value (see 4.3)                        |
| .../actions/bgp-actions/config/set-local-pref                            | ROUTE_MAP      | set_local_pref                    | uint32                                                                |
| .../actions/bgp-actions/config/set-med (+ set-med-action)                | ROUTE_MAP      | set_med / set_metric + set_metric_action | Encoding by `set-med-action` (see 4.3)                         |
| .../actions/bgp-actions/config/set-route-origin                          | ROUTE_MAP      | set_origin                        | `IGP`/`EGP`/`INCOMPLETE`→`igp`/`egp`/`incomplete`                     |
| .../actions/bgp-actions/config/set-source-address (oc-rp-ext)            | ROUTE_MAP      | set_src                           | IPv4 or IPv6 address                                                 |
| .../actions/bgp-actions/set-as-path-prepend/config/asn                   | ROUTE_MAP      | set_asn                           | ASN 0 rejected (reserved)                                            |
| .../actions/bgp-actions/set-as-path-prepend/config/repeat-n              | ROUTE_MAP      | set_repeat_asn                    | Requires `asn` to be configured                                      |
| .../actions/bgp-actions/set-as-path-prepend/config/asn-sequence (oc-rp-ext) | ROUTE_MAP   | set_asn_list                      | Space-separated ASN sequence                                         |
| .../actions/bgp-actions/set-community/config/method                       | ROUTE_MAP      | set_community_inline / set_community_ref | `INLINE`→inline field; `REFERENCE`→ref field                  |
| .../actions/bgp-actions/set-community/config/options                      | ROUTE_MAP      | set_community_inline              | `ADD` only (appends ` additive`)                                     |
| .../actions/bgp-actions/set-community/inline/config/communities          | ROUTE_MAP      | set_community_inline              | `method=INLINE`; `options=ADD` appends ` additive` (see 4.3)          |
| .../actions/bgp-actions/set-community/reference/config/community-set-refs | ROUTE_MAP      | set_community_ref                 | `method=REFERENCE`; exactly one ref (SONiC stores single)             |
| .../actions/bgp-actions/set-ext-community/config/method                   | ROUTE_MAP      | set_ext_community_inline / set_ext_community_ref | `INLINE`→inline field; `REFERENCE`→ref field          |
| .../actions/bgp-actions/set-ext-community/config/options                  | ROUTE_MAP      | set_ext_community_inline          | `REPLACE` only                                                       |
| .../actions/bgp-actions/set-ext-community/inline/config/communities      | ROUTE_MAP      | set_ext_community_inline          | `method=INLINE`; `options=REPLACE` only                               |
| .../actions/bgp-actions/set-ext-community/reference/config/ext-community-set-refs | ROUTE_MAP | set_ext_community_ref           | `method=REFERENCE`; exactly one ref                                   |
| .../actions/bgp-actions/set-large-community/config/method (oc-rp-ext)     | ROUTE_MAP      | set_large_community_inline        | `INLINE` only                                                        |
| .../actions/bgp-actions/set-large-community/config/options (oc-rp-ext)    | ROUTE_MAP      | set_large_community_inline        | `ADD` only (appends ` additive`)                                     |
| .../actions/bgp-actions/set-large-community/inline/config/large-communities (oc-rp-ext) | ROUTE_MAP | set_large_community_inline | `method=INLINE` only; `options=ADD` appends ` additive`               |
| .../actions/set-tag/config/mode                                          | ROUTE_MAP      | set_tag                           | `INLINE` only                                                        |
| .../actions/set-tag/inline/config/tag                                    | ROUTE_MAP      | set_tag                           | `mode=INLINE` only; single uint32 value; `set-tag/reference` unsupported |

#### 4.3 Value Encoding
The following OpenConfig leaves do not map 1:1 to a single DB field; the transformer selects/encodes the DB representation:

| OpenConfig leaf / value                        | SONiC DB field(s) written                          | Notes                                                                 |
|------------------------------------------------|----------------------------------------------------|-----------------------------------------------------------------------|
| set-next-hop = IPv4 address                    | set_next_hop                                       | e.g. `7.7.7.7`                                                        |
| set-next-hop = IPv6 address                    | set_ipv6_next_hop_global                           | e.g. `2004::7`                                                        |
| set-next-hop = `PREFER_GLOBAL`                 | set_ipv6_next_hop_prefer_global = `true`           | IPv4/IPv6/PREFER_GLOBAL mutually exclusive per statement              |
| set-med + set-med-action = `SET`               | set_med                                            | `set_metric`/`set_metric_action` cleared                             |
| set-med + set-med-action = `ADD`               | set_metric + set_metric_action = `METRIC_ADD_VALUE` | `set_med` cleared                                                   |
| set-med + set-med-action = `SUBTRACT`          | set_metric + set_metric_action = `METRIC_SUBTRACT_VALUE` | `set_med` cleared                                              |
| set-community inline + options = `ADD`         | set_community_inline = `"<c1> additive, <c2> additive"` | additive suffix per member                                    |
| set-community inline (no options)              | set_community_inline = `"<c1>, <c2>"`              | comma-separated, no suffix                                            |
| set-large-community inline + options = `ADD`   | set_large_community_inline = `"<lc> additive, ..."`| INLINE method only                                                    |
| set-ext-community inline                       | set_ext_community_inline = `"<c1>,<c2>"`           | options only `REPLACE` (FRR replaces unconditionally)                 |
| match-prefix-set (referenced set mode IPv4)    | match_prefix_set                                   | chosen via prefix-set `mode`                                          |
| match-prefix-set (referenced set mode IPv6)    | match_ipv6_prefix_set                              | chosen via prefix-set `mode`                                          |

Translation Notes (constraints not captured by the table above):
- `community-set-refs` / `ext-community-set-refs` accept exactly one non-empty entry because SONiC stores a single reference (`set_community_ref` / `set_ext_community_ref`).
- `install-protocol-eq` supports only `BGP`, `DIRECTLY_CONNECTED`, and `STATIC`.
- `match-neighbor` is a leaf-list limited to a single entry (SONiC `match_neighbor@`).
- Attributes marked `"not-supported": true` in `openconfig-routing-policy-annotation.json` (see Scope) are rejected.

# 5 Error Handling
Invalid configurations report an error. Validations enforced by the transformers and YANG/CVL include:
- `policy-result` accepts only `ACCEPT_ROUTE` (→ `permit`) and `REJECT_ROUTE` (→ `deny`); other enum values are rejected.
- `set-next-hop` must be a valid IPv4 address, IPv6 address, or the `PREFER_GLOBAL` enum. IPv4, IPv6, and PREFER_GLOBAL are mutually exclusive on a statement; a second/conflicting family is rejected.
- `match-prefix-set` resolves the prefix-set address-family (via `getPrefixIpType`) and writes `match_prefix_set` (IPv4) or `match_ipv6_prefix_set` (IPv6); mixing an IPv4 and IPv6 prefix-set on the same statement is rejected.
- `set-community`/`set-ext-community`/`set-large-community` `options` support only additive/replace semantics as applicable: set-community `options=ADD` only; set-ext-community `options=REPLACE` only; set-large-community `method=INLINE` and `options=ADD` only. `options` cannot be configured without inline communities/reference.
- `community-set-refs` / `ext-community-set-refs` must contain exactly one non-empty entry (SONiC stores a single reference).
- `set-med` and `set-med-action` are must-paired; `set-med-action` cannot be set without a MED value in the same request (or already present in DB for PATCH). `set-med` accepts only the numeric (uint32) variant, not the identityref variant.
- `set-as-path-prepend/repeat-n` requires `asn` to be configured.
- `install-protocol-eq` supports only `BGP`, `DIRECTLY_CONNECTED`, and `STATIC`; other protocol identities are rejected as unsupported.
- `set-tag` supports only `mode=INLINE` with a single uint32 tag value; `set-tag/reference` is not supported.
- `set-asn` rejects ASN 0 (reserved).
- `on-match-goto-statement` cannot be used when `on-match-next` is true (enforced by the `must` constraint in `sonic-route-map.yang` / the `-ext` model).

# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Create, verify, and delete a route-map (policy-definition) and statements using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
2. Verify `policy-result` (ACCEPT_ROUTE/REJECT_ROUTE) set/get/delete on statements, and its mapping to SONiC `route_operation` (permit/deny).
3. Verify flow control: `on-match-next`, `on-match-goto-statement`, and `next-statement` set/get/delete.
4. Verify BGP `set-next-hop` for IPv4 (e.g. `7.7.7.7` → `set_next_hop`), IPv6 (e.g. `2004::7` → `set_ipv6_next_hop_global`), and `PREFER_GLOBAL` (→ `set_ipv6_next_hop_prefer_global`).
5. Verify `set-community` INLINE (with `options=ADD` additive) and REFERENCE (`community-set-refs`), and `set-ext-community` INLINE/REFERENCE, and `set-large-community` INLINE.
6. Verify `set-med` with `set-med-action` SET (→ `set_med`) and ADD/SUBTRACT (→ `set_metric` + `set_metric_action`).
7. Verify `set-local-pref`, `set-route-origin`, `set-source-address`, `set-tag`, and `set-as-path-prepend` (asn / repeat-n / asn-sequence).
8. Verify match conditions referencing defined-sets: prefix-set (IPv4 and IPv6 mutual exclusion), community-set, ext-community-set, as-path-set, tag, local-pref, med, origin, install-protocol, and the SONiC-ext next-hop-set / src-network-instance / neighbor.
9. Verify wild-card/subtree GET: `/routing-policy/policy-definitions`.
10. Verify gNMI subscription (ONCE) on `/routing-policy/policy-definitions`.

## 6.2 Negative Test Cases
1. Verify `on-match-goto-statement` together with `on-match-next = true` is rejected (CVL `must` constraint).
2. Verify an invalid `set-next-hop` (not an IP and not `PREFER_GLOBAL`) returns an error.
3. Verify configuring both an IPv4 and an IPv6 `set-next-hop` (or IP + PREFER_GLOBAL) on the same statement returns an error.
4. Verify attaching an IPv4 and an IPv6 prefix-set to the same statement returns an error.
5. Verify `set-community options` without inline communities/reference returns an error; verify `set-ext-community options` other than `REPLACE`, and `set-community options` other than `ADD`, are rejected.
6. Verify `community-set-refs` / `ext-community-set-refs` with zero or more than one entry returns an error.
7. Verify `set-med-action` without a MED value (and no existing MED in DB) returns an error; verify the identityref variant of `set-med` is rejected.
8. Verify `set-as-path-prepend/repeat-n` without `asn` returns an error, and `set-asn = 0` is rejected.
9. Verify an unsupported `install-protocol-eq` value (e.g. `OSPF`, `ISIS`) returns an error.
10. Verify `set-tag` with `mode` other than `INLINE`, or more than one tag entry, returns an error.
11. Verify a GET on a deleted route-map/statement returns a "Resource not found" error.