# No Default VRF Route Fallback

## Table of Contents

1. [Revision](#1-revision)
2. [Scope](#2-scope)
3. [Definitions and Abbreviations](#3-definitions-and-abbreviations)
4. [Overview](#4-overview)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
8. [SAI API](#8-sai-api)
9. [Configuration and Management](#9-configuration-and-management)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions and Limitations](#12-restrictions-and-limitations)
13. [Testing Requirements and Design](#13-testing-requirements-and-design)
14. [Open and Action Items](#14-open-and-action-items)

## 1. Revision

| Rev | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2025-09-04 | Sudharsan Rajagopalan | Initial draft for VRF route fallback control |
| 2.0 | 2025-09-09 | Sudharsan Rajagopalan | Added default unreachable routes and the global fallback knob |
| 3.0 | 2026-07-02 | Sudharsan Rajagopalan | Clarified the kernel-only scope and CONFIG_DB-only management; removed the CLI design |

## 2. Scope

This HLD changes only Linux VRF route lookup for traffic processed by the host kernel, including VRF-bound locally originated traffic and packets forwarded in software. It does not add or modify hardware routes, SAI objects, or ASIC forwarding behavior.

- By default, `vrfmgrd` disables legacy Linux routing-policy database (RPDB) fall-through by installing managed IPv4 and IPv6 unreachable default routes in each applicable non-default Linux VRF table.
- A temporary global CONFIG_DB setting can remove those routes, restoring fallback in the Linux kernel route-lookup path, including VRF-bound local output and software-forwarded packets, by permitting RPDB lookup to continue to later rules and tables.
- This HLD defines the CONFIG_DB schema and `vrfmgrd` behavior. It does not define a feature-specific configuration CLI or show command.
- The global compatibility setting will be deprecated and removed in a future release.

## 3. Definitions and Abbreviations

| Term | Definition |
|---|---|
| VRF | Virtual Routing and Forwarding |
| FIB | Forwarding Information Base |
| RPDB | Linux routing-policy database |
| SAI | Switch Abstraction Interface |
| ASIC | Application-Specific Integrated Circuit |
| BGP | Border Gateway Protocol |
| FRR | FRRouting |
| FPM | Forwarding Plane Manager protocol used between FRR zebra and `fpmsyncd` |

## 4. Overview

Linux VRF devices use an `l3mdev` RPDB rule to select the routing table associated with the VRF. If that table has no matching route, lookup can continue to later RPDB rules and routing tables, including the default routing table. This legacy behavior can allow kernel-routed traffic to leave the intended VRF.

The [Linux VRF documentation](https://docs.kernel.org/networking/vrf.html) recommends an unreachable default route with metric `4278198272`. The route makes an otherwise-unmatched lookup terminal while allowing more-specific routes, or a usable default route with a lower metric, to take precedence. FRR interprets the metric as administrative distance and priority `[255/8192]`.

This feature changes Linux route lookup only. It neither enables nor disables fallback in an ASIC. Hardware behavior remains unchanged and is determined by the platform's existing SAI and ASIC implementation. On platforms whose hardware already terminates a route miss within the selected virtual router, this feature aligns the Linux route-miss result with that behavior.

The unreachable defaults are installed directly in the Linux kernel. FRR may observe kernel route notifications, so `fpmsyncd` must filter both add and delete notifications for `RTN_UNREACHABLE` routes before changing APP_DB. Consequently, the managed sentinel routes are not translated into ASIC_DB or SAI route objects and do not consume hardware FIB resources.

## 5. Requirements

### 5.1. Functional Requirements

- **FR-1**: When kernel fallback is not enabled, ensure that managed IPv4 and IPv6 unreachable default routes with metric `4278198272` are present in every applicable non-default Linux VRF table.
- **FR-2**: Provide one global CONFIG_DB setting that controls both IPv4 and IPv6 behavior for all applicable non-default VRFs.
- **FR-3**: When `status` is `enabled`, remove only the managed sentinel routes from existing non-default VRFs and do not add them to newly created non-default VRFs.
- **FR-4**: When `status` is `disabled`, the CONFIG_DB entry is deleted, or the entry is absent, ensure that the managed sentinel routes are present in existing and newly created non-default VRFs.
- **FR-5**: Read the effective global state before processing VRF creation events and reconcile all existing non-default VRFs at startup, after a configuration change, and after `vrfmgrd` restarts.
- **FR-6**: Keep the managed sentinel routes out of APP_DB, ASIC_DB, SAI, and the hardware FIB. `fpmsyncd` must ignore their add and delete notifications before mutating APP_DB, so removing a sentinel cannot remove or alter a real unicast default route.
- **FR-7**: Preserve an explicitly configured compatibility setting across reboot and configuration reload through the standard persistent CONFIG_DB workflow.
- **FR-8**: Deprecate and remove the compatibility setting in a future release.

### 5.2. Non-Functional Requirements

- **NFR-1**: Do not change ASIC or hardware forwarding behavior or performance.
- **NFR-2**: Make route reconciliation idempotent and proportional to the number of applicable VRFs.
- **NFR-3**: Do not consume ASIC route-table resources for the managed sentinel routes.

### 5.3. Exemptions and Limitations

- **EX-1**: The setting is global; there is no per-VRF override.
- **EX-2**: One setting controls both IPv4 and IPv6; the address families cannot be configured independently.
- **EX-3**: A feature-specific CLI, show command, and management API are outside the scope of this HLD.
- **EX-4**: SAI and hardware fallback behavior are outside the scope of this HLD.
- **EX-5**: The feature applies to non-default Linux VRFs managed through the `vrfmgrd` lifecycle. Specialized VRF-like objects outside that lifecycle retain their existing handling.

## 6. Architecture Design

- **CONFIG_DB** stores the global compatibility setting.
- **VRF Manager (`vrfmgrd`)** caches the effective setting and reconciles managed sentinel routes in the applicable Linux VRF tables.
- **Linux Kernel** performs the affected route lookup and maintains the unreachable route entries.
- **FRR zebra and `fpmsyncd`** may observe kernel route notifications. `fpmsyncd` filters `RTN_UNREACHABLE` additions and deletions before they can change APP_DB or the hardware programming pipeline.

```text
Persistent CONFIG_DB writer
             |
             v
CONFIG_DB (KERNEL_VRF_FALLBACK|GLOBAL)
             |
             v
          vrfmgrd  ------->  Linux VRF routing tables
                                  |
                                  | RTN_UNREACHABLE notification
                                  v
                           FRR zebra / FPM
                                  |
                                  v
                           fpmsyncd filter
                                  X
                      APP_DB / ASIC_DB / SAI / ASIC
```

## 7. High-Level Design

### 7.1. Effective State

The default effective state is `disabled`, meaning that legacy Linux RPDB fall-through is disabled. Only the explicit value `enabled` selects the compatibility behavior.

| CONFIG_DB state | `vrfmgrd` action | Linux route-lookup result | Hardware result |
|---|---|---|---|
| Entry absent, entry deleted, or `status=disabled` | Ensure both managed sentinel routes are present | An otherwise-unmatched lookup terminates in the selected VRF table | Unchanged |
| `status=enabled` | Remove both managed sentinel routes and skip them for new VRFs | An otherwise-unmatched lookup may continue to later RPDB rules and tables | Unchanged |

Removing the unreachable defaults permits legacy fall-through; it does not guarantee reachability. A later RPDB rule and matching route must exist for lookup to succeed.

### 7.2. Route Lifecycle and Ownership

At startup, `vrfmgrd` reads and caches the effective global state before it processes VRF creation events. It then enumerates existing applicable non-default VRFs and reconciles them with that state.

When the effective state is `disabled`, `vrfmgrd` uses idempotent route replacement for each VRF table:

```bash
ip route replace table <TABLE_ID> unreachable default metric 4278198272
ip -6 route replace table <TABLE_ID> unreachable default metric 4278198272
```

When the effective state changes to `enabled`, `vrfmgrd` removes the exact managed sentinel routes:

```bash
ip route del table <TABLE_ID> unreachable default metric 4278198272
ip -6 route del table <TABLE_ID> unreachable default metric 4278198272
```

The managed sentinel identity is the tuple of address family, VRF table, route type `unreachable`, default prefix, and metric `4278198272`. If an exact matching route already exists when the effective state is `disabled`, `vrfmgrd` adopts it as the managed sentinel instead of creating a duplicate. An operator cannot independently own an identical route while this feature manages the VRF; selecting `status=enabled` removes the adopted match. Routes that differ in type, prefix, or metric, including any unicast default, are not managed and must be preserved. An already-present route during replacement and an already-absent route during deletion are treated as success.

For a VRF created while `status=enabled`, `vrfmgrd` does not add either managed sentinel. When the CONFIG_DB entry is deleted or changed to `disabled`, `vrfmgrd` adds or adopts both sentinels in all existing applicable VRFs and applies the same rule to future VRFs.

### 7.3. CONFIG_DB Schema

**New entry: `KERNEL_VRF_FALLBACK|GLOBAL`**

```json
{
    "KERNEL_VRF_FALLBACK": {
        "GLOBAL": {
            "status": "enabled"
        }
    }
}
```

| Field | Allowed values | Default | Description |
|---|---|---|---|
| `status` | `enabled`, `disabled` | `disabled` | `enabled` permits legacy Linux RPDB fall-through; `disabled` installs the managed sentinel routes |

- If the table, `GLOBAL` key, or `status` field is absent, the effective state is `disabled`.
- `GLOBAL` is the only valid key in this table; the schema rejects additional keys.
- Deleting the entry restores the default `disabled` state.
- The CONFIG_DB schema rejects values other than `enabled` and `disabled`. As a defensive measure, `vrfmgrd` treats an unrecognized value as `disabled` and logs an error.
- The CONFIG_DB schema and validation updates are in scope. No feature-specific configuration CLI or show command is defined.

### 7.4. APP_DB and Hardware Isolation

`vrfmgrd` installs the managed sentinel routes directly in the kernel and does not write them to APP_DB. Because FRR zebra may report kernel routes through FPM, `fpmsyncd` must inspect route type before any APP_DB operation and ignore both `RTM_NEWROUTE` and `RTM_DELROUTE` notifications whose route type is `RTN_UNREACHABLE`. Existing add-path filtering is retained; the delete path must provide the equivalent guard.

Removal of a managed sentinel must not delete an APP_DB unicast default for the same prefix. Unit and integration tests must cover coexistence with a real IPv4 or IPv6 default route.

No SAI object or ASIC route is created, changed, or removed by this feature.

### 7.5. Transition and Deprecation

The global setting is a temporary compatibility mechanism. It will be documented as deprecated and removed in a future release. New deployments must not depend on Linux VRF fall-through.

Before a warm or in-service rollback to software that does not implement this feature, the rollback procedure must remove the managed IPv4 and IPv6 sentinel routes from retained VRF tables and remove the persisted `KERNEL_VRF_FALLBACK|GLOBAL` entry. A cold rollback that deletes and recreates the VRF devices naturally removes their old routing tables, but the persisted CONFIG_DB entry must still be removed or migrated.

## 8. SAI API

- **No SAI API changes are required.**
- This feature does not create a SAI route, change `SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID`, or alter a SAI virtual-router fallback setting.
- This HLD makes no platform-independent assertion that ASIC VRF fallback is present or absent. Existing hardware behavior is unchanged and outside the feature scope.

## 9. Configuration and Management

### 9.1. Persistent Configuration

The setting is supplied through the standard persistent CONFIG_DB workflow, such as a persistent configuration patch or `config_db.json`, and is loaded during normal CONFIG_DB initialization. A direct in-memory Redis write alone is not considered persistent configuration.

No feature-specific SONiC CLI, show command, or management API is introduced. Kernel state can be inspected with the existing Linux commands `ip route show vrf <VRF_NAME>` and `ip -6 route show vrf <VRF_NAME>`.

### 9.2. Backward Compatibility

- Default, with the entry absent or `status=disabled`: legacy fall-through is disabled in the kernel route-lookup path; ASIC programming and hardware lookup behavior are unchanged.
- Knob enabled: fallback is restored in the kernel forwarding path only. In this HLD, that means the Linux kernel route-lookup path for VRF-bound local output and software-forwarded packets. The managed sentinels are removed, permitting legacy RPDB fall-through when a later matching route exists; ASIC programming and hardware lookup behavior are unchanged.
- Existing deployments that temporarily require the prior kernel behavior can persist `status=enabled` during migration.
- New deployments must not rely on kernel VRF fallback.

## 10. Warmboot and Fastboot Design Impact

### 10.1. Warmboot Impact

- `vrfmgrd` reads the effective CONFIG_DB state before reconciling non-default VRFs.
- Reconciliation is idempotent, so retained kernel state can be corrected after `vrfmgrd` restarts or warmboot completes.
- The feature adds no APP_DB, ASIC_DB, SAI, or hardware replay state.
- Kernel-routed reachability can change when the compatibility setting changes, as intended; hardware-forwarded traffic is unchanged.

### 10.2. Fastboot Impact

- The setting is loaded through the normal CONFIG_DB startup path.
- `vrfmgrd` reconciles the applicable VRFs after their Linux devices and tables exist.
- No additional hardware programming dependency is introduced.

### 10.3. Performance Analysis

- A steady-state VRF adds at most two kernel sentinel routes.
- A global state transition performs at most two route operations per applicable VRF.
- There is no ASIC route operation or hardware FIB impact.

## 11. Memory Consumption

- CONFIG_DB stores one small global entry only when the compatibility setting is explicitly present.
- In the default `disabled` state, the Linux kernel stores one IPv4 and one IPv6 unreachable default per applicable non-default VRF.
- Kernel route memory and transient reconciliation state scale linearly with the number of applicable VRFs.
- The feature consumes no ASIC FIB resources.

## 12. Restrictions and Limitations

### 12.1. Design Limitations

- **L-1**: The unreachable routes affect Linux route lookup, including VRF-bound locally generated traffic and packets forwarded in software. They do not affect packets forwarded entirely by the ASIC.
- **L-2**: The setting is global and dual-stack; there is no per-VRF or per-address-family override.
- **L-3**: Removing the sentinel routes only permits later RPDB lookup. It does not guarantee that a later rule or route provides reachability.
- **L-4**: There is no BGP configuration or routing-protocol code change. The kernel route visibility and FPM filtering behavior remain subject to the tests in Section 13.
- **L-5**: The design relies on `fpmsyncd` filtering `RTN_UNREACHABLE` additions and deletions before APP_DB mutation and preserving any coexisting unicast default route.

### 12.2. Platform Dependencies

- Linux VRF and `l3mdev` RPDB support are required.
- `iproute2` must support IPv4 and IPv6 unreachable routes in a VRF table.
- Existing SAI and ASIC behavior is unchanged; no platform-specific SAI capability is required by this feature.

### 12.3. Scale Characteristics

- The default state adds two kernel routes per applicable non-default VRF.
- Startup and global-state reconciliation are linear in the number of applicable VRFs.

## 13. Testing Requirements and Design

### 13.1. Unit Tests

#### 13.1.1. CONFIG_DB Tests

- **UT-DB-1**: Validate `KERNEL_VRF_FALLBACK|GLOBAL` with `status=enabled` and `status=disabled`.
- **UT-DB-2**: Reject an invalid `status` value and a malformed entry.
- **UT-DB-3**: Verify that an absent or deleted entry produces the default `disabled` state.
- **UT-DB-4**: Verify serialization and reload of the persistent global entry.

#### 13.1.2. VRF Manager Tests

- **UT-MGR-1**: Verify that startup reads the global state before reconciling existing VRFs.
- **UT-MGR-2**: Verify IPv4 and IPv6 route replacement when the state is absent or `disabled`.
- **UT-MGR-3**: Verify exact route deletion when the state changes to `enabled` and that a VRF created while enabled receives no sentinel route.
- **UT-MGR-4**: Verify that entry deletion restores both routes in every existing applicable VRF.
- **UT-MGR-5**: Verify idempotent replacement, tolerant deletion of an already-absent route, and recovery after a route-operation failure.
- **UT-MGR-6**: Verify that specialized VRF-like objects outside the `vrfmgrd` lifecycle retain their existing behavior.

#### 13.1.3. FPM and RouteSync Tests

- **UT-FPM-1**: Verify that IPv4 and IPv6 `RTN_UNREACHABLE` add and delete notifications are ignored before APP_DB mutation.
- **UT-FPM-2**: Verify that deleting a managed sentinel does not delete a coexisting APP_DB unicast default.
- **UT-FPM-3**: Verify that no ASIC_DB or SAI route operation is generated for the sentinel routes.

### 13.2. System Tests

#### 13.2.1. Functional Tests

- **ST-FUNC-1**: With the entry absent, verify that both sentinel routes are present and an otherwise-unmatched Linux VRF lookup is terminal.
- **ST-FUNC-2**: With `status=enabled`, verify that both sentinel routes are absent and RPDB fall-through is permitted; verify successful fallback only when a later matching route exists.
- **ST-FUNC-3**: Verify the same global behavior for IPv4 and IPv6 across multiple non-default VRFs.
- **ST-FUNC-4**: Verify that more-specific routes and real default routes with a lower metric take precedence over the sentinel routes.
- **ST-FUNC-5**: Verify both VRF-bound locally originated traffic and packets forwarded in software.

#### 13.2.2. Integration Tests

- **ST-INT-1**: Verify the end-to-end CONFIG_DB-to-kernel path for enable, disable, and entry deletion.
- **ST-INT-2**: Verify that no sentinel route appears in APP_DB or ASIC_DB and that hardware forwarding state is unchanged.
- **ST-INT-3**: Verify coexistence with a real IPv4 and IPv6 default route while toggling the setting.
- **ST-INT-4**: Verify a new VRF created while enabled, a VRF deleted during reconciliation, and multiple existing VRFs during a global transition.
- **ST-INT-5**: Verify behavior after `vrfmgrd` restart, configuration reload, warmboot, and fastboot.

#### 13.2.3. Upgrade and Downgrade Tests

- **ST-UPG-1**: Upgrade with no compatibility entry and verify installation of the default sentinel routes.
- **ST-UPG-2**: Upgrade with `status=enabled` and verify preservation of the legacy kernel behavior.
- **ST-UPG-3**: Verify explicit sentinel and persisted CONFIG_DB-entry cleanup during a warm or in-service downgrade.
- **ST-UPG-4**: Verify that a cold downgrade that recreates VRF devices leaves no stale sentinel route or unsupported CONFIG_DB entry.
- **ST-UPG-5**: Verify adoption of an exact pre-existing sentinel when the feature starts in the default `disabled` state.

#### 13.2.4. Performance and Scale Tests

- **ST-PERF-1**: Measure startup and reconciliation time with the platform's supported VRF scale.
- **ST-PERF-2**: Validate linear kernel route and memory growth.
- **ST-PERF-3**: Confirm that no ASIC route operations are generated during reconciliation.

#### 13.2.5. Negative Tests

- **ST-NEG-1**: Reject invalid CONFIG_DB values and malformed entries.
- **ST-NEG-2**: Verify convergence when VRFs are created or deleted during global-state reconciliation.
- **ST-NEG-3**: Inject kernel route-operation failures and verify error reporting and later reconciliation.
- **ST-NEG-4**: Verify that toggling the setting preserves every route that does not exactly match the managed sentinel identity, including a unicast default route.

### 13.3. Warmboot and Fastboot Testing

- Verify persistence of an explicit `enabled` or `disabled` state across boot cycles.
- Verify kernel route reconciliation after warmboot and service restart.
- Confirm that the sentinel routes remain absent from APP_DB and ASIC_DB after reconciliation.
- Confirm that configuration changes affect only kernel-routed traffic and do not disrupt ASIC or hardware forwarding.

## 14. Open and Action Items

- Implement the CONFIG_DB schema and `vrfmgrd` handling for the temporary compatibility setting.
- Add regression coverage for `fpmsyncd` filtering and preservation of coexisting unicast default routes.
- Document the compatibility setting's deprecation, persistent configuration path, and rollback cleanup procedure.
