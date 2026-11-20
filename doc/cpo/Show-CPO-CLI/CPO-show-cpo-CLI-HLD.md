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
  - 7.6.Output Contract and Exit Codes
  - 7.7.show interfaces transceiver Dispatching
- 8.Command Functional Specification (show)

  - 8.1.Common Parameters
  - 8.2.show interfaces transceiver (CPO Port Behavior)
  - 8.3.show cpo map
  - 8.4.show cpo oe
  - 8.5.show cpo els
  - 8.6.cposhow Direct Invocation Form
- 9.Warmboot and Fastboot Design Impact
- 10.Memory Consumption & CPU Usage
- 11.Restrictions/Limitations
- 12.Testing Requirements/Design
- 13.Open/Action Items
- 14.Dependencies
- 15.SAI API
- 16.Configuration and management
- Appendix A: Command ↔ Source Mapping
- Appendix B: Exit Codes
- Appendix C: Sample `cpo.json`

---

## 1.Revision

| Rev | Date       | Author     | Description                                                                                                                                                                                                                                               |
| --- | ---------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0 | 2026-11-06 | KroosMicas | Initial: CPO CLI for SONiC — the `show cpo` / `cposhow` query family (map / oe / els, `cposhow port` command group), dispatching and rendering of `show interfaces transceiver` on CPO ports, and the platform-specific key format map framework |
| 1.1 | 2026-11-12 | KroosMicas | Revised the key-map, the `cpo_port` judgment logic, along with other minor tweaks.                                                                                                                                                                      |

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
6. The **platform-specific key** rendering framework for the four data classes `status` / `flag` / `dom` / `info`

**Out of scope:**

1. The functionality and implementation of `cpoutil` / `sfputil` themselves, including the mutual-exclusion hints between them and CPO handling on the `sfputil` side (see [github.com/sonic-net/SONiC/pull/2498](https://github.com/sonic-net/SONiC/pull/2498) for both); this document does not describe these two tools
2. Firmware query and upgrade are carried by `cpoutil` (`cpoutil show fwversion` and the `cpoutil` upgrade commands, see [SONiC PR #2484](https://github.com/sonic-net/SONiC/pull/2484)); `show cpo` only reports the firmware versions already in the DB (`firmware-info`, §8.4.9 / §8.5.10)
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
| Format Map  | Mapping table from a DB field key → display name/unit/group, in two layers: the community common map and the platform-specific map |

## 4.Overview

`show cpo` / `cposhow` answer the question: **what state does the system believe this port is in** (similar to `show interfaces transceiver`). Data comes from the STATE_DB snapshot plus the `cpo.json` topology, and root is not required.

When **direct register read/write** is needed (similar to the former `sfputil`), use `cpoutil`; that is out of scope here. The two read different layers, so they coexist rather than replace each other:

| Dimension   | `cpoutil show interface` / `oe` / `els`                 | `show cpo` / `cposhow`                                         |
| ----------- | ------------------------------------------------------------- | ------------------------------------------------------------------ |
| Data source | Registers read directly (device API)                          | STATE_DB (snapshot written by periodic xcvrd polling)              |
| Privilege   | Requires root                                                 | No root required                                                   |
| Freshness   | Real-time value                                               | Value from the last poll, with `Last updated`                    |
| Purpose     | Debugging, field triage, ground truth when the DB has no data | Day-to-day queries, stable output scripts/automation can depend on |

The two command families have overlapping nouns; the one-to-one mapping and the expected differences are below:

| `show cpo` / `cposhow`                                                                    | `cpoutil show` peer                   | Data source                                               | Expected difference |
| --------------------------------------------------------------------------------------------- | --------------------------------------- | --------------------------------------------------------- | ------------------- |
| `map`                                                                                       | `interface map`                       | both from`cpo.json` (same source, neither reads the DB) | None                |
| `els presence`                                                                              | `interface presence`                  | cposhow:STATE_DB <br />cpoutil: API                      | None                |
| `oe status`, `els status`                                                                 | `oe status`, `els status`           | cposhow:STATE_DB <br />cpoutil: API                      | None                |
| `oe lpmode`, `els lpmode`                                                                 | `oe lpmode`, `els lpmode`           | cposhow::Derived from STATE_DB<br />cpoutil: API          | None                |
| `oe temperature`, `els temperature`                                                       | `oe temperature`, `els temperature` | cposhow:STATE_DB <br />cpoutil: API                      | None                |
| `oe dom`, `els dom`                                                                       | `interface dom`                       | cposhow:STATE_DB <br />cpoutil: API                      | None                |
| `oe info`, `oe flag`, `oe voltage`, `firmware-info`, `list` and the ELS equivalents | `interface dom`                       | cposhow:STATE_DB <br />cpoutil: API                      | None                |

`show cpo` reuses the established pattern of `show interfaces transceiver`: **the command tree only parses and dispatches parameters, while the implementation lives in the standalone script `cposhow`**.

## 5.Requirements

### 5.1.Functional Requirements

- **FR1.** Provide the new `show cpo {oe,els}` command
- **FR2.** `show cpo` and `cposhow` produce identical output **content** (the former is a wrapper around the latter); the only permitted differences are alias resolution, default namespace handling, and `--verbose` writing to stderr (§8.6)
- **FR3.** The OE/ELS dimension must support single-instance queries and full aggregation, while preserving bank semantics
- **FR4.** `info`/`status`/`flag`/`dom` must render platform-specific keys: keys not covered are not displayed and must never interrupt the output; the label/unit of platform-specific keys **may only come from the static format map the platform provides** (the `format` section of `cpo.json`), and `sonic-utilities` hardcodes no platform strings; rendering never constructs `platform_chassis`
- **FR5.** `show interfaces transceiver *` must distinguish CPO ports: non-CPO ports keep the original sfpshow logic, and CPO ports are switched to cposhow to display OE/ELS related information
- **FR6.** Every `show cpo` / `cposhow` query command supports `--json` machine-readable output, and keys in the JSON must be the raw DB keys. `show interfaces transceiver` is **out of this requirement**: it keeps its current no-JSON behaviour (L4)

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
    │        ├─ Format Map Loader  ← community CPO map (utilities_common) + the `format` section of cpo.json
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
| `Format Map Loader` | Merge of the community map and the `format` section of `cpo.json`, key normalization, classification of uncovered keys |
| `DB Reader`         | Read by table name / key                                                                                                   |
| `Formatter`         | Output in table or JSON format                                                                                             |

### 6.2.Data Source Matrix

| Command family           | Primary data source                                                                                                                                                                                                                                                                                                                   | Notes                                                                                                                                              |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cpo map`              | `device_info.get_cpo_data()` + `platform.json`                                                                                                                                                                                                                                                                                    | Pure topology, **reads no DB and creates no table**                                                                                          |
| `format map`           | The `format` section of `cpo.json`, read through `device_info.get_cpo_data()`                                                                                                                                                                                                                                                   | Static file; neither builds the chassis nor reads registers (§7.5)                                                                                |
| `els presence`         | `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                                                                                                                                              | Determines whether this table exists                                                                                                               |
| `oe/els info`          | `TRANSCEIVER_INFO` + `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                                                                                                                       | The two sides have different field sets (§8.2.3)                                                                                                  |
| `oe/els status`        | `TRANSCEIVER_STATUS` + `TRANSCEIVER_ELS_STATUS`                                                                                                                                                                                                                                                                                   | Includes DP / config / tx status                                                                                                                   |
| `oe/els flag`          | `TRANSCEIVER_DOM_FLAG` / `TRANSCEIVER_STATUS_FLAG` / `TRANSCEIVER_ELS_DOM_FLAG` / `TRANSCEIVER_ELS_STATUS_FLAG`; `--history` additionally reads `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT` | `--history` turns on the change count / set time / clear time columns; set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME` |
| `oe/els dom`           | `TRANSCEIVER_DOM_SENSOR` + `TRANSCEIVER_DOM_THRESHOLD` + the corresponding ELS tables                                                                                                                                                                                                                                             | Values and thresholds on the same screen                                                                                                           |
| `oe/els temperature`   | `TRANSCEIVER_DOM_TEMPERATURE` / `TRANSCEIVER_ELS_DOM_TEMPERATURE`, falling back to `*_DOM_SENSOR.temperature` when absent                                                                                                                                                                                                       | A value is still available when the temperature table has no data (§8.4.7 / §8.5.8)                                                              |
| `oe/els voltage`       | `TRANSCEIVER_DOM_SENSOR.voltage` + `TRANSCEIVER_ELS_DOM_SENSOR.voltage`                                                                                                                                                                                                                                                           | —                                                                                                                                                 |
| `oe/els firmware-info` | `TRANSCEIVER_FIRMWARE_INFO` + `TRANSCEIVER_ELS_FIRMWARE_INFO`                                                                                                                                                                                                                                                                     | —                                                                                                                                                 |
| `port error-status`    | OE: `TRANSCEIVER_STATUS_SW`; ELS: `TRANSCEIVER_ELS_STATUS`                                                                                                                                                                                                                                                                        | Different semantics per side, read separately (§8.2.8)                                                                                            |

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

 cpo.json (`format` section)
   └─ get_cpo_data()["format"] ──► Format Map Loader ──► cposhow rendering
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
│  ├─ info [OE_INDEX]
│  ├─ status [OE_INDEX] [-b BANK]
│  ├─ lpmode [OE_INDEX]
│  ├─ flag [OE_INDEX] [-b BANK] [--history] [--show-suppressed]
│  ├─ dom [OE_INDEX] [-b BANK] [--show-suppressed]
│  ├─ temperature [OE_INDEX] [--show-suppressed]
│  ├─ voltage [OE_INDEX]
│  └─ firmware-info [OE_INDEX]
└─ els
   ├─ list
   ├─ presence [ELS_INDEX]
   ├─ info [ELS_INDEX]
   ├─ status [ELS_INDEX] [-b BANK]
   ├─ lpmode [ELS_INDEX]
   ├─ flag [ELS_INDEX] [-b BANK] [--history] [--show-suppressed]
   ├─ dom [ELS_INDEX] [-b BANK] [--show-suppressed]
   ├─ temperature [ELS_INDEX] [--show-suppressed]
   ├─ voltage [ELS_INDEX]
   └─ firmware-info [ELS_INDEX]

cposhow port        # CPO ports only; produced for `show interfaces transceiver` (§7.7)

├─ eeprom [PORT] [-d/--dom]
├─ error-status [PORT] [-hw]
├─ info [PORT]
├─ lpmode [PORT]
├─ presence [PORT]
└─ status [PORT]
```

### 7.2.Responsibility Split

| Concern               | `show interfaces transceiver`                                                                                                                                                                         | `show cpo`                                             | `cposhow`                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Parameter definitions | Existing options, **nothing added**                                                                                                                                                               | click group + options with the same names as `cposhow` | click, with `-h` as the authoritative version                                                 |
| Alias conversion      | Already present (`try_convert_interfacename_from_alias`)                                                                                                                                              | Same as left                                             | Aliases not supported                                                                           |
| namespace             | Existing `-n`, **except `lpmode`**: `show interfaces transceiver lpmode` has no `-n` option today, and this document does not add one                                                     | `-n` passed through                                    | Accepts `-n` directly                                                                         |
| Dispatch              | Existing → `sfpshow` (`lpmode` / `error-status` use `sudo sfputil show`, the existing implementation)                                                                                          | `clicommon.run_command(['cposhow', ...])`              | Is itself the execution body                                                                    |
| Port type dispatching | Decided in the **click layer** (`is_cpo_port()` → the `interfaces` keys of `get_cpo_data()`, §7.4): CPO ports are routed to `cposhow port`, SFP ports use the original command          | —                                                       | Provides the `port` command group (6 subcommands, `pm` excluded)                            |
| Output implementation | SFP ports: the original command's output as-is; CPO ports: the block/value returned by `cposhow` as-is; both combined by the click layer into a single table or concatenated block by block per §7.6 | No post-processing, stdout passed through                | The single implementation; `port`, `show cpo` and `cpoutil show` share the same formatter |

Rule 1: **On the `show` path the dispatch point is the click layer, not the execution body.** Once a port is identified as CPO, `cposhow port` is called **directly**; `sfpshow` does not participate at all, so CPO text has exactly one producer.

Rule 2: **`cpo.json` is parsed once per process, and classification is then one set lookup per port.** In the single-port case it is looked up once; in the full case the code enumerates `platform_sfputil.logical`, splits it into a CPO set and an SFP set, then submits one command per set (CPO → batched `cposhow port <sub> --port ...`; SFP → the original command without `-p`). The whole decision costs one JSON parse (§10) and is independent of the port count; **no chassis is constructed**, so `show` keeps running without root and a non-CPO platform keeps its current path at zero cost.

### 7.3.Topology Source and Resource Addressing

**The single topology source**: `sonic_py_common.device_info.get_cpo_data()` (`device_info.py`).

- File lookup: the platform directory, a file named `cpo.json`;
- If the file is missing or corrupt it returns `None`, and the caller takes the "non-CPO platform" branch based on that `None`.

Structure (the schema matches the existing validation; the block below is abridged, and the canonical sample that every example in §8 uses is Appendix C):

```json
{
  "devices": {
    "oe0":  {"device_type": "optical_engine", "asic_lanes": "41,42,43,44,...,56",
             "max_banks": 2, "i2c_path": "/sys/bus/i2c/devices/32-0050"},
    "els0": {"device_type": "external_laser_source",
             "laser_to_asic_lane_mapping": {"1": "41,42", "2": "43,44"}}
  },
  "interfaces": {
    "Ethernet0": {"associated_devices": [{"device_id": "oe0", "bank": 0},
                                         {"device_id": "els0", "bank": 0}]}
  }
}
```

The same file may also carry an optional `format` section declaring the display attributes of platform-specific keys (§7.5.3); that section takes no part in topology validation, and when absent the degradation behavior in §7.5.3 applies.

**Mapping reuse**: `cposhow` does `from cpoutil.mapping import CpoMapping` directly (`cpoutil` and `cposhow` ship in the same sonic-utilities package; the package list is in `setup.py`), so the parsing logic is not implemented twice. It can later be moved up to `utilities_common/cpo_mapping.py` without any behavior change (§13 OI-1).

### 7.4.CPO Port Identification

Consumers need the same criterion: `cposhow` (positive identification) and `sfpshow` (negative identification, skipping CPO ports during full enumeration). Both run without root and neither may import `sonic_platform`, so the criterion is **static**, taken from the same file that carries the topology:

Criterion: the port name is a key of `interfaces` in `cpo.json` — `port in get_cpo_data()["interfaces"]`.

- No chassis construction, no device access, no root: `cpo.json` is a plain `0644` file, read by `get_cpo_data()`.
- The file is read **once per process** and turned into a set of CPO port names; the per-port cost is one set lookup.
- `get_cpo_data()` returns `None` (no `cpo.json`, or unparsable) → **every port is treated as SFP** and the original path runs unchanged, so a non-CPO platform pays one `isfile()` and nothing else.

Shared helper: `utilities_common/cpo_helper.py`, used by both the `show/interfaces` click layer and `sfpshow`.

```python
def is_cpo_port(port, cpo_ports):     # cpo_ports: set parsed once per process
    return port in cpo_ports
```

Failure handling (the helper must never fail the command):

| Case                                                                 | Behavior                                                                                                                                                                                 |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No `cpo.json`, or `get_cpo_data()` returns `None`              | All ports treated as SFP, no warning — this is the normal non-CPO platform                                                                                                              |
| `cpo.json` unparsable, or `CpoMapping` validation fails          | All ports treated as SFP plus one `warning` on stderr; `show cpo *` itself fails with exit code 4 (§Appendix B)                                                                     |
| A vendor chassis class that does not call `ChassisBase.__init__()` | Cannot occur here: this path never consults the chassis, so `_cpo_list` is never touched and the `AttributeError` / `RuntimeError` cases of `ChassisBase.get_cpo()` do not arise |

`sfputil/port.py::is_cpo_port()` reads the device through the platform API and is **not** used on the `show` path, because `sfpshow` is DB-only and cannot import `sonic_platform`. The two predicates answer the same question from different layers; this document fixes only the static one.

### 7.5.Key Format Mapping Framework (Platform-Specific Keys)

#### 7.5.1.Static format map

**This document owns the format-map design**; no existing HLD is cited as its source. The split below is fixed here:

1. **Maps for community common fields live in utilities** and ship with `sonic-utilities` (§7.5.2);
2. **Maps for platform-private fields are declared by the platform**, so `sonic-utilities` hardcodes no platform label/unit.

The value format that `dom` and `flag --history` present follows §4 of the merged CMIS diagnostic monitoring HLD (value plus four thresholds; flag plus change count / last set / last clear; a `Last updated` line per block), so an OE or ELS row reads like a CMIS module row.

For point 2 the platform **declares data, not code**: the display attributes of platform-private keys are carried by the `format` section of the same `cpo.json` (§7.5.3) and read back through the existing `device_info.get_cpo_data()`. No new reader is introduced.

`get_cpo_data()` only normalizes the known lane fields and returns everything else untouched, so adding a `format` section does not affect xcvrd consumption. `cposhow` only reads that file at render time: it builds no chassis, imports no platform code and needs no root, and a platform without a `cpo.json` never enters the CPO path, so its behavior is unchanged.

#### 7.5.2.Community common CPO map

They land in `utilities_common/cpo_format.py` (promoted from the CPO-related maps in the existing `cpoutil/helper.py`, shared by `cposhow` / `sfpshow` / `cpoutil`):

| Map                                                           | Objects covered                   | Example keys                                                             |
| ------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------ |
| `CPO_INFO_FIELD_MAP`                                        | `TRANSCEIVER(_ELS)_INFO`        | `vendor_name`, `lane_count`, `control_mode`                        |
| `CPO_STATUS_MAP`                                            | `TRANSCEIVER(_ELS)_STATUS`      | `module_state`, `DP<N>State`, `enable_lane<N>`                     |
| `CPO_DOM_MODULE_MONITOR_MAP`                                | Module-level monitored values     | `temperature`, `voltage`, `icc`                                    |
| `CPO_DOM_CHANNEL_MONITOR_MAP`                               | Lane/laser-level monitored values | `laser_bias_current_lane*`, `optical_power_lane*`, `voltage_lane*` |
| `CPO_DOM_FLAG_MAP`                                          | Alarm bits                        | `temperature_alarm_high`, `laser_bias_warn_low`                      |
| `CPO_DOM_VALUE_UNIT_MAP` / `CPO_DOM_MODULE_THRESHOLD_MAP` | Units / thresholds                | —                                                                       |

They are merged into the rendering flow only when `device_type == CPO`, so the ordinary transceiver path is unaffected.

#### 7.5.3.Platform extension map: the `format` section of `cpo.json`

The platform adds an optional `format` section to the `cpo.json` in the same directory, declaring keys and display attributes for `info` / `status` / `dom` / `flag` separately for `oe` and `els`:

```json
{
  "...": "(the original topology content of cpo.json, see §7.3)",
  "format": {
    "version": 1,
    "oe": {
      "info": {
        "vendor_name":   {"label": "Vendor", "type": "str"},
        "serial_number": {"label": "Serial", "type": "str"}
      },
      "status": {
        "DP{lane}State": {"label": "DP{lane} State", "type": "enum",
                          "values": {"0": "Unspecified", "3": "DataPathDeactivated", "4": "DataPathActivated"}}
      },
      "dom": {
        "temperature": {"label": "Module Temperature", "unit": "C", "type": "float", "precision": 2}
      },
      "flag": {
        "lasertempHAlarm": {"label": "Laser Temp High Alarm", "type": "bool"}
      }
    },
    "els": {
      "info":   {"vendor_name": {"label": "Vendor", "type": "str"}},
      "status": {"enable_lane{lane}": {"label": "Lane {lane} Enable", "type": "bool"}},
      "dom":    {"laser_bias_current_lane{lane}": {"label": "Laser Bias {lane}", "unit": "mA", "type": "float", "precision": 3}},
      "flag":   {"lasertempHAlarm": {"label": "Laser Temp High Alarm", "type": "bool"}}
    }
  }
}
```

Field semantics:

| Field         | Required | Notes                                                                              |
| ------------- | -------- | ---------------------------------------------------------------------------------- |
| `label`     | Yes      | Non-empty string; may contain placeholders                                         |
| `unit`      | No       | Empty string / `C` / `mA` / `mW` / `V` / `dBm`                           |
| `type`      | No       | `str` / `int` / `float` / `bool` / `enum` / `hex`; defaults to `str` |
| `values`    | No       | Value table for `type=enum`; the raw value is shown when no mapping exists       |
| `precision` | No       | Decimal places for `type=float`; defaults to 2                                   |

Rendering rules:

1. **Text output renders in the order declared by the `format` section**; keys not declared there **are not displayed** (platform-specific and standard keys alike) — this is also how a key is disabled;
2. **Placeholders**: `{lane}` — in the OE section this is the **bank-relative index 1..8** (bank 1 is still `DP1..DP8`), in the ELS section it is the **absolute lane** (bank 1 is `lane9..16`); `{bank}` takes the bank number of that row;
3. **Fixed formats not described by the `format` section, generated uniformly by the renderer**:
   - `dom`: value plus four thresholds (High Alarm / High Warn / Low Warn / Low Alarm);
   - `flag --history`: flag plus change count, last set time, and last clear time;
   - one `Last updated: <last_update_time>` line at the end of each block (the `info` table has no `last_update_time` field, so that block shows `N/A`);
4. `--json` **does not apply the `format` section**; it outputs the raw DB keys (FR6).

Degradation behavior (NFR2 — the command must not be interrupted):

| Case                                                                        | Behavior                                                                                                                                  |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `format` section absent                                                   | Render with the built-in standard key table (common CMIS names, §7.5.2); platform-specific keys are not displayed; no error, exit code 0 |
| One entry invalid (empty label / unknown type / unit outside the allowlist) | That key is skipped with a `warning` on stderr; everything else renders normally                                                        |
| Unknown `version`                                                         | Render with the built-in table and emit one warning                                                                                       |

#### 7.5.4.Merging, normalization, and uncovered keys

Merging rules:

1. The `format` section may only **add** keys: it cannot rename, retype, or hide a community common key, because that would let each vendor redefine fields that are supposed to be identical across vendors. A `format` entry for a key the community map already declares is **ignored** and reported as one `warning` on stderr (the community label wins, the command still succeeds);
2. Keys declared by the `format` section go into the `PlatformSpecific*` section (label taken from the `format` section); keys declared by neither do not enter the output (last table of this section);
3. Ordering: keys declared in the `format` section follow their declaration order (JSON preserves order, so the output is stable); keys generated from the community map follow its declaration order; keys that carry a numeric suffix (`lane2`, `lane10`) are sorted with **natural sort** (`natsorted`, as `sfpshow` does), never lexicographically;
4. The `format` section is parsed only once per `cposhow` process.

Coverage is the four classes `info` / `status` / `flag` / `dom`; `threshold` reuses the value/unit declarations of `dom`.

Handling of uncovered keys (this is how "platform-specific keys must be presented" is realized):

| Case                   | table mode                        | JSON mode |
| ---------------------- | --------------------------------- | --------- |
| Community map hit      | Rendered by the common rules      | Raw key   |
| `format` section hit | Rendered as the platform declared | Raw key   |
| Neither hits           | Not displayed                     | Raw key   |

Constraint: **uncovered keys are not displayed**.

### 7.6.Output Contract and Exit Codes

**table mode — mixed ports (`show interfaces transceiver` full run)**

The click layer first collects all ports and sorts them with `natsorted`, then presents them one of two ways depending on the subcommand. `cposhow` / `sfpshow` emit only "port + value" data rows; **the click layer adds the header uniformly**:

| Type       | Subcommands                                | Presentation                                                                                            |
| ---------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| table type | `presence`, `lpmode`, `error-status` | **One table, one header**; CPO rows carry the composite value `OE: …; ELS: …`                 |
| block type | `eeprom`, `info`, `status`           | One block per port, with `OE:` / `ELS:` subsections inside a CPO block; **no overall header** |

`pm` is not dispatched (§8.2.5) and keeps the original `sfpshow` output shape, so it is out of scope for this table.

**table mode — structure inside a block**

- Port dimension: grouped inside the block by the CMIS section names: `ModuleMonitorValues` / `ChannelMonitorValues` / `PlatformSpecificDomValues` (status/flag/info similarly use `ModuleStatusValues` / `ChannelStatusValues`);
- Resource dimension: one block per resource, with bank/lane as subheadings (`Bank 1 (Lane 9-16)`). **The lane range in the heading is a physical lane range; keys inside the OE section always use the bank-relative index 1..8, while keys inside the ELS section always use the absolute index**;
- Missing values: `N/A` (key absent / empty value / unparsable all become `N/A`); booleans: `True`/`False`, **taken directly from the DB with no prefix marker**;

**JSON mode — resource dimension** (`show cpo oe|els … --json`)

- OE: four levels `resource → bank → group → key`, where the bank number comes from `oe_bank_id` in `cpo.json` (0..max_banks-1);
- ELS: three levels `resource → group → key` (an ELSFP has no bank concept; `els_bank` is a legacy compatibility field and does not appear as a JSON level);
- Leaf key = the **raw DB key**, with values kept as DB strings (never converted to float on a whim).

```json
{
  "oe0": {
    "bank0": {"info": {"vendor_name": "BROADCOM"}, "status": {"DP1State": "DataPathActivated"},
              "dom": {"temperature": "41.125"}, "flag": {"tempHAlarm": "False"}},
    "bank1": {"info": {"vendor_name": "BROADCOM"}, "status": {"DP1State": "DataPathActivated"},
              "dom": {"temperature": "42.375"}, "flag": {"tempHAlarm": "False"}}
  }
}
```

`oe list` / `els list` keep the list shape:

```json
[{"id": "oe0", "banks": [0,1,2,3,4,5,6,7]}, {"id": "oe1", "banks": [0,1,2,3,4,5,6,7]}]
```

**JSON mode — port dimension** (`cposhow port … --json`)

The port layer solves "different ports own different lane subsets": a subport emits only the keys for the lanes it owns (xcvrd publishes per-lane data only to the subport that owns that lane).

```json
{
  "Ethernet0": {
    "oe":  {"id": "oe0", "bank": 0, "status": {"DP1State": "DataPathActivated"}},
    "els": {"id": "els0", "status": {"enable_lane4": "True"}}
  }
}
```

Exit codes are listed in Appendix B.

### 7.7.show interfaces transceiver Dispatching

The dispatch decision is made in `show/interfaces/__init__.py`: **once a port is identified as CPO, `cposhow port` is called directly** and `sfpshow` is not entered. `cpo.json` is parsed once per process (§7.4) and the resulting port set is reused, so no chassis is built and no hardware is read.

The subcommands of `cposhow port` correspond one-to-one to `show interfaces transceiver`, and their **primary purpose is to carry the `show interfaces transceiver` calls on CPO ports**:

| `show interfaces transceiver <sub>` | CPO port routed to            | Notes                                                                                             |
| ------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------- |
| `eeprom [PORT] [-d/--dom]`          | `cposhow port eeprom`       | `-d` appends both the OE and ELS DOM sections                                                   |
| `info [PORT]`                       | `cposhow port info`         | OE section + ELS section; different field sets are not merged                                     |
| `status [PORT]`                     | `cposhow port status`       | Includes DP / config / tx status                                                                  |
| `presence [PORT]`                   | `cposhow port presence`     | Determined by the existence of `TRANSCEIVER_ELS_INFO`                                           |
| `lpmode [PORT]`                     | `cposhow port lpmode`       | Derived from `module_state`                                                                     |
| `error-status [PORT] [-hw]`         | `cposhow port error-status` | OE reads `TRANSCEIVER_STATUS_SW`, ELS reads `TRANSCEIVER_ELS_STATUS`; for `-hw` see §8.2.8 |
| `pm [PORT]`                         | —                            | Not dispatched; CPO ports still use the original `sfpshow` path                                 |

Ordinary pluggable ports are unaffected: they keep the original `sfpshow` path with zero changes. Port-dimension data queries always reuse `show interfaces transceiver`; no new entry point is added just because a port is CPO.

For a full run mixing CPO and SFP ports, the click layer does the sorting and table assembly: table-type subcommands are combined into **one table** (CPO rows carry the `OE: …; ELS: …` composite value), while block-type subcommands keep one block per port — see §7.6 for the rules.

**Relationship with `config interface`**: configuration commands such as `config interface transceiver *` are not affected by this change and their behavior is not revised. This document covers the query side only; the configuration semantics of CPO ports remain as they are.

Details are in §8.2.

## 8.Command Functional Specification (show)

### 8.1.Common Parameters

| Parameter                        | Applies to                                                   | Notes                                                                                                                                                                                                     |
| -------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[OE_INDEX]` / `[ELS_INDEX]` | All oe/els subcommands                                       | `oe0` / `0` are equivalent; omitted = all instances                                                                                                                                                   |
| `-b, --bank N`                 | oe/els `status` / `flag` / `dom`                       | Selects one bank of the OE/ELS; omitted = every bank shown as its own section. Only bank-scoped groups take it: `lpmode`, `temperature` and `voltage` are module-level and have **no** `-b` |
| `-j, --json`                   | All                                                          | Machine-readable output                                                                                                                                                                                   |
| `-n, --namespace NAME`         | All                                                          | Specifies the namespace and passes it through to the execution body                                                                                                                                       |
| `--history`                    | `flag`                                                     | Appends the change count / set time / clear time columns                                                                                                                                                  |
| `--show-suppressed`            | `info` / `status` / `dom` / `temperature` / `flag` | Displays keys suppressed by §7.5 (for debugging)                                                                                                                                                         |
| `--verbose`                    | All (`show cpo` side)                                      | Prints the actual `cposhow` command line executed                                                                                                                                                       |

Notes:

- An out-of-range `-b` value (negative, or ≥ the bank count of that resource) is a usage error: exit code 2 (§Appendix B).
- `-d` and `--dom` are the same option of `show interfaces transceiver eeprom`; both forms are listed once in §7.1 and §8.2.2, and the rest of this document writes `-d`.

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
        ChannelMonitorValues
        Lane 1: TXBias 12.400 mA / TXPower 2.104 dBm / RXPower 1.757 dBm
        Lane 2: TXBias 12.550 mA / TXPower 2.118 dBm / RXPower 1.898 dBm
        ELS (els0, bank 0)
        ...(same as above, no laser temperature)
        ModuleMonitorValues
        Temperature: 36.750 C
        Voltage: 3.300 V
        Icc: 4.512 A
        ChannelMonitorValues
        Laser 1: Bias 152.000 mA / Optical Power 4.771 dBm / Voltage 3.302 V
        Laser 2: Bias 151.200 mA / Optical Power 4.690 dBm / Voltage 3.301 V
```

Rendering follows §7.5: the CPO-specific `ChannelMonitorValues` / `ModuleMonitorValues` labels come from the community map, platform-specific keys come from the `format` section of `cpo.json`, and keys declared by neither are not displayed.

#### 8.2.3.`show interfaces transceiver info [PORT]`

Function: Static identification information. CPO ports go through `cposhow port info`, which outputs an OE section + an ELS section (different field sets, not merged).

Data source: `TRANSCEIVER_INFO` / `TRANSCEIVER_ELS_INFO`; labels are determined by `CPO_INFO_FIELD_MAP` plus `format.oe/els.info`.

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

Function: Operational status. CPO ports go through `cposhow port status`, which outputs an OE section (module/DP/config/tx) + an ELS section (module/laser enable/state/fault).

Data source: `TRANSCEIVER_STATUS` / `TRANSCEIVER_ELS_STATUS`; labels are determined by `CPO_STATUS_MAP` plus `format.oe/els.status`.

```text
admin@sonic:~$ show interfaces transceiver status Ethernet0
Ethernet0: CPO EEPROM detected
        OE (oe0, bank 0)
        Module State: ModuleReady
        Module Fault Cause: N/A
        DP State: DP1..DP8 DataPathActivated
        Config Status: ConfigSuccess (lane 1-8)
        Tx Disabled Channel: 0x00
        Tx Output Status: On (lane 1-8)
        ELS (els0, bank 0)
        Module State: ModuleReady
        Module Fault Cause: N/A
        Laser Enable: True True True True True True True True
        Laser State: Output on (laser 1-8)
        Output Fiber Checked: True True True True False False True True
        Fault Code: 0x00
```

#### 8.2.5.`show interfaces transceiver pm [PORT]`

**CPO does not support `pm`, and nothing is changed in this phase**.

`pm` does not take part in CPO dispatching: `get_pm` in `sfpshow` reads `TRANSCEIVER_PM|<subport>` (`sfpshow:609-610`); a CPO port has no such table, so it takes the existing `ZR_PM_NOT_APPLICABLE_STR` branch (`sfpshow:652-653`) and outputs `N/A`. Therefore **no port-type decision is needed and CPO rows need not be skipped**; `pm` behaves identically on CPO and non-CPO ports, satisfying "queryable on all ports". The click layer **does not dispatch `pm`** (the 6 subcommands in §8.2.1 do not include `pm`), so CPO ports still use the original `sfpshow` path.

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
Ethernet16   Not present
Ethernet512  Present
Ethernet520  Not present
```

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
Ethernet8    OE: Off; ELS: On
Ethernet512  Off
Ethernet520  On
```

Design choice: **keep one column and add none**; in mixed-port scenarios the click layer assembles a single table (§7.6), with CPO rows carrying the `OE: …; ELS: …` composite value.

#### 8.2.8.`show interfaces transceiver error-status [PORT] [-hw]`

Function: Error status. CPO ports are no longer skipped; instead a composite value is emitted, where OE and ELS each reach a verdict from its own status table.

Change: once the click layer determines a port is CPO it calls `cposhow port error-status`; **without `-hw`** `cposhow` reads STATE_DB internally, without calling `sfp.get_error_description()` and without going through `sfputil`:

| Location                                      | Current state                                     | Change                                                                                                                                                              |
| --------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show/interfaces/__init__.py: error_status` | Calls `sudo sfputil show error-status` directly | CPO ports are routed to `cposhow port error-status`                                                                                                               |
| `-hw` path                                  | Calls `sfp.get_error_description()`             | For CPO ports the hardware read moves to `cpoutil`: `show` still accepts `-hw`, but the value is produced by a new `cpoutil` command (revision below, OI-2) |

The semantics of `-hw` (`--fetch-from-hardware`) are unchanged: skip the DB cache and force a read from hardware. Hardware direct reads on CPO ports are handled uniformly by `cpoutil` — `cposhow` reads STATE_DB only and never accesses registers.

**`cpoutil` revision carried by this change** (implemented on the `cpoutil` side in sync with PR 5032, tracked as OI-2):

| Aspect           | Revision                                                                                                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Command          | A new subcommand of `cpoutil show` that returns the error status of one CPO port read from hardware                                                                         |
| Target selection | The port name; `--oe` / `--els` narrows it to one side of the port (default: both, in the same `OE: …; ELS: …` shape as `show interfaces transceiver error-status`) |
| Read path        | Calls the device API directly (`get_error_description()` on the OE side, the ELSFP status call on the ELS side), bypassing STATE_DB                                         |
| Output contract  | The same text vocabulary as the DB path of this section, so the two are diffable: `OK` / `Unplugged` / the module error text, with `N/A` for a missing side             |
| Privilege        | Root, like the rest of `cpoutil` — this is why `show` cannot do it in-process                                                                                            |
| Failure          | Non-zero exit with the reason on stderr; `show interfaces transceiver ... -hw` maps that to `N/A` plus a warning and still exits 0 (NFR4)                                 |

Until that command lands, `show interfaces transceiver error-status -hw` on a CPO port prints `N/A` and a `warning` — it does not fall back to the DB value, because reporting a cached value under `-hw` would be wrong.

Value derivation rules (implemented inside `cposhow`, DB-only; **applicable only to the default path without `-hw`**):

| Section        | Data source                                                                                                                | Rule                                                                                                                                                                                          |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OE             | The `status` / `error` of the `<port>` row in `TRANSCEIVER_STATUS_SW`                                              | Exactly the same as SFP (`sfputil/main.py:1087-1124`, same semantics): `status=1` → `OK`; `status=0` → `Unplugged`; otherwise take `error`                                      |
| ELS            | The `module_state` / `module_fault_cause` / `lane_summary_fault` of the `<port>` row in `TRANSCEIVER_ELS_STATUS` | All three normal → `OK`; otherwise take `module_state`, append `(<cause>)` when `module_fault_cause` is not `No Fault`, and append `lane fault` when `lane_summary_fault=True` |
| ELS row absent | —                                                                                                                         | `N/A`                                                                                                                                                                                       |

The OE section has **exactly the same semantics as an SFP row**, which is why a mixed-port scenario can be assembled into a single table (§7.6). Note that in `TRANSCEIVER_STATUS_SW` a CPO port carries only the OE error text (`CpoStateUpdateTask._get_port_error_description()` reads the OE only), so the ELSFP state has to be read from `TRANSCEIVER_ELS_STATUS`.

```text
admin@sonic:~$ show interfaces transceiver error-status
Port         Error Status
-----------  -------------------------------------
Ethernet0    OE: OK; ELS: OK
Ethernet8    OE: OK; ELS: ModuleFault (Lane fault)
Ethernet512  OK
Ethernet520  SFP EEPROM not detected
```

### 8.3.`show cpo map [PORT]`

Function: Output the mapping port → OE(id, bank) → ELS(id, bank) → laser. Pure topology; reads neither registers nor the DB. Lasers belong to the ELS, so the `Lasers` column follows the ELS section.

Data source: `device_info.get_cpo_data()` + `platform.json` (with `port_config` as fallback).

```text
admin@sonic:~$ show cpo map
Interface    ASIC Lanes                  OE     OE Bank    ELS     ELS Bank    Lasers
-----------  --------------------------  -----  ---------  ------  ----------  --------
Ethernet0    1,2,3,4,5,6,7,8             oe0    0          els0    0           5,6
Ethernet8    9,10,11,12,13,14,15,16      oe0    1          els0    0           7,8
Ethernet16   17,18,19,20,21,22,23,24     oe0    2          els0    0           1,2
```

```json
admin@sonic:~$ show cpo map Ethernet0 -j
{"Ethernet0": {"asic_lanes": [1,2,3,4,5,6,7,8], "oe": {"id": "oe0", "bank": 0},
               "els": {"id": "els0", "bank": 0}, "laser_ids": [5, 6]}}
```

### 8.4.show cpo oe

Resource dimension: a single OE instance view aggregates all the ports it drives. The difference from the port dimension is that **OE is a shared resource**, so module-level fields are read once from a shared port and annotated with the source port.

#### 8.4.1.`show cpo oe list`

Function: List all OE instances, the ports they drive, the bank count, and the module state.

Data source: `cpo_data["devices"]` (`device_type == optical_engine`) + a reverse index over `cpo_data["interfaces"]`; the module state is taken from `TRANSCEIVER_STATUS.module_state`, read once from the ports of that OE and reported with the source port when they disagree.

```text
admin@sonic:~$ show cpo oe list
OE     Ports                                   Banks   Module State
-----  --------------------------------------  ------  ------------
oe0    Ethernet0,Ethernet8,...,Ethernet56          8     ModuleReady
oe1    Ethernet64,Ethernet72,...,Ethernet120       8     ModuleReady
```

#### 8.4.2.`show cpo oe info [OE_INDEX]`

Function: OE static information. Data source `TRANSCEIVER_INFO` (keys taken from any shared port, output after per-field consistency checking).

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

#### 8.4.3.`show cpo oe status [OE_INDEX] [-b BANK]`

Function: OE status, including DP/config/tx. Data source `TRANSCEIVER_STATUS`.

```text
admin@sonic:~$ show cpo oe status oe0
oe0   Bank 0 (Lane 1-8)   ports: Ethernet0
        Module State            ModuleReady
        Module Fault Cause      N/A
        DP State                DP1..DP8 DataPathActivated
        Config Status           ConfigSuccess (lane 1-8)
        Tx Disabled Channel     0x00
        Tx Output Status        On (lane 1-8)
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

#### 8.4.5.`show cpo oe flag [OE_INDEX] [-b BANK] [--history]`

Function: OE alarm flags. Data source `TRANSCEIVER_DOM_FLAG` + `TRANSCEIVER_STATUS_FLAG`; `--history` additionally reads the change counts `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` + `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT`, and set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME`.

```text
admin@sonic:~$ show cpo oe flag oe0
oe0   Bank 0 (Lane 1-8)
        TempHighAlarm         False
        TempLowAlarm          False
        TempHighWarn          False
        VccHighAlarm          False
        VccLowAlarm           False
        Rx1Los                True
        Rx3Los                True
        PlatformSpecificFlags
        pmd_fault_lane1       False
        Last updated: 2026-11-12 10:41:07
```

With `--history`, each flag gains its change count and the last set / last clear time (same layout as the CMIS diagnostic HLD §4):

```text
admin@sonic:~$ show cpo oe flag oe0 --history
oe0   Bank 0 (Lane 1-8)
        Flag                  Value   Change Count   Last Set             Last Clear
        TempHighAlarm         False   0              -                    -
        Rx1Los                True    3              2026-11-12 09:12:44  2026-11-12 08:55:02
        Last updated: 2026-11-12 10:41:07
```

#### 8.4.6.`show cpo oe dom [OE_INDEX] [-b BANK]`

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

#### 8.4.7.`show cpo oe temperature [OE_INDEX]`

Function: OE module temperature. Data source `TRANSCEIVER_DOM_TEMPERATURE` (falling back to `TRANSCEIVER_DOM_SENSOR.temperature` when absent).

```text
admin@sonic:~$ show cpo oe temperature
OE     Temperature(C)   HAlarm(C)   HWarn(C)
-----  ---------------  ----------  ---------
oe0    41.125           75.000      70.000
oe1    42.375           75.000      70.000
```

#### 8.4.8.`show cpo oe voltage [OE_INDEX]`

Function: OE Vcc and thresholds. Data source `TRANSCEIVER_DOM_SENSOR.voltage` + `TRANSCEIVER_DOM_THRESHOLD`; the `Status` column is taken from the Vcc alarm bits of `TRANSCEIVER_DOM_FLAG`, **not computed from the thresholds**, so it always agrees with `show cpo oe flag`.

```text
admin@sonic:~$ show cpo oe voltage
OE     Voltage(V)   HAlarm(V)   LAlarm(V)   Status
-----  -----------  ----------  ----------  ----------
oe0    3.312        3.600       3.000       OK
oe1    2.912        3.600       3.000       VccLowAlarm
```

#### 8.4.9.`show cpo oe firmware-info [OE_INDEX]`

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

Function: List all ELS instances, the ports they drive, the laser count, and the bank count.

Data source: `cpo_data["devices"]` (`device_type == external_laser_source`) + a reverse index over `interfaces` + `TRANSCEIVER_ELS_INFO` (`lane_count`/`control_mode`).

```text
admin@sonic:~$ show cpo els list
ELS     Ports                                        Lasers  Module State
------  -------------------------------------------  ------  ------------
els0    Ethernet0,Ethernet8,Ethernet16,Ethernet24    8       ModuleReady
els1    Ethernet32,Ethernet40,Ethernet48,Ethernet56  8       ModuleReady
```

#### 8.5.2.`show cpo els presence [ELS_INDEX]`

Function: ELS presence.

Data source: whether `TRANSCEIVER_ELS_INFO` exists

```text
admin@sonic:~$ show cpo els presence
ELS     Presence      Ports
------  ------------  ----------------------
els0    Present       Ethernet0, Ethernet8, Ethernet16, Ethernet24
els1    Not present   Ethernet32, Ethernet40, Ethernet48, Ethernet56
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

#### 8.5.4.`show cpo els status [ELS_INDEX] [-b BANK]`

Function: ELS status (module + laser enable/state/fault/warning). Data source `TRANSCEIVER_ELS_STATUS`.

```text
admin@sonic:~$ show cpo els status els0
els0   Bank 0 (Laser 1-8)   ports: Ethernet0,Ethernet8,Ethernet16,Ethernet24
        Module State            ModuleReady
        Module Fault Cause      N/A
        Laser Enable            True True True True True True True True
        Laser State             Output on (laser 1-8)
        Output Fiber Checked    True True True True False False True True
        Fault Code              0x00
        Warning Code            0x00
```

#### 8.5.5.`show cpo els lpmode [ELS_INDEX]`

Function: ELS low-power status, derived from `module_state` with the four-state rule of §8.2.7. DB-only; `ElsfpApi.get_lpmode()` is not called.

```text
admin@sonic:~$ show cpo els lpmode
ELS     Low-power Mode
------  --------------
els0    Off
els1    On
```

#### 8.5.6.`show cpo els flag [ELS_INDEX] [-b BANK] [--history]`

Function: ELS alarm flags, including per-lane fault/warn latch and the lane summary. Data source `TRANSCEIVER_ELS_DOM_FLAG` + `TRANSCEIVER_ELS_STATUS_FLAG`; `--history` additionally reads the change counts `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` + `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT`, and set/clear time come from the same-named `*_SET_TIME` / `*_CLEAR_TIME`.

```text
admin@sonic:~$ show cpo els flag els0
els0   Bank 0 (Laser 1-8)
        TemperatureHighAlarm   False
        VoltageLowWarn         False
        LaneSummaryFault       False
        LaneSummaryWarning     False
        FaultFlagLane2         True
        WarningFlagLane5       True
        PlatformSpecificFlags
        wavelength_drift_alert_lane2   True
```

#### 8.5.7.`show cpo els dom [ELS_INDEX] [-b BANK]`

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

#### 8.5.8.`show cpo els temperature [ELS_INDEX]`

Function: ELS module temperature. Data source `TRANSCEIVER_ELS_DOM_TEMPERATURE` (falling back to `TRANSCEIVER_ELS_DOM_SENSOR.temperature` when absent).

```text
admin@sonic:~$ show cpo els temperature
ELS     Temperature(C)   HAlarm(C)   HWarn(C)
------  ---------------  ----------  ---------
els0    36.750           70.000      65.000
els1    37.125           70.000      65.000
```

#### 8.5.9.`show cpo els voltage [ELS_INDEX]`

Function: ELS Vcc and thresholds. Data source `TRANSCEIVER_ELS_DOM_SENSOR.voltage` + `TRANSCEIVER_ELS_DOM_THRESHOLD`; the `Status` column is taken from the Vcc alarm bits of `TRANSCEIVER_ELS_DOM_FLAG`, **not computed from the thresholds**, so it always agrees with `show cpo els flag`.

```text
admin@sonic:~$ show cpo els voltage
ELS     Voltage(V)   HAlarm(V)   LAlarm(V)   Status
------  -----------  ----------  ----------  ------
els0    3.300        3.600       3.000       OK
els1    3.288        3.600       3.000       OK
```

#### 8.5.10.`show cpo els firmware-info [ELS_INDEX]`

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
| `get_cpo_data()` + `platform.json`                | < 5 ms   | File < 50 KB, pure JSON; this is also the port classification (§7.4)                     |
| STATE_DB reads (HGETALL, 64 ports)                    | < 300 ms | pipeline                                                                                  |
| Port classification (`show interfaces transceiver`) | < 5 ms   | One set lookup per port over the result of the parse above; **no chassis, no root** |

- No background polling; `sfpshow` / `cposhow` are both pure DB paths;
- In the `show interfaces transceiver` scenario the two subprocesses run **in sequence**, not in parallel: the output is ordered and assembled by the click layer (§7.6), and the memory increase is only the two output texts (about 1–2 MB for 64 CPO + 64 SFP ports in full).

## 11.Restrictions/Limitations

- **L1.** Queried data is an xcvrd polling snapshot, not real-time; for real-time register values use `cpoutil`
- **L2.** Some bits in the `flag` tables are **clear-on-read** (CMIS hardware behavior), so a `show` read may increase the change count seen on the next read; therefore `show cpo` reads the DB only by default and never triggers a hardware read.
- **L3.** When the platform declares no `format` section in `cpo.json`, platform-only keys **do not appear in table output** (`--show-suppressed` can list them and `--json` keeps the raw keys); keys covered by neither the community map nor the `format` section are likewise not displayed.
- **L4.** `show interfaces transceiver` provides no JSON (status quo); when machine readability is needed, use `show cpo ... -j` or `cposhow port ... -j`, or read STATE_DB directly.
- **L5.** On multi-ASIC platforms the click layer identifies CPO ports per namespace, and `-n` applies only to the namespace of the current invocation; `show cpo oe list` / `els list` list only the instances in the current namespace; aggregated output across namespaces is out of scope for this change.

## 12.Testing Requirements/Design

### 12.1.Unit Test

1. `topology`: `cpo_data` parsing, even splitting by `max_banks`, bank → lane conversion validation;
2. `format map`: parsing of the `format` section, `{lane}` / `{bank}` placeholder expansion (bank-relative index for OE, absolute lane for ELS), override precedence against the community map, undeclared keys not displayed (`--show-suppressed` can list them), and the three degradation behaviors for a missing section / an invalid entry / an unknown `version`;
3. `formatter`: table/JSON consistency, booleans, uniform `N/A` for missing values;
4. Parameter parsing: invalid port, invalid index, `--bank` out of range;
5. Exit codes: distinguishing a missing `cpo.json` (3) from a file that exists but fails parsing/validation (4), with `os.path.isfile()` checked first.

### 12.2.Platform Functional Test

1. All query commands return valid output at the three granularities: single port / single instance / full;
2. Byte-for-byte comparison of `show cpo X` and `cposhow X` output;
3. Platform-specific key injection: declare custom keys in the `format` section of `cpo.json` and verify label/unit/precision take effect; then put a key in the DB that the `format` section does not declare and verify it **does not appear** in table mode, can be listed by `--show-suppressed`, and keeps its raw key in JSON mode;
4. ELS plug/unplug: `presence` goes from Present to Not present, and `lpmode` / `error-status` follow;
5. `show interfaces transceiver` outputs both the OE and ELS sections on CPO ports with no skip hint; in a full mixed run the table-type subcommands (`presence` / `lpmode` / `error-status`) produce **one table** with composite values on CPO rows, while block-type subcommands produce one block per port with no duplicate rows;
6. **Hard availability constraint**: on the same CPO port, all 7 subcommands of `show interfaces transceiver` are executable.

**Impact outside the CLI itself** (all three are part of the deliverable, not follow-ups):

7. **sonic-mgmt**: `parse_eeprom()`, `parse_output()`, and the checks for `SFP EEPROM detected` need CPO support. The one-header-per-port layout of §7.6 keeps the port name as the dict key, so `parse_eeprom()` continues to produce one entry per port; the OE/ELS sub-blocks are parsed as sub-sections. A sonic-mgmt PR accompanies PR 5032;
8. **`sonic-utilities` unit tests**: the `show/interfaces` dispatch is tested with a mock `cpo.json` and a mock STATE_DB, and one case runs with **no `cpo.json`** to prove that a non-CPO platform's output is byte-identical to master;
9. **`doc/Command-Reference.md`**: the `show cpo` family and `cposhow` are added, and the CPO behaviour of the 6 `show interfaces transceiver` subcommands is noted under their existing entries.

### 12.3.Integration Test

1. Script compatibility with mixed traversal of 64 CPO + N ordinary ports alongside `show interfaces transceiver`;
2. Table-missing scenarios during an xcvrd restart (the command does not crash and outputs `N/A`).

### 12.4.Edge Case Test

1. `cpo.json` missing → all commands report "no CPO topology" with exit code 3;
2. `cpo.json` present but JSON parsing fails, or `CpoMapping` validation fails → explicit error plus the file path, exit code 4 (not silent);
3. One entry in the `format` section invalid (empty label / unknown type / unit outside the allowlist) → that key is skipped with a stderr warning, the command still succeeds with exit code 0 (NFR2);
4. `format` section absent → render with the built-in standard key table, platform-specific keys not displayed, exit code 0;
5. A new uncovered key added by the API → output complete, no error, and the key is not displayed per §7.5.4;
6. Fields inconsistent across multiple ports of the same OE (some ports read `N/A`) → take the valid value and annotate the source port;
7. ELSFP not present → every subcommand exits 0 with the value `N/A` (`presence` shows `Not present`).

## 13.Open/Action Items

| ID   | Item                                                                                                   | Owner              | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---- | ------------------------------------------------------------------------------------------------------ | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OI-1 | Move `cpoutil/mapping.py` up to `utilities_common/cpo_mapping.py`                                  | utilities          | Avoids `cposhow` depending on a private module of the `cpoutil` package; pure refactor, no behavior change                                                                                                                                                                                                                                                                                                                                                                                                                      |
| OI-2 | A new `cpoutil` command providing hardware direct-read results for `error-status -hw` on CPO ports | cpoutil / platform | This document only fixes the data source and the dispatch location (§8.2.8): `-hw` semantics are preserved and hardware direct reads on CPO ports are no longer carried by `cposhow`. The command shape, parameters, output contract, privilege and failure mode are specified in §8.2.8 so the two sides can be implemented against one text; the `cpoutil` side lands it in the same release. Until it is available, `show interfaces transceiver error-status -hw` prints `N/A` plus a `warning` and still exits 0 |

## 14.Dependencies

| Dependency                                                                                   | Kind             | What this document relies on                                                                                                                                                   | State today                                                                                                                                                                                                                      |
| -------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [sonic-platform-daemons PR 933](https://github.com/sonic-net/sonic-platform-daemons/pull/933) | Code (xcvrd)     | Publishes the ELS DOM / flag / status / firmware / temperature tables and their `*_FLAG_CHANGE_COUNT`, `*_SET_TIME`, `*_CLEAR_TIME` counterparts                         | **Not on master.** Master publishes only `TRANSCEIVER_ELS_INFO` and `TRANSCEIVER_ELS_DOM_THRESHOLD`, and `cpo/dom_mgr.py` is a stub, so every §6.2 row except `els presence` becomes readable only after it lands |
| Platform `cpo.json`                                                                        | Data (vendor)    | Topology (`devices` / `interfaces`) and the optional `format` section (§7.3, §7.5.3)                                                                                   | Delivered per platform; no code dependency                                                                                                                                                                                       |
| [sonic-utilities PR 5032](https://github.com/sonic-net/sonic-utilities/pull/5032)             | Code (utilities) | `cposhow` itself, and the `show/interfaces` dispatch of the 6 subcommands to `cposhow port` (§8.2.1)                                                                    | Open                                                                                                                                                                                                                             |
| [cpoutil HLD, SONiC PR 2498](https://github.com/sonic-net/SONiC/pull/2498)                    | Design           | `cpoutil` command family, and the hardware direct read on CPO ports for `error-status -hw` (§8.2.8, OI-2). `cposhow` imports `CpoMapping` from `cpoutil/mapping.py` | Merged                                                                                                                                                                                                                           |

## 15.SAI API

**Not applicable.** This feature adds no SAI attribute, no SAI API call, and no ASIC-side behaviour: every command in this document is a read-only consumer of STATE_DB plus the static `cpo.json` (§6.2). The tables themselves are written by xcvrd through the existing CMIS/ELSFP API paths (`CmisApi` / `ElsfpApi`), which are unchanged by this document, and no new SAI object is introduced for OE or ELS.

## 16.Configuration and management

**Not applicable.** This document defines query commands only (`show cpo`, `cposhow`, and the CPO behaviour of `show interfaces transceiver`). There is no new configuration command, no ConfigDB schema change, no YANG model, and no `config_db.json` field.

`config interface *` (speed, FEC, MTU, low-power, and similar) is **not affected by this change and is not revised**: CPO ports keep their existing configuration semantics and existing commands (see §7.7, "Relationship with `config interface`").

---

## Appendix A: Command ↔ Source Mapping

Everything below is referenced **by symbol, not by line number**: line numbers drift between branches, and the upstream task names change when the tables are contributed (sonic-platform-daemons PR 933 publishes the CPO DOM set and renames `xcvrd/cpo/dom_mgr.py` to `xcvrd/cpo/cpo_dom_mgr.py`).

| Command                                                                      | Data source                                                                                                                                                                                                      | Producer / entry point                                                                                                            | Underlying API (origin)                                                                                                                                  |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `show cpo map` / `cposhow map`                                           | `cpo.json` + `platform.json`                                                                                                                                                                                 | `device_info.get_cpo_data()` + `CpoMapping` (`cpoutil/mapping.py`)                                                          | —                                                                                                                                                       |
| `show cpo oe list` / `els list`                                          | `cpo_data["devices"]` + `cpo_data["interfaces"]`                                                                                                                                                             | `CpoMapping` reverse index                                                                                                      | —                                                                                                                                                       |
| `show interfaces transceiver presence`                                     | `TRANSCEIVER_ELS_INFO`                                                                                                                                                                                         | `CpoStateUpdateTask` — writes the row only when `_wrapper_get_presence()` is true                                            | Whether `TRANSCEIVER_ELS_INFO` exists                                                                                                                  |
| `show interfaces transceiver info`                                         | `TRANSCEIVER_INFO` / `TRANSCEIVER_ELS_INFO`                                                                                                                                                                  | `CpoStateUpdateTask`                                                                                                            | `CmisApi.get_transceiver_info()` / `ElsfpApi.get_elsfp_info()`                                                                                       |
| `show interfaces transceiver status`                                       | `TRANSCEIVER_STATUS` / `TRANSCEIVER_ELS_STATUS`                                                                                                                                                              | `CpoDomInfoUpdateTask`                                                                                                          | `CpoCmisApi.get_transceiver_status()` / `ElsfpApi.get_elsfp_status()`                                                                                |
| `show cpo oe / els flag`                                                   | `*_DOM_FLAG` / `*_STATUS_FLAG` + `TRANSCEIVER_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_STATUS_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_DOM_FLAG_CHANGE_COUNT` / `TRANSCEIVER_ELS_STATUS_FLAG_CHANGE_COUNT` | `CpoDomInfoUpdateTask`                                                                                                          | `get_transceiver_dom_flags()` / `get_elsfp_dom_flags()`                                                                                              |
| `show cpo oe / els dom` / `cposhow port eeprom -d`                       | `*_DOM_SENSOR` / `*_DOM_THRESHOLD`                                                                                                                                                                           | `CpoDomInfoUpdateTask` + `CPODOMDBUtils`                                                                                      | `get_transceiver_dom_real_value()` / `get_elsfp_dom_real_value()`                                                                                    |
| `show cpo oe / els temperature`                                            | OE: `TRANSCEIVER_DOM_TEMPERATURE`; ELS: `TRANSCEIVER_ELS_DOM_TEMPERATURE`; both fall back to `*_DOM_SENSOR.temperature`                                                                                    | `CpoDomInfoUpdateTask` — **both sides own a temperature table**; the ELS one is added by PR 933                          | `get_module_temperature()`                                                                                                                             |
| `show cpo oe / els voltage`                                                | `*_DOM_SENSOR.voltage` + the threshold tables; the `Status` column reads `*_DOM_FLAG`                                                                                                                      | `CpoDomInfoUpdateTask`                                                                                                          | `CmisApi.get_voltage()` / `ElsfpApi.get_module_voltage()`                                                                                            |
| `show cpo oe / els firmware-info`                                          | `*_FIRMWARE_INFO`                                                                                                                                                                                              | `CpoDomInfoUpdateTask`                                                                                                          | `get_transceiver_info_firmware_versions()` / `get_elsfp_info_firmware_versions()`                                                                    |
| `show cpo oe / els lpmode` / `cposhow port lpmode`                       | `*_STATUS.module_state`                                                                                                                                                                                        | Derived inside `cposhow` (§8.2.7)                                                                                              | `ModuleLowPwr` → `On`; `ModulePwrUp` / `ModuleReady` / `ModulePwrDn` → `Off`; `ModuleFault` → `N/A (ModuleFault)`; no data → `N/A` |
| `show interfaces transceiver error-status` / `cposhow port error-status` | OE: `TRANSCEIVER_STATUS_SW`; ELS: `TRANSCEIVER_ELS_STATUS`; `-hw`: the `cpoutil` command of §13 OI-2                                                                                                    | OE row: `CpoStateUpdateTask` through the base-class path (`_get_port_error_description()`); ELS row: `CpoDomInfoUpdateTask` | `OeApi.get_error_description()` / `ElsfpApi.get_elsfp_status()`                                                                                      |

## Appendix B: Exit Codes

| Code | Meaning                      | Trigger                                                                                                                            |
| ---- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 0    | Success                      | Includes "some port data missing, output as `N/A`"                                                                               |
| 2    | Usage error                  | Unknown subcommand / invalid argument / `--port` does not exist / `-b` out of the bank range; click's default code, not custom |
| 3    | Platform has no CPO topology | `cpo.json` does not exist (`os.path.isfile()` is checked **before** calling `get_cpo_data()`)                          |
| 4    | CPO topology invalid         | The file exists but JSON parsing fails, or `CpoMapping` validation fails                                                         |
| 5    | Runtime environment error    | STATE_DB connection failure, unrelated to the data content                                                                         |

## Appendix C: Sample `cpo.json`

This is the single topology that every example in §8 uses. 8 banks per OE, one port per bank, 8 lasers per ELS with 4 ASIC lanes each.

```json
{
  "devices": {
    "OE0":  {"device_type": "optical_engine", "asic_lanes": "1,2,...,64", "max_banks": 8,
             "i2c_path": "/sys/bus/i2c/devices/24-0050"},
    "OE1":  {"device_type": "optical_engine", "asic_lanes": "65,66,...,128", "max_banks": 8,
             "i2c_path": "/sys/bus/i2c/devices/25-0050"},
    "ELS0": {"device_type": "external_laser_source",
             "laser_to_asic_lane_mapping": {"1": "17,18,19,20", "2": "21,22,23,24",
                                            "3": "25,26,27,28", "4": "29,30,31,32",
                                            "5": "1,2,3,4",     "6": "5,6,7,8",
                                            "7": "9,10,11,12",  "8": "13,14,15,16"}},
    "ELS1": {"device_type": "external_laser_source",
             "laser_to_asic_lane_mapping": {"1": "49,50,51,52", "2": "53,54,55,56",
                                            "3": "57,58,59,60", "4": "61,62,63,64",
                                            "5": "33,34,35,36", "6": "37,38,39,40",
                                            "7": "41,42,43,44", "8": "45,46,47,48"}}
  },
  "interfaces": {
    "Ethernet0":  {"index": "1,1,1,1,1,1,1,1",
                   "associated_devices": [{"device_id": "OE0", "bank": 0}, {"device_id": "ELS0", "bank": 0}]},
    "Ethernet8":  {"index": "2,2,2,2,2,2,2,2",
                   "associated_devices": [{"device_id": "OE0", "bank": 1}, {"device_id": "ELS0", "bank": 0}]},
    "Ethernet16": {"index": "3,3,3,3,3,3,3,3",
                   "associated_devices": [{"device_id": "OE0", "bank": 2}, {"device_id": "ELS0", "bank": 0}]},
    "Ethernet24": {"index": "4,4,4,4,4,4,4,4",
                   "associated_devices": [{"device_id": "OE0", "bank": 3}, {"device_id": "ELS0", "bank": 0}]},
    "Ethernet32": {"index": "5,5,5,5,5,5,5,5",
                   "associated_devices": [{"device_id": "OE0", "bank": 4}, {"device_id": "ELS1", "bank": 0}]},
    "Ethernet40": {"index": "6,6,6,6,6,6,6,6",
                   "associated_devices": [{"device_id": "OE0", "bank": 5}, {"device_id": "ELS1", "bank": 0}]},
    "Ethernet48": {"index": "7,7,7,7,7,7,7,7",
                   "associated_devices": [{"device_id": "OE0", "bank": 6}, {"device_id": "ELS1", "bank": 0}]},
    "Ethernet56": {"index": "8,8,8,8,8,8,8,8",
                   "associated_devices": [{"device_id": "OE0", "bank": 7}, {"device_id": "ELS1", "bank": 0}]}
  }
}
```

Reading notes:

- `bank` is **bank-local** (0..`max_banks-1`); the lane range of a bank is derived by even splitting of `asic_lanes` (`CpoMapping`), so `OE0` bank 0 is lanes 1-8 and bank 7 is lanes 57-64;
- `interfaces` keys are the logical port names, which is also the CPO port set used by §7.4 for classification;
- `laser_ids` per port are derived from `laser_to_asic_lane_mapping` (each port owns the lasers whose lanes intersect its own lanes); a platform that declares no mapping on the ELS falls back to `laser_ids` in `platform.json`;
- the optional `format` section (§7.5.3) is omitted here; it is orthogonal to topology and ignored by xcvrd.
