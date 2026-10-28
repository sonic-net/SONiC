# SONiC-VPP NAT High Level Design

## Table of Contents
- [1. Objectives](#1-objectives)
- [2. Scope](#2-scope)
- [3. Feature Description](#3-feature-description)
  - [3.1 SONiC NAT Architecture](#31-sonic-nat-architecture)
  - [3.2 VPP NAT44 Implementation](#32-vpp-nat44-implementation)
  - [3.3 Misalignment Between SONiC Expectation and VPP](#33-misalignment-between-sonic-expectation-and-vpp)
- [4. Proposed Solution](#4-proposed-solution)
  - [4.1 Design Principles](#41-design-principles)
  - [4.2 VPP Configuration Mode](#42-vpp-configuration-mode)
  - [4.3 NAT Miss Punt to LCP Tap](#43-nat-miss-punt-to-lcp-tap)
  - [4.4 Aging, Hit Bit, and Counter Tracking](#44-aging-hit-bit-and-counter-tracking)
  - [4.5 Zone Assignment](#45-zone-assignment)
  - [4.6 Global NAT Enable/Disable](#46-global-nat-enabledisable)
  - [4.7 End-to-End Flows](#47-end-to-end-flows)
  - [4.8 Future Work](#48-future-work)
  - [4.9 Implementation Phases](#49-implementation-phases)
- [5. VPP Binary API Mapping](#5-vpp-binary-api-mapping)
- [6. SONiC Configuration](#6-sonic-configuration)
- [7. Test Plan](#7-test-plan)
  - [7.1 Unit Tests](#71-unit-tests)
  - [7.2 sonic-mgmt Test Coverage](#72-sonic-mgmt-test-coverage)

---

## 1. Objectives

Provide SONiC NAT feature support on the sonic-vpp platform by implementing the SAI NAT API on top of VPP's `nat44-ed` (endpoint-dependent) plugin. The implementation must:

- Make VPP behave as a "dumb" 3-tuple NAT translation engine, mirroring what SONiC expects from a hardware ASIC.
- Preserve SONiC's existing control plane (NatMgr, natsyncd, NatOrch, kernel iptables/conntrack) without changes.
- Allow the existing sonic-mgmt NAT test suite to pass on the sonic-vpp platform.
- Add no performance penalty for established flows (data plane runs entirely in VPP).
- Punt the first packet of every new dynamic flow to the Linux kernel via the LCP tap interface, so iptables/conntrack can establish session state.
- Emit flow aging notifications (`SAI_NAT_EVENT_AGED`) from the VPP SAI layer to NatOrch for both **TCP** (idle timeout, FIN, RST) and **UDP** (idle timeout) flows, so SONiC can clean up APP_DB and kernel conntrack state without observing the data-plane packets.

## 2. Scope

### In Scope

| SONiC NAT Feature | Supported |
|---|---|
| Static NAT (1:1 IP) | Yes |
| Static NAPT (1:1 IP+port) | Yes |
| Dynamic NAT/NAPT (kernel-driven via iptables → NatOrch → SAI) | Yes |
| Twice (Double) NAT/NAPT | Yes |
| NAT zones (0–3) on Ethernet, VLAN, PortChannel, Loopback interfaces | Yes |
| Full Cone NAT behavior | Yes (via VPP endpoint-dependent mode) |
| Per-entry packet/byte counters | Yes (from VPP session counters) |
| Hit bit (used for aging by NatOrch) | Yes (derived from VPP `last_heard`) |
| Per-zone counters (SNAT/DNAT translations, discards, translations_needed) | Yes (software counters in SAI layer) |
| Global NAT enable/disable (`SAI_SWITCH_ATTR_NAT_ENABLE`) | Yes |
| SNAT_MISS / DNAT_MISS trap to CPU | Yes (via LCP punt) |
| Configurable TCP/UDP/global aging timeouts | Yes (mapped to VPP timeouts) |
| ACL with `do_not_nat` / `forward` action affecting NAT | **Functional (kernel-only in first release)** — see note below |
| ICMP NAT translation | Yes (handled entirely in Linux kernel per SONiC HLD; no VPP work needed) |
| Bi-directional translation (one config entry → 2 SAI entries) | Yes |

**Note on ACL + NAT**: SONiC ACL `do_not_nat` and `forward` actions must bypass the NAT pipeline for matching traffic. In the **first release**, sonic-vpp does **not** program NAT-bypass ACLs into VPP. Instead:

- The SAI ACL layer programs `permit` / `deny` rules normally; NAT-related ACL keywords (`do_not_nat`, `forward`) are recorded in the SAI cache but produce no VPP-side bypass action.
- Matching packets fall through to the NAT slow path → `nat44-lcp-punt` punts them to the LCP tap of the ingress interface.
- The Linux kernel iptables rules installed by NatMgrd (`iptables -t nat ... -j ACCEPT` for `do_not_nat`, mangle MARK rules for zones) match in the kernel and forward the packet without NAT.
- conntrack does not report a NAT'd connection → NatOrch does not install a VPP entry → every subsequent packet of the bypassed flow takes the same slow path.

This is **functionally correct** and matches the SONiC NAT HLD's split-architecture semantics, but bypassed flows are **CPU-bound** (kernel forwarding speed, not VPP line rate). Acceptable for a virtual-switch / lab platform; the dedicated VPP fast-path bypass is deferred. See [§4.8 Future Work](#48-future-work) for the planned VPP ACL plugin extension.

### Out of Scope

- Warm boot NAT entry persistence (depends on VPP SAI warm boot framework, separate effort)
- NAT64 (IPv6-to-IPv4 translation)
- VRF-aware NAT (SONiC HLD also limits NAT to default VRF)
- Hairpinning (listed as future SONiC enhancement)
- ALG (Application Layer Gateway) support
- Subnet-based NAT
- NAT on fragmented IP packets

## 3. Feature Description

### 3.1 SONiC NAT Architecture

SONiC implements NAT as a **split architecture** where the Linux kernel is the brain (session establishment, policy, port allocation) and the ASIC is a dumb fast-path translation cache.

```
┌────────────────────────────────────────────────────────────────┐
│                    SONiC NAT Architecture                      │
│                                                                │
│   CONFIG_DB                                                    │
│      │  STATIC_NAT, STATIC_NAPT, NAT_POOL, NAT_BINDINGS,       │
│      │  NAT_GLOBAL, *_INTERFACE.nat_zone                       │
│      ▼                                                         │
│   NatMgr ──┬──→ APP_DB (NAT_TABLE, NAPT_TABLE, ...)            │
│            │                                                   │
│            └──→ iptables (PREROUTING/POSTROUTING)              │
│                 mangle (zone → mark)                           │
│                                                                │
│   APP_DB ──→ NatOrch ──→ SAI ──→ ASIC                          │
│                  ▲                  ▲                          │
│                  │                  │ trap NAT miss (CPU)      │
│   conntrack ─────┘                  │                          │
│       ▲                             │                          │
│       │                             │                          │
│       └─── natsyncd ←── netlink ────┘                          │
│                                                                │
│   Data plane:                                                  │
│     First packet  → trap to CPU → iptables → conntrack         │
│                  → natsyncd → APP_DB → NatOrch → ASIC          │
│     Subsequent   → ASIC translates at line rate                │
└────────────────────────────────────────────────────────────────┘
```

#### What SONiC expects the ASIC to support

The ASIC is expected to be a simple 3-tuple lookup + rewrite engine:

| Capability | Description |
|---|---|
| 3-tuple match | `{proto, src_ip, src_port}` for SNAT or `{proto, dst_ip, dst_port}` for DNAT |
| Rewrite | Replace matched fields with translated values; recompute IP and L4 checksums |
| Per-entry counters | Packet count, byte count |
| Hit bit | Was this entry hit since last query? Used by NatOrch for aging |
| Zone per L3 interface | `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID`; NAT applied only when packet crosses zones |
| Per-zone counters | DNAT/SNAT discards, translation-needed, translations |
| NAT miss trap | Trap to CPU at lower priority than protocol queues, higher than broadcast (CoPP queue 3) at ~600pps |
| Global enable | `SAI_SWITCH_ATTR_NAT_ENABLE` |

The ASIC does **NOT** need to:
- Track TCP state
- Allocate dynamic ports
- Maintain 5-tuple session tables
- Make policy decisions
- Time out entries (NatOrch handles aging)

### 3.2 VPP NAT44 Implementation

VPP's `nat44-ed` plugin is a full-featured stateful NAT implementation:

| Feature | VPP Mechanism |
|---|---|
| Session tracking | 6-tuple session hash (`bihash`) in `nat44-ed-in2out`, `nat44-ed-out2in` |
| Static 1:1 mapping | `nat44 add static mapping` |
| Static NAPT | `nat44 add static mapping tcp/udp/icmp <port> ...` |
| Dynamic pool | `nat44 add address <range>` |
| Port allocation | VPP allocates dynamically from pool with collision detection |
| Twice NAT | `nat44 add static mapping ... twice-nat` + twice-nat pool |
| Interface designation | `set interface nat44 in/out <intfc>` (binary: inside/outside) |
| Counters | `total_pkts`, `total_bytes` per session |
| Last-heard timestamp | `last_heard` per session, used for VPP-internal aging |
| Forwarding | `nat44 forwarding enable` → unmatched packets go to `ip4-lookup` instead of drop |
| Static-mapping-only mode | Startup config `static_mapping_only`: no dynamic allocation, drop unmatched |
| Endpoint-dependent mode | Required for full cone, twice NAT, out2in-only |

#### VPP packet flow (in2out direction)

```
interface-input
    │
    ▼
nat44-ed-in2out-worker-handoff  (hash src_ip, route to worker)
    │
    ▼
nat44-ed-in2out  (fast-path: 6-tuple session lookup)
    │
    ├── Session HIT  → translate → ip4-lookup → output
    │
    └── Session MISS → nat44-ed-in2out-slow-path
                         │
                         ├── Static mapping match → create session, translate
                         │
                         ├── Pool available → allocate, create session, translate
                         │
                         └── NO MATCH (NAT miss):
                              ├── forwarding enabled → ip4-lookup (untranslated)
                              └── forwarding disabled → error-drop
```

### 3.3 Misalignment Between SONiC Expectation and VPP

| Aspect | SONiC Expects | VPP Default Behavior | Gap |
|---|---|---|---|
| Session model | ASIC stores 3-tuple, kernel stores 5-tuple | VPP stores 6-tuple session table | VPP would duplicate kernel's role |
| Dynamic port allocation | Kernel iptables/conntrack | VPP nat44 pool | Two allocators would conflict |
| Session source of truth | Kernel conntrack table | VPP session table | Need to pick one |
| NAT miss | Trap to CPU (kernel iptables creates flow) | Drop OR forward untranslated | Neither matches SONiC |
| First packet handling | Goes through kernel, then ASIC | Stays in VPP, never reaches kernel | Kernel conntrack never learns flow |
| Zones | 0–3 per interface | Binary in/out | Need mapping (zone 0 → in, others → out) |
| Hit bit | Boolean: hit since last read | `last_heard` floating-point timestamp | Need conversion |
| Static NAPT type | One config entry → 2 SAI entries (SNAT + DNAT) | One static mapping handles both directions | NatOrch sends 2 SAI calls; need to dedupe |

The fundamental misalignment is that **VPP wants to own session state**, while **SONiC expects the kernel to own it**. Reconciling this is the central design problem.

## 4. Proposed Solution

### 4.1 Design Principles

1. **Make VPP behave like a dumb ASIC.** Disable VPP's own dynamic port allocation. Only translate packets that match preconfigured static mappings.
2. **Preserve SONiC's existing control plane.** No changes to NatMgr, natsyncd, NatOrch, or kernel iptables.
3. **Trap NAT-miss to kernel via LCP tap.** Restore SONiC's "first packet to CPU" semantics. Kernel iptables/conntrack establishes the flow, NatOrch programs it back into VPP as a static mapping.
4. **Translate the first packet in kernel software, all subsequent packets in VPP.** Exactly the SONiC ASIC model.
5. **Map SAI semantics 1:1 to VPP API.** Keep the SAI translation layer thin.

### 4.2 VPP Configuration Mode

VPP startup configuration:

```
nat {
    endpoint-dependent     # 6-tuple sessions, required for twice-nat / full-cone
    translation hash buckets 1024
    max translations per thread 65535
    max users per thread 1024
}
```

At runtime, when SAI receives `SAI_SWITCH_ATTR_NAT_ENABLE = true`, call vpp equivalent APIs of below:

```
vppctl> nat44 plugin enable sessions 65535
vppctl> nat44 forwarding disable             # drop unmatched (we'll add punt next)
vppctl> nat44 lcp-punt enable              # NEW: punt NAT-miss to LCP tap
```
**Important**: We do NOT call `nat44 add address` (no pool allocation in VPP). All translations come from `nat44 add static mapping` calls driven by NatOrch.

### 4.3 NAT Miss Punt to LCP Tap

SONiC has two distinct first-packet models, and they must be handled differently:

| NAT type | Entry creation | First packet on ASIC | Kernel sees first packet? |
|---|---|---|---|
| Static NAT / NAPT | **Proactive** — at config time (NatMgr → NatOrch → SAI) | ASIC has the entry; translates directly | **No** — ASIC handles it; iptables exists only as a fallback |
| Dynamic NAT (pool + binding) | **Reactive** — on first packet | No entry → **trap to CPU via `SAI_HOSTIF_TRAP_TYPE_SNAT_MISS` / `DNAT_MISS`** | **Yes** — kernel iptables + conntrack create the flow, then NatOrch programs the ASIC |
| Twice NAT (static) | Proactive | ASIC translates directly | No |

Therefore the VPP "punt to LCP tap" mechanism is invoked **only for the dynamic NAT-miss case** (and only when a NAT-enabled zone is configured). Static NAT packets are translated by VPP immediately without any kernel involvement — exactly as a hardware ASIC would do.

A small VPP plugin extension (`nat44-lcp-punt`) hooks into the slow-path nodes to redirect NAT-miss packets (no static mapping, no pool match) to the LCP tap of the ingress interface.

#### Pseudocode of the patch

```c
// In nat44_ed_in2out_slow_path_inline() and nat44_ed_out2in_slow_path_inline():

// After existing static-mapping and pool-allocation checks fail:
no_translation_path:
    if (sm->lcp_punt_enabled)
    {
        u32 rx_sw_if = vnet_buffer(b)->sw_if_index[VLIB_RX];
        u32 host_sw_if = lcp_itf_pair_get_host(rx_sw_if);
        if (host_sw_if != ~0)
        {
            vnet_buffer(b)->sw_if_index[VLIB_TX] = host_sw_if;
            next = NAT_NEXT_INTERFACE_OUTPUT;  // send to tap
            goto trace;
        }
    }
    // Fall back to drop
    b->error = ...;
    next = NAT_NEXT_DROP;
```

#### Flow diagram

```
              ┌─────────────────────────────────┐
              │  Packet on inside interface     │
              │  (e.g., GigabitEthernet0/8/0)   │
              └────────────────┬────────────────┘
                               │
                               ▼
                   nat44-ed-in2out (fast path)
                               │
                       Session lookup
                               │
              ┌────────────────┴────────────────┐
              │                                 │
         Session HIT                       Session MISS
              │                                 │
              ▼                                 ▼
       Translate, forward          nat44-ed-in2out-slow-path
              │                                 │
              │                  ┌──────────────┴──────────────┐
              │                  │                             │
              │            Static map hits             NAT MISS (no match)
              │            (created earlier by                 │
              │            NatOrch from APP_DB)                │
              │                  │                             │
              │                  ▼                             ▼
              │           Translate, forward        lcp_punt enabled?
              │           (no kernel involvement)              │
              │                                  ┌─────────────┴─────────────┐
              │                                Yes                           No
              │                                  │                           │
              │                                  ▼                           ▼
              │                          Set TX = LCP tap              error-drop
              │                          (host_sw_if of                (zone DISCARDS++)
              │                          ingress intf)
              │                                  │
              │                                  ▼
              │                          interface-output → tap
              │                                  │
              │                                  ▼
              │                          Linux kernel "EthernetX"
              │                                  │
              │                                  ▼
              │                          iptables PREROUTING/POSTROUTING
              │                          (pool + binding match)
              │                                  │
              │                                  ▼
              │                          conntrack: NEW 5-tuple entry,
              │                          allocates external port
              │                                  │
              │                                  ▼
              │                          kernel forwards packet
              │                          out → other tap → VPP → wire
              │                                  │
              │                                  ▼
              │                          netlink → natsyncd
              │                                  │
              │                                  ▼
              │                          APP_DB NAPT_TABLE
              │                                  │
              │                                  ▼
              │                          NatOrch → SAI create_nat_entry
              │                                  │
              │                                  ▼
              │                          nat44 add static mapping
              │                          (VPP now has the dynamic mapping;
              │                          subsequent packets HIT fast path)
              │                                  │
              ◀──────────────────────────────────┘
```

#### Why use LCP tap and not VPP punt sockets

- LCP tap pairs already exist for every SONiC port (created in `SwitchVppRif.cpp`).
- The tap names match SONiC port names (`Ethernet0`, `Vlan1000`, etc.).
- Packets arriving on the tap go straight to the Linux kernel's normal receive path, triggering iptables PREROUTING.
- No additional infrastructure required.

#### Behavior when a punted packet does not match any NAT pool

A NAT-miss punt fires for every zone-crossing packet that has no matching static mapping. Once the packet reaches the kernel, three outcomes are possible:

| Case | Kernel behavior | VPP entry created? | Subsequent packets |
|---|---|---|---|
| **A. Matches iptables pool binding** | conntrack allocates external port, applies SNAT/DNAT, routes back to VPP | **Yes** (via natsyncd → NatOrch → SAI) | Fast path in VPP (line rate) |
| **B. No iptables NAT rule matches** | Kernel just routes (no NAT) via egress LCP tap | **No** — natsyncd reports nothing | Every packet re-punts: kernel slow-path forever, CPU-bound throughput |
| **C. CoPP rate-limit exceeded** | Trap dropped before reaching kernel | No | Packets dropped; zone `DISCARDS` counter incremented |

Case B is the same architectural limitation that exists on a real ASIC: traffic that crosses NAT zones but isn't covered by any pool/binding cannot be fast-pathed and stays on the slow path. SONiC mitigates this in three ways:

1. **ACL with `forward` / `do_not_nat` action** — In the first release this is enforced **only in the kernel** (NatMgrd installs the corresponding `iptables -t nat ... -j ACCEPT` / mangle rules). Matching packets reach the kernel via the NAT-miss punt, kernel iptables short-circuits before the NAT chain, and the packet is forwarded without translation. Because no NAT'd conntrack entry is created, NatOrch never installs a VPP fast-path entry, so every packet of the bypassed flow takes the same kernel slow-path. This is correct but CPU-bound — acceptable for the virtual-switch use case. A VPP-side fast-path bypass is planned (see [§4.8 Future Work](#48-future-work)).
2. **NatMgrd kernel iptables** is also the fallback for any zone-crossing punt that doesn't match a pool: kernel routing simply forwards the packet, but again every packet re-punts.
3. **CoPP rate-limit** on the SNAT_MISS / DNAT_MISS trap (~600 pps per SONiC HLD, queue 3) caps the slow-path cost; excess punts are dropped and counted as zone `DISCARDS`. CoPP enforcement lives in the `nat44-lcp-punt` plugin (token bucket per zone) since VPP does not natively rate-limit interface-output.

In short: **punted packets are not silently dropped** — they go to the kernel, which decides (via iptables) whether they should be NAT'd or bypassed. Bypassed flows remain CPU-bound in this release.

#### Static NAT first-packet flow

```
For STATIC_NAPT|65.55.42.1|TCP|1024 → 20.0.0.1:6000

Configuration (control plane, no packets yet):
  ① NatMgr installs iptables rules (fallback only; never exercised in steady state)
  ② NatMgr pushes entry to APP_DB
  ③ NatOrch → SAI → nat44 add static mapping tcp local 20.0.0.1 6000 \
                                                external 65.55.42.1 1024 out2in-only
     VPP now has the static mapping. No packets have been seen yet.

First TCP SYN from external host 1.2.3.4:5000 to 65.55.42.1:1024:
  ④ Arrives on VPP outside interface
  ⑤ nat44-ed-out2in fast path: no session yet → slow path
  ⑥ nat44-ed-out2in-slow-path: static mapping MATCH
       → Create VPP session
       → Translate dst 65.55.42.1:1024 → 20.0.0.1:6000
       → Forward to inside interface
  ⑦ Kernel is NOT involved. No tap duplication.

Subsequent packets in this flow:
  ⑧ Session HIT in fast path; translated at line rate
  ⑨ FIN/RST eventually moves VPP session to TRANSITORY; idle timeout removes it
  ⑩ SAI aging thread emits SAI_NAT_EVENT_AGED for the dynamic 5-tuple counter entry
     (the static 3-tuple SAI entry itself is never aged)
```

This matches the SONiC ASIC model exactly. The only place the LCP tap punt is used is the **dynamic** NAT-miss case below.

#### Dynamic NAT first-packet flow

See [Flow 3 in section 4.7](#flow-3-dynamic-snat-nat-pool-binding-kernel-driven).


### 4.4 Aging, Hit Bit, and Counter Tracking

Per the SONiC NAT HLD, the **SAI/SDK layer owns aging**: NatOrch sets `SAI_NAT_ENTRY_ATTR_AGING_TIME` per entry, registers a `sai_nat_event_notification_fn` callback, and then waits passively for `SAI_NAT_EVENT_AGED` notifications. NatOrch does **not** poll the hit bit.

This is critical for sonic-vpp because, once the first packet of a flow has been programmed as a VPP static mapping, **all subsequent packets (data, FIN, RST) are translated entirely in VPP fast path and never reach the Linux kernel**. The kernel conntrack table therefore cannot detect TCP teardown or idle aging on its own — VPP is the only authoritative observer.

#### SAI aging thread

The VPP SAI layer runs a dedicated aging thread (period: 1 second). On each tick it:

1. Calls `nat44_user_session_v3_dump` to retrieve all current VPP sessions with their `last_heard`, `total_pkts`, `total_bytes`, and TCP state.
2. For each SAI dynamic NAT entry, compares `now - last_heard` against the configured `aging_time`.
3. For each entry whose corresponding VPP session has **disappeared** from the dump (VPP removed it after `tcp_transitory` timeout following FIN/RST, or `tcp_established` / `udp` / `icmp` idle timeout), or whose `last_heard` age exceeds `aging_time`, emits a `SAI_NAT_EVENT_AGED` notification with `nat_event = SAI_NAT_EVENT_AGED` and the SAI NAT entry key.
4. NatOrch receives the aged event, deletes the entry from APP_DB / ASIC_DB, calls `conntrack -D` to clean the stale kernel conntrack entry, and SAI then removes the VPP static mapping (if still present).

#### TCP session termination

VPP's nat44-ed state machine handles TCP teardown internally:

| Event observed by VPP | VPP session state | Action |
|---|---|---|
| SYN, SYN-ACK, ACK | ESTABLISHED | Reset idle to `tcp_established_timeout` (7440s default; SONiC HLD = 432000s for established) |
| FIN from either side | TRANSITORY | Idle timer shortened to `tcp_transitory_timeout` (240s default; SONiC HLD = 120s) |
| RST | TRANSITORY | Same |
| Idle timer expires | Session removed from VPP bihash | Session no longer appears in `nat44_user_session_v3_dump` |

The SAI aging thread detects the session disappearance and emits `SAI_NAT_EVENT_AGED` for the corresponding SAI entry. This restores the same end-to-end semantics as a hardware ASIC: NatOrch is informed of TCP teardown without ever seeing the FIN itself, and it then propagates the deletion to APP_DB and the kernel conntrack table.

#### Timeout configuration

SONiC exposes NAT aging timeouts through the `NAT_GLOBAL` table in CONFIG_DB (CLI: `config nat set tcp-timeout|udp-timeout|timeout <secs>`):

| CONFIG_DB key | Default (s) | Applies to |
|---|---|---|
| `nat_tcp_timeout` | 86400 | TCP established sessions |
| `nat_udp_timeout` | 300 | UDP sessions |
| `nat_timeout` | 600 | Generic / non-TCP-UDP-ICMP |

NatMgrd publishes these to APP_DB; NatOrch passes them to SAI in two places:

1. **Per-entry**: each `create_nat_entry` includes `SAI_NAT_ENTRY_ATTR_AGING_TIME` chosen from the protocol-appropriate value above. The SAI aging thread compares `now - last_heard` against this per-entry value when deciding whether to emit `SAI_NAT_EVENT_AGED`.
2. **Global VPP timeouts**: the SAI layer also mirrors the same values into VPP via `nat_set_timeouts`, so VPP's internal session bihash ages out at the same rate. Whenever NatOrch updates a global timeout, the SAI layer re-issues:

   ```
   nat_set_timeouts udp <nat_udp_timeout> \
                    tcp_established <nat_tcp_timeout> \
                    tcp_transitory 120 \
                    icmp 60
   ```

   `tcp_transitory` and `icmp` are not exposed by SONiC NAT_GLOBAL and remain at fixed VPP defaults aligned with the SONiC NAT HLD (120s / 60s). ICMP NAT is handled entirely in the kernel; the value is included only because the VPP API requires it.

Updating these at runtime affects new sessions immediately and existing sessions on their next idle check; no traffic disruption.

#### Static entries

`aging_time = 0` is special — entries never age. The SAI layer skips them in the aging thread. For TCP static mappings, the underlying VPP session may still age out (causing the next packet to re-create it through the slow path) but the SAI entry and VPP static mapping remain intact.

#### Hit bit (legacy attribute)

`SAI_NAT_ENTRY_ATTR_HIT_BIT` and `HIT_BIT_COR` are still implemented for completeness, but NatOrch does not poll them. They are computed on demand:

```cpp
bool SwitchVpp::getNatEntryHitBit(const sai_nat_entry_t &entry, bool clear_on_read)
{
    auto sess = lookupVppSessionForEntry(entry);
    if (!sess) return false;

    f64 last_heard = sess->last_heard;
    f64 last_poll = m_natHitPollTime[entry];
    bool hit = (last_heard > last_poll);

    if (clear_on_read) {
        m_natHitPollTime[entry] = vlib_time_now();
    }
    return hit;
}
```

#### Counter polling

VPP exposes session counters via `nat44_user_session_v3_dump`. The SAI layer caches the SAI-entry → VPP-session mapping at creation time so lookups are O(1). The aging thread reuses the same dump to refresh counters, so per-entry `get_nat_entry_attribute(PACKET_COUNT|BYTE_COUNT)` is served from the cached snapshot (refreshed every 1s).

#### Notification path

```
            VPP aging thread (1s tick)
                    │
                    ▼
        nat44_user_session_v3_dump
                    │
                    ▼
        Detect aged / disappeared sessions
                    │
                    ▼
        sai_nat_event_notification_fn
            { event = SAI_NAT_EVENT_AGED,
              nat_entry = <sai key> }
                    │
                    ▼
                NatOrch
                    │
            ┌───────┴────────────┐
            ▼                    ▼
        APP_DB delete       conntrack -D
                    │
                    ▼
        (kernel state now consistent)
```


### 4.5 Zone Assignment

SONiC supports zones 0–3. VPP supports only binary inside/outside. Mapping:

| SONiC zone | VPP designation |
|---|---|
| 0 (default = inside) | `is_inside = 1` |
| 1, 2, 3 (outside) | `is_inside = 0` |

This is implemented in `SwitchVppRif.cpp` when `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` is set:

```cpp
sai_status_t SwitchVpp::setRifNatZone(sai_object_id_t rif_oid, uint32_t zone)
{
    const char *hwif = rifToHwif(rif_oid);
    bool is_inside = (zone == 0);
    return vpp_nat44_interface_add_del_feature(hwif, is_inside, /*is_add=*/true);
}
```

#### Loopback handling

The SONiC HLD permits the Loopback IP to be used as the public NAT IP. In SONiC the Loopback zone is "not propagated to the hardware" — it's only used in the kernel by NatMgrd to install the mangle MARK rules. For sonic-vpp we follow the same approach: Loopback zone is recorded in the SAI cache but no `nat44 in/out` is called on the loopback interface in VPP. This is safe because loopback is never traversed as a packet-forwarding interface — it is purely an IP address. Zone-crossing in VPP is decided by the `nat44 in/out` feature on the physical, VLAN, or PortChannel ingress/egress interfaces, not by any property of the loopback.

#### VLAN, PortChannel, and sub-interface RIFs

SONiC supports `nat_zone` on Ethernet, VLAN, PortChannel, and (sub-)interface RIFs. VPP represents each of these as a single `sw_if_index`, and `nat44 in/out` can be attached to any of them:

| SONiC RIF type | VPP representation | NAT feature attachment |
|---|---|---|
| `Ethernet0` (port RIF) | Hardware interface `GigabitEthernet0/8/0` | `set int nat44 in/out GigabitEthernet0/8/0` |
| `Vlan1000` (VLAN RIF) | BVI (`loop0` with `bvi 1`) in a bridge-domain | `set int nat44 in/out loop0` |
| `PortChannel01` (LAG RIF) | `bond0` interface | `set int nat44 in/out bond0` |
| `Ethernet0.100` (sub-interface) | `GigabitEthernet0/8/0.100` | `set int nat44 in/out GigabitEthernet0/8/0.100` |

The zone assignment code in `SwitchVppRif::setRifNatZone()` resolves the SAI RIF object to the appropriate VPP `sw_if_index` (via the existing `rifToHwif()` helper used for IP address assignment) and calls `vpp_nat44_interface_add_del_feature` on that index. **No special-case handling per RIF type is needed.**

For the VLAN/BVI case in particular: NAT44 runs on the BVI's feature arc, so the L3-routed traffic crossing the VLAN boundary is subject to NAT; pure L2 traffic between bridge members (same VLAN, no routing) bypasses the BVI and is not NAT'd — which is the correct semantic.

When a packet ingresses on a physical port, gets L2-bridged into a VLAN, hits the BVI, and the nat44 slow path punts it, the `nat44-lcp-punt` plugin uses the **BVI's `sw_if_index`** as the rx interface. The BVI's LCP pair is the `Vlan1000` tap, so the kernel sees the punted packet on `Vlan1000` (not on the underlying physical port). This matches what kernel iptables / NatMgrd expect: the zone MARK rules are keyed by Linux interface name (`Vlan1000`).

#### How VPP decides zone-crossing

VPP does not have an explicit "zone" attribute. The feature-arc placement of `nat44-ed-in2out` (on `is_inside=1` interfaces) and `nat44-ed-out2in` (on `is_outside=1` interfaces) implicitly defines zone boundaries:

- A packet ingresses on an `is_inside` interface → `nat44-ed-in2out` runs → SNAT path (slow path on miss for dynamic, fast path on hit).
- A packet ingresses on an `is_outside` interface → `nat44-ed-out2in` runs → DNAT path.
- A packet ingressing on an interface with neither designation is L3-routed unmodified (no NAT decision).

So "zone crossing" is detected as "ingress interface has a nat44 feature AND the matching feature found a translation (or NAT-miss punt)." There is no zone-equality check inside VPP — the feature-arc topology encodes it.

#### Multi-outside-zone limitation

SONiC defines NAT semantics as **"translate whenever a packet crosses any zone boundary"**, where zones are 0–3. Because VPP only has binary inside/outside, all non-zero SONiC zones collapse to `is_outside=1`. Consequences:

| Traffic pattern | SONiC HLD expectation | sonic-vpp behavior | Status |
|---|---|---|---|
| Zone 0 ↔ Zone 1, 2, or 3 | NAT applies | NAT applies (inside ↔ outside in VPP) | ✓ Correct |
| Zone 1 ↔ Zone 2 (or any inter-outside-zone) | NAT applies | Both ingress and egress are `is_outside=1`; nat44-ed-out2in runs on ingress and finds no static mapping → punt to kernel | ⚠ Functional via kernel slow path only |
| Same-zone traffic (e.g., zone 0 ↔ zone 0) | No NAT | No NAT (both `is_inside=1`; nat44-ed-in2out on ingress finds no match → punt; kernel iptables also finds no match → forward) | ✓ Correct but inefficient |

The inter-outside-zone case is rare in practice — almost all SONiC NAT deployments use only zone 0 (inside) and zone 1 (outside). Multi-outside zones are listed as a [§4.8 Future Work](#48-future-work) item.

#### Zone counters

VPP does not have a "zone" concept — only binary `is_inside` / `is_outside` per interface. Per-zone NAT counters are therefore synthesized in the SAI layer by tagging each event with the zone of the ingress interface (which the SAI layer already knows from `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID`).

| SAI counter | Source | Mechanism |
|---|---|---|
| `SAI_NAT_ZONE_COUNTER_ATTR_TRANSLATIONS` | Per-session `total_pkts`, bucketed by ingress zone | Aging thread walks `nat44_user_session_v3_dump`, maps each session's ingress `sw_if_index` → zone via SAI cache, sums into per-zone accumulator |
| `SAI_NAT_ZONE_COUNTER_ATTR_TRANSLATION_NEEDED` | `nat44-lcp-punt` per-sw_if_index punt counter | VPP stats segment `/nat44-lcp-punt/punted[sw_if_index]`; SAI maps `sw_if_index → zone` and sums |
| `SAI_NAT_ZONE_COUNTER_ATTR_DISCARDS` | `nat44-lcp-punt` per-sw_if_index drop counter | VPP stats segment `/nat44-lcp-punt/dropped[sw_if_index]`; SAI maps and sums |

##### Counter publication (VPP side)

The `nat44-lcp-punt` plugin maintains two `vlib_simple_counter_main_t` vectors **indexed by `sw_if_index`**, not by zone. Each time the punt node processes a packet it:

1. Reads the ingress `sw_if_index`.
2. Increments either `punted` (successful punt to LCP tap) or `dropped` (CoPP drop, no LCP tap available, etc.) at that `sw_if_index` index on the current worker thread.

Both vectors are registered in the VPP stats segment at plugin init:

```
/nat44-lcp-punt/punted    [sw_if_index 0..N]
/nat44-lcp-punt/dropped   [sw_if_index 0..N]
```

This keeps the plugin agnostic to SONiC zone semantics — it just publishes raw per-interface punt accounting.

##### Counter aggregation (SAI side)

The SAI layer maintains a `sw_if_index → zone` map (populated when `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` is set). On `get_nat_zone_counter_attribute`, it reads the per-`sw_if_index` counters from the VPP stats segment and sums them across all interfaces belonging to the requested zone. Using `libvppinfra`'s stats client (same library used by `vpp_get_stats`) the segment is `mmap`-ed once at SAI init — no binary-API round-trip per read.

```cpp
// One-time at SAI init:
m_statClient = stat_client_get();
m_idxPunted  = stat_segment_vec_index(m_statClient, "/nat44-lcp-punt/punted");
m_idxDropped = stat_segment_vec_index(m_statClient, "/nat44-lcp-punt/dropped");

// Per get_nat_zone_counter_attribute(zone):
uint64_t sum = 0;
for (auto sw_if_index : m_zoneToSwIfs[zone]) {
    sum += stat_segment_read_counter_at(m_statClient,
                                        m_idxPunted /* or m_idxDropped */,
                                        sw_if_index);
}
attr->value.u64 = sum;
```

A counter read is a single cache-line load (~100 ns); aggregation over a handful of interfaces per zone is microseconds. On-demand polling from `show nat statistics` is sufficient — no event subscription, no per-packet IPC.

### 4.6 Global NAT Enable/Disable

`SAI_SWITCH_ATTR_NAT_ENABLE = true`:
- `nat44 plugin enable`
- Enable `lcp-punt` mode
- Mark SAI internal state `m_natEnabled = true`

`SAI_SWITCH_ATTR_NAT_ENABLE = false`:
- `nat44 plugin disable` — automatically removes all static mappings, sessions, pools, and interface designations
- Mark `m_natEnabled = false`
- Clear SAI-side caches (entry → VPP session map, zone counters)

### 4.7 End-to-End Flows

#### Flow 1: Configuration of a static NAT entry

```
1. User: config nat add static basic 65.55.42.3 20.0.0.3
2. NatMgrd reads CONFIG_DB STATIC_NAT
3. NatMgrd: installs iptables rules in kernel; pushes APP_DB NAT_TABLE entries
4. NatOrch reads APP_DB → creates 2 SAI entries:
     (a) SNAT entry: src 20.0.0.3 → 65.55.42.3
     (b) DNAT entry: dst 65.55.42.3 → 20.0.0.3
5. SAI VPP receives create_nat_entry calls:
     (a) → vppctl nat44 add static mapping local 20.0.0.3 external 65.55.42.3 \
                                    out2in-only twice-nat-flag=no
     (b) → DEDUPED: the same VPP static mapping handles both directions; SAI
                    caches both SAI OIDs as referring to the same VPP mapping
6. SAI returns SUCCESS for both
```

#### Flow 2: First TCP SYN from outside to a static NAPT entry

```
External 1.2.3.4:5000 → 65.55.42.1:1024 (SYN)

1. Arrives on VPP outside interface (zone=1)
2. nat44-ed-out2in: no session
3. nat44-ed-out2in-slow-path:
     - Static mapping found (pre-programmed at config time)
     - Create VPP session: out2in {1.2.3.4:5000, 65.55.42.1:1024} →
                            in2out {1.2.3.4:5000, 20.0.0.1:6000}
     - Translate dst to 20.0.0.1:6000
     - Forward to inside interface
   (Kernel is NOT involved. No tap duplication.)
4. 20.0.0.1 server replies (SYN-ACK from 20.0.0.1:6000 to 1.2.3.4:5000):
   - VPP nat44-ed-in2out: session HIT → translate src to 65.55.42.1:1024 → forward
5. ACK from external completes handshake; VPP session state = ESTABLISHED
6. All data packets translated by VPP fast path
7. Eventual FIN/RST → VPP session moves to TRANSITORY → idle expiry → session removed
8. SAI aging thread detects session disappearance → emits SAI_NAT_EVENT_AGED for
   the corresponding dynamic 5-tuple counter entry (the static SAI entry itself remains)
```

#### Flow 3: Dynamic SNAT (NAT pool binding, kernel-driven)

```
Internal 20.0.0.5:7000 → 8.8.8.8:53 (DNS query, no existing session)

1. Arrives on VPP inside interface (zone=0)
2. nat44-ed-in2out: no session
3. nat44-ed-in2out-slow-path: no static mapping (only static-mapping-only mode),
                              no pool (we don't configure VPP pool)
                              → NAT MISS
4. lcp-punt enabled → packet sent to LCP tap of inside interface "Vlan1000"
5. Linux kernel receives on Vlan1000:
     - mangle PREROUTING: MARK = zone+1 = 1
     - Route lookup: out via Ethernet4 (outside)
     - mangle POSTROUTING: MARK reaches POSTROUTING
     - iptables POSTROUTING (mark=2): SNAT 20.0.0.5:7000 → 65.55.42.1:1025 fullcone
     - conntrack: NEW entry
6. Kernel forwards via Ethernet4 tap → VPP outside interface → out wire
7. natsyncd notifies APP_DB with new dynamic NAPT entries
8. NatOrch creates 2 SAI entries:
     (a) SNAT: 20.0.0.5:7000 → 65.55.42.1:1025
     (b) DNAT: 65.55.42.1:1025 → 20.0.0.5:7000
9. SAI VPP: nat44 add static mapping tcp local 20.0.0.5 7000 external 65.55.42.1 1025
10. Subsequent packets for this flow: VPP fast-path translates entirely
11. After timeout, NatOrch deletes entry; SAI removes VPP mapping
```

### 4.8 Future Work

The following items are deliberately deferred from the first release. They are correctness-neutral (the first release passes all sonic-mgmt NAT tests without them) but address performance and operational gaps:

#### 4.8.1 VPP ACL fast-path NAT bypass

**Problem (first release):** Packets matching a SONiC ACL with `do_not_nat` or `forward` action are not bypassed in VPP. They take the NAT-miss punt to the kernel on every packet, so bypassed flows are CPU-bound at kernel forwarding speed (~few Gbps per core) instead of VPP line rate.

**Planned solution:** Extend the VPP ACL plugin with a new action `ACL_ACTION_PERMIT_BYPASS_NAT` (value 3, alongside existing 0=deny, 1=permit, 2=permit+reflect). On match it sets a per-buffer flag `VNET_BUFFER2_NAT_BYPASS`. A ~5-LOC check at the top of `nat44_ed_in2out_fast_path_inline()` and `nat44_ed_out2in_fast_path_inline()` honors the flag and short-circuits to the next feature, skipping translation and the punt entirely.

`SwitchVppAcl.cpp` would then translate `SAI_ACL_ACTION_TYPE_NO_NAT` / `forward` to `ACL_ACTION_PERMIT_BYPASS_NAT` instead of plain `permit`. Kernel iptables rules remain (defense in depth).

**Why not VPP identity mappings as an alternative?** Identity mappings require enumerating exact 5-tuples and cannot represent ACL ranges (`permit any 10.0.0.0/8`); rejected.

**Estimated effort:** ~15 LOC across two VPP plugins + ~50 LOC SAI translation changes + unit tests.

#### 4.8.2 Warm boot NAT persistence

Restoring the VPP session table and static-mapping configuration from the SAI warm-boot snapshot, so that established flows survive a SONiC container restart. Depends on the broader sonic-vpp warm boot framework.

#### 4.8.3 VRF-aware NAT

Multi-VRF NAT (NAT applied per non-default VRF). The SONiC NAT HLD itself restricts NAT to the default VRF, so this only becomes relevant if the SONiC HLD is extended.

#### 4.8.4 Multi-outside-zone NAT (zones 1, 2, 3 differentiation)

VPP nat44-ed has only binary inside/outside, so SONiC zones 1–3 collapse into a single `is_outside=1`. Traffic crossing two outside zones (e.g., zone 1 ↔ zone 2) is not detected as zone-crossing by VPP and falls through to the kernel slow path. A future enhancement could introduce a per-interface "zone tag" carried in `vnet_buffer2` and a zone-mismatch check at the top of the nat44-ed nodes to trigger translation/punt on inter-zone traffic. Almost never required in practice.

#### 4.8.4 Hairpinning

Inside-to-inside translation when both endpoints are behind the same NAT. VPP nat44-ed supports this natively (`out2in-only` flag disabled, hairpinning enabled); the work is plumbing the SAI option and verifying SONiC NatMgr produces appropriate config.

#### 4.8.5 IPv6 / NAT64

Out of scope of the SONiC NAT HLD, but VPP has a separate `nat64-ed` plugin that could be wired similarly if SONiC ever extends NAT to v6.

#### 4.8.6 Subnet-based NAT and fragmented packet NAT

Both are listed as out-of-scope in the SONiC HLD but may become required later. VPP nat44-ed supports virtual reassembly for fragments via the `ip4-reassembly` feature.

### 4.9 Implementation Phases

The work is broken into five sequential phases. Each phase is independently testable and leaves the system in a working state. Phase _N_ depends on phase _N-1_.

#### Phase 1 — Static NAT

**Goal:** End-to-end static NAT/NAPT translation entirely in VPP with no kernel involvement on the data path.

| SAI API | New / Modified |
|---|---|
| `create_switch / set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE)` | New |
| `create_nat_entry(SAI_NAT_TYPE_SOURCE_NAT)` | New |
| `create_nat_entry(SAI_NAT_TYPE_DESTINATION_NAT)` | New (with dedup against SNAT pair) |
| `create_nat_entry(SAI_NAT_TYPE_DOUBLE_NAT)` | New (twice-nat) |
| `remove_nat_entry` | New |
| `set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID)` | New |
| Global timeout (`nat_tcp_timeout`, `nat_udp_timeout`, `nat_timeout`) | New — programs `nat_set_timeouts` |

**Tasks:**
- Add NAT data structures (`vpp_nat_static_mapping_t`, SAI-entry ↔ VPP-mapping cache) to `SaiVppXlate.h`.
- Implement `vpp_nat44_plugin_enable_disable`, `vpp_nat44_add_del_static_mapping`, `vpp_nat44_interface_add_del_feature`, `vpp_nat44_set_timeouts` in `SaiVppXlate.c`.
- Create `SwitchVppNat.cpp` with SAI NAT entry CRUD; integrate into `SwitchVpp.cpp` (NAT_ENABLE handling) and `SwitchVppRif.cpp` (zone → in/out mapping).
- VPP startup config: enable nat plugin with `endpoint-dependent` mode.

**Exit criteria:** `config nat add static basic ...` and `config nat add static napt ...` produce traffic that is translated by VPP fast path; verified with `vppctl show nat44 static mappings` and data-plane test with traffic.

#### Phase 2 — Counter Support

**Goal:** Per-entry counters (packets/bytes) and per-zone counters readable from SONiC CLI.

| SAI API | New / Modified |
|---|---|
| `get_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_PACKET_COUNT, BYTE_COUNT)` | New |
| `get_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_HIT_BIT, HIT_BIT_COR)` | New |
| `create_nat_zone_counter / get_nat_zone_counter_attribute` | New |

**Tasks:**
- Implement `vpp_nat44_session_dump` (binary API) and a 1-second background poller that refreshes a SAI-entry → cached session counter map.
- Wire `get_nat_entry_attribute(PACKET_COUNT, BYTE_COUNT)` to read from the cached snapshot.
- Add zone-counter cache; aggregate `total_pkts` per zone from session dumps.
- Hook the `nat44-lcp-punt` plugin stub (counters only — punt path comes in Phase 3) to publish `/nat44-lcp-punt/punted` and `/nat44-lcp-punt/dropped` per `sw_if_index` in the VPP stats segment.
- Implement stats-segment client in SAI; aggregate per-`sw_if_index` counters into per-zone via `m_zoneToSwIfs` map.

**Exit criteria:** `show nat translations count` and `show nat statistics` return accurate values for active static-NAT'd flows.

#### Phase 3 — Dynamic NAT

**Goal:** Dynamic SNAT via kernel iptables/conntrack with VPP fast-path acceleration after the first packet.

| SAI API | New / Modified |
|---|---|
| `create_hostif_trap(SAI_HOSTIF_TRAP_TYPE_SNAT_MISS / DNAT_MISS)` | New |
| `create_nat_entry` from natsyncd-driven APP_DB updates | Existing (Phase 1), now exercised reactively |

**Tasks:**
- Implement the `nat44-lcp-punt` plugin punt path: on NAT-miss in `nat44-ed-{in2out,out2in}-slow-path`, redirect the packet to the LCP tap of the ingress interface (via `lcp_itf_pair_get_host`).
- Add new VPP binary API `nat44_lcp_punt_enable_disable`.
- Implement `vpp_nat44_lcp_punt_enable_disable` in vppxlate.
- Map SAI hostif trap creation to plugin enable.
- Verify NAT_GLOBAL `admin_mode = enabled` triggers the full sequence: lcp-punt enable + nat44 plugin enable + RIF zone programming.
- Ensure `nat44 forwarding disable` is set (no untranslated fall-through).

**Exit criteria:** A dynamic-pool-bound flow generated from an inside host appears in conntrack after the first packet, gets programmed into VPP by NatOrch, and subsequent packets fast-path through VPP.

#### Phase 4 — Aging Support

**Goal:** Notify SONiC of session termination (TCP FIN/RST, idle timeout) for both TCP and UDP so APP_DB and conntrack stay consistent.

| SAI API | New / Modified |
|---|---|
| `sai_switch_notification_t.on_nat_event` registration | New |
| `set_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_AGING_TIME)` | New (per-entry value cached in SAI) |
| Emit `SAI_NAT_EVENT_AGED` via notification channel | New |

**Tasks:**
- Implement the SAI aging thread (1-second tick) that walks `nat44_user_session_v3_dump` and detects:
  - Sessions whose `last_heard` is older than the per-entry `aging_time`, OR
  - Sessions that have disappeared from the dump (VPP removed them after `tcp_transitory` / idle timeout).
- For each aged dynamic entry, post `SAI_NAT_EVENT_AGED` to the registered notification callback.
- Skip entries with `aging_time = 0` (static).
- Verify NatOrch receives the event, deletes APP_DB entries, and issues `conntrack -D`.
- Update VPP `nat_set_timeouts` whenever NAT_GLOBAL timeout values change.

**Exit criteria:**
- A long-running TCP flow that receives FIN/RST is reported as aged within `tcp_transitory_timeout`.
- An idle UDP flow is reported as aged within `nat_udp_timeout`.
- A static entry is never reported as aged.

#### Phase 5 — sonic-mgmt Integration

**Goal:** Pass the upstream sonic-mgmt NAT test suite on a sonic-vpp DUT in a t0 topology.

**Tasks:**
- Build a sonic-vpp image with NAT enabled (build flag `ENABLE_NAT = y`, NAT docker included).
- Stand up a t0 sonic-vpp testbed.
- Run `pytest tests/nat/` and triage failures.
- Document any test that is expected to be skipped (`test_nat_reboot_*` — depends on warm boot; multi-outside-zone tests if added later).
- File issues / fix bugs surfaced by integration testing.
- Add platform-specific test markers to `pytest_collection_modifyitems` for any tests intentionally not exercised on sonic-vpp.

**Exit criteria:** All non-deferred tests in the [§7.2 sonic-mgmt Test Coverage](#72-sonic-mgmt-test-coverage) table pass; deferred tests are explicitly skipped with documented justifications.

## 5. VPP Binary API Mapping

| SAI API | VPP API Message | VPP Plugin |
|---|---|---|
| `set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE)` | `nat44_plugin_enable_disable` | nat |
| `create_nat_entry(SAI_NAT_TYPE_SOURCE_NAT)` | `nat44_add_del_static_mapping_v2` `(addr_only=0, out2in_only=1, local=local_ip:port, external=global_ip:port, proto)` | nat |
| `create_nat_entry(SAI_NAT_TYPE_DESTINATION_NAT)` | Same as above; SAI dedupes with SNAT pair | nat |
| `create_nat_entry(SAI_NAT_TYPE_DOUBLE_NAT)` | `nat44_add_del_static_mapping_v2 (twice_nat=1, ...)` + `nat44_add_del_address_range (twice_nat=1)` for the twice pool | nat |
| `remove_nat_entry` | `nat44_add_del_static_mapping_v2 (is_add=0)` | nat |
| `set_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_AGING_TIME)` | Stored per-entry in SAI cache; consumed by SAI aging thread. No VPP call. | — |
| Global TCP / UDP / generic timeout (NAT_GLOBAL via `set_switch_attribute`) | `nat_set_timeouts (udp, tcp_established, tcp_transitory=120, icmp=60)` | nat |
| `get_nat_entry_attribute(HIT_BIT, HIT_BIT_COR)` | `nat44_user_session_v3_dump` → `last_heard` | nat |
| `get_nat_entry_attribute(PACKET_COUNT, BYTE_COUNT)` | `nat44_user_session_v3_dump` → `total_pkts`, `total_bytes` | nat |
| `set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID)` | `nat44_interface_add_del_feature (is_inside, sw_if_index)` | nat |
| `create_nat_zone_counter` | Internal software counter (no VPP API) | — |
| `get_nat_zone_counter_attribute` | Aggregated from VPP sessions / lcp-punt counters | — |
| `create_hostif_trap(SAI_HOSTIF_TRAP_TYPE_SNAT_MISS / DNAT_MISS)` | `nat44_lcp_punt_enable_disable` (new VPP plugin API) | nat-lcp-punt |

### New VPP plugin API (added by sonic-vpp)

```
define nat44_lcp_punt_enable_disable
{
    u32 client_index;
    u32 context;
    u8  enable;             /* 1 = punt NAT miss to LCP tap, 0 = drop */
};
define nat44_lcp_punt_enable_disable_reply { u32 context; i32 retval; };
```

### Translation layer changes

In `src/sonic-sairedis/vslib/vpp/vppxlate/SaiVppXlate.{h,c}`, new function signatures:

```c
int vpp_nat44_plugin_enable_disable(bool enable);
int vpp_nat44_add_del_static_mapping(vpp_nat_static_mapping_t *m, bool is_add);
int vpp_nat44_interface_add_del_feature(const char *hwif, bool is_inside, bool is_add);
int vpp_nat44_set_timeouts(uint32_t udp, uint32_t tcp_est, uint32_t tcp_trans, uint32_t icmp);
int vpp_nat44_session_dump(vpp_nat_session_t **sessions, uint32_t *count);
int vpp_nat44_lcp_punt_enable_disable(bool enable);
```

## 6. SONiC Configuration

No changes required to SONiC configuration schema. The existing CONFIG_DB tables (`STATIC_NAT`, `STATIC_NAPT`, `NAT_POOL`, `NAT_BINDINGS`, `NAT_GLOBAL`, `*_INTERFACE.nat_zone`) work unchanged. Existing CLI commands (`config nat add static …`, `show nat translations`, `sonic-clear nat …`) work unchanged.

Platform-specific changes:

1. **VPP startup config** (`platform/vpp/files/vpp_startup.conf`):
   ```
   plugins {
       plugin nat_plugin.so { enable }
       plugin linux_cp_plugin.so { enable }
   }
   nat {
       endpoint-dependent
   }
   ```

2. **NAT docker enabled on VPP platform** (`build_image.sh` / docker compose): same as Mellanox/Broadcom.

3. **Hwsku NAT capability** (`device/virtual/x86_64-kvm_x86_64-r0/.../hwsku.json`): advertise NAT capability.

## 7. Test Plan

### 7.1 Unit Tests

Location: `src/sonic-sairedis/unittest/vslib/TestSwitchVppNat.cpp` (new file).

| Test | Description |
|---|---|
| `EnableDisableSwitchNat` | `SAI_SWITCH_ATTR_NAT_ENABLE` toggle calls `nat44_plugin_enable_disable` |
| `CreateRemoveStaticSnat` | `create_nat_entry(SOURCE_NAT)` → `nat44_add_del_static_mapping` with correct fields |
| `CreateRemoveStaticDnat` | Same for DNAT; verify dedup with paired SNAT |
| `CreateRemoveStaticNapt` | TCP/UDP NAPT with L4 ports |
| `CreateRemoveDoubleNat` | Twice NAT mapping + twice-nat pool address |
| `SetGetNatEntryCounters` | Mock VPP session dump returns `total_pkts/bytes`; SAI returns them |
| `HitBitToggle` | First poll returns true after session activity; second poll without activity returns false |
| `AgedNotificationOnIdleTimeout` | Mock session with stale `last_heard` triggers `SAI_NAT_EVENT_AGED` callback to NatOrch |
| `AgedNotificationOnTcpFin` | Mock session disappearing from VPP dump (post tcp_transitory) triggers aged event |
| `StaticEntryNeverAged` | Entries with `aging_time=0` are skipped by the aging thread |
| `RifZoneInside` | RIF with `nat_zone=0` calls `nat44_interface_add_del_feature(is_inside=1)` |
| `RifZoneOutside` | RIF with `nat_zone=1` calls `nat44_interface_add_del_feature(is_inside=0)` |
| `RifZoneLoopback` | Loopback RIF zone change does NOT call VPP API |
| `ZoneCounterCreateGet` | Software zone counter create/read |
| `SnatMissTrap` | Enabling SNAT_MISS hostif trap calls `nat44_lcp_punt_enable_disable(enable=1)` |
| `BulkCreateNatEntries` | Bulk API correctly batched |
| `AgingTimeMapping` | `SAI_NAT_ENTRY_ATTR_AGING_TIME` → `nat_set_timeouts` with proto-appropriate value |

VPP API calls are mocked using a shim layer (`SaiVppXlate` already supports a test mode via `init_vpp_client` stub).

### 7.2 sonic-mgmt Test Coverage

The sonic-mgmt test suite at `tests/nat/` is the primary validation. Tests run against a sonic-vpp DUT in a t0 topology.

| Test Case | Status | Notes |
|---|---|---|
| `test_nat_static_basic` | Supported | Static SNAT/DNAT pair on TCP/UDP |
| `test_nat_static_basic_icmp` | Supported | Kernel-only; VPP not involved |
| `test_nat_static_napt` | Supported | TCP/UDP NAPT |
| `test_nat_clear_statistics_static_basic` | Supported | Counter increment, then `sonic-clear nat statistics` |
| `test_nat_clear_statistics_static_napt` | Supported | Same for NAPT |
| `test_nat_clear_translations_static_basic` | Supported | Verify static entries not cleared |
| `test_nat_clear_translations_static_napt` | Supported | Same for NAPT |
| `test_nat_crud_static_nat` | Supported | Create/delete/recreate lifecycle |
| `test_nat_crud_static_napt` | Supported | Same for NAPT |
| `test_nat_reboot_static_basic` | **Limited** | Requires VPP SAI warm boot — fall back to cold reboot only |
| `test_nat_reboot_static_napt` | **Limited** | Same |
| `test_nat_static_zones_basic_snat` | Supported | Zone 0 vs 1 toggle |
| `test_nat_static_zones_basic_icmp_snat` | Supported | Kernel-only |
| `test_nat_static_zones_napt_dnat_and_snat` | Supported | NAPT with zones |
| `test_nat_static_iptables_add_remove` | Supported | Verifies kernel iptables; unrelated to VPP |
| `test_nat_static_global_double_add` | Supported | Overlap detection in NatMgr |
| `test_nat_static_interface_add_remove_interface_ip` | Supported | IP add/remove on RIF |
| `test_nat_static_interface_add_remove_interface` | Supported | RIF admin state |
| `test_nat_static_redis_global_pool_binding` | Supported | DB sync verification |
| `test_nat_static_redis_napt` | Supported | DB sync |
| `test_nat_static_redis_asic` | Supported | ASIC_DB to VPP sync |
| `test_nat_same_static_and_dynamic_rule` | Supported | Static precedence |
| `test_nat_dynamic_basic` | Supported | Kernel-driven; VPP receives static mapping from NatOrch |
| `test_nat_dynamic_basic_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_entry_persist` | Supported | Aging via hit_bit polling |
| `test_nat_dynamic_entry_persist_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_disable_nat` | Supported | `SAI_SWITCH_ATTR_NAT_ENABLE = false` clears everything |
| `test_nat_dynamic_disable_nat_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_bindings` | Supported | ACL-pool binding |
| `test_nat_dynamic_bindings_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_other_protocols` | Supported | GRE not NAT'ted (no static mapping created) |
| `test_nat_dynamic_acl_rule_actions` | Supported | do_not_nat vs forward (kernel iptables + VPP ACL) |
| `test_nat_dynamic_acl_rule_actions_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_acl_modify_rule` | Supported | ACL changes propagate |
| `test_nat_dynamic_acl_modify_rule_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_pool_threshold` | Supported | Kernel iptables enforces pool size; VPP just receives entries |
| `test_nat_dynamic_crud` | Supported | Pool range update |
| `test_nat_dynamic_crud_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_full_cone` | Supported | Full cone behavior comes from kernel SNAT --fullcone; VPP translates accordingly |
| `test_nat_dynamic_enable_disable_nat_docker` | Supported | NAT docker lifecycle |
| `test_nat_dynamic_enable_disable_nat_docker_icmp` | Supported | Kernel-only |
| `test_nat_clear_statistics_dynamic` | Supported | Counter increment + clear |
| `test_nat_clear_translations_dynamic` | Supported | Dynamic entry flush |
| `test_nat_interfaces_flap_dynamic` | Supported | Link flap doesn't remove sessions |
| `test_nat_dynamic_zones` | Supported | Zone-based control |
| `test_nat_dynamic_zones_icmp` | Supported | Kernel-only |
| `test_nat_dynamic_extremal_ports` | Supported | High/low ports |
| `test_nat_dynamic_single_host` | Supported | Many sessions, one host |
| `test_nat_dynamic_binding_remove` | Supported | Unbind ACL |
| `test_nat_dynamic_iptable_snat` | Supported | Kernel iptables verification |
| `test_nat_dynamic_outside_interface_delete` | Supported | Outside RIF delete |
| `test_nat_dynamic_nat_pools` | Supported | Multiple pools |
| `test_nat_dynamic_modify_bindings` | Supported | Binding modify |

**Coverage gaps**:
- Warm boot tests (`test_nat_reboot_*`) require sonic-vpp warm boot framework, which is a separate effort.
- No upstream tests cover twice NAT explicitly, although the HLD describes it. We will add internal twice-NAT smoke tests in the unit test suite to cover this gap.

### 7.3 Manual VPP Verification

After running an integration test, verify VPP state with:

```
vppctl> show nat44 static mappings
vppctl> show nat44 sessions detail
vppctl> show nat44 interfaces
vppctl> show nat44 timeouts
vppctl> show nat44 summary
```

Counter and hit-bit verification:

```
redis-cli -n 1 hgetall "COUNTERS:oid:0x...nat..."
redis-cli -n 6 hgetall "COUNTERS_NAT:65.55.42.3"
```
