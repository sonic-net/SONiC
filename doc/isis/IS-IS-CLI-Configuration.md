# IS-IS Protocol Integration HLD

- [Revision](#revision)
- [Scope](#scope)
- [Requirements](#requirements)
- [High Level Design](#high-level-design)
- [Config DB Enhancement](#config-db-enhancement)
- [CLI Reference](#cli-reference)
- [Configuration Example](#configuration-example)
- [Warm reboot, upgrade and restrictions](#warm-reboot-upgrade-and-restrictions)
- [Test plan](#test-plan)

### Revision

| Revision | Date | Author | Change Description |
| -------- | ---- | ------ | ------------------ |
| 1.0 | Oct 26 2026 | Unraous | Initial proposal |
| 1.1 | Nov 5 2026 | Unraous | CR alignment, binding lifecycle and integration test plan |
| 1.2 | Nov 10 2026 | Unraous | gs-based increment: named instances, explicit binding, per-level policy and recovery |

### Scope

Built-in SONiC IS-IS northbound configuration over the existing FRR implementation.
The model separates instance, instance/level, circuit, circuit/level and
redistribution policy. Independent AF and MT controls build on gs1571's fixes;
the default LSP MTU remains his corrected 1497. This iteration does not modify
FRR, Zebra, FPM, SWSS or SAI and does not add SRv6 capabilities.

### Requirements

1. Install matching utilities, YANG models and FRR management framework packages.
   Enable `DEVICE_METADATA|localhost.frr_mgmt_framework_config=true` and restart
   the affected bgp container. That restart interrupts routing.
2. An instance is identified by `(vrf, instance)`. Its name maps to FRR `area-tag`.
   Non-default VRFs must already exist. NETs in the same VRF share a system ID.
3. Explicitly bind an existing routed interface to its parent. Alias naming mode
   is supported. PortChannel/VLAN members are rejected; use routed aggregates.
4. Disable retains configuration; delete/unbind removes it; reset removes an
   override. Editing disabled objects is allowed subject to validation.
5. A successful CLI write confirms desired ConfigDB state, not FRR convergence.
   Observe native state and recovery logs separately.

### High Level Design

```text
Click / validated configuration load -> ConfigDB
                                          |
                         +----------------+---------------+
                         |                                |
                  frozen startup snapshot        event/periodic worker
                         |                                |
                  ownership registration          native readback + journal
                         |                                |
                         +------ shared projection -------+
                                          |
                                     existing FRR
show isis -> rvtysh / vtysh -> native operational state
```

The shared `sonic_isis` package in the YANG models wheel defines identities,
defaults and graph validation. Startup and runtime use the same FRR command
builders. Coupled LSP timers use FRR's atomic `lsp-timers` command. Same-VRF
system-ID replacement tears down owned bindings and all old areas before creating
any new area; foreign native objects prevent that operation.

Recovery reuses gs1571's kernel, journal and fail-fast native transport. The
worker uses independent sessions, a two-second wakeup interval and a 30-second
attempt deadline. Confirmation requires fresh native readback; partial execution
is never treated as applied. Owned offline deletions are reconciled after daemon
restart. Unsupported native configuration and unowned conflicts fail closed.
The journal is `/etc/frr/isis-owned.json`, within the bgp container. Startup
registers ownership as `prepared` (no deadline) before exposing the rendered
fragment. On its first recovery step, the worker durably changes this to `pending`
and starts the 30-second deadline before reading desired or native state. Container
initialization before that step consumes no recovery budget; unavailable services
after that step do. Repeated worker/container starts preserve an existing pending
deadline and failed latch for the same digest and boot. `prepared` is not an
applied-state claim. Install the startup renderer and recovery worker from the same
framework revision; older readers reject this new journal phase safely.
If registration fails,
the same frozen snapshot renders other protocols with an empty IS-IS fragment
and logs the failure. Container replacement reconstructs native configuration;
the journal is not a promise of host-persistent forwarding state.

No APP_DB, ASIC_DB, STATE_DB or COUNTERS_DB schema is introduced. isisd runs in the
bgp container after zebra under the existing shared supervisord lifecycle policy.
Package/build details and contributor provenance are in the
[design record](IS-IS-Northbound-Redesign.md#modules-and-build-artifacts).

### Config DB Enhancement

The implemented table names are below. Scalar columns map directly to FRR attributes;
splitting tables follows ownership and key dimensions, not CLI command grouping.

| Table | Key | Fields / purpose |
| -------------- | --- | ---------------- |
| `ISIS_INSTANCE` | `vrf\|instance` | `enabled`, NET list, `level_type`, `dynamic_hostname`, `metric_style`, `lsp_mtu`, `overload`, `overload_on_startup`, `ipv6_multi_topology`; optional complete SPF backoff tuple |
| `ISIS_INSTANCE_LEVEL` | `vrf\|instance\|level` | `lsp_refresh_interval`, `lsp_maximum_lifetime`, `lsp_generation_interval`, `spf_minimum_interval` |
| `ISIS_INTERFACE` | `interface` | Parent `vrf` and `instance`, `enabled`, `ipv4_enabled`, `ipv6_enabled`, `level_type`, `network_type`, `passive` |
| `ISIS_INTERFACE_LEVEL` | `interface\|level` | `metric`, `hello_interval`, `hello_multiplier`; other per-level interface controls only as explicitly scoped |
| `ISIS_REDISTRIBUTE` | `vrf\|instance\|af\|protocol\|level` | Optional `metric`, `route_map`; row presence enables this policy |

There is no replacement catch-all timer table. LSP MTU belongs to the instance;
LSP and minimum-SPF timers belong to the instance/level; hello timers belong to the
interface/level. SPF IETF backoff is an instance-wide tuple in this FRR model.
Redistribution is keyed by AF, source protocol and destination level, not stored
as a single process-wide boolean.

NETs are a bounded list (FRR allows up to three), not separate instances. Schema
encoding must preserve list semantics and reject incompatible system IDs. FRR
shares per-VRF state between areas; different area-tags must not be advertised as
independent system-ID namespaces.

The interface key intentionally permits only one area binding per logical
interface. A VRF/instance composite reference must validate against the parent.
All child tables require referential validation, including configuration loads
that bypass Click. Key strings must reject Redis delimiters and unsafe FRR command
tokens; final length/character restrictions must be checked against existing SONiC
VRF/interface types and pinned FRR area-tag handling.

#### Defaults and level semantics

| Attribute | Effective default / constraint | Source or policy |
| --------- | --------------------------------------- | ---------------- |
| Instance/interface admin state | Disabled until explicitly enabled | Northbound policy |
| Instance/interface level | `level-1-2` | Pinned FRR |
| IPv4 / IPv6 routing | Independently false until enabled | Pinned FRR; deliberate change from current PR's dual-stack defaults |
| Dynamic hostname | true | Pinned FRR |
| Metric style | wide | Pinned FRR; required for MT |
| LSP MTU | 1497; 128..4352 | Pinned FRR, not 1492 |
| LSP refresh / maximum lifetime / generation | 900 / 1200 / 30 seconds, per level | Pinned FRR |
| Minimum SPF interval | 1 second, per level; 1..120 | Pinned FRR |
| IETF SPF backoff | Absent until the complete five-value tuple is supplied; each 0..60000 ms | Pinned FRR presence container |
| Overload / overload on startup | false / 0 seconds; startup 0..86400 | Pinned FRR |
| Interface metric | 10 per level | Pinned FRR |
| Hello interval / multiplier | 3 seconds / 10 per level | Pinned FRR |
| Network type / passive | broadcast / false | Pinned FRR; platform/interface applicability still validated |

Validate LSP lifetime >= refresh + 300 and generation < refresh using effective
values, including absent fields. Validate all five backoff values together and
the RFC 8405 hold-down/time-to-learn relationship. The pinned FRR scheduler uses
IETF backoff when configured; otherwise it uses the per-level minimum interval.
Minimum-interval values remain configured while backoff is active and apply again
after backoff reset. The northbound does not invent an exclusivity restriction or
separate per-level backoff tuples.

`both` is a CLI convenience that writes concrete Level-1 and Level-2 values.
There is no persisted inherited `both` value. Resetting Level-1 deletes only its
override; it does not copy Level-2. Validate the complete proposed operation before
writing either row. The CLI captures the relevant graph with one Redis Lua evaluation, validates the
candidate, then compares and commits all affected rows atomically in another
evaluation. A concurrent graph change rejects the operation for retry. Runtime
uses an independent atomic snapshot, rather than reconstructing transactions from
individual keyspace notifications.


#### Field ranges

| Table | Field | Valid values |
| ----- | ----- | ------------ |
| ISIS_INSTANCE | net_titles | Up to three unique NETs; same system ID within one VRF; zero NSEL |
| ISIS_INSTANCE | spf_init_delay, spf_short_delay, spf_long_delay, spf_hold_down, spf_time_to_learn | All five together, each 0–60000 ms; hold-down > time-to-learn |
| ISIS_INSTANCE_LEVEL | lsp_refresh_interval | 1–65235 seconds |
| ISIS_INSTANCE_LEVEL | lsp_maximum_lifetime | 350–65535 seconds; at least refresh + 300 |
| ISIS_INSTANCE_LEVEL | lsp_generation_interval | 1–120 seconds; less than refresh |
| ISIS_INTERFACE_LEVEL | metric | 0–16777215 |
| ISIS_INTERFACE_LEVEL | hello_interval | 1–600 seconds |
| ISIS_INTERFACE_LEVEL | hello_multiplier | 2–100 |
| ISIS_REDISTRIBUTE | metric | 0–16777215; default 0 |
| ISIS_REDISTRIBUTE | route_map | Optional existing ROUTE_MAP_SET name |

Instance names and safe command identifiers use 1–64 characters from letters,
digits, underscore, dot and hyphen; the first character is a letter, digit or
underscore. Existing routed-interface and VRF constraints also apply. The CLI
uses dashed field names (for example `lsp-maximum-lifetime`); ConfigDB uses the
underscore spellings above.

#### FRR translation and lifecycle

| Operation | Desired configuration | Runtime behavior |
| --------- | --------------------- | ---------------- |
| Create instance | Create disabled parent | No active routing instance required |
| Edit disabled object | Retain validated values | Do not activate routing |
| Enable instance | Set enabled after prerequisite checks | Apply instance then eligible bound interfaces |
| Disable instance | Retain parent and child values | Detach applied interfaces, then remove/disable native instance as required by FRR |
| Delete instance | Refuse while any interface binding remains; remove owned level/policy rows with parent | Remove remaining native instance state |
| Bind interface | Explicit parent reference | Activate only when parent, interface and at least one AF are enabled |
| Disable interface | Retain binding and attributes | Remove active circuit configuration |
| Unbind interface | Delete binding and its owned per-level rows | Remove active circuit; explicit destructive operation |
| Reset field | Delete override | Restore effective default; preserve unrelated settings |
| Move interface to another VRF | Do not guess a new parent | Detach stale application; require explicit valid rebind |

Changing the FRR area-tag on an existing circuit is not an in-place operation in
the pinned callback. Rebinding therefore needs ordered teardown and recreation,
with failure reporting. AF transitions must preserve metric/passive/level settings
even if removing the last AF causes FRR to destroy and recreate the circuit.

FRR 10.7.1 clears the shared VRF system ID when destroying an area, even if
another area survives. Until the pinned FRR is fixed, CLI and GCU reject deleting
or disabling an active area while another active area in the same VRF survives.
The native planner also refuses this transition, including when the surviving
area is not owned by this feature. It does not rebuild sibling areas as a
workaround. Removing an inactive area, retiring the sole active area, and an
explicit atomic shutdown of all active areas remain supported. Interface
disable/unbind does not itself retire its parent area.

Replacing NETs with an unchanged system ID retains at least one NET throughout
the native update and never exceeds FRR's three-NET limit. Native confirmation
checks the operational system ID as well as configuration: configured NETs with
a missing or inconsistent runtime system ID cannot be reported as applied.
Interface VRF identity is read from Zebra because the isisd configuration writer
can omit it. Direct unvalidated Redis writes are not a supported API; the planner
refuses an unsafe native transition even if a bypassing writer changes ConfigDB.
The existing generic `config load`/`sonic-cfggen --write-to-db` path does not run
the IS-IS transition validator. Such a write may change desired rows, but the
planner refuses unsafe live retirement and reports failure rather than modifying
FRR. Use the IS-IS CLI or GCU for rejection before ConfigDB mutation.

### CLI Reference

Commands require `sudo` or equivalent privilege. For multi-ASIC configuration use
`config isis -n NAMESPACE ...` and `config interface -n NAMESPACE isis ...` with
the same namespace. Boolean scalar values use `true` / `false`.

The following is the implemented Click syntax. `INSTANCE` is always explicit for parent
operations and initial interface binding; `--vrf` defaults to `default` for parent
operations and is inferred/checked for interface binding. `LEVEL` is `level-1`,
`level-2` or the write convenience `both`.

| Function | Command |
| -------- | ---------------- |
| Instance lifecycle | `config isis instance <add\|enable\|disable\|del> INSTANCE [--vrf VRF]` |
| NET list | `config isis net <add\|del> INSTANCE NET [--vrf VRF]` |
| Instance scalar setting | `config isis set INSTANCE FIELD VALUE [--vrf VRF]` |
| Instance reset | `config isis reset INSTANCE FIELD [--vrf VRF]` |
| Level setting/reset | `config isis level <set\|reset> INSTANCE LEVEL FIELD [VALUE] [--vrf VRF]` |
| Complete SPF backoff tuple | `config isis spf-backoff set INSTANCE INIT SHORT LONG HOLD LEARN [--vrf VRF]` |
| Remove SPF backoff | `config isis spf-backoff reset INSTANCE [--vrf VRF]` |
| Bind/unbind | `config interface isis bind INTERFACE INSTANCE [--vrf VRF]`; `config interface isis unbind INTERFACE` |
| Interface admin state | `config interface isis <enable\|disable> INTERFACE` |
| Independent AF control | `config interface isis af INTERFACE <ipv4\|ipv6> <enable\|disable\|reset>` |
| Interface scalar setting/reset | `config interface isis <set\|reset> INTERFACE FIELD [VALUE]` |
| Interface level setting/reset | `config interface isis level <set\|reset> INTERFACE LEVEL FIELD [VALUE]` |
| Redistribution | `config isis redistribute add INSTANCE AF PROTOCOL LEVEL [--metric VALUE] [--route-map NAME] [--vrf VRF]` |
| Redistribution removal | `config isis redistribute del INSTANCE AF PROTOCOL LEVEL [--vrf VRF]` |

`FIELD` is a documented Click choice, not an arbitrary FRR passthrough. Instance
choices include level type, hostname, metric style, LSP MTU, overload and IPv6 MT.
Interface choices include level type, network type and passive mode. Level choices
are restricted to the corresponding table's fields. Optional values in the compact
table are mandatory for `set` and forbidden for `reset`.

The exposed protocol allowlist is IPv4 `connected`, `static`, `kernel`, `bgp`,
`ospf`, `rip`; IPv6 `connected`, `static`, `kernel`, `bgp`, `ospf6`, `ripng`.
A route-map must reference an existing `ROUTE_MAP_SET` entry. Table-direct redistribution has an additional table-ID
dimension and must not be collapsed into a protocol-only row. Default origination
is a separate FRR object, not an alias for redistributing static routes. Table-direct and default origination are outside this iteration.

Operational commands cover summary, neighbors, interface, database, route,
hostname, topology and VRF inventory. Implement filters only when the pinned
command/output can faithfully represent them. Do not return another instance's
state under an instance filter; exact native command mapping is an acceptance gate.

#### Operational commands

| Command | Scope and format |
| ------- | ---------------- |
| `show isis summary` | `--vrf VRF`, `--json`, `--instance NAME` with JSON |
| `show isis neighbor` | Same options; one VRF per JSON query |
| `show isis database [detail]` | Same options; one VRF per JSON query |
| `show isis interface` | Same options; one VRF per JSON query |
| `show isis route` / `show isis topology` | `--vrf VRF`, `--level level-1\|level-2`, `--json`; JSON rejected for multiple areas |
| `show isis hostname` | `--vrf VRF`, text only |
| `show isis vrf` | All-VRF summary, optional `--json` |

All support `-n` / `--namespace`. `--instance` requires JSON and one VRF; it
filters native area objects, never substitutes another area's data. FRR's
route/topology JSON can overwrite multiple areas, and most all-VRF JSON writers
can overwrite VRFs. Unsupported combinations fail explicitly; text remains
available. Native command errors propagate to the caller.

### Configuration Example

Commands for a default-VRF, Level-2 dual-stack point-to-point interface:

```bash
config isis instance add CORE
config isis net add CORE 49.0001.0000.0000.0001.00
config isis set CORE level-type level-2-only
config interface isis bind Ethernet0 CORE
config interface isis set Ethernet0 network-type point-to-point
config interface isis set Ethernet0 level-type level-2-only
config interface isis af Ethernet0 ipv4 enable
config interface isis af Ethernet0 ipv6 enable
config interface isis enable Ethernet0
config isis instance enable CORE
```

Addressing and routed-interface prerequisites are configured separately. IPv6 MT
is an explicit instance setting and is not implicitly enabled by IPv6 routing.

### Warm reboot, upgrade and restrictions

Use `config save` to persist ConfigDB. Cold startup and runtime share effective
defaults. This does not implement hitless IS-IS warm reboot/fastboot. Matching
CLI/schema/runtime revisions must be installed together. These PRs do not expose
a previously released IS-IS Click contract requiring an old-syntax compatibility
layer. Remove test bindings and all five tables before downgrading to an image
without the model. One area per logical interface is supported by FRR's exposed
binding API; multiple areas in one VRF share system state.

Source tests and native libyang validation have run locally. Native pinned-FRR
lifecycle, Linux package/container builds and DUT traffic acceptance remain to be
run; this document does not claim those tests passed. No scale/performance limit
or new SNMP/REST/gNMI binding is asserted.

### Test plan

See [IS-IS integration test plan](IS-IS-Test-Plan.md) for the complete contract,
recovery and forwarding matrix. Unit/schema tests do not replace native execution.

### References

- [Buildimage PR](https://github.com/sonic-net/sonic-buildimage/pull/28789)
- [Utilities PR](https://github.com/sonic-net/sonic-utilities/pull/4738)
- [Design record and pinned FRR references](IS-IS-Northbound-Redesign.md#references)

#### Explicit recovery retry

After correcting a failed recovery condition, use
`sudo docker exec bgp supervisorctl signal HUP frrcfgd` (select the actual ASIC's
bgp container on multi-ASIC systems). SIGHUP requests a new bounded IS-IS attempt;
it does not restart frrcfgd/BGP or discard the ownership journal. If no valid
desired snapshot is available, the retry stays pending until one can be read.
