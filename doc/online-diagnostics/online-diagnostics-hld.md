# SONiC Forwarding Path Online Diagnostics HLD

| Field   | Value |
|---------|-------|
| Authors | Anand Mehra, Xiaohu Huang, Sridhar Talari |
| Status  | Draft |

## Table of Contents

- [1 Revision](#1-revision)
- [2 Scope](#2-scope)
- [3 Definitions and Abbreviations](#3-definitions-and-abbreviations)
- [4 Overview](#4-overview)
- [5 Requirements](#5-requirements)
- [6 SAI API Summary](#6-sai-api-summary)
- [7 Architecture Design](#7-architecture-design)
- [8 Database Schema](#8-database-schema)
- [9 Component Design](#9-component-design)
- [10 Configuration and Management](#10-configuration-and-management)
- [11 Counter and Telemetry Design](#11-counter-and-telemetry-design)
- [12 Fault Detection and Syslog](#12-fault-detection-and-syslog)
- [13 Warmboot and Fastboot Impact](#13-warmboot-and-fastboot-impact)
- [14 Multi-ASIC and Chassis Considerations](#14-multi-asic-and-chassis-considerations)
- [15 Restrictions and Limitations](#15-restrictions-and-limitations)
- [16 Testing Requirements](#16-testing-requirements)
- [17 Open Items](#17-open-items)
- [18 References](#18-references)

---

## 1 Revision

| Rev | Date       | Author(s)                                   | Change Description                          |
|-----|------------|---------------------------------------------|---------------------------------------------|
| 0.1 | 2026-07-02 | Anand Mehra, Xiaohu Huang, Sridhar Talari | Initial SONiC HLD mapped to SAI proposal |

---

## 2 Scope

This HLD specifies how SONiC integrates **SAI Online Diagnostics**: a switch-scoped, active datapath health check that periodically injects implementation-controlled probe packets, validates internal receive paths, and exposes aggregate counters.

**In scope**

- Mapping SAI switch attributes and switch statistics into SONiC configuration, orchestration, counters, and operational visibility.
- Community CLI/YANG for enable/disable, interval, loss threshold, and optional probe parameters.
- Flex-counter integration for the four aggregate SAI switch statistics.
- Capability discovery and graceful degradation when a platform returns `SAI_STATUS_NOT_SUPPORTED`.

**Out of scope**

- Vendor-specific probe packet format, injection mechanism, internal path selection, or per-slice/per-NPU object models (these remain in the SAI/vendor implementation).
- Standard SAI alarm/notification callback (explicitly excluded by the SAI proposal).
- Test-only error injection controls (may remain vendor debug CLI only).
- Replacing or duplicating existing passive counter-based health monitoring (CRM, drop counters, etc.).

This community HLD standardizes the SONiC-facing contract once the SAI attributes and statistics are upstreamed.

---

## 3 Definitions and Abbreviations

| Term | Definition |
|------|------------|
| Online Diagnostics | Periodic internal probe injection and validation while the switch remains in service |
| Probe cycle | One interval of diagnostic transmit/receive activity controlled by `ONLINE_DIAG_INTERVAL_MS` |
| Aggregate counters | Switch-level TX/RX/loss/corruption statistics exposed via `sai_switch_stat_t` |
| SwitchOrch | orchagent component that programs switch-level SAI attributes from `SWITCH_TABLE` |
| Flex Counter | SONiC framework that polls SAI statistics into `COUNTERS_DB` |

---

## 4 Overview

### 4.1 Problem

SONiC today exposes many passive counters (port, queue, switch drop reasons, CRM resources) but lacks a **standard, vendor-neutral active health check** that injects known test traffic and verifies it returns correctly through internal datapath blocks. Silent packet loss and corruption on internal paths can therefore go undetected until customer traffic is impacted.

### 4.2 Proposed solution

The upstream SAI proposal adds switch-level configuration attributes and four aggregate statistics. The diagnostic engine runs in the **SAI implementation** (typically inside syncd). SONiC's role is to:

1. Expose configuration through `CONFIG_DB` / community CLI.
2. Program SAI switch attributes through existing `SwitchOrch` → syncd paths.
3. Poll and publish counters through the Flex Counter framework.
4. Surface operational status in `STATE_DB`, `show` commands, and telemetry.
5. Optionally raise syslog/events when counter deltas indicate sustained loss or corruption (since SAI defines no notification callback).

### 4.3 Design principles

| Principle | Rationale |
|-----------|-----------|
| Switch-scoped only | Matches SAI model; no new object type or orchagent object lifecycle |
| Disabled by default | Backward compatible; no behavior change until explicitly enabled |
| Vendor-neutral SONiC surface | CONFIG/STATE/CLI expose only SAI-standard fields |
| Fail gracefully | Unsupported platforms hide/disable feature via capability discovery |
| Minimal orchagent footprint | Extend `SwitchOrch` and flex counters rather than a new daemon |

---

## 5 Requirements

### 5.1 Functional

| ID | Requirement |
|----|-------------|
| F1 | SONiC shall allow enabling/disabling Online Diagnostics per switch/ASIC. |
| F2 | SONiC shall configure probe interval (`interval_ms`), consecutive loss threshold, optional payload patterns, and optional packet lengths when supported by SAI. |
| F3 | SONiC shall publish `TX`, `RX`, `PACKET_LOSS`, and `PACKET_CORRUPTIONS` counters in `COUNTERS_DB`. |
| F4 | SONiC shall expose configuration and runtime status via community CLI. |
| F5 | SONiC shall record platform capability (`supported` / `not_supported`) in `STATE_DB`. |
| F6 | On platforms returning `SAI_STATUS_NOT_SUPPORTED`, configuration commands shall fail with a clear error; default config shall not block boot or config reload. |

### 5.2 Non-functional

| ID | Requirement |
|----|-------------|
| NF1 | Configuration changes shall not require orchagent restart. |
| NF2 | Counter polling shall reuse Flex Counter with a configurable interval (default 10 s). |
| NF3 | Feature shall have no impact when disabled (SAI default). |
| NF4 | Diagnostic traffic shall not appear on front-panel ports unless the vendor implementation explicitly intends that (SAI operational guidance). |

---

## 6 SAI API Summary

Source: SAI proposal `doc/SAI-Proposal-Online-Diag.md`.

### 6.1 New switch attributes

| SAI attribute | Type | Default | SONiC field (proposed) |
|---------------|------|---------|-------------------------|
| `SAI_SWITCH_ATTR_ONLINE_DIAG_ENABLE` | `bool` | `false` | `enabled` |
| `SAI_SWITCH_ATTR_ONLINE_DIAG_INTERVAL_MS` | `uint64` | `5000` | `interval_ms` |
| `SAI_SWITCH_ATTR_ONLINE_DIAG_LOSS_THRESHOLD` | `uint64` | `1` | `loss_threshold` |
| `SAI_SWITCH_ATTR_ONLINE_DIAG_PAYLOAD_PATTERNS` | `sai_u32_list_t` | empty | `payload_patterns` |
| `SAI_SWITCH_ATTR_ONLINE_DIAG_PACKET_LENGTHS` | `sai_u32_list_t` | empty | `packet_lengths` |

**Validation**

- `interval_ms` must be > 0.
- Recommended packet length range: 64–9000 bytes; vendor may reject unsupported values with `SAI_STATUS_INVALID_PARAMETER`.
- Empty pattern/length lists select vendor-defined defaults.

### 6.2 New switch statistics

| SAI statistic | Description |
|---------------|-------------|
| `SAI_SWITCH_STAT_ONLINE_DIAG_TX_PACKETS` | Transmitted probe packets |
| `SAI_SWITCH_STAT_ONLINE_DIAG_RX_PACKETS` | Received probe packets |
| `SAI_SWITCH_STAT_ONLINE_DIAG_PACKET_LOSS` | Detected probe loss |
| `SAI_SWITCH_STAT_ONLINE_DIAG_PACKET_CORRUPTIONS` | Detected probe corruption |

Counters use existing `get_switch_stats` / clear-stats semantics.

### 6.3 SAI non-goals (SONiC inherits)

- No standard wire format, MAC addresses, or hardware block requirements.
- No per-port/per-slice SAI object model.
- No SAI notification callback for alarms.
- No standard test error-injection API.

---

## 7 Architecture Design

```
+--------------------------- SONiC switch ---------------------------+
|                                                                    |
|  CLI / REST / gNMI                                                 |
|       |                                                            |
|       v                                                            |
|  CONFIG_DB                                                         |
|   ONLINE_DIAG|switch  (or SWITCH|online_diag subgroup)             |
|       |                                                            |
|       v  config reload / translib                                  |
|  APPL_DB  SWITCH_TABLE:switch  (+ online_diag_* fields)            |
|       |                                                            |
|       v                                                            |
|  orchagent / SwitchOrch                                            |
|   - map fields -> SAI_SWITCH_ATTR_ONLINE_DIAG_*                    |
|   - capability -> STATE_DB                                         |
|   - enable flex counter group                                      |
|       |                                                            |
|       v                                                            |
|  syncd / SAI vendor implementation                                 |
|   - probe thread / hardware scheduler                              |
|   - inject, receive, validate, aggregate counters                  |
|       |                                                            |
|       v                                                            |
|  Flex Counter (syncd)  --->  COUNTERS_DB                           |
|       |                                                            |
|       +--> show online-diag / telemetry / eventd (optional)        |
|                                                                    |
+--------------------------------------------------------------------+
```

### 7.1 Control plane flow

1. Operator sets `enabled`, `interval_ms`, etc. via CLI → `CONFIG_DB`.
2. `config reload` or incremental config pushes fields to `APPL_DB` `SWITCH_TABLE`.
3. `SwitchOrch::doAppSwitchTableTask` applies attributes through `sai_switch_api->set_switch_attribute`.
4. On first successful enable, `SwitchOrch` registers flex counters for the four statistics.
5. `SwitchOrch` writes `STATE_DB|ONLINE_DIAG_TABLE|switch` with `status`, `supported`, and last-known config.

### 7.2 Data plane flow (vendor implementation)

The SAI implementation owns probe generation, internal looping, validation, and counter updates. SONiC does not construct diagnostic packets. Vendor implementations should ensure probes stay isolated from tenant/customer traffic (per SAI proposal).

---

## 8 Database Schema

### 8.1 CONFIG_DB

**Option A (recommended): dedicated table**

```
; schema: ONLINE_DIAG|switch
enabled=true|false
interval_ms=5000
loss_threshold=1
payload_patterns=0x00000000,0xffffffff    ; optional, comma-separated u32 hex
packet_lengths=64,256,1518,9000             ; optional, comma-separated decimal
```

**Option B: extend existing SWITCH table**

Add the same fields under `CONFIG_DB|SWITCH|switch`. Option A keeps the feature modular and easier to gate by platform capability.

### 8.2 APPL_DB

Mirror CONFIG fields on `APPL_DB|SWITCH_TABLE|switch`:

```
online_diag_enabled
online_diag_interval_ms
online_diag_loss_threshold
online_diag_payload_patterns
online_diag_packet_lengths
```

`SwitchOrch` already consumes `SWITCH_TABLE`; new fields extend `switch_attribute_map`.

### 8.3 STATE_DB

```
STATE_DB|ONLINE_DIAG_TABLE|<asic_name>
  supported=true|false
  operational_status=disabled|enabled|error
  interval_ms=<uint>
  loss_threshold=<uint>
  last_error=<string>          ; e.g. SAI_STATUS_NOT_SUPPORTED
  tx_packets=<uint64>          ; optional cache from last flex-counter read
  rx_packets=<uint64>
  packet_loss=<uint64>
  packet_corruptions=<uint64>
```

For multi-ASIC, key is per ASIC (`switch0`, `switch1`, …) consistent with other switch-scoped features.

### 8.4 COUNTERS_DB

Follow existing switch flex-counter naming:

```
COUNTERS:oid:0x<switch_oid>
  SAI_SWITCH_STAT_ONLINE_DIAG_TX_PACKETS
  SAI_SWITCH_STAT_ONLINE_DIAG_RX_PACKETS
  SAI_SWITCH_STAT_ONLINE_DIAG_PACKET_LOSS
  SAI_SWITCH_STAT_ONLINE_DIAG_PACKET_CORRUPTIONS
```

Optional name map entry in `COUNTERS:SWITCH_NAME_MAP` for human-readable `show` output.

### 8.5 FLEX_COUNTER_DB

```
FLEX_COUNTER_TABLE|ONLINE_DIAG
  FLEX_COUNTER_STATUS|enable
  POLL_INTERVAL|10000
  STATS_MODE|STATS_READ
```

Registered by `SwitchOrch` when feature is supported and enabled (or pre-registered with polling gated by enable flag — implementation choice).

---

## 9 Component Design

### 9.1 sonic-swss / SwitchOrch

**Changes**

1. Extend `switch_attribute_map` with online-diag field → SAI attribute mappings.
2. Parse list fields (`payload_patterns`, `packet_lengths`) into `sai_u32_list_t` buffers before SAI set.
3. On boot, query SAI capability (`sai_query_attribute_capability` or trial set/get) and publish `supported` to `STATE_DB`.
4. Register flex counter group `ONLINE_DIAG` with the four stat IDs (pattern matches `fabricportsorch.cpp` switch drop counters).
5. Handle `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_INVALID_PARAMETER` with structured logs; do not retry indefinitely.

**Attribute apply order**

Configure interval, threshold, patterns, and lengths **before** setting `ONLINE_DIAG_ENABLE=true`, matching the SAI usage example.

**Disable path**

Set `ONLINE_DIAG_ENABLE=false` first on disable; optionally stop flex-counter polling to reduce load.

### 9.2 syncd / SAI vendor

Vendor implements probe scheduler and counter maintenance. Expected behaviors:

- Start/stop diagnostic paths on enable/disable.
- Release resources when disabled.
- Increment aggregate counters atomically.
- Emit vendor syslog on loss/corruption (optional but recommended for operability).

SONiC does not require syncd code changes beyond flex-counter stat ID support already present for switch stats.

### 9.3 sonic-utilities / CLI

**Configuration (config CLI)**

```
config online-diag enable
config online-diag disable
config online-diag interval <milliseconds>
config online-diag loss-threshold <count>
config online-diag payload-patterns <hex-list>   ; optional
config online-diag packet-lengths <len-list>     ; optional
```

**Show**

```
show online-diag status
show online-diag counters
```

Example `show online-diag status`:

```
Online Diagnostics Status
-------------------------
ASIC          Supported   Enabled   Interval(ms)   Loss threshold
switch0       yes         yes       5000           3

Counters (switch0)
  TX packets       : 1234567
  RX packets       : 1234560
  Packet loss      : 7
  Corruptions      : 0
```

### 9.4 YANG / Management Framework

Add OpenConfig or SONiC-native YANG leaves under switch diagnostics (exact model TBD with mgmt framework WG). Translib maps YANG → `CONFIG_DB|ONLINE_DIAG|switch`.

### 9.5 Platform capability

`platform.json` or `device_metadata.json` may include:

```json
"online_diag": {
  "supported": true
}
```

This allows CLI/help to hide unsupported commands before SAI is queried. Runtime truth remains SAI capability discovery.

---

## 10 Configuration and Management

### 10.1 Defaults

| Parameter | Default | Notes |
|-----------|---------|-------|
| enabled | `false` | Matches SAI default |
| interval_ms | `5000` | SAI default |
| loss_threshold | `1` | SAI default |
| payload_patterns | empty | Vendor defaults |
| packet_lengths | empty | Vendor defaults |

### 10.2 Config reload / replay

Online-diag attributes are switch-scoped and survive in SAI until changed. On orchagent restart:

1. Replay `APPL_DB` `SWITCH_TABLE` online-diag fields.
2. Re-register flex counters.
3. Refresh `STATE_DB` from SAI get where needed.

### 10.3 Container config

No new container. Feature lives in existing `syncd` (SAI) and `swss` (SwitchOrch) processes.

---

## 11 Counter and Telemetry Design

### 11.1 Flex Counter

Use `FlexCounterManager` with `CounterType::SWITCH` (or `SWITCH_DEBUG` if grouping with other switch stats). Poll interval default **10 seconds** (configurable via `FLEX_COUNTER_TABLE`).

### 11.2 Telemetry

Export the four counters through existing COUNTERS_DB → telemetry pipeline (gNMI `/sonic/counters/...` or equivalent). Metric names should mirror SAI stat names for vendor-neutral dashboards.

### 11.3 Clear counters

Support `sonic-clear online-diag counters` mapping to SAI `clear_switch_stats` for the four stat IDs when the vendor supports clear-on-read/clear API.

---

## 12 Fault Detection and Syslog

The SAI proposal does **not** define a notification callback. SONiC has two complementary options:

| Approach | Owner | Pros | Cons |
|----------|-------|------|------|
| A. Vendor syslog in syncd/SAI | Vendor | Immediate, detailed (e.g. slice ID) | Not standardized across vendors |
| B. orchagent/eventd poll on counter deltas | SONiC | Portable | Coarser granularity; poll delay |

**Recommended**

- **Phase 1:** Rely on vendor syslog plus `show online-diag counters`.
- **Phase 2 (optional):** Add `eventd` plugin watching `PACKET_LOSS` / `PACKET_CORRUPTIONS` deltas and emitting `EVENT_ONLINE_DIAG_FAULT` with severity based on threshold crossing.

SONiC shall **not** block on a new SAI callback for initial delivery.

---

## 13 Warmboot and Fastboot Impact

| Scenario | Expected behavior |
|----------|-------------------|
| Warm reboot | Reapply CONFIG → APPL → SAI attributes after orchagent/syncd restart; counters reset per vendor warmboot rules |
| Fast reboot / express boot | Same as warm reboot unless vendor preserves diagnostic state (implementation defined) |
| orchagent restart | Replay switch attributes from APPL_DB |

No new warmboot state tables are required for aggregate counters. If a vendor needs to preserve enable flag across warmboot, handle inside SAI/syncd.

---

## 14 Multi-ASIC and Chassis Considerations

- Each ASIC has its own SAI switch object → separate `ONLINE_DIAG` config/state keys per ASIC (`switch0`, `switch1`, …).
- Chassis line cards: config may be applied per linecard namespace or host namespace depending on existing multi-ASIC config pattern.
- CLI should accept `-n <namespace>` consistent with other `config`/`show` commands on multi-ASIC platforms.
- Fabric cards (if modeled as separate switches) may independently support or reject the feature.

---

## 15 Restrictions and Limitations

1. **Aggregate visibility only** — SONiC cannot standardize per-slice/per-path status without vendor extensions.
2. **No root-cause isolation** — Counters detect loss/corruption but not the failing hardware block (same as SAI non-goals).
3. **Platform support varies** — VS/simulator likely returns `NOT_SUPPORTED`.
4. **No SAI alarm callback** — Event latency depends on syslog or SONiC polling design.
5. **Probe load** — Very short intervals may increase CPU/DMA load (SAI guidance); CLI should document sensible minimums per platform.
6. **List attributes** — Large pattern/length lists may require buffer handling per `SAI_STATUS_BUFFER_OVERFLOW` on get (primarily a debug/show concern).

---

## 16 Testing Requirements

### 16.1 Unit tests (sonic-swss)

- `SwitchOrch` maps CONFIG/APPL fields to correct SAI attributes.
- List parsing for `payload_patterns` and `packet_lengths`.
- Graceful handling of `SAI_STATUS_NOT_SUPPORTED`.
- Flex counter registration when enabled.

### 16.2 VS/mock tests

- Mock `sai_switch_api->set_switch_attribute` / `get_switch_stats` and verify DB state transitions.

### 16.3 sonic-mgmt / pytest

| Test | Description |
|------|-------------|
| T1 | Enable online-diag on supported HW; verify SAI attributes in ASIC_DB |
| T2 | Verify counters increment over time in COUNTERS_DB |
| T3 | Disable feature; verify enable attribute false |
| T4 | Invalid interval (0) rejected at CLI/SAI |
| T5 | Unsupported platform: config rejected, boot succeeds |
| T6 | Config reload preserves settings |
| T7 | Multi-ASIC: independent config per namespace |

### 16.4 Vendor HW tests

- Validate probe isolation (no front-panel leakage).
- Loss/corruption injection via vendor debug hooks (outside community scope).
- Soak test under production traffic load (no false positives).

---

## 17 Open Items

| # | Item | Owner |
|---|------|-------|
| 1 | Final CONFIG table name: `ONLINE_DIAG` vs extend `SWITCH` | SONiC community |
| 2 | SAI PR merge timeline and enum values | SAI WG |
| 3 | YANG model placement (OpenConfig vs SONiC native) | Mgmt FW WG |
| 4 | Minimum interval guidance per platform | Vendors |
| 5 | Phase-2 eventd integration for portable alarms | SONiC community |

---

## 18 References

1. SAI Proposal: `doc/SAI-Proposal-Online-Diag.md`
2. SAI header changes: `inc/saiswitch.h` — `SAI_SWITCH_ATTR_ONLINE_DIAG_*`, `SAI_SWITCH_STAT_ONLINE_DIAG_*`
3. SONiC `SwitchOrch` — `src/sonic-swss/orchagent/switchorch.cpp`
4. Switch flex counters — `src/sonic-swss/orchagent/fabricportsorch.cpp` (switch stat flex counter pattern)
