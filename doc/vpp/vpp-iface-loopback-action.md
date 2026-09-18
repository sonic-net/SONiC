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
9. [Known Issues / Open Items](#9-known-issues--open-items)
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
  `SwitchVpp::setRifStats()` in saivpp so the SAI RIF `tx_err`
  (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`) reflects it (saivpp previously populated VPP counters
  only for ports, not RIFs; see §7.4).
- saivpp handling of `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` on RIF create and set, for all
  five RIF identifiers exercised by the test (ethernet, VLAN, port-channel/LAG, sub-port, port-channel
  sub-port).
- Advertising the attribute as supported via the SAI capability query path.

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
| `tx-error` | VPP per-interface simple counter at `/interfaces/<name>/tx-error`; mapped to the SAI RIF `tx_err` (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`) by the new `SwitchVpp::setRifStats()` via `SaiIntfStats.c` (§7.4). |

### 3.2 RIF identifiers exercised by the test

The sonic-mgmt test labels its RIF scenarios with five names, but these are not five SAI RIF *types*.
There are three SAI types involved (`PORT`, `SUB_PORT`, `VLAN`); the count reaches five because the test
also varies the underlying interface between a physical port and a LAG (PortChannel, "PO"):

| Test case | Example interface | SAI RIF type | Underlying `PORT_ID` | VPP interface (`vpp_get_rif_hwif_name`) |
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
because a VLAN RIF has no `PORT_ID` and must be resolved to the bridge BVI. §7.6 introduces the unified
`vpp_get_rif_hwif_name()` resolver that covers every shape above.

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

The feature is **purely additive** and opt-in per interface:

- The default action is `FORWARD`, which leaves the `sonic-ext-ip4-loopback`/`sonic-ext-ip6-loopback`
  node **disabled** on the interface's output arc. Interfaces without `loopback-action drop` pay
  **zero** per-packet cost and see no change in forwarding or counters.
- No existing VPP node, arc, default, or counter is modified; only two new nodes and a new binary API
  are added to the `sonic_ext` plugin, plus a new saivpp handler. There is no ABI/CRC or
  submodule-ordering concern beyond the `VPP_VERSION` bump (§7.1), because no existing message or core
  header changes.
- Per-interface state is one `u8` in a vector indexed by `sw_if_index`, so there is no scaling concern
  with port/RIF count.
- The drop decision is interface-identity based (`VLIB_RX == VLIB_TX`), independent of VRF and IP, so
  duplicate addresses across VRFs do not affect it.

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
| VPP | `iface_loopback_set_action { sw_if_index, action }` (§7.5) |

The per-interface action needs no plugin-side persistence across reboots: orchagent re-applies it from
CONFIG_DB (cold/fast boot) or syncd replays it from ASIC_DB (warm boot), re-issuing the RIF set to
saivpp. `test_loopback_action_reload` uses **cold** reboot by default (§8.1).

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
| `sai_router_interface_api->createRouterif()` dispatch | Already routes create->create / set->update; no change beyond the attribute handler. |

### 6.3 Capability query

No work is required here. `SwitchVpp::queryAttributeCapability` (`vslib/vpp/SwitchVpp.cpp`) returns
`create_implemented = set_implemented = get_implemented = true` for every attribute, so
`LOOPBACK_PACKET_ACTION` is already advertised as supported. The RIF create/update paths also ignore
unrecognised attributes today (they fail only if `TYPE`/`PORT_ID` are missing), so adding the handler
introduces no regression.

---

## 7. VPP Implementation

### 7.1 Component Overview

The feature lives in the existing **`sonic_ext`** plugin (`vppbld/plugins/sonic_ext/`) — the
consolidated home for custom SONiC VPP dataplane nodes (added upstream by sonic-platform-vpp #255).
It adds two output-arc nodes and the plugin's first binary API:

```
vppbld/plugins/sonic_ext/
  sonic_ext.api            (new)  define iface_loopback_set_action { sw_if_index, action }
  ip4_loopback_node.c      (new)  IPv4 output-arc node  (node "sonic-ext-ip4-loopback")
  ip6_loopback_node.c      (new)  IPv6 output-arc node  (node "sonic-ext-ip6-loopback")
  sonic_ext.h              (edit) msg_id_base + loopback_action_by_sw_if_index vector + decls
  sonic_ext.c              (edit) API handler, set-action fn, msg-id table, delete-reset hook
  CMakeLists.txt           (edit) add the two nodes + API_FILES sonic_ext.api
  FEATURE.yaml             (edit) add the iface-loopback feature
```

The plugin directory is auto-copied into VPP's `src/plugins/` at build time; **no
`vppbld/patches/series` change is needed** (only *patches* are registered there). Bump
`VPP_VERSION` in `rules/vpp.mk` (the deb cache key) so downstream builds don't reuse a stale
cached VPP deb without the new nodes.

> `sonic_ext` is **already** enabled in both `docker-syncd-vpp/conf/startup.conf.tmpl` and
> `docker-sonic-vpp/conf/startup.conf.tmpl` (upstream, since #255), so **no startup.conf change is
> needed** — the loopback nodes and the `iface_loopback_set_action` binary API load with the rest of
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
  keyed on the bond index (the index saivpp resolves via `vpp_get_hwif_name`, §7.6).
- Sub-port / LAG sub-port RIF: ingress classification and egress both use the sub-interface
  (`<hwif>.<vlan>` / `<bond>.<vlan>`) `sw_if_index`, so the comparison and the action key are the
  sub-interface index.

This is the correctness condition for the `PO_RIF` / `PO_SUB_PORT_RIF` cases (half the t1-lag matrix) and
is exercised by the sonic-mgmt integration test (§8.1, validated in §8.4).

### 7.4 Counter

The node increments VPP's per-interface **`tx-error`** counter on the egress `sw_if_index`. The
test asserts on the SAI RIF `tx_err` (`SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`, surfaced by
`show interfaces counters rif`).

The drop is implemented in two parts: the buffer is enqueued to `error-drop` with
`b->error = node->errors[HAIRPIN_DROP]` (the node-level diagnostic count, visible in `vppctl show
errors`), and the interface counter the test reads is bumped explicitly with
`vlib_increment_simple_counter(vnm->interface_main.sw_if_counters + VNET_INTERFACE_COUNTER_TX_ERROR,
thread_index, tx_sw_if_index, 1)`.

> ⚠️ **saivpp RIF counters must be populated from VPP (new code).** Integration testing on a
> `t1-lag-vpp` DUT showed `show interfaces counters rif` reading `0` for *every* RIF: saivpp only wired
> the VPP stats segment into **port** stats (`SwitchVpp::setPortStats`), while `ROUTER_INTERFACE`
> getStats fell through to the base virtual-switch handler and returned `0`. This HLD therefore adds
> `SwitchVpp::setRifStats()` (mirroring `setPortStats`): it resolves the RIF to its VPP hardware
> interface — port/LAG, sub-ports via the outer VLAN id, and **VLAN RIFs to the bridge BVI
> (`bvi<vlan-id>`)** — via the unified `vpp_get_rif_hwif_name()` resolver (§7.6), reads
> `/interfaces/<name>/*` through `vpp_intf_stats_query` (`SaiIntfStats.c`, `#define TX_ERROR "tx-error"`),
> and maps the counters to `SAI_ROUTER_INTERFACE_STAT_*` — in particular `tx-error` ->
> `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`. It is wired into `getStatsExt` for
> `SAI_OBJECT_TYPE_ROUTER_INTERFACE`.
>
> **Validated end to end** (Ethernet RIF, 10 injected hairpin packets): with `DROP`, `vppctl show
> errors` shows `10 sonic-ext-ip4-loopback hairpin packets dropped`, VPP `tx-error = 10`, and `show
> interfaces counters rif` reports `TX_ERR = 10`; with `FORWARD`, the packets egress and `TX_ERR`
> stays `0`.

> ⚠️ **Counter API differs from `ip_validate`.** `ip_validate` counts via a VPP **node** error counter
> (`vlib_node_increment_counter`), which appears only in `vppctl show errors` and is **not** a
> per-interface stat. The explicit `vlib_increment_simple_counter` on `VNET_INTERFACE_COUNTER_TX_ERROR`
> is what `setRifStats` surfaces as RIF `tx_err`; the node-level `error-drop` count is diagnostic only.

### 7.5 Binary API

```
autoreply define iface_loopback_set_action
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
2. **Resolve the RIF to its VPP interface.** Port-backed RIFs (`PORT` / `SUB_PORT`, over a physical
   port or a LAG) reuse the existing `vpp_get_hwif_name(port_id, vlan_id, ifname)` helper — the same
   helper the MTU/admin set-paths use — which returns the correct hwif **name**:
   - LAG (`SAI_OBJECT_TYPE_LAG`) -> `BondEthernet<id>` (via `get_lag_bond_info`);
   - port -> hwif (via `getTapNameFromPortId` + `tap_to_hwif_name`);
   - sub-port / LAG sub-port -> appends `.<vlan_id>` to the above.

   **VLAN RIFs carry no `PORT_ID`** (they are created via the separate `vpp_create_bvi_interface`
   path and are backed by the bridge BVI), so `vpp_update_router_interface` returned early for the
   `VLAN` type and never applied the loopback action. A unified `vpp_get_rif_hwif_name(rif_oid,
   ifname)` resolver closes this gap: it reads the RIF `TYPE` and maps `VLAN` -> `bvi<vlan-id>` (via
   `SAI_ROUTER_INTERFACE_ATTR_VLAN_ID` -> `SAI_VLAN_ATTR_VLAN_ID`, mirroring `vpp_create_bvi_interface`),
   and otherwise falls back to `vpp_get_hwif_name` for the port/LAG/sub-port shapes. The VLAN loopback
   set-path and `setRifStats` (§7.4) both use this resolver, so the node and counter operate on the
   BVI's `sw_if_index` like any other interface (exercised by the `VLAN_RIF` case in the sonic-mgmt
   integration, §8.1).

   The test's "five RIF types" map to **three** SAI RIF *types* (`PORT`, `SUB_PORT`, `VLAN`); `PO_*` are
   `PORT`/`SUB_PORT` whose `PORT_ID` is a LAG. (The SAI RIF `TYPE_LOOPBACK` is a different, unrelated
   concept — see §3.1 — and is not exercised here.)
3. Map `SAI_PACKET_ACTION_FORWARD` -> `0`, `SAI_PACKET_ACTION_DROP` -> `1`.
4. Resolve the hwif name to a `sw_if_index` with the existing `get_swif_idx()` helper and send the
   message (see §7.7).

**API helper** (`vslib/vpp/vppxlate/SaiVppXlate.c` / `.h`), following the `tunterm_acl` /
`set_ip_flow_hash_v2` binding pattern:

- `#include <vpp_plugins/sonic_ext/sonic_ext.api_enum.h>` and `..._types.h` (the `sonic_ext` plugin now carries
  the `iface_loopback_set_action` message; the message name is unchanged).
- Register the `sonic_ext` plugin's `msg_id_base` during init (looked up as `sonic_ext_%08x`).
- Add a reply handler and a send helper `vpp_iface_loopback_set_action(const char *hwif_name, int action)`
  that calls `get_swif_idx()` to obtain the `sw_if_index`, then issues the message via the
  `M(IFACE_LOOPBACK_SET_ACTION, mp)` macro (balanced `VPP_LOCK()`/`VPP_UNLOCK()` on every path).

**Idempotency and teardown.** Create-with-attribute and a later set reach the same handler; re-sending
the same action is a no-op (the plugin toggles the arcs only on a real transition), and `DROP` ->
`FORWARD` disables the arcs and restores the per-interface state to `FORWARD`. On the SAI side the
loopback action is applied symmetrically on RIF create (including VLAN RIFs, via `vpp_create_bvi_interface`)
and cleared to `FORWARD` on RIF remove, so a recycled `sw_if_index` cannot inherit a stale `DROP`.

### 7.7 Interface identity resolution

saivpp is name-centric (`vpp_get_hwif_name` yields a name like `BondEthernet0` or `eth1.100`), while the
plugin and `vnet_feature_enable_disable` work on `sw_if_index`. The API is therefore **index-based** (the
VPP convention), and the binding bridges the two using the existing `get_swif_idx(vam, hwif_name)` helper
in `SaiVppXlate.c` (defined at `SaiVppXlate.c:1698`). That helper looks the name up in the
`sw_if_index_by_interface_name` table saivpp already maintains from VPP interface dumps, and is the same
resolution the other send helpers use, so no new infrastructure is needed.

### 7.8 Control and data flow

```
Control: config interface ip loopback-action -> CONFIG_DB -> orchagent (intfsorch) -> ASIC_DB -> syncd
         --[SAI API]--> saivpp (SwitchVppRif -> SaiVppXlate)
         --[VPP binary API: iface_loopback_set_action]--> sonic_ext plugin (per-interface state + arc enable)

Data:    ingress RIF -> ip4-input -> ip4-lookup -> ip4-rewrite (next-hop OUT same if; sets VLIB_TX)
         -> ip4-output arc -> [sonic-ext-ip4-loopback node]
              DROP    : tx-error++ , error-drop
              FORWARD : continue -> interface-output -> egress
```

The control flow above is the detailed expansion of the §3.3 overview: the `SAI API` boundary is
`syncd -> saivpp`, and the `VPP binary API` boundary (the `iface_loopback_set_action` message) is
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

### 8.4 Live-DUT validation results (`vms-kvm-vpp-t1-lag`)

Validated on a live `vms-kvm-vpp-t1-lag` KVM testbed (32-port, `asic_type=vpp`,
VPP `v2606-0.4+b1sonic1`, Debian trixie):

- **Full module passes.** The `iface_loopback_action` module reports **`3 passed`
  (~17 min)** — `test_loopback_action_basic`, `test_loopback_action_port_flap`, and
  `test_loopback_action_reload`. Every RIF instance the module creates (Ethernet,
  VLAN, PortChannel, port sub-interface and PortChannel sub-interface, across two
  cycles) passes both the `FORWARD` and the `DROP` verification, and the drop
  behaviour survives a port flap and a cold reboot.
- **Plugin + control path:** `sonic_ext_plugin.so` loads with the
  `sonic-ext-ip4-loopback`/`sonic-ext-ip6-loopback` nodes (`vppctl show node
  sonic-ext-ip4-loopback` → `state active`), `create_switch` succeeds, and
  `config interface ip loopback-action <rif> drop|forward` toggles the feature arcs on the
  resolved VPP interface for every RIF shape — including the `VLAN_RIF` case, where
  `Vlan51` resolves to `bvi51`.
- **Data path (every RIF shape, 10 hairpin packets):** `DROP` → the loopback node
  drops 10 + VPP `tx-error = 10` + SONiC `show interfaces counters rif` `TX_ERR = 10`;
  `FORWARD` → the packet is looped back out the ingress RIF and `TX_ERR = 0`.
- **RIF counters:** every RIF shape (port/LAG/sub-port and the VLAN BVI) appears in
  `show interfaces counters rif` with live VPP counters via `vpp_get_rif_hwif_name()`.

Reaching this required fixing five pre-existing, feature-independent defects that each
blocked the run at a successive RIF shape — see §9.

---

## 9. Resolved Pre-existing Defects (found during enablement)

The feature itself is validated end to end (§8.4). Getting the **full**
`iface_loopback_action` module to pass on `vms-kvm-vpp-t1-lag` first required fixing
**five distinct, pre-existing defects** that are independent of the loopback
feature — four in the stock VPP SAI layer (`sonic-sairedis/vslib/vpp`) and one in
the KVM testbed VM template (`sonic-mgmt`). Each
of the five blockers stopped the run at a successive RIF shape; fixing one exposed the
next. Each is summarized below.

1. **`std::stoi` shutdown-wait (the actual syncd stall).** Unguarded `std::stoi`
   calls in `vslib/vpp` throw on non-numeric interface names; the exception reaches
   `Syncd::run()` which logs *"Runtime error: stoi — entering shutdown-wait mode"*
   and parks syncd. syncd then drops all requests, the in-flight orchagent op never
   completes, the critical-process watchdog restarts swss, and the config (incl. the
   test's neighbor) is torn down before it reaches `ASIC_DB` — the "Failed to add
   neighbor" symptom. **Fix:** `vpp_safe_stoi()` guards every such call in
   `SwitchVppRif.cpp`/`SwitchVppFdb.cpp`.

2. **VLAN-RIF neighbors never programmed.** `addRemoveIpNbr` skipped RIFs without a
   PORT/LAG `PORT_ID`, so VLAN RIFs (`Vlan51`) never got their neighbor in VPP and
   the DUT ARPed instead of forwarding. **Fix:** resolve via `vpp_get_rif_hwif_name()`
   (VLAN → `bvi<id>`) in `SwitchVppNbr.cpp`.

3. **qemu virtio `ctrl_vlan` drops all tagged frames (testbed).** The DUT VM's
   `virtio-net-pci` NICs default to `ctrl_vlan=on`; since VPP/DPDK registers no
   VLANs, qemu drops every VLAN-tagged frame before it reaches VPP. VLAN RIFs pass
   (untagged bridge member) but L3 sub-interfaces (need the tag) do not. **Fix:**
   `-global virtio-net-pci.ctrl_vlan=off` in `sonic.xml.j2` for VPP DUTs. Proven by a
   controlled tagged-vs-untagged counter test (untagged ~100 arrive, tagged ~0
   before / ~100 after); OVS verified vlan-agnostic, DPDK vlan-strip off.

4. **PortChannel sub-port RIF IP on the wrong interface.** The RIF-IP resolver did
   not understand SONiC's `Po<id>.<vlan>` short form, so `Po54.54`'s IP never reached
   `BondEthernet54.54` and its FIB stayed `UNRESOLVED`. **Fix:** handle the
   `Po<id>.<vlan>`/`PortChannel<id>.<vlan>` form in `vpp_add_del_intf_ip_addr_norif`
   (`SwitchVppRif.cpp`).

5. **`find_new_bond_id` misassigns `bond_id 0`.** The PO sub-interface shows as
   `Po54.54@PortChannel54`, matches `grep PortChannel`, and its garbage suffix parses
   to `bond_id 0`, which got assigned to a real LAG — so a 2nd PortChannel RIF's
   neighbor landed on `BondEthernet0`. **Fix:** skip non-base PortChannel entries
   (`.`/`@`/non-digit suffix) in `find_new_bond_id` (`SwitchVppFdb.cpp`).

With the five blockers applied, syncd stays responsive (`RestartCount = 0`, no
shutdown-wait, orchagent never crashes) and the test passes.

---

## Appendix A: File Change Summary

### sonic-platform-vpp

| File | Change | Description |
|---|---|---|
| `vppbld/plugins/sonic_ext/sonic_ext.api` | **New** | The plugin's first binary API: `iface_loopback_set_action { sw_if_index, action }` |
| `vppbld/plugins/sonic_ext/ip4_loopback_node.c`, `ip6_loopback_node.c` | **New** | The `sonic-ext-ip4-loopback` / `sonic-ext-ip6-loopback` output-arc nodes |
| `vppbld/plugins/sonic_ext/sonic_ext.c` | Modify | API handler, set-action fn (`sonic_ext_iface_loopback_set_action`), msg-id table, delete-reset hook |
| `vppbld/plugins/sonic_ext/sonic_ext.h` | Modify | `msg_id_base` + `loopback_action_by_sw_if_index` in `sonic_ext_main_t`; node externs; action defines; set-fn decl |
| `vppbld/plugins/sonic_ext/CMakeLists.txt`, `FEATURE.yaml` | Modify | Add the two nodes + `API_FILES sonic_ext.api`; add the `iface-loopback` feature |
| `rules/vpp.mk` | Modify | Bump `VPP_VERSION` suffix so CI does not pull a stale cached `.deb` without the new nodes (§7.1) |
| `doc/vpp/vpp-iface-loopback-action.md` (in sonic-net/SONiC) | **New** | This document |

### sonic-sairedis

**Feature changes:**

| File | Change | Description |
|---|---|---|
| `vslib/vpp/SwitchVppRif.cpp` | Modify | Handle `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` symmetrically on RIF create/set **and clear it on remove**; add unified `vpp_get_rif_hwif_name()` resolver (port/LAG/sub-port via `vpp_get_hwif_name()`, VLAN -> `bvi<vlan>`); de-duplicated setters via `vpp_apply_loopback_action()`; map `sai_packet_action_t` -> plugin action |
| `vslib/vpp/SwitchVpp.cpp` | Modify | `setRifStats()` (RIF `tx_err` etc. from VPP, §7.4); resolve every RIF shape via `vpp_get_rif_hwif_name()` |
| `vslib/vpp/SwitchVpp.h` | Modify | Declare `vpp_apply_loopback_action()`, `vpp_set_interface_loopback_action()`, `vpp_set_rif_loopback_action()`, `vpp_get_rif_hwif_name()`, `setRifStats()` |
| `vslib/vpp/vppxlate/SaiVppXlate.c` / `.h` | Modify | Include `sonic_ext` plugin API headers; register the `sonic_ext` `msg_id_base`; reply handler + `iface_loopback_set_action` send helper (resolves name via `get_swif_idx()`) |
| `vslib/vpp/SwitchVppFdb.cpp` | Modify | Apply the loopback action on the **VLAN BVI create** path (`vpp_create_bvi_interface`, via `vpp_apply_loopback_action()`), so VLAN RIFs are covered like port/LAG RIFs (feature — distinct from this file's defect fixes below) |

**Pre-existing-defect fixes (§9) — separable from the feature, worth their own commits/PR:**

| File | Change | Description |
|---|---|---|
| `vslib/vpp/SwitchVppUtils.h` / `.cpp` | Modify | Shared `vpp_safe_stoi()` helper guarding previously-unguarded `std::stoi` calls (defect #1) — used by both `SwitchVppRif.cpp` and `SwitchVppFdb.cpp` |
| `vslib/vpp/SwitchVppRif.cpp` | Modify | Route `std::stoi` calls through `vpp_safe_stoi()` (defect #1); handle the `Po<id>.<vlan>` / `PortChannel<id>.<vlan>` short form in `vpp_add_del_intf_ip_addr_norif` so PortChannel sub-port RIF IPs reach `BondEthernet<id>.<vlan>` (defect #4) |
| `vslib/vpp/SwitchVppNbr.cpp` | Modify | `addRemoveIpNbr` resolves the interface via `vpp_get_rif_hwif_name()` so VLAN (and all) RIF neighbors are programmed into VPP (defect #2) |
| `vslib/vpp/SwitchVppFdb.cpp` | Modify | `vpp_safe_stoi()` guard (defect #1); `find_new_bond_id` skips non-base PortChannel entries (`.`/`@`/non-digit suffix) so sub-interfaces like `Po54.54@PortChannel54` don't get mis-parsed to `bond_id 0` (defect #5) |

### sonic-mgmt

| File | Change | Description |
|---|---|---|
| `ansible/roles/vm_set/templates/sonic.xml.j2` | Modify | For `asic_type == 'vpp'` DUTs only, add `<qemu:commandline> -global virtio-net-pci.ctrl_vlan=off` (with an explanatory comment) so the virtio VLAN filter stops dropping tagged frames (defect #3). *(No resource change — a VM resource bump used during bring-up was reverted as a loaded-host workaround, not a feature requirement.)* |
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

Defined in `sonic_ext.api` (the `sonic_ext` plugin's first binary API message):

```
autoreply define iface_loopback_set_action {
  u32 client_index; u32 context;
  vl_api_interface_index_t sw_if_index;   // resolved by the binding via get_swif_idx() (§7.7)
  u8 action;                              // 0 = FORWARD, 1 = DROP
};
```
Consumed by saivpp via the `M(IFACE_LOOPBACK_SET_ACTION, mp)` send macro in `SaiVppXlate.c`.
