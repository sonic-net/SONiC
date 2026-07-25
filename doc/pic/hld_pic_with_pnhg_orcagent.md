# Protection NHG for Primary/Standby ECMP Routes

Rev v1.1

## Table of Contents

1. [Revision History](#1-revision-history)  
2. [About this document](#2-about-this-document)  
3. [Scope](#3-scope)  
4. [Definitions and Abbreviations](#4-definitions-and-abbreviations)  
5. [Overview](#5-overview)  
6. [Requirements](#6-requirements)  
7. [Architecture and Design](#7-architecture-and-design)  
8. [Behavior Scenarios](#8-behavior-scenarios)  
9. [SAI Contract](#9-sai-contract)  
10. [Data Model and DB Schema](#10-data-model-and-db-schema)  
11. [Switchover Trigger Sources](#11-switchover-trigger-sources)  
12. [Capability Detection and Eligibility](#12-capability-detection-and-eligibility)  
13. [Configuration and Manageability](#13-configuration-and-manageability)  
14. [Warm Boot and Fast Boot](#14-warm-boot-and-fast-boot)  
15. [Restrictions and Limitations](#15-restrictions-and-limitations)  
16. [Test Plan](#16-test-plan)  
17. [Open Questions and Future Work](#17-open-questions-and-future-work)

---

## 1\. Revision History


| Rev | Date | Author(s) | Notes |
| :---- | :---- | :---- | :---- |
| v1.0 | 2026-05-06 | Prashanth (Nexthop AI) | Capability-driven N:M protection NHG; covers expected behavior in all paths. |
| v1.1 | 2026-07-17 | Prashanth (Nexthop AI) | Two-level realization: the protection NHG is an ECMP-of-ECMPs — one inner ECMP per role subset — with the protection NHG limited to switchover. Producer contract unchanged. |

---

## 2\. About this document

This document is a High-Level Design (HLD) for orchagent's support of *protection* next-hop groups (NHGs).  This describes the platform implementation of the PIC feature covered by the [https://github.com/sonic-net/SONiC/pull/2292](https://github.com/sonic-net/SONiC/pull/2292), where NHGs whose member set is partitioned into a **primary** subset and a **standby** subset, with orchagent-driven switching between the two.

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
- Routes that point at an explicit NhgOrch next-hop-group index (`NEXT_HOP_GROUP_TABLE`) as protection NHGs. The current scope is flat-list `ROUTE_TABLE` routes carrying `primary_nh_count` (see §7.4); index-based NHGs are a possible follow-up.

---

## 4\. Definitions and Abbreviations


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

A traditional ECMP NHG treats every member as an equal peer; loss of a member only redistributes flows across the survivors. While it provides high-availability, it does not provide a mechanism to create a hierarchy of these members where one set of paths is preferred and a backup set to take over on failure of the preferred set. Adding this capability allows for a quick datapath convergence when the primary path fails, until the control plane can determine the new optimal path and update the routes accordingly.

A **protection NHG** introduces that framework. The route producer marks the first *N* of the route's *N+M* next hops as **primary** and the remaining *M* as **standby**. When all primaries are unreachable, traffic is steered to the standbys; when at least one primary becomes reachable again, traffic returns to the primaries. Since these NHGs are shared by multiple routes, on failure it provides a faster convergence to all the routes using this group.

This design supports any **N:M** ratio, including 1:1, subject only to the platform's NHG capacity limit. The transition from primary to standby and back is driven by orchagent, which issues `SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER` based on next-hop liveness reported by NeighOrch.

**Structure — an ECMP of ECMPs.** The protection NHG is realized as a two-level group. Each role subset is itself an ECMP next-hop group — a *primary inner ECMP* over the primary next hops and a *standby inner ECMP* over the standby next hops — and the protection NHG has just two members, one per role, each pointing at its inner ECMP. (An inner ECMP is created only when the subset has more than one next hop; a subset with a single next hop is used directly as the member.) The protection NHG's only responsibility is the **switchover**: selecting which inner group is the active subset. Per-next-hop liveness *within* a subset — an individual member going down or recovering — is handled by that subset's inner ECMP exactly as an ordinary ECMP handles it (the inner ECMP shrinks or grows and re-hashes over its survivors), with no change to the protection NHG's own two members. This split keeps the protection NHG stable across neighbor flaps, reuses the standard, well-exercised ECMP liveness path for intra-subset changes, and limits orchagent-issued `SET_SWITCHOVER` to the moments an entire subset crosses the all-down / first-up boundary.

Hardware/SDK-driven switchover (for example, via SAI monitored objects that track interface or BFD session state) is **out of scope** for this design; see §17.

---

## 6\. Requirements

As mentioned earlier, this HLD is the platform complement of the feature described in the HLD [https://github.com/sonic-net/SONiC/pull/2292](https://github.com/sonic-net/SONiC/pull/2292)

### 6.1 Functional

- Support arbitrary **N:M** primary:standby ratios, including 1:1.  
- Activate the protection-NHG path **only when SAI advertises support** for `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION`. On platforms that do not advertise it, fall back to plain ECMP over the primary subset; never spread BGP traffic across standbys when the producer asked for protection.  
- When **all primary** next hops become unreachable, switch the active subset to **standby**.  
- When **any primary** next hop becomes reachable again, switch the active subset **back to primary**.  
- While at least one primary is reachable (i.e., not switched over), neighbor events on individual primaries shall **shrink or grow the primary subset programmed in SAI** without changing the switchover state.  
- While not switched over, neighbor events on individual standbys shall keep the standby subset programmed in SAI in sync with their reachability state, so that a future switchover lands on a current set.  
- While switched over (standbys active), neighbor events on individual standbys shall **shrink or grow the standby subset programmed in SAI**, exactly as primary events do while primaries are active — the active subset is kept current so traffic is never hashed onto a known-dead standby. The one guard is that the active subset is never allowed to empty as a side effect: removing the *last* live standby is the degenerate all-paths-dead case handled in §8.7.  
- Multiple routes whose primary and standby sets are identical shall **share** a single protection NHG (deduplication keyed on the member tuple).

### 6.2 Configuration

- The producer signals protection-NHG intent by adding a `primary_nh_count` field on the existing `APPL_DB.ROUTE_TABLE` entry. No new tables, no schema migration. The field is optional; absent, or `primary_nh_count == len(nexthop)`, means the route is plain ECMP.  
- **Producer contract:** a well-behaved producer never emits `primary_nh_count == 0`. When all primaries are withdrawn (permanently) after reconvergence, the producer republishes the route with the surviving paths promoted to primaries and `primary_nh_count` set accordingly — which may be a plain ECMP route (`primary_nh_count == len(nexthop)`, no standbys). Orchagent treats a stray `primary_nh_count == 0` defensively (WARN + skip the row); it should not occur in normal operation.

### 6.3 Scalability

- The two-level structure consumes more NHG objects than a single flat group would: one NHG for the protection group itself, plus one inner ECMP NHG per role subset that has **more than one** next hop. So an N:M group with N>1 and M>1 uses **three** NHG objects (protection + primary inner ECMP + standby inner ECMP); a 1:1 group uses **one** (both subsets are single next hops used directly, so no inner ECMP is created). The number of protection groups the system can hold is bounded by the SAI/SDK NHG capacity, which now also accounts for these inner ECMPs.  
- The max member count is similar to plain ECMP; for a protection group the relevant per-subset limit is the member count of each inner ECMP (each an ordinary ECMP over that role's next hops).  
- Routes with identical primary+standby sets share one protection NHG (refcounted); its inner ECMPs are private to it (§7.4) and are not shared with plain-ECMP routes.

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

**Legend:** every box except *Route Producer (BGP/FRR)* is a C++ class within the single `orchagent` process — `RouteOrch`, `NhgOrch`, `PortsOrch`, `NeighOrch`, and `ProtNhg`. `ProtNhg` in particular is an in-process object owned by `NhgOrch`, **not** a new daemon.

### 7.2 Lifecycle of a Protection NHG

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

### 7.3 RouteOrch Eligibility Decision

When a `ROUTE_TABLE` entry is processed, RouteOrch classifies it based on `primary_nh_count`:

| `primary_nh_count` | Outcome |
| :---- | :---- |
| equal to `len(nexthop)` | Existing path: ECMP, single-NH, blackhole, or interface route as appropriate. |
| `> len(nexthop)` | Invalid: warn, skip the row. |
| `0 < primary_nh_count < len(nexthop)` and platform supports it | **Protection-NHG path**: first `primary_nh_count` nexthops are primary, rest are standby. |
| `0 < primary_nh_count < len(nexthop)` and platform does **not** support it | Truncate to primaries only, program as ECMP. Logged at WARN. |

Once classified into the protection-NHG path, RouteOrch builds a deterministic key (canonicalized over the primary and standby sets) and asks `NhgOrch` to materialize it. Distinct routes with the same key share the same SAI NHG OID.

### 7.4 Ownership: RouteOrch drives, NhgOrch holds

Ownership here differs from plain ECMP, so it is worth stating precisely:

- **Plain ECMP over a flat `ROUTE_TABLE` nexthop list** is owned by **RouteOrch** (`m_syncdNextHopGroups`, keyed by the `NextHopGroupKey`); NhgOrch is not involved.  
- **Routes that point at an explicit next-hop-group index** (`NEXT_HOP_GROUP_TABLE`) are owned by **NhgOrch**.

Protection NHGs are produced by flat-list `ROUTE_TABLE` entries (carrying `primary_nh_count`), so by the rule above they would normally be RouteOrch-owned. This design instead introduces a **new, dedicated collection in NhgOrch — `m_protNhgs`** — to hold the protection-NHG objects, while **RouteOrch is modified to drive their lifecycle**:

- **RouteOrch** classifies the row, builds a deterministic key over the primary and standby sets, calls `NhgOrch::createProtNhg(key, primaries, standbys)`, pins the route to the returned NHG OID, and maintains the per-route refcount (`incProtNhgRefCount` / `decProtNhgRefCount`), asking NhgOrch to destroy the object when the refcount reaches zero. This is analogous to how RouteOrch manages its own `m_syncdNextHopGroups`, except the objects are centralized in NhgOrch so that distinct routes with identical primary/standby sets dedup onto one OID.  
- **NhgOrch** stores the objects (keyed by the deterministic string, refcounted, created lazily, destroyed at refcount zero) and reuses its existing `validateNextHop` / `invalidateNextHop` NeighOrch fan-out to drive per-member liveness and switchover. This fan-out is the reason the objects live in NhgOrch rather than RouteOrch's `m_syncdNextHopGroups`, which has no per-member liveness/switchover machinery.

The protection-NHG object (`ProtNhg`) encapsulates:

- the SAI OID of the protection NHG,  
- its (up to) two members — one per role — where a role subset with more than one next hop is realized as a **private inner ECMP NHG** and a subset with a single next hop uses that next hop directly,  
- the SAI OIDs of the inner ECMPs and their per-next-hop members,  
- the *active subset* state (whether the group is currently forwarding on the primary or the standby inner group).

**Inner ECMPs are private to the protection NHG — they are not shared with plain-ECMP routes** that happen to carry the same member set. The reason is lifecycle divergence on an empty subset: a plain-ECMP NHG is destroyed when its last member is withdrawn (SONiC does not keep a zero-member group; the route is reprogrammed), whereas a protection subset must *persist* even when all its members are down — an empty primary subset is precisely the switchover trigger, and the inner group must survive so the protection NHG can switch **back** when a primary recovers. Sharing an inner ECMP with a plain route would let that route's "last member down → destroy" tear down an object the protection NHG still depends on, and would couple the two consumers' membership churn. Individual next-hop objects are still shared per-IP; only the ECMP *group* is private.

Existing fan-out hooks in `NhgOrch::validateNextHop` and `NhgOrch::invalidateNextHop` (driven by `NeighOrch`) are extended to consult `m_protNhgs` on every NH liveness change and to call into the protection-NHG object so it can re-evaluate its active subset. A liveness change on an individual next hop updates the relevant **inner ECMP**; the protection NHG re-evaluates the active subset (and issues `SET_SWITCHOVER` only if an entire subset crossed the all-down / first-up boundary).

### 7.5 NeighOrch Integration

`NeighOrch` is the single source of truth for next-hop liveness. The orchagent already publishes liveness changes to `NhgOrch`:

- when an NH transitions to `NHFLAGS_IFDOWN` (set by `setNextHopFlag`), `NhgOrch::invalidateNextHop` fans out;  
- when `NHFLAGS_IFDOWN` is cleared (by `clearNextHopFlag`), `NhgOrch::validateNextHop` fans out.

In addition, when a *fresh* NH is added to `NeighOrch`'s map (for example after ARP timed out during an extended link-down and re-resolves on link-up), the design notifies `NhgOrch` so any pre-existing protection NHG that has the NH as a member can resync its SAI member and re-evaluate the active subset. Without this notification, the down→up direction would be silently lost in the case where the NH was reaped from `m_syncdNextHops`.

---

## 8\. Behavior Scenarios

This section walks through the expected control flow for the situations the design must handle. *Primary live count* below means the count of primary NHs that `NeighOrch` reports as resolved and not `NHFLAGS_IFDOWN`.

Recall from §5 and §7.4 that each role subset (of more than one next hop) is an inner ECMP NHG. A member going down or recovering *within* a subset is applied to that subset's **inner ECMP** — the inner group shrinks or grows and re-hashes over its survivors — and does **not** change the protection NHG's own two members. The protection NHG itself changes only on **switchover** (`SET_SWITCHOVER`). Accordingly, the `create_next_hop_group_member` / `remove_next_hop_group_member` calls in the flows below operate on the relevant **inner ECMP**, unless stated otherwise.

### 8.1 Steady state — all paths up


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
    |           |           |           |          | create inner ECMP(primary)=[p1,p2]
    |           |           |           |          | create inner ECMP(standby)=[s1,s2]
    |           |           |           |          +------->|
    |           |           |           |          | create_next_hop_group(type=PROTECTION)
    |           |           |           |          +------->|
    |           |           |           |          | create_next_hop_group_member x2
    |           |           |           |          | (member -> inner ECMP OID, CONFIGURED_ROLE per role)
    |           |           |           |          +------->|
    |           |           |           |          |  ** NHG OID assigned, primary inner group active **
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

This is the **last-live-primary** case. When the last live primary's neighbor goes down, its next hop is removed from the **primary inner ECMP** (the same intra-subset shrink as §8.2), leaving that inner group with no live members. The protection NHG observes that the primary subset is now empty of live members and issues `SET_SWITCHOVER=true`, making the **standby inner ECMP** the active subset.

Two things distinguish this from the flat model:

- The dead primary is removed from the **inner primary ECMP**, not from the protection NHG. The protection NHG's two members (the two inner ECMPs) are unchanged; the switchover simply flips **which of the two is active**. The flat model's "issue `SET_SWITCHOVER` before deleting the dead member, so the active subset is never empty" ordering does not apply here, because no member of the protection NHG is deleted on this event — the protection NHG's members are stable and only their active selection changes.
- The now-empty **primary inner ECMP persists** (§7.4) rather than being destroyed, so a later primary recovery (§8.4) repopulates it and the group switches back.

If, at this moment, the standby subset has no programmed members, the switchover is **not** issued — that is the all-paths-dead case in §8.7.

```
   NeighOrch    NhgOrch      ProtNhg    SAI
       |           |            |        |
       | invalidateNextHop(p2)  ** p2 is the last live primary **
       +---------->|            |        |
       |           | remove p2 from the primary inner ECMP
       |           +--------------------->|
       |           |            |         | ** primary inner ECMP now has no live members **
       |           | re-evaluate protection NHG
       |           +----------->|         |
       |           |            | ** primary subset empty; standby subset is programmed **
       |           |            | set_next_hop_group_attribute(SET_SWITCHOVER=true)
       |           |            +-------->|
       |           |            | ** standby inner ECMP is now the active subset **
       |           |   ok       |         |
       |           |<-----------+         |
```

After this, the route forwards across the standby inner ECMP. `m_switched_over` is `true` in the protection-NHG object; the primary inner ECMP remains in place (empty of live members), ready for switchback.

### 8.4 At least one primary recovers — switch back

The first primary recovery causes a switchback. The recovered primary is added back to the **primary inner ECMP** (repopulating it, §8.3); the protection NHG then flips the active subset back via `SET_SWITCHOVER=false`.

```
   NeighOrch    NhgOrch      ProtNhg    SAI
       |           |            |        |
       | validateNextHop(p1)
       +---------->|            |        |
       |           | add p1 to the primary inner ECMP
       |           +--------------------->|
       |           |            |         | ** primary inner ECMP now has a live member **
       |           | re-evaluate protection NHG
       |           +----------->|         |
       |           |            | ** primary live count > 0 -> wanted=Primary_Active **
       |           |            | set_next_hop_group_attribute(SET_SWITCHOVER=false)
       |           |            +-------->|
       |           |            | ** primary inner ECMP is the active subset again **
```

### 8.5 Standby flap while not switched over

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

### 8.6 Standby flap while switched over

While the standbys are the active subset, a standby member's death is handled the same way a primary member's death is handled while primaries are active: the dead standby is removed from the active subset in SAI (the standby ECMP set shrinks), and a recovered standby is added back. This keeps the active set current so traffic is never hashed onto a known-dead standby. The single guard is that orchagent never removes the *last* live member of the active subset — that would empty it; removing the last live standby is the all-paths-dead case handled in §8.7.

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | invalidateNextHop(s1)  ** switched over, s1 dies, other standbys live **
       +---------->|          |        |
       |           | invalidate standby s1 (switched over)
       |           +--------->|        |
       |           |          | remove_next_hop_group_member(s1)
       |           |          +------->|
       |           |          | ** active (standby) subset shrinks; still non-empty **
```

### 8.7 Last primary down with no live standbys ("all paths dead")

When the last live primary goes down, orchagent first checks the standby subset it has programmed in SAI. If that subset has zero members — because all standbys were unreachable long enough to be removed from SAI per §8.5 — switching over would leave the active subset empty, so orchagent **does not issue `SET_SWITCHOVER`**. It aborts the operation:

- `SET_SWITCHOVER=true` is **not** issued: orchagent pre-checks that the target subset is non-empty (see §9.4), so it does not rely on a SAI/SDK error code to detect this case;  
- `m_switched_over` is **not** flipped — the group stays `Primary_Active`;  
- the primary inner ECMP is left as the active subset, with its last (now-dead) member in place — orchagent does not empty the active subset (the §8.6 guard). (Contrast §8.3, where a standby is available: the switchover makes the standby inner ECMP the active subset, so the primary inner ECMP is no longer active and may drop to empty and persist for switchback.)

Traffic that hashes onto the dead primary FEC is dropped. This is the same end-state as a regular ECMP NHG with all members dead. The system is **self-healing**: when any primary or standby returns, the next neighbor event re-runs the active-subset evaluation and either restores primary forwarding (if a primary recovers) or now successfully switches over (if a standby recovers, so the target subset is no longer empty).

```
   NeighOrch    NhgOrch    ProtNhg    SAI
       |           |          |        |
       | invalidateNextHop(p_last)
       +---------->|          |        |
       |           | invalidate primary p_last
       |           +--------->|        |
       |           |          | ** last live primary; would switch to standbys **
       |           |          | ** pre-check: standby programmed count == 0 **
       |           |          | ** -> abort: do NOT issue SET_SWITCHOVER, do NOT remove p_last **
       |           |          |        |
       |           |  ** switchover state stays Primary_Active **
       |           |  ** black-hole until recovery **

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

Orchagent re-classifies the `ROUTE_TABLE` entry on **every** update and derives a fresh key from the current `nexthop` list and `primary_nh_count`. Because role is purely positional — the first `primary_nh_count` entries are primaries, the rest standbys, and a given next hop appears **once** in the list — a next hop is never simultaneously a primary and a standby; a change that moves a next hop between the two subsets simply produces a different key. The three transitions are handled uniformly by re-keying:

1. **Plain ECMP → protection** (producer adds `0 < primary_nh_count < len`): RouteOrch builds the protection-NHG key, materializes it via `NhgOrch`, repoints the route, and releases the old plain-ECMP NHG.  
2. **Protection → plain ECMP** (producer drops the field or sets `primary_nh_count == len` — e.g., standbys promoted to primaries after reconvergence, §8.7 / §6.2): RouteOrch reprograms the route as plain ECMP and decRefs the protection NHG (destroyed at refcount zero).  
3. **Protection → protection with a different split** (the primary/standby membership or the N:M boundary changes): a new key, a new protection NHG, the route repointed, and the old NHG decRef'd.

In all cases the old NHG's refcount is decremented and, if it reaches zero, the old NHG is destroyed in SAI. Routes still referencing the old key are not perturbed. A given next hop that appears in the primary set of one route and the standby set of another is fine — they are distinct keys / distinct NHGs; the positional rule only constrains a *single* route's list.

### 8.9 Route delete

`RouteOrch` deletes the route from SAI and decrements the protection-NHG refcount. When the refcount reaches zero, `NhgOrch` destroys the protection NHG in SAI (members removed, group OID released). No special handling is required even when the route is deleted *while switched over* — the destroy path is symmetric.

---

## 9\. SAI Contract

The design uses only standard SAI attributes. orchagent does **not** assume anything about the SAI driver implementation; it assumes only that the driver respects the documented semantics of these attributes.

### 9.1 Capability query (boot, once)


```c
sai_object_type_get_availability(switch_id, SAI_OBJECT_TYPE_NEXT_HOP_GROUP, ...);
sai_query_attribute_enum_values_capability(switch_id, SAI_OBJECT_TYPE_NEXT_HOP_GROUP,
                                           SAI_NEXT_HOP_GROUP_ATTR_TYPE, &values);
```

The orchagent inspects the returned enum list for:

- `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` — software-controlled active subset (orchagent issues `SET_SWITCHOVER`).

If it is not advertised, protection-NHG creation is disabled and routes fall back to ECMP-over-primaries.

### 9.2 NHG create


```c
SAI_NEXT_HOP_GROUP_ATTR_TYPE = SAI_NEXT_HOP_GROUP_TYPE_PROTECTION
```

The `TYPE` attribute is set once at creation time and is immutable. The OID returned is stable for the life of the protection NHG; routes pin to it across switchover and member churn.

### 9.3 Members

The protection NHG has (up to) two members, one per role. Each is created with:

```c
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID = <protection NHG OID>
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID       = <inner ECMP NHG OID>   // or a plain <NH SAI OID> when the subset has a single next hop
SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE   = SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_PRIMARY
                                                or _CONFIGURED_ROLE_STANDBY
```

The inner ECMPs are ordinary `SAI_NEXT_HOP_GROUP_TYPE_*ECMP` groups; their members are the individual next-hop OIDs of that role subset and are added/removed as those next hops resolve or go down (§8). Because per-next-hop liveness is applied at the inner-ECMP level, the protection NHG's own two members change only when a role subset appears or disappears entirely, not on individual neighbor flaps.

orchagent expects that adding or removing a member of one inner ECMP does **not** disturb the other inner ECMP or the protection NHG's active-subset selection.

### 9.4 Active-subset selection

For `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION`:

```c
SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER = false  // primary subset active (default)
SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER = true   // standby subset active
```

orchagent never issues `SET_SWITCHOVER` toward a target subset that has **zero programmed members** — it pre-checks the target subset's programmed member count and aborts the switchover if it would be empty (see §8.7). A SAI driver may additionally reject such a call defensively, but orchagent does not depend on that rejection or on any particular return code.

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
- The first `primary_nh_count` entries of `nexthop` are the primary set; the remainder are the standby set. **Producer contract:** the producer — FRR or any other routing stack / controller — MUST place the primary next hops at the **front** of the `nexthop` / `ifname` lists, since role is determined purely by position.  
- The **order of primaries and the order of standbys** is preserved internally only for parsing; the orchagent canonicalizes them when constructing the protection-NHG key, so two routes with the same set are deduped regardless of producer order.  
- The optional `weight` field is the existing ECMP/WCMP weight (not new to this design); when present, weights apply to members **within the currently active subset**.

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

- one `SAI_OBJECT_TYPE_NEXT_HOP_GROUP` for the protection NHG, with `SAI_NEXT_HOP_GROUP_ATTR_TYPE` \= `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION`,  
- up to two `SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER` of the protection NHG (one per role), each carrying `CONFIGURED_ROLE` and pointing via `NEXT_HOP_ID` at an inner ECMP NHG — or directly at a next hop when that subset has a single next hop,  
- one `SAI_OBJECT_TYPE_NEXT_HOP_GROUP` per inner ECMP (an ordinary ECMP type), each with one `SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER` per resolved next hop in that subset,  
- the route entry pointing to the protection NHG OID via `SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID`.

No ASIC\_DB schema is introduced.

Here is an example of the ASIC\_DB contents for the Protection NHG group example above (2 primary + 2 standby). The protection NHG has two members, each pointing at an inner ECMP NHG (one per role); the leaf next hops are the members of the inner ECMPs.

```
# Protection NHG: two members, one per role
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x5800000000c401'
  1) "SAI_NEXT_HOP_GROUP_ATTR_TYPE"
  2) "SAI_NEXT_HOP_GROUP_TYPE_PROTECTION"
  3) "SAI_NEXT_HOP_GROUP_ATTR_SET_SWITCHOVER"
  4) "false"                                        # primary inner group is active

# Protection member -> PRIMARY inner ECMP
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c405'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"                         # the protection NHG
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x5800000000c402"                         # the PRIMARY inner ECMP NHG
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_PRIMARY"

# Protection member -> STANDBY inner ECMP
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:oid:0x2d00000000c406'
  1) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID"
  2) "oid:0x5800000000c401"                         # the protection NHG
  3) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID"
  4) "oid:0x5800000000c403"                         # the STANDBY inner ECMP NHG
  5) "SAI_NEXT_HOP_GROUP_MEMBER_ATTR_CONFIGURED_ROLE"
  6) "SAI_NEXT_HOP_GROUP_MEMBER_CONFIGURED_ROLE_STANDBY"

# PRIMARY inner ECMP NHG (ordinary ECMP over the primary next hops)
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x5800000000c402'
  1) "SAI_NEXT_HOP_GROUP_ATTR_TYPE"
  2) "SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_UNORDERED_ECMP"
  # member 10.0.0.1 / PortChannel102 -> NEXT_HOP_GROUP_ID=oid:0x5800000000c402, NEXT_HOP_ID=oid:0x4000000000a311
  # member 10.0.0.2 / PortChannel103 -> NEXT_HOP_GROUP_ID=oid:0x5800000000c402, NEXT_HOP_ID=oid:0x4000000000a312

# STANDBY inner ECMP NHG (ordinary ECMP over the standby next hops)
$ redis-cli -n 1 hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:oid:0x5800000000c403'
  1) "SAI_NEXT_HOP_GROUP_ATTR_TYPE"
  2) "SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_UNORDERED_ECMP"
  # member 10.0.0.3 / Ethernet68     -> NEXT_HOP_GROUP_ID=oid:0x5800000000c403, NEXT_HOP_ID=oid:0x4000000000a313
  # member 10.0.0.5 / PortChannel105 -> NEXT_HOP_GROUP_ID=oid:0x5800000000c403, NEXT_HOP_ID=oid:0x4000000000a314
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

At orchagent boot, `NhgOrch` performs one capability query against SAI for the `SAI_NEXT_HOP_GROUP_ATTR_TYPE` enum and caches a boolean:

- `sw_protection_supported` — true iff `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` is in the returned enum.

A route is **eligible** for the protection-NHG path if all of the following hold:

1. The platform advertises `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION` (`sw_protection_supported` is true).  
2. `0 < primary_nh_count < len(nexthop)`.  
3. The route is a plain underlay route (not overlay, not SRv6, not blackhole) — these flavors are out of scope for Phase 1\.

If (2) and (3) hold but (1) fails, the route is programmed as ECMP **over the primary subset only** and a WARN is emitted. Standbys are *never* spread into a plain-ECMP fallback, because doing so would defeat the producer's intent.

---

## 13\. Configuration and Manageability

This design introduces **no CLI knobs**; the feature is controlled by two existing gates rather than a switch-level toggle:

1. **SAI capability.** Orchagent activates the protection-NHG path only when SAI advertises `SAI_NEXT_HOP_GROUP_TYPE_PROTECTION`. On platforms that do not, routes carrying `primary_nh_count` fall back to plain ECMP over the primary subset (§12).  
2. **Per-route producer opt-in.** A route becomes a protection NHG only when the producer sets `primary_nh_count` on its `ROUTE_TABLE` entry. If a producer never emits the field, orchagent creates no protection NHGs — there is no always-on behavior to disable.

Because of (2), enabling or disabling the feature is naturally controlled at the **producer (FRR/BGP)**, which owns the config knobs that decide whether to mark routes with primary/standby intent. A separate switch-side enable knob would be redundant: on incapable hardware the capability gate disables it, and on capable hardware the producer controls it per route. Producer-side configuration is out of scope for this document.

---

## 14\. Warm Boot and Fast Boot

The protection NHG inherits warm-boot semantics from the regular NHG path:

- The SAI NHG OID is preserved across the warm boot via SAI's standard warm-boot semantics.  
- On orchagent restart, `RouteOrch` re-classifies the `ROUTE_TABLE` row using its current `primary_nh_count`. If the SAI NHG OID is the same and the member set is the same, no reprogramming is necessary; otherwise the standard reconciliation path applies.  
- The active-subset state (whether `SET_SWITCHOVER` was true or false at the moment of the warm boot) is implicit in the SAI driver's persistence; orchagent re-derives the desired state from `NeighOrch`'s current view of NH liveness on its first pass after warm-boot reconciliation, and issues `SET_SWITCHOVER` only if the desired and actual differ.

No explicit warm-boot serialization is introduced by this design.

---

## 15\. Restrictions and Limitations

1. **Active-subset shrink guard** (§8.6, §8.7). Orchagent never removes the last live member of the active subset, since that would leave it empty; the resulting black hole is the all-paths-dead case (§8.7), self-healing on any recovery. Otherwise the active subset (primary or standby) is kept in sync with `NeighOrch` liveness.  
2. **Tunnel/overlay next hops** are not yet supported as members of a protection NHG. Protection NHGs are limited to plain underlay next hops in Phase 1\.  
3. **All-paths-dead** results in a black hole (§8.7), the same end-state as regular ECMP all-down. The route is not reprogrammed to a drop next hop. This is consistent with existing SONiC behavior; no separate handling is added.  
4. **Total member count** is bounded by the platform's SAI/SDK NHG capacity, the same as plain ECMP; orchagent does not impose a separate per-group cap — oversized groups are rejected by SAI.  
5. **Triggers are limited to port oper events today**. Other sources (§12) are supported by the existing `NeighOrch` plumbing and will work without orchagent changes; integrating them is out of scope for the initial deliverable.

---

## 16\. Test Plan

### 16.1 Unit tests (orchagent)

- `RouteOrch` route-handling matrix:  
  - `primary_nh_count` absent / `0` / equal / greater-than `len(nexthop)`: exercise each branch.  
  - Capability supported vs. not supported (mock `NhgOrch::isSwProtectionSupported`).  
  - Primary set, standby set canonicalization (two routes with different producer orderings dedupe).  
- Two-level structure:  
  - A role subset with more than one next hop materializes an **inner ECMP** member; a single-next-hop subset uses that next hop directly as the member (no inner ECMP).  
  - The protection NHG has (up to) two members, each carrying `CONFIGURED_ROLE` and referencing its inner ECMP OID (or the NH OID for a single-NH subset).  
  - Inner ECMPs are **private**: a protection route and a plain-ECMP route with the same member set resolve to **distinct** group OIDs (the inner ECMP is not shared).  
- `ProtNhg` member lifecycle:  
  - Create with all members resolved \-\> the two role members and their inner-ECMP members are synced in SAI.  
  - Create with some unresolved \-\> sync proceeds, members synced as they resolve later.  
  - Refcount-driven destroy (the protection NHG and its private inner ECMPs are released at refcount zero).

### 16.2 Functional / integration tests

- 1+1, N+1, 1+M, and N+M topologies, with N and M up to a small but representative bound.  
- **Two-level layout** \-\> verify the protection NHG has two role members referencing inner ECMP OIDs (or a plain NH OID for a single-NH subset), and each inner ECMP holds its subset's leaf next hops (see §10.2).  
- **Intra-subset liveness stays in the inner ECMP** \-\> a member flap within a subset changes only that inner ECMP; the protection NHG's two members and switchover state are unchanged.  
- Primary down (non-last) \-\> the primary **inner ECMP** shrinks (protection NHG members unchanged); verify no `SET_SWITCHOVER`.  
- Last live primary down \-\> the dead primary is removed from the primary inner ECMP and the protection NHG issues a single `SET_SWITCHOVER=true` (standby inner ECMP becomes active); verify the primary inner ECMP **persists** (empty of live members) for switchback.  
- Primary recovery from switched-over state \-\> the recovered primary is (re)added to the primary inner ECMP and the group issues a single `SET_SWITCHOVER=false`; verify the primary inner ECMP is current.  
- Standby down while not switched over \-\> the standby **inner ECMP** shrinks; verify no `SET_SWITCHOVER`.  
- Standby down while switched over (not the last) \-\> the active standby **inner ECMP** shrinks; verify no `SET_SWITCHOVER`. Last live standby down \-\> all-paths-dead handling (§8.7).  
- All-paths-dead \-\> verify orchagent pre-check aborts the switchover (no `SET_SWITCHOVER` issued, primary inner ECMP left in place); verify recovery on either side.  
- Route update that changes the NH set \-\> verify deterministic key, refcount transitions, and old protection-NHG (with its private inner ECMPs) destroyed when refcount==0.  
- Back-to-back primary flaps (rapid up\-\>down\-\>up\-\>down) \-\> verify OA/SAI resource churn is bounded (no NHG/member OID leak, switchover count tracks the flaps) and the group converges to the correct active subset; stress at a high flap rate to constrain OA and HW resource usage.

### 16.3 Negative tests

- Capability not advertised \-\> protection-NHG path disabled, route falls back to ECMP-over-primaries with the documented WARN.  
- `primary_nh_count > len(nexthop)` \-\> WARN, row skipped.

---

## 17\. Open Questions and Future Work

1. **Tunnel/overlay next-hop members.** Phase 2\.  
2. **Hardware/SDK-driven switchover.** Using `SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION` with per-member monitored objects (interface / BFD session state) so the ASIC/SDK performs switchover without orchagent issuing `SET_SWITCHOVER`. Out of scope for this design (§5); the switchover here is orchagent-driven.  
3. **Combination with ARS / adaptive load balancing.** A protection NHG is a distinct SAI NHG type; combining it with ARS/ALB on the same group is not supported today and would need separate design.

