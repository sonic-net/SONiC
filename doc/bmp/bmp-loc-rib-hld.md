# BMP Loc-RIB Support High-Level Design

## Table of Contents
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
- [Configuration and Management](#configuration-and-management)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Testing Requirements](#testing-requirements)
- [References](#references)

## Revision

| Rev | Date       | Author | Description |
|-----|------------|--------|-------------|
| 0.1 | 2026-10-04 | -      | Initial draft |

## Scope

This document describes the high-level design for adding Loc-RIB (Local Routing Information Base) monitoring support to SONiC's BMP implementation per RFC 9069.

## Definitions/Abbreviations

| Term | Definition |
|------|------------|
| BMP | BGP Monitoring Protocol (RFC 7854) |
| Loc-RIB | Local Routing Information Base - the post-policy, best-path selected routing table |
| Adj-RIB-In | Adjacent RIB Inbound - routes received from BGP peers |
| Adj-RIB-Out | Adjacent RIB Outbound - routes advertised to BGP peers |

## Overview

### Background

BMP (RFC 7854) defines a protocol for monitoring BGP sessions and routing information. The current SONiC BMP implementation supports:

| RIB Type | Description | Current Support |
|----------|-------------|-----------------|
| Adj-RIB-In | Routes received from peers | ✅ Implemented |
| Adj-RIB-Out | Routes sent to peers | ✅ Implemented |
| **Loc-RIB** | Local routing table (best paths) | ❌ Not implemented |

RFC 9069 extends BMP to support Loc-RIB monitoring, which provides visibility into the routes that have been selected as best paths after BGP path selection and import policy application.

### Why Loc-RIB?

Loc-RIB monitoring enables:
- **Best Path Visibility** - See which routes were selected as best paths
- **Policy Verification** - Understand import policy effects on the routing table
- **Forwarding Verification** - Verify routes installed for forwarding decisions
- **Troubleshooting** - Debug routing issues by comparing Loc-RIB with Adj-RIB-In

## Requirements

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Support Loc-RIB monitoring via BMP protocol (RFC 9069) |
| FR-2 | Store Loc-RIB data in BMP_STATE_DB |
| FR-3 | Provide CLI to enable/disable Loc-RIB monitoring |
| FR-4 | Support IPv4 and IPv6 Loc-RIB entries |
| FR-5 | Support VRF-aware Loc-RIB monitoring |
| FR-6 | Support Filtered Loc-RIB to limit routes sent to telemetry |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Minimal performance impact on BGP convergence |
| NFR-2 | Scale to 1M+ routes |

## Architecture Design

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SONiC DUT                               │
│                                                                 │
│  ┌──────────────┐     BMP (peer_type=3)     ┌───────────────┐  │
│  │  FRR/bgpd    │ ─────────────────────────▶│  sonic-bmp    │  │
│  │  (Loc-RIB)   │                           │  (openbmpd)   │  │
│  └──────────────┘                           └───────┬───────┘  │
│                                                     │          │
│                                           ┌─────────▼────────┐ │
│                                           │   BMP_STATE_DB   │ │
│                                           │ ┌──────────────┐ │ │
│                                           │ │BGP_LOC_RIB   │ │ │
│                                           │ │    _TABLE    │ │ │
│                                           │ └──────────────┘ │ │
│                                           └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### BMP Message Format for Loc-RIB

Per RFC 9069, Loc-RIB uses BMP Route Monitoring messages with:
- **Peer Type = 3** (indicates Loc-RIB)
- **F Flag** (bit 7): Filtered Loc-RIB indicator
- **Peer Distinguisher**: VRF/table identifier

### Filtered vs Unfiltered Loc-RIB

RFC 9069 supports two modes:

| Mode | F Flag | Description | Use Case |
|------|--------|-------------|----------|
| **Unfiltered** | 0 | Full Loc-RIB sent to collector | Complete visibility |
| **Filtered** | 1 | Subset of Loc-RIB based on policy | Scale/bandwidth optimization |

Filtered Loc-RIB allows operators to limit telemetry to specific prefixes using prefix-lists, reducing BMP traffic and Redis storage for large-scale deployments.

### Mechanisms to Limit Telemetry

| Mechanism | Configuration | Description |
|-----------|---------------|-------------|
| **Address Family Selection** | FRR config | Monitor only IPv4, only IPv6, or both |
| **Filtered Loc-RIB** | CONFIG_DB + prefix-list | Limit to specific prefixes |
| **VRF Selection** | Per-VRF BMP config | Monitor specific VRFs only |

## High-Level Design

### Database Changes

#### CONFIG_DB

Add `bgp_loc_rib_table` and optional filter to existing BMP configuration:

| Key | Field | Value | Description |
|-----|-------|-------|-------------|
| BMP\|table | bgp_loc_rib_table | "true" / "false" | Enable/disable Loc-RIB monitoring |
| BMP\|table | bgp_loc_rib_filter | prefix-list name | Optional: filter to limit routes (empty = unfiltered) |

#### BMP_STATE_DB

New table `BGP_LOC_RIB_TABLE`:

| Key Format | Fields |
|------------|--------|
| BGP_LOC_RIB_TABLE\|{vrf}\|{prefix} | prefix, next_hop, as_path, origin, local_pref, med, community, is_filtered, timestamp |

**Example:**
```
BGP_LOC_RIB_TABLE|default|10.0.0.0/24
BGP_LOC_RIB_TABLE|Vrf_red|192.168.1.0/24
```

### Component Changes

| Component | Changes |
|-----------|---------|
| **sonic-bmp** | Add `BGP_LOC_RIB_TABLE` handling in RedisManager |
| **FRR/bgpd** | Enable `bmp monitor loc-rib` in BMP targets configuration |
| **sonic-utilities** | Add CLI commands for Loc-RIB table management |
| **sonic-yang-models** | Add `bgp_loc_rib_table` leaf to BMP YANG model |

### FRR Configuration

Add Loc-RIB monitoring to BMP targets:
```
bmp targets sonic-bmp
  bmp monitor ipv4 unicast loc-rib
  bmp monitor ipv6 unicast loc-rib
```

**Address Family Selection** - enable only specific AFI/SAFI:
```
# IPv4 only
bmp targets sonic-bmp
  bmp monitor ipv4 unicast loc-rib

# IPv6 only
bmp targets sonic-bmp
  bmp monitor ipv6 unicast loc-rib
```

**Filtered Loc-RIB** - limit to specific prefixes:
```
bmp targets sonic-bmp
  bmp monitor ipv4 unicast loc-rib prefix-list BMP_FILTER
  bmp monitor ipv6 unicast loc-rib prefix-list BMP_FILTER6
```

## Configuration and Management

### CLI Commands

```bash
# Enable Loc-RIB monitoring (unfiltered)
config bmp enable bgp-loc-rib-table

# Enable Loc-RIB monitoring with filter (filtered)
config bmp enable bgp-loc-rib-table --filter <prefix-list-name>

# Disable Loc-RIB monitoring
config bmp disable bgp-loc-rib-table

# Show Loc-RIB table
show bmp bgp-loc-rib-table

# Show all BMP table status
show bmp tables
```

### Expected Output

```
admin@sonic:~$ show bmp tables
BMP tables:
  bgp_neighbor_table    true
  bgp_rib_in_table      true
  bgp_rib_out_table     true
  bgp_loc_rib_table     true

admin@sonic:~$ show bmp bgp-loc-rib-table
VRF      Prefix           Next-Hop       AS-Path        Origin  LocalPref
-------  ---------------  -------------  -------------  ------  ---------
default  10.0.0.0/24      192.168.1.1    65001 65002    igp     100
default  10.1.0.0/24      192.168.1.2    65001 65003    igp     100
```

## Warmboot and Fastboot Design Impact

- Loc-RIB table in BMP_STATE_DB is **not** preserved across warmboot/fastboot
- FRR will re-send full Loc-RIB via BMP when sessions re-establish
- Consistent with existing Adj-RIB-In/Out behavior

## Testing Requirements

### Test Cases

| Test | Description |
|------|-------------|
| TC-1 | Enable/disable Loc-RIB table via CLI |
| TC-2 | Verify Loc-RIB entries in BMP_STATE_DB |
| TC-3 | Compare Loc-RIB content with FRR's actual RIB |
| TC-4 | VRF-aware Loc-RIB verification |
| TC-5 | Scale test with large number of routes |
| TC-6 | Filtered Loc-RIB: verify only matching prefixes are in BMP_STATE_DB |
| TC-7 | Verify F flag is set correctly (filtered vs unfiltered) |

## References

- [RFC 7854 - BGP Monitoring Protocol (BMP)](https://datatracker.ietf.org/doc/html/rfc7854)
- [RFC 9069 - Support for Local RIB in BMP](https://datatracker.ietf.org/doc/html/rfc9069)
- [FRR BMP Documentation](https://docs.frrouting.org/en/latest/bmp.html)
- [SONiC BMP HLD](https://github.com/sonic-net/SONiC/blob/master/doc/bmp/bmp.md)
