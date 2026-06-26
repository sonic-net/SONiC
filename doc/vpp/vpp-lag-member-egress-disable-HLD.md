# SONiC-VPP LAG Member Egress Disable HLD

## Table of Contents

1. [Revisions](#1-revisions)
2. [Scope](#2-scope)
3. [Definitions](#3-definitions)
4. [Background](#4-background)
5. [Problem Statement](#5-problem-statement)
6. [Goals and Non-Goals](#6-goals-and-non-goals)
7. [High Level Design](#7-high-level-design)
8. [Behavior Matrix](#8-behavior-matrix)
9. [Call Flows](#9-call-flows)
10. [Error Handling](#10-error-handling)
11. [Limitations and Future Work](#11-limitations-and-future-work)
12. [References](#12-references)

## 1. Revisions

| Rev | Date | Author(s) | Changes |
|---|---|---|---|
| v0.1 | 2026-06-05 | Chenyang Wang | Initial HLD for VPP LAG member egress disable support |
| v0.2 | 2026-06-23 | Chenyang Wang | Model egress disable by setting the member port VPP admin state down instead of detaching it from the VPP bond |
| v0.3 | 2026-06-24 | Chenyang Wang | Model egress disable by detaching the member from the VPP bond while keeping its link up. The v0.2 admin-state-down approach drops the teamd-run LACP control path and was found to prevent LACP/BGP convergence on uplink PortChannels. |

## 2. Scope

This document describes how SONiC-VPP handles `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` for LAG members in the VPP-backed virtual switch path.

The design covers:

- Creating a LAG member while egress is disabled.
- Dynamically disabling egress on an existing LAG member.
- Dynamically enabling egress on a previously disabled LAG member.
- Keeping VPP bond egress membership aligned with SONiC SAI egress-disable state, without disturbing the member link used by LACP.
- Preserving the existing delayed LCP/tap creation behavior for VPP LAGs.

This document is a focused extension of the broader [SONiC VPP LAG Support](vpp-lag.md) HLD.

## 3. Definitions

| Term | Meaning |
|---|---|
| LAG | Link Aggregation Group, exposed in SONiC as a PortChannel |
| LAG member | A physical port that belongs to a LAG |
| Bond | VPP BondEthernet interface used to model a SONiC PortChannel |
| Bond membership | Whether a member port is currently attached to (a forwarding participant of) the VPP BondEthernet |
| LCP | VPP Linux Control Plane plugin, used to pair VPP interfaces with Linux interfaces |
| Egress disable | SAI LAG member attribute that prevents a member from being used for egress traffic |
| Member admin state | The up/down admin state of the VPP interface backing a LAG member port |

## 4. Background

SONiC represents a PortChannel as a SAI LAG object and each member port as a SAI LAG member object. In SONiC-VPP, the SAI-VPP layer translates these objects into VPP bond configuration:

```text
SONiC PortChannel
    -> SAI LAG
        -> VPP BondEthernet

SONiC PortChannel member
    -> SAI LAG member
        -> VPP bond member
```

The existing VPP LAG design creates the VPP LAG bond first, then adds member ports to the bond. For L3 PortChannel host-path support, SONiC-VPP also creates an LCP/tap pair for the bond interface.

One important detail is that LCP/tap creation is intentionally delayed until the first enabled member is added. Creating the tap too early, while the VPP bond has no active member, can leave the tap with a stale generated MAC address instead of the first member's MAC address. When the first member is added, the VPP bond adopts that member's MAC, so delaying tap creation until then ensures the tap, bond, and first-member MAC addresses all match.

### Egress disable in the data plane

`SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` controls only **data-plane egress distribution** for a LAG member. It is the egress half of the IEEE 802.1AX *collecting / distributing* model that SONiC uses to represent a member's LACP selection state, and it has an ingress counterpart:

| SAI attribute | 802.1AX role | Direction | Effect when set to `true` |
|---|---|---|---|
| `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` | Distributing off | Egress (Tx data frames) | Member is removed from the LAG's egress distribution (hash) set |
| `SAI_LAG_MEMBER_ATTR_INGRESS_DISABLE` | Collecting off | Ingress (Rx data frames) | Member stops accepting data frames into the LAG |

SONiC drives these attributes from teamd's LACP state: a member is added with both disabled while it is still unselected, and Orchagent clears them once teamd reports the member as collecting and distributing. SONiC's expectation for `EGRESS_DISABLE=true` is therefore deliberately narrow:

- **Only data frames are affected.** The member is taken out of the port channel's egress traffic distribution, so the forwarding plane no longer hashes data traffic onto it. `EGRESS_DISABLE` is the egress counterpart of `INGRESS_DISABLE`; it is **not** a port shutdown and **not** a "drop all egress" rule.
- **The member link stays up and LACP keeps running.** Egress-disable does not bring the member link down. LACP is control-plane traffic that continues to be exchanged over the member regardless of its distribution state, so teamd can still select or deselect it. If egress-disable dropped *all* egress packets, LACPDUs could not be sent, LACP would stall, and the member could never be (re)selected, which is why it must not be modeled as a blanket egress drop.
- **It is a normal transient state, not an error.** SONiC adds every LAG member with `EGRESS_DISABLE=true` (and `INGRESS_DISABLE=true`) *before* LACP has selected it, then teamd clears both once the member reaches the collecting + distributing state. Egress-disable is thus the expected initial and deselected state of a member that is still negotiating LACP.

The contract any SONiC dataplane must honor is: remove the member from egress data distribution while keeping its link up and its LACP control path alive. This is exactly why this design models egress-disable by detaching the member from the VPP bond rather than taking the member link down (see [§7](#7-high-level-design)); the next subsection details the VPP-specific LACP path that makes this distinction load-bearing.

### LACP control path

The VPP bond is created in **XOR mode**; VPP itself does not run LACP. LACP is run by **teamd in Linux**. Each LAG member port (e.g. `Ethernet0`) is an LCP tap paired with the member's VPP hardware-interface, and teamd runs the LACP state machine over those member taps. LACP control PDUs are punted/injected through the member hardware-interface, and teamd's per-member link watch follows that interface's link state.

A member hardware-interface is therefore simultaneously:

1. The **LACP control-plane path** for that member: `peer <-> member hwif <-> LCP tap <-> teamd`, and
2. A **bond egress member** in the VPP dataplane.

This dual role is the key constraint that drives the design choice in [§7](#7-high-level-design): anything that takes the member hardware-interface link down also stops LACP for that member.

## 5. Problem Statement

Before this feature, SONiC-VPP created and removed VPP bond members, but it did not react to updates of `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE`.

That caused two gaps:

1. If a LAG member was created with egress disabled, SONiC-VPP still brought it up as an active egress member of the VPP bond.
2. If SONiC later changed the egress-disable state of a LAG member, VPP bond egress membership did not change accordingly.

As a result, SONiC control-plane state and VPP dataplane state could diverge.

## 6. Goals and Non-Goals

### Goals

- Honor `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` in the VPP dataplane.
- Keep disabled LAG members out of VPP bond egress selection.
- Restore the member to active forwarding when egress is re-enabled.
- Preserve LACP convergence by keeping the member link administratively up across egress-disable transitions.
- Treat a missing stored `EGRESS_DISABLE` attribute as the SAI default value, `false`.
- Avoid unnecessary VPP operations when the requested egress-disable state does not change.
- Keep the delayed LCP/tap creation behavior unchanged.

### Non-Goals

- No change to SONiC CLI, Config DB, APP DB, or Orchagent behavior.
- No change to LACP protocol handling (LACP remains owned by teamd).
- No change to VPP bond mode or load-balancing algorithm selection.
- No support for additional SAI LAG member attributes beyond this feature.
- No redesign of the existing LAG LCP/tap and `tc` redirect model.

## 7. High Level Design

### 7.1 Design Summary

SONiC-VPP maps the SAI egress-disable state to VPP bond egress membership, and leaves the member link admin state untouched:

| SAI egress-disable state | VPP action |
|---|---|
| `true` | Detach the member from the VPP bond (remove it from egress distribution), leaving the member link administratively up |
| `false` | Re-attach the member to the VPP bond |

This honors egress-disable while keeping the LACP control plane intact:

- The SAI LAG member object follows the normal create/remove lifecycle.
- VPP bond membership reflects whether the member is eligible for egress traffic.
- The member port's link admin state is driven solely by `SAI_PORT_ATTR_ADMIN_STATE`, independent of egress-disable.

#### Why not member admin state down

An earlier revision (v0.2) modeled `EGRESS_DISABLE=true` by setting the member port's VPP interface **admin state down**, leaving the member attached to the bond. That approach is incompatible with this platform's LACP path and was found to prevent BGP convergence on LACP PortChannels.

As described in [§4 LACP control path](#lacp-control-path), the member hardware-interface carries both LACP control traffic and bond egress. Setting the member admin state **down** drops the LACP control path as well as egress: teamd's link watch sees the member tap go down and deselects the member, so the PortChannel never aggregates.

This is fatal during bring-up. SONiC creates each LAG member with `EGRESS_DISABLE=true` *before* LACP has selected it (the initial unselected LACP state, where teamd has not yet enabled collection/distribution). With the admin-down model:

1. The member is created egress-disabled, so its link is forced down.
2. With the link down, LACP PDUs cannot flow, so teamd can never select the member.
3. Because the member is never selected, SONiC never sets `EGRESS_DISABLE=false`.
4. The member stays down permanently, and the PortChannel (and any BGP session over it) never comes up.

The same deadlock applies to any later re-selection, because the member link must be up for LACP to renegotiate. Detaching the member from the bond instead removes it from egress distribution **while keeping its link up**, so LACP PDUs keep flowing and the member can be selected or re-selected. This mirrors how a hardware LAG implements egress-disable: the member link stays up and LACP-trapped, while the member is removed from the egress distribution set.

VPP offers no per-member egress-only disable on an XOR bond. Member `weight` is rejected by VPP for non-active-backup modes (`set interface bond: Weight valid for active-backup only`), so it cannot exclude a member from XOR egress while keeping the link up. Detach is therefore the only VPP mechanism that disables egress while preserving the LACP control plane. See [§7.9 Alternatives Considered](#79-alternatives-considered).

#### Port admin state independence

Because egress-disable no longer touches the member link admin state, the member link admin state is driven only by the port's own `SAI_PORT_ATTR_ADMIN_STATE`, and the two inputs are independent:

- Egress-disable detaches/re-attaches the member; it never changes the member link admin state.
- An administratively down port stays down regardless of egress-disable; an egress-disabled member stays administratively up (its link must stay up for LACP).

This removes the shared-knob coupling that the v0.2 design needed, so no "effective admin state" combination of the two inputs is required.

### 7.2 Create Path

When a LAG member is created:

1. Store the LAG member in the normal SAI-VPP object state.
2. Add the member to the VPP bond, as in the base LAG design.
3. Ensure LCP/tap setup for the bond (created on the first member, as before).
4. Check whether `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` is present and set to `true`.
5. If egress is disabled, detach the member from the VPP bond.

`create_internal()` records the SAI object in the virtual switch state, and `vpp_create_lag_member()` programs the VPP bond membership and the bond LCP/tap as before. Adding the member first (even when it will be detached) lets the bond adopt the first member's MAC and complete the delayed LCP/tap setup. For an initially disabled member it is then detached so it is not used for egress, while its link stays up for LACP.

```text
create LAG member
    |
    v
store SAI object state
    |
    v
add port to VPP bond
    |
    v
ensure bond LCP/tap exists
    |
    v
egress_disable == true?
    | yes
    v
detach member from VPP bond
```

### 7.3 Set Path

`SwitchVpp::set()` routes `SAI_OBJECT_TYPE_LAG_MEMBER` updates to `SwitchVpp::setLagMember()`.

`setLagMember()` handles only `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` specially. All other attributes continue to use the existing generic `set_internal()` path.

The set path follows this order:

1. Validate that the LAG member object exists.
2. Read the current stored `EGRESS_DISABLE` value.
3. Decide whether the requested value requires no action, detaching the member, or re-attaching it.
4. Program VPP first.
5. Update the stored SAI object state only after the VPP operation succeeds.

This order prevents SONiC-VPP from recording a new SAI state when the corresponding VPP programming fails.

### 7.4 Action Selection

The action selector uses three inputs:

- Requested `egress_disable` value from the new SAI set operation.
- Whether the current stored attribute exists.
- Current stored `egress_disable` value, if present.

The result is one of:

| Action | Meaning |
|---|---|
| `NONE` | No bond membership change is needed |
| `DISABLE` | Detach the member from the VPP bond |
| `ENABLE` | Re-attach the member to the VPP bond |

If the current stored attribute is missing, SONiC-VPP treats it as the SAI default `false`.

### 7.5 Disable Egress (Detach Member)

When egress is disabled:

```text
set EGRESS_DISABLE=true
    |
    v
detach member from VPP bond
    |
    v
update stored SAI attr to true
```

The SAI object is unchanged and the member link is left administratively up. Only the member's bond membership changes: it is detached from the VPP bond, removing it from egress distribution. Because the link stays up, the teamd-run LACP control plane continues to operate on the member.

### 7.6 Enable Egress (Re-attach Member)

When egress is re-enabled:

```text
set EGRESS_DISABLE=false
    |
    v
re-attach member to VPP bond
    |
    v
update stored SAI attr to false
```

Enabling reads the member's stored `SAI_LAG_MEMBER_ATTR_LAG_ID` and `SAI_LAG_MEMBER_ATTR_PORT_ID` to locate the VPP bond and member port, then re-attaches the member to the bond so it resumes egress distribution. The LCP/tap pair already exists, so no LCP/tap change is required.

### 7.7 LCP/Tap Handling

This feature does not change LCP/tap handling. The bond LCP/tap pair is created once, when the first member is added during the create path (the delayed-tap behavior from the base design).

- Egress-disable detach and egress-enable re-attach do not create or remove the LCP/tap pair.
- Re-attach calls only `create_bond_member()` and never re-enters `vpp_ensure_lag_lcp()`, so the bond's LCP/tap pairing and MAC are unaffected by egress transitions.
- The LCP/tap pair is removed only by normal LAG teardown.

`vpp_ensure_lag_lcp()` is still called from the create path and creates the LCP/tap pair only if it has not already been created for the LAG.

### 7.8 Remove Path and Lifecycle Edge Cases

The expected lifecycle behavior is:

| Case | Expected behavior |
|---|---|
| Remove an egress-enabled member | The member is still a bond member; detach it from the VPP bond, then remove the SAI object state, as in the base design |
| Remove an egress-disabled member | The member is already detached from the bond; skip the detach and just remove the SAI object state |
| Disable a member (including the last enabled member) | Detach it from the VPP bond; keep the member link up and keep all bond LCP/tap state |
| Re-enable a member | Re-attach it to the VPP bond; no LCP/tap change |

Because a disabled member is already detached from the bond, the remove path must not attempt to detach it again. SONiC-VPP tracks the set of egress-disabled member ports and, on remove, skips the redundant bond detach for a member that is already detached, then removes the SAI object. This explicitly handles the remove-while-already-detached case.

The member link admin state is never forced down by this feature, so there is no port admin state to restore on remove.

### 7.9 Alternatives Considered

Two options were evaluated for modeling `EGRESS_DISABLE=true`:

| Option | Description | Decision |
|---|---|---|
| Detach the member from the VPP bond | Remove the member from the bond on disable and re-add it on enable, keeping the member link administratively up | **Chosen.** Removes the member from egress distribution while keeping its link up, so the teamd-run LACP control plane keeps working and the PortChannel/BGP can converge. Mirrors hardware LAG egress-disable behavior. |
| Set the member port admin state down | Keep the member attached to the VPP bond and toggle its interface admin state down on disable and up on enable | **Not used.** The member hardware-interface also carries the LACP control path (teamd over its LCP tap), so admin-down drops LACP. Because SONiC creates members egress-disabled before LACP selects them, the member is never selected, egress is never re-enabled, and the member is stuck down. Validated as the cause of an all-uplink BGP-down regression on a VPP testbed. |

Detach keeps the member link up at the cost of bond add/remove churn on each egress transition. The churn is bounded (transitions happen only on LACP select/deselect) and is the only VPP mechanism that disables egress while preserving the LACP control plane. The concerns previously raised against detach are addressed by this design:

- **Re-add must not re-evaluate LCP/tap** — re-attach calls only `create_bond_member()` and never re-enters `vpp_ensure_lag_lcp()`, so LCP/tap and the bond MAC are untouched (see [§7.7](#77-lcptap-handling)).
- **Member attributes on re-add** — the bond index and member port are looked up from stored SAI object state, not reconstructed.
- **Remove-while-already-detached** — handled explicitly by tracking egress-disabled members and skipping the redundant detach on remove (see [§7.8](#78-remove-path-and-lifecycle-edge-cases)).

## 8. Behavior Matrix

| Current stored attr exists? | Current value | Requested value | VPP action | Stored state update |
|---|---|---|---|---|
| Yes | `false` | `false` | None | Set attr to `false` |
| Yes | `false` | `true` | Detach member from bond | Set attr to `true` after the update succeeds |
| Yes | `true` | `false` | Re-attach member to bond | Set attr to `false` after the update succeeds |
| Yes | `true` | `true` | None | Set attr to `true` |
| No | default `false` | `false` | None | Set attr to `false` |
| No | default `false` | `true` | Detach member from bond | Set attr to `true` after the update succeeds |

The member link admin state is not changed by any of these transitions; it is driven solely by `SAI_PORT_ATTR_ADMIN_STATE`.

## 9. Call Flows

### 9.1 LAG Member Created with Egress Enabled

```text
syncd
  |
  v
SwitchVpp::createLagMember()
  |
  v
create_internal(SAI_OBJECT_TYPE_LAG_MEMBER)
  |
  v
vpp_create_lag_member()
  |
  v
add member to VPP BondEthernet
  |
  v
vpp_ensure_lag_lcp()
```

### 9.2 LAG Member Created with Egress Disabled

```text
syncd
  |
  v
SwitchVpp::createLagMember()
  |
  v
create_internal(SAI_OBJECT_TYPE_LAG_MEMBER)
  |
  v
vpp_create_lag_member()
  |
  v
add member to VPP BondEthernet
  |
  v
vpp_ensure_lag_lcp()
  |
  v
detect EGRESS_DISABLE=true
  |
  v
detach member from VPP bond
```

### 9.3 Existing LAG Member Disabled

```text
syncd
  |
  v
SwitchVpp::set(SAI_OBJECT_TYPE_LAG_MEMBER)
  |
  v
SwitchVpp::setLagMember(EGRESS_DISABLE=true)
  |
  v
getLagMemberEgressDisableAction() -> DISABLE
  |
  v
vpp_set_lag_member_egress_disable(true)  [detach member from bond]
  |
  v
set_internal(EGRESS_DISABLE=true)
```

### 9.4 Existing LAG Member Re-Enabled

```text
syncd
  |
  v
SwitchVpp::set(SAI_OBJECT_TYPE_LAG_MEMBER)
  |
  v
SwitchVpp::setLagMember(EGRESS_DISABLE=false)
  |
  v
getLagMemberEgressDisableAction() -> ENABLE
  |
  v
vpp_set_lag_member_egress_disable(false)  [re-attach member to bond]
  |
  v
set_internal(EGRESS_DISABLE=false)
```

## 10. Error Handling

| Error case | Handling |
|---|---|
| Null set attribute | Return `SAI_STATUS_INVALID_PARAMETER` |
| LAG member object not found | Return `SAI_STATUS_ITEM_NOT_FOUND` |
| Unsupported LAG member attribute | Use existing generic `set_internal()` behavior |
| VPP detach-member (bond del) fails | Return the VPP failure status and do not update stored `EGRESS_DISABLE` state |
| VPP re-attach-member (bond add) fails | Return the VPP failure status and do not update stored `EGRESS_DISABLE` state |
| Stored `LAG_ID` or `PORT_ID` missing while toggling membership | Return `SAI_STATUS_FAILURE` |
| Stored `LAG_ID` or `PORT_ID` has the wrong object type | Return `SAI_STATUS_FAILURE` |
| Member port VPP hardware interface lookup fails | Return `SAI_STATUS_FAILURE` |
| Bond interface name lookup fails during LCP setup on the create path | Return `SAI_STATUS_FAILURE` |
| VPP bond add/detach API returns an error | Return `SAI_STATUS_FAILURE` |

## 11. Limitations and Future Work

- VPP has no per-member egress-only disable on an XOR bond, so this design models egress-disable by detaching the member from the bond. Detach removes the member from both egress distribution and ingress collection; because SONiC owns LACP and a detached member is not LACP-selected for traffic, the ingress side effect does not change effective forwarding.
- Egress transitions cause bond add/remove operations. This is bounded to LACP select/deselect events and keeps the member link (and LACP) up throughout.
- This feature depends on stored SAI object state to recover the member `LAG_ID` and `PORT_ID` when toggling bond membership.
- Additional integration coverage can be added after the related SONiC-VPP test topology supports direct validation of this attribute transition.

## 12. References

- [SONiC VPP LAG Support](vpp-lag.md)
- [SONiC VPP Platform HLD](SONICVPP-HLD.md)
- [sonic-sairedis PR #1928](https://github.com/sonic-net/sonic-sairedis/pull/1928)
