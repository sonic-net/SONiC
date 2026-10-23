# Protocol Route-Map Support in SONiC

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions / Abbreviations](#3-definitions--abbreviations)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
   - 7.1 [YANG Schema](#71-yang-schema)
   - 7.2 [Boot-time Rendering (Jinja Template)](#72-boot-time-rendering-jinja-template)
   - 7.3 [Runtime Apply — frrcfgd](#73-runtime-apply--frrcfgd)
   - 7.4 [FRR Zebra Route-Map Evaluation](#74-frr-zebra-route-map-evaluation)
8. [CLI](#8-cli)
   - 8.1 [CONFIG_DB Example](#81-config_db-example)
   - 8.2 [Rendered FRR CLI](#82-rendered-frr-cli)
9. [Information Flow Diagrams](#9-information-flow-diagrams)
   - 9.1 [Apply Flow](#91-apply-flow)
   - 9.2 [Remove Flow](#92-remove-flow)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
11. [Test Plan](#11-test-plan)
    - 11.1 [Unit Tests](#111-unit-tests)
    - 11.2 [sonic-mgmt Tests](#112-sonic-mgmt-tests)

---

## 1. Revision

| Rev | Date       | Author         | Description     |
|-----|------------|----------------|-----------------|
| 0.1 | 2026-05-15 | Kalash Nainwal | Initial version |
| 0.2 | 2026-07-28 | Kalash Nainwal | Scope to frrcfgd only per HLD review |

---

## 2. Scope

This document describes the High-Level Design of **Protocol Route-Map** for SONiC: a CONFIG_DB-driven mechanism to attach a route-map to zebra's install path per (VRF, address-family, source-protocol), so an operator can select which routes from a given routing protocol are allowed to be installed into the forwarding plane.

The feature is backed by FRR's native `ip|ipv6 protocol <PROTO> route-map <NAME>` zebra route filtering — the CLI keeps the FRR name. SONiC adds:

- A YANG model and CONFIG_DB table (`PROTOCOL_ROUTE_MAP`).
- A boot-time render path (Jinja template included from `frr.conf.j2`).
- A runtime mutation path via `frrcfgd` — new `protocol_route_map_handler`, routed via `mgmtd`.

This document scopes the SONiC integration to the `frrcfgd` (unified FRR config) path. The underlying FRR feature itself is documented at <https://docs.frrouting.org/en/stable/zebra.html#zebra-route-filtering>.

---

## 3. Definitions / Abbreviations

| Term         | Definition |
|--------------|------------|
| FIB          | Forwarding Information Base — the dataplane route table actually programmed into hardware |
| RIB          | Routing Information Base — control-plane route table held by zebra/bgpd/staticd/etc. |
| AFI          | Address Family Identifier (IPv4 / IPv6) |
| VRF          | Virtual Routing and Forwarding instance |
| FRR          | FRRouting suite |
| `frrcfgd`    | SONiC FRR Configuration Daemon — translates CONFIG_DB rows to FRR commands via `mgmtd` |
| `mgmtd`      | FRR's management front-end daemon (target of `DEFPY_YANG` commands) |
| Route-map    | FRR mechanism for matching and acting on routes; used here in deny-mode to reject install |
| Prefix-list  | FRR mechanism for matching IP prefixes by length range; commonly referenced from a route-map's `match` clause |

---

## 4. Overview

SONiC already has YANG and CONFIG_DB coverage for route-maps, prefix-lists, community sets, and BGP-side redistribution policies. What was missing is a knob that says **"limit which routes from this routing protocol get programmed into the forwarding plane / hardware"** — i.e., a CONFIG_DB-driven binding for FRR's `ip|ipv6 protocol <PROTO> route-map <NAME>`.

Without this feature, the only way to configure that binding is to hand-edit `frr.conf` — which is not survivable across `config_reload`, not declarative, and not visible through the standard SONiC configuration plane.

Protocol Route-Map closes that gap with:

1. A new YANG module `sonic-protocol-route-map` that defines a CONFIG_DB table keyed `vrf_name | addr_family | protocol`, with a mandatory `route_map` leafref into the existing `ROUTE_MAP_SET`.
2. A Jinja2 template (`zebra.protocol_route_map.conf.j2`) included from the `frrcfgd` frr config (`frr.conf.j2`), so the binding survives `config_reload` and warmboot.
3. Runtime translation in `frrcfgd`: a `sonic-db-cli HSET PROTOCOL_ROUTE_MAP|... route_map RM` takes effect immediately, without a reload. `protocol_route_map_handler` in `frrcfgd.py` picks up the SET / DELETE event and pushes the matching FRR command via `vtysh`, routed via `mgmtd` since `ip|ipv6 protocol … route-map …` is implemented as a `DEFPY_YANG` command on the FRR side.

The operator-facing model is a single CONFIG_DB row per binding.

### Operator use case

The primary use case is reducing pressure on hardware route-table capacity by selectively excluding routes from a given source protocol — for example, dropping BGP-learned routes that match a deny prefix-list while leaving the control plane untouched. The denied routes remain in zebra's RIB and are still advertised to BGP peers; only the dataplane-install side is filtered.

A second common use case, made possible by the accompanying `set_src` route-map action, is stamping BGP-installed FIB entries with a specific source address (`Loopback0`) — the same behavior SONiC has historically provided via a hardcoded `RM_SET_SRC` route-map, now expressible via CONFIG_DB.

---

## 5. Requirements

1. The configuration model SHALL be a CONFIG_DB table keyed by `(vrf_name, addr_family, protocol)`, with a mandatory `route_map` field.
2. The `route_map` field SHALL be a leafref into the existing `ROUTE_MAP_SET`; the referenced route-map must exist.
3. The `vrf_name` field SHALL accept the literal `default` for the global routing table, or a leafref into the `VRF` table for a named VRF.
4. The feature SHALL apply CONFIG_DB changes at runtime, without `config_reload`, via `frrcfgd`.
5. Boot-time rendering SHALL group multiple rows belonging to the same non-default VRF into a single `vrf <N> / ... / exit-vrf` block.
6. Deletion of a CONFIG_DB row SHALL remove the corresponding `ip|ipv6 protocol <PROTO> [route-map …]` binding from FRR at runtime.
7. The feature MUST NOT alter BGP/OSPF/etc. control-plane state — only the install side into zebra's FIB is affected.

---

## 6. Architecture Design

```
              ┌─────────────────────────────────────────────────────────────┐
              │                       CONFIG_DB                             │
              │                                                             │
              │   PROTOCOL_ROUTE_MAP|<vrf>|<afi>|<protocol> → route_map=<RM>│
              └────────────┬────────────────────────────┬───────────────────┘
                           │ runtime SET/DEL            │ boot / config_reload
              ┌────────────┴────────────┐         ┌─────┴─────────────────┐
              │ frrcfgd:                │         │ Jinja2 template       │
              │   .protocol_route_map_  │         │   zebra.protocol_     │
              │     handler             │         │     route_map.conf.j2 │
              │   → routed via mgmtd    │         │                       │
              │                         │         │ included from:        │
              │                         │         │   frr.conf.j2         │
              └────────────┬────────────┘         └─────┬─────────────────┘
                           │ vtysh                      │ on FRR startup
                           ▼                            ▼
              ┌──────────────────────────────────────────────────────────┐
              │                  FRR (zebra)                             │
              │                                                          │
              │   ip   protocol <P> route-map <RM>                       │
              │   ipv6 protocol <P> route-map <RM>                       │
              │                                                          │
              │   • zebra_route_map_check_inbound() invoked from         │
              │     nexthop_active_check() at RIB install time           │
              │   • RMAP_DENYMATCH → NEXTHOP_FLAG_ACTIVE cleared →       │
              │     route stays in RIB but is never marked INSTALLED →   │
              │     rib_install_kernel() short-circuited                 │
              │   • Result: route absent from kernel FIB, fpmsyncd /     │
              │     orchagent / ASIC_DB never see it                     │
              └──────────────────────────────────────────────────────────┘
```

### Key components added

| Component | Repository / file | Purpose |
|---|---|---|
| YANG module | `sonic-yang-models/yang-models/sonic-protocol-route-map.yang` (new) | Schema for the `PROTOCOL_ROUTE_MAP` table. |
| Route-map schema addition | `sonic-yang-models/yang-models/sonic-route-map.yang` (edit) | New `set_src` leaf on `ROUTE_MAP_SET_LIST` so a route-map can carry a `set src <addr>` clause via CONFIG_DB (feature parity with the traditional `RM_SET_SRC` behavior). |
| Boot-render template | `dockers/docker-fpm-frr/frr/zebra/zebra.protocol_route_map.conf.j2` (new) | Walks the `PROTOCOL_ROUTE_MAP` CONFIG_DB table and emits `ip\|ipv6 protocol <PROTO> route-map <NAME>` grouped by VRF. |
| frr.conf include | `sonic-frr-mgmt-framework/templates/frr/frr.conf.j2` (edit) | Pulls the template above into the `frrcfgd`-owned frr config. |
| Route-map template render | `sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.route_map.j2` (edit) | Emit `set src <addr>` in the route-map body when `set_src` is populated. |
| Runtime handler | `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (edit) | `protocol_route_map_handler` + `'PROTOCOL_ROUTE_MAP': ['mgmtd']` in `TABLE_DAEMON`; plus `set_src` entry in the route-map key map for runtime `set src <addr>` rendering. |

---

## 7. High-Level Design

### 7.1 YANG Schema

New module `sonic-protocol-route-map.yang`:

```yang
module sonic-protocol-route-map {
    namespace "http://github.com/sonic-net/sonic-protocol-route-map";
    prefix sprm;
    yang-version 1.1;

    import sonic-vrf       { prefix vrf; }
    import sonic-route-map { prefix rmap; }
    import sonic-types     { prefix stypes; }

    revision 2026-04-20 { description "Initial revision."; }

    typedef protocol-route-map-protocol {
        type enumeration {
            enum any;
            enum bgp;
            enum connected;
            enum eigrp;
            enum isis;
            enum kernel;
            enum nhrp;
            enum ospf;
            enum ospf6;
            enum rip;
            enum ripng;
            enum sharp;
            enum static;
            enum table;
        }
    }

    container sonic-protocol-route-map {
        container PROTOCOL_ROUTE_MAP {
            list PROTOCOL_ROUTE_MAP_LIST {
                key "vrf_name addr_family protocol";

                // AFI / protocol compatibility (matches what FRR accepts).
                must "not(addr_family = 'IPv4' and (protocol = 'ospf6' or protocol = 'ripng')) and "
                   + "not(addr_family = 'IPv6' and (protocol = 'ospf'  or protocol = 'rip' "
                   +                            "or protocol = 'eigrp'))" {
                    error-message "protocol is not valid for the selected addr_family";
                }

                leaf vrf_name {
                    type union {
                        type string  { pattern "default"; }
                        type leafref { path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name"; }
                    }
                }

                leaf addr_family { type stypes:ip-family; }      // IPv4 | IPv6
                leaf protocol    { type protocol-route-map-protocol; }

                leaf route_map {
                    type leafref {
                        path "/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/"
                           + "rmap:ROUTE_MAP_SET_LIST/rmap:name";
                    }
                    mandatory true;
                }
            }
        }
    }
}
```

Additive edit to `sonic-route-map.yang`: a new `set_src` leaf on `ROUTE_MAP_SET_LIST` so an operator can define a route-map that stamps FIB installs with a specific source address (the classic `RM_SET_SRC` behavior, now expressible via CONFIG_DB):

```yang
leaf set_src {
    type inet:ip-address;
    description
        "Set the source IP address (IPv4 or IPv6) that zebra uses when
         installing matched routes into the kernel FIB. The address must
         be locally configured on the device (typically a Loopback0
         address). Renders to FRR's route-map 'set src <addr>' clause.";
}
```

`inet:ip-address` is already imported by `sonic-route-map.yang`, so no new imports are required.

### 7.2 Boot-time Rendering (Jinja Template)

A new template `dockers/docker-fpm-frr/frr/zebra/zebra.protocol_route_map.conf.j2` walks the `PROTOCOL_ROUTE_MAP` CONFIG_DB table and emits FRR CLI:

```jinja
{# Render the PROTOCOL_ROUTE_MAP CONFIG_DB table as zebra's
       ip|ipv6 protocol <PROTO> route-map <NAME>
   wrapped in a 'vrf <N> / ... / exit-vrf' block for non-default VRFs.
   Key format from CONFIG_DB: "<vrf>|<addr_family>|<protocol>".
   Jinja may present the key as either a 'pipe|joined' string or a
   tuple, so we normalize both. Entries are grouped by VRF so each
   non-default VRF renders as a single 'vrf <N> / ... / exit-vrf'
   block regardless of how many entries it carries. #}
{% set ip_str = {'IPv4': 'ip', 'IPv6': 'ipv6'} %}
{% if PROTOCOL_ROUTE_MAP is defined and PROTOCOL_ROUTE_MAP|length > 0 %}
{% set ns = namespace(by_vrf={}) %}
{% for prm_key, prm_val in PROTOCOL_ROUTE_MAP.items() %}
{%   if prm_key is string %}
{%     set parts = prm_key.split('|') %}
{%   elif prm_key is iterable %}
{%     set parts = prm_key %}
{%   else %}
{%     set parts = [] %}
{%   endif %}
{%   if parts|length == 3 and prm_val is mapping and 'route_map' in prm_val %}
{%     set prm_ip_kw = ip_str.get(parts[1]) %}
{%     if prm_ip_kw is not none %}
{%       set _ = ns.by_vrf.setdefault(parts[0], []).append((prm_ip_kw, parts[2], prm_val['route_map'])) %}
{%     endif %}
{%   endif %}
{% endfor %}
{% for vrf, entries in ns.by_vrf.items() %}
{%   if vrf == 'default' %}
{%     for ip_kw, proto, rm in entries %}
{{ ip_kw }} protocol {{ proto }} route-map {{ rm }}
{%     endfor %}
!
{%   else %}
vrf {{ vrf }}
{%     for ip_kw, proto, rm in entries %}
 {{ ip_kw }} protocol {{ proto }} route-map {{ rm }}
{%     endfor %}
exit-vrf
!
{%   endif %}
{% endfor %}
{% endif %}
```

This template is included from `src/sonic-frr-mgmt-framework/templates/frr/frr.conf.j2` so `config_reload` and warm reboot reproduce the same zebra config from CONFIG_DB.

`bgpd.conf.db.route_map.j2` (existing template rendering the body of each route-map) is extended to emit `set src <addr>` when the row carries a `set_src` field.

VRF grouping is two-pass: the first pass buckets valid rows into a per-VRF list; the second pass emits one block per VRF.

### 7.3 Runtime Apply — frrcfgd

`frrcfgd` subscribes to CONFIG_DB and translates rows into mgmtd / vtysh commands. Runtime apply is provided by `protocol_route_map_handler` registered against the `PROTOCOL_ROUTE_MAP` table:

```python
class BgpdClientMgr(threading.Thread):
    TABLE_DAEMON = {
        ...
        'PROTOCOL_ROUTE_MAP': ['mgmtd']
    }
```

```python
class BGPConfigDaemon:
    def __init__(self, ...):
        ...
        ('PROTOCOL_ROUTE_MAP', self.protocol_route_map_handler),
        ...

    def protocol_route_map_handler(self, table, key, data):
        """Translate PROTOCOL_ROUTE_MAP rows to zebra commands.

        CONFIG_DB key: "<vrf>|<addr_family>|<protocol>". Emits:
            [vrf <vrf>]
             ip|ipv6 protocol <protocol> route-map <route_map>
            [exit-vrf]
        """
```

The handler is registered against `'mgmtd'` in `TABLE_DAEMON`, not `'zebra'`. The FRR `ip|ipv6 protocol <P> route-map <RM>` command is a `DEFPY_YANG`, which mgmtd's northbound owns; targeting `['zebra']` directly returns "Unknown command."

A per-key state cache (`self.protocol_route_map_state`) is populated from the initial CONFIG_DB table on startup. It lets DELETE emit the matching `no ip|ipv6 protocol <PROTO> route-map <NAME>` using the last-applied name (the CONFIG_DB row is already gone by the time the handler runs), and lets idempotent re-sets short-circuit. State is only advanced AFTER the vtysh command succeeds, so a transient failure leaves the cache in sync with FRR and the next event retries cleanly.

The `frrcfgd` route-map key map is extended with a `set_src` entry so a runtime SET on `ROUTE_MAP` carrying a `set_src` field emits `set src <addr>` inside the route-map body. This mirrors the template-side change and makes the `set src` action available through both the boot and runtime paths.

### 7.4 FRR Zebra Route-Map Evaluation

When `ip protocol bgp route-map <RM>` is configured, zebra invokes `zebra_route_map_check_inbound()` from inside `nexthop_active_check()` for each BGP-protocol route the RIB processes. The check evaluates `<RM>` against the route's attributes. On `RMAP_DENYMATCH`:

```c
// zebra/zebra_nhg.c (paraphrased)
ret = zebra_route_map_check(family, re, p, nexthop, zvrf);
if (ret == RMAP_DENYMATCH) {
    UNSET_FLAG(nexthop->flags, NEXTHOP_FLAG_ACTIVE);
}
```

With no active nexthops, `rib_process()` does not mark the entry `ROUTE_ENTRY_INSTALLED`, `rib_install_kernel()` is short-circuited, and the route never reaches the kernel FIB. The downstream effect:

- The route stays in zebra's RIB (`show ip route <prefix>` still shows a `protocol: bgp` entry).
- FRR's `installed` JSON field is omitted (the `ROUTE_ENTRY_INSTALLED` flag was never set; `zebra_vty.c` only emits the key when set).
- fpmsyncd never sees the install, `APPL_DB ROUTE_TABLE` is not populated for the prefix, and orchagent does not program it into `ASIC_DB`. Hardware never carries the route.

Importantly, BGP / OSPF / etc. control-plane state is unaffected — the route is still advertised to peers; only the dataplane-install side is filtered.

For `set src <addr>` (the `set_src` action), zebra applies the source-address stamp on the accepted route as part of the same route-map evaluation, so an installed route carries the operator-configured source IP.

---

## 8. CLI

This feature is configured through the new CONFIG_DB table rather than dedicated config commands. The table can be populated by editing config_db.json followed by config reload, or by GCU/JSON patch (config apply-patch).

### 8.1 CONFIG_DB Example

```text
CONFIG_DB:

{
    "PROTOCOL_ROUTE_MAP": {
        "default|IPv4|bgp":    { "route_map": "RM_FROM_BGP" },
        "default|IPv6|ospf6":  { "route_map": "RM_FROM_OSPF6" },
        "Vrf_red|IPv4|static": { "route_map": "RM_STATIC_V4" },
        "Vrf_red|IPv4|bgp":    { "route_map": "RM_BGP_RED" }
    }
}
```

Using the new `set_src` route-map action to reproduce the `RM_SET_SRC` behavior:

```json
{
    "ROUTE_MAP": {
        "RM_FROM_BGP|10": { "route_operation": "permit", "set_src": "10.1.0.1" }
    },
    "PROTOCOL_ROUTE_MAP": {
        "default|IPv4|bgp": { "route_map": "RM_FROM_BGP" }
    }
}
```

### 8.2 Rendered FRR CLI

```text
ip protocol bgp route-map RM_FROM_BGP
ipv6 protocol ospf6 route-map RM_FROM_OSPF6
!
vrf Vrf_red
 ip protocol static route-map RM_STATIC_V4
 ip protocol bgp route-map RM_BGP_RED
exit-vrf
!
```

---

## 9. Information Flow Diagrams

### 9.1 Apply Flow

```
  Operator                CONFIG_DB           frrcfgd                FRR (zebra)
     │                       │                  │                       │
     │ sonic-db-cli HSET     │                  │                       │
     │ PROTOCOL_ROUTE_MAP|.. ►                  │                       │
     │     route_map RM      │ SET event ──────►│                       │
     │                       │                  │ vtysh (via mgmtd):    │
     │                       │                  │   [vrf <V>]           │
     │                       │                  │   ip protocol P       │
     │                       │                  │   route-map RM        │
     │                       │                  │   [exit-vrf]        ──►
     │                       │                  │                       │ re-evaluate
     │                       │                  │                       │ existing RIB
     │                       │                  │                       │ entries of P;
     │                       │                  │                       │ uninstall deny
     │                       │                  │                       │ matches from FIB
```

### 9.2 Remove Flow

```
  Operator                CONFIG_DB           frrcfgd                FRR (zebra)
     │ sonic-db-cli DEL      │                  │                       │
     │ PROTOCOL_ROUTE_MAP|.. ►                  │                       │
     │                       │ DEL event ──────►│                       │
     │                       │                  │ vtysh (via mgmtd):    │
     │                       │                  │   [vrf <V>]           │
     │                       │                  │   no ip protocol P   ──►
     │                       │                  │   [exit-vrf]          │
     │                       │                  │                       │ previously denied
     │                       │                  │                       │ entries re-eval;
     │                       │                  │                       │ now eligible to
     │                       │                  │                       │ install into FIB
```

---

## 10. Warmboot and Fastboot Design Impact

The feature relies on the same code path that already handles `route-map`, `prefix-list`, and the other CONFIG_DB-driven FRR config: the Jinja template is rendered into `frr.conf` on boot, and FRR re-reads its config on startup. There is no extra warmboot state to preserve — the CONFIG_DB row IS the persisted state, and re-rendering after FRR comes back up reproduces the same `ip|ipv6 protocol … route-map …` binding.

---

## 11. Test Plan

### 11.1 Unit Tests

Unit tests live alongside each touched component and cover:

- **YANG model.** Positive load of valid `PROTOCOL_ROUTE_MAP` rows (default and named VRF, multiple AFI/protocol combinations); negative cases for leafref violations against `ROUTE_MAP_SET` / `VRF_LIST`, out-of-enum protocol values, the mandatory `route_map` constraint, and every AFI/protocol incompatibility enforced by the `must` expression. Positive test for a `ROUTE_MAP` row carrying `set_src`, and a negative test for a non-IP `set_src` value.
- **`frrcfgd`.** For `protocol_route_map_handler`: exact `vtysh` command shape for SET and DELETE in default and non-default VRFs across both AFIs; idempotent re-set short-circuiting; upsert when the same key is re-bound to a different route-map; rejection of malformed CONFIG_DB keys, unsupported AFIs, and rows missing `route_map`; per-key state tracking so deleting one row leaves siblings intact; events routed via `mgmtd` (not `zebra`) per `TABLE_DAEMON`; the per-key state cache advanced only when the underlying vtysh invocation succeeds so transient failures stay retryable. For `set_src`: the route-map render emits `set src <addr>` exactly when the field is present.

### 11.2 sonic-mgmt Tests

A system test runs end-to-end on a real DUT and covers two scenarios:

1. **Selective drop on BGP routes.** Pick a handful of BGP-learned IPv4 prefixes currently present in ASIC_DB, build a route-map that denies just those prefixes, and apply a `PROTOCOL_ROUTE_MAP|default|IPv4|bgp` row. Verify the denied prefixes leave ASIC_DB while still appearing in the BGP RIB (`show ip bgp <prefix>`) and in zebra's RIB without the `installed` marker — the three-layer fingerprint that distinguishes this feature from table-map / redistribute / BGP-side filters. Remove the binding and verify the prefixes return to ASIC_DB.
2. **Per-protocol scope.** With a single route-map whose prefix-list covers both BGP-learned and statically injected prefixes, bind the map for `static` only and verify only the static prefixes drop from ASIC_DB while BGP routes are untouched; then bind the same map for `bgp` only and verify the inverse. This pins the `(afi, protocol)` scoping of the CONFIG_DB key.
