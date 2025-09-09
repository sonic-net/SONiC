# No Default VRF Route Fallback

## Table of Content

### 1. Revision
### 2. Scope
### 3. Definitions/Abbreviations
### 4. Overview
### 5. Requirements
### 6. Architecture Design
### 7. High-Level Design
### 8. SAI API
### 9. Configuration and Management
### 10. Warmboot and Fastboot Design Impact
### 11. Memory Consumption
### 12. Restrictions/Limitations
### 13. Testing Requirements/Design
### 14. Open/Action Items

## 1. Revision

| Rev | Date       | Author      | Description                                |
|-----|------------|-------------|--------------------------------------------|
| 1.0 | 2025-09-04 | Sudharsan Rajagopalan | Initial draft for VRF route fallback control |
| 2.0 | 2025-09-09 | Sudharsan Rajagopalan | Default unreachable route, global fallback knob added |

## 2. Scope

This high-level design covers changes to SONiC VRF route fallback behavior:
- By default, disables kernel VRF fallback by installing an unreachable default route in all non-default VRFs on creation (matching ASIC behavior).
- Introduces a temporary global knob to enable legacy kernel fallback, which removes the unreachable route from all non-default VRFs when set.
- Updates to CONFIG_DB schema, CLI, and show commands to manage and display this behavior.
- The global knob will be deprecated and removed in future releases.

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| VRF | Virtual Routing and Forwarding |
| FIB | Forwarding Information Base |
| SAI | Switch Abstraction Interface |
| ASIC | Application-Specific Integrated Circuit |
| BGP | Border Gateway Protocol |
| FRR | Free Range Routing |

## 4. Overview

In prior SONiC releases, Linux kernel allowed VRF lookup fallback if a route was missing in a non-default VRF, which could cause divergence from ASIC behavior and security/operational risks.

**This design ensures:**
- By default, fallback is disabled both in kernel and ASIC by installing an unreachable default route in every new non-default VRF.
- A temporary global knob (`kernel-vrf-fallback`) can be set to restore the old fallback behavior. When set, the unreachable default route is removed from all non-default VRFs, allowing the kernel to fall back as before.
- The knob is intended only for backward compatibility and will be deprecated.

> **Note:**  
> The unreachable default route added to non-default VRFs exists only in the Linux kernel routing table.  
> **It will not be added to APP_DB and will not be propagated to lower layers such as ASIC_DB, SAI, or programmed into hardware.**  
> This ensures there is no impact on hardware FIB or ASIC resources.

## 5. Requirements

### 5.1. Functional Requirements

- **FR-1**: On non-default VRF creation, add unreachable default route with high metric (for both IPv4 and IPv6).
- **FR-2**: Provide a global CLI/DB knob to enable/disable kernel VRF fallback.
- **FR-3**: When knob is **enabled**, remove unreachable default route from all non-default VRFs.
- **FR-4**: When knob is **unset** or **removed** (default), restore unreachable default route to all non-default VRFs.
- **FR-5**: CLI and show commands updated to reflect new behavior and knob state.
- **FR-6**: Configuration persists across reboots and config reloads.
- **FR-7**: Knob is deprecated and will be removed in a future release.

### 5.2. Non-Functional Requirements

- **NFR-1**: No impact on dataplane performance.
- **NFR-2**: Minimal memory and CPU overhead.
- **NFR-3**: No ASIC table consumption for unreachable routes.

### 5.3. Exemptions/Limitations

- **EX-1**: No change to kernel routing implementation (uses existing unreachable route mechanism).
- **EX-2**: Knob is global only; no per-VRF override.

## 6. Architecture Design

- **CONFIG_DB**: Stores global fallback knob status.
- **VRF Manager (vrfmgrd)**: Handles adding/removing unreachable default routes to non-default VRFs based on knob.
- **sonic-utilities**: CLI and show command updates.
- **Linux Kernel**: Manages unreachable route entries.

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│             │    │              │    │             │
│   CLI / GUI │───▶│  CONFIG_DB   │───▶│   vrfmgrd   │
└─────────────┘    └──────────────┘    └─────────────┘
                                          │
                                          ▼
                                 ┌───────────────────┐
                                 │   Linux Kernel    │
                                 │ (unreachable rt)  │
                                 └───────────────────┘
```

## 7. High-Level Design

### 7.1. Default Behavior

- On creation of any non-default VRF, vrfmgrd adds:
  - `ip route add unreachable default metric 4278198272 vrf <VRF_NAME>`
  - (For both IPv4 and IPv6.)
- This disables fallback in the kernel.
- **This unreachable default route will not be added to APP_DB and will not be propagated to lower layers.**

### 7.2. Global Fallback Knob

- New global configuration (in CONFIG_DB and CLI): `KERNEL_VRF_FALLBACK`
- When set to `enabled`:
    - vrfmgrd removes all unreachable default routes from non-default VRFs.
    - Kernel fallback is restored (legacy behavior).
- When unset/removed (default):
    - vrfmgrd ensures unreachable default routes are present.
    - Disables kernel fallback.

- **Note:** This knob is temporary and will be deprecated in future releases. Users are advised to migrate away from relying on kernel VRF fallback.

### 7.3. DB Schema Changes

**New Table: KERNEL_VRF_FALLBACK**
```json
"KERNEL_VRF_FALLBACK": {
    "status": "enabled"
}
```
- When the table/field is absent or status is not `enabled`, fallback is disabled (unreachable route present).

### 7.4. CLI and Show Command Changes

#### 7.4.1. Configuration Commands

- Enable kernel VRF fallback (removes unreachable route from all non-default VRFs):
    ```bash
    config vrf kernel-vrf-fallback enable
    ```
- Disable (default, unreachable route present in all non-default VRFs):
    ```bash
    config vrf kernel-vrf-fallback disable
    ```
  or to restore default:
    ```bash
    config vrf kernel-vrf-fallback delete
    ```
  (This will remove the KERNEL_VRF_FALLBACK entry, restoring unreachable route.)

#### 7.4.2. Show Command

- Show current fallback configuration:
    ```bash
    show vrf kernel-vrf-fallback
    ```
  **Sample Output:**
    ```
    Kernel VRF Fallback: Disabled
    (Unreachable default route present in all non-default VRFs)
    ```
    or
    ```
    Kernel VRF Fallback: Enabled
    (Unreachable default route NOT present; kernel fallback active)
    ```

### 7.5. Transition and Deprecation

- The knob is a transitional setting, will be announced as deprecated, and removed in a future release.

## 8. SAI API

- **No SAI API changes required.**
- Unreachable routes are kernel-only and not programmed in hardware.

## 9. Configuration and Management

### 9.1. CLI/YANG Model

- See section 7.4 for updated config and show commands.

### 9.2. CONFIG_DB Schema

- See section 7.3.

### 9.3. Backward Compatibility

- Default (knob unset): fallback disabled, matches ASIC.
- Knob enabled: fallback restored (legacy only).
- New deployments should not rely on kernel fallback feature.

## 10–14. (Remain as in previous version, with test cases and open items updated to reflect new default and knob.)

## 13. Testing Requirements/Design

### 13.1. Unit Tests

- **UT-CLI-1**: Validate new CLI commands.
- **UT-DB-1**: Schema validation for KERNEL_VRF_FALLBACK.
- **UT-MGR-1**: Ensure unreachable route is added/removed on knob change.

### 13.2. System Tests

- **ST-FUNC-1**: Confirm fallback is disabled by default (unreachable route present).
- **ST-FUNC-2**: Confirm fallback is enabled when knob set (unreachable route absent).
- **ST-FUNC-3**: Confirm correct behavior after config reload/warmboot.

## 14. Open/Action Items

- Implementation and deprecation notice for knob in docs.
- CLI and show command updates.
