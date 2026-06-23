# IPv6-Only Active-Active Control Plane Support

## Revision

| Rev | Date | Author | Change Description |
| --- | --- | --- | --- |
| 0.1 | 2026-06-22 | Jing Zhang | Initial design for IPv6-only active-active DualToR control-plane support |

## Overview

This document describes the SONiC behavior required to support IPv6-only active-active DualToR clusters for control-plane paths that currently depend on IPv4 endpoints.

The change is intentionally conservative. Existing IPv4-only and dual-stack deployments must continue to use IPv4. IPv6 is selected only when the corresponding IPv4 field is missing.

This document does not redesign DualToR data-plane forwarding, neighbor handling, IPinIP routing, or the active-active state machine. Those behaviors should remain unchanged unless validation exposes a direct dependency on IPv4-only control endpoints.

## Background

Active-active DualToR deployments use linkmgrd to probe server or SoC reachability and use ycabled to send gRPC requests to the SoC or NIC side for forwarding-state control.

The `MUX_CABLE` schema already has both IPv4 and IPv6 endpoint fields:

```text
MUX_CABLE|<port>:
    server_ipv4: <server IPv4 prefix>
    server_ipv6: <server IPv6 prefix>
    soc_ipv4:    <SoC IPv4 prefix>
    soc_ipv6:    <SoC IPv6 prefix>
    cable_type:  active-active | active-standby
    state:       auto | manual | detach | active | standby
```

No new Config DB fields are required.

## Problem Statement

An IPv6-only active-active cluster may have `server_ipv6` and `soc_ipv6` for a mux cable, but no `server_ipv4` or `soc_ipv4`. Existing IPv4-oriented control paths can fail in this shape:

1. Config generation may skip a `MUX_CABLE` row when the server IPv4 loopback is missing, even if the server IPv6 loopback exists.
2. linkmgrd may fail to select an IPv6 endpoint for link probing when IPv4 is absent.
3. ycabled may fail to create a gRPC channel when `soc_ipv4` is absent, even if `soc_ipv6` exists.

As a result, an IPv6-only active-active cluster can miss required mux configuration, fail link probing, or fail SoC-side gRPC control.

## Goals

1. Support IPv6-only active-active DualToR control-plane endpoints.
2. Preserve IPv4 behavior for existing IPv4-only deployments.
3. Preserve IPv4 preference for dual-stack deployments.
4. Avoid Config DB schema changes.
5. Keep failures isolated to the affected port when an endpoint is missing or malformed.
6. Preserve existing active-active state-machine behavior.


## Component Requirements

| Component | Required behavior |
| --- | --- |
| Config generation | <ul><li>Generate `MUX_CABLE` entries when `server_ipv6` exists even if `server_ipv4` is absent.</li><li>Include `server_ipv6` and `soc_ipv6` fields when available.</li><li>Preserve IPv4 fields when they are present.</li></ul> |
| linkmgrd | <ul><li>Select IPv4 endpoints first when present.</li><li>Use `server_ipv6` and `soc_ipv6` when the matching IPv4 field is absent.</li><li>Use Loopback2 IPv6 as the link-prober source address when the selected probe endpoint is IPv6.</li><li>Use Loopback3 IPv6 as the GUID source component when the selected probe endpoint is IPv6.</li><li>Use ICMPv6 link probing for IPv6-selected endpoints.</li><li>Create IPv6 hardware ICMP echo session fields when hardware probing is enabled for IPv6-selected endpoints.</li></ul> |
| ycabled | <ul><li>Select `soc_ipv4` first when present.</li><li>Use `soc_ipv6` when `soc_ipv4` is absent.</li><li>Format IPv6 gRPC targets as `[addr]:port`.</li></ul> |

## Loopback Address Selection

linkmgrd uses Loopback2 as the link-prober source address and Loopback3 as part of link-prober GUID generation.

| Selected probe endpoint | Link-prober source address | GUID source component |
| --- | --- | --- |
| IPv4 server or SoC address | Loopback2 IPv4 | Loopback3 IPv4 |
| IPv6 server or SoC address | Loopback2 IPv6 | Loopback3 IPv6 |

A missing IPv4 loopback is not fatal when the corresponding IPv6 loopback exists and the selected probe endpoint is IPv6.

## Examples

IPv6-only active-active port:

```json
{
    "MUX_CABLE": {
        "Ethernet8": {
            "state": "auto",
            "cable_type": "active-active",
            "server_ipv6": "fc02:1000::2/128",
            "soc_ipv6": "fc02:1000::3/128"
        }
    }
}
```

Expected behavior:

1. Config generation emits the `MUX_CABLE` entry.
2. linkmgrd probes `fc02:1000::3` with ICMPv6.
3. ycabled connects gRPC to `[fc02:1000::3]:<port>`.

Dual-stack active-active port:

```json
{
    "MUX_CABLE": {
        "Ethernet8": {
            "state": "auto",
            "cable_type": "active-active",
            "server_ipv4": "10.10.10.2/32",
            "server_ipv6": "fc02:1000::2/128",
            "soc_ipv4": "10.10.10.3/32",
            "soc_ipv6": "fc02:1000::3/128"
        }
    }
}
```

Expected behavior:

1. linkmgrd continues to use `soc_ipv4` for probing.
2. ycabled continues to use `soc_ipv4` for gRPC.
3. IPv6 fields remain available but are not selected by default.

## Compatibility

| Config shape | linkmgrd selected endpoint | ycabled selected endpoint |
| --- | --- | --- |
| `soc_ipv4` only | `soc_ipv4` | `soc_ipv4` |
| `soc_ipv4` and `soc_ipv6` | `soc_ipv4` | `soc_ipv4` |
| `soc_ipv6` only | `soc_ipv6` | `soc_ipv6` |
| Neither field present | unavailable | unavailable |

No migration is required for existing deployments.

## Error Handling

For each mux port:

1. If IPv4 is missing but IPv6 exists, select IPv6.
2. If both IPv4 and IPv6 endpoint fields are missing, leave the endpoint unavailable for that port and log the condition.
3. If the selected endpoint is malformed, reject that endpoint for the affected port and log the condition.
4. If IPv4 is present but malformed, do not silently fall back to IPv6 unless SONiC maintainers explicitly choose tolerant fallback semantics.

## Validation

Validation should be covered through sonic-mgmt so the IPv6-only active-active topology is represented by the same testbed, simulator, and traffic-control framework used by existing DualToR testing.

Required sonic-mgmt adaptation:

1. Configuration examples and generated testbed inputs must support active-active mux ports that have `server_ipv6` and `soc_ipv6`, without `server_ipv4` or `soc_ipv4`.
2. Testbed and simulator configuration must carry Loopback2 IPv6 and Loopback3 IPv6 addresses so linkmgrd can use Loopback2 as the ICMPv6 probe source and Loopback3 as the GUID source component.
3. Shared DualToR address handling must apply the same IPv4-preferred rule as SONiC: use IPv4 when present, use IPv6 only when the matching IPv4 field is absent, and format IPv6 host/port strings with brackets.
4. The ICMP responder must support ICMPv6 echo replies for link-prober validation while preserving the link-prober payload.
5. The NiC simulator and its control helpers must support IPv6 SoC endpoints, including gRPC bind and client targets, and must use `soc_ipv6` when `soc_ipv4` is absent.
6. Simulator management paths that build HTTP or gRPC URLs must handle IPv6 addresses correctly, while preserving existing IPv4 behavior.
7. Existing IPv4-only and dual-stack sonic-mgmt coverage must remain in place to confirm IPv4 is still selected when present.

Validation is complete when sonic-mgmt can load an IPv6-only active-active configuration, drive ICMPv6 link-prober health through the responder, exercise NiC simulator gRPC control over IPv6 endpoints, verify mux state transitions, and rerun dual-stack coverage to confirm IPv4 preference.


