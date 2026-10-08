# CPO Firmware Upgrade Command

## Table of Contents


- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Background](#4-background)
  - [4.1 Traditional Transceiver Default Pattern](#41-traditional-transceiver-default-pattern)
  - [4.2 CPO Architecture Speciality](#42-cpo-architecture-speciality)
  - [4.3 Persistent Target Mode Background](#43-persistent-target-mode-background)
- [5. Proposed CLI](#5-proposed-cli)
  - [5.1 Unified Command Syntax](#51-unified-command-syntax)
  - [5.2 Port-based Operations](#52-port-based-operations)
    - [5.2.1 unlock (support --password)](#521-unlock-support---password)
    - [5.2.2 download](#522-download)
    - [5.2.3 run](#523-run)
    - [5.2.4 commit](#524-commit)
    - [5.2.5 upgrade (one-step full flow, support --password)](#525-upgrade-one-step-full-flow-support---password)
  - [5.3 Global Bulk Upgrade with -a Flag](#53-global-bulk-upgrade-with--a-flag)
  - [5.4 show firmware vesion](#54-show-firmware-vesion)
  - [5.5 Persistent Target Mode CLI](#55-persistent-target-mode-cli)
    - [5.5.1 Set persistent target](#551-set-persistent-target)
    - [5.5.2 List all persisted targets](#552-list-all-persisted-targets)
    - [5.5.3 Clear one persisted target](#553-clear-one-persisted-target)
    - [5.5.4 Clear all persisted targets](#554-clear-all-persisted-targets)
- [6. High-Level Design](#6-high-level-design)
- [7. Command Resolution](#7-command-resolution)
- [8. Persistent Target Mode StateDB Design](#8-persistent-target-mode-statedb-design)
  - [8.1 StateDB Table: CPO\_FIRMWARE\_TARGET](#81-statedb-table-cpo_firmware_target)
  - [8.2 Table lifecycle rules](#82-table-lifecycle-rules)
  - [8.3 Mutual‑exclusion / conflict check logic](#83-mutualexclusion--conflict-check-logic)
  - [8.4 State transition rules](#84-state-transition-rules)
- [9. Firmware Upgrade Execution Sequence Constraint](#9-firmware-upgrade-execution-sequence-constraint)
- [10. Locking \& Concurrency](#10-locking--concurrency)
- [11. Status \& Version Display](#11-status--version-display)
- [12. Command ↔ Standard CDB Handler API Mapping](#12-command--standard-cdb-handler-api-mapping)
- [13. Test Plan](#13-test-plan)


## 1. Revision

| Rev | Date       | Author     | Change Description                                                                                                                                                                                        |
| --- | ---------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1 | 2026-08-02 | KroosMicas | Initial version                                                                                                                                                                                           |
| 0.2 | 2026-08-07 | KroosMicas | Rework CLI: port-based as default;<br /> add -a for all ports bulk upgrade;<br />Add full command ↔ CPO CMIS API mapping chapter, API implementation reference HLD: CPO Firmware Upgrade CMIS Bailly API |
| 1.0 | 2026-08-12 | KroosMicas | Add Persistent target mode feature for cpoutil firmware; add StateDB table CPO_FIRMWARE_TARGET design; add mutual‑exclusion logic, state transition, CLI interaction                                     |

## 2. Scope

This HLD defines SONiC support for **CPO firmware upgrade** via `cpoutil firmware` command model.

Key design points:

1. Port-based operations are the default user interface, consistent with traditional `sfputil` transceiver operation habit.
2. Add single optional `-a` flag to perform bulk upgrade for all CPO ports on platform;
3. Mandatory mcu/oe/els subcommand is added before port target:
   Actions without firmware file (unlock/run/commit) cannot parse package to auto-detect component type, must explicitly specify target component.
   Download/upgrade with firmware file also unify the same CLI format for consistent syntax.
4. CPO architecture has multiple ports sharing one MCU/OE/ELS partition; CLI automatically maps input port to corresponding backend hardware instance.
5. Add  **Persistent Target Mode** : allow user pre‑select firmware target (component + physical instance). Subsequent operations can work against persisted target without repeating port/component arguments; persist metadata inside StateDB `CPO_FIRMWARE_TARGET`.

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

### 4.3 Persistent Target Mode Background

In debug / interactive development workflow, users repeatedly execute a sequence of `unlock → download → run → commit` against  **same physical CPO instance** .
Persistent Target Mode solves this:

1. User runs cpoutil firmware target `component + port` once to select target.
2. System resolves to physical hardware instance, persist metadata in state_db CPO_FIRMWARE_TARGET.
3. Support multiple persisted target entries (different physical instances).When adding new target, enforce mutual‑exclusion check via cpo.json physical‑device mapping: same component‑physical‑instance cannot have multiple entries; prompt user for overwrite confirmation if conflict detected.

## 5. Proposed CLI

### 5.1 Unified Command Syntax

```
cpoutil firmware <action> <component> {EthernetX | -a} [fw_package] [--password <pwd>]
Usage: 
    <action>: unlock / download / run / commit / upgrade / target
    <component>: mandatory mcu / oe / els  (when not using target mode)
    Target selector: either single port EthernetX (default) or -a (all CPO ports bulk)
    [fw_package]: optional, only required for download / upgrade
    [--password <pwd>]: optional parameter only valid for unlock / upgrade actions
```

<action>

<action>

### 5.2 Port-based Operations

Behavior:

* Explicit component subcommand defines target partition;
* Resolve all ports sharing the same target component instance, print affected port list and prompt user confirmation `[N/Y]`.

#### 5.2.1 unlock (support --password)

```
cpoutil firmware unlock mcu Ethernet0 --password 123456
cpoutil firmware unlock oe Ethernet0
cpoutil firmware unlock els Ethernet0 --password abcdef
```

#### 5.2.2 download

```
cpoutil firmware download mcu Ethernet0 mcu.bin
cpoutil firmware download oe Ethernet0 oe.bin
cpoutil firmware download els Ethernet0 rlm.bin
```

#### 5.2.3 run

```
cpoutil firmware run mcu Ethernet0
cpoutil firmware run oe Ethernet0
cpoutil firmware run els Ethernet0
```

#### 5.2.4 commit

```
cpoutil firmware commit mcu Ethernet0
cpoutil firmware commit oe Ethernet0
cpoutil firmware commit els Ethernet0
```

#### 5.2.5 upgrade (one-step full flow, support --password)

```
cpoutil firmware upgrade mcu Ethernet0 mcu.bin --password 123456
cpoutil firmware upgrade oe Ethernet0 oe.bin
cpoutil firmware upgrade els Ethernet0 rlm.bin --password abcdef
```

### 5.3 Global Bulk Upgrade with -a Flag

Append -a flag to command to trigger upgrade for all CPO ports on platform; no port argument needed.

```
# unlock bulk
cpoutil firmware unlock mcu -a --password 123456
cpoutil firmware unlock oe -a
# download bulk
cpoutil firmware download oe -a oe.bin
# run bulk
cpoutil firmware run els -a
# commit bulk
cpoutil firmware commit mcu -a
# upgrade bulk
cpoutil firmware upgrade els -a rlm.bin --password abcdef
```

Bulk upgrade behavior:

1. Enumerate all valid CPO ports from cpo.json config automatically.
2. Execute component-specific workflow sequentially for every port.
3. Print full port list affected before workflow start, require user confirmation.
4. Acquire global chassis lock to block other CPO firmware operations during bulk upgrade.
5. Restriction: Cannot mix Ethernet port argument and -a flag in one command, parser throws syntax error.

### 5.4 show firmware vesion

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

### 5.5 Persistent Target Mode CLI

#### 5.5.1 Set persistent target

```
cpoutil firmware target <component> <EthernetX>
```

Example:

```
cpoutil firmware target oe Ethernet0
cpoutil firmware target mcu Ethernet56
```

* On execution: resolve port → physical‑instance from `cpo.json`. Insert / update entry into StateDB `CPO_FIRMWARE_TARGET`.
* Conflict scenario example (same physical OE0 already present in DB):

```
WARNING: Physical instance oe:OE0 already exists in target table (state: downloading).
Overwrite existing persistent target entry? [N/Y]
```

#### 5.5.2 List all persisted targets

Display the current specified list of targets

```
cpoutil firmware target list
```

Sample output:

```
CPO firmware targets:
MCU0| cur_component:OE0    Ref_Ports:Ethernet0,  Ethernet8,  Ethernet16..., Ethernet48  State:downloading
MCU7| cur_component:ELS16  Ref_Ports:Ethernet448,Ethernet456,Ethernet464...,Ethernet504 State:unlocked
```

#### 5.5.3 Clear one persisted target

An example of the application scenario for this command: Currently, the target is the unlocked stage of oe0, but we do not want to proceed with the subsequent upgrade of oe0. Instead, we want to use it for the upgrade of mcu0.

```
cpoutil firmware target clear <component> <EthernetX>
```

#### 5.5.4 Clear all persisted targets

```
cpoutil firmware target clear ‑a
```

## 6. High-Level Design

```
cpoutil firmware <action> <comp> {EthernetX | -a} [fw_package]
        ↓
CPO target resolver
        ├─ Check whether persistent‑target‑shortcut mode applies,mandatory mcu/oe/els unless valid single persistent target exists
        ├─ Validate --password only exists on unlock/upgrade
        ├─ If EthernetX: map port to bound mcu/oe/els component instance
        └─ Reject mixed port + -a input
        ↓
CPO firmware upgrade manager (locking + user confirmation prompt)
        ├─ Collect affected ports & user confirmation prompt
        └─  (StateDB manager) Update StateDB CPO_FIRMWARE_TARGET state field on each action start / finish
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

| Component                      | Responsibility                                                                                                                                                                                                                                                                                  |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cpoutil                        | CLI parser; enforce mandatory mcu/oe/els subcommand; distinguish port target vs`-a` bulk flag; reject mixed port + `-a` input                                                                                                                                                               |
| CPO target resolver            | 1.Check whether persistent‑target‑shortcut mode applies,mandatory mcu/oe/els unless valid single persistent target exists<br />2.Validate --password only exists on unlock/upgrade<br />3.Map Ethernet port to bound MCU/OE/ELS entity<br />4. Expand`-a`flag to full list of all CPO ports |
| CPO firmware upgrade manager   | 1.Manage instance/chassis lock;<br />2.list affected ports/hardware and wait user confirmation before running CDB workflow<br />3.update runtime state into persistent‑target DB entry                                                                                                         |
| CpoCmisApi CDB upgrade handler | Execute standard CDB command sequence (0x0100/0101/0102/0104/0107/0109/010A)                                                                                                                                                                                                                    |
| CdbFw                          | CMIS/CDB XcvrEeprom read-write API                                                                                                                                                                                                                                                              |
| optoe driver                   | CMIS EEPROM low-level access                                                                                                                                                                                                                                                                    |

## 7. Command Resolution

**Case 1 Single Port Operation**

```
cpoutil firmware upgrade oe Ethernet0 oe_fw.bin
        ↓
Resolver map Ethernet0 to bound OE instance.Check whether persistent‑target mode applies.
        ↓
If not conflict with current target mode, Prompt all shared affected ports, wait Y confirmation,defaut is N(Not upgrade).
eg:This will affect Ethernet0 Ethernet8 Ethernet16 Ethernet24 Ethernet32 Ethernet40 Ethernet48 Ethernet56, Are you sure you want to continue? [N/Y]
        ↓
Execute full OE upgrade CDB sequence.
If current target mode exist, update runtime state into persistent‑target DB entry
```

**Case 2 Bulk -a All Ports Operation**

```
cpoutil firmware run mcu -a
        ↓
Enumerate all CPO ports on chassis bound to MCU.Check whether persistent‑target mode applies.
        ↓
If not conflict with current target mode, Print full port list, request user confirmation
eg:This will affect all Ports, Are you sure you want to continue? [N/Y]
        ↓
Acquire chassis global lock, sequentially run MCU run operation for all ports
If current target mode exist, update runtime state into persistent‑target DB entry
```

**Case 3 Persistent‑target shortcut flow**

```
cpoutil firmware target oe Ethernet0
        ↓
Check whether persistent‑target mode applies.
If not conflict with current target mode, insert entry into StateDB CPO_FIRMWARE_TARGET.
        ↓
cpoutil firmware download oe Ethernet0 oe.bin
        ↓
cpoutil firmware download mcu Ethernet0 mcu.bin
CLI detect conflicting with current target mode. Print warning:
WARNING: Physical instance oe:OE0 already exists in target table (state: downloaded).
Overwrite existing persistent target entry? [N/Y]N
        ↓
cpoutil firmware download run Ethernet0
        ↓
Update entry state to `running`
        ↓
Invoke corresponding CDB handler sequence
        ↓
On finish update entry state to `ran`
```

## 8. Persistent Target Mode StateDB Design

### 8.1 StateDB Table: CPO_FIRMWARE_TARGET

StateDB global table. Primary key format: <component></component>|<physical_instance_id>

Since the conflict of the target is based on the conflict of the CMIS controller, therefore, in this case, the CMIS controller MCU is used as the physical_instance_id key.

e.g. MCU0/MCU1

| Field          | Type             | Description                                                                                                                                                          |
| -------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cur_component  | string           | MCU0/OE0/ELS0                                                                                                                                                        |
| ref_components | string           | Physical hardware instance id from`cpo.json`e.g. OE0, MCU0, ELS0, ELS1                                                                                             |
| ref_ports      | string list      | All front‑panel Ethernet ports referencing this physical instance.<br />eg: [Ethernet0 Ethernet8 Ethernet16 Ethernet24 Ethernet32 Ethernet40 Ethernet48 Ethernet56] |
| state          | string           | Runtime state enum:`idle`/`unlocking`/`unlocked`/`downloading`/`downloaded`/`runing`/`ran/ commiting/ committed`/`upgrading`/`upgraded/ error`     |
| last_error     | string(optional) | Last failure error message                                                                                                                                           |

Example DB entry key‑value:

```
KEY: CPO_FIRMWARE_TARGET|MCU0
    cur_component : OE0
    ref_components : "OE0, MCU0, ELS0, ELS1"
    ref_ports : "Ethernet0,Ethernet8,Ethernet16,Ethernet24,Ethernet32,Ethernet40,Ethernet48,Ethernet56"
    state : downloaded
    last_error : ""
```

### 8.2 Table lifecycle rules

* **System reboot** : Entries in `CPO_FIRMWARE_TARGET` are  **automatically cleared** . No persistent config DB backing.
* **`config reload`** :  **Preserve all entries in StateDB** , config‑reload does not touch running StateDB runtime state, CDB session is not disturbed.
* Process crash/restart: entries remain in StateDB;

### 8.3 Mutual‑exclusion / conflict check logic

When executing **cpoutil firmware target** `comp + port`:

1. Resolve port → `component` + `physical_instance_id` from `cpo.json`.
2. Use **physical instance**  related CMIS controller MCU as key to look up inside `CPO_FIRMWARE_TARGET`.
3. If key already exist in `CPO_FIRMWARE_TARGET`(same physical hardware instance already persisted):
   1. Print warning:`show current component, ref_components, ref_ports, current stored state.`
   2. Prompt user:` Overwrite existing persistent target entry? [N/Y]`
   3. `Y`: overwrite DB entry; reset state=`idle`.
   4. `N:`abort target‑set operation without DB modification.
4. if key does **not** exist: insert new DB entry, set state=`idle`.

> Note: Multiple different physical‑instance entries are allowed in table. Conflict only applies to **CMIS controller** . Different physical‑instances witch differernt CMIS controller can co‑exist in table.

### 8.4 State transition rules

Each cpoutil firmware action updates the state field of corresponding persistent‑target DB entry if **same physical‑instance** target table exist:

* Before starting action: set state to action‑in‑progress state (`unlocking` / `downloading` / `runing` / `committed` / `upgrading`).
* Action complete success: set state to final state (`unlocked` / `downloaded` / `ran` / `committed / upgraded`).
* Action fails / exception: set state=`error`; fill `last_error` field with error string.
* `cpoutil firmware target clear`: delete target entry.

## 9. Firmware Upgrade Execution Sequence Constraint

Hardware cross-partition dependency rule enforced by upgrade manager:

1. If user intends to upgrade multiple partition types (OE -> MCU/ELS):

   The full OE workflow `unlock → download → run → commit` must finish completely before triggering any MCU or ELS upgrade command.
2. System check before every MCU/ELS upgrade entry:

   CPO manager query OE firmware running & committed status via CDB 0x0100 status API.

   If OE upgrade incomplete / uncommitted, reject MCU/ELS upgrade and output error prompt:

   `Error: OE firmware upgrade flow unfinished, complete OE unlock/download/run/commit first before MCU/ELS operation`
3. MCU and ELS upgrade have same sequential restriction with OE

## 10. Locking & Concurrency

| Target Mode            | Lock Scope                              | Restriction Rules                                             |
| ---------------------- | --------------------------------------- | ------------------------------------------------------------- |
| mcu/oe/els + EthernetX | Only hardware entity bound to this port | Block concurrent operations targeting same MCU/OE/ELS         |
| mcu/oe/els + -a        | Entire chassis all CPO hardware         | Block all other cpoutil firmware commands during bulk upgrade |

General rules:

* Block overlapping upgrades sharing same underlying MCU/OE/ELS resource
* Disable all firmware operations during warm / fast reboot
* `-a` bulk upgrade holds exclusive highest priority chassis lock

## 11. Status & Version Display

**Single port query output**

```
cpoutil show fwversion mcu Ethernet0
```

Example output:

```
MCU (CMIS):
  Active: 1.2.0
  Inactive: 1.3.0
```

**Full platform dump with -a**

```
cpoutil show fwversion oe -a
```

Iterate every CPO port and print corresponding MCU/OE/ELS version info one by one.

**Persistent‑target list output**

```
cpoutil firmware target list
CPO firmware targets:
MCU0| cur_component:OE0    Ref_Ports:Ethernet0,  Ethernet8,  Ethernet16..., Ethernet48  State:downloading
MCU7| cur_component:ELS16  Ref_Ports:Ethernet448,Ethernet456,Ethernet464...,Ethernet504 State:unlocked
```

## 12. Command ↔ Standard CDB Handler API Mapping

All underlying API implementation logic refers to independent design document: **HLD: CPO Firmware Upgrade CMIS Bailly API**

**Common Rule**

1. Unified community standard `CdbFwHandler` methods reused for all partitions; no custom function names.
2. Partition differentiation via dedicated handle instances:
   * MCU partition: `api.cdb_mcu_fw_hdlr`
   * OE partition: `api.cdb_oe_fw_hdlr`
   * ELS partition: `api.cdb_els_fw_hdlr`
3. Composite `upgrade` command internally invokes full sequence: `enter_password → start_fw_download → write block loop → complete_fw_download → run_fw_image → commit_fw_image`
4. All CDB opcode mapping aligns with base CdbFwHandler definition:

| Handler Method                 | CDB Opcode | Function Description                             |
| ------------------------------ | ---------- | ------------------------------------------------ |
| enter_password(password)       | 0x0001     | CDB authentication unlock                        |
| get_fw_status()                | 0x0100     | Query firmware bank status & last command result |
| start_fw_download(imgpath)     | 0x0101     | Initialize firmware download session             |
| abort_fw_download()            | 0x0102     | Terminate incomplete download session            |
| write_lpl_block(address, data) | 0x0103     | Write LPL payload chunk                          |
| write_epl_block(address, data) | 0x0104     | Write EPL payload chunk                          |
| complete_fw_download()         | 0x0107     | Finish download & trigger MCU image validation   |
| run_fw_image(mode)             | 0x0109     | Switch active firmware bank & soft reset         |
| commit_fw_image()              | 0x010A     | Persist running image to non-volatile boot bank  |

**Full Mapping Table**

| CLI Command Segment                                         | Target Partition Handler Call Logic                                                                                                                                                                                                    |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| cpoutil firmware unlock mcu {port/-a} [--password pwd]      | `api.cdb_mcu_fw_hdlr.enter_password(password)`                                                                                                                                                                                       |
| cpoutil firmware unlock oe {port/-a} [--password pwd]       | `api.cdb_oe_fw_hdlr.enter_password(password)`                                                                                                                                                                                        |
| cpoutil firmware unlock els {port/-a} [--password pwd]      | `api.cdb_els_fw_hdlr.enter_password(password)`                                                                                                                                                                                       |
| cpoutil show fwversion mcu {port/-a}                        | `api.cdb_mcu_fw_hdlr.get_fw_status()`(0x0100)                                                                                                                                                                                        |
| cpoutil show fwversion oe {port/-a}                         | `api.cdb_oe_fw_hdlr.get_fw_status()`(0x0100)                                                                                                                                                                                         |
| cpoutil show fwversion els {port/-a}                        | `api.cdb_els_fw_hdlr.get_fw_status()`(0x0100)                                                                                                                                                                                        |
| cpoutil firmware download mcu {port/-a} img                 | 1.`api.cdb_mcu_fw_hdlr.start_fw_download(imgpath)`(0x0101)<br />2. Loop`write_lpl_block`/`write_epl_block`(0x0103/0x0104)<br />3.`api.cdb_mcu_fw_hdlr.complete_fw_download()`(0x0107)                                          |
| cpoutil firmware download oe {port/-a} img                  | 1.`api.cdb_oe_fw_hdlr.start_fw_download(imgpath)`(0x0101)<br />2. Loop`write_lpl_block`/`write_epl_block`(0x0103/0x0104,)<br />3.`api.cdb_oe_fw_hdlr.complete_fw_download()`(0x0107)                                           |
| cpoutil firmware download els {port/-a} img                 | 1.`api.cdb_els_fw_hdlr.start_fw_download(imgpath)`(0x0101)<br />2. Loop`write_lpl_block`/`write_epl_block`(0x0103/0x0104)<br />3.`api.cdb_els_fw_hdlr.complete_fw_download()`(0x0107)                                          |
| cpoutil firmware run mcu {port/-a}                          | `api.cdb_mcu_fw_hdlr.run_fw_image(mode=0x01)`(0x0109)                                                                                                                                                                                |
| cpoutil firmware run oe {port/-a}                           | `api.cdb_oe_fw_hdlr.run_fw_image(mode=0x01)`(0x0109)                                                                                                                                                                                 |
| cpoutil firmware run els {port/-a}                          | `api.cdb_els_fw_hdlr.run_fw_image(mode=0x01)`(0x0109)                                                                                                                                                                                |
| cpoutil firmware commit mcu {port/-a}                       | `api.cdb_mcu_fw_hdlr.commit_fw_image()`(0x010A)                                                                                                                                                                                      |
| cpoutil firmware commit oe {port/-a}                        | `api.cdb_oe_fw_hdlr.commit_fw_image()`(0x010A)                                                                                                                                                                                       |
| cpoutil firmware commit els {port/-a}                       | `api.cdb_els_fw_hdlr.commit_fw_image()`(0x010A)                                                                                                                                                                                      |
| cpoutil firmware upgrade mcu {port/-a} img [--password pwd] | Composite sequential calls:<br />1.`cdb_mcu_fw_hdlr.enter_password(password)`<br />2. Full download sequence (start + block write + complete)<br />3.`cdb_mcu_fw_hdlr.run_fw_image()`<br />4.`cdb_mcu_fw_hdlr.commit_fw_image()` |
| cpoutil firmware upgrade oe {port/-a} img [--password pwd]  | Composite sequential calls:<br />1.`cdb_oe_fw_hdlr.enter_password(password)`<br />2. Full download sequence (start + block write + complete)<br />3.`cdb_oe_fw_hdlr.run_fw_image()`<br />4.`cdb_oe_fw_hdlr.commit_fw_image()`    |
| cpoutil firmware upgrade els {port/-a} img [--password pwd] | Composite sequential calls:<br />1.`cdb_els_fw_hdlr.enter_password(password)`<br />2. Full download sequence (start + block write + complete)<br />3.`cdb_els_fw_hdlr.run_fw_image()`<br />4.`cdb_els_fw_hdlr.commit_fw_image()` |

> The "cpoutil firmware target" command only involves database operations and does not require the invocation of APIs.

## 13. Test Plan

**Unit Tests**

* CLI parser validation: port as default target, support `-a` flag, reject port + `-a` mixed input
* CLI parser verify mcu/oe/els is mandatory subcommand, reject commands missing component(when not using target mode).
* `-a` flag enumerates all CPO ports defined in cpo.json
* Port-to-component mapping lookup correctness.
* Persistent‑target unit tests:
  * cpoutil firmware target `comp + port` writes correct entry into StateDB CPO_FIRMWARE_TARGET.
  * Conflict‑check: same physical‑instance triggers overwrite prompt; N aborts; Y overwrites and resets state.
  * `target list` / `target clear` / `target clear‑all` operate StateDB correctly.
  * Table lifecycle test: simulated reboot clears table; simulated config‑reload preserves table entries.
  * Action‑driven DB state transition test: unlock/download/run/commit/upgrade/error update DB `state` and `last_error`.

**Integration Tests**

* Single port full workflow: unlock → download → run → commit  and upgrade for mcu/oe/els respectively.
* Execute MCU upgrade before OE finish, verify error prompt output.
* Single port unlock/upgrade with --password parameter pass value to underlying API.
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
