# IS-IS integration test plan

## Scope

Test the CLI and frrcfgd behavior introduced by this change: input handling,
ConfigDB mutations, FRR command mapping, field deltas, dependencies and startup
rendering. Include installed configuration, adjacency, route learning/withdrawal
and persistence checks to demonstrate that the SONiC configuration path works.
Protocol algorithms, scale, convergence benchmarks and downstream bug repair
are outside this change's acceptance criteria.

## Setup and evidence

Install matching buildimage and utilities changes against FRR 10.7.1
(`10.7.1-sonic-0`). Enable the FRR management framework and restart bgp.
Confirm isisd/frrcfgd run. The [HLD](IS-IS-HLD.md) defines the authoritative
three-table schema and CLI.

Prepare default, VrfA and VrfB, routed interfaces and multiple named instances.
NETs in a VRF share a system ID; different areas may use different area addresses.
Use supported Ethernet, PortChannel, VLAN, loopback and VLAN subinterfaces.
Use the same namespace for configuration and runtime observations.

Capture image/commit IDs, namespace, relevant ConfigDB rows, FRR running
configuration, frrcfgd logs and command transcripts. Record each case as passed,
failed or **not run**. A device result requires successful configuration
readback and the specified runtime or forwarding observations. Record native
FRR failures with their commands and logs.

## Test responsibilities

- YANG tests cover field ranges, defaults, references and model constraints.
- CLI tests cover arguments, ConfigDB mutations, validation and query syntax.
- Handler tests cover command groups, field deltas, dependencies, startup
  rendering and the existing command-failure/cache behavior.
- Device tests provide representative installed CLI/connector/daemon smoke
  coverage across the distinct paths below. Check ConfigDB, running-config
  and the relevant observable result. Unit coverage does not replace installed
  AF, VRF, redistribution or restoration checks.

## Configuration and lifecycle matrix

| Case | Action | Required result |
| --- | --- | --- |
| C1: empty instance | `config isis add CORE`, repeat add, set/reset attributes | Row existence creates FRR instance; duplicate add preserves fields; final reset retains empty instance/defaults. |
| C2: NET | Set/replace/remove exact NET; attempt bad format, nonzero NSEL and different same-VRF system ID | Valid operations preserve other instances' ConfigDB rows; incompatible system ID and mismatched deletion are rejected. Commands use the correct instance/VRF context. Capture shared system-ID runtime state after deletion/replacement. |
| C3: binding | Enable IPv4 only, IPv6 only, then both with explicit instance | AFs are independent; parent must exist in actual interface VRF; a minimal AF row binds immediately. |
| C4: final AF disable | Set custom metric/Hello/P2P, disable one AF, then final AF | First disable preserves row/other AF; final disable removes entire row and parameters; re-enable uses defaults. |
| C5: binding identity | Attempt different instance while AF remains; delete/re-enable against another parent | Active rebinding rejected; explicit delete/re-enable succeeds; no old-instance binding remains. |
| C6: instance deletion | Delete while referenced; remove interfaces then delete | Referenced deletion rejected without changing ConfigDB; allowed deletion removes parent and all its redistribution rows only. |
| C7: VRF ownership | Remove IS-IS row, move actual interface default → VrfA → VrfB → default, re-enable each time | New key matches actual VRF and same-VRF parent; both old AF bindings removed. Wrong `--vrf` rejected. |
| C8: external interface changes | Change/delete actual routed-interface base row while IS-IS row remains, then restore or delete IS-IS row | Mismatched ownership detaches old bindings; no implicit key migration or default rebind. Prefix-only events do not move bindings. |
| C9: levels | Save distinct L1/L2 fields; narrow/widen instance and interface levels | Runtime circuit uses level intersection; empty intersection rejected; inactive-level fields retained. |
| C10: LAN/P2P | Save distinct Hello intervals/multipliers; switch LAN → P2P → LAN | CLI preserves per-level fields; handler emits the correct network-type and Hello commands. Native FRR timer behavior is not retested. |
| C11: command failure | Unit-test failed instance/interface/policy application and a successful parent with a failed child | Failure is logged and failed state is not recorded as successfully applied. A failed child does not invalidate its successful parent. Subsequent explicit configuration events use the ordinary handler path. Late child deletion must not recreate a removed parent. No automatic retry, rollback or compensation is introduced. |
| C12: startup | Exercise template rendering and command replay; restart an installed image and perform a normal saved-config reload | Newly added fields/defaults/levels/AFs/NET/backoff/redistribution are mapped consistently; child startup replay does not repeat commands already applied by its parent. Saved objects and bindings are restored, then accept a new update/delete. |
| C13: namespaces | Repeat configuration and queries on one ASIC | Selected ConfigDB and bgp container only; other ASIC configuration and neighbors unchanged. |

## Parameter and query matrix

| Area | Required checks |
| --- | --- |
| LSP | Boundary ranges, independent L1/L2 updates, `lifetime >= refresh + 300`, `generation < refresh`, defaults included; complete lsp-timers keeps other saved values. Both-level operations reject before writing either invalid result. |
| SPF | Independent 1–120 second minimum intervals; all five 0–60000 ms backoff fields or none; `hold_down > time_to_learn`; delete backoff preserves minimum intervals. |
| Global attributes | Default/explicit/set/reset for dynamic hostname, MTU, overload, overload-on-startup and IPv6 multi-topology. CLI preserves independent fields; handler/template emits the corresponding commands; IPv6 topology remains separate from AF enable. Native overload timer algorithms are not qualification targets. |
| Interface attributes | LAN/P2P, passive, level, metric, Hello interval and Hello multiplier each have set/reset mapping coverage. Per-level fields cover L1, L2 and both; combined operations preserve sibling fields. |
| Redistribution | AF-specific sources; parent level; ordinary ID 0/table ID 1–65535; multiple table IDs and both levels; metric 0/max; route-map reference; complete replacement removes omitted old route-map and restores metric 0. |
| Validation | Invalid VRF/instance/interface, wrong actual VRF, member port, missing parent, no AF, bad ranges and unsupported source protocols. Validate final ConfigDB using YANG and applicable GCU operations. |
| Reset | Remove only selected explicit fields/levels; retain sibling fields and rows; AF has no reset; NET and backoff use their own deletion. |
| Show | All HLD query forms, range/mutual exclusions, default/all VRF, JSON where supported, LSP ID with detail, namespace selection and nonzero daemon exit propagation. Configuration reads ConfigDB explicit/effective values. |
| Packaging | One packaged template, isisd shared supervisord lifecycle, startup/dynamic defaults agree, utilities gitlink matches the intended companion commit. |

Cover every supported attribute's set/reset command and every distinct command
group in the CLI/handler/template suites. Test valid boundaries and invalid
values in model/CLI suites. Parameterize independent values and use shared
setup and validators. Separate incompatible AF/level/VRF combinations.

For reset, test removal of the selected ConfigDB fields and the corresponding
handler commands. Device checks exercise representative command groups without
requiring a separate forwarding assertion for every attribute.

## Device smoke test

Use the Force10 seven-node topology for IPv4/IPv6 routing and configuration
tests. Use an isolated local VRF for context/level tests and a multi-ASIC DUT
for namespace selection. The required groups are:

| Group | Actions and expected observations | Current automation |
| --- | --- | --- |
| D1: basic configuration and routing | Create a named instance, NET and routed/passive bindings through SONiC CLI. Check ConfigDB and the instance/interface running-config context, Up neighbors, a learned IPv4 route and one ping. Remove a test advertised prefix/binding with no alternative advertisement and check route withdrawal; restore it and check return. | Force10 implements instance/interface context, IPv4 neighbors/route/ping, PE3 passive-loopback withdrawal and restoration. Device execution: **not run**. |
| D2: AF and object lifecycle | Exercise IPv4-only, IPv6-only and dual-AF bindings once; disabling one AF preserves the other, disabling the final AF deletes the row, re-enable restores a minimal binding. Delete referenced instances only after interface cleanup, then recreate. Check installed IPv6 binding and one learned IPv6 route/reachability path on a capable setup. | Force10 implements IPv6 route/ping, dual → IPv6-only → final disable → IPv4-only → dual, and referenced instance delete/recreate. Device execution: **not run**. |
| D3: context and levels | Install one non-default-VRF instance/binding and another instance; confirm keys and correct FRR contexts. Change parent/interface levels and verify the installed circuit level. On multi-ASIC systems exercise one selected namespace and verify other namespace configuration is unchanged. | Force10 implements temporary VrfIsisTest/Loopback901/second instance, parent/interface levels and wrong-VRF rejection. Separate namespace test checks selected container and other ASIC ConfigDB/neighbors; skips single-ASIC. Device execution: **not run**. |
| D4: attribute update/reset | Use one compatible snapshot to exercise global flags/MTU, LSP/SPF command groups, interface Hello/passive/network-type and per-level metric. Update and reset representative fields, comparing ConfigDB and running-config while preserving siblings. All individual fields retain unit mapping coverage. | Force10 implements flags/MTU, LSP generation/SPF/backoff, Hello interval/multiplier, metric, passive and P2P/reset, with configuration snapshot restoration. Device execution: **not run**. |
| D5: redistribution | Add/update/delete one ordinary-source and one table-id policy, with metric/route-map replacement. Compare ConfigDB and running-config. Use a controlled source prefix to check advertisement and withdrawal once; do not benchmark redistribution or exhaust AF/source/level combinations on devices. | Force10 implements static/table-id policy CRUD and metric/route-map replacement. One temporary static prefix checks advertisement/withdrawal; table-id checks policy installation only. Device execution: **not run**. |
| D6: restoration and coexistence | Save a representative configuration, restart bgp once and perform one normal saved-config reload. Compare restored objects and running-config, basic adjacency/route recovery, then update/delete a restored object. Check unrelated BGP configuration/session state before and after IS-IS changes; no zero-packet-loss or convergence-time target. | Force10 implements save, one bgp restart and one normal reload, metric/backoff restore then update/reset/delete, adjacency/route recovery and BGP config/established-peer recovery. Original saved file is backed up/restored. Device execution: **not run**. |
| D7: query wrappers | Compare representative SONiC neighbor/interface/route/configuration queries with the selected daemon or ConfigDB, including supported JSON/VRF/namespace forms. Keep malformed-option coverage in CLI tests. | Force10 compares interface/route JSON to vtysh and explicit configuration to ConfigDB; neighbor all-VRF and non-default-VRF JSON are parsed. Separate namespace test compares selected daemon output. Device execution: **not run**. |

Share fabric setup and validators across groups. Await asynchronous application
with bounded condition checks. Require successful route-query return codes and
valid JSON; a failed query must not satisfy a withdrawal assertion.

## Automation prerequisites and execution status

The current `test_isis_cli_force10.py` has eleven cases; the independent
`test_isis_cli_namespace.py` adds one multi-ASIC case. The Force10 profiles have
IPv6-only transit links, so the fixture checks for conflicts and adds twelve
temporary IPv4 /31 pairs from `192.0.2.0/27`, removing only its own addresses.
Existing IS-IS configuration must be removed by the operator before running:
the fixture refuses to overwrite it. The temporary VRF process needs no NET
for this context/command smoke test and does not claim non-default-VRF traffic
coverage. Table-id source traffic, additional routed-interface types and the
full lifecycle matrix remain separate device acceptance work.

| Validation | Result |
| --- | --- |
| CLI contracts | 82 cases passed; native SONiC imports mocked on macOS, real interface helpers used |
| Framework regression | 71 cases passed: 49 IS-IS and 22 existing framework cases |
| Device predicates and fixture cleanup | 14 local checks passed |
| Device CLI command arguments | 49 representative configuration commands validated against real Click groups |
| Device source checks | Python syntax and lint passed |
| YANG fixtures | 27 groups passed in the existing model validation run |
| Force10 and multi-ASIC device execution | **not run** |

Local results establish the tested contracts and helper behavior. Installed
device behavior requires execution of the device cases. No line/branch coverage
percentage is available.

Restore only the objects mutated by an individual case; fabric-wide restoration
is required when that case actually deletes or rebuilds the fabric configuration.

## Cleanup and limits

Remove interface rows before deleting test instances, then restore original
VRFs, addresses and saved configuration. Verify no
leftover bindings, adjacencies or test advertisements in any namespace/VRF.

FRR protocol qualification, scale/performance, warm reboot, fastboot and graceful
restart are outside its scope.

## References

- [Unified FRR management unit tests](../mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md#9-unit-test)
- [BGP dynamic peer modification](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testplan/BGP-Dynamic-Peer-Range-Modify.md)
- [BGP aggregate address](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testplan/BGP-Aggregate-Address.md)
- [BGP router ID](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testplan/BGP-Router-ID-test-plan.md)
- [BGP CLI tests](https://github.com/sonic-net/sonic-mgmt/blob/master/tests/bgp/test_bgp_command.py)
- [OSPF routing](https://github.com/sonic-net/sonic-mgmt/blob/master/docs/testplan/OSPF-test-plan.md)
- [Static route BFD tests](../static-route/SONiC_static_route_bfd_hld.md#tests)
