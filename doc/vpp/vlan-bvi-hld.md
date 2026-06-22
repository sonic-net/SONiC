# VLAN Bridge Domain with BVI — High-Level Design

## Revision History

| Rev | Date | Author | Summary |
|-----|------|--------|---------|
| 1.0 | 2026-04 | yuega2 | Initial design.  ARP/DHCP punted via the `l2-input-classify` clone-on-hit VPP patch (0010); IP unicast and ARP redirected via sonic_ext plugin features on the `ip4-punt`/`ip6-punt`/`arp` arcs; per-buffer state held in a global `orig_rx_by_bi[]` sidecar keyed by buffer index. |
| 1.1 | 2026-06 | yuega2 | Re-architected control-plane punt around the `sonic_ext` out-of-tree VPP plugin. Removed all dependence on classifier clone-on-hit for ARP/DHCP. Per-buffer state moved into the `vnet_buffer2(b)->unused` overlay (`sonic_ext_buffer_opaque_t`) so it survives `vlib_buffer_clone()` automatically with no atomic ops or worker handoff concerns. ARP and DHCP now reach the kernel via the `l2-flood -> linux-cp-punt-xc` path with a BVI-side feature node, then through `linux-cp-punt -> aggr-tap-redirect` on the BVI host tap, which restores the original member tap and re-pushes the wire VLAN tag from the cookie. The classifier now handles only LLDP (always redirect-punt). Updated §5 packet-flow walkthroughs to match v1.1 architecture.|

---

## 1. Problem Statement

SONiC on VPP needs to support L2 bridging with L3 SVI (VLAN interfaces) for both
tagged and untagged VLAN members. The standard SONiC data model creates:

- A VLAN (e.g., Vlan10)
- An SVI with an IP address (e.g., 10.0.0.1/24 on Vlan10)
- Member ports with tagging mode (tagged or untagged)

VPP's bridge-domain (BD) and BVI (Bridge Virtual Interface) constructs map to this
model, but require explicit wiring for two distinct traffic classes:

1. **Control-plane protocols (ARP, LLDP, LACP, DHCP)** — must be delivered to
   Linux on the **member interface tap** (the LCP host tap of the wire phy /
   sub-if that received the frame), so per-port services (LLDP/LACP agents,
   DHCP relay) see frames with the right ifindex.

2. **L3 traffic over the VLAN SVI IP** — IP unicast destined to the SVI address
   (e.g., ping, SSH, routing protocols) is also delivered to the Linux
   control plane via the **member interface tap**, not via a BVI tap. The BVI
   exists only to give the BD an L3 endpoint inside VPP for routing/ARP
   resolution; no packets are punted through the BVI to Linux.

In summary, SONiC doesn't expect NPU to punt packets to virtual netdev, such as Vlan,
Port Channel directly. The packets should be punted via member interface then delivered
to the virtual netdev by linux kernel.

### Challenges

1. **No BVI → Linux punt path**: VPP's BVI is purely an internal L3 endpoint
   for the BD. The control plane must instead see all punted traffic on the
   originating member interface, so Linux observes ports the same way it
   would on physical hardware.

2. **Per-port punt for control protocols**: ARP, LLDP, LACP, and DHCP must be
   punted directly to the LCP host tap of the wire ingress port so Linux
   daemons (lldpd, teamd, dhcrelay) receive frames on the correct netdev.

3. **Original wire ingress is lost by L2 bridging**: ARP and DHCP broadcasts
   reach the BVI via `l2-flood`, by which point `vnet_buffer(b)->sw_if_index[VLIB_RX]`
   has been overwritten with the BVI sw_if. The redirect path needs to know
   which member the frame entered VPP on. We carry this in a per-buffer
   cookie stamped at `device-input` (see §3.7).

4. **Wire VLAN tag is consumed by the sub-interface**: a tagged frame's
   802.1Q header is stripped by `ethernet-input` (sub-if dispatch) or by L2
   VTR pop-1, before any redirect node runs.  The kernel still needs to see
   the original wire frame on the member tap, so the tag must be re-pushed
   on egress (see §3.7).

5. **Tagged member dispatch**: VPP must create dot1q sub-interfaces for tagged
   members, strip the tag on ingress to the BD, and push it back on egress.

6. **Untagged member handling**: The physical interface itself joins the BD
   directly — no sub-interface or VLAN tag rewrite needed.

7. **Promiscuous mode**: VPP's virtio/DPDK backend filters tagged frames at
   the device level unless promiscuous mode is enabled on the parent interface.

8. **Multiple BVIs share a FIB**: a single global `255.255.255.255/32` route
   to "the" BVI tap cannot disambiguate which bridge a DHCP discover came
   from when several Vlan SVIs live in the default VRF. The redirect must
   therefore be per-buffer (via the cookie) rather than per-route.

---

## 2. SONiC Configuration Example

```json
// config_db.json excerpts

"VLAN": {
    "Vlan10": { "vlanid": "10" }
}

"VLAN_INTERFACE": {
    "Vlan10": {},
    "Vlan10|10.0.0.1/24": {}
}

"VLAN_MEMBER": {
    "Vlan10|Ethernet0": { "tagging_mode": "tagged" },
    "Vlan10|Ethernet4": { "tagging_mode": "untagged" }
}
```

CLI equivalents:
```bash
config vlan add 10
config vlan member add 10 Ethernet0    # tagged by default
config vlan member add -u 10 Ethernet4 # untagged
config interface ip add Vlan10 10.0.0.1/24
```

---

## 3. Design Principles

### 3.1 Punt Strategy Summary

All Linux-bound traffic is delivered on the **member interface tap**, never on
a BVI tap. The BVI has no LCP pair on the kernel-visible side — its only LCP
pair is internal to VPP (a `loop` interface that exists so VPP has a place
to anchor the SVI IP / MAC). Different protocols use different VPP hooks to
reach the right member tap:

| Protocol | VPP entry point | sonic_ext node(s) involved | Visible in Linux on |
|----------|-----------------|----------------------------|----------------------|
| ARP | `arp` arc on the BVI | `sonic-ext-aggr-tap-redirect` (on BVI host tap interface-output) | original member iface |
| DHCP (broadcast → BVI) | `ip4-unicast` arc on the BVI | `sonic-ext-bcast-redirect` → `linux-cp-punt` → `sonic-ext-aggr-tap-redirect` | original member iface |
| LLDP | `l2-input-classify` (consume) | none — direct redirect-punt to `linux-cp-punt` on the member's own LCP host tap | member iface only |
| LACP | `ethernet-input` on bond | none — direct redirect-punt | original member iface only |
| IP unicast to SVI | `ip4-punt` / `ip6-punt` arc | `sonic-ext-aggr-tap-redirect` on BVI host tap interface-output | original member iface |
| Linux → wire reply | `device-input` on host tap | `sonic-ext-host-xc` → phy `interface-output` | (sent on the wire) |

Three principles unify the table:

- **The BVI is the L3 / broadcast funnel.** ARP, DHCP and L3 unicast all
  reach the BVI naturally via the VPP graph (l2-flood for broadcast, l2-fwd
  for unicast addressed to the BVI MAC). The sonic_ext plugin then redirects
  off the BVI to the correct member tap rather than letting the punt land on
  a BVI host tap.
- **Per-buffer cookie disambiguates the original member.** A small overlay
  on `vnet_buffer2(b)->unused` (`sonic_ext_buffer_opaque_t`) is stamped at
  `device-input` on the wire phy and survives `vlib_buffer_clone()` (VPP
  memcpys opaque2 wholesale into every clone) and `vlib_buffer_advance()`
  (it lives in metadata, not packet bytes). The redirect node reads it back
  to recover the original RX sw_if_index and outermost wire VLAN tag.
- **LLDP is still classifier punt** because it is strictly per-port
  link-local protocols (must not be flooded to other members) and has no
  natural BVI/L3 path.

### 3.2 L2 Classifier-Based Punt (untagged-member LLDP only)

LLDP arriving on an **untagged BD member** is punted directly from the
member interface using VPP's `l2-input-classify` feature with the
`linux-cp-punt` node as the target. Action is always
`CLASSIFY_ACTION_NONE` (redirect-punt — the original is consumed;
nothing else is done with it).

**Why this is needed — BD floods link-local multicast.** When a frame
with a multicast destination MAC enters the BD via `l2-input`, VPP
unconditionally strips `L2INPUT_FEAT_FWD` (and `UU_FLOOD` / `UU_FWD`)
from the per-buffer feature bitmap (see
`src/vnet/l2/l2_input_node.c`), so the FDB is never consulted and a
static `l2fib` entry pointing the LLDP DA at the BVI cannot suppress
the flood.  Without the classifier, the LLDP frame would be replicated
by `l2-flood` to every BD member — including the BVI flood-copy,
which `linux-cp-punt-xc` then delivers to the BVI host tap.  The
result is that `lldpd` would observe the **same neighbour on multiple
netdevs** (the originating member, every other VLAN member, and the
Vlan SVI tap), corrupting neighbour discovery whenever the switch and
any peer reachable through another VLAN member both advertise on the
same BD.  `l2-input-classify` runs **before** the multicast feat-mask
strip, so a redirect-punt session here consumes the frame and
delivers it only to the originating member's LCP host tap.

**Why LACP and tagged-member LLDP are NOT in the classifier.**
`SaiVppXlate.c` calls `vpp_lcp_ethertype_enable(0x88cc / 0x8809 /
0x0806)` at startup, which registers `linux-cp-punt-xc` as the
`ethernet-input` next for those ethertypes.  `ethernet-input`
dispatches by **outer** ethertype, before any sub-interface or BD
lookup, so:

- **LACP (0x8809)** on any phy goes straight to `linux-cp-punt-xc` (or
  to `bond-input` first if the phy is a bond slave) and never reaches
  `l2-input`.
- **Tagged-member LLDP (0x88CC)** also bypasses the BD: LLDP is never
  802.1Q-tagged on the wire, so it arrives on the **parent** phy
  (which is not in the BD) with outer ethertype 0x88CC and is
  consumed by the same `linux-cp-punt-xc` shortcut.
- **Untagged-member LLDP (0x88CC)** is the only case that reaches
  `l2-input`, because here the parent phy is itself the BD member.
  `ethernet-input` does dispatch the frame to `linux-cp-punt-xc`
  by ethertype — but only when the rx interface is **not** an L2
  bridged port.  When the rx interface is a BD member, the BD path
  takes precedence and the frame falls into `l2-input`, where the
  classifier catches it.

### 3.3 Classifier Table Design (LLDP only)

Two shared classify tables are created lazily on the first BD member add and
persist for the lifetime of the process. A single `linux-cp-punt` next-index
is resolved via `vpp_add_node_next("l2-input-classify", "linux-cp-punt")`.

The previously-defined `untag_ip4` and `tag_dhcp` tables (which used to
clone-on-hit DHCP) have been removed in v1.1 because DHCP is now handled by
the `sonic-ext-bcast-redirect` plugin path (see §3.7).

#### 3.3.1 Untagged Member Tables

Untagged frames have the ethertype at byte offset 12 (standard Ethernet).

**Table: untag_other** — matches ethertype directly (skip=0, match=1)

| Byte Offset | Field | Mask |
|-------------|-------|------|
| 12–13 | Ethertype | `0xFFFF` |

Sessions:

| Protocol | Ethertype | action | Action |
|----------|-----------|--------|--------|
| LLDP | `0x88CC` | 0 (NONE) | punt (consume) |

Miss: continue L2 feature chain (to VTR, learn, fwd, flood).

#### 3.3.2 Tagged Member Tables

No classifier is needed for tagged members. LLDP packets are received on
main interface without vlan tags. They are not processed in the bridge.
The regular forwarding path (ethernet-input -> linux-cp-punt-xc) punts
the packets directly to the member interface.

#### 3.3.3 Table Attachment

When a BD member is added:
- **Untagged member** (parent phy, e.g., `bobm0`):
  `classify_set_interface_l2_tables(bobm0, ip4=~0, ip6=~0, other=untag_other)`

### 3.4 Frames in the BD Are Always Untagged

All frames inside the bridge domain are **untagged**:
- Tagged members: VPP sub-interface pops the outer tag on ingress (`pop 1`)
  and pushes it back on egress (symmetric VTR)
- Untagged members: frames arrive without a tag and stay untagged
- BVI: exchanges untagged frames with the BD (no VTR on BVI)

This matches the Linux kernel model where the `Vlan10` SVI sees untagged frames.

### 3.5 Promiscuous Mode on Physical Interfaces

VPP's virtio/DPDK backend implements `VIRTIO_NET_F_CTRL_VLAN` which filters
tagged frames at the device level. Promiscuous mode is enabled on every
physical interface at LCP pair creation time so that tagged frames pass
through to VPP's `ethernet-input` for sub-interface dispatch.

### 3.6 Auto Sub-Interface (lcp-auto-subint)

VPP's linux-cp plugin `lcp-auto-subint` feature **must be disabled**.

When enabled, linux-cp would auto-create a Linux netdev (e.g., `Ethernet0.10`)
for every VPP sub-interface. This breaks the punt-via-member design:

- The `sonic-ext-aggr-tap-redirect` node looks up the LCP pair of
  `orig_rx_sw_if_index` and rewrites VLIB_TX to that pair's host tap.
  If a sub-if `Ethernet0.10` were also LCP-paired, the redirect would
  resolve to `tap_Ethernet0.10` (a netdev that is not in any kernel
  bridge and is not the parent of `Vlan10`), so the kernel would never
  see the punted frame on the `Ethernet0` netdev where it expects it.
- More importantly, on the **kernel** side, an `Ethernet0.10` 8021q netdev
  intercepts tagged frames from `Ethernet0` via `vlan_do_receive()` before
  any bridge VLAN demux can deliver them to `Vlan10`. Tagged ARP/DHCP
  punted onto `Ethernet0` would never reach `Vlan10`.

With `lcp-auto-subint` **off**, only one LCP pair per physical port is
created (parent ↔ `Ethernet<n>`). The control plane sees tagged frames on
`Ethernet<n>`, and Linux's regular vlan-filtering bridge (or explicit user
config) decides how to dispatch them to `Vlan<id>`.

### 3.7 The `sonic_ext` Out-of-Tree Plugin (Punt Architecture)

All redirect logic for control-plane and SVI-bound traffic is implemented
entirely by the out-of-tree `sonic_ext` VPP plugin
(`platform/vpp/vppbld/plugins/sonic_ext/`).  The build system auto-copies
that directory into `repo/src/plugins/` and VPP's plugin glob discovers it,
so **no upstream VPP source is modified**.  The plugin is the long-term
home for any SONiC-specific behavior that mainline VPP would not accept,
which keeps us free of merge conflicts when tracking new VPP releases.
We will migrate some of the patches, such as port channel drop
counter, to this plugin.

#### 3.7.1 Per-Buffer Cookie

The plugin defines an overlay on `vnet_buffer2(b)->unused`:

```c
typedef struct {
  u32 magic;            // 'SNCX' (0x534e4358) when populated
  u32 orig_rx_sw_if_index;  // wire phy or sub-if that RXed the frame
  u32 orig_vlan_tag;        // outer 802.1Q TCI (0 if untagged)
} sonic_ext_buffer_opaque_t;
```

This overlay lives in buffer metadata, **not** in the packet payload, so:

- **It survives `vlib_buffer_advance()`** (advance changes only `current_data`/`current_length`).
- **It survives `vlib_buffer_clone()`** — VPP memcpys `opaque2` wholesale into every clone, so any flooded copy carries the same cookie.
- **No atomics or worker-handoff sidecar are needed** — the cookie travels with the buffer through the entire graph and across worker thread handoffs.

This is the v1.1 replacement for the v1.0 `orig_rx_by_bi[]` global vector.
It is simpler, lock-free by construction, and removes a recycled-buffer
race that the v1.0 design needed atomic swap-clear to defend against.

#### 3.7.2 Plugin Nodes

| Node | Arc | Insertion | Job |
|------|-----|-----------|-----|
| `sonic-ext-capture` | `device-input` | runs before `ethernet-input`, enabled **only on wire phys** (not BVIs / aggregate ifaces, not host taps) | Stamp the cookie: `magic='SNCX'`, `orig_rx = b->sw_if_index[VLIB_RX]`, `orig_vlan_tag = outer 802.1Q TCI` if the frame is dot1q (peeked from the L2 header before sub-if dispatch). |
| `sonic-ext-host-xc` | `device-input` | runs before `ethernet-input`, enabled on host taps | When a Linux reply re-enters VPP on a host tap, jump straight to the paired phy's `interface-output` (skip `ethernet-input` re-parse / sub-if dispatch). |
| `sonic-ext-bcast-redirect` | `ip4-unicast` | runs before `ip4-lookup`, enabled on every BVI that has an LCP pair (i.e. every L3 SVI BVI).  BVIs created purely as the L2 endpoint of a VXLAN tunnel termination have no LCP pair and are therefore **not** instrumented by this node — limited broadcasts on those BVIs continue down the regular L2/VXLAN forwarding path and can be encapsulated to the remote VTEP. | Match all of: `dst==255.255.255.255`, IP `proto==UDP`, UDP `sport==68 && dport==67` (DHCPv4 client→server), and a valid sonic_ext cookie.  Matching frames are dispatched to `linux-cp-punt` instead of `ip4-lookup`; everything else (subnet-directed broadcasts, non-UDP broadcasts, other UDP broadcasts such as NetBIOS / RIPv1 / vendor discovery / WoL, and host-originated traffic with no cookie) falls through to `ip4-lookup` so it is dropped against the default 255/32 route. The narrow port match keeps the per-member punt limited to the protocol that actually requires it; widening the gate (e.g. to additional UDP services) is a localized change in the plugin node only. |
| `sonic-ext-aggr-tap-redirect` | `interface-output` | runs on the BVI's host-tap interface (and any future bond/lag aggregate tap) | Read the cookie. Look up the LCP pair of `orig_rx_sw_if_index` and rewrite `b->sw_if_index[VLIB_TX]` to that LCP's host tap.  If `orig_vlan_tag != 0`, mac-shift the L2 header back 4 bytes and write `[TPID 0x8100][TCI orig_vlan_tag]` at offsets 12 and 14, restoring the original wire VLAN.  Update `vnet_buffer(b)->l2_hdr_offset` so any later rewind lands on the tagged header. |

The `sonic-ext-arp-redirect` and `sonic-ext-ip{4,6}-punt-redirect` features
of v1.0 collapse into the same `aggr-tap-redirect` egress feature in v1.1
because all three control-plane classes funnel through the BVI's host-tap
egress path:

- **ARP** flooded onto a BD member → `l2-input` → `l2-input-classify`
  (LLDP classifier in v1.1 misses on ARP) → `l2-learn` →
  `l2-flood` → `linux-cp-punt-xc` → BVI host tap
  `interface-output` → `aggr-tap-redirect` → member host tap.
- **DHCP** (limited broadcast) flooded onto a BD member → `l2-input` →
  `l2-flood` → ethernet-input on BVI → `ip4-input` →
  `sonic-ext-bcast-redirect` → `linux-cp-punt` → BVI host tap
  `interface-output` → `aggr-tap-redirect` → member host tap.
- **L3 unicast to SVI** unicast-forwarded to BVI → `ip4-input` →
  `ip4-lookup` → `ip4-local` → `linux-cp-punt-xc` → BVI host tap
  `interface-output` → `aggr-tap-redirect` → member host tap.

Concrete ARP trace (tagged member, vlan 10):

```
ethernet-input        ARP ff:ff:ff:ff:ff:ff 802.1q vlan 10
l2-input              sw_if_index 23 (member sub-if)
l2-input-classify     table 1 -> next 13      (LLDP miss = continue)
l2-input-vtr          pop outer tag
l2-learn / l2-flood   bd_index 1
linux-cp-punt-xc      lip-punt: 24 -> 25      (BVI sw_if 24 -> bvi-tap 25)
tap4107-output        bvi-host-tap egress     (ARP, untagged at this point)
sonic-ext-aggr-tap-redirect
                      aggr-tap 25 orig-rx 1 member-tap 17 vlan-pushed vid 10
tap4101-output        member-host-tap egress  (ARP, 802.1q vlan 10 restored)
tap4101-tx
```

Note that `linux-cp-punt-xc` is what handles ARP today: there is no
explicit `arp-input` -> `linux-cp-arp-phy` hop in this graph.  The
flood copy delivered to the BVI is cross-connected straight to the
BVI's host tap, where `aggr-tap-redirect` then rewrites VLIB_TX onto
the original member's tap and re-inserts the original VLAN.

In all three flows, `linux-cp-punt[-xc]` only writes
`b->sw_if_index[VLIB_TX]` and rewinds with `vlib_buffer_advance(b, -len0)`
(where `len0 = vlib_buffer_get_current(b) - ethernet_buffer_get_header(b)`).
**It does not modify L2 MACs**, so the original wire L2 header reaches
`aggr-tap-redirect` intact.  The redirect node only changes VLIB_TX and
re-pushes the VLAN tag — destination and source MACs are preserved.

#### 3.7.3 Configuration & Defaults

The plugin exposes:

```
sonic-ext punt-via-member [on|off]
sonic-ext host-xc [on|off]
show sonic-ext
```

Both `punt-via-member` and `host-xc` are turned **on by default** at
`sonic_ext_init()` time, immediately after `lcp_itf_pair_register_vft()`.
Operators do not need to issue any vppctl command for the standard SONiC
data path.

The plugin registers a `lcp_itf_pair_vft` callback so node enablement
follows LCP pair add/del events:

- On `lcp_itf_pair_add_cb(phy, host_tap)`:
  - Enable `sonic-ext-capture` on `phy` **only if** `phy` is not an
    aggregate interface (`!sonic_ext_phy_is_aggregate(phy)`, which today
    means "not a BVI"; bond/lag aggregates will be added later).
  - Enable `sonic-ext-host-xc` on `host_tap`.
  - If `phy` is a BVI, enable `sonic-ext-bcast-redirect` on the BVI's
    `ip4-unicast` arc and `sonic-ext-aggr-tap-redirect` on the BVI's host-tap
    `interface-output` arc.
- On `lcp_itf_pair_del_cb(...)`: symmetric disable.

Because node enablement is driven from LCP pair add/del, BVIs without
an LCP pair are never touched.  Concretely:

- **L3 SVI BVIs** (the BVI for a routed VLAN) get an LCP pair via
  `lcp-auto-subint` / the explicit BVI LCP pair from §3.8, so
  `bcast-redirect` is enabled and limited broadcasts on those BVIs are
  punted to the host.
- **VXLAN tunnel-termination BVIs** (BVIs created only as the L2 end
  of a VXLAN VNI ↔ VLAN mapping, with no `Vlan<id>` host interface) do
  **not** have an LCP pair.  `bcast-redirect` stays disabled and
  limited broadcasts on those BVIs continue down the regular L2 path,
  so they can be flooded into the BD members and encapsulated into
  VXLAN towards the remote VTEPs.

Because the capture node is only attached to wire phys, the cookie is
stamped exactly once per RX (no double-stamp on host taps, no irrelevant
stamping on BVIs that have no `dpdk-input` of their own).

#### 3.7.4 Alternative Design — Classifier + Side-Car for Full-Header Punt

The current implementation stores `orig_rx_sw_if_index` and
`orig_vlan_tag` in `vnet_buffer2(b)->unused`. This is sufficient for
ARP, DHCP and L3 unicast where the L2 header (and at most one outer
VLAN tag) is all that needs to be restored on the punted copy.

If we ever need to punt **encapsulated** packets to Linux while
preserving the encapsulation (e.g. for VXLAN snooping where the kernel
must see the full outer + inner headers), the in-buffer cookie becomes
too small. An alternative architecture would be:

- Re-enable patch `0010-l2-input-classify-clone-on-hit.patch` to add
  `CLASSIFY_ACTION_CLONE = 4` to `l2-input-classify`.
- Trigger punt via classify sessions (as in v1.0 of this design) so the
  clone happens at a well-defined L2 hook with the original buffer still
  carrying its full ingress headers.
- Replace the in-buffer cookie with a **side-car table keyed by buffer
  index**: at clone time, copy the entire ingress header (or any other
  per-packet state needed) into a dynamically-sized side-car slot. The
  redirect node looks the slot up, pre-pends/restores the saved bytes,
  and frees the slot.

This is **not currently implemented**.  It is documented here so the
v1.1 plugin layout doesn't lock us out of supporting full-header punt
later — both the classifier-clone hooks and the side-car table can be
added without changing the v1.1 redirect-node interfaces (`aggr-tap-redirect`,
`bcast-redirect`, `host-xc`) which only consume the cookie.

### 3.8 BVI Configuration

The BVI (`bvi<vlanid>`) still exists inside VPP because:
- The BD needs an L3 endpoint for ARP resolution and inter-VLAN routing.
- The BVI MAC is the gateway MAC seen by hosts in the BD.

Unlike v1.0, the BVI **does** have an LCP pair, but the host tap is
**not exposed to the kernel** (its only consumer is
`sonic-ext-aggr-tap-redirect`, which always rewrites VLIB_TX away from
the BVI tap before the buffer reaches the tap-output dispatcher).  In
practice this means Linux never sees a `tap_Vlan10` netdev for end-host
traffic — every punt that would have landed on `tap_Vlan10` is
intercepted on the BVI host tap's `interface-output` arc and redirected
to the originating member's tap.

BVI flood/UU flood are left **enabled**.  ARP and DHCP traverse the BVI
on the bridge-flood path; the redirect node hands them off to the
correct member tap on the way out.

---

## 4. Implementation Changes

### 4.1 BVI Creation (Internal-Only LCP Pair)

**File**: `SwitchVppFdb.cpp` — `vpp_create_bvi_interface()`

When a VLAN SVI is created (SAI `ROUTER_INTERFACE_TYPE_VLAN`):
1. Create BVI: `create_bvi_interface(mac, vlan_id)`
2. Add BVI to BD: `set_sw_interface_l2_bridge(bvi<id>, vlan_id, true, BVI)`
3. Bring the BVI up: `interface_set_state(bvi<id>, true)`
4. Create the BVI's internal LCP pair so `aggr-tap-redirect` has a host
   tap to anchor on.  This host tap is **never exposed to the kernel
   data path** — every packet that would land on it is intercepted by
   `sonic-ext-aggr-tap-redirect` on the BVI's `interface-output` arc
   and rewritten to a member tap before tap-output.

IP unicast destined to the SVI address, ARP, and DHCP are all delivered
to Linux on the originating member tap via the sonic_ext plugin (§3.7).
No `tap_Vlan<id>` traffic ever reaches the kernel under normal data flow.

Teardown removes the BVI from the BD, deletes the internal LCP pair,
and deletes the BVI interface.

### 4.2 Tagged Member: Sub-Interface + VTR Pop-1 + Classifier

**File**: `SwitchVppFdb.cpp` — `vpp_create_vlan_member()` (TAGGED path)

1. Create VPP sub-interface: `create_sub_interface(bobm0, 10, 10)`
   - `lcp-auto-subint` is **disabled**, so no Linux `Ethernet0.10` netdev
     is created automatically. The control plane sees tagged frames on
     the parent (`Ethernet0`); see §3.6.
2. Add sub-interface to BD: `set_sw_interface_l2_bridge(bobm0.10, 10, true, NORMAL)`
3. Set VTR pop-1: `set_l2_interface_vlan_tag_rewrite(bobm0.10, 10, ~0, DOT1Q, POP_1)`
4. Admin up: `interface_set_state(bobm0.10, true)`
5. Attach classifier: `l2_punt_classify_apply(bobm0.10, true /*tagged*/)`

### 4.3 Untagged Member: Parent Interface in BD + Classifier

**File**: `SwitchVppFdb.cpp` — `vpp_create_vlan_member()` (UNTAGGED path)

1. Add parent phy directly to BD: `set_sw_interface_l2_bridge(bobm0, 10, true, NORMAL)`
2. Attach classifier: `l2_punt_classify_apply(bobm0, false /*untagged*/)`

No sub-interface or VTR needed — wire frames are already untagged.

### 4.4 Classifier Initialization

**File**: `SwitchVppFdb.cpp` — `l2_punt_classify_init()`

Lazily creates the one shared classify table (`untag_other`)
and the LLDP redirect-punt sessions described in Section 3.3. Called
automatically on the first BD member add.  ARP and DHCP table slots that
existed in v1.0 (`untag_ip4`, `tag_dhcp`) are no longer created — those
protocols are handled by the `sonic_ext` plugin (§3.7).

### 4.5 The `sonic_ext` VPP Plugin

Implements the design in §3.7 entirely as an out-of-tree VPP plugin
under `platform/vpp/vppbld/plugins/sonic_ext/`.  The build system
auto-copies that directory into `repo/src/plugins/` and the upstream
plugin glob auto-discovers it, so **no modifications to upstream VPP
source are required**.  Patches `0008` and `0012` (legacy in-tree punt
hooks) were removed when this plugin was introduced; patch `0010`
(classifier clone-on-hit) is no longer required by the v1.1 design and
is retained only for the future alternative described in §3.7.4.

The plugin contains four feature nodes plus a CLI/init module:

| Node | Arc | Bound to | Purpose |
|------|-----|----------|---------|
| `sonic-ext-capture` | `device-input` | wire phys only (skipped on BVIs and host taps via `sonic_ext_phy_is_aggregate()`) | Stamp `sonic_ext_buffer_opaque_t` cookie (`magic='SNCX'`, `orig_rx`, `orig_vlan_tag`) on `vnet_buffer2(b)->unused` before `ethernet-input` overwrites RX. |
| `sonic-ext-host-xc` | `device-input` | LCP host taps | Steer Linux replies straight to the paired phy's `interface-output`. |
| `sonic-ext-bcast-redirect` | `ip4-unicast` | every BVI that has an LCP pair (gated on `sonic_ext_phy_is_bvi()` inside the LCP pair add/del callback).  VXLAN tunnel-termination BVIs without an LCP pair are not enabled. | Match cookie + `dst==255.255.255.255` + UDP + `sport==68 && dport==67` (DHCPv4 client→server) and dispatch the frame to `linux-cp-punt`; everything else falls through to `ip4-lookup`. |
| `sonic-ext-aggr-tap-redirect` | `interface-output` | BVI host tap | Read cookie; rewrite `VLIB_TX = LCP host tap of orig_rx`; if `orig_vlan_tag != 0`, re-insert `[0x8100][orig_vlan_tag]` into the L2 header. |

**Per-buffer cookie.**  See §3.7.1.  The cookie lives on
`vnet_buffer2(b)->unused` and survives `vlib_buffer_clone()` and
`vlib_buffer_advance()`.  No global sidecar, no atomic ops, no
worker-handoff complexity.

**VLAN re-insertion** in `sonic-ext-aggr-tap-redirect`: shift dst+src
MAC back 4 bytes and write `[TPID 0x8100][TCI orig_vlan_tag]` at offsets
12 and 14 of the new L2 header.  After inserting the tag,
`vnet_buffer(b)->l2_hdr_offset` is updated so any later rewind (e.g.
inside `lip_punt_xc_inline`) lands on the new tagged header.

**L2 header preservation.**  `linux-cp-punt[-xc]` only writes
`b->sw_if_index[VLIB_TX]` and rewinds the buffer with
`vlib_buffer_advance(b, -len0)`.  It does **not** memcpy or rewrite L2
MAC bytes.  The original wire L2 header therefore reaches
`aggr-tap-redirect` intact, and the kernel ultimately sees the exact
src/dst MAC pair that arrived on the wire.

**CLI.**

```
sonic-ext punt-via-member [on|off]
sonic-ext host-xc [on|off]
show sonic-ext
```

Both knobs default to **on**.  `sonic_ext_init()` calls
`sonic_ext_set_punt_via_member(1)` and `sonic_ext_set_host_xc(1)`
immediately after `lcp_itf_pair_register_vft()`, so operators do not
need to issue any vppctl command for the standard SONiC data path.

**Per-pair enablement.**  Instead of walking all sw interfaces, the
plugin registers a `lcp_itf_pair_vft` callback.  On every LCP pair
add, `sonic-ext-capture` and `sonic-ext-host-xc` are enabled on the
phy and host tap respectively (the capture path skips BVIs / aggregates
via `sonic_ext_phy_is_aggregate(phy)`); if the phy is a BVI the BVI's
`ip4-unicast` feature `sonic-ext-bcast-redirect` and the BVI host
tap's `interface-output` feature `sonic-ext-aggr-tap-redirect` are also
enabled.  Symmetric disable on pair delete.

### 4.6 VPP API Wrappers

**File**: `SaiVppXlate.c`

New functions for the classify binary API:
- `vpp_classify_table_create()` — create table with mask
- `vpp_classify_table_delete()` — delete table
- `vpp_classify_session_add()` — add session with match/action
- `vpp_classify_session_del()` — delete session
- `vpp_classify_set_interface_l2_tables()` — attach/detach tables on interface
- `vpp_add_node_next()` — resolve next-node index

All use the `M`/`M22` macros for socket-aware message allocation.

### 4.7 Promiscuous Mode on Every Physical Interface

**File**: `SwitchVppHostif.cpp`

At LCP pair creation for each physical port:
```cpp
configure_lcp_interface(hwif_name, dev, true);
interface_set_promiscuous(hwif_name, true);  // <-- added
// punt-via-member and host-xc are turned on by default at sonic_ext_init();
// no vppctl invocation is needed for the standard data path.
```

---

## 5. Packet Flow

### 5.1 ARP from a BD Member

ARP requests broadcast onto a BD member follow the same graph regardless
of whether the member is tagged or untagged.  `sonic-ext-capture` stamps
the cookie (and the original outer 802.1Q TCI, if any) at `device-input`,
the BD floods the ARP onto the BVI, `linux-cp-punt-xc` cross-connects the
BVI flood-copy to the BVI's host tap, and `sonic-ext-aggr-tap-redirect`
on the BVI host tap rewrites `VLIB_TX` to the original member's host tap
and re-pushes the original VLAN if the cookie carries one.  The tagged
case is identical to the untagged case at the graph level — VLAN
re-insertion is conditional on `orig_vlan_tag != 0`, not on a separate
code path.

```
Wire (ARP, 802.1q vlan 10 — tagged member)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie {orig_rx=1, orig_vlan_tag=10}
      → ethernet-input: etype=0x8100/0x0806, dispatched to bobm0.10
        → l2-input (sw_if_index 23, BD 1)
          → l2-input-classify (LLDP miss → continue)
          → l2-input-vtr: pop outer 802.1Q
          → l2-learn / l2-flood (bd_index 1)
            → linux-cp-punt-xc: lip-punt 24 → 25  (BVI sw_if 24 → bvi-tap 25)
              → bvi-host-tap (tap4107) interface-output  (ARP, untagged)
                → sonic-ext-aggr-tap-redirect:
                    aggr-tap 25, orig-rx 1, member-tap 17,
                    vlan-pushed vid 10 tpid 0x8100 → REDIRECTED
                  → member-host-tap (tap4101) interface-output
                    → tap4101-tx  (ARP, 802.1q vlan 10 restored)
                      → kernel sees ARP on Ethernet0.10
```

### 5.2 LLDP from Tagged Member

LLDP uses link-local ethertypes (0x8809) — **not** 0x8100.
When a tagged member port receives an LLDP frame, `ethernet-input` sees
ethertype 0x88CC and does **not** dispatch it to the dot1q sub-interface.
The frame stays on the parent physical interface, which has an LCP pair
but is not in the BD. It follows the regular LCP punt path:

```
Wire (LLDP 0x88CC, no 802.1Q encapsulation — LLDP is always untagged)
  → bobm0 (dpdk-input, promisc on)
    → ethernet-input: etype=0x88CC, hw-if-index=1, sw-if-index=1 (parent)
      → linux-cp-punt-xc: sw_if_index 1 → tap (Ethernet0)
        → kernel lldpd/teamd processes the frame on Ethernet0
```

The classifier on the sub-interface (`bobm0.10`) never sees LLDP.
This is the standard behavior — LLDP is a link-layer protocol that is
not VLAN-tagged on the wire.

### 5.3 LLDP from Untagged Member

```
Wire (no tag, LLDP 0x88CC)
  → bobm1 → ethernet-input → bobm1
    → l2-input (BD 10)
      → l2-input-classify: etype=0x88CC → "other" table
        → untag_other: etype=0x88CC → HIT, action=NONE
          → punt (consume): → linux-cp-punt → Ethernet4 tap
            → kernel lldpd/teamd processes the frame
```


### 5.4 LACP from a BD Member

LACP (Slow Protocols, ethertype `0x8809`, dst MAC `01:80:c2:00:00:02`)
is the link-bundling control protocol used by `teamd` on the SONiC
control plane.  Like LLDP it is a link-layer protocol — frames are
**always untagged on the wire**, even on tagged-trunk members — so the
graph for tagged and untagged members is identical from the LACP
perspective.

LACP punt does **not** rely on the L2 classifier.  When the
`linux-cp` plugin's `lcp-ethertype` shortcut is registered for
`0x8809` (see `vpp_lcp_ethertype_enable()` in `SaiVppXlate.c`), the
`linux-cp-punt-xc` node is wired as a direct ethernet-input next for
that ethertype.  `ethernet-input` therefore short-circuits the entire
L2 pipeline (`l2-input` / `l2-flood` / classifier / FDB are all
bypassed) and delivers the frame straight to the parent phy's host
tap.

Because the punt happens at `ethernet-input` on the **parent** phy
(not the dot1q sub-interface), there is no need for the `sonic_ext`
cookie / `aggr-tap-redirect` machinery: the frame is already on the
correct member's host tap with its original wire L2 header intact.
The `sonic-ext-capture` node still runs at `device-input` and stamps
the cookie, but the cookie is never consumed for LACP — it is
harmless metadata that gets freed with the buffer.

```
Wire (LACP 0x8809, no 802.1Q — LACP is always untagged, both tagged- and
                                untagged-member ports)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie (ignored downstream for LACP)
      → bond-input  (LAG bundle resolution; no-op for non-bond ports)
        → ethernet-input: etype=0x8809, hw-if 1, sw-if 1 (parent phy)
          → linux-cp-punt-xc: lip-punt 1 → 17  (parent → tap4101)
            → tap4101-output / tap4101-tx
              → kernel teamd processes the frame on Ethernet0
```

Key observations:

- **Same graph for tagged and untagged members.**  LACP carries no
  802.1Q header on the wire, so `ethernet-input` always hands it to
  the parent phy regardless of whether the member is configured as a
  tagged trunk or an untagged access port.  The dot1q sub-interface
  (`bobm0.10`) never sees an LACP frame.
- **No L2 classifier session for LACP.**  The classifier installed
  on BD members today only matches LLDP (`0x88CC`); LACP is handled
  earlier by the linux-cp ethertype shortcut, so adding a classifier
  session for `0x8809` would be redundant (and never hit).
- **No BVI involvement.**  LACP never reaches `l2-input` on the
  member sub-interface, so `l2-flood` does not produce a BVI copy and
  `sonic-ext-bcast-redirect` is not triggered.
- **`sonic_ext` cookie is stamped but unused.**  `sonic-ext-capture`
  runs unconditionally on every wire phy at `device-input`, ahead of
  the ethertype shortcut.  For LACP the cookie is simply discarded
  along with the buffer once the kernel consumes the frame.

### 5.5 DHCP Broadcast from a BD Member

DHCP broadcasts (`dst = 255.255.255.255`) follow the same graph regardless
of whether the originating member is tagged or untagged.  `sonic-ext-capture`
stamps the cookie at `device-input`; `l2-flood` produces one copy per BD
member plus one for the BVI; the per-member copies are flooded back out the
wire by the regular `l2-output → <member>-output` path; the BVI copy enters
`ip4-input`, where `sonic-ext-bcast-redirect` matches `cookie-magic +
dst==255.255.255.255` and dispatches the frame to `linux-cp-punt`.  That
delivers the buffer to the BVI's host tap, where
`sonic-ext-aggr-tap-redirect` rewrites `VLIB_TX` to the originating member's
host tap and re-pushes the original VLAN if the cookie carries one.

```
Wire (DHCP DISCOVER, 802.1q vlan 10 — tagged member bobm0.10)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie {orig_rx=3, orig_vlan_tag=10}
      → ethernet-input → l2-input (sw_if 26, BD 1)
        → l2-input-classify (LLDP miss → continue)
        → l2-input-vtr: pop outer 802.1Q
        → l2-learn / l2-flood (bd_index 1)
            ├─→ l2-output → bobm1-output → bobm1-tx              (untagged member, flooded out wire)
            ├─→ l2-output → bobm0-output → bobm0-tx              (tagged member, vid 10 re-pushed by l2-output-vtr)
            └─→ ip4-input on BVI (sw_if 24)
                → sonic-ext-bcast-redirect:
                    rx 24 dst 255.255.255.255 cookie ok orig_rx 3 → PUNTED
                  → linux-cp-punt: lip-punt 24 → 25               (BVI sw_if → bvi-tap)
                    → bvi-host-tap (tap4107) interface-output     (DHCP, untagged)
                      → sonic-ext-aggr-tap-redirect:
                          aggr-tap 25 orig-rx 3 member-tap 19
                          vlan-pushed vid 10 tpid 0x8100 → REDIRECTED
                        → member-host-tap (tap4103) interface-output
                          → tap4103-tx  (DHCP, 802.1q vlan 10 restored)
                            → kernel sees DHCP on Ethernet0.10
```

Key observations:

- **Member flood copies are not punted** — they just go out the wire on
  the other BD members.  The BVI is the only flood-copy that reaches
  `ip4-input`, so `sonic-ext-bcast-redirect` runs at most once per
  ingress frame.
- **DHCPv4 client→server match only.**  The redirect node checks the
  cookie, `dst==255.255.255.255`, IP `proto==UDP`, and UDP
  `sport==68 && dport==67`.  Other limited-broadcast traffic
  (subnet-directed broadcasts, non-UDP, NetBIOS, RIPv1, vendor
  discovery, WoL, etc.) falls through to `ip4-lookup` and is dropped
  against the default 255/32 drop route.  The narrow gate keeps the
  per-member punt limited to the protocol that requires it; widening
  the match (e.g. for additional UDP services) is a localized change
  in the plugin node.
- **VLAN re-insertion is conditional** on `orig_vlan_tag != 0`.  An
  untagged ingress would print `no-vlan REDIRECTED` at
  `sonic-ext-aggr-tap-redirect` and deliver the frame to the member
  host tap untagged; everything else in the graph is identical.
- **Path of the punted copy is BVI-tap → member-tap**, not BVI-tap →
  Linux Vlan10 netdev.  The kernel observes the DHCP request on the
  netdev that corresponds to the original wire ingress (e.g.
  `Ethernet0.10` for `bobm0.10`), which is what the SONiC DHCP relay
  expects.

#### Servicing model: relay and/or in-VLAN DHCP server

This design supports **both** DHCP servicing models on the switch, and
they are not mutually exclusive:

- **DHCP relay (`dhcrelay`)** — the switch runs `dhcrelay` listening on
  the member-tap netdev (`Ethernet0.10` in the example above).  The
  punted DISCOVER/REQUEST that `aggr-tap-redirect` delivers to that tap
  is consumed by `dhcrelay`, which unicasts it to an L3-reachable
  server (typically reached via a different VRF/VLAN/uplink) and
  relays the OFFER/ACK back to the client.

- **In-VLAN DHCP server (`dhcp-server` / `kea-dhcp4` / etc.)** — the
  switch (or any other BD member) runs a DHCP server bound to the
  Vlan SVI / member netdev.  The server sees the DISCOVER through the
  same member-tap that `dhcrelay` would have used, because the punted
  copy is delivered to the *ingress member's* host tap (where Linux
  exposes it as `Ethernet0.10`, which is enslaved to `Vlan10`).  The
  server replies through the kernel; the reply path is the standard
  Linux → host-tap → BVI → `l2-output` flow back out the wire.

SONiC ensures either DHCP relay or server is enable but not both.

We deliberately **do not block** intra-VLAN L2 flooding of DHCP
broadcasts.  A foreign DHCP server that happens to live on another
member of the same BD will also see the DISCOVER as part of the
normal `l2-flood` fan-out (the per-member copies in the trace above)
and may answer it directly at L2 without involving the switch CPU.
The redirect-to-tap copy that drives the on-switch daemon is an
**additional** copy taken off the BVI flood-set, not a replacement
for the L2 flood.

Consequences:

1. **Foreign in-VLAN DHCP server is not an expected SONiC topology.**
   SONiC's DHCP model assumes the DHCP client and DHCP server are
   *not* both behind member ports of the same VLAN: either the server
   is L3-remote (reached via `dhcrelay`) or it runs on the switch
   itself (`dhcp-server` bound to the SVI).  This design does **not**
   explicitly block a foreign in-VLAN server — pure-L2 flood-and-
   answer will work as a side-effect of normal bridging — but the
   topology is not a tested target.

2. **DHCP snooping is out of scope.**  This HLD does not implement
   DHCP snooping, the snooping binding table, trusted/untrusted
   port classification, or Option-82 insertion/strip.  Operators who
   need to mix client-facing and server-facing member ports in the
   same VLAN — and therefore need the snooping security guarantees
   that prevent a rogue host from impersonating a DHCP server — are
   not covered by the current design.  Snooping support will be
   addressed in a separate HLD when the requirement is formalised; at
   that point the snooping enforcement node is expected to sit on
   the BD member's `l2-input` arc (before `l2-flood`) so that
   server-sourced frames arriving on untrusted member ports are
   dropped before they reach either the L2 flood-set or the
   punt-to-tap path.

3. **Double-servicing is theoretically possible** if (a) a foreign
   DHCP server sits on another BD member *and* (b) the switch is
   also running `dhcrelay` or an on-switch `dhcp-server` for the same
   VLAN.  In that case the client may receive two OFFERs — one from
   the foreign in-VLAN server (via the L2 flood path) and one from
   the on-switch daemon (via the punt → tap path).  This is benign
   by DHCP protocol design (the client picks one OFFER and the other
   lease falls through `DHCPRELEASE` / lease-timeout) and matches
   the behaviour of a hardware switch with both an in-VLAN server
   and a relay helper-address configured but no snooping enabled.
   Per consequence #1 this configuration is outside the supported
   topology; it is mentioned only to describe what the data plane
   will do if it occurs.

4. **Which member sees the punt** is unambiguous: the cookie carries
   the *original* `orig_rx` (the ingress wire port), so
   `aggr-tap-redirect` always delivers the punted copy to the
   ingress member's tap — never to a sibling member's tap.  There is
   exactly one punted copy per ingress frame regardless of BD
   membership count (see "Key observations" above).

5. **DHCPv6 is out of scope.**  Everything above describes DHCPv4
   only.  DHCPv6 client traffic is **link-scoped IPv6 multicast** to
   `ff02::1:2` (`All_DHCP_Relay_Agents_and_Servers`) — it is *not* a
   limited IPv4 broadcast, so the `dst == 255.255.255.255` gate in
   `sonic-ext-bcast-redirect` does not match it and there is no
   equivalent IPv6 redirect node in the current `sonic_ext` plugin.
   On the BVI, `ip6-input` / `ip6-mfib` will handle the multicast
   per the BVI's IPv6 multicast routing / MLD state (typically
   l2-flood only, no punt to Linux), so DHCPv6 will *not* be
   delivered to a member host tap by this design.  DHCPv6 relay /
   server support is deferred to a future HLD together with IPv6 ND
   (§7); when that work lands, an IPv6 sibling of
   `bcast-redirect` will be added on the BVI's `ip6-unicast` /
   `ip6-multicast` arc gating on the DHCPv6 link-local multicast
   destinations (`ff02::1:2`, and `ff05::1:3` for the relay-agent
   scope), reusing the same cookie and `aggr-tap-redirect` egress
   path.

### 5.6 IPv4 Unicast to the SVI (L3 Punt)

A unicast IPv4 frame addressed to the BVI's MAC is L2-forwarded by the
BD (`l2-fwd` resolves the dst MAC to the BVI), enters `ip4-input` on the
BVI, then `ip4-lookup` returns a local-receive next.  The packet is
handed to `ip4-receive` / `ip4-icmp-input` / `ip4-punt`, the SONiC punt
infrastructure redirects it via `ip4-punt-redirect` → `ip4-dvr-dpo` →
`ip4-dvr-reinject` to the BVI's host tap, and `sonic-ext-aggr-tap-redirect`
on the BVI host tap rewrites `VLIB_TX` to the originating member's host
tap and re-pushes the original VLAN if the cookie carries one.  Tagged
and untagged members share the graph; only the conditional VLAN push at
the end differs.

`sonic-ext-bcast-redirect` runs on the BVI's `ip4-unicast` arc but is a
no-op for unicast: the dst is not `255.255.255.255`, so the node falls
through (`passthru`) and `ip4-lookup` proceeds normally.

```
Wire (ICMP echo, 802.1q vlan 10 — tagged member bobm0.10)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie {orig_rx=1, orig_vlan_tag=10}
      → ethernet-input → l2-input (sw_if 23, BD 1)
        → l2-input-classify (LLDP miss → continue)
        → l2-input-vtr: pop outer 802.1Q
        → l2-learn / l2-fwd  (dst MAC resolved to BVI, sw_if 24)
          → ip4-input on BVI
            → sonic-ext-bcast-redirect: dst=10.0.0.1 → passthru
            → ip4-validate / ip4-lookup → local
              → ip4-receive → ip4-icmp-input → ip4-punt
                → ip4-punt-redirect (via redirect:22)
                  → ip4-dvr-dpo (sw_if 25)
                    → ip4-dvr-reinject
                      → bvi-host-tap (tap4107) interface-output
                        → sonic-ext-aggr-tap-redirect:
                            aggr-tap 25 orig-rx 1 member-tap 17
                            vlan-pushed vid 10 tpid 0x8100 → REDIRECTED
                          → member-host-tap (tap4101) interface-output
                            → tap4101-tx  (ICMP, 802.1q vlan 10 restored)
                              → kernel sees the packet on Ethernet0.10
```

Notes:

### 5.7 L2 Unicast Forwarding Between Members

Normal L2 forwarding is unaffected by the classifier (miss path):

```
bobm0.10 (ingress, tagged) → l2-input → classifier miss → POP tag
  → l2-learn + l2-fwd → dst MAC on bobm1 (untagged):
    → l2-output → no VTR → bobm1 → wire (untagged)

bobm1 (ingress, untagged) → l2-input → classifier miss
  → l2-learn + l2-fwd → dst MAC on bobm0.10 (tagged):
    → l2-output → l2-output-vtr: PUSH tag 10 → bobm0.10 → wire (tagged)
```

---

## 6. VPP Configuration Summary (Runtime State)

After SONiC applies the configuration above, VPP state looks like:

```
# Bridge domain 10 with BVI, tagged member, untagged member
vppctl show bridge-domain 10 detail
  BD-ID 10, flood, learn
    bvi10        (BVI, sw_if_index 25)
    bobm0.10     (tagged member, sw_if_index 23, vtr pop-1)
    bobm1        (untagged member, sw_if_index 3)

# LCP pairs
vppctl show lcp
  bvi10     → tap_Vlan10
  bobm0     → Ethernet0      (physical)
  bobm1     → Ethernet4      (physical)

# Classifier tables
vppctl show classify tables
  Table 0 (untag_other): skip=0 match=1 sessions=2  # LLDP

# Classifier attachment
vppctl show classify interface
  bobm1:    ip4=~0 ip6=~0 other=0 (untag_other)

# sonic_ext plugin state
vppctl show sonic-ext
  punt-via-member : on (default)
  host-xc         : on (default)
  bcast punts     : <counter>

# Promiscuous mode
vppctl show interface bobm0
  flags: ... promisc ...
```

---

## 7. IPv6 Neighbor Discovery (Future Work)

IPv6 Neighbor Discovery (ND) punt is not covered in this design and will be
addressed in a separate document. Two options are under consideration:

1. **VPP built-in ND handling**: VPP's `ip6-neighbor-discovery` and linux-cp
   plugin can handle ND natively without involving the SONiC control plane.
   VPP would respond to NS/NA on the BVI and program neighbor entries directly.

2. **Classifier-based punt**: Extend the classifier tables to match IPv6 ND
   packets (Next Header=0x3A ICMPv6, Type=0x87 NS / 0x88 NA) and punt/clone
   them to the Linux control plane, similar to the ARP approach. This would
   require additional ip6 table slots.

**DHCPv6** is also explicitly out of scope for v1.1 (see §5.4
consequence #5).  Unlike DHCPv4 it is link-scoped IPv6 multicast
(`ff02::1:2` for client → relay/server, `ff05::1:3` for relay → server),
so the IPv4-only `dst == 255.255.255.255` gate in
`sonic-ext-bcast-redirect` does not catch it and the design currently
has no IPv6 punt path for it.  When DHCPv6 support is required, an
IPv6 sibling of `bcast-redirect` will be added on the BVI's IPv6 arc,
gated on the DHCPv6 multicast destinations and reusing the existing
cookie + `aggr-tap-redirect` egress to deliver the frame to the
originating member's host tap (where `dhcp6relay` / `kea-dhcp6` /
etc. observe it).  This work is expected to land alongside the IPv6
ND solution above.
---

## 8. Files Modified

| File | Change |
|------|--------|
| `platform/vpp/docker-syncd-vpp/conf/startup.conf.tmpl` | Ensure `lcp-auto-subint` is **disabled** |
| `platform/vpp/docker-sonic-vpp/conf/startup.conf.tmpl` | Ensure `lcp-auto-subint` is **disabled** |
| `platform/vpp/vppbld/patches/0010-l2-input-classify-clone-on-hit.patch` | **No longer required** by the v1.1 design.  Retained in the patch directory only as a building block for the future full-header punt option (§3.7.4). |
| `platform/vpp/vppbld/plugins/sonic_ext/` | Out-of-tree VPP plugin: `sonic-ext-capture`, `sonic-ext-host-xc`, `sonic-ext-bcast-redirect`, `sonic-ext-aggr-tap-redirect` + CLI/init.  Per-buffer cookie on `vnet_buffer2(b)->unused`.  Defaults `punt-via-member` and `host-xc` to **on** at init.  Hooks into LCP pair add/del to manage per-pair feature enablement.  Supersedes patches 0008 and 0012. |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.c` | Classify API wrappers, `interface_set_promiscuous()` |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.h` | Extern declarations |
| `src/sonic-sairedis/vslib/vpp/SwitchVppFdb.cpp` | BVI in BD (with internal LCP pair for redirect anchor), classifier init/apply/remove for **LLDP only** in v1.1 (ARP and DHCP are handled by the sonic_ext plugin instead), tagged/untagged member handling |
| `src/sonic-sairedis/vslib/vpp/SwitchVppRif.cpp` | SUB_PORT RIF |
| `src/sonic-sairedis/vslib/vpp/SwitchVppHostif.cpp` | Promisc on every phy at LCP creation; no vppctl invocation needed (sonic_ext defaults are on) |
| `src/sonic-sairedis/vslib/vpp/SwitchVpp.h` | `m_bvi_vlan_lcp_map` member |
