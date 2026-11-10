# IS-IS Northbound Configuration Redesign HLD

> Status: design proposal, not implemented. CLI examples and ConfigDB names below
> describe the proposed contract, not commands available in the current PRs.
> This document supplements the [current integration HLD](IS-IS-CLI-Configuration.md)
> and [current test plan](IS-IS-Test-Plan.md). It does not change their implementation status.

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High Level Design](#high-level-design)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Memory Consumption](#memory-consumption)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
- [Open Action Items](#open-action-items)
- [References](#references)

### Revision

| Revision | Date | Change Description |
| -------- | ---- | ------------------ |
| 0.1 | Nov 10 2026 | Draft interface contract, FRR capability boundaries, build scope and contributor assessment |
| 0.2 | Nov 10 2026 | Adopt existing PR history and gs1571 contributions as the implementation baseline; organize remaining work as incremental changes |

#### Local implementation checkpoint (Nov 10 2026)

The five-table model and CLI below are implemented locally. The original gs1571
commits `c6bc0e681`, `e01033a2b`, `63a644b1` and `c0b6238d` remain unchanged in
history, including author and sign-off. Recovery kernel and native transport are
adapted from gs1571's `f7b6ef84dfb0ff8ffcdeb032cd17867c31298baa`, with provenance
in the source. The default-instance projection is adapted for composite identity;
no SRv6 feature or modified FRR dependency is imported.

Local verification currently covers the framework source suite (142 tests), Click
commands against an isolated real Redis server (23 tests), and 37 positive/negative
schema fixtures using the repository harness with native libyang 3.12.2 and
the SONiC-patched Python 3.1.0 binding. All seven committed Force10 topology
profiles pass configuration/projection/cleanup checks in the local CLI harness.
The YANG-model and framework pure-Python wheels build locally and contain the
new shared module, models, recovery adapter and startup template. Utilities
wheel generation stops at its existing missing `sonic-config-engine` dependency
check; its Linux dependency stack has not been replaced with fake packages. These are source/contract checks, not
native FRR lifecycle or DUT forwarding acceptance. Linux SONiC package/container
builds and seven-node execution remain unexecuted. No push or remote PR update is
part of this work. The HLD and test plan describe the implemented contract and
separately identify the acceptance work requiring a matching SONiC image.

Local implementation commits (not pushed):

| Repository | Commit |
| ---------- | ------ |
| sonic-buildimage | `880832c47` |
| sonic-utilities | `9bb54224` |
| sonic-mgmt | `0b9444cbb` |

The buildimage utilities gitlink points to the local utilities commit above.
A separate builder must receive that commit locally before resolving the submodule;
it is not yet available from the upstream remote. The four original gs1571
AF/MT/MTU commits retain their exact IDs and sign-offs. Adapted recovery source
and tests identify their original commits/authors rather than attributing that
work to the new northbound adapter.

### Scope

Design a durable northbound model while implementing only the IS-IS capabilities
needed by the current integration and review: instance identity, explicit interface
binding, independent IPv4/IPv6 enablement, IPv6 multi-topology, existing interface
attributes and LSP timers, overload, SPF timers, redistribution and operational CLI.

The implementation remains a wrapper around the FRR revision selected by
sonic-buildimage: `f8c0b08dcb0c78f9e42b9b86ae70b049e4e617c1`.
FRR daemon, protocol and southbound infrastructure changes are outside this work.
SRv6 persistence, arbitrary RFC 8202 circuit multi-instance support, and exposing
every FRR feature are not implied by the long-term model.

### Definitions/Abbreviations

| Term | Meaning |
| ---- | ------- |
| Instance | An FRR IS-IS area identified by VRF and area-tag; not necessarily an independent daemon or system ID |
| Level | IS-IS Level 1 or Level 2, distinct from address family and topology |
| AF | IPv4 or IPv6 address family |
| NET | Network Entity Title; multiple NETs do not imply multiple independent systems |
| Desired configuration | ConfigDB values, including values retained while disabled |
| Applied configuration | Configuration successfully installed in FRR |
| MT | Multi-topology routing, separate from IPv6 routing enablement |

### Overview

The current PR tables mix instance identity with VRF identity and group unrelated
settings under a global timer table. The redesign follows FRR's actual ownership:
instance, instance/level, interface binding, interface/level and redistribution
policy. An address-family switch does not create another circuit. A level switch
does not select LAN versus point-to-point operation. LSP MTU is an instance
attribute, not a timer or an interface MTU.

RFC 9130 and OpenConfig provide structural references. FRR's pinned YANG and
callbacks determine what can actually be implemented. Neither reference requires
an identical count of SONiC Redis tables.

### Requirements

1. Identify instances by `(vrf, instance)` and map `instance` to FRR `area-tag`.
2. Bind a routed interface explicitly to one instance. Infer VRF from the routed
   interface; an explicitly supplied VRF must match it.
3. Permit configuration edits while disabled. Validate types, ranges and references
   immediately; check operational prerequisites when enabling.
4. Disable preserves desired configuration. Delete removes configuration. Reset
   removes an override and restores the documented default.
5. Do not implicitly rebind interfaces after a VRF change or select the only instance
   as a substitute for an explicit binding.
6. Keep startup rendering and runtime translation semantically equivalent.
7. Expose failures as failures; a successful ConfigDB write alone does not prove that
   FRR applied the configuration. Preserve useful object and operation context in logs.
8. Keep CLI, schema reference, HLD and test-plan examples consistent in the same change.

### Architecture Design

```text
Click CLI / validated configuration load
                  |
                  v
              CONFIG_DB
                  |
          +-------+-------+
          |               |
     startup renderer   frrcfgd runtime handlers
          |               |
          +-------+-------+
                  v
             existing FRR

show isis -> existing rvtysh / vtysh -> FRR operational state
```

This is a built-in feature. No new service or Application Extension is required.
No APP_DB, ASIC_DB or COUNTERS_DB schema changes are proposed. Recovery reuses the contributor kernel, durable ownership journal and native
transport. A separate worker reads a consistent ConfigDB snapshot and native
state before planning changes; Redis callbacks only wake this worker.
Existing FRR/Zebra/FPM/SWSS forwarding integration remains in place.

### High Level Design

#### Implementation baseline and sequence

Build on the existing PR history and gs1571's contributions. Existing implementation,
fixes and regression tests are the default starting point, not merely examples to
rewrite. Preserve original authorship, sign-offs and traceability when incorporating
commits. Trust the contributor's work as an engineering baseline; integration tests
check the resulting combination and changed contracts rather than requiring an
independent reimplementation of already addressed behavior.

1. Establish the combined commit history for each repository. Compare ancestry and
   patch equivalence before selecting commits so fixes already present are not
   applied twice. Retain the current lifecycle/schema fixes in buildimage and the
   CLI validation, registration, namespace and reset fixes in utilities.
2. Incorporate gs1571's independent-AF and MTU commits, and the associated AF/MT CLI
   commits, in dependency order. Reuse their implementation and tests. Resolve
   overlap with existing fixes explicitly; record any adaptation in follow-up commits.
3. Apply the agreed model changes on top: instance identity, explicit binding,
   disable-versus-delete semantics, editing while disabled and per-level ownership.
   Adapt existing handlers and templates wherever possible. The table and CLI
   proposals below are a target contract, not a mandate to replace working modules.
4. For recovery, use #30607's existing implementation as the preferred starting
   point. Map its commit dependencies and isolate the IS-IS-relevant work before
   integration. Extend its default-instance assumptions only where needed by the
   agreed model. Keep unrelated SRv6 features and changes requiring a modified FRR
   outside this iteration; reuse shared code where that boundary can be maintained.
   Document concrete coupling if it prevents reuse rather than assuming a rewrite.
5. Reuse #29119's recovery checks and existing test-plan coverage. Add or adjust
   tests for changed contracts and integration gaps. Update interface documentation
   from the resulting implementation, preserving useful existing CLI conventions.
6. Validate affected source tests and wheels first, then the combined native FRR
   behavior. Build the routing container only for the integration stage. Keep
   upstream contribution results identifiable alongside our combined-head results.

This sequence does not expand this iteration to every feature in the contributor's
branches. Remaining new implementation should be attributable to an agreed
requirement or a concrete integration gap.

#### Modules and build artifacts

| Repository / module | Responsibility | Artifact |
| ------------------- | -------------- | -------- |
| sonic-buildimage / sonic-yang-models | Keys, validation, defaults and schema reference | `sonic_yang_models-1.0-py3-none-any.whl` |
| sonic-buildimage / sonic-frr-mgmt-framework | Runtime translation, startup templates and tests | `sonic_frr_mgmt_framework-1.0-py3-none-any.whl` |
| sonic-utilities | Config/show commands, command reference and unit tests | `sonic_utilities-1.2-py3-none-any.whl` |
| sonic-utilities / sonic-utilities-data | Generated shell completion for changed CLI | `sonic-utilities-data_1.0-1_all.deb` |
| sonic-buildimage / docker-fpm-frr | Package the framework and routing runtime | `docker-fpm-frr.gz` |
| SONiC / doc/isis | HLD and test plan | Documentation only |
| sonic-mgmt / tests/isis | Integration acceptance | Test source only |

The framework wheel includes the FRR/IS-IS startup templates. CLI and YANG wheels
also have host consumers; replacing only the bgp container is not sufficient for
a complete CLI/schema update. YANG changes can additionally invalidate consuming
config-engine/base-image builds when packaging a full image.

No modified FRR binary deb is expected for this redesign. FRR, SWSS, libyang and
swsscommon still appear in the dependency graph and must be available. The
framework wheel also depends on config-engine for its tests. The utilities wheel
depends on config-engine, YANG management/models and platform/common packages.

#### Targeted build and cache scope

Use an already configured Linux SONiC builder with the correct architecture,
platform and submodule revisions. The following are target examples for this
branch's Trixie build. They are not builds executed for this document.

```bash
make NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 NOBOOKWORM=1 NOTRIXIE=0 \
  target/python-wheels/trixie/sonic_yang_models-1.0-py3-none-any.whl
make NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 NOBOOKWORM=1 NOTRIXIE=0 \
  target/python-wheels/trixie/sonic_frr_mgmt_framework-1.0-py3-none-any.whl
make NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 NOBOOKWORM=1 NOTRIXIE=0 \
  target/python-wheels/trixie/sonic_utilities-1.2-py3-none-any.whl
make NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 NOBOOKWORM=1 NOTRIXIE=0 \
  target/debs/trixie/sonic-utilities-data_1.0-1_all.deb
make NOJESSIE=1 NOSTRETCH=1 NOBUSTER=1 NOBULLSEYE=1 NOBOOKWORM=1 NOTRIXIE=0 \
  target/docker-fpm-frr.gz
```

Only build targets needed for a given validation step. Source/unit tests come first,
then affected wheels, then container/integration validation. The outer Makefile
enables both Bookworm and Trixie by default; select the intended distribution
explicitly rather than accidentally running both paths.

A target build still needs its build-slave image, native test dependencies and
missing prerequisites. Wheel-only does not mean dependency-free. Reuse matching
artifacts and Docker layers; do not run global clean/distclean or prune all caches.
If invalidation requires a clean, inspect and use the individual artifact's clean
target. Do not change the shared cache policy just to build this feature. Actual
disk use must be measured on the chosen builder; no cache-size claim is made here.

### SAI API

No new SAI API or object is introduced. Existing IP route, next-hop and router
interface programming remains the responsibility of the existing forwarding stack.

### Configuration and management

#### Config DB Enhancement

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

#### Lifecycle and binding

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

#### CLI Reference

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

#### Configuration Example

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

### Warmboot and Fastboot Design Impact

Saved ConfigDB must render the same effective configuration at cold/container start
as runtime updates. Disable is not deletion on restart. This is not a claim of
hitless IS-IS warm restart. Warmboot/fastboot protocol and forwarding continuity
require separate verification. Record control-plane and data-plane disruption;
do not infer zero disruption from successful configuration restoration.

Startup rendering adds work proportional to configured objects. The recovery worker reconciles on events and every two seconds, with bounded
snapshot/native calls and a 30-second attempt deadline. Measure boot overhead with the feature absent,
disabled and enabled; no numerical performance claim is available yet.

### Memory Consumption

Expected configuration bookkeeping grows with instances, bindings, levels and
redistribution rows. Disabled objects intentionally retain their configuration.
The contributor recovery journal at `/etc/frr/isis-owned.json` retains bounded
ownership and attempt state. Measure its storage cost. Measure process RSS and
ConfigDB growth under repeated create/delete and disable/enable cycles.

### Restrictions/Limitations

- One area binding per logical interface, matching the exposed FRR model.
- Same-VRF multiple area-tags have a model representation but require native FRR
  lifecycle validation before being declared supported. They share per-VRF state.
- The new CLI/schema are under development in these PRs. There is no established
  released IS-IS Click interface assumed for compatibility; update all PR examples
  and tests together. Do not claim that SONiC previously had no IS-IS test support.
- No FRR modification, SRv6 capability expansion, SNMP, REST or gNMI implementation
  is included merely by changing ConfigDB.
- Recovery from updates/deletes missed during frrcfgd downtime is an explicit
  verification item. Startup rendering alone is not proof of that recovery.

### Testing Requirements/Design

Retain applicable coverage from the existing test plan. The additional cases below
follow changed contracts; they are not unrelated feature expansion.

| ID | Scenario | Required observation |
| -- | -------- | -------------------- |
| R1 | Same name in different VRFs; multiple names in one VRF | Correct native identity, system-ID constraints and isolation; gate unsupported combinations |
| R2 | Edit disabled parent/interface, enable, disable, re-enable | Desired values survive and native values are fully restored |
| R3 | Parent delete with active or disabled bindings | Reject without partial deletion |
| R4 | Explicit binding, incorrect VRF, VRF move, rebind | No guessed binding; native teardown/recreation ordered and failures visible |
| R5 | Four AF combinations and all transitions, passive and active | Correct native routing commands; attributes survive circuit recreation |
| R6 | IPv6 with/without MT; metric-style conflict | AF and topology remain distinct; invalid combinations rejected |
| R7 | Per-level values, both, reset one level, absent fields | No cross-level inheritance; FRR defaults and startup/runtime agree |
| R8 | MTU implicit 1497 and explicit 1492; LSP timer boundaries | Matching YANG, rendering, runtime and documentation |
| R9 | Overload and on-startup overload | Native setting plus transit-path effect and timer expiry |
| R10 | Minimum SPF and complete IETF backoff tuple | Correct scope/units, bounds, reset and pinned FRR mode behavior |
| R11 | Redistribution AF/protocol/level/metric/route-map and removal | Selected route advertisement and withdrawal; unrelated policies preserved |
| R12 | Cold start, bgp restart, config reload, missed offline update/delete | Compare desired and native state; explicitly report unsupported recovery |
| R13 | CLI and validated bulk configuration rejection | Same cross-reference/range checks; no partial mutation on validation failure |
| R14 | Seven-node traffic and show filters | Learned routes and end-to-end IPv4/IPv6 forwarding; correct VRF/instance output |
| R15 | Existing BGP and other routing behavior | No unwanted daemon restart or unrelated configuration removal |

Run schema, translator/template and Click tests before package builds. Native FRR
and DUT tests are necessary for capability/lifecycle claims that mocks cannot
establish. Distinguish source tests, native package tests and DUT results in reports.

### Open Action Items

1. Run native pinned-FRR acceptance for multiple areas, rebind, coupled timers,
   overload expiry, redistribution and operational output; record actual readback.
2. Build the matching Linux wheels/completion deb/container and run the DUT cases
   in the test plan, including recovery and concurrent BGP traffic.
3. Keep native/DUT acceptance distinct from the source and schema test results.

#### Existing contributor work reviewed

The contributor is **gs1571 (Grigorii Solovev)**. The following assessment is based
on commit diffs and PR descriptions, not local execution of their test suite.

| Contribution | Assessment | Use in this redesign |
| ------------ | ---------- | -------------------- |
| [buildimage c6bc0e6](https://github.com/gs1571/sonic-buildimage/commit/c6bc0e681156b454da515eb48606e7444005dea5) | Adds independent IPv4 enablement to YANG, startup/runtime translation and AF tests | Adopt implementation and tests as baseline; adapt instance keys and lifecycle in follow-up changes |
| [buildimage e01033a](https://github.com/gs1571/sonic-buildimage/commit/e01033a2bb2bd0e1e00a135e5bdc7d0bde626abd) | Corrects default LSP MTU to FRR's 1497; preserves explicit 1492 test coverage | Adopt fix and tests; update HLD/CLI reference defaults as well |
| [utilities 63a644b](https://github.com/gs1571/sonic-utilities/commit/63a644b167bfa9248b4103c1c1f9168c5ca7a11c) | Adds IPv4/IPv6 CLI and reset | Adopt CLI and tests; then adapt binding and disabled-edit guards |
| [utilities c0b6238](https://github.com/gs1571/sonic-utilities/commit/c0b6238d636fc491c3929028bdf65dc582c38a22) | Adds IPv6 MT CLI/reset | Adopt CLI/reset implementation and tests; preserve distinction from AF enablement |
| [SONiC 71a662e](https://github.com/gs1571/SONiC/commit/71a662e40c3095a5899e531cd98d81ebb4f38f29) | Documents IS-IS/SRv6 persistence and additional schema | Reuse relevant documentation alongside integrated code; retain accurate scope and validation status |
| [buildimage #30607](https://github.com/sonic-net/sonic-buildimage/pull/30607) | Dependent draft: default-instance IS-IS/SRv6 persistence, ownership journal, native readback and bounded reconciliation | Preferred recovery implementation baseline; resolve dependencies and adapt profile limits without importing unrelated SRv6 scope |
| [mgmt #29119](https://github.com/sonic-net/sonic-mgmt/pull/29119) | Tests restart/reload/cold-boot and offline update/delete recovery with BGP checks | Reuse applicable recovery tests with integrated code; adapt fixtures and identity assumptions |

#30607 explicitly excludes upstream package/image and full upstream lifecycle
acceptance from its executed validation. #29119 states standard sonic-mgmt T0
fixture validation is pending. Their reported passes must not be presented as
validation of our current PR head. The related AF/MT/MTU commits were incorporated by fast-forward in the local
implementation checkpoint above, preserving their original commit identities.

### References

- [Pinned FRR IS-IS YANG](https://github.com/FRRouting/frr/blob/f8c0b08dcb0c78f9e42b9b86ae70b049e4e617c1/yang/frr-isisd.yang)
- [Pinned FRR IS-IS configuration callbacks](https://github.com/FRRouting/frr/blob/f8c0b08dcb0c78f9e42b9b86ae70b049e4e617c1/isisd/isis_nb_config.c)
- [RFC 9130: IS-IS YANG Data Model](https://www.rfc-editor.org/rfc/rfc9130.html)
- [RFC 8202: IS-IS Multi-Instance](https://www.rfc-editor.org/rfc/rfc8202.html)
- [RFC 5308: Routing IPv6 with IS-IS](https://www.rfc-editor.org/rfc/rfc5308.html)
- [RFC 5120: Multi Topology IS-IS](https://www.rfc-editor.org/rfc/rfc5120.html)
- [RFC 8405: SPF Back-Off Delay Algorithm](https://www.rfc-editor.org/rfc/rfc8405.html)
- [OpenConfig IS-IS](https://github.com/openconfig/public/blob/master/release/models/isis/openconfig-isis.yang)
- [SONiC HLD template](../guidelines/hld_template.md)
