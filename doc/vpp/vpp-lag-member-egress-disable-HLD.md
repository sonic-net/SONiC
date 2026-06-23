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

## 2. Scope

This document describes how SONiC-VPP handles `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` for LAG members in the VPP-backed virtual switch path.

The design covers:

- Creating a LAG member while egress is disabled.
- Dynamically disabling egress on an existing LAG member.
- Dynamically enabling egress on a previously disabled LAG member.
- Keeping the VPP member port admin state aligned with SONiC SAI egress-disable state.
- Preserving the existing VPP bond membership and delayed LCP/tap creation behavior for VPP LAGs.

This document is a focused extension of the broader [SONiC VPP LAG Support](vpp-lag.md) HLD.

## 3. Definitions

| Term | Meaning |
|---|---|
| LAG | Link Aggregation Group, exposed in SONiC as a PortChannel |
| LAG member | A physical port that belongs to a LAG |
| Bond | VPP BondEthernet interface used to model a SONiC PortChannel |
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

## 5. Problem Statement

Before this feature, SONiC-VPP created and removed VPP bond members, but it did not react to updates of `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE`.

That caused two gaps:

1. If a LAG member was created with egress disabled, SONiC-VPP still brought it up as an active egress member of the VPP bond.
2. If SONiC later changed the egress-disable state of a LAG member, the VPP member port admin state did not change accordingly.

As a result, SONiC control-plane state and VPP dataplane state could diverge.

## 6. Goals and Non-Goals

### Goals

- Honor `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` in the VPP dataplane.
- Keep disabled LAG members out of VPP bond egress selection.
- Restore the member to active forwarding when egress is re-enabled.
- Treat a missing stored `EGRESS_DISABLE` attribute as the SAI default value, `false`.
- Avoid unnecessary VPP operations when the requested egress-disable state does not change.
- Keep the existing VPP bond member lifecycle and delayed LCP/tap creation behavior unchanged.

### Non-Goals

- No change to SONiC CLI, Config DB, APP DB, or Orchagent behavior.
- No change to LACP protocol handling.
- No change to VPP bond mode or load-balancing algorithm selection.
- No support for additional SAI LAG member attributes beyond this feature.
- No redesign of the existing LAG LCP/tap and `tc` redirect model.

## 7. High Level Design

### 7.1 Design Summary

SONiC-VPP maps the SAI egress-disable state to the VPP member port admin state:

| SAI egress-disable state | VPP action |
|---|---|
| `true` | Keep the member in the VPP bond, but set its VPP member port admin state down |
| `false` | Keep the member in the VPP bond and set its VPP member port admin state up |

This keeps the object lifecycle and dataplane membership stable, and uses admin state to reflect egress eligibility:

- The SAI LAG member object and its VPP bond membership follow the normal create/remove lifecycle, unchanged by this feature.
- The member port's VPP admin state reflects whether the member is eligible for egress traffic.

VPP does not expose an egress-only disable flag on a bond member, but a bond does not select a down member for egress. This design therefore models `EGRESS_DISABLE=true` by setting the member port's VPP interface admin state down, leaving the member attached to the bond. Re-enabling sets the member port admin state back up. Because the member stays a VPP bond member across both transitions, this avoids repeated bond add/remove churn, and the bond's LCP/tap pairing and MAC are unaffected. LACP ownership and packet punt/inject behavior remain unchanged: SONiC continues to run LACP, and this feature only changes the member port admin state.

Setting the member port down stops ingress on that member as well, which is broader than the strict egress-only scope of `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE`. This is acceptable because SONiC continues to own LACP: a member that SONiC has marked egress-disabled is not selected for traffic distribution at the control-plane level, so also stopping its ingress does not change the member's effective forwarding behavior.

#### Effective Admin State

The member port's VPP interface admin state is also driven by the port's own `SAI_PORT_ATTR_ADMIN_STATE`. Two SAI inputs therefore share one VPP knob, so SONiC-VPP programs the *effective* admin state rather than letting each writer overwrite the other:

```text
vpp_admin_up = port_admin_state AND NOT egress_disable
```

- The egress-disable path computes the effective state from the requested egress-disable value and the port's stored admin state.
- The port admin-state path (`SAI_PORT_ATTR_ADMIN_STATE`) computes the effective state from the requested admin state and the port's current egress-disable contribution.

This guarantees that an egress-disabled member stays down even if its port admin state is later set up, and that an administratively down port stays down even if egress is enabled. When a port's admin state has never been explicitly set, it is treated as up, matching the existing behavior where an active member port comes up when added to the bond.

### 7.2 Create Path

When a LAG member is created:

1. Store the LAG member in the normal SAI-VPP object state.
2. Add the member to the VPP bond, as in the base LAG design.
3. Ensure LCP/tap setup for the bond (created on the first member, as before).
4. Check whether `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` is present and set to `true`.
5. If egress is disabled, set the member port's VPP admin state down.

`create_internal()` records the SAI object in the virtual switch state, and `vpp_create_lag_member()` programs the VPP bond membership as before. For an initially disabled member, the member port is then set down so it is not used for egress.

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
set member port admin state down
```

### 7.3 Set Path

`SwitchVpp::set()` routes `SAI_OBJECT_TYPE_LAG_MEMBER` updates to `SwitchVpp::setLagMember()`.

`setLagMember()` handles only `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` specially. All other attributes continue to use the existing generic `set_internal()` path.

The set path follows this order:

1. Validate that the LAG member object exists.
2. Read the current stored `EGRESS_DISABLE` value.
3. Decide whether the requested value requires no action, setting the member down, or setting it up.
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
| `NONE` | No member admin state change is needed |
| `DISABLE` | Set the member port admin state down |
| `ENABLE` | Set the member port admin state up |

If the current stored attribute is missing, SONiC-VPP treats it as the SAI default `false`.

### 7.5 Disable Egress (Set Member Down)

When egress is disabled:

```text
set EGRESS_DISABLE=true
    |
    v
set member port admin state down
    |
    v
update stored SAI attr to true
```

The SAI object and VPP bond membership remain unchanged. Only the member port's VPP admin state changes, computed as `port_admin_state AND NOT egress_disable` (see [Effective Admin State](#effective-admin-state)). With egress disabled this resolves to down, so the bond stops selecting the member for egress.

### 7.6 Enable Egress (Set Member Up)

When egress is re-enabled:

```text
set EGRESS_DISABLE=false
    |
    v
set member port admin state up
    |
    v
update stored SAI attr to false
```

Enabling reads the member's stored `SAI_LAG_MEMBER_ATTR_PORT_ID` to locate the VPP member port, clears its egress-disable contribution, and reprograms the effective admin state `port_admin_state AND NOT egress_disable`. With egress enabled this resolves to the port's own admin state. The member is already attached to the VPP bond and the LCP/tap pair already exists, so no bond membership or LCP/tap change is required.

### 7.7 LCP/Tap Handling

This feature does not change LCP/tap handling. Because members remain attached to the VPP bond regardless of egress-disable state, the existing base LAG behavior is preserved without modification:

- The bond LCP/tap pair is created when the first member is added (the delayed-tap behavior from the base design).
- Egress-disable and egress-enable transitions do not create or remove the LCP/tap pair.
- The LCP/tap pair is removed only by normal LAG teardown.

`vpp_ensure_lag_lcp()` is still called from the create path and creates the LCP/tap pair only if it has not already been created for the LAG. Toggling member admin state never reaches this helper.

### 7.8 Remove Path and Lifecycle Edge Cases

The LAG member remove path is not redesigned by this feature. Because egress-disable no longer changes VPP bond membership, a disabled member is still a normal VPP bond member, so it follows the same remove path as an enabled member. The expected lifecycle behavior is:

| Case | Expected behavior |
|---|---|
| Remove a member (enabled or disabled) | Remove it from the VPP bond, then remove the SAI object state, exactly as in the base design |
| Disable a member (including the last enabled member) | Set the effective member port state down; keep it in the VPP bond and keep all LCP/tap state |
| Re-enable a member | Clear the egress-disable contribution and restore the effective member port state; no bond membership or LCP/tap change |

When a member that was egress-disabled is removed, the remove path clears its egress-disable contribution and restores the port to its own `SAI_PORT_ATTR_ADMIN_STATE` before the SAI object is deleted. This prevents the physical port from being left forced down in VPP after it is no longer a LAG member.

The earlier regression case where a disabled member could already be absent from the VPP bond when the remove operation arrives no longer applies under this design, because disabling a member leaves it attached to the bond.

### 7.9 Alternatives Considered

Two options were evaluated for modeling `EGRESS_DISABLE=true`:

| Option | Description | Decision |
|---|---|---|
| Set the member port admin state down | Keep the member attached to the VPP bond and toggle its interface admin state down on disable and up on enable | **Chosen.** A down member is not selected for bond egress, so this honors egress-disable while avoiding repeated bond add/remove churn and leaving LCP/tap pairing and bond MAC untouched. |
| Detach the member from the VPP bond | Remove the member from the bond on disable and add it back on enable | **Not used.** Adds bond add/remove churn on every transition, must reconstruct member attributes and re-evaluate LCP/tap on re-add, and introduces a remove-while-already-absent edge case. |

Setting the member down keeps the bond membership stable across egress-disable transitions, at the cost of also stopping ingress on the member (see [§7.1](#71-design-summary)). Because SONiC owns LACP, that ingress side effect does not change the member's effective forwarding behavior.

## 8. Behavior Matrix

| Current stored attr exists? | Current value | Requested value | VPP action | Stored state update |
|---|---|---|---|---|
| Yes | `false` | `false` | None | Set attr to `false` |
| Yes | `false` | `true` | Reprogram effective port state (down) | Set attr to `true` after the update succeeds |
| Yes | `true` | `false` | Reprogram effective port state (up if port admin up) | Set attr to `false` after the update succeeds |
| Yes | `true` | `true` | None | Set attr to `true` |
| No | default `false` | `false` | None | Set attr to `false` |
| No | default `false` | `true` | Reprogram effective port state (down) | Set attr to `true` after the update succeeds |

The "effective port state" is `port_admin_state AND NOT egress_disable` (see [Effective Admin State](#effective-admin-state)). Enabling egress resolves to the port's own admin state, not unconditionally up.

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
set member port admin state down
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
vpp_set_lag_member_egress_disable(true)  [set member port down]
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
vpp_set_lag_member_egress_disable(false)  [set member port up]
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
| VPP set-member-down fails | Return the VPP failure status and do not update stored `EGRESS_DISABLE` state |
| VPP set-member-up fails | Return the VPP failure status and do not update stored `EGRESS_DISABLE` state |
| Stored `PORT_ID` missing while toggling member state | Return `SAI_STATUS_FAILURE` |
| Stored `PORT_ID` has the wrong object type | Return `SAI_STATUS_FAILURE` |
| Member port VPP hardware interface lookup fails | Return `SAI_STATUS_FAILURE` |
| Bond interface name lookup fails during LCP setup on the create path | Return `SAI_STATUS_FAILURE` |
| VPP interface set-state API returns an error | Return `SAI_STATUS_FAILURE` |

## 11. Limitations and Future Work

- This design models egress disable by setting the member port's VPP interface admin state down. It does not use a VPP-native per-member egress-only disable flag, so a disabled member's ingress is also stopped.
- This feature depends on stored SAI object state to recover the member `PORT_ID` when toggling the member port admin state.
- Additional integration coverage can be added after the related SONiC-VPP test topology supports direct validation of this attribute transition.

## 12. References

- [SONiC VPP LAG Support](vpp-lag.md)
- [SONiC VPP Platform HLD](SONICVPP-HLD.md)
- [sonic-sairedis PR #1928](https://github.com/sonic-net/sonic-sairedis/pull/1928)

