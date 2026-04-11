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

---

## 2. Scope

This document covers the High-Level Design of **PIC Local**, also known as BGP Fast Reroute (FRR), for SONiC-based switching platform. PIC Local enables BGP to pre-compute a backup forwarding path and install it alongside the primary path in the data plane. Upon local link failure, the data plane switches to the backup path immediately — without waiting for BGP to reconverge.

This document describes the design and implementation across the following layers:

- **BGP (FRR bgpd)**: Backup path selection algorithm and ZAPI messaging
- **Zebra**: Backup nexthop encoding in FPM netlink messages
- **fpmsyncd**: Parsing and programming backup nexthops to APP_DB
- **YANG / Config**: Configuration models for enabling the feature
- **Orchagent**: *(TBD — Not part of this HLD)*
- **Nexthop-Group**: (TBD — Not part of this HLD)*

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
1. **bgpd** computes a backup path (or ECMP set) after bestpath selection and sends it to Zebra via ZAPI.
2. **Zebra** encodes backup nexthops with a `RTNH_F_BACKUP` flag in FPM netlink messages to fpmsyncd.
3. **fpmsyncd** stores primary and backup nexthops together in APP_DB, using `primary_nh_count` to distinguish them.
4. **Orchagent** currently programs only primary nexthops; backup nexthop hardware programming is TBD.

---

## 5. Requirements

1. BGP SHALL compute at most one backup path per prefix when `install backup-path` is configured.
2. BGP SHALL compute multiple equal-cost backup paths (ECMP) when `install backup-path ecmp` is configured, respecting `maximum-paths` configuration.
3. The backup path MUST NOT include any nexthop that is already in the primary ECMP set.
4. Backup path computation SHALL be triggered after bestpath selection for each destination.
5. Backup paths SHALL be sent to Zebra via ZAPI as backup nexthops alongside primary nexthops.
6. Zebra SHALL encode backup nexthops in FPM netlink messages with a distinguishing flag (`RTNH_F_BACKUP`).
7. fpmsyncd SHALL store both primary and backup nexthops in APP_DB with a `primary_nh_count` field to distinguish them.
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
    │  - Parses primary + backup nexthops (RTNH_F_BACKUP flag)        │
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
| `bgpd/bgp_zebra.c`    | sonic-frr (FRR patch)   | ZAPI message with backup nexthops |
| `zebra/rt_netlink.c`  | sonic-frr (FRR patch)   | RTNH_F_BACKUP flag in FPM messages |
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

And two new per-path flags (`BGP_PATH_BACKUP`, `BGP_PATH_BACKUP_CHG`) are added to `bgp_path_info`:

```c
#define BGP_PATH_BACKUP       (1 << N)   // path is selected as backup
#define BGP_PATH_BACKUP_CHG   (1 << M)   // backup selection has changed (notify Zebra)
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

In `bgp_process_main_one()`, the condition to send an update to Zebra is extended to include backup path changes:

```c
// Before this change:
if (bgp_zebra_has_route_changed(old_select)) { ... }

// After this change:
if (bgp_zebra_has_route_changed(old_select) ||
    CHECK_FLAG(old_select->flags, BGP_PATH_BACKUP_CHG)) { ... }
```

This ensures Zebra (and ultimately fpmsyncd) is notified whenever the backup path set changes, even if the primary route is unchanged. After the update is sent, `BGP_PATH_BACKUP_CHG` is cleared.

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

For a route with backup nexthops, the `zapi_route` structure is populated as follows:

```
struct zapi_route {
    uint8_t  type;                    // ZEBRA_ROUTE_BGP
    prefix   prefix;                  // Destination prefix (e.g. 10.1.0.0/24)
    uint32_t message;                 // Flags set include:
                                      //   ZAPI_MESSAGE_NEXTHOP
                                      //   ZAPI_MESSAGE_BACKUP_NEXTHOPS  (NEW)
    uint16_t nexthop_num;             // Number of primary nexthops (e.g. 3)
    zapi_nexthop nexthops[...];       // Primary nexthops

    uint16_t backup_nexthop_num;      // Number of backup nexthops (e.g. 2)
    zapi_nexthop backup_nexthops[...];// Backup nexthops (NEW)
};
```

The `ZAPI_MESSAGE_BACKUP_NEXTHOPS` flag in `api.message` signals to Zebra that backup nexthops are present.

#### 7.2.2 Linking Primary to Backup Nexthops

Each primary nexthop references its backup nexthops by index:

```
Primary nexthop (api.nexthops[0]):
  type      = NEXTHOP_TYPE_IPV4_IFINDEX
  gate.ipv4 = <primary NH IP>
  ifindex   = <primary interface>
  flags     = ZAPI_NEXTHOP_FLAG_HAS_BACKUP   (NEW)
  backup_num = 2                              (NEW)
  backup_idx = [0, 1]                         (NEW - indices into backup_nexthops[])

Backup nexthop 0 (api.backup_nexthops[0]):
  type      = NEXTHOP_TYPE_IPV4_IFINDEX
  gate.ipv4 = <backup NH 1 IP>
  ifindex   = <backup NH 1 interface>

Backup nexthop 1 (api.backup_nexthops[1]):
  type      = NEXTHOP_TYPE_IPV4_IFINDEX
  gate.ipv4 = <backup NH 2 IP>
  ifindex   = <backup NH 2 interface>
```

#### 7.2.3 ZAPI Message Construction (bgpd/bgp_zebra.c)

The function `bgp_zebra_announce()` is extended to populate backup nexthops:

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

        /* Populate backup_api_nh from backup_path's nexthop */
        struct zapi_nexthop *backup_api_nh =
            &api->backup_nexthops[backup_nh_count];
        /* ... fill in type, gate, ifindex, flags ... */
        backup_nh_count++;
    }

    if (backup_nh_count > 0) {
        /* Set HAS_BACKUP flag and backup_idx on first primary NH */
        api_nh = &api->nexthops[0];
        SET_FLAG(api_nh->flags, ZAPI_NEXTHOP_FLAG_HAS_BACKUP);
        api_nh->backup_num = backup_nh_count;
        for (i = 0; i < backup_nh_count; i++)
            api_nh->backup_idx[i] = i;
        api->backup_nexthop_num = backup_nh_count;
        SET_FLAG(api->message, ZAPI_MESSAGE_BACKUP_NEXTHOPS);
    }
}
```

#### 7.2.4 Zebra Processing of ZAPI Backup Nexthops

In `zebra/zapi_msg.c`, `zapi_route_decode()` reads backup nexthops when `ZAPI_MESSAGE_BACKUP_NEXTHOPS` is set:

```c
if (CHECK_FLAG(api.message, ZAPI_MESSAGE_BACKUP_NEXTHOPS)) {
    // Read backup_nexthop_num
    // For each backup nexthop, parse into zapi_nexthop
}
```

Then `zapi_read_nexthops()` converts them into kernel `nexthop` objects and stores them in `nhg_backup_info` — Zebra's internal structure for backup nexthop groups. The route entry (`re`) gets its `fib_backup_ng` populated.

---

### 7.3 Netlink Message: Zebra → fpmsyncd

Zebra communicates routes to fpmsyncd via the **FPM (Forwarding Plane Manager)** interface using Linux netlink messages.

#### 7.3.1 RTNH_F_BACKUP Flag

A custom flag is defined for encoding backup nexthops in `RTA_MULTIPATH`:

```c
/* Custom SONiC flag to mark backup nexthops in FPM protocol.
 * Value 128 uses the last available bit in rtnh_flags (unsigned char).
 * This flag is set by zebra and consumed by fpmsyncd for failover.
 */
#ifndef RTNH_F_BACKUP
#define RTNH_F_BACKUP 128
#endif
```

This flag repurposes bit 7 of `rtnh_flags` in the `struct rtnexthop` netlink attribute. (Note: Standard Linux kernel flags only use bits 0-6; bit 7 is available for private/vendor use in the FPM protocol.)

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
    RTA_MULTIPATH:                   (all nexthops, primary then backup)
      rtnexthop[0]:                  (primary nexthop 1)
        rtnh_len     = sizeof(rtnexthop) + sizeof(RTA_GATEWAY)
        rtnh_flags   = 0             (no backup flag)
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
      rtnexthop[2]:                  (backup nexthop 1)
        rtnh_len     = ...
        rtnh_flags   = 0x80          (RTNH_F_BACKUP = 128)
        rtnh_ifindex = <iface_index>
        Attrs:
          RTA_GATEWAY = 10.0.2.1
```

The function `_netlink_route_build_multipath()` in `zebra/rt_netlink.c` is modified to accept an `is_backup` parameter. When `fpm=true` and `is_backup=true`, it sets `rtnh->rtnh_flags |= RTNH_F_BACKUP`.

The FPM encoding loop:

```c
// Encode primary nexthops (is_backup=false)
for each nexthop in re->nhe->nhg:
    _netlink_route_build_multipath(p, ..., nexthop, &req->n, ..., fpm=true, is_backup=false)

// For FPM: also encode backup nexthops (is_backup=true)
if (fpm && dplane_ctx_get_backup_ng(ctx)) {
    const struct nexthop_group *backup_nhg = dplane_ctx_get_backup_ng(ctx);
    for each backup_nh in backup_nhg:
        if NEXTHOP_IS_ACTIVE(backup_nh->flags):
            _netlink_route_build_multipath(p, ..., backup_nh, ..., fpm=true, is_backup=true)
}
```

**Important**: Backup nexthops are encoded in FPM messages only — they are NOT installed in the Linux kernel routing table. The `fpm` flag gates the backup encoding.

#### 7.3.3 Forcing Multipath Encoding

Even when a route has only one primary nexthop, if backup nexthops are present, the message is encoded using `RTA_MULTIPATH` (not `RTA_GATEWAY`) to accommodate the backup nexthop entries.

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

The `getNextHopList()` function in `routesync.cpp` is extended to count primary nexthops:

```cpp
int RouteSync::getNextHopList(struct rtnl_route *route_obj, string& gw_list,
                              string& mpls_list, string& intf_list)
{
    int primary_count = 0;

    for (int i = 0; i < rtnl_route_get_nnexthops(route_obj); i++) {
        struct rtnl_nexthop *nexthop = rtnl_route_nexthop_n(route_obj, i);
        unsigned int flags = rtnl_route_nh_get_flags(nexthop);

        if (!(flags & RTNH_F_BACKUP)) {
            // This is a primary nexthop
            primary_count++;
        }
        // Add nexthop to gw_list, intf_list regardless of primary/backup
        // ... append to lists ...
    }
    return primary_count;  // return to caller
}
```

The returned `primary_count` is stored in `fvw.primary_nh_count` and written to APP_DB.

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

When `install backup-path ecmp` is configured, the number of backup ECMP paths is bounded by `maximum-paths` configured for the same address family.

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

The BGP table summary uses `, backup` at the end of the route flags line (similar to how `, multipath` marks ECMP members):

```
r1# show ip bgp
BGP table version is 912, local router ID is 10.0.0.1, vrf id 0
Default local pref 100, local AS 65001
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

   Network          Next Hop            Metric LocPrf Weight Path
*> 10.203.6.0/24    10.0.1.101               1             0 99 i
*=                  10.0.1.102               1             0 99 i
*=                  10.0.1.103               1             0 99 i
*=                  10.0.1.104               1             0 99 i
*=                  10.0.1.105               1             0 99 i
*=                  10.0.3.111               1             0 99 i
*=                  10.0.3.112               1             0 99 i
*=                  10.0.3.113               1             0 99 i
*=                  10.0.3.114               1             0 99 i
*=                  10.0.3.115               1             0 99 i
*                   10.0.2.106               6             0 99 i
```

Note: In the summary view, the backup path appears as `*` (valid) without `>` (best) or `=` (multipath). The `backup` designation is visible in the per-prefix detail view below.

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

The JSON routing table output includes a `"backupNexthops"` field alongside the primary `"nexthops"`:

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
      ]
    }
  ]
}
```

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
   │  Check bgp_zebra_has_route_changed() OR BGP_PATH_BACKUP_CHG
   ▼
bgp_zebra_announce()
   │  Build zapi_route:
   │    api.nexthops[]          = primary nexthops
   │    api.backup_nexthops[]   = backup nexthops   ← NEW
   │    api.message |= ZAPI_MESSAGE_BACKUP_NEXTHOPS  ← NEW
   │
   ▼ (ZAPI over Unix socket)
zebra / zapi_msg.c
   │  zapi_route_decode() → parse backup nexthops
   │  rib_add_multipath_nhe() → store in route entry with backup_info
   ▼
Zebra dataplane (zebra_dplane.c)
   │  ctx->backup_ng = backup nexthop group
   ▼
zebra/rt_netlink.c
   │  _netlink_route_build_singlepath() or _netlink_route_multipath()
   │  For FPM:
   │    Encode primary nexthops (RTNH_F_BACKUP not set)
   │    Encode backup nexthops (RTNH_F_BACKUP = 0x80)    ← NEW
   │
   ▼ (FPM socket — netlink)
fpmsyncd / routesync.cpp
   │  onMsg(RTM_NEWROUTE) → onRouteMsg()
   │  getNextHopList() → count primary_count, build combined lists
   │  fvw.primary_nh_count = primary_count                ← NEW
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
2. **Single primary nexthop assumption**: The current implementation links backup nexthops only to the first primary nexthop (`api.nexthops[0]`). When primary ECMP is used, all backup nexthops are referenced from nexthop[0] only.
3. **Backup ECMP bound**: Backup ECMP paths are bounded by the address-family `maximum-paths` configuration.
4. **RTNH_F_BACKUP is a private flag**: Value 128 (bit 7) in `rtnh_flags` is not a standard Linux kernel flag. It is a private convention between zebra and fpmsyncd, used only in FPM messages. It MUST NOT be passed to the Linux kernel route netlink socket.
5. **VRF support**: `BGP_DEVICE_GLOBAL_AF` targets the default VRF only. Per-VRF configuration uses `BGP_GLOBALS_AF`.
6. **Orchagent backup programming**: Currently orchagent only programs primary nexthops. Hardware-based failover (without orchagent intervention) requires future SAI work — TBD.
7. **Soft failures**: This feature protects against local link failures detected at the hardware level. BGP/BFD session failures (soft failures) do not benefit from data-plane fast failover with the current implementation.

---

## 13. Testing Requirements / Design

### 13.1 Unit Test Cases (bgpd)

The topotest `bgp_pic_backup_path/test_bgp_pic_backup_path.py` (added in patch `0215-bgpd-Support-Compute-PIC-backup-path.patch`) covers:

| # | Test | Description |
|---|------|-------------|
| 1 | No backup without config | Verify `backup: true` does NOT appear in JSON output before enabling `install backup-path` |
| 2 | Single backup path | Enable `install backup-path`; verify exactly 1 path is marked backup in BGP table and routing table |
| 3 | ECMP backup paths | Enable `install backup-path ecmp`; verify multiple equal-cost paths are marked backup |
| 4 | Backup removed on disable | Run `no install backup-path`; verify backup flags are cleared and Zebra is notified |
| 5 | Backup not advertised to peers | Verify backup paths are not included in UPDATE messages to BGP peers |
| 6 | JSON output | Verify `show ip bgp json` includes `"backup": true` for backup paths |
| 7 | Text output | Verify `show ip bgp` shows `, backup` in path summary |
| 8 | Route table | Verify `show ip route json` includes `backupNexthops` for backup nexthops |
| 9 | Config write | Verify `show running-config` includes `install backup-path [ecmp]` in AF block |

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
| 3 | **Multi-primary to backup linking**: Current design links backups only to `nexthops[0]`; evaluate whether each primary ECMP NH should independently reference backup NHs | TBD | Open |
| 4 | **Warmboot validation**: Validate that backup nexthops are correctly reconciled after warm restart without creating ASIC inconsistencies | TBD | Open |
