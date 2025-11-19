# SONiC Fast Link-Up

## High Level Design document

## Table of contents

- [Revision](#revision)
- [About this manual](#about-this-manual)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [List of figures](#list-of-figures)
- [List of tables](#list-of-tables)
- [1 Introduction](#1-introduction)
  - [1.1 Feature overview](#11-feature-overview)
  - [1.2 Requirements](#12-requirements)
    - [1.2.1 Functionality](#121-functionality)
    - [1.2.2 Command interface](#122-command-interface)
    - [1.2.3 Error handling](#123-error-handling)
    - [1.2.4 Event logging](#124-event-logging)
- [2 Design](#2-design)
  - [2.1 Overview](#21-overview)
  - [2.2 Capability discovery](#22-capability-discovery)
  - [2.3 Configuration model](#23-configuration-model)
  - [2.4 SAI API](#24-sai-api)
  - [2.5 Orchestration agent](#25-orchestration-agent)
    - [2.5.1 Switch orch](#251-switch-orch)
    - [2.5.2 Ports orch](#252-ports-orch)
  - [2.6 DB schema](#26-db-schema)
    - [2.6.1 Config DB](#261-config-db)
    - [2.6.2 State DB](#262-state-db)
    - [2.6.3 Data sample](#263-data-sample)
    - [2.6.4 Configuration sample](#264-configuration-sample)
    - [2.6.5 Initial configuration](#265-initial-configuration)
    - [2.6.6 Configuration migration](#266-configuration-migration)
  - [2.7 Flows](#27-flows)
    - [2.7.1 Config section](#271-config-section)
    - [2.7.2 Show section](#272-show-section)
  - [2.8 CLI](#28-cli)
    - [2.8.1 Command structure](#281-command-structure)
    - [2.8.2 Usage examples](#282-usage-examples)
  - [2.9 YANG model](#29-yang-model)
  - [2.10 Warm/Fast boot](#210-warmfast-boot)
- [3 Test plan](#3-test-plan)
  - [3.1 Unit tests via VS](#31-unit-tests-via-vs)
  - [3.2 Data plane tests via PTF](#32-data-plane-tests-via-ptf)

## Revision

| Rev | Date       | Author            | Description |
|:---:|:----------:|:-----------------:|:------------|
| 0.9 | 2025-11-19 | Fast Link-Up Team | Draft       |
| 1.0 | TBD        | Fast Link-Up Team | GA          |

## Scope

This document describes the high level design of the Fast Link-Up feature in SONiC.


## List of figures

[Figure 1: Architecture overview](#figure-1-architecture-overview)  
[Figure 2: Global configuration flow](#figure-2-global-configuration-flow)  
[Figure 3: Per-interface flow](#figure-3-per-interface-flow)  
[Figure 4: Link recovery state machine](#figure-4-link-recovery-state-machine)


# 1 Introduction

## 1.1 Feature overview

Fast Link-Up accelerates link bring-up and recovery on platforms that support a dedicated SAI port attribute for fast link-up. The feature is capability-gated; configuration is accepted only when the platform advertises support and ranges.

Key points:
1. Global parameters tune the behavior: polling interval, guard time, BER threshold.
2. Per-port enable/disable controls whether Fast Link-Up is attempted on that port.
3. If at guard expiry link quality exceeds configured BER threshold, system falls back to the regular link-up path.

## 1.2 Requirements

### 1.2.1 Functionality

The feature supports the following functionality:
1. Global Fast Link-Up configuration in `SWITCH_FAST_LINKUP|GLOBAL` (`polling_time`, `guard_time`, `ber_threshold`).
2. Per-port enable/disable via `PORT|<ifname>:fast_linkup`.
3. Capability and range discovery via `STATE_DB:SWITCH_CAPABILITY|switch`.
4. Safe fallback to regular link-up when conditions are not met.

### 1.2.2 Command interface

Config section:
- `config switch-fast-linkup global [--polling-time <sec>] [--guard-time <sec>] [--ber <exp>]`
- `config interface fast-linkup <interface_name> <enabled|disabled>`

Show section:
- `show switch-fast-linkup global [--json]`
- `show interfaces fast-linkup status`

Notes:
- Invalid or out-of-range global values are rejected with a clear error.
- On unsupported platforms, global configuration is rejected; per-port changes become a safe no-op.

### 1.2.3 Error handling

Frontend (CLI):
1. Missing parameters
2. Invalid parameter value or out-of-range based on STATE_DB capability ranges
3. Unsupported platform (FAST_LINKUP_CAPABLE != true)

Backend (OA):
1. Unknown fields in `SWITCH_FAST_LINKUP` are ignored with warning
2. Out-of-range global values are rejected when ranges are published
3. Unsupported SAI attributes result in safe no-ops

### 1.2.4 Event logging

Frontend:
- Notice on successful global configuration apply
- Error on invalid parameters or unsupported platform

Backend:
- Notice on successful SAI attribute updates
- Error/Warning when capability/range queries fail or invalid updates attempted

###### Table 1: Frontend event logging

| Event                                     | Severity |
|:------------------------------------------|:---------|
| Fast Link-Up global update: success       | NOTICE   |
| Fast Link-Up global update: error         | ERROR    |
| Per-port fast_linkup toggle: success      | NOTICE   |
| Per-port fast_linkup toggle: error        | ERROR    |
# 2 Design

## 2.1 Overview

The design consists of:
- Capability discovery via `STATE_DB` populated by platform components.
- Global configuration via `CONFIG_DB:SWITCH_FAST_LINKUP|GLOBAL` modeled in YANG.
- Per-port control via `CONFIG_DB:PORT|<ifname>:fast_linkup`.
- Orchestration in SWSS to program SAI `SAI_PORT_ATTR_FAST_LINKUP_ENABLED` when supported.

###### Figure 1: Architecture overview

![Architecture Overview](images/architecture-overview.png)

###### Figure 4: Link recovery state machine

![Link Recovery State Machine](images/link-recovery-sm.png)

## 2.2 Capability discovery

`STATE_DB:SWITCH_CAPABILITY|switch` provides:
- `FAST_LINKUP_CAPABLE`: 'true' | 'false'
- `FAST_LINKUP_POLLING_TIMER_RANGE`: "min,max"
- `FAST_LINKUP_GUARD_TIMER_RANGE`: "min,max"

These are used by CLI validation and to guard SWSS programming.

## 2.3 Configuration model

- Global container: `SWITCH_FAST_LINKUP|GLOBAL`
  - `polling_time` (string seconds)
  - `guard_time` (string seconds)
  - `ber_threshold` (string exponent, e.g., 12 -> 1e-12)
- Per-port: `PORT|<ifname>:fast_linkup` ('true' | 'false')

## 2.4 SAI API

- Switch attributes:
  - `SAI_SWITCH_ATTR_FAST_LINKUP_POLLING_TIME_RANGE` (read-only)
  - `SAI_SWITCH_ATTR_FAST_LINKUP_POLLING_TIME`
  - `SAI_SWITCH_ATTR_FAST_LINKUP_GUARD_TIME_RANGE` (read-only)
  - `SAI_SWITCH_ATTR_FAST_LINKUP_GUARD_TIME`
  - `SAI_SWITCH_ATTR_FAST_LINKUP_BER_THRESHOLD`
- Port attribute:
  - `SAI_PORT_ATTR_FAST_LINKUP_ENABLED` (boolean)

## 2.5 Orchestration agent

### 2.5.1 Switch orch

- On init:
  - Query capability and ranges via SAI
  - Publish to `STATE_DB:SWITCH_CAPABILITY|switch`
- On config update:
  - Validate ranges (if present)
  - Apply `SAI_SWITCH_ATTR_*` attributes

### 2.5.2 Ports orch

- On `PORT|<ifname>:fast_linkup` change:
  - Check capability for `SAI_PORT_ATTR_FAST_LINKUP_ENABLED`
  - Set per-port attribute (safe no-op if unsupported)

## 2.6 DB schema

### 2.6.1 Config DB

- `SWITCH_FAST_LINKUP|GLOBAL`:
  - `polling_time` (1..65535)
  - `guard_time` (0..255)
  - `ber_threshold` (uint8 exponent, e.g., 12 -> 1e-12)
- `PORT|<ifname>`:
  - `fast_linkup` ('true'|'false', default 'false')

### 2.6.2 State DB

- `SWITCH_CAPABILITY|switch`:
  - `FAST_LINKUP_CAPABLE` ('true'|'false')
  - `FAST_LINKUP_POLLING_TIMER_RANGE` ("min,max")
  - `FAST_LINKUP_GUARD_TIMER_RANGE` ("min,max")

### 2.6.3 Data sample

```json
{
  "SWITCH_FAST_LINKUP|GLOBAL": {
    "polling_time": "60",
    "guard_time": "10",
    "ber_threshold": "12"
  }
}
```

```json
{
  "PORT": {
    "Ethernet0": {
      "fast_linkup": "true"
    }
  }
}
```

```json
{
  "SWITCH_CAPABILITY|switch": {
    "FAST_LINKUP_CAPABLE": "true",
    "FAST_LINKUP_POLLING_TIMER_RANGE": "5,120",
    "FAST_LINKUP_GUARD_TIMER_RANGE": "1,20"
  }
}
```

### 2.6.4 Configuration sample

- `config switch-fast-linkup global --polling-time 60 --guard-time 10 --ber 12`
- `config interface fast-linkup Ethernet0 enabled`

### 2.6.5 Initial configuration
- Disabled by default (no `fast_linkup` entries; `SWITCH_FAST_LINKUP|GLOBAL` may be absent).

### 2.6.6 Configuration migration
- None; additive schema. Older images ignore unknown keys.

## 2.7 Flows

### 2.7.1 Config section

###### Figure 2: Global configuration flow

![Global Configuration Flow](images/global-config-flow.png)

### 2.7.2 Show section

###### Figure 3: Per-interface flow

![Per-interface Flow](images/per-port-flow.png)

## 2.8 CLI

### 2.8.1 Command structure

- Command groups:
  - Config: `config switch-fast-linkup`, `config interface fast-linkup`
  - Show: `show switch-fast-linkup`, `show interfaces fast-linkup`

### 2.8.2 Usage examples

- Global show:
  - `show switch-fast-linkup global`
  - `show switch-fast-linkup global --json`
  - Output table (example):
    ```
    +---------------+-------+
    | Field         | Value |
    +---------------+-------+
    | polling_time  | 60    |
    | guard_time    | 10    |
    | ber_threshold | 12    |
    +---------------+-------+
    ```
  - Output JSON (example):
    ```json
    {
      "polling_time": "60",
      "guard_time": "10",
      "ber_threshold": "12"
    }
    ```

- Global config:
  - `config switch-fast-linkup global [--polling-time <sec>] [--guard-time <sec>] [--ber <exp>]`
  - Behavior: validates platform capability and enforces min/max ranges from STATE_DB; partial updates preserve unspecified fields.
  - Error cases:
    - Unsupported platform → non-zero exit with a clear error.
    - Out-of-range value → non-zero exit and a message with supported range.

- Per-interface show:
  - `show interfaces fast-linkup status`
  - Output (example):
    ```
    -------------------------------
    | Interface | fast_linkup     |
    |-----------+-----------------|
    | Ethernet0 | true            |
    | Ethernet4 | false           |
    -------------------------------
    ```

- Per-interface config:
  - `config interface fast-linkup <interface_name> <enabled|disabled|true|false|on|off>`
  - Notes:
    - Interface aliases are converted automatically when alias mode is enabled.
    - On multi-ASIC systems, namespace can be supplied and is propagated to backend.
    - If the platform does not support the SAI attribute, SWSS safely no-ops (no disruptive errors).

## 2.9 YANG model

New module `sonic-fast-linkup.yang` models the global configuration:
- Module: `sonic-fast-linkup`
- Top container: `sonic-fast-linkup`
- Container: `SWITCH_FAST_LINKUP/GLOBAL`
- Leafs:
  - `polling_time` (uint16, seconds): interval for status checks during accelerated window
  - `guard_time` (uint16, seconds): maximum time window before fallback decision
  - `ber_threshold` (uint8, exponent): BER threshold E such that threshold is 1e-<E> (e.g., 12 → 1e-12)

Details:
- The YANG module provides type/structure validation for `SWITCH_FAST_LINKUP|GLOBAL` during `config apply/replace`.
- Platform min/max ranges (from STATE_DB) are enforced at runtime by the CLI; dynamic ranges are not modeled in YANG.
- Per-port enable/disable remains a `PORT` table field (`PORT|<ifname>:fast_linkup`) and follows existing `PORT` schema.

Example matching CONFIG_DB:
```json
{
  "SWITCH_FAST_LINKUP|GLOBAL": {
    "polling_time": "60",
    "guard_time": "10",
    "ber_threshold": "12"
  }
}
```

## 2.10 Warm/Fast boot

No special handling is required. Standard config reload mechanisms apply.

# 3 Test plan

## 3.1 Unit tests via VS

1. Capability publish: verify `FAST_LINKUP_CAPABLE` presence and ranges in `STATE_DB`.
2. Global apply: write `SWITCH_FAST_LINKUP|GLOBAL` and verify switch SAI attributes in ASIC_DB.
3. Global validation (range): push out-of-range values when ranges are known and assert no apply.
4. Per-port toggle: toggle `PORT.fast_linkup` and verify `SAI_PORT_ATTR_FAST_LINKUP_ENABLED` in ASIC_DB.
5. CLI error handling: verify messages for unsupported platform and out-of-range values.

## 3.2 Data plane tests via PTF

1. Measure recovery-time improvement on supported modes versus baseline.
2. Validate fallback to regular link-up when BER > threshold at guard expiry.
3. Stability across repeated recovery cycles with toggled fast_linkup.

---



