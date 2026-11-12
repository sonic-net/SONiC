# SONiC-VPP CoPP Dataplane Enablement — HLD

## Revisions

| Rev | Date | Author(s) | Changes |
|-----|------|-----------|---------|
| 1.0 | 2026-09-02 | nhegde-microsoft | Initial HLD for the completed `copp_punt_policer` device-input plugin design. |
| 1.1 | 2026-09-18 | nhegde-microsoft | • Switched from ingress policing at device-input to egress policing at interface_output<br>• Migrated from standalone plugins to sonic_ext |
| 1.2 | 2026-09-20 | nhegde-microsoft | Added a node-graph summary. |

---

## Background

[sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801) asks to enable Control Plane Policing (CoPP) testing on SONiC-VPP, so `tests/copp/test_copp.py` in sonic-mgmt is no longer skipped for the `sonic-vpp` platform. The implementation is topology-agnostic and applies to any SONiC-VPP topology.

CoPP on real ASICs classifies control-plane protocols, traps them to the CPU, groups traps under trap-groups, and rate-limits each group with a policer. On SONiC-VPP, the SAI **config plane** already worked end-to-end before this effort (`orchagent`'s `CoppOrch` issues normal SAI calls, accepted and stored by `saivpp`) — what was missing was the **dataplane enforcement**: no VPP mechanism actually rate-limited or even punted most CoPP-relevant traffic to the CPU.

### Control-plane protocols in scope

This implementation programs the following traps from SONiC's default CoPP config (`copp_cfg.j2`):

| Protocol / trap | Trap group | CIR/CBS (pps) |
|---|---|---|
| ARP request / response (`arp_req`, `arp_resp`) | `queue4_group2` | 600 |
| LACP (`lacp`) | `queue4_group1` | 600 |
| LLDP (`lldp`) | `queue4_group3` | 100 |
| UDLD (`udld`) | `queue4_group3` | 100 |
| TTL_ERROR (default trap group, IPv4 TTL-expiry) | (implicit default group) | 600 |
| BGP / BGPv6 (`bgp`, `bgpv6`) | `queue4_group1` | 600 |
| IPv4 IP2ME (including SNMP/SSH traffic to tracked router addresses) | `queue1_group1` | 600 |
| DHCP / DHCPv6 (`dhcp`, `dhcpv6`) | `queue4_group3` | 100 (300 on management devices) |
| Neighbor miss (`neighbor_miss`) | `queue1_group3` | 200 |

Other SAI trap types are stored by `saivpp` but do not install a VPP CoPP binding in this implementation.

The implemented paths on `linux-cp`-paired ports include:

- **EtherType-based L2 traffic** — ARP, LACP, LLDP
- **LLC/SNAP traffic** — UDLD
- **L3 punt traffic** — IPv4 IP2ME/SNMP/SSH and BGP/BGPv6
- **IPv4 transit TTL expiry** — TTL_ERROR
- **DHCP traffic** — classifier-driven DHCPv4/DHCPv6 on VLAN members and receive-route handling on routed interfaces
- **Unresolved next-hop traffic** — IPv4/IPv6 NEIGHBOR_MISS on routed interfaces, subinterfaces, bonds, and BVIs

## Requirements

| # | Requirement |
|---|-------------|
| REQ-1 | Creating, updating, or removing a SAI `POLICER` object must synchronously create, replace, or delete the mapped native VPP policer using the attribute mappings described below. |
| REQ-2 | A SAI `HOSTIF_TRAP` with packet action `TRAP` or `COPY` must install the implemented VPP binding for ARP request/response, LACP, LLDP, UDLD, TTL_ERROR, IP2ME, BGP/BGPv6, DHCP/DHCPv6, or NEIGHBOR_MISS. |
| REQ-3 | Matched traffic with a named policer must pass through the VPP policer bound to the trap's `HOSTIF_TRAP_GROUP`. DROP and HANDOFF results are dropped; TRANSMIT and MARK_AND_TRANSMIT results pass without DSCP re-marking. An active unpoliced DHCP or NEIGHBOR_MISS row preserves trap delivery, while an unresolved non-empty policer name fails closed. |
| REQ-4 | Removing/disabling a trap at runtime (`test_add_new_trap`, `test_remove_trap`) must add/remove the corresponding classify/punt binding immediately, with no swss/syncd restart required. |
| REQ-5 | SAI `getStatsExt` on a mapped `POLICER` object must return cumulative `SAI_POLICER_STAT_GREEN/YELLOW/RED_PACKETS/BYTES` values from VPP's conform/exceed/violate counters. |
| REQ-6 | Trap/trap-group/policer configuration must persist and be re-applied after `config save` + reboot, matching existing SONiC CoPP semantics. |
| REQ-7 | The feature must not regress existing ACL, FDB, VLAN-admission, or routing dataplane behavior in `saivpp`; CoPP uses dedicated SAI object dispatch, `sonic_ext` nodes, and narrowly scoped core-VPP hooks for TTL_ERROR and IPv6 neighbor resolution. |

## Design: `sonic_ext` classify + policer nodes

The nodes below handle L3 host-bound traffic, Ethernet L2 traffic, LLC/SNAP UDLD, transiting IPv4 TTL expiry, DHCP traffic delivered by the existing saivpp classifier/receive-route paths, and unresolved next-hop traffic. Policing runs in `sonic-ext-copp-ip2me` for ordinary L3 traffic and in `sonic-ext-copp-ifout` for Ethernet, UDLD, TTL_ERROR, DHCP/DHCPv6, and NEIGHBOR_MISS. Both policing paths call `vnet_police_packet()` against the named VPP policer bound from the trap's SAI trap group.

All CoPP dataplane nodes live in the existing `sonic_ext` VPP plugin. `SwitchVpp` synchronously dispatches SAI `POLICER`, `HOSTIF_TRAP_GROUP`, and `HOSTIF_TRAP` operations; its CoPP mutex protects the policer, trap-group, trap, and effective-binding maps, while VPP RPCs run outside the lock. A trap group's `POLICER` selects the VPP binding; `ADMIN_STATE` and `QUEUE` are cached but are not programmed into VPP. Binding updates program VPP before committing the replay cache and restore the previous effective row on failure. The binding journal distinguishes an absent row from an active row with no policer and from a named-policer row. DHCPv4 and DHCPv6 each have one physical row shared by all SAI owners of that family; TRAP dominates until every installed owner requests COPY, and action-only updates preserve the current row owner. IPv4 router-interface address changes also update the IP2ME tracked-address set.

Although SAI CoPP defaults to PPS, this implementation supports both PPS and KBPS metering. CIR/PIR populate VPP's 32-bit CIR/EIR fields; in PPS mode, packet CBS/PBS values are converted to VPP millisecond burst windows, while KBPS mode uses byte-based bursts directly. SR_TCM uses 1R3C only when PBS is present, TR_TCM uses 2R3C only when PIR is present, and other cases use 1R2C. Both color-aware and color-blind policing are supported. FORWARD/COPY/LOG/TRANSIT map to transmit; DENY/DROP map to drop.

Policer metrics are read through the reentrant VPP statistics client. `vpp_stats_dump()` reads `/net/policer/` and accumulates per-worker conform, exceed, and violate packet and byte counters for the native policer. `getStatsExt` exposes those values as the corresponding SAI green, yellow, and red counters.

1. **`sonic-ext-copp-ip2me` / `sonic-ext-copp-ip2me-ip6`** (L3) — global features on `ip4-punt` and `ip6-punt`. IPv4 matches registered destination addresses for IP2ME/SNMP/SSH or TCP source/destination port 179 for BGP; the TCP-port slot takes precedence when both match. An active DHCPv4 row bypasses the generic IP2ME policer so DHCP is metered exactly once at `sonic-ext-copp-ifout`. IPv6 matches TCP/179 for BGPv6 when TCP directly follows the base IPv6 header.
2. **`sonic-ext-copp-ifout`** (host-TAP output) — a feature on `interface-output` of non-aggregate LCP host TAPs. It walks up to two 802.1Q/802.1ad tags, then matches ARP, LACP, and LLDP by EtherType, UDLD structurally, TTL_ERROR by IPv4 EtherType plus TTL≤1, DHCP by its UDP client/server ports, and NEIGHBOR_MISS by an explicit per-buffer reason. DHCP has priority over TTL_ERROR and plain EtherType rows. An empty policer name is the active-unpoliced form for DHCP and NEIGHBOR_MISS; a non-empty name that cannot be resolved is dropped.
3. **`sonic-ext-copp-udld`** (LLC/SNAP) — registered only for Cisco-OUI UDLD SNAP traffic. It restores the intact Ethernet frame, selects the ingress PHY's paired LCP TAP, initializes the `interface-output` arc, and hands the packet to `sonic-ext-copp-ifout` for structural reclassification and policing.
4. **`sonic-ext-copp-ttl-punt`** (IPv4 transit TTL expiry) — a conditional `ip4-rewrite` hook redirects the original TTL-expired packet to the ingress PHY's LCP TAP and then to `sonic-ext-copp-ifout` when the TTL_ERROR trap is installed. Without the trap, VPP retains its stock `ip4-icmp-error` behavior.
5. **saivpp DHCP classifier and receive routes** — VLAN-member DHCPv4 TRAP uses the existing fixed-offset tagged/untagged `l2-input-classify` sessions. DHCPv6 TRAP uses equivalent tagged/untagged sessions matching destination MAC `33:33:00:01:00:02`. For COPY, the corresponding sessions are removed so normal bridge flooding supplies the BVI copy. DHCPv4 uses a local-receive `255.255.255.255/32` route while its semantic trap is active. DHCPv6 COPY programs `ff02::1:2/128` with an MFIB Accept path on each BVI and a shared local Forward path; routed interfaces receive the same Accept-plus-local entry whenever DHCPv6 is active. These paths converge on `sonic-ext-copp-ifout`, which recognizes UDP 67/68 or 546/547 and applies the DHCP family’s trap-group policer.
6. **`sonic-ext-glean-redirect`** (NEIGHBOR_MISS) — a global feature on `ip4-drop` and `ip6-drop`. For drops from the IPv4/IPv6 neighbor-resolution nodes, it validates an unresolved connected adjacency, restores the ingress frame, redirects it to the ingress member's LCP TAP, and stamps the NEIGHBOR_MISS reason consumed by `sonic-ext-copp-ifout`. An active NEIGHBOR_MISS row supersedes the legacy fixed glean throttle.

The NEIGHBOR_MISS stamp uses plugin-private, buffer-indexed side-band storage rather than a classifier or a neighbor/adjacency-keyed table. The facility allocates one 8-byte `sonic_ext_vnet_buf_t` slot per VPP buffer position while it has an active claimant. One `VNET_BUFFER_F_AVAIL2` bit is the per-buffer-incarnation witness, and one bit in the slot's validity bitmap identifies the NEIGHBOR_MISS field. `sonic-ext-glean-redirect` claims that field after validating the miss; `sonic-ext-copp-ifout` consumes it at most once. A buffer-free callback clears slots, while the incarnation flag prevents stale side-band data from a DPDK-recycled buffer from being trusted. If another facility already owns the required buffer callback, binding fails closed instead of enabling an unsafe fallback. Thus the resource cost is linear in configured VPP buffer positions, not in neighbors, routes, or unresolved adjacencies.

### Node-graph summary

```
ip4-input (host-bound)  ->  ip4-punt  ->  sonic-ext-copp-ip2me  ->  {police -> ip4-punt-redirect | ip4-drop}
                                                (IPv4 IP2ME/SNMP/SSH by dst-IP; BGP by TCP src/dst port 179)

ip6-input (host-bound)  ->  ip6-punt  ->  sonic-ext-copp-ip2me-ip6  ->  {police -> ip6-punt-redirect | ip6-drop}
                                                (BGPv6 by TCP src/dst port 179)

linux-cp-punt / linux-cp-punt-xc  ->  interface-output (LCP host TAP)  ->  sonic-ext-copp-ifout  ->  {police -> TAP | drop}
                                                (ARP/LACP/LLDP by inner EtherType)

ethernet-input  ->  llc-input  ->  snap-input  ->  sonic-ext-copp-udld  ->  sonic-ext-copp-ifout  ->  {police -> TAP | drop}
                                                (Cisco-OUI UDLD SNAP)

ip4-rewrite (TTL expired, trap enabled)  ->  sonic-ext-copp-ttl-punt  ->  interface-output (ingress LCP TAP)
                                                        ->  sonic-ext-copp-ifout  ->  {police -> TAP | drop}

VLAN member -> l2-input-classify -> DHCPv4/DHCPv6 TRAP -> ingress LCP TAP
                                  -> COPY miss -> normal L2 flood -> BVI receive route -> host TAP
                                                        -> sonic-ext-copp-ifout -> {police -> TAP | drop}

routed DHCPv4/DHCPv6 -> local receive / MFIB Accept+local route -> host TAP
                                                        -> sonic-ext-copp-ifout -> {police -> TAP | drop}

ip4-arp/ip4-glean/ip6-glean/ip6-discover-neighbor -> ip4-drop/ip6-drop -> sonic-ext-glean-redirect
                                                        -> interface-output (ingress LCP TAP, NEIGHBOR_MISS reason)
                                                        -> sonic-ext-copp-ifout -> {police -> TAP | drop}
```

Each named binding references the native VPP policer selected by its SAI trap group. L3 IP2ME and BGP/BGPv6 traffic is policed in the IPv4/IPv6 IP2ME nodes; Ethernet, UDLD, TTL_ERROR, DHCP/DHCPv6, and NEIGHBOR_MISS traffic is policed in `sonic-ext-copp-ifout`.

## Alternate Designs Considered

Three earlier enforcement designs were built, deployed, and disproven or reworked before landing on the design above.

1. **A standalone `device-input` classify+police plugin (`copp_punt_policer`).** Worked, but appropriately pointed out in review that it ran unconditionally on every packet on every interface, taxing the ~100% of ordinary forwarded traffic that never matches. Reworked into the `interface-output`-arc design above, which only sees traffic already decided to be CPU-bound.
2. **Linux `tc` ingress policer on each port's hostif TAP device.** Looked correct (`tc -s filter show` reported real hits/drops matching the configured CIR), but was **structurally incapable of enforcing anything**: this project's PTF harness reads punted traffic off the TAP via a raw `AF_PACKET`/`SOCK_RAW` socket, and Linux delivers a copy of every received frame to `AF_PACKET` sniffers via the `netif_receive_skb_core`/`ptype_all` tap point — which fires **before** the ingress qdisc/`tc filter` chain gets a chance to run. Confirmed via a controlled veth-pair experiment inside syncd's own netns: a `tc ingress` drop-all filter reported 7/7 packets correctly dropped, yet a raw-socket receiver on the *same, filtered* device still received all 9 sent frames. Not fixable by tuning `tc`; the enforcement point was fundamentally downstream of the measurement point.
3. **VPP-native classify table bound via `policer_classify_set_interface(..., l2_table_index)`.** Technically correct VPP configuration (verified live: sessions created, correct policer bindings, ports bound), but bound to the `l2-input` feature arc — which this project's `linux-cp`-paired, L3-routed ports' ARP/LACP/LLDP/UDLD traffic never traverses at all (confirmed via `show classify tables verbose`: `hits 0` on every session even after a full test run). A genuine architecture mismatch, not a misconfiguration.

## Status

### Revised-head qualification

The implementation revisions aligned with this HLD are:

| Component | Revision | Scope |
|---|---|---|
| `sonic-platform-vpp` PR #326 | `e7434b4` | NEIGHBOR_MISS metadata/policing and DHCP-family `copp-ifout` policer selection; no DHCP node on the bridged IPv4/IPv6 hot path. |
| `sonic-sairedis` PR #2149 | `ff148db` | DHCPv4/DHCPv6 classifier TRAP, COPY flooding/BVI receive, routed receive routes, and transactional trap state. |
| `sonic-mgmt` PR #28577 | `9a4517f` | T0 enablement and CoPP test selection. |

Combined-image qualification of these exact revisions is **pending**. The acceptance run will execute `copp/test_copp.py` on both `t0-vpp` and `t1-lag-vpp`. In particular, VLAN-member DHCPv4/DHCPv6 TRAP must prove one CPU delivery with no peer flood, while COPY must prove peer forwarding plus one BVI CPU delivery. Results must not be inferred from routed-port tests or from the earlier baseline below.

### Historical baseline (before the DHCP/NEIGHBOR_MISS extension)

The earlier CoPP implementation passed all then-applicable `test_copp.py` cases on `t1-lag-vpp` (`vlab-vpp-01`):

| Test | Protocol | Historical result |
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
| `test_trap_neighbor_miss[IPv4/IPv6 × VlanSubnet/VlanSubnetIPinIP]` | NEIGHBOR_MISS | Not applicable on T1-LAG |
| `test_add_new_trap` | BGP (install fresh trap) | ✅ PASS |
| `test_remove_trap[delete_feature_entry]` | BGP (`redis-cli del FEATURE\|bgp`) | ✅ PASS |
| `test_remove_trap[disable_feature_status]` | BGP (`config feature state bgp disabled`) | ✅ PASS |
| `test_trap_config_save_after_reboot` | BGP (reboot persistence) | ✅ PASS |

This historical run predates PRs #326/#2149/#28577 and is retained only as regression context; it is not acceptance evidence for their revised heads.

### `test_remove_trap` fix (2026-09-18)

Both `test_remove_trap` tests (disable_feature_status and delete_feature_entry) were failing intermittently because `RX PPS` measurements would occasionally just outside the expected 540-780pps window. Root cause was a test-harness measurement bug. Although VPP trap statistics showed correct policed values, `BGPTest`'s reported `RX PPS` came from a raw NN/interface packet counter, which on any topology with live BGP sessions also counts real background BGP traffic sharing tcp/179 with the test's synthetic packets. 

Fix: `BGPTest` now measures `RX PPS` using its own existing content-matched packet count (`recv_count`, which was already being computed. Change scoped to `BGPTest` only.

## Key files changed

| Repo | File | Change |
|---|---|---|
| `sonic-platform-vpp` (`platform/vpp` submodule) | `vppbld/plugins/src/sonic_ext/{copp_ip2me_node.c, copp_ifout_node.c, copp_udld_node.c, copp_ttl_punt_node.c}` | IPv4/IPv6 punt policing, interface-output policing, and UDLD/TTL redirect nodes in the existing `sonic_ext` plugin. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/glean_redirect_node.c` | Semantic NEIGHBOR_MISS redirect. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/{copp_api.c, sonic_ext_copp.api}` | Compatibility-isolated DHCP and NEIGHBOR_MISS bind APIs. |
| `sonic-platform-vpp` | `vppbld/patches/0021-ip4-redirect-ttl-expired-to-copp-punt-hook.patch` | Conditional `ip4-rewrite` redirect to `sonic-ext-copp-ttl-punt` when TTL_ERROR is installed. |
| `sonic-platform-vpp` | `vppbld/patches/0025-ip6-preserve-packet-destination-during-neighbor-discovery.patch` | Preserve the original IPv6 packet while neighbor discovery runs so a miss can be redirected intact. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/{sonic_ext.api, sonic_ext_api.c, sonic_ext.h, sonic_ext.c}` | CoPP bind APIs, state, and IPv4/IPv6 feature enablement. |
| `sonic-platform-vpp` | `docker-syncd-vpp/conf/startup.conf.tmpl` | Enable the native VPP policer plugin used by the CoPP nodes. |
| `sonic-sairedis` | `vslib/vpp/SwitchVpp.cpp` / `.h`, `SwitchVppPolicer.cpp` / `.h` | SAI object dispatch, CoPP state, native policer lifecycle, attribute translation, and statistics. |
| `sonic-sairedis` | `vslib/vpp/SwitchVppHostifTrap.cpp` / `.h` | Transactional trap-group/trap state and L2, IP2ME, BGP/BGPv6, TTL_ERROR, DHCP/DHCPv6, and NEIGHBOR_MISS binding lifecycle. |
| `sonic-sairedis` | `vslib/vpp/SwitchVppFdb.cpp` | DHCPv4/DHCPv6 classifier TRAP/COPY handling, DHCPv4 limited-broadcast receive, and DHCPv6 MFIB receive lifecycle. |
| `sonic-sairedis` | `vslib/vpp/SwitchVppRif.cpp` | IPv4 router-interface address synchronization plus routed DHCPv4/DHCPv6 receive-route lifecycle. |
| `sonic-sairedis` | `vslib/vpp/vppxlate/SaiVppXlate.c` / `.h` | Native policer VAPI/statistics and `sonic_ext` CoPP bind wrappers. |
| `sonic-mgmt` | `tests/common/plugins/conditional_mark/tests_mark_conditions_sonic_vpp.yaml` | Lift `copp` skip for `asic_type in ['vpp']`. |
| `sonic-mgmt` | `ansible/roles/test/files/ptftests/py3/copp_tests.py` | `BGPTest`: measure `RX PPS` from the existing content-matched `recv_count` instead of the raw NN interface counter, to avoid counting real background BGP session traffic sharing tcp/179. |

## References

- [sonic-buildimage#25801](https://github.com/sonic-net/sonic-buildimage/issues/25801)
