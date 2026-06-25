# BGP Unnumbered over VLAN Subinterfaces

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [High-Level Design](#6-high-level-design)
7. [Configuration and Management](#7-configuration-and-management)
8. [Warmboot and Fastboot Impact](#8-warmboot-and-fastboot-impact)
9. [Restrictions](#9-restrictions)
10. [Testing](#10-testing)
11. [Component Changes](#11-component-changes)

## 1. Revision

| Rev | Date       | Author                | Change Description |
|:---:|:----------:|:----------------------|--------------------|
| 0.1 | 2026-06-25 | Sudharsan Rajagopalan | Initial community proposal |

## 2. Scope

This document describes the SONiC changes needed to support BGP unnumbered
over VLAN subinterfaces when IPv6 link-local next hops are used. The work covers
the long-name form (`Ethernet0.10`, `PortChannel1.20`) and the short-name form
(`Eth0.10`, `Po1.20`).

The change spans:

| Repository | Area |
|------------|------|
| `sonic-buildimage` | YANG model for `VLAN_SUB_INTERFACE.ipv6_use_link_local_only` and BGP neighbor VLAN subinterface leafrefs |
| `sonic-utilities` | CLI enable/disable and show support for VLAN subinterfaces |
| `sonic-swss` | `neighsyncd` IPv6 link-local neighbor admission |
| `frr` | BGP unnumbered VLAN subinterface topotest coverage |
| `sonic-mgmt` | Optional end-to-end SONiC regression coverage |

## 3. Definitions

| Term | Definition |
|------|------------|
| BGP unnumbered | FRR interface peering using `neighbor <ifname> interface remote-as <as>`, where IPv4 routes use an IPv6 link-local next hop as described by RFC 5549. |
| VLAN subinterface | Dot1q subinterface configured under `VLAN_SUB_INTERFACE`, for example `Ethernet0.10` or `Eth0.10`. |
| Long-name subinterface | VLAN subinterface whose parent uses the full SONiC name, for example `Ethernet0.10` or `PortChannel1.20`. |
| Short-name subinterface | VLAN subinterface whose parent uses the compact name, for example `Eth0.10` or `Po1.20`. |
| IFNAMSIZ | Linux interface-name size limit. The usable interface name length is 15 characters. |

## 4. Overview

BGP unnumbered allows a routed link to form a BGP session without assigning an
IPv4 address to the link. FRR installs IPv4 routes with IPv6 link-local next
hops learned from the peer interface. For SONiC to program those routes, the
kernel IPv6 link-local neighbor must flow through `neighsyncd`,
`APPL_DB:NEIGH_TABLE`, `neighorch`, and then the SAI neighbor and next-hop
objects.

Before this change, SONiC's control path was incomplete for VLAN subinterfaces:

1. The YANG model did not allow `ipv6_use_link_local_only` under
   `VLAN_SUB_INTERFACE`.
2. The BGP neighbor YANG model did not allow a neighbor entry to reference a
   VLAN subinterface.
3. The CLI only handled physical, PortChannel, and VLAN interfaces for
   `config interface ipv6 enable/disable use-link-local-only`.
4. `show ipv6 link-local-mode` did not display VLAN subinterface state.
5. `neighsyncd` checked the wrong CONFIG_DB table for dotted interface names,
   so IPv6 link-local neighbors on VLAN subinterfaces could be dropped before
   reaching `APPL_DB`.
6. Short names such as `Eth112.200` were not recognized by the `neighsyncd`
   IPv6 link-local gate, even though short names are required when the long form
   would exceed Linux `IFNAMSIZ`.

The expected behavior after this change is:

| Signal | Expected result |
|--------|-----------------|
| BGP session | Established on VLAN subinterfaces |
| Kernel neighbor | IPv6 link-local neighbor present on the subinterface |
| `APPL_DB:NEIGH_TABLE` | Populated for the subinterface when link-local mode is enabled |
| ASIC programming | Neighbor, next-hop, and route objects resolved through the subinterface |
| Data plane | IPv4 prefixes learned over BGP unnumbered forward through the link-local next hop |

## 5. Requirements

1. `ipv6_use_link_local_only` must be valid for `VLAN_SUB_INTERFACE`.
2. BGP neighbor configuration must allow VLAN subinterface names.
3. The CLI must enable and disable IPv6 link-local-only mode on VLAN
   subinterfaces.
4. `show ipv6 link-local-mode` must show VLAN subinterface entries.
5. `neighsyncd` must look up VLAN subinterface link-local mode in
   `VLAN_SUB_INTERFACE`, not in the parent `INTERFACE` or
   `PORTCHANNEL_INTERFACE` table.
6. Long-name and short-name VLAN subinterfaces must both be accepted by the
   `neighsyncd` data path.
7. Unsupported dotted interface names must continue to be rejected.
8. Existing behavior for physical, PortChannel, and VLAN interfaces must remain
   unchanged.

## 6. High-Level Design

### 6.1 YANG

Add `ipv6_use_link_local_only` to `VLAN_SUB_INTERFACE_LIST` in
`sonic-vlan-sub-interface.yang`:

```
leaf ipv6_use_link_local_only {
    description "Enable/Disable IPv6 link local address on vlan-sub-interface";
    type stypes:mode-status;
    default disable;
}
```

This matches the existing interface-table model and allows Config DB validation
for entries such as:

```
VLAN_SUB_INTERFACE|Eth0.10
    admin_status: up
    vlan: 10
    ipv6_use_link_local_only: enable
```

Also allow `BGP_NEIGHBOR_LIST.neighbor` to reference
`VLAN_SUB_INTERFACE_LIST.name` by adding a `sonic-vlan-sub-interface` import and
a VLAN subinterface leafref to the neighbor union type.

### 6.2 CLI and Show Commands

`config interface ipv6 enable use-link-local-only <interface-name>` and
`config interface ipv6 disable use-link-local-only <interface-name>` are updated
to classify dotted Ethernet and PortChannel names as `VLAN_SUB_INTERFACE`.

The command continues to validate that the requested interface exists in
CONFIG_DB. For bare Ethernet and PortChannel interfaces, existing VLAN member
and PortChannel member checks are preserved. These checks are skipped for VLAN
subinterfaces because the subinterface itself is not a VLAN or PortChannel
member.

`show ipv6 link-local-mode` is updated to include `VLAN_SUB_INTERFACE` entries
in addition to physical, PortChannel, and VLAN interfaces.

### 6.3 `neighsyncd`

`neighsyncd::isLinkLocalEnabled()` is updated to classify VLAN subinterfaces
before checking bare interface tables. For subinterfaces, it reads
`VLAN_SUB_INTERFACE|<ifname>` and checks whether `ipv6_use_link_local_only` is
set to `enable`.

The final implementation uses the shared `swss::subIntf` parser. This keeps
the accepted names consistent with other SWSS components such as `intfmgr`,
`portsorch`, and `intfsorch`.

```
kernel netlink RTM_NEWNEIGH
        |
        v
neighsyncd::isLinkLocalEnabled(ifname)
        |
        +-- swss::subIntf valid: read VLAN_SUB_INTERFACE
        +-- Vlan*:              read VLAN_INTERFACE
        +-- PortChannel*:       read PORTCHANNEL_INTERFACE
        +-- Ethernet*:          read INTERFACE
        +-- otherwise:          reject
        |
        v
APPL_DB:NEIGH_TABLE -> neighorch -> SAI neighbor / next-hop / route
```

There is no SAI API change and no change to FRR's BGP configuration model.

## 7. Configuration and Management

Example configuration:

```
config subinterface add Eth0.10 10
config interface ipv6 enable use-link-local-only Eth0.10
```

Example FRR configuration:

```
router bgp 65001
 neighbor Eth0.10 interface remote-as 65002
 address-family ipv4 unicast
  network 1.1.1.1/32
 exit-address-family
```

Operational checks:

```
show ipv6 link-local-mode
show bgp summary
show ip route
```

## 8. Warmboot and Fastboot Impact

No warmboot or fastboot impact is expected. The changes add schema validation,
CLI handling, and a `neighsyncd` classification path. They do not add persisted
state beyond the existing `ipv6_use_link_local_only` field and do not alter SAI
object lifecycles.

## 9. Restrictions

- IPv6 link-local-only mode must be explicitly enabled on the VLAN subinterface.
- Non-canonical dotted names such as `eth0.10`, `lo.10`, or `Vlan100.10` are
  rejected by the SWSS subinterface parser.
- Short names may be required when the long-name form exceeds Linux `IFNAMSIZ`.

## 10. Testing

Required coverage:

| Repository | Coverage |
|------------|----------|
| `sonic-buildimage` | YANG model tests for valid and invalid `ipv6_use_link_local_only` values under `VLAN_SUB_INTERFACE`, plus schema support for VLAN subinterface BGP neighbors. |
| `sonic-utilities` | CLI unit tests for enable/disable on VLAN subinterfaces, short-name subinterfaces, invalid names, and `show ipv6 link-local-mode`. |
| `sonic-swss` | Mock tests for `isLinkLocalEnabled()` covering bare interfaces, long/short subinterfaces, disabled/missing config, and rejected dotted names. |
| `frr` | Topotest that brings up BGP unnumbered on VLAN subinterfaces and verifies route exchange and session recovery. |
| `sonic-mgmt` | Optional end-to-end test that verifies BGP session state, `APPL_DB:NEIGH_TABLE`, kernel routes, and data-plane reachability. |

## 11. Component Changes

The upstream code PRs should be tracked from the HLD PR description until all
component changes merge. At minimum, the tracked PR set is:

| Repository | Change |
|------------|--------|
| `sonic-buildimage` | Add `VLAN_SUB_INTERFACE.ipv6_use_link_local_only` to YANG and tests, and allow BGP neighbors to reference VLAN subinterfaces. |
| `sonic-utilities` | Add CLI/show support for long and short VLAN subinterface names. |
| `sonic-swss` | Add `neighsyncd` VLAN subinterface link-local lookup and parser-driven short-name support. |
| `frr` | Add BGP unnumbered VLAN subinterface topotest. |
| `sonic-mgmt` | Add end-to-end SONiC regression coverage if accepted by the test maintainers. |
