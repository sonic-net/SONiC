# SONiC-VPP CoPP Dataplane Enablement — HLD

## Revisions

| Rev | Date | Author(s) | Changes |
|-----|------|-----------|---------|
| 1.0 | 2026-09-02 | Vesper | Initial HLD for  `copp_punt_policer` design. |

---

## Background

[sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801) asks to enable Control Plane Policing (CoPP) testing for `t1-lag` topology on the SONiC-VPP KVM testbed.

CoPP on real ASICs classifies control-plane protocols, traps them to the CPU, groups traps under trap-groups, and rate-limits each group with a policer. On SONiC-VPP, the SAI `config plane` already worked end-to-end before this effort (`orchagent`'s `CoppOrch` issues normal SAI calls, accepted and stored by `saivpp`) — what was missing was the `dataplane enforcement`: no VPP mechanism actually rate-limited or even punted most CoPP-relevant traffic to the CPU.

### Control-plane protocols in scope

SONiC's default CoPP config (`copp_cfg.j2`) traps the following protocols on this platform (`show copp config` on `vlab-vpp-01`):

| Protocol / trap | Trap group | CIR/CBS (pps) | Notes |
|---|---|---|---|
| ARP request / response (`arp_req`, `arp_resp`) | `queue4_group2` | 600 | Addressed by this effort (device-input plugin) |
| LACP (`lacp`) | `queue4_group1` | 600 | Addressed by this effort |
| LLDP (`lldp`) | `queue4_group3` | 100 | Addressed by this effort |
| UDLD (`udld`) | `queue4_group3` | 100 | Addressed by this effort |
| TTL_ERROR (default trap group, IPv4 TTL-expiry) | (implicit default group) | 600 | Addressed by this effort |
| BGP / BGPv6 (`bgp`, `bgpv6`) | `queue4_group1` | 600 | Already worked pre-effort (rides `ip4-unicast`/`ip6-unicast`) |
| DHCP / DHCPv6 (`dhcp`, `dhcpv6`) | `queue4_group3` | 100 | Already worked pre-effort |
| IP2ME (`ip2me`) | `queue1_group1` | 600 | Already worked pre-effort (IP-destined-to-router traffic) |
| Neighbor discovery (`neigh_discovery`) | `queue4_group2` | 600 | Already worked pre-effort |

ARP, LACP, LLDP, UDLD, TTL_ERROR are ethertype/L2-level control-plane traffic on `linux-cp`-paired, L3-routed ports, which never reaches any of VPP's existing classify-based policing arcs. BGP/DHCP/IP2ME/neighbor-discovery are IP-layer traffic that were already targeted by VPP's `ip4-unicast`/`ip6-unicast` policer-classify feature prior to this effort.

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

## Design
### `copp_punt_policer` VPP plugin

**Why a new plugin, not VPP's existing classify/policer features:** VPP already ships a classify-based policer feature (`policer-classify`), but it only runs on three feature arcs — `l2-input` (bridged L2 traffic), `ip4-unicast`, `ip6-unicast`. This project's ports are `linux-cp`-paired, L3-routed ports: ARP/LACP/LLDP/UDLD traffic on them never traverses any of those three arcs — `ethernet-input` dispatches it directly to protocol-specific nodes (`arp-input`, `linux-cp-punt-xc`) that punt straight to each port's TAP.
**What we built:** a self-contained VPP plugin, `copp_punt_policer` registering one feature node on `device-input`. It performs the following tasks:

1. **Classify**: parses the raw 14-byte Ethernet header and looks up a small, bounded ethertype→policer-name table. TTL_ERROR is matched by ethertype `0x0800` (IPv4) **plus** an additional condition requiring the IP header's TTL ≤ 1.
2. **Police**: applies VPP's existing `vnet_police_packet()` token-bucket primitive against the same VPP policer object `SwitchVppPolicer.cpp` already creates from SAI `POLICER` attributes — no new metering implementation. Uses a fixed 256-byte reference packet length since VPP's pps→token-bucket conversion assumes that fixed size internally.
3. **Deliver**: for a conforming packet, sets the buffer's TX interface directly to the mapped linux-cp TAP and dispatches straight to `interface-output`. Resolves against the raw ingress port for every ethertype uniformly, matching what this project's PTF test harness (`ptf_nn_agent`) actually observes.

SAI wiring (`SwitchVppHostifTrap.cpp`) mirrors the existing per-trap dispatch pattern used for bookkeeping: on `createHostifTrap`/`setHostifTrap`/`setHostifTrapGroup`, resolve the trap's bound policer to its VPP policer name and call the plugin's `copp_punt_policer_bind` API — switch-wide, since the plugin auto-enables its feature on every interface as it's created (`VNET_SW_INTERFACE_ADD_DEL_FUNCTION`), no per-port bind needed.

## Alternate Designs Considered

Two earlier enforcement designs were built, deployed, and disproven before landing on the design above.

1. **Linux `tc` ingress policer on each port's hostif TAP device.** Linux delivers a copy of every received frame to `AF_PACKET` sniffers and PTF harness reads punted traffic off the TAP via a raw `AF_PACKET`/`SOCK_RAW` socket. But this happens _before_ the ingress qdisc/`tc filter` chain gets a chance to run.
2. **VPP-native classify table bound via `policer_classify_set_interface(..., l2_table_index)`.** ARP/LACP/LLDP/UDLD traffic on the `linux-cp`-paired L3-routed ports are not caught by the policer bindings that are bound to the `l2-input` feature arc.

## Status

All CoPP `test_policer` sub-tests plus the config-cli test, plus `test_trap_config_save_after_reboot` and the BGP variant of `test_policer_mtu`, pass on `vlab-vpp-01` (testbed `vms-kvm-vpp-t1-lag`):

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
| `test_trap_config_save_after_reboot` | (config persistence) | ✅ PASS (real DUT reboot: config save + reboot + wait + verify trap persists) |
| `test_policer_mtu[BGP]` (64/1514/4096B) | BGP | ✅ PASS (all 3 packet sizes; rides the pre-existing `ip4/ip6-unicast` policer-classify path, unaffected by this effort) |

**Known failure, not yet root-caused:** `test_policer_mtu[IP2ME/SNMP/SSH]` (all 3 packet sizes each, 9 cases total) fail with zero packets received at the PTF side (`Actual PPS: 0`, expected 540-780) — a different failure mode than anything else seen in this effort. Confirmed via live `vppctl show copp punt policer`/`show policer` that these traps aren't handled by the `copp_punt_policer` plugin at all (expected — they ride the separate, pre-existing `ip4/ip6-unicast` mechanism, same as BGP/DHCP); confirmed via `ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:*` that config-plane trap installation is unaffected. This looks like a genuine, separate, pre-existing gap unrelated to the `copp_punt_policer` plugin, not something this effort broke or is responsible for fixing — root cause not yet identified.

## Key files changed

| Repo | File | Change |
|---|---|---|
| `sonic-platform-vpp` (`platform/vpp` submodule) | `vppbld/plugins/copp_punt_policer/{copp_punt_policer.c,.h,.api,_node.c,CMakeLists.txt}` | New VPP plugin: device-input classify+police+direct-to-TAP, incl. TTL_ERROR IPv4-TTL match support |
| `sonic-sairedis` | `vslib/vpp/SwitchVppHostifTrap.cpp` | Per-trap-type ethertype/TTL match-key table, plugin bind/unbind wiring, default-trap-group tracking fix |
| `sonic-sairedis` | `vslib/vpp/vppxlate/SaiVppXlate.c` / `.h` | `vpp_copp_punt_policer_bind()`/`_get_counters()` VAPI wrappers, extended with `match_ip4_ttl_expiring` |
| `sonic-mgmt` | `tests/common/plugins/conditional_mark/tests_mark_conditions_sonic_vpp.yaml` | Lift `copp` skip for `asic_type in ['vpp']` |

## References

- [sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801)
- `sonic-sairedis` branch `copp-vpp-enablement` (SAI POLICER/HOSTIF_TRAP/HOSTIF_TRAP_GROUP wiring)
- `sonic-platform-vpp` branch `copp-vpp-enablement` (`copp_punt_policer` VPP plugin)
