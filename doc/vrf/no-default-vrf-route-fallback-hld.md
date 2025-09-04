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
| 1.0 | <Date>     | <Your Name> | Initial draft for VRF route fallback control |

## 2. Scope

This high-level design document covers the implementation of a configurable mechanism to disable VRF (Virtual Routing and Forwarding) route fallback behavior in SONiC. The scope includes:

- Global and per-VRF configuration of route fallback behavior
- CONFIG_DB schema changes for fallback configuration
- CLI enhancements for configuration and monitoring
- VRF Manager daemon modifications
- Support for both IPv4 and IPv6 protocols
- Configuration persistence and migration handling

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

In current implementations of SONiC, the route lookup behavior can fall back to other VRFs when a route is not found in a non-default VRF. This can lead to unintended consequences and security risks.

This document outlines a proposed solution to enhance SONiC's multi-VRF capabilities by providing a configurable mechanism to disable this fallback behavior. By introducing unreachable default routes in Linux VRF tables, the solution eliminates the need for kernel changes while allowing flexible, per-VRF and global configuration of fallback behavior.

## 5. Requirements

### 5.1. Functional Requirements

- **FR-1**: Support global configuration to disable VRF route fallback for IPv4 and IPv6
- **FR-2**: Support per-VRF override of global fallback configuration
- **FR-3**: Maintain current fallback behavior as default (backward compatibility)
- **FR-4**: Support both IPv4 and IPv6 route fallback control independently
- **FR-5**: Persist configuration across reboots and config reload operations
- **FR-6**: Provide CLI commands for configuration and monitoring
- **FR-7**: Support seamless upgrade/downgrade scenarios

### 5.2. Non-Functional Requirements

- **NFR-1**: No impact on dataplane performance
- **NFR-2**: Minimal memory footprint
- **NFR-3**: No ASIC hardware table consumption for unreachable routes
- **NFR-4**: Support existing warmboot/fastboot requirements

### 5.3. Exemptions/Limitations

- **EX-1**: Feature does not modify kernel routing behavior, only leverages existing mechanisms
- **EX-2**: Unreachable routes are software-only and not programmed into hardware

## 6. Architecture Design

The feature integrates into existing SONiC architecture without requiring changes to the core framework. The solution leverages:

- **CONFIG_DB**: For storing global and per-VRF fallback configuration
- **VRF Manager (vrfmgrd)**: For monitoring configuration and applying kernel routes
- **sonic-utilities**: For CLI interface implementation
- **Linux Kernel**: For unreachable route mechanisms

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│   CLI Commands  │───▶│    CONFIG_DB     │───▶│    vrfmgrd      │
│  (sonic-util)   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │                 │
                                               │  Linux Kernel   │
                                               │ (Unreachable    │
                                               │  Routes)        │
                                               └─────────────────┘
```

## 7. High-Level Design

### 7.1. Design Principles

- **Built-in SONiC Feature**: This is a core SONiC feature, not an Application Extension
- **Minimal Changes**: Leverages existing infrastructure with minimal modifications
- **Backward Compatibility**: Maintains current behavior unless explicitly configured
- **Kernel-Only Solution**: Uses Linux kernel unreachable routes, no hardware programming

### 7.2. Repositories Modified

- **sonic-utilities**: CLI command implementation
- **sonic-swss**: VRF Manager daemon modifications
- **sonic-buildimage**: Build configuration updates

### 7.3. Module Dependencies

- **vrfmgrd**: Core module responsible for applying configuration
- **CONFIG_DB**: Configuration storage
- **Linux iproute2**: For kernel route manipulation

### 7.4. DB Schema Changes

#### 7.4.1. CONFIG_DB Changes

**New Table: VRF_ROUTE_FALLBACK_GLOBAL**
```json
"VRF_ROUTE_FALLBACK_GLOBAL|ipv4": {
    "status": "enabled"
},
"VRF_ROUTE_FALLBACK_GLOBAL|ipv6": {
    "status": "disabled"
}
```

**Extended Table: VRF**
```json
"VRF|VrfRed": {
    "fallback": "enabled",
    "fallback_v6": "disabled"
}
```

### 7.5. Component Design

#### 7.5.1. VRF Manager Changes

**Responsibilities:**
- Monitor `VRF_ROUTE_FALLBACK_GLOBAL` and `VRF` tables
- Apply unreachable routes when fallback is disabled
- Remove unreachable routes when fallback is enabled
- Handle configuration validation and error cases

**Route Management:**
- Add: `ip route add unreachable default metric 4278198272 vrf <VRF_NAME>`
- Remove: `ip route del unreachable default vrf <VRF_NAME>`

#### 7.5.2. CLI Implementation

**Configuration Commands:**
- `config vrf route-fallback [ipv4|ipv6] [enable|disable]`
- `config vrf route-fallback [ipv4|ipv6] [enable|disable] -v <VRF_NAME>`

**Show Commands:**
- `show vrf-route-fallback`

### 7.6. Warm Reboot Impact

- Configuration persists across warm reboots
- Route reconciliation occurs during vrfmgrd startup
- No impact on warm reboot timing or data plane disruption

### 7.7. Fastboot Impact

- No additional dependencies for fastboot
- Configuration loaded during normal startup sequence

## 8. SAI API

**No SAI API changes are required for this feature.**

The unreachable routes are maintained only in the Linux kernel and are explicitly not programmed into the ASIC hardware. This design choice ensures:
- No consumption of hardware FIB resources
- No impact on dataplane performance
- No SAI object creation or modification needed

## 9. Configuration and Management

### 9.1. CLI/YANG Model Enhancements

#### 9.1.1. Configuration Commands

**Global Configuration:**
```bash
# Configure global fallback for IPv4
config vrf route-fallback ipv4 disable

# Configure global fallback for IPv6  
config vrf route-fallback ipv6 enable
```

**Per-VRF Configuration:**
```bash
# Configure fallback for specific VRF
config vrf route-fallback ipv4 disable -v VrfRed
config vrf route-fallback ipv6 enable -v VrfBlue

# Delete per-VRF override
config vrf route-fallback ipv4 -v VrfRed --delete
```

#### 9.1.2. Show Commands

```bash
# Display current fallback configuration
show vrf-route-fallback
```

**Sample Output:**
```
Protocol: ipv4
Global Fallback: Enabled

VRF Name    Fallback (Override)
----------  ---------------------
VrfRed      Disabled

Protocol: ipv6
Global Fallback: Enabled

VRF Name    Fallback (Override)
----------  ---------------------
VrfRed      Enabled
```

### 9.2. Config DB Enhancements

#### 9.2.1. Schema Changes

**New Table: VRF_ROUTE_FALLBACK_GLOBAL**
- Key: `VRF_ROUTE_FALLBACK_GLOBAL|<protocol>`
- Fields:
  - `status`: "enabled" or "disabled"

**Extended Table: VRF**
- Additional optional fields:
  - `fallback`: "enabled" or "disabled" (IPv4 override)
  - `fallback_v6`: "enabled" or "disabled" (IPv6 override)

#### 9.2.2. Backward Compatibility

- New tables and fields are optional
- Absence of configuration maintains current behavior
- Existing VRF configurations remain unaffected

#### 9.2.3. Schema Migration

**Upgrade Path:**
- No migration required - optional configuration
- Default behavior preserved until explicitly configured

**Downgrade Path:**
- Graceful degradation - new fields ignored
- Pre-downgrade cleanup script removes unreachable routes

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

## 14. Open/Action Items

### 14.1. Implementation Items

- **AI-1**: Implement CLI commands in sonic-utilities repository
- **AI-2**: Extend vrfmgrd for configuration monitoring and route management
- **AI-3**: Add CONFIG_DB schema validation
- **AI-4**: Create migration scripts for upgrade/downgrade scenarios

### 14.2. Testing Items

- **AI-5**: Develop comprehensive test suite covering all scenarios
- **AI-6**: Performance baseline establishment
- **AI-7**: Multi-platform compatibility testing
- **AI-8**: Long-term stability testing

### 14.3. Documentation Items

- **AI-9**: Update SONiC command reference documentation
- **AI-10**: Create user guide for VRF route fallback configuration
- **AI-11**: Platform-specific deployment notes
