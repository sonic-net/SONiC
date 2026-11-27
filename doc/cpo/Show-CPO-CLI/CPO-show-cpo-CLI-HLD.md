# HLD: show cpo / cposhow – CPO CLI for SONiC

## Table of Contents

- 1.Revision
- 2.Scope
- 3.Definitions/Abbreviations
- 4.Overview
- 5.Requirements

  - 5.1.Functional Requirements
  - 5.2.Non-Functional Requirements
- 6.Architecture Design

  - 6.1.Component and Process Model
  - 6.2.Data Source Matrix
  - 6.3.Data Flow
- 7.High-Level Design

  - 7.1.CLI Hierarchy Overview
  - 7.2.Responsibility Split
  - 7.3.Topology Source and Resource Addressing
  - 7.4.CPO Port Identification
  - 7.5.Key Format Mapping Framework (Platform-Specific Keys)
    - 7.5.1.Community map plus platform map
    - 7.5.2.Community common CPO map
    - 7.5.3.Platform extension map
    - 7.5.4.Merging, normalization, and uncovered keys
  - 7.6.Output Contract and Exit Codes
  - 7.7.show interfaces transceiver Dispatching
- 8.Command Functional Specification (show)

  - 8.1.Common Parameters
  - 8.2.show interfaces transceiver (CPO Port Behavior)
    - 8.2.1.Dispatching implementation principles
    - 8.2.2.`show interfaces transceiver eeprom [PORT] [-d/--dom]`
    - 8.2.3.`show interfaces transceiver info [PORT]`
    - 8.2.4.`show interfaces transceiver status [PORT]`
    - 8.2.5.`show interfaces transceiver pm [PORT]`
    - 8.2.6.`show interfaces transceiver presence [PORT]`
    - 8.2.7.`show interfaces transceiver lpmode [PORT]`
    - 8.2.8.`show interfaces transceiver error-status [PORT] [-hw]`
  - 8.3.show cpo map
  - 8.4.show cpo oe
    - 8.4.1.`show cpo oe list`
    - 8.4.2.`show cpo oe info [OE_INDEX]`
    - 8.4.3.`show cpo oe status [OE_INDEX] [-b BANK] [--history]`
    - 8.4.4.`show cpo oe lpmode [OE_INDEX]`
    - 8.4.5.`show cpo oe dom [OE_INDEX] [-b BANK]`
    - 8.4.6.`show cpo oe temperature [OE_INDEX]`
    - 8.4.7.`show cpo oe voltage [OE_INDEX]`
    - 8.4.8.`show cpo oe firmware-info [OE_INDEX]`
  - 8.5.show cpo els
    - 8.5.1.`show cpo els list`
    - 8.5.2.`show cpo els presence [ELS_INDEX]`
    - 8.5.3.`show cpo els info [ELS_INDEX]`
    - 8.5.4.`show cpo els status [ELS_INDEX] [-b BANK] [--history]`
    - 8.5.5.`show cpo els lpmode [ELS_INDEX]`
    - 8.5.6.`show cpo els dom [ELS_INDEX] [-b BANK]`
    - 8.5.7.`show cpo els temperature [ELS_INDEX]`
    - 8.5.8.`show cpo els voltage [ELS_INDEX]`
    - 8.5.9.`show cpo els firmware-info [ELS_INDEX]`
  - 8.6.cposhow Direct Invocation Form
- 9.Warmboot and Fastboot Design Impact
- 10.Memory Consumption & CPU Usage
- 11.Restrictions/Limitations
- 12.Testing Requirements/Design

  - 12.1.Unit Test
  - 12.2.Platform Functional Test
  - 12.3.Integration Test
  - 12.4.Edge Case Test
- 13.Open/Action Items
- 14.Dependencies
- 15.SAI API
- 16.Configuration and management
- Appendix A: Command ↔ Source Mapping
- Appendix B: Exit Codes

---

## 1.Revision

| Rev | Date       | Author     | Description |
| --- | ---------- | ---------- | ----------- |
| 1.0 | 2026-11-06 | KroosMicas | Initial: CPO CLI for SONiC — the `show cpo` / `cposhow` query family (map / oe / els, `cposhow port` command group), dispatching and rendering of `show interfaces transceiver` on CPO ports, and the platform-specific key format map framework |
| 1.1 | 2026-11-12 | KroosMicas | Revised the key-map, the `cpo_port` judgment logic, along with other minor tweaks. |
| 1.2 | 2026-11-27 | KroosMicas | Review update: port identification resolves `cpo.json` names through the `platform.json` index; platform keys come from one `get_cpo_format_map()` classmethod; `flag` is folded into `status`; ELS bank and error status; output assembly and exit codes |

## 2.Scope

This document defines two CLI paths for CPO on SONiC:

1. **Query path**: `show cpo` (user entry) and its execution body `cposhow` (script entry)
2. **Boundary changes**: for `show interfaces transceiver *`, non-CPO ports keep the original sfpshow logic while CPO ports are served by cposhow to display OE/ELS related information

**The scope includes:**

1. `show interfaces transceiver`: non-CPO ports keep the original sfpshow logic; CPO ports are served by cposhow to display OE/ELS related information
2. `show cpo`: common port-level and OE/ELS-level queries
3. `show cpo oe`: Optical Engine instance-level queries
4. `show cpo els`: External Laser Source instance-level queries
5. `cposhow`: the actual execution body of the commands above
6. The **platform-specific key** rendering framework for the three data classes `info` / `status` / `dom`

**Out of scope:**

1. The functionality and implementation of `cpoutil` / `sfputil` themselves, including the mutual-exclusion hints between them and CPO handling on the `sfputil` side (see [github.com/sonic-net/SONiC/pull/2498](https://github.com/sonic-net/SONiC/pull/2498) for both); this document does not describe these two tools
2. Firmware query and upgrade are carried by `cpoutil`: version query is `cpoutil show {oe,els} fwversion`, upgrade is the `cpoutil firmware upgrade|download|run|commit` group, both designed in the merged [cpoutil CPO Component Firmware Management HLD](https://github.com/sonic-net/SONiC/blob/master/doc/cpo-util/cpo-util-hld.md); `show cpo` only reports the versions already published in the DB (`firmware-info`, §8.4.8 / §8.5.9), so after an upgrade the value here follows the next DB publication rather than the upgrade itself
3. API layer implementation details (`CpoCmisApi` / `ElsfpApi`); this document only references their output
4. Table-writing implementation on the xcvrd side; this document describes only the consumer side

## 3.Definitions/Abbreviations

| Term        | Definition / Abbreviation                                                                                                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| CPO         | Co-packaged optics                                                                                                                  |
| OE          | Optical Engine                                                                                                                      |
| ELS / ELSFP | External Laser Source (FP), a standalone pluggable module                                                                           |
| DP          | Data Path (CMIS concept, one-to-one with host lanes)                                                                                |
| bank        | Lane grouping page of OE/ELS; one OE bank covers 8 host lanes                                                                       |
| pport       | Physical port number (`interfaces[ifname].index` in `platform.json`), internal use only, never appears in output                |
| Format Map  | Mapping table from a DB field key → display name/unit/group, in two layers: the community common map (in `sonic-utilities`) and the platform extension map (returned by `get_cpo_format_map()` on the platform class, §7.5) |

## 4.Overview

`show cpo` / `cposhow` answer the question: **what state does the system believe this port is in** (similar to `show interfaces transceiver`). Data comes from the STATE_DB snapshot plus the `cpo.json` topology, and root is not required.

When **direct register read/write** is needed (similar to the former `sfputil`), use `cpoutil`; that is out of scope here. The two read different layers, so they coexist rather than replace each other:

| Dimension   | `cpoutil show interface` / `oe` / `els`                 | `show cpo` / `cposhow`                                         |
| ----------- | ------------------------------------------------------------- | ------------------------------------------------------------------ |
| Data source | Registers read directly (device API)                          | STATE_DB (snapshot written by periodic xcvrd polling)              |
| Privilege   | Requires root                                                 | No root required                                                   |
| Freshness   | Real-time value                                               | Value from the last poll, with `Last updated`                    |
| Purpose     | Debugging, field triage, ground truth when the DB has no data | Day-to-day queries, stable output scripts/automation can depend on |

The two command families have overlapping nouns. The peer table lists **only real peers**: where `cpoutil` has no command of the same scope, the row says so instead of claiming "same output".

| `show cpo` / `cposhow`                                                                    | `cpoutil show` peer                   | Data source                                               | Expected difference |
| --------------------------------------------------------------------------------------------- | --------------------------------------- | --------------------------------------------------------- | ------------------- |
| `map`                                                                                       | `interface map`                       | both from `cpo.json` (same source, neither reads the DB) | None — same columns, same JSON shape, same 0-based laser IDs (both come from `CpoMapping`) |
| `els presence`                                                                              | `interface presence`                  | cposhow: `TRANSCEIVER_ELS_INFO`; cpoutil: device API      | cpoutil reads the module, cposhow reads the xcvrd snapshot — equal except for one poll interval |
| `oe status`, `els status`                                                                 | `oe status`, `els status`             | cposhow: STATE_DB; cpoutil: device API                    | Snapshot vs live; cposhow additionally shows the bank, the source port and the alarm bits |
| `oe lpmode`, `els lpmode`                                                                 | `oe lpmode`, `els lpmode`             | cposhow: derived from `module_state`; cpoutil: `get_lpmode()` | Snapshot vs live. The derivation is aligned with `get_lpmode()` (§8.2.7), so the two agree except for one poll interval |
| `oe temperature`, `els temperature`                                                       | `oe temperature`, `els temperature`   | both from the DOM snapshot / API                          | Snapshot vs live; cposhow adds the threshold columns |
| `oe dom`, `els dom`                                                                       | **none** (closest: `interface dom`, per port) | cposhow: STATE_DB                                 | Different scope: `interface dom` is one port; `show cpo … dom` is one device and renders every bank of it |
| `oe firmware-info`, `els firmware-info`                                                    | `oe fwversion`, `els fwversion`       | cposhow: `TRANSCEIVER_FIRMWARE_INFO` / `TRANSCEIVER_ELS_FIRMWARE_INFO`; cpoutil: `get_firmware_info()` | Snapshot vs live. `cpoutil` prints the whole `get_firmware_info()` record (image A/B, factory, running, committed), the DB row carries only active/inactive; the firmware commands do not write that table, so after an upgrade the two differ until the next publication |
| `oe info`, `oe voltage`, `list` and the ELS equivalents | **none**                              | cposhow: STATE_DB                                         | No peer command exists; `cpoutil` reads these values only through `status` / `dom` |

Labels and units are shared: `cpoutil`, `cposhow` and `sfpshow` all render through the same community map (`utilities_common/cpo_format.py`, §7.5.2), so a field name never differs between the two tools.

`show cpo` reuses the established pattern of `show interfaces transceiver`: **the command tree only parses and dispatches parameters, while the implementation lives in the standalone script `cposhow`**.

## 5.Requirements

### 5.1.Functional Requirements

- **FR1.** Provide the new `show cpo {oe,els}` command
- **FR2.** `show cpo` and `cposhow` produce identical output **content** (the former is a wrapper around the latter); the only permitted differences are alias resolution, default namespace handling, and `--verbose` writing to stderr (§8.6)
- **FR3.** The OE/ELS dimension must support single-instance queries and full aggregation, while preserving bank semantics
- **FR4.** `info`/`status`/`dom` must render platform-specific keys: keys not covered are not displayed and must never interrupt the output; the label/unit of platform-specific keys **may only come from the platform itself**, through the classmethod format map of §7.5.3, and `sonic-utilities` hardcodes no platform strings; rendering never instantiates `platform_chassis` and never needs root
- **FR5.** `show interfaces transceiver *` must distinguish CPO ports: non-CPO ports keep the original sfpshow logic, and CPO ports are switched to cposhow to display OE/ELS related information
- **FR6.** Every `show cpo` / `cposhow` query command supports `--json` machine-readable output, and keys in the JSON must be the raw DB keys. `show interfaces transceiver` is **out of this requirement**: it keeps its current no-JSON behavior (L4)

### 5.2.Non-Functional Requirements

- **NFR1.** `show cpo` topology resolution does not access hardware;
- **NFR2.** A failure to obtain the Format Map must not fail the command; degrade to the community common map;
- **NFR3.** Output format follows SONiC community CLI style (click + tabulate simple);
- **NFR4.** Missing tables, missing fields, and read failures are uniformly rendered as `N/A`, never as a bare exception;
- **NFR5.** A single bad port must not interrupt full output.

## 6.Architecture Design

### 6.1.Component and Process Model

```text
User Shell
    │
    ├── show cpo <map|oe|els> ...             # sonic-utilities click group (show/cpo/__init__.py)
    │        │  clicommon.run_command(['cposhow', ...])
    │        ▼
    ├── cposhow <map|oe|els> ...              # /usr/local/bin/cposhow (short-lived process)
    │        │
    │        ├─ Topology Resolver  ← device_info.get_cpo_data() + platform.json + port_config
    │        ├─ Format Map Loader  ← community CPO map (utilities_common) + `get_cpo_format_map()` of §7.5.3
    │        ├─ DB Reader          ← STATE_DB: TRANSCEIVER_* / TRANSCEIVER_ELS_*
    │        └─ Formatter          ← table / json
    │
    └── show interfaces transceiver <...>     # sonic-utilities click group (show/interfaces/__init__.py)
            │ cpo_port                │ sfp_port
            ▼                         ▼
        cposhow port <sub> ...     sfpshow <sub> ...
```

Component responsibilities:

| Component             | Responsibility                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `show cpo`          | Parameter parsing, alias → port name conversion, namespace, `run_command` dispatch, return code passthrough             |
| `cposhow`           | All query logic and rendering                                                                                              |
| `Topology Resolver` | Port ↔ OE/ELS/laser mapping, bank resolution, CPO port identification                                                     |
| `Format Map Loader` | Merge of the community map and `get_cpo_format_map()`, key normalization, classification of uncovered keys |
| `DB Reader`         | Read by table name / key                                                                                                   |
| `Formatter`         | Output in table or JSON format                                                                                             |

### 6.2.Data Source Matrix

| Command family           | Primary data source                                                                                                                                                                                                                                                                                                                   | Notes                                                                                                                                              |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cpo map`              | `device_info.get_cpo_data()` + `platform.json`                                                                                                                                                                                                                                                                                    | Pure topology, **reads no DB and creates no table**                                                                                          |
| `format map`           | `get_cpo_format_map()` on the platform class                                                                                                                                                                                                                                                | Code, not data: called as a classmethod, so no chassis object is built and no register is read (§7.5.3)                                           |
| `els presence`         | `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                                                                                                                                              | Determines whether this table exists                                                                                                               |
| `oe/els info`          | `TRANSCEIVER_INFO` + `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                                                                                                                       | The two sides have different field sets (§8.2.3)                                                                                                  |
| `oe/els status`        | `TRANSCEIVER_STATUS` + `TRANSCEIVER_ELS_STATUS`, plus `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` / `TRANSCEIVER_ELS_DOM_FLAG` / `TRANSCEIVER_ELS_STATUS_FLAG` for the flag groups; `--history` additionally reads `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT` | Includes DP / config / tx status and the alarm flags; `--history` turns on the change count / set time / clear time columns, and set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME` |
| `oe/els dom`           | `TRANSCEIVER_DOM_SENSOR` + `TRANSCEIVER_DOM_THRESHOLD` + the corresponding ELS tables                                                                                                                                                                                                                                             | Values and thresholds on the same screen                                                                                                           |
| `oe/els temperature`   | `*_DOM_SENSOR.temperature` for the value, `*_DOM_THRESHOLD` for the four thresholds                                                                                                                                                                                                                                               | `TRANSCEIVER(_ELS)_DOM_TEMPERATURE` is **not** used: no CPO writer exists for it (`DomThermalInfoUpdateTask` covers pluggable ports only), so the sensor table is the only source with data (§8.4.6 / §8.5.7) |
| `oe/els voltage`       | `TRANSCEIVER_DOM_SENSOR.voltage` + `TRANSCEIVER_ELS_DOM_SENSOR.voltage`                                                                                                                                                                                                                                                           | Threshold columns from `*_DOM_THRESHOLD`; the `Status` column reads the Vcc bits of `*_DOM_FLAG` (§8.4.7 / §8.5.8)                                                                                                 |
| `oe/els firmware-info` | `TRANSCEIVER_FIRMWARE_INFO` + `TRANSCEIVER_ELS_FIRMWARE_INFO`                                                                                                                                                                                                                                                                     | —                                                                                                                                                 |
| `port error-status`    | OE side: `TRANSCEIVER_STATUS_SW`; ELS side: `TRANSCEIVER_ELS_STATUS`                                                                                                                                                                                                                                                              | One rule per side, identical vocabulary to `sfputil`; ELS lane-level latches stay out of this command (§8.2.8)                                     |

### 6.3.Data Flow

```text
   cpo.json ──┐
              ├─┐
 platform.json┘ ├──► device_info.get_cpo_data() ──► Topology Resolver ─┐
                │
 port_config ───┘                                                      │
                                                                       ▼
 ┌──────────── xcvrd (sonic-platform-daemons) ─────────────┐      cposhow ──► stdout
 │ CpoStateUpdateTask  ──► TRANSCEIVER_INFO / _ELS_INFO    │         ▲
 │ CpoDomInfoUpdateTask──► *_DOM_SENSOR / _FLAG / _STATUS  │         │
 │ CPODOMDBUtils       ──► *_DOM_THRESHOLD                 │    STATE_DB
 └────────────────────────────┬────────────────────────────┘      (redis)
                             ▼                                     ▲
                        STATE_DB ──────────────────────────────────┘

 platform class (classmethod, no instantiation)
   └─ get_cpo_format_map() ──► Format Map Loader ──► cposhow rendering
```

## 7.High-Level Design

### 7.1.CLI Hierarchy Overview

```text
show interfaces transceiver                  # existing command, behavior dispatched by port type
├─ eeprom [PORT] [-d/--dom]           ──►    cposhow port eeprom
├─ error-status [PORT] [-hw]          ──►    cposhow port error-status
├─ info [PORT]                        ──►    cposhow port info
├─ lpmode [PORT]                      ──►    cposhow port lpmode
├─ pm [PORT]                                (not supported, still goes through sfpshow)
├─ presence [PORT]                    ──►    cposhow port presence
└─ status [PORT]                      ──►    cposhow port status

show cpo            # the click wrapper; the tree is identical to cposhow (§8.6)

├─ map [PORT]
├─ oe
│  ├─ list
│  ├─ info [OE_INDEX] [--show-suppressed]
│  ├─ status [OE_INDEX] [-b BANK] [--history] [--show-suppressed]
│  ├─ lpmode [OE_INDEX]
│  ├─ dom [OE_INDEX] [-b BANK] [--show-suppressed]
│  ├─ temperature [OE_INDEX]
│  ├─ voltage [OE_INDEX]
│  └─ firmware-info [OE_INDEX]
└─ els
   ├─ list
   ├─ presence [ELS_INDEX]
   ├─ info [ELS_INDEX] [--show-suppressed]
   ├─ status [ELS_INDEX] [-b BANK] [--history] [--show-suppressed]
   ├─ lpmode [ELS_INDEX]
   ├─ dom [ELS_INDEX] [-b BANK] [--show-suppressed]
   ├─ temperature [ELS_INDEX]
   ├─ voltage [ELS_INDEX]
   └─ firmware-info [ELS_INDEX]

cposhow port        # CPO ports only; produced for `show interfaces transceiver` (§7.7); options in §8.1

├─ eeprom       [-p PORT ...] [--all] [-d/--dom]
├─ error-status [-p PORT ...] [--all]
├─ info         [-p PORT ...] [--all]
├─ lpmode       [-p PORT ...] [--all]
├─ presence     [-p PORT ...] [--all]
└─ status       [-p PORT ...] [--all]
```

### 7.2.Responsibility Split

| Concern               | `show interfaces transceiver`                                                                                                                                                                         | `show cpo`                                             | `cposhow`                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Parameter definitions | Existing options, **nothing added**                                                                                                                                                               | click group + options with the same names as `cposhow` | click, with `-h` as the authoritative version                                                 |
| Alias conversion      | Already present (`try_convert_interfacename_from_alias`)                                                                                                                                              | Same as left                                             | Aliases not supported                                                                           |
| namespace             | Existing `-n`, **except `lpmode`**: `show interfaces transceiver lpmode` has no `-n` option today, and this document does not add one                                                     | `-n` passed through                                    | Accepts `-n` directly                                                                         |
| Dispatch              | Existing → `sfpshow` (`lpmode` / `error-status` use `sudo sfputil show`, the existing implementation)                                                                                          | `clicommon.run_command(['cposhow', ...])`              | Is itself the execution body                                                                    |
| Port type dispatching | Decided in the **click layer** (`is_cpo_port()` → physical-port intersection with the `interfaces` of `get_cpo_data()`, §7.4): CPO ports are routed to `cposhow port`, SFP ports use the original command          | —                                                       | Provides the `port` command group (6 subcommands, `pm` excluded)                            |
| Output implementation | SFP ports: the original command's output as-is; CPO ports: the block/value returned by `cposhow` as-is; both combined by the click layer into a single table or concatenated block by block per §7.6 | No post-processing, stdout passed through                | The single implementation; `port`, `show cpo` and `cpoutil show` share the same formatter |

Rule 1: **On the `show` path the dispatch point is the click layer, not the execution body.** Once a port is identified as CPO, `cposhow port` is called **directly**; `sfpshow` does not participate at all, so CPO text has exactly one producer.

Rule 2: **`cpo.json` + the PORT table are read once per process, and classification is then one set intersection per port.** In the single-port case it is resolved once; in the full case the code enumerates `platform_sfputil.logical` for the current namespace, splits it into a CPO set and an SFP set, then submits one command per set (CPO → batched `cposhow port <sub> --port ...`; SFP → the original command without `-p`). The whole decision costs one JSON parse plus one CONFIG_DB read (§10) and is independent of the port count; **no chassis is constructed**, so `show` keeps running without root and a non-CPO platform keeps its current path at zero cost.

The two sides cannot disagree about a port: `sfputil`'s own predicate (`chassis.get_cpo(physical_port)`) is physical-port based as well, and §7.4 uses the same unit, so a breakout subport is classified identically on both paths and is neither shown twice nor dropped; a unit test on a broken-out HwSKU keeps it that way (§12.4.8).

### 7.3.Topology Source and Resource Addressing

**The single topology source**: `sonic_py_common.device_info.get_cpo_data()` (`device_info.py`).

- File lookup: the platform directory, a file named `cpo.json`;
- Missing file, or JSON that does not parse → returns `None`, and the caller takes the "no CPO platform" branch (`NO_TOPOLOGY`, §7.4);
- A file that parses but fails normalization raises instead of returning `None` (`ValueError` / `KeyError` / `AttributeError`, §7.4). Every caller wraps it and degrades to `INVALID`; a bare call on the classification path would take down `show interfaces transceiver` for **all** ports, SFP ports included.

Structure (the schema matches the existing validation; the block below is abridged):

```json
{
  "devices": {
    "oe0":  {"device_type": "optical_engine", "asic_lanes": "41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56",
             "max_banks": 2, "i2c_path": "/sys/bus/i2c/devices/32-0050"},
    "els0": {"device_type": "external_laser_source",
             "laser_to_asic_lane_mapping": {"1": "41,42", "2": "43,44"}}
  },
  "interfaces": {
    "Ethernet0": {"associated_devices": [{"device_id": "oe0", "bank": 0},
                                         {"device_id": "els0", "bank": 0}]},
    "Ethernet4": {"associated_devices": [{"device_id": "oe0", "bank": 1},
                                         {"device_id": "els0", "bank": 0}]}
  }
}
```

**`cpo.json` carries topology only** — devices, port→device associations and banks. It carries no display text (labels and units live in code, §7.5.3) and no physical-port list: `index` stays where the platform defines it, in `platform.json`, and §7.4 resolves the names above against it. `get_cpo_data()` normalizes the known lane fields and returns everything else untouched, so the file has no effect on xcvrd consumption beyond the topology itself.

**Mapping reuse**: `cposhow` does `from cpoutil.mapping import CpoMapping` directly (`cpoutil` and `cposhow` ship in the same sonic-utilities package; the package list is in `setup.py`), so the parsing logic is not implemented twice. It can later be moved up to `utilities_common/cpo_mapping.py` without any behavior change (§13 OI-1).

### 7.4.CPO Port Identification

Consumers need the same criterion: `cposhow` (positive identification) and `sfpshow` (negative identification, skipping CPO ports during full enumeration). Both run without root and neither may import `sonic_platform`, so the criterion is **static** and built from two files already on disk: `cpo.json` says **which** logical ports are CPO, `platform.json` says **where** each of them sits physically.

Criterion: **classification is by physical port, not by logical port name.** A name listed in `cpo.json` is resolved to its `index` in the PORT table; the union of those physical ports is the CPO set, and a logical port belongs to it when any of its own physical ports is in that set:

```text
cpo_names         = keys of cpo.json["interfaces"]
cpo_pports        = union of PORT index of every name in cpo_names
physical(port)    = PORT index of that logical port (a list; ganged subports share one physical port)
is_cpo_port(port) = bool(set(physical(port)) & cpo_pports)
```

- **Two files, one key.** `cpo.json` names ports, `platform.json` places them: `index` is defined once by the platform and is not repeated into `cpo.json`. Both readers therefore agree on the physical-port set by construction, with no second spelling to keep in sync.
- **The logical name is not the key.** On a HwSKU whose physical ports are broken out into several logical ports, only the base name of that group appears in `cpo.json`, yet every subport carries the same physical port and is a CPO port. Comparing names would misclassify the remaining subports as SFP and hand them to `sfputil` / `sfpshow`, neither of which has EEPROM semantics for a CPO physical port. Resolving the name to its `index` first, then intersecting, is the only criterion that holds on both a 1:1 port map and a broken-out one.
- **A name with no PORT entry contributes nothing.** A port removed from configuration, or a stale `cpo.json`, is skipped rather than raising: the remaining names still classify, and if none of them resolves the topology counts as empty (`NO_TOPOLOGY`, table below).
- No chassis construction, no device access, no root: `cpo.json` is a plain `0644` file read by `get_cpo_data()`, and the PORT table is the `platform.json` shipped with the platform, or the `PORT` entries derived from it, a CONFIG_DB read.
- Both inputs are built **once per process**; the per-port cost is one set intersection.
- Non-CPO platform: the helper returns `False` for every port and the original path runs unchanged.

Shared helper: `utilities_common/cpo_helper.py`, used by both the `show/interfaces` click layer and `sfpshow`.

```python
def get_cpo_pports():                 # parsed once per process, cached
    ...
    return set_of_physical_ports      # cpo.json names resolved through the PORT index; raises only CpoTopologyInvalid, folded below

def is_cpo_port(physical_ports, cpo_pports):
    return bool(set(physical_ports) & cpo_pports)
```

Failure handling — topology resolution is a **single upfront step**, so a bad file fails once, not once per port (the helper must never fail the command):

| State           | Condition                                                                                            | `show interfaces transceiver`                                                                       | `show cpo *`                                     |
| --------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `NO_TOPOLOGY` | no `cpo.json`, or it yields no usable topology                                                      | every port treated as SFP, **silent**, original path                                                | exit code 3                                      |
| `INVALID`     | the file exists but reading / normalizing raises, or `CpoMapping` rejects it (see below)             | every port treated as SFP plus **one** `warning` on stderr, **exit 0**                            | exit code 4                                      |
| `OK`          | `CpoMapping` built successfully                                                                     | classification per the criterion above                                                              | normal output                                    |

`INVALID` covers more than a syntax error: `get_cpo_data()` catches only `json.JSONDecodeError` / `IOError` / `TypeError` / `ValueError` around the JSON load, while the subsequent normalization raises on its own (`ValueError` for an unrecognized `device_type` or an unparsable lane string, `KeyError` for a missing `device_type`, `AttributeError` for a non-dict `devices`). A file that passes a shallow syntax check can still fail `CpoMapping` — a `cpo.json` written before the `devices` schema, for example, carries `oes` / `elss` / `interfaces` and no `devices`. Both cases must land in `INVALID`, which is why the resolver wraps the whole chain in `except (ValueError, KeyError, TypeError, AttributeError, CpoMappingError)` and reports one warning.

`show cpo` decides 3 / 4 **before entering the port loop**, so the diagnostic appears once instead of once per port.

A vendor chassis class that does not call `ChassisBase.__init__()` cannot affect this path: it never consults the chassis, so `_cpo_list` is never touched and the `AttributeError` / `RuntimeError` cases of `ChassisBase.get_cpo()` do not arise.

`sfputil/port.py::is_cpo_port()` reads the device through the platform API and is **not** used on the `show` path, because `sfpshow` is DB-only and cannot import `sonic_platform`. The two predicates answer the same question from different layers; this document fixes only the static one.

### 7.5.Key Format Mapping Framework (Platform-Specific Keys)

#### 7.5.1.Community map plus platform map

The format map has two layers:

1. **Maps for community common fields live in utilities** and ship with `sonic-utilities` (§7.5.2);
2. **Maps for platform-private fields are returned by `get_cpo_format_map()` on the platform class** (§7.5.3), so `sonic-utilities` hardcodes no platform label/unit and `cpo.json` stays a pure topology file.

The value format that `dom` and the `status` flag table present follows §4 of the merged [CMIS diagnostic monitoring HLD](https://github.com/sonic-net/SONiC/blob/master/doc/platform_api/CMIS_Diagnostic_Monitoring_Overview_in_SONiC.md) (value plus four thresholds; flag plus change count / last set / last clear; a `Last updated` line per block), so an OE or ELS row reads like a CMIS module row. The producer side of the tables it reads is the [xcvrd CPO HLD](https://github.com/sonic-net/SONiC/blob/master/doc/pmon/xcvrd_cpo.md). Both cross-references are absolute because the folder this document finally lands in (`doc/cpo/` versus `doc/pmon/`) is decided by the doc maintainers.

**How `cposhow` reaches the map without a chassis.** `get_cpo_format_map()` is a classmethod, so it is called on the class and no `platform_chassis` object is created:

```python
from sonic_platform.chassis import Chassis          # module import only, no instantiation
oe_dom = Chassis.get_cpo_format_map().get("dom", {}).get("oe", {})
```

Consequences, all of them requirements on the implementation:

- **No root, no device access, no chassis construction.** The 0.5–1 s `platform_chassis` construction of the current `sfputil` / `cpoutil` path is not on this path at all; the cost is one module import, measured in §10;
- **A platform with no private keys returns `{}`** (the default on the base class), so the community map is the whole output and the platform pays nothing;
- **A platform without CPO never calls the map**: the §7.4 classification already returned `NO_TOPOLOGY` before rendering starts;
- **Import failures are contained**: if the platform module cannot be imported or `get_cpo_format_map()` raises, `cposhow` degrades to the community map with one `warning` and still exits 0 (NFR2, degradation table in §7.5.3).

`get_cpo_format_map()` is a **new API in `sonic-platform-common` plus a vendor override**; that cross-repo pair is tracked as OI-4 (§13).


#### 7.5.2.Community common CPO map

They land in `utilities_common/cpo_format.py` (promoted from the CPO-related maps in the existing `cpoutil/helper.py`, shared by `cposhow` / `sfpshow` / `cpoutil`):

| Map                                                           | Objects covered                   | Example keys                                                             |
| ------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------ |
| `CPO_INFO_FIELD_MAP`                                        | `TRANSCEIVER(_ELS)_INFO`        | `manufacturer`, `serial`, `lane_count`, `control_mode`               |
| `CPO_STATUS_MAP`                                            | `TRANSCEIVER(_ELS)_STATUS`      | `module_state`, `DP<N>State`, `enable_lane<N>`                     |
| `CPO_DOM_MODULE_MONITOR_MAP`                                | Module-level monitored values     | `temperature`, `voltage`, `icc`                                    |
| `CPO_DOM_CHANNEL_MONITOR_MAP`                               | Lane/laser-level monitored values | `laser_bias_current_lane*`, `optical_power_lane*`, `voltage_lane*` |
| `CPO_DOM_FLAG_MAP`                                          | Alarm bits                        | `temperature_alarm_high`, `laser_bias_warn_low`                      |
| `CPO_DOM_VALUE_UNIT_MAP` / `CPO_DOM_MODULE_THRESHOLD_MAP` | Units / thresholds                | —                                                                       |

They are merged into the rendering flow only when `device_type == CPO`, so the ordinary transceiver path is unaffected.

#### 7.5.3.Platform extension map

One classmethod on the platform class, `get_cpo_format_map()`. The base class returns `{}`; a platform returns the map owned by its CPO class, which is where the private keys are decoded:

```python
# sonic_platform_base/chassis_base.py
class ChassisBase:
    @classmethod
    def get_cpo_format_map(cls):
        """Static display metadata for platform-private CPO keys. {} by default."""
        return {}

# sonic_platform/cpo.py — the platform CPO class; the example keys are a TEC
# current and a private alarm bit of one OE
class Cpo(..., CpoBase):
    PLATFORM_SPECIFIC_FORMAT_MAP = {
        "dom": {"oe": {"tec_current": {"label": "TEC Current", "unit": "mA", "type": "float", "precision": 1}}},
        "status": {"oe": {"pmd_fault_lane{lane}": {"label": "PMD Fault Lane {lane}", "type": "bool"}}},
    }

# sonic_platform/chassis.py — the same two lines on every platform
class Chassis(ChassisBase):
    @classmethod
    def get_cpo_format_map(cls):
        from .cpo import Cpo          # class definition only; no object is built
        return Cpo.PLATFORM_SPECIFIC_FORMAT_MAP
```

Return value — display class, then endpoint, then raw key:

```python
{
    "info":   {"oe": {raw_key: entry}, "els": {raw_key: entry}},
    "status": {"oe": {raw_key: entry}, "els": {raw_key: entry}},
    "dom":    {"oe": {raw_key: entry}, "els": {raw_key: entry}},
}
```

These are the three display classes that can carry vendor keys. A missing category or endpoint reads as `{}`, and `show cpo {oe,els} dom` renders `map["dom"]["oe"]` / `map["dom"]["els"]`.

`PLATFORM_SPECIFIC_FORMAT_MAP` already exists on `CpoBase` (merged [PR 825](https://github.com/sonic-net/sonic-platform-common/pull/825)) with the same three categories and two endpoints, as an all-empty skeleton: a vendor fills only the branches it extends.

**`status` is one display class, and it renders both the status keys and the alarm bits**, so it is one category of the map. The standard part needs no entry: `module_state`, `DP<N>State`, `config_state_hostlane<N>`, `enable_lane<N>`, `fault_code_lane<N>`, `warning_code_lane<N>` all come from the CMIS / ELSFP-CMIS register set and have community labels in `CPO_STATUS_MAP`, and the alarm bits have community labels in `CPO_DOM_FLAG_MAP` (§7.5.2). `map["status"]` covers the rest of that class: a platform-private alarm bit that sits next to the CMIS bits, or a private status code. A key that should be common to every vendor belongs in the community map instead. Vendor-private **real-time monitored values that are not flags** — a TEC current, an extra ADC channel, a rail voltage — are not status keys: they are declared under `dom` and render in `show cpo {oe,els} dom` next to the CMIS channels.

The key names above are illustrative platform-private keys, not a required set: a platform returns whatever its API publishes **beyond** the community map. Keys the community map already covers (`manufacturer`, `serial`, `DP{lane}State`, `temperature`, `enable_lane{lane}`, …) must not be returned — rendering rule 1 fixes what happens if one is.

Entry semantics:

| Field         | Required | Notes                                                                              |
| ------------- | -------- | ---------------------------------------------------------------------------------- |
| `label`     | Yes      | Non-empty string; may contain placeholders                                         |
| `unit`      | No       | Exactly one of `C` / `mA` / `mW` / `V` / `dBm` / `nm` / `A` / `s`, or `""` (no unit). Anything else makes the entry invalid (degradation table below). The renderer prints `<value> <unit>` with one space and rewrites no symbol — `41.13 C`, never `41.13°C` |
| `type`      | No       | `str` / `int` / `float` / `bool` / `enum` / `hex`; defaults to `str` |
| `values`    | No       | Value table for `type=enum`; the raw value is shown when no mapping exists       |
| `precision` | No       | Decimal places for `type=float`; defaults to 2                                   |

Rendering rules — one rule per question, no overlap:

1. **Community common keys are always rendered**, in the order and with the label/unit of the community map (§7.5.2). An entry for such a key is **ignored** and reported as one `warning` on stderr; the command still succeeds. The label and unit of a community field must be identical on every vendor, otherwise the same field cannot be compared across platforms;
2. **Platform-private keys are rendered only when the map declares an entry for them**, appended after the community keys in declaration order, with the label/unit/type/precision taken from the entry. Keys the map does not declare are not displayed — that is the whole rule, and the only way to hide a platform-private key is to drop its entry;
3. **Placeholders**: `{lane}` — in the OE section this is the **bank-relative index 1..8** (bank 1 is still `DP1..DP8`), in the ELS section it is the **absolute lane** (bank 1 is `lane9..16`); `{bank}` takes the bank number of that row;
4. **Fixed formats, generated uniformly by the renderer and not described by the platform map**:
   - `dom`: value plus four thresholds (High Alarm / High Warn / Low Warn / Low Alarm), with `ModuleThresholdValues` and `ChannelThresholdValues` as separate sections (§8.2.2);
   - `status --history`: each flag gains change count, last set time, and last clear time, in the CMIS diagnostic-HLD layout; the status keys above it keep their one-line form;
   - one `Last updated: <last_update_time>` line at the end of each block (the `info` table has no `last_update_time` field, so that block shows `N/A`);
5. `--json` **does not apply the platform map**; it outputs the raw DB keys (FR6).

Degradation behavior (NFR2 — the command must not be interrupted):

| Case                                                                        | Behavior                                                                                                                                  |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Map not overridden (base class `{}`), or every branch left empty | Every community common key is rendered; platform-private keys are not displayed; no error, exit code 0                                  |
| One entry invalid (empty label / unknown type / unit outside the list above) | That key is skipped with a `warning` on stderr; everything else renders normally, including all community keys                          |
| One entry declares a community common key                                 | That entry is ignored with a `warning`; the community label/unit win and the key is still rendered                                     |
| The import or the classmethod call raises                                 | The whole map is treated as `{}` with one `warning`; every community key still renders, exit code 0                                   |

The four cases are consistent by construction: the community map decides the common part, the platform map decides the platform-private part, and neither can suppress the other.


#### 7.5.4.Merging, normalization, and uncovered keys

Merging rules:

1. The platform map may only **add platform-private keys**: it cannot rename, retype, or hide a community common key, because that would let each vendor redefine fields that are supposed to be identical across vendors. An entry for a key the community map already declares is **ignored** and reported as one `warning` on stderr (the community label wins, the command still succeeds);
2. Keys declared by the platform map go into the `PlatformSpecific*` section of that display class (label taken from the entry); platform-private keys the map does not declare do not enter the output (last table of this section);
3. Ordering: platform-private keys follow the declaration order of the map dict (Python preserves insertion order, so the output is stable); keys generated from the community map follow its declaration order; keys that carry a numeric suffix (`lane2`, `lane10`) are sorted with **natural sort** (`natsorted`, as `sfpshow` does), never lexicographically;
4. The map is fetched **once per `cposhow` process** and cached for the run.

Coverage is the three display classes `info` / `status` / `dom`; `threshold` reuses the value/unit declarations of `dom`.

Handling of uncovered keys (this is how "platform-specific keys must be presented" is realized):

| Case                        | table mode                        | JSON mode |
| --------------------------- | --------------------------------- | --------- |
| Community map hit           | Rendered by the common rules      | Raw key   |
| The platform map declares it | Rendered as the platform declared | Raw key   |
| Neither hits                | Not displayed                     | Raw key   |

Constraint: **uncovered keys are not displayed**.

### 7.6.Output Contract and Exit Codes

**table mode — mixed ports (`show interfaces transceiver` full run)**

For a full run the click layer owns the assembly, in a fixed four-step order. Producers are called unchanged, so a table-type producer still prints its two-line header; the click layer drops those lines and prints **one** header for the merged table:

1. **Order.** `ports = natsorted(platform_sfputil.logical)` for the current namespace, computed once and handed to both producers, so the two halves can never interleave differently;
2. **Split.** `cpo_ports` / `sfp_ports` from the §7.4 criterion. A single-port query (positional `PORT` or `-p`) runs exactly one producer and **passes its stdout through unchanged, header included** — this keeps a single SFP port byte-identical to today;
3. **Table type** (`presence` / `lpmode` / `error-status`): call both producers with `return_cmd=True`, drop each producer's first two lines (title + rule), split every remaining line at the first run of whitespace into `(port, value)`, merge the two into one dict, then print **once** with a fixed header (`Port` plus the one fixed column name of that subcommand) through `tabulate(tablefmt="simple")`. A port missing from a producer is filled with `N/A`;
4. **Block type** (`eeprom` / `info` / `status`): split each producer's stdout into per-port blocks, order the blocks by step 1, and concatenate with **one blank line** between blocks. A CPO block keeps the internal layout of §8.2.2–§8.2.4 (`Ethernet0: CPO EEPROM detected` plus `OE (...)` / `ELS (...)` sub-blocks); `sfpshow` blocks are concatenated verbatim and not re-ordered internally.

| Type       | Subcommands                                | Presentation                                                                                            |
| ---------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| table type | `presence`, `lpmode`, `error-status` | **One table, one header**; CPO rows carry the composite value `OE: …; ELS: …`                 |
| block type | `eeprom`, `info`, `status`           | One block per port, with `OE:` / `ELS:` subsections inside a CPO block; **no overall header** |

The same full run, both presentations side by side — table type is one row per port, block type is one block per port:

```text
admin@sonic:~$ show interfaces transceiver lpmode          # table type: one header, one row per port
Port         Low-power Mode
-----------  -----------------
Ethernet0    OE: Off; ELS: Off
Ethernet128  Off
```

```text
admin@sonic:~$ show interfaces transceiver info            # block type: one block per port, no header
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        Vendor Name: BROADCOM
        ...
        ELS (els0, bank 0)
        Vendor Name: BROADCOM
        ...

Ethernet128: SFP EEPROM detected
        Vendor Name: ...
```

The distinction is also visible to a parser: table type keeps the port name in column one, so `stdout_lines[2:]` still yields data rows; block type keeps the port name in the block header, so `parse_eeprom()` still keys one entry per port.

Failure and boundary cases — every one of them keeps the overall command at **exit 0** (NFR4/NFR5):

| Case                                         | Behavior                                                                                              |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| A producer exits non-zero                    | its ports print `N/A` (table type) or `EthernetN: N/A` (block type), one `warning` on stderr, exit 0 |
| A producer omits a port it is supposed to own | that port prints `N/A`; no empty block is emitted                                                      |
| Both producers succeed but a port has no row | `N/A`, identical to the single-port output                                                            |
| `-n` invalid, or the port does not exist      | click rejects it before assembly, exit 2 (§Appendix B)                                                |

What the click layer does **not** do: measure column widths, re-order fields inside a line, or build the `OE: …; ELS: …` text itself — the composite value is produced by `cposhow port`, so every output line has exactly one producer.

`pm` is not dispatched (§8.2.5) and keeps the original `sfpshow` output shape, so it is out of scope for this table.

**table mode — structure inside a block**

- Port dimension: grouped inside the block by the CMIS section names: `ModuleMonitorValues` / `ChannelMonitorValues` / `PlatformSpecificDomValues` (status and info similarly use `ModuleStatusValues` / `ChannelStatusValues`);
- Resource dimension: one block per resource, with a bank subheading (`Bank 0 (Lane 1-8)` for OE, `Bank 0 (Laser 1-8)` for ELS). **OE headings name host lanes and ELS headings name lasers; keys inside the OE section always use the bank-relative index 1..8, while keys inside the ELS section always use the absolute index**;
- Missing values: `N/A` (key absent / empty value / unparsable all become `N/A`); booleans: `True`/`False`, **taken directly from the DB with no prefix marker**;

**One bank model for both resources.** A bank is a property of the **port → device association**, not of the device and not of a DB row: `cpo.json` declares bank per association, and STATE_DB keys rows by logical port with no bank dimension (`xcvrd/cpo/cpo_dom_mgr.py`: the CPO object is bound to the bank covering that port's lanes). OE and ELS are therefore structurally identical:

1. Every association carries a bank. `oe.bank` is mandatory in practice, `els.bank` may be omitted and then means **bank 0** — never `N/A`, so the same data can never appear as three different spellings across map, JSON and heading;
2. The resource-dimension JSON keeps module-level groups at the resource level and puts bank-scoped groups one level down (`resource → banks → bankN → group → key`, §7.6 sample below, §8.5);
3. `-b BANK` (§8.1) means the same thing on both sides: show only the rows whose association bank equals `BANK`; there is no per-device bank selection;
4. Bank numbers are **0-based** everywhere (fields, heading, `-b`). The lane window in a heading is 1-based because it names physical lanes; that is a lane label, not a bank index.

**One value for a shared resource.** A module-level field belongs to the device but is stored per **logical port**, so a device view has to pick one row. The rule, identical in `oe list` / `els list` / `oe info` / `els info` / `oe status` / `els status`:

- take **the lowest logical port in `natsorted` order that has a non-`N/A` value**, and name it in the heading (`ports: Ethernet0`);
- if another port of the same device carries a **different** value, keep the first one and append `(differs on Ethernet8, Ethernet16)` so the reader is never told a single value is the whole truth;
- if no port has a value, print `N/A`, with no source annotation.

This makes the device view deterministic (the same device never reports two module states in one run) and keeps it consistent with `oe list`, which has to choose one `Module State` per OE.

**JSON mode — resource dimension** (`show cpo oe|els … --json`)

Levels: **module-level groups at the resource level, bank-scoped groups under `banks`**:

```text
resource → info            (module-level: static identity)
resource → dom             (module-level monitored values: temperature, voltage, icc)
resource → banks → bankN → status / flag / dom   (bank-scoped or lane-scoped keys)
```

A module-level key is **not** repeated under each bank: an OE has one temperature, not one per bank (the previous layout reported 41.125 and 42.375 for the same OE, which is an artifact of which row happened to be read). Bank-scoped keys carry a lane index that is only meaningful inside that bank, so they stay under `bankN`.

```json
{
  "oe0": {
    "info": {"manufacturer": "BROADCOM", "serial": "SB243500200"},
    "dom":  {"temperature": "41.125", "voltage": "3.312"},
    "banks": {
      "0": {"status": {"DP1State": "DataPathActivated", "module_state": "ModuleReady"},
            "dom":    {"tx1bias": "12.400"},
            "flag":   {"tempHAlarm": "False"}},
      "1": {"status": {"DP1State": "DataPathActivated", "module_state": "ModuleReady"},
            "dom":    {"tx1bias": "12.550"},
            "flag":   {"tempHAlarm": "False"}}
    }
  },
  "els0": {
    "info": {"manufacturer": "BROADCOM", "serial": "SB243600118"},
    "dom":  {"temperature": "36.750", "voltage": "3.300", "icc": "4.512"},
    "banks": {
      "0": {"status": {"enable_lane5": "True", "fault_code_lane5": "0x00"},
            "dom":    {"laser_bias_current_lane5": "152.000"},
            "flag":   {"lane_summary_fault": "False"}}
    }
  }
}
```

Bank numbers come from the `bank` field of the port→device association in `cpo.json` (0..`max_banks-1` for OE; 0 for an ELS, which declares a single bank). Leaf key = the **raw DB key**, with values kept as DB strings (never converted to float on a whim).

`oe list` / `els list` keep the list shape:

```json
[{"id": "oe0", "banks": [0,1,2,3,4,5,6,7]}, {"id": "oe1", "banks": [0,1,2,3,4,5,6,7]}]
```

**JSON mode — port dimension** (`cposhow port … --json`)

Two rules decide what a port row contains; both are needed because a broken-out CPO physical port maps to several logical ports:

1. **Which row to read.** Tables differ in granularity. `TRANSCEIVER_INFO`, `TRANSCEIVER_ELS_INFO`, `TRANSCEIVER_STATUS_SW`, the threshold tables and the firmware tables are keyed **per logical port**, so the queried port's own row is read. The DOM sensor / flag / status tables (`*_DOM_SENSOR`, `*_DOM_FLAG`, `*_STATUS`, `*_ELS_STATUS`, and the ELS flag table) are keyed **per physical port**; xcvrd writes them on the **first subport** of that physical port today. `cposhow` therefore resolves the row as "own row if present, otherwise the first subport of the same physical port" (`CpoMapping`), and then keeps only the lanes of the queried subport. When xcvrd starts publishing a row per subport — the direction of the [xcvrd CPO HLD](https://github.com/sonic-net/SONiC/blob/master/doc/pmon/xcvrd_cpo.md) — the own row is found first and nothing changes here;
2. **Which lanes.** A subport emits only the keys of the lanes it owns (`CpoMapping.lane_positions()`), so two subports of one physical port never print the same lane twice. A subport that owns no lane of a given bank prints `N/A` for that bank rather than the sibling's value.

```json
{
  "Ethernet0": {
    "oe":  {"id": "oe0", "bank": 0, "status": {"DP1State": "DataPathActivated"}},
    "els": {"id": "els0", "bank": 0, "status": {"enable_lane5": "True", "enable_lane6": "True"}}
  }
}
```

Exit codes are listed in Appendix B.

### 7.7.show interfaces transceiver Dispatching

The dispatch decision is made in `show/interfaces/__init__.py`: **once a port is identified as CPO, `cposhow port` is called directly** and `sfpshow` is not entered. `cpo.json` and the PORT table are read once per process (§7.4) and the resulting physical-port set is reused, so no chassis is built and no hardware is read.

The subcommands of `cposhow port` correspond one-to-one to `show interfaces transceiver`, and their **primary purpose is to carry the `show interfaces transceiver` calls on CPO ports**:

| `show interfaces transceiver <sub>` | CPO port routed to            | Notes                                                                                             |
| ------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------- |
| `eeprom [PORT] [-d/--dom]`          | `cposhow port eeprom`       | `-d` appends both the OE and ELS DOM sections                                                   |
| `info [PORT]`                       | `cposhow port info`         | OE section + ELS section; different field sets are not merged                                     |
| `status [PORT]`                     | `cposhow port status`       | Includes DP / config / tx status                                                                  |
| `presence [PORT]`                   | `cposhow port presence`     | Determined by the existence of `TRANSCEIVER_ELS_INFO`                                           |
| `lpmode [PORT]`                     | `cposhow port lpmode`       | Derived from `module_state`                                                                     |
| `error-status [PORT] [-hw]`         | `cposhow port error-status` | OE side reads `TRANSCEIVER_STATUS_SW`, ELS side reads `TRANSCEIVER_ELS_STATUS`; `-hw` is not a `cposhow port` option, see §8.2.8 |
| `pm [PORT]`                         | —                            | Not dispatched; CPO ports still use the original `sfpshow` path and print `Transceiver performance monitoring not applicable` (§8.2.5) |

Ordinary pluggable ports are unaffected: they keep the original `sfpshow` path with zero changes. Port-dimension data queries always reuse `show interfaces transceiver`; no new entry point is added just because a port is CPO.

For a full run mixing CPO and SFP ports, the click layer does the sorting and table assembly: table-type subcommands are combined into **one table** (CPO rows carry the `OE: …; ELS: …` composite value), while block-type subcommands keep one block per port — see §7.6 for the rules.

**Relationship with `config interface`**: configuration commands such as `config interface transceiver *` are not affected by this change and their behavior is not revised. This document covers the query side only; the configuration semantics of CPO ports remain as they are.

Details are in §8.2.

## 8.Command Functional Specification (show)

### 8.1.Common Parameters

| Parameter                        | Applies to                                                   | Notes                                                                                                                                                                                                     |
| -------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[OE_INDEX]` / `[ELS_INDEX]` | All oe/els subcommands                                       | `oe0` / `0` are equivalent; omitted = all instances                                                                                                                                                   |
| `-b, --bank N`                 | oe/els `status` / `dom`                                | Selects one bank of the OE/ELS: only the rows whose port→device association carries that bank are shown (§7.6). Omitted = every bank shown as its own section. Only bank-scoped groups take it: `lpmode`, `temperature` and `voltage` are module-level and have **no** `-b` |
| `-j, --json`                   | All                                                          | Machine-readable output                                                                                                                                                                                   |
| `-n, --namespace NAME`         | All                                                          | Selects one namespace and passes it through to the execution body. Omitted = every namespace, the same default as `sfpshow` (`@multi_asic_util.run_on_multi_asic`) |
| `--history`                    | `status`                                                   | Turns the flag groups into a table with change count / set time / clear time columns                                                                                                                     |
| `--show-suppressed`            | `info` / `status` / `dom`                         | Lists the DB keys present on that resource for which neither the community map nor the platform map has an entry, so a vendor can see what is unpublished (debugging only; output stays exit 0) |
| `--verbose`                    | All (`show cpo` side)                                      | Prints the actual `cposhow` command line executed                                                                                                                                                       |

Notes:

- An out-of-range `-b` value (negative, or ≥ the bank count of that resource) is a usage error: exit code 2 (§Appendix B).
- `-d` and `--dom` are the same option of `show interfaces transceiver eeprom`; both forms are listed once in §7.1 and §8.2.2, and the rest of this document writes `-d`.
- `--show-suppressed` is not offered on `lpmode`, `temperature` or `voltage`: those subcommands have fixed columns and no format-map entries, so there is nothing to suppress.

**`cposhow port` options — defined here, once.** These are a contract between the click layer and `cposhow`, so they are listed in one place and referenced from §7.1 and §8.6:

| Option                  | Applies to                                   | Meaning                                                                                                       |
| ----------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `-p, --port NAME`     | all 6 subcommands                            | Port to report; **repeatable**, so one call can carry many ports (the click layer batches one call per set)   |
| `--all`               | all 6 subcommands                            | Every CPO port of the selected namespace(s); mutually exclusive with `-p`                                    |
| `-n, --namespace NAME` | all 6 subcommands                           | One namespace; omitted = every namespace                                                                     |
| `-d, --dom`           | `eeprom`                                   | Append the OE and ELS DOM sections                                                                           |
| `-j, --json`          | all 6 subcommands                            | Machine-readable output                                                                                       |

`cposhow port error-status` has **no `-hw`**: `-hw` is an option of `show interfaces transceiver`, and on CPO ports it is served by the `cpoutil` command of OI-2, never forwarded to `cposhow` (§8.2.8).

### 8.2.show interfaces transceiver (CPO Port Behavior)

#### 8.2.1.Dispatching implementation principles

On the `show` path the decision is made in exactly one place, the click layer: `sfpshow` serves SFP ports only, and CPO ports are routed to `cposhow port`. `sfpshow` gains nothing beyond a static skip list — it recognizes no CPO table and no CPO field.

| Component                       | Change                                                                                                                                                                                                                                                                                                               |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show/interfaces/__init__.py` | For 6 subcommands (`eeprom`/`info`/`status`/`presence`/`lpmode`/`error-status`), `clicommon.run_command(...)` is changed so CPO ports go to `cposhow port`; `pm` is not dispatched (§8.2.5). click parameter definitions are **unchanged**                                                  |
| `sfpshow`                     | **New in this change**: skips CPO ports during full enumeration (`get_eeprom:661` / `get_status:713` / `get_presence:683`, one place each), using the static predicate of §7.4 (DB-only, no root, no chassis). Master has no such skip. **No CPO branch is added and no CPO field is recognized** |
| `cposhow`                     | Adds the `port` command group (§7.7, §8.6), the sole producer of CPO port text                                                                                                                                                                                                                                   |

Unchanged parts: the `-p` parameter and namespace logic, tabulate headers, all functions for non-CPO ports, and the parameter definitions of `sfpshow`.

**`lpmode` / `error-status` are the two subcommands handled specially**: they differ from the other 5 — on the SFP side they are carried by `sudo sfputil show ...` (`show/interfaces/__init__.py:731/777`), not by `sfpshow`. On CPO ports the click layer routes them to `cposhow port lpmode` / `cposhow port error-status`, which **`cposhow` derives internally from STATE_DB fields** (§8.2.7 / §8.2.8); they neither enter `sfputil` nor have `cposhow` access hardware directly (hardware direct reads for `error-status -hw` are handled separately, see §8.2.8). SFP ports keep the original commands and are not changed here.

**Hard constraint (non-negotiable)**: the changes above alter only the **data source** of `show interfaces transceiver` on CPO ports, not its **availability** — any port (SFP / CPO) must produce a result under this command, and must **never** refuse to execute or suggest using another command just because the port is CPO. Rejection semantics exist only at the `sfputil` / `cpoutil` layer.

**When the ELSFP is not present**: `cpo_state_task` hits `continue` before writing `TRANSCEIVER_INFO` / `TRANSCEIVER_ELS_INFO` (`CpoStateUpdateTask._wrapper_get_presence()`), so that CPO port has no row at all in STATE_DB. Each subcommand then treats it as a "missing table" and outputs `N/A` uniformly (`presence` outputs `Not present`); this is **not treated as an error and does not interrupt the output**. To find out why, use `cpoutil show interface` / `oe` / `els` to read the live state on the register side.

This `N/A` for the **OE** side is intentional, not an oversight: xcvrd creates and deletes the OE and ELS rows **in lockstep**, because orchagent reacts to the creation/deletion of the transceiver tables for an interface, and a CPO port must present the same lifecycle semantics as a pluggable one. While the ELSFP is out, the port therefore has neither row, and the answer to "is this port populated" is `Not present` — the onboard OE being soldered on does not make the port usable, because the OE is not operational without its laser source. No action item is raised against xcvrd for this.


#### 8.2.2.`show interfaces transceiver eeprom [PORT] [-d/--dom]`

Function: Full EEPROM information. CPO ports go through `cposhow port eeprom`, which outputs two sections, OE and ELS; `-d` appends the DOM of each section.

Data source: `TRANSCEIVER_INFO` + `TRANSCEIVER_ELS_INFO`; `-d` additionally reads `TRANSCEIVER_DOM_SENSOR`/`_THRESHOLD` and `TRANSCEIVER_ELS_DOM_SENSOR`/`_THRESHOLD`.

```text
admin@sonic:~$ show interfaces transceiver eeprom Ethernet0
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        Vendor Name: BROADCOM
        Vendor PN: BCM789096FBB0KLG
        Vendor SN: SB243500200
        Vendor Date Code(YYYY-MM-DD Lot): 2024-08-12
        Vendor OUI: 00-10-18
        Vendor Rev: 01
        CMIS Rev: 5.2
        Host Lane Count: 8
        Media Lane Count: 8
        Media Interface Technology: 400GBASE-FR4
        is_replaceable: False
        ELS (els0, bank 0)
        Vendor Name: BROADCOM
        Vendor PN: ARLM-96F8DMZ
        Vendor SN: SB243600118
        Vendor Rev: 01
        CMIS Rev: 5.2
        Laser Count: 8
        Control Mode: APC
        Maximum Optical Power: 4.771 dBm
        Minimum Optical Power: -1.200 dBm
        Maximum Laser Bias: 200.000 mA
        is_replaceable: True
```

**With `-d`:**

```text
admin@sonic:~$ show interfaces transceiver eeprom Ethernet0 -d
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        ...(same as above)
        ModuleMonitorValues
        Temperature: 41.125 C
        Voltage: 3.312 V
        ModuleThresholdValues
        Temperature High Alarm: 75.000 C
        Temperature High Warn: 70.000 C
        Voltage High Alarm: 3.600 V
        Voltage Low Alarm: 3.000 V
        ChannelMonitorValues
        Lane 1: TXBias 12.400 mA / TXPower 2.104 dBm / RXPower 1.757 dBm
        Lane 2: TXBias 12.550 mA / TXPower 2.118 dBm / RXPower 1.898 dBm
        ChannelThresholdValues
        Lane 1: TXBias High Alarm 200.000 mA / TXPower High Alarm 4.771 dBm / RXPower High Alarm 3.000 dBm
        Lane 2: TXBias High Alarm 200.000 mA / TXPower High Alarm 4.771 dBm / RXPower High Alarm 3.000 dBm
        ELS (els0, bank 0)
        ...(same as above, no laser temperature)
        ModuleMonitorValues
        Temperature: 36.750 C
        Voltage: 3.300 V
        Icc: 4.512 A
        ModuleThresholdValues
        Temperature High Alarm: 70.000 C
        Temperature High Warn: 65.000 C
        Voltage High Alarm: 3.600 V
        Voltage Low Alarm: 3.000 V
        ChannelMonitorValues
        Laser 5: Bias 152.000 mA / Optical Power 4.771 dBm / Voltage 3.302 V
        Laser 6: Bias 151.200 mA / Optical Power 4.690 dBm / Voltage 3.301 V
        ChannelThresholdValues
        Laser 5: Bias High Alarm 200.000 mA / Optical Power High Alarm 5.500 dBm
        Laser 6: Bias High Alarm 200.000 mA / Optical Power High Alarm 5.500 dBm
```

`-d` mirrors the section layout of `sfpshow -d`: `ModuleMonitorValues`, `ModuleThresholdValues`, `ChannelMonitorValues`, `ChannelThresholdValues`. Thresholds come from `*_DOM_THRESHOLD` (§6.2) and are printed in their own section, never inline in the monitor section, so a parser can read values and limits separately. The ELS channel rows cover only the lasers this port owns (`Ethernet0` → lasers 5 and 6), not all eight.

Rendering follows §7.5: the `ChannelMonitorValues` / `ModuleMonitorValues` labels come from the community map, platform-private keys come from the platform map, and keys declared by neither are not displayed.

#### 8.2.3.`show interfaces transceiver info [PORT]`

Function: Static identification information. CPO ports go through `cposhow port info`, which outputs an OE section + an ELS section (different field sets, not merged).

Block layout and field labels follow the `cpoutil` interface display merged in [sonic-utilities PR 4864](https://github.com/sonic-net/sonic-utilities/pull/4864): the `<port>: CPO EEPROM detected` line, then one section per endpoint in OE → ELS order, fields at one indent level, labels from `CPO_INFO_FIELD_MAP` plus the platform map. The same block convention applies to §8.2.2 and §8.2.4; the order of the monitor/threshold sections inside the DOM block is the `sfpshow -d` order stated there. This document adds the instance and bank to the section header (`OE (oe0, bank 0)`), the annotation §4 describes for the device views.

Data source: `TRANSCEIVER_INFO` / `TRANSCEIVER_ELS_INFO`; labels are determined by `CPO_INFO_FIELD_MAP` plus the `info` category of `get_cpo_format_map()`.

```text
admin@sonic:~$ show interfaces transceiver info Ethernet0
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        Vendor Name: BROADCOM
        Vendor PN: BCM789096FBB0KLG
        Vendor SN: SB243500200
        CMIS Rev: 5.2
        Host Lane Count: 8
        Media Lane Count: 8
        is_replaceable: False
        ELS (els0, bank 0)
        Vendor Name: BROADCOM
        Vendor PN: ARLM-96F8DMZ
        Laser Count: 8
        Control Mode: APC
        is_replaceable: True
```

#### 8.2.4.`show interfaces transceiver status [PORT]`

Function: Operational status. CPO ports go through `cposhow port status`, which outputs an OE section (module/DP/config/tx + flags) + an ELS section (module/laser enable/state/fault + flags).

Data source: `TRANSCEIVER_STATUS` / `TRANSCEIVER_ELS_STATUS` for the status keys, plus `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` for the OE flags and `TRANSCEIVER_ELS_DOM_FLAG` / `TRANSCEIVER_ELS_STATUS_FLAG` for the ELS flags, including the two ELS lane-summary bits; labels are determined by `CPO_STATUS_MAP` and `CPO_DOM_FLAG_MAP` (§7.5.3), with platform-private bits from the `status` category of `get_cpo_format_map()`.

```text
admin@sonic:~$ show interfaces transceiver status Ethernet0
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        Module State: ModuleReady
        Module Fault Cause: No Fault detected
        DP State: DP1..DP8 DataPathActivated
        Config Status: ConfigSuccess (lane 1-8)
        Tx Disabled Channel: 0x00
        Tx Output Status: On (lane 1-8)
        Flags
        TempHighAlarm: False
        VccHighAlarm: False
        Rx1Los: True
        ELS (els0, bank 0)
        Module State: ModuleReady
        Module Fault Cause: No Fault detected
        Lane Summary Fault: False
        Lane Summary Warning: False
        Laser Enable: True True
        Laser State: Output on (laser 5-6)
        Output Fiber Checked: True True
        Fault Code: 0x00 0x00 (laser 5-6)
        Warning Code: 0x00 0x00 (laser 5-6)
        Flags
        Temperature High Alarm: False
        Fault Flag Lane 5: True
```

The flag rows are part of `status`, as they are for every transceiver: each block lists its `Flags` group (§8.4.3, §8.5.4 for the device view of the same groups). `Lane Summary Fault` / `Lane Summary Warning` are ELSFP-CMIS fields and live in `TRANSCEIVER_ELS_STATUS_FLAG`, not in `TRANSCEIVER_ELS_STATUS`; they stay in the status rows and are not repeated under `Flags`. `fault_code_lane<N>` / `warning_code_lane<N>` are per-lane and are shown for the lanes this port owns. `PlatformSpecificFlags` follows `Flags` when the platform map declares a private bit for the block. `error-status` stays aligned with `sfputil` and does not fold the lane summary in (§8.2.8).


#### 8.2.5.`show interfaces transceiver pm [PORT]`

**CPO does not support `pm`, and nothing is changed in this phase**.

`pm` does not take part in CPO dispatching: `get_pm` in `sfpshow` reads `TRANSCEIVER_PM|<subport>`; a CPO port has no such table, so it takes the existing `ZR_PM_NOT_APPLICABLE_STR` branch and prints `Transceiver performance monitoring not applicable`. That string is exactly what a pluggable module without PM data prints today, so CPO and SFP ports are indistinguishable to a parser:

```text
admin@sonic:~$ show interfaces transceiver pm Ethernet0
Ethernet0: Transceiver performance monitoring not applicable
```

Therefore **no port-type decision is needed and CPO rows need not be skipped**; `pm` behaves identically on CPO and non-CPO ports, satisfying "queryable on all ports". The click layer **does not dispatch `pm`** (the 6 subcommands in §8.2.1 do not include `pm`), so CPO ports still use the original `sfpshow` path.

#### 8.2.6.`show interfaces transceiver presence [PORT]`

CPO ports likewise go through `cposhow port presence`, and the decision logic is analogous to SFP ports: determine whether `TRANSCEIVER_ELS_INFO|<port>` exists.

This decision holds on CPO ports because the xcvrd CPO task gates writes to `TRANSCEIVER_ELS_INFO` on `_wrapper_get_presence(physical_port)` (`CpoStateUpdateTask._wrapper_get_presence()`):

- ELSFP present → `TRANSCEIVER_ELS_INFO` has a row → `Present`
- ELSFP absent → no row is written at all → `Not present`

Semantically this is "whether the ELSFP corresponding to this port is present", consistent with the CPO definition of physical presence, and no hardware read is needed. **Presence only means something for ELS: the OE is an on-board device, so there is no "present/absent" for it.** The `Presence` column of a CPO row is therefore a single value, not an `OE: …; ELS: …` composite.

`presence` is table type, so in a mixed-port scenario the click layer assembles **one table**:

```text
admin@sonic:~$ show interfaces transceiver presence
Port         Presence
-----------  -----------
Ethernet0    Present
Ethernet8    Present
Ethernet32   Not present
Ethernet128  Present
Ethernet136  Not present
```

`Ethernet0` and `Ethernet8` share `ELS0` and therefore agree; `Ethernet32` sits on `ELS1`, which is absent in the examples, and is the one CPO row that reports `Not present`.

#### 8.2.7.`show interfaces transceiver lpmode [PORT]`

Function: Low-power mode status. CPO ports are no longer skipped; instead, both the OE and ELS values are emitted in the `Low-power Mode` column.

Change: once the click layer determines a port is CPO it calls `cposhow port lpmode` directly; `cposhow` derives the value only from `module_state` in STATE_DB, without calling `sfp.get_lpmode()` and without going through `sfputil`:

| `module_state`                                    | `Low-power Mode`    |
| --------------------------------------------------- | --------------------- |
| `ModuleLowPwr`                                    | `On`                |
| `ModulePwrUp` / `ModuleReady` / `ModulePwrDn` | `Off`               |
| `ModuleFault`                                     | `N/A (ModuleFault)` |
| table or row missing                                | `N/A`               |

The rule is identical on both sides: OE reads `TRANSCEIVER_STATUS.module_state`, ELS reads `TRANSCEIVER_ELS_STATUS.module_state`. It matches `CmisApi.get_lpmode()`, which reports low power only for `ModuleLowPwr`, so `show cpo` and `cpoutil show ... lpmode` agree except for snapshot lag (§4).

```text
admin@sonic:~$ show interfaces transceiver lpmode
Port         Low-power Mode
-----------  -----------------
Ethernet0    OE: Off; ELS: Off
Ethernet8    OE: Off; ELS: Off
Ethernet32   OE: Off; ELS: N/A
Ethernet128  Off
Ethernet136  On
```

`Ethernet0` and `Ethernet8` share `ELS0`, so their ELS half is identical by construction; the two rows can differ only in the OE half, which is the only per-port part of this value. `Ethernet32` has no ELS row (the examples leave `ELS1` absent), so its ELS half is `N/A` while the OE half still reads.

Design choice: **keep one column and add none**; in mixed-port scenarios the click layer assembles a single table (§7.6), with CPO rows carrying the `OE: …; ELS: …` composite value.

#### 8.2.8.`show interfaces transceiver error-status [PORT] [-hw]`

Function: Error status. CPO ports are no longer skipped; a composite value is emitted, where the OE and ELS sides each reach a verdict from the same table `sfputil` uses, so a CPO row and an SFP row mean the same thing.

Change: once the click layer determines a port is CPO it calls `cposhow port error-status`; **without `-hw`** `cposhow` reads STATE_DB internally, without calling `sfp.get_error_description()` and without going through `sfputil`:

| Location                                      | Current state                                     | Change                                                                                                                                                              |
| --------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show/interfaces/__init__.py: error_status` | Calls `sudo sfputil show error-status` directly | CPO ports are routed to `cposhow port error-status`                                                                                                               |
| `-hw` path                                  | Calls `sfp.get_error_description()`             | For CPO ports the hardware read moves to `cpoutil`: `show` still accepts `-hw`, but the value is produced by a new `cpoutil` command (revision below, OI-2) |

The semantics of `-hw` (`--fetch-from-hardware`) are unchanged: skip the DB cache and force a read from hardware. Hardware direct reads on CPO ports are handled uniformly by `cpoutil` — `cposhow` reads STATE_DB only and never accesses registers.

**What this document asks of `cpoutil`** — the command itself is designed in the `cpoutil` HLD ([SONiC PR 2498](https://github.com/sonic-net/SONiC/pull/2498)); here only the contract the `show` side depends on is fixed (tracked as OI-2):

| Contract        | Value this document relies on                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Scope           | One CPO port, both sides, hardware direct read (the `-hw` semantics of `show interfaces transceiver`), bypassing STATE_DB                                                        |
| Vocabulary      | `OK` / `Unplugged` / the module error text, `N/A` for a side with no data — the same strings as this section, so a `-hw` result can be diffed against the DB result               |
| Privilege       | Root, like the rest of `cpoutil`; that is why `show` cannot do it in-process                                                                                                   |
| Failure         | Non-zero exit with the reason on stderr; `show interfaces transceiver ... -hw` maps it to `N/A` plus a warning and still exits 0 (NFR4)                                          |

Until that command lands, `show interfaces transceiver error-status -hw` on a CPO port prints `N/A` and a `warning` — it does not fall back to the DB value, because reporting a cached value under `-hw` would be wrong.

Value derivation rules (implemented inside `cposhow`, DB-only; **applicable only to the default path without `-hw`**):

| Section        | Data source                                                                                             | Rule                                                                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OE             | The `status` / `error` of the `<port>` row in `TRANSCEIVER_STATUS_SW`                                   | Same as SFP (`sfputil` `fetch_error_status_from_state_db`): `status=1` → `OK`; `status=0` → **`N/A (ELSFP absent)`**, because the absent device is the ELSFP and the OE is on board; otherwise the `error` text |
| ELS            | The same `status` field, plus `module_state` / `module_fault_cause` of the `<port>` row in `TRANSCEIVER_ELS_STATUS` | `status=0` → `Unplugged`; otherwise `OK` only when `module_state` is `ModuleReady` **and** `module_fault_cause` is `No Fault detected`; else `<module_state> (<cause>)`, with the cause omitted when it is `N/A` |
| Row absent     | —                                                                                                       | `N/A`                                                                                                                                                                                   |

The two sides read the same `status` bit: for a CPO port xcvrd derives `TRANSCEIVER_STATUS_SW.status` from the **ELSFP** plug event (`CpoStateUpdateTask._get_port_change_event()` → `get_elsfp_change_event()`), and writes the **OE** error text through `_get_port_error_description()`. So `status=0` always means "the ELSFP is out", never "the OE is out".

`lane_summary_fault` is not part of this command. It is an ELSFP-CMIS summary of the latched per-lane flags, it lives in `TRANSCEIVER_ELS_STATUS_FLAG` (not in `TRANSCEIVER_ELS_STATUS`), and those source registers are clear-on-read — folding a clear-on-read summary into `error-status` would make the verdict depend on which tool read the module last (L2). The lane summary is shown in `show interfaces transceiver status` (§8.2.4) and in `show cpo els status`, where the reader is asking about lanes rather than about link state. `error-status` therefore stays a module-level verdict, exactly like an SFP row, which is also why a mixed-port table can carry both kinds of row.

```text
admin@sonic:~$ show interfaces transceiver error-status
Port         Error Status
-----------  -----------------------------------------
Ethernet0    OE: OK; ELS: OK
Ethernet8    OE: OK; ELS: OK
Ethernet32   OE: N/A (ELSFP absent); ELS: Unplugged
Ethernet128  OK
Ethernet136  SFP EEPROM not detected
```

`Ethernet0` and `Ethernet8` share `ELS0` and therefore show the same ELS verdict; `Ethernet32` sits on `ELS1`, which is absent in the examples (§8.5.2), so its OE side reads `N/A (ELSFP absent)` rather than `Unplugged`. When the ELSFP is present but faulted, the same row reads `OE: OK; ELS: ModuleFault (Transmitter fault)`.

### 8.3.`show cpo map [PORT]`

Function: Output the mapping port → OE(id, bank) → ELS(id, bank) → laser. Pure topology; reads neither registers nor the DB. Lasers belong to the ELS, so the laser column follows the ELS section. **The table and the JSON are identical to `cpoutil show interface map`** (same columns, same order, same record shape), because both are produced by the shared formatter of §4; the only difference remains the data source of the values, which here is the static file.

Why it still exists next to `cpoutil show interface map`: the two are the same data through two doors, and the door matters. `show cpo map` runs **without root**, so it is the mapping an operator or a script can read on a box where `cpoutil` is unavailable; it sits under the same command tree as the rest of the CPO queries, so `show cpo` alone answers "what is this port wired to" without knowing that `cpoutil` exists; and it is the only mapping command that works when STATE_DB is empty or xcvrd is restarting, because it reads the static topology. `cpoutil` keeps its own copy for the field workflow that starts from the tool it is already using. Both being cheap, the duplication costs one formatter, which is shared.

Data source: `device_info.get_cpo_data()` + `platform.json` (with `port_config` as fallback).

```text
admin@sonic:~$ show cpo map
Interface    OE          OE Lanes                 ELS          ELS Lasers
-----------  ----------  -----------------------  -----------  ------------
Ethernet0    oe0 bank0   1,2,3,4,5,6,7,8          els0 bank0   4,5
Ethernet8    oe0 bank1   9,10,11,12,13,14,15,16   els0 bank0   6,7
Ethernet16   oe0 bank2   17,18,19,20,21,22,23,24  els0 bank0   0,1
```

```json
admin@sonic:~$ show cpo map Ethernet0 -j
{"Ethernet0": {"oe": {"id": "oe0", "bank": 0, "lanes": [1,2,3,4,5,6,7,8]},
               "els": {"id": "els0", "bank": 0, "lasers": [4, 5]}}}
```

Numbering: the keys of `laser_to_asic_lane_mapping` in `cpo.json` are **1-based**, while both the CLI columns and the JSON are **0-based** (`CpoMapping` normalizes on parse), so `laser 5` in the file is `4` in the output. A platform that declares no mapping falls back to `laser_ids` in `platform.json`; if neither yields a value the cell reads `N/A (needs laser_to_asic_lane_mapping)`.

### 8.4.show cpo oe

Resource dimension: a single OE instance view aggregates all the ports it drives. The difference from the port dimension is that **OE is a shared resource**, so a module-level field is stored once per logical port and a device view has to choose one copy: it follows the one-value rule of §7.6 (lowest port in natural order that has a value, annotated with that source port, plus `(differs on …)` when another port disagrees).

#### 8.4.1.`show cpo oe list`

Function: List all OE instances, the ports they drive, the bank count, and the module state.

Data source: `cpo_data["devices"]` (`device_type == optical_engine`) + a reverse index over `cpo_data["interfaces"]`; the module state is taken from `TRANSCEIVER_STATUS.module_state` of the ports of that OE, using the one-value rule of §7.6 (lowest port in natural order that has a value, with `(differs on …)` when another port disagrees), so the column is deterministic.

```text
admin@sonic:~$ show cpo oe list
OE     Ports                                   Banks   Module State
-----  --------------------------------------  ------  ------------
oe0    Ethernet0,Ethernet8,...,Ethernet56          8     ModuleReady
oe1    Ethernet64,Ethernet72,...,Ethernet120       8     ModuleReady
```

#### 8.4.2.`show cpo oe info [OE_INDEX]`

Function: OE static information. Data source `TRANSCEIVER_INFO`, read with the one-value rule of §7.6 (a field that differs across the ports of one OE is annotated rather than silently averaged or overwritten).

```text
admin@sonic:~$ show cpo oe info oe0
oe0: shared by 8 ports (Ethernet0, Ethernet8, ..., Ethernet56)
        Vendor Name: BROADCOM
        Vendor PN: BCM789096FBB0KLG
        Vendor SN: SB243500200
        CMIS Rev: 5.2
        Host Lane Count: 8
        Media Lane Count: 8
        is_replaceable: False
```

#### 8.4.3.`show cpo oe status [OE_INDEX] [-b BANK] [--history]`

Function: OE status, including DP/config/tx and the alarm flags. Data source `TRANSCEIVER_STATUS` for the status keys; the flag groups read `TRANSCEIVER_DOM_FLAG` + `TRANSCEIVER_STATUS_FLAG`; `--history` additionally reads the change counts `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` + `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT`, and set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME`.

```text
admin@sonic:~$ show cpo oe status oe0
oe0   Bank 0 (Lane 1-8)   ports: Ethernet0
        Module State            ModuleReady
        Module Fault Cause      No Fault detected
        DP State                DP1..DP8 DataPathActivated
        Config Status           ConfigSuccess (lane 1-8)
        Tx Disabled Channel     0x00
        Tx Output Status        On (lane 1-8)
        Flags
        TempHighAlarm           False
        TempLowAlarm            False
        TempHighWarn            False
        VccHighAlarm            False
        VccLowAlarm             False
        Rx1Los                  True
        Rx3Los                  True
        PlatformSpecificFlags
        pmd_fault_lane1         False
        Last updated: 2026-11-12 10:41:07
```

`Flags` and `PlatformSpecificFlags` are the two groups of the single `status` display class: community bits carry their `CPO_DOM_FLAG_MAP` label, platform-private bits come from the `status` category of `get_cpo_format_map()` (§7.5.3). `pmd_fault_lane1` is illustrative — it is what a platform would declare in that map, not an OE key that `CpoCmisApi` publishes. Every other row above is a real `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` key rendered with its community label, and every status key is a real `TRANSCEIVER_STATUS` key.

`--history` turns the flag groups into a table; the status keys keep the one-line form above:

```text
admin@sonic:~$ show cpo oe status oe0 --history
oe0   Bank 0 (Lane 1-8)   ports: Ethernet0
        Module State            ModuleReady
        Module Fault Cause      No Fault detected
        DP State                DP1..DP8 DataPathActivated
        Config Status           ConfigSuccess (lane 1-8)
        Tx Disabled Channel     0x00
        Tx Output Status        On (lane 1-8)
        Flag                  Value   Change Count   Last Set             Last Clear
        TempHighAlarm         False   0              -                    -
        Rx1Los                True    3              2026-11-12 09:12:44  2026-11-12 08:55:02
        Last updated: 2026-11-12 10:41:07
```

#### 8.4.4.`show cpo oe lpmode [OE_INDEX]`

Function: OE low-power status, **derived from `module_state`** with the four-state rule of §8.2.7. DB-only; `OeBase.get_lpmode()` is not called.

Data source: `TRANSCEIVER_STATUS.module_state`.

```text
admin@sonic:~$ show cpo oe lpmode
OE     Low-power Mode
-----  --------------
oe0    Off
oe1    On
```

#### 8.4.5.`show cpo oe dom [OE_INDEX] [-b BANK]`

Function: OE DOM values + thresholds. Data source `TRANSCEIVER_DOM_SENSOR` + `TRANSCEIVER_DOM_THRESHOLD`.

```text
admin@sonic:~$ show cpo oe dom oe0
oe0   Bank 0 (Lane 1-8)   ports: Ethernet0
        ModuleMonitorValues
        Temperature       41.125 C    (75.000 / 70.000 / 0.000 / -5.000)
        Voltage            3.312 V    (3.600 / 3.450 / 3.150 / 3.000)
        ChannelMonitorValues
        Lane  Tx Bias(mA)  Tx Power(dBm)  Rx Power(dBm)
        1     12.400       2.104          1.757
        2     12.550       2.118          1.898
        3     12.480       2.097          1.812
        Last updated: 2026-11-12 10:41:07
```

Thresholds read `(High Alarm / High Warn / Low Warn / Low Alarm)`; `Last updated` is `last_update_time`, so the reader can tell how old the snapshot is (L1).

#### 8.4.6.`show cpo oe temperature [OE_INDEX]`

Function: OE module temperature. Data source `TRANSCEIVER_DOM_SENSOR.temperature` for the value and `TRANSCEIVER_DOM_THRESHOLD` for the `HAlarm` / `HWarn` columns. `TRANSCEIVER_DOM_TEMPERATURE` is **not** read: it is written only by `DomThermalInfoUpdateTask`, which xcvrd starts for pluggable ports and only when `--dom_temperature_poll_interval` is set, so for a CPO port it has no writer and would be a permanently empty source.

```text
admin@sonic:~$ show cpo oe temperature
OE     Temperature(C)   HAlarm(C)   HWarn(C)
-----  ---------------  ----------  ---------
oe0    41.125           75.000      70.000
oe1    42.375           75.000      70.000
```

#### 8.4.7.`show cpo oe voltage [OE_INDEX]`

Function: OE Vcc and thresholds. Data source `TRANSCEIVER_DOM_SENSOR.voltage` + `TRANSCEIVER_DOM_THRESHOLD`; the `Status` column is taken from the Vcc alarm bits of `TRANSCEIVER_DOM_FLAG`, **not computed from the thresholds**, so it always agrees with the flag group of `show cpo oe status`.

```text
admin@sonic:~$ show cpo oe voltage
OE     Voltage(V)   HAlarm(V)   LAlarm(V)   Status
-----  -----------  ----------  ----------  ----------
oe0    3.312        3.600       3.000       OK
oe1    2.912        3.600       3.000       VccLowAlarm
```

#### 8.4.8.`show cpo oe firmware-info [OE_INDEX]`

Function: OE firmware versions. Data source `TRANSCEIVER_FIRMWARE_INFO` (`active_firmware` / `inactive_firmware`).

```text
admin@sonic:~$ show cpo oe firmware-info
OE     Active   Inactive
-----  -------  ---------
oe0    1.2      1.1
oe1    1.2      1.0
```

### 8.5.show cpo els

#### 8.5.1.`show cpo els list`

Function: List all ELS instances, the ports they drive, the laser count, and the module state.

Data source: `cpo_data["devices"]` (`device_type == external_laser_source`) + a reverse index over `interfaces` + `TRANSCEIVER_ELS_INFO` (`lane_count`/`control_mode`). The module state follows the one-value rule of §7.6. The bank count is not a column here: every ELS carries one bank, so the column would be constant; bank-scoped detail is in `show cpo els status -b`.

```text
admin@sonic:~$ show cpo els list
ELS     Ports                                            Lasers  Module State
------  -----------------------------------------------  ------  ------------
els0    Ethernet0,Ethernet8,Ethernet16,Ethernet24        8       ModuleReady
els1    Ethernet32,Ethernet40,Ethernet48,Ethernet56      8       ModuleReady
els2    Ethernet64,Ethernet72,Ethernet80,Ethernet88      8       ModuleReady
els3    Ethernet96,Ethernet104,Ethernet112,Ethernet120   8       ModuleReady
```

#### 8.5.2.`show cpo els presence [ELS_INDEX]`

Function: ELS presence.

Data source: whether `TRANSCEIVER_ELS_INFO` exists

```text
admin@sonic:~$ show cpo els presence
ELS     Presence      Ports
------  ------------  -----------------------------------------------
els0    Present       Ethernet0, Ethernet8, Ethernet16, Ethernet24
els1    Not present   Ethernet32, Ethernet40, Ethernet48, Ethernet56
els2    Present       Ethernet64, Ethernet72, Ethernet80, Ethernet88
els3    Present       Ethernet96, Ethernet104, Ethernet112, Ethernet120
```

#### 8.5.3.`show cpo els info [ELS_INDEX]`

Function: ELS static information. Data source `TRANSCEIVER_ELS_INFO`.

```text
admin@sonic:~$ show cpo els info els0
els0: drives 4 ports (Ethernet0, Ethernet8, Ethernet16, Ethernet24)
        Vendor Name: BROADCOM
        Vendor PN: ARLM-96F8DMZ
        Vendor SN: SB243600118
        Laser Count: 8
        Control Mode: APC
        Maximum Optical Power: 4.771 dBm
        Minimum Optical Power: -1.200 dBm
        Maximum Laser Bias: 200.000 mA
        CMIS Rev: 5.2
        is_replaceable: True
```

#### 8.5.4.`show cpo els status [ELS_INDEX] [-b BANK] [--history]`

Function: ELS status (module + laser enable/state/fault/warning) and the alarm flags. Data source `TRANSCEIVER_ELS_STATUS`, plus `TRANSCEIVER_ELS_STATUS_FLAG` for the lane summary and the flags, `TRANSCEIVER_ELS_DOM_FLAG` for the module/lane alarm bits; `--history` additionally reads the change counts `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` + `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT`, and set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME`.

```text
admin@sonic:~$ show cpo els status els0
els0   Bank 0 (Laser 1-8)   ports: Ethernet0,Ethernet8,Ethernet16,Ethernet24
        Module State            ModuleReady
        Module Fault Cause      No Fault detected
        Lane Summary Fault      False
        Lane Summary Warning    False
        Laser Enable            True True True True True True True True
        Laser State             Output on (laser 1-8)
        Output Fiber Checked    True True True True False False True True
        Fault Code              0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        Warning Code            0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        Flags
        Temperature High Alarm  False
        Voltage Low Warn        False
        Fault Flag Lane 5       True
        Warning Flag Lane 6     True
        PlatformSpecificFlags
        mpd_power_lane5         False
        Last updated: 2026-11-12 10:41:07
```

`Lane Summary Fault` / `Lane Summary Warning` stay in the status rows and are not repeated under `Flags`: both are read from `TRANSCEIVER_ELS_STATUS_FLAG`, and the same bit is printed once.

The community labels above are the `CPO_DOM_FLAG_MAP` entries for the raw keys `temperature_alarm_high`, `voltage_warn_low`, `lane_summary_fault`, `lane_summary_warning`, `fault_flag_lane<N>` and `warning_flag_lane<N>`; `mpd_power_lane5` is an illustrative platform-private key declared in the `status` category of `get_cpo_format_map()`, not an `ElsfpApi` key. The `Last updated` line is required on every status block (§7.5.3, rule 4). Only the lanes this port owns are listed — `Ethernet0` owns lasers 5 and 6.

`--history` turns the flag groups into a table in the CMIS diagnostic-HLD layout; the status rows keep their one-line form:

```text
admin@sonic:~$ show cpo els status els0 --history
els0   Bank 0 (Laser 1-8)   ports: Ethernet0,Ethernet8,Ethernet16,Ethernet24
        Module State            ModuleReady
        Module Fault Cause      No Fault detected
        Lane Summary Fault      False
        Lane Summary Warning    False
        Laser Enable            True True True True True True True True
        Laser State             Output on (laser 1-8)
        Output Fiber Checked    True True True True False False True True
        Fault Code              0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        Warning Code            0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        Flag                    Value   Change Count   Last Set             Last Clear
        Temperature High Alarm  False   0              -                    -
        Fault Flag Lane 5       True    2              2026-11-12 09:58:31  -
        Last updated: 2026-11-12 10:41:07
```

This is the **device** view, so it lists all eight lasers of `els0`, not the two that `Ethernet0` owns; the port view of §8.2.4 narrows the same rows to the port's own lanes.

#### 8.5.5.`show cpo els lpmode [ELS_INDEX]`

Function: ELS low-power status, derived from `module_state` with the four-state rule of §8.2.7. DB-only; `ElsfpApi.get_lpmode()` is not called.

```text
admin@sonic:~$ show cpo els lpmode
ELS     Low-power Mode
------  --------------
els0    Off
els1    On
```

#### 8.5.6.`show cpo els dom [ELS_INDEX] [-b BANK]`

Function: ELS DOM values + thresholds, including per-lane bias/optical power/voltage. Data source `TRANSCEIVER_ELS_DOM_SENSOR` + `TRANSCEIVER_ELS_DOM_THRESHOLD`. If no related data is available, display N/A.

```text
admin@sonic:~$ show cpo els dom els0
els0   Bank 0 (Laser 1-8)
        ModuleMonitorValues
        Temperature       36.750 C    (70.000 / 65.000 / 0.000 / -5.000)
        Voltage            3.300 V    (3.600 / 3.450 / 3.150 / 3.000)
        Icc                4.512 A
        ChannelMonitorValues
        lane   Bias(mA)   Optical Power(dBm)  Voltage(V)
        1      152.000    4.771               3.302
        2      151.200    4.690               3.301
        3      150.400    4.655               3.299
        Last updated: 2026-11-12 10:41:07
```

#### 8.5.7.`show cpo els temperature [ELS_INDEX]`

Function: ELS module temperature. Data source `TRANSCEIVER_ELS_DOM_SENSOR.temperature` for the value and `TRANSCEIVER_ELS_DOM_THRESHOLD` for the `HAlarm` / `HWarn` columns. `TRANSCEIVER_ELS_DOM_TEMPERATURE` is declared by `CpoXcvrTableHelper` but no writer publishes to it — xcvrd only uses it in its delete lists — so it is not a data source here.

```text
admin@sonic:~$ show cpo els temperature
ELS     Temperature(C)   HAlarm(C)   HWarn(C)
------  ---------------  ----------  ---------
els0    36.750           70.000      65.000
els1    37.125           70.000      65.000
```

#### 8.5.8.`show cpo els voltage [ELS_INDEX]`

Function: ELS Vcc and thresholds. Data source `TRANSCEIVER_ELS_DOM_SENSOR.voltage` + `TRANSCEIVER_ELS_DOM_THRESHOLD`; the `Status` column is taken from the Vcc alarm bits of `TRANSCEIVER_ELS_DOM_FLAG`, **not computed from the thresholds**, so it always agrees with the flag group of `show cpo els status`.

```text
admin@sonic:~$ show cpo els voltage
ELS     Voltage(V)   HAlarm(V)   LAlarm(V)   Status
------  -----------  ----------  ----------  ------
els0    3.300        3.600       3.000       OK
els1    3.288        3.600       3.000       OK
```

#### 8.5.9.`show cpo els firmware-info [ELS_INDEX]`

Function: ELS firmware versions. Data source `TRANSCEIVER_ELS_FIRMWARE_INFO`.

```text
admin@sonic:~$ show cpo els firmware-info
ELS     Active   Inactive
------  -------  ---------
els0    0.9      0.8
els1    0.9      0.8
```

### 8.6.cposhow Direct Invocation Form

`show cpo X` and `cposhow X` correspond one-to-one; the only differences are alias resolution and default namespace handling:

```text
cposhow map
cposhow map Ethernet0 --json
cposhow oe dom oe0 -b 1
cposhow oe lpmode
cposhow els dom els0 --json
cposhow els presence
```

```bash
cposhow port info --port Ethernet0              # CPO port data query
cposhow port info --all -n asic0
cposhow port eeprom -d --port Ethernet0
cposhow port error-status --all
```

The subcommands of `cposhow` are the four groups `map` / `oe` / `els` / `port` — **topology** is carried by `show cpo map`, while the port-dimension data of `show interfaces transceiver` is produced by `cposhow port` (§7.7).

## 9.Warmboot and Fastboot Design Impact

1. `show cpo` / `cposhow` are stateless and cache nothing (apart from a one-shot in-process cache), so there is no behavior difference during warm/fast reboot.
2. STATE_DB is preserved during warm reboot, so `show cpo` can return the previous snapshot even before xcvrd's first poll (same as `show interfaces transceiver`).
3. Topology comes from `cpo.json` (a static file) and is queryable immediately after reboot, without waiting for any daemon.
4. No special warm reboot handling is required.

## 10.Memory Consumption & CPU Usage

**Memory**

1. Peak per-process usage < 80 MB (64 ports × 4 banks fully expanded + the merged format map);
2. The `cpo.json` parse result (`CpoMapping`) stays resident at < 2 MB;
3. It is released when the command ends; there is no persistent cache.

**CPU / latency**

| Path                                                  | Cost     | Notes                                                                                     |
| ----------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------- |
| `get_cpo_data()` + `platform.json` + one `CpoMapping` build | < 15 ms  | File < 50 KB, pure JSON; built **once per process** and reused by every later query      |
| PORT table read (CONFIG_DB)                           | < 5 ms   | `index` per logical port, needed for the physical-port criterion (§7.4)                  |
| Platform format map (§7.5.3)                          | < 50 ms  | One `import sonic_platform.chassis` plus one classmethod call; **no chassis object**, so none of the 0.5–1 s construction cost of `platform_chassis` |
| STATE_DB reads (HGETALL, 64 ports)                    | < 300 ms | pipeline                                                                                  |
| Port classification (`show interfaces transceiver`) | < 5 ms   | One set intersection per port over the two results above; **no chassis, no root** |

- No background polling; `sfpshow` / `cposhow` are both pure DB paths;
- In the `show interfaces transceiver` scenario the two subprocesses run **in sequence**, not in parallel: the output is ordered and assembled by the click layer (§7.6), and the memory increase is only the two output texts (about 1–2 MB for 64 CPO + 64 SFP ports in full).

## 11.Restrictions/Limitations

- **L1.** Queried data is an xcvrd polling snapshot, not real-time; for real-time register values use `cpoutil`
- **L2.** The risk to the alarm-bit change counters comes from **hardware** reads, not from `show`: a `cpoutil` read of a clear-on-read latch clears it before xcvrd's next poll, so xcvrd never sees the event and the change count stays at its old value. A DB read (`show cpo`) changes no count. Therefore `show cpo` reads the DB only and never triggers a hardware read; when in doubt about a flag that does not move, compare with `cpoutil`.
- **L3.** Platform-only keys appear in table output only if the platform map declares an entry for them; a platform that overrides nothing shows the community keys alone (`--show-suppressed` lists the DB keys that have no map entry, and `--json` always keeps the raw keys). Keys covered by neither the community map nor the platform map are likewise not displayed.
- **L4.** `show interfaces transceiver` provides no JSON (status quo); when machine readability is needed, use `show cpo ... -j` or `cposhow port ... -j`, or read STATE_DB directly.
- **L5.** On multi-ASIC platforms the click layer identifies CPO ports per namespace. `-n` selects one namespace; **omitted, the command covers every namespace**, matching `sfpshow`'s `@multi_asic_util.run_on_multi_asic` default, so `show cpo oe list` on a multi-ASIC box is not silently empty when run from the default namespace. Output is grouped per namespace with the namespace named in the heading; merged cross-namespace aggregation into a single table is out of scope for this change.

## 12.Testing Requirements/Design

### 12.1.Unit Test

1. `topology`: `cpo_data` parsing, even splitting by `max_banks`, bank → lane conversion validation; the classification helper: `cpo.json` names resolved to `platform.json` `index` (a name with no PORT entry skipped, an empty result reported as `NO_TOPOLOGY`), physical-port intersection (1:1 map, ganged port, breakout subports), and the `NO_TOPOLOGY` / `INVALID` / `OK` split of §7.4;
2. `format map`: the base class returns `{}`; a vendor override is picked up through `Chassis.get_cpo_format_map()` without instantiating the chassis, and the three categories and two endpoints are read from the nested dict; `{lane}` / `{bank}` placeholder expansion (bank-relative index for OE, absolute lane for ELS); add-only behavior (a map entry for a community key is ignored with a warning); a key the map does not declare is not displayed (`--show-suppressed` lists it); and the degradation behaviors for an empty map, an invalid entry, a raising call, and an unimportable platform module;
3. `formatter`: table/JSON consistency, booleans, uniform `N/A` for missing values; the merged `status` block (status keys, then `Flags` / `PlatformSpecificFlags`, the ELS lane summary printed once, and `--history` applied to the flag groups only);
4. Parameter parsing: invalid port, invalid index, `--bank` out of range;
5. Exit codes: distinguishing a missing `cpo.json` (3) from a file that exists but fails parsing/validation (4), with `os.path.isfile()` checked first.

### 12.2.Platform Functional Test

1. All query commands return valid output at the three granularities: single port / single instance / full; the full run is repeated on a HwSKU whose physical ports are broken out, where **every subport of a CPO physical port must land on the CPO side** and no `sfputil` call may be made for it (§7.4);
2. Byte-for-byte comparison of `show cpo X` and `cposhow X` output;
3. Platform-specific key injection: override `get_cpo_format_map()` with custom keys and verify label/unit/precision take effect; then put a key in the DB that the map does not declare and verify it **does not appear** in table mode, can be listed by `--show-suppressed`, and keeps its raw key in JSON mode; finally run the same platform with the base-class `{}` and verify the output is community-only with exit 0;
4. ELS plug/unplug: `presence` goes from Present to Not present, and `lpmode` / `error-status` follow (`error-status` reads `OE: N/A (ELSFP absent); ELS: Unplugged`); confirm that `lpmode` and `error-status` on a **different** port of the same ELS report the same ELS half;
5. `show interfaces transceiver` outputs both the OE and ELS sections on CPO ports with no skip hint; in a full mixed run the table-type subcommands (`presence` / `lpmode` / `error-status`) produce **one table** with composite values on CPO rows, while block-type subcommands produce one block per port with no duplicate rows; `pm` on a CPO port prints `Transceiver performance monitoring not applicable`, the same string as a pluggable port without PM data;
6. **Hard availability constraint**: on the same CPO port, all 7 subcommands of `show interfaces transceiver` are executable.

**Impact outside the CLI itself** (all three are part of the deliverable, not follow-ups):

7. **sonic-mgmt**: `parse_eeprom()`, `parse_output()`, and the checks for `SFP EEPROM detected` need CPO support. The one-header-per-port layout of §7.6 keeps the port name as the dict key, so `parse_eeprom()` continues to produce one entry per port; the OE/ELS sub-blocks are parsed as sub-sections. A sonic-mgmt PR accompanies PR 5032;
8. **`sonic-utilities` unit tests**: the `show/interfaces` dispatch is tested with a mock `cpo.json` and a mock STATE_DB, and one case runs with **no `cpo.json`** to prove that a non-CPO platform's output is byte-identical to master;
9. **`doc/Command-Reference.md`**: the `show cpo` family and `cposhow` are added, and the CPO behavior of the 6 `show interfaces transceiver` subcommands is noted under their existing entries.

### 12.3.Integration Test

1. Script compatibility with mixed traversal of 64 CPO + N ordinary ports alongside `show interfaces transceiver`;
2. Table-missing scenarios during an xcvrd restart (the command does not crash and outputs `N/A`);
3. Multi-ASIC: `show cpo oe list` / `els list` without `-n` cover every namespace (nothing is silently missing when run from the default namespace); with `-n asic0` only that namespace appears; `show interfaces transceiver` on a full run splits CPO and SFP ports **per namespace** and still produces one table per subcommand.

### 12.4.Edge Case Test

1. `cpo.json` missing → all commands report "no CPO topology" with exit code 3;
2. `cpo.json` present but JSON parsing fails, `CpoMapping` validation fails, or normalization raises (`ValueError` / `KeyError` / `AttributeError` — e.g. a legacy file that has `interfaces` but no `devices`) → `show cpo` prints an explicit error with the file path and exits 4, **once**, not once per port; on the same platform `show interfaces transceiver` degrades **every** port to the SFP path with a single stderr warning and exits 0, so ordinary SFP ports are not collateral damage;
3. One entry declared by the map is invalid (empty label / unknown type / unit outside the list) → that key is skipped with a stderr warning, the command still succeeds with exit code 0 (NFR2);
4. Map not overridden (base class `{}`) → render with the community map only, platform-private keys not displayed, exit code 0;
5. A new uncovered key added by the API → output complete, no error, and the key is not displayed per §7.5.4;
6. Fields inconsistent across multiple ports of the same OE → the row shows the value of the lowest port in natural order and appends `(differs on …)` naming the other ports (§7.6);
7. ELSFP not present → every subcommand exits 0 with the value `N/A` (`presence` shows `Not present`; `error-status` shows `OE: N/A (ELSFP absent); ELS: Unplugged`);
8. Breakout subports: a 2x400G and a 4x200G configuration on a CPO physical port → every subport is classified CPO (§7.4), each reports only its own lanes, and a subport whose row is published on the first sibling still shows its own values (§7.6 port-dimension rule 1).

## 13.Open/Action Items

| ID   | Item                                                                                                   | Owner              | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---- | ------------------------------------------------------------------------------------------------------ | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OI-1 | Move `cpoutil/mapping.py` up to `utilities_common/cpo_mapping.py`                                  | utilities          | Avoids `cposhow` depending on a private module of the `cpoutil` package; pure refactor, no behavior change                                                                                                                                                                                                                                                                                                                                                                                                                      |
| OI-2 | A new `cpoutil` command providing hardware direct-read results for `error-status -hw` on CPO ports | cpoutil / platform | The command itself is designed in the `cpoutil` HLD ([SONiC PR 2498](https://github.com/sonic-net/SONiC/pull/2498)), not here. This document fixes only the four-point contract the `show` side depends on (§8.2.8): scope, vocabulary, privilege, failure mode. Until it lands, `show interfaces transceiver error-status -hw` prints `N/A` plus a `warning` and still exits 0 |
| OI-3 | Default an omitted `els.bank` to 0 | cpoutil / utilities | `_bank(..., optional=True)` returns `"N/A"` today for an association that carries no `bank`; §7.6 requires 0 for OE and ELS alike, so one file yields one spelling in `map`, JSON and section headings. `CpoMapping` keeps taking `index` from the `port_config` entry, since `cpo.json` no longer declares it (§7.4) |
| OI-4 | `get_cpo_format_map()` on the platform class | sonic-platform-common / vendor platform | New API (§7.5.3): base class returns `{}`; the vendor override is a two-line classmethod that imports its CPO class and returns `PLATFORM_SPECIFIC_FORMAT_MAP`, which already exists on `CpoBase` ([sonic-platform-common PR 825](https://github.com/sonic-net/sonic-platform-common/pull/825), merged). The base-class stub lands in `sonic-platform-common` together with the `cposhow` consumer ([sonic-utilities PR 5032](https://github.com/sonic-net/sonic-utilities/pull/5032)); each vendor adds its override in the same change that publishes its private keys. No vendor override is required for this document to be correct — a platform without one renders the community map |

## 14.Dependencies

| Dependency                                                                                   | Kind                | What this document relies on                                                                                                                                                   | State today                                                                                                                                                                                                                      |
| -------------------------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [sonic-platform-daemons PR 933](https://github.com/sonic-net/sonic-platform-daemons/pull/933) | Code (xcvrd)        | Publishes the ELS DOM / flag / status / firmware / temperature tables and their `*_FLAG_CHANGE_COUNT`, `*_SET_TIME`, `*_CLEAR_TIME` counterparts                         | **Merged.** The producer is `CpoDomInfoUpdateTask` in `xcvrd/cpo/cpo_dom_mgr.py`; every §6.2 row is readable without further work                                                                                          |
| [sonic-buildimage PR 29676](https://github.com/sonic-net/sonic-buildimage/pull/29676)          | Integration (platform) | The front end of this document's data: builds `Oe` / `Elsfp` / `Cpo` from the `devices` and interface associations of `cpo.json`, publishes the CPO topology from the platform hook, reports ELS presence on its own change-event stream, and renames the existing vendor CLI | **Open**                                                                                                                                                                                                                         |
| Platform `cpo.json`                                                                        | Data (vendor)       | Topology only: `devices`, `interfaces`, and the `bank` of each port→device association (§7.3). It is read together with `platform.json`, which supplies the `index` of each named interface (§7.4). It carries no display text | Delivered per platform; no code dependency. A legacy file without `devices` is `INVALID` (§7.4), not `NO_TOPOLOGY`                                                              |
| Platform format map (`get_cpo_format_map()`)                                               | Code (platform)     | Labels / units / precision of platform-private keys (§7.5.3); base class returns `{}`, the vendor returns its CPO class's `PLATFORM_SPECIFIC_FORMAT_MAP`                        | New API, tracked as OI-4: the base-class stub lands with sonic-utilities PR 5032, the vendor's two-line override lands with the vendor's own key change. A platform with no override renders the community map |
| [sonic-utilities PR 5032](https://github.com/sonic-net/sonic-utilities/pull/5032)             | Code (utilities)    | `cposhow` itself, and the `show/interfaces` dispatch of the 6 subcommands to `cposhow port` (§8.2.1)                                                                    | Open                                                                                                                                                                                                                             |
| [sonic-utilities PR 4864](https://github.com/sonic-net/sonic-utilities/pull/4864)             | Code (utilities)    | `cpoutil` itself — the device-side peer of every §8.2.x CPO block, and the source of the block layout and field labels those blocks follow (§8.2.3). It also ships `cpoutil/mapping.py` and the display maps §7.5.2 promotes | **Merged**                                                                                                                                                                                                                       |
| [cpoutil HLD, SONiC PR 2498](https://github.com/sonic-net/SONiC/pull/2498)                    | Design              | `cpoutil` command family, and the hardware direct read on CPO ports for `error-status -hw` (§8.2.8, OI-2). `cposhow` imports `CpoMapping` from `cpoutil/mapping.py` | **Open** (under review)                                                                                                                                                                                                          |
| [cpoutil CPO Component Firmware Management HLD](https://github.com/sonic-net/SONiC/blob/master/doc/cpo-util/cpo-util-hld.md) | Design (merged)     | Firmware query (`cpoutil show {oe,els} fwversion`) and upgrade (`cpoutil firmware upgrade` / `download` / `run` / `commit`), and the rule that these commands do not write `TRANSCEIVER_FIRMWARE_INFO` | **Merged.** No dependency for the commands here; it fixes what `firmware-info` (§8.4.8 / §8.5.9) can show and when that value changes |

Order of landing: this document is readable end-to-end once PR 933 is merged, which it is; the two Open items (PR 5032 for the CLI, PR 29676 for the platform `cpo.json`) gate the commands themselves, and the Open design item (PR 2498) is why the `error-status -hw` path is still in its interim shape (OI-2).

**Relationship with the CPO work already in flight.** Three open PRs predate this document and take the opposite division of labour, so the relationship is stated explicitly rather than left implicit:

| PR | What it does | Relationship to this document |
| -- | ------------ | ----------------------------- |
| [sonic-utilities PR 4673](https://github.com/sonic-net/sonic-utilities/pull/4673) | Adds CPO output to `sfputil` | **Re-scoped by this document.** `sfputil` keeps the refusal and the "use `cpoutil`" hint on CPO ports; it renders no CPO data. Its CPO-rendering part is superseded, not depended on |
| [sonic-utilities PR 4708](https://github.com/sonic-net/sonic-utilities/pull/4708) | Adds CPO output to `sfputil` / `sfpshow` | **Re-scoped by this document.** `sfpshow` gains only the §7.4 skip; CPO text has exactly one producer, `cposhow port` (§7.6). If 4708 lands unchanged, the same port would have two producers with two formats |
| [sonic-buildimage PR 28325](https://github.com/sonic-net/sonic-buildimage/pull/28325) | Vendor CPO fields for the two tools above | **Becomes unnecessary on the `show` path.** Those fields are rendered by `cposhow` from STATE_DB with labels from the platform map (§7.5.3); the PR stays relevant only for the `cpoutil` path, if at all |

This document therefore **does not depend on** any of the three. It replaces their `show`-side behavior, and the decision on how to close or re-scope them belongs to their authors; what it must not do is land alongside them and create a second CPO output format on the same command.

## 15.SAI API

**Not applicable.** This feature adds no SAI attribute, no SAI API call, and no ASIC-side behavior: every command in this document is a read-only consumer of STATE_DB plus the static `cpo.json` (§6.2). The tables themselves are written by xcvrd through the existing CMIS/ELSFP API paths (`CmisApi` / `ElsfpApi`), which are unchanged by this document, and no new SAI object is introduced for OE or ELS.

## 16.Configuration and management

**Not applicable.** This document defines query commands only (`show cpo`, `cposhow`, and the CPO behavior of `show interfaces transceiver`). There is no new configuration command, no ConfigDB schema change, no YANG model, and no `config_db.json` field.

`config interface *` (speed, FEC, MTU, low-power, and similar) is **not affected by this change and is not revised**: CPO ports keep their existing configuration semantics and existing commands (see §7.7, "Relationship with `config interface`").

---

## Appendix A: Command ↔ Source Mapping

Everything below is referenced **by symbol, not by line number**: line numbers drift between branches, and the upstream task names changed when the tables were contributed (sonic-platform-daemons PR 933, **merged**, publishes the CPO DOM set and renamed `xcvrd/cpo/dom_mgr.py` to `xcvrd/cpo/cpo_dom_mgr.py`).

| Command                                                                      | Data source                                                                                                                                                                                                      | Producer / entry point                                                                                                            | Underlying API (origin)                                                                                                                                  |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show cpo map` / `cposhow map`                                           | `cpo.json` + `platform.json`                                                                                                                                                                                 | `device_info.get_cpo_data()` + `CpoMapping` (`cpoutil/mapping.py`)                                                          | —                                                                                                                                                       |
| `show cpo oe list` / `els list`                                          | `cpo_data["devices"]` + `cpo_data["interfaces"]`                                                                                                                                                             | `CpoMapping` reverse index                                                                                                      | —                                                                                                                                                       |
| `show interfaces transceiver presence`                                     | `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                         | `CpoStateUpdateTask` — writes the row only when `_wrapper_get_presence()` is true                                            | Whether `TRANSCEIVER_ELS_INFO` exists                                                                                                                  |
| `show interfaces transceiver info`                                         | `TRANSCEIVER_INFO` / `TRANSCEIVER_ELS_INFO`                                                                                                                                                                  | `CpoStateUpdateTask`                                                                                                            | `CmisApi.get_transceiver_info()` / `ElsfpApi.get_elsfp_info()`                                                                                       |
| `show interfaces transceiver status`                                       | `TRANSCEIVER_STATUS` / `TRANSCEIVER_ELS_STATUS`                                                                                                                                                              | `CpoDomInfoUpdateTask`                                                                                                          | `CpoCmisApi.get_transceiver_status()` / `ElsfpApi.get_elsfp_status()`                                                                                |
| `show cpo oe / els status` (flag groups)                                  | `*_DOM_FLAG` / `*_STATUS_FLAG` + `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT` | `CpoDomInfoUpdateTask`                                                                                                          | `get_transceiver_dom_flags()` / `get_elsfp_dom_flags()`                                                                                              |
| `show cpo oe / els dom` / `cposhow port eeprom -d`                       | `*_DOM_SENSOR` / `*_DOM_THRESHOLD`                                                                                                                                                                           | `CpoDomInfoUpdateTask` + `CPODOMDBUtils`                                                                                      | `get_transceiver_dom_real_value()` / `get_elsfp_dom_real_value()`                                                                                    |
| `show cpo oe / els temperature`                                            | `*_DOM_SENSOR.temperature` (value) + `*_DOM_THRESHOLD` (limits)                                                                                                                                            | `CpoDomInfoUpdateTask` + `CPODOMDBUtils`                                                                                      | `get_module_temperature()`                                                                                                                             |
| `show cpo oe / els voltage`                                                | `*_DOM_SENSOR.voltage` + the threshold tables; the `Status` column reads `*_DOM_FLAG`                                                                                                                      | `CpoDomInfoUpdateTask`                                                                                                          | `CmisApi.get_voltage()` / `ElsfpApi.get_module_voltage()`                                                                                            |
| `show cpo oe / els firmware-info`                                          | `*_FIRMWARE_INFO`                                                                                                                                                                                              | `CpoDomInfoUpdateTask`                                                                                                          | `get_transceiver_info_firmware_versions()` / `get_elsfp_info_firmware_versions()`                                                                    |
| `show cpo oe / els lpmode` / `cposhow port lpmode`                       | `*_STATUS.module_state`                                                                                                                                                                                        | Derived inside `cposhow` (§8.2.7)                                                                                              | `ModuleLowPwr` → `On`; `ModulePwrUp` / `ModuleReady` / `ModulePwrDn` → `Off`; `ModuleFault` → `N/A (ModuleFault)`; no data → `N/A` |
| `show interfaces transceiver error-status` / `cposhow port error-status` | `status` / `error` of `TRANSCEIVER_STATUS_SW` (both halves) + `module_state` / `module_fault_cause` of `TRANSCEIVER_ELS_STATUS`; `-hw`: the `cpoutil` command of OI-2 | `CpoStateUpdateTask` — writes the status from the ELSFP plug event and the error text from the OE API | `CmisApi.get_error_description()` (through `CpoCmisApi`) / `ElsfpApi.get_elsfp_status()` |
| Labels / units of every table above                                        | community map in `utilities_common/cpo_format.py` + the platform map                                                                                                                                    | `utilities_common` + the platform class (`Chassis.get_cpo_format_map()`, classmethod)                                                  | —                                                                                                                                                       |

## Appendix B: Exit Codes

| Code | Meaning                      | Trigger                                                                                                                            |
| ---- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 0    | Success                      | Includes "some port data missing, output as `N/A`"                                                                               |
| 2    | Usage error                  | Unknown subcommand / invalid argument / a port that does not exist / `-b` out of the bank range. `cposhow` validates the port itself and raises the usage error (`ctx.fail()`); click does not check that a port exists, so this code comes from `cposhow`, not from click |
| 3    | Platform has no CPO topology | `cpo.json` does not exist (`os.path.isfile()` is checked **before** calling `get_cpo_data()`)                          |
| 4    | CPO topology invalid         | The file exists but JSON parsing fails, normalization raises, or `CpoMapping` validation fails                                  |
| 5    | Runtime environment error    | STATE_DB connection failure, unrelated to the data content                                                                         |

Codes 3 and 4 are `show cpo` / `cposhow` codes. `show interfaces transceiver` **never** propagates them: on both states every port takes the SFP path and the command exits 0 (§7.4), because that command must stay available on every port (§8.2.1).
