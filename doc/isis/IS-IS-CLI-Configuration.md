# IS-IS Protocol Integration HLD

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [Overview](#overview)
- [Requirements](#requirements)
- [High Level Design](#high-level-design)
- [Config DB Enhancement](#config-db-enhancement)
- [CLI Reference](#cli-reference)
  - [Global Configuration](#global-configuration)
  - [Interface Configuration](#interface-configuration)
  - [Operational Commands](#operational-commands)
- [Configuration Example](#configuration-example)
- [Warm reboot, upgrade and restrictions](#warm-reboot-upgrade-and-restrictions)
- [Test plan](#test-plan)
- [References](#references)

### Revision

| Revision | Date        | Author  | Change Description |
| -------- | ----------- | ------- | ------------------ |
| 1.0      | Oct 26 2026 | Unraous | Initial proposal   |
| 1.1      | Nov 5 2026 | Unraous | CR alignment, binding lifecycle and integration test plan |

### Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| IS-IS | Intermediate System to Intermediate System routing protocol |
| ConfigDB | SONiC Redis database used to store persistent configuration |
| VRF | Virtual Routing and Forwarding instance |
| NET | Network Entity Title identifying an IS-IS system and area |
| LSP | Link State PDU |
| FRR | Free Range Routing |

### Scope

This HLD covers built-in IS-IS integration in SONiC: daemon lifecycle, ConfigDB/YANG, dynamic FRR translation, startup rendering, dual-stack routing, passive interfaces, and the northbound CLI. It consolidates the implementation HLD and CLI guide.

### Overview

The IS-IS CLI provides `config isis` commands for process-level configuration and `config interface isis` commands for interface-level configuration. Configuration commands write to ConfigDB. The FRR management framework consumes the IS-IS ConfigDB tables and applies the corresponding configuration to FRR. The `show isis` command group retrieves operational state through FRR's `vtysh` interface.

### Requirements

1. The image must include the IS-IS CLI and FRR management framework. `DEVICE_METADATA|localhost` must set `frr_mgmt_framework_config` to `"true"`, followed by a restart of the affected bgp container. This is disruptive to routing; schedule the restart appropriately. Without this mode the CLI writes ConfigDB but configuration is not applied.
2. IS-IS process configuration is scoped to a VRF. When a VRF argument is omitted, the CLI uses `default`.
3. Interface commands take an existing interface name (or its alias in alias naming mode). PortChannel and VLAN members are rejected; configure the routed aggregate interface instead.
4. The IS-IS process must be enabled before setting its NET, level, dynamic-hostname option, or timers. The VRF must exist before enabling a non-default instance.

### High Level Design

The configuration and show paths are:

```text
config isis / config interface isis
              |
              v
          ConfigDB
              |
              v
           frrcfgd
              |
              v
             FRR

show isis ---> rvtysh (vtysh fallback) ---> FRR operational state
```

Configuration is split between three ConfigDB tables: `ISIS_GLOBALS` for process attributes, `ISIS_GLOBALS_TIMERS` for global LSP timers, and `ISIS_INTERFACE` for interface attributes. The CLI does not generate FRR configuration files directly.

### Config DB Enhancement

| ConfigDB table | Purpose |
| -------------- | ------- |
| `ISIS_GLOBALS` | IS-IS process settings, including NET, level, and dynamic hostname |
| `ISIS_GLOBALS_TIMERS` | LSP MTU, refresh interval, and lifetime |
| `ISIS_INTERFACE` | Per-interface enable state, metric, circuit type, and passive state |

Keys are `ISIS_GLOBALS|<vrf_name>`, `ISIS_GLOBALS_TIMERS|<vrf_name>`, and
`ISIS_INTERFACE|<ifname>`. The timer key references an existing global row. Interface
keys reference PORT, PORTCHANNEL, VLAN_INTERFACE, LOOPBACK_INTERFACE or
VLAN_SUB_INTERFACE entries. Global VRFs reference VRF, except `default`.
ConfigDB stores scalar values as strings; YANG validates the following types.

| Table | Field | YANG type / range | Default |
| --- | --- | --- | --- |
| ISIS_GLOBALS | enabled | boolean | false |
| ISIS_GLOBALS | net_title | string matching `[0-9a-fA-F]{2}(\.[0-9a-fA-F]{4}){3,9}\.00` | absent |
| ISIS_GLOBALS | level | level-1, level-2, level-1-2 | level-1-2 |
| ISIS_GLOBALS | dynamic_hostname | boolean | true |
| ISIS_GLOBALS | ipv6_multi_topology | boolean | true |
| ISIS_GLOBALS_TIMERS | lsp_mtu | uint16, 128–4352 | 1492 |
| ISIS_GLOBALS_TIMERS | lsp_refresh_interval | uint16, 1–65235 seconds | 900 |
| ISIS_GLOBALS_TIMERS | lsp_lifetime | uint16, 350–65535 seconds | 1200 |
| ISIS_INTERFACE | enabled | boolean | false |
| ISIS_INTERFACE | ipv6_enabled | boolean | true |
| ISIS_INTERFACE | metric | uint32, 1–16777215 | 10 |
| ISIS_INTERFACE | circuit_type | p2p, lan | lan |
| ISIS_INTERFACE | passive | boolean | absent (not passive) |

Lifetime must be at least refresh interval + 300 seconds, including when either
field is omitted and its default applies. CLI reset operations enforce this too.

#### FRR translation and lifecycle

- An enabled global row creates `router isis <vrf>` (default VRF) or
  `router isis <vrf> vrf <vrf>` (non-default), even with no other attributes.
  Deletion or `enabled=false` removes that router instance.
- `net_title` maps to `net`; replacement removes the old NET before adding the new
  NET. `level-2` maps to `is-type level-2-only`. Dynamic hostname maps to
  `[no] hostname dynamic`, never the global hostname command.
- `ipv6_multi_topology=true` renders `topology ipv6-unicast`; false removes that
  topology to allow single-topology IPv6 peers. `ipv6_enabled` controls the
  interface's `ipv6 router isis` binding independently. IPv4 bindings remain
  enabled on administratively enabled interfaces. These optional fields are
  configured through ConfigDB; this CLI revision does not add dedicated commands.
- Enabling an interface immediately applies `ip router isis <vrf>` and, by default,
  `ipv6 router isis <vrf>`. The interface VRF comes from its routed interface table.
  Disabled interfaces and interfaces without an enabled global row are not bound.
- `passive=false` sends `no isis passive`. Removing circuit type returns to LAN,
  matching FRR and YANG defaults. Explicit p2p sends `isis network point-to-point`.
- Deleting timers resets LSP MTU, refresh and lifetime. Timer updates preserve the
  lifetime/refresh relationship while issuing commands. A late deletion after
  the global instance is removed does not recreate the instance. Re-enabling a
  process restores retained timer values against the recreated FRR defaults.
- `config isis disable` refuses while any interface rows reference that VRF;
  remove those bindings first. It then removes timers and the global row.
  Interface disable can remove retained disabled/stale rows even after the
  interface is removed or becomes a member port.
- frrcfgd subscribes to base-row changes in INTERFACE, PORTCHANNEL_INTERFACE,
  VLAN_INTERFACE, LOOPBACK_INTERFACE and VLAN_SUB_INTERFACE. It tracks the VRF
  of each successfully applied IS-IS binding, removes old IPv4/IPv6 bindings
  before moving to a new VRF, and ignores address-prefix row events. Removing
  a routed-interface row detaches the binding without rebinding it to default.
  A missing target process leaves the interface unbound; a later global enable
  reconciles the retained interface configuration. Partial command failures keep
  both possible destinations for cleanup on a later event/retry.
- Startup uses the single packaged `isisd.conf.j2` in sonic-frr-mgmt-framework;
  dynamic updates use frrcfgd. Both honor the same enable flags and defaults.

`isisd` runs inside the bgp container after zebra. Its supervisord entry uses the
shared daemon lifecycle policy (KILL stop signal, no independent autorestart).
No new APP_DB, ASIC_DB, STATE_DB or COUNTERS_DB tables are introduced. Routes flow
through the existing FRR/zebra and SONiC route programming pipeline. There are no
new SWSS, syncd or SAI API requirements.

### CLI Reference

Configuration commands require `sudo` or equivalent privilege. On multi-ASIC
systems use `config isis -n NAMESPACE ...` and
`config interface -n NAMESPACE isis ...`; configure the same namespace in both.
`config isis reset FIELD [VRF]` removes net, level, hostname, lsp-mtu, lsp-refresh
or lsp-lifetime. `config interface isis reset INTERFACE FIELD` resets metric,
circuit-type or passive. Removal restores the schema/FRR default; NET has no default.

#### Global Configuration

| Command | Description |
| ------- | ----------- |
| `config isis enable [VRF]` | Enable IS-IS for the specified VRF. The default VRF is `default`. |
| `config isis disable [VRF]` | Disable IS-IS for the specified VRF. |
| `config isis net NET [VRF]` | Set the IS-IS NET for the specified VRF. |
| `config isis level {level-1\|level-2\|level-1-2} [VRF]` | Set the IS-IS level for the specified VRF. |
| `config isis hostname {enable\|disable} [VRF]` | Enable or disable dynamic hostname support for the specified VRF. |
| `config isis timer lsp-mtu MTU [VRF]` | Set the LSP MTU. Valid range: 128–4352. |
| `config isis timer lsp-refresh SECONDS [VRF]` | Set the LSP refresh interval. Valid range: 1–65235 seconds. |
| `config isis timer lsp-lifetime SECONDS [VRF]` | Set the LSP lifetime. Valid range: 350–65535 seconds. |

#### Interface Configuration

| Command | Description |
| ------- | ----------- |
| `config interface isis enable INTERFACE` | Enable IS-IS on an interface. |
| `config interface isis disable INTERFACE` | Disable IS-IS on an interface. |
| `config interface isis metric INTERFACE METRIC` | Set the interface metric. Valid range: 1–16777215. |
| `config interface isis circuit-type INTERFACE {p2p\|lan}` | Set the IS-IS circuit type. |
| `config interface isis passive INTERFACE {enable\|disable}` | Enable or disable passive mode on an interface. |

#### Operational Commands

| Command | Description |
| ------- | ----------- |
| `show isis summary` | Display IS-IS process summary. |
| `show isis neighbor` | Display IS-IS neighbors. |
| `show isis database [detail]` | Display the link-state database. |

`show isis interface` displays interface state and settings.

Each show command accepts `-j` or `--json` for JSON output, and `-n` or `--namespace NAMESPACE` to select an ASIC namespace on a multi-ASIC device.

### Configuration Example

The following example enables IS-IS in the default VRF, configures a NET and Level 2 operation, and enables IS-IS on `Ethernet0` as a point-to-point circuit:

```shell
sudo config isis enable
sudo config isis net 49.0001.0000.0000.0001.00
sudo config isis level level-2
sudo config interface isis enable Ethernet0
sudo config interface isis circuit-type Ethernet0 p2p
sudo config interface isis metric Ethernet0 20
sudo config interface isis enable Loopback0
sudo config interface isis passive Loopback0 enable

show isis summary
show isis neighbor
show isis database
```

### Warm reboot, upgrade and restrictions

Configuration must be saved with the existing `config save` workflow to persist.
Cold startup rebuilds FRR configuration from ConfigDB. This change does not
implement IS-IS graceful restart, warm-reboot state restoration or fastboot route
preservation; these behaviors must not be advertised as supported without
end-to-end validation. An upgrade must install the matching utilities and
buildimage changes. Before downgrading to a schema without IS-IS, disable and
remove the three IS-IS tables from saved configuration.

The feature requires an FRR build containing isisd and the management-framework
mode. No new hardware-specific APIs are required. Adjacency count, LSDB size,
reconvergence time and CPU/memory growth must be measured on the intended platform;
this design does not assert an unmeasured scale limit. No new SNMP, REST or gNMI
bindings are defined by these PRs. Routing show commands and frrcfgd logs provide
operational diagnostics; successful ConfigDB writes alone are not proof of an
installed FRR configuration.

### Test plan

The [IS-IS integration test plan](IS-IS-Test-Plan.md) defines the binding transition
matrix, observations, acceptance criteria and cleanup, including failed moves and
startup/namespace cases.

1. Unit-test frrcfgd enable-only rows, disable/delete, NET replacement, non-default
   VRFs, boolean toggles, timer resets and command failure/cache behavior.
2. Render startup templates with equivalent states and compare their semantic
   defaults and bindings with dynamic updates. Verify the packaged include path.
3. Validate YANG positive and negative cases for NET, ranges, timer relationships,
   VRF and interface references, and the interface enabled field.
4. Exercise CLI aliases, ASIC namespace selection, absent interfaces/VRFs,
   member-port rejection, updates preserving other fields, resets and show errors.
5. In the seven-node topology, verify L1/L2 adjacency, IPv4/IPv6 routes and passive
   loopback reachability. Test MT and single-topology neighbors separately.
6. Repeat using enable-only interfaces, change NET and timers dynamically, disable
   passive, remove fields, save/restart bgp and compare effective configuration.
   Exercise default ↔ VRF and VrfA → VrfB moves, both interface deletion orders,
   delayed target-process enable and partial command failures. Verify no stale
   IPv4/IPv6 bindings remain. Test process removal only after interface cleanup. Record interruption and
   recovery behavior; do not infer warm-reboot support from cold-restart success.

### References

- [IS-IS integration implementation](https://github.com/sonic-net/sonic-buildimage/pull/28789).
- [IS-IS Click CLI implementation](https://github.com/sonic-net/sonic-utilities/pull/4738) implements the commands documented here.
- [Community Force10 7-node topology](https://github.com/sonic-net/sonic-mgmt/blob/master/ansible/vars/topo_force10-7nodes.yml) provides the reusable topology definition for multi-node protocol testing.
