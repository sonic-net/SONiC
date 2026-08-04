# PMON Daemon Configuration Resolution High Level Design

## Table of Content

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1. Component: `PmonDaemonConfig`](#71-component-pmondaemonconfig)
  - [7.2. Per-daemon schema: `XcvrdConfig`](#72-per-daemon-schema-xcvrdconfig)
  - [7.3. Resolution precedence](#73-resolution-precedence)
  - [7.4. Merge, coercion, and validation](#74-merge-coercion-and-validation)
  - [7.5. Tunable reference: types, ranges, defaults](#75-tunable-reference-types-ranges-defaults)
  - [7.6. Daemon wiring](#76-daemon-wiring)
  - [7.7. Data flow](#77-data-flow)
  - [7.8. Adding a future tunable](#78-adding-a-future-tunable)
  - [7.9. Adopting the mechanism in another pmon daemon](#79-adopting-the-mechanism-in-another-pmon-daemon)
  - [7.10. Alternatives considered](#710-alternatives-considered)
- [8. SAI API](#8-sai-api)
- [9. Configuration and management](#9-configuration-and-management)
  - [9.1. Manifest](#91-manifest-if-the-feature-is-an-application-extension)
  - [9.2. CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
  - [9.3. Top-level keys versus the daemon section](#93-top-level-keys-versus-the-daemon-section)
  - [9.4. Config DB Enhancements](#94-config-db-enhancements)
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
| 0.2 | 2026-07-31 | Aditya (Nexthop)| Generalize `XcvrdConfig` into a shared `PmonDaemonConfig` base usable by any pmon daemon; add per-field range validation and a documented range for each tunable |

## 2. Scope

This document describes the design for how pmon daemons resolve their runtime
tunables from the platform-supplied `xcvrd`-style sections of
`pmon_daemon_control.json`, replacing the per-tunable command-line-flag
mechanism.

It defines a shared resolver, `PmonDaemonConfig`, and applies it to `xcvrd`
(the transceiver information update daemon, part of `sonic-platform-daemons`)
as the first adopter. The scope of the accompanying code change is:

- `sonic_py_common`: the new shared `PmonDaemonConfig` component.
- `xcvrd`: a `XcvrdConfig(PmonDaemonConfig)` schema and the removal of its
  `dom_*` command-line flags.
- `docker-platform-monitor` (`pmon`) supervisord template: stop emitting the
  removed `xcvrd` flags.

Migrating other pmon daemons (`thermalctld`, `psud`, `ledd`, `syseepromd`, ...)
onto `PmonDaemonConfig` is explicitly enabled by this design but is left to
follow-up changes owned by those daemons' maintainers; see
[7.9](#79-adopting-the-mechanism-in-another-pmon-daemon). This design does not
change transceiver data-path behavior, the DOM sensor polling algorithms
themselves, or any SAI interaction.

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
| `sonic_py_common` | Shared Python library depended on by every pmon daemon (`device_info`, `daemon_base`, `syslogger`, ...) |
| `PmonDaemonConfig` | Shared base class introduced here that resolves one daemon's section of `pmon_daemon_control.json` |
| HLD | High Level Design |

## 4. Overview

pmon daemons accept a small but steadily growing set of runtime tunables, e.g.
the `xcvrd` DOM temperature poll interval and DOM update interval. Historically
each tunable was plumbed end-to-end as a command-line flag:

1. A platform sets the value in the daemon's section of
   `pmon_daemon_control.json`.
2. `sonic-cfggen` loads that file when rendering the pmon supervisord template
   (`docker-pmon.supervisord.conf.j2`).
3. The template flattens the value into a `--<flag> <value>` argument on the
   daemon's command line.
4. `argparse` in the daemon's `main()` parses the flag.
5. The value is passed through the daemon constructor and stored as an instance
   attribute.

Adding one tunable therefore required edits in four places (template, argparse,
constructor signature, attribute assignment), and the daemon constructor grew a
parameter every time.

This is not specific to `xcvrd`. `thermalctld` carries the identical pattern
today, with five tunables each hand-plumbed through the same template
(`thermal_monitor_initial_interval`, `thermal_monitor_update_interval`,
`thermal_monitor_update_elapsed_threshold`, `enable_liquid_cooling`,
`liquid_cooling_update_interval`), and every future pmon tunable would repeat
it. The mechanism is therefore defined once, in `sonic_py_common`, rather than
once per daemon.

This design removes steps 2-5 for tunables. A daemon reads its own section of
`pmon_daemon_control.json` directly via `PmonDaemonConfig` - the same
per-platform file, read from the same device directories that
`media_settings.json` and `optics_si_settings.json` are already read from.
Adding a new tunable becomes a one-field change to the daemon's config schema;
platform owners continue to set values in the section they already maintain.

This also simplifies the operational flow for changing a tunable at runtime.
Because the value is read directly from `pmon_daemon_control.json` rather than
baked into the rendered supervisord command line, updating a flag only requires
restarting the daemon to pick up the new value, instead of having `pmon`
regenerate the whole supervisord template.

## 5. Requirements

- A new pmon daemon tunable shall be addable without editing the supervisord
  template, `argparse`, or the daemon constructor signature.
- The resolution mechanism shall be daemon-agnostic: any pmon daemon shall be
  able to adopt it by declaring a section name and a set of typed fields, with
  no copy of the file-location, parsing, or merge logic.
- Adoption shall be incremental. A daemon that has not migrated shall be
  unaffected, and no flag-day change across all pmon daemons shall be required.
- Per-platform default values shall continue to be expressible by the platform
  owner in a file shipped with the platform, and per-hwsku overrides shall take
  precedence over per-platform values.
- A missing file, missing section, malformed JSON, or unreadable file shall not
  prevent the daemon from starting; it shall fall back to built-in defaults.
- Each tunable shall declare a valid range (or an explicit "unbounded"), the
  range shall be enforced after type coercion, and an out-of-range value shall
  be rejected in favor of the built-in default rather than being passed to the
  consuming code.
- Existing per-platform values already present in the `xcvrd` section
  (e.g. `dom_temperature_poll_interval`, `dom_update_interval`) shall continue
  to take effect with identical observed behavior for all in-range values.
- The resolution logic shall be unit-testable without touching the filesystem.

## 6. Architecture Design

This change is internal to the pmon daemons and the pmon container's startup
rendering. It introduces no new processes, threads, daemons, or inter-process
interfaces, and does not alter the overall SONiC architecture.

The only architectural shift is the **source** from which a daemon obtains its
tunables: previously the rendered supervisord command line (argv), now its own
section of `pmon_daemon_control.json` read directly by the daemon at startup.
Both the old and new paths originate from the same per-platform file; the
redundant "flatten into argv then re-parse" round trip is eliminated.

The change spans two repositories:

| Repository | Change |
|------------|--------|
| `sonic-buildimage` | New `sonic_py_common/pmon_daemon_config.py`; `docker-pmon.supervisord.conf.j2` stops emitting the removed `xcvrd` flags |
| `sonic-platform-daemons` | `XcvrdConfig(PmonDaemonConfig)` schema; `xcvrd` `argparse`/constructor cleanup |

The `sonic_py_common` change must merge before the `sonic-platform-daemons`
submodule is advanced, since the daemon imports the new module. Both are built
into the same image from a single `sonic-buildimage` build, so version skew is
bounded to the submodule bump.

## 7. High-Level Design

### 7.1. Component: `PmonDaemonConfig`

A new module, `sonic_py_common/pmon_daemon_config.py`, provides the resolver
that all pmon daemons share. It owns everything that is not daemon-specific:
locating `pmon_daemon_control.json`, extracting the daemon's section, merging
it over the built-in defaults, coercing types, validating ranges, and degrading
safely on any error.

```python
@dataclass(frozen=True)
class FieldSpec:
    """Per-field type coercion and validation policy."""
    caster: Optional[Callable] = None   # applied first, e.g. int / to_bool
    minimum: Optional[int] = None       # inclusive; None means unbounded below
    maximum: Optional[int] = None       # inclusive; None means unbounded above
    choices: Optional[tuple] = None     # enumerated values, if applicable


@dataclass
class PmonDaemonConfig:
    """Base class. Subclasses declare SECTION_NAME, FIELD_SPECS, and fields."""

    SECTION_NAME: ClassVar[str] = ''
    FIELD_SPECS: ClassVar[Dict[str, FieldSpec]] = {}
    SYSLOG_IDENTIFIER: ClassVar[Optional[str]] = None   # default "<section>_config"

    @classmethod
    def resolve(cls, platform_section=None):
        """Layer the platform section over the built-in defaults."""
        cfg = cls()
        if platform_section is None:
            platform_section = cls._read_platform_section()
        cfg._merge(platform_section)
        cfg._post_merge()
        return cfg

    def __init_subclass__(cls): ...           # reject fields/FIELD_SPECS mismatch
    def _merge(self, overrides): ...          # coerce + validate + assign
    def _post_merge(self): ...                # cross-field hook; no-op by default
    @classmethod
    def _read_platform_section(cls): ...      # locate file, return dict or {}
```

`FIELD_SPECS` is keyed by field name, so a key matching no field would be
silently ignored - and that tunable would then get neither coercion nor a range
check, the exact failure the specs exist to prevent. `__init_subclass__` rejects
that mismatch, and the reverse (a field with no spec), when the schema class is
defined. These are static errors in the schema rather than bad input, so they
raise at import and are caught by the first unit test that loads the module;
bad values in `pmon_daemon_control.json` remain non-fatal.

`platform_section` is exposed so the merge and validation logic can be unit
tested without touching the filesystem; in production it is read from disk.

The base class carries no fields of its own, so a subclass's `@dataclass` field
ordering and defaults are unaffected.

A `to_bool` helper is provided alongside `FieldSpec` because `bool("false")` is
`True` in Python; boolean tunables (e.g. `thermalctld`'s `enable_liquid_cooling`)
must parse `"true"`/`"false"`/`"1"`/`"0"` explicitly rather than relying on
`bool()`.

### 7.2. Per-daemon schema: `XcvrdConfig`

`xcvrd/xcvrd_utilities/xcvrd_config.py` shrinks to a schema declaration:

```python
@dataclass
class XcvrdConfig(PmonDaemonConfig):
    SECTION_NAME = 'xcvrd'
    FIELD_SPECS = {
        'dom_temperature_poll_interval': FieldSpec(caster=int, minimum=0, maximum=86400),
        'dom_update_interval':           FieldSpec(caster=int, minimum=0, maximum=86400),
    }

    # Built-in defaults (lowest precedence).
    dom_temperature_poll_interval: Optional[int] = None
    dom_update_interval: Optional[int] = None
```

`None` is a meaningful default and is preserved: a `None`
`dom_temperature_poll_interval` disables the DOM thermal poll thread, and a
`None` `dom_update_interval` lets `DomInfoUpdateTask` apply its own
`DEFAULT_DOM_INFO_UPDATE_PERIOD_SECS` (60s).

### 7.3. Resolution precedence

`resolve()` layers sources, highest precedence first:

1. **Per-platform / per-hwsku file** - the daemon's section of
   `pmon_daemon_control.json`.
2. **Built-in defaults** - the dataclass field defaults.

The platform file is located using
`device_info.get_paths_to_platform_and_hwsku_dirs()` - the same helper and the
same hwsku-over-platform precedence used by `docker_init.j2` and the existing
`media_settings_parser` / `optics_si_parser`. Only the first existing file is
consulted (no cross-file merge), mirroring `docker_init` semantics.

### 7.4. Merge, coercion, and validation

Each key in the section is processed in order:

1. **Unknown key** - ignored with a log notice (forward-compatible: a newer
   platform file may carry keys an older daemon does not know).
2. **`None` value** - skipped; an absent override never clobbers a lower layer.
3. **Coercion** - `FieldSpec.caster` coerces the value to the declared type
   (e.g. the string `"20"` becomes `int 20`), mirroring the old
   `argparse type=int`. An uncoercible value is rejected.
4. **Validation** - the coerced value is checked against `minimum` / `maximum`
   (inclusive) and `choices`. An out-of-range value is rejected.
5. **Assignment** - the surviving value is stored on the dataclass instance.

A rejection at step 3 or 4 logs a warning naming the field, the offending
value, and the expected range, and leaves the lower-precedence value (the
built-in default) in place. Rejection is never fatal: the daemon always starts.

Once every key has been processed, `resolve()` calls the `_post_merge()` hook.
`FieldSpec` validates each field in isolation, so a schema that needs a
constraint spanning two fields overrides this hook to enforce or clamp the
relationship with all overrides already applied. The base implementation does
nothing, so schemas without cross-field constraints ignore it.

Any failure to resolve the platform directories or read/parse the file degrades
to an empty section, i.e. built-in defaults.

**Why validation belongs in this layer.** Type coercion alone is not enough: a
negative interval coerces to a perfectly good `int` but is not a valid
configuration value, and the two `xcvrd` tunables currently disagree about what
happens next. `DomInfoUpdateTask` checks for a negative `dom_update_interval`
and falls back to its 60s default with a warning, while
`DomThermalInfoUpdateTask` does not check `poll_interval` at all - a negative
value there makes the next scheduled poll time permanently in the past, so the
sweep runs back-to-back with no delay. A typo such as `-60` therefore silently
produces maximum transceiver I2C load instead of one poll per minute. Centralizing
the range check in `PmonDaemonConfig` gives every tunable one documented,
uniformly enforced contract and one place to test it.

The existing negative-value guard in `DomInfoUpdateTask.__init__` is retained as
defense-in-depth for direct constructor callers and unit tests; for
config-sourced values it becomes unreachable.

### 7.5. Tunable reference: types, ranges, defaults

| Field | Type | Valid range (inclusive) | Built-in default | Boundary semantics |
|-------|------|-------------------------|------------------|--------------------|
| `dom_temperature_poll_interval` | int, seconds | `0` - `86400` | `None` | `None`: `DomThermalInfoUpdateTask` is not started. `0`: poll continuously with no delay between sweeps. |
| `dom_update_interval` | int, seconds | `0` - `86400` | `None` | `None`: `DomInfoUpdateTask` uses `DEFAULT_DOM_INFO_UPDATE_PERIOD_SECS` (60s). `0`: update continuously with no delay between sweeps. |

Rationale for the bounds:

- **Lower bound `0`** - `0` is a supported, documented value meaning "no delay
  between sweeps". Anything below `0` has no defined meaning and is rejected.
- **Upper bound `86400`** (24h) - a poll interval longer than a day is
  operationally indistinguishable from "disabled" and is far more likely a units
  mistake (milliseconds entered where seconds are expected) than an intent. The
  bound is a typo guard, not a functional limit; it is called out in
  [section 14](#14-openaction-items---if-any) as adjustable if the community
  prefers a different value or an unbounded field.

Every field declared on a config schema must carry a `FieldSpec`; this is
enforced at class definition, not left as a convention (see
[7.1](#71-component-pmondaemonconfig)). Fields whose values are genuinely
unbounded declare `FieldSpec(caster=...)` with no `minimum`/`maximum`, so
"unbounded" is an explicit, reviewable choice rather than an omission.

### 7.6. Daemon wiring

`DaemonXcvrd.__init__` calls `self.config = XcvrdConfig.resolve()` once at
startup. Call sites read tunables via `self.config.<field>` (e.g.
`self.config.dom_temperature_poll_interval`). `main()` no longer parses or
forwards `dom_*` flags.

### 7.7. Data flow

Before:

```
pmon_daemon_control.json --(sonic-cfggen -j)--> Jinja flattens to --flag value
   --> argparse --> DaemonXcvrd(..., dom_temperature_poll_interval, ...)
```

After:

```
pmon_daemon_control.json["xcvrd"] --(read directly by XcvrdConfig.resolve)--> self.config
```

### 7.8. Adding a future tunable

1. Add one field (with default) to the daemon's config schema.
2. Add one `FIELD_SPECS` entry declaring its type coercion and valid range.
3. Read it via `self.config.<field>` where needed.

No template, `argparse`, or constructor-signature change is required. Platform
owners set the value in the section they already maintain.

### 7.9. Adopting the mechanism in another pmon daemon

A daemon adopts the mechanism by declaring a schema; it inherits all resolution,
coercion, validation, and error handling. Using `thermalctld`'s existing
tunables as a worked example:

```python
@dataclass
class ThermalctldConfig(PmonDaemonConfig):
    SECTION_NAME = 'thermalctld'
    FIELD_SPECS = {
        'thermal_monitor_initial_interval':         FieldSpec(caster=int, minimum=0, maximum=86400),
        'thermal_monitor_update_interval':          FieldSpec(caster=int, minimum=0, maximum=86400),
        'thermal_monitor_update_elapsed_threshold': FieldSpec(caster=int, minimum=0, maximum=86400),
        'enable_liquid_cooling':                    FieldSpec(caster=to_bool),
        'liquid_cooling_update_interval':           FieldSpec(caster=int, minimum=0, maximum=86400),
    }

    thermal_monitor_initial_interval: Optional[int] = None
    thermal_monitor_update_interval: Optional[int] = None
    thermal_monitor_update_elapsed_threshold: Optional[int] = None
    enable_liquid_cooling: Optional[bool] = None
    liquid_cooling_update_interval: Optional[int] = None
```

That schema replaces five `argparse` arguments, five constructor parameters, and
roughly twenty lines of conditional Jinja in
`docker-pmon.supervisord.conf.j2`. The equivalent applies to `psud`, `ledd`, and
`syseepromd` as they acquire tunables.

Adoption is per-daemon and independent: a daemon that has not migrated keeps its
flags, keeps its template block, and is unaffected by this change. Migrating
`thermalctld` and others is intentionally left to separate changes so each can be
reviewed and regression-tested by its own maintainers; only `xcvrd` is migrated
here.

### 7.10. Alternatives considered

| Alternative | Why not chosen |
|-------------|----------------|
| Keep the resolver private to `xcvrd` (`XcvrdConfig` only) | Every other pmon daemon would re-implement the same file location, parse, merge, and validation logic. `thermalctld` already has five tunables on the flag path that would duplicate it verbatim. |
| New shared wheel in `sonic-platform-daemons` | Requires a new Python package, Debian packaging, and an install line in the pmon Dockerfile for every consuming daemon. `sonic_py_common` is already a universal dependency of all pmon daemons, so it carries no new packaging. |
| Fold the resolver into `DaemonBase` | Couples config resolution to daemon construction and to the `DaemonBase` contract, and makes the resolver awkward to use from utility modules and unit tests. A thin `DaemonBase` convenience wrapper over `PmonDaemonConfig` remains possible later; see [section 14](#14-openaction-items---if-any). |
| Source tunables from Config DB instead of the platform file | Changes the ownership model: these are platform-owner defaults shipped with the platform, not operator configuration. A Config DB layer can be added on top later as a higher-precedence source; see [9.4](#94-config-db-enhancements). |

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
**retained** unchanged. They are derived from top-level keys in
`pmon_daemon_control.json`, not from the `xcvrd` section; see
[9.3](#93-top-level-keys-versus-the-daemon-section) for which keys live where
and why.

Other daemons' flags (e.g. `thermalctld`'s `--thermal-monitor-*` and
`--*liquid_cooling*`) are **unchanged** by this design; they are removed only
when those daemons adopt `PmonDaemonConfig` in their own changes.

Backwards compatibility note (per template guidance): the removed flags were
emitted only by `docker-pmon.supervisord.conf.j2`, which is updated in the same
change to stop emitting them. Every supported platform configures `xcvrd`
through this template, so there is no in-tree caller that passes the removed
flags. The per-platform `pmon_daemon_control.json` `xcvrd` section format is
unchanged, so platforms already setting `dom_temperature_poll_interval` /
`dom_update_interval` there continue to work with identical behavior for all
in-range values. The one intentional behavior change is that an out-of-range
value (e.g. a negative interval) is now rejected in favor of the built-in
default and logged, instead of reaching the polling threads; see
[7.4](#74-merge-coercion-and-validation).

### 9.3. Top-level keys versus the daemon section

`pmon_daemon_control.json` holds two kinds of per-daemon settings, and only one
of them is in scope for `PmonDaemonConfig`. The distinction is already the
convention in shipped platform files - e.g.
`device/aspeed/arm64-aspeed_nvidia_ast2700_bmc-r0/pmon_daemon_control.json`
carries a top-level `skip_thermalctld` alongside a nested `thermalctld` object -
but it has not been written down, so this design states it explicitly:

- **Top-level keys** (`skip_<daemon>`, `delay_<daemon>`, and the per-daemon
  capability keys) are **pmon orchestration settings**. They are consumed by
  `sonic-cfggen` while rendering `docker-pmon.supervisord.conf.j2` and describe
  how supervisord should launch the daemon.
- **The nested `"<daemon>"` object** holds the daemon's **own runtime
  configuration**, read by the daemon itself. This is what `PmonDaemonConfig`
  resolves.

For `xcvrd` the template reads four top-level keys. None move into the `xcvrd`
section:

| Top-level key | Effect | Why it stays top-level |
|---------------|--------|------------------------|
| `skip_xcvrd` | Whether the `[program:xcvrd]` block is emitted at all | Consumed before the process exists. A daemon cannot decline to start itself, so this can never be daemon-side under any design. |
| `delay_xcvrd` | Wraps the command in `bash -c "sleep 30 && ..."` | Same: it changes how supervisord launches the process, which the process cannot do for itself. |
| `skip_xcvrd_cmis_mgr` | Emits `--skip_cmis_mgr` | Could technically move (see below), but is left alone to keep this change mechanical. |
| `enable_xcvrd_sff_mgr` | Emits `--enable_sff_mgr` | Same. |

The first two are structural: they gate and shape process startup, so they
belong to whoever writes the supervisord config and are outside the reach of any
daemon-side resolver.

The last two are a deliberate scope decision rather than a structural limit, and
worth being honest about. `xcvrd` is already running when it reads them, so they
could be expressed as two `bool` fields with the `to_bool` caster exactly like
any other flag - the mechanism would handle them unchanged. They are left on the
command line because:

- Migrating them changes the key's location in the platform file
  (`skip_xcvrd_cmis_mgr` at top level would become, say, `skip_cmis_mgr` inside
  the `xcvrd` section), which is a breaking change for every platform that sets
  them today. The `dom_*` tunables being replaced here need no such move: they
  are already inside the `xcvrd` section.
- They select which task managers start, so a mistake in migrating them changes
  link bring-up behavior rather than a polling cadence. That warrants its own
  change with its own regression testing, not a ride-along.

If the community prefers the mgr flags to move too, the mechanism does not need
to change - only the platform-file key location and a compatibility window that
accepts both spellings during the transition. Listed in
[section 14](#14-openaction-items---if-any).

### 9.4. Config DB Enhancements

No Config DB schema changes. Tunables are sourced from the per-platform
`pmon_daemon_control.json` file, not from Config DB.

(Future option, out of scope here: a Config DB table per daemon could be layered
on top of `PmonDaemonConfig` as a higher-precedence operator-override source
without disturbing the file-based default mechanism. Because merge, coercion,
and validation are already centralized, such a layer would be an additional
source in `resolve()` rather than new per-daemon logic.)

## 10. Warmboot and Fastboot Design Impact

No impact on warmboot or fastboot. The change only affects how a daemon reads
its startup tunables; it adds no state that must be preserved across a reboot
and changes no boot ordering, dependency, or persisted data.

### 10.1. Warmboot and Fastboot Performance Impact

No control-plane or data-plane downtime impact. At daemon startup the daemon
performs at most one additional small file read (`pmon_daemon_control.json`)
from the local device directory; this is negligible and occurs only once during
process initialization, not on the warmboot/fastboot data-path critical
timeline.

## 11. Memory Consumption

Negligible and bounded. The resolved configuration is a single dataclass
instance holding a fixed, small number of scalar fields, created once at daemon
startup. There is no per-port or per-event allocation and no growth over time.
When the daemon is effectively "disabled" for a tunable (value left at default),
no additional memory is consumed and no resources are allocated for that
tunable's behavior (e.g. the DOM thermal poll thread is simply not started when
`dom_temperature_poll_interval` is `None`).

## 12. Restrictions/Limitations

- Tunables are resolved once at daemon startup. Changing a value in
  `pmon_daemon_control.json` requires an `xcvrd` (or pmon container) restart to
  take effect. Runtime/dynamic reconfiguration is out of scope.
- Only the first existing `pmon_daemon_control.json` (hwsku preferred, then
  platform) is consulted; values are not merged across both files.
- Configuration is sourced from the platform file only; there is currently no
  operator-facing override (e.g. Config DB).
- An invalid or out-of-range value is not surfaced to the operator beyond a
  syslog warning; the daemon starts on the built-in default rather than failing
  fast. This is deliberate - a bad tunable must never keep transceiver
  monitoring down - but it does mean a misconfiguration can go unnoticed if logs
  are not inspected.
- `FieldSpec` validation is per-field only. A constraint spanning two fields
  (e.g. one interval that must not exceed another) is not expressible
  declaratively and must be written as imperative code in the schema's
  `_post_merge()` override.
- `PmonDaemonConfig` lives in `sonic_py_common`, so a daemon adopting it takes a
  dependency on a `sonic_py_common` version that provides it. Within a single
  `sonic-buildimage` build this is guaranteed; out-of-tree daemons pinning an
  older `sonic_py_common` cannot adopt it until they upgrade.

## 13. Testing Requirements/Design

### 13.1. Unit Test cases

New unit tests for the shared `PmonDaemonConfig` (in `sonic_py_common`'s test
suite), exercised through a small test-only subclass so the base is covered
independently of any real daemon:

- Defaults when no section is present.
- Section overrides defaults; a partial section leaves other fields at default.
- A `None` value in the section does not override.
- A string value is coerced via `FieldSpec.caster`.
- An uncoercible value is ignored and the default is kept.
- `to_bool` accepts `true`/`false`/`1`/`0`/`yes`/`no` in either case and rejects
  other strings (in particular, `"false"` resolves to `False`, not `True`).
- Range validation: a value below `minimum` and a value above `maximum` are each
  rejected with the default kept; `minimum` and `maximum` are inclusive, so the
  boundary values themselves are accepted.
- A field whose `FieldSpec` declares no bounds accepts any coercible value.
- Schema guard: a `FIELD_SPECS` key naming no field, and a field with no
  `FIELD_SPECS` entry, each raise at class definition; a schema declaring only
  `ClassVar`s and a schema extending another are both accepted.
- A value outside `choices` is rejected.
- Unknown keys are ignored.
- Two subclasses with different `SECTION_NAME`s read their own sections and do
  not see each other's keys.
- The `_post_merge()` hook runs after every override is applied, sees defaults
  the section did not override, and is a no-op for schemas that do not override
  it.
- File location: platform file used when no hwsku file; hwsku file takes
  precedence over platform file; hwsku file present but lacking the daemon's
  section does not fall back to the platform file.
- No section, malformed JSON, non-dict section, an empty directory path entry,
  and a `device_info` failure all degrade to defaults.

`xcvrd` schema tests in `tests/test_xcvrd_config.py`:

- Bare `XcvrdConfig()` construction yields the documented defaults
  (`None` for both `dom_*` fields).
- Platform section overrides both `dom_*` fields.
- The value `0` is preserved for both fields (meaningful: continuous polling).
- A negative `dom_temperature_poll_interval` and a negative `dom_update_interval`
  are each rejected and the default is kept - the case that previously reached
  `DomThermalInfoUpdateTask` and produced an undelayed poll loop.
- A value above the documented maximum is rejected for both fields.
- `86400` and `0` are accepted for both fields (inclusive boundaries).
- End-to-end `resolve()` reads from disk and applies defaults when nothing is on
  disk.

Wiring tests in `tests/test_xcvrd.py`:

- `DaemonXcvrd.__init__` populates `self.config` from `XcvrdConfig.resolve()`.
- With no platform overrides, `dom_*` tunables fall back to `None` defaults.
- With a rejected (out-of-range) `dom_temperature_poll_interval`, the DOM thermal
  poll thread is not started, matching the `None` default.

All `sonic-xcvrd` unit tests pass (full suite green) and the new modules are
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
- With an out-of-range value configured (e.g. `dom_update_interval: -60`),
  verify `xcvrd` starts, logs a warning naming the field and expected range, and
  runs on the built-in default cadence.
- Regression: confirm existing platforms (e.g. ones setting
  `dom_temperature_poll_interval`) behave identically to the prior
  flag-based path.

## 14. Open/Action items - if any

- **Upper bounds.** The `86400`-second maximum on the `dom_*` intervals is a
  units-typo guard rather than a functional limit. Confirm the value, or decide
  that these fields should be bounded below only.
- **`DaemonBase` integration.** Whether to add a thin convenience hook (e.g.
  `DaemonBase.load_config(config_cls)`) once a second daemon has adopted
  `PmonDaemonConfig`, so the resolve call is not repeated in each daemon's
  `__init__`.
- **The mgr capability flags.** Whether `skip_xcvrd_cmis_mgr` and
  `enable_xcvrd_sff_mgr` should also move into the `xcvrd` section. The resolver
  handles them as-is; the cost is relocating a key platforms already set, so it
  needs a compatibility window accepting both spellings. Deliberately excluded
  here; see [9.3](#93-top-level-keys-versus-the-daemon-section).
- **Migration order.** Which daemon migrates next. `thermalctld` is the largest
  beneficiary (five tunables, ~20 lines of template Jinja) and is the natural
  second adopter; sequencing is for its maintainers.
- **Config DB override layer.** Whether to introduce per-daemon Config DB tables
  as a higher-precedence, operator-facing override layer (would enable runtime
  reconfiguration). Out of scope for this design.
