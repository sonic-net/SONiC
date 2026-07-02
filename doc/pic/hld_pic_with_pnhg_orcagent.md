# Protection NHG for Primary/Standby ECMP Routes

Rev v1.0

## Table of Contents

1. [Revision History](#1-revision-history)  
2. [About this Manual](#2-about-this-manual)  
3. [Scope](#3-scope)  
4. [Definitions and Abbreviations](#4-definitions-and-abbreviations)  
5. [References](#5-references)  
6. [5\. Overview](#5-overview)  
7. [6\. Requirements](#6-requirements)  
8. [7\. Architecture and Design](#7-architecture-and-design)  
9. [8\. Behavior Scenarios](#8-behavior-scenarios)  
10. [9\. SAI Contract](#9-sai-contract)  
11. [10\. Data Model and DB Schema](#10-data-model-and-db-schema)  
12. [11\. Switchover Trigger Sources](#11-switchover-trigger-sources)  
13. [12\. Capability Detection and Eligibility](#12-capability-detection-and-eligibility)  
14. [13\. Configuration and Manageability](#13-configuration-and-manageability)  
15. [14\. Warm Boot and Fast Boot](#14-warm-boot-and-fast-boot)  
16. [15\. Restrictions and Limitations](#15-restrictions-and-limitations)  
17. [16\. Test Plan](#16-test-plan)  
18. [17\. Open Questions and Future Work](#17-open-questions-and-future-work)

---

## 1\. Revision History

## 

| Rev | Date | Author(s) | Notes |
| :---- | :---- | :---- | :---- |
| v1.0 | 2026-05-06 | Prashanth (Nexthop AI) | Capability-driven N:M protection NHG; covers expected behavior in all paths. |

---

## 2\. About this document

This document is a High-Level Design (HLD) for orchagent's support of *protection* next-hop groups (NHGs).  This describes the platform implementation of the PIC feature covered by the [https://github.com/sonic-net/SONiC/pull/2292](https://github.com/sonic-net/SONiC/pull/2292), where NHGs whose member set is partitioned into a **primary** subset and a **standby** subset, with hardware/SDK-assisted switching between the two.

The design is platform-capability driven: orchagent uses the protection-NHG path only when SAI advertises support; otherwise the route falls back to ECMP over the primary subset.  

---

## 3\. Scope

In scope:

- The orchagent control plane: how routes carrying primary/standby intent are translated into protection NHGs, how member adds/removes are wired into liveness events, and how the active subset is selected.  
- The producer contracts on `APPL_DB.ROUTE_TABLE` that triggers protection-NHG handling.  
- The SAI contract that orchagent assumes (attributes, capability query, expected semantics).  
- Behavior under primary loss, primary recovery, standby loss, and degenerate "all paths dead" cases.

Out of scope:

- The route producer (BGP/FRR or any other control-plane source). Producer-side logic is the responsibility of that component; this design only describes what producers must place in `APPL_DB`.  
- SAI driver / SDK implementation. This document specifies the SAI surface that orchagent uses; how a particular SAI implementation realizes the contract on its hardware (for example, FEC pairs vs. ECMP-replace) is out of scope.  
- Tunnel/overlay next hops as protection-NHG members. The current scope is plain underlay next hops only. Tunnel/overlay support is anticipated as a follow-up.

---

## 4\. Definitions and Abbreviations

## 

| Term | Definition |
| :---- | :---- |
| NHG | Next Hop Group |
| ECMP | Equal Cost Multi-Path |
| NH | Next Hop |
| FEC | Forwarding Equivalence Class — hardware forwarding entry |
| SAI | Switch Abstraction Interface |
| OID | SAI Object Identifier |
| APPL\_DB | Application database (Redis) populated by route producers (e.g., BGP/FRR) |
| ASIC\_DB | ASIC database (Redis) populated by orchagent after SAI programming |
| BFD | Bidirectional Forwarding Detection |
| Primary | A next hop intended to carry traffic when reachable |
| Standby | A next hop that takes over when the primary subset becomes unreachable |
| Active subset | The role (primary or standby) currently selected for forwarding by the protection NHG |
| Switchover | A transition of the active subset from primary to standby |
| Switchback | A transition of the active subset from standby back to primary |

## 5\. Overview

A traditional ECMP NHG treats every member as an equal peer; loss of a member only redistributes flows across the survivors. While it provides high-availability, it does not provide a mechanism to create a hierarchy of these members where one set of paths is preferred and a backup set to take over on failure of the preferred set.

A **protection NHG** introduces that framework. The route producer marks the first *N* of the route's *N+M* next hops as **primary** and the remaining *M* as **standby**. When all primaries are unreachable, traffic is steered to the standbys; when at least one primary becomes reachable again, traffic returns to the primaries. Since these NHGs are shared by multiple routes, on failure it provides a faster convergence to all the routes using this group.

This design supports any **N:M** ratio, including 1:1, subject only to the platform's NHG capacity limit. The transition from primary to standby and back can be either HW driven or SW driven based on the capability of underlying HW/SDK.  

For example, if the HW/SDK can support monitoring objects like interface state or BFD session state and use that to trigger switchover in HW itself.  However if the HW does not support some or all of the features required, then we can switchover by issuing `SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER` to the affected group based on the nature of the failure.

---

## 6\. Requirements

As mentioned earlier, this HLD is the platform complement of the feature described in the HLD [https://github.com/sonic-net/SONiC/pull/2292](https://github.com/sonic-net/SONiC/pull/2292)

### 6.1 Functional

- Support arbitrary **N:M** primary:standby ratios, including 1:1.  
- Activate the protection-NHG path **only when SAI advertises support** for `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` or `SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION`. On platforms that advertise neither, fall back to plain ECMP over the primary subset; never spread BGP traffic across standbys when the producer asked for protection.  
- When **all primary** next hops become unreachable, switch the active subset to **standby**.  
- When **any primary** next hop becomes reachable again, switch the active subset **back to primary**.  
- While at least one primary is reachable (i.e., not switched over), neighbor events on individual primaries shall **shrink or grow the primary subset programmed in SAI** without changing the switchover state.  
- While not switched over, neighbor events on individual standbys shall keep the standby subset programmed in SAI in sync with their reachability state, so that a future switchover lands on a current set.  
- While switched over (standbys active), neighbor events on individual standbys are **deferred** — orchagent does not perturb the standby set in SAI in the current design. This would cause traffic to blackhole if the traffic was being hashed to the standby path that is down.  But given that this is a second order failure and the fact that it leads to a degenerate case where there are no primary or secondary paths with similar results, this is not a concern.  Since this is solution for faster convergence, the expectation is that this is just a transit state and that control plane would eventually come and update the routes with best paths available.  
- Multiple routes whose primary and standby sets are identical shall **share** a single protection NHG (deduplication keyed on the member tuple).

### 6.2 Configuration

- The producer signals protection-NHG intent by adding a `primary_nh_count` field on the existing `APPL_DB.ROUTE_TABLE` entry. No new tables, no schema migration. The field is optional; absent or `0` or if `primary_nh_count` is the same as the size of nexthop list, means the route is plain ECMP.

### 6.3 Scalability

- There is no change to scale numbers due to this feature.  The number of distinct protection NHGs in the system is bounded by the SAI/SDK NHG capacity.  
- The max member count per group is also similar to the ECMP behavior, except in case of Protection NHGs, the max member count could be enforced on the total size including primary and standby members.    
- Routes with identical primary+standby sets share one NHG (refcounted).

### 6.4 Boot and Replay

- Warm boot semantics are **inherited** from regular ECMP NHGs — the design does not introduce new persistence requirements. See §15.

---

## 7\. Architecture and Design

### 7.1 Component Interaction

```
   +-----------------------------+        +-----------------------+
   | Route Producer (BGP / FRR)  |        |     PortsOrch         |
   +--------------+--------------+        +-----------+-----------+
                  |                                   |
                  | set primary_nh_count              | port oper status
                  v                                   v
   +-----------------------------+        +-----------------------+
   |   APPL_DB.ROUTE_TABLE       |        |      NeighOrch        |
   |   + primary_nh_count        |        |  (NH liveness oracle) |
   +--------------+--------------+        +-----------+-----------+
                  |                                   |
                  | notify                            | setNextHopFlag IFDOWN
                  v                                   | clearNextHopFlag IFDOWN
   +-----------------------------+                    | addNextHop / removeNextHop
   |          RouteOrch          |                    |
   +--------------+--------------+                    |
                  |                                   |
                  | createProtNhg                     |
                  | decProtNhgRefCount                |
                  | removeProtNhg                     |
                  v                                   v
   +------------------------------------------------------+
   |                       NhgOrch                        |
   |  owns m_protNhgs    fan-out: validateNextHop /       |
   |                     invalidateNextHop                |
   +--------------+---------------------------------------+
                  |
                  | validateMember / invalidateMember /
                  | updateSwitchoverState
                  v
   +------------------------------------------------------+
   |    ProtNhg     (per-route key, refcounted)           |
   +--------------+---------------------------------------+
                  |
                  | create_next_hop_group
                  | create_next_hop_group_member
                  | set_next_hop_group_attribute
                  v
   +------------------------------------------------------+
   |                        SAI                           |
   +------------------------------------------------------+
```

### 7.1 Lifecycle of a Protection NHG

This design assumes that the PR that is currently being upstreamed provides the infrastructure necessary to create and manage the lifecycle of a Protection NHG.  The PR is available at [https://github.com/sonic-net/sonic-swss/pull/4390\#issuecomment-4228074250](https://github.com/sonic-net/sonic-swss/pull/4390#issuecomment-4228074250)

However, additional changes may be necessary to support this use case of N:M cardinality and initiating switchover via the control plane.  
   

```
                     producer sets primary_nh_count
                     and route is eligible
                              |
                              v
                  +-----------------------+
                  |        Created        |
                  +-----------+-----------+
                              |
                              | ProtNhg::sync, SAI NHG OID assigned
                              v
                  +-----------------------+
                  |   Primary_Active      | <-----------------+
                  |  (primary subset is   |                   |
                  |   the active subset)  |                   | any primary
                  +-----------+-----------+                   | recovers
                              |                               | (SET_SWITCHOVER
                              |  last live primary lost       |  = false)
                              |  (SET_SWITCHOVER = true)      |
                              v                               |
                  +-----------------------+                   |
                  |   Standby_Active      | ------------------+
                  |  (standby subset is   |
                  |   the active subset)  |
                  +-----------+-----------+
                              |
              route deleted or replaced (either state) -> refcount-- ; if 0:
                              v
                  +-----------------------+
                  |        Removed        |  --> SAI NHG / members destroyed
                  +-----------------------+
```

The state lives in the `ProtNhg` instance. The `Primary_Active` ↔ `Standby_Active` transition is the *switchover*; everything else is membership and lifecycle.

### 7.2 RouteOrch Eligibility Decision

When a `ROUTE_TABLE` entry is processed, RouteOrch classifies it based on `primary_nh_count`:

| `primary_nh_count` | Outcome |
| :---- | :---- |
| equal to `len(nexthop)` | Existing path: ECMP, single-NH, blackhole, or interface route as appropriate. |
| `> len(nexthop)` | Invalid: warn, skip the row. |
| `0 < primary_nh_cout < len(nexthop)` and platform supports it | **Protection-NHG path**: first `primary_nh_count` nexthops are primary, rest are standby. |
| `0 < pc < len(nexthop)` and platform does **not** support it | Truncate to primaries only, program as ECMP. Logged at WARN. |

Once classified into the protection-NHG path, RouteOrch builds a deterministic key (canonicalized over the primary and standby sets) and asks `NhgOrch` to materialize it. Distinct routes with the same key share the same SAI NHG OID.

### 7.3 NhgOrch Ownership

`NhgOrch` owns the protection-NHG objects in the same way it owns regular ECMP NHGs: keyed by a deterministic string, refcounted by the routes referencing them, created lazily, and destroyed when the refcount reaches zero. The protection-NHG object encapsulates:

- the SAI NHG OID,  
- per-member SAI OIDs (one per resolved primary or standby NH),  
- the *active subset* state (whether the group is currently forwarding on primaries or standbys).

Existing fan-out hooks in `NhgOrch::validateNextHop` and `NhgOrch::invalidateNextHop` (driven by `NeighOrch`) are extended to consult the protection-NHG table on every NH liveness change and to call into the protection-NHG object so it can re-evaluate its active subset.

### 7.4 NeighOrch Integration

`NeighOrch` is the single source of truth for next-hop liveness. The orchagent already publishes liveness changes to `NhgOrch`:

- when an NH transitions to `NHFLAGS_IFDOWN` (set by `setNextHopFlag`), `NhgOrch::invalidateNextHop` fans out;  
- when `NHFLAGS_IFDOWN` is cleared (by `clearNextHopFlag`), `NhgOrch::validateNextHop` fans out.

In addition, when a *fresh* NH is added to `NeighOrch`'s map (for example after ARP timed out during an extended link-down and re-resolves on link-up), the design notifies `NhgOrch` so any pre-existing protection NHG that has the NH as a member can resync its SAI member and re-evaluate the active subset. Without this notification, the down→up direction would be silently lost in the case where the NH was reaped from `m_syncdNextHops`.

---

## 8\. Behavior Scenarios

This section walks through the expected control flow for the situations the design must handle. *Primary live count* below means the count of primary NHs that `NeighOrch` reports as resolved and not `NHFLAGS_IFDOWN`.

### 8.1 Steady state — all paths up

### 

```
 Producer    APPL_DB    RouteOrch    NhgOrch    ProtNhg    SAI
    |           |           |           |          |        |
    | SET prefix, nexthop=p1,p2,s1,s2, primary_nh_count=2
    +---------->|           |           |          |        |
    |           |  notify   |           |          |        |
    |           +---------->|           |          |        |
    |           |           | classify -> protection NHG path
    |           |           | createProtNhg(key, [p1,p2], [s1,s2])
    |           |           +---------->|          |        |
    |           |           |           |  sync    |        |
    |           |           |           +--------->|        |
    |           |           |           |          | create_next_hop_group(type=PROTECTION)
    |           |           |           |          +------->|
    |           |           |           |          | create_next_hop_group_member x4
    |           |           |           |          | (CONFIGURED_ROLE per member)
    |           |           |           |          +------->|
    |           |           |           |          |  ** NHG OID assigned, primary subset active **
    |           |           |           |   ok     |        |
    |           |           |           |<---------+        |
    |           |           |   NHG OID |          |        |
    |           |           |<----------+          |        |
    |           |           | route SET_NEXT_HOP_ID = NHG OID
    |           |           +-------------------------------->|
```

The route is forwarded across the primary subset. The standby subset is programmed but not selected.

### 8.2 One primary goes down, others remain up

The primary subset is programmed in SAI to reflect **only the live primaries**. No switchover happens. As long as at least one primary remains alive, the active subset stays `Primary_Active`.

```
  PortsOrch    NeighOrch    NhgOrch    ProtNhg    SAI
      |            |           |          |        |
      | port p1 oper down                          |
      +----------->|           |          |        |
      |            | setNextHopFlag(p1, IFDOWN)    |
      |            +--+        |          |        |
      |            |<-+        |          |        |
      |            | invalidateNextHop(p1)
      |            +---------->|          |        |
      |            |           | invalidate primary p1
      |            |           +--------->|        |
      |            |           |          | remove_next_hop_group_member(p1)
      |            |           |          +------->|
      |            |           |          | ** primary live count > 0 -> no switchover **
```

### 8.3 All primaries down — switchover to standbys

This is the **last-live-primary** case. The design issues `SET_SWITCHOVER=true` to SAI **before** removing the dead primary, so that the active subset is never empty at the moment of the SAI member-delete. After SAI accepts the switchover, the dead primary is removed from the (now inactive) primary subset.

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | invalidateNextHop(p2)  ** p2 is the last live primary **
       +---------->|          |        |
       |           | invalidate primary p2
       |           +--------->|        |
       |           |          | ** detect: would empty live primaries **
       |           |          | set_next_hop_group_attribute(SET_SWITCHOVER=true)
       |           |          +------->|
       |           |          |  ** standbys are now the active subset **
       |           |          | remove_next_hop_group_member(p2)
       |           |          +------->|
       |           |   ok     |        |
       |           |<---------+        |
```

After this, the route forwards across the standby subset. `m_switched_over` is `true` in the protection-NHG object.

### 8.4 At least one primary recovers — switch back

The first primary recovery causes a switchback. The recovered primary is added to (or refreshed in) the primary subset in SAI; the active subset flips back via `SET_SWITCHOVER=false`.

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | validateNextHop(p1)
       +---------->|          |        |
       |           | validate primary p1
       |           +--------->|        |
       |           |          | create_next_hop_group_member(p1, role=PRIMARY)
       |           |          +------->|
       |           |          | ** primary live count > 0 -> wanted=Primary_Active **
       |           |          | set_next_hop_group_attribute(SET_SWITCHOVER=false)
       |           |          +------->|
       |           |          |  ** primary subset is now active again **
```

### 8.5 Standby flap while not switched over (req: keep SDK in sync)

The standby is added to or removed from the SAI standby subset as its NeighOrch state changes, so the standby subset stays current and a future switchover lands on a clean set. No switchover state change.

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | invalidateNextHop(s1)  ** primaries still up **
       +---------->|          |        |
       |           | invalidate standby s1 (not switched over)
       |           +--------->|        |
       |           |          | remove_next_hop_group_member(s1)
       |           |          +------->|
       |           |          | ** switchover state unchanged **
```

### 8.6 Standby flap while switched over (deferred)

While the standbys are currently active, the design does **not** add or remove standbys from SAI on individual standby NeighOrch events. Rationale: doing so would shrink the active subset on the fly, potentially down to zero, while the active path is in use. The current design accepts that the standby subset programmed in SAI may diverge from NeighOrch's view while it is active, and re-syncs on the next switchover. See §16, §18.

```
   NeighOrch    NhgOrch    ProtNhg
       |           |          |
       | invalidateNextHop(s1)  ** switched over, s1 dies **
       +---------->|          |
       |           | invalidate standby s1 (switched over)
       |           +--------->|
       |           |          | ** no-op (deferred) **
```

### 8.7 Last primary down with no live standbys ("all paths dead")

When the last live primary goes down and the standby subset programmed in SAI has zero members (because all standbys were unreachable for long enough that they were already removed from SAI per §9.5), the SAI `SET_SWITCHOVER=true` call is rejected by SAI/SDK because the destination active subset would be empty. The design responds gracefully:

- the SAI rejection is propagated up;  
- `m_switched_over` is **not** flipped;  
- the dead primary is **not** removed from SAI.

Traffic that hashes onto the dead primary FEC is dropped. This is the same end-state as a regular ECMP NHG with all members dead. The system is **self-healing**: when any primary or standby returns, the next neighbor event re-runs the active-subset evaluation and either restores primary forwarding (if a primary recovers) or successfully completes the deferred switchover (if a standby recovers).

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | invalidateNextHop(p_last)
       +---------->|          |        |
       |           | invalidate primary p_last
       |           +--------->|        |
       |           |          | set_next_hop_group_attribute(SET_SWITCHOVER=true)
       |           |          +------->|
       |           |          |  error: no standby members in active set
       |           |          |<-------+
       |           | failure  |        |
       |           |<---------+        |
       |           |  ** switchover state stays Primary_Active; **
       |           |  ** p_last is NOT removed from SAI **
       |           |          |        |
       |           |          |  ** black-hole until recovery **

  -- later, any path recovers --

       | validateNextHop(any p or s)
       +---------->|          |        |
       |           | validate |        |
       |           +--------->|        |
       |           |          | create_next_hop_group_member(...)
       |           |          | and/or set_next_hop_group_attribute(SET_SWITCHOVER=...)
       |           |          +------->|
```

### 8.8 Route update that changes the NH set

If a route is updated such that its primary or standby set changes, RouteOrch builds a **new** key and asks `NhgOrch` to materialize the new protection NHG. The route is repointed to the new NHG OID. The old NHG's refcount is decremented; if it hits zero, the old NHG is destroyed in SAI. Routes with the same NH set are not perturbed.

If only `primary_nh_count` flips between zero and non-zero (i.e., the route transitions in or out of protection-NHG semantics), RouteOrch tears down the protection NHG (decRef) and reprograms the route as plain ECMP, or vice versa.

### 8.9 Route delete

`RouteOrch` deletes the route from SAI and decrements the protection-NHG refcount. When the refcount reaches zero, `NhgOrch` destroys the protection NHG in SAI (members removed, group OID released). No special handling is required even when the route is deleted *while switched over* — the destroy path is symmetric.

---

## 9\. SAI Contract

The design uses only standard SAI attributes. orchagent does **not** assume anything about the SAI driver implementation; it assumes only that the driver respects the documented semantics of these attributes.

### 9.1 Capability query (boot, once)

### 

```c
sai_object_type_get_availability(switch_id, SAI_OBJECT_TYPE_NEXT_HOP_GROUP, ...);
sai_query_attribute_enum_values_capability(switch_id, SAI_OBJECT_TYPE_NEXT_HOP_GROUP,
                                           SAI_NEXT_HOP_GROUP_ATTR_TYPE, &values);
```

The orchagent inspects the returned enum list for:

- `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` — software-controlled active subset (orchagent issues `SET_SWITCHOVER`).  
- `SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION` — hardware/SDK-controlled active subset based on per-member `MONITORED_OBJECT`; orchagent uses `ADMIN_ROLE` for explicit overrides.

If neither is advertised, protection-NHG creation is disabled and routes fall back to ECMP-over-primaries.

### 9.2 NHG create

### 

```c
SAI_NEXT_HOP_GROUP_ATTR_TYPE = SAI_NEXT_HOP_GROUP_TYPE_PROTECTION   // or HW_PROTECTION
```

The `TYPE` attribute is set once at creation time and is immutable. The OID returned is stable for the life of the protection NHG; routes pin to it across switchover and member churn.

### 9.3 Member add/remove

Each member is created with:

```c
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID = <NHG OID>
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID       = <NH SAI OID>
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE   = SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_PRIMARY
                                                or _CONFIGURED_ROLE_STANDBY
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_MONITORED_OBJECT  = <oid, optional, HW_PROTECTION only>
```

orchagent expects that adding a member to either subset does **not** disturb the currently-active subset, and that removing a member from a subset also does not disturb the other subset.

### 9.4 Active-subset selection

For `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION`:

```c
SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER = false  // primary subset active (default)
SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER = true   // standby subset active
```

For `SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION`, the hardware/SDK selects the active subset based on the per-member `MONITORED_OBJECT` state. orchagent may override with `SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE`.

orchagent expects that issuing `SET_SWITCHOVER` to a target subset that has **zero programmed members** is rejected by SAI (it would otherwise produce an undefined active subset). This rejection is the trigger for the §9.7 graceful-failure behavior.

### 9.5 Observability

Each member exposes:

```c
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_OBSERVED_ROLE   // ACTIVE / INACTIVE
```

orchagent does not currently consume this attribute; it is reserved for future use.

---

## 10\. Data Model and DB Schema

### 10.1 APPL\_DB.ROUTE\_TABLE

A single new optional field is added to the existing entry:

```
Key:    ROUTE_TABLE:<vrf>:<prefix>
Fields:
    nexthop          = "<ip1>,<ip2>,...,<ipN>"   (N+M total)
    ifname           = "<a1>,<a2>,...,<aN>"      (N+M total)
    weight           = "<w1>,...,<wN>"           (optional)
    primary_nh_count = <N>                       (NEW, optional)
```

Semantics:

- `0 < primary_nh_count < len(nexthop)` is the **only** value that triggers protection-NHG handling.  
- The first `primary_nh_count` entries of `nexthop` are the primary set; the remainder are the standby set.  
- The **order of primaries and the order of standbys** is preserved internally only for parsing; the orchagent canonicalizes them when constructing the protection-NHG key, so two routes with the same set are deduped regardless of producer order.

The field is optional; no schema migration is needed. Producers that do not understand the field continue to publish plain-ECMP rows and orchagent processes them unchanged.

Here is an example of a route with 2 primary and 2 standby members

```
$ redis-cli -n 0 hgetall 'ROUTE_TABLE:100.0.0.0/24'
   1) "nexthop"
   2) "10.0.0.1,10.0.0.2,10.0.0.3,10.0.0.5"
   3) "ifname"
   4) "PortChannel102,PortChannel103,Ethernet68,PortChannel105"
   5) "weight"
   6) "1,1,1,1"
   7) "primary_nh_count"
   8) "2"
```

### 10.2 ASIC\_DB

ASIC\_DB representation is the standard SAI representation of:

- one `SAI_OBJECT_TYPE_NEXT_HOP_GROUP` per protection NHG, with `SAI_NEXT_HOP_GROUP_ATTR_TYPE` \= `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` (or `_HW_PROTECTION`),  
- one `SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER` per resolved member, carrying `CONFIGURED_ROLE`,  
- the route entry pointing to the NHG OID via `SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID`.

No ASIC\_DB schema is introduced.

Here is an example of the ASIC\_DB contents for the Protection NHG group example above.

```
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x5800000000c401'
  1) "SAI_NEXT_HOP_GROUP_ATTR_TYPE"
  2) "SAI_NEXT_HOP_GROUP_TYPE_PROTECTION"
  3) "SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER"
  4) "false"                                        # primaries are active

# Primary member: 10.0.0.1 / PortChannel102
  $ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c405'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x4000000000a311"
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_PRIMARY"

  # Primary member: 10.0.0.2 / PortChannel103
  $ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c406'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x4000000000a312"
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_PRIMARY"

  # Standby member: 10.0.0.3 / Ethernet68
  $ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c407'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x4000000000a313"
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_STANDBY"

  # Standby member: 10.0.0.5 / PortChannel105
  $ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c408'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x4000000000a314"
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_STANDBY"
```

---

## 11\. Switchover Trigger Sources

orchagent's protection-NHG state machine reacts to NH liveness as reported by `NeighOrch`. `NeighOrch` derives liveness from multiple input sources; any input that toggles `NHFLAGS_IFDOWN` or adds/removes an NH from `NeighOrch::m_syncdNextHops` is, in principle, a valid trigger for the protection-NHG path.

| Trigger source | Status in this design |
| :---- | :---- |
| Port operational status change | **Implemented** end-to-end. Driven by `PortsOrch::updatePortOperStatus` \-\> `NeighOrch::ifChangeInformNextHop` \-\> `setNextHopFlag` / `clearNextHopFlag`. |

This document does not require any of the non-port sources to be wired up as part of the initial deliverable; the design simply does not preclude them.

---

## 12\. Capability Detection and Eligibility

At orchagent boot, `NhgOrch` performs one capability query against SAI for the `SAI_NEXT_HOP_GROUP_ATTR_TYPE` enum and caches two booleans:

- `sw_protection_supported` — true iff `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` is in the returned enum.  
- `hw_protection_supported` — true iff `SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION` is in the returned enum.

A route is **eligible** for the protection-NHG path if all of the following hold:

1. The platform advertises a usable protection variant (at least one of the two booleans is true). When only one is supported, that variant is used.  
2. `0 < primary_nh_count < len(nexthop)`.  
3. The route is a plain underlay route (not overlay, not SRv6, not blackhole) — these flavors are out of scope for Phase 1\.  
4. `len(nexthop) <= NHGRP_MAX_SIZE`.

If (2) and (3) hold but (1) or (4) fails, the route is programmed as ECMP **over the primary subset only** and a WARN is emitted that names the failing condition. Standbys are *never* spread into a plain-ECMP fallback, because doing so would defeat the producer's intent.

---

## 13\. Configuration and Manageability

There are no CLI knobs introduced by this design. The feature is gated by SAI capability.

A ROUTE\_TABLE entry with appropriate `primary_nh_count` is the recommended way to opt routes into protection NHG handling on a per-route basis. Producer-side configuration is out of scope for this document.

---

## 14\. Warm Boot and Fast Boot

The protection NHG inherits warm-boot semantics from the regular NHG path:

- The SAI NHG OID is preserved across the warm boot via SAI's standard warm-boot semantics.  
- On orchagent restart, `RouteOrch` re-classifies the `ROUTE_TABLE` row using its current `primary_nh_count`. If the SAI NHG OID is the same and the member set is the same, no reprogramming is necessary; otherwise the standard reconciliation path applies.  
- The active-subset state (whether `SET_SWITCHOVER` was true or false at the moment of the warm boot) is implicit in the SAI driver's persistence; orchagent re-derives the desired state from `NeighOrch`'s current view of NH liveness on its first pass after warm-boot reconciliation, and issues `SET_SWITCHOVER` only if the desired and actual differ.

No explicit warm-boot serialization is introduced by this design.

---

## 15\. Restrictions and Limitations

1. **Standby flap while switched over is a no-op** (§9.6). The standby subset programmed in SAI may temporarily diverge from `NeighOrch`'s view when the standbys are the active subset. This is a deliberate trade-off, not a bug; lifting the restriction is straightforward when needed (see §18).  
2. **Tunnel/overlay next hops** are not yet supported as members of a protection NHG. Protection NHGs are limited to plain underlay next hops in Phase 1\.  
3. **All-paths-dead** results in a black hole (§9.7), the same end-state as regular ECMP all-down. The route is not reprogrammed to a drop next hop. This is consistent with existing SONiC behavior; no separate handling is added.  
4. **Total member count** is bounded by `NHGRP_MAX_SIZE` (currently 128). Routes that exceed this fall back to ECMP-over-primaries.  
5. **Triggers are limited to port oper events today**. Other sources (§12) are supported by the existing `NeighOrch` plumbing and will work without orchagent changes; integrating them is out of scope for the initial deliverable.

---

## 16\. Test Plan

### 16.1 Unit tests (orchagent)

- `RouteOrch` route-handling matrix:  
  - `primary_nh_count` absent / `0` / equal / greater-than `len(nexthop)`: exercise each branch.  
  - Capability supported vs. not supported (mock `NhgOrch::isSwProtectionSupported`).  
  - Primary set, standby set canonicalization (two routes with different producer orderings dedupe).  
- `ProtNhg` member lifecycle:  
  - Create with all members resolved \-\> all members synced in SAI.  
  - Create with some unresolved \-\> sync proceeds, members synced as they resolve later.  
  - Refcount-driven destroy.

### 16.2 Functional / integration tests

- 1+1, N+1, 1+M, and N+M topologies, with N and M up to a small but representative bound.  
- Primary down (non-last) \-\> shrink primary subset; verify no `SET_SWITCHOVER`.  
- Last live primary down \-\> single `SET_SWITCHOVER=true` immediately followed by the dead-member remove; verify ordering at SAI.  
- Primary recovery from switched-over state \-\> single `SET_SWITCHOVER=false`; verify primary set is current.  
- Standby down while not switched over \-\> standby subset shrinks; verify no `SET_SWITCHOVER`.  
- Standby down while switched over \-\> verify SAI is **not** touched (deferred).  
- All-paths-dead \-\> verify SAI rejection of `SET_SWITCHOVER=true` is propagated; verify recovery on either side.  
- Route update that changes the NH set \-\> verify deterministic key, refcount transitions, and old-NHG destroy when refcount==0.

### 16.3 Negative tests

- Capability not advertised \-\> protection-NHG path disabled, route falls back to ECMP-over-primaries with the documented WARN.  
- `primary_nh_count > len(nexthop)` \-\> WARN, row skipped.

---

## 17\. Open Questions and Future Work

1. **Lifting the §9.6 restriction.** Allowing standby member churn while standbys are active would require ensuring the active subset never empties out as a side effect — feasible, but the cost/value trade-off should be revisited based on real deployment data.  
2. **Tunnel/overlay next-hop members.** Phase 2\.

