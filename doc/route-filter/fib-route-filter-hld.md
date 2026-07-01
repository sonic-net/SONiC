# FIB Route Filtering Support in SONiC

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions / Abbreviations](#3-definitions--abbreviations)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
   - 7.1 [YANG Schema](#71-yang-schema)
   - 7.2 [CONFIG_DB Schema](#72-config_db-schema)
   - 7.3 [Boot-time Rendering (Jinja Templates)](#73-boot-time-rendering-jinja-templates)
   - 7.4 [Runtime Apply — bgpcfgd](#74-runtime-apply--bgpcfgd)
   - 7.5 [Runtime Apply — frrcfgd](#75-runtime-apply--frrcfgd)
   - 7.6 [FRR Zebra Route-Map Evaluation](#76-frr-zebra-route-map-evaluation)
8. [Configuration and Management](#8-configuration-and-management)
   - 8.1 [CONFIG_DB / `sonic-db-cli` Examples](#81-config_db--sonic-db-cli-examples)
   - 8.2 [Rendered FRR CLI](#82-rendered-frr-cli)
9. [Information Flow Diagrams](#9-information-flow-diagrams)
   - 9.1 [Apply Filter Flow](#91-apply-filter-flow)
   - 9.2 [Remove Filter Flow](#92-remove-filter-flow)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions / Limitations](#12-restrictions--limitations)
13. [Test Plan](#13-test-plan)
    - 13.1 [Unit Tests](#131-unit-tests)
    - 13.2 [sonic-mgmt Tests](#132-sonic-mgmt-tests)

---

## 1. Revision

| Rev | Date       | Author         | Description     |
|-----|------------|----------------|-----------------|
| 0.1 | 2026-05-15 | Kalash Nainwal | Initial version |

---

## 2. Scope

This document describes the High-Level Design of **FIB Route Filter** for SONiC: a CONFIG_DB-driven mechanism to select, per (VRF, address-family, source-protocol), which routes from a given routing protocol are allowed to be installed into the forwarding plane.

The feature is backed by FRR's native `ip|ipv6 protocol <PROTO> route-map <NAME>` zebra route filtering. SONiC adds:

- A YANG model and CONFIG_DB table (`FIB_ROUTE_FILTER`).
- A boot-time render path (Jinja template included from `zebra.conf.j2` / `frr.conf.j2`).
- A runtime mutation path in **both** SONiC CONFIG_DB → FRR translators:
  - `bgpcfgd` — new `FibRouteFilterMgr`.
  - `frrcfgd` — new `fib_route_filter_handler`, routed via `mgmtd`.

This document covers the SONiC plumbing only. The underlying FRR feature itself is documented at <https://docs.frrouting.org/en/stable/zebra.html#zebra-route-filtering>.

---

## 3. Definitions / Abbreviations

| Term         | Definition |
|--------------|------------|
| FIB          | Forwarding Information Base — the dataplane route table actually programmed into hardware |
| RIB          | Routing Information Base — control-plane route table held by zebra/bgpd/staticd/etc. |
| AFI          | Address Family Identifier (IPv4 / IPv6) |
| VRF          | Virtual Routing and Forwarding instance |
| FRR          | FRRouting suite |
| `bgpcfgd`    | SONiC BGP Configuration Daemon — translates CONFIG_DB rows directly to `vtysh` commands |
| `frrcfgd`    | SONiC FRR Configuration Daemon — translates CONFIG_DB rows to FRR commands via `mgmtd` |
| `mgmtd`      | FRR's management front-end daemon (target of `DEFPY_YANG` commands) |
| Route-map    | FRR mechanism for matching and acting on routes; used here in deny-mode to reject install |
| Prefix-list  | FRR mechanism for matching IP prefixes by length range; commonly referenced from a route-map's `match` clause |

---

## 4. Overview

SONiC already has YANG and CONFIG_DB coverage for route-maps, prefix-lists, community sets, and BGP-side redistribution policies. What was missing is a knob that says **"limit which routes from this routing protocol get programmed into the forwarding plane / hardware"** — i.e., a CONFIG_DB-driven binding for FRR's `ip|ipv6 protocol <PROTO> route-map <NAME>`.

Without this feature, the only way to configure that binding is to hand-edit `zebra.conf` (when `bgpcfgd` owns FRR config) or `frr.conf` (when `frrcfgd` owns FRR config) — which is not survivable across `config_reload`, not declarative, and not visible through the standard SONiC configuration plane.

FIB Route Filter closes that gap with:

1. A new YANG module `sonic-fib-route-filter` that defines a CONFIG_DB table keyed `vrf_name | addr_family | protocol`, with a mandatory `route_map` leafref into the existing `ROUTE_MAP_SET`.
2. A Jinja2 template (`zebra.fib_route_filter.conf.j2`) included from both the `bgpcfgd` zebra config (`zebra.conf.j2`) and the `frrcfgd` frr config (`frr.conf.j2`), so the binding survives `config_reload` and warmboot.
3. Runtime translation so a `sonic-db-cli HSET FIB_ROUTE_FILTER|... route_map RM` takes effect immediately, without a reload, in both translators:
   - **`bgpcfgd`** (`docker_routing_config_mode=split`): `FibRouteFilterMgr` subscribes to the CONFIG_DB table and emits the corresponding FRR command via `vtysh`.
   - **`frrcfgd`** (`frr_mgmt_framework_config=true`): `fib_route_filter_handler` does the same, routed via `mgmtd` since `ip|ipv6 protocol … route-map …` is implemented as a `DEFPY_YANG` command on the FRR side.

The operator-facing model is unchanged whichever translator the DUT runs — a single CONFIG_DB row applies the filter.

### Operator use case

The primary use case is reducing pressure on hardware route-table capacity by selectively excluding routes from a given source protocol — for example, dropping BGP-learned routes that match a deny prefix-list while leaving the control plane untouched. The denied routes remain in zebra's RIB and are still advertised to BGP peers; only the dataplane-install side is filtered.

---

## 5. Requirements

1. The configuration model SHALL be a CONFIG_DB table keyed by `(vrf_name, addr_family, protocol)`, with a mandatory `route_map` field.
2. The `route_map` field SHALL be a leafref into the existing `ROUTE_MAP_SET`; the referenced route-map must exist.
3. The `vrf_name` field SHALL accept the literal `default` for the global routing table, or a leafref into the `VRF` table for a named VRF.
4. The feature SHALL apply CONFIG_DB changes at runtime, without `config_reload`, via both `bgpcfgd` and `frrcfgd`.
5. Boot-time rendering SHALL group multiple filter rows belonging to the same non-default VRF into a single `vrf <N> / ... / exit-vrf` block.
6. Deletion of a CONFIG_DB row SHALL remove the corresponding `ip|ipv6 protocol <PROTO> [route-map …]` binding from FRR at runtime.
7. The feature MUST NOT alter BGP/OSPF/etc. control-plane state — only the install side into zebra's FIB is affected.

---

## 6. Architecture Design

```
              ┌─────────────────────────────────────────────────────────────┐
              │                       CONFIG_DB                             │
              │                                                             │
              │   FIB_ROUTE_FILTER|<vrf>|<afi>|<protocol> → route_map=<RM>  │
              └────────────┬────────────────────────────┬───────────────────┘
                           │ runtime SET/DEL            │ boot / config_reload
              ┌────────────┴────────────┐         ┌─────┴─────────────────┐
              │ bgpcfgd:                │         │ Jinja2 template       │
              │   .FibRouteFilterMgr    │         │   zebra.fib_route_    │
              │   → vtysh               │         │     filter.conf.j2    │
              │                         │         │                       │
              │ frrcfgd:                │         │ included from:        │
              │   .fib_route_filter_    │         │   zebra.conf.j2       │
              │     handler             │         │     (bgpcfgd path)    │
              │   → routed via mgmtd    │         │   frr.conf.j2         │
              │                         │         │     (frrcfgd path)    │
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
| YANG module | `sonic-yang-models/yang-models/sonic-fib-route-filter.yang` (new) | Schema for the `FIB_ROUTE_FILTER` table. |
| Boot-render template | `dockers/docker-fpm-frr/frr/zebra/zebra.fib_route_filter.conf.j2` (new) | Shared template that walks the CONFIG_DB table and emits FRR CLI. |
| zebra.conf include | `dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2` (edit) | Pull the shared template into the `bgpcfgd`-owned zebra config. |
| frr.conf include | `sonic-frr-mgmt-framework/templates/frr/frr.conf.j2` (edit) | Pull the same shared template into the `frrcfgd`-owned frr config. |
| Runtime translator — `bgpcfgd` | `sonic-bgpcfgd/bgpcfgd/managers_fib_route_filter.py` (new) | `FibRouteFilterMgr` — subscribes to CONFIG_DB `FIB_ROUTE_FILTER`, pushes vtysh on SET / DEL. |
| Runtime translator — `frrcfgd` | `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (edit) | `fib_route_filter_handler` + `'FIB_ROUTE_FILTER': ['mgmtd']` in `TABLE_DAEMON`. |

---

## 7. High-Level Design

### 7.1 YANG Schema

```yang
module sonic-fib-route-filter {
    namespace "http://github.com/sonic-net/sonic-fib-route-filter";
    prefix frfilter;
    yang-version 1.1;

    import sonic-vrf       { prefix vrf; }
    import sonic-route-map { prefix rmap; }
    import sonic-types     { prefix stypes; }

    revision 2026-04-20 { description "Initial revision."; }

    typedef fib-route-filter-protocol {
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

    container sonic-fib-route-filter {
        container FIB_ROUTE_FILTER {
            list FIB_ROUTE_FILTER_LIST {
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
                leaf protocol    { type fib-route-filter-protocol; }

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

### 7.2 Boot-time Rendering (Jinja Templates)

A new shared template `dockers/docker-fpm-frr/frr/zebra/zebra.fib_route_filter.conf.j2` walks the `FIB_ROUTE_FILTER` CONFIG_DB table and emits FRR CLI:

```jinja
{# Render the FIB_ROUTE_FILTER CONFIG_DB table as zebra's
       ip|ipv6 protocol <PROTO> route-map <NAME>
   wrapped in a 'vrf <N> / ... / exit-vrf' block for non-default VRFs.
   Key format from CONFIG_DB: "<vrf>|<addr_family>|<protocol>".
   Shared between the bgpcfgd zebra.conf.j2 and the frrcfgd
   frr.conf.j2; Jinja may present the key as either a
   'pipe|joined' string or a tuple, so we normalize both.
   Entries are grouped by VRF so each non-default VRF renders as a
   single 'vrf <N> / ... / exit-vrf' block regardless of how many
   filters it carries. #}
{% set ip_str = {'IPv4': 'ip', 'IPv6': 'ipv6'} %}
{% if FIB_ROUTE_FILTER is defined and FIB_ROUTE_FILTER|length > 0 %}
{% set ns = namespace(by_vrf={}) %}
{% for frf_key, frf_val in FIB_ROUTE_FILTER.items() %}
{%   if frf_key is string %}
{%     set parts = frf_key.split('|') %}
{%   elif frf_key is iterable %}
{%     set parts = frf_key %}
{%   else %}
{%     set parts = [] %}
{%   endif %}
{%   if parts|length == 3 and frf_val is mapping and 'route_map' in frf_val %}
{%     set frf_ip_kw = ip_str.get(parts[1]) %}
{%     if frf_ip_kw is not none %}
{%       set _ = ns.by_vrf.setdefault(parts[0], []).append((frf_ip_kw, parts[2], frf_val['route_map'])) %}
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

This template is included from two places, so a single rendering layer covers both `bgpcfgd` and `frrcfgd` at boot / config_reload:

- `dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2` (`bgpcfgd`-owned)
- `src/sonic-frr-mgmt-framework/templates/frr/frr.conf.j2` (`frrcfgd`-owned)

VRF grouping is two-pass: the first pass buckets valid rows into a per-VRF list; the second pass emits one block per VRF.

### 7.3 Runtime Apply — bgpcfgd

When `bgpcfgd` owns FRR config translation, the boot template alone is not enough — operators expect `sonic-db-cli HSET FIB_ROUTE_FILTER|...` to take effect immediately, without `config_reload`. This is provided by `FibRouteFilterMgr`, a new `bgpcfgd` manager registered in `main.py` alongside the existing route-policy managers.

```python
class FibRouteFilterMgr(Manager):
    """Runtime handler for FIB_ROUTE_FILTER in CONFIG_DB.

    set:    ip|ipv6 protocol <proto> route-map <name>          (default VRF)
            vrf <name> / ip|ipv6 protocol <proto> route-map <name> / exit-vrf
                                                                (named VRF)
    del:    no ip|ipv6 protocol <proto>                         (default VRF)
            vrf <name> / no ip|ipv6 protocol <proto> / exit-vrf (named VRF)
    """
```

### 7.4 Runtime Apply — frrcfgd

When `frrcfgd` is the active CONFIG_DB → FRR translator (in place of `bgpcfgd`), it subscribes to CONFIG_DB and translates rows into mgmtd / vtysh commands. The same runtime apply is provided by `fib_route_filter_handler` registered against the `FIB_ROUTE_FILTER` table:

```python
class BgpdClientMgr(threading.Thread):
    TABLE_DAEMON = {
        ...
        'FIB_ROUTE_FILTER': ['mgmtd']
    }
```

```python
class BGPConfigDaemon:
    def __init__(self, ...):
        ...
        ('FIB_ROUTE_FILTER', self.fib_route_filter_handler),
        ...

    def fib_route_filter_handler(self, table, key, data):
        """Translate FIB_ROUTE_FILTER rows to zebra commands.

        CONFIG_DB key: "<vrf>|<addr_family>|<protocol>". Emits:
            [vrf <vrf>]
             ip|ipv6 protocol <protocol> route-map <route_map>
            [exit-vrf]
        """
```

### 7.5 FRR Zebra Route-Map Evaluation

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

---

## 8. CLI

This feature is configured through the new CONFIG_DB tables rather than dedicated config commands. The tables can be populated by editing config_db.json followed by config reload, by GCU/JSON patch (config apply-patch).

### 8.1 CONFIG_DB Example

```text
CONFIG_DB:

{
    "FIB_ROUTE_FILTER": {
        "default|IPv4|bgp":    { "route_map": "RM_FROM_BGP" },
        "default|IPv6|ospf6":  { "route_map": "RM_FROM_OSPF6" },
        "Vrf_red|IPv4|static": { "route_map": "RM_STATIC_V4" },
        "Vrf_red|IPv4|bgp":    { "route_map": "RM_BGP_RED" }
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

### 9.1 Apply Filter Flow

```
  Operator                CONFIG_DB        runtime manager           FRR (zebra)
     │                       │                  │                       │
     │ sonic-db-cli HSET     │                  │                       │
     │ FIB_ROUTE_FILTER|... ─►                  │                       │
     │     route_map RM      │ SET event ──────►│                       │
     │                       │                  │ vtysh:                │
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

The runtime manager is `bgpcfgd.FibRouteFilterMgr` when `bgpcfgd` owns FRR config translation, and `frrcfgd.fib_route_filter_handler` (routed through `mgmtd`) when `frrcfgd` is the active translator.

### 9.2 Remove Filter Flow

```
  Operator                CONFIG_DB        runtime manager           FRR (zebra)
     │ sonic-db-cli DEL      │                  │                       │
     │ FIB_ROUTE_FILTER|... ─►                  │                       │
     │                       │ DEL event ──────►│                       │
     │                       │                  │ vtysh:                │
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

The feature relies on the same code path that already handles `route-map`, `prefix-list`, and the other CONFIG_DB-driven FRR config: the Jinja template is rendered into `zebra.conf` / `frr.conf` on boot, and FRR re-reads its config on startup. There is no extra warmboot state to preserve — the CONFIG_DB row IS the persisted state, and re-rendering after FRR comes back up reproduces the same `ip|ipv6 protocol … route-map …` binding.

---

## 11. Test Plan

### 11.1 Unit Tests

Unit tests live alongside each touched component and cover:

- **YANG model.** Positive load of valid rows (default and named VRF, multiple AFI/protocol combinations); negative cases for leafref violations against `ROUTE_MAP_SET` / `VRF_LIST`, out-of-enum protocol values, the mandatory `route_map` constraint, and every AFI/protocol incompatibility enforced by the `must` expression.
- **`bgpcfgd` (`FibRouteFilterMgr`).** Exact `vtysh` command shape for SET and DELETE in default and non-default VRFs across both AFIs; idempotent re-set short-circuiting; upsert when the same key is re-bound to a different route-map; rejection of malformed CONFIG_DB keys, unsupported AFIs, and rows missing `route_map`; per-key state tracking so deleting one row leaves siblings intact; full set→del→re-set lifecycle.
- **`frrcfgd` (`fib_route_filter_handler`).** Same set/del/idempotency/upsert/rejection surface as above, plus that events are routed via `mgmtd` (not `zebra`) per `TABLE_DAEMON`, and that the per-key state cache is only advanced when the underlying vtysh invocation succeeds so transient failures stay retryable.
- **`sonic-config-engine` template rendering.** Render the boot Jinja against a fixture covering the default VRF, a non-default VRF, and multiple rows under the same VRF; byte-compare against a committed sample to lock the emitted `ip|ipv6 protocol … route-map …` shape and the `vrf … / exit-vrf` grouping.

### 11.2 sonic-mgmt Tests

A system test runs end-to-end on a real DUT and covers two scenarios:

1. **Selective drop on BGP routes.** Pick a handful of BGP-learned IPv4 prefixes currently present in ASIC_DB, build a route-map that denies just those prefixes, and apply a `FIB_ROUTE_FILTER|default|IPv4|bgp` row. Verify the denied prefixes leave ASIC_DB while still appearing in the BGP RIB (`show ip bgp <prefix>`) and in zebra's RIB without the `installed` marker — the three-layer fingerprint that distinguishes this feature from table-map / redistribute / BGP-side filters. Remove the binding and verify the prefixes return to ASIC_DB.
2. **Per-protocol scope.** With a single route-map whose prefix-list covers both BGP-learned and statically injected prefixes, bind the filter for `static` only and verify only the static prefixes drop from ASIC_DB while BGP routes are untouched; then bind the same map for `bgp` only and verify the inverse. This pins the `(afi, protocol)` scoping of the CONFIG_DB key.

