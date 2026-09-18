# SONiC-VPP CoPP Dataplane Enablement — HLD

## Revisions

| Rev | Date | Author(s) | Changes |
|-----|------|-----------|---------|
| 1.0 | 2026-09-02 | Vesper | Initial HLD for the completed `copp_punt_policer` device-input plugin design. |
| 1.1 | 2026-09-18 | Vesper | • Switched from ingress policing at device-input to egress policing at interface_output<br>• Migrated from standalone plugins to sonic_ext|

---

## Background

[sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801) asks to enable Control Plane Policing (CoPP) testing on SONiC-VPP, so `tests/copp/test_copp.py` in sonic-mgmt is no longer skipped for the `sonic-vpp` platform. This has been implemented and validated on the `t1-lag-vpp` KVM testbed, but the design is topology-agnostic and applies to any SONiC-VPP topology.

CoPP on real ASICs classifies control-plane protocols, traps them to the CPU, groups traps under trap-groups, and rate-limits each group with a policer. On SONiC-VPP, the SAI **config plane** already worked end-to-end before this effort (`orchagent`'s `CoppOrch` issues normal SAI calls, accepted and stored by `saivpp`) — what was missing was the **dataplane enforcement**: no VPP mechanism actually rate-limited or even punted most CoPP-relevant traffic to the CPU.

### Control-plane protocols in scope

SONiC's default CoPP config (`copp_cfg.j2`) traps the following protocols on this platform (`show copp config`):

| Protocol / trap | Trap group | CIR/CBS (pps) |
|---|---|---|
| ARP request / response (`arp_req`, `arp_resp`) | `queue4_group2` | 600 |
| LACP (`lacp`) | `queue4_group1` | 600 |
| LLDP (`lldp`) | `queue4_group3` | 100 |
| UDLD (`udld`) | `queue4_group3` | 100 |
| TTL_ERROR (default trap group, IPv4 TTL-expiry) | (implicit default group) | 600 |
| BGP / BGPv6 (`bgp`, `bgpv6`) | `queue4_group1` | 600 |
| DHCP / DHCPv6 (`dhcp`, `dhcpv6`) | `queue4_group3` | 100 |
| IP2ME (`ip2me`) | `queue1_group1` | 600 |
| Neighbor discovery (`neigh_discovery`) | `queue4_group2` | 600 |

The five protocols in scope span three distinct traffic types on `linux-cp`-paired, L3-routed ports:

- **EtherType-based L2 traffic** — ARP, LACP, LLDP, TTL_ERROR
- **LLC-encapsulated traffic** — UDLD
- **L3 (IP-layer) traffic** — BGP, DHCP, IP2ME, neighbor discovery

A working path for the L3 traffic already existed before this effort, but it has been redesigned as part of this work to share the same classify/policer model as the other two traffic types (see Design below).

## Requirements

| # | Requirement |
|---|-------------|
| REQ-1 | Creating a SAI `POLICER` object must program an equivalent policer in the VPP dataplane (CIR/CBS/PIR/PBS, meter type, mode, conform/exceed/violate actions), not just store the attributes. |
| REQ-2 | Creating a SAI `HOSTIF_TRAP` for a given `trap_type` must cause matching control-plane traffic (ARP, BGP, LACP, LLDP, DHCP/DHCPv6, UDLD, TTL_ERROR, IP2ME, SNMP, SSH, etc.) to be classified and punted to the CPU via the existing TAP/genetlink punt path. |
| REQ-3 | Traffic punted for a trap must first pass through the VPP policer bound to that trap's `HOSTIF_TRAP_GROUP` (`SAI_HOSTIF_TRAP_GROUP_ATTR_POLICER`), so excess traffic is dropped (or marked, per `SAI_POLICER_ATTR_RED_PACKET_ACTION`) rather than delivered to the CPU. |
| REQ-4 | Removing/disabling a trap at runtime (`test_add_new_trap`, `test_remove_trap`) must add/remove the corresponding classify/punt binding immediately, with no swss/syncd restart required. |
| REQ-5 | SAI `getStats`/`getStatsExt` on a `POLICER` object must return live counters (`SAI_POLICER_STAT_GREEN/YELLOW/RED_PACKETS/BYTES`) sourced from VPP's policer conform/exceed/violate counters, not stubbed zeros. |
| REQ-6 | Trap/trap-group/policer configuration must persist and be re-applied after `config save` + reboot, matching existing SONiC CoPP semantics. |
| REQ-7 | The feature must not regress existing ACL, FDB, or routing dataplane behavior in `saivpp` — new code is additive (new object-type dispatch cases + new files), following the existing `SwitchVpp` extension pattern. |
| REQ-8 | Underlying testbed/harness issues that currently prevent the packet-injection subtests from even running (PTF auth, DUT service stability under VPP CPU load) must be resolved, since they block validation of REQ-1..REQ-6 regardless of SAI correctness. |

## Design: `sonic_ext` classify + policer nodes

The plugins below exist to identify three structurally different kinds of CoPP-relevant traffic — L3 (IP-destined-to-router), Ethernet (L2 ethertype), and LLC (non-Ethernet-II, sub-0x600 length-field frames). Each of these is dispatched by VPP's graph differently and none of them land on an existing policer-capable arc. 

Note that despite three distinct classification points, _policing itself is consolidated_. The idea is to meter at different locations but police in the same location. Rather than create a separate node for policing, the ethertype classification node doubles as a policer. So the LLC path redirects into the same node that performs Ethernet-ethertype policing. Also, all metering locations use te same metering logic by applying the same SAI-created VPP policer object via `vnet_police_packet()`. 

All three plugins live in the existing `sonic_ext` VPP plugin (not standalone plugins), and SAI wiring in `SwitchVppHostifTrap.cpp` resolves each trap's bound policer to a VPP policer name and calls the appropriate bind API on `createHostifTrap`/`setHostifTrap`/`setHostifTrapGroup`.

1. **`sonic-ext-copp-ip2me`** (L3) — a feature node on `ip4-punt`, matching by destination IP address (IP2ME/SNMP/SSH) or by TCP destination port (BGP). `ip4-punt` is a single, always-on, global arc every IP packet VPP's own dataplane has already decided is host-bound reaches, regardless of ingress interface.
2. **`sonic-ext-copp-ifout`** (Ethernet) — a feature node on `interface-output` of each linux-cp-paired TAP, matching by EtherType (ARP, LACP, LLDP, TTL_ERROR via ethertype 0x0800 + IPv4 TTL≤1). By the time linux-cp's punt path (`linux-cp-punt`/`linux-cp-punt-xc`/`lcp_arp_phy_node`) reaches `interface-output`, it has already rewound the buffer to an intact Ethernet frame and set the TX interface to the correct TAP — so this node only ever sees traffic VPP already decided is CPU-bound.
3. **`sonic-ext-copp-udld`** (LLC) — UDLD's wire encoding is sub-0x600, so VPP's `ethernet-input` treats its 14th/15th bytes as an 802.3 length field, not an EtherType, and always routes it to `llc-input`, which drops it before it can ever reach `sonic-ext-copp-ifout`'s EtherType classify. This node registers as the LLC/SNAP handler for UDLD's real (Cisco OUI) and PTF-test (LLC-null-adjacent) wire encodings, resolves the ingress phy's paired TAP, tags the frame in opaque metadata, and hands the packet directly to `sonic-ext-copp-ifout` for policing.


## Alternate Designs Considered

Three earlier enforcement designs were built, deployed, and disproven or reworked before landing on the design above.

1. **A standalone `device-input` classify+police plugin (`copp_punt_policer`).** Worked, but appropriately pointed out in review that it ran unconditionally on every packet on every interface, taxing the ~100% of ordinary forwarded traffic that never matches. Reworked into the `interface-output`-arc design above, which only sees traffic already decided to be CPU-bound.
2. **Linux `tc` ingress policer on each port's hostif TAP device.** Looked correct (`tc -s filter show` reported real hits/drops matching the configured CIR), but was **structurally incapable of enforcing anything**: this project's PTF harness reads punted traffic off the TAP via a raw `AF_PACKET`/`SOCK_RAW` socket, and Linux delivers a copy of every received frame to `AF_PACKET` sniffers via the `netif_receive_skb_core`/`ptype_all` tap point — which fires **before** the ingress qdisc/`tc filter` chain gets a chance to run. Confirmed via a controlled veth-pair experiment inside syncd's own netns: a `tc ingress` drop-all filter reported 7/7 packets correctly dropped, yet a raw-socket receiver on the *same, filtered* device still received all 9 sent frames. Not fixable by tuning `tc`; the enforcement point was fundamentally downstream of the measurement point.
3. **VPP-native classify table bound via `policer_classify_set_interface(..., l2_table_index)`.** Technically correct VPP configuration (verified live: sessions created, correct policer bindings, ports bound), but bound to the `l2-input` feature arc — which this project's `linux-cp`-paired, L3-routed ports' ARP/LACP/LLDP/UDLD traffic never traverses at all (confirmed via `show classify tables verbose`: `hits 0` on every session even after a full test run). A genuine architecture mismatch, not a misconfiguration.

## Status

All CoPP `test_copp.py` sub-tests pass on `vlab-vpp-01` (testbed `vms-kvm-vpp-t1-lag`):

| Test | Protocol | Result |
|---|---|---|
| `test_verify_copp_configuration_cli` | (config-plane, no traffic) | ✅ PASS |
| `test_policer[ARP]` | ARP | ✅ PASS |
| `test_policer[LACP]` | LACP | ✅ PASS |
| `test_policer[LLDP]` | LLDP | ✅ PASS |
| `test_policer[UDLD]` | UDLD | ✅ PASS |
| `test_policer[Default]` | TTL_ERROR | ✅ PASS |
| `test_policer[DHCP]` | DHCP | ✅ PASS |
| `test_policer[DHCP6]` | DHCPv6 | ✅ PASS |
| `test_policer_mtu[BGP/IP2ME/SNMP/SSH]` (64B/1514B/4096B) | 4 protocols × 3 MTU sizes | ✅ PASS |
| `test_add_new_trap` | BGP (install fresh trap) | ✅ PASS |
| `test_remove_trap[delete_feature_entry]` | BGP (`redis-cli del FEATURE\|bgp`) | ✅ PASS |
| `test_remove_trap[disable_feature_status]` | BGP (`config feature state bgp disabled`) | ✅ PASS |
| `test_trap_config_save_after_reboot` | BGP (reboot persistence) | ✅ PASS |

#### Skipped

| Test | Reason |
|---|---|
| `test_trap_neighbor_miss` | Gated to T0-family topologies (`tests_mark_conditions.yaml`'s topo_name condition, independent of `asic_type`). Needs to be done during T0 testing. |

### `test_remove_trap` fix (2026-09-18)

Both `test_remove_trap` tests (disable_feature_status and delete_feature_entry) were failing intermittently because `RX PPS` measurements would occasionally just outside the expected 540-780pps window. Root cause was a test-harness measurement bug. Although VPP trap statistics showed correct policed values, `BGPTest`'s reported `RX PPS` came from a raw NN/interface packet counter, which on any topology with live BGP sessions also counts real background BGP traffic sharing tcp/179 with the test's synthetic packets. 

Fix: `BGPTest` now measures `RX PPS` using its own existing content-matched packet count (`recv_count`, which was already being computed. Change scoped to `BGPTest` only.

## Key files changed

| Repo | File | Change |
|---|---|---|
| `sonic-platform-vpp` (`platform/vpp` submodule) | `vppbld/plugins/sonic_ext/{copp_ip2me_node.c, copp_ifout_node.c, copp_udld_node.c}` | Three classify+police entry points (L3 on `ip4-punt`, Ethernet on `interface-output`, LLC redirect into the Ethernet node) folded into the existing `sonic_ext` plugin. |
| `sonic-sairedis` | `vslib/vpp/SwitchVppHostifTrap.cpp` | Per-trap-type match-key table, plugin bind/unbind wiring, default-trap-group tracking fix. |
| `sonic-sairedis` | `vslib/vpp/vppxlate/SaiVppXlate.c` / `.h` | VAPI wrappers for policer bind and counter readback, extended with IPv4-TTL-expiry match support. |
| `sonic-mgmt` | `tests/common/plugins/conditional_mark/tests_mark_conditions_sonic_vpp.yaml` | Lift `copp` skip for `asic_type in ['vpp']`. |
| `sonic-mgmt` | `ansible/roles/test/files/ptftests/py3/copp_tests.py` | `BGPTest`: measure `RX PPS` from the existing content-matched `recv_count` instead of the raw NN interface counter, to avoid counting real background BGP session traffic sharing tcp/179. |

## References

- [sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801)
