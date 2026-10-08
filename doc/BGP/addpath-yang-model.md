# HLD: BGP ADDPATH Yang Model Changes

Rev v0.2

## Table of Contents

1. [Revisions](#revisions)
2. [Scope](#scope)
3. [Definitions and Abbreviations](#definitions-and-abbreviations)
4. [Overview](#overview)
5. [Background](#background)
6. [Requirements](#requirements)
7. [Design](#design)
   - [Yang Model Changes](#yang-model-changes)
   - [FRR Configuration Support](#frr-configuration-support)
8. [Configuration and Management](#configuration-and-management)
   - [CONFIG_DB Schema](#configdb-schema)
9. [Backward Compatibility](#backward-compatibility)
10. [Testing](#testing)
11. [References](#references)

---

## Revisions

| Rev  | Date       | Author    | Description                                               |
|------|------------|-----------|-----------------------------------------------------------|
| v0.1 | 2026-05-31 | Fred Xia  | Initial draft                                             |

---

## Scope

This document describes Yang model changes to `sonic-bgp-common.yang` to expose all FRR BGP
ADDPATH configuration options in SONiC. It covers:

- A new `tx_best_selected` enum value added to the existing `bgp_tx_add_paths_type` typedef
- A new `bgp_tx_add_paths_max_best_selected` leaf for the best-selected path count
- New Yang leaves for ADDPATH RX control
- Supporting template and `frrcfgd` changes that translate CONFIG_DB entries to FRR CLI commands

---

## Definitions and Abbreviations

| Term      | Definition                                                                                  |
|-----------|---------------------------------------------------------------------------------------------|
| ADDPATH   | BGP ADD-PATH extension (RFC 7911) — allows advertising multiple paths per prefix            |
| AFI/SAFI  | Address Family Identifier / Subsequent Address Family Identifier                            |
| FRR       | FRRouting — open-source routing suite used as the BGP implementation in SONiC               |
| NLRI      | Network Layer Reachability Information                                                      |
| Path ID   | 4-octet identifier prepended to NLRI to distinguish multiple paths for the same prefix      |
| RX        | Receive direction — paths received from a BGP peer                                          |
| TX        | Transmit direction — paths advertised to a BGP peer                                         |

---

## Overview

BGP ADDPATH (RFC 7911) enables a BGP speaker to advertise multiple paths for the same address
prefix to a peer. Each path is identified by a locally assigned 4-octet Path Identifier prepended
to the NLRI encoding. The capability is negotiated using BGP Capability Code 69, with separate
send and receive directions per AFI/SAFI.

This feature is widely implemented by major vendors and is fully supported by FRR. However, the
SONiC Yang model historically exposed only one attribute — `tx_add_paths` — with two enumerated
values (`tx_all_paths`, `tx_best_path_per_as`). This left the full set of FRR ADDPATH knobs
unreachable through the SONiC configuration interface.

Extending the Yang model to cover all ADDPATH options serves two purposes. First, it provides a
more complete and accurate picture of the BGP router configuration at the SONiC level, enabling
operators to manage and audit the full ADDPATH policy through SONiC tooling. Second, and more
importantly, it allows ADDPATH configuration to be persisted in CONFIG_DB — the source of truth
for SONiC configuration. Any configuration applied directly via `vtysh` is transient: the FRR
container is ephemeral, and its running state is discarded on restart or reboot. Only
configuration reflected in CONFIG_DB survives across restarts and is reliably replayed when FRR
is brought back up.

This HLD describes the Yang model extensions required to support all FRR ADDPATH configuration
options, along with corresponding changes in FRR template rendering and `frrcfgd` to wire them
through to the running FRR configuration.

---

## Background

### RFC 7911 — Advertisement of Multiple Paths in BGP

RFC 7911 defines the ADD-PATH Capability (code 69) which allows a BGP speaker to advertise
multiple paths for the same prefix without new paths implicitly replacing previous ones. Key
points:

- Each path is tagged with a 4-octet Path Identifier assigned locally by the advertising speaker.
- The capability is negotiated per `<AFI, SAFI>` with independent send/receive directions.
- A speaker SHOULD include the best route when advertising multiple paths, unless that path was
  received from the same peer.
- RFC 7911 explicitly calls out a security concern: multiple paths for a large number of prefixes
  may deplete memory or cause network-wide instability (a potential denial-of-service vector).

### ADDPATH Paths Limit (draft-abraitis-idr-addpath-paths-limit)

This IETF draft extends ADDPATH negotiation to allow a receiver to advertise a limit on the
number of additional paths it is willing to accept per prefix. The limit is signaled as part
of the ADD-PATH Capability during BGP OPEN. The sending peer is expected to honor the limit.

FRR supports the receiving side of this draft via `addpath-rx-paths-limit`. Enforcement on the
receiving side (dropping paths from a non-compliant peer that exceeds the limit) is not yet
implemented in FRR.

### FRR ADDPATH Configuration Options

FRR exposes the following per-neighbor, per-address-family ADDPATH knobs:

```
addpath-tx-all-paths               Advertise all paths to the peer
addpath-tx-best-selected <N>       Advertise N best-selected paths to the peer (N: 1–6)
addpath-tx-bestpath-per-AS         Advertise the best path from each neighboring AS

disable-addpath-rx                 Do not accept additional paths from the peer
addpath-rx-paths-limit <N>         Signal a limit of N paths willing to receive (N: 1–65535)
```

All TX options are mutually exclusive. In FRR, ADDPATH RX is enabled by default.

### Prior SONiC Yang Model

The `sonic-bgp-cmn-af` grouping in `sonic-bgp-common.yang` contained a single leaf backed by
a two-value enum:

```yang
typedef bgp_tx_add_paths_type {
    type enumeration {
        enum tx_all_paths { ... }
        enum tx_best_path_per_as { ... }
    }
}

leaf tx_add_paths {
    type bgp_tx_add_paths_type;
}
```

This covered only two of the five FRR knobs and provided no RX-direction control.

---

## Requirements

| # | Requirement                                                                                        |
|---|----------------------------------------------------------------------------------------------------|
| 1 | Expose all three mutually exclusive FRR TX ADDPATH modes in the Yang model                         |
| 2 | Expose the FRR `disable-addpath-rx` knob in the Yang model                                         |
| 3 | Expose the FRR `addpath-rx-paths-limit` knob in the Yang model                                     |
| 4 | Translate new Yang attributes to FRR CLI commands via existing template and `frrcfgd` mechanisms   |

---

## Design

### Yang Model Changes

The changes are in the `sonic-bgp-cmn-af` grouping of `sonic-bgp-common.yang`. This grouping is
shared by neighbor and peer-group address-family tables.

#### Extended `bgp_tx_add_paths_type` Typedef

A third enum value `tx_best_selected` is added to the existing `bgp_tx_add_paths_type` typedef.

```yang
typedef bgp_tx_add_paths_type {
    type enumeration {
        enum tx_all_paths {
            description
                "Send multiple path advertisements for an NLRI from
                the neighbor or group";
        }
        enum tx_best_path_per_as {
            description
                "Send only best path per AS advertisements for an NLRI from
                the neighbor or group";
        }
        enum tx_best_selected {
            description
                "Send N best-selected path advertisements for an NLRI to
                the neighbor or group (count set by bgp_tx_add_paths_max_best_selected)";
        }
    }
    description
        "Type to describe the add paths TX advertisement method.";
}
```

#### Updated `tx_add_paths` Leaf

Its description is updated to reference the new companion leaf:

```yang
leaf tx_add_paths {
    type bgp_tx_add_paths_type;
    description "TX add-path mode: tx_all_paths, tx_best_path_per_as, or tx_best_selected.
                 When tx_best_selected, the count is set by bgp_tx_add_paths_max_best_selected.";
}
```

Mutual exclusion is enforced implicitly: `tx_add_paths` is a single-valued leaf, so only one TX
mode can be active at a time.

#### New `bgp_tx_add_paths_max_best_selected` Leaf

When `tx_add_paths` is set to `tx_best_selected`, the number of paths to advertise is controlled
by this companion leaf:

```yang
leaf bgp_tx_add_paths_max_best_selected {
    type uint8 {
        range "1..6";
    }
    when "../tx_add_paths = 'tx_best_selected'";
    default "1";
    description "Number of best-selected paths to advertise when tx_add_paths is tx_best_selected.";
}
```

Key points:

- **Type is `uint8`**, not `uint16`. The range 1–6 matches the FRR limit.
- **`when` condition**: the leaf is only valid when `tx_add_paths` is `tx_best_selected`. Setting
  `bgp_tx_add_paths_max_best_selected` while `tx_add_paths` is absent or set to another value is
  a Yang validation error. This constraint is enforced by libyang at load time.
- **Default of `1`**: a bare `tx_best_selected` configuration without an explicit count advertises
  one path. In CONFIG_DB the field may be omitted; the template and `frrcfgd` both fall back to `1`.

#### New ADDPATH RX Leaves

```yang
leaf addpath_rx_disable {
    type boolean;
    description "Disable receiving add-path advertisements from this neighbor";
}

leaf addpath_rx_paths_limit {
    type uint16 {
        range "1..65535";
    }
    description "Limit the number of add-path paths received from this neighbor";
}
```

`addpath_rx_paths_limit` is optional. When set, it signals the paths-limit value to the peer
during capability negotiation as specified by draft-abraitis-idr-addpath-paths-limit.

Note: FRR currently does not enforce the received path limit locally — it is up to the peer to
honor the limit conveyed during capability negotiation. Enforcement work in FRR is ongoing.

#### YANG Revision Entry

```yang
revision 2026-04-22 {
    description
        "Add BGP address-family level add-path configuration parameters supported by FRR to
         sonic-bgp-cmn-af grouping: add tx_best_selected enum to bgp_tx_addpaths_type,
         add bgp_tx_add_paths_max_best_selected (uint8, 1..6, default 1).";
}
```

The revision text is intentionally scoped to the TX changes introduced in this commit. The RX
leaves (`addpath_rx_disable`, `addpath_rx_paths_limit`) were established in the same revision
cycle and are present in the model.

#### Complete `sonic-bgp-cmn-af` Addpath Grouping (after changes)

For reference, the complete set of addpath-related leaves in `sonic-bgp-cmn-af` after this change:

```yang
leaf tx_add_paths {
    type bgp_tx_add_paths_type;        // enum: tx_all_paths | tx_best_path_per_as | tx_best_selected
    description "...";
}

leaf bgp_tx_add_paths_max_best_selected {
    type uint8 { range "1..6"; }
    when "../tx_add_paths = 'tx_best_selected'";
    default "1";
    description "...";
}

leaf addpath_rx_disable {
    type boolean;
    description "...";
}

leaf addpath_rx_paths_limit {
    type uint16 { range "1..65535"; }
    description "...";
}
```

---

### FRR Configuration Support

The FRR configuration templates and `frrcfgd` scripts are adjusted to support the extended
`tx_add_paths` enum and the new companion leaf.

`bgpcfgd` is **not supported**. `bgpcfgd` operates in legacy mode and has no logic to process
neighbor address-family tables (`BGP_NEIGHBOR_AF`, `BGP_PEER_GROUP_AF`). ADDPATH configuration
requires `frrcfgd`.

#### Jinja2 Template (`bgpd.conf.db.nbr_af.j2`)

The `tx_add_paths` block in the existing template is extended with a branch for the new
`tx_best_selected` value. The block reads `bgp_tx_add_paths_max_best_selected` from the neighbor
AF dict, defaulting to `1` if the key is absent:

```jinja2
{% if 'tx_add_paths' in n_af_val %}
{% if n_af_val['tx_add_paths'] == 'tx_all_paths' %}
  neighbor {{nbr_name}} addpath-tx-all-paths
{% elif n_af_val['tx_add_paths'] == 'tx_best_selected' %}
  neighbor {{nbr_name}} addpath-tx-best-selected {{n_af_val.get('bgp_tx_add_paths_max_best_selected', '1')}}
{% elif n_af_val['tx_add_paths'] == 'tx_best_path_per_as' %}
  neighbor {{nbr_name}} addpath-tx-bestpath-per-AS
{% endif %}
{% endif %}
```

The redundant second block that rendered the old `addpath_tx_all_paths`, `addpath_tx_best_selected`,
and `addpath_tx_bestpath_per_as` leaves is removed.

#### frrcfgd

A dedicated handler `hdl_tx_add_paths` is added. It receives `tx_add_paths` and the optional
`bgp_tx_add_paths_max_best_selected` together and emits the appropriate FRR command, falling back
to count `1` when the companion field is absent. The RX leaves (`addpath_rx_disable`,
`addpath_rx_paths_limit`) use standard format-string dispatch and are unchanged.

---

## Configuration and Management

### CONFIG_DB Schema

The new and updated attributes land in the `BGP_NEIGHBOR_AF` and `BGP_PEER_GROUP_AF` tables,
keyed as `<vrf>|<neighbor>|<afi_safi>`. All attributes are optional;
`bgp_tx_add_paths_max_best_selected` defaults to `1` and is only valid (per the YANG `when`
condition) when `tx_add_paths` is `tx_best_selected`.

| Field                                | Type    | Values / Range                                              | Description                                      |
|--------------------------------------|---------|-------------------------------------------------------------|--------------------------------------------------|
| `tx_add_paths`                       | enum    | `tx_all_paths`, `tx_best_path_per_as`, `tx_best_selected`   | TX add-path mode (mutually exclusive by leaf)    |
| `bgp_tx_add_paths_max_best_selected` | uint8   | 1–6 (default: `1`)                                          | Path count when `tx_add_paths = tx_best_selected`|
| `addpath_rx_disable`                 | boolean | `true`/`false`                                              | Disable ADDPATH RX                               |
| `addpath_rx_paths_limit`             | uint16  | 1–65535                                                     | Paths-limit signaled during capability negotiation|

---

## Backward Compatibility

The `tx_add_paths` leaf and `bgp_tx_add_paths_type` typedef retain their existing structure with
the original two enum values unchanged. Existing configurations using `tx_all_paths` or
`tx_best_path_per_as` continue to work without modification. FRR ADDPATH RX behavior is
unchanged — it remains enabled by default unless `addpath_rx_disable` is set to `true`.

---

## Testing

### Unit Tests — Yang Model Constraints

A pytest suite (`test_bgp_addpath.py`) validates the Yang model using libyang. Tests cover:

- All three `tx_add_paths` enum values load successfully.
- `bgp_tx_add_paths_max_best_selected` range: values 1 and 6 succeed; 0 and 7 fail.
- `bgp_tx_add_paths_max_best_selected` `when` condition: setting the leaf while `tx_add_paths`
  is absent or set to `tx_all_paths`/`tx_best_path_per_as` produces a `When condition` error.
- `addpath_rx_paths_limit` range: 1 and 65535 succeed; 0 and 65536 fail.
- Combined TX + RX options validate successfully.
- Tests run for both `BGP_NEIGHBOR_AF_LIST` and `BGP_PEER_GROUP_AF_LIST`.

### Unit Tests — Template and frrcfgd

Tests in `test_config.py` verify CONFIG_DB entries produce the correct FRR CLI output:

| CONFIG_DB input                                                              | Expected FRR command                           |
|------------------------------------------------------------------------------|------------------------------------------------|
| `tx_add_paths = tx_all_paths`                                                | `neighbor <N> addpath-tx-all-paths`            |
| `tx_add_paths = tx_best_selected`, `bgp_tx_add_paths_max_best_selected = 3`  | `neighbor <N> addpath-tx-best-selected 3`      |
| `tx_add_paths = tx_best_path_per_as`                                         | `neighbor <N> addpath-tx-bestpath-per-AS`      |
| `addpath_rx_disable = true`                                                  | `neighbor <N> disable-addpath-rx`              |
| `addpath_rx_disable = false`                                                 | `no neighbor <N> disable-addpath-rx`           |
| `addpath_rx_paths_limit = 100`                                               | `neighbor <N> addpath-rx-paths-limit 100`      |

---

## References

- [RFC 7911 — Advertisement of Multiple Paths in BGP](https://www.rfc-editor.org/rfc/rfc7911)
- [draft-abraitis-idr-addpath-paths-limit — Paths Limit for BGP ADD-PATH](https://www.ietf.org/archive/id/draft-abraitis-idr-addpath-paths-limit-04.txt)
- [SONiC HLD Guidelines](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines)
- `src/sonic-yang-models/yang-models/sonic-bgp-common.yang`
