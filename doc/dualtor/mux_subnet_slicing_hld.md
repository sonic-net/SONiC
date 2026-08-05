# Mux Subnet Slicing

Mux subnet slicing is an optimization for dual ToR topology that replaces per-VM IPv6 neighbor entries with a single per-host slice prefix route, reducing the per-port neighbor count and the time complexity of mux state transitions.

<!-- TOC orderedlist:true -->

## Table of Content
- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Overview](#3-overview)
- [4. Requirements](#4-requirements)
- [5. High-Level Design](#5-high-level-design)
  - [5.1 Orchagent](#51-orchagent)
    - [5.1.1 MuxOrch](#511-muxorch)
    - [5.1.2 NeighborOrch](#512-neighbororch)
  - [5.2 DB Schema Changes](#52-db-schema-changes)
    - [5.2.1 Config-DB](#521-config-db)
    - [5.2.2 State-DB](#522-state-db)
  - [5.3 Show CLI](#53-show-cli)
  - [5.4 Utilities](#54-utilities)
- [6. Considerations](#6-considerations)
- [7. Test Plan](#7-test-plan)

<!-- /TOC -->

### 1. Revision

|  Rev  |    Date    |        Author        | Change Description |
| :---: | :--------: | :------------------: | ------------------ |
|  0.1  | 2026-04-28 |   Nikola Dancejic    | Initial draft      |

### 2. Scope
This document describes the high-level design of mux subnet slicing for dual ToR topologies. It covers the new CONFIG_DB / STATE_DB schema, orchagent (MuxOrch / NeighborOrch) changes, a `show mux config` visibility column, dualtor utility updates, and the test plan. IPv4 is out of scope; this feature is IPv6 only.

### 3. Overview
On dual ToR topologies each VM running on a host is currently learned as an independent IPv6 neighbor on the mux-cabled VLAN port member. Per-port neighbor count therefore scales with the number of VMs per host, and mux state transitions configure every neighbor/route entry in the ASIC. This grows with VM density and becomes very costly during switchover.

Vlan mux subnet slicing assigns a dedicated IPv6 prefix (a "slice", typically /112) to each host and forwards in-slice traffic through a single route whose nexthop is configured as `server_ipv6`. From the ToR's perspective:

* Only one neighbor entry per host subnet slice (`server_ipv6`) is programmed in the ASIC, regardless of VM count.
* Neighbors that fall outside of the subnet slice are programmed normally.
* A single slice prefix route covers all in-slice destinations on that port.
* Mux state transitions act on the host neighbor + the slice route, not on every VM IP.

This reduces per-port neighbor state and switchover work, and removes the per-VM neighbor scaling pressure on the neighbor table.

### 4. Requirements

**Schema**
* **CONFIG_DB:** A new `subnet_slice_ipv6` field on `MUX_CABLE` to declare a per-port slice prefix.
* **STATE_DB:** Slice configuration and per-port in-slice / out-of-slice neighbor visibility will be important for validation and debugging.

**Orchagent**
* **MuxOrch:** Consumes `subnet_slice_ipv6` at port initialization and programs a slice prefix route via `server_ipv6` when configured. Switchover operations for in-slice neighbors will follow the existing `updateNextHopRoutes` path to update `subnet_slice_ipv6` route nexthop.
* **NeighborOrch:** When a port has a slice configured, IPv6 neighbor add for in-slice addresses (other than `server_ipv6`) skips ASIC programming via the SAI neighbor API. Out-of-slice neighbors and neighbors on non-sliced ports are unaffected. `server_ipv6` is always programmed normally and takes precedence over the slice route.
* **Prefix-route mux-neighbor mode compatibility:** When a port is also operating in prefix-route mux-neighbor mode, subnet-slicing behavior should remain consistent. Likely no specific change will be needed, but both configurations need to be compatible with each other.

**CLI and Scripts**
* **`show mux config`:** Must display the slice prefix as an additional column.
* **`dualtor_neighbor_check`:** Must be aware of the sliced state and not treat missing ASIC neighbor entries as inconsistent for in-slice addresses.

**Compatibility**
* **Backward compatibility:** Absence of `subnet_slice_ipv6` on a mux port preserves today's per-VM neighbor behavior on the port. Sliced and non-sliced ports may coexist on the same ToR.

### 5. High-Level Design

#### 5.1 Orchagent

##### 5.1.1 MuxOrch
MuxOrch is the consumer of the new `subnet_slice_ipv6` field. It will initialize the subnet-slice route and manage nexthop configuration based on mux port status.

* Reads `subnet_slice_ipv6` from `MUX_CABLE` at port initialization. Validates the prefix and caches the per-port `{slice_prefix, server_ipv6}` mapping.
* On port init with a configured slice: installs the slice prefix route via `server_ipv6` as nexthop once `server_ipv6` is resolved.
* On mux state transition (active ⇄ standby): the slice route is treated as a normal mux-owned route and follows the existing `updateNextHopRoutes` path during the disable path. Its nexthop is swapped to the tunnel nexthop in standby and back to the direct neighbor nexthop in active. The route entry itself is persistent across transitions.

##### 5.1.2 NeighborOrch
NeighborOrch's neighbor add path will check subnet-slice configuration before the SAI neighbor create call. NeighborOrch will suppress mux neighbor programming for entries that fall within the subnet slice prefix, and ensure internal consistency of resource count and state tracking.

* If the neighbor's port has `subnet_slice_ipv6` configured, AND the neighbor's IPv6 address falls within `slice_prefix`, AND the neighbor address is not `server_ipv6` itself, then NeighborOrch skips the SAI neighbor create call. The neighbor remains in `NEIGH_TABLE` and the kernel, but no ASIC entry is programmed.
* All other neighbors (out-of-slice on a sliced port, or any neighbor on a non-sliced port) follow today's path unchanged.
* `server_ipv6` is always programmed normally.

#### 5.2 DB Schema Changes

##### 5.2.1 Config-DB
A new `subnet_slice_ipv6` field is added to the `MUX_CABLE` table:

```
MUX_CABLE|<vlan>|<port>:
  state: auto|active|standby|...
  server_ipv4: <ipv4>/32
  server_ipv6: <ipv6>/128
  subnet_slice_ipv6: <ipv6_prefix>   # new — optional; presence enables slicing on this port
```

`subnet_slice_ipv6` is optional. If it is not configured, the mux port maintains current behavior. The value is an IPv6 prefix; the expected length is /112 but the schema allows any valid IPv6 prefix.

##### 5.2.2 State-DB
`MUX_CABLE_TABLE` is extended with 'subnet_slice_ipv6' and per-port aggregate counters `in_slice_neighbor_count` and `out_of_slice_neighbor_count`:

```
MUX_CABLE_TABLE|<port>:
  ...
  subnet_slice_ipv6: <ipv6_prefix>      # new — present if slicing is configured and the slice route is installed
  in_slice_neighbor_count: <int>        # new — number of learned IPv6 neighbors whose address falls within the slice prefix (excluding server_ipv6); these are not programmed to ASIC
  out_of_slice_neighbor_count: <int>    # new — number of learned IPv6 neighbors on this port whose address falls outside the slice prefix; these are programmed to ASIC
```

#### 5.3 Show CLI
The `show mux config` output is extended with a `subnet_slice_ipv6` column reflecting the configured slice prefix (empty when slicing is not enabled on a port).

Example output on a ToR where `Ethernet4` and `Ethernet8` have slicing configured and `Ethernet0` does not:

```
admin@sonic:~$ show mux config
        Port    State    IPv4               IPv6                Subnet Slice IPv6
------------  -------  --------------  ---------------------  -----------------------
   Ethernet0     auto  192.168.0.2/32  fc02:1000::2/128
   Ethernet4     auto  192.168.0.3/32  fc02:1000::3/128       fc02:1000:0:3::/112
   Ethernet8  standby  192.168.0.4/32  fc02:1000::4/128       fc02:1000:0:4::/112
  Ethernet12     auto  192.168.0.5/32  fc02:1000::5/128
```

#### 5.4 Utilities
`dualtor_neighbor_check` is updated to treat in-slice neighbors on a subnet-slice configured mux port with missing ASIC as consistent.

Example output on a ToR where `Ethernet4` and `Ethernet8` have slicing configured (`server_ipv6` programmed; in-slice VM neighbors suppressed and consistent with the slice route):

```
admin@sonic:~$ sudo dualtor_neighbor_check.py --log-output stdout --log-level WARNING
================================================================================
Neighbors in HOST-ROUTE mode:
================================================================================
NEIGHBOR         MAC                PORT        MUX_STATE  IN_MUX_TOGGLE  NEIGHBOR_IN_ASIC  TUNNEL_IN_ASIC  HWSTATUS
---------------  -----------------  ----------  ---------  -------------  ----------------  --------------  ----------
fc02:1000::2     52:54:00:12:34:02  Ethernet0   active     no             yes               no              consistent
fc02:1000::5     52:54:00:12:34:05  Ethernet12  standby    no             no                yes             consistent

================================================================================
Neighbors in SUBNET-SLICE mode:
================================================================================
NEIGHBOR              MAC                PORT       MUX_STATE  SLICE_PREFIX          IN_SLICE  NEIGHBOR_IN_ASIC  HWSTATUS
--------------------  -----------------  ---------  ---------  --------------------  --------  ----------------  ----------
fc02:1000::3          52:54:00:12:34:03  Ethernet4  active     fc02:1000:0:3::/112   no        yes               consistent
fc02:1000:0:3::a      52:54:00:aa:00:0a  Ethernet4  active     fc02:1000:0:3::/112   yes       no                consistent
fc02:1000:0:3::b      52:54:00:aa:00:0b  Ethernet4  active     fc02:1000:0:3::/112   yes       no                consistent
fc02:1000::4          52:54:00:12:34:04  Ethernet8  standby    fc02:1000:0:4::/112   no        no                consistent
fc02:1000:0:4::a      52:54:00:bb:00:0a  Ethernet8  standby    fc02:1000:0:4::/112   yes       no                consistent
fd00:beef::1          52:54:00:cc:00:01  Ethernet8  standby    fc02:1000:0:4::/112   no        no                consistent
```

### 6. Considerations

* **`server_ipv6` is a hard dependency.** The slice route's nexthop is `server_ipv6`, so orchagent must keep track of `server_ipv6` reachability to ensure no blackholing. If `server_ipv6` goes stale or ages out, orchagent must re-program in-slice neighbors to the ASIC.
* **Slice route is ASIC-only.** The slice prefix is installed via the SAI route API only and is intentionally *not* injected into the kernel routing table.
* **Address scope filtering.** Link-local (`fe80::/10`) and any IPv6 address that does not fall within the configured slice prefix are unaffected by slicing.
* **IPv4 unchanged.** Slicing is IPv6-only. IPv4 neighbors on a sliced port follow today's per-neighbor ASIC programming path with no changes.
* **CRM/refcount accounting.** The slice route consumes one ASIC route slot per sliced port. Suppressed in-slice neighbors must not be counted against CRM neighbor usage, since they are not programmed to ASIC. CRM counters for neighbor and route resources must remain accurate after the change.
* **Slice prefix is initialization-only.** The configuration is read once at port initialization; runtime add/remove/change of `subnet_slice_ipv6` is not supported, and in-place mutation requires a config or device reload.

### 7. Test Plan

| Scenario | Expected Result |
|-----------------|-----------------|
| Configure `subnet_slice_ipv6` on a port | <ul><li>`server_ipv6` neighbor in ASIC</li><li>Slice route in ASIC with nexthop = `server_ipv6`</li><li>CONFIG_DB and STATE_DB match</li></ul> |
| In-slice neighbors added/removed | <ul><li>Neighbor not in ASIC</li><li>Neighbor present in `NEIGH_TABLE`</li><li>`in_slice_neighbor_count` matches expected</li></ul> |
| Out-of-slice neighbors added/removed | <ul><li>Neighbor present in ASIC</li><li>`out_of_slice_neighbor_count` matches</li></ul> |
| `server_ipv6` falls inside the slice prefix | <ul><li>`server_ipv6` programmed normally</li><li>In-slice still suppressed</li><li>LPM resolves traffic via `server_ipv6`</li></ul> |
| `server_ipv6` becoming stale and then resolving again | <ul><li>Slice route deferred until resolved</li><li>Withdrawn on loss</li><li>In-slice neighbors re-programmed from `NEIGH_TABLE`</li></ul> |
| Mix of subnet sliced and default mux ports | <ul><li>Sliced ports suppress in-slice</li><li>Non-sliced ports retain per-VM behavior</li></ul> |
| MAC move between mux ports | Neighbor follows expected port configuration |
| Active ↔ standby transitions on a sliced port | <ul><li>Slice route nexthop swaps tunnel/direct</li><li>Neighbors maintain expected configuration</li></ul> |
| Slice + prefix-route mux-neighbor mode on same port | <ul><li>Only `server_ipv6` / out-of-slice get prefix routes</li><li>In-slice have neither neighbor nor prefix route</li></ul> |
| IPv4 / link-local on sliced port | <ul><li>Programmed normally</li><li>Slicing does not apply</li></ul> |
| Link flap on a sliced port | Matches standby behavior |
| `dualtor_neighbor_check` on sliced ports | <ul><li>Reports slice prefix</li><li>In-slice absences not flagged as discrepancies</li><li>Derived in-slice list matches `NEIGH_TABLE` ∩ slice prefix</li></ul> |
| Switchover performance comparison of neighbor-scaling | Switchover time stays constant as in-slice IPv6 neighbor count grows |

