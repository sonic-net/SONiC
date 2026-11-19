# IPv6 Neighbor Discovery Router Advertisement (ND RA) Parameters

## High Level Design Document

### Rev 0.1

## Table of Contents

* [Revision](#revision)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitionsabbreviations)
* [Overview](#overview)
* [Requirements](#requirements)
* [Architecture Design](#architecture-design)
* [High-Level Design](#high-level-design)
  * [Affected Repositories](#affected-repositories)
  * [Config DB Schema](#config-db-schema)
  * [YANG Model Changes](#yang-model-changes)
  * [FRR / zebra Integration](#frr--zebra-integration)
* [SAI API](#sai-api)
* [CLI / User Interface](#cli--user-interface)
  * [Config Commands](#config-commands)
  * [Show Commands](#show-commands)
* [Warm Boot / Fast Reboot Support](#warm-boot--fast-reboot-support)
* [Restrictions/Limitations](#restrictionslimitations)
* [Testing Requirements/Design](#testing-requirementsdesign)
* [Open/Action items](#openaction-items)

## Revision

| Rev |     Date    |       Author       | Change Description                                      |
|:---:|:-----------:|:------------------:|----------------------------------------------------------|
| 0.1 | 2026-10-14  |   Aakash Tiwari    | Initial version                                         |

## Scope

This document describes the high level design for configuring IPv6 Neighbor
Discovery (ND) Router Advertisement (RA) parameters in SONiC on a
per-interface and per-prefix basis.

Per-interface RA parameters:

* **`nd_reachable_time`** – reachable time (milliseconds) advertised for
  neighbor entries.
* **`nd_managed_config_flag`** – Managed Address Configuration flag (M-bit);
  addresses are available via DHCPv6.
* **`nd_other_config_flag`** – Other Configuration flag (O-bit); other
  configuration (e.g. DNS) is available via DHCPv6.
* **`nd_ra_interval`** / **`nd_ra_interval_msec`** – RA transmission interval
  in seconds or milliseconds (mutually exclusive).
* **`nd_ra_lifetime`** – router lifetime advertised in RAs (0 = non-default
  gateway).
* **`nd_ra_hop_limit`** – current hop limit advertised in RAs.
* **`nd_ra_retrans_interval`** – neighbor solicitation retransmit interval.
* **`nd_router_preference`** – default router preference (`high`/`medium`/`low`).
* **`nd_mtu`** – MTU option advertised in RAs.
* **`nd_adv_interval_option`** – include the Advertisement Interval option in RAs.
* **`nd_ra_fast_retrans`** – enable/disable fast RA retransmission (FRR default
  is enabled).
* **`nd_suppress_ra`** – suppress RA transmission on the interface (defaults
  to `true`, matching FRR).

Per-prefix RA attributes live in dedicated `*_ND_PREFIX` tables, keyed by
interface and IPv6 prefix and independent of interface address assignment:

* **`nd_prefix_no_advertise`** – do not advertise this prefix in RAs.
* **`nd_prefix_valid_lifetime`** – valid lifetime (seconds).
* **`nd_prefix_preferred_lifetime`** – preferred lifetime (seconds); must not
  exceed `nd_prefix_valid_lifetime`.
* **`nd_prefix_router_address`** – set the Router Address flag.
* **`nd_prefix_off_link`** – do not use the prefix for on-link determination.
* **`disable_autoconfiguration`** – do not use the prefix for SLAAC.

Supported interface types:

* `INTERFACE` (routed physical/Ethernet)
* `PORTCHANNEL_INTERFACE` (routed PortChannel)
* `VLAN_INTERFACE` (SVI)

Loopback interfaces are out of scope.

## Definitions/Abbreviations

| Term    | Meaning                                                    |
|---------|------------------------------------------------------------|
| ND      | Neighbor Discovery (RFC 4861)                              |
| RA      | Router Advertisement                                       |
| PIO     | Prefix Information Option                                  |
| M-bit   | Managed Address Configuration flag                         |
| O-bit   | Other Configuration flag                                   |
| SVI     | Switched Virtual Interface (VLAN interface)                |
| FRR     | Free Range Routing                                         |
| frrcfgd | FRR Config Daemon (SONiC FRR management framework)         |
| GCU     | Generic Config Updater                                     |

## Overview

IPv6 hosts rely on Router Advertisements to learn default gateways, on-link
prefixes, and configuration policy (stateless vs. stateful/DHCPv6). In SONiC,
RAs for routed interfaces are originated by **FRR/zebra** using `ipv6 nd ...`
interface commands.

This feature adds per-interface RA scalars and per-prefix advertisement
on Ethernet, PortChannel, and VLAN interfaces. An RA prefix is an independent
object (matching FRR/zebra) rather than a property of an assigned interface
address.

## Requirements

* Configure the full set of per-interface RA parameters listed in [Scope](#scope)
  on `INTERFACE`, `PORTCHANNEL_INTERFACE`, and `VLAN_INTERFACE`.
* Configure per-prefix advertisement attributes independently of interface
  address assignment, including keys-only rows that advertise a prefix with
  FRR defaults.
* Support `nd_prefix_no_advertise` so a prefix can be present without emitting
  a PIO in RAs.
* Validate ranges, mutual exclusion of `nd_ra_interval` /
  `nd_ra_interval_msec`, `nd_ra_lifetime` vs. the effective interval, and
  no-advertise vs. other prefix flags in YANG.
* Program FRR at runtime (`frrcfgd` / `vtysh`) and restore the same state from
  CONFIG_DB when the BGP container starts (zebra templates).
* Default `nd_suppress_ra` to `true`. RAs are not transmitted unless it is
  set to `false`.

## Architecture Design

There is no change to the overall SONiC architecture. New leaves are added to
existing CONFIG_DB interface tables, three dedicated per-prefix tables are
introduced, and `frrcfgd` in the `bgp` container consumes those tables and
programs FRR.

```
                 +----------------------------+
   config CLI    |         CONFIG_DB          |
  (config intf   |  INTERFACE / PORTCHANNEL_  |
   ipv6 nd ...)  |  INTERFACE / VLAN_INTERFACE|  <- per-interface scalars
        +------->|                            |
                 |  INTERFACE_ND_PREFIX       |
                 |  PORTCHANNEL_INTERFACE_    |
                 |  ND_PREFIX                 |  <- per-prefix RA attributes
                 |  VLAN_INTERFACE_ND_PREFIX  |
                 +-------------+--------------+
                               |
                               v
                 +----------------------+
                 |  bgp container       |
                 |  frrcfgd + zebra     |
                 |  templates           |
                 |  -> FRR              |
                 |  "ipv6 nd ..."       |
                 +----------------------+
```

## High-Level Design

### Affected Repositories

| Repository | Change |
|------------|--------|
| `sonic-yang-models` | ND scalar leaves on the three interface lists; `INTERFACE_ND_PREFIX`, `PORTCHANNEL_INTERFACE_ND_PREFIX`, and `VLAN_INTERFACE_ND_PREFIX` |
| `sonic-frr-mgmt-framework` | `frrcfgd` handlers for scalars and prefixes; VLAN zebra template |
| `sonic-buildimage` | `zebra.interfaces.conf.j2` for Ethernet and PortChannel |
| `sonic-utilities` | `config interface ipv6 nd ...` and `show ipv6 nd ...` |

### Config DB Schema

New fields on the interface-name keyed rows of `INTERFACE`,
`PORTCHANNEL_INTERFACE`, and `VLAN_INTERFACE`. Address rows
(`<if>|<ip-prefix>`) are ignored for ND scalars.

```
; INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE

nd_reachable_time       = 1*7DIGIT              ; 1..3600000, milliseconds. Absent = FRR default.
nd_managed_config_flag  = "true" / "false"
nd_other_config_flag    = "true" / "false"
nd_ra_interval          = 1*4DIGIT              ; 1..1800, seconds. Mutually exclusive with nd_ra_interval_msec.
nd_ra_interval_msec     = 2*7DIGIT              ; 70..1800000, milliseconds. Mutually exclusive with nd_ra_interval.
nd_ra_lifetime          = 1*4DIGIT              ; 0..9000, seconds (0 = non-default gateway)
nd_ra_hop_limit         = 1*3DIGIT              ; 0..255
nd_ra_retrans_interval  = 1*10DIGIT             ; 0..4294967295, milliseconds
nd_router_preference    = "high" / "medium" / "low"
nd_mtu                  = 1*5DIGIT              ; 1..65535
nd_adv_interval_option  = "true" / "false"
nd_ra_fast_retrans      = "true" / "false"      ; FRR default is enabled
nd_suppress_ra          = "true" / "false"      ; default "true"
```

Boolean fields also accept the aliases `on`/`enabled`/`1` and
`off`/`disabled`/`0` (case-insensitive) on the ConfigDB / `frrcfgd` path.

Per-prefix attributes live in tables keyed by `<if>|<ipv6-prefix>`, decoupled
from interface address assignment:

* `INTERFACE_ND_PREFIX|<if>|<ipv6-prefix>`
* `PORTCHANNEL_INTERFACE_ND_PREFIX|<if>|<ipv6-prefix>`
* `VLAN_INTERFACE_ND_PREFIX|<if>|<ipv6-prefix>`

```
; INTERFACE_ND_PREFIX|<if>|<ipv6-prefix> (and PORTCHANNEL / VLAN equivalents)

nd_prefix_no_advertise        = "true" / "false"
nd_prefix_valid_lifetime      = 1*10DIGIT  ; seconds
nd_prefix_preferred_lifetime  = 1*10DIGIT  ; seconds, must be <= nd_prefix_valid_lifetime
nd_prefix_router_address      = "true" / "false"
nd_prefix_off_link            = "true" / "false"
disable_autoconfiguration     = "true" / "false"
```

A keys-only row (interface + prefix, no optional attributes) is valid and
means "advertise this prefix with FRR defaults". Optional attributes only
change how it is advertised. `nd_prefix_no_advertise = true` is mutually
exclusive with the lifetime and flag attributes on the same prefix.

Host addresses in the prefix key (for example `2001:db8:1::1/64`) are
normalized to the covering network (`2001:db8:1::/64`) before they are
programmed into FRR.

Example:

```json
{
    "INTERFACE": {
        "Ethernet0": {
            "nd_reachable_time": "30000",
            "nd_managed_config_flag": "true",
            "nd_other_config_flag": "false",
            "nd_ra_interval": "200",
            "nd_suppress_ra": "false"
        }
    },
    "INTERFACE_ND_PREFIX": {
        "Ethernet0|2001:db8:1::/64": {},
        "Ethernet0|2001:db8:2::/64": {
            "nd_prefix_no_advertise": "true"
        }
    }
}
```

`Ethernet0|2001:db8:1::/64` with an empty hash is a keys-only advertise. The
PortChannel and VLAN prefix tables use the same key and optional leaves.

### YANG Model Changes

YANG is the validation source of truth used by GCU. The Config DB fields above
are added to:

* `sonic-interface.yang` — `INTERFACE_LIST` and new `INTERFACE_ND_PREFIX_LIST`
* `sonic-portchannel.yang` — `PORTCHANNEL_INTERFACE_LIST` and new
  `PORTCHANNEL_INTERFACE_ND_PREFIX_LIST`
* `sonic-vlan.yang` — `VLAN_INTERFACE_LIST` and new
  `VLAN_INTERFACE_ND_PREFIX_LIST`

Each prefix list is keyed by `name ip-prefix`. `ip-prefix` is
`sonic-ip6-prefix` (IPv6 only), so IPv4 prefixes are rejected by type rather
than a `must`. `name` must refer to an existing interface-list entry.

Notable constraints (full leaf text lives in the YANG modules, not duplicated
here):

| Constraint | Rule |
|------------|------|
| RA interval | `nd_ra_interval` and `nd_ra_interval_msec` are mutually exclusive |
| RA lifetime | 0, or ≥ `nd_ra_interval`, or ≥ `nd_ra_interval_msec / 1000`, or ≥ 600 s when neither interval is set |
| Reachable time | `1..3600000` ms; `0` is not accepted |
| No-advertise | cannot be combined with valid/preferred lifetime or router-address / off-link / no-autoconfig |
| Preferred lifetime | requires `nd_prefix_valid_lifetime` and must not exceed it |

### FRR / zebra Integration

Two paths keep FRR in sync with CONFIG_DB:

1. **Runtime** — `frrcfgd` subscribes to the three interface tables and the
   three `*_ND_PREFIX` tables and issues `ipv6 nd` commands over `vtysh`.
   Only the interface-name key is handled on the scalar tables; address rows
   are skipped.
2. **Startup / config reload** — the same fields are rendered into zebra
   templates (`dockers/docker-fpm-frr/frr/zebra/zebra.interfaces.conf.j2` for
   Ethernet and PortChannel,
   `src/sonic-frr-mgmt-framework/templates/zebra/zebra.vlan.conf.j2` for
   VLAN) so the container restores ND state on boot.

An ND interface stanza is emitted only when at least one scalar is set, a
prefix row exists, or `nd_suppress_ra` is present. When a stanza is emitted,
`ipv6 nd suppress-ra` or `no ipv6 nd suppress-ra` is always written
(default suppress).

#### Per-interface command mapping

| CONFIG_DB field | FRR command |
|-----------------|-------------|
| `nd_suppress_ra=true` (default) | `ipv6 nd suppress-ra` |
| `nd_suppress_ra=false` | `no ipv6 nd suppress-ra` |
| `nd_reachable_time` | `ipv6 nd reachable-time <ms>` |
| `nd_managed_config_flag=true` | `ipv6 nd managed-config-flag` |
| `nd_other_config_flag=true` | `ipv6 nd other-config-flag` |
| `nd_ra_interval` | `ipv6 nd ra-interval <sec>` |
| `nd_ra_interval_msec` | `ipv6 nd ra-interval msec <ms>` |
| `nd_ra_lifetime` | `ipv6 nd ra-lifetime <sec>` |
| `nd_ra_hop_limit` | `ipv6 nd ra-hop-limit <n>` |
| `nd_ra_retrans_interval` | `ipv6 nd ra-retrans-interval <ms>` |
| `nd_router_preference` | `ipv6 nd router-preference <high\|medium\|low>` |
| `nd_mtu` | `ipv6 nd mtu <mtu>` |
| `nd_adv_interval_option=true` | `ipv6 nd adv-interval-option` |
| `nd_ra_fast_retrans=false` | `no ipv6 nd ra-fast-retrans` |
| delete `nd_ra_fast_retrans` | `ipv6 nd ra-fast-retrans` (restore FRR default) |
| delete `nd_suppress_ra` | `ipv6 nd suppress-ra` (restore default) |
| delete interval field | `no ipv6 nd ra-interval` |

`nd_ra_interval` and `nd_ra_interval_msec` program FRR's single
`ra-interval`. Switching from seconds to msec (or the reverse) SETs the new
form only; `frrcfgd` does not send `no ipv6 nd ra-interval` first. If both
fields are present (YANG should have rejected this), `frrcfgd` logs an error
and uses seconds.

#### Per-prefix command mapping

Prefix flags are combined into one FRR command, not separate lines:

| CONFIG_DB | FRR |
|-----------|-----|
| keys-only row | `ipv6 nd prefix <network>` |
| `nd_prefix_no_advertise=true` | `ipv6 nd prefix <network> no-advertise` |
| valid / preferred lifetimes | `ipv6 nd prefix <network> <valid> <preferred>` |
| `nd_prefix_router_address=true` | append `router-address` |
| `nd_prefix_off_link=true` | append `off-link` |
| `disable_autoconfiguration=true` | append `no-autoconfig` |
| row deleted | `no ipv6 nd prefix <network>` |

If only `nd_prefix_valid_lifetime` is set, preferred is programmed as the
same value. Removing the last optional attribute leaves a keys-only row,
which stays programmed with FRR defaults; it does **not** unconfigure the
prefix. IPv4 and invalid IPv6 keys are skipped.

Example composite command:

```
ipv6 nd prefix 2001:db8:a::/64 3600 1800 router-address off-link no-autoconfig
```

## SAI API

No SAI changes are required. RAs are handled entirely in the control plane
(FRR/zebra); no ASIC programming is involved.

## CLI / User Interface

### Config Commands

A new `nd` sub-group is added under `config interface ipv6`. ND is allowed
only on routed Ethernet, PortChannel, and VLAN interfaces (not subinterfaces,
VLAN members, PortChannel members, or ports in access/trunk mode).

```
config interface ipv6 nd reachable-time           <interface_name> [<reachable_time>]
config interface ipv6 nd managed-config-flag       <interface_name> [<enable|disable>]
config interface ipv6 nd other-config-flag         <interface_name> [<enable|disable>]
config interface ipv6 nd ra-interval               <interface_name> [<interval>]
config interface ipv6 nd ra-interval-msec          <interface_name> [<interval_msec>]
config interface ipv6 nd ra-lifetime               <interface_name> [<lifetime>]
config interface ipv6 nd ra-hop-limit              <interface_name> [<hop_limit>]
config interface ipv6 nd ra-retrans-interval       <interface_name> [<retrans_interval>]
config interface ipv6 nd ra-router-preference      <interface_name> [<high|medium|low>]
config interface ipv6 nd ra-mtu                    <interface_name> [<mtu>]
config interface ipv6 nd ra-adv-interval-option    <interface_name> [<enable|disable>]
config interface ipv6 nd ra-fast-retrans           <interface_name> [<enable|disable>]
config interface ipv6 nd suppress-ra               <interface_name> [<enable|disable>]
config interface ipv6 nd prefix add                <interface_name> <ipv6_prefix>
                                                    [--no-advertise]
                                                    [--valid-lifetime <seconds>]
                                                    [--preferred-lifetime <seconds>]
                                                    [--router-address | --no-router-address]
                                                    [--off-link | --on-link]
                                                    [--no-autoconfig | --autoconfig]
config interface ipv6 nd prefix del                <interface_name> <ipv6_prefix>
```

Omitting the optional value on a scalar command clears the CONFIG_DB field
(revert to FRR default). Configuring `ra-interval` clears `ra-interval-msec`
and the reverse. `prefix add` with no options writes a keys-only row.
`--no-advertise` cannot be combined with the other prefix options. The
inverse prefix flags (`--no-router-address`, `--on-link`, `--autoconfig`)
clear the corresponding field.

Example:

```
admin@sonic:~$ sudo config interface ipv6 nd reachable-time Ethernet0 30000
admin@sonic:~$ sudo config interface ipv6 nd managed-config-flag Ethernet0 enable
admin@sonic:~$ sudo config interface ipv6 nd other-config-flag Vlan100 disable
admin@sonic:~$ sudo config interface ipv6 nd ra-interval Ethernet0 200
admin@sonic:~$ sudo config interface ipv6 nd suppress-ra Ethernet0 disable
admin@sonic:~$ sudo config interface ipv6 nd prefix add Ethernet0 2001:db8:1::/64
admin@sonic:~$ sudo config interface ipv6 nd prefix add Ethernet0 2001:db8:2::/64 --no-advertise
admin@sonic:~$ sudo config interface ipv6 nd prefix del Ethernet0 2001:db8:2::/64
```

### Show Commands

`show ipv6 nd interfaces [<interface_name>]` lists per-interface ND RA
scalars. Omit the interface to show every interface that has ND fields
configured. `nd_ra_interval` and `nd_ra_interval_msec` are mutually
exclusive, so only one interval column is populated:

```
admin@sonic:~$ show ipv6 nd interfaces Vlan1000
Interface      Reachable Time (ms)    RA Interval (s)    RA Interval (ms)    RA Lifetime (s)    RA Hop Limit    Retrans Interval (ms)  Router Preference      MTU  Managed Flag    Other Flag    Adv Interval Option    Fast Retrans    Suppress RA
-----------  ---------------------  -----------------  ------------------  -----------------  --------------  -----------------------  -------------------  -----  --------------  ------------  ---------------------  --------------  -------------
Vlan1000                     30000                600                                     1800              64                     1000  high                  1500  true            true          true                   false           false
```

`show ipv6 nd prefix [<interface_name>]` lists advertised prefixes,
including keys-only rows. Omit the interface to show prefixes on all
interfaces:

```
admin@sonic:~$ show ipv6 nd prefix Vlan1000
Interface    Prefix           No Advertise    Valid Lifetime (s)    Preferred Lifetime (s)    Router Address    Off-Link    No Autoconfig
-----------  ---------------  --------------  --------------------  ------------------------  ----------------  ----------  ---------------
Vlan1000     2001:db8:1::/64                  3600                  1800                      true              true        true
Vlan1000     2001:db8:2::/64  true
```

## Warm Boot / Fast Reboot Support

The parameters are CONFIG_DB fields consumed at container start and by
`frrcfgd`. No special warm-boot handling is required; the configuration is
restored from CONFIG_DB and re-applied to FRR after reboot.

## Restrictions/Limitations

* CONFIG_DB/YANG accept reachable time `1..3600000` ms, matching FRR's
  `ipv6 nd reachable-time` range. `0` is not accepted. To restore FRR's
  default, remove `nd_reachable_time`.
* `nd_ra_interval` and `nd_ra_interval_msec` are mutually exclusive.
* `nd_suppress_ra` defaults to `true`. **It must be set to `false` for RAs
  to be transmitted.** Other `nd_*` / `nd_prefix_*` settings have no on-wire
  effect while suppression is enabled.
* Per-prefix `nd_prefix_*` leaves and `disable_autoconfiguration` are
  IPv6-only and mutually exclusive with `nd_prefix_no_advertise = true`.
  These prefixes are independent of interface address assignment.
* `nd_prefix_preferred_lifetime` requires `nd_prefix_valid_lifetime` and
  must not exceed it.
* Parameters take effect only when IPv6 is operational on the interface.
* Loopback interfaces are not supported.
* Runtime programming through `frrcfgd` requires the FRR management framework
  (`DEVICE_METADATA.localhost.frr_mgmt_framework_config` set to `true`).
  Without it, ND settings are applied from the zebra templates when the BGP
  container starts or reloads.

## Testing Requirements/Design

### Unit tests

* `sonic-frr-mgmt-framework` unit tests cover `frrcfgd` programming of ND
  scalars and prefixes on Ethernet, PortChannel, and VLAN interfaces.
* `sonic-yang-models` tests cover valid and invalid RA scalar and prefix
  configuration on those interface types.

### System tests

Separate SONiC management tests will be added to cover this feature.

## Open/Action items

* None.
