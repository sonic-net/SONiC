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
| 0.3 | 2026-08-27 | Aditya (Nexthop)| Allow one-level-deep subsections within a daemon section; add generic `SUBSECTIONS` and `LEGACY_ALIASES` support to `PmonDaemonConfig`; regroup `xcvrd` tunables under `dom`/`cmis_mgr`/`sff_mgr`/`cpo_mgr`; relocate the manager enable/disable toggles into the `xcvrd` section (deprecating top-level `skip_xcvrd_cmis_mgr` / `enable_xcvrd_sff_mgr` behind a compatibility window) |

## 2. Scope

This document describes the design for how pmon daemons resolve their runtime
tunables from the platform-supplied `xcvrd`-style sections of
`pmon_daemon_control.json`, replacing the per-tunable command-line-flag
mechanism.

It defines a shared resolver, `PmonDaemonConfig`, and applies it to `xcvrd`
(the transceiver information update daemon, part of `sonic-platform-daemons`)
as the first adopter. The scope of the accompanying code change is:

- `sonic_py_common`: the new shared `PmonDaemonConfig` component.
- `xcvrd`: a `XcvrdConfig(PmonDaemonConfig)` schema grouping its tunables into
  one-level-deep subsections (`dom`, `cmis_mgr`, `sff_mgr`, `cpo_mgr`) and the
  removal of its `dom_*` and manager (`--skip_cmis_mgr`, `--enable_sff_mgr`,
  `--skip_cpo_mgr`) command-line flags.
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
    caster: Optional[Callable] = None   # applied first, e.g. int / float / to_bool
    minimum: Optional[float] = None     # inclusive; None means unbounded below
    maximum: Optional[float] = None     # inclusive; None means unbounded above
    choices: Optional[tuple] = None     # enumerated values, if applicable


@dataclass(frozen=True)
class LegacyAlias:
    """Maps a deprecated key to a field on the new (possibly nested) schema."""
    target: str                          # dotted path, e.g. "cmis_mgr.enabled"
    scope: str = 'section'               # 'section' (daemon section) or 'file' (top-level)
    transform: Optional[Callable] = None  # value rewrite, e.g. invert for skip_*


@dataclass
class PmonDaemonConfig:
    """Base class. Subclasses declare SECTION_NAME, FIELD_SPECS, and fields."""

    SECTION_NAME: ClassVar[str] = ''
    FIELD_SPECS: ClassVar[Dict[str, FieldSpec]] = {}
    SUBSECTIONS: ClassVar[Dict[str, type]] = {}            # field -> subsection schema
    LEGACY_ALIASES: ClassVar[Dict[str, LegacyAlias]] = {}  # old key -> target
    SYSLOG_IDENTIFIER: ClassVar[Optional[str]] = None      # default "<section>_config"

    @classmethod
    def resolve(cls, platform_section=None, platform_file=None):
        """Layer the platform section over the built-in defaults."""
        cfg = cls()
        if platform_section is None:
            platform_section, platform_file = cls._read_platform_section()
        cfg._apply_legacy_aliases(platform_section, platform_file)
        cfg._merge(platform_section)
        cfg._post_merge()
        return cfg

    def __init_subclass__(cls): ...           # reject spec/field/subsection mismatch
    def _apply_legacy_aliases(self, section, file): ...  # route deprecated keys
    def _merge(self, overrides): ...          # coerce + validate + assign; recurse subsections
    def _post_merge(self): ...                # cross-field hook; no-op by default
    @classmethod
    def _read_platform_section(cls): ...      # locate file, return (section, whole-file)
```

Every declared field maps to **exactly one** of `FIELD_SPECS` (a scalar tunable)
or `SUBSECTIONS` (a nested group). A field in neither would get neither coercion
nor validation - the exact failure the specs exist to prevent - and a field in
both is ambiguous. `__init_subclass__` rejects both cases, plus the reverse (a
`FIELD_SPECS` or `SUBSECTIONS` key naming no field), when the schema class is
defined. These are static errors in the schema rather than bad input, so they
raise at import and are caught by the first unit test that loads the module; bad
values in `pmon_daemon_control.json` remain non-fatal.

**Subsections are exactly one level deep.** Each value in `SUBSECTIONS` must be a
`PmonDaemonConfig` subclass whose own `SUBSECTIONS` is empty; `__init_subclass__`
rejects a subsection schema that itself declares subsections. A subsection reuses
the same `_merge` machinery on its own `FIELD_SPECS`, so coercion and validation
inside a subsection are identical to the top level; only nesting further is a
schema error, caught at import, not something a platform file can trigger.

`LEGACY_ALIASES` maps a deprecated key to a `target` field via a dotted path
(`"cmis_mgr.enabled"`). `__init_subclass__` verifies every target resolves to a
real field or subsection field. Aliases are applied before the nested form is
merged, so the nested key always wins when both are present (see
[7.4](#74-merge-coercion-and-validation)).

`platform_section` and `platform_file` are exposed so the merge, alias, and
validation logic can be unit tested without touching the filesystem; in
production both are read from disk. `platform_file` is needed because a
`scope='file'` alias reads a top-level (sibling) key from outside the daemon
section.

The base class carries no fields of its own, so a subclass's `@dataclass` field
ordering and defaults are unaffected.

A `to_bool` helper is provided alongside `FieldSpec` because `bool("false")` is
`True` in Python; boolean tunables (e.g. a manager `enabled` toggle) must parse
their spelling explicitly rather than relying on `bool()`. It accepts real
booleans, the integers `0`/`1`, and the case-insensitive strings
`true`/`false`/`yes`/`no`/`on`/`off`/`1`/`0`; anything else raises so the
built-in default is kept (in particular `"false"` resolves to `False`, not
`True`).

`minimum` and `maximum` are typed `Optional[float]` rather than `Optional[int]`:
the same `FieldSpec` bounds a float cadence (e.g. `liquid_cooling.update_interval`,
whose caster is `float`) as well as the integer `dom` intervals, so the bound
type must accommodate both.

### 7.2. Per-daemon schema: `XcvrdConfig`

`xcvrd/xcvrd_utilities/xcvrd_config.py` shrinks to a schema declaration:

```python
@dataclass
class DomConfig(PmonDaemonConfig):
    SECTION_NAME = 'dom'
    FIELD_SPECS = {
        'temperature_poll_interval': FieldSpec(caster=int, minimum=0, maximum=86400),
        'update_interval':           FieldSpec(caster=int, minimum=0, maximum=86400),
    }
    temperature_poll_interval: Optional[int] = None
    update_interval: Optional[int] = None


@dataclass
class MgrConfig(PmonDaemonConfig):
    """Reused for cmis_mgr / sff_mgr / cpo_mgr - a single enabled toggle."""
    FIELD_SPECS = {'enabled': FieldSpec(caster=to_bool)}
    enabled: Optional[bool] = None


@dataclass
class XcvrdConfig(PmonDaemonConfig):
    SECTION_NAME = 'xcvrd'
    SUBSECTIONS = {
        'dom':      DomConfig,
        'cmis_mgr': MgrConfig,
        'sff_mgr':  MgrConfig,
        'cpo_mgr':  MgrConfig,
    }
    LEGACY_ALIASES = {
        # Flat dom_* keys that used to live directly in the xcvrd section. The
        # `v or None` transform reproduces the old Jinja truthy gate, so a flat
        # 0 maps to the default (parity with the removed template) while the
        # nested dom.* form still treats 0 as continuous.
        'dom_temperature_poll_interval': LegacyAlias('dom.temperature_poll_interval',
                                                     transform=lambda v: v or None),
        'dom_update_interval':           LegacyAlias('dom.update_interval',
                                                     transform=lambda v: v or None),
        # Top-level capability keys (scope='file'); skip_* inverts to enabled.
        'skip_xcvrd_cmis_mgr':  LegacyAlias('cmis_mgr.enabled', scope='file',
                                            transform=lambda v: not to_bool(v)),
        'enable_xcvrd_sff_mgr': LegacyAlias('sff_mgr.enabled',  scope='file'),
    }

    # Built-in defaults (lowest precedence): preserve today's behavior.
    dom:      DomConfig = field(default_factory=DomConfig)
    cmis_mgr: MgrConfig = field(default_factory=lambda: MgrConfig(enabled=True))
    sff_mgr:  MgrConfig = field(default_factory=lambda: MgrConfig(enabled=False))
    cpo_mgr:  MgrConfig = field(default_factory=lambda: MgrConfig(enabled=True))
```

`DomConfig` and `MgrConfig` are declared once each; `cmis_mgr`, `sff_mgr`, and
`cpo_mgr` all reuse `MgrConfig`. The manager defaults preserve today's behavior
exactly for a platform that overrides nothing: CMIS and CPO managers enabled,
SFF manager disabled.

A subsection schema's `SECTION_NAME` does not drive resolution - which
subsection a nested object maps to is decided by the parent's `SUBSECTIONS` key
(`'dom'`, `'cmis_mgr'`, ...), not by the child's `SECTION_NAME`. It is used only
to label log lines emitted while merging that subsection, so it is optional:
`MgrConfig` deliberately omits it (one class backs three subsections, so no
single name fits), while `DomConfig` sets `SECTION_NAME = 'dom'` purely for a
clearer `dom config: ...` prefix on its warnings. Only the top-level daemon
schema (`XcvrdConfig`) needs `SECTION_NAME`, to locate its section in the file.

`None` remains a meaningful default inside `dom`: a `None`
`dom.temperature_poll_interval` disables the DOM thermal poll thread, and a
`None` `dom.update_interval` lets `DomInfoUpdateTask` apply its own
`DEFAULT_DOM_INFO_UPDATE_PERIOD_SECS` (60s). Call sites read nested attributes,
e.g. `self.config.dom.update_interval` and `self.config.cmis_mgr.enabled`.

### 7.3. Resolution precedence

`resolve()` layers sources, highest precedence first:

1. **Nested section keys** - the subsection form in the daemon's section of
   `pmon_daemon_control.json` (e.g. `xcvrd.dom.update_interval`).
2. **Legacy aliases** - deprecated flat section keys (`dom_update_interval`) and
   top-level keys (`skip_xcvrd_cmis_mgr`), honored for a compatibility window.
3. **Built-in defaults** - the dataclass field defaults.

These three are the sub-tiers of a single input source - the per-platform file
layered over the built-in defaults. In the current scope `resolve()` reads no
other source: there is no Config DB or operator-facing tier. A Config DB
override layer is a deliberate follow-up that would slot in above the platform
file without changing per-daemon logic (see [9.4](#94-config-db-enhancements)
and [14](#14-openaction-items---if-any)).

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

**Subsections.** A key naming a `SUBSECTIONS` entry must have a dict value; the
nested dict is merged into the subsection instance by the same coercion and
validation steps applied to its own `FIELD_SPECS`. A non-dict value is rejected
with a warning and the subsection keeps its defaults. A partial subsection dict
leaves that subsection's other fields at their defaults, and unknown keys inside
a subsection are ignored exactly as at the top level.

**Legacy aliases.** Before the nested form is merged, `_apply_legacy_aliases`
walks `LEGACY_ALIASES`: for each deprecated key present (in the daemon section for
`scope='section'`, or the whole file for `scope='file'`), it applies the alias's
`transform` (e.g. inverting a `skip_*` flag to an `enabled` value) and writes the
result to the alias `target` only if the nested key is absent, then logs a
one-time deprecation notice. Because aliases are applied first and never
overwrite an explicit nested value, the nested form always wins when both are
present.

Once every key has been processed, `resolve()` calls the `_post_merge()` hook.
`FieldSpec` validates each field in isolation, so a schema that needs a
constraint spanning two fields (including fields in different subsections)
overrides this hook to enforce or clamp the relationship with all overrides
already applied. The base implementation does nothing, so schemas without
cross-field constraints ignore it.

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
config-sourced values it becomes unreachable. `DomThermalInfoUpdateTask` has no
equivalent guard of its own, so for its `poll_interval` this config layer is the
only place a negative value is caught - a further reason validation belongs here
rather than being duplicated (or forgotten) per task.

### 7.5. Tunable reference: types, ranges, defaults

| Field | Type | Valid range (inclusive) | Built-in default | Legacy source | Boundary semantics |
|-------|------|-------------------------|------------------|---------------|--------------------|
| `dom.temperature_poll_interval` | int, seconds | `0` - `86400` | `None` | `dom_temperature_poll_interval` | `None`: `DomThermalInfoUpdateTask` is not started. `0`: poll continuously with no delay between sweeps. |
| `dom.update_interval` | int, seconds | `0` - `86400` | `None` | `dom_update_interval` | `None`: `DomInfoUpdateTask` uses `DEFAULT_DOM_INFO_UPDATE_PERIOD_SECS` (60s). `0`: update continuously with no delay between sweeps. |
| `cmis_mgr.enabled` | bool | `true` / `false` | `true` | `skip_xcvrd_cmis_mgr` (inverted) | CMIS task manager runs by default; `false` skips it. |
| `sff_mgr.enabled` | bool | `true` / `false` | `false` | `enable_xcvrd_sff_mgr` | SFF task manager off by default; `true` enables it. |
| `cpo_mgr.enabled` | bool | `true` / `false` | `true` | *(none)* | CPO task manager runs by default; `false` skips it. No prior top-level key. |

The `0` semantics in the last column describe the **nested** form
(`dom.update_interval` / `dom.temperature_poll_interval`), which is the new
explicit API. The **deprecated flat** keys keep their historical behavior
instead: the removed template gated each flag with a Jinja truthy test
(`{% if xcvrd.dom_update_interval %}`), so a flat `0` was never emitted and the
daemon fell back to its default. The resolver preserves that exactly - a flat
`dom_update_interval: 0` or `dom_temperature_poll_interval: 0` resolves to the
built-in default (60s / thread not started), not to continuous polling - via a
`transform=lambda v: v or None` on those two legacy aliases (see
[7.3](#73-resolution-precedence)). Negative values remain rejected in both
forms.

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
startup. Call sites read tunables via the nested namespace, e.g.
`self.config.dom.temperature_poll_interval` and `self.config.cmis_mgr.enabled`.
`main()` no longer parses or forwards the `dom_*`, `--skip_cmis_mgr`,
`--enable_sff_mgr`, or `--skip_cpo_mgr` flags.

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

1. Add one field (with default) to the relevant schema - the daemon schema for a
   top-level tunable, or the subsection schema for one that belongs to a group.
2. Add one `FIELD_SPECS` entry declaring its type coercion and valid range.
3. Read it via `self.config.<field>` (or `self.config.<subsection>.<field>`)
   where needed.

No template, `argparse`, or constructor-signature change is required. Platform
owners set the value in the section they already maintain.

### 7.9. Adopting the mechanism in another pmon daemon

A daemon adopts the mechanism by declaring a schema; it inherits all resolution,
coercion, validation, and error handling. Using `thermalctld`'s existing
tunables as a worked example:

```python
@dataclass
class ThermalMonitorConfig(PmonDaemonConfig):
    SECTION_NAME = 'thermal_monitor'
    FIELD_SPECS = {
        'initial_interval':         FieldSpec(caster=int, minimum=0, maximum=86400),
        'update_interval':          FieldSpec(caster=int, minimum=0, maximum=86400),
        'update_elapsed_threshold': FieldSpec(caster=int, minimum=0, maximum=86400),
    }
    initial_interval: Optional[int] = 5
    update_interval: Optional[int] = 60
    update_elapsed_threshold: Optional[int] = 30


@dataclass
class LiquidCoolingConfig(PmonDaemonConfig):
    SECTION_NAME = 'liquid_cooling'
    FIELD_SPECS = {
        'enabled':         FieldSpec(caster=to_bool),
        'update_interval': FieldSpec(caster=float, minimum=0, maximum=86400),
    }
    enabled: Optional[bool] = False
    update_interval: Optional[float] = 0.5


@dataclass
class ThermalctldConfig(PmonDaemonConfig):
    SECTION_NAME = 'thermalctld'
    SUBSECTIONS = {
        'thermal_monitor': ThermalMonitorConfig,
        'liquid_cooling':  LiquidCoolingConfig,
    }
    LEGACY_ALIASES = {
        'thermal_monitor_initial_interval':         LegacyAlias('thermal_monitor.initial_interval'),
        'thermal_monitor_update_interval':          LegacyAlias('thermal_monitor.update_interval'),
        'thermal_monitor_update_elapsed_threshold': LegacyAlias('thermal_monitor.update_elapsed_threshold'),
        'enable_liquid_cooling':                    LegacyAlias('liquid_cooling.enabled'),
        'liquid_cooling_update_interval':           LegacyAlias('liquid_cooling.update_interval'),
    }

    thermal_monitor: ThermalMonitorConfig = field(default_factory=ThermalMonitorConfig)
    liquid_cooling:  LiquidCoolingConfig = field(default_factory=LiquidCoolingConfig)
```

The `thermal_monitor` defaults (`5`/`60`/`30`) and `liquid_cooling` defaults
(`enabled=False`, `update_interval=0.5`) match `thermalctld`'s current `argparse`
defaults; the schema is illustrative and its migration is a separate change. It
replaces five `argparse` arguments, five constructor parameters, and roughly
twenty lines of conditional Jinja in `docker-pmon.supervisord.conf.j2`, with the
old flat keys retained as legacy aliases. The equivalent applies to `psud`,
`ledd`, and `syseepromd` as they acquire tunables.

The matching `pmon_daemon_control.json` section a platform owner would write is
(illustrative, mirroring the schema above; `thermalctld`'s migration is a
separate change):

```json
{
    "skip_thermalctld": false,
    "thermalctld": {
        "thermal_monitor": { "initial_interval": 5, "update_interval": 60, "update_elapsed_threshold": 30 },
        "liquid_cooling":  { "enabled": false, "update_interval": 0.5 }
    }
}
```

`skip_thermalctld` stays top-level (pmon orchestration; see
[9.3](#93-top-level-keys-versus-the-daemon-section)) while the nested
`thermalctld` object is what `ThermalctldConfig.resolve()` reads.

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
- `--skip_cmis_mgr`
- `--enable_sff_mgr`
- `--skip_cpo_mgr`

The manager toggles that the last three flags carried now live in the `xcvrd`
section as `cmis_mgr.enabled` / `sff_mgr.enabled` / `cpo_mgr.enabled`. The
top-level `skip_xcvrd_cmis_mgr` / `enable_xcvrd_sff_mgr` keys are retained as
deprecated legacy aliases for a compatibility window; see
[9.3](#93-top-level-keys-versus-the-daemon-section) for which keys live where and
why.

Other daemons' flags (e.g. `thermalctld`'s `--thermal-monitor-*` and
`--*liquid_cooling*`) are **unchanged** by this design; they are removed only
when those daemons adopt `PmonDaemonConfig` in their own changes.

Backwards compatibility note (per template guidance): the removed flags were
emitted only by `docker-pmon.supervisord.conf.j2`, which is updated in the same
change to stop emitting them. Every supported platform configures `xcvrd`
through this template, so there is no in-tree caller that passes the removed
flags. Platforms that already set the flat `dom_temperature_poll_interval` /
`dom_update_interval` keys (or the top-level `skip_xcvrd_cmis_mgr` /
`enable_xcvrd_sff_mgr` keys) continue to work unchanged: the resolver honors them
as legacy aliases for a compatibility window, with a deprecation warning, until
platform files migrate to the nested form. A flat interval of `0` continues to
select the built-in default, matching the old truthy-gated template; only the new
nested form reads `0` as continuous polling (see
[7.5](#75-tunable-reference-types-ranges-defaults)). The one intentional behavior
change is that an out-of-range value (e.g. a negative interval) is now rejected
in favor of the built-in default and logged, instead of reaching the polling
threads; see [7.4](#74-merge-coercion-and-validation).

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

For `xcvrd` the template reads four top-level keys today. The two structural ones
stay top-level; the two manager toggles move into the `xcvrd` section:

| Top-level key today | Effect | Under this design |
|---------------------|--------|-------------------|
| `skip_xcvrd` | Whether the `[program:xcvrd]` block is emitted at all | **Stays top-level.** Consumed before the process exists; a daemon cannot decline to start itself. |
| `delay_xcvrd` | Wraps the command in `bash -c "sleep 30 && ..."` | **Stays top-level.** Changes how supervisord launches the process, which the process cannot do for itself. |
| `skip_xcvrd_cmis_mgr` | Emits `--skip_cmis_mgr` | **Moves** to `xcvrd.cmis_mgr.enabled` (inverted). Retained as a deprecated `scope='file'` legacy alias for a compatibility window. |
| `enable_xcvrd_sff_mgr` | Emits `--enable_sff_mgr` | **Moves** to `xcvrd.sff_mgr.enabled`. Retained as a deprecated `scope='file'` legacy alias for a compatibility window. |

The first two are structural: they gate and shape process startup, so they
belong to whoever writes the supervisord config and are outside the reach of any
daemon-side resolver.

The two manager toggles are daemon-side runtime settings - `xcvrd` is already
running when it reads them - so they belong in the `xcvrd` section as `bool`
fields with the `to_bool` caster, alongside the new `cpo_mgr.enabled` (which has
no prior top-level key, since the template never emitted `--skip_cpo_mgr`). To
avoid a flag-day break for platforms that set the old top-level keys, the
resolver honors them as `scope='file'` legacy aliases: when the nested form is
absent, the old key still takes effect and logs a one-time deprecation warning;
when both are present, the nested form wins. `skip_xcvrd_cmis_mgr` inverts to
`cmis_mgr.enabled` via the alias `transform`. The compatibility window before the
aliases are removed is tracked in [section 14](#14-openaction-items---if-any).

A platform owner writes the two structural keys at top level and the daemon's
own runtime settings inside the nested `xcvrd` object:

```json
{
    "skip_xcvrd": false,
    "xcvrd": {
        "dom":      { "temperature_poll_interval": 60, "update_interval": 60 },
        "cmis_mgr": { "enabled": true },
        "sff_mgr":  { "enabled": false },
        "cpo_mgr":  { "enabled": true }
    }
}
```

The deprecated form below remains valid for the compatibility window: the
top-level `skip_xcvrd_cmis_mgr` / `enable_xcvrd_sff_mgr` keys are honored as
`scope='file'` aliases and the flat `dom_*` keys as `scope='section'` aliases,
each logging a one-time deprecation warning. When both forms are present the
nested form wins.

```json
{
    "skip_xcvrd": false,
    "skip_xcvrd_cmis_mgr": false,
    "enable_xcvrd_sff_mgr": false,
    "xcvrd": { "dom_temperature_poll_interval": 60, "dom_update_interval": 60 }
}
```

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
`dom.temperature_poll_interval` is `None`).

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
- Subsections are limited to **exactly one level deep** by design;
  `__init_subclass__` rejects a subsection schema that declares its own
  subsections. Deeper nesting is intentionally not supported.
- The legacy flat and top-level aliases (`dom_*`, `skip_xcvrd_cmis_mgr`,
  `enable_xcvrd_sff_mgr`) are transitional. They are honored with a deprecation
  warning only for a compatibility window and are removed once platform files
  migrate to the nested form; see [section 14](#14-openaction-items---if-any).

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
- `to_bool` accepts `true`/`false`/`yes`/`no`/`on`/`off`/`1`/`0` in either case
  (plus real booleans and the integers `0`/`1`) and rejects other strings (in
  particular, `"false"` resolves to `False`, not `True`).
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
- A subsection value is merged, coerced, and range-validated against the
  subsection's own `FIELD_SPECS`; a partial subsection dict leaves the
  subsection's other fields at their defaults.
- A non-dict value for a subsection key is rejected and the subsection keeps its
  defaults; unknown keys inside a subsection are ignored.
- Schema guard: a `SUBSECTIONS` value that is not a `PmonDaemonConfig` subclass,
  a subsection schema that itself declares `SUBSECTIONS`, and a field appearing
  in both `FIELD_SPECS` and `SUBSECTIONS` each raise at class definition.
- Legacy aliases: a `scope='section'` alias routes a flat key to its nested
  target; a `scope='file'` alias routes a top-level key; a `transform` (e.g.
  `skip_* -> enabled` inversion) is applied; the nested key wins when both the
  alias and the nested form are present; using an alias logs a deprecation
  notice.
- File location: platform file used when no hwsku file; hwsku file takes
  precedence over platform file; hwsku file present but lacking the daemon's
  section does not fall back to the platform file.
- No section, malformed JSON, non-dict section, an empty directory path entry,
  and a `device_info` failure all degrade to defaults.

`xcvrd` schema tests in `tests/test_xcvrd_config.py`:

- Bare `XcvrdConfig()` construction yields the documented defaults: `None` for
  both `dom` fields, `cmis_mgr.enabled=True`, `sff_mgr.enabled=False`,
  `cpo_mgr.enabled=True`.
- A nested `dom` section overrides `dom.temperature_poll_interval` /
  `dom.update_interval`.
- The value `0` is preserved for both `dom` fields in the nested form
  (meaningful: continuous polling).
- A legacy flat `dom_update_interval: 0` / `dom_temperature_poll_interval: 0`
  instead resolves to the built-in default (parity with the removed
  truthy-gated template), while the nested form's `0` is preserved; a legacy
  flat string `"0"` faithfully inherits the template's quirk of being treated as
  truthy.
- A negative `dom.temperature_poll_interval` and a negative `dom.update_interval`
  are each rejected and the default is kept - the case that previously reached
  `DomThermalInfoUpdateTask` and produced an undelayed poll loop.
- A value above the documented maximum is rejected for both `dom` fields.
- `86400` and `0` are accepted for both `dom` fields (inclusive boundaries).
- The `cmis_mgr` / `sff_mgr` / `cpo_mgr` `enabled` flags parse via `to_bool`
  (including `"false"` -> `False`) and keep their defaults when unset.
- Legacy aliases: flat `dom_update_interval` resolves to `dom.update_interval`;
  top-level `skip_xcvrd_cmis_mgr: true` resolves to `cmis_mgr.enabled=False`
  (inverted); `enable_xcvrd_sff_mgr: true` resolves to `sff_mgr.enabled=True`;
  the nested form wins when both are present; each alias logs a deprecation
  notice.
- End-to-end `resolve()` reads from disk and applies defaults when nothing is on
  disk.

Wiring tests in `tests/test_xcvrd.py`:

- `DaemonXcvrd.__init__` populates `self.config` from `XcvrdConfig.resolve()`.
- With no platform overrides, `self.config.dom` tunables fall back to `None`
  defaults and the manager toggles keep their built-in defaults.
- With a rejected (out-of-range) `dom.temperature_poll_interval`, the DOM thermal
  poll thread is not started, matching the `None` default.

All `sonic-xcvrd` unit tests pass (full suite green) and the new modules are
covered at 100%.

### 13.2. System Test cases

- On a platform whose `pmon_daemon_control.json` `xcvrd` section sets
  `dom.temperature_poll_interval`, verify the DOM thermal poll thread starts and
  polls at the configured interval (e.g. STATE_DB DOM updates observed at the
  expected cadence).
- On a platform whose section sets `dom.update_interval`, verify DOM info
  updates occur at the configured interval.
- On a platform whose section sets `cmis_mgr.enabled: false`, verify the CMIS
  task manager does not start; with `sff_mgr.enabled: true`, verify the SFF task
  manager does start.
- On a platform with no `xcvrd` section, verify `xcvrd` starts cleanly on
  built-in defaults.
- With an out-of-range value configured (e.g. `dom.update_interval: -60`),
  verify `xcvrd` starts, logs a warning naming the field and expected range, and
  runs on the built-in default cadence.
- Regression: confirm existing platforms setting the legacy flat keys
  (`dom_temperature_poll_interval` / `dom_update_interval`) or the top-level
  `skip_xcvrd_cmis_mgr` / `enable_xcvrd_sff_mgr` keys behave identically to the
  prior flag-based path and log a deprecation warning.

## 14. Open/Action items - if any

- **Upper bounds.** The `86400`-second maximum on the `dom_*` intervals is a
  units-typo guard rather than a functional limit. Confirm the value, or decide
  that these fields should be bounded below only.
- **`DaemonBase` integration.** Whether to add a thin convenience hook (e.g.
  `DaemonBase.load_config(config_cls)`) once a second daemon has adopted
  `PmonDaemonConfig`, so the resolve call is not repeated in each daemon's
  `__init__`.
- **Legacy alias compatibility window.** How long the deprecated flat keys
  (`dom_temperature_poll_interval`, `dom_update_interval`) and top-level manager
  keys (`skip_xcvrd_cmis_mgr`, `enable_xcvrd_sff_mgr`) are honored before
  removal, and whether the template should emit a one-time migration warning. The
  manager toggles now live under the `xcvrd` section as `cmis_mgr.enabled` /
  `sff_mgr.enabled`; see [9.3](#93-top-level-keys-versus-the-daemon-section).
- **Migration order.** Which daemon migrates next. `thermalctld` is the largest
  beneficiary (five tunables, ~20 lines of template Jinja) and is the natural
  second adopter; sequencing is for its maintainers.
- **Config DB override layer.** Whether to introduce per-daemon Config DB tables
  as a higher-precedence, operator-facing override layer (would enable runtime
  reconfiguration). Out of scope for this design.
