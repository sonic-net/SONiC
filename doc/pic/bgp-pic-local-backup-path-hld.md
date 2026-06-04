# BGP PIC Local (Fast Reroute) High-Level Design

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions / Abbreviations](#3-definitionsabbreviations)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
   - 7.1 [BGP Bestpath Computation and Backup Path Selection](#71-bgp-bestpath-computation-and-backup-path-selection)
   - 7.2 [ZAPI Message: BGP → Zebra](#72-zapi-message-bgp--zebra)
   - 7.3 [Netlink Message: Zebra → fpmsyncd](#73-netlink-message-zebra--fpmsyncd)
   - 7.4 [APP_DB Schema: Primary and Backup Paths](#74-app_db-schema-primary-and-backup-paths)
   - 7.5 [Orchagent (TBD)](#75-orchagent-tbd)
8. [Configuration and Management](#8-configuration-and-management)
   - 8.1 [FRR Configuration](#81-frr-configuration)
   - 8.2 [YANG Model](#82-yang-model)
   - 8.3 [Config DB](#83-config-db)
9. [Information Flow Diagrams](#9-information-flow-diagrams)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions / Limitations](#12-restrictionslimitations)
13. [Testing Requirements / Design](#13-testing-requirementsdesign)
14. [Open / Action Items](#14-openaction-items)

---

## 1. Revision

| Rev | Date       | Author                                         | Description      |
|-----|------------|------------------------------------------------|------------------|
| 0.1 | 2026-04-10 | Venkit Kasiviswanathan                         | Initial version  |
| 0.2 | 2026-05-12 | Venkit Kasiviswanathan                         | Replace the "stash `backup_idx[]` on the first primary" convention with an explicit, self-describing wire flag: `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN` on the ZAPI side, mirrored by a parent-NHE flag `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN` and a `dplane_route_info::backup_all_primaries_down` boolean (with accessor) on the zebra/dplane side. Updates §7.2, §8.1 JSON examples, §12, §13, §14 accordingly. |
| 0.3 | 2026-06-04 | Venkit Kasiviswanathan                         | Sync §7.1 with the final upstream FRR PR ([FRRouting/frr#21814](https://github.com/FRRouting/frr/pull/21814)): fix the per-path flag bit assignments (`BGP_PATH_BACKUP = 1 << 21`, `BGP_PATH_BACKUP_CHG = 1 << 22`); rework §7.1.4 so the backup-change check is folded into `bgp_zebra_has_route_changed()` (instead of a separate call-site `||`), document the same-best-path `BGP_PATH_BACKUP_CHG` clear in `bgp_process_main_one()` and the update-group UPDATE suppression; update the §9.2 flow diagram accordingly. |

---

## 2. Scope

This document covers the High-Level Design of **PIC Local**, also known as BGP Fast Reroute (FRR), for SONiC-based switching platform. PIC Local enables BGP to pre-compute a backup forwarding path and install it alongside the primary path in the data plane. Upon local link failure, the data plane switches to the backup path immediately — without waiting for BGP to reconverge.
If routes had ECMP paths, every ECMP member is usable and link failure handling essentially involves removing the failed member from the group. The scope and intent for this feature is to address a set of non-ideal and non-ECMP scenarios, where we dont have equidistant multi-paths. In such cases installing backup paths to quickly do local repair before control plane converges will limit traffic loss. 

One example of the above scenario is documented in section.4 of the PIC architecture HLD (https://github.com/sonic-net/SONiC/blob/master/doc/pic/bgp_pic_arch_doc.md). This feature could provide quick convergence at the egress side until the ingress recovers, by rerouting traffic to a peering PE where another path is available to reach the destination.

Additionally,

- **Single dominant next‑hop with a less preferred backup.**
  For many important prefixes (e.g., default route towards a border, DCI prefixes, service VRFs), operators deliberately steer traffic to a single primary border/exit, with a different border or path as a backup. Today, when the primary border/link fails, data-plane failover waits on BGP convergence. With PIC local, we pre‑compute an explicitly less-preferred backup and program it alongside the primary so we can switch locally without waiting for control-plane reconvergence.

- **Non‑equidistant or non‑Clos topologies.**
  SONiC is also used in collapsed core, WAN edge, and mixed DC/WAN environments where paths are not strictly equidistant, ECMP is not always available, and you still want sub‑second protection. Here, an explicit backup next‑hop that is not in the primary ECMP set is required.

- **Node/rack protection rather than just a single local link.**
  Even in DC, there are cases where the primary path is constrained to a particular device or rack (e.g., primary border leaf, services leaf). The goal is to have a pre‑installed backup via a different device/failure domain, not just “some other member of the same ECMP group,” so that a device/rack failure is locally protected.

This document describes the design and implementation across the following layers:

- **BGP (FRR bgpd)**: Backup path selection algorithm and ZAPI messaging
- **Zebra**: Backup nexthop encoding in FPM netlink messages
- **fpmsyncd**: Parsing and programming backup nexthops to APP_DB
- **YANG / Config**: Configuration models for enabling the feature
- **Orchagent**: *(TBD — Not part of this HLD)*
- **Nexthop-Group**: (TBD — Not part of this HLD)

---

## 3. Definitions / Abbreviations

| Term        | Definition |
|-------------|------------|
| PIC         | Prefix Independent Convergence |
| FRR         | Fast Reroute (also the name of the routing suite) |
| PIC Local   | PIC for locally attached interfaces; synonymous with BGP Fast Reroute |
| BGP         | Border Gateway Protocol |
| ECMP        | Equal-Cost Multi-Path |
| NHG         | Nexthop Group |
| FIB         | Forwarding Information Base |
| RIB         | Routing Information Base |
| FPM         | Forwarding Plane Manager |
| ZAPI        | Zebra API (protocol between BGP daemon and Zebra) |
| APP_DB      | Application Database (Redis, interface between fpmsyncd and orchagent) |
| ASIC_DB     | ASIC Database (Redis, interface between orchagent and syncd) |
| AFI/SAFI    | Address Family Identifier / Subsequent Address Family Identifier |
| bgpcfgd     | BGP Configuration Daemon (Python) |
| frrcfgd     | FRR Configuration Daemon |
| SAI         | Switch Abstraction Interface |

---

## 4. Overview

Prefix Independent Convergence (PIC) is a family of techniques that make routing convergence time independent of the number of affected prefixes. The three flavors are:

- **PIC Core** — fast convergence on underlay/IGP failures, by updating a shared Nexthop Group rather than individual routes.
- **PIC Edge** — fast convergence when a remote BGP peer (overlay endpoint) becomes unreachable.
- **PIC Local** — fast convergence on locally connected interface failures, using pre-computed primary/backup paths.

For background on PIC Core and PIC Edge, see the SONiC PIC architecture document: [bgp_pic_arch_doc.md](https://github.com/sonic-net/SONiC/blob/master/doc/pic/bgp_pic_arch_doc.md). The IETF specification is at [draft-ietf-rtgwg-bgp-pic](https://datatracker.ietf.org/doc/draft-ietf-rtgwg-bgp-pic/).

This document covers **PIC Local** only.

**PIC Local** (also called Fast Reroute) protects against failure of a locally connected interface. BGP pre-computes a backup path alongside the primary and installs both in the FIB. When the local link fails, the data plane switches to the backup immediately — without waiting for BGP to reconverge. BGP reconverges in the background and eventually replaces the backup-as-primary with a newly selected best path.

The implementation extends the FRR stack:
1. **bgpd** computes a backup path (or ECMP set) after bestpath selection and sends it to Zebra via ZAPI. The wire format is self-describing: a new ZAPI message bit `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN` names the PIC-Local semantic (engage backups only when *all* primaries are down) — primary nexthops on the wire carry **no** `HAS_BACKUP` flag or `backup_idx[]`.
2. **Zebra** mirrors the wire bit onto a parent-NHE flag `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN` (so the flag participates in NHE hash key/equality) and onto a `backup_all_primaries_down` boolean inside the dplane context (with accessor `dplane_ctx_get_backup_all_primaries_down()`). zebra also encodes backup nexthops in FPM netlink messages to fpmsyncd as a SONiC-private attribute (`FPM_RTA_BACKUP_NH = 200`).
3. **fpmsyncd** stores primary and backup nexthops together in APP_DB, using `primary_nh_count` to distinguish them.
4. **Orchagent** currently programs only primary nexthops; backup nexthop hardware programming is TBD.

The current HLD intentionally focuses on the end-to-end control-plane paths and data model:

- bgpd: backup path computation and signalling
- zebra: encoding backup nexthops in FPM (`FPM_RTA_BACKUP_NH` SONiC-private attribute)
- fpmsyncd / APP_DB: modelling primary and backup nexthops

The orchagent/SAI parts are marked TBD. It will be covered in another HLD. It gives us an opportunity to get agreement on 

1. The semantics and selection rules for primary vs backup paths
2. The configuration/YANG model and how backup information flows through APP_DB 

**NOTE**: Until the orchagent design/changes to consume the primary+backup info from APP_DB and map it into ASIC nexthop groups and use concrete SAI API for primary/backup groups, this feature does **not** deliver hardware failover for data-plane traffic yet. It only prepares the control-plane and data-model side.

---

## 5. Requirements

1. BGP SHALL compute at most one backup path per prefix when `install backup-path` is configured.
2. BGP SHALL compute multiple equal-cost backup paths (ECMP) when `install backup-path ecmp` is configured, respecting `maximum-paths` configuration. The maximum-paths limit apply to backup paths separately from bestpaths.
3. The backup path MUST NOT include any nexthop that is already in the primary ECMP set. This ensures that the backup path represents a different failure domain.
4. Backup path computation SHALL be triggered after bestpath selection for each destination.
5. Backup paths SHALL be sent to Zebra via ZAPI as backup nexthops alongside primary nexthops.
6. Zebra SHALL encode backup nexthops in FPM netlink messages distinctly from primaries (Implemented as a SONiC-private top-level attribute `FPM_RTA_BACKUP_NH = 200` carrying a sequence of `struct rtnexthop` entries).
7. fpmsyncd SHALL store both primary and backup nexthops in APP_DB with appropriate way to distinguish between them (Implemented using `primary_nh_count` field to distinguish them)
8. The feature SHALL be configurable per AFI/SAFI (IPv4 unicast, IPv6 unicast only).
9. The feature SHALL be configurable device-wide (via `BGP_DEVICE_GLOBAL_AF`) or per-VRF (via `BGP_GLOBALS_AF`).
11. When the feature is disabled, backup paths SHALL be flushed and Zebra SHALL be notified to remove them from the FIB.
12. Orchestrator support for hardware programming of backup paths is **TBD** (out of scope for current implementation).
13. The Zebra nexthop-group support is also **TBD** (out of scope for this HLD)

---

## 6. Architecture Design

The overall architecture follows the existing SONiC routing stack. PIC Local adds a new data flow for **backup nexthops** alongside the existing primary nexthop flow.

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                        FRR (Docker: bgp)                        │
    │                                                                 │
    │  ┌─────────────────┐   ZAPI    ┌──────────────────────────────┐ │
    │  │   bgpd          │ ────────► │  zebra                       │ │
    │  │                 │           │                              │ │
    │  │ - bestpath      │           │ - RIB/FIB management         │ │
    │  │ - backup path   │           │ - Netlink kernel updates     │ │
    │  │   computation   │           │ - FPM netlink to fpmsyncd    │ │
    │  └─────────────────┘           └──────────────────────────────┘ │
    │                                          │ FPM (netlink)        │
    └──────────────────────────────────────────┼──────────────-───────┘
                                               │
    ┌──────────────────────────────────────────▼──────────────-───────┐
    │                     fpmsyncd                                    │
    │                                                                 │
    │  - Receives RTM_NEWROUTE netlink messages                       │
    │  - Parses primary + backup nexthops (FPM_RTA_BACKUP_NH attr)    │
    │  - Writes to APP_DB:ROUTE_TABLE with primary_nh_count           │
    └──────────────────────────────────────────┬──────────────-───────┘
                                               │ APP_DB (Redis)
    ┌──────────────────────────────────────────▼──────────────-───────┐
    │                     orchagent                                   │
    │                                                                 │
    │  - Reads ROUTE_TABLE from APP_DB                                │
    │  - Currently programs only primary nexthops to ASIC_DB          │
    │  - Backup nexthop programming: TBD                              │
    └──────────────────────────────────────────┬─────────────────────┘
                                               │ ASIC_DB (Redis)
    ┌──────────────────────────────────────────▼──────────────-───────┐
    │                     syncd / SAI                                 │
    │  - Programs routes into hardware ASIC                           │
    └─────────────────────────────────────────────────────────────────┘

Configuration flow:
    ┌────────────────--------┐       ┌─────────────────┐      ┌─────────────┐
    │  CONFIG_DB             │──────►│  bgpcfgd /      │─────►│  FRR vtysh  │
    │  BGP_DEVICE_GLOBAL_AF  │       │   frrcfgd       │      │  (bgpd)     │
    │  or                    │       │  (translation)  │      │             │
    │  BGP_GLOBALS_AF        │       └─────────────────┘      └─────────────┘
    └────────────────--------┘
```

**Key Components Modified:**

| Component             | Repository              | Change |
|-----------------------|-------------------------|--------|
| `bgpd/bgp_route.c`    | sonic-frr (FRR patch)   | Backup path computation, ZAPI encoding |
| `bgpd/bgpd.h`         | sonic-frr (FRR patch)   | New AF flags for backup path config |
| `bgpd/bgp_zebra.c`    | sonic-frr (FRR patch)   | ZAPI message with route-level backup nexthops (sets `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN`; primaries unannotated) |
| `lib/zclient.h`, `lib/zclient.c` | sonic-frr (FRR patch) | New ZAPI message bit `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN` (0x0800) for self-describing route-level backup semantic |
| `zebra/zebra_nhg.h`, `zebra/zebra_nhg.c` | sonic-frr (FRR patch) | New parent-NHE flag `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN`; participates in hash key/equality; propagated by `zebra_nhe_copy()`. Recursive-resolution guard so route-level pools are not overwritten by per-NH resolver backups. |
| `zebra/zebra_dplane.c`, `zebra/zebra_dplane.h` | sonic-frr (FRR patch) | New `dplane_route_info::backup_all_primaries_down` field + `dplane_ctx_get_backup_all_primaries_down()` accessor |
| `zebra/zapi_msg.c`    | sonic-frr (FRR patch)   | Decode `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN`; set the NHE flag pre-`zebra_nhe_copy()` so hash lookup is correct |
| `dplane_fpm_sonic/dplane_fpm_sonic.c` | sonic-frr (SONiC FPM plugin) | `FPM_RTA_BACKUP_NH` (=200) top-level attribute appender |
| `fpmsyncd/routesync.cpp` | sonic-swss          | Parse backup nexthops, write primary_nh_count |
| `fpmsyncd/routesync.h`   | sonic-swss          | primary_nh_count in RouteTableFieldValueTupleWrapper |
| `orchagent/routeorch.cpp`| sonic-swss          | Read and limit to primary_nh_count nexthops |
| `sonic-bgp-global.yang`  | sonic-yang-models   | install_backup_path enum in BGP_GLOBALS_AF |
| `sonic-bgp-device-global.yang` | sonic-yang-models | install_backup_path in BGP_DEVICE_GLOBAL_AF |
| `bgpcfgd/managers_device_global_af.py` | sonic-bgpcfgd | DeviceGlobalAfMgr |
| `templates/bgpd/bgpd.conf.db.addr_family.j2` | sonic-frr-mgmt-framework | FRR config template |

---

## 7. High-Level Design

### 7.1 BGP Bestpath Computation and Backup Path Selection

#### 7.1.1 Configuration Flags

Two new per-AFI/SAFI flags are added to `struct bgp` (`bgpd/bgpd.h`):

```c
/* BGP Per AF flags */
uint16_t af_flags[AFI_MAX][SAFI_MAX];
#define BGP_CONFIG_BACKUP_PATH          (1 << 12)   // install backup-path
#define BGP_CONFIG_BACKUP_PATH_ECMP     (1 << 13)   // install backup-path ecmp
#define BGP_CONFIG_BACKUP_PATH_FLUSH    (1 << 14)   // flush backup paths (transient)
```

And two new per-path flags (`BGP_PATH_BACKUP`, `BGP_PATH_BACKUP_CHG`) are added to `bgp_path_info` (`bgpd/bgp_route.h`):

```c
#define BGP_PATH_BACKUP       (1 << 21)  // path is selected as backup
#define BGP_PATH_BACKUP_CHG   (1 << 22)  // backup selection has changed (notify Zebra)
```

#### 7.1.2 Backup Path Selection Algorithm

Backup path computation runs in `bgp_compute_backup_path()` (called from `bgp_best_selection()`) **after** the primary ECMP set has been finalized by `bgp_path_info_mpath_update()`.

The algorithm:

```
Input:
  new_best     - the selected bestpath (primary)
  dest         - the BGP destination node
  mpath_cfg    - maximum-paths configuration
  afi, safi    - address family
  ecmp_enabled - whether BGP_CONFIG_BACKUP_PATH_ECMP is set

Algorithm:
  1. Clear all BGP_PATH_BACKUP flags from all paths.
     Track whether any flags changed (backup_changed).

  2. Iterate all paths under dest:
     a. Skip if path is in hold-down, peer not established, or path == new_best.
     b. Skip if path is in the primary ECMP set (BGP_PATH_MULTIPATH flag set).
     c. Select the FIRST remaining valid path as the first_backup.
     d. If ecmp_enabled:
          - Set maxpaths from first_backup's peer type (iBGP or eBGP).
          - For subsequent paths, call bgp_path_info_cmp() against first_backup.
          - If paths_eq, also mark as backup (up to maxpaths).
        Else:
          - Only one backup path is selected.

  3. If backup set changed: set BGP_PATH_BACKUP_CHG on new_best.
     This triggers Zebra notification.
```

Key eligibility checks in `is_path_valid_candidate_for_backup()`:

```c
static bool is_path_valid_candidate_for_backup(struct bgp *bgp,
    struct bgp_path_info *pi, struct bgp_path_info *new_best)
{
    // Reject paths in hold-down
    if (BGP_PATH_HOLDDOWN(pi)) return false;
    // Reject paths with disconnected peers
    if (!peer_established(pi->peer->connection)) return false;
    // Reject the bestpath itself
    if (pi == new_best) return false;
    // Reject existing primary ECMP paths
    if (CHECK_FLAG(pi->flags, BGP_PATH_MULTIPATH)) return false;
    return true;
}
```

#### 7.1.3 Integration with bgp_best_selection()

```c
void bgp_best_selection(...) {
    // ... existing primary selection and ECMP computation ...
    bgp_path_info_mpath_update(bgp, dest, new_select, old_select,
                               num_candidates, mpath_cfg);

    // Compute backup path (NEW)
    if (CHECK_FLAG(bgp->af_flags[afi][safi], BGP_CONFIG_BACKUP_PATH))
        bgp_compute_backup_path(bgp, new_select, dest, mpath_cfg, afi, safi);
    else if (CHECK_FLAG(bgp->af_flags[afi][safi], BGP_CONFIG_BACKUP_PATH_FLUSH))
        bgp_clear_backup_paths(new_select, dest);

    bgp_addpath_update_ids(bgp, dest, afi, safi);
    // ...
}
```

#### 7.1.4 Triggering Zebra Updates

When the primary best path is unchanged but the backup set is, the route still needs re-announcing to Zebra so the FIB picks up the new backup pool. Rather than adding a separate `|| CHECK_FLAG(...)` test at each call site, the backup-change check is folded directly into `bgp_zebra_has_route_changed()` so all of its existing callers see backup-set changes uniformly:

```c
/* bgpd/bgp_route.c — bgp_zebra_has_route_changed() */
if (CHECK_FLAG(selected->flags, BGP_PATH_IGP_CHANGED) ||
    CHECK_FLAG(selected->flags, BGP_PATH_MULTIPATH_CHG) ||
    CHECK_FLAG(selected->flags, BGP_PATH_LINK_BW_CHG) ||
    CHECK_FLAG(selected->flags, BGP_PATH_BACKUP_CHG))
    return true;
```

This ensures Zebra (and ultimately fpmsyncd) is notified whenever the backup path set changes, even if the primary route is otherwise unchanged.

The same-best-path branch in `bgp_process_main_one()` clears `BGP_PATH_BACKUP_CHG` alongside `BGP_PATH_MULTIPATH_CHG` and `BGP_PATH_LINK_BW_CHG` after the FIB update, so a subsequent process cycle does not re-fire on stale state.

A spurious peer announce from this path is harmless: the BGP route attributes do not change for a backup-only update, so the per-peer "is this an actual change?" filter in the update-group code (`bgpd/bgp_updgrp_adv.c`) suppresses the wire-side UPDATE.

#### 7.1.5 Flush Behavior on Disable

When the user runs `no install backup-path`:

1. `BGP_CONFIG_BACKUP_PATH` is cleared.
2. `BGP_CONFIG_BACKUP_PATH_FLUSH` is set temporarily.
3. `bgp_recalculate_afi_safi_bestpaths()` is called.
4. For each prefix, `bgp_clear_backup_paths()` clears all `BGP_PATH_BACKUP` flags and sets `BGP_PATH_BACKUP_CHG` if any were cleared.
5. Zebra receives an updated route with no backup nexthops.
6. Once the work queue drains, `BGP_CONFIG_BACKUP_PATH_FLUSH` is cleared via a completion callback.

---

### 7.2 ZAPI Message: BGP → Zebra

ZAPI is the internal IPC protocol between FRR daemons (bgpd, ospfd, etc.) and Zebra. It uses Unix domain sockets and a binary protocol defined in `lib/zclient.h` and `lib/zclient.c`.

#### 7.2.1 ZAPI Route Message Structure

For a PIC-Local route with backup nexthops, the `zapi_route` structure is populated as follows:

```
struct zapi_route {
    uint8_t  type;                    // ZEBRA_ROUTE_BGP
    prefix   prefix;                  // Destination prefix (e.g. 10.1.0.0/24)
    uint32_t message;                 // Flags set include:
                                      //   ZAPI_MESSAGE_NEXTHOP
                                      //   ZAPI_MESSAGE_BACKUP_NEXTHOPS              (NEW)
                                      //   ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN    (NEW)
    uint16_t nexthop_num;             // Number of primary nexthops (e.g. 3)
    zapi_nexthop nexthops[...];       // Primary nexthops, NO HAS_BACKUP, NO backup_idx[]

    uint16_t backup_nexthop_num;      // Number of backup nexthops (e.g. 2)
    zapi_nexthop backup_nexthops[...];// Route-level backup pool (NEW)
};
```

Two ZAPI message bits cooperate:

```c
/* lib/zclient.h */
#define ZAPI_MESSAGE_BACKUP_NEXTHOPS            0x40
#define ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN  0x0800   /* NEW */
```

- `ZAPI_MESSAGE_BACKUP_NEXTHOPS` says "a backup section follows."
- `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN` says "the section is a *route-scope* pool engaged only when **all** primaries are down" — the PIC-Local semantic.

#### 7.2.2 Backup Semantics: Route-Level vs Per-Nexthop Backup

This is the central design choice. The semantic differs from FRR's pre-existing per-nexthop backup model (used by IP-FRR / TI-LFA) and the difference shows up at every layer below — ZAPI, the parent NHE in zebra, and the dplane context handed to FPM providers.

**What FRR's existing nexthop/ZAPI model already supports.** The `zapi_nexthop` structure carries a per-primary-nexthop backup association:

```c
struct zapi_nexthop {
    ...
    uint8_t backup_num;
    uint8_t backup_idx[NEXTHOP_MAX_BACKUPS];   /* indices into
                                                * api->backup_nexthops[]
                                                */
};
```

Each primary nexthop can independently declare which backup nexthops protect it via the `ZAPI_NEXTHOP_FLAG_HAS_BACKUP` flag plus `backup_idx[]`. Two primaries can therefore reference different (possibly disjoint) backup sets — the natural shape for **per-nexthop protection** (TI-LFA / IGP fast reroute), where every primary has its own per-link or per-node alternate.

**What PIC Local wants ("all-primaries-down").** PIC Local does **not** want per-nexthop protection. The intent is:

> While **any** primary nexthop is up, traffic uses the primary set (potentially across all of them via ECMP). The backup nexthops are engaged in the data plane **only when every primary nexthop is down.**

There is one logical backup pool for the whole route, not one per primary. Concretely:

- If primaries are `{P0, P1, P2}` (ECMP) and one or two of them go down, the surviving primaries continue to forward — backups are not used.
- Only when `{P0, P1, P2}` are *all* down does the data plane fall over to the backup set `{B0, B1, ...}`.
- The backup set itself may be ECMP'd internally (`install backup-path ecmp`), but it acts as a single tier behind the primaries.

This matches the operator-facing examples PIC Local is designed for — "primary border / backup border", "primary leaf / backup leaf via a different rack" — where the failure event protected against is *loss of the whole primary path*, not loss of one ECMP member.

**How we express this on the wire.** Earlier versions of this design encoded the policy by overloading the first primary nexthop with `ZAPI_NEXTHOP_FLAG_HAS_BACKUP` plus `backup_idx[0..M-1]` (i.e. "anchor the backups to `nexthops[0]`"). That was a positional convention with no protocol-level signal — a reader had to know to look at `nexthops[0]` and to ignore the lack of annotations on the other primaries.

The design now uses an explicit, self-describing message bit:

```
api.message       |= ZAPI_MESSAGE_BACKUP_NEXTHOPS
api.message       |= ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN
api.nexthops[..]:
    no HAS_BACKUP flag, no backup_idx[]      /* primaries untouched */
api.backup_nexthops[0..M-1]:
    M backup nexthops belonging to the route as a whole
```

The two semantics co-exist in the protocol but are **orthogonal**:

- A producer that wants per-NH protection (TI-LFA, IP-FRR) sets `HAS_BACKUP` + `backup_idx[]` on individual primaries. The new message bit is **not** set.
- A producer that wants route-level protection (PIC Local) sets the new message bit. The primaries stay clean.

The cost is a single new bit; the benefit is a self-describing wire format that does not depend on convention.

**How the route-level semantic is stored in zebra.** A new flag tracks the same semantic on the parent `nhg_hash_entry`:

```c
/* zebra/zebra_nhg.h */
#define NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN (1 << 11)
```

Set on the **parent** NHE (the one whose `backup_info` is non-NULL) at ZAPI decode time when the wire bit was present. The inner pool NHE keeps `NEXTHOP_GROUP_BACKUP` as before — its meaning ("this NHE is a backup pool") is unchanged.

The flag participates in the NHE hash key and equality so two otherwise-identical NHEs that differ only in semantics produce distinct hash entries:

```c
/* zebra_nhg_hash_key() */
if (CHECK_FLAG(nhe->flags, NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN))
    key = jhash_1word(NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN, key);

/* zebra_nhg_hash_equal() */
if (CHECK_FLAG(nhe1->flags, NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN) !=
    CHECK_FLAG(nhe2->flags, NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN))
    return false;
```

`zebra_nhe_copy()` propagates the flag across copies so the hash lookup, the insert, and the later dplane-ctx population are all consistent.

**How dplane providers discover the semantic.** `dplane_route_info` gains a boolean that mirrors the parent NHE flag:

```c
/* zebra/zebra_dplane.c */
struct dplane_route_info {
    ...
    struct nexthop_group  backup_ng;
    bool                  backup_all_primaries_down;
    ...
};

/* zebra/zebra_dplane.h */
bool dplane_ctx_get_backup_all_primaries_down(
    const struct zebra_dplane_ctx *ctx);
```

`dplane_ctx_route_init()` sets the boolean from `re->nhe->flags` at the same site it `copy_nexthops()`-es the backup chain. An external FPM consumer (or the Lua dplane hook) decides between per-NH and route-level encoding by calling the accessor — no convention to remember, no `nexthops[0]`-special-cased reading. The SONiC `dplane_fpm_sonic` plugin only needs the backup chain itself for the `FPM_RTA_BACKUP_NH` emission (see §7.3); the accessor is exposed for any future consumer that wants to differentiate.

**Implication for ECMP backups.** When `install backup-path ecmp` is configured, `api.backup_nexthops[]` may contain multiple entries `{B0, B1, ...}`. Once all primaries are down the data plane is free to load-balance across the entire backup pool. The per-AF `maximum-paths` setting bounds the cardinality of the pool.

#### 7.2.3 ZAPI Message Construction (bgpd/bgp_zebra.c)

The function `bgp_zebra_announce()` is extended to populate backup nexthops. Per §7.2.2, primaries carry no backup annotation — the route-level semantic is conveyed entirely by message bits:

```c
/* Process backup paths - iterate through non-selected paths */
if (CHECK_FLAG(bgp->af_flags[afi][safi], BGP_CONFIG_BACKUP_PATH) &&
    info->net) {
    struct bgp_path_info *backup_path;
    unsigned int backup_nh_count = 0;

    for (backup_path = bgp_dest_get_bgp_path_info(dest);
         backup_path && backup_nh_count < NEXTHOP_MAX_BACKUPS;
         backup_path = backup_path->next) {

        /* Only process paths marked as backup */
        if (!CHECK_FLAG(backup_path->flags, BGP_PATH_BACKUP))
            continue;

        struct zapi_nexthop *backup_api_nh =
            &api->backup_nexthops[backup_nh_count];
        zapi_nexthop_init(backup_api_nh);          /* see note below */
        /* ... fill in type, gate, ifindex, weight, labels, etc ... */
        backup_nh_count++;
    }

    if (backup_nh_count > 0) {
        /* Route-level "all-primaries-down" pool. Primaries are NOT
         * annotated; the semantic is carried by the message bit only.
         */
        api->backup_nexthop_num = backup_nh_count;
        SET_FLAG(api->message, ZAPI_MESSAGE_BACKUP_NEXTHOPS);
        SET_FLAG(api->message, ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN);
    }
}
```

**Implementation note.** `zapi_route_init()` deliberately omits the large `nexthops[]` and `backup_nexthops[]` arrays from its memset to keep route construction cheap. The primary loop already calls `zapi_nexthop_init()` per slot to zero just-enough state; the backup loop must do the same. Skipping this step leaves stack residue in `flags` / `seg_num` and corrupts the encoded ZAPI stream — zebra rejects it with `stream_get2: Attempt to get out of bounds`.

#### 7.2.4 Zebra Processing of ZAPI Backup Nexthops

In `zebra/zapi_msg.c`, `zapi_route_decode()` reads the backup section when `ZAPI_MESSAGE_BACKUP_NEXTHOPS` is set:

```c
if (CHECK_FLAG(api.message, ZAPI_MESSAGE_BACKUP_NEXTHOPS)) {
    // Read backup_nexthop_num
    // For each backup nexthop, parse into zapi_nexthop
}
```

`zapi_read_nexthops()` then converts each entry into a kernel-style `nexthop` and stores it in `nhg_backup_info` inside the route entry's NHE.

When `ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN` is **also** set, `zread_route_add()` sets `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN` on the temporary NHE *before* `zebra_nhe_copy()` so the flag participates in the hash lookup/insert (see §7.2.2). `zebra_nhe_copy()` propagates the flag across copies; `dplane_ctx_route_init()` mirrors it onto the dplane ctx as `backup_all_primaries_down`. Consumers reach the backup chain via `dplane_ctx_get_backup_ng()` and the policy via `dplane_ctx_get_backup_all_primaries_down()`.

#### 7.2.5 Recursive Resolution

Zebra's recursive resolver (`nexthop_active()` → `resolve_backup_nexthops()` in `zebra/zebra_nhg.c`) merges the *resolver's* per-NH backup info into the resolved nexthop's NHE when the resolver carries `NEXTHOP_FLAG_HAS_BACKUP` (TI-LFA / IP-FRR style). This pre-existing mechanism is **not** extended to route-level pools:

- A resolver flagged `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN` does not cascade its pool down to a route that resolves through it. Each PIC-Local route uses the pool its own producer (bgpd) computed.
- The recursive-merge call site is guarded so it does not overwrite a resolved NHE that already has the route-level flag set:

  ```c
  if (resolver && newhop->backup_num > 0 &&
      !CHECK_FLAG(nhe->flags, NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN))
      resolve_backup_nexthops(newhop, match->nhe, resolver, nhe, &map);
  ```

  Without this guard, a per-NH-protected resolver would append per-NH backups to a parent NHE flagged route-level, producing a pool whose entries had mixed engagement semantics. The guard makes the resolved route's own pool authoritative.

This is intentional for the PIC-Local case in this design — bgpd computes the pool per route — but see §14 for the limitation when one PIC-Local route resolves through another.

---

### 7.3 Netlink Message: Zebra → fpmsyncd

Zebra communicates routes to fpmsyncd via the **FPM (Forwarding Plane Manager)** interface using Linux netlink messages.

#### 7.3.1 FPM_RTA_BACKUP_NH Top-Level Attribute

Backup nexthops travel on the FPM wire as a **SONiC-private netlink RTA**, distinct from the standard `RTA_MULTIPATH` that carries primaries:

```c
/*
 * SONiC-private top-level RTA carrying BGP-PIC backup nexthops on the
 * FPM wire. Numbered well above the kernel's RTA_MAX (currently around
 * 30) so it can't collide with future kernel additions. Mirrored byte-
 * for-byte by the decoder side in
 * sonic-swss/fpmsyncd/fpm/fpm_backup_nh.h.
 *
 * Carries regular IP nexthops only (gateway + ifindex + weight + onlink).
 */
#define FPM_RTA_BACKUP_NH 200
```

The encoder lives entirely inside `dplane_fpm_sonic` (the SONiC FPM plugin), so no patch to upstream `zebra/rt_netlink.c` is needed.

#### 7.3.2 RTM_NEWROUTE Message Structure

For a route with 2 primary nexthops and 1 backup nexthop:

```
RTM_NEWROUTE
  rtmsg:
    rtm_family   = AF_INET
    rtm_dst_len  = 24           (prefix length)
    rtm_protocol = RTPROT_BGP
    rtm_type     = RTN_UNICAST
    rtm_flags    = 0

  Attributes:
    RTA_DST      = 10.1.0.0          (destination prefix)

    RTA_MULTIPATH:                   (primaries — standard kernel RTA)
      rtnexthop[0]:                  (primary nexthop 1)
        rtnh_len     = sizeof(rtnexthop) + sizeof(RTA_GATEWAY)
        rtnh_flags   = 0
        rtnh_hops    = 0             (weight-1)
        rtnh_ifindex = <iface_index>
        Attrs:
          RTA_GATEWAY = 192.168.1.1
      rtnexthop[1]:                  (primary nexthop 2)
        rtnh_len     = ...
        rtnh_flags   = 0
        rtnh_ifindex = <iface_index>
        Attrs:
          RTA_GATEWAY = 192.168.2.1

    FPM_RTA_BACKUP_NH (=200):        (backups — SONiC-private RTA)
      rtnexthop[0]:                  (backup nexthop 1)
        rtnh_len     = ...
        rtnh_flags   = 0
        rtnh_ifindex = <iface_index>
        Attrs:
          RTA_GATEWAY = 10.0.2.1
```

`FPM_RTA_BACKUP_NH`'s payload is a sequence of `struct rtnexthop` entries — exactly the same wire shape `RTA_MULTIPATH` uses for primaries — so the only new thing for the decoder to learn is the top-level attribute number.

The encoder helpers live in `dplane_fpm_sonic/dplane_fpm_sonic.c`:

```c
/*
 * Emit one nexthop as a struct rtnexthop entry. Scope: regular IP
 * nexthops only (gateway + ifindex + weight + onlink).
 */
static bool fpm_route_build_rtnh(struct nlmsghdr *nlmsg, size_t buflen,
                                 const struct nexthop *nexthop);

/*
 * Append a top-level FPM_RTA_BACKUP_NH attribute to a route message.
 * No-ops on NULL/empty backup_ng AND when every backup is recursive or
 * inactive (in which case the wire-format contract is "attribute
 * absent" rather than "present-and-empty"). Rolls back on partial-
 * write or empty-result so the caller's buffer is structurally clean.
 */
static ssize_t fpm_append_backup_nexthops(struct nlmsghdr *nlmsg, size_t buflen,
                                          const struct nexthop_group *backup_ng);
```

`fpm_nl_enqueue()` calls `fpm_append_backup_nexthops()` right after `netlink_route_multipath_msg_encode()` in the standard-route encode path, so `FPM_RTA_BACKUP_NH` lands on every `RTM_NEWROUTE` that carries backup nexthops.

#### 7.3.3 Primary Nexthop Encoding Unchanged

Single-primary routes stay encoded with `RTA_GATEWAY` + `RTA_OIF` (the kernel's singlepath form); multi-primary routes use `RTA_MULTIPATH`. Adding `FPM_RTA_BACKUP_NH` does not force multipath encoding for primaries — the backup attribute is independent of how primaries are laid out, so libnl's default decode path for primaries is preserved verbatim.

#### 7.3.4 Decoder Side-Channel

libnl's `rtnl_route` parser uses an `rtattr *tb[RTA_MAX + 1]` array and silently drops attributes outside the kernel-defined range, so attribute `200` is invisible to the standard libnl-converted message that `NetDispatcher` dispatches to `RouteSync::onRouteMsg()`. fpmsyncd handles this by peeking at the raw `nlmsghdr` directly:

```cpp
// In FpmLink::processFpmMessage (per-message, before NetDispatcher):
m_routesync->setPendingBackupNexthopsFromRawMsg(nl_hdr);
NetDispatcher::getInstance().onNetlinkMessage(msg);
```

`setPendingBackupNexthopsFromRawMsg()` walks the top-level RTAs by hand looking for `FPM_RTA_BACKUP_NH`, parses the contained `rtnexthop` sequence into `m_pendingBackupNexthops`, and self-clears its state on each call — so the side channel scopes to exactly the in-flight message and no post-dispatch clear is needed. The hot path (no backups) is a single top-level RTA scan with no allocation or string work, keeping scale-route processing cost essentially unchanged.

`getNextHopList()` and `getNextHopWt()` then merge `m_pendingBackupNexthops` onto the end of the comma-separated `nexthop` / `ifname` / `mpls_nh` / `weight` strings they already build for primaries, and `primary_nh_count` records the boundary. Section 7.4.3 covers the merge in detail.

---

### 7.4 APP_DB Schema: Primary and Backup Paths

fpmsyncd writes route information to `APP_DB:ROUTE_TABLE:<prefix>`.

#### 7.4.1 Extended Schema

The schema is extended with a new field:

```
Key:     ROUTE_TABLE:<vrf>:<prefix>
         e.g.  ROUTE_TABLE:10.1.0.0/24
               ROUTE_TABLE:Vrf1:10.1.0.0/24

Fields:
  protocol           : string          (routing protocol, e.g. "0xc2" for BGP)
  blackhole          : bool            ("true"/"false")
  nexthop            : string          (comma-separated list of ALL nexthop IPs,
                                        primary first, then backup)
                       e.g. "192.168.1.1,192.168.2.1,10.0.2.1"
  ifname             : string          (comma-separated interface names,
                                        same order as nexthop)
                       e.g. "Ethernet0,Ethernet4,Ethernet8"
  weight             : string          (comma-separated weights,
                                        same order as nexthop)
                       e.g. "1,1,1"
  mpls_nh            : string          (MPLS nexthop labels, if any)
  vni_label          : string          (VNI/VXLAN label, if any)
  router_mac         : string          (EVPN router MAC, if any)
  segment            : string          (SRv6 segment, if any)
  seg_src            : string          (SRv6 source, if any)
  nexthop_group      : string          (NHG ID, if using NHG mode)
  primary_nh_count   : string (int)    (NEW: count of primary nexthops.
                                        Nexthops 0..(N-1) are primary,
                                        N..end are backup)
                       e.g. "2"  (first 2 are primary, rest are backup)
```

#### 7.4.2 Example APP_DB Entries

**Single primary, single backup:**
```
ROUTE_TABLE:10.4.0.0/32
  protocol         : "0xc2"
  blackhole        : "false"
  nexthop          : "10.0.0.1,10.0.0.65"
  ifname           : "Ethernet128,Ethernet160"
  weight           : "1,1"
  primary_nh_count : "1"
```

**ECMP primary (3 paths), ECMP backup (2 paths):**
```
ROUTE_TABLE:10.1.0.0/24
  protocol         : "0xc2"
  blackhole        : "false"
  nexthop          : "192.168.1.1,192.168.2.1,192.168.3.1,10.0.2.1,10.0.3.1"
  ifname           : "Eth0,Eth4,Eth8,Eth12,Eth16"
  weight           : "1,1,1,1,1"
  primary_nh_count : "3"
```

#### 7.4.3 fpmsyncd Processing

`getNextHopList()` in `routesync.cpp` walks libnl's primary nexthops (which already exclude backups — those rode in the SONiC-private `FPM_RTA_BACKUP_NH` attribute that libnl's `rtnl_route` parser ignores) and then merges the backups parked in the side channel by `FpmLink`:

```cpp
int RouteSync::getNextHopList(struct rtnl_route *route_obj, string& gw_list,
                              string& mpls_list, string& intf_list)
{
    int libnl_count = rtnl_route_get_nnexthops(route_obj);
    /*
     * libnl only sees primaries (RTA_MULTIPATH or singlepath); backups
     * arrive via setPendingBackupNexthopsFromRawMsg() and live in
     * m_pendingBackupNexthops. primary_nh_count returned to the caller
     * is the libnl-parsed count.
     */
    int primary_count = libnl_count;

    for (int i = 0; i < libnl_count; i++) {
        struct rtnl_nexthop *nexthop = rtnl_route_nexthop_n(route_obj, i);
        // ... append primary's gw / mpls / ifname to the lists ...
    }

    // Merge backups onto the end of the same lists. Order matters:
    // orchagent uses primary_nh_count to know that the first N entries
    // are primaries and the rest are backups.
    for (const auto &nh : m_pendingBackupNexthops) {
        gw_list   += nh.gw;
        mpls_list += "na";   // backups carry no encap (matches old contract)
        intf_list += getIfName(nh.if_index, ...);
        // ... NHG_DELIMITER between entries ...
    }

    return primary_count;
}
```

`getNextHopWt()` performs the same merge for the per-nexthop `weight` string. The returned `primary_count` is stored in `fvw.primary_nh_count` and written to APP_DB.

`m_pendingBackupNexthops` is a `RouteSync` member used as a per-message side channel — written by `FpmLink` before `NetDispatcher` dispatches the libnl-converted message, read by the consumers above inside the same dispatch path. fpmsyncd is single-threaded, so no synchronization is needed; the member declaration carries a comment noting that contract.

---

### 7.5 Orchagent (TBD)

The orchagent reads `primary_nh_count` from APP_DB and restricts nexthop vector processing to the first `primary_nh_count` entries. This ensures that backup nexthops are **not** programmed as additional primary nexthops into the ASIC.

The full backup nexthop handling in orchagent — including:
- Creating separate SAI nexthop objects for backup nexthops
- Programming SAI with primary/backup nexthop groups
- Enabling hardware-based failover on link down

— is **TBD** and will be addressed in a subsequent design document.

---

## 8. Configuration and Management

### 8.1 FRR Configuration

PIC Local is enabled via FRR CLI commands in the BGP address-family context:

```
router bgp <ASN>
  address-family ipv4 unicast
    install backup-path          ! Enable single backup path (PIC local)
    install backup-path ecmp     ! Enable ECMP backup paths (PIC local with ECMP)
    no install backup-path       ! Disable backup path (clears and flushes)
  exit-address-family
  !
  address-family ipv6 unicast
    install backup-path
  exit-address-family
```

**Supported AFIs:** `ipv4 unicast`, `ipv6 unicast`
**Not supported:** `l2vpn evpn`, `ipv4 multicast`, `ipv6 multicast`

When `install backup-path ecmp` is configured, the number of backup ECMP paths is bounded by `maximum-paths` configured for the same address family. The limit applies separately for bestpaths and backup paths.

**Show commands:**

#### show ip route

The routing table uses the `b` prefix character to denote backup nexthops. Backup nexthops appear indented below the primary ECMP set lines (which use `*`). The legend is updated to include `b - backup`.

```
r1# show ip route
Codes: K - kernel route, C - connected, L - local, S - static,
       R - RIP, O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric, t - Table-Direct,
       > - selected route, * - FIB route, q - queued, r - rejected, b - backup
       t - trapped, o - offload failure

IPv4 unicast VRF default:
B>* 10.203.6.0/24 [20/1] via 10.0.1.101, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.1.102, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.1.103, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.1.104, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.1.105, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.3.111, r1-eth2, weight 1, 02:09:40
  *                       via 10.0.3.112, r1-eth2, weight 1, 02:09:40
  *                       via 10.0.3.113, r1-eth2, weight 1, 02:09:40
  *                       via 10.0.3.114, r1-eth2, weight 1, 02:09:40
  *                       via 10.0.3.115, r1-eth2, weight 1, 02:09:40
  b                        via 10.0.2.106, r1-eth1, weight 1
B>* 10.204.9.0/24 [20/1] via 10.0.1.101, r1-eth0, weight 1, 02:09:40
  *                       via 10.0.3.111, r1-eth2, weight 1, 02:09:40
  *                       via 10.0.4.116, r1-eth3, weight 1, 02:09:40
  b                        via 10.0.2.107, r1-eth1, weight 1
  b                        via 10.0.2.108, r1-eth1, weight 1
```

Interpretation:
- Lines with `*` are active primary (FIB-installed) nexthops; the first line also has `>` (selected best).
- Lines with `b` are backup nexthops — present in the FIB as backup but not actively forwarding.
- `install backup-path` produces a single `b` line; `install backup-path ecmp` can produce multiple `b` lines of equal cost.

To see the detail for a single prefix including backup nexthop:

```
r1# show ip route 10.203.6.0/24
Routing entry for 10.203.6.0/24
  Known via "bgp", distance 20, metric 1, best
  Last update 02:11:15 ago
  * 10.0.1.101, via r1-eth0, weight 1
  * 10.0.1.102, via r1-eth0, weight 1
  * 10.0.1.103, via r1-eth0, weight 1
  * 10.0.1.104, via r1-eth0, weight 1
  * 10.0.1.105, via r1-eth0, weight 1
  * 10.0.3.111, via r1-eth2, weight 1
  * 10.0.3.112, via r1-eth2, weight 1
  * 10.0.3.113, via r1-eth2, weight 1
  * 10.0.3.114, via r1-eth2, weight 1
  * 10.0.3.115, via r1-eth2, weight 1
    b 10.0.2.106, via r1-eth1, weight 1
```

The `b` indented under the primary set represents the pre-installed backup nexthop.

#### show ip bgp (summary)

The BGP table summary uses `B` prefix to display the backup paths

```
r1# show ip bgp
BGP table version is 6, local router ID is 1.1.1.1, vrf id 0
Default local pref 100, local AS 65001
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed, B Backup
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>  10.99.99.0/24    10.1.2.2                               0 65002 65004 i
 *=                   10.1.2.2                               0 65002 65005 i
 *B                   10.1.3.3                               0 65003 65006 i
 *B                   10.1.3.3                               0 65003 65007 i

Displayed 1 routes and 4 total paths
```

Note: In the summary view, the backup path appears as `*` (valid) without `>` (best) or `=` (multipath).


#### show ip bgp \<prefix\> (per-prefix detail)

The per-prefix detail view explicitly labels backup paths with `, backup` in the status line. This is the most informative view for verifying PIC Local is operating correctly:

```
r1# show ip bgp 10.203.6.0/24
BGP routing table entry for 10.203.6.0/24, version 687
Paths: (20 available, best #1, table default)
  Advertised to peers:
  10.0.1.101 10.0.1.102 10.0.1.103 10.0.1.104 10.0.1.105
  10.0.2.106 10.0.2.107 10.0.2.108 10.0.2.109 10.0.2.110
  10.0.3.111 10.0.3.112 10.0.3.113 10.0.3.114 10.0.3.115
  99
    10.0.1.101 from 10.0.1.101 (10.0.1.101)
      Origin IGP, metric 1, valid, external, multipath, best (MED)
      Last update: Thu Feb 26 21:49:30 2026
  99
    10.0.1.102 from 10.0.1.102 (10.0.1.102)
      Origin IGP, metric 1, valid, external, multipath
      Last update: Thu Feb 26 21:49:45 2026
  99
    10.0.1.103 from 10.0.1.103 (10.0.1.103)
      Origin IGP, metric 1, valid, external, multipath
      Last update: Thu Feb 26 21:50:01 2026
  99
    10.0.3.111 from 10.0.3.111 (10.0.3.111)
      Origin IGP, metric 1, valid, external, multipath
      Last update: Thu Feb 26 21:55:38 2026
  99
    10.0.2.106 from 10.0.2.106 (10.0.2.106)
      Origin IGP, metric 6, valid, external, backup
      Last update: Thu Feb 26 21:52:34 2026
```

Key observations:
- Primary ECMP paths have `, multipath` in their status (metric 1, preferred by MED).
- The backup path has `, backup` in its status (metric 6, higher cost — excluded from primary ECMP set because it has a different MED from a different set of peers).
- The backup path is still `valid` and `external`, and is advertised to peers normally — the `backup` designation affects only the FIB, not BGP advertisement.
- Only one backup path is shown here because `install backup-path` (non-ECMP) was configured. With `install backup-path ecmp`, multiple paths at metric 6 would all show `, backup`.

#### show ip bgp \<prefix\> json

For automation and monitoring, the JSON output includes a `"backup": true` field on backup paths:

```json
{
  "10.203.6.0/24": {
    "paths": [
      {
        "aspath": { "string": "99" },
        "nexthops": [ { "ip": "10.0.1.101", "afi": "ipv4" } ],
        "valid": true,
        "multipath": true,
        "bestpath": { "overall": true, "selectionReason": "MED" }
      },
      {
        "aspath": { "string": "99" },
        "nexthops": [ { "ip": "10.0.2.106", "afi": "ipv4" } ],
        "valid": true,
        "backup": true
      }
    ]
  }
}
```

#### show ip route \<prefix\> json

The JSON routing table output includes a `"backupNexthops"` field alongside the primary `"nexthops"`. PIC-Local routes additionally carry a `"backupAllPrimariesDown": true` field so a JSON consumer can tell the route-level and per-NH semantics apart:

```json
{
  "10.203.6.0/24": [
    {
      "prefix": "10.203.6.0/24",
      "protocol": "bgp",
      "selected": true,
      "installed": true,
      "nexthops": [
        { "ip": "10.0.1.101", "interfaceName": "r1-eth0", "weight": 1, "active": true },
        { "ip": "10.0.1.102", "interfaceName": "r1-eth0", "weight": 1, "active": true },
        { "ip": "10.0.3.111", "interfaceName": "r1-eth2", "weight": 1, "active": true }
      ],
      "backupNexthops": [
        { "ip": "10.0.2.106", "interfaceName": "r1-eth1", "weight": 1, "active": true }
      ],
      "backupAllPrimariesDown": true
    }
  ]
}
```

`backupAllPrimariesDown` is emitted only when `NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN` is set on the parent NHE — that is, only for route-level pools. Per-NH protected routes (`HAS_BACKUP` on individual primaries) render `backupNexthops` without the new field.

### 8.2 YANG Model

Two YANG models are provided for configuring PIC Local:

#### 8.2.1 Device-Global (sonic-bgp-device-global.yang)

Applies to the **default VRF** globally across the device. This is the recommended configuration path for datacenter devices with a single global BGP instance.

```yang
module sonic-bgp-device-global {
  container sonic-bgp-device-global {
    container BGP_DEVICE_GLOBAL_AF {
      list BGP_DEVICE_GLOBAL_AF_LIST {
        key "afi_safi";
        // afi_safi: "ipv4_unicast" | "ipv6_unicast"

        leaf install_backup_path {
          must "current() = 'disabled' or
                contains(current()/../afi_safi, '_unicast')" {
            error-message "install_backup_path is supported only for
                           unicast address families";
          }
          type enumeration {
            enum disabled;   // Default. No backup paths computed or installed.
            enum pic;        // Single backup path. Maps to 'install backup-path'.
            enum pic-ecmp;   // ECMP backup paths. Maps to 'install backup-path ecmp'.
          }
          default disabled;
        }
      }
    }
  }
}
```

Config DB key: `BGP_DEVICE_GLOBAL_AF|<afi_safi>`
Example: `BGP_DEVICE_GLOBAL_AF|ipv4_unicast`
Field: `install_backup_path = pic | pic-ecmp | disabled`

#### 8.2.2 Per-VRF (sonic-bgp-global.yang)

Applies per-VRF within the `BGP_GLOBALS_AF` table. Used when different VRFs need different PIC settings.

```yang
container BGP_GLOBALS_AF {
  list BGP_GLOBALS_AF_LIST {
    key "vrf_name afi_safi";

    leaf install_backup_path {
      must "current() = 'disabled' or
            contains(current()/../afi_safi, '_unicast')" {
        error-message "install_backup_path is supported only for
                       unicast address families";
      }
      type enumeration {
        enum disabled;
        enum pic;
        enum pic-ecmp;
      }
      default disabled;
      description "Controls BGP Prefix Independent Convergence (PIC) backup path
                   installation for this address family. Supported only for
                   ipv4_unicast and ipv6_unicast.";
    }
  }
}
```

Config DB key: `BGP_GLOBALS_AF|<vrf_name>|<afi_safi>`
Example: `BGP_GLOBALS_AF|default|ipv4_unicast`
Field: `install_backup_path = pic | pic-ecmp | disabled`

### 8.3 Config DB

#### 8.3.1 BGP_DEVICE_GLOBAL_AF (device-wide, default VRF)

```json
{
  "BGP_DEVICE_GLOBAL_AF": {
    "ipv4_unicast": {
      "install_backup_path": "pic"
    },
    "ipv6_unicast": {
      "install_backup_path": "pic-ecmp"
    }
  }
}
```

#### 8.3.2 BGP_GLOBALS_AF (per-VRF)

```json
{
  "BGP_GLOBALS_AF": {
    "default|ipv4_unicast": {
      "install_backup_path": "pic"
    },
    "Vrf1|ipv4_unicast": {
      "install_backup_path": "pic-ecmp"
    }
  }
}
```


---

## 9. Information Flow Diagrams

### 9.1 Configuration Flow (Steady State — Feature Enable)

```
Operator
   │
   │  config set BGP_DEVICE_GLOBAL_AF|ipv4_unicast
   │          install_backup_path = pic
   ▼
CONFIG_DB (Redis)
   │
   │  (bgpcfgd DeviceGlobalAfMgr subscribes)
   ▼
bgpcfgd / DeviceGlobalAfMgr
   │
   │  vtysh commands:
   │    router bgp <ASN>
   │     address-family ipv4 unicast
   │      install backup-path
   │     exit-address-family
   │    exit
   ▼
FRR bgpd
   │
   │  SET_FLAG(bgp->af_flags[AFI_IP][SAFI_UNICAST], BGP_CONFIG_BACKUP_PATH)
   │  bgp_recalculate_afi_safi_bestpaths(bgp, AFI_IP, SAFI_UNICAST)
   │  (triggers full re-bestpath for all IPv4 prefixes)
   ▼
  [see Route Update Flow below]
```

### 9.2 Route Update Flow (Backup Path Computed)

```
BGP Update received (new route learned)
   │
   ▼
bgp_process()
   │
   ▼
bgp_best_selection()
   ├── Normal bestpath selection
   ├── ECMP set computation (bgp_path_info_mpath_update)
   │
   └── bgp_compute_backup_path()        ← NEW
       │  Select first non-primary, non-holddown path as backup
       │  (or multiple if BGP_CONFIG_BACKUP_PATH_ECMP)
       │  Set BGP_PATH_BACKUP flag on selected paths
       │  Set BGP_PATH_BACKUP_CHG on new_best if set changed
       ▼
bgp_process_main_one()
   │  Check bgp_zebra_has_route_changed()  (now also returns true on BGP_PATH_BACKUP_CHG)
   ▼
bgp_zebra_announce()
   │  Build zapi_route:
   │    api.nexthops[]          = primary nexthops (no HAS_BACKUP, no backup_idx[])
   │    api.backup_nexthops[]   = route-scope backup pool          ← NEW
   │    api.message |= ZAPI_MESSAGE_BACKUP_NEXTHOPS                ← NEW
   │    api.message |= ZAPI_MESSAGE_BACKUP_ALL_PRIMARIES_DOWN      ← NEW
   │
   ▼ (ZAPI over Unix socket)
zebra / zapi_msg.c
   │  zapi_route_decode() → parse backup nexthops
   │  zread_route_add() → set NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN
   │                     on tmp NHE before zebra_nhe_copy()        ← NEW
   │  rib_add_multipath_nhe() → store in route entry with backup_info
   ▼
Zebra dataplane (zebra_dplane.c)
   │  ctx->backup_ng                  = backup nexthop group
   │  ctx->backup_all_primaries_down  = mirrored from parent NHE   ← NEW
   ▼
dplane_fpm_sonic / dplane_fpm_sonic.c (SONiC FPM plugin)
   │  fpm_nl_enqueue() → netlink_route_multipath_msg_encode() (primaries)
   │                  → fpm_append_backup_nexthops()       ← NEW
   │                       FPM_RTA_BACKUP_NH (=200)
   │                         struct rtnexthop[N]           ← backups
   │
   ▼ (FPM socket — netlink, framed)
fpmsyncd / fpmlink.cpp
   │  setPendingBackupNexthopsFromRawMsg(nl_hdr) ← peek raw, decode 200
   │  NetDispatcher::onNetlinkMessage(msg)       ← libnl primary path
   ▼
fpmsyncd / routesync.cpp
   │  onMsg(RTM_NEWROUTE) → onRouteMsg()
   │  getNextHopList() → libnl primaries + merge m_pendingBackupNexthops
   │  fvw.primary_nh_count = libnl-parsed primary count    ← NEW
   │
   ▼ (APP_DB via ProducerStateTable)
APP_DB:ROUTE_TABLE:<prefix>
   │  nexthop:          "primary1,primary2,backup1"
   │  ifname:           "Eth0,Eth4,Eth8"
   │  weight:           "1,1,1"
   │  primary_nh_count: "2"                              ← NEW
   │
   ▼ (orchagent subscribes)
orchagent (routeorch.cpp)
   │  Parse primary_nh_count → limit nexthop vector to first N
   │  Create SAI route with primary nexthops only         ← current behavior
   │  Backup nexthop programming: TBD
   ▼
ASIC_DB → syncd → SAI → Hardware
```

### 9.3 Link Failure Flow (Data Plane Failover — Future)

PIC convergence i.e., primary-to-backup switchover can be achieved via two methods:

    a. Entirely in hardware
    b. In software layer (orchagent)

The following describes a high level flow for (b). Both (a) and (b) will be covered in a different HLD.

```
Hardware detects link failure
   │
   ▼
ASIC notifies syncd (via SAI notification)
   │
   ▼
syncd → orchagent (port state change)
   │
   ▼
orchagent
   │  Lookup routes using failed interface
   │  For each affected route:
   │    Look up backup nexthops from APP_DB (primary_nh_count field)
   │    Program backup nexthops as new primary           ← TBD
   ▼
ASIC_DB → syncd → SAI → Hardware
  (traffic rerouted to backup path, no BGP reconvergence needed)

Meanwhile (in parallel):
BGP detects session/prefix change → reconverges
bgpd installs new bestpath → sends updated ZAPI to zebra
  (eventually replaces the backup-as-primary with proper new primary)
```

---

## 10. Warmboot and Fastboot Design Impact

### Warmboot

PIC Local does not introduce changes to the warm restart reconciliation logic. During warm restart:

- **bgpd** replays routes to zebra including backup nexthops (if feature is enabled).
- **fpmsyncd** processes RTM_NEWROUTE messages as usual; `primary_nh_count` is written for routes with backup nexthops.
- **orchagent** reconciliation processes `primary_nh_count` correctly; only primary nexthops are programmed into ASIC (no behavioral change during reconciliation).

No stalls or new IO operations are introduced in the warm restart boot path.

### Fastboot

PIC Local does not affect the critical fastboot path. BGP backup path computation is a post-bestpath-selection step and does not block route convergence or FIB installation.

---

## 11. Memory Consumption

**bgpd**: Each `bgp_path_info` gains no new memory allocation; `BGP_PATH_BACKUP` and `BGP_PATH_BACKUP_CHG` are packed into the existing `flags` field.

**zebra**: The `nhg_backup_info` structure stores backup nexthops. Memory is proportional to the number of routes with backup nexthops × number of backup nexthops per route. In a typical datacenter deployment with ~1M prefixes and 1-2 backup nexthops each, this adds approximately 50-100MB of additional memory in zebra (rough estimate).

**fpmsyncd**: No persistent state; backup nexthops flow through and are written to Redis. Redis memory for APP_DB will increase proportionally with `primary_nh_count` overhead — a small constant per route entry.

**When feature is disabled**: No memory overhead in bgpd, zebra, or fpmsyncd. `BGP_CONFIG_BACKUP_PATH` is not set, so `bgp_compute_backup_path()` is never called, and no backup nexthops are computed or stored.

---

## 12. Restrictions / Limitations

1. **Supported AFIs**: IPv4 unicast and IPv6 unicast only. Not supported for L2VPN EVPN, IPv4 multicast, or IPv6 multicast.
2. **Backup ECMP bound**: Backup ECMP paths are bounded by the address-family `maximum-paths` configuration. The bound is independent of the primary `maximum-paths`.
3. **`FPM_RTA_BACKUP_NH = 200` is a SONiC-private wire-format attribute**: it lives in a number space well above the kernel's `RTA_MAX` (which is currently around 30) so it can't collide with future kernel additions, and it is only meaningful between zebra's `dplane_fpm_sonic` plugin and fpmsyncd. The same number MUST be kept in sync on both ends — the encoder (`sonic-frr/dplane_fpm_sonic/dplane_fpm_sonic.c`) and decoder (`sonic-swss/fpmsyncd/fpm/fpm_backup_nh.h`) hold mirror copies of the `#define`. The attribute is never passed to the Linux kernel route netlink socket.
4. **VRF support**: `BGP_DEVICE_GLOBAL_AF` targets the default VRF only. Per-VRF configuration uses `BGP_GLOBALS_AF`.
5. **Backup paths are FPM-only**: zebra populates the dplane context with the backup pool plus the `backup_all_primaries_down` flag, but the in-tree netlink and FPM-netlink providers do not encode backups for the kernel. Backup engagement is the FPM consumer's job (hardware agent, fpmsyncd extension, etc.).
6. **Orchagent backup programming**: Currently orchagent only programs primary nexthops. Hardware-based failover (without orchagent intervention) requires future SAI work — TBD.
7. **Route-level backup does not propagate through recursive resolution**: If route A is PIC-Local with backup pool `{B0, B1, ...}` and route X resolves recursively through A, X does **not** inherit A's pool. Each route's backup is whatever its own producer (bgpd) computed. The recursive resolver only ever inherits per-NH (TI-LFA-style) backup info, never route-level pools. This is acceptable for the in-tree use case — bgpd computes a pool per route and PIC-Local resolvers are typically static / IGP routes without backups — but it leaves a semantic gap if a future deployment stacks two PIC-Local routes (see §14).
8. **Soft failures**: This feature protects against local link failures detected at the hardware level. BGP/BFD session failures (soft failures) do not benefit from data-plane fast failover with the current implementation.

---

## 13. Testing Requirements / Design

### 13.1 Unit Test Cases (bgpd)

Topotest coverage in `tests/topotests/`:

- `bgp_backup/` — 4-router topology covering single-backup selection, BGP table and routing-table rendering (text + JSON), and dynamic backup re-selection on interface state change under `install backup-path`.
- `bgp_backup_ecmp/` — 7-router topology covering ECMP backup paths under `install backup-path ecmp`, the ECMP→non-ECMP transition, and feature disablement via `no install backup-path` (flush behaviour).
- `bgp_backup_recursive/` — 5-router pure-iBGP topology where R1 has loopback-to-loopback sessions to two PE routers (R4 primary, R5 backup) reachable only through separate transit hops. Both BGP next-hops require recursive resolution through static underlay routes, exercising the path zebra takes to merge backup info from a resolver into a recursively-resolved nexthop (and the guard that prevents that merge from clobbering a route-level pool).

Cases exercised:

| # | Test | Description |
|---|------|-------------|
| 1 | No backup without config | Verify `backup: true` does NOT appear in JSON output before enabling `install backup-path` |
| 2 | Single backup path | Enable `install backup-path`; verify exactly 1 path is marked backup in BGP table and routing table |
| 3 | ECMP backup paths | Enable `install backup-path ecmp`; verify multiple equal-cost paths are marked backup |
| 4 | Backup removed on disable | Run `no install backup-path`; verify backup flags are cleared and Zebra is notified |
| 5 | Backup not advertised to peers | Verify backup paths are not included in UPDATE messages to BGP peers |
| 6 | JSON output | Verify `show ip bgp json` includes `"backup": true` for backup paths |
| 7 | Text output | Verify `show ip bgp` shows `, backup` in path summary |
| 8 | Route table | Verify `show ip route json` includes `backupNexthops` and `backupAllPrimariesDown: true` for PIC-Local routes |
| 9 | Config write | Verify `show running-config` includes `install backup-path [ecmp]` in AF block |
| 10 | Recursive resolution | With both primary and backup BGP next-hops recursively resolved through static underlay routes, verify the resolved NHE carries the route-level pool unchanged (no per-NH merge clobber) |

### 13.2 Integration Tests (fpmsyncd)

| # | Test | Description |
|---|------|-------------|
| 1 | Backup knob enabled | verify `primary_nh_count` is set in APP_DB |
| 2 | Primary count accuracy | With 3 primary + 2 backup, verify `primary_nh_count=3` |
| 3 | Orchagent isolation | With backup nexthops in APP_DB, verify only primary nexthops are programmed in ASIC_DB |

### 13.3 System Test Cases

| # | Test | Description |
|---|------|-------------|
| 1 | End-to-end PIC local | Configure `install backup-path`; bring down primary link; verify traffic reroutes to backup path within data-plane failover window |
| 2 | ECMP backup | Configure `install backup-path ecmp`; bring down primary link; verify traffic load-balances across backup paths |
| 3 | Feature toggle | Enable, disable, re-enable feature; verify no stale backup paths |
| 4 | BGP session reset | Bring BGP session down on primary peer; verify backup is selected correctly after re-convergence |

---

## 14. Open / Action Items

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | **Orchagent backup programming**: Design and implement SAI-level programming of backup nexthop groups; enable hardware-based failover on link down | TBD | Open |
| 2 | **SAI API requirements**: Determine SAI API support needed for primary/backup nexthop group programming and hardware failover notification | TBD | Open |
| 3 | **Zebra nexthop-group support**: Backup nexthops are currently expressed as a separate group on each route entry rather than as kernel-style NHGs; integration with zebra's NHG model is left for follow-up. | TBD | Open |
| 4 | **Route-level backup through recursive resolution**: Route-level pools (`NEXTHOP_GROUP_BACKUP_ALL_PRIMARIES_DOWN`) do **not** propagate through `resolve_backup_nexthops()` — only per-NH (TI-LFA-style) backup info does. Acceptable for the in-tree use case (bgpd computes a pool per route, PIC-Local resolvers are typically static / IGP without backups), but leaves a semantic gap if a future deployment stacks two PIC-Local routes (e.g. a more-specific BGP route resolving through a less-specific PIC-Local route) and expects "all primaries down" to cascade. Closing this would require extending `resolve_backup_nexthops()` (or adding a parallel route-level path) to copy a resolver's pool plus the flag into a resolved NHE that has no pool of its own, with conflict resolution against any existing per-route pool. | TBD | Open |
| 5 | **Warmboot validation**: Validate that backup nexthops are correctly reconciled after warm restart without creating ASIC inconsistencies | TBD | Open |
