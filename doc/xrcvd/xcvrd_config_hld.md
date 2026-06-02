# xcvrd Configuration Resolution High Level Design

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1. Manifest](#91-manifest-if-the-feature-is-an-application-extension)
  - [9.2. CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3. Config DB Enhancements](#93-config-db-enhancements)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
  - [10.1. Warmboot and Fastboot Performance Impact](#101-warmboot-and-fastboot-performance-impact)
- [11. Memory Consumption](#11-memory-consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations)
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
  - [13.1. Unit Test cases](#131-unit-test-cases)
  - [13.2. System Test cases](#132-system-test-cases)
- [14. Open/Action items](#14-openaction-items---if-any)

## 1. Revision

| Rev | Date       | Author          | Change Description                          |
|-----|------------|-----------------|---------------------------------------------|
| 0.1 | 2026-06-01 | Aditya (Nexthop)| Initial version                             |

## 2. Scope

This document describes the design for how `xcvrd` (the transceiver
information update daemon, part of `sonic-platform-daemons`) resolves its
runtime tunables.

It covers the replacement of the per-tunable command-line-flag mechanism with a
single configuration object (`XcvrdConfig`) that reads the platform-supplied
`xcvrd` section of `pmon_daemon_control.json`. The scope is limited to the
`xcvrd` daemon and the `docker-platform-monitor` (`pmon`) supervisord template
that launches it. It does not change transceiver data-path behavior, the DOM
sensor polling algorithms themselves, or any SAI interaction.

## 3. Definitions/Abbreviations

| Term | Definition |
|------|------------|
| xcvrd | Transceiver information update daemon running in the `pmon` container |
| DOM | Digital Optical Monitoring (transceiver diagnostic sensor data) |
| pmon | Platform monitor Docker container |
| CMIS | Common Management Interface Specification (transceiver management) |
| SFF | Small Form Factor (transceiver management) |
| hwsku | Hardware SKU - per-SKU device configuration directory |
| `pmon_daemon_control.json` | Per-platform / per-hwsku file controlling which pmon daemons start and their tunables |
| HLD | High Level Design |

## 4. Overview

`xcvrd` accepts a small but steadily growing set of runtime tunables, e.g. the
DOM temperature poll interval and the DOM update interval. Historically each
tunable was plumbed end-to-end as a command-line flag:

1. A platform sets the value in the `xcvrd` section of
   `pmon_daemon_control.json`.
2. `sonic-cfggen` loads that file when rendering the pmon supervisord template
   (`docker-pmon.supervisord.conf.j2`).
3. The template flattens the value into a `--<flag> <value>` argument on the
   `xcvrd` command line.
4. `argparse` in `xcvrd`'s `main()` parses the flag.
5. The value is passed through `DaemonXcvrd.__init__` and stored as an instance
   attribute.

Adding one tunable therefore required edits in four places (template, argparse,
constructor signature, attribute assignment), and the daemon constructor grew a
parameter every time.

This design removes steps 2-5 for tunables. `xcvrd` reads the `xcvrd` section of
`pmon_daemon_control.json` directly via a new `XcvrdConfig` resolver - the same
per-platform file, read from the same device directories that
`media_settings.json` and `optics_si_settings.json` are already read from.
Adding a new tunable becomes a one-field change to `XcvrdConfig`; platform
owners continue to set values in the `xcvrd` section they already maintain.

This also simplifies the operational flow for changing a tunable at runtime.
Because the value is read directly from `pmon_daemon_control.json` rather than
baked into the rendered supervisord command line, updating a flag only requires
restarting `xcvrd` to pick up the new value, instead of having `pmon` regenerate
the whole supervisord template.

## 5. Requirements

- A new `xcvrd` tunable shall be addable without editing the supervisord
  template, `argparse`, or the `DaemonXcvrd` constructor signature.
- Per-platform default values shall continue to be expressible by the platform
  owner in a file shipped with the platform, and per-hwsku overrides shall take
  precedence over per-platform values.
- A missing file, missing `xcvrd` section, malformed JSON, or unreadable file
  shall not prevent `xcvrd` from starting; it shall fall back to built-in
  defaults.
- Existing per-platform values already present in the `xcvrd` section
  (e.g. `dom_temperature_poll_interval`, `dom_update_interval`) shall continue
  to take effect with identical observed behavior.
- The resolution logic shall be unit-testable without touching the filesystem.

## 6. Architecture Design

This change is internal to the `xcvrd` daemon and the pmon container's startup
rendering. It introduces no new processes, threads, daemons, or inter-process
interfaces, and does not alter the overall SONiC architecture.

The only architectural shift is the **source** from which `xcvrd` obtains its
tunables: previously the rendered supervisord command line (argv), now the
`xcvrd` section of `pmon_daemon_control.json` read directly by the daemon at
startup. Both the old and new paths originate from the same per-platform file;
the redundant "flatten into argv then re-parse" round trip is eliminated.

## 7. High-Level Design

### 7.1. Component: `XcvrdConfig`

A new module, `xcvrd/xcvrd_utilities/xcvrd_config.py`, defines a dataclass
`XcvrdConfig` whose fields are the resolvable tunables and whose field defaults
are the built-in defaults:

```python
@dataclass
class XcvrdConfig:
    dom_temperature_poll_interval: Optional[int] = None
    dom_update_interval: Optional[int] = None
```

`None` is a meaningful default and is preserved: a `None`
`dom_temperature_poll_interval` disables the DOM thermal poll thread, and a
`None` `dom_update_interval` lets `DomInfoUpdateTask` apply its own
`DEFAULT_DOM_INFO_UPDATE_PERIOD_SECS` (60s).

### 7.2. Resolution precedence

`XcvrdConfig.resolve()` layers sources, highest precedence first:

1. **Per-platform / per-hwsku file** - the `xcvrd` section of
   `pmon_daemon_control.json`.
2. **Built-in defaults** - the dataclass field defaults.

The platform file is located using
`device_info.get_paths_to_platform_and_hwsku_dirs()` - the same helper and the
same hwsku-over-platform precedence used by `docker_init.j2` and the existing
`media_settings_parser` / `optics_si_parser`. Only the first existing file is
consulted (no cross-file merge), mirroring `docker_init` semantics.

### 7.3. Merge and coercion

- Keys not declared as `XcvrdConfig` fields are ignored with a log notice
  (forward-compatible: a newer platform file may carry keys an older daemon
  does not know).
- A `None` value never overrides a lower layer.
- A `_FIELD_CASTERS` map coerces values to the declared type (e.g. a value given
  as the string `"20"` becomes `int 20`), mirroring the old `argparse type=int`.
  An uncoercible value is ignored with a log warning and the default is kept.
- Any failure to resolve the platform directories or read/parse the file
  degrades to an empty section, i.e. built-in defaults.

### 7.4. Daemon wiring

`DaemonXcvrd.__init__` calls `self.config = XcvrdConfig.resolve()` once at
startup. Call sites read tunables via `self.config.<field>` (e.g.
`self.config.dom_temperature_poll_interval`). `main()` no longer parses or
forwards `dom_*` flags.

### 7.5. Data flow

Before:

```
pmon_daemon_control.json --(sonic-cfggen -j)--> Jinja flattens to --flag value
   --> argparse --> DaemonXcvrd(..., dom_temperature_poll_interval, ...)
```

After:

```
pmon_daemon_control.json["xcvrd"] --(read directly by XcvrdConfig.resolve)--> self.config
```

### 7.6. Adding a future tunable

1. Add one field (with default) to `XcvrdConfig`.
2. If it needs non-trivial coercion, add one entry to `_FIELD_CASTERS`.
3. Read it via `self.config.<field>` where needed.

No template, `argparse`, or constructor-signature change is required. Platform
owners set the value in the `xcvrd` section they already maintain.

## 8. SAI API

No SAI API changes. This feature does not interact with SAI.

## 9. Configuration and management

### 9.1. Manifest (if the feature is an Application Extension)

Not applicable. `xcvrd` is a built-in pmon daemon, not an Application Extension.

### 9.2. CLI/YANG model Enhancements

No operator-facing CLI or YANG model changes.

The following internal `xcvrd` command-line flags are **removed**, as the values
are now read directly from the platform file:

- `--dom_temperature_poll_interval`
- `--dom_update_interval`

The feature-capability flags `--skip_cmis_mgr` and `--enable_sff_mgr` are
**retained** unchanged; they are derived from top-level keys in
`pmon_daemon_control.json` (`skip_xcvrd_cmis_mgr`, `enable_xcvrd_sff_mgr`) and
are start-time capability decisions rather than tunables.

Backwards compatibility note (per template guidance): the removed flags were
emitted only by `docker-pmon.supervisord.conf.j2`, which is updated in the same
change to stop emitting them. Every supported platform configures `xcvrd`
through this template, so there is no in-tree caller that passes the removed
flags. The per-platform `pmon_daemon_control.json` `xcvrd` section format is
unchanged, so platforms already setting `dom_temperature_poll_interval` /
`dom_update_interval` there continue to work with identical behavior.

### 9.3. Config DB Enhancements

No Config DB schema changes. Tunables are sourced from the per-platform
`pmon_daemon_control.json` file, not from Config DB.

(Future option, out of scope here: a Config DB `XCVRD` table could be layered on
top of `XcvrdConfig` as a higher-precedence operator-override source without
disturbing the file-based default mechanism.)

## 10. Warmboot and Fastboot Design Impact

No impact on warmboot or fastboot. The change only affects how `xcvrd` reads its
startup tunables; it adds no state that must be preserved across a reboot and
changes no boot ordering, dependency, or persisted data.

### 10.1. Warmboot and Fastboot Performance Impact

No control-plane or data-plane downtime impact. At daemon startup `xcvrd`
performs at most one additional small file read
(`pmon_daemon_control.json`) from the local device directory; this is
negligible and occurs only once during process initialization, not on the
warmboot/fastboot data-path critical timeline.

## 11. Memory Consumption

Negligible and bounded. The resolved configuration is a single dataclass
instance holding a fixed, small number of scalar fields, created once at daemon
startup. There is no per-port or per-event allocation and no growth over time.
When the daemon is effectively "disabled" for a tunable (value left at default),
no additional memory is consumed and no resources are allocated for that
tunable's behavior (e.g. the DOM thermal poll thread is simply not started when
`dom_temperature_poll_interval` is `None`).

## 12. Restrictions/Limitations

- Tunables are resolved once at `xcvrd` startup. Changing a value in
  `pmon_daemon_control.json` requires an `xcvrd` (or pmon container) restart to
  take effect. Runtime/dynamic reconfiguration is out of scope.
- Only the first existing `pmon_daemon_control.json` (hwsku preferred, then
  platform) is consulted; values are not merged across both files.
- Configuration is sourced from the platform file only; there is currently no
  operator-facing override (e.g. Config DB).

## 13. Testing Requirements/Design

### 13.1. Unit Test cases

New unit tests in `tests/test_xcvrd_config.py` cover `XcvrdConfig`:

- Defaults when no platform section is present.
- Bare `XcvrdConfig()` construction yields documented defaults.
- Platform section overrides defaults; partial sections leave other fields at
  default.
- A `None` value in the section does not override.
- The value `0` is preserved (meaningful: continuous polling).
- A string value is coerced to `int`.
- An invalid (uncoercible) value is ignored and the default is kept.
- Unknown keys are ignored.
- `pmon_daemon_control.json` location: platform file used when no hwsku file;
  hwsku file takes precedence over platform file; hwsku file present but lacking
  an `xcvrd` section does not fall back to the platform file.
- No `xcvrd` section, malformed JSON, non-dict `xcvrd` section, an empty
  directory path entry, and a `device_info` failure all degrade to defaults.
- End-to-end `resolve()` reads from disk and applies defaults when nothing is on
  disk.

Wiring tests in `tests/test_xcvrd.py`:

- `DaemonXcvrd.__init__` populates `self.config` from `XcvrdConfig.resolve()`.
- With no platform overrides, `dom_*` tunables fall back to `None` defaults.

All `sonic-xcvrd` unit tests pass (full suite green) and the new module is
covered at 100%.

### 13.2. System Test cases

- On a platform whose `pmon_daemon_control.json` `xcvrd` section sets
  `dom_temperature_poll_interval`, verify the DOM thermal poll thread starts and
  polls at the configured interval (e.g. STATE_DB DOM updates observed at the
  expected cadence).
- On a platform whose section sets `dom_update_interval`, verify DOM info
  updates occur at the configured interval.
- On a platform with no `xcvrd` section, verify `xcvrd` starts cleanly on
  built-in defaults.
- Regression: confirm existing platforms (e.g. ones setting
  `dom_temperature_poll_interval`) behave identically to the prior
  flag-based path.

## 14. Open/Action items - if any

- Decide whether to introduce a Config DB `XCVRD` table as a higher-precedence,
  operator-facing override layer (would enable runtime reconfiguration). Out of
  scope for this design.
