# CDB Commands with Advertised MaxDuration

## Table of Contents
- [List of Tables](#list-of-tables)
- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Timeout Resolution Flow](#71-timeout-resolution-flow)
  - [7.2 Commands Using Module Advertised MaxDuration (CMIS Compliant)](#72-commands-using-module-advertised-maxduration-cmis-compliant)
  - [7.3 CDB Commands in the Firmware Upgrade Workflow](#73-cdb-commands-in-the-firmware-upgrade-workflow)
  - [7.4 Repository to Change](#74-repository-to-change)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Restrictions/Limitations](#11-restrictionslimitations)
- [12. Testing Requirements](#12-testing-requirements)
- [References](#references)

## List of Tables
  * [Table 1: Definitions](#table-1-definitions)
  * [Table 2: Commands Using Advertised MaxDuration](#table-2-commands-using-advertised-maxduration)
  * [Table 3: Upgrade Workflow CDB Commands](#table-3-upgrade-workflow-cdb-commands)

## 1. Revision
| Rev | Date       | Author | Change Description |
|-----|------------|--------|--------------------|
| 0.1 | 2026-05-19 | Pavan Kalyan Nakka      | Initial version    |

## 2. Scope

This document describes changes to use module advertised MaxDuration timeouts for CDB firmware commands, as defined in [CMIS 5.3](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf). It proposes which commands should use the module advertised MaxDuration values and which will retain fixed defaults for command execution time.

## 3. Definitions/Abbreviations

#### Table 1: Definitions
| **Term**        | **Definition/Abbreviations**                                          |
|-----------------|-----------------------------------------------------------------------|
| CDB             | Command Data Block                                                    |
| CMIS            | Common Management Interface Specification                             |
| LPL             | Local Payload                                                         |
| EPL             | Extended Payload                                                      |
| FW              | Firmware                                                              |
| xcvrd           | Transceiver Daemon                                                    |

## 4. Overview

The [CMIS 5.3](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf) defines per-command **MaxDuration** fields on Page 9Fh (bytes 144–153) that advertise the maximum time a module requires to execute specific CDB commands. These are U16 values in milliseconds, scaled by a multiplier **M** defined by bit 137.3:

- `0b` -> M = 1 (timeout in 1 ms units)
- `1b` -> M = 10 (timeout in 10 ms units)

The advertised MaxDuration values (bytes 144–153) are multiplied by M to get the effective timeout in milliseconds. The module populates these fields in the CDB 0041h (Firmware Management Features) reply.

**For example**: If MaxDurationStart is 100 and M = 10, the timeout for the Start (0101h) command is 100 × 10 = 1000 ms.

The current implementation applies a fixed timeout to most CDB commands. This can cause:

- **Premature timeouts** — Some commands may require more time to complete depending on the module.
- **Non-compliance** — the host must respect the module advertised MaxDuration when present.

This change uses the module advertised MaxDuration as the per-command timeout where defined. Commands without a MaxDuration field retain fixed defaults.

## 5. Requirements

### Functional Requirements

1. For CDB commands where the CMIS defines a MaxDuration field, use the module advertised value as the command timeout.
2. For CDB commands where the CMIS does not define a MaxDuration field, use a fixed default timeout.
3. Fall back to the default timeout when CDB 0041h is not supported by the module or returns invalid data.
4. Continue to use CDB status polling for early completion detection regardless of timeout value.

### Non-Functional Requirements

1. No increase in firmware upgrade time for modules that already complete within the current timeout window.
2. Backward compatibility with modules that do not support CDB 0041h.

## 6. Architecture Design

No changes to the overall SONiC architecture. This modifies timeout in the CDB command execution path (`CdbFwHandler` in `sonic-platform-common/sonic_platform_base/sonic_xcvr/cdb/cdb_fw.py`).

The firmware upgrade flow queries MaxDuration values via CDB 0041h at the start, then passes the appropriate timeout to each subsequent CDB command:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Firmware Upgrade                              │
├──────────────────────────────────────────────────────────────────────┤
│  CdbFwHandler                                                        │
│      │                                                               │
│      ├── Query module for MaxDuration values (CDB 0041h)             │
│      │         │                                                     │
│      │         └── Parse per-command MaxDuration from response       │
│      │                                                               │
│      ├── Abort FW Download (0102h)    ── use advertised timeout      │
│      ├── Start FW Download (0101h)    ── use advertised timeout      │
│      ├── Write FW Block (0103h/0104h) ── use advertised timeout      │
│      ├── Complete FW Download (0107h) ── use advertised timeout      │
│      ├── Run FW Image (0109h)         ── use default timeout         │
│      └── Commit FW Image (010Ah)      ── use default timeout         │
└──────────────────────────────────────────────────────────────────────┘
```

## 7. High-Level Design

### 7.1 Timeout Resolution Flow

When a CDB command is issued during firmware upgrade, the timeout is determined as follows:

```
CDB command issued
    │
    ▼
Does the CMIS spec define a MaxDuration for this command (via CDB 0041h)?
    │
    ├── Yes ──► Use the module advertised MaxDuration as the timeout  ─┐
    │                                                                  │
    └── No  ──► Use the fixed default timeout ─────────────────────────┤
                                                                       │
                                                                       ▼
               Poll CDB status register for early completion regardless of timeout value
```

### 7.2 Commands Using Module Advertised MaxDuration (CMIS Compliant)

The following commands have their MaxDuration defined on Page 9Fh (bytes 144–153) and returned in the CDB 0041h response:

#### Table 2: Commands Using Advertised MaxDuration
| Command | CMD ID | MaxDuration Field | Byte Offset (Page 9Fh) |
|---------|--------|-------------------|------------------------|
| Start FW Download | 0101h | MaxDurationStart | 144–145 |
| Abort FW Download | 0102h | MaxDurationAbort | 146–147 |
| Write FW Block (LPL) | 0103h | MaxDurationWrite | 148–149 |
| Write FW Block (EPL) | 0104h | MaxDurationWrite | 148–149 |
| Complete FW Download | 0107h | MaxDurationComplete | 150–151 |

If CDB 0041h is not supported, these commands fall back to the default timeout.

### 7.3 CDB Commands in the Firmware Upgrade Workflow

The following table lists all CDB commands involved in the firmware upgrade process along with proposed timeout behavior:

#### Table 3: Upgrade Workflow CDB Commands
| # | Command | CMD ID | MaxDuration | 
|---|---------|--------|-------------|
| 1 | Firmware Management Features | 0041h | Default |
| 2 | Get FW Info | 0100h | Default |
| 3 | Start FW Download | 0101h | Advertised |
| 4 | Abort FW Download | 0102h | Advertised |
| 5 | Write FW Block (LPL) | 0103h | Advertised |
| 6 | Write FW Block (EPL) | 0104h | Advertised |
| 7 | Complete FW Download | 0107h | Advertised |
| 8 | Run FW Image | 0109h | Default |
| 9 | Commit FW Image | 010Ah | Default |
| 10 | Enter Password | 0001h | Default |

**Note:** The Run FW Image command already uses its own fixed timeout value independent of the default.

### 7.4 Repository to Change

| Repository            | Files to Modify |
|-----------------------|-----------------|
| sonic-platform-common | `sonic_platform_base/sonic_xcvr/cdb/cdb_fw.py`, `sonic_platform_base/sonic_xcvr/cdb/cdb.py`, `sonic_platform_base/sonic_xcvr/mem_maps/public/cdb.py`, `sonic_platform_base/sonic_xcvr/fields/cdb_consts.py` |

**Changes:**

1. **Parse MaxDuration in `initFwHandler()`** — Extend the existing CDB 0041h response parsing to extract MaxDuration fields (bytes 144–153), read the M multiplier from bit 137.3, multiply the U16 values by M, and store the resulting ms values as instance attributes.

2. **Pass timeouts to `send_cmd()`** — Update the following methods to pass their respective MaxDuration value:
   - `start_fw_download()` -> `timeout_start`
   - `abort_fw_download()` -> `timeout_abort`
   - `write_lpl_block()` / `write_epl_block()` -> `timeout_write`
   - `complete_fw_download()` -> `timeout_complete`

3. **Fallback** — If the 0041h reply does not contain valid MaxDuration values (e.g., zero or module doesn't support it), retain `None` so `wait_for_cdb_status()` falls back to its existing default.

No changes to API signatures, xcvrd, or any higher-level callers.

## 8. SAI API

N/A

## 9. Configuration and Management

N/A

## 10. Warmboot and Fastboot Design Impact

N/A

## 11. Restrictions/Limitations

- **Modules not supporting CDB 0041h**: Fall back to the default timeout for all commands.
- **Zero-value advertisements**: A module advertising 0 ms is treated as "use default timeout" to avoid immediate timeout failures.
- **Non-advertised commands**: Commands that do not advertise MaxDuration will rely solely on default or fixed timeouts.

## 12. Testing Requirements

1. Verify advertised MaxDuration is used as timeout for supported CDB commands.
2. Verify fallback to default timeout when CDB 0041h is not supported.
3. Verify that a 0 ms advertised value falls back to the default timeout.
4. Perform firmware upgrade end-to-end and verify no timeout failures on supported modules.

## References

- [OIF CMIS 5.3](https://www.oiforum.com/wp-content/uploads/OIF-CMIS-05.3.pdf) — Section 9.4.2, Page 9Fh MaxDuration fields (bytes 144–153)
- [sonic-platform-common](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_xcvr/cdb/cdb_fw.py) — CDB firmware commands implementation
