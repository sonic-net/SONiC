# Event-Driven Retry for Orchagent Route Programming

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
  - [6.1. Existing design](#61-existing-design)
  - [6.2. Issues with the existing design](#62-issues-with-the-existing-design)
  - [6.3. New design overview](#63-new-design-overview)
- [7. High-Level Design](#7-high-level-design)
  - [7.1. Task lifecycle](#71-task-lifecycle)
  - [7.2. RetryCache constraints](#72-retrycache-constraints)
  - [7.3. Partial next hop groups](#73-partial-next-hop-groups)
  - [7.4. Single next hop route on an unresolved neighbor](#74-single-next-hop-route-on-an-unresolved-neighbor)
  - [7.5. ECMP route with no programmable member](#75-ecmp-route-with-no-programmable-member)
  - [7.6. Route on an unsynced NHG index](#76-route-on-an-unsynced-nhg-index)
  - [7.7. SAI resource exhaustion](#77-sai-resource-exhaustion)
  - [7.8. Stuck-park reporting](#78-stuck-park-reporting)
  - [7.9. Where parking is disabled](#79-where-parking-is-disabled)
  - [7.10. Modules and repositories affected](#710-modules-and-repositories-affected)
  - [7.11. SWSS / Syncd changes](#711-swss--syncd-changes)
  - [7.12. DB and schema changes](#712-db-and-schema-changes)
  - [7.13. Scalability and performance](#713-scalability-and-performance)
  - [7.14. Serviceability and debug](#714-serviceability-and-debug)
  - [7.15. Platform dependency](#715-platform-dependency)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
- [14. Open/Action items](#14-openaction-items)

## 1. Revision

| Rev | Date       | Author | Change Description |
| --- | ---------- | ------ | ------------------ |
| 0.1 | 2026-10-05 | Aviral Kapoor, Nilkamal Thakuria, Ravindra Bikkina, Suresh Krishnan Balakrishnan | Initial version |

## 2. Scope

This document describes how orchagent RouteOrch handles routes that cannot be programmed because something they depend on is not ready yet. It covers:

- Programming an ECMP route over the next hop group members that are resolved, and adding the remaining members as they resolve (partial next hop groups).
- Moving routes that cannot make progress out of the active retry set (`m_toSync`) into RouteOrch's RetryCache ("parking"), and replaying them when the blocking condition clears.
- Four blocking conditions: unresolved neighbor for a single next hop route, ECMP group with no programmable member, NhgOrch group index not yet synced, and SAI route table resource exhaustion.

Out of scope: label routes (`APP_LABEL_ROUTE_TABLE`), fine-grained ECMP, protection next hop groups, overlay/SRv6 next hop groups, next hop group capacity exhaustion and NhgOrch's own retry of `NEXTHOP_GROUP_TABLE`. These keep the existing retry behavior.

## 3. Definitions/Abbreviations

| Term | Meaning |
| ---- | ------- |
| m_toSync | Per-consumer map of pending tasks in orchagent. Every task in it is re-run on each orchagent event and once a second when idle. |
| RetryCache | Existing orchagent store (`retrycache.h`) that holds tasks keyed by the constraint blocking them. Already used for PIC contexts and ACL rules. |
| Constraint | A (type, data) pair that names what a parked task is waiting for, for example (`RETRY_CST_UNRESOLVED_NH`, `"10.0.0.1@Ethernet0"`). |
| Park | Move a task from `m_toSync` into the RetryCache under a constraint. |
| Notify | Mark a constraint resolved when the event that can unblock it happens (`notifyRetry`). |
| Replay | Move the tasks under a resolved constraint back into `m_toSync` (`retryToSync`, quota-bounded). |
| Deferred member | A next hop group member that is part of the group key but has no SAI member object yet because its neighbor is unresolved. |
| NHG | Next hop group |
| DVS | Docker virtual switch test framework |

## 4. Overview

Before this work, RouteOrch handled every "not ready yet" failure the same way: the task stayed in `m_toSync` and was retried on every drain with no cap. For two classes of failure the retry can never succeed until an external event happens:

- The next hop neighbor is not resolved. Only the first attempt triggers ARP/ND, so later retries do no work.
- The ASIC route table is full. Each retry fails again, and for ECMP routes each retry creates and destroys a next hop group.

At scale this kept orchagent at 92 to 99 percent CPU with no ASIC progress (for example, about 35K routes on an unresolvable RFC 5549 next hop, or a route table filled past capacity), which in turn delayed other orch agents.

In addition, an ECMP route was programmed all-or-nothing. If any member was unresolved, the route fell back to a single, randomly chosen path until every member resolved.

This design makes route programming event-driven. A route that can forward on part of its next hops is programmed over those members. A route that cannot make progress is parked and costs no CPU until the event that unblocks it arrives.

## 5. Requirements

1. An ECMP route with at least one resolved member must be programmed over its resolved members, with weights preserved, and the remaining members must join the same group as they resolve.
2. A route blocked on an unresolved neighbor, an unsynced NHG index or SAI resource exhaustion must not be re-run until an event that can unblock it occurs.
3. A parked route must be replayed when its blocker clears, without operator action.
4. If a route is deleted while it is parked, the parked add must be discarded, so the route is not installed when its blocker clears.
5. Parking must only be used where an unblocking event is guaranteed to notify. Where it is not, the existing hot retry is kept.
6. Each parking mode must have a kill switch that restores the previous behavior exactly.
7. Parked routes must be visible for debugging.
8. No change to CONFIG_DB, APPL_DB, YANG models or CLI.

## 6. Architecture Design

### 6.1. Existing design

```
APPL_DB ROUTE_TABLE --> RouteOrch m_toSync --> doTask() --> addRoute()
                             ^                                 |
                             |        fails (neighbor          |
                             +------- unresolved / table  <----+
                                      full / NHG not synced)
             re-run on every event and every 1 s idle timer, no cap
```

For ECMP routes, `addNextHopGroup()` fails if any member is unresolved and `addTempRoute()` installs a single random member.

### 6.2. Issues with the existing design

- CPU cost grows with the number of blocked prefixes, and the work produces no result.
- The busy RouteOrch drain delays neighbor, interface and other orch processing, which slows down the very events that would unblock the routes.
- A multipath route forwards on one link while any member is unresolved. For a weighted route, the single path can be the lightest member.

### 6.3. New design overview

```
                          +-------------------------------+
APPL_DB ROUTE_TABLE --->  | RouteOrch m_toSync / doTask() |
                          +-------------------------------+
                             |  partial ECMP: program         ^
                             |  resolved members (forwarding) |  replay (quota-bounded,
                             |                                |  next doTask)
                             v blocked                        |
                          +-------------------------------+   |
                          | RetryCache (parked tasks)     |---+
                          |  UNRESOLVED_NH   "ip@alias"   |
                          |  UNRESOLVED_NHG  group key    |
                          |  NHG_INDEX       index        |
                          |  SAI_RESOURCE    ""           |
                          +-------------------------------+
                                       ^ notifyRetry(constraint)
          +-----------------------+----+------------------+-----------------------+
          | NeighOrch: next hop   | NhgOrch/CbfNhgOrch:   | RouteOrch: route      | 60 s sweep
          | inserted and usable   | group synced          | deleted               | (resource only)
          +-----------------------+-----------------------+-----------------------+
```

Two complementary changes:

- **Partial next hop groups**: an ECMP route with any resolved member is programmed, so it leaves `m_toSync`. Deferred members join the existing group in place when their neighbor resolves or their link/BFD recovers.
- **Parking**: a route with nothing to program, or one rejected for lack of SAI resources, is moved to the RetryCache under a constraint and replayed when that constraint is notified.

## 7. High-Level Design

### 7.1. Task lifecycle

1. **Park**: `addRoute()` or `addRoutePost()` stamps the blocking constraint on the bulk context and returns without queuing SAI work. After the bulk flush, the task is moved from `m_toSync` into the RetryCache.
2. **Notify**: the component that owns the unblocking event calls `notifyRetry()` for the constraint. A notify for a constraint with nothing parked is a no-op.
3. **Replay**: on the next `Orch::doTask()`, `retryToSync()` moves the tasks under resolved constraints back into `m_toSync`, bounded by a quota. Each task is evaluated from scratch.
4. **Re-park**: a task that is still blocked parks again under its current constraint.

If a route is deleted while it is parked, the parked add is discarded (`Consumer::addToSync()` removes it from the RetryCache) and only the delete is processed. Without this, the route would be installed later, when its blocker clears, even though it no longer exists in APPL_DB. If a newer add for the same route arrives while it is parked, the parked add is merged with it, the same way two queued adds are merged today, so an outdated version of the route is never replayed.

The RetryCache keeps a reverse index from constraint to keys, so a replay only visits the tasks waiting on the constraint that was notified.

### 7.2. RetryCache constraints

| Constraint | Data | Parked when | Notified by |
| ---------- | ---- | ----------- | ----------- |
| RETRY_CST_UNRESOLVED_NH | "ip@alias" | Single next hop route whose neighbor is unresolved, or resolved but interface down / BFD down | NeighOrch, when the next hop is inserted into `m_syncdNextHops` and is usable, or its last down flag clears |
| RETRY_CST_UNRESOLVED_NHG | ECMP group key | ECMP route where no member is programmable | NeighOrch, through a reverse index from next hop to waiting groups, when any member becomes usable |
| RETRY_CST_NHG_INDEX | NHG index | Route with `nexthop_group` set to an NhgOrch/CbfNhgOrch group that is not synced yet | NhgOrch/CbfNhgOrch, when the group is created (`emplaceNhg()`) |
| RETRY_CST_SAI_RESOURCE | "" (one global bucket) | Route create or set returns TABLE_FULL, INSUFFICIENT_RESOURCES, NO_MEMORY or NV_STORAGE_FULL | RouteOrch, after a successful route delete; plus a 60 s sweep |

The existing `RETRY_CST_PIC` and `RETRY_CST_PIC_REF` constraints and ACL usage of the RetryCache are unchanged.

### 7.3. Partial next hop groups

Applies to RouteOrch-built groups and to NhgOrch groups (`nexthop_group=enabled`).

- An unresolved member no longer fails the group create. It is added to the group as a deferred member with no SAI member object, and the group is programmed over the resolved members. If no member is resolved, the create still fails (see 7.5).
- The group stays keyed by the full member set. The group OID does not change when members join, so ARS and other holders of the group id are not affected.
- Ordered ECMP sequence ids are reserved over the full key, so a member that joins later takes the slot it would have had.
- A deferred member joins on neighbor resolution (`NeighOrch::notifyNextHopResolved`) or on link/BFD recovery. A pending-group index keyed by ip+alias finds the groups to update without walking all routes.
- Reference counts follow the SAI member object: a deferred member is counted when it joins and released only if it was taken.
- Route observers (MirrorOrch, AclOrch, NatOrch, TamOrch) are given the installed subset. If no member is installed, they are given the full key.
- A member whose SAI create fails is flagged so it does not block the default route next hop swap.
- Overlay/VXLAN and SRv6 groups stay all-or-nothing, because their members do not come from neighbor resolution.

### 7.4. Single next hop route on an unresolved neighbor

- A single next hop route whose neighbor is unresolved calls `resolveNeighbor()` and parks under `RETRY_CST_UNRESOLVED_NH` keyed by `"ip@alias"`. The key is built the same way on the park and notify sides, so labels and weights do not affect matching.
- NeighOrch notifies through `registerSyncdNextHop()`, which every plain-neighbor insertion into `m_syncdNextHops` goes through. Tunnel and SRv6 next hops are skipped.
- If the neighbor is created while the interface is down or BFD is down, the route stays parked and is replayed when the next hop becomes usable. It is not installed as a blackhole in the meantime.
- At park time RouteOrch re-checks `hasNextHop()`, so a neighbor created earlier in the same `doTask()` batch is not missed.
- An ECMP route with at least one resolved member is not parked, since it is already forwarding (7.3).

### 7.5. ECMP route with no programmable member

- When every member of a classic ECMP group is unresolved or down, the route parks under `RETRY_CST_UNRESOLVED_NHG` keyed by the whole group.
- A reverse index maps each next hop to the groups waiting on it. When any member becomes usable, `releaseRoutesParkedOnNextHop()` notifies every waiting group. This avoids parking on one chosen member and missing a different member that resolves first.
- On replay, the route is programmed as a partial group over the members that are now usable (7.3).
- Groups with overlay/SRv6 members or interface next hops (`0.0.0.0@EthernetX`) are not parked, because nothing would notify for them. They keep the hot retry.
- `pruneOrphanedParkedGroups()` removes reverse index entries whose parked task was discarded by a delete.

### 7.6. Route on an unsynced NHG index

- With `nexthop_group=enabled`, a route that names an NhgOrch group index that is not synced yet parks under `RETRY_CST_NHG_INDEX`. Previously it was set aside and merged straight back into `m_toSync`.
- `NhgOrchCommon::emplaceNhg()` both stores the group and notifies, so every group create site, including CbfNhgOrch, wakes the routes parked on that index.
- NhgOrch's own retry of `NEXTHOP_GROUP_TABLE` is unchanged. It is bounded by the number of unique ECMP sets, not by prefixes.

### 7.7. SAI resource exhaustion

- When a route create or set returns a resource status, `addRoutePost()` requests a park under `RETRY_CST_SAI_RESOURCE` before any refcount or CRM change, so a replay starts from clean accounting. A just-created group with no other users is removed first.
- If several routes share a group that was torn down because of a resource failure, all of them park in the same pass, with one group create and one remove.
- A successful route delete in `removeRoutePost()` notifies the constraint once per resolution.
- When a replayed route parks again, the constraint is marked unresolved, so the replay stops after one batch until the next delete or sweep. The table being full does not cause a loop.
- A 60 s sweep timer marks the constraint resolved if anything is parked under it. This covers capacity freed without a route delete, for example on DNX where the route and host tables share a pool and a neighbor removal frees route capacity.
- Non-resource failures are not parked and keep their existing handling.

### 7.8. Stuck-park reporting

A parked route is not in `m_toSync` and not in ASIC_DB, so it can look like a missing route with an idle orchagent. `warnOnStuckParks()` logs a WARNING once per constraint when a park has been outstanding for more than 600 s, and a NOTICE when it clears. It covers every constraint RouteOrch parks on, including PIC.

### 7.9. Where parking is disabled

| Condition | Effect | Reason |
| --------- | ------ | ------ |
| Dual-ToR (mux) | Neighbor and NHG-group parking off | A mux neighbor can become usable through MuxOrch without the NeighOrch insert that notifies. |
| VOQ chassis (CHASSIS_APP_DB in use) | Neighbor and NHG-group parking off | Remote-ASIC neighbors arrive through CHASSIS_APP_DB and do not notify. A standalone (single-ASIC) VOQ switch parks normally. |
| Overlay/SRv6 members, interface next hops | Not parked | No neighbor event will notify. |
| Label routes, fine-grained ECMP, protection NHG, NHG capacity exhaustion | Not parked | Out of scope; existing hot retry. |

### 7.10. Modules and repositories affected

| Repository | Files |
| ---------- | ----- |
| sonic-swss | `orchagent/retrycache.h`, `orch.cpp`, `routeorch.{h,cpp}`, `neighorch.{h,cpp}`, `nhgorch.{h,cpp}`, `nhgbase.h`, `cbf/cbfnhgorch.cpp`, mock tests, `tests/test_nhg.py` |
| sonic-mgmt | `tests/route/test_unresolved_nexthop_park.py`, route resource parking test |

### 7.11. SWSS / Syncd changes

All changes are in orchagent. No changes to syncd, sairedis or fpmsyncd.

### 7.12. DB and schema changes

None.

### 7.13. Scalability and performance

- A parked route costs no CPU until its constraint is notified.
- Replay is quota-bounded per `doTask()` and visits only the keys under resolved constraints.
- Partial group promotions are done in place, so a member join is one SAI member create, not a group re-create.
- Measured on a standalone VOQ switch: with 10,000 single next hop routes and 5,000 ECMP routes on unresolved neighbors, orchagent CPU went from 99 percent to 0 percent. After the neighbors resolved, the routes were programmed in 770 ms and 865 ms respectively.

### 7.14. Serviceability and debug

- `dumpPendingTasks` includes parked tasks, annotated with `retry_cst:(type, data)`.
- The retry recorder (`retry.rec`) logs every park, notify and replay.
- Stuck-park WARNING/NOTICE syslog messages (7.8).

### 7.15. Platform dependency

None in code. On DNX, route capacity freed by neighbor removal is picked up by the 60 s sweep rather than by a delete notification.

## 8. SAI API

No new SAI APIs or attributes. Existing next hop group, next hop group member and route entry APIs are used. Partial groups use member create/remove on an existing group.

## 9. Configuration and management

### 9.1. Manifest (if the feature is an Application Extension)

Not applicable.

### 9.2. CLI/YANG model Enhancements

None. The behavior is controlled by orchagent environment variables, all enabled by default:

| Variable | Default | Effect when set |
| -------- | ------- | --------------- |
| ORCH_ROUTE_NEIGH_PARK | on | `0` disables unresolved-neighbor and ECMP-group parking (UNRESOLVED_NH, UNRESOLVED_NHG) |
| ORCH_ROUTE_NHG_INDEX_PARK | on | `0` disables NHG index parking (NHG_INDEX) |
| ORCH_ROUTE_RESOURCE_PARK | on | `0` disables SAI resource parking (SAI_RESOURCE) |
| ORCH_ROUTE_PARK_WARN_SEC | 600 | Stuck-park report threshold in seconds; `0` disables the report |

Partial next hop groups have no knob.

### 9.3. Config DB Enhancements

None.

## 10. Warmboot and Fastboot Design Impact

No change to warm or fast boot flows. The RetryCache is in memory and is rebuilt from APPL_DB replay after restart. The stuck-park age table is not preserved across an orchagent restart. Ordering between NeighOrch and RouteOrch reconciliation is unchanged; partial groups during warm restart are covered by unit tests only.

## 11. Memory Consumption

Parked tasks move from `m_toSync` to the RetryCache, so total task memory is about the same. The additional memory is the constraint-to-keys index, the next hop to parked-group index and the pending-member index for partial groups, each proportional to the number of parked routes or deferred members. No memory is used when nothing is parked.

## 12. Restrictions/Limitations

- Label routes, fine-grained ECMP, protection NHG, overlay/SRv6 groups and NHG capacity exhaustion still hot-retry.
- Neighbor parking is off on dual-ToR and VOQ chassis.
- Resource parking does not cover routes on NhgOrch-owned groups or route DEL failures.
- If NhgOrch drops a `NEXTHOP_GROUP_TABLE` entry on a validation error, routes parked on that index wait until the stuck-park report fires. They would not have programmed under the old behavior either.
- A partially programmed group key can differ from what is installed in the ASIC until all members join.

## 13. Testing Requirements/Design

### 13.1. Unit Test cases

| Area | Cases |
| ---- | ----- |
| Partial NHG | Partial create; late join on resolution and on link/BFD recovery; labeled members; overlay fail-closed; ARS replicate path; deferred-member refcounts; teardown; default-route swap with a failed and a pending member; observers keep full key when nothing installed; shared resolution key index |
| Neighbor parking | Single next hop park and replay; no reprocessing while blocked; constraint keying; delete discards parked add; ECMP partial not parked; standalone VOQ parks; VOQ chassis does not park |
| ECMP / NHG index parking | All-unresolved ECMP parks and replays on any member; NHG index parks until group syncs; orphan prune; re-park; stuck-park report |
| Resource parking | Create TABLE_FULL parks; shared NHG parks in one pass; SET parks; delete notifies and replays; no-op delete does not notify; re-park halts drain; sweep replays and is a no-op when empty; delete discards parked add; kill switch restores hot retry; non-resource error not parked |

### 13.2. System Test cases

| Suite | Cases |
| ----- | ----- |
| DVS (`tests/test_nhg.py`) | `test_route_nhg_partial_unresolved_neighbor`, `test_nhgorch_partial_unresolved_neighbor`, `test_route_nhg_ifdown_during_arp`, `test_route_nhg_all_members_unresolved_parked`, `test_route_nhg_index_parked_until_group_syncs` |
| sonic-mgmt `route/test_unresolved_nexthop_park.py` | Single next hop park and replay; not reprocessed while blocked; shared neighbor replays all; delete discards parked route; ECMP all-unresolved parked; ECMP partial not parked; scale, parked routes stay off ASIC (IPv4 and IPv6) |
| sonic-mgmt route resource parking | Fill the route table past capacity; overflow routes park; delete replays |

## 14. Open/Action items

- Extend parking to label routes and the remaining hot-retry cases listed in section 12.
