# Router Interface Loopback Packet Action on VPP Dataplane: High Level Design

## Table of Contents

1. [Revisions](#1-revisions)
2. [Scope](#2-scope)
3. [Overview](#3-overview)
4. [Feature Description](#4-feature-description)
5. [SONiC Configuration](#5-sonic-configuration)
6. [SAI API Calls](#6-sai-api-calls)
7. [VPP Implementation](#7-vpp-implementation)
8. [Test Plan](#8-test-plan)
9. [Historical bring-up findings](#9-historical-bring-up-findings)
10. [Appendix A: File Change Summary](#appendix-a-file-change-summary)
11. [Appendix B: VPP API Reference](#appendix-b-vpp-api-reference)

---

## 1. Revisions

| Rev | Date | Author(s) | Changes |
|-----|------|-----------|---------|
| 1.0 | 07/05/2026 | Aaron Bernardino (aaronber@microsoft.com) | Initial version. |

---

## 2. Scope

This document describes the high level design for **router interface loopback packet action** on the
SONiC VPP dataplane. The feature implements the SAI attribute
`SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION`, which controls what happens to a packet that
ingresses on a router interface (RIF) and, after routing, resolves to a next-hop that egresses on
**that same RIF** (a "hairpin"). The action is either `FORWARD` (default) or `DROP`.

The feature implementation spans two repositories (a third, `sonic-mgmt`, carries only test enablement
and a testbed VM fix — see §8.2 and §9):

- **`sonic-platform-vpp`**: two new loopback nodes and a binary API added to the existing consolidated
  `sonic_ext` VPP plugin; they enforce the drop/forward decision in the VPP dataplane and increment the
  interface `tx-error` counter on drop.
- **`sonic-sairedis`**: the VPP-backed SAI implementation (`vslib/vpp`), which translates the SAI RIF
  attribute into a call to the `sonic_ext` plugin's binary API.

It enables the existing sonic-mgmt test
[`iface_loopback_action`](https://github.com/sonic-net/sonic-mgmt/tree/master/tests/iface_loopback_action)
to run on the `t1-lag-vpp` topology.

**In scope**

- A VPP plugin node on the IPv4 and IPv6 **output** feature arcs that drops a routed packet when its
  ingress interface equals its egress interface and the per-interface action is `DROP`.
- Per-interface state (action = forward/drop) settable via a binary API.
- Incrementing the existing VPP interface `tx-error` counter on each loopback drop, and adding
  `SwitchVpp::getRifStatsExt()` in saivpp so the SAI RIF `tx_err`
  (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`) reflects it (saivpp previously populated VPP counters
  only for ports, not RIFs; see §7.4).
- saivpp handling of `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` on RIF create and set, for all
  five RIF identifiers exercised by the test (ethernet, VLAN, port-channel/LAG, sub-port, port-channel
  sub-port).
- Advertising the attribute as supported only when the plugin's `iface-loopback` feature is enabled.

**Out of scope**

- Any loopback-action behaviour beyond `FORWARD`/`DROP` (e.g. trap/copy to CPU).
- Orchagent, SONiC CLI, or CONFIG_DB schema changes (these already exist upstream; see §5).
- Multicast hairpin handling (already covered by upstream VPP; see §3.4).
- Non-VPP ASIC behaviour and the sonic-mgmt test logic itself (only test enablement, in a separate PR).

---

## 3. Overview

### 3.1 Terminology

| Term | Meaning |
|------|---------|
| Hairpin / loopback | A routed packet whose resolved next-hop egresses the same RIF it ingressed on. Distinct from the RIF *type* `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK`, which is a different concept. |
| RIF identifiers | The five RIF shapes the test exercises (see §3.2). |
| `tx-error` | VPP per-interface simple counter at `/interfaces/<name>/tx-error`; mapped to the SAI RIF `tx_err` (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`) by `SwitchVpp::getRifStatsExt()` via `SaiIntfStats.c` (§7.4). |

### 3.2 RIF identifiers exercised by the test

The sonic-mgmt test labels its RIF scenarios with five names, but these are not five SAI RIF *types*.
There are three SAI types involved (`PORT`, `SUB_PORT`, `VLAN`); the count reaches five because the test
also varies the underlying interface between a physical port and a LAG (PortChannel, "PO"):

| Test case | Example interface | SAI RIF type | Underlying `PORT_ID` | VPP interface (via `VppInterfaceRegistry`) |
|-----------|-------------------|--------------|----------------------|--------------------------------------|
| `ETHERNET_RIF` (`ethernet`) | `Ethernet0` | `PORT` | physical port | hwif |
| `PO_RIF` (`po`) | `PortChannel0001` | `PORT` | LAG | `BondEthernet<id>` |
| `SUB_PORT_RIF` (`sub_port`) | `Ethernet0.10` | `SUB_PORT` | physical port | `<hwif>.<vlan>` |
| `PO_SUB_PORT_RIF` (`po_sub_port`) | `PortChannel0001.10` | `SUB_PORT` | LAG | `BondEthernet<id>.<vlan>` |
| `VLAN_RIF` (`vlan`) | `Vlan1000` (SVI) | `VLAN` | none (VLAN id) | BVI (`bvi<vlan>`) |

`PORT` and `SUB_PORT` each appear twice (over a physical port and over a LAG), plus `VLAN` once, totaling
five. Each shape resolves to a different VPP interface, and the drop node's `RX == TX` check keys on that
identity, so the feature must handle all five. The LAG shapes (`PO_RIF`, `PO_SUB_PORT_RIF`) are the
highest-risk because the identity must be the bond, not a member; the `VLAN_RIF` shape is distinct
because a VLAN RIF has no `PORT_ID` and must be resolved to the bridge BVI. §7.6 describes the
`VppInterfaceRegistry` RIF-OID binding that covers every shape above.

### 3.3 Summary

`SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` selects `FORWARD` (default) or `DROP` for a hairpin
packet (`SAI/inc/sairouterinterface.h`):

> *"Packet action when a packet ingress and gets routed on the same RIF."*
> `@type sai_packet_action_t`, `@flags CREATE_AND_SET`, `@default SAI_PACKET_ACTION_FORWARD`.

The SONiC-VPP stack programs the dataplane through SAI:

```
CONFIG_DB -> orchagent (intfsorch) -> ASIC_DB -> syncd -> SAI API
          -> saivpp (vslib/vpp) -> VPP binary API -> sonic_ext plugin (loopback nodes) -> drop / forward
```

This design implements the attribute in the last two stages: saivpp translates the SAI attribute into a
**VPP binary API** call, and the **`sonic_ext` plugin's loopback nodes** enforce it. The two integration
boundaries it crosses are the **SAI API** (syncd to saivpp) and the **VPP binary API** (saivpp to the
`sonic_ext` plugin), as labelled in the diagram above.

### 3.4 Why this is net-new on VPP

Stock fd.io VPP, in `src/vnet/ip/ip4_forward.c`, already compares
`adj.rewrite_header.sw_if_index == vnet_buffer(b)->sw_if_index[VLIB_RX]` and raises
`IP4_ERROR_SAME_INTERFACE`, **but only inside an `if (is_mcast)` guard** (and `ip6_forward.c` has no
equivalent `SAME_INTERFACE` check at all). For **unicast** traffic
(what this feature and the test exercise) VPP forwards the hairpin by default, with no per-RIF,
configurable drop/forward control. saivpp's `vslib/vpp` currently has **no** handler for the attribute
(verified: 0 references to `LOOPBACK_PACKET_ACTION` in `vslib/vpp` @ `7b3b8f3a`). The feature is
therefore genuinely net-new; this design reuses upstream's same-interface comparison idiom inside a new
plugin.

---

## 4. Feature Description

### 4.1 Motivation

The sonic-mgmt test `iface_loopback_action` could not pass on SONiC-VPP without this feature, because:

- saivpp does not implement `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION`; setting it is a no-op,
  so `drop` never takes effect and the `tx_err` assertion fails.
- The VPP dataplane forwards unicast hairpin packets unconditionally, so there is no way to drop
  same-RIF traffic per interface.

Without this, the test module stays disabled on `t1-lag-vpp`, leaving a SAI RIF behaviour unverified on
the VPP platform.

### 4.2 How the test forges the hairpin

The real-world use case is anti-loop / anti-spoof hardening: an operator drops (and counts) traffic
that would otherwise be reflected back out its ingress interface. The test
(`iface_loopback_action_helper.py`) reproduces this exactly:

1. Pick a RIF on PTF port *p*; install a **static neighbor** mapping `ip_dst` -> the MAC of PTF port
   *p* on that same RIF, so the route for `ip_dst` points back out the ingress interface.
2. Send `NUM_OF_TOTAL_PACKETS` (= 10) packets into port *p* with `eth_dst = router_mac` (forces L3
   routing) and that `ip_dst`.
3. The DUT routes them; the next-hop egresses port *p* -> hairpin.

### 4.3 Expected behaviour

For a routed unicast packet whose next-hop egresses its ingress RIF:

| RIF action | VPP behaviour | Counter | Test assertion |
|------------|---------------|---------|----------------|
| `FORWARD` (default) | packet egresses the same RIF (TTL 121->120) | RIF `tx_err` unchanged | `verify_packet` passes |
| `DROP` | packet dropped at the `ip4/6-loopback` node | RIF `tx_err` += dropped count | `verify_no_packet` passes; `tx_err == 10` |

Behaviour is identical for IPv4 and IPv6 and for all five RIF identifiers. Non-hairpin traffic
(`VLIB_RX != VLIB_TX`) is never affected, regardless of action.

### 4.4 Approach: Track-2 plugin (alternatives considered)

The team ships SAI-feature-specific dataplane behaviour in one of two tracks:

| Track | When | Precedent |
|-------|------|-----------|
| **Track 1, core VPP patch** in `vppbld/patches/*.patch` (with a gerrit `Change-Id`, upstreamed to fd.io) | Generic protocol/datapath capability useful to the whole community | inner-aware flow hash (`0011`), ipip mp2p (`0009`) |
| **Track 2, self-contained plugin** in `vppbld/plugins/<name>/` | SAI-feature-specific, per-interface datapath node | `ip_validate`, `tunterm_acl` |

**Decision: a VPP plugin node, hosted in the consolidated `sonic_ext` plugin.** The nearest
precedent is `ip_validate`, a per-interface unicast drop node + counter, mechanically almost
identical to loopback-action. A plugin node avoids a core forwarding-path change and the
multi-month fd.io review cycle, and is easy to maintain/revert. Rather than adding a separate
standalone plugin, the two loopback nodes and their control API are added to **`sonic_ext`** —
the upstream plugin (sonic-platform-vpp #255) that is the designated home for custom SONiC VPP
dataplane nodes (BVI/VLAN punt, host cross-connect, L2 trap fixup, …). This keeps all
SONiC-specific VPP extensions in one plugin.

**Alternatives rejected:**

- **Track 1, generalize the multicast-only `SAME_INTERFACE` check** into a per-RIF unicast control and
  upstream it. Rejected for this story (heavier, slower, not the team pattern); revisitable later.
- **A separate standalone plugin.** Rejected in favour of hosting the node inside `sonic_ext` (see above).
- **No-op / counter-only.** Rejected: the test sends real traffic and asserts both packet drop and the
  `tx_err` increment, so a logical-only implementation would not pass.

### 4.5 Compatibility and impact

The dataplane loopback check is additive and opt-in per interface. The accompanying saivpp
counter and CREATE changes also affect RIFs that do not configure `DROP`:

- The default action is `FORWARD`, which leaves the `sonic-ext-ip4-loopback`/`sonic-ext-ip6-loopback`
  node **disabled** on the interface's output arc. Interfaces without `loopback-action drop` pay
  **zero** loopback-node per-packet cost, no forwarding change from this check, and no
  loopback-node counter increments. This does not mean their SAI RIF counters remain zero.
- No existing VPP node, arc, default, or counter definition is modified; two new nodes and a new
  binary API are added to the `sonic_ext` plugin. There is no ABI/CRC or
  submodule-ordering concern beyond the `VPP_VERSION` bump (§7.1), because no existing message or core
  header changes.
- Per-interface state is one `u8` in a vector indexed by `sw_if_index`, so there is no scaling concern
  with port/RIF count.
- The drop decision is interface-identity based (`VLIB_RX == VLIB_TX`), independent of VRF and IP, so
  duplicate addresses across VRFs do not affect it.
- `getRifStatsExt()` exposes real VPP-backed packet, byte, and error counters for all backed
  PORT/LAG, SUB_PORT, and VLAN RIFs, not just those using loopback action. Counter consumers now
  see baseline-relative values rather than the previous zero values; creation and clear epochs,
  query failures, and parent/sub-interface overlap are described in §7.4.
- RIF CREATE is transactional regardless of loopback action (§7.6). Interface programming,
  registration, and the initial counter snapshot must succeed before the SAI object is committed.
  Failures unwind newly acquired resources and restore changed persistent-interface settings
  (IPv4 VRF, protocol MTUs, admin state, and the CREATE's own MPLS mutation). These are general
  RIF lifecycle changes, not conditional on enabling the loopback nodes.

---

## 5. SONiC Configuration

**No SONiC control-plane changes are required.** The CLI, CONFIG_DB/APPL_DB schema, and orchagent
handling already exist upstream; this section documents the top-to-bottom mapping for reference.

Operator commands:

```
config interface ip loopback-action <interface> <forward|drop>
show ip interfaces loopback-action          # read back
```

CONFIG_DB representation (the `loopback_action` field is set on whichever `*_INTERFACE` table owns the
RIF):

```
INTERFACE|Ethernet0                  loopback_action: drop
VLAN_INTERFACE|Vlan1000              loopback_action: drop
PORTCHANNEL_INTERFACE|PortChannel1   loopback_action: drop
VLAN_SUB_INTERFACE|Ethernet0.100     loopback_action: drop
```

End-to-end mapping:

| Layer | Representation |
|-------|----------------|
| CLI | `config interface ip loopback-action <intf> drop` |
| CONFIG_DB | `*_INTERFACE` table, `loopback_action = drop` |
| APPL_DB | `INTF_TABLE:<intf>` `loopback_action` (propagated by intfmgrd) |
| orchagent | `intfsorch` sets `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` on the RIF |
| ASIC_DB / syncd | RIF attribute create/set |
| saivpp | `SwitchVppRif` -> `SaiVppXlate` (§6, §7.6) |
| VPP | `sonic_ext_iface_loopback_set_action { sw_if_index, action }` (§7.5) |

The intended restoration paths need no plugin-side persistence: orchagent re-applies the action from
CONFIG_DB (cold/fast boot), or syncd replays it from ASIC_DB (warm boot), re-issuing the RIF operation
to saivpp. **Warm-boot replay has not been validated for this feature on VPP**; it is an expected
restoration path, not a verified result. `test_loopback_action_reload` uses **cold** reboot by
default (§8.1); the current validation limits are recorded in §8.4.

---

## 6. SAI API Calls

### 6.1 Changed SAI operations

No new SAI attribute, object type, or behaviour is introduced; the attribute
`SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` already exists in the SAI headers saivpp builds
against (`SAI/inc/sairouterinterface.h`; SAI submodule `c67f115`; **no SAI bump required**). The work is
to make saivpp **honour** it on RIF create and set; capability is already advertised (§6.3).

saivpp currently handles these RIF attributes on the create/set paths (verified in `SwitchVppRif.cpp`
@ `7b3b8f3a`): `TYPE`, `PORT_ID`, `OUTER_VLAN_ID`, `VIRTUAL_ROUTER_ID`, `MTU`, `ADMIN_V4_STATE`,
`ADMIN_V6_STATE`. This path has **no** `LOOPBACK_PACKET_ACTION` handling — that is what this change
adds. (`SRC_MAC` is set only on the separate VLAN BVI create path in `SwitchVppFdb.cpp`, not on this
`SwitchVppRif.cpp` path.)

### 6.2 Affected SAI path

| SAI call (already exists) | What changes inside saivpp |
|---|---|
| `sai_router_interface_api->create_router_interface()` -> `SwitchVpp::vpp_create_router_interface()` | If `LOOPBACK_PACKET_ACTION` is present, resolve the RIF interface and program the plugin; if absent, send nothing (the plugin default `FORWARD` stands). |
| `sai_router_interface_api->set_router_interface_attribute()` -> `SwitchVpp::vpp_update_router_interface()` | Same, on attribute change. |
| `SwitchVpp::createRouterif()` dispatch | Program the interface, bind its RIF OID, snapshot counters, and persist the SAI object; roll back on failure (§7.6). |

### 6.3 Capability query

`SwitchVpp::queryAttributeCapability` (`vslib/vpp/SwitchVpp.cpp`) handles
`SAI_OBJECT_TYPE_ROUTER_INTERFACE` / `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` explicitly.
It calls the status-returning `sonicExtFeatureEnabled("iface-loopback", enabled)` helper:

| Feature query result | Capability result |
|---|---|
| Enabled | `SAI_STATUS_SUCCESS`; create, set, and get flags are all `true`. |
| Disabled | `SAI_STATUS_SUCCESS`; all three flags are `false`. |
| Query failure | `SAI_STATUS_FAILURE`; no successful capability result is reported. The failed query is not cached, so a later call can retry. |

Successful feature queries are cached because the feature setting is fixed at VPP startup. The
feature defaults to enabled; deployments can disable it in the `sonic-ext` startup stanza. Other
objects and attributes retain their existing capability behavior. This reporting is part of the
implementation, not a deferred follow-up.

---

## 7. VPP Implementation

### 7.1 Component Overview

The feature lives in the existing **`sonic_ext`** plugin (`vppbld/plugins/src/sonic_ext/`), the
consolidated home for custom SONiC VPP dataplane nodes. It adds two output-arc nodes and extends
the plugin's existing binary API and feature framework:

```
vppbld/plugins/src/sonic_ext/
  sonic_ext.api            (edit) define sonic_ext_iface_loopback_set_action { sw_if_index, action }
  ip4_loopback_node.c      (new)  IPv4 output-arc node  (node "sonic-ext-ip4-loopback")
  ip6_loopback_node.c      (new)  IPv6 output-arc node  (node "sonic-ext-ip6-loopback")
  sonic_ext.h              (edit) IFACE_LOOPBACK feature entry, action vector, declarations
  sonic_ext.c              (edit) set-action function and interface delete-reset hook
  sonic_ext_api.c          (edit) API handler using the existing message-ID table
  CMakeLists.txt           (edit) add the two nodes
  FEATURE.yaml             (edit) add the iface-loopback feature
```

The plugin directory is auto-copied into VPP's `src/plugins/` at build time; **no
`vppbld/patches/series` change is needed** (only *patches* are registered there). Bump
`VPP_VERSION` in `rules/vpp.mk` (the deb cache key) so downstream builds don't reuse a stale
cached VPP deb without the new nodes.

> `sonic_ext` is **already** enabled in both `docker-syncd-vpp/conf/startup.conf.tmpl` and
> `docker-sonic-vpp/conf/startup.conf.tmpl`, so **no startup.conf change is
> needed** — the loopback nodes and the `sonic_ext_iface_loopback_set_action` binary API load with the rest of
> `sonic_ext`.

### 7.2 Feature arc

The nodes register on the **output** arcs (not the `*-unicast` input arcs used by `ip_validate`)
because the egress interface (`VLIB_TX`) is only known after lookup/rewrite:

```c
VNET_FEATURE_INIT (sonic_ext_ip4_loopback_feat, static) = {
  .arc_name    = "ip4-output",
  .node_name   = "sonic-ext-ip4-loopback",
  .runs_before = VNET_FEATURES ("interface-output"),
};
```

The IPv6 registration has the same constraint on `ip6-output`. The loopback nodes require ordering
before `interface-output`, but specify no relative priority against egress ACLs or other features
on the same IP output arc. Their relative order follows VPP's feature graph; this design does not
promise ACL-before-loopback or loopback-before-ACL. A packet dropped by an earlier feature never
reaches the loopback check and does not increment its `tx-error`; a loopback drop bypasses later
output features. In contrast, nodes on the subsequent `interface-output` arc, such as
`sonic-ext-egress-mirror` and `sonic-ext-copp-ifout`, run after this check and cannot see packets
dropped here. Any feature that changes the RIF identity before this check must preserve the §7.3
identity condition or require an explicit ordering dependency.

The node is enabled on an interface's `ip4-output`/`ip6-output` arcs **only while its action is
`DROP`** (enable on the `FORWARD`→`DROP` transition, disable on `DROP`→`FORWARD`; repeated same-action
requests are a no-op because VPP's feature enable/disable is ref-counted), so there is zero
per-packet cost on interfaces that do not use the feature.

> ⚠️ **Do not copy `ip_validate`'s auto-enable.** `ip_validate` enables itself on *every* interface via
> `VNET_SW_INTERFACE_ADD_DEL_FUNCTION`. The loopback nodes must enable the arc only on `DROP`.

### 7.3 Node algorithm (per IP family)

```
rx = vnet_buffer(b)->sw_if_index[VLIB_RX];
tx = vnet_buffer(b)->sw_if_index[VLIB_TX];
if (rx == tx && per_interface_action[tx] == DROP) {
    increment interface tx-error on tx (see §7.4);
    next = error-drop;
} else {
    vnet_feature_next(&next, b);   // continue the output arc
}
```

Per-interface state is a `u8` action vector indexed by `sw_if_index`, defaulting to `FORWARD`. Copy the
batching / trace structure from `ip_validate`'s node; only the check and the counter differ.

**Interface identity for LAG and sub-ports.** The `RX == TX` test compares the RIF's own `sw_if_index`,
which is what both `VLIB_RX` and `VLIB_TX` carry on the output arc:

- LAG RIF: `bond-input` rewrites `VLIB_RX` to the bond `sw_if_index` on member ingress, and egress out
  the bond sets `VLIB_TX` to the same bond index, so `RX == TX` holds at the bond. The action vector is
  keyed on the bond index (the interface saivpp resolves through `VppInterfaceRegistry`, §7.6).
- Sub-port / LAG sub-port RIF: ingress classification and egress both use the sub-interface
  (`<hwif>.<vlan>` / `<bond>.<vlan>`) `sw_if_index`, so the comparison and the action key are the
  sub-interface index.

This is the correctness condition for the `PO_RIF` / `PO_SUB_PORT_RIF` cases (half the t1-lag matrix) and
is exercised by the sonic-mgmt integration test (§8.1; validation scope is described in §8.4).

> ⚠️ **Limitation — decapsulated traffic re-routed out its ingress RIF.** The `RX == TX` test relies on
> `VLIB_TX` still carrying the RIF's own `sw_if_index` when the loopback node runs on the output arc.
> For transit traffic that is **decapsulated** (IPinIP / VXLAN / GRE) and then routed back out the
> **same** RIF it arrived on, VPP overwrites `VLIB_TX` with the **tunnel** interface's `sw_if_index`
> before the `interface-output` arc, so `RX != TX` at the loopback node and the hairpin is **not**
> dropped even with `DROP` configured. This feature targets plain routed hairpins — what the SAI
> attribute describes and the test forges (§4.2); decap-then-hairpin through a tunnel is out of scope
> and would require the check to compare the pre-decap ingress interface instead. Documented so the
> behaviour is explicit rather than surprising.

### 7.4 Counter

The node increments VPP's per-interface **`tx-error`** counter on the egress `sw_if_index`. The
test asserts on the SAI RIF `tx_err` (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`, surfaced by
`show interfaces counters rif`).

The drop is implemented in two parts: the buffer is enqueued to `error-drop` with
`b->error = node->errors[HAIRPIN_DROP]` (the node-level diagnostic count, visible in `vppctl show
errors`), and the interface counter the test reads is bumped explicitly with
`vlib_increment_simple_counter(vnm->interface_main.sw_if_counters + VNET_INTERFACE_COUNTER_TX_ERROR,
thread_index, tx_sw_if_index, 1)`.

**SAI counter mapping.** `SwitchVpp::getRifStatsExt()` resolves the backing interface through
`m_ifaceRegistry.resolveHwIfByRifOid()` (§7.6) and reads `/interfaces/<name>/*` through
`queryRifStats()` / `vpp_intf_stats_query()`. RX/TX packets, bytes, and errors map to the six
corresponding `SAI_ROUTER_INTERFACE_STAT_*` counters; `tx-error` maps to
`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`. RIF types without a backing VPP interface return
zero counters without allocating a baseline.

**Ingress-side accounting.** VPP's `error-drop` path also increments
`/interfaces/<rx>/drops` using `VLIB_RX`, including the super-interface's `drops` for a
sub-interface. A hairpin therefore increments both `tx-error` and `drops` on its backing
interface, but these are two views of the same discarded packet, not two packet losses.
`SaiIntfStats.c::handle_stat_one()` keeps `drops` and `rx-error` separate, and `queryRifStats()`
maps only `rx-error` to `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS`; it does not map `drops`
into a SAI RIF counter. Thus the expected loopback-drop delta is one
`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS` and no increment of
`SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS` from this drop. The generic ingress `drops`
increment must not be interpreted as an additional SAI RIF RX error.

`initializeRifStats()` snapshots these counters at RIF creation, so a new port/LAG RIF does not
inherit traffic from an earlier RIF on the same persistent interface. READ_AND_CLEAR returns the
delta from the previous baseline and advances only the requested counters' baselines. A detected
VPP counter reset discards the affected baseline. Query failures return failure without changing
the baseline or acknowledging a clear. RIF removal discards its baseline. Metadata unit-test
counter injection and reads continue to use the base virtual-switch implementation.

**Parent/sub-interface accounting limitation.** If a RIF is configured on a physical interface
and another on one of its VLAN sub-interfaces, the physical interface's packet/byte counters
include both untagged traffic and tagged child traffic. The child also has its own counters.
Consequently, the parent RIF's packet/byte statistics are inclusive backing-interface totals,
**not exclusive untagged-RIF counters**. Summing the parent and child RIF statistics double-counts
the child traffic. RIF-specific baselines separate creation/clear epochs; they do not change
this VPP accounting model. Exclusive per-RIF packet/byte accounting is outside this loopback-action
change.

The loopback node's own `TX_ERROR` increment is different: it explicitly targets the selected
egress `sw_if_index`. A sub-interface hairpin drop is counted on that sub-interface, without an
additional parent increment by this node. Packet/byte overlap should not be taken to imply that
all error counters have the same aggregation behavior.

> ⚠️ **Counter API differs from `ip_validate`.** `ip_validate` counts via a VPP **node** error counter
> (`vlib_node_increment_counter`), which appears only in `vppctl show errors` and is **not** a
> per-interface stat. The explicit `vlib_increment_simple_counter` on `VNET_INTERFACE_COUNTER_TX_ERROR`
> is what `getRifStatsExt` surfaces as RIF `tx_err`; the node-level `error-drop` count is diagnostic only.

### 7.5 Binary API

```
autoreply define sonic_ext_iface_loopback_set_action
{
  u32 client_index;
  u32 context;
  vl_api_interface_index_t sw_if_index;   // resolved by the binding (see §7.7)
  u8  action;                             // 0 = FORWARD, 1 = DROP
};
```

The handler stores `action` for the interface and, on an actual `FORWARD`↔`DROP` transition, calls
`vnet_feature_enable_disable("ip4-output", "sonic-ext-ip4-loopback", sw_if_index, action == DROP, 0, 0)`
(and the IPv6 equivalent), with rollback of both the arc state and the stored action on partial failure.
Repeated same-action requests are a no-op (VPP feature enable/disable is ref-counted).

### 7.6 saivpp binding

**Attribute handling** (`vslib/vpp/SwitchVppRif.cpp`), on both `vpp_create_router_interface` and
`vpp_update_router_interface`:

1. Look for the `LOOPBACK_PACKET_ACTION` attribute. If it is **absent**, send nothing — the plugin's
   default `FORWARD` applies. If present, read its `sai_packet_action_t` value and continue.
2. **Resolve the RIF to its VPP interface.** CREATE uses the existing
   `m_ifaceRegistry.resolveHwIfName(backing_oid, vlan_id)` mapping: physical port to hwif, LAG to
   `BondEthernet<id>`, sub-port to the corresponding `.<vlan_id>` child, and VLAN to its BVI.
   `vpp_register_router_interface()` records the RIF OID with `setRifOid()` in a separate registry
   index; it does not replace the backing port/LAG/VLAN OID. SET, REMOVE, and statistics use
   `resolveHwIfByRifOid()`, avoiding a second name-parsing resolver. VLAN RIF CREATE is handled by
   `vpp_create_bvi_interface()` and binds the same BVI record.

   The test's "five RIF types" map to **three** SAI RIF *types* (`PORT`, `SUB_PORT`, `VLAN`); `PO_*` are
   `PORT`/`SUB_PORT` whose `PORT_ID` is a LAG. (The SAI RIF `TYPE_LOOPBACK` is a different, unrelated
   concept — see §3.1 — and is not exercised here.)
3. Reject actions other than `FORWARD`/`DROP` with `SAI_STATUS_NOT_SUPPORTED`. Query
   `sonicExtFeatureEnabled("iface-loopback", enabled)`; query errors fail the operation.
   With the feature explicitly disabled, neither action sends a plugin call: `FORWARD` may
   return `SAI_STATUS_SUCCESS` as a no-op, but `DROP` must return `SAI_STATUS_NOT_SUPPORTED`,
   without committing the requested action. Capability is also false (§6.3), but capability
   reporting alone does not enforce this CREATE/SET contract.
   Otherwise map `SAI_PACKET_ACTION_FORWARD` -> `0`, `SAI_PACKET_ACTION_DROP` -> `1`.
4. Resolve the hwif name to a `sw_if_index` with the existing `get_swif_idx()` helper and send the
   message (see §7.7).

`vpp_apply_loopback_action()` enforces the disabled-feature status in the adapter correction in
[sonic-net/sonic-sairedis#2144](https://github.com/sonic-net/sonic-sairedis/pull/2144).
CREATE propagates a rejected `DROP` without committing the SAI object, and SET returns before
updating the stored action. `FORWARD` remains a successful no-op. The merged baseline and
follow-up validation are distinguished in §8.4.

**API helper** (`vslib/vpp/vppxlate/SaiVppXlate.c` / `.h`), following the `tunterm_acl` /
`set_ip_flow_hash_v2` binding pattern:

- `#include <vpp_plugins/sonic_ext/sonic_ext.api_enum.h>` and `..._types.h` (the `sonic_ext` plugin now carries
  the `sonic_ext_iface_loopback_set_action` message).
- Reuse the canonical `sonic_ext` plugin message-ID base registered during init.
- Add a reply handler and a send helper `vpp_iface_loopback_set_action(const char *hwif_name, int action)`
  that calls `get_swif_idx()` to obtain the `sw_if_index`, then issues the message via the
  `M(SONIC_EXT_IFACE_LOOPBACK_SET_ACTION, mp)` macro (balanced `VPP_LOCK()`/`VPP_UNLOCK()` on every path).

**Idempotency and teardown.** Create-with-attribute and a later set reach the same handler; re-sending
the same action is a no-op (the plugin toggles the arcs only on a real transition), and `DROP` ->
`FORWARD` disables the arcs and restores the per-interface state to `FORWARD`. On the SAI side the
loopback action is applied symmetrically on RIF create (including VLAN RIFs, via `vpp_create_bvi_interface`)
and cleared to `FORWARD` on RIF remove, so a recycled `sw_if_index` cannot inherit a stale `DROP`.
Removal clears the RIF-OID binding without deleting a persistent port/LAG registry record.

**Failed CREATE rollback.** `createRouterif()` commits the SAI object only after interface
programming, RIF registration, and the initial stats snapshot succeed. `RifCreateState` tracks owned
sub-interface/BVI, LCP, bridge, and loopback changes so a failure unwinds only resources acquired by
that CREATE. For a persistent port/LAG, `get_interface_vrf()` reuses VPP's `sw_interface_get_table`
query to capture the actual prior IPv4 table before rebinding. A later failure restores that
table even if loopback programming never succeeded, and does not delete shared VRF tables.
When CREATE changes persistent-interface MTU, MPLS enablement, or admin state, it first reads
the actual VPP settings. Failure restores the previous values, including all four protocol
MTUs, rather than assuming defaults. Query and setter errors abort creation. Deferred child
admin-up requests are replayed only after the parent CREATE commits; deleting an owned
sub-interface during rollback also removes its pending admin request.
MPLS requests that match the captured enabled state do not call VPP's reference-counted
enable/disable API, avoiding extra references or a disable at zero.
After a changed request, CREATE verifies the actual MPLS state. If other references keep
MPLS enabled or verification fails, CREATE fails and rolls back its own changes rather
than consuming the other references or reporting a successful disable.
A successful default-VRF CREATE binds table 0 if the persistent interface is still in another
table. VRF lookup/programming failures abort creation; rollback API failures are logged and
reported as failures, not silently treated as successful cleanup.

### 7.7 Interface identity resolution

saivpp's interface registry yields names like `BondEthernet0` or `eth1.100`, while the
plugin and `vnet_feature_enable_disable` work on `sw_if_index`. The API is therefore **index-based** (the
VPP convention), and the binding bridges the two using the existing `get_swif_idx(vam, hwif_name)` helper
in `SaiVppXlate.c`. That helper looks the name up in the
`sw_if_index_by_interface_name` table saivpp already maintains from VPP interface dumps, and is the same
resolution the other send helpers use, so no new infrastructure is needed.

### 7.8 Control and data flow

```
Control: config interface ip loopback-action -> CONFIG_DB -> orchagent (intfsorch) -> ASIC_DB -> syncd
         --[SAI API]--> saivpp (SwitchVppRif -> SaiVppXlate)
         --[VPP binary API: sonic_ext_iface_loopback_set_action]--> sonic_ext plugin (per-interface state + arc enable)

Data:    ingress RIF -> ip4-input -> ip4-lookup -> ip4-rewrite (next-hop OUT same if; sets VLIB_TX)
         -> ip4-output arc -> [sonic-ext-ip4-loopback node]
              DROP    : tx-error++ , error-drop
              FORWARD : continue -> interface-output -> egress
```

The control flow above is the detailed expansion of the §3.3 overview: the `SAI API` boundary is
`syncd -> saivpp`, and the `VPP binary API` boundary (the `sonic_ext_iface_loopback_set_action` message) is
`saivpp -> sonic_ext plugin`.

---

## 8. Test Plan

### 8.1 SONiC integration (sonic-mgmt, `t1-lag-vpp`)

The `iface_loopback_action` module (`pytest.mark.topology('any')`, so t1-lag is included):

- `test_loopback_action_basic`: set forward/drop per RIF identifier; send 10 packets
  (`eth_dst = router_mac`, TTL 121->120); assert `verify_packet` (forward) or `verify_no_packet` +
  `tx_err == 10` (drop).
- `test_loopback_action_port_flap`: same assertions after a port flap (state survives a link bounce).
- `test_loopback_action_reload`: same assertions after a **cold** reboot
  (default `--rif_loopback_reboot_type=cold`); config restored from CONFIG_DB re-applies the attribute.

### 8.2 Enablement

A **separate sonic-mgmt PR**, to land **last**, adds `iface_loopback_action` to the `t1-lag-vpp` section
of `.azure-pipelines/pr_test_scripts.yaml`. Gate any unavoidable skips on `asic_type in ['vpp']` (not
`topo_name`).

### 8.3 Counters across flap and reload

The test reads `tx_err` from `show interfaces counters rif` and clears it with `sonic-clear rifcounters`
before each measurement, so absolute counter persistence is not required. `tx-error` is the standard VPP
interface counter and behaves like the others across a port flap; after the cold reboot in
`test_loopback_action_reload`, counters start at zero and the action is re-applied from CONFIG_DB (§5).

### 8.4 Validation evidence and remaining integration work

Early prototype testing on `vms-kvm-vpp-t1-lag` demonstrated the IPv4 basic test across all five
RIF shapes, including FORWARD/DROP behavior and `TX_ERR` accounting. A focused IPv6 check also
observed loopback-node drops only in DROP mode. These results predate the re-port to the current
plugin feature framework and `VppInterfaceRegistry`; they are not a fresh full-module pass for
the current PR revisions.

The SAI baseline merged through sonic-net/sonic-sairedis#1983 (PR head `3aece9f5`) has a native
VPP-enabled build and 37 focused C++ tests passing,
including the six upstream deferred sub-interface admin-state tests.
Coverage includes feature enabled/disabled/query-error handling, capability reporting, RIF-OID
lifecycle, stats baselines/reset/error paths, metadata counter injection, and failed-CREATE
cleanup. VRF regressions exercise port and LAG failures after table binding, restoration of a
nonzero prior table, a subsequent default-VRF CREATE, and lookup/setter failures.
Seven additional regressions cover exact MTU/MPLS/admin restoration after failed PORT/LAG
CREATE, query/setter errors, matching MPLS requests, post-change verification, reference counts, and deferred-admin
cleanup and replay. An isolated VPP process
also verified the real MTU/admin/MPLS query and restoration APIs, link-state compatibility,
and invalid-interface error handling. It also confirmed that repeated MPLS enables require
matching disables, which the reference-counting test mock reproduces.

The follow-up in
[sonic-net/sonic-sairedis#2144](https://github.com/sonic-net/sonic-sairedis/pull/2144)
additionally returns the default `FORWARD` on GET when the action was omitted at CREATE, and
rejects disabled-feature `DROP` with `SAI_STATUS_NOT_SUPPORTED` instead of the baseline's successful
no-op. These corrections are not present in baseline `3aece9f5`. Follow-up revision `fa67bc84`,
based on upstream `75804e2d`, passed a full native VPP-enabled build, all 39 selected VPP tests in
shuffled order (seed 1983), and the five source checks. The disabled-feature helper regression and the new
CREATE/SET regression both failed before the disabled-feature correction. The latter covers all
five RIF shapes, rejected CREATE cleanup, unchanged stored attributes after rejected SET,
explicit/omitted `FORWARD`, and no loopback API calls while disabled.

A fresh image containing the SAI changes is still needed for the complete
`iface_loopback_action` integration run, including flap and cold reboot. The native tests
mock VPP APIs and RIF host operations; neither these tests nor the isolated API check
replaces that live-DUT validation. The ingress-side counter expectations in §7.4 are derived
from the VPP drop path and SAI mapping, not a fresh runtime measurement; a focused check should
compare `tx-error`, `drops`, and `rx-error` deltas as well as the SAI RIF error counters.

---

## 9. Historical bring-up findings

These observations describe the early prototype environment, not universal prerequisites for
loopback action or sub-port forwarding. The prototype's parsing and neighbor fixes were removed
from the current SAI PR during its re-port onto upstream interface-registry code; they are not
additional changes shipped by this feature series.

1. **`std::stoi` shutdown-wait (the actual syncd stall).** Unguarded `std::stoi`
   calls in `vslib/vpp` throw on non-numeric interface names; the exception reaches
   `Syncd::run()` which logs *"Runtime error: stoi — entering shutdown-wait mode"*
   and parks syncd. syncd then drops all requests, the in-flight orchagent op never
   completes, the critical-process watchdog restarts swss, and the config (incl. the
   test's neighbor) is torn down before it reaches `ASIC_DB` — the "Failed to add
   neighbor" symptom. The prototype guarded these conversions; the current feature uses the
   upstream registry instead of adding another name-parsing path.

2. **VLAN-RIF neighbors never programmed.** `addRemoveIpNbr` skipped RIFs without a
   PORT/LAG `PORT_ID`, so VLAN RIFs (`Vlan51`) never got their neighbor in VPP and
   the DUT ARPed instead of forwarding. The prototype added a manual VLAN-to-BVI resolver.
   The current feature uses `VppInterfaceRegistry` (§7.6), not that former helper.

3. **Tagged-frame loss with virtio VLAN filtering in the bring-up environment.**
   On that QEMU/virtio/DPDK setup, tagged packets did not reach VPP while untagged
   packets did. Disabling `ctrl_vlan` restored tagged ingress: a controlled
   comparison observed approximately 100 untagged / 0 tagged packets before and
   approximately 100 tagged packets after; OVS was VLAN-agnostic and DPDK
   VLAN stripping was off. This does **not** establish that all VPP testbeds
   require the override; existing sub-port tests can pass on other setups.
   The VPP-DUT-only `-global virtio-net-pci.ctrl_vlan=off` override in
   `ansible/roles/vm_set/templates/sonic.xml.j2` has already merged in
   [sonic-net/sonic-mgmt#26035](https://github.com/sonic-net/sonic-mgmt/pull/26035).
   It is a testbed workaround for the observed filtering behavior, not a new
   requirement introduced by loopback action.

4. **PortChannel sub-port RIF IP on the wrong interface.** The RIF-IP resolver did
   not understand SONiC's `Po<id>.<vlan>` short form, so `Po54.54`'s IP never reached
   `BondEthernet54.54` and its FIB stayed `UNRESOLVED`. The prototype handled the
   `Po<id>.<vlan>`/`PortChannel<id>.<vlan>` form in `vpp_add_del_intf_ip_addr_norif`
   (`SwitchVppRif.cpp`).

5. **`find_new_bond_id` misassigns `bond_id 0`.** The PO sub-interface shows as
   `Po54.54@PortChannel54`, matches `grep PortChannel`, and its garbage suffix parses
   to `bond_id 0`, which got assigned to a real LAG — so a 2nd PortChannel RIF's
   neighbor landed on `BondEthernet0`. The prototype skipped non-base PortChannel entries
   (`.`/`@`/non-digit suffix) in `find_new_bond_id` (`SwitchVppFdb.cpp`).

The current validation scope, including the remaining live-DUT run, is recorded in §8.4.

---

## Appendix A: File Change Summary

### sonic-platform-vpp

| File | Change | Description |
|---|---|---|
| `vppbld/plugins/src/sonic_ext/sonic_ext.api` | Modify | Add `sonic_ext_iface_loopback_set_action { sw_if_index, action }` to the existing plugin API |
| `vppbld/plugins/src/sonic_ext/ip4_loopback_node.c`, `ip6_loopback_node.c` | **New** | The `sonic-ext-ip4-loopback` / `sonic-ext-ip6-loopback` output-arc nodes |
| `vppbld/plugins/src/sonic_ext/sonic_ext.c`, `sonic_ext_api.c` | Modify | Set-action function, delete-reset hook, and API handler using the canonical message-ID table |
| `vppbld/plugins/src/sonic_ext/sonic_ext.h` | Modify | `IFACE_LOOPBACK` feature entry, action vector, node declarations, and action constants |
| `vppbld/plugins/src/sonic_ext/CMakeLists.txt`, `FEATURE.yaml` | Modify | Add the two nodes and document the `iface-loopback` feature |
| `vppbld/plugins/tests/sonic_ext/test_sonic_ext_loopback.py` | **New** | Plugin-level forwarding/drop, toggle, idempotency, and unsupported-action tests |
| `rules/vpp.mk` | Modify | Bump `VPP_VERSION` suffix so CI does not pull a stale cached `.deb` without the new nodes (§7.1) |
| `doc/vpp/vpp-iface-loopback-action.md` (in sonic-net/SONiC) | **New** | This document |

### sonic-sairedis

**Feature changes:**

| File | Change | Description |
|---|---|---|
| `vslib/vpp/SwitchVppRif.cpp` | Modify | Apply/clear loopback actions, bind RIF OIDs, initialize counters, and roll back failed CREATE resources and persistent-interface settings |
| `vslib/vpp/SwitchVpp.cpp` | Modify | Feature-aware capability reporting and `getRifStatsExt()` with initial/clear baselines and explicit query-error handling |
| `vslib/vpp/SwitchVpp.h` | Modify | Declare action/counter helpers and `RifCreateState` transaction bookkeeping |
| `vslib/vpp/VppInterfaceRegistry.h` / `.cpp` | Modify | Maintain a separate RIF-OID index and preserve backing port/LAG/VLAN identity |
| `vslib/vpp/SwitchVppUtils.h` / `.cpp` | Modify | Status-returning feature query; cache successful results only |
| `vslib/vpp/vppxlate/SaiVppXlate.c` / `.h` | Modify | Loopback API helper; queries for prior VRF, MTU, admin, and MPLS settings, plus exact protocol-MTU restoration |
| `vslib/vpp/SwitchVppFdb.cpp` | Modify | Apply the action on VLAN BVI CREATE and track acquired resources for rollback |
| `unittest/vslib/TestSwitchVpp.cpp`, `Makefile.am` | Modify | Retain upstream interface-state tests and conditionally link the split VPP test modules |
| `unittest/vslib/TestSwitchVppRif.cpp`, `TestVppInterfaceRegistry.cpp` | Add | Separate native regression suites for RIF behavior and registry bindings |
| `unittest/vslib/MockVppXlate.cpp` / `.h` | Add | Shared C API wrappers, resettable mock state, and testable RIF host-operation overrides without mangled C++ linker symbols |

### sonic-mgmt

| File | Change | Description |
|---|---|---|
| `ansible/roles/vm_set/templates/sonic.xml.j2` | Modify (merged) | VPP-DUT-only `virtio-net-pci.ctrl_vlan=off` workaround for the observed testbed filtering issue (§9); not a universal loopback prerequisite or VM resource increase |
| `.azure-pipelines/pr_test_scripts.yaml` | Modify | Add `iface_loopback_action/test_iface_loopback_action.py` to the `t1-lag-vpp` section (separate PR, lands last) |
| `tests/common/plugins/conditional_mark/tests_mark_conditions.yaml` | Modify | Add `vpp` to the allowed `asic_type` for `iface_loopback_action`, with a comment naming the prerequisite PRs + issue #25788 |

---

## Appendix B: VPP API Reference

### B.1 Feature-arc enable/disable

```c
int vnet_feature_enable_disable (const char *arc_name, const char *node_name,
                                 u32 sw_if_index, int enable_disable,
                                 void *feature_config, u32 n_feature_config_bytes);
```
Used in the API handler to toggle `sonic-ext-ip4-loopback` / `sonic-ext-ip6-loopback` on `ip4-output` /
`ip6-output` for an interface, with rollback on partial failure.

### B.2 Interface `tx-error` simple counter

```c
vlib_increment_simple_counter (
    &vnet_get_main()->interface_main.sw_if_counters[VNET_INTERFACE_COUNTER_TX_ERROR],
    vm->thread_index, sw_if_index, n);
```
Surfaces in the stats segment as `/interfaces/<name>/tx-error`; read by `SaiIntfStats.c`
(`handle_stat_one`) into the SAI RIF `tx_err` field. This is the counter the test asserts on.

### B.3 Per-packet ingress/egress interface

```c
vnet_buffer(b)->sw_if_index[VLIB_RX];   // ingress interface
vnet_buffer(b)->sw_if_index[VLIB_TX];   // egress interface (set by ip4/6-rewrite)
```
The entire dataplane check is `RX == TX && action == DROP`.

### B.4 New plugin message

Added to the existing `sonic_ext.api`:

```
autoreply define sonic_ext_iface_loopback_set_action {
  u32 client_index; u32 context;
  vl_api_interface_index_t sw_if_index;   // resolved by the binding via get_swif_idx() (§7.7)
  u8 action;                              // 0 = FORWARD, 1 = DROP
};
```
Consumed by saivpp via the `M(SONIC_EXT_IFACE_LOOPBACK_SET_ACTION, mp)` send macro in `SaiVppXlate.c`.
