# L1 Summary CLI Command HLD

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
- [8. SAI API](#8-sai-api)
- [9. Configuration and Management](#9-configuration-and-management)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)

---

## 1. Revision

| Rev | Date       | Author          | Description          |
|-----|------------|-----------------|----------------------|
| 0.1 | 2026-01-13 | Bobby McGonigle | Initial version      |

---

## 2. Scope

This document describes the design of the `show interfaces l1-summary` CLI command in SONiC. This command provides a consolidated Layer 1 (physical layer) summary view of front-panel interfaces, including operational status, FEC mode, fault status, transceiver information, media interface type, and link flap statistics.

---

## 3. Definitions/Abbreviations

| Term        | Definition                                          |
|-------------|-----------------------------------------------------|
| L1          | Layer 1 (Physical Layer)                            |
| FEC         | Forward Error Correction                            |
| CMIS        | Common Management Interface Specification           |
| Appsel      | Application Select (CMIS transceiver mode)          |
| QSFP-DD     | Quad Small Form Factor Pluggable Double Density     |
| OSFP        | Octal Small Form Factor Pluggable                   |

---

## 4. Overview

The `show interfaces l1-summary` command provides a concise, single-view summary of Layer 1 interface attributes. This is particularly useful for:

- Quickly assessing the operational state of all front-panel ports
- Identifying interfaces with faults
- Viewing transceiver vendor/model and active media interface mode (particulary when using mutliple vendors/types of transceivers or working from SSH)
- Monitoring link stability via flap counts and last up/down timestamps

The command is intended to be a high level summary to spot issues and not a detailed troubleshooting tool. Once an issue is identified, the user can use existing and more detailed commands.

---

## 5. Requirements

### Functional Requirements

1. Display a summary table of all front-panel interfaces with the following columns:
   - Interface name and alias
   - Mode (speed/lanes, e.g., `100G/4`)
   - FEC mode
   - Operational and administrative status
   - Fault status (local, remote, local+remote, or none)
   - Transceiver vendor and model
   - Media interface type (for CMIS transceivers)
   - Flap count
   - Last up time
   - Last down time

2. Support filtering by interface name
3. Support multi-ASIC platforms with namespace filtering
4. Support display options (`all`, `frontend`, `internal`)

### Non-Functional Requirements

1. Command execution should complete within a reasonable time for systems with many ports
2. Output should be human-readable in tabular format

---

## 6. Architecture Design

This feature does not change the existing SONiC architecture. It is a CLI-only enhancement that reads from existing database tables.

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI Layer                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  show interfaces l1-summary                             │    │
│  │  (show/interfaces/__init__.py)                          │    │
│  └────────────────────────┬────────────────────────────────┘    │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐    │
│  │  intfutil -c l1_summary                                 │    │
│  │  (scripts/intfutil)                                     │    │
│  └────────────────────────┬────────────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                      Redis Databases                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │  APPL_DB    │  │  STATE_DB   │  │  CONFIG_DB          │    │
│  │ PORT_TABLE  │  │ PORT_TABLE  │  │ PORT table          │    │
│  │             │  │ TRANSCEIVER │  │                     │    │
│  │             │  │ _INFO       │  │                     │    │
│  │             │  │ PORT_OPERR  │  │                     │    │
│  │             │  │ _TABLE      │  │                     │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## 7. High-Level Design

### 7.1 Feature Type

This is a built-in SONiC feature, not an Application Extension.

### 7.2 Modified Modules

| Repository       | Module/File                   | Description                           |
|------------------|-------------------------------|---------------------------------------|
| sonic-utilities  | `scripts/intfutil`            | Core L1 summary logic (`IntfL1Summary` class) |
| sonic-utilities  | `show/interfaces/__init__.py` | CLI command registration              |

### 7.3 Database Schema (Read-Only)

This feature reads from existing database tables. No schema changes are required.

#### APPL_DB - PORT_TABLE

| Field           | Description                              |
|-----------------|------------------------------------------|
| alias           | Interface alias                          |
| oper_status     | Operational status (up/down)             |
| admin_status    | Administrative status (up/down)          |
| speed           | Configured speed in Mbps                 |
| lanes           | Comma-separated lane list                |
| fec             | FEC mode                                 |
| flap_count      | Number of link state changes             |
| last_up_time    | Timestamp of last link up event          |
| last_down_time  | Timestamp of last link down event        |

#### STATE_DB - TRANSCEIVER_INFO

| Field                     | Description                              |
|---------------------------|------------------------------------------|
| type                      | Transceiver form factor                  |
| manufacturer              | Vendor name                              |
| model                     | Transceiver model                        |
| cmis_rev                  | CMIS revision (indicates CMIS support)   |
| application_advertisement | Dict of supported application modes      |
| active_apsel_hostlaneN    | Active application select per lane       |

#### STATE_DB - PORT_OPERR_TABLE

| Field             | Description                              |
|-------------------|------------------------------------------|
| oper_error_status | Bitmask (bit 0: local fault, bit 1: remote fault) |

### 7.4 Key Implementation Details

#### IntfL1Summary Class

A new class `IntfL1Summary` is added to `scripts/intfutil` that:

1. Iterates through all front-panel ports from APPL_DB
2. Collects L1 status from multiple tables
3. Processes CMIS transceiver information to extract active media interface
4. Formats output using tabulate

#### Helper Functions

| Function                        | Description                                      |
|---------------------------------|--------------------------------------------------|
| `get_port_application_info()`   | Extracts host electrical and media interface IDs from CMIS transceivers |
| `clean_media_interface_text()`  | Removes placeholder/clause suffixes from media interface strings |
| `state_db_port_operr_status_get()` | Retrieves fault status from PORT_OPERR_TABLE |
| `is_bit_set()`                  | Checks if a specific bit is set in the oper_error_status bitmask |
| `get_fault_status()`            | Converts local/remote fault booleans to display string |
| `get_transceiver_display()`     | Combines vendor and model into display string |
| `format_link_change_time()`     | Formats timestamps for compact display |

### 7.5 SWSS and Syncd Changes

No changes required. This feature only reads existing data.

### 7.6 Sequence Diagram

```
User                CLI                 intfutil             Redis
 │                   │                     │                   │
 │ show interfaces   │                     │                   │
 │ l1-summary        │                     │                   │
 │──────────────────>│                     │                   │
 │                   │ intfutil -c         │                   │
 │                   │ l1_summary          │                   │
 │                   │────────────────────>│                   │
 │                   │                     │ get PORT keys     │
 │                   │                     │──────────────────>│
 │                   │                     │<──────────────────│
 │                   │                     │                   │
 │                   │                     │ for each port:    │
 │                   │                     │ get APPL_DB data  │
 │                   │                     │──────────────────>│
 │                   │                     │<──────────────────│
 │                   │                     │ get STATE_DB data │
 │                   │                     │──────────────────>│
 │                   │                     │<──────────────────│
 │                   │                     │ get TRANSCEIVER   │
 │                   │                     │──────────────────>│
 │                   │                     │<──────────────────│
 │                   │                     │ get PORT_OPERR    │
 │                   │                     │──────────────────>│
 │                   │                     │<──────────────────│
 │                   │                     │                   │
 │                   │ formatted table     │                   │
 │                   │<────────────────────│                   │
 │ tabular output    │                     │                   │
 │<──────────────────│                     │                   │
```

### 7.7 Warmboot/Fastboot Dependencies

None. This is a read-only CLI command.

### 7.8 Platform Dependencies

None. This feature works on all platforms.

---

## 8. SAI API

No SAI API changes are required. This feature reads from existing database tables that are populated by other components.

---

## 9. Configuration and Management

### 9.1 Manifest

Not applicable. This is a built-in feature.

### 9.2 CLI Enhancements

#### New Command

```
show interfaces l1-summary [INTERFACENAME] [-n NAMESPACE] [-d DISPLAY]
```

**Arguments:**

| Argument       | Required | Description                                    |
|----------------|----------|------------------------------------------------|
| INTERFACENAME  | No       | Filter output to specific interface(s)         |
| -n, --namespace| No       | Filter by ASIC namespace (multi-ASIC systems)  |
| -d, --display  | No       | Display option: `all`, `frontend`, or `internal` |

**Example Output:**

```
  admin@sonic:~$ show int l1-summary
  Interface    Alias     Mode    FEC    Oper    Admin    Fault                      Transceiver    Media Interface    Flaps          Last Up    Last Down
-----------  -------  -------  -----  ------  -------  -------  -------------------------------  -----------------  -------  ---------------  -----------
Ethernet256   Port33  1600G/8     rs      up       up     none         VendorA ABCD-1234-E6P-CA        1.6TBASE-DR8        1  Jan 06 22:49:53          N/A
Ethernet264   Port34  1600G/8     rs    down     down     none         VendorA ABCD-1234-T6P-CA        1.6TBASE-DR8        0              N/A          N/A
Ethernet288   Port37  1600G/8     rs      up       up     none         VendorB EFGH-5678-HSD-LR1       1.6TBASE-DR8        1  Jan 06 22:51:47          N/A
Ethernet296   Port38  1600G/8     rs      up       up     none         VendorC IJKL-9012-05D-3XX       1.6TBASE-DR8        1  Jan 06 22:51:47          N/A
Ethernet320   Port41  1600G/8     rs    down     down     none         VendorA ABCD-1234-T6P-CA        1.6TBASE-DR8        0              N/A          N/A
Ethernet328   Port42  1600G/8     rs      up       up     none         VendorB EFGH-5678-HSD-LR1       1.6TBASE-DR8        1  Jan 06 22:51:58          N/A
Ethernet352   Port45  1600G/8     rs      up       up     none         VendorC IJKL-9012-05D-3XX       1.6TBASE-DR8        1  Jan 06 22:51:13          N/A
Ethernet360   Port46  1600G/8     rs      up       up     none         VendorA ABCD-1234-E6P-CA        1.6TBASE-DR8        1  Jan 06 22:51:08          N/A
Ethernet384   Port49  1600G/8     rs      up       up     none         VendorB EFGH-5678-HSD-LR1       1.6TBASE-DR8        1  Jan 06 22:50:59          N/A
Ethernet392   Port50  1600G/8     rs    down     down     none         VendorC IJKL-9012-05D-3XX       1.6TBASE-DR8        0              N/A          N/A
Ethernet416   Port53  1600G/8     rs      up       up     none         VendorA ABCD-1234-E6P-CA        1.6TBASE-DR8        1  Jan 06 22:50:46          N/A
Ethernet424   Port54  1600G/8     rs      up       up     none         VendorC IJKL-9012-05D-3XX       1.6TBASE-DR8        1  Jan 06 22:50:48          N/A
Ethernet448   Port57  1600G/8     rs      up       up     none         VendorB EFGH-5678-HSD-6XX       1.6TBASE-DR8        1  Jan 06 22:50:42          N/A
Ethernet456   Port58  1600G/8     rs      up       up     none         VendorA ABCD-1234-E6P-CA        1.6TBASE-DR8        1  Jan 06 22:50:35          N/A
Ethernet480   Port61  1600G/8     rs      up       up     none         VendorA ABCD-1234-E6P-CA        1.6TBASE-DR8        1  Jan 06 22:48:41          N/A
Ethernet488   Port62  1600G/8     rs      up       up     none         VendorB EFGH-5678-HSD-6XX       1.6TBASE-DR8        1  Jan 06 22:48:49          N/A

admin@dvc137:~$ show int l1-summary Ethernet504
  Interface    Alias     Mode    FEC    Oper    Admin    Fault             Transceiver    Media Interface    Flaps          Last Up    Last Down
-----------  -------  -------  -----  ------  -------  -------  ----------------------  -----------------  -------  ---------------  -----------
  Ethernet0    Port1  1600G/8     rs      up       up     none  VendorD MNOP-3456-N00-XX       1.6TBASE-DR8        1  Jan 07 00:18:34          N/A
```

**Column Descriptions:**

| Column          | Description                                              |
|-----------------|----------------------------------------------------------|
| Interface       | Interface name                                           |
| Alias           | Interface alias                                          |
| Mode            | Speed/lanes (e.g., `100G/4` = 100Gbps over 4 lanes)     |
| FEC             | Forward Error Correction mode                            |
| Oper            | Operational status                                       |
| Admin           | Administrative status                                    |
| Fault           | Fault status: `none`, `local`, `remote`, `local+remote` |
| Transceiver     | Vendor and model of transceiver                          |
| Media Interface | Active media interface type (CMIS transceivers)          |
| Flaps           | Link flap count                                          |
| Last Up         | Timestamp of last link up event                          |
| Last Down       | Timestamp of last link down event                        |

### 9.3 Config DB Enhancements

No configuration changes required. This is a show command only.

---

## 10. Warmboot and Fastboot Design Impact

### Impact

None. This feature is a read-only CLI command that does not affect warmboot or fastboot functionality.

### Warmboot and Fastboot Performance Impact

- Does not add any stalls/sleeps/IO operations to the boot critical chain
- Does not add any CPU-heavy processing to the boot path
- Does not update any third-party dependencies
- Not involved in boot sequence at all

---

## 11. Memory Consumption

This feature has negligible memory impact:

- No persistent memory allocation
- Temporary memory is allocated only during command execution
- Memory is released immediately after command completion
- No background processes or daemons

---

## 12. Restrictions/Limitations

1. **CMIS Transceiver Information**: Media interface type is only available for CMIS-compliant transceivers (QSFP-DD, OSFP, etc.). Non-CMIS transceivers will show "N/A".

2. **Fault Status**: Requires `PORT_OPERR_TABLE` to be populated in STATE_DB. If not available, fault status defaults to "none".

3. **Flap Count and Timestamps**: Requires `flap_count`, `last_up_time`, and `last_down_time` fields to be populated in APPL_DB PORT_TABLE. If not available, shows "N/A".

---

## 13. Testing Requirements/Design

### 13.1 Unit Test Cases

| Test Case                                      | Description                                    |
|------------------------------------------------|------------------------------------------------|
| `test_multi_asic_interface_l1_summary`         | Verify l1-summary output on multi-ASIC platform with all interfaces |
| `test_multi_asic_interface_l1_summary_asic1_ethernet64` | Verify filtering by namespace and interface |
| `test_l1_summary_asic0`                        | Verify CLI invokes intfutil with correct arguments |
| `test_l1_summary_all`                          | Verify `-d all` display option handling       |
