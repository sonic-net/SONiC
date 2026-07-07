# Device Local Diagnosis Rules Schema HLD

## Table of Contents

1. [Introduction](#introduction)
2. [Document Authority](#document-authority)
3. [Definitions](#definitions)
4. [Requirements](#requirements)
5. [Schema Versioning](#schema-versioning)
6. [Rule Structure](#rule-structure)
7. [Abstract Rule Data Source Extensions](#abstract-rule-data-source-extensions---vendor-extensible)
8. [Rule Examples](#rule-examples)
9. [Schema Validation](#schema-validation)
10. [Backward Compatibility](#backward-compatibility)

## Introduction

This document defines the schema and structure for vendor rules consumed by the Device Local Diagnosis Daemon (DLDD) running on SONiC switches. The rules schema provides a standardized, extensible format for defining fault detection signatures that can be consumed by DLDD.

The schema is designed to be:
- **Flexible**: Support multiple data sources (i2c, Redis, platform APIs, CLI, files, etc.)
- **Versioned**: Enable and track schema modifications
- **Extensible**: Allow for new fault types and detection methods
- **Standardized**: Provide a common format for rule definitions regardless of underlying SW
- **Hardware-agnostic**: Allow for hardware abstraction through data source extension (DSE) layers

## Document Authority

This document is the sole HLD authority for the DLDD vendor rules wire contract, schema versioning, Pydantic validation and error isolation, DSE authoring contract, generated authoring artifacts, and schema-to-runtime translation semantics. The companion `device-local-diagnosis-daemon.md` is the sole authority for SONiC runtime architecture, scheduling, fault lifecycle, telemetry storage, operations, and implementation locations. The generated Draft 2020-12 JSON Schema is a derivative authoring artifact; it is neither an HLD nor a runtime validation authority.

## Definitions

| Term | Definition |
|------|------------|
| **Schema Version** | Version identifier for the rules structure format |
| **Signature** | A complete fault detection rule with metadata, conditions, and actions |
| **Event** | A specific data collection and evaluation point within a signature |
| **Data Source Extension (DSE)** | Translation layer between abstract rule definitions and hardware/software specific implementation |
| **Abstract Rule** | Rule using DSE identifiers resolved by the trusted installed `DSERegistry`; any backing data file is vendor-owned and optional |
| **Direct Rule** | Rule with explicit hardware-specific paths, bypassing the DSE layer |

## Requirements

### Functional Requirements
- Support multiple SW versions and hardware revisions within a single schema
- Support both abstract (DSE) and direct rule definitions
- Enable fault correlation across multiple events and conditions
- Schema must be human-readable and maintainable
- Schema evolution must maintain backward compatibility with existing implementations wherever possible. Changes that violate this must modify schema major version as defined below.

## Schema Versioning

### Version Format
The schema version follows semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Non-backward compatible changes requiring modification of the on-device component
- **MINOR**: Backward compatible additions such as new optional fields or evaluator/source types that are advertised as supported by the consuming daemon
- **PATCH**: Minor corrections and clarifications

### Version Header
Every rules source root object must contain a scalar schema version declaration (mapping-key order is not significant):

```yaml
schema_version: "0.0.1"
```

**CRITICAL**: The field name and scalar value form are immutable entry points for schema interpretation.

### Versioning and Compatibility with SONiC NOS

Schema versions evolve independently from SONiC releases. A DLDD release may support multiple schema versions, but runtime support is determined only through an exact-match registry of installed Pydantic contracts packaged with the daemon.

Semantic versioning describes how schema authors classify changes; it does not authorize runtime version-range matching. A rules source declaring `0.0.2` is accepted only when `0.0.2` has an explicit registry entry. A registry entry may deliberately reuse another version's models or DTO-to-domain converter, but DLDD must not infer compatibility or silently select the nearest major, minor, or patch version.

An uploaded rules source selects a contract only through its scalar `schema_version`. It cannot supply a schema path, module name, URI, validator, or materializer. The exact-version Pydantic contract and its explicit DTO-to-domain converter define extraction and interpretation.

Unknown-field behavior is defined independently by each registered schema contract. Core DLDD objects reject unknown fields. Explicit vendor extension envelopes may accept and preserve bounded JSON-compatible vendor fields after the installed platform advertises the extension type. Unknown types, enum values, required fields, or behavior-bearing fields outside those extension points fail validation for the scope in which they occur.

Schema `0.0.1` is a pre-release contract and already incorporates the authoritative Pydantic model, optional per-event `sampling_interval`, and optional bounded `async` collection behavior described below. Those changes do not require compatibility shims before the first release. After release, behavior for an exact version is immutable; a behavioral change requires a new explicit schema version and registry entry.

## Rule Structure
At the highest level, a rules source file contains a `schema_version`, an optional rules-source default for local action timeouts, and a non-empty `signatures` list. Each `signature` contains 3 primary sections: `metadata`, `conditions`, and `actions`. A breakdown of the content of each of these can be found below.

### Canonical File Structure

```yaml
schema_version: "0.0.1"
local_action_default_timeout: 300

signatures:
  - signature:
      metadata:
        # Signature Metadata section
      conditions:
        # Condition Logic and Event Definition sections
      actions:
        # Action Specification section
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | String | Yes | Schema version used to interpret the rules file |
| `local_action_default_timeout` | Integer | Conditional | Rules-source default timeout in seconds for local actions that omit per-action `timeout`. Required when any local action omits `timeout`; optional when every local action declares its own timeout. Strict integer 1-4294967295; explicit `null` is invalid. |
| `signatures` | List | Yes | 1-1024 signature objects |
| `signatures[*].signature.metadata` | Object | Yes | Rule metadata |
| `signatures[*].signature.conditions` | Object | Yes | Rule condition logic and events |
| `signatures[*].signature.actions` | Object | Yes | Repair actions and optional diagnostic log collection |

### Signature Metadata
Each signature contains comprehensive metadata for identification and applicability. Every field serves a specific purpose in rule processing and system integration:

- **Severity Ordering**: The `severity` field encodes DLDD rule severity (`CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN`). Higher severity signatures always take precedence when multiple rules target the same component/symptom pair. This field is DLDD/SONiC diagnostic metadata; it is not a native OpenConfig Healthz fault leaf.
- **Priority Tiebreaker**: The optional `priority` field provides deterministic ordering for rules that share the same severity and symptom. Lower numeric values indicate higher priority; when omitted, Pydantic validation/domain conversion applies `5`.

```yaml
signature:
  metadata:
    name: "PSU_OV_FAULT"                    # Required: Unique string identifier for the rule
    id: 1000001                             # Required: Unique numeric ID for cross-referencing
    version: "1.0.0"                        # Required: Semantic version for rule tracking
    description: |                          # Required: Human-readable fault explanation
      An over voltage fault has occurred on the output feed from the PSU to the chassis.
      This condition indicates potential hardware failure requiring immediate attention.
    product_ids:                            # Required: List of compatible hardware products
      - "8122-64EHF-O P1"                   # Product ID with hardware revision
      - "8122-64EHF-O P2"                   # Multiple products can share the same rule
    sw_versions:                           # Required: List of compatible software versions
      - "202311.3.0.1"                      # Specific software version where rule is validated
      - "202311.3.0.2"                      # Additional compatible versions
    component: "PSU"                        # Required: Component type affected by fault
    symptom: "SYMPTOM_OVER_THRESHOLD"       # Required: Supported OpenConfig Healthz symptom
    error_type: "POWER"                     # Required: High-level OpenConfig-aligned error category where available
    severity: "CRITICAL"                    # Required: DLDD rule severity enumeration
    priority: 1                             # Optional: Numeric priority to account for rule ordering (default is 5 when omitted)
    tags:                                   # Optional: Classification tags for filtering, below is just an example
      - "power"                             # Functional category tag
      - "voltage"                           # Specific fault type tag
```

#### Metadata Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `name` | String | Yes | Unique, non-empty human-readable identifier for the rule | `^[A-Za-z0-9_]+$` | `"PSU_OV_FAULT"` |
| `id` | Integer | Yes | Unique numeric identifier for programmatic reference | 1000000-9999999 | `1000001` |
| `version` | String | Yes | Decimal `MAJOR.MINOR.PATCH` triplet; prerelease/build suffixes are not accepted in schema `0.0.1` | `^[0-9]+\.[0-9]+\.[0-9]+$` | `"1.0.0"` |
| `description` | String | Yes | Non-empty, human-readable explanation of the fault condition | Plain text; may use a YAML literal block | See example above |
| `product_ids` | List | Yes | Non-empty list of non-empty hardware product identifiers where this rule applies | Product/revision formatting is vendor EEPROM dependent | `["8122-64EHF-O P1"]` |
| `sw_versions` | List | Yes | Non-empty list of non-empty software version identifiers where this rule is validated | Formatting is NOS/vendor dependent | `["202311.3.0.1"]` |
| `component` | String | Yes | Primary vendor/platform component type affected. DLDD preserves the identity and does not maintain a component-type allowlist. | Any non-empty vendor-defined component type string | `"PSU"`, `"VENDOR_FABRIC_MODULE"` |
| `symptom` | String | Yes | Supported OpenConfig Healthz fault symptom published to telemetry | `SYMPTOM_OVER_THRESHOLD`, `SYMPTOM_UNDER_THRESHOLD`, `SYMPTOM_MEMORY_ERRORS`, `SYMPTOM_MISSING_COMPONENT`, `SYMPTOM_COMM_ERROR`, `SYMPTOM_UNKNOWN` | `"SYMPTOM_OVER_THRESHOLD"` |
| `error_type` | String | Yes | Non-empty high-level fault category published to `FAULT_INFO.error_type`. Values should be OpenConfig-aligned where available; otherwise vendors use a stable category that UMF can translate or preserve consistently. | Any non-empty string | `"POWER"` |
| `severity` | String | Yes | DLDD rule severity used for deterministic precedence and optional SONiC/alarm metadata | `CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN` | `"CRITICAL"` |
| `priority` | Integer | No | Numeric priority for rules with matching severity and symptom (lower value = higher priority, default = 5 when omitted) | Strict integer 0-4294967295 | `5` |
| `tags` | List | No | Categorization tags for filtering and organization; omission defaults to an empty list | List of non-empty strings | `["power", "voltage"]` |

### Condition Logic
Conditions define the logical evaluation framework for determining when a fault has occurred. This section controls how multiple positive fault events are correlated and evaluated. Each event is expected to describe an active failing behavior; the signature logic combines those active event matches.

```yaml
conditions:
  logic: "1 AND 2"                         # Required: Boolean expression referencing event IDs
  logic_lookback_time: 60                  # Required: Time window for event correlation (seconds)
  events:                                  # Required: List of individual detection events
    - event:
        id: 1                            # Required: Unique identifier within this signature
        # ... event definition
    - event:
        id: 2                            # Required: Must be unique within signature
        # ... event definition
```

#### Condition Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `logic` | String | Yes | Boolean expression defining how active fault events are combined; bounded to 16,384 characters, 4,096 tokens, and nesting depth 64 | Boolean operators: `AND`, `OR` with event IDs | `"1 AND 2"`, `"1 OR (2 AND 3)"` |
| `logic_lookback_time` | Integer | Yes | Maximum age in seconds between active event matches used for logic correlation. Zero disables match-age filtering and evaluates only the current active/clear state of each event. | 0-86400 (0=current active state, 86400=24 hours) | `60` (1 minute window) |
| `events` | List | Yes | Array of event definitions that can trigger the fault | 1-1000 events | See Event Definition below |

#### Logic Expression Rules
- **Event References**: Use numeric IDs that match event `id` fields. Each referenced event represents a positive fault predicate.
- **Operators**: `AND`, `OR` (case sensitive)
- **Precedence**: `AND` binds more tightly than `OR`; parentheses override precedence. For example, `"1 OR 2 AND 3"` means `"1 OR (2 AND 3)"`.
- **Simple Cases**: Single event: `"1"`, Multiple events: `"1 AND 2"`
- **Time Correlation**: When `logic_lookback_time` is greater than zero, the events that make the boolean expression true must have active matches within that many seconds of the newest event time. For `OR`, only the satisfied branch must meet the window; unsatisfied branches are not required to produce matches. When `logic_lookback_time` is zero, DLDD applies no historical age window: every event that is currently in its active failing state remains true until valid clear evidence makes it false. Thus, if event 2 became active five minutes ago and remains active, event 1 becoming active now immediately satisfies `1 AND 2`. The events do not need matching transition timestamps. Each event's own `match_count` and `match_period` semantics still apply before its current truth value participates in signature logic.
- **No Negated Events**: `NOT` is not part of schema version `0.0.1`. If an absent, inactive, or false component state is itself a fault, model that as an explicit event whose evaluator positively matches the failing state.
- **Instance Correlation**: Signature logic is evaluated per resolved diagnosis instance. Explicit `instances` entries and DSE selectors that expand to component instances both create instanced events. Events that do not carry explicit or implicit instances are treated as common predicates that apply to every resolved instance of the signature.

#### Instance Resolution and Correlation

When one or more events define explicit `instances`, or when a DSE selector expands to component instances, DLDD expands the signature into per-instance evaluation groups before applying `conditions.logic`.

- Each `instances` entry names the affected component instance and may also carry a source binding using the `DeviceName:PathIdentifier` form.
- A DSE selector with a wildcard, such as `{psu*}`, is an implicit instance source within the signature's `metadata.component` scope. The vendor DSE resolver must return the component instance identity with each expanded operation so DLDD can correlate the event per instance.
- Events that resolve to the same component instance are correlated with each other for that instance only.
- Events without explicit `instances` and without a DSE-resolved instance identity are global/common predicates for the signature. Their current match state is available to each per-instance evaluation group.
- List-valued direct paths that accompany `instances`, such as an I2C `bus` list, are interpreted positionally unless a DSE resolver supplies a more explicit mapping. The number of positional path entries must match the number of instances for that field.

Example: for `logic: "1 AND 2 AND 3"`, if events 1 and 2 are instanced for `PSU0` and `PSU1`, while event 3 is not instanced, DLDD evaluates:
- `event1[PSU0] AND event2[PSU0] AND event3`
- `event1[PSU1] AND event2[PSU1] AND event3`

DLDD must not satisfy a per-instance expression by combining event matches from different component instances, such as `event1[PSU0]` with `event2[PSU1]`.

### Event Definition
Events specify individual data collection points and their evaluation criteria. Each event represents a specific positive check for failing behavior that can contribute to fault detection:

```yaml
event:
  id: 1                                    # Required: Unique identifier within signature
  type: "i2c"                             # Required: Data source type
  instances: ['PSU0:IO-MUX-6', 'PSU1:IO-MUX-7'] # Optional: Device instance DSE
  path:                                   # Required: Data source specification (varies by type)
    bus: ['IO-MUX-6', 'IO-MUX-7']        # I2C bus names (resolver notation)
    chip_addr: '0x58'                     # I2C chip address (hex format)
    i2c_type: 'get'                       # Direct I2C sampling is read-only; only 'get' is valid
    command: '0x7A'                       # I2C register/command (hex format)
    size: 'b'                             # Data size (b=byte, w=word, l=long)
    scaling: 'N/A'                        # Optional: Value scaling factor
  evaluation:                             # Required: Fault detection criteria
    type: 'mask'                          # Evaluation method
    logic: '&'                            # Logical operation for mask
    value: "0b10000000"                   # Comparison value (binary string)
  sampling_interval: 60                   # Optional: Normal sampling cadence in seconds
  async: true                             # Optional: Collect/evaluate in shared worker pool
  match_count: 1                          # Required: Number of matches needed
  match_period: 0                         # Required: Time window for matches (seconds)
```

#### Event Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `id` | Integer | Yes | Unique identifier within the signature | 1-999 (unique per signature) | `1` |
| `type` | String | Yes | Data source type determining path structure. The authoritative enum set is defined in Canonical Values and Extensible Identities. | See Canonical Values and Extensible Identities | `"i2c"` |
| `instances` | List | No | Non-empty list of device instances used for per-instance correlation and optional source binding. Component prefixes before `:` must be unique within the event; explicit `null` is invalid. | Each entry matches `^[^:]+:.*$`; an empty `PathIdentifier` means the event applies to the whole named component | `["PSU0:IO-MUX-6"]` |
| `path` | Object or String | Yes | Data source specification (structure varies by type) | See Path Specifications below | See examples below |
| `evaluation` | Object | Yes | Criteria for determining if fault condition is met | See Evaluation Specifications | See examples below |
| `sampling_interval` | Integer | No | Target interval in seconds between normal collection attempts while the materialized work item is eligible for polling. When omitted, each materialized source inherits the effective polling interval of its assigned monitor. | Strict integer 1-4294967295; explicit `null`, zero, booleans, floats, and numeric strings are invalid | `60` |
| `async` | Boolean | No | When `true`, submit this event's single materialized source collection and evaluation to the shared bounded asynchronous collection pool so a slow operation does not block other due work in the owning monitor. Defaults to `false`. | Strict boolean; explicit `null`, integers, floats, and strings are invalid | `true` |
| `match_count` | Integer | Yes | Number of positive evaluations needed to trigger event | 1-1000 | `1` |
| `match_period` | Integer | Yes | Time window in seconds for accumulating matches. `0` means current-sample state and requires `match_count: 1`. | 0-3600 | `0` |

#### Event Sampling Semantics

`sampling_interval` schedules normal source collection; it does not alter evaluation or correlation semantics. It is independent of `match_period`, `logic_lookback_time`, local-action `wait_period`, operation `timeout`, and `active_fault_recheck_interval`.

When `sampling_interval` is omitted, Pydantic preserves the omission instead of inserting a literal default. During planning, DLDD resolves the effective interval from the assigned monitor: direct Redis events use `redis_monitor_polling_interval`, direct file events use `file_monitor_polling_interval`, and common/vendor/DSE templates use `common_monitor_polling_interval`. Every runtime child of a DSE template retains the template's explicit or inherited cadence relationship. The normal configuration precedence remains CONFIG_DB, then platform defaults, then hardcoded service defaults.

Every eligible work item is immediately due when a new DLDD process or monitor plan starts. Cadence timestamps are process-local and are not restored across restart. After a normal collection attempt, the next attempt is scheduled from monotonic time using the effective interval; missed intervals are coalesced rather than replayed as a catch-up burst. `IN_FLIGHT`, held, suspended, and broken states take precedence over normal cadence, while an eligible primary-requested `RECHECK_ONCE` bypasses the normal interval.

When `async: true`, the due-time decision remains owned by the normal monitor thread, but collection, normalization, and event evaluation for that one materialized work item run as one job in a process-wide bounded pool. DLDD allows only one outstanding job per correlation key. The owning monitor marks the key `COLLECTING`, continues scheduling unrelated work, and later applies the immutable result through its normal result/evidence path; worker threads never mutate monitor state or publish fault evidence directly. The default pool has eight daemon workers and capacity for 256 queued jobs. Eight waiting slots are reserved from normal collection so primary-requested async `RECHECK_ONCE` jobs can still enter a saturated pool. Rechecks are ordered ahead of all waiting normal jobs and FIFO relative to other rechecks; an already running operation is never preempted. If normal capacity is exhausted, the key remains due and is retried without counting a collection attempt or failure.

Async cadence is scheduled from successful job submission. A job that waits or runs past its next nominal interval is not overlapped or replayed because the correlation key remains `COLLECTING`; after completion, the next eligible cycle coalesces the missed intervals into one attempt. `RECHECK_ONCE` uses the same collection mode while bypassing normal cadence and receiving queue priority. `async` does not add a timeout or make an adapter thread-safe: vendors must enable it only for adapters/hooks whose single-item collection is safe for concurrent invocation and whose underlying operation has an appropriate bounded timeout. Omission or `false` retains inline monitor-thread collection.

#### Path Specifications by Type

These path shapes are the wire contract for schema `0.0.1`. A different shape requires a new exact schema contract and registry entry. The authoritative `event.type` set is defined in Canonical Values and Extensible Identities:

| `event.type` | `path` shape | Notes |
|--------------|--------------|-------|
| `i2c` | Object | Direct read-only I2C source definition |
| `redis` | Object | Redis database/table/key/path definition |
| `dse` | String | DSE reference resolved by vendor DSE hook |
| `cli` | Object | CLI argv object executed without a shell |
| `file` | Object | File or glob source definition |
| `sysfs` | Object | Sysfs source definition |
| `platform_api` | String or Object | Vendor/platform API source, typically resolved through DSE |

**I2C Path Structure:**
```yaml
path:
  bus: ['IO-MUX-6', 'IO-MUX-7']          # List of bus names (notation defined by vendor with association to instance, in this case the example is "ACPI_nickname-mux-number")
  chip_addr: '0x58'                       # Hex address of target chip
  i2c_type: 'get'                         # Direct event sampling is read-only; only 'get' is valid
  command: '0x7A'                         # Register/command in hex
  size: 'b'                               # Data size: 'b'(byte), 'w'(word), 'l'(long)
  scaling: 'N/A'                          # Scaling factor or 'N/A'
```

Direct `event.type: i2c` sampling is limited to read operations. I2C writes or read-modify-write operations are not valid monitoring events in schema version `0.0.1`; if a vendor needs write behavior, it must be modeled as a vendor DSE operation or as an explicit `type: i2c` local action where the vendor owns the side-effect contract.

**Redis Path Structure:**
```yaml
path:
  database: 'STATE_DB'                    # Redis database name
  table: 'PSU_INFO'                       # Table name within database
  key: 'PSU_INFO|PSU0'                   # Full key or template
  path: 'value/output_voltage'            # JSON path within value
```

**DSE Path Structure (Abstract):**
```yaml
path: "PSU:get_output_voltage_fault_register()"  # Abstract DSE reference
```

**CLI Path Structure:**
```yaml
path:
  argv: ['/usr/bin/lspci', '-vvnnt']      # Command and arguments executed without a shell
  timeout: 30                            # Optional: Command timeout in seconds
```

CLI paths execute a single command by argv. Shell features such as pipes, glob expansion, redirection, and command substitution are not part of the path schema. Filtering command output is modeled through the event `evaluation` block.

Operational safety for vendor-selected commands, I2C operations, DSE functions, and file/log paths is owned by the vendor rule package. DLDD validation confirms schema shape, supported execution mode, and DSE/evaluator contracts; it does not prove that a vendor-defined diagnostic operation is non-disruptive for the target hardware.

Example CLI output filtering:
```yaml
path:
  argv: ['/usr/bin/lspci', '-vvnnt']
  timeout: 30
evaluation:
  type: 'string'
  operator: 'contains'
  value: 'a008'
  case_sensitive: false
```

**File Path Structure:**
```yaml
path:
  file: "/var/log/platform.log"
  format: "text"
```

The Pydantic path contract requires `file` and `format` to be non-empty strings and permits optional `scaling` and `unit`. During materialization, the built-in file/sysfs adapter supports `text`, `string`, `raw`, `json`, `yaml`, `integer`, `int`, `float`, and `boolean`; another format fails adapter validation for that rule.

**Sysfs Path Structure:**
```yaml
path:
  file: "/sys/class/hwmon/hwmon0/temp1_input"
  format: "integer"
  scaling: 0.001
  unit: "celsius"
```

**Platform API Path Structure:**
```yaml
path: "{psu*}:{get_output_voltage_fault_register()}"
```

Schema `0.0.1` also accepts a hook object for direct platform sources:

```yaml
path:
  hook: "read_vendor_sensor"       # Required non-empty installed hook name
  sensor_class: "power"            # Bounded JSON-compatible vendor option
  channel: ["rail0", "rail1"]     # Positional when instances are declared
```

The object requires `hook`; other members are bounded JSON-compatible vendor options. With `instances`, every list-valued option except `argv` is positional and must have the same length as the instance list.

When an event declares `instances`, any list-valued path field other than an
`argv` command list is positional and must have exactly one element per
instance. This applies to built-in I2C lists and to list-valued fields in a
`platform_api` vendor hook envelope; mismatches are rule-level validation
errors rather than runtime indexing failures.

Direct platform API access is expected to be vendor-defined. DSE is the preferred abstraction for platform APIs because it lets vendors bind symbolic rule references to platform object methods and hardware-specific implementation details.

#### Evaluation Specifications

**Mask Evaluation (Bitwise Operations):**
```yaml
evaluation:
  type: 'mask'                            # Evaluation method
  logic: '&'                              # Bitwise operator. Direct mask events use '&' in schema version 0.0.1
  value: "0b10000000"                     # Mask value (binary string)
```

**Comparison Evaluation:**
```yaml
evaluation:
  type: 'comparison'                      # Evaluation method
  operator: '>'                           # Comparison: '>', '<', '>=', '<=', '==', '!='
  value: 50.0                             # Comparison value
  unit: 'celsius'                         # Optional: Value unit
```

**String Match Evaluation:**
```yaml
evaluation:
  type: 'string'                          # Evaluation method
  operator: 'contains'                    # String operation: 'contains', 'equals', 'regex'
  value: 'error'                         # Search string or regex pattern
  case_sensitive: false                   # Optional: Case sensitivity
```

`case_sensitive` defaults to `true` when omitted.

**Boolean Evaluation:**
```yaml
evaluation:
  type: 'boolean'                         # Evaluation method
  value: true                            # Expected boolean value
```

**DSE Evaluation:**
```yaml
evaluation:
  type: 'dse'                             # Evaluation method resolved through DSE
  operator: 'equals'                      # Optional: Operator applied by DLDD when the DSE returns a value
  value: "{psu*}:{get_output_voltage_failure_value()}" # DSE reference that resolves to expected value or expression input
```

DSE can be used both as a data source path (`event.type: dse`) and as an evaluation type (`evaluation.type: dse`). A DSE evaluation is vendor extensible: the vendor hook resolves the rule reference to a trusted evaluator handle during activation, and the monitor invokes that handle for the current binding at every event sample.

When `operator` is present, DLDD applies the named operator to the event value and the value returned by the DSE evaluator handle for that sample. This allows rules to use DSE for dynamic value resolution while keeping comparison semantics visible in the rule.

When `operator` is omitted, the DSE evaluator handle must return a complete comparator/evaluator contract. Handle resolution is the activation gate; because activation never invokes the handle, a malformed runtime return is reported as an isolated evaluator failure rather than an activation-time schema result.

For schema version `0.0.1`, a DSE evaluation with `operator` uses the same normalized comparison vocabulary as other DLDD evaluators. `equals` is accepted as the readable alias for `==`, and `not_equals` is accepted as the readable alias for `!=`.

#### Evaluation Field Requirements

| Evaluation Type | Required Fields | Optional Fields | Truth Semantics |
|-----------------|-----------------|-----------------|-----------------|
| `mask` | `type`, `logic`, `value` | `value_configs` | Applies bitwise `&` to the collected value and configured mask. A match is true when `(collected_value & value) == value`. Other bitwise comparison forms should be modeled through a DSE evaluator in schema version `0.0.1`. |
| `comparison` | `type`, `operator`, `value` | `unit`, `value_configs` | Applies numeric/string comparison using `>`, `<`, `>=`, `<=`, `==`, or `!=`. |
| `string` | `type`, `operator`, `value` | `case_sensitive`, `value_configs` | Applies `contains`, `equals`, or `regex` to the collected string. |
| `boolean` | `type`, `value` | `value_configs` | Matches when the collected boolean equals `value`. |
| `dse` | `type`, `value` | `operator`, `value_configs` | If `operator` is present, DLDD applies it to the collected event value and DSE-resolved `value`. If omitted, the DSE hook supplies the complete comparator/evaluator contract. DSE may also supply value metadata implicitly. |

Binary values should be represented as quoted strings such as `"0b10000000"` to avoid YAML loader ambiguity.

#### Value Configuration Metadata

In schema `0.0.1`, `value_configs` is an optional member of an `evaluation` object; it is not valid on arbitrary rule fields. It describes how the evaluated value should be represented in diagnostics and UMF translation. DLDD always publishes value metadata for fault events. If the rule and resolved source do not supply more specific metadata, runtime telemetry uses the `N/A` defaults below.

```yaml
value_configs:
  type: "binary"                          # Required: binary, hex, int, float, string, boolean, json, bytes, or N/A
  unit: "N/A"                             # Required: unit string or "N/A"
  scaling: "N/A"                          # Optional: numeric scale factor or "N/A"
  encoding: "N/A"                         # Optional: text/binary encoding hint or "N/A"
```

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `type` | String | Yes | Representation type used for telemetry and optional value parsing. Values are defined in Canonical Values and Extensible Identities. | `"binary"`, `"int"`, `"float"` |
| `unit` | String | Yes | Measurement unit or `"N/A"` when no unit applies | `"celsius"`, `"rpm"`, `"N/A"` |
| `scaling` | Number or String | No | Scaling factor applied to raw values, or `"N/A"` | `0.001`, `"N/A"` |
| `encoding` | String | No | Encoding hint for string or byte values, or `"N/A"` | `"utf-8"`, `"N/A"` |

When DLDD generates default metadata, it uses `type: "N/A"`, `unit: "N/A"`, `scaling: "N/A"`, and `encoding: "N/A"` unless the adapter or DSE provides a more specific value.

### Action Specification
Actions define the response procedures when a fault is detected. This section specifies both immediate local remediation and escalating remote actions:

```yaml
actions:
  repair_actions:
    local_actions:                        # Optional: Actions scheduled asynchronously by DLDD
      wait_period: 60                     # Required if local_actions: Nonblocking wait before secondary check and further escalation (seconds)
      action_list:                        # Required if local_actions: Vendor defined method calls to execute on action worker context
        - action: 
            type: 'dse'
            command: 'PSU:reset_output_power()'
            timeout: 120
        - action: 
            type: 'dse'
            command: 'PSU:clear_faults()'
            timeout: 120
    remote_actions:                       # Required: Actions for remote controller
      action_list:                        # Required: Escalating sequence of actions
        - ACTION_RESEAT                   # First action: Remove and reinsert the component (if possible)
        - ACTION_COLD_REBOOT              # Second action: System reboot
        - ACTION_POWER_CYCLE              # Third action: Power cycle
        - ACTION_FACTORY_RESET            # Fourth action: Full software reimage
        - ACTION_REPLACE                  # Final action: Return material authorization
      time_window: 86400                  # Required: Duration controller tracks fault history for escalation (seconds)
  log_collection:                         # Optional: Diagnostic data to collect on fault
    logs:                                 # Optional: Static log files to capture
      - log: "/var/log/platform.log"      # Log file path
      - log: "/var/log/syslog"            # System log path
    queries:                              # Optional: Dynamic data collection commands
      - query:
          type: "dse"            # Query type
          command: "PSU:get_status()"      # Platform API method to call
      - query:
          type: "cli"                     # CLI command type
          argv: ["/usr/local/bin/show", "platform", "psu"] # CLI argv to execute without a shell
          timeout: 60
```

#### Action Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `repair_actions` | Object | Yes | Container for all local and remote remedial actions | See subfields below | See example above |
| `log_collection` | Object | No | Diagnostic data collection specification. If omitted, DLDD publishes the fault without generating rule-defined Healthz artifacts. | See subfields below | See example above |

If `log_collection` is present, it must include at least one of `logs` or `queries`. Both may be present.

#### Repair Actions Structure

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `local_actions` | Object | No | Vendor-defined local remediation sequence scheduled by DLDD before remote escalation recommendations are relied on. | See subfields below | See example below |
| `remote_actions` | Object | Yes | Controller-visible remediation recommendation sequence published through `FAULT_INFO` and translated to OpenConfig Healthz remediations. | See subfields below | See example below |

**Local Actions (Optional):**
```yaml
local_actions:
  wait_period: 60                         # Required: Nonblocking wait after scheduled actions
  action_list:                            # Required: List of vendor-defined method calls
    - action:
        type: 'dse'               # Action type
        command: 'PSU:reset_output_power()' # Command to execute
        timeout: 120              # Optional: Overrides global local action timeout
    - action:
        type: 'dse'               # Action type
        command: 'PSU:clear_fault_register()' # Multiple actions executed in sequence
        timeout: 120              # Optional: Overrides global local action timeout
```

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `wait_period` | Integer | Yes | Time in seconds to wait after local actions before the primary thread requests a recheck and before remote action escalation is relied on. This is a nonblocking timer for DLDD; the primary thread continues telemetry publication and monitoring of unaffected correlation keys. | Strict integer 0-4294967295 seconds | `60` |
| `action_list` | List | Yes | Ordered sequence of vendor-defined remediation actions scheduled locally by DLDD on action worker context. Each list entry is a wrapper object containing one `action` object. The wrapped action object contains a `type` field specifying the execution method and type-specific fields for the operation. Actions are executed sequentially within the action sequence. | List of `action` wrapper objects. Supported wrapped action types: `dse`, `cli`, `i2c`, and explicit vendor-supported action types. CLI actions use `argv`. DSE actions use `command`. Direct I2C actions use `path`. | See example above |

Each action may specify `timeout` as a strict integer from 1 through 4294967295 seconds. If omitted, DLDD uses the top-level `local_action_default_timeout` from the active rules source. Validation fails for any local action that omits `timeout` when the rules source also omits `local_action_default_timeout`. A timeout marks that action as failed, records the failure in DLDD status/audit telemetry, triggers Healthz artifact collection when configured, and allows the primary thread to continue the post-action recheck path rather than leaving the correlation key held indefinitely. Artifact completion is not part of the local action result.

`local_actions` are executed by DLDD at most once per active fault lifetime for the same rule/component/symptom fault identity. Repeated event matches while the fault remains active refresh internal event history but do not start another identical local action sequence. If `local_actions` are configured, DLDD must complete the local action sequence and the subsequent `wait_period` recheck before publishing controller-visible `FAULT_INFO` fault telemetry for that fault lifetime. A clear result publishes the fault as `INACTIVE` with local action metadata so controllers can observe that DLDD detected and recovered the condition. A continued match publishes the fault as `ACTIVE` with the configured remote remediation recommendations. A new local action run is allowed only after the fault has cleared and later becomes active again, unless a future schema version defines explicit retry or cooldown fields.

#### Local Action and Query Validation Model

Schema version `0.0.1` validates local actions and log queries through type-specific contracts. Each `action_list[]` entry must be a wrapper object with an `action` member, and each `queries[]` entry must be a wrapper object with a `query` member. The required and optional fields below apply to the wrapped `action` or `query` object.

| Type | Valid Contexts | Required Fields | Optional Fields | Notes |
|------|----------------|-----------------|-----------------|-------|
| `dse` | local action, log query | `type`, `command` | `timeout` | `command` is a vendor DSE reference or command understood by the installed vendor DSE hook. DSE code and side effects are vendor-owned. |
| `cli` | local action, log query | `type`, `argv` | `timeout`, `max_output_bytes` | `argv` is executed without a shell. Shell pipelines, redirects, command substitution, and glob expansion are not valid. |
| `i2c` | local action; accepted as a query shape for a vendor executor | `type`, `path` | `timeout` | Direct monitoring events are read-only. Direct I2C local actions use the same target path fields as I2C event paths; write actions add a value to write. The default artifact query runner does not execute direct I2C queries, so a platform that wants that query form must advertise `i2c` in its query types and register the matching runtime hook; otherwise use `dse` or another vendor query type. |

Operation `timeout` fields are strict integers from 1 through 4294967295
seconds. CLI `max_output_bytes`, when present, is a strict integer from 1
through 4294967295. Reserved built-in fields (`path`, `command`, `argv`, and
`max_output_bytes`) are not valid opaque extras on a vendor operation.

Direct I2C local action path structure:

```yaml
action:
  type: "i2c"
  path:
    bus: "IO-MUX-6"
    chip_addr: "0x58"
    i2c_type: "set"
    command: "0x7A"
    size: "b"
    value: "0x00"
  timeout: 30
```

For `type: i2c` local actions, `path.bus`, `path.chip_addr`, `path.command`, and `path.size` identify the target using the same shape as the direct I2C event path. `path.i2c_type: "get"` performs a read action and records the result in action/audit metadata. `path.i2c_type: "set"` writes `path.value` to the target; that field must be present and non-null. More complex I2C side effects, such as read-modify-write sequences, should be modeled through vendor DSE actions unless a later schema version defines a direct structure for them.

Vendors may add implementation-specific action/query types only when the platform validator advertises support for those types. Unknown action/query types fail validation for the affected rule.

For local actions, omitted `timeout` values are filled from the top-level `local_action_default_timeout` when it is present. If an action omits `timeout` and the rules source omits `local_action_default_timeout`, validation fails for that rule. For log queries, `timeout` is optional and is not defaulted by the schema; if omitted, DLDD does not impose a schema-level query timeout, while the DLDD artifact client's retention and storage policies still bound stored output.

**Remote Actions (Required):**
The action list uses OpenConfig Healthz fault remediation identities. OpenConfig identity values are extensible, so DLDD requires each entry to be a non-empty string but does not restrict it to a locally maintained enum. Standard or vendor-defined identities are preserved unchanged for the controller. Vendor identities use `<yang-module>:<identity>` and must be present in the platform's compiled YANG model for UMF export. `time_window` defines how long, in seconds, the controller should retain the fault history for escalation decisions; if the fault remains active throughout this window, the controller may progress to the next action in `action_list` according to controller policy.
```yaml
remote_actions:
  action_list:                            # Required: Escalating sequence of controller actions
    - ACTION_RESEAT                       # Level 1: Remove and reinsert the component (if possible)
    - ACTION_COLD_REBOOT                  # Level 2: System reboot
    - ACTION_POWER_CYCLE                  # Level 3: Power cycle
    - ACTION_FACTORY_RESET                # Level 4: Full software reimage
    - ACTION_REPLACE                      # Final action: Replace the component
  time_window: 86400                      # Required: Fault history window for escalation evaluation (seconds)
```

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `action_list` | List | Yes | Ordered sequence of OpenConfig Healthz remediation action identities. List position becomes the remediation index published to `FAULT_INFO`. DLDD preserves each identity unchanged. | Non-empty list of non-empty standard or vendor-defined OpenConfig identity strings | `["ACTION_RESEAT", "vendor-healthz:ACTION_REPAIR_FABRIC_MODULE"]` |
| `time_window` | Integer | Yes | Fault history window, in seconds, used by the controller for escalation decisions. DLDD publishes the value; controller policy decides whether and when to execute actions. | Strict integer 1-4294967295 seconds | `86400` |

For the comprehensive list of OpenConfig fault actions and symptoms, refer to the [OpenConfig platform healthz fault model](https://openconfig.net/projects/models/schemadocs/yangdoc/openconfig-platform.html).

Remote action list order is the remediation index used when DLDD publishes `FAULT_INFO`. In schema version `0.0.1`, `remote_actions.action_list` is a list of action identities only. The OpenConfig remediation target defaults to the affected component instance resolved at runtime. A future schema version may add an explicit per-action target override if the remediation target and affected component need to differ.

#### Canonical Values and Extensible Identities

| Field | Values | Notes |
|-------|--------|-------|
| `metadata.severity` | `CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN` | Rule-derived severity used by DLDD for deterministic ordering and optional SONiC/alarm metadata. It is not a native OpenConfig Healthz fault leaf. |
| `metadata.symptom` | `SYMPTOM_OVER_THRESHOLD`, `SYMPTOM_UNDER_THRESHOLD`, `SYMPTOM_MEMORY_ERRORS`, `SYMPTOM_MISSING_COMPONENT`, `SYMPTOM_COMM_ERROR`, `SYMPTOM_UNKNOWN` | Closed schema `0.0.1` set accepted by Pydantic and the current UMF translator. |
| `metadata.error_type` | OpenConfig-aligned fault category strings or stable vendor category strings | Published to `FAULT_INFO.error_type`. UMF owns any mapping from this value into OpenConfig or SONiC extensions. |
| `metadata.component` | Any non-empty string | Vendor/platform-defined component type identity. Examples such as `PSU`, `FAN`, and `TRANSCEIVER` are conventional, not an allowlist. |
| `remote_actions.action_list[]` | Any non-empty string | Extensible OpenConfig Healthz remediation identity. Standard examples include `ACTION_RESEAT`, `ACTION_WARM_REBOOT`, `ACTION_COLD_REBOOT`, `ACTION_POWER_CYCLE`, `ACTION_FACTORY_RESET`, and `ACTION_REPLACE`. Vendor-defined identities are accepted and preserved; they use `<yang-module>:<identity>` and require that identity in the platform's compiled YANG model for UMF export. |
| `event.type` | `i2c`, `redis`, `dse`, `cli`, `file`, `sysfs`, `platform_api` | Type-specific `path` schema is defined above. |
| `evaluation.type` | `mask`, `comparison`, `string`, `boolean`, `dse` | Type-specific evaluation schema is defined above. |
| `value_configs.type` | `binary`, `hex`, `int`, `float`, `string`, `boolean`, `json`, `bytes`, `N/A` | Representation metadata for values in rules and DLDD telemetry. `N/A` is used when neither the rule nor DSE supplies more specific metadata. |
| `local_actions.action_list[].action.type` | `dse`, `cli`, `i2c`, or platform-advertised vendor-specific types | Type-specific local action schema is defined in Local Action and Query Validation Model. |


#### Schema to FAULT_INFO Translation Notes

DLDD translates vendor rules into the Redis `FAULT_INFO` payload before UMF exports OpenConfig Healthz telemetry:

- DLDD adds the fixed `producer: dldd` ownership marker. This is daemon metadata, not a vendor-selectable rule field.
- `metadata.component` plus the resolved event instance identifies the affected component. `FAULT_INFO.component_type` carries the vendor-defined component type, `component_name` carries the canonical vendor/platform component name for the affected instance, and `component_serial_number` carries the best available serial number or an empty string.
- `metadata.symptom` maps to the OpenConfig fault symptom. `metadata.severity` remains DLDD metadata used for ordering and diagnostics; it is not a native Healthz fault leaf.
- `metadata.error_type` maps to `FAULT_INFO.error_type`. UMF owns the OpenConfig translation for this value; vendors must keep the category stable for a given rule version.
- `remote_actions.action_list[]` maps to `repair_actions[]` in `FAULT_INFO`. List position is the remediation index, and the target defaults to the resolved affected component.
- `log_collection` maps to Healthz artifact creation. DLDD publishes an artifact identifier in `FAULT_INFO` when artifact generation is triggered, even though the artifact content may still be collected asynchronously.
- `origin_time` and `last_detection_time` are generated by DLDD at runtime and published as whole Unix epoch seconds using mathematical floor. `last_detection_time` is the last detected fault state change for the record. UMF converts these timestamps to the nanosecond representation required by OpenConfig. Internal monotonic scheduling retains full precision; durations and intervals are not rounded or floored.

#### Log Collection Structure

**Static Log Files:**
```yaml
logs:
  - log: "/var/log/syslog"                # System log file
  - log: "/var/log/platform.log"          # Platform-specific logs
  - log: "/mnt/obfl/*"                    # Onboard failure logging, capturing all files in the wildcard
```

**Dynamic Queries:**
```yaml
queries:
  - query:
      type: "dse"                # Platform abstraction layer
      command: "PSU:get_blackbox()"        # Component-specific method
      timeout: 60
  - query:
      type: "cli"                         # Command line interface
      argv: ["/usr/local/bin/show", "platform", "temperature"] # Standard CLI command executed without a shell
      timeout: 60
  - query:
      type: "dse"                      # Vendor-specific hardware diagnostic dump
      command: "CHASSIS:get_sdk_debug_dump()" # Detailed hardware dump
      timeout: 300
```

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `queries` | List | Conditional | Ordered sequence of diagnostic data collection commands triggered after local recovery actions complete, or after signature confirmation when no local actions are configured. Each query wrapper contains a `query` object with a type field specifying the execution method and type-specific fields for the operation. Queries are executed sequentially in the artifact worker context. DLDD can publish the Healthz artifact identifier before the query output is complete; outputs/content are added to the artifact when generation completes. Required only when `log_collection` omits `logs`; if `logs` is also omitted, at least one `query` is required. | List of `query` wrapper objects. Supported wrapped query types are defined by the Local Action and Query Validation Model. CLI queries use `argv`. DSE queries use `command`. | See example above |
| `logs` | List | Conditional | Static files or glob patterns collected by the artifact worker after local recovery actions complete, or after signature confirmation when no local actions are configured. Required only when `log_collection` omits `queries`; if `queries` is also omitted, at least one `log` is required. | List of log objects | See example above |

DLDD owns artifact generation, local storage, and retention under `/var/lib/sonic/dldd/artifacts`; the default client uses two artifact workers, retains at most 20 artifacts, and limits an artifact to 50 MiB. Static log collection expands globs but accepts only regular non-symlink files and does not recurse. The gNOI Healthz `Artifact` RPC exposes completed files to authenticated controllers. DLDD validation confirms the log/query schema and applies query timeouts only when a query declares `timeout`. Artifact generation is asynchronous with respect to local action result, post-action recheck, and `FAULT_INFO` publication.

## Abstract Rule Data Source Extensions - Vendor Extensible

### What are Data Source Extensions

Abstract data source extensions (DSE) provide a way for vendors to extend the schema with granularity at the NOS level. This allows vendors to define their own detailed hardware abstractions that can be used to match against specific events and conditions, while keeping the actual rules source file standardized and uniform. Vendors are not required to implement or use DSE, but they provide a way to better simplify the rules source file and make it more maintainable. Complexity and potential variations in hardware implementations can be abstracted away from the rules source file. Actual integration and usage of the DSE will be done through a vendor implemented hook which the on-device service will operate on. If a rule references a DSE function that is not defined for the target platform, validation fails for that rule.

Data source extensions also allow for the ability to hook into NOS specific APIs and methods. A good example of this would be defining a DSE that resolves to a method to call on the SONiC platform chassis object to retrieve the PSU object, and then using that object to retrieve the PSU output voltage fault register. This allows for the reuse of existing infrastructure the NOS provides wherever possible.

### Data Source Extension Architecture

Abstract rules use symbolic references resolved by trusted platform Python loaded from the fixed `sonic_platform.dldd` module. Uploaded rule data cannot select a module, class, or callable. A platform can provide `create_dse_registry(dse_path, product_id, software_version)`, which returns a `DSERegistry`; the generic daemon passes the packaged `dld_dse.yaml` path to that factory but does not parse, Pydantic-validate, or prescribe the file's contents. The DSE file is opaque vendor configuration, not part of the versioned vendor-rules wire schema and not a second generic schema. A vendor may omit it, use another internal representation, or validate it with vendor code.

The fixed trusted platform extension surface is:

| Factory or hook | Contract |
|-----------------|----------|
| `create_dse_registry(dse_path, product_id, software_version)` | Returns the `DSERegistry` that resolves source, evaluation, action, and query references. `dse_path` may be absent; its format is vendor-owned. |
| `create_vendor_hooks()` | Returns a `VendorHookRegistry` advertising vendor source/action/query types and their validation/execution hooks. |
| `create_compatibility_matcher(...)` | Optionally replaces exact product/software membership matching with a vendor compatibility policy. |
| `create_artifact_client(identity, artifact_directory, query_runner)` | Optionally replaces the default filesystem artifact client while retaining the asynchronous artifact contract. |
| `source_lifecycle` named hook | Classifies vendor-specific peer-source outages as expected maintenance. SONiC has no generic mapping from an arbitrary rule path or Redis table to its producer service. Without this hook, peer-source absence is unexpected `UNAVAILABLE` and normal grace/failure policy applies. DLDD's own FEATURE/systemd lifecycle is managed separately and is not inferred from rule telemetry. |
| `component_metadata` named hook | Supplies optional component metadata such as serial number for fault publication. |
| `i2c` named hook | Validates/resolves vendor logical I2C bus identifiers. |

These factories are discovered only from the installed `sonic_platform.dldd` module. Rule YAML can provide bounded hook parameters, but cannot change the discovery module or attach executable code. A vendor implementation should expose a small reviewed function bank rather than import or evaluate a function name supplied by a rule. One bank may contain expansion, source, evaluator, action, and query handlers; each registration declares the uses it permits so the implementation stays extensible without duplicating registries.

#### Selector, Expansion, and Function Separation

A selector is an abstract component family, not a transport declaration. For example, `temperature*` means the platform's temperature-sensor instance space; it does not mean Redis, Platform API, I2C, or any other backend. The vendor DSE implementation supplies one canonical expansion hook for that selector and separately maps each rule-facing function to a trusted handler. Expansion and function handlers may use different backends.

The resulting responsibilities are:

| Layer | Responsibility |
|-------|----------------|
| Rule reference | Names only an abstract selector and capability, such as `{temperature*}:{get_value()}`. |
| Selector expansion | Discovers current component instances and returns opaque `DSEBinding` objects with stable instance/source identities. |
| Selector function | Uses one binding to perform `get_value`, `get_high_threshold`, another source/evaluator capability, or a future vendor operation. |
| Function bank | Maps vendor configuration aliases to reviewed installed Python handlers and enforces permitted uses. It never imports a rule-selected module or evaluates a rule-selected expression. |
| Backend handler | Implements Redis, Platform API, SDK, I2C, sysfs, file, or another vendor mechanism behind the abstract capability. |

Core DLDD does not prescribe a YAML layout for this vendor-private mapping. The concrete reference files are identified in the daemon HLD's cross-repository implementation map. The included non-normative platform reference implementation uses the following shape solely as its own configuration contract:

```yaml
function_bank:
  state_db_hash_expand:
    handler: redis_hash_expand
    uses: [expansion]
  state_db_hash_read:
    handler: redis_hash_read
    uses: [source, evaluation]

selectors:
  "temperature*":
    expansion:
      hook: state_db_hash_expand
      authoritative: false
      parameters:
        database: STATE_DB
        table: TEMPERATURE_INFO
        key_pattern: "TEMPERATURE_INFO|*"
      policy:
        bootstrap_scans: 2
        bootstrap_interval: 5
        warmup_cycles: 3
        stable_interval: 300
    functions:
      get_value:
        use: source
        hook: state_db_hash_read
        parameters:
          field: temperature
          value_type: float
          unit: celsius
      get_high_threshold:
        use: evaluation
        hook: state_db_hash_read
        parameters:
          field: high_threshold
          operator: ">="
          value_type: float
          unit: celsius
```

Here `temperature*`, `get_value()`, and `get_high_threshold()` remain transport-neutral. Only the opaque platform mapping mentions STATE_DB. The expansion binding contains enough vendor-private identity for the chosen function handler, while another function under the same selector may instead use the instance name to call Platform API or an SDK. A function must be explicitly present under the selected selector; being registered in the global function bank does not expose it automatically.

#### DSE Reference Grammar

DSE references use one of two canonical forms:

```text
<selector>:<function>()
{<selector>}:{<function>()}
```

The braced form supports `*` and `?` wildcard selectors. The unbraced form is accepted only for a simple selector without wildcards. Both sides of a reference must use matching brace style.

| Element | Description | Examples |
|---------|-------------|----------|
| `selector` | Component selector or instance selector understood by the vendor DSE hook; wildcard selector content is valid only inside the braced reference form | `PSU`, `{psu*}`, `PSU0` |
| `function` | Vendor-defined DSE function name | `get_output_voltage_fault_register`, `get_output_voltage_failure_value` |
| `()` | Function-call marker. Arguments are not part of schema version `0.0.1`; vendors may extend through DSE data if needed. | `get_status()` |

DSE resolution is vendor extensible, but resolution and execution are separate phases. During activation, a DSE source reference resolves to a `DSESourceHandle` and a DSE evaluation reference resolves to a `DSEEvaluationHandle`. Core DLDD checks that the requested reference is exposed and that the returned functions are callable; it does not invoke source expansion, enumerate instances, fetch a value, fetch a threshold, or build an evaluator. A resolution error marks only the affected rule broken when another usable rule remains.

The monitor invokes the handles at runtime:

- `DSESourceHandle.expand(rule_context)` returns `DSEExpansionResult(bindings, authoritative)` when discovery is due. Each `DSEBinding` has a stable component `instance`, stable `source_id`, immutable vendor data, and optional value metadata.
- `DSESourceHandle.get_value(invocation_context)` reads one expanded binding at event sampling time.
- `DSEEvaluationHandle.get_evaluator(invocation_context)` runs at event sampling time and returns an expected value/operator mapping or a trusted complete comparator contract.
- `DSEExpansionPolicy` supplies bootstrap scan count/spacing, warmup monitor-cycle count, and stable rescan interval. The common monitor owns and executes this policy; the primary orchestration thread never calls DSE source/evaluator functions.

This split allows a vendor DSE source to discover instances periodically while reading fast-changing values and thresholds every event sample. For example, a platform's abstract `current*` selector may use a private STATE_DB expansion handler every five minutes once stable, while `get_value()` rereads `current` and `get_high_threshold()` rereads `high_threshold` every five-second sample. Direct Redis paths likewise query the configured source on every sample; a direct value is never cached merely because its rule was materialized.

In the rules source, the event path would be defined like so:
```yaml
# Abstract rule definition
path: "{psu*}:{get_output_voltage_fault_register()}"
```

The platform reference sensor rules use the same single-event shape for all
instances; discovery supplies one binding per matching STATE_DB key:

```yaml
event:
  id: 1
  type: dse
  path: "{current*}:{get_value()}"
  evaluation:
    type: dse
    value: "{current*}:{get_high_threshold()}"
  sampling_interval: 5
```

This is one logical event instanced over every discovered current sensor, not
one event per sensor and not an OR expression containing every sensor.

For source and evaluator references, resolution returns callable handles and must not read live hardware, Redis, files, or other external state. DSE action/query references continue to resolve to a `ResolvedCommand`, and resolution must not execute the command. The default compatibility matcher requires exact product and software-version membership; a platform may install `create_compatibility_matcher(...)` when its version/product matching rules differ.

#### DSE Instance Semantics

A wildcard source is instanced and expands into one ordinary `MonitorWorkItem` per returned binding. It remains one logical rule event: the per-instance work items do not become a large OR expression and retain the event's single ID. Correlation joins events by the returned component instance.

When the same signature also contains a non-instanced event, DLDD clones that common predicate into each newly discovered component execution rather than changing the rule logic or creating an OR list. Multiple DSE events that discover the same component share ownership of an identical common-predicate clone so removing one dynamic binding does not remove work still required by another event.

| Source cardinality | Evaluator cardinality | Schema `0.0.1` behavior |
|--------------------|-----------------------|--------------------------|
| Common | Common | Supported |
| Common | Instanced wildcard | Rejected; there is no source instance with which to bind the evaluator |
| Instanced | Common | Supported; the common evaluator runs once per source sample with that source binding context |
| Instanced | Instanced wildcard | Supported only when source and evaluator selectors match exactly; the same binding is passed to both handles |

A direct event with explicit `instances` is also an instanced source and may use an instanced DSE evaluator. A direct common event may use only a common DSE evaluator. These rules prevent ambiguous cross-products while still allowing a vendor evaluator to derive a per-instance expected value.

#### Runtime Expansion and Stabilization

Source inventory may be incomplete while SONiC producers are starting, and no generic API can prove it globally complete. DLDD therefore treats repeated unchanged scans as stable rather than claiming completeness. The monitor-owned state machine is:

1. **BOOTSTRAP**: run the vendor-configured number of closely spaced expansion scans. The included platform reference policy uses two scans five seconds apart. No source/evaluator value reads occur merely because expansion ran.
2. **WARMUP**: sample every currently expanded child for one full monitor cycle, then rescan. Repeat for the configured number of unchanged cycles; the included platform reference policy uses three. Any binding change resets the unchanged count.
3. **STABLE**: rescan at the vendor stable interval; the included platform reference policy uses 300 seconds. A changed fingerprint returns to WARMUP. Child `get_value()` and `get_evaluator()` still run at normal event cadence during this interval.

The DSE layer owns the policy values and the meaning of `authoritative`; the common monitor owns timing, phase transitions, and child work state. A non-authoritative empty or reduced result does not delete established children, which avoids losing monitoring during transient producer startup/restart. An authoritative result may remove absent children only when they are not in-flight or held by the primary. Expansion failures retain existing children, degrade discovery status, and retry at the bootstrap interval.

The monitor queues a `DSEExpansionEvent` before a new child is eligible to sample. The primary consumes that registration to add the child to correlation state; vendor handles are not invoked by the primary. If registration cannot enter the bounded FIFO, the monitor does not install/sample the child and retries expansion, so child evidence cannot outrun correlation registration.

### DSE Benefits
- **Hardware Abstraction**: Rules remain independent of hardware implementation details
- **SW Version Support**: Single rule supports multiple SW versions
- **Maintainability**: Hardware changes require only DSE updates
- **Reusability**: Common patterns can be shared across rules

## Rule Examples

### Complete PSU Over-Voltage Rule

```yaml
schema_version: "0.0.1"
local_action_default_timeout: 300

signatures:
  - signature:
      metadata:
        name: PSU_OV_FAULT
        id: 1000001
        version: "1.0.0"
        description: |
          An over voltage fault has occurred on the output feed from the PSU to the chassis.
        product_ids:
          - "8122-64EHF-O P1"
          - "8122-64EHF-O P2"
        sw_versions:
          - "202311.3.0.1"
        component: PSU
        symptom: "SYMPTOM_OVER_THRESHOLD"
        error_type: "POWER"
        severity: "CRITICAL"
        priority: 1
        tags: 
          - power
          - voltage

      conditions:
        logic: "1 OR 2"
        logic_lookback_time: 60
        events:
          - event:
              id: 1
              type: i2c
              instances: ['PSU0:IO-MUX-6', 'PSU1:IO-MUX-7']
              path:
                bus: ['IO-MUX-6', 'IO-MUX-7']
                chip_addr: '0x58'
                i2c_type: 'get'
                command: '0x7A'
                size: 'b'
                scaling: 'N/A'
              evaluation:
                type: 'mask'
                logic: '&'
                value: "0b10000000"
              sampling_interval: 60
              match_count: 1
              match_period: 0

          - event:
              id: 2
              type: dse
              path: "{psu*}:{get_output_voltage_fault_register()}"  # DSE wildcard implies PSU-scoped instances
              evaluation:
                type: 'dse'
                operator: 'equals'
                value: "{psu*}:{get_output_voltage_failure_value()}"
              # sampling_interval omitted: inherit the common monitor default
              match_count: 1
              match_period: 0

      actions:
        repair_actions:
          local_actions:
            wait_period: 60
            action_list:
              - action:
                  type: 'dse'
                  command: 'PSU:reset_output_power()'
                  timeout: 120
          remote_actions:
            action_list:
              - ACTION_RESEAT
              - ACTION_COLD_REBOOT
              - ACTION_POWER_CYCLE
              - ACTION_FACTORY_RESET
              - ACTION_REPLACE
            time_window: 86400
        log_collection:
          logs:
            - log: "/var/log/platform.log"
          queries:
            - query:
                type: "dse"
                command: "PSU:get_blackbox()"
                timeout: 60
            - query:
                type: "cli"
                argv: ["/usr/local/bin/show", "platform", "voltage"]
                timeout: 60
```

## Schema Validation

### Validation Requirements
- Schema version must be present and valid
- All required fields must be populated
- Event IDs must be unique within a signature
- Logic expressions must reference valid event IDs and use only the supported `AND`/`OR` operators
- Product IDs and SW versions must match the platform/NOS matching contract used by the consuming daemon
- Direct I2C monitoring events must use `i2c_type: 'get'`
- CLI condition paths, CLI local actions, and CLI log queries must use `argv`; shell pipelines and redirection are not valid path syntax
- An event `sampling_interval`, when present, must be a strict integer from 1 through 4294967295 seconds. Omission is preserved for monitor-default inheritance; explicit `null` is invalid.
- An event `async`, when present, must be a strict boolean. Omission resolves to `false`; explicit `null`, numeric values, and strings are invalid.
- `value_configs.type` must use the canonical enum values defined in this document
- Local actions and log queries must conform to a supported type-specific contract, including timeout handling
- Local actions that omit per-action `timeout` require a top-level rules-source `local_action_default_timeout`
- DSE source/evaluation references must resolve to callable handles without invoking them. Built-in evaluator/operator compatibility is checked during validation; a DSE evaluator's returned value/operator/comparator contract is checked each time the monitor invokes it.
- Remote activation must fail if per-signature validation and materialization leave zero usable direct rules and zero successfully resolved DSE templates for the current platform. A valid DSE template with zero instances before runtime expansion is still usable.
- Complete examples in this document should be valid YAML or JSON and should be usable as validation fixtures, but examples are not the validation authority.

### Validation Contract

Validation is driven by trusted, exact-version Pydantic v2 contracts rather than prose examples or a runtime-loaded JSON Schema. For every supported `schema_version`, DLDD registers an immutable contract containing a shallow file-envelope `TypeAdapter`, an independently callable per-signature `TypeAdapter`, the corresponding fully nested document model used for schema generation/tests, and an explicit DTO-to-domain converter. Context-free, version-specific semantic checks are Pydantic model validators. DSE reference resolution, platform compatibility, and direct-source materialization follow conversion and consume only the immutable, version-neutral domain model.

The Pydantic models own required fields, strict primitive types, enum values, ranges, DSE reference grammar, collection bounds, unknown-field policy, and type-specific path, evaluation, action, and query shapes. Bounded DLDD helpers and model validators own context-free cross-field constraints such as event ID uniqueness, condition-logic parsing, timeout inheritance eligibility, event references, and built-in evaluator/operator compatibility. Product/software matching, DSE handle resolution, trusted vendor-hook discovery, and direct adapter configuration remain later materialization concerns. Runtime DSE expansion and per-sample handle invocation are deliberately outside activation validation. The contents of vendor `dld_dse.yaml` are outside every core Pydantic contract.

Core models reject unknown fields and use strict validation: numeric strings are not converted to numbers, booleans are not integers, non-finite numbers are rejected, and behavior-bearing unions use explicit type dispatch. Explicit vendor extension envelopes may preserve only bounded JSON-compatible fields for a type advertised by installed trusted platform code. A malformed built-in type never falls through to vendor handling.

To keep all accepted domain objects safe for JSON/Redis serialization,
`priority` and `max_output_bytes` use the unsigned 32-bit range. Integer
comparison/scaling values, I2C/vendor JSON payload integers, and parsed mask
integers use -9223372036854775808 through 18446744073709551615. Mask integer
strings are at most 256 characters and must parse into that range. Float
fields require an actual finite float; an oversized integer cannot fall
through a float union branch and lose precision.

Omission, explicit `null`, zero/false, and empty values are distinct input states. Explicit `null` is invalid unless the exact field contract declares it nullable. Authorized defaults are applied to the validated DTO or during explicit version-specific DTO-to-domain conversion; the raw parsed document is never mutated. In particular, omitted `sampling_interval` remains unresolved until planner monitor assignment.

The examples in this document should be included as positive fixtures for the validator, but adding or changing examples must not be required to change validation behavior.

#### Strict Base Model and Domain Boundary

All core versioned models inherit one closed contract policy equivalent to `strict=True`, `extra="forbid"`, `validate_default=True`, `allow_inf_nan=False`, `frozen=True`, `hide_input_in_errors=True`, `loc_by_alias=True`, and `revalidate_instances="always"`. Consequently, numeric strings are not coerced, booleans are not accepted as integers, unknown core fields are not silently discarded, defaults are validated, non-finite numbers are rejected, input values are hidden from dependency error rendering, and wire aliases are used in error locations. Explicit vendor extension objects are the only places where additional bounded fields may be admitted.

Pydantic receives the already parsed and bounded Python object graph; it never receives untrusted file bytes directly, and DLDD does not use `model_validate_json()` as a parser shortcut. This preserves duplicate-key rejection, YAML alias/tag rejection, source-line mapping, and uniform JSON/YAML resource limits before model construction.

Pydantic DTOs are short-lived validation objects. `frozen=True` prevents assignment but is not deep immutability, so each exact-version contract has an explicit converter that creates the version-neutral domain dataclasses, converts collections to tuples, recursively freezes mappings and vendor options, applies only documented defaults/inheritance, and never attaches a callable selected by uploaded data. Planning, DSE handle resolution, correlation, actions, and telemetry consume only these immutable domain objects; they do not consume Pydantic models or unreviewed `model_dump()` output. Callable handles are attached only by the trusted installed registry after conversion.

Built-in event, evaluator, action, and query types use explicit typed dispatch. A reserved built-in name must validate against its exact built-in model and cannot fall through to a generic vendor extension after malformed input. Vendor extensions use a bounded JSON-compatible envelope and are accepted only when trusted installed platform code explicitly advertises that type. Uploaded rules cannot select a Python module, class, callable, URL, or filesystem schema.

#### Trusted Model Registry and Validator Dependency

The contract registry is Python code installed with DLDD and is immutable after initialization. Lookup is exact; a rule declaring `0.0.2` never falls back to `0.0.1`. Uploaded rules cannot provide a schema URI, filesystem path, module, class, callable, model name, or validator. A newer exact version receives an explicit registry entry even when it intentionally reuses an existing implementation.

DLDD uses pinned Pydantic v2 and its compatible pinned `pydantic-core` as the runtime structural validation dependency. `sonic-host-services` declares Python `>=3.9`; the current deployed target is CPython 3.13 and has been exercised on Python 3.13.5. The current integration pins `pydantic==2.13.4` and `pydantic_core==2.46.4` in both build and host-image dependency locks. Registry construction verifies that each entry's version matches the envelope and document models' literal `schema_version`, that envelope/signature/document adapters can be constructed, and that every entry supplies its DTO-to-domain converter. An import failure, registry/model mismatch, adapter construction failure, or unexpected validator exception is a daemon/package failure; it is not attributed to uploaded rule content and must not be downgraded to a per-rule `BROKEN` result.

Every supported SONiC Python version and architecture must qualify the exact dependency set with binary-wheel availability, deterministic hashes, native-extension import/linkage checks, `pip check`, complete `sonic-host-services` tests, image construction, license/SBOM/vulnerability review, and startup/resource regression checks. Floating ranges, prereleases, runtime downloads, and an unexpected Rust/source build in the image path are not acceptable. Failure to import the compatible `pydantic-core` is an image construction/package defect rather than a rule-file validation result.

Pinned `regex` remains the bounded regular-expression evaluation dependency. Runtime regular-expression searches have a 100 ms deadline; exceeding it produces an evaluator error instead of indefinitely blocking a monitor worker.

#### Generated JSON Schema

DLDD publishes a deterministic Draft 2020-12 JSON Schema generated from the fully nested exact-version Pydantic models for vendor authoring, editor integration, documentation, and offline tooling. The generated artifact has a stable `$id`, title, exact rule schema version, and a generated-file warning, and CI verifies that regeneration with the pinned Pydantic version matches the committed artifact.

The generated artifact remains derivative where JSON Schema cannot represent
Python parsing semantics exactly. In particular, JSON Schema does not retain
the lexical distinction between an integer and an integral-valued float, and
it cannot apply numeric bounds after parsing a mask value from a string. Those
branches carry an `x-dldd-runtime-constraint` annotation describing the exact
Pydantic check. The installed Pydantic contract remains authoritative.

The generated JSON Schema is derivative, is not a second runtime authority, and is never loaded or executed by the daemon. Runtime validation must continue to work if the generated artifact is absent from an installed test environment.

#### Input Safety

Before Pydantic validation, DLDD bounds the source text, rejects duplicate JSON and YAML mapping keys, rejects YAML aliases and unsafe tags, uses the YAML safe loader, and bounds parsed document depth, node count, collection size, and scalar values/keys. Pydantic field and model validation then enforces signature/event counts, logic-expression size/nesting, regular-expression size/nesting, strict numeric ranges, and bounded vendor payload types. The current document limits are a 4 MiB source, depth 64, 100,000 document nodes, 10,000 entries in any collection, 1 MiB per string scalar or mapping key, 1,024 signatures, and 1,000 events per signature. Direct internal validation of an already constructed Python mapping applies the same document limits and strict model contract. Parsing preserves source line information for diagnostics.

Raw Pydantic errors are never published directly. DLDD normalizes them and custom semantic failures into stable issue codes, file/rule scope, canonical JSON-style paths containing the signature index, source lines when available, and rule ID/name when identifiable. Diagnostics are deterministically ordered, redact raw input, and are bounded per rule and per candidate so dependency-specific error formatting cannot become an operator-facing API or an unbounded telemetry payload.

Representative normalization is owned by DLDD rather than by Pydantic message text:

| Pydantic error type | Stable DLDD issue code |
|---------------------|------------------------|
| `missing` | `missing_field` |
| `dict_type`, `list_type`, `string_type`, `int_type`, `bool_type`, `float_type` | `invalid_type` |
| `extra_forbidden` | `unknown_field` |
| `literal_error`, `enum` | `unsupported_value` |
| `greater_than*`, `less_than*` | `out_of_range` |
| `too_short`, `too_long` | `invalid_length` |
| `string_pattern_mismatch` | `invalid_format` |
| `union_tag_not_found`, `union_tag_invalid` | `unsupported_type` |
| DLDD `PydanticCustomError` | Its explicit stable DLDD semantic code |

The normalizer removes model and union-branch implementation names, uses wire aliases, prepends the signature index, and emits canonical paths such as `$.signatures[2].signature.conditions.events[0].event.sampling_interval`. It excludes raw input and dependency documentation URLs from the published result.

Schema `0.0.1` returns at most 64 Pydantic issues per rule and 4,096 issues
per candidate, bounds each message to 1,024 bytes and each published path to
2,048 bytes, and keeps compact serialized candidate diagnostics within 1 MiB.
Long paths and diagnostic identities include a short SHA-256 suffix so
distinct fields remain distinct after truncation. When raw issues exceed a
per-rule or per-candidate budget, each affected rule retains a stable
`validation_issues_truncated` marker.

The complete safety contract therefore requires: no network schema retrieval; no rule-selected schema/module/class/callable; no duplicate-key ambiguity or YAML object construction; no silent core-field dropping; no lax scalar coercion or non-finite values; bounded source, document, logic, regular-expression, vendor-payload, and diagnostic complexity; no hardware/source reads or side effects during normal activation; no raw rule payload in diagnostics; no mutable vendor data in runtime structures; no malformed built-in accepted through vendor fallback; and no version accepted by semantic-version proximity.

#### Validation Model

Validation uses a shallow Pydantic file-envelope pass followed by an independent Pydantic pass for every signature. A fully nested model may be used to generate the derivative JSON Schema and for positive contract tests, but it is never the runtime activation gate because doing so would turn one localized signature error into a file-level failure.

1. **File-envelope activation gate**: Validates the root object, exact registered `schema_version`, top-level optional fields, non-empty `signatures` list, deterministic signature wrapper shape, configured input limits, and cross-signature identity uniqueness. Malformed input, unsupported versions, invalid top-level structure, duplicate rule IDs or names, and errors that prevent deterministic signature isolation reject the entire candidate and trigger rollback or retention of the previous active generation.
2. **Per-signature Pydantic and semantic gate**: Applies the version's strict signature model and context-free semantic validation independently to every isolated signature. Missing per-rule fields, invalid types, paths, enums, condition expressions, action/query contracts, and other localized authoring errors mark only that rule broken.
3. **Per-signature materialization gate**: Checks product/software applicability, DSE reference-to-handle resolution/callability, source/evaluator instance-cardinality compatibility, trusted vendor-hook availability, and direct adapter configuration without invoking DSE handles, sampling monitoring sources, or executing actions. Localized failures mark only that rule broken.
4. **Usable-rule activation guard**: Activation succeeds as `DEGRADED` when at least one rule is usable and one or more rules are broken. Activation fails when zero usable rules remain, preserving or restoring the previous valid generation or fallback.

Normal activation validates rules, direct configuration, and DSE handle resolution only. DLDD core does not call adapter source-read/collection methods, DSE expansion/source/evaluator functions, or local actions. Trusted DSE registry and vendor validation methods invoked during resolution must be side-effect-free and must not sample hardware or external source values. A DSE source template is usable even before any runtime instance is discovered. A currently absent key, file, device, component, or fault-only source is a runtime availability/discovery condition, not an activation failure. Invalid direct source configuration, an unresolved DSE reference/handle, incompatible instance cardinality, or a required trusted vendor hook that is not installed remains a per-rule materialization failure.

Declared rule/materialization errors (`DSEError` or `ValueError`) are localized to the affected rule. Unexpected exceptions from trusted validator or vendor code indicate an implementation/package failure; they abort that candidate attempt and enter lifecycle fallback rather than being mislabeled as vendor-rule authoring errors.

Schema `0.0.1` keeps `event.type` and `evaluation.type` closed. Direct platform-source extension uses the bounded `platform_api` hook object, while a DSE source resolves to a trusted installed handle and runtime binding. Action and query operations have a bounded generic vendor envelope whose type must be advertised and validated by the trusted platform registry. Vendors may supply side-effect-free validation and execution hooks, but uploaded rules do not install or select a Pydantic model. A type name in uploaded YAML never causes dynamic module import, and reserved built-in type names are always dispatched to their exact built-in models.

#### Validation Modes

The validation CLI exposes progressively stronger, explicit modes:

| Mode | Behavior |
|------|----------|
| `static-schema` | Bounded safe parsing, exact contract selection, shallow envelope validation, independent strict per-signature Pydantic validation, and context-free semantics. The historical name is retained, but no runtime JSON Schema is loaded. No platform extension discovery or source access occurs. |
| `dse-resolve` | Adds DSE and trusted vendor-extension reference-to-handle resolution without expanding sources, enumerating instances, fetching values/thresholds, invoking evaluator handles, or executing actions. |
| `activation-dry-run` | Adds product/software compatibility, direct work/DSE template materialization, trusted hook discovery, and side-effect-free direct adapter configuration validation. This is the normal promotion gate. |
| `hardware-probe` | Explicit operator qualification that may invoke vendor-selected read-only source access. It is not part of normal activation. |
| `e2e-execute` | Explicit controlled monitoring-source qualification that expands DSE templates and calls each resulting/direct adapter's `collect()` path (collection, normalization, and evaluation). It does not execute local actions or artifact queries and is not part of normal activation. |

### Validation Process
1. **Bounded Syntax Validation**: Parse the immutable staged JSON/YAML copy using duplicate-safe, alias-free, bounded parsing.
2. **Exact Contract Selection**: Read `schema_version` and require its exact trusted registry entry.
3. **Envelope Validation**: Validate only the shallow file envelope and cross-rule identities at file scope.
4. **Independent Rule Validation**: Run strict version-specific Pydantic and context-free semantic validation for each isolated signature, retaining localized diagnostics.
5. **DSE and Evaluator Validation**: Resolve DSE references to callable handles, validate source/evaluator cardinality, and verify deterministic built-in evaluator semantics without invoking the DSE handles.
6. **Materialization Preflight**: Check compatibility, trusted vendor hooks, and direct adapter configuration without expanding DSE inventory, collecting source values/thresholds, invoking DSE evaluators, or executing actions.
7. **Activation Guard**: Reject the candidate if no usable rules remain; otherwise activate the usable rules and publish localized failures as broken-rule diagnostics.
8. **Qualification Modes**: Invoke configured source-read or collection paths only when an operator explicitly requests hardware-probe or end-to-end validation. These paths are vendor-selected and must be reviewed for their intended read-only qualification behavior.

Validation occurs when a candidate generation changes. A generation remains tied to the exact schema contract and active-source checksum used to validate it. A file-level failure rejects the candidate generation. A per-rule failure omits only the affected rule when at least one usable rule remains. A zero-usable-rule result keeps or restores the previous active generation or fallback.

## Backward Compatibility
- A daemon supports an older schema version by retaining an explicit Pydantic contract registry entry for that exact version.
- A new registry entry may intentionally reuse existing models or a DTO-to-domain converter, and converted domain rules may share version-neutral materialization, but compatibility is never inferred from semantic-version proximity.
- A generated JSON Schema should remain available for authoring tools while its exact schema contract is supported.
- Unknown-field handling is controlled by each exact schema contract; consumers must not apply a blanket ignore policy across versions.

---

*This document defines the vendor-defined rules for hardware health monitoring. For implementation details of the SONiC-focused DLDD service itself, refer to the companion Device Local Diagnosis Service HLD document.*
