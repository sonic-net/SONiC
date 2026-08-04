# CPO Firmware Upgrade Command

## Table of Contents

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Background](#4-background)
  - [4.1 Traditional Transceiver Default Pattern](#41-traditional-transceiver-default-pattern)
  - [4.2 CPO Architecture Speciality](#42-cpo-architecture-speciality)
- [5. Proposed CLI](#5-proposed-cli)
  - [5.1 Port-based Operations](#51-port-based-operations)
  - [5.2 Global Bulk Upgrade with -a Flag](#52-global-bulk-upgrade-with--a-flag)
  - [5.3 show firmware vesion](#53-show-firmware-vesion)
- [6. High-Level Design](#6-high-level-design)
- [7 Target Resolution](#7-target-resolution)
- [8. Locking \& Concurrency](#8-locking--concurrency)
- [9. Status \& Version Display](#9-status--version-display)
- [10. Test Plan](#10-test-plan)

## 1. Revision

| Rev | Date       | Author     | Change Description                                                          |
| --- | ---------- | ---------- | --------------------------------------------------------------------------- |
| 0.1 | 2026-08-02 | KroosMicas | Initial version                                                             |
| 0.2 | 2026-08-07 | KroosMicas | Rework CLI: port-based as default;<br /> add -a for all ports bulk upgrade; |

## 2. Scope

This HLD defines SONiC support for **CPO firmware upgrade** via `cpoutil firmware` command model.

Key design principles:

1. Port-based operations are the default user interface, consistent with traditional `sfputil` transceiver operation habit.
2. Add single optional `-a` flag to perform bulk upgrade for all CPO ports on platform;
3. Mandatory mcu/oe/els subcommand is added before port target:
   Actions without firmware file (unlock/run/commit) cannot parse package to auto-detect component type, must explicitly specify target component.
   Download/upgrade with firmware file also unify the same CLI format for consistent syntax.
4. CPO architecture has multiple ports sharing one MCU/OE/ELS partition; CLI automatically maps input port to corresponding backend hardware instance.

Firmware-bearing entities inside CPO vModule:

* MCU / CMIS controller
* OE (Optical Engine / PRISM)
* ELS (External Laser Source / RLM)

## 3. Definitions/Abbreviations

| **Term** | **Definition/Abbreviations**        |
| -------------- | ----------------------------------------- |
| CDB            | Command Data Block                        |
| CMIS           | Common Management Interface Specification |
| optoe          | Optical Transceiver Open EEPROM driver    |
| EPL            | Extended Payload                          |
| CPO            | Co-packaged optics                        |
| OE             | Optical Engine / PRISM                    |
| ELS/RLM        | External Laser Sources                    |
| MCU            | Microprogrammed Control Unit              |

## 4. Background

### 4.1 Traditional Transceiver Default Pattern

Traditional sfputil firmware operations are port-based:

```
sfputil firmware unlock Ethernet0 
sfputil firmware download Ethernet0  <fw_file>
sfputil firmware run Ethernet0
sfputil firmware commit Ethernet
sfputil firmware upgrade Ethernet0  <fw_file>
```

### 4.2 CPO Architecture Speciality

CPO breaks one-port-one-module mapping: multiple front panel Ethernet ports share a single MCU/OE/ELS hardware partition.

* Port-based input remains default for daily operation.
* `-a` flag provides one-click full-platform bulk upgrade for production deployment.
* For actions without firmware binary input (`unlock / run / commit`), there is no package header to parse and auto-judge target component type. Thus, `mcu/oe/els` subcommand must be explicitly specified in all firmware commands to clarify which partition the operation acts on.

## 5. Proposed CLI

**Unified Command Syntax**

```
cpoutil firmware <action> <component> {EthernetX | -a} [fw_package]
Usage: 
    <action>: unlock / download / run / commit / upgrade
    <component>: mandatory mcu / oe / els
    Target selector: either single port EthernetX (default) or -a (all CPO ports bulk)
    [fw_package]: optional, only required for download / upgrade
```

<action>

<action>

### 5.1 Port-based Operations

Specify component + single front panel port as target:

```
# No firmware file (unlock/run/commit)
cpoutil firmware unlock mcu Ethernet0
cpoutil firmware run oe Ethernet0
cpoutil firmware commit els Ethernet0

# With firmware file (download / one-step upgrade)
cpoutil firmware download mcu Ethernet0 mcu_fw.bin
cpoutil firmware upgrade oe Ethernet0 oe_fw.bin
```

Behavior:

* Explicit component subcommand defines target partition;
* Resolve all ports sharing the same target component instance, print affected port list and prompt user confirmation `[N/Y]`.

### 5.2 Global Bulk Upgrade with -a Flag

Append -a flag to command to trigger upgrade for all CPO ports on platform; no port argument needed.

```
# Bulk unlock/run/commit all ports for target component
cpoutil firmware unlock mcu -a
cpoutil firmware run oe -a
cpoutil firmware commit els -a

# Bulk download / full upgrade all ports
cpoutil firmware download mcu -a mcu_fw.bin
cpoutil firmware upgrade els -a rlm_fw.bin
```

Bulk upgrade behavior:

1. Enumerate all valid CPO ports from cpo.json config automatically.
2. Execute component-specific workflow sequentially for every port.
3. Print full port list affected before workflow start, require user confirmation.
4. Acquire global chassis lock to block other CPO firmware operations during bulk upgrade.
5. Restriction: Cannot mix Ethernet port argument and -a flag in one command, parser throws syntax error.

### 5.3 show firmware vesion

Consistent component + port / -a syntax:

```
# Single port component version
cpoutil show fwversion mcu Ethernet0
cpoutil show fwversion oe Ethernet0
cpoutil show fwversion els Ethernet0

# Dump target component version of all CPO ports
cpoutil show fwversion mcu -a
cpoutil show fwversion oe -a
cpoutil show fwversion els -a
```

## 6. High-Level Design

```
cpoutil firmware <action> <comp> {EthernetX | -a} [fw_package]
        ↓
CPO target resolver
        ├─ If EthernetX: map port to bound mcu/oe/els component instance
        └─ If -a: expand to all CPO ports for specified component
        ↓
CPO firmware upgrade manager (locking + user confirmation prompt)
        ↓
CpoCmisApi CDB upgrade handler
        ↓
CdbFw / XcvrEeprom
        ↓
optoe / CMIS CDB access
        ↓
I2C MCU / OE / ELS hardware
```

**Component Roles**

| Component                      | Responsibility                                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| cpoutil                        | CLI parser; enforce mandatory mcu/oe/els subcommand; distinguish port target vs`-a` bulk flag; reject mixed port + `-a` input                                  |
| CPO target resolver            | 1. Map Ethernet port to bound MCU/OE/ELS entity<br />2. Expand`-a`flag to full list of all CPO ports<br />3. Collect all dependent ports for confirmation prompt |
| CPO firmware upgrade manager   | Manage instance/chassis lock; list affected ports/hardware and wait user confirmation before running CDB workflow                                                  |
| CpoCmisApi CDB upgrade handler | Execute standard CDB command sequence (0x0100/0101/0102/0104/0107/0109/010A)                                                                                       |
| CdbFw                          | CMIS/CDB XcvrEeprom read-write API                                                                                                                                 |
| optoe driver                   | CMIS EEPROM low-level access                                                                                                                                       |

## 7 Target Resolution

**Case 1 Single Port Operation**

```
cpoutil firmware upgrade oe Ethernet0 oe_fw.bin
        ↓
Resolver map Ethernet0 to bound OE instance
        ↓
Prompt all shared affected ports, wait Y confirmation,defaut is N(Not upgrade).
eg:This will affect Ethernet0 Ethernet8 Ethernet16 Ethernet24 Ethernet32 Ethernet40 Ethernet48 Ethernet56, Are you sure you want to continue? [N/Y]
        ↓
Execute full OE upgrade CDB sequence
```

**Case 2 Bulk -a All Ports Operation
**

```
cpoutil firmware run mcu -a
        ↓
Enumerate all CPO ports on chassis bound to MCU
        ↓
Print full port list, request user confirmation
eg:This will affect all Ports, Are you sure you want to continue? [N/Y]
        ↓
Acquire chassis global lock, sequentially run MCU run operation for all ports
```

## 8. Locking & Concurrency

| Target Mode            | Lock Scope                              | Restriction Rules                                             |
| ---------------------- | --------------------------------------- | ------------------------------------------------------------- |
| mcu/oe/els + EthernetX | Only hardware entity bound to this port | Block concurrent operations targeting same MCU/OE/ELS         |
| mcu/oe/els + -a        | Entire chassis all CPO hardware         | Block all other cpoutil firmware commands during bulk upgrade |

General rules:

* Block overlapping upgrades sharing same underlying MCU/OE/ELS resource
* Disable all firmware operations during warm / fast reboot
* `-a` bulk upgrade holds exclusive highest priority chassis lock

## 9. Status & Version Display

Single port query output

```
cpoutil show fwversion mcu Ethernet0
```

Example output:

```
MCU (CMIS):
  Active: 1.2.0
  Inactive: 1.3.0
```

Full platform dump with -a

```
cpoutil show fwversion oe -a
```

Iterate every CPO port and print corresponding MCU/OE/ELS version info one by one.

## 10. Test Plan

**Unit Tests**

* CLI parser validation: port as default target, support `-a` flag, reject port + `-a` mixed input
* CLI parser verify mcu/oe/els is mandatory subcommand, reject commands missing component.
* `-a` flag enumerates all CPO ports defined in cpo.json
* Port-to-component mapping lookup correctness.

**Integration Tests**

* Single port full workflow: unlock → download → run → commit  and upgrade for mcu/oe/els respectively.
* `-a` bulk upgrade all CPO ports end-to-end
* Confirm user prompt lists all affected ports for single port and `-a` mode
* Post-upgrade version verification via `show fwversion` single port / `-a`

**Negative Tests**

* Mix Ethernet port and `-a` flag in one command (syntax error rejected)
* Missing mcu/oe/els subcommand (CLI syntax error rejected).
* Invalid port name or unsupported component keyword.
* Concurrent firmware operation on same hardware entity (blocked by lock)
* Execute firmware commands during warm/fast reboot (rejected)
* Interrupted upgrade recovery for single port and `-a` bulk upgrade mode
