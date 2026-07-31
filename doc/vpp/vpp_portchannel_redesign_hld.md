# Port Channel Punt Redesign — High-Level Design

## Revision History

| Rev | Date       | Author  | Summary |
|-----|------------|---------|---------|
| 1.0 | 2026-06-30 | Yue Gao | Initial design. Redesign of port-channel control-plane punt so that traffic received on a bonded member is delivered to Linux **on the originating member netdev** (and let the kernel bond/8021q stack carry it up to `PortChannel<id>[.<vlan>]`), instead of being punted directly onto the `PortChannel<id>` netdev via the `be<id>` host tap + TC redirect. Reuses the existing `sonic_ext` capture + aggregate-tap-redirect machinery (originally built for VLAN/BVI) by teaching `sonic_ext_phy_is_aggregate()` to recognize bond masters and bond sub-interfaces. |

---

## 1. Problem Statement

The current port-channel implementation punts control-plane packets **directly to
the `PortChannel<id>` (bond) netdev**:

- `sonic-sairedis` creates the bond as `BondEthernet<id>` and, on the first member
  enslave, wires a linux-cp pair `BondEthernet<id> ↔ be<id>` plus a TC filter
  redirect `be<id> → PortChannel<id>`
  (`SwitchVppFdb.cpp`, `vpp_create_lag_member`).
- A packet received on a bonded member and punted by VPP is dispatched by
  `linux-cp-punt-xc` to the `be<id>` host tap, and the TC redirect moves it
  straight onto the Linux `PortChannel<id>` team/bond netdev.

This **does not conform to the SONiC data-plane model.** On real hardware the NPU
punts control traffic to the CPU on the **physical/member port** it was received
on; the Linux bonding driver (and, for tagged traffic, the 8021q layer) is then
responsible for delivering the frame up to the logical `PortChannel<id>` /
`PortChannel<id>.<vlan>` netdev. SONiC per-port daemons therefore expect to see
punted frames arrive with the **member ifindex**, not the aggregate ifindex.

The most visible symptom is **DHCP relay**. `sonic-dhcp-relay` / `dhcrelay`
(the SONiC relay agent) binds and accepts uplink packets **only on port-channel
member interfaces**. Because today's solution delivers the frame on the
`PortChannel<id>` netdev instead of the member, the relay agent never sees the
uplink packet and DHCP relay over a port-channel uplink is broken.

### Goal

Punt port-channel control traffic **via the member interface**:

1. Deliver the frame to the LCP host tap of the **member** that actually received
   it on the wire.
2. Support port-channel subinterface and deliver the frame to the LCP host tap of
   the **member** interface with the wire VLAN tag. This ensures kernel 8021q layer
   can demux tagged (sub-interface) traffic to `PortChannel<id>.<vlan>`.
3. Keep data-plane forwarding and the kernel-to-wire (host → phy) direction
   unchanged.

---

## 2. SONiC Configuration Example

Standard SONiC `CONFIG_DB` for a routed port channel with two members, an L3
address on the main interface, and a routed VLAN sub-interface:

```json
{
  "PORTCHANNEL": {
    "PortChannel10": {
      "admin_status": "up",
      "mtu": "9100",
      "lacp_key": "auto"
    }
  },

  "PORTCHANNEL_MEMBER": {
    "PortChannel10|Ethernet0": {},
    "PortChannel10|Ethernet4": {}
  },

  "PORTCHANNEL_INTERFACE": {
    "PortChannel10": {},
    "PortChannel10|1.0.0.1/24": {}
  },

  "VLAN_SUB_INTERFACE": {
    "PortChannel10.1": {
      "admin_status": "up",
      "vlan": "1"
    },
    "PortChannel10.1|2.0.0.1/24": {}
  }
}
```

Resulting objects:

| SONiC name              | VPP interface            | Linux host netdev            |
|-------------------------|--------------------------|------------------------------|
| `PortChannel10`         | `BondEthernet10`         | `be10` (LCP tap) → `PortChannel10` (team) |
| `PortChannel10` members | `BondEthernet10` members | `Ethernet0`, `Ethernet4` member taps |
| `PortChannel10.1`       | `BondEthernet10.1`       | `PortChannel10.1` (8021q on the team netdev) |

---

## 3. Design Principles (Punt Strategy Summary)

The design utilizes the punt-via-member infra in sonic-ext plugin introduced for VLAN/BVI. It uses
sonic-ext-capture node to record the original rx interface. Then uses sonic-ext-aggr-tap-redirect
node attached to output path of aggregate tap interface (bvi, bond etc) to restore the vlan tag in
the packet and redirect it to the original member tap interface.

The design divides port-channel traffic into classes and defines, for each,
**where the punted copy must land in Linux** and **how VPP delivers it there**.

| Traffic class | Received on | Must appear in Linux on | VPP punt mechanism |
|---------------|-------------|--------------------------|--------------------|
| **ARP** (main interface) | member phy | member netdev → kernel bond → `PortChannel10` | `linux-cp-punt-xc` → `be10` tap → **`sonic-ext-aggr-tap-redirect` → member tap** |
| **IPv4 unicast for-us** (main interface) | member phy | member netdev → kernel bond → `PortChannel10` | same as ARP |
| **ARP** (sub-interface) | member phy (tagged) | member netdev → bond → 8021q → `PortChannel10.1` | `linux-cp-punt-xc` → `be10.1` tap → **`sonic-ext-aggr-tap-redirect` → member tap (re-push .1Q)** |
| **IPv4 unicast for-us** (sub-interface) | member phy (tagged) | member netdev → bond → 8021q → `PortChannel10.1` | same as sub-if ARP |
| **LLDP** | member phy | member netdev directly | member's own linux-cp punt (**unchanged**) |
| **LACP** | member phy | member netdev directly (teamd) | member's own linux-cp punt (**unchanged**) |

Key principles:

1. **Never punt to the aggregate netdev.** All punted copies are delivered on the
   originating member tap; the Linux bonding + 8021q stack does the rest.
2. **The member is recovered from a per-buffer cookie**, not from
   `VLIB_RX` (which `bond-input` overwrites with `BondEthernet<id>`). The cookie
   is stamped at `device-input` before any L2 rewrite.
3. **Slow protocols (LLDP, LACP) are untouched.** They already punt to the member
   tap through each member's own linux-cp pair — the bond master is not on their
   path — so no change is required.
4. **Toggleable.** The behaviour is gated by the existing `sonic-ext
   punt-via-member` runtime toggle (default on); disabling it restores the legacy
   punt-to-aggregate behaviour.

---

## 4. Current Solution (for contrast)

```
member Ethernet0 (wire) ── ARP/IP punt ──▶ linux-cp-punt-xc
        │                                     │  VLIB_TX = be10 (bond host tap)
        ▼                                     ▼
   bond-input                            interface-output[be10]
   (VLIB_RX = BondEthernet10)                 │
                                              ▼  TC filter redirect
                                        PortChannel10 netdev   ✗ wrong netdev
```

The frame lands on `PortChannel10`; per-member consumers (DHCP relay) never see it.

---

## 5. Proposed Solution (changes in the `sonic_ext` plugin)

The `sonic_ext` out-of-tree VPP plugin already implements everything needed for
**VLAN/BVI** aggregate punt. The redesign extends that same machinery to bonds; no
new nodes are required.

### 5.1 Existing building blocks (reused as-is)

- **`sonic-ext-capture`** (feature on the `device-input` arc, enabled on every
  real wire phy). Stamps a per-buffer cookie
  (`sonic_ext_buffer_opaque_t` inside `vnet_buffer2(b)->unused`) with a magic +
  `orig_rx_sw_if_index` (the member) + the wire VLAN tag, before
  `ethernet-input`/`bond-input` can overwrite `VLIB_RX`. Because it lives in
  `opaque2`, the cookie survives `vlib_buffer_clone()` (flood/mcast paths).
- **`sonic-ext-aggr-tap-redirect`** (feature on the `interface-output` arc,
  enabled on the LCP **host tap of every aggregate phy**). When `linux-cp-punt-xc`
  has already set `VLIB_TX` to the aggregate host tap (`be10` / `be10.1`), this
  node reads the cookie, looks up the LCP pair of the original member
  (`lcp_itf_pair_find_by_phy(orig_rx)`), rewrites `VLIB_TX` to the **member tap**,
  and re-pushes the saved wire VLAN tag when one was present. Re-entering
  `interface-output` on the member tap (which does not have this feature) delivers
  the frame with no recursion.

### 5.2 The one required change: recognize bonds as aggregates

`sonic_ext_phy_is_aggregate()` currently returns true only for a BVI. The redesign
makes it also return true for:

- a **bond master** (`BondEthernet<id>`), and
- a **bond sub-interface** (`BondEthernet<id>.<vlan>`),

detected via `sonic_ext_phy_is_bond()` (which resolves the super-hw interface and
matches the `"bond"` device class, so it is true for both the master and its
sub-interfaces, and false for members and regular ports).

Flipping this predicate has two automatic effects, both driven by the existing
LCP-pair add/del callback (`sonic_ext_lcp_pair_add_cb`):

1. **`sonic-ext-aggr-tap-redirect` is enabled** on the bond/sub-if host tap
   (`be<id>` / `be<id>.<vlan>`), so punted frames are steered to the member tap.
2. **`sonic-ext-capture` stays enabled on the members** (members are not
   aggregates) and **is not enabled on the bond master**, exactly as required —
   the cookie is produced on the wire member and consumed at the aggregate tap.

### 5.3 sonic-sairedis alignment

- The member LCP pairs created at port init are **retained** after enslave, so
  `lcp_itf_pair_find_by_phy(orig_rx)` always resolves to a valid member tap
  (redirect target).
- The routed **sub-interface** `BondEthernet<id>.<vlan>` is given a **valid LCP
  pair** with a host tap named `be<id>.<vlan>` (a VLAN netdev on the `be<id>`
  tap), so `linux-cp-punt-xc` has a valid host to punt to and
  `aggr-tap-redirect` runs on it. The name intentionally differs from the kernel
  8021q netdev `PortChannel<id>.<vlan>` to avoid a name collision.
  However, the host tap for BondEthernet and subinterface are not used for punting
  traffic. The TC redirect filter used to forward packets from BondEthernet to
  PortChannel kernel netdev is not needed anymore and will be removed.

### 5.4 Runtime control

The behaviour follows the existing global toggle:

```
vppctl sonic-ext punt-via-member enable    # default
vppctl sonic-ext punt-via-member disable   # legacy punt-to-aggregate
vppctl show sonic-ext                       # shows punt-via-member on/off + counters
```

---

## 6. Packet Flow

Legend: `bobmN` = member wire phy in VPP; `be10` = bond LCP host tap; `Ethernet0`
tap = member LCP host tap; `PortChannel10` = Linux team netdev.

### 6.1 ARP over the port-channel **main** interface

The trace below is a broadcast ARP (`22:f8:d0:b9:ed:35 → ff:ff:ff:ff:ff:ff`)
received on member phy `bobm0` (`sw_if_index 1`, SONiC `Ethernet0`) of
`BondEthernet10`. Aggregate LCP tap `be10` is `sw_if_index 24` (`tap4107`) and
the member LCP tap is `sw_if_index 17` (`tap4101`).

```
1. dpdk-input                     bobm0 (member phy) rx        [VLIB_RX = bobm0, sw_if_index 1]
     ARP: 22:f8:d0:b9:ed:35 -> ff:ff:ff:ff:ff:ff
2. sonic-ext-capture              sw_if_index 1                → cookie: orig_rx = member (1)
3. bond-input                     bobm0 -> BondEthernet10      [VLIB_RX rewritten = BondEthernet10]
4. ethernet-input                 ARP
5. linux-cp-punt-xc               lip-punt: 23 -> 24           [VLIB_TX = be10 tap (24)]
6. tap4107-output (be10 tap)      → sonic-ext-aggr-tap-redirect
       SONIC-EXT-AGGR-TAP-REDIRECT: aggr-tap 24 orig-rx 1 member-tap 17 REDIRECTED
7. tap4101-output (member tap 17) → tap4101-tx                 [VLIB_TX = Ethernet0 tap (17)]
       ARP: 22:f8:d0:b9:ed:35 -> ff:ff:ff:ff:ff:ff
8. member netdev → Linux bond driver delivers up to PortChannel10   ✓ member ifindex
```

Notes:
- `sonic-ext-capture` runs at `device-input`, **before** `bond-input` rewrites
  `VLIB_RX` to `BondEthernet10`, so the cookie preserves the true ingress member
  (`sw_if_index 1`).
- The punt lands first on the aggregate tap `be10` (`linux-cp-punt-xc` 23 → 24);
  `sonic-ext-aggr-tap-redirect` then reads the cookie and redirects the buffer
  from `aggr-tap 24` to `member-tap 17`, so the frame is delivered on the member
  netdev rather than the `PortChannel10` netdev.

### 6.2 IPv4 unicast (for-us) over the port-channel **main** interface

```
1. ICMP/TCP to 1.0.0.1 arrives on member Ethernet0       [VLIB_RX = member]
2. sonic-ext-capture                                     → cookie: orig_rx=member
3. ethernet-input → bond-input                           [VLIB_RX = BondEthernet10]
4. ip4-input (IP4 enabled on BondEthernet10, addr 1.0.0.1)
       → for-us → linux-cp-punt-xc                        [VLIB_TX = be10]
5. interface-output[be10] → sonic-ext-aggr-tap-redirect
       reads cookie → member LCP tap                     [VLIB_TX = Ethernet0 tap]
6. member netdev → Linux bond → PortChannel10            ✓
   (kernel answers the ping / hands to the socket on PortChannel10)
```

### 6.3 ARP over the port-channel **sub-interface** (`PortChannel10.1`)

The trace below is a broadcast ARP tagged `802.1q vlan 1`
(`22:f8:d0:b9:ed:35 → ff:ff:ff:ff:ff:ff`) received on member phy `bobm0`
(`sw_if_index 1`, SONiC `Ethernet0`). The aggregate sub-interface LCP tap
`be10.1` is `sw_if_index 26` (`tap4107.1`) and the member LCP tap is
`sw_if_index 17` (`tap4101`).

```
1. dpdk-input                     bobm0 (member phy) rx        [VLIB_RX = bobm0, sw_if_index 1]
     ARP: 22:f8:d0:b9:ed:35 -> ff:ff:ff:ff:ff:ff 802.1q vlan 1
2. sonic-ext-capture              sw_if_index 1                → cookie: orig_rx = member (1)
3. bond-input                     bobm0 -> BondEthernet10      [VLIB_RX rewritten = BondEthernet10]
4. ethernet-input                 ARP ... 802.1q vlan 1        → sub-if classify → BondEthernet10.1
5. linux-cp-punt-xc               lip-punt: 25 -> 26           [VLIB_TX = be10.1 tap (26)]
6. tap4107-output (be10.1 tap)    → sonic-ext-aggr-tap-redirect
       SONIC-EXT-AGGR-TAP-REDIRECT: aggr-tap 26 orig-rx 1 member-tap 17 REDIRECTED
7. tap4101-output (member tap 17) → tap4101-tx                 [VLIB_TX = Ethernet0 tap (17)]
       ARP: 22:f8:d0:b9:ed:35 -> ff:ff:ff:ff:ff:ff 802.1q vlan 1   (vlan-1-deep)
8. member netdev (tagged) → Linux bond → 8021q → PortChannel10.1   ✓ member ifindex
```

Notes:
- The `802.1q vlan 1` tag is **preserved in the packet through the entire path** —
  it is present at `dpdk-input`, on the aggregate tap output, and at `tap4101-tx`
  (`vlan-1-deep`, `l3-hdr-offset 18`). No tag strip/re-push is required; the tag
  simply rides along and the kernel 8021q layer demuxes it to `PortChannel10.1`.
- `sonic-ext-capture` records the ingress member (`sw_if_index 1`) at
  `device-input`, before `bond-input` and the sub-interface classify rewrite
  `VLIB_RX` to `BondEthernet10` / `BondEthernet10.1`.
- The punt lands on the aggregate sub-if tap `be10.1` (`linux-cp-punt-xc` 25 → 26);
  `sonic-ext-aggr-tap-redirect` then redirects the buffer from `aggr-tap 26` to
  `member-tap 17`, delivering the tagged frame on the member netdev.

### 6.4 IPv4 unicast (for-us) over the port-channel **sub-interface**

```
1. Tagged ICMP to 2.0.0.1 on member Ethernet0             [VLIB_RX = member]
2. sonic-ext-capture                                      → cookie: orig_rx=member, tag={0x8100,vid1}
3. ethernet-input → bond-input → sub-if classify          [VLIB_RX = BondEthernet10.1]
4. ip4-input (IP4 enabled on BondEthernet10.1, addr 2.0.0.1)
       → for-us → linux-cp-punt-xc                         [VLIB_TX = be10.1]
5. interface-output[be10.1] → sonic-ext-aggr-tap-redirect
       reads cookie → member LCP tap, RE-PUSH .1Q vid 1    [VLIB_TX = Ethernet0 tap]
6. member netdev → bond → 8021q → PortChannel10.1          ✓
```

### 6.5 LLDP and LACP over the port channel — **no change**

LLDP and LACP are slow/link-scoped protocols consumed per member. They are
punted on **each member's own linux-cp pair** (the bond master is not on their
punt path), so they already arrive on the member netdev where `lldpd` / `teamd`
expect them. This redesign does not alter that path.

```
LLDP/LACP on member Ethernet0 → member linux-cp punt → Ethernet0 tap → lldpd/teamd
```

---

## 7. Summary

By teaching `sonic_ext_phy_is_aggregate()` to include bond masters and bond
sub-interfaces, the port channel reuses the proven VLAN/BVI aggregate-punt path:
`sonic-ext-capture` records the ingress member, and `sonic-ext-aggr-tap-redirect`
steers the punted copy from the aggregate host tap (`be<id>` / `be<id>.<vlan>`)
to that member's tap (re-pushing the wire VLAN for sub-interfaces). Control
traffic then reaches Linux on the member netdev exactly as it would on hardware,
restoring DHCP relay over port-channel uplinks and conforming to the SONiC punt
model, while LLDP/LACP and the data plane are unaffected.
