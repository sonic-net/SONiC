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

## 10. Warmboot and Fastboot Design Impact

### 10.1. Warmboot Impact

**No negative impact on warmboot functionality:**
- Configuration persistence through CONFIG_DB
- Route reconciliation during vrfmgrd restart
- No additional stalls or IO operations in boot path
- No changes to critical boot sequence

### 10.2. Fastboot Impact

**No impact on fastboot performance:**
- Configuration loaded during normal service startup
- No additional dependencies or processing overhead
- Feature can be delayed without affecting critical services

### 10.3. Performance Analysis

- **Boot Time**: No measurable impact on boot time
- **CPU Usage**: Minimal CPU overhead during configuration changes only
- **IO Operations**: Limited to route add/delete operations
- **Critical Path**: Not in critical boot path

## 11. Memory Consumption

### 11.1. Memory Analysis

**Static Memory:**
- Configuration storage in CONFIG_DB: ~100 bytes per VRF
- Additional code in vrfmgrd: ~5KB

**Dynamic Memory:**
- No growing memory consumption during operation
- Kernel route entries: ~64 bytes per unreachable route
- No memory leaks or unbounded growth

**Total Impact:**
- Negligible memory footprint
- No memory consumption when feature is disabled
- Scales linearly with number of configured VRFs

## 12. Restrictions/Limitations

### 12.1. Design Limitations

- **L-1**: Unreachable routes affect only software-forwarded traffic
- **L-2**: Feature requires Linux kernel support for unreachable routes
- **L-3**: Does not modify BGP or other routing protocol behavior
- **L-4**: Limited to VRF route lookup control, not general routing policy

### 12.2. Platform Dependencies

- **No platform-specific dependencies**
- **Standard Linux iproute2 functionality required**
- **Compatible with all SONiC-supported platforms**

### 12.3. Scale Limitations

- **Limited by kernel route table capacity**
- **Recommended maximum: 1000 VRFs (platform dependent)**

## 13. Testing Requirements/Design

### 13.1. Unit Test Cases

#### 13.1.1 CLI Tests
- **UT-CLI-1**: Validate CLI command syntax and parameter validation
- **UT-CLI-2**: Test CONFIG_DB updates for valid configurations
- **UT-CLI-3**: Test error handling for invalid VRF names
- **UT-CLI-4**: Test show command output formatting

#### 13.1.2 CONFIG_DB Tests
- **UT-DB-1**: Schema validation for global fallback entries
- **UT-DB-2**: Schema validation for per-VRF fallback entries
- **UT-DB-3**: Invalid configuration handling
- **UT-DB-4**: Configuration persistence testing

#### 13.1.3 VRF Manager Tests
- **UT-MGR-1**: Configuration change monitoring
- **UT-MGR-2**: Route addition/removal logic
- **UT-MGR-3**: IPv4 and IPv6 handling independently
- **UT-MGR-4**: Error handling for route operations

### 13.2. System Test Cases

#### 13.2.1 Functional Tests
- **ST-FUNC-1**: Verify route fallback disabled with unreachable route present
- **ST-FUNC-2**: Verify per-VRF override of global setting
- **ST-FUNC-3**: Verify IPv4 and IPv6 independent operation
- **ST-FUNC-4**: Test with multiple VRFs and mixed configurations

#### 13.2.2 Integration Tests  
- **ST-INT-1**: End-to-end CLI to kernel route verification
- **ST-INT-2**: Configuration persistence across reboots
- **ST-INT-3**: Config reload testing
- **ST-INT-4**: Warm reboot with feature enabled

#### 13.2.3 Upgrade/Downgrade Tests
- **ST-UPG-1**: Seamless upgrade from pre-feature version
- **ST-UPG-2**: Configuration migration validation
- **ST-UPG-3**: Graceful downgrade with cleanup
- **ST-UPG-4**: Schema validation across versions

#### 13.2.4 Performance Tests
- **ST-PERF-1**: Boot time impact measurement
- **ST-PERF-2**: Memory consumption validation
- **ST-PERF-3**: Route operation performance
- **ST-PERF-4**: Scale testing with multiple VRFs

#### 13.2.5 Negative Tests
- **ST-NEG-1**: Invalid configuration handling
- **ST-NEG-2**: Non-existent VRF handling
- **ST-NEG-3**: Kernel route operation failures
- **ST-NEG-4**: Configuration corruption recovery

### 13.3. Warmboot/Fastboot Testing

- **Verify no impact on existing warmboot/fastboot timings**
- **Confirm zero data plane disruption during configuration changes**
- **Test route reconciliation after warmboot**
- **Validate configuration persistence across boot cycles**
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
