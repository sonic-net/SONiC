# VLAN Bridge Domain with BVI — High-Level Design

## Revision History

| Rev | Date | Author | Summary |
|-----|------|--------|---------|
| 1.0 | 2026-04 | yuega2 | Initial design.  ARP/DHCP punted via the `l2-input-classify` clone-on-hit VPP patch (0010); IP unicast and ARP redirected via sonic_ext plugin features on the `ip4-punt`/`ip6-punt`/`arp` arcs; per-buffer state held in a global `orig_rx_by_bi[]` sidecar keyed by buffer index. |
| 1.1 | 2026-06 | yuega2 | Re-architected control-plane punt around the `sonic_ext` out-of-tree VPP plugin. Removed all dependence on classifier clone-on-hit for ARP/DHCP. Per-buffer state moved into the `vnet_buffer2(b)->unused` overlay (`sonic_ext_buffer_opaque_t`) so it survives `vlib_buffer_clone()` automatically with no atomic ops or worker handoff concerns. ARP and DHCP now reach the kernel via the `l2-flood -> linux-cp-punt-xc` path with a BVI-side feature node, then through `linux-cp-punt -> aggr-tap-redirect` on the BVI host tap, which restores the original member tap and re-pushes the wire VLAN tag from the cookie. The classifier now handles only LLDP (always redirect-punt). Updated §5 packet-flow walkthroughs to match v1.1 architecture.|
| 1.2 | 2026-06 | yuega2 | Moved DHCPv4 client-broadcast punt off the BVI `ip4-unicast` `sonic-ext-bcast-redirect` path and back onto `l2-input-classify`, matching how SONiC/SAI `SAI_PACKET_ACTION_TRAP` behaves on hardware: the frame is **consumed before `l2-flood`**, so it is punted to the originating member but **not flooded** to the other BD members (required by sonic-mgmt `DHCPBroadcastNotFloodedTest`). Untagged DHCP hits a direct `linux-cp-punt`; tagged DHCP goes through the new `sonic-ext-l2-trap-fixup` node, which swaps `VLIB_RX` from the bridged sub-if to the parent phy before `linux-cp-punt` (the L2 rewind re-exposes the intact .1Q tag, so the kernel's 8021q layer demuxes it up to the Vlan netdev — no `aggr-tap-redirect` and no tag re-push). `sonic-ext-bcast-redirect` is retired. ARP and L3-unicast-to-SVI still use the BVI `aggr-tap-redirect` path. Updated §3 and §5.5 to match.|

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

3. **Original wire ingress is lost by L2 bridging**: ARP broadcasts
   reach the BVI via `l2-flood`, by which point `vnet_buffer(b)->sw_if_index[VLIB_RX]`
   has been overwritten with the BVI sw_if. The redirect path needs to know
   which member the frame entered VPP on. We carry this in a per-buffer
   cookie stamped at `device-input` (see §3.7).  (DHCP avoids this entirely
   by trapping at `l2-input-classify` before `l2-flood`, while the buffer's
   `VLIB_RX` still points at the ingress member — see §3.2/§3.3.)

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

8. **DHCP must be trapped, not flooded or routed**: a DHCP client
   broadcast must be delivered only to the ingress member's tap and must
   **not** be flooded to other BD members (sonic-mgmt
   `DHCPBroadcastNotFloodedTest`).  Routing it through the BVI/FIB is
   also undesirable: a single global `255.255.255.255/32` route cannot
   disambiguate which bridge a discover came from, and the L3 path would
   subject DHCP to IP/UDP checksum validation.  The design therefore
   traps DHCP at `l2-input-classify` (before `l2-flood` and before any
   L3 lookup), emulating a hardware `SAI_PACKET_ACTION_TRAP`.

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
| DHCPv4 (client broadcast) | `l2-input-classify` (consume, before `l2-flood`) | untagged: direct `linux-cp-punt`; tagged: `sonic-ext-l2-trap-fixup` → `linux-cp-punt` | original member iface |
| LLDP | `l2-input-classify` (consume) | none — direct redirect-punt to `linux-cp-punt` on the member's own LCP host tap | member iface only |
| LACP | `ethernet-input` on bond | none — direct redirect-punt | original member iface only |
| IP unicast to SVI | `ip4-punt` / `ip6-punt` arc | `sonic-ext-aggr-tap-redirect` on BVI host tap interface-output | original member iface |
| Linux → wire reply | `device-input` on host tap | `sonic-ext-host-xc` → phy `interface-output` | (sent on the wire) |

Three principles unify the table:

- **The BVI is the L3 / ARP funnel.** ARP and L3 unicast reach the BVI
  naturally via the VPP graph (l2-flood for ARP broadcast, l2-fwd for
  unicast addressed to the BVI MAC). The sonic_ext plugin then redirects
  off the BVI to the correct member tap rather than letting the punt land on
  a BVI host tap.
- **DHCP and LLDP are classifier punt** because SONiC expects these
  protocols to be **punted to the originating member but not flooded** to
  the other BD members (this mirrors a hardware `SAI_PACKET_ACTION_TRAP`,
  which drops the frame from the forwarding pipeline while copying it to
  the CPU). `l2-input-classify` runs **before `l2-flood`**, so a
  redirect-punt session there consumes the frame and no peer-member or
  BVI flood copies are ever produced.
- **Per-buffer cookie disambiguates the original member.** A small overlay
  on `vnet_buffer2(b)->unused` (`sonic_ext_buffer_opaque_t`) is stamped at
  `device-input` on the wire phy and survives `vlib_buffer_clone()` (VPP
  memcpys opaque2 wholesale into every clone) and `vlib_buffer_advance()`
  (it lives in metadata, not packet bytes). The redirect node reads it back
  to recover the original RX sw_if_index and outermost wire VLAN tag.
  (The cookie is consumed only by the ARP / L3-unicast `aggr-tap-redirect`
  path; the classifier DHCP/LLDP punt does not need it.)

### 3.2 L2 Classifier-Based Punt (DHCP + LLDP)

LLDP arriving on an **untagged BD member** is punted directly from the
member interface using VPP's `l2-input-classify` feature with the
`linux-cp-punt` node as the target. Action is always
`CLASSIFY_ACTION_NONE` (redirect-punt — the original is consumed;
nothing else is done with it).

DHCPv4 client broadcasts are punted by the **same `l2-input-classify`
feature**, with one extra hop for tagged members (see below).  Both
protocols share the goal of *punt-to-member-without-flood*; the
classifier is the only L2 hook that runs **before `l2-flood`**, so it
is where SONiC's `SAI_PACKET_ACTION_TRAP` semantics are emulated.

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

**Why this is needed — DHCP must be trapped, not flooded.** A DHCP
client DISCOVER/REQUEST is an L2 broadcast (`dst=ff:ff:ff:ff:ff:ff`).
If it entered the BD it would hit `l2-flood` and fan out to **every**
other BD member port on the wire, which sonic-mgmt's
`DHCPBroadcastNotFloodedTest` explicitly forbids (a real ASIC traps
the frame to the CPU and removes it from the forwarding pipeline).
Trapping at `l2-input-classify` consumes the buffer before flood and
hands exactly one copy to the host:

- **Untagged member** — `VLIB_RX` is already the parent phy (the
  untagged BD member *is* the parent phy; sub-if dispatch never ran),
  so the session points straight at `linux-cp-punt`, which resolves
  the parent's LCP host tap directly.
- **Tagged member** — `VLIB_RX` is the bridged dot1q sub-if
  (e.g. `Ethernet0.10`), which has **no LCP pair** (a pure bridge
  member is not LCP-paired), so `linux-cp-punt` alone would drop the
  frame.  The session therefore points at `sonic-ext-l2-trap-fixup`,
  which rewrites `VLIB_RX` to the parent phy (`Ethernet0`) and then
  hands to `linux-cp-punt`.  Because the classifier runs before L2
  VTR pop, the 802.1Q tag is still in buffer memory; `linux-cp-punt`
  rewinds to the wire L2 start and re-exposes the tagged frame, so
  the kernel sees it on `Ethernet0` with the tag intact and its
  8021q layer demuxes it up to `Ethernet0.10` / `Vlan10`, where
  `dhcrelay` (or the in-VLAN server) is listening.  No
  `aggr-tap-redirect` and no tag re-push are involved — going via the
  BVI tap would double-tag the frame.

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

### 3.3 Classifier Table Design (DHCP + LLDP)

Four shared classify tables are created lazily on the first BD member add and
persist for the lifetime of the process.  Two `l2-input-classify` hit-next
indices are resolved once via `vpp_add_node_next()`:

- `linux-cp-punt` — LLDP (any) and **untagged** DHCPv4.
- `sonic-ext-l2-trap-fixup` — **tagged** DHCPv4 only (rewrites `VLIB_RX`
  to the parent phy, then hands to `linux-cp-punt`).  If this plugin node
  is not registered, the tagged-DHCP table is skipped and only tagged
  DHCP punt is lost; untagged DHCP and all LLDP are unaffected.

`l2-input-classify` selects the per-interface table slot by the **outer**
ethertype at `current_data`:

- `0x0800` (IPv4) → ip4 slot
- `0x86DD` (IPv6) → ip6 slot (unused here)
- everything else (incl. `0x8100` VLAN and `0x88CC` LLDP) → other slot

DHCPv4 client→server is matched on: `dst MAC == ff:ff:ff:ff:ff:ff`,
ethertype `0x0800`, IP `proto == UDP (17)`, and UDP `dport == 67`
(BOOTPS; `sport` is intentionally not matched).  IP options are not
matched (IHL=5 assumed, same assumption SAI TCAM trap rules make).

#### 3.3.1 Untagged Member Tables

Untagged frames carry the inner protocol's ethertype on the wire, so
DHCPv4 lands in the **ip4 slot** and LLDP in the **other slot** — there
is no chain between them.

**Table: untag_ip4** — DHCPv4 client broadcast (skip=0, match=3, 48-byte vector)

| Byte Offset | Field | Mask |
|-------------|-------|------|
| 0–5 | dst MAC = `ff:ff:ff:ff:ff:ff` | `0xFF×6` |
| 12–13 | Ethertype = `0x0800` | `0xFFFF` |
| 23 | IP protocol = UDP (`0x11`) | `0xFF` |
| 36–37 | UDP dport = `67` | `0xFFFF` |

Session: hit → `linux-cp-punt` (action NONE).  Miss → continue (non-DHCP
IPv4 traffic is unaffected).

**Table: untag_other** — matches ethertype directly (skip=0, match=1)

| Byte Offset | Field | Mask |
|-------------|-------|------|
| 12–13 | Ethertype | `0xFFFF` |

Session: LLDP `0x88CC` → `linux-cp-punt` (action NONE).  Miss → continue
L2 feature chain (to VTR, learn, fwd, flood).

#### 3.3.2 Tagged Member Tables

A tagged frame's outer ethertype is `0x8100`, so **every** tagged frame
(including IPv4-inside-VLAN) lands in the **other slot**.  The other slot
chains `tag_other → tag_dhcp → continue`.  All post-L2 offsets shift by
+4 because the 802.1Q tag is still present at classify time (L2 VTR pop
has not yet run).

**Table: tag_other** — inner ethertype (skip=1, match=1; defensive LLDP)

| Byte Offset | Field | Mask |
|-------------|-------|------|
| 16–17 | inner ethertype | `0xFFFF` |

Session: inner LLDP `0x88CC` → `linux-cp-punt` (defensive; tagged LLDP
normally never reaches the BD — see §3.2).  Miss → chain to `tag_dhcp`.

**Table: tag_dhcp** — DHCPv4 over .1Q (skip=0, match=3, 48-byte vector)

| Byte Offset | Field | Mask |
|-------------|-------|------|
| 0–5 | dst MAC = `ff:ff:ff:ff:ff:ff` | `0xFF×6` |
| 16–17 | inner ethertype = `0x0800` | `0xFFFF` |
| 27 | IP protocol = UDP (`0x11`) | `0xFF` |
| 40–41 | UDP dport = `67` | `0xFFFF` |

Session: hit → `sonic-ext-l2-trap-fixup` (action NONE).  Miss → continue
normal L2 path.

#### 3.3.3 Table Attachment

When a BD member is added (`l2_punt_classify_apply()`):
- **Untagged member** (parent phy, e.g., `bobm0`):
  `classify_set_interface_l2_tables(bobm0, ip4=untag_ip4, ip6=~0, other=untag_other)`
- **Tagged member** (dot1q sub-if, e.g., `bobm0.10`):
  `classify_set_interface_l2_tables(bobm0.10, ip4=~0, ip6=~0, other=tag_other)`
  (the ip4 slot is unused because the outer ethertype is `0x8100`).

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
| `sonic-ext-l2-trap-fixup` | hit-next of `l2-input-classify` | resolved as a graph next of `l2-input-classify`; used only by the **tagged-DHCP** classifier session (§3.3.2) | Substitute the **parent physical interface** for the bridged sub-if in `b->sw_if_index[VLIB_RX]`, then hand off to `linux-cp-punt`.  Needed because a pure bridge sub-if (e.g. `Ethernet0.10`) has no LCP pair, so `linux-cp-punt` would otherwise drop the frame.  The buffer still carries its wire .1Q tag below `current_data`, so the subsequent `linux-cp-punt` rewind re-exposes the tagged frame verbatim — no tag re-push, and the BVI `aggr-tap-redirect` arc is **not** traversed (going via the BVI would double-tag). Protocol-agnostic — future STP/IGMP/CoPP traps can reuse it. |
| `sonic-ext-aggr-tap-redirect` | `interface-output` | runs on the BVI's host-tap interface (and any future bond/lag aggregate tap) | Read the cookie. Look up the LCP pair of `orig_rx_sw_if_index` and rewrite `b->sw_if_index[VLIB_TX]` to that LCP's host tap.  If `orig_vlan_tag != 0`, mac-shift the L2 header back 4 bytes and write `[TPID 0x8100][TCI orig_vlan_tag]` at offsets 12 and 14, restoring the original wire VLAN.  Update `vnet_buffer(b)->l2_hdr_offset` so any later rewind lands on the tagged header. |

The `sonic-ext-arp-redirect` and `sonic-ext-ip{4,6}-punt-redirect` features
of v1.0 collapse into the same `aggr-tap-redirect` egress feature because
ARP and L3-unicast-to-SVI both funnel through the BVI's host-tap egress
path.  DHCP no longer uses this egress feature — it is trapped at
`l2-input-classify` (§3.3) before reaching the BVI:

- **ARP** flooded onto a BD member → `l2-input` → `l2-input-classify`
  (DHCP/LLDP classifier misses on ARP) → `l2-learn` →
  `l2-flood` → `linux-cp-punt-xc` → BVI host tap
  `interface-output` → `aggr-tap-redirect` → member host tap.
- **DHCP** (client broadcast) → `l2-input` → `l2-input-classify`
  **hit** (consume, before `l2-flood`) → untagged: `linux-cp-punt`;
  tagged: `sonic-ext-l2-trap-fixup` → `linux-cp-punt` → parent phy host
  tap.  No BVI, no flood copies.
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
  - If `phy` is a BVI, enable `sonic-ext-aggr-tap-redirect` on the BVI's
    host-tap `interface-output` arc (for ARP and L3-unicast-to-SVI).
- On `lcp_itf_pair_del_cb(...)`: symmetric disable.

Because node enablement is driven from LCP pair add/del, BVIs without
an LCP pair are never touched.  Concretely:

- **L3 SVI BVIs** (the BVI for a routed VLAN) get an LCP pair via
  `lcp-auto-subint` / the explicit BVI LCP pair from §3.8, so
  `aggr-tap-redirect` is enabled and ARP / L3-unicast punts on those
  BVIs are redirected to the originating member tap.
- **VXLAN tunnel-termination BVIs** (BVIs created only as the L2 end
  of a VXLAN VNI ↔ VLAN mapping, with no `Vlan<id>` host interface) do
  **not** have an LCP pair, so the egress redirect stays disabled.

`sonic-ext-l2-trap-fixup` is **not** a per-interface feature — it is a
graph node resolved as a hit-next of `l2-input-classify` and is reached
only when the tagged-DHCP classifier session (installed per BD member by
SAI, §3.3.2) fires.  DHCP punt therefore does not depend on any BVI
feature being enabled.

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
plugin layout doesn't lock us out of supporting full-header punt
later — both the classifier-clone hooks and the side-car table can be
added without changing the redirect-node interfaces (`aggr-tap-redirect`,
`host-xc`) which only consume the cookie.

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

BVI flood/UU flood are left **enabled**.  ARP traverses the BVI on the
bridge-flood path; the redirect node hands it off to the correct member
tap on the way out.  DHCP does **not** traverse the BVI \u2014 it is trapped
at `l2-input-classify` before `l2-flood` (\u00a73.2/\u00a73.3).

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

Lazily creates the four shared classify tables (`untag_ip4`,
`untag_other`, `tag_other`, `tag_dhcp`) and their redirect-punt sessions
described in Section 3.3, and resolves the two `l2-input-classify`
hit-next indices (`linux-cp-punt`, `sonic-ext-l2-trap-fixup`).  Called
automatically on the first BD member add.  If `sonic-ext-l2-trap-fixup`
is not registered (plugin missing), the `tag_dhcp` table is skipped and
only tagged-DHCP punt is lost; untagged DHCP and all LLDP still work via
the direct `linux-cp-punt` next.

### 4.5 The `sonic_ext` VPP Plugin

Implements the design in §3.7 entirely as an out-of-tree VPP plugin
under `platform/vpp/vppbld/plugins/sonic_ext/`.  The build system
auto-copies that directory into `repo/src/plugins/` and the upstream
plugin glob auto-discovers it, so **no modifications to upstream VPP
source are required**.  Patches `0008` and `0012` (legacy in-tree punt
hooks) were removed when this plugin was introduced; patch `0010`
(classifier clone-on-hit) is no longer required by the v1.1 design and
is retained only for the future alternative described in §3.7.4.

The plugin contains four feature/graph nodes plus a CLI/init module:

| Node | Arc | Bound to | Purpose |
|------|-----|----------|---------|
| `sonic-ext-capture` | `device-input` | wire phys only (skipped on BVIs and host taps via `sonic_ext_phy_is_aggregate()`) | Stamp `sonic_ext_buffer_opaque_t` cookie (`magic='SNCX'`, `orig_rx`, `orig_vlan_tag`) on `vnet_buffer2(b)->unused` before `ethernet-input` overwrites RX. |
| `sonic-ext-host-xc` | `device-input` | LCP host taps | Steer Linux replies straight to the paired phy's `interface-output`. |
| `sonic-ext-l2-trap-fixup` | hit-next of `l2-input-classify` | tagged-DHCP classifier session only | Rewrite `VLIB_RX` from the bridged sub-if to the parent phy, then hand to `linux-cp-punt` (the sub-if has no LCP pair). Protocol-agnostic; reusable by future L2 CoPP traps. |
| `sonic-ext-aggr-tap-redirect` | `interface-output` | BVI host tap | Read cookie; rewrite `VLIB_TX = LCP host tap of orig_rx`; if `orig_vlan_tag != 0`, re-insert `[0x8100][orig_vlan_tag]` into the L2 header. Used by ARP and L3-unicast-to-SVI (not DHCP). |

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
via `sonic_ext_phy_is_aggregate(phy)`); if the phy is a BVI the BVI host
tap's `interface-output` feature `sonic-ext-aggr-tap-redirect` is also
enabled (for ARP and L3-unicast-to-SVI).  Symmetric disable on pair
delete.

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
  on BD members matches only LLDP (`0x88CC`) and DHCPv4; LACP is
  handled earlier by the linux-cp ethertype shortcut, so adding a
  classifier session for `0x8809` would be redundant (and never hit).
- **No BVI involvement.**  LACP never reaches `l2-input` on the
  member sub-interface, so `l2-flood` does not produce a BVI copy.
- **`sonic_ext` cookie is stamped but unused.**  `sonic-ext-capture`
  runs unconditionally on every wire phy at `device-input`, ahead of
  the ethertype shortcut.  For LACP the cookie is simply discarded
  along with the buffer once the kernel consumes the frame.

### 5.5 DHCP Broadcast from a BD Member

DHCP client broadcasts (`dst MAC = ff:ff:ff:ff:ff:ff`, `dst IP =
255.255.255.255`, UDP `dport=67`) are **trapped at `l2-input-classify`
before `l2-flood`**, so they are punted to the originating member only
and are **never flooded** to the other BD members (emulating a hardware
`SAI_PACKET_ACTION_TRAP`; sonic-mgmt's `DHCPBroadcastNotFloodedTest`
relies on this).  The graph differs slightly for tagged vs untagged
members because a bridged dot1q sub-if has no LCP pair:

- **Untagged member** — the classifier ip4-slot session (`untag_ip4`)
  hits and points directly at `linux-cp-punt`.  `VLIB_RX` is already
  the parent phy, so the frame lands on that phy's host tap.
- **Tagged member** — the classifier other-slot chain
  (`tag_other → tag_dhcp`) hits `tag_dhcp` and points at
  `sonic-ext-l2-trap-fixup`, which swaps `VLIB_RX` to the parent phy
  and hands to `linux-cp-punt`.  The 802.1Q tag is still in buffer
  memory (L2 VTR pop has not run), so the `linux-cp-punt` rewind
  re-exposes the tagged frame and the kernel's 8021q layer demuxes it
  up to the Vlan netdev.  Neither the BVI nor `aggr-tap-redirect` is
  involved.

```
Wire (DHCP DISCOVER, 802.1q vlan 10 — tagged member bobm0.10)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie {orig_rx=26, orig_vlan_tag=10}  (unused on this path)
      → ethernet-input: dispatch to bobm0.10, step past .1Q tag
        → l2-input (sw_if 26, BD 1)
          → l2-input-classify: other-slot tag_other (miss)
                              → tag_dhcp (HIT, action NONE) → CONSUMED (no l2-flood)
            → sonic-ext-l2-trap-fixup: VLIB_RX 26 → 1 (parent phy Ethernet0)
              → linux-cp-punt: lip-punt 1 → 17  (parent phy → tap4101)
                  rewind to wire L2 start (re-exposes .1Q vlan 10)
                → tap4101-output / tap4101-tx  (DHCP, 802.1q vlan 10 intact)
                  → kernel: Ethernet0 → 8021q → Ethernet0.10 → Vlan10 → dhcrelay
```

Untagged member (e.g. `bobm1` as a `Vlan10` access port):

```
Wire (DHCP DISCOVER, no tag — untagged member bobm1)
  → bobm1 (dpdk-input)
    → sonic-ext-capture: stamp cookie (unused)
      → ethernet-input → l2-input (sw_if = bobm1, BD 1)
        → l2-input-classify: ip4-slot untag_ip4 (HIT, action NONE) → CONSUMED (no l2-flood)
          → linux-cp-punt: lip-punt bobm1 → tap(Ethernet4)
            → kernel: Ethernet4 → Vlan10 → dhcrelay
```

Key observations:

- **No flood copies at all.**  Because the classifier consumes the
  buffer before `l2-flood`, there is exactly one punted copy and zero
  wire copies to peer members.  This is the behavior
  `DHCPBroadcastNotFloodedTest` checks for.
- **DHCPv4 client→server match only.**  The classifier matches
  `dst MAC = ff:ff:ff:ff:ff:ff`, ethertype `0x0800`, IP `proto=UDP`,
  and UDP `dport=67`.  Other broadcast/L2 traffic misses the session
  and continues the normal L2 path (learn/fwd/flood) unchanged.
  Server→client (`sport=67/dport=68`) is not matched here — that
  direction is generated locally and egresses via the BVI, not a wire
  member RX.
- **Tagged vs untagged differ only by the fixup hop.**  Untagged DHCP
  goes straight to `linux-cp-punt`; tagged DHCP inserts
  `sonic-ext-l2-trap-fixup` to repoint `VLIB_RX` at the parent phy.
  The VLAN tag is preserved by the L2 rewind in both the wire memory
  and the kernel's 8021q demux — there is no explicit tag re-push.
- **Punted copy lands on the member's own tap**, not a `Vlan10` tap.
  The kernel observes the DHCP request on the netdev corresponding to
  the original wire ingress (`Ethernet0.10` for `bobm0.10`,
  `Ethernet4` for `bobm1`), which is what the SONiC DHCP relay expects.

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
  switch runs a DHCP server bound to the Vlan SVI / member netdev.  The
  server sees the DISCOVER through the same member-tap that `dhcrelay`
  would have used, because the punted copy is delivered to the *ingress
  member's* host tap (where Linux exposes it as `Ethernet0.10`, which is
  enslaved to `Vlan10`).  The server replies through the kernel; the
  reply path is the standard Linux → host-tap → BVI → `l2-output` flow
  back out the wire.

SONiC ensures either DHCP relay or server is enabled but not both.

DHCP client broadcasts are **trapped at `l2-input-classify` and
consumed before `l2-flood`**, so they are **not** flooded to the other
BD members — only the on-switch relay/server (bound to the SVI via the
ingress member tap) receives them.  This matches a hardware switch with
`SAI_PACKET_ACTION_TRAP` for DHCP, and is exactly what sonic-mgmt's
`DHCPBroadcastNotFloodedTest` verifies.  A foreign DHCP server living on
another member port of the same VLAN therefore does **not** see the
DISCOVER via L2 flooding under this design.

Consequences:

1. **Foreign in-VLAN DHCP server is not an expected SONiC topology.**
   SONiC's DHCP model assumes the DHCP client and DHCP server are
   *not* both behind member ports of the same VLAN: either the server
   is L3-remote (reached via `dhcrelay`) or it runs on the switch
   itself (`dhcp-server` bound to the SVI).  Because the client
   broadcast is trapped before `l2-flood`, a foreign in-VLAN server on
   another member port will **not** receive it — consistent with the
   trap-to-CPU behaviour of real hardware.

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

3. **Double-servicing via L2 flood is no longer possible.**  Because
   the client broadcast is consumed at `l2-input-classify` before
   `l2-flood`, a foreign in-VLAN DHCP server on another member port
   never receives a flooded copy, so it cannot race the on-switch
   relay/server.  Only the on-switch daemon (relay or in-VLAN server)
   answers, matching a hardware switch that traps DHCP to the CPU.

4. **Which member sees the punt** is unambiguous: the classifier
   trap runs on the ingress member's `l2-input-classify`, so the
   punted copy is delivered to that ingress member's tap (directly for
   untagged members, or via `sonic-ext-l2-trap-fixup` → parent phy for
   tagged members) — never to a sibling member's tap.  There is
   exactly one punted copy per ingress frame and zero wire flood
   copies.

5. **DHCPv6 is out of scope.**  Everything above describes DHCPv4
   only.  DHCPv6 client traffic is **link-scoped IPv6 multicast** to
   `ff02::1:2` (`All_DHCP_Relay_Agents_and_Servers`) — it is *not* a
   limited IPv4 broadcast, so the DHCPv4 classifier sessions do not
   match it and there is no equivalent IPv6 trap in the current
   design.  On the BVI, `ip6-input` / `ip6-mfib` will handle the
   multicast per the BVI's IPv6 multicast routing / MLD state
   (typically l2-flood only, no punt to Linux), so DHCPv6 will *not*
   be delivered to a member host tap by this design.  DHCPv6 relay /
   server support is deferred to a future HLD together with IPv6 ND
   (§7); when that work lands, an IPv6 DHCPv6 classifier session
   (matching the DHCPv6 link-local multicast destinations `ff02::1:2`,
   and `ff05::1:3` for the relay-agent scope) will be added on the BD
   member, reusing the same `l2-input-classify` → `linux-cp-punt` /
   `sonic-ext-l2-trap-fixup` punt path.

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

The DHCPv4 `l2-input-classify` trap does not affect this path: a unicast
frame to the SVI does not have a broadcast dst MAC and so misses the
classifier session, continuing down the normal L2-forward-to-BVI path.

```
Wire (ICMP echo, 802.1q vlan 10 — tagged member bobm0.10)
  → bobm0 (dpdk-input)
    → sonic-ext-capture: stamp cookie {orig_rx=1, orig_vlan_tag=10}
      → ethernet-input → l2-input (sw_if 23, BD 1)
        → l2-input-classify (LLDP miss → continue)
        → l2-input-vtr: pop outer 802.1Q
        → l2-learn / l2-fwd  (dst MAC resolved to BVI, sw_if 24)
          → ip4-input on BVI
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
  Table 0 (untag_ip4)  : skip=0 match=3 sessions=1  # DHCPv4 (untagged)
  Table 1 (untag_other): skip=0 match=1 sessions=1  # LLDP    (untagged)
  Table 2 (tag_dhcp)   : skip=0 match=3 sessions=1  # DHCPv4 over .1Q (tagged)
  Table 3 (tag_other)  : skip=1 match=1 sessions=1  # inner LLDP, chains to tag_dhcp

# Classifier attachment
vppctl show classify interface
  bobm1:    ip4=0 (untag_ip4) ip6=~0 other=1 (untag_other)   # untagged member
  bobm0.10: ip4=~0 ip6=~0 other=3 (tag_other → tag_dhcp)     # tagged member

# sonic_ext plugin state
vppctl show sonic-ext
  punt-via-member : on (default)
  host-xc         : on (default)
  l2 trap fixups  : <counter>          # tagged-DHCP punts repointed to parent phy

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

**DHCPv6** is also explicitly out of scope (see §5.5
consequence #5).  Unlike DHCPv4 it is link-scoped IPv6 multicast
(`ff02::1:2` for client → relay/server, `ff05::1:3` for relay → server),
so the IPv4-only DHCPv4 classifier sessions do not catch it and the
design currently has no IPv6 punt path for it.  When DHCPv6 support is
required, a DHCPv6 `l2-input-classify` session (matching the ICMPv6/UDP
DHCPv6 multicast destinations) will be added on the BD member, reusing
the same `linux-cp-punt` / `sonic-ext-l2-trap-fixup` punt path to
deliver the frame to the originating member's host tap (where
`dhcp6relay` / `kea-dhcp6` / etc. observe it).  This work is expected
to land alongside the IPv6 ND solution above.
---

## 8. Files Modified

| File | Change |
|------|--------|
| `platform/vpp/docker-syncd-vpp/conf/startup.conf.tmpl` | Ensure `lcp-auto-subint` is **disabled** |
| `platform/vpp/docker-sonic-vpp/conf/startup.conf.tmpl` | Ensure `lcp-auto-subint` is **disabled** |
| `platform/vpp/vppbld/patches/0010-l2-input-classify-clone-on-hit.patch` | **No longer required** by the v1.1 design.  Retained in the patch directory only as a building block for the future full-header punt option (§3.7.4). |
| `platform/vpp/vppbld/plugins/sonic_ext/` | Out-of-tree VPP plugin: `sonic-ext-capture`, `sonic-ext-host-xc`, `sonic-ext-l2-trap-fixup`, `sonic-ext-aggr-tap-redirect` + CLI/init.  Per-buffer cookie on `vnet_buffer2(b)->unused`.  Defaults `punt-via-member` and `host-xc` to **on** at init.  Hooks into LCP pair add/del to manage per-pair feature enablement.  Supersedes patches 0008 and 0012. |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.c` | Classify API wrappers, `interface_set_promiscuous()` |
| `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.h` | Extern declarations |
| `src/sonic-sairedis/vslib/vpp/SwitchVppFdb.cpp` | BVI in BD (with internal LCP pair for redirect anchor), classifier init/apply/remove for **LLDP and DHCPv4** (untagged DHCP → `linux-cp-punt`, tagged DHCP → `sonic-ext-l2-trap-fixup`); ARP is handled by the sonic_ext plugin instead; tagged/untagged member handling |
| `src/sonic-sairedis/vslib/vpp/SwitchVppRif.cpp` | SUB_PORT RIF |
| `src/sonic-sairedis/vslib/vpp/SwitchVppHostif.cpp` | Promisc on every phy at LCP creation; no vppctl invocation needed (sonic_ext defaults are on) |
| `src/sonic-sairedis/vslib/vpp/SwitchVpp.h` | `m_bvi_vlan_lcp_map` member |
