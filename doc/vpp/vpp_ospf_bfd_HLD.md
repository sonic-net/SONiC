# OSPF and FRR BFD on SONiC-VPP — High-Level Design

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2026-11-17 | nhegde-microsoft | Initial OSPFv2, OSPFv3, and FRR BFD control-plane design. |
| 1.1 | 2026-11-19 | nhegde-microsoft | Add single-hop BFD delivery and record passing cEOS qualification. |
| 1.2 | 2026-11-20 | nhegde-microsoft | Reuse the existing linux-cp OSPF multicast, local-protocol, and unknown-UDP punt paths instead of adding protocol-specific graph nodes. |

## Scope

This design enables OSPFv2 and OSPFv3 routing on SONiC-VPP and qualifies the FRR single-hop BFD sessions used by the OSPF tests.

No new OSPF or BFD graph node is required. VPP and linux-cp already provide the complete local-delivery path:

- linux-cp programs local IPv4 and IPv6 multicast routes for LCP interfaces;
- VPP sends unhandled local IP protocols, including OSPF protocol 89, to the standard IP punt arcs;
- linux-cp sends unhandled local UDP, including FRR BFD ports when VPP has no native BFD session, to the same punt arcs; and
- each LCP pair has IPv4 and IPv6 punt redirects to its Linux host interface.

The design does **not** add a CoPP policer, change the CoPP API, modify saivpp hostif-trap programming, add native VPP BFD session offload, or change non-VPP platforms.

## Requirements

| # | Requirement |
|---|---|
| REQ-1 | Locally delivered IPv4 protocol 89 and IPv6 next-header 89 on an LCP-paired interface must reach the Linux control plane. |
| REQ-2 | OSPFv2 multicast in `224.0.0.0/24` and OSPFv3 multicast in `ff00::/8`, including `224.0.0.5/6` and `ff02::5/6`, must use linux-cp's multicast accept and local-delivery routes. |
| REQ-3 | OSPF unicast and multicast traffic must use the existing `ip4-punt` / `ip6-punt` and linux-cp delivery path. |
| REQ-4 | OSPF delivery must be independent of the optional sonic-ext CoPP feature. |
| REQ-5 | Local single-hop IPv4/IPv6 FRR BFD traffic must reach Linux through the existing unknown-UDP punt path when no native VPP BFD session owns the port. |
| REQ-6 | The sonic-mgmt tests must assert a non-zero expected peer set and prove adjacency, route installation, BFD-driven withdrawal, and recovery. |
| REQ-7 | The OSPF BFD test must exercise FRR `bfdd` without requiring a SAI BFD session or native VPP BFD offload. |
| REQ-8 | Focused VPP coverage must reproduce the linux-cp multicast state omitted by the synthetic LCP test-pair helper without adding production dataplane behavior. |

## Architecture

### linux-cp interface state

Creating an LCP pair installs IPv4 and IPv6 punt-redirect paths from the physical interface to the paired Linux host interface. The original receive interface selects the correct redirect, so packets entering the common `ip4-punt` or `ip6-punt` arc reach the corresponding Linux TAP.

linux-cp also maintains multicast state through its router synchronization:

- each IPv4 LCP address enables an ingress `ACCEPT` path for `(*,224.0.0.0/24)`;
- each IPv6 LCP address enables an ingress `ACCEPT` path for `(*,ff00::/8)`; and
- each corresponding multicast table has a `FIB_ROUTE_PATH_LOCAL` forwarding path for the same prefix.

The local multicast path resolves through a receive DPO to `ip4-receive` or `ip6-receive`. This is existing linux-cp behavior; no sonic-ext feature lifecycle is involved.

### OSPF packet path

VPP initializes unregistered local IP protocols to the standard IP punt next. OSPF protocol 89 has no native VPP consumer, so both unicast packets addressed to the switch and multicast packets selected by the linux-cp routes reach the appropriate punt arc.

```text
OSPF unicast addressed to the switch
  -> ip4-input or ip6-input
  -> unicast lookup
  -> receive DPO
  -> ip4-local/ip4-receive or ip6-local/ip6-receive
  -> protocol 89 default local action
  -> ip4-punt or ip6-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel
  -> FRR ospfd/ospf6d

OSPF multicast
  -> ip4-multicast or ip6-multicast
  -> linux-cp MFIB ingress ACCEPT check
  -> linux-cp MFIB local forwarding path
  -> receive DPO
  -> protocol 89 default local action
  -> ip4-punt or ip6-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel
  -> FRR ospfd/ospf6d
```

Lookup remains authoritative. The dataplane does not punt every protocol-89 packet before lookup, so matching transit traffic is not diverted to Linux.

### FRR BFD packet path

The sonic-mgmt `ospf/test_ospf_bfd.py` scenario starts FRR `ospfd` and `bfdd`; it does not create a SAI BFD session or native VPP BFD session.

linux-cp enables unknown-UDP punt for IPv4 and IPv6. VPP's local UDP lookup sends a datagram with no registered VPP destination-port consumer to `ip4-punt` or `ip6-punt`. Therefore local UDP/3784 BFD control and UDP/3785 BFD echo traffic follow the existing path:

```text
local UDP/3784 or UDP/3785
  -> ip4-input or ip6-input
  -> unicast lookup
  -> receive DPO
  -> ip4-udp-lookup or ip6-udp-lookup
  -> no registered VPP port consumer
  -> unknown-UDP punt
  -> ip4-punt or ip6-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel UDP socket
  -> FRR bfdd
```

A native VPP BFD session would register the BFD UDP ports with VPP and change their ownership. Native VPP BFD is outside this design.

Return traffic uses the existing linux-cp host-to-physical path. No new API or graph node is introduced.

`caclmgrd` normally opens host UDP/3784 and UDP/4784 after a SAI `BFD_SESSION_TABLE` event. This FRR-only qualification intentionally has no such event, so its module-scoped fixture installs the equivalent host allowance and removes only rules it inserted.

### CoPP relationship

OSPF can be represented by SAI hostif trap types and policed by hardware implementations. That concern is independent of basic protocol delivery in SONiC-VPP.

This design:

- does not create or resolve VPP policers;
- does not add an IP-protocol slot to `sonic-ext-copp-ip2me`;
- does not change `sonic_ext_copp.api`;
- does not require `SwitchVppHostifTrap` changes; and
- does not depend on `sonic-ext { copp on }`.

If OSPF or BFD policer enforcement is needed later, it should be proposed and qualified independently.

### Platform scope

The provider-level test and all dataplane behavior described here are VPP/linux-cp specific. Hardware ASIC platforms retain their existing SAI hostif-trap and CoPP paths. The sonic-mgmt assertions remain platform-neutral except for selecting the tests on `t0-vpp`.

## Failure Handling

- Without an LCP pair, the punt arc has no redirect to a paired Linux host interface.
- Without the multicast ingress `ACCEPT` path, MFIB rejects OSPF multicast received on that interface.
- Without the multicast local forwarding path, the multicast packet is not delivered to the local IP protocol handler.
- A non-local unicast OSPF or BFD packet follows normal forwarding and is not stolen by a protocol-specific pre-lookup node.
- A VPP ingress ACL can still deny traffic before lookup; this design does not introduce an ACL bypass.
- If a native VPP BFD session registers UDP/3784 or UDP/3785, VPP owns that traffic instead of the unknown-UDP punt path.
- The host firewall allowance is scoped to the FRR-only test and removes only rules inserted by its fixture.

## Test Strategy

### Focused VPP test

The provider-level test creates an in-process linux-cp test pair and verifies:

1. OSPFv2 multicast to `224.0.0.5` reaches the paired host interface.
2. OSPFv3 multicast to `ff02::5` reaches the paired host interface.
3. Local IPv4 UDP/3784 reaches the paired host interface.
4. Local IPv6 UDP/3784 reaches the paired host interface.

The linux-cp unittest `test lcp add` helper creates the pair and punt redirects, but it does not generate Linux Netlink address events. The test therefore explicitly installs the same multicast ingress `ACCEPT` and table-local forwarding paths that production linux-cp installs from those events. This is test setup only; it does not add production configuration or alter another platform.

A node-disabled control run passed all four cases through the existing linux-cp paths. The committed provider test uses those paths directly and has no dependency on sonic-ext OSPF or BFD nodes.

### sonic-mgmt qualification

The standard `t0-vpp` topology uses four cEOS neighbors. The tests prove:

- all expected OSPF neighbors reach `FULL`;
- the expected peer count is non-zero before assertions run;
- an advertised loopback route is installed and then withdrawn;
- FRR BFD sessions reach `Up`;
- silent BFD packet loss withdraws the route while carrier remains up; and
- removing the packet-loss fault recovers BFD and routing.

The prior combined-image qualification validates the sonic-mgmt setup and assertions. A combined image built without protocol-specific punt nodes must rerun the same tests to provide final integration evidence for this design.

## Files Changed

| Repository | File | Purpose |
|---|---|---|
| `sonic-platform-vpp` | provider-level linux-cp OSPF/BFD test | Reproduce production multicast state and verify existing OSPF and BFD delivery paths. |
| `sonic-mgmt` | `tests/ospf/` and VPP CI selectors | End-to-end OSPF and FRR BFD qualification. |

## Alternatives Considered

### Add protocol-specific OSPF and BFD input nodes

Rejected. The four IPv4/IPv6 OSPF/BFD cases pass through existing linux-cp paths when the focused test reproduces production multicast state. Pre-lookup nodes would duplicate existing local-delivery behavior and divert matching transit packets without first establishing that they are destined to the switch.

### Register OSPF protocol 89 directly to the punt nodes

Rejected. VPP already initializes unregistered local IP protocols to the punt next, so explicit IPv4 and IPv6 protocol registrations would not change behavior.

### Couple OSPF activation to a CoPP hostif-trap binding

Rejected. It would require a new VPP CoPP API and saivpp changes, and would make basic routing-protocol delivery depend on optional policer programming.

### Add native VPP BFD offload

Rejected for this scope. The test uses FRR `bfdd`, and the existing Linux UDP path is the behavior being qualified.

### Add a pre-ACL bypass

Rejected for this scope. The existing focused and integration tests do not install a DUT VPP ingress deny ACL. If hardware-style pre-ACL trapping becomes a requirement, it needs a separate design with destination-local scoping and an A/B test that first demonstrates failure through the stock path.
