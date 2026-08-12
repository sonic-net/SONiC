# HLD: cpoutil – SONiC CLI Utility for CPO (Co-Packaged Optics)

## Table of Contents

- [1.Revision](#1revision)
- [2.Scope](#2scope)
- [3.Definitions/Abbreviations](#3definitionsabbreviations)
- [4.Overview](#4overview)
- [5.Requirements](#5requirements)
  - [5.1.Functional Requirements](#51functional-requirements)
  - [5.2.Non-Functional Requirements](#52non-functional-requirements)
- [6.Architecture Design](#6architecture-design)
- [7.High-Level Design](#7high-level-design)
  - [7.1.CLI Command Hierarchy Overview](#71cli-command-hierarchy-overview)
- [8.Command Functional Specification](#8command-functional-specification)
  - [8.1.cpoutil show (Read-only Query Commands)](#81cpoutil-show-read-only-query-commands)
    - [8.1.1.cpoutil show interface map \[PORT\]](#811cpoutil-show-interface-map-port)
    - [8.1.2.cpoutil show interface dom \[PORT\]](#812cpoutil-show-interface-dom-port)
    - [8.1.3.cpoutil show interface tx\_disable \[PORT\]](#813cpoutil-show-interface-tx_disable-port)
    - [8.1.4.cpoutil show interface speed \[PORT\]](#814cpoutil-show-interface-speed-port)
    - [8.1.5.cpoutil show interface lane-status \[PORT\]](#815cpoutil-show-interface-lane-status-port)
    - [8.1.6.cpoutil show oe lpmode \[OE\_INDEX\]](#816cpoutil-show-oe-lpmode-oe_index)
    - [8.1.7.cpoutil show oe status \[OE\_INDEX\]](#817cpoutil-show-oe-status-oe_index)
    - [8.1.8.cpoutil show oe temperature \[OE\_INDEX\]](#818cpoutil-show-oe-temperature-oe_index)
    - [8.1.9.cpoutil show oe input-power \[OE\_INDEX\]](#819cpoutil-show-oe-input-power-oe_index)
    - [8.1.10.cpoutil show els presence \[ELS\_INDEX\]](#8110cpoutil-show-els-presence-els_index)
    - [8.1.11.cpoutil show els lpmode \[ELS\_INDEX\]](#8111cpoutil-show-els-lpmode-els_index)
    - [8.1.12.cpoutil show els status \[ELS\_INDEX\]](#8112cpoutil-show-els-status-els_index)
    - [8.1.13.cpoutil show els temperature \[ELS\_INDEX\]](#8113cpoutil-show-els-temperature-els_index)
    - [8.1.14.cpoutil show els output-power \[ELS\_INDEX\]](#8114cpoutil-show-els-output-power-els_index)
  - [8.2.cpoutil config (Hardware Control Commands)](#82cpoutil-config-hardware-control-commands)
    - [8.2.1.cpoutil config interface tx-disable PORT](#821cpoutil-config-interface-tx-disable-port)
    - [8.2.2.cpoutil config oe lpmode OE\_INDEX](#822cpoutil-config-oe-lpmode-oe_index)
    - [8.2.3.cpoutil config oe reset OE\_INDEX](#823cpoutil-config-oe-reset-oe_index)
    - [8.2.4.cpoutil config oe tx-disable OE\_INDEX](#824cpoutil-config-oe-tx-disable-oe_index)
    - [8.2.5.cpoutil config els lpmode ELS\_INDEX](#825cpoutil-config-els-lpmode-els_index)
    - [8.2.6.cpoutil config els reset ELS\_INDEX](#826cpoutil-config-els-reset-els_index)
    - [8.2.7.cpoutil config els tx-disable ELS\_INDEX](#827cpoutil-config-els-tx-disable-els_index)
  - [8.3.cpoutil read-eeprom / write-eeprom (Low-level EEPROM Access)](#83cpoutil-read-eeprom--write-eeprom-low-level-eeprom-access)
    - [8.3.1.cpoutil read-eeprom oe](#831cpoutil-read-eeprom-oe)
    - [8.3.2.cpoutil read-eeprom els](#832cpoutil-read-eeprom-els)
    - [8.3.3.cpoutil write-eeprom oe](#833cpoutil-write-eeprom-oe)
    - [8.3.4.cpoutil write-eeprom els](#834cpoutil-write-eeprom-els)
- [9.Warmboot and Fastboot Design Impact](#9warmboot-and-fastboot-design-impact)
- [10.Memory Consumption](#10memory-consumption)
- [11.Restrictions/Limitations](#11restrictionslimitations)
- [12.Testing Requirements/Design](#12testing-requirementsdesign)
  - [12.1.Unit Test](#121unit-test)
  - [12.2.Platform Functional Test](#122platform-functional-test)
  - [12.3.Integration Test](#123integration-test)
  - [12.4.Edge Case Test](#124edge-case-test)
- [13.Open/Action Items](#13openaction-items)

## 1.Revision

| Rev | Date       | Author     | Description                                                                |
| --- | ---------- | ---------- | -------------------------------------------------------------------------- |
| 1.0 | 2026-08-11 | KroosMicas | Initial Draft                                                              |
| 1.1 | 2026-09-1  | KroosMicas | Update scope; add descriptions for vendor‑specific fields in`show dom`. |

## 2.Scope

This document defines the high-level design of `cpoutil`, a platform CLI utility to manage CPO OE (Optical Engine) and ELS (Electrical Laser Source) modules on SONiC.
**The scope includes:**

1. `cpoutil show` read-only status queries
2. `cpoutil config` module configuration controls
3. `cpoutil read-eeprom / write-eeprom` low-level CMIS EEPROM access

**Out of scope:**

1. All `cpoutil firmware` subcommands (see separate linked design document:[github.com/sonic-net/SONiC/pull/2484](https://github.com/sonic-net/SONiC/pull/2484))
2. Non-CMIS proprietary vendor registers
3. The current design document only targets `cpoutil`, the debug command for direct register access. CLI commands such as `show interfaces transceiver` that retrieve data from the database will be covered in the subsequent CPO CLI design.

## 3.Definitions/Abbreviations

| **Term** | **Definition/Abbreviations**        |
| -------------- | ----------------------------------------- |
| CMIS           | Common Management Interface Specification |
| CPO            | Co-packaged optics                        |
| OE             | Optical Engine / PRISM                    |
| ELS/RLM        | External Laser Sources                    |

## 4.Overview

`cpoutil` is a SONiC platform command-line utility designed for debug, validation and manual provisioning of CPO OE and ELS modules.
It follows the same CLI user experience pattern as `sfputil`.
`cpoutil` relies on platform provided `cpo.json` to resolve front-panel ports to underlying OE/ELS instances and lanes.
All hardware register access is abstracted via platform HAL to maintain platform agnostic CLI logic.

Major capabilities:

- Query port-level aggregated OE/ELS status, lane state, speed, DOM, optical power
- Direct OE/ELS instance level status, temperature, low power mode query
- Configuration control: Tx-disable, low power mode, hardware reset, datapath speed
- Raw CMIS EEPROM read/write for low-level hardware debug
- Support single resource query or bulk query for all instances
- Support human-readable table output and machine parseable JSON output

## 5.Requirements

### 5.1.Functional Requirements

FR1. Provide hierarchical CLI namespace: `show`, `config`, `read-eeprom`, `write-eeprom`

FR2. Resolve port to OE/ELS mapping from `cpo.json`

FR3. Support query individual port/OE/ELS or dump all instances

FR4. Expose CMIS defined module state, temperature, DOM, optical power, datapath status

FR5. Support set Tx-disable, low power mode, hardware reset for OE and ELS

FR6. Provide raw EEPROM read/write with bank/page/offset/size addressing for CMIS registers

FR7. Output supports human readable format and `--json` structured output

FR8. Consistent error code and error message convention aligned with SONiC sfputil

### 5.2.Non-Functional Requirements

NFR1. `cpoutil` is a on-demand CLI tool; no background daemon process

NFR2. Minimal memory footprint, short-lived execution

NFR3. CLI syntax follows SONiC community style guideline

NFR4. Do not write configuration into SONiC ConfigDB; operations are direct one-shot hardware access

NFR5. write-eeprom is debug-only; no built-in high-level CMIS validation logic

## 6.Architecture Design

```
User Shell
    ↓
cpoutil CLI Parser (argparse)
    ↓
cpoutil Core Logic
    ├─ cpo.json Mapping Parser
    └─ Platform HAL Interface (CMIS Api CPO OE/ELS Abstraction)
    ↓
Platform Driver / I2C Layer
    ↓
CPO Hardware: OE Modules, ELS Modules
```

1. `cpoutil` runs as a short-lived foreground process, no persistent runtime.
2. Mapping information loaded from static platform file `cpo.json` at command startup.
3. All register access is delegated to platform HAL(CMIS API); main CLI logic contains no direct hardware I/O.
4. Separate HAL APIs for OE and ELS to isolate device access logic.
5. CLI output formatter supports table and JSON mode controlled by global `--json` flag.

## 7.High-Level Design

### 7.1.CLI Command Hierarchy Overview

```
cpoutil
├─ show
│   ├─ interface
│   │   ├─ map [PORT]
│   │   ├─ dom [PORT]
│   │   ├─ tx_disable [PORT]
│   │   ├─ speed [PORT]
│   │   └─ lane-status [PORT]
│   ├─ oe
│   │   ├─ lpmode [OE_INDEX]
│   │   ├─ status [OE_INDEX]
│   │   ├─ temperature [OE_INDEX]
│   │   └─ input-power [OE_INDEX]
│   └─ els
│       ├─ presence [ELS_INDEX]
│       ├─ lpmode [ELS_INDEX]
│       ├─ status [ELS_INDEX]
│       ├─ temperature [ELS_INDEX]
│       └─ output-power [ELS_INDEX]
├─ config
│   ├─ interface
│   │   └─ tx-disable PORT {enable|disable}
│   ├─ oe
│   │   ├─ lpmode OE_INDEX {full|low}
│   │   ├─ reset OE_INDEX
│   │   └─ tx-disable OE_INDEX {enable|disable}
│   └─ els
│       ├─ lpmode ELS_INDEX {full|low}
│       ├─ reset ELS_INDEX
│       └─ tx-disable ELS_INDEX {enable|disable}
├─ read-eeprom
│   ├─ interface PORT [--oe|--els]
│   ├─ oe -i INDEX -b BANK -n PAGE -o OFFSET -s SIZE
│   └─ els -i INDEX -b BANK -n PAGE -o OFFSET -s SIZE
└─ write-eeprom
    ├─ interface PORT [--oe|--els]
    ├─ oe -i INDEX -b BANK -n PAGE -o OFFSET -d HEX_DATA
    └─ els -i INDEX -b BANK -n PAGE -o OFFSET -d HEX_DATA
```

> cpoutil firmware commands excluded, see separate design document.

## 8.Command Functional Specification

### 8.1.cpoutil show (Read-only Query Commands)

#### 8.1.1.cpoutil show interface map [PORT]

Function: Retrieve mapping from cpo.json; display port -> OE index, OE_BANK, ELS index, ELS_BANK, lane association.

- Without PORT: show all ports mapping
- With PORT: show single port mapping

```
admin@sonic:~$ cpoutil show portmap
PORT_INDEX          OE_INDEX             OE_BANK          ELS_INDEX           ELS_BANK 
Ethernet0             oe0                 bank0             els0                bank0
Ethernet8             oe0                 bank1             els0                bank1
```

#### 8.1.2.cpoutil show interface dom [PORT]

Function: Show aggregated DOM parameters for port, includes OE and ELS monitoring data.
Open Item: Reuse DOM parsing logic from sfputil.

> Note: Since `cpoutil` is primarily intended for debugging, all key‑value pairs retrieved via its APIs will be displayed, including vendor‑specific fields.

```
admin@sonic:~$ cpoutil show interface dom Ethernet0
Ethernet0: SFP EEPROM detected
        Active Firmware: N/A
        Active application selected code assigned to host lane 1: 6
        Active application selected code assigned to host lane 2: 6
        Active application selected code assigned to host lane 3: 6
        Active application selected code assigned to host lane 4: 6
        Active application selected code assigned to host lane 5: 6
        Active application selected code assigned to host lane 6: 6
        Active application selected code assigned to host lane 7: 6
        Active application selected code assigned to host lane 8: 6
        Application Advertisement: 400GAUI-4-L C2M (Annex 120G) - Host Assign (0x11) - 400G-FR4/400GBASE-FR4 (Cl 151) - Media Assign (0x11)
                                   200GAUI-4 C2M (Annex 120E) - Host Assign (0x11) - 200GBASE-FR4 (Cl 122) - Media Assign (0x11)
                                   Bailly-Reserved-2 - Host Assign (0x11) - Bailly-Reserved-LC-2 - Media Assign (0x11)
                                   CAUI-4 C2M (Annex 83E) with RS(528,514) FEC - Host Assign (0x11) - 100G CWDM4 MSA Spec - Media Assign (0x11)
                                   Bailly-Reserved-1 - Host Assign (0x1) - Bailly-Reserved-LC-1 - Media Assign (0x1)
                                   800GAUI-8 L C2M (Annex 120G) - Host Assign (0x1) - Bailly-800G-2xFR4 - Media Assign (0x1)
        CMIS Rev: 5.2
        Connector: LC
        ELS Identifier: QSFP-DD Double Density 8X Pluggable Transceiver
        ELS Laser Count: 8
        ELS Maximum Power Consumption: 12.0
        ELS Revision: 0.1
        ELS Vendor Date Code(YYYY-MM-DD Lot): 2024-06-28
        ELS Vendor Name: BROADCOM
        ELS Vendor OUI: ec-01-e2
        ELS Vendor PN: ARLM-96F8DMZ
        ELS Vendor Rev: A0
        ELS Vendor SN: FD2424VG006
```

#### 8.1.3.cpoutil show interface tx_disable [PORT]

Function: Read per-lane Tx output enable status mapped to the port. Output lane-level laser enable state.

```
admin@sonic:~$ cpoutil show interface tx_disable Ethernet0 -j
    "Ethernet0": {
        "lane0": "Tx output enable",
        "lane1": "Tx output enable",
        "lane2": "Tx output enable",
        "lane3": "Tx output enable"
    }
```

#### 8.1.4.cpoutil show interface speed [PORT]

Function: Read CMIS  registers: Application Select Controls(Page:0x10) and Active Application Control Set(Page:0x11). Show configured speed and active operating speed per lane.

```
admin@sonic:~$ cpoutil show interface speed Ethernet0 -j
    "Ethernet0": {
            "Application Select Controls": {
            "lane00": 400000,
            "lane01": 400000,
            "lane02": 400000,
            "lane03": 400000,
            "lane04": 400000,
            "lane05": 400000,
            "lane06": 400000,
            "lane07": 400000
        },
        	"Active Application Control Set": {
            "lane00": 400000,
            "lane01": 400000,
            "lane02": 400000,
            "lane03": 400000,
            "lane04": 400000,
            "lane05": 400000,
            "lane06": 400000,
            "lane07": 400000
        }
   }
```

#### 8.1.5.cpoutil show interface lane-status [PORT]

Function: Read OE Data Path State Indicator and ELS lane status, display lane activation status.

```
admin@sonic:~$ cpoutil show interface lane-status Ethernet0 -j
    "Ethernet0": {
        "Data Path State Indicator": {
            "lane00": "DataPathActivated",
            "lane01": "DataPathActivated",
            "lane02": "DataPathActivated",
            "lane03": "DataPathActivated",
            "lane04": "DataPathActivated",
            "lane05": "DataPathActivated",
            "lane06": "DataPathActivated",
            "lane07": "DataPathActivated"
        },
        "ELS LaneState": {
            "lane00": "Output on",
            "lane01": "Output on",
            "lane02": "Output on",
            "lane03": "Output on",
            "lane04": "Output on",
            "lane05": "Output on",
            "lane06": "Output on",
            "lane07": "Output on"
        }
    }
```

#### 8.1.6.cpoutil show oe lpmode [OE_INDEX]

Function: Query OE low power mode status. Omit index to show all OEs.

```
admin@sonic:~$ cpoutil show oe lpmode
    OE0: full-power
    OE1: full-power
    OE2: full-power
    OE3: low-power
```

#### 8.1.7.cpoutil show oe status [OE_INDEX]

Function: Query CMIS Module State for target OE (e.g. ModuleReady).

```
admin@sonic:~$ cpoutil show oe status
    OE0: ModuleReady
    OE1: ModuleFault
    OE2: Reset
    OE3: ModuleLowPwr
```

#### 8.1.8.cpoutil show oe temperature [OE_INDEX]

Function: Read OE internal temperature, support single or all OE dump. Unit: Celsius.

```
admin@sonic:~$ cpoutil show oe temperature -j
{
    "oe0": "71.7617C",
    "oe1": "72.2383C",
    "oe2": "72.4453C",
    "oe3": "71.1719C",
    "oe4": "72.4531C",
    "oe5": "72.3398C",
    "oe6": "71.5977C",
    "oe7": "73.1016C"
}
```

#### 8.1.9.cpoutil show oe input-power [OE_INDEX]

Function: Read optical power input from ELS to OE, used for optical path dirty check diagnostics.

```
admin@sonic:~$ cpoutil show oe input-power oe1
    EIC Laser0 Input Power: 90.330 mW 19.558 dBm
    EIC Laser1 Input Power: 85.550 mW 19.322 dBm
    EIC Laser2 Input Power: 72.840 mW 18.624 dBm
    EIC Laser3 Input Power: 112.750 mW 20.521 dBm
    EIC Laser4 Input Power: 70.840 mW 18.503 dBm
    EIC Laser5 Input Power: 75.840 mW 18.799 dBm
    EIC Laser6 Input Power: 69.730 mW 18.434 dBm
    EIC Laser7 Input Power: 94.780 mW 19.767 dBm
```

#### 8.1.10.cpoutil show els presence [ELS_INDEX]

Function: Check hardware presence of ELS module.

```
admin@sonic:~$ cpoutil show els presence
ELS0(OE0): Presence.
ELS1(OE0): Presence.
ELS2(OE1): Presence.
ELS3(OE1): Presence.
ELS4(OE2): Presence.
ELS5(OE2): Presence.
ELS6(OE3): Presence.
ELS7(OE3): Presence.
ELS8(OE4): Presence.
ELS9(OE4): Presence.
ELS10(OE5): Presence.
ELS11(OE5): Presence.
ELS12(OE6): Presence.
ELS13(OE6): Presence.
ELS14(OE7): Presence.
ELS15(OE7): Presence.
```

#### 8.1.11.cpoutil show els lpmode [ELS_INDEX]

Function: Query ELS low power mode status.

```
admin@sonic:~$ cpoutil show els lpmode
    ELS0: full-power
    ELS1: full-power
    ELS2: full-power
    ELS3: low-power
```

#### 8.1.12.cpoutil show els status [ELS_INDEX]

Function: Query CMIS Module State for target ELS.

```
admin@sonic:~$ cpoutil show els status
    ELS0: ModuleReady
    ELS1: ModuleFault
    ELS2: Reset
    ELS3: ModuleLowPwr
```

#### 8.1.13.cpoutil show els temperature [ELS_INDEX]

Function: Read ELS module temperature.

```
admin@sonic:~$ cpoutil show els temperature
    ELS0: 21.7617C,
    ELS1: 22.2383C,
    ELS2: 22.4453C,
    ELS3: 21.1719C,
    ELS4: 22.4531C,
    ELS5: 22.3398C,
    ELS6: 21.5977C,
    ELS7: 23.1016C
```

#### 8.1.14.cpoutil show els output-power [ELS_INDEX]

Function: Read ELS output optical power towards OE, used for dirty-check diagnostics.

```
admin@sonic:~$ cpoutil show els output-power els7
    Laser00 opitcal power monitor: 90.330 mW 19.558 dBm
    Laser01 opitcal power monitor: 85.550 mW 19.322 dBm
    Laser02 opitcal power monitor: 72.840 mW 18.624 dBm
    Laser03 opitcal power monitor: 112.750 mW 20.521 dBm
    Laser04 opitcal power monitor: 70.840 mW 18.503 dBm
    Laser05 opitcal power monitor: 75.840 mW 18.799 dBm
    Laser06 opitcal power monitor: 69.730 mW 18.434 dBm
    Laser07 opitcal power monitor: 94.780 mW 19.767 dBm
```

### 8.2.cpoutil config (Hardware Control Commands)

#### 8.2.1.cpoutil config interface tx-disable PORT

Function: Apply Tx-disable control to all mapped OE and ELS lanes belonging to specified port.

#### 8.2.2.cpoutil config oe lpmode OE_INDEX

Function: Switch OE between full power / low power operating mode.

#### 8.2.3.cpoutil config oe reset OE_INDEX

Function: Trigger OE hardware reset via low speed control signal.

#### 8.2.4.cpoutil config oe tx-disable OE_INDEX

Function: Enable/disable Tx laser at OE module level.

#### 8.2.5.cpoutil config els lpmode ELS_INDEX

Function: Switch ELS full/low power mode.

#### 8.2.6.cpoutil config els reset ELS_INDEX

Function: Trigger ELS hardware reset signal.

#### 8.2.7.cpoutil config els tx-disable ELS_INDEX

Function: Control Tx-disable for lanes within target ELS module.

### 8.3.cpoutil read-eeprom / write-eeprom (Low-level EEPROM Access)

> Warning: These commands are intended for engineering debug only. Direct write may corrupt CMIS configuration.

#### 8.3.1.cpoutil read-eeprom oe

Mandatory arguments:

- `-i, --index`: OE index
- `-b, --bank`: EEPROM bank (hex, default=0)
- `-n, --page`: CMIS page number (hex)
- `-o, --offset`: offset within page
- `-s, --size`: number of bytes to read

#### 8.3.2.cpoutil read-eeprom els

Mandatory arguments same format as read-eeprom oe, target ELS index.

#### 8.3.3.cpoutil write-eeprom oe

Mandatory arguments:

- `-i, --index`
- `-b, --bank`
- `-n, --page`
- `-o, --offset`
- `-d, --data`: hex string data payload to write

#### 8.3.4.cpoutil write-eeprom els

Same parameter set as write-eeprom oe, target ELS module.

## 9.Warmboot and Fastboot Design Impact

No impact.

## 10.Memory Consumption

1. Memory usage spikes only when dumping full status for all OE/ELS instances.
2. All runtime objects released after command completes; no memory leak.
3. No persistent cache.

## 11.Restrictions/Limitations

L1. `cpoutil` operations directly manipulate hardware registers; changes are not persisted to SONiC ConfigDB.
L2. write-eeprom provides no CMIS content validation; misuse can permanently misconfigure modules.
L3. Read-clear CMIS fault flags will be cleared once read; cpoutil cannot suppress this hardware behavior.
L4. cpoutil cannot co-manage traditional pluggable transceivers; sfputil remains for pluggables.

## 12.Testing Requirements/Design

### 12.1.Unit Test

1. Unit test CLI argument parsing for all subcommands and error paths.
2. Mock HAL layer to verify output formatting (table / JSON).

### 12.2.Platform Functional Test

1. Verify all `show` commands return valid data for single instance and bulk query.
2. Verify `config` commands change corresponding CMIS register state.
3. Verify read-eeprom can read known CMIS registers; write-eeprom can write and read back data.
4. Negative testing: invalid index, invalid port, missing module, malformed hex input.

### 12.3.Integration Test

1. Validate CLI behavior aligned with sfputil user experience.
2. Verify JSON output parsable by automation scripts.

### 12.4.Edge Case Test

1. Concurrent multiple cpoutil invocations (lock handled at platform driver layer, outside cpoutil).

## 13.Open/Action Items

No
