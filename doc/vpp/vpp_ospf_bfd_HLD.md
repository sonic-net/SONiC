# OSPF and FRR BFD on SONiC-VPP — High-Level Design

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2026-11-17 | nhegde-microsoft | Initial OSPFv2, OSPFv3, and FRR BFD control-plane design. |

## Scope

This design enables OSPFv2 and OSPFv3 routing on SONiC-VPP and qualifies the existing FRR single-hop BFD path used by the OSPF tests.

The feature is an OSPF control-plane delivery path. It does **not** add a CoPP policer, change the CoPP API, modify saivpp hostif-trap programming, or add VPP BFD offload. The existing CoPP HLD is used only as a documentation-format reference.

## Requirements

| # | Requirement |
|---|---|
| REQ-1 | IPv4 protocol 89 and IPv6 next-header 89 arriving on an LCP-paired interface must reach the Linux control plane. |
| REQ-2 | OSPF unicast and multicast traffic must use the existing `ip4-punt` / `ip6-punt` and linux-cp delivery path. |
| REQ-3 | OSPF multicast destinations `224.0.0.5/6` and `ff02::5/6` must be redirected before FIB or MFIB lookup can consume or drop them. |
| REQ-4 | OSPF delivery must be independent of the optional sonic-ext CoPP feature and must remain functional when `sonic-ext { copp off }` is configured. |
| REQ-5 | Every current and future LCP pair must receive the IPv4 and IPv6 OSPF input features, and pair removal must remove them. |
| REQ-6 | The sonic-mgmt tests must assert a non-zero expected peer set and prove adjacency, route installation, withdrawal, and recovery. |
| REQ-7 | The OSPF BFD test must exercise FRR `bfdd` without requiring a SAI BFD session or native VPP BFD offload. |

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

`sonic-ext` owns the OSPF path directly:

1. On main-loop entry it walks any existing LCP pairs and enables all four OSPF features on each pair's physical VPP interface.
2. The LCP pair-add callback enables the same features on each new pair.
3. The pair-delete callback disables them.
4. Enabling or disabling one pair is transactional. If one of the four feature-arc operations fails, already-changed arcs are rolled back.

There is no SAI RPC or CoPP state gate in this lifecycle.

### CoPP relationship

OSPF is commonly represented by SAI hostif trap types and can be policed by a hardware implementation. That adjacent concern is not required to make OSPF work on SONiC-VPP and is outside this feature.

The OSPF punt nodes:

- do not create or resolve VPP policers;
- do not add an IP-protocol slot to `sonic-ext-copp-ip2me`;
- do not change `sonic_ext_copp.api`;
- do not require `SwitchVppHostifTrap` changes;
- continue to work when sonic-ext CoPP is disabled.

If OSPF policer enforcement is needed later, it should be proposed and qualified independently without making basic OSPF delivery depend on it.

### FRR BFD path

The sonic-mgmt `ospf/test_ospf_bfd.py` scenario starts FRR `ospfd` and `bfdd`. It does not create a SAI BFD session. Single-hop BFD UDP traffic therefore follows the existing Linux control-plane path and terminates in FRR:

```text
wire UDP/3784
  -> existing VPP local/Linux control-plane delivery
  -> paired Linux TAP
  -> kernel UDP socket
  -> FRR bfdd
```

Return traffic uses the existing linux-cp/host-xc path. No VPP BFD node, SAI BFD object, or new API is introduced.

## Failure Handling

- A truncated packet that does not contain a complete base IP header is passed to the next feature.
- Failure to enable one address-family/arc combination rolls back the feature operations already completed for that LCP pair.
- Pair callback failures are logged with the affected `sw_if_index`; they do not modify CoPP state.
- The OSPF nodes do not retain per-neighbor, per-route, or per-packet state.

## Test Strategy

### Focused VPP test

`test_sonic_ext_ospf.py` creates an in-process linux-cp test pair with `sonic-ext { copp off }` and verifies:

1. OSPFv2 multicast to `224.0.0.5` reaches the paired host interface.
2. OSPFv3 multicast to `ff02::5` reaches the paired host interface.

This proves both multicast arcs and proves that OSPF delivery is not coupled to CoPP.

### sonic-mgmt qualification

The standard `t0-vpp` topology uses four cEOS neighbors. The tests must prove:

- all expected OSPF neighbors reach `FULL`;
- the expected peer count is non-zero before assertions run;
- an advertised loopback route is installed and then withdrawn;
- FRR BFD sessions reach `Up`;
- BFD-only failure withdraws the route while carrier remains up;
- restoring BFD recovers adjacency and routing.

A pre-feature run reached four cEOS neighbors in `INIT` while the DUT learned none, demonstrating the missing protocol-89 ingress punt.

## Implementation and Qualification Revisions

| Component | Revision | Scope |
|---|---|---|
| `sonic-platform-vpp` | `6aa4ba3` | CoPP-independent OSPFv2/OSPFv3 unicast and multicast punt to linux-cp. |
| `sonic-mgmt` | `320d74230` | Standard `t0-vpp` cEOS setup, non-vacuous OSPF assertions, and FRR BFD failure/recovery coverage. |

Combined-image execution of `ospf/test_ospf.py` and `ospf/test_ospf_bfd.py` is pending.

## Files Changed

| Repository | File | Purpose |
|---|---|---|
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/ospf_punt_node.c` | Protocol-89 IPv4/IPv6 unicast and multicast redirection. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/sonic_ext.c` | Existing-pair walk and LCP pair add/delete lifecycle. |
| `sonic-platform-vpp` | `vppbld/plugins/src/sonic_ext/sonic_ext.h` | OSPF pair feature helper declaration. |
| `sonic-platform-vpp` | `vppbld/plugins/tests/sonic_ext/test_sonic_ext_ospf.py` | CoPP-off OSPFv2/OSPFv3 punt tests. |
| `sonic-mgmt` | `tests/ospf/` and VPP CI selectors | End-to-end OSPF and FRR BFD qualification. |

## Alternatives Considered

### Couple OSPF activation to a CoPP hostif-trap binding

Rejected. It would require a new VPP CoPP API and saivpp changes, and would make basic routing-protocol delivery depend on optional policer programming.

### Add native VPP BFD offload

Rejected for this scope. The test uses FRR `bfdd`, and the existing Linux UDP path is the behavior being qualified.

### Punt only OSPF unicast

Rejected. OSPF adjacency formation depends on the AllSPFRouters and AllDRouters multicast groups, which otherwise follow VPP MFIB processing rather than the host punt path.
