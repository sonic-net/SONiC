# SR-Policy High-Level Design

## Table of Contents

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
  - [5.1 Functional requirements](#51-functional-requirements)
  - [5.2 Exemptions (not supported)](#52-exemptions-not-supported)
- [6. Architecture Design](#6-architecture-design)
- [7. SR-Policy Objects](#7-sr-policy-objects)
  - [7.1 Segment-List](#71-segment-list)
  - [7.2 Candidate-Path](#72-candidate-path)
  - [7.3 SR-Policy](#73-sr-policy)
  - [7.4 Policy hierarchy](#74-policy-hierarchy)
- [8. YANG Models](#8-yang-models)
  - [8.1 sonic-sr-te.yang](#81-sonic-sr-teyang)
  - [8.2 sonic-static-route.yang color extension](#82-sonic-static-routeyang-color-extension)
- [9. DB Tables](#9-db-tables)
  - [9.1 CONFIG_DB](#91-config_db)
  - [9.2 APPL_DB](#92-appl_db)
  - [9.3 ASIC_DB](#93-asic_db)
- [10. Traffic Steering](#10-traffic-steering)
  - [10.1 Static route with Color:Endpoint nexthop](#101-static-route-with-colorendpoint-nexthop)
  - [10.2 BGP routes with Color extended-community](#102-bgp-routes-with-color-extended-community)
- [11. Detailed Design](#11-detailed-design)
  - [11.1 frrcfgd (SR_TE_SEGMENT_LIST → pathd)](#111-frrcfgd-sr_te_segment_list--pathd)
  - [11.2 orchagent](#112-orchagent)
- [12. CLI Reference](#12-cli-reference)
  - [12.1 Configuration commands](#121-configuration-commands)
  - [12.2 Show commands](#122-show-commands)
  - [12.3 vtysh commands](#123-vtysh-commands)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
- [14. End-to-End Configuration Example](#14-end-to-end-configuration-example)
  - [14.1 Topology](#141-topology)
  - [14.2 Addressing Plan](#142-addressing-plan)
  - [14.3 Base Configuration](#143-base-configuration)
  - [14.4 SR-Policy Configuration](#144-sr-policy-configuration)
  - [14.5 Verification](#145-verification)
  - [14.6 Service Routes Steered into SR-Policies](#146-service-routes-steered-into-sr-policies)
  - [14.7 Debugging SR-Policy Resolution](#147-debugging-sr-policy-resolution)
- [15. Restrictions/Limitations](#15-restrictionslimitations)

## 1. Revision

| Rev | Date       | Author                                                      | Change Description |
|:---:|:----------:|:------------------------------------------------------------|:-------------------|
| 0.1 | 2026-06-29 | Shyam Sethuram, Manoharan Sundaramoorthy, Ravindra Bikkina | Initial version    |

## 2. Scope

This document describes the design of **SR-Policy** (Segment Routing Traffic Engineering
Policy) support in SONiC.

The base SRv6 architecture, locators, static SIDs, and global configuration are covered in:

- [srv6_hld.md](srv6_hld.md) — base SRv6 architecture and `srv6orch`.
- [srv6_static_config_hld.md](srv6_static_config_hld.md) — static locator/SID configuration.
- [srv6_fullsid_hld.md](srv6_fullsid_hld.md) — full-length SID (`End`/`End.X`) support.

**In scope:**

- Static SR-Policy objects: segment-lists, candidate-paths, and policies identified by
  *(Color, Endpoint)*.
- Explicit candidate-paths with `ipv6-address` (Type B) SRv6 SID segments.
- Traffic steering into SR-Policies via:
  - Static routes with a Color:Endpoint nexthop.
  - BGP routes carrying a Color extended-community (RFC 9830).
- YANG, CONFIG_DB, APPL_DB, ASIC_DB schema.
- `frrcfgd` → FRR `pathd` integration.
- `config sr-te` / `show sr-te policy` CLI.

**Out of scope:**

- Dynamic/PCE-computed candidate-paths.
- SR-MPLS and non-`ipv6-address` segment types.
- Binding SIDs (BSID).
- uSID-locator SR-Policy (policies use full-length SIDs).

## 3. Definitions/Abbreviations

| Term            | Definition                                                                    |
|:----------------|:------------------------------------------------------------------------------|
| SR-Policy       | Segment Routing Traffic Engineering Policy, identified by (Color, Endpoint).  |
| SR-TE           | Segment Routing Traffic Engineering.                                          |
| Segment-List    | An ordered list of SRv6 SIDs forming an explicit forwarding path.            |
| Candidate-Path  | A path within an SR-Policy, identified by a preference value.                |
| Color           | An administrative intent/service identifier (uint32) carried with a policy.  |
| Endpoint        | The tail-end (destination) node address of an SR-Policy.                     |
| BSID            | Binding SID — a local SID that steers traffic into a policy (not supported). |
| RNH             | Recursive Nexthop — FRR's mechanism to track nexthop reachability.           |
| pathd           | FRR SR-TE path daemon, manages SR-Policy state.                               |
| H.Encaps.Red    | Reduced SRv6 head-end encapsulation: outer IPv6 DA = first SID, no SRH.      |

## 4. Overview

SR-Policy is a traffic engineering construct that steers packets along an explicitly
provisioned sequence of SRv6 SIDs. A policy is identified by a *(Color, Endpoint)* tuple:
the *Color* encodes an administrative intent (e.g., low-latency, best-effort) and the
*Endpoint* identifies the tail-end node.

Service prefixes are steered into an SR-Policy by tagging them with the matching
*(Color, Endpoint)* — either through a static route or via the BGP Color
extended-community. When the policy is active, matching traffic is SRv6-encapsulated with
the segment list selected by the active candidate-path. When the policy goes inactive (e.g.,
all segment lists become unreachable), traffic falls back to plain IP forwarding.

The SONiC implementation uses FRR's `pathd` daemon as the SR-TE control plane. SONiC's
`frrcfgd` renders CONFIG_DB SR-Policy objects into `pathd` configuration via `vtysh`. FRR
`pathd` maintains the candidate-path and segment-list selection state and notifies `zebra`,
which installs the resolved forwarding entries. `fpmsyncd` writes the resulting SID-list
routes into APPL_DB, and `orchagent` programs the SAI `SRV6_SIDLIST` and `NEXT_HOP` objects
into ASIC_DB.

## 5. Requirements

### 5.1 Functional requirements

1. An operator must be able to define named segment-lists, each consisting of an ordered
   set of SRv6 SIDs indexed by integer position.
2. An operator must be able to define SR-Policies identified by *(Color, Endpoint)* and
   attach one or more explicit candidate-paths to each policy.
3. Each candidate-path must reference one segment-list (current backend limitation).
4. When multiple candidate-paths are configured, the one with the highest preference whose
   segment-list is valid must be selected as the active path.
5. A segment-list must be considered valid only when its first SID is reachable in the RIB.
   Losing SID reachability must immediately invalidate the segment-list and trigger
   candidate-path and policy reselection.
6. Static routes must support a `color` attribute to steer traffic into an SR-Policy via
   a Color:Endpoint nexthop.
7. BGP routes carrying the Color extended-community (RFC 9830) must automatically steer
   into the matching SR-Policy when one is active.
8. When an SR-Policy goes inactive, traffic must fall back to plain IP forwarding without
   operator intervention.

### 5.2 Exemptions (not supported)

- Dynamic/PCE-computed candidate-paths.
- SR-MPLS segment types (MPLS label, NAI-prefix, NAI-adjacency).
- Multiple segment-lists per candidate-path (backend limitation — only one segment-list
  per candidate-path is accepted by FRR `pathd`).
- Binding SIDs (BSID).
- `CO` bits of Color extended-community other than `'00'`.

## 6. Architecture Design

SR-Policy fits into the existing SONiC SRv6 pipeline alongside the existing locator/SID
configuration path. The two paths share the `fpmsyncd`/`orchagent` forwarding pipeline but
diverge at the `frrcfgd` rendering layer:

```
CONFIG_DB
  SR_TE_SEGMENT_LIST  ──┐
  SR_POLICY           ──┴──► frrcfgd ──► pathd (FRR SR-TE)
                                              │
                                         zebra (RNH, policy-route install)
                                              │
                                         fpmsyncd
                                              │
                                         APPL_DB: SRV6_SID_LIST_TABLE
                                              │
                                         orchagent (srv6orch)
                                              │
                                     ASIC_DB: SAI_OBJECT_TYPE_SRV6_SIDLIST
                                              SAI_OBJECT_TYPE_NEXT_HOP
                                              SAI_OBJECT_TYPE_ROUTE_ENTRY
```

Service-route steering is handled entirely within FRR: `staticd` resolves static
Color:Endpoint routes against the SR-Policy state maintained by `pathd`/`zebra`.
BGP Color extended-communities are resolved by `bgpd`. The resolved forwarding entries
flow through `fpmsyncd` → APPL_DB → `orchagent` → ASIC_DB via the standard route pipeline.

## 7. SR-Policy Objects

### 7.1 Segment-List

A segment-list is a named, ordered set of SRv6 SIDs. Each SID entry is identified by an
integer index that determines its position in the stack; indices need not be consecutive
(e.g., 10, 20, 30 allows later insertion of 15). The same segment-list can be referenced
by multiple candidate-paths.

A segment-list is **valid** when its first SID is reachable in the RIB. FRR's recursive
nexthop tracking (RNH) monitors this continuously; reachability loss immediately marks the
segment-list invalid.

### 7.2 Candidate-Path

A candidate-path is a named path within an SR-Policy, uniquely identified by its
*preference* value (higher = more preferred). It is provisioned with an explicit type and
references one segment-list.

A candidate-path is **active** when it has at least one valid segment-list. When multiple
candidate-paths are configured, the one with the highest preference among the active ones
is selected for forwarding.

### 7.3 SR-Policy

An SR-Policy is identified by the tuple *(Color, Endpoint)*. It groups one or more
candidate-paths and exposes the active path's segment-list for forwarding.

An SR-Policy is **active** when at least one of its candidate-paths is active. An inactive
SR-Policy causes all service routes steered into it to fall back to plain IP forwarding.

### 7.4 Policy hierarchy

```
  Segment-List11 <Name>
    SID1
    SID2
    SID3
    ...
  Segment-List12 <Name>
    SID1
    SID2
    ...
  ...

  SR-Policy1 <Color, Endpoint>
    Candidate-Path1 <Preference>
      Segment-List11 <Name>, Weight
      Segment-List12 <Name>, Weight   ← weight reserved; currently one seg-list per CP
      ...
    Candidate-Path2 <Preference>
      Segment-List21 <Name>, Weight
      ...
    ...
  SR-Policy2 <Color, Endpoint>
    ...
```

## 8. YANG Models

### 8.1 sonic-sr-te.yang

```yang
typedef sbfd-mode {
    type enumeration {
        enum enable {
            description "Enable Seamless BFD (sBFD)";
        }
        enum disable {
            description "Disable Seamless BFD (sBFD)";
        }
    }
    default "disable";
    description "sBFD operational mode";
}

container sonic-sr-te {
    container SR_TE_GLOBAL {
        description "Global SR-TE configuration parameters";

        list SR_TE_GLOBAL_LIST {
            max-elements 1;
            key "name";

            leaf name {
                type string {
                    pattern "default";
                }
                description "Global configuration key (must be 'default')";
            }

            leaf sbfd {
                type sbfd-mode;
                description "Global sBFD default for all SR-TE policies";
            }

            leaf sbfd-profile {
                type leafref {
                    path "/bfd:sonic-bfd/bfd:BFD_PROFILE/bfd:BFD_PROFILE_LIST/bfd:profile_name";
                }
                when "../sbfd = 'enable'";
                description "Reference to a BFD profile to use for sBFD sessions";
            }
        }
    }
    /* end of container SR_TE_GLOBAL */

    container SR_TE_SEGMENT_LIST {
        description "Segment list configuration for SR policies";

        list SR_TE_SEGMENT_LIST_LIST {
            key "name index";

            leaf name {
                type string { length "1..255"; }
                description "Segment list name";
            }

            leaf index {
                type uint32 { range "1..65535"; }
                description
                    "Segment index — determines the order of segments in the path.
                     Indices do not need to be consecutive, allowing insertion of
                     segments between existing ones (e.g., 10, 20, 30 allows inserting 15).";
            }

            leaf segment_type {
                type enumeration {
                    enum ipv6-address {
                        description "SRv6 SID (Type B) - IPv6 address";
                    }
                    // Future segment types (not yet supported in backend):
                    // enum mpls-label
                    // enum nai-prefix-v4 / nai-prefix-v6
                    // enum nai-adjacency-v4 / nai-adjacency-v6
                }
                default "ipv6-address";
                description "Type of segment. Currently only ipv6-address (SRv6 Type B) is supported.";
            }

            leaf ipv6_address {
                type inet:ipv6-address;
                when "../segment_type = 'ipv6-address'";
                mandatory true;
                description "SRv6 SID IPv6 address (Type B segment, RFC 9256). Required when segment_type is 'ipv6-address'.";
            }
        }
    }
    /* end of container SR_TE_SEGMENT_LIST */

    container SR_POLICY {
        description
            "SR policy configuration — variable-length keys represent the hierarchy.
             2-part key (color|endpoint)                 = Policy
             3-part key (color|endpoint|preference)      = Candidate Path
             4-part key (color|endpoint|preference|name) = Segment List Association";

        list SR_POLICY_LIST {
            key "color endpoint";
            unique "name";

            leaf color {
                type uint32 { range "1..4294967295"; }
                description "Policy color (distinguisher)";
            }

            leaf endpoint {
                type inet:ip-address;
                description "Policy endpoint (IPv4 or IPv6 address)";
            }

            leaf name {
                type string { length "1..255"; }
                description
                    "Policy name — must be unique across all policies.
                     Note: once set, the policy name cannot be modified.";
            }

            leaf sbfd {
                type sbfd-mode;
                description "sBFD mode for this SR policy; overrides the global default";
            }

            leaf sbfd-profile {
                type leafref {
                    path "/bfd:sonic-bfd/bfd:BFD_PROFILE/bfd:BFD_PROFILE_LIST/bfd:profile_name";
                }
                when "../sbfd = 'enable'";
                description "Reference to a BFD profile; applicable only when sbfd is 'enable'";
            }
        }
        /* end of list SR_POLICY_LIST */

        list SR_POLICY_CANDIDATE_PATH_LIST {
            key "color endpoint preference";
            unique "color endpoint name";

            must "/srte:sonic-sr-te/srte:SR_POLICY/srte:SR_POLICY_LIST[srte:color=current()/color][srte:endpoint=current()/endpoint]" {
                error-message "Candidate path must reference an existing SR_POLICY (color|endpoint)";
            }

            leaf color {
                type uint32 { range "1..4294967295"; }
                description "Policy color — must match an existing SR_POLICY entry";
            }

            leaf endpoint {
                type inet:ip-address;
                description "Policy endpoint — must match an existing SR_POLICY entry";
            }

            leaf preference {
                type uint32 { range "1..4294967295"; }
                description "Candidate path preference (higher value = higher preference)";
            }

            leaf name {
                type string { length "1..255"; }
                mandatory true;
                description "Candidate path name (required by the routing backend)";
            }

            leaf type {
                type enumeration {
                    enum explicit {
                        description "Explicit path using segment list";
                    }
                    // Future: dynamic (not yet supported in backend)
                }
                default "explicit";
                description "Candidate path type. Currently only 'explicit' is supported.";
            }

            leaf sbfd {
                type sbfd-mode;
                description "sBFD mode for this candidate path; overrides the policy setting";
            }

            leaf sbfd-profile {
                type leafref {
                    path "/bfd:sonic-bfd/bfd:BFD_PROFILE/bfd:BFD_PROFILE_LIST/bfd:profile_name";
                }
                when "../sbfd = 'enable'";
                description "Reference to a BFD profile; applicable only when sbfd is 'enable'";
            }
        }
        /* end of list SR_POLICY_CANDIDATE_PATH_LIST */

        list SR_POLICY_CANDIDATE_PATH_SEGMENT_LIST_LIST {
            key "color endpoint preference name";

            must "count(/srte:sonic-sr-te/srte:SR_POLICY/srte:SR_POLICY_CANDIDATE_PATH_SEGMENT_LIST_LIST[srte:color=current()/color][srte:endpoint=current()/endpoint][srte:preference=current()/preference]) = 1" {
                error-message "Only one segment list is allowed per candidate path (color|endpoint|preference). Backend limitation.";
            }

            must "/srte:sonic-sr-te/srte:SR_POLICY/srte:SR_POLICY_CANDIDATE_PATH_LIST[srte:color=current()/color][srte:endpoint=current()/endpoint][srte:preference=current()/preference]" {
                error-message "Segment list association must reference an existing SR_POLICY_CANDIDATE_PATH (color|endpoint|preference)";
            }

            must "/srte:sonic-sr-te/srte:SR_POLICY/srte:SR_POLICY_CANDIDATE_PATH_LIST[srte:color=current()/color][srte:endpoint=current()/endpoint][srte:preference=current()/preference]/srte:type = 'explicit'" {
                error-message "Segment list can only be associated with explicit candidate paths.";
            }

            leaf color {
                type uint32 { range "1..4294967295"; }
            }

            leaf endpoint {
                type inet:ip-address;
            }

            leaf preference {
                type uint32 { range "1..4294967295"; }
            }

            leaf name {
                type leafref {
                    path "/srte:sonic-sr-te/srte:SR_TE_SEGMENT_LIST/srte:SR_TE_SEGMENT_LIST_LIST/srte:name";
                }
                description "Name of the segment list to associate with this candidate path";
            }

            leaf weight {
                type uint32 { range "1..4294967295"; }
                default "1";
                description
                    "Weight for weighted ECMP when multiple segment lists are configured.
                     Note: The routing backend currently supports only one segment list per candidate path.";
            }
        }
        /* end of list SR_POLICY_CANDIDATE_PATH_SEGMENT_LIST_LIST */
    }
    /* end of container SR_POLICY */
}
/* end of container sonic-sr-te */
```

### 8.2 sonic-static-route.yang color extension

The `color` leaf is added to both `STATIC_ROUTE_TEMPLATE_LIST` and `STATIC_ROUTE_LIST` to
allow static service routes to be steered into an SR-Policy by Color:Endpoint nexthop.

```yang
leaf color {
    type string {
        pattern "(0|[1-9][0-9]{0,9})(,(0|[1-9][0-9]{0,9}))*";
    }
    default "0";
    description
        "SR-Policy color value for the nexthop (0-4294967295), comma-separated for multiple nexthops.
         Value 0 means no SR-Policy color (backward-compatible default).
         When specified, the static route will steer over the SR-Policy matching this color and the
         route's nexthop endpoint.";
}
```

## 9. DB Tables

### 9.1 CONFIG_DB

```
DB Name:    CONFIG_DB
Table Name: SR_TE_SEGMENT_LIST

key = SR_TE_SEGMENT_LIST|<seglist_name>|<index>

name         : <seglist_name>   # segment-list name
index        : <index>          # position of this SID in the list
segment_type : <type>           # e.g. ipv6-address
ipv6_address : <sid_addr>       # the SID at this index
```

```
DB Name:    CONFIG_DB
Table Name: SR_POLICY

# Policy key (2-part)
key = SR_POLICY|<color>|<endpoint>
  color    : <color>
  endpoint : <endpoint>
  name     : <pol_name>

# Candidate-path key (3-part)
key = SR_POLICY|<color>|<endpoint>|<preference>
  color      : <color>
  endpoint   : <endpoint>
  preference : <preference>
  name       : <cp_name>
  type       : explicit

# Candidate-path segment-list association (4-part)
key = SR_POLICY|<color>|<endpoint>|<preference>|<seglist_name>
  color      : <color>
  endpoint   : <endpoint>
  preference : <preference>
  name       : <seglist_name>
  weight     : <weight>       # default 1
```

### 9.2 APPL_DB

```
DB Name:    APPL_DB
Table Name: SRV6_SID_LIST_TABLE

key = SRV6_SID_LIST_TABLE:<seg1>|<seg2>|<seg3>

path : <seg1,seg2,seg3>   # ordered comma-separated SID list
```

### 9.3 ASIC_DB

```
DB Name:    ASIC_DB
Table Name: ASIC_STATE:SAI_OBJECT_TYPE_SRV6_SIDLIST

key = ASIC_STATE:SAI_OBJECT_TYPE_SRV6_SIDLIST:<oid>

SAI_SRV6_SIDLIST_ATTR_SEGMENT_LIST : <count:seg1,seg2,seg3>  # programmed SID stack
SAI_SRV6_SIDLIST_ATTR_TYPE         : <SAI SID-list type>     # e.g. ENCAPS_RED
```

```
DB Name:    ASIC_DB
Table Name: ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP

key = ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:{<oid>}

SAI_NEXT_HOP_ATTR_TYPE            : SAI_NEXT_HOP_TYPE_SRV6_SIDLIST
SAI_NEXT_HOP_ATTR_SRV6_SIDLIST_ID : <sidlist oid>
SAI_NEXT_HOP_ATTR_TUNNEL_ID       : <srv6 tunnel oid>
```

```
DB Name:    ASIC_DB
Table Name: ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL

key = ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL:oid:{<oid>}

SAI_TUNNEL_ATTR_TYPE               : SAI_TUNNEL_TYPE_SRV6
SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE : <intf oid>
SAI_TUNNEL_ATTR_ENCAP_SRC_IP       : <ipv6_addr>   # global encap source address
```

```
DB Name:    ASIC_DB
Table Name: ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY

key = ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:{<dest, switch_id, vr>}

SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID : <nexthop oid>   # points to the SRv6 nexthop
```

## 10. Traffic Steering

Service routes are steered into an SR-Policy when they carry a *(Color, Endpoint)* that
matches an active policy. When the policy is active, the route is installed in the FIB
with the SR-Policy's segment list. When the policy goes inactive, the route falls back to
plain IP forwarding using the endpoint address as an ordinary nexthop.

### 10.1 Static route with Color:Endpoint nexthop

An operator installs a static service route pointing to a nexthop address and a color
value. FRR's `staticd` resolves this route recursively against the SR-Policy state
maintained by `pathd`/`zebra`.

```
config route add prefix <prefix> nexthop <endpoint> color <color>
config route del prefix <prefix> nexthop <endpoint> color <color>
```

**Example:**
```
$ sudo config route add prefix 172.16.100.0/24 nexthop 10.0.0.4 color 100
$ sudo config route add prefix 2001:db8:100::/48 nexthop fc00::4 color 100
```

### 10.2 BGP routes with Color extended-community

The Color extended-community (RFC 9830) carries the Color value on a BGP path. When a BGP
route is received with a Color EC, the nexthop of the BGP prefix is treated as the Endpoint
and the Color value selects the matching SR-Policy. If the policy is active, the BGP route
is forwarded via the SR-Policy. If not, it is forwarded via plain IP.

If more than one Color extended-community is received on a single path, the highest color
value is used.

> Note: Processing of `CO` bits of the Color extended-community is limited to `'00'` value only.

## 11. Detailed Design

### 11.1 frrcfgd (SR_TE_SEGMENT_LIST → pathd)

`frrcfgd.py` subscribes to `SR_TE_SEGMENT_LIST` CONFIG_DB changes and renders them into
FRR `pathd` CLI via `vtysh`. The table-to-daemon routing is:

```python
'SR_TE_SEGMENT_LIST': ['pathd'],
```

For each segment-list entry (`name`, `index`, `ipv6_address`), `frrcfgd` emits:

```
segment-routing
 traffic-eng
  segment-list <name>
   index <index> mpls label <sid>    # rendered as SRv6 SID
  !
 !
!
```

Similarly, `SR_POLICY` entries are rendered into `pathd` policy/candidate-path/segment-list
CLI that `pathd` uses to build and select the active path.

`pathd` monitors segment-list SID reachability via RNH subscriptions to `zebra`, selects
the best candidate-path per policy, and notifies `zebra` of policy state changes. `zebra`
installs the resolved SR-TE forwarding entries into the FIB, which `fpmsyncd` then writes
into APPL_DB `SRV6_SID_LIST_TABLE`.

### 11.2 orchagent

`orchagent` consumes `SRV6_SID_LIST_TABLE` from APPL_DB and programs:

1. `SAI_OBJECT_TYPE_SRV6_SIDLIST` — the SID stack (one SAI object per unique segment-list).
2. `SAI_OBJECT_TYPE_NEXT_HOP` with `SAI_NEXT_HOP_TYPE_SRV6_SIDLIST` pointing to the SID
   list and the shared SRv6 tunnel object.
3. `SAI_OBJECT_TYPE_ROUTE_ENTRY` for each service prefix, pointing to the SRv6 nexthop.

When a service route falls back from SR-TE to plain IP (policy inactive), `orchagent`
reprograms the route with a regular IP nexthop.

## 12. CLI Reference

### 12.1 Configuration commands

#### config sr-te segment-list

```
config sr-te segment-list add <seglist_name> <index> --ipv6-address <sid_addr>
config sr-te segment-list del <seglist_name> [<index>]
```

- `<seglist_name>` — segment-list name.
- `<index>` — position of the SID within the segment-list.
- `<sid_addr>` — SID IPv6 address at this index.
- Omitting `<index>` from `del` deletes the entire segment-list.

**Example:**
```
$ sudo config sr-te segment-list add sl11 20 --ipv6-address fd00:db8:2:1::
$ sudo config sr-te segment-list add sl11 30 --ipv6-address fd00:db8:3:1::
$ sudo config sr-te segment-list del sl11 30
$ sudo config sr-te segment-list del sl11
```

#### config sr-te policy

```
config sr-te policy add <color> <endpoint> <pol_name>
config sr-te policy del <color> <endpoint>

config sr-te policy candidate-path add <color> <endpoint> <preference> <cp_name> --type explicit
config sr-te policy candidate-path del <color> <endpoint> <preference>

config sr-te policy candidate-path segment-list add <color> <endpoint> <preference> <seglist_name>
config sr-te policy candidate-path segment-list del <color> <endpoint> <preference> <seglist_name>
```

- `<color>` — policy color (administrative intent).
- `<endpoint>` — policy endpoint (tail-end address, IPv4 or IPv6).
- `<pol_name>` — policy name (unique, immutable after creation).
- `<preference>` — candidate-path preference (higher = more preferred).
- `<cp_name>` — candidate-path name.
- `--type explicit` — only explicit paths are supported.
- `<seglist_name>` — name of a configured segment-list.

**Example:**
```
$ sudo config sr-te policy add 100 10.0.0.4 srp1

$ sudo config sr-te policy candidate-path add 100 10.0.0.4 250 cp250 --type explicit
$ sudo config sr-te policy candidate-path segment-list add 100 10.0.0.4 250 sl11

$ sudo config sr-te policy candidate-path add 100 10.0.0.4 150 cp150 --type explicit
$ sudo config sr-te policy candidate-path segment-list add 100 10.0.0.4 150 sl21
```

Teardown order must be bottom-up (segment-list → candidate-path → policy):
```
$ sudo config sr-te policy candidate-path segment-list del 100 10.0.0.4 250 sl11
$ sudo config sr-te policy candidate-path del 100 10.0.0.4 250
$ sudo config sr-te policy del 100 10.0.0.4
```

#### config route (Color:Endpoint steering)

```
config route add prefix <prefix> nexthop <endpoint> color <color>
config route del prefix <prefix> nexthop <endpoint> color <color>
```

**Example:**
```
$ sudo config route add prefix 172.16.100.0/24 nexthop 10.0.0.4 color 100
$ sudo config route del prefix 172.16.100.0/24 nexthop 10.0.0.4 color 100
```

### 12.2 Show commands

#### show sr-te policy

```
show sr-te policy [detail]
show sr-te policy rib [color <color> endpoint <endpoint>]
```

- `detail` — show per-candidate-path and segment-list detail.
- `color` / `endpoint` — filter the rib view.

**Example:**
```
$ show sr-te policy
 Endpoint  Color  Name          BSID  Status  Type
 ---------------------------------------------------
 10.0.0.4  100    pol-r4-v4-be  -     Active  SRV6
 10.0.0.4  200    pol-r4-v4-ll  -     Active  SRV6
 fc00::4   100    pol-r4-v6-be  -     Active  SRV6
 fc00::4   200    pol-r4-v6-ll  -     Active  SRV6

$ show sr-te policy detail

Endpoint: 10.0.0.4  Color: 100  Name: pol-r4-v4-be  BSID: -  Status: Active Type: SRV6
  * Preference: 250  Name: cp250  Type: explicit  Protocol-Origin: Local
    Segment-List: sl11                            Weight: 1    valid
    Preference: 150  Name: cp150  Type: explicit  Protocol-Origin: Local
    Segment-List: sl21                            Weight: 1    valid

$ show sr-te policy rib color 100 endpoint 10.0.0.4
Color: 100  Endpoint: 10.0.0.4
  Type: SRv6
  Status: UP
  Name: pol-r4-v4-be
  VRF: default
  SRv6 Segment List [0] (weight 1) valid:
    SID Stack: [fd00:db8:2:1::]
    Via:
      ifindex 656 (ifindex 656)
```

### 12.3 vtysh commands

The following `vtysh` (FRR shell) commands are useful for observing SR-Policy state.

```
# Segment-list resolution state
show sr-te segment-lists

# Per-SID RNH resolution and segment-list membership
show sr-te segment srv6-rnh

# Nexthop tracking — shows color-annotated SR-TE NHT entries
show ipv6 nht
show ip nht

# FRR route table — shows SR-TE annotation on resolved routes
show {ip | ipv6} route [<prefix>]
```

## 13. Testing Requirements/Design

### 13.1 YANG model tests

- `sonic-yang-models/tests/yang_model_tests/tests/sr_policy.json`

### 13.2 CLI tests

- `sonic-utilities/tests/sr_policy_test.py`

### 13.3 DVS tests

- `sonic-swss/tests/test_srv6.py`

### 13.4 sonic-mgmt tests

- `sonic-mgmt/tests/srv6/test_srv6_srpolicy_basic.py`
  - Static SR-Policy with explicit candidate-paths
  - Single-SID and multi-SID segment lists
  - Policy failover: SID goes unreachable → policy inactive → route falls back to IP
  - Policy recovery: SID becomes reachable → policy active → route re-steers
  - Static service routes steered via Color:Endpoint nexthop
  - BGP routes steered via Color extended-community

## 14. End-to-End Configuration Example

This chapter walks through a complete SR-Policy setup from scratch on a four-node diamond
topology. All commands are issued on **R1 (the DUT)**.

### 14.1 Topology

```
                    R2 (10.0.0.2 / fc00::2)
                   /                         \
                  / 10.1.12.0/30               \ 10.1.24.0/30
R1 ---[Ethernet0]-   2001:db8:12::/64            --- R4 (10.0.0.4 / fc00::4)
(DUT)                                           /
R1 ---[Ethernet4]-   2001:db8:13::/64           /--- R4
                  \ 10.1.13.0/30               / 10.1.34.0/30
                   \                         /
                    R3 (10.0.0.3 / fc00::3)
```

- **R1** is the SR-Policy headend (DUT).
- **R4** is the SR-Policy tailend; its loopbacks are the policy endpoints.
- Traffic colored **100** takes the R1→R2→R4 path (best-effort).
- Traffic colored **200** takes the R1→R3→R4 path (low-latency).

### 14.2 Addressing Plan

**Loopback addresses**

| Node | IPv4 loopback | IPv6 loopback |
|------|---------------|---------------|
| R1   | 10.0.0.1/32   | fc00::1/128   |
| R2   | 10.0.0.2/32   | fc00::2/128   |
| R3   | 10.0.0.3/32   | fc00::3/128   |
| R4   | 10.0.0.4/32   | fc00::4/128   |

**Link addresses**

| Link  | R1 Interface | IPv4 subnet  | R1 address   | R2/R3 address |
|-------|--------------|--------------|--------------|---------------|
| R1–R2 | Ethernet0    | 10.1.12.0/30 | 10.1.12.1/30 | 10.1.12.2/30  |
| R1–R3 | Ethernet4    | 10.1.13.0/30 | 10.1.13.1/30 | 10.1.13.2/30  |

| Link  | IPv6 subnet       | R1 address        | R2/R3 address     |
|-------|-------------------|-------------------|-------------------|
| R1–R2 | 2001:db8:12::/64  | 2001:db8:12::1/64 | 2001:db8:12::2/64 |
| R1–R3 | 2001:db8:13::/64  | 2001:db8:13::1/64 | 2001:db8:13::2/64 |

**SRv6 locators** — block `fd00:db8::/32`, 16-bit node-ID, 16-bit function

| Node | Locator prefix  | End SID (function=1) |
|------|-----------------|----------------------|
| R1   | fd00:db8:1::/48 | fd00:db8:1:1::/128   |
| R2   | fd00:db8:2::/48 | fd00:db8:2:1::/128   |
| R3   | fd00:db8:3::/48 | fd00:db8:3:1::/128   |
| R4   | fd00:db8:4::/48 | fd00:db8:4:1::/128   |

**SR-Policy summary**

| Policy name  | Color | Endpoint | Path via | Segment list |
|--------------|-------|----------|----------|--------------|
| pol-r4-v4-be | 100   | 10.0.0.4 | R2       | sl-via-r2    |
| pol-r4-v4-ll | 200   | 10.0.0.4 | R3       | sl-via-r3    |
| pol-r4-v6-be | 100   | fc00::4  | R2       | sl-via-r2    |
| pol-r4-v6-ll | 200   | fc00::4  | R3       | sl-via-r3    |

### 14.3 Base Configuration

The following base configuration is required before SR-Policy objects can be provisioned.
It establishes interface addresses, enables SRv6, creates R1's locator and End SID, and
installs underlay routes to remote locators so segment-list SIDs are resolvable.

```
# Interface addresses
$ sudo config interface ip add Loopback0 10.0.0.1/32
$ sudo config interface ip add Loopback0 fc00::1/128
$ sudo config interface ip add Ethernet0 10.1.12.1/30
$ sudo config interface ip add Ethernet0 2001:db8:12::1/64
$ sudo config interface ip add Ethernet4 10.1.13.1/30
$ sudo config interface ip add Ethernet4 2001:db8:13::1/64

# Enable SRv6 and set encap source
$ sudo config srv6 global device_srv6_enabled true
$ sudo config srv6 global encap_source_address fc00::1

# Create R1's locator
$ sudo config srv6 locator add loc-r1 fd00:db8:1::/48 \
    --block-len 32 --node-len 16 --function-len 16

# Allocate R1's End SID
$ sudo config srv6 static-sid add fd00:db8:1:1::/128 loc-r1 End

# Underlay routes to remote locators (so SIDs are resolvable)
$ sudo config route add prefix fd00:db8:2::/48 nexthop 2001:db8:12::2
$ sudo config route add prefix fd00:db8:3::/48 nexthop 2001:db8:13::2
$ sudo config route add prefix fd00:db8:4::/48 nexthop 2001:db8:12::2
```

### 14.4 SR-Policy Configuration

#### Segment lists

Two segment lists are defined — one per transit node. Each carries the transit node's
`End` SID as its single entry.

```
$ sudo config sr-te segment-list add sl-via-r2 10 --ipv6-address fd00:db8:2:1::
$ sudo config sr-te segment-list add sl-via-r3 10 --ipv6-address fd00:db8:3:1::
```

The same segment lists are reused by both the IPv4-endpoint and IPv6-endpoint policies.

#### Policies — IPv4 endpoint (10.0.0.4)

```
# Color 100 — best-effort via R2
$ sudo config sr-te policy add 100 10.0.0.4 pol-r4-v4-be
$ sudo config sr-te policy candidate-path add 100 10.0.0.4 100 cp-r4-v4-be --type explicit
$ sudo config sr-te policy candidate-path segment-list add 100 10.0.0.4 100 sl-via-r2

# Color 200 — low-latency via R3
$ sudo config sr-te policy add 200 10.0.0.4 pol-r4-v4-ll
$ sudo config sr-te policy candidate-path add 200 10.0.0.4 100 cp-r4-v4-ll --type explicit
$ sudo config sr-te policy candidate-path segment-list add 200 10.0.0.4 100 sl-via-r3
```

#### Policies — IPv6 endpoint (fc00::4)

```
# Color 100 — best-effort via R2
$ sudo config sr-te policy add 100 fc00::4 pol-r4-v6-be
$ sudo config sr-te policy candidate-path add 100 fc00::4 100 cp-r4-v6-be --type explicit
$ sudo config sr-te policy candidate-path segment-list add 100 fc00::4 100 sl-via-r2

# Color 200 — low-latency via R3
$ sudo config sr-te policy add 200 fc00::4 pol-r4-v6-ll
$ sudo config sr-te policy candidate-path add 200 fc00::4 100 cp-r4-v6-ll --type explicit
$ sudo config sr-te policy candidate-path segment-list add 200 fc00::4 100 sl-via-r3
```

### 14.5 Verification

```
$ show sr-te policy
 Endpoint  Color  Name          BSID  Status  Type
 ---------------------------------------------------
 10.0.0.4  100    pol-r4-v4-be  -     Active  SRV6
 10.0.0.4  200    pol-r4-v4-ll  -     Active  SRV6
 fc00::4   100    pol-r4-v6-be  -     Active  SRV6
 fc00::4   200    pol-r4-v6-ll  -     Active  SRV6

$ show sr-te policy detail

Endpoint: 10.0.0.4  Color: 100  Name: pol-r4-v4-be  BSID: -  Status: Active Type: SRV6
  * Preference: 100  Name: cp-r4-v4-be  Type: explicit  Protocol-Origin: Local
    Segment-List: sl-via-r2                       Weight: 1    valid

Endpoint: 10.0.0.4  Color: 200  Name: pol-r4-v4-ll  BSID: -  Status: Active Type: SRV6
  * Preference: 100  Name: cp-r4-v4-ll  Type: explicit  Protocol-Origin: Local
    Segment-List: sl-via-r3                       Weight: 1    valid

Endpoint: fc00::4  Color: 100  Name: pol-r4-v6-be  BSID: -  Status: Active Type: SRV6
  * Preference: 100  Name: cp-r4-v6-be  Type: explicit  Protocol-Origin: Local
    Segment-List: sl-via-r2                       Weight: 1    valid

Endpoint: fc00::4  Color: 200  Name: pol-r4-v6-ll  BSID: -  Status: Active Type: SRV6
  * Preference: 100  Name: cp-r4-v6-ll  Type: explicit  Protocol-Origin: Local
    Segment-List: sl-via-r3                       Weight: 1    valid
```

The `*` marks the active candidate path. `valid` confirms the segment list resolved
against the underlay. BSID is empty because no Binding SID is assigned.

```
$ show sr-te policy rib
Color  Endpoint                                 Type     Status
------ ---------------------------------------- -------- ----------
100    10.0.0.4                                 SRv6     UP
200    10.0.0.4                                 SRv6     UP
100    fc00::4                                  SRv6     UP
200    fc00::4                                  SRv6     UP

Total: 4 policies
```

### 14.6 Service Routes Steered into SR-Policies

Install static service routes using Color:Endpoint nexthops:

```
$ sudo config route add prefix 172.16.100.0/24 nexthop 10.0.0.4 color 100
$ sudo config route add prefix 172.16.200.0/24 nexthop 10.0.0.4 color 200
$ sudo config route add prefix 2001:db8:100::/48 nexthop fc00::4 color 100
$ sudo config route add prefix 2001:db8:200::/48 nexthop fc00::4 color 200
```

**Verifying recursive resolution:**

```
$ show ip route 172.16.100.0/24
Routing entry for 172.16.100.0/24
  Known via "static", distance 1, metric 0, tag 1, best
  Last update 00:04:38 ago
  Flags: Recursion Selected RR Distance
  Status: Installed
    10.0.0.4 (recursive), srv6(endpoint|color):a00:4::|100, weight 1
  *   2001:db8:12::2, via Ethernet0, seg6 fd00:db8:2:1::, srv6(endpoint|color):2001:db8:12::2|0, weight 1
```

- The unstarred line is the SR-Policy nexthop: `a00:4::` is `10.0.0.4` in hex, `|100` is the color.
- The `*` line is the resolved FIB entry: outgoing interface + SRv6 SID to push.
- `Status: Installed` confirms the route is programmed to the ASIC.

**APPL_DB:**

```
$ redis-cli -n 0 hgetall 'ROUTE_TABLE:172.16.100.0/24'
segment
fd00:db8:2:1::
seg_src
fc00::1

$ redis-cli -n 0 hgetall 'ROUTE_TABLE:172.16.200.0/24'
segment
fd00:db8:3:1::
seg_src
fc00::1
```

**ASIC_DB (color-100 routes):**

Both `172.16.100.0/24` and `2001:db8:100::/48` share the same nexthop and SID-list OID
because they map to the same SR-Policy.

```
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP:oid:0x4000000000601'
SAI_NEXT_HOP_ATTR_TYPE
SAI_NEXT_HOP_TYPE_SRV6_SIDLIST
SAI_NEXT_HOP_ATTR_SRV6_SIDLIST_ID
oid:0x3d000000000600
SAI_NEXT_HOP_ATTR_TUNNEL_ID
oid:0x2a0000000005ff

$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_SRV6_SIDLIST:oid:0x3d000000000600'
SAI_SRV6_SIDLIST_ATTR_SEGMENT_LIST
1:fd00:db8:2:1::
SAI_SRV6_SIDLIST_ATTR_TYPE
SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED
```

### 14.7 Debugging SR-Policy Resolution

#### How an SR-Policy becomes active

An SR-Policy's active state is determined bottom-up through a dependency chain:

```
SR-Policy active
  └── at least one candidate-path is active
        └── at least one segment-list is valid
              └── the first SID in the segment-list is reachable (RNH resolved)
```

Breaking any link deactivates the policy and causes service routes to fall back to plain IP.

#### Segment-list resolution

```
$ sudo vtysh -c 'show sr-te segment-lists'
Segment-List: sl-via-r2
  Type: SRv6
  Protocol-Origin: Local
  Resolution: Resolved
  Segments:
    Index 10: fd00:db8:2:1::
```

`Resolution: Resolved` means the SID is reachable via the RIB.

#### SRv6 SID RNH resolution

```
$ sudo vtysh -c 'show sr-te segment srv6-rnh'
SRv6 SID resolution via IPv6 route: enabled.
SRv6 SID: fd00:db8:2:1::
  Resolution: RESOLVED
  RNH Registered: Yes
  Segment-Lists (1):
    [1] sl-via-r2 (origin: Local, type: SRv6)
```

`RNH Registered: Yes` confirms that SID reachability is actively tracked. All segment-lists
dependent on this SID are listed — useful when multiple segment-lists share the same SID.

#### Nexthop tracking (NHT)

```
$ sudo vtysh -c 'show ipv6 nht'
VRF default:
...
fc00::4 (SR-TE color)
 SR-TE color: 100
 resolved via srte, prefix ::/0
 via fc00::4 (vrf default), SR-TE color 100, seg6 fd00:db8:2:1::, encap behavior H.Insert, weight 1
 Client list: static(fd 57)
...
fc00::4
 resolved via static, prefix fc00::/64
 is directly connected, Loopback0 (vrf default), weight 1
 Client list: static(fd 57)
fd00:db8:2:1::
 resolved via static, prefix fd00:db8:2::/48
 via 2001:db8:12::2, Ethernet0 (vrf default), weight 1
 Client list: srte(fd 52) zebra[sr-policies]
```

`staticd` registers two NHT entries per SR-Policy endpoint:
1. `<endpoint> (SR-TE color N)` — tracks the SR-Policy state; resolves via `srte` when active.
2. `<endpoint>` (plain) — IGP fallback when no SR-Policy is active.

#### SR-Policy going inactive — SID reachability lost

When the locator route `fd00:db8:2::/48` is withdrawn, `fd00:db8:2:1::` becomes
unreachable. The cascade is immediate:

```
$ sudo vtysh -c 'show sr-te segment-lists'
Segment-List: sl-via-r2
  Resolution: Unresolved

$ show sr-te policy
 Endpoint  Color  Name          BSID  Status    Type
 ----------------------------------------------------
 10.0.0.4  100    pol-r4-v4-be  -     Inactive  SRV6
 10.0.0.4  200    pol-r4-v4-ll  -     Active    SRV6
 fc00::4   100    pol-r4-v6-be  -     Inactive  SRV6
 fc00::4   200    pol-r4-v6-ll  -     Active    SRV6
```

Color-100 routes fall back to plain IP; color-200 routes are unaffected.

#### Recovery — SID reachability restored

When `fd00:db8:2::/48` is re-advertised, the dependency chain resolves bottom-up:
SID reachable → segment-list valid → candidate-path active → SR-Policy active →
service routes re-steer onto the SR-Policy path.

```
$ show sr-te policy
 Endpoint  Color  Name          BSID  Status  Type
 --------------------------------------------------
 10.0.0.4  100    pol-r4-v4-be  -     Active  SRV6
 10.0.0.4  200    pol-r4-v4-ll  -     Active  SRV6
 fc00::4   100    pol-r4-v6-be  -     Active  SRV6
 fc00::4   200    pol-r4-v6-ll  -     Active  SRV6
```

## 15. Restrictions/Limitations

- Only `explicit` candidate-paths are supported; dynamic/PCE-computed paths are not.
- Only `ipv6-address` (SRv6 Type B) segments are supported; SR-MPLS and NAI segment types
  are reserved in the YANG model but not implemented.
- Only one segment-list per candidate-path is supported (FRR `pathd` backend limitation).
- Binding SIDs (BSID) are not supported.
- `CO` bits of the Color extended-community are only handled for value `'00'`.
- SR-Policy objects use full-length SIDs (segments are `/128` IPv6 addresses). uSID
  behaviors are not steered through SR-Policy candidate-paths.
