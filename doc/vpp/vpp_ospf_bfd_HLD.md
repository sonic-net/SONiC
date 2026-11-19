# OSPF and FRR BFD on SONiC-VPP — High-Level Design

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2026-11-17 | nhegde-microsoft | Initial OSPFv2, OSPFv3, and FRR BFD control-plane design. |
| 1.1 | 2026-11-19 | nhegde-microsoft | Add single-hop BFD punt delivery and record passing cEOS qualification. |

## Scope

This design enables OSPFv2 and OSPFv3 routing on SONiC-VPP and qualifies FRR single-hop BFD used by the OSPF tests.

The feature adds protocol-specific OSPF and BFD control-plane delivery nodes. It does **not** add a CoPP policer, change the CoPP API, modify saivpp hostif-trap programming, or add native VPP BFD session offload. The existing CoPP HLD is used only as a documentation-format reference.

## Requirements

| # | Requirement |
|---|---|
| REQ-1 | IPv4 protocol 89 and IPv6 next-header 89 arriving on an LCP-paired interface must reach the Linux control plane. |
| REQ-2 | OSPF unicast and multicast traffic must use the existing `ip4-punt` / `ip6-punt` and linux-cp delivery path. |
| REQ-3 | OSPF multicast destinations `224.0.0.5/6` and `ff02::5/6` must be redirected before FIB or MFIB lookup can consume or drop them. |
| REQ-4 | OSPF delivery must be independent of the optional sonic-ext CoPP feature and must remain functional when `sonic-ext { copp off }` is configured. |
| REQ-5 | Every current and future LCP pair must receive the IPv4 and IPv6 OSPF and BFD input features, and pair removal must remove them. |
| REQ-6 | Single-hop IPv4/IPv6 BFD packets with TTL/hop-limit 255 must reach FRR before ingress ACL or route lookup can consume them. |
| REQ-7 | The sonic-mgmt tests must assert a non-zero expected peer set and prove adjacency, route installation, BFD-driven withdrawal, and recovery. |
| REQ-8 | The OSPF BFD test must exercise FRR `bfdd` without requiring a SAI BFD session or native VPP BFD offload. |

## Architecture

### OSPF packet path

The `sonic_ext` plugin adds two protocol-specific nodes:

- `sonic-ext-ospf4-punt`
- `sonic-ext-ospf6-punt`

Each node is registered on both the unicast and multicast input arcs for its address family. A packet whose IPv4 protocol or IPv6 base-header next-header is 89 is redirected to the corresponding standard IP punt node. Every other packet follows the next feature unchanged.

```text
wire IPv4
  -> ip4-input
  -> sonic-ext-ospf4-punt (ip4-unicast or ip4-multicast)
       protocol != 89 -> next input feature
       protocol == 89 -> ip4-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel
  -> FRR ospfd

wire IPv6
  -> ip6-input
  -> sonic-ext-ospf6-punt (ip6-unicast or ip6-multicast)
       next-header != 89 -> next input feature
       next-header == 89 -> ip6-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel
  -> FRR ospf6d
```

The implementation deliberately reuses linux-cp instead of cloning packets directly to a TAP. This preserves the normal LCP interface selection, Linux receive processing, namespaces, and FRR socket path.

### Feature lifecycle

`sonic-ext` owns the OSPF and BFD paths directly:

1. On main-loop entry it walks any existing LCP pairs and enables four OSPF features plus two BFD features on each pair's physical VPP interface.
2. The LCP pair-add callback enables the same features on each new pair.
3. The pair-delete callback disables them.
4. OSPF and BFD helpers roll back earlier feature-arc changes if a later operation on the same pair fails.

There is no SAI RPC or CoPP state gate in this lifecycle.

### CoPP relationship

OSPF is commonly represented by SAI hostif trap types and can be policed by a hardware implementation. That adjacent concern is not required to make OSPF work on SONiC-VPP and is outside this feature.

The OSPF and BFD punt nodes:

- do not create or resolve VPP policers;
- do not add an IP-protocol slot to `sonic-ext-copp-ip2me`;
- do not change `sonic_ext_copp.api`;
- do not require `SwitchVppHostifTrap` changes;
- continue to work when sonic-ext CoPP is disabled.

If OSPF policer enforcement is needed later, it should be proposed and qualified independently without making basic OSPF delivery depend on it.

### FRR BFD path

The sonic-mgmt `ospf/test_ospf_bfd.py` scenario starts FRR `ospfd` and `bfdd`. It does not create a SAI BFD session. The `sonic-ext-bfd4-punt` and `sonic-ext-bfd6-punt` nodes match UDP/3784 control packets (and UDP/3785 echo packets) only when TTL or hop-limit is 255, then redirect them before ingress ACL and route lookup:

```text
wire UDP/3784, TTL or hop-limit 255
  -> sonic-ext-bfd4-punt or sonic-ext-bfd6-punt
  -> ip4-punt or ip6-punt
  -> linux-cp punt redirect
  -> paired Linux TAP
  -> kernel UDP socket
  -> FRR bfdd
```

Return traffic uses the existing linux-cp/host-xc path. No native VPP BFD session, SAI BFD object, or new API is introduced.

`caclmgrd` normally opens host UDP/3784 and UDP/4784 after a SAI `BFD_SESSION_TABLE` event. This FRR-only qualification intentionally has no such event, so its module-scoped fixture installs the equivalent host allowance and removes only rules it inserted.

## Failure Handling

- A truncated packet that does not contain a complete base IP header is passed to the next feature.
- A non-UDP packet, a non-BFD destination port, or a BFD packet without TTL/hop-limit 255 passes to the next feature.
- Failure to enable one address-family/arc combination rolls back the feature operations already completed for that LCP pair.
- Pair callback failures are logged with the affected `sw_if_index`; they do not modify CoPP state.
- The OSPF and BFD nodes do not retain per-neighbor, per-route, or per-packet state.

## Test Strategy

### Focused VPP test

`test_sonic_ext_ospf_bfd.py` creates an in-process linux-cp test pair with `sonic-ext { copp off }` and verifies:

1. OSPFv2 multicast to `224.0.0.5` reaches the paired host interface.
2. OSPFv3 multicast to `ff02::5` reaches the paired host interface.
3. IPv4 UDP/3784 with TTL 255 reaches the paired host interface.
4. IPv6 UDP/3784 with hop-limit 255 reaches the paired host interface.

This proves both OSPF multicast arcs, both BFD families, and independence from CoPP.

### sonic-mgmt qualification

The standard `t0-vpp` topology uses four cEOS neighbors. The tests must prove:

- all expected OSPF neighbors reach `FULL`;
- the expected peer count is non-zero before assertions run;
- an advertised loopback route is installed and then withdrawn;
- FRR BFD sessions reach `Up`;
- silent BFD packet loss withdraws the route while carrier remains up;
- removing the packet-loss fault recovers BFD and routing.

A pre-feature run reached four cEOS neighbors in `INIT` while the DUT learned none, demonstrating the missing protocol-89 ingress punt.

## Implementation and Qualification Revisions

| Component | Revision | Scope |
|---|---|---|
| `sonic-platform-vpp` | `c607f7b06dbe697a366e9d32169c8a4bcd2f8db7` | CoPP-independent OSPFv2/OSPFv3 and single-hop IPv4/IPv6 BFD punt to linux-cp. |
| `sonic-mgmt` | `44a506541be3176f23d566a899e4b2b6522b01ea` | Standard `t0-vpp` cEOS setup, non-vacuous OSPF assertions, host BFD allowance, and silent-fault withdrawal/recovery coverage. |

Focused VPP tests passed **4/4**. Combined-image cEOS qualification passed **2/2 OSPF tests** and **1/1 BFD failure/withdrawal/recovery test**, with no failures, errors, or skips.

## Files Changed

| Repository | File | Purpose |
|---|---|---|
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/ospf_punt_node.c` | Protocol-89 IPv4/IPv6 unicast and multicast redirection. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/bfd_punt_node.c` | Single-hop IPv4/IPv6 BFD redirection before ACL and lookup. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/sonic_ext.c` | Existing-pair walk and LCP pair add/delete lifecycle. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/sonic_ext.h` | OSPF and BFD pair feature helper declarations. |
| `sonic-platform-vpp` | `vppbld/plugins/tests/sonic_ext/test_sonic_ext_ospf_bfd.py` | CoPP-off OSPFv2/OSPFv3 and IPv4/IPv6 BFD punt tests. |
| `sonic-mgmt` | `tests/ospf/` and VPP CI selectors | End-to-end OSPF and FRR BFD qualification. |

## Alternatives Considered

### Couple OSPF activation to a CoPP hostif-trap binding

Rejected. It would require a new VPP CoPP API and saivpp changes, and would make basic routing-protocol delivery depend on optional policer programming.

### Add native VPP BFD offload

Rejected for this scope. The test uses FRR `bfdd`, and the existing Linux UDP path is the behavior being qualified.

### Punt only OSPF unicast

Rejected. OSPF adjacency formation depends on the AllSPFRouters and AllDRouters multicast groups, which otherwise follow VPP MFIB processing rather than the host punt path.
