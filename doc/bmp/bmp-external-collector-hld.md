# BMP External Collector Support in SONiC

## High Level Design Document

# Table of Contents

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Definitions/Abbreviation](#definitionsabbreviation)

  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
    * [1.2 CLI requirements](#12-cli-requirements)
    * [1.3 Scalability and Default Values](#13-scalability-and-default-values)
    * [1.4 Warm Restart requirements](#14-warm-restart-requirements)
  * [2 Architecture Design](#2-architecture-design)
    * [2.1 High-Level Architecture](#21-high-level-architecture)
    * [2.2 BMP Object Model](#22-bmp-object-model)
    * [2.3 BGP/FRR Configuration Mapping](#23-bgpfrr-configuration-mapping)
    * [2.4 Configuration Rendering (bgpcfgd and frrcfgd)](#24-configuration-rendering-bgpcfgd-and-frrcfgd)
    * [2.5 Backward Compatibility](#25-backward-compatibility)
    * [2.6 Config DB and YANG Schema](#26-config-db-and-yang-schema)
    * [2.7 Information Flow](#27-information-flow)
  * [3 CLI](#3-cli)
  * [4 Resource usage and Test plan](#4-resource-usage-and-test-plan)

###### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |  06/04/2026 |   Kalash Nainwal   | Initial version                   |


# About this Manual

SONiC already supports BMP (BGP Monitoring Protocol, RFC 7854) for monitoring on-box BGP state. That feature — described in the existing design document [BMP for monitoring SONiC BGP info](https://github.com/sonic-net/SONiC/blob/master/doc/bmp/bmp.md) — brings up a `bmp` container running two daemons: `bmpcfgd`, which watches the `BMP` table in CONFIG_DB and controls which tables are populated, and `openbmpd`, an **oon-box** BMP collector that accepts the BMP stream from `bgpd`, parses it, and writes BGP state into `BMP_STATE_DB` for consumption over GNMI / streaming telemetry. To feed `openbmpd`, `bgpd` is started with the BMP module (`-M bmp`) and its configuration template emits a single, hard-coded BMP target connecting to `127.0.0.1:5000`. The only operator-facing knobs (`BMP|table` — `bgp_neighbor_table`, `bgp_rib_in_table`, `bgp_rib_out_table`) control *which tables `openbmpd` populates*; there is no way to point `bgpd` at any collector other than the local one, and no way to tune what each target monitors.

However, some customers want to stream BMP to one or more **external** collectors of their own choosing, rather than depending on the locally-running OpenBMP instance in the `bmp` container. Running that collector on the switch also carries a heavy memory cost in high route-scale environments. Shipping BMP directly to purpose-built external collectors alleviates this memory concern.

This document proposes **extending** that support so that, in addition to (or instead of) the on-box collector, an operator can stream BMP to one or more **external** collectors and fully control the BMP feed. Concretely, this feature adds the ability to configure: multiple BMP **targets**; one or more **collectors** per target (by IP/hostname and TCP port); per-target, per-AFI/SAFI selection of Adj-RIB-In pre-policy, Adj-RIB-In post-policy, and Loc-RIB; per-target route mirroring and statistics interval; per-collector connection-retry timers and source interface; and a global mirror buffer limit. The underlying capability already exists in `sonic-frr`'s `bgpd`; this design exposes it through SONiC's configuration model (CONFIG_DB + YANG), while preserving today's behavior for deployments that configure nothing new.

The on-box collector path (`openbmpd`, `BMP_STATE_DB`, the GNMI/telemetry consumption, and the `BMP|table` controls) is unchanged by this design.

# Definitions/Abbreviation

| **Term**     | **Meaning**                                                       | **Link**                                      |
|--------------|------------------------------------------------------------------|-----------------------------------------------|
| BMP          | BGP Monitoring Protocol                                          | https://datatracker.ietf.org/doc/html/rfc7854 |
| OpenBMP      | Open Source BGP Monitoring Protocol Collection Framework (on-box `openbmpd`) | https://github.com/SNAS/openbmp     |
| BGP/FRR      | SONiC BGP container and `bgpd` daemon producing the BMP stream    | https://github.com/sonic-net/sonic-frr        |
| GNMI         | gRPC Network Management Interface                                 | https://github.com/openconfig/gnmi            |
| Collector    | A BMP monitoring station receiving the BMP TCP stream             |                                               |
| Target       | An FRR BMP block grouping a set of collectors and monitored data  |                                               |
| Adj-RIB-In   | Per-peer RIB of received routes (pre-policy / post-policy views)  |                                               |
| Loc-RIB      | Local RIB — routes selected by the local BGP best-path            |                                               |
| Mirroring    | BMP Route Mirroring — verbatim forwarding of received BGP PDUs (RFC 7854 §4.7) | |
| `bgpcfgd`    | BGP configuration daemon — renders FRR config from CONFIG_DB via Jinja2 templates at container start | |
| `frrcfgd`    | FRR configuration daemon — applies CONFIG_DB changes to FRR at runtime via `vtysh`                   | |


# 1 Requirements Overview

## 1.1 Functional requirements

Today the SONiC BMP feed is fixed to a single on-box collector and cannot be redirected or tuned. Operators increasingly run off-box BMP collectors (centralized route-analytics, anomaly-detection, archival). At a high level, the following should be supported:

- Configure one or more BMP **targets**.
- Configure one or more **collectors** per target, identified by `(IP/hostname, TCP port)`.
- Select, per target and per AFI/SAFI, whether to export Adj-RIB-In pre-policy, Adj-RIB-In post-policy, and/or Loc-RIB.
- Support these AFI/SAFI combinations: IPv4 unicast, IPv6 unicast, IPv4 multicast, IPv6 multicast, L2VPN EVPN, IPv4 VPN, IPv6 VPN.
- Enable per-target BMP route mirroring and a configurable statistics interval.
- Configure per-collector minimum/maximum connection-retry intervals and an optional source interface (important when the collector is reachable only over a management or loopback address).
- Configure a global mirror buffer limit shared by all targets.
- Keep on-box telemetry working: a device with no new configuration must behave exactly as today (single `sonic-bmp` target to `127.0.0.1:5000`).

## 1.2 CLI requirements

- Configuration is expressed in CONFIG_DB through new tables (`BMP|global`, `BMP_TARGET`, `BMP_TARGET_COLLECTOR`, `BMP_TARGET_AFI_SAFI`), validated by a YANG model, and therefore drivable via `config reload`/`config load`, GCU/JSON patch, and gNMI SET.
- Operational visibility of the collected BMP data continues to use the existing `show bmp …` commands and the GNMI/telemetry path (unchanged).
- The existing `config bmp enable|disable …` table controls are unchanged.

## 1.3 Scalability and Default Values

| Parameter                | Range / Type                       | Default       |
|--------------------------|------------------------------------|---------------|
| `mirror-buffer-limit`    | `0..4294967294` bytes              | `4294967214`  |
| `stats-interval`         | `100..86400000` ms                 | unset (FRR default applies) |
| `min-retry`              | `100..86400000` ms                 | `30000`       |
| `max-retry`              | `100..86400000` ms                 | `720000`      |
| `mirror`                 | boolean                            | `false`       |
| `adj-rib-in-pre/post`, `loc-rib` | boolean                    | `false`       |
| target `name`            | string, length `1..64`             | n/a           |

The number of targets/collectors is bounded by what `bgpd` and the platform can sustain; no artificial SONiC-side cap is imposed. The monitored AFI/SAFI set is limited to the seven enumerated values above.

## 1.4 Warm Restart requirements

No special handling for Warm restart. BMP is a monitoring/export feature outside the data-forwarding path. BMP configuration is ordinary persistent CONFIG_DB state and is reapplied through the standard render/daemon path after a reboot or container restart; sessions re-establish according to the configured retry timers.


# 2 Architecture Design

## 2.1 High-Level Architecture

This feature does **not** introduce a new daemon or container. It introduces new CONFIG_DB tables and the logic to translate them into FRR `bgpd` BMP configuration. The BMP stream is produced by `bgpd` directly to each configured collector; the existing on-box `openbmpd` simply becomes one collector among potentially several.

```
                       CONFIG_DB
        +-------------------------------+
        |  BMP|global    (buffer limit) |
        |  BMP_TARGET                   |
        |  BMP_TARGET_COLLECTOR         |
        |  BMP_TARGET_AFI_SAFI          |
        +---------------+---------------+
                        |
                        |  rendered by bgpcfgd (at container start)
                        |  applied  by frrcfgd (at runtime)
                        v
              +-------------------------+
              |   FRR bgpd  ( -M bmp )  |
              |  bmp targets / connect  |
              |  monitor / mirror /stats|
              +------+-----------+------+
                     |           |
                 TCP |           | TCP
                     v           v
        +--------------------+  +--------------------------+
        |  127.0.0.1:5000    |  |  external collector(s)   |
        |  (on-box openbmpd) |  |  e.g. 192.0.2.10:5000    |
        +---------+----------+  +--------------------------+
                  |
                  v
            BMP_STATE_DB
                  |
                  v
        GNMI / telemetry  (unchanged)
```

The following components are changed:

| Component | Repository | Change |
|-----------|-----------|--------|
| `yang-models/sonic-bmp.yang` | sonic-yang-models | New `BMP global`, `BMP_TARGET`, `BMP_TARGET_COLLECTOR`, `BMP_TARGET_AFI_SAFI` tables and an `afi-safi-type` typedef |
| `dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2` | sonic-buildimage | Render BMP targets/collectors/AFI-SAFI from CONFIG_DB into `bgpd.conf` (`bgpcfgd` path) |
| `frrcfgd/frrcfgd.py`, `templates/bgpd/bgpd.conf.db.j2` | sonic-frr-mgmt-framework | Subscribe to the new tables and apply BMP config at runtime (`frrcfgd` path) |
| `tests/test_frr.py`, sample outputs | sonic-config-engine | Template render unit tests for single/multiple-target cases |
| `tests/test_config.py` | sonic-frr-mgmt-framework | `frrcfgd` handler unit tests |

No SAI API is involved; BMP is a control/monitoring-plane feature only.

## 2.2 BMP Object Model

The configuration is decomposed into four CONFIG_DB tables. The model deliberately avoids YANG nested lists (which the SONiC YANG tooling does not handle well) by placing collectors and AFI/SAFI rows into separate tables keyed by the parent target name (leafref):

- **`BMP|global`** — singleton; global settings (currently `mirror-buffer-limit`).
- **`BMP_TARGET`** — one row per target; carries `mirror` and `stats-interval`.
- **`BMP_TARGET_COLLECTOR`** — one row per `(target, ip, port)`; the outgoing BMP session and its `min-retry`, `max-retry`, `source-interface`.
- **`BMP_TARGET_AFI_SAFI`** — one row per `(target, afi_safi_name)`; selects `adj-rib-in-pre`, `adj-rib-in-post`, `loc-rib`.

The `target_name` leaf in the collector and AFI/SAFI tables is a YANG `leafref` to `BMP_TARGET/name`, guaranteeing referential integrity.

## 2.3 BGP/FRR Configuration Mapping

Each row maps directly onto an FRR `bgpd` BMP command inside a `bmp targets <name> … exit` block:

| CONFIG_DB | FRR command |
|-----------|-------------|
| `BMP global:mirror-buffer-limit` | `bmp mirror buffer-limit <bytes>` |
| `BMP_TARGET:<name>` | `bmp targets <name>` … `exit` |
| `BMP_TARGET:stats-interval` | `bmp stats interval <ms>` |
| `BMP_TARGET:mirror = true` | `bmp mirror` |
| `BMP_TARGET_AFI_SAFI:adj-rib-in-pre = true` | `bmp monitor <afi> <safi> pre-policy` |
| `BMP_TARGET_AFI_SAFI:adj-rib-in-post = true` | `bmp monitor <afi> <safi> post-policy` |
| `BMP_TARGET_AFI_SAFI:loc-rib = true` | `bmp monitor <afi> <safi> loc-rib` |
| `BMP_TARGET_COLLECTOR:<ip>,<port>` | `bmp connect <ip> port <port> min-retry <ms> max-retry <ms> [source-interface <if>]` |

The `afi_safi_name` enum maps to FRR's `<afi> <safi>` token pair:

| `afi_safi_name` | FRR tokens |
|-----------------|-----------|
| `ipv4_unicast`   | `ipv4 unicast` |
| `ipv6_unicast`   | `ipv6 unicast` |
| `ipv4_multicast` | `ipv4 multicast` |
| `ipv6_multicast` | `ipv6 multicast` |
| `l2vpn_evpn`     | `l2vpn evpn` |
| `ipv4_vpn`       | `ipv4 vpn` |
| `ipv6_vpn`       | `ipv6 vpn` |

## 2.4 Configuration Rendering (bgpcfgd and frrcfgd)

1. **`bgpcfgd` path** — at container start, `bgpd.main.conf.j2` iterates the four tables and renders the `bmp targets …` blocks into `bgpd.conf`. The `BMP` rendering is guarded by the existing feature gate (`FEATURE['bmp'].state == 'enabled'` or `FEATURE['frr_bmp'].state == 'enabled'`).

2. **`frrcfgd` path** — `frrcfgd` subscribes to `BMP`, `BMP_TARGET`, `BMP_TARGET_COLLECTOR`, and `BMP_TARGET_AFI_SAFI`. On any change, `bmp_handler()` re-reads all four tables, assembles a per-target view (collectors + AFI/SAFI + mirror + stats), and applies the resulting `bmp …` commands via `vtysh`. Target deletion emits `no bmp targets <name>`.

Both paths share the same defaults and the same backward-compatibility behavior described in [2.5](#25-backward-compatibility).

## 2.5 Backward Compatibility

When **no** rows exist in `BMP_TARGET` (and hence no collectors/AFI-SAFI), both rendering paths synthesize the legacy default target, preserving today's on-box behavior:

```
  bmp targets sonic-bmp
  bmp stats interval 1000
  bmp monitor ipv4 unicast pre-policy
  bmp monitor ipv6 unicast pre-policy
  bmp connect 127.0.0.1 port 5000 min-retry 10000 max-retry 15000
  exit
```

As soon as one or more targets are configured, the synthesized default is **not** emitted; the operator is fully in control. To keep on-box telemetry while adding an external collector, the operator simply defines a target with both a `127.0.0.1:5000` collector and the external collector.

## 2.6 Config DB and YANG Schema

### Config DB schema

**`BMP|global`**
```
"BMP": {
    "global": {
        "mirror-buffer-limit": "1000000000"
    }
}
```

**`BMP_TARGET`** — key: `name`
```
"BMP_TARGET": {
    "production": {
        "stats-interval": "2000"
    },
    "troubleshooting": {
        "mirror": "true",
        "stats-interval": "500"
    }
}
```

**`BMP_TARGET_COLLECTOR`** — key: `target_name|ip|port`
```
"BMP_TARGET_COLLECTOR": {
    "production|192.168.1.100|5000": {
        "min-retry": "30000",
        "max-retry": "720000"
    },
    "troubleshooting|10.0.0.1|6000": {
        "min-retry": "20000",
        "max-retry": "600000",
        "source-interface": "Loopback0"
    }
}
```

**`BMP_TARGET_AFI_SAFI`** — key: `target_name|afi_safi_name`
```
"BMP_TARGET_AFI_SAFI": {
    "production|ipv4_unicast": {
        "adj-rib-in-pre": "true"
    },
    "troubleshooting|ipv4_unicast": {
        "adj-rib-in-pre": "true",
        "adj-rib-in-post": "true"
    },
    "troubleshooting|l2vpn_evpn": {
        "loc-rib": "true"
    }
}
```

### YANG model

The model lives in `sonic-bmp.yang`. Key elements:

- `typedef afi-safi-type` — enumeration of the seven supported AFI/SAFI values.
- `container BMP` — adds a `global` container (`mirror-buffer-limit`) alongside the existing `table` container.
- `container BMP_TARGET` → `list BMP_TARGET_LIST` keyed by `name`, with `mirror` (boolean) and `stats-interval` (uint32, ms).
- `container BMP_TARGET_COLLECTOR` → `list BMP_TARGET_COLLECTOR_LIST` keyed by `target_name ip port`, with `min-retry`, `max-retry` (uint32, ms) and `source-interface` (`stypes:interface_name`). `target_name` is a leafref to `BMP_TARGET_LIST/name`; `ip` is `inet:ip-address`; `port` is `inet:port-number`.
- `container BMP_TARGET_AFI_SAFI` → `list BMP_TARGET_AFI_SAFI_LIST` keyed by `target_name afi_safi_name`, with `adj-rib-in-pre`, `adj-rib-in-post`, `loc-rib` (booleans). `target_name` is a leafref; `afi_safi_name` is `afi-safi-type`.

The module declares revisions `2024-03-20` (first revision), `2025-12-24` (collector configuration parameters), and `2026-04-21` (source-interface).

### Rendered FRR configuration

For the CONFIG_DB example above, `bgpd.conf` renders as:

```
!
  bmp mirror buffer-limit 1000000000
!
  bmp targets production
  bmp stats interval 2000
  bmp monitor ipv4 unicast pre-policy
  bmp connect 192.168.1.100 port 5000 min-retry 30000 max-retry 720000
  exit
!
  bmp targets troubleshooting
  bmp stats interval 500
  bmp mirror
  bmp monitor ipv4 unicast pre-policy
  bmp monitor ipv4 unicast post-policy
  bmp monitor l2vpn evpn loc-rib
  bmp connect 10.0.0.1 port 6000 min-retry 20000 max-retry 600000 source-interface Loopback0
  exit
!
```

## 2.7 Information Flow

### Configuration flow (runtime)

```
 Operator        CONFIG_DB         frrcfgd /              bgpd            Collectors
 (config/                          bgpcfgd               (-M bmp)
  gNMI)
   |                 |                  |                   |                  |
   |  set BMP_TARGET |                  |                   |                  |
   |  / _COLLECTOR / |                  |                   |                  |
   |  _AFI_SAFI /    |                  |                   |                  |
   |  BMP|global     |                  |                   |                  |
   |---------------->|                  |                   |                  |
   |                 |  table change    |                   |                  |
   |                 |----------------->|                   |                  |
   |                 |                  | read 4 tables,    |                  |
   |                 |                  | build per-target  |                  |
   |                 |                  | model             |                  |
   |                 |                  |                   |                  |
   |                 |                  | vtysh: bmp targets <name>            |
   |                 |                  |   bmp stats / mirror / monitor       |
   |                 |                  |   bmp connect <ip> port <p> ...      |
   |                 |                  |------------------>|                  |
   |                 |                  |                   | open BMP TCP     |
   |                 |                  |                   | session(s)       |
   |                 |                  |                   |----------------->|
   |                 |                  |                   | Init/Peer-Up,    |
   |                 |                  |                   | Route Monitoring,|
   |                 |                  |                   | Mirror, Stats    |
   |                 |                  |                   |=================>|
```


# 3 CLI

This feature is configured through the new CONFIG_DB tables rather than dedicated config commands. The tables can be populated by editing `config_db.json` followed by `config reload`, by GCU/JSON patch (`config apply-patch`), or via gNMI SET — all validated against `sonic-bmp.yang`.

A minimal `config_db.json` snippet enabling one on-box and one external collector for the same target:

```
"BMP_TARGET": {
    "default": {
        "stats-interval": "1000"
    }
},
"BMP_TARGET_AFI_SAFI": {
    "default|ipv4_unicast": { "adj-rib-in-pre": "true" },
    "default|ipv6_unicast": { "adj-rib-in-pre": "true" }
},
"BMP_TARGET_COLLECTOR": {
    "default|127.0.0.1|5000":   { "min-retry": "10000", "max-retry": "15000" },
    "default|192.0.2.10|5000":  { "min-retry": "30000", "max-retry": "720000", "source-interface": "Loopback0" }
}
```

Operational visibility of the collected data continues to use the existing commands (unchanged):

```
1. Command: `show bmp bgp-neighbor-table`
2. Command: `show bmp bgp-rib-out-table`
3. Command: `show bmp bgp-rib-in-table`
4. Command: `show bmp tables`
```

Dedicated `config bmp collector …` / `show bmp collectors` click commands for ergonomic editing and display of the new tables are a possible follow-up but are not required by this design.


# 4 Resource usage and Test plan

### Resource usage

This feature adds no new daemon or container and stores only a small amount of configuration in CONFIG_DB. The BMP stream itself is produced by `bgpd` (as today); configuring additional external collectors causes `bgpd` to maintain one additional TCP session and BMP encoder per collector. CPU/memory impact is proportional to the number of configured collectors and the volume of monitored routes (Adj-RIB-In pre/post and Loc-RIB), and is governed by FRR's BMP implementation. The global `mirror-buffer-limit` bounds the memory FRR uses for buffered mirroring messages across all targets.

### Test plan

#### Unit test

Template-rendering unit tests (`sonic-config-engine/tests/test_frr.py`, validated against golden files `bgpd_frr_bmp_single_target.conf` / `bgpd_frr_bmp_multiple_targets.conf`):

1. No BMP config → legacy default `sonic-bmp` target rendered (backward compatibility).
2. Single target with one collector and AFI/SAFI selection renders the expected `bmp targets`/`connect`/`monitor` block.
3. Multiple targets, including `mirror`, multiple AFI/SAFI views, custom retry timers, and `source-interface`, render correctly.
4. Global `mirror-buffer-limit` rendered from `BMP|global`; default applied when absent.

Runtime handler unit tests (`sonic-frr-mgmt-framework/tests/test_config.py`):

5. `bmp_handler` assembles the per-target model from the four tables and issues the correct `vtysh` commands.
6. Target deletion issues `no bmp targets <name>`.
7. Backward-compatibility default applied when all tables are empty.

YANG validation:

8. Positive/negative samples for each table, including leafref integrity (collector/AFI-SAFI must reference an existing target), range checks on retry/stats/buffer values, and the `afi-safi-type` enum. A `sample_config_db.json` row is added so the YANG wheel build's 1:1 model/sample check passes.

#### System test

1. Configure an external collector and verify the device establishes a BMP session and that the collector receives the selected Adj-RIB-In/Loc-RIB and mirroring data; verify retry behavior and `source-interface` selection.
2. Verify the default on-box `openbmpd` → `BMP_STATE_DB` → telemetry path is unaffected when no targets are configured and when a `127.0.0.1:5000` collector is configured alongside an external one.
