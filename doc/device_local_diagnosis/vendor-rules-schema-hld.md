# Device Local Diagnosis Rules Schema HLD

## Table of Contents

1. [Introduction](#introduction)
2. [Definitions](#definitions)
3. [Requirements](#requirements)
4. [Schema Versioning](#schema-versioning)
5. [Rule Structure](#rule-structure)
6. [Abstract Rule Data Source Extensions](#abstract-rule-data-source-extensions---vendor-extensible)
7. [Schema Layout Definitions](#schema-layout-definitions)
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

## Definitions

| Term | Definition |
|------|------------|
| **Schema Version** | Version identifier for the rules structure format |
| **Signature** | A complete fault detection rule with metadata, conditions, and actions |
| **Event** | A specific data collection and evaluation point within a signature |
| **Data Source Extension (DSE)** | Translation layer between abstract rule definitions and hardware/software specific implementation |
| **Abstract Rule** | Rule using DSE identifiers that are resolved through data source extension files |
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
Every rules source file must begin with a schema version declaration:

```yaml
schema_version: "0.0.1"
```

**CRITICAL**: This header format is immutable and serves as the entry point for schema interpretation.

### Versioning and Compatibility with SONiC NOS
 
The schema version does not have explicit associated DLDD or SW version requirements. Schema versioning is independent of the software release cycle, allowing for:

- Multiple schema versions supported by a single DLDD version
- Backward compatibility across software releases
- Independent evolution of schema structure and daemon implementation

DLDD is responsible for handling schema version compatibility through its schema layout definitions.

Compatibility is evaluated against the daemon's supported schema versions and feature set. Unknown optional fields may be ignored. Unknown required fields, unknown event types, unknown evaluation types, unknown action types, or unknown enum values must fail validation because they can change execution behavior.

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
| `local_action_default_timeout` | Integer | Conditional | Rules-source default timeout in seconds for local actions that omit per-action `timeout`. Required when any local action omits `timeout`; optional when every local action declares its own timeout. |
| `signatures` | List | Yes | Non-empty list of signature objects |
| `signatures[*].signature.metadata` | Object | Yes | Rule metadata |
| `signatures[*].signature.conditions` | Object | Yes | Rule condition logic and events |
| `signatures[*].signature.actions` | Object | Yes | Repair actions and optional diagnostic log collection |

### Signature Metadata
Each signature contains comprehensive metadata for identification and applicability. Every field serves a specific purpose in rule processing and system integration:

- **Severity Ordering**: The `severity` field encodes DLDD rule severity (`CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN`). Higher severity signatures always take precedence when multiple rules target the same component/symptom pair. This field is DLDD/SONiC diagnostic metadata; it is not a native OpenConfig Healthz fault leaf.
- **Priority Tiebreaker**: The optional `priority` field provides deterministic ordering for rules that share the same severity and symptom. Lower numeric values indicate higher priority; when omitted, adapters treat the priority as `5`.

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
    symptom: "<OC symptom>"                 # Required: OpenConfig Healthz fault symptom enumeration
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
| `name` | String | Yes | Unique human-readable identifier for the rule | Alphanumeric with underscores | `"PSU_OV_FAULT"` |
| `id` | Integer | Yes | Unique numeric identifier for programmatic reference | 1000000-9999999 | `1000001` |
| `version` | String | Yes | Semantic version following MAJOR.MINOR.PATCH format | Semantic versioning | `"1.0.0"` |
| `description` | String | Yes | Multi-line human-readable explanation of the fault condition | Plain text, can use YAML literal block | See example above |
| `product_ids` | List | Yes | Hardware products where this rule applies | Product ID (and HW version) are defined in vendor EEPROM, format dependent on that | `["8122-64EHF-O P1"]` |
| `sw_versions` | List | Yes | SW versions where rule is validated | SW version formatting dependent on NOS, given example is for Cisco release identifier for SONiC NOS | `["202311.3.0.1"]` |
| `component` | String | Yes | Primary component category affected | `PSU`, `FAN`, `CHASSIS`, `SSD`, `CPU`, `MEMORY`, `ASIC`, `TRANSCEIVER` | `"PSU"` |
| `symptom` | String | Yes | OpenConfig Healthz fault symptom enumeration for telemetry | OpenConfig Healthz fault symptoms | `"SYMPTOM_OVER_THRESHOLD"` |
| `error_type` | String | Yes | High-level fault category published to `FAULT_INFO.error_type`. Values should use OpenConfig-defined or OpenConfig-aligned identities where available; otherwise vendors must use a stable DLDD/vendor category that UMF can translate or preserve consistently. | OpenConfig-aligned fault categories or stable vendor category strings | `"POWER"` |
| `severity` | String | Yes | DLDD rule severity used for deterministic precedence and optional SONiC/alarm metadata | `CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN` | `"CRITICAL"` |
| `priority` | Integer | No | Numeric priority for rules with matching severity and symptom (lower value = higher priority, default = 5 when omitted) | Non-negative integer | `5` |
| `tags` | List | No | Categorization tags for filtering and organization | Arbitrary strings | `["power", "voltage"]` |

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
| `logic` | String | Yes | Boolean expression defining how active fault events are combined | Boolean operators: `AND`, `OR` with event IDs | `"1 AND 2"`, `"1 OR (2 AND 3)"` |
| `logic_lookback_time` | Integer | Yes | Time window in seconds for correlating events | 0-86400 (0=instant, 86400=24 hours) | `60` (1 minute window) |
| `events` | List | Yes | Array of event definitions that can trigger the fault | Must contain at least 1 event | See Event Definition below |

#### Logic Expression Rules
- **Event References**: Use numeric IDs that match event `id` fields. Each referenced event represents a positive fault predicate.
- **Operators**: `AND`, `OR` (case sensitive)
- **Precedence**: Use parentheses for complex expressions: `"(1 OR 2) AND 3"`
- **Simple Cases**: Single event: `"1"`, Multiple events: `"1 AND 2"`
- **Time Correlation**: The events that make the boolean expression true must have active matches within `logic_lookback_time` seconds. For `OR`, only the satisfied branch must meet the window; unsatisfied branches are not required to produce matches.
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
  match_count: 1                          # Required: Number of matches needed
  match_period: 0                         # Required: Time window for matches (seconds)
```

#### Event Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `id` | Integer | Yes | Unique identifier within the signature | 1-999 (unique per signature) | `1` |
| `type` | String | Yes | Data source type determining path structure. The authoritative enum set is defined in Canonical Enum Values. | See Canonical Enum Values | `"i2c"` |
| `instances` | List | No | Device instances used for per-instance correlation and optional source binding | Format: `"DeviceName:PathIdentifier"` (if `PathIdentifier` is empty, the whole event applies to `DeviceName`) | `["PSU0:IO-MUX-6"]` |
| `path` | Object or String | Yes | Data source specification (structure varies by type) | See Path Specifications below | See examples below |
| `evaluation` | Object | Yes | Criteria for determining if fault condition is met | See Evaluation Specifications | See examples below |
| `match_count` | Integer | Yes | Number of positive evaluations needed to trigger event | 1-1000 | `1` |
| `match_period` | Integer | Yes | Time window in seconds for accumulating matches | 0-3600 (0=instant) | `0` |

#### Path Specifications by Type

Any change to the schema that results in the structure of the path content changing must update this section accordingly. A running history of older schemas and their layouts can be maintained elsewhere. Currently the below examples are for schema version: "0.0.1". The authoritative `event.type` set is defined in Canonical Enum Values; this table defines the path shape for each supported type:

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

DSE can be used both as a data source path (`event.type: dse`) and as an evaluation type (`evaluation.type: dse`). A DSE evaluation is vendor extensible: the vendor-provided DSE hook defines how the reference is resolved and what underlying platform, SDK, command, or API path is used.

When `operator` is present, DLDD applies the named operator to the event value and the DSE-resolved `value`. This allows rules to use DSE for value resolution while keeping comparison semantics visible in the rule.

When `operator` is omitted, the DSE hook must resolve the evaluation into a complete comparator/evaluator contract that DLDD can execute consistently. If neither the rule nor the DSE hook provides comparison semantics, validation fails.

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

`value_configs` is required in published DLDD telemetry and may also appear in rules anywhere a rule defines, reads, compares, or reports a value. It describes how a collected value or configured condition value should be represented for diagnostics and UMF translation. DSE-backed sources and evaluators may supply this metadata implicitly. If neither the rule nor DSE supplies metadata, DLDD uses default `N/A` metadata in telemetry rather than omitting the field.

```yaml
value_configs:
  type: "binary"                          # Required: binary, hex, int, float, string, boolean, json, bytes, or N/A
  unit: "N/A"                             # Required: unit string or "N/A"
  scaling: "N/A"                          # Optional: numeric scale factor or "N/A"
  encoding: "N/A"                         # Optional: text/binary encoding hint or "N/A"
```

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `type` | String | Yes | Representation type used for telemetry and optional value parsing. Values are defined in Canonical Enum Values. | `"binary"`, `"int"`, `"float"` |
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
| `wait_period` | Integer | Yes | Time in seconds to wait after local actions before the primary thread requests a recheck and before remote action escalation is relied on. This is a nonblocking timer for DLDD; the primary thread continues telemetry publication and monitoring of unaffected correlation keys. | Non-negative integer seconds, vendor-defined | `60` |
| `action_list` | List | Yes | Ordered sequence of vendor-defined remediation actions scheduled locally by DLDD on action worker context. Each list entry is a wrapper object containing one `action` object. The wrapped action object contains a `type` field specifying the execution method and type-specific fields for the operation. Actions are executed sequentially within the action sequence. | List of `action` wrapper objects. Supported wrapped action types: `dse`, `cli`, `i2c`, and explicit vendor-supported action types. CLI actions use `argv`. DSE actions use `command`. Direct I2C actions use `path`. | See example above |

Each action may specify `timeout` in seconds. If omitted, DLDD uses the top-level `local_action_default_timeout` from the active rules source. Validation fails for any local action that omits `timeout` when the rules source also omits `local_action_default_timeout`. A timeout marks that action as failed, records the failure in DLDD status/audit telemetry, triggers Healthz artifact collection when configured, and allows the primary thread to continue the post-action recheck path rather than leaving the correlation key held indefinitely. Artifact completion is not part of the local action result.

`local_actions` are executed by DLDD at most once per active fault lifetime for the same rule/component/symptom fault identity. Repeated event matches while the fault remains active refresh internal event history but do not start another identical local action sequence. If `local_actions` are configured, DLDD must complete the local action sequence and the subsequent `wait_period` recheck before publishing controller-visible `FAULT_INFO` fault telemetry for that fault lifetime. A clear result publishes the fault as `INACTIVE` with local action metadata so controllers can observe that DLDD detected and recovered the condition. A continued match publishes the fault as `ACTIVE` with the configured remote remediation recommendations. A new local action run is allowed only after the fault has cleared and later becomes active again, unless a future schema version defines explicit retry or cooldown fields.

#### Local Action and Query Validation Model

Schema version `0.0.1` validates local actions and log queries through type-specific contracts. Each `action_list[]` entry must be a wrapper object with an `action` member, and each `queries[]` entry must be a wrapper object with a `query` member. The required and optional fields below apply to the wrapped `action` or `query` object.

| Type | Valid Contexts | Required Fields | Optional Fields | Notes |
|------|----------------|-----------------|-----------------|-------|
| `dse` | local action, log query | `type`, `command` | `timeout` | `command` is a vendor DSE reference or command understood by the installed vendor DSE hook. DSE code and side effects are vendor-owned. |
| `cli` | local action, log query | `type`, `argv` | `timeout`, `max_output_bytes` | `argv` is executed without a shell. Shell pipelines, redirects, command substitution, and glob expansion are not valid. |
| `i2c` | local action only unless vendor explicitly enables query use | `type`, `path` | `timeout` | Direct monitoring events are read-only. Direct I2C local actions use the same target path fields as I2C event paths; write actions add a value to write. |

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

For `type: i2c` local actions, `path.bus`, `path.chip_addr`, `path.command`, and `path.size` identify the target using the same shape as the direct I2C event path. `path.i2c_type: "get"` performs a read action and records the result in action/audit metadata. `path.i2c_type: "set"` writes `path.value` to the target. More complex I2C side effects, such as read-modify-write sequences, should be modeled through vendor DSE actions unless a later schema version defines a direct structure for them.

Vendors may add implementation-specific action/query types only when the platform validator advertises support for those types. Unknown action/query types fail validation for the affected rule.

For local actions, omitted `timeout` values are filled from the top-level `local_action_default_timeout` when it is present. If an action omits `timeout` and the rules source omits `local_action_default_timeout`, validation fails for that rule. For log queries, `timeout` is optional and is not defaulted by the schema; if omitted, DLDD does not impose a schema-level query timeout, while Healthz artifact retention and storage policies still bound stored output.

**Remote Actions (Required):**
The action list uses OpenConfig Healthz fault remediation identities. `time_window` defines how long, in seconds, the controller should retain the fault history for escalation decisions; if the fault remains active throughout this window, the controller may progress to the next action in `action_list` according to controller policy.
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
| `action_list` | List | Yes | Ordered sequence of OpenConfig Healthz remediation action identities. List position becomes the remediation index published to `FAULT_INFO`. | Values listed in Canonical Enum Values | `["ACTION_RESEAT", "ACTION_COLD_REBOOT"]` |
| `time_window` | Integer | Yes | Fault history window, in seconds, used by the controller for escalation decisions. DLDD publishes the value; controller policy decides whether and when to execute actions. | Positive integer seconds | `86400` |

For the comprehensive list of OpenConfig fault actions and symptoms, refer to the [OpenConfig platform healthz fault model](https://openconfig.net/projects/models/schemadocs/yangdoc/openconfig-platform.html).

Remote action list order is the remediation index used when DLDD publishes `FAULT_INFO`. In schema version `0.0.1`, `remote_actions.action_list` is a list of action identities only. The OpenConfig remediation target defaults to the affected component instance resolved at runtime. A future schema version may add an explicit per-action target override if the remediation target and affected component need to differ.

#### Canonical Enum Values

| Field | Values | Notes |
|-------|--------|-------|
| `metadata.severity` | `CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN` | Rule-derived severity used by DLDD for deterministic ordering and optional SONiC/alarm metadata. It is not a native OpenConfig Healthz fault leaf. |
| `metadata.symptom` | OpenConfig `SYMPTOM_*` identities | Must map to the OpenConfig Healthz fault `symptom` identity. |
| `metadata.error_type` | OpenConfig-aligned fault category strings or stable vendor category strings | Published to `FAULT_INFO.error_type`. UMF owns any mapping from this value into OpenConfig or SONiC extensions. |
| `remote_actions.action_list[]` | `ACTION_RESEAT`, `ACTION_WARM_REBOOT`, `ACTION_COLD_REBOOT`, `ACTION_POWER_CYCLE`, `ACTION_FACTORY_RESET`, `ACTION_REPLACE` | OpenConfig Healthz remediation action identities. |
| `event.type` | `i2c`, `redis`, `dse`, `cli`, `file`, `sysfs`, `platform_api` | Type-specific `path` schema is defined above. |
| `evaluation.type` | `mask`, `comparison`, `string`, `boolean`, `dse` | Type-specific evaluation schema is defined above. |
| `value_configs.type` | `binary`, `hex`, `int`, `float`, `string`, `boolean`, `json`, `bytes`, `N/A` | Representation metadata for values in rules and DLDD telemetry. `N/A` is used when neither the rule nor DSE supplies more specific metadata. |
| `local_actions.action_list[].action.type` | `dse`, `cli`, `i2c`, or platform-advertised vendor-specific types | Type-specific local action schema is defined in Local Action and Query Validation Model. |


#### Schema to FAULT_INFO Translation Notes

DLDD translates vendor rules into the Redis `FAULT_INFO` payload before UMF exports OpenConfig Healthz telemetry:

- `metadata.component` plus the resolved event instance identifies the affected component. The published `component_info.name` is the canonical vendor/platform component name for the affected instance.
- `metadata.symptom` maps to the OpenConfig fault symptom. `metadata.severity` remains DLDD metadata used for ordering and diagnostics; it is not a native Healthz fault leaf.
- `metadata.error_type` maps to `FAULT_INFO.error_type`. UMF owns the OpenConfig translation for this value; vendors must keep the category stable for a given rule version.
- `remote_actions.action_list[]` maps to `repair_actions[]` in `FAULT_INFO`. List position is the remediation index, and the target defaults to the resolved affected component.
- `log_collection` maps to Healthz artifact creation. DLDD publishes an artifact identifier in `FAULT_INFO` when artifact generation is triggered, even though the artifact content may still be collected asynchronously.
- `origin_time` and `last_detection_time` are generated by DLDD at runtime as Unix epoch seconds, optionally fractional. `last_detection_time` is the last detected fault state change for the record. UMF converts these timestamps to the nanosecond representation required by OpenConfig.

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

Healthz owns artifact lifecycle and storage retention. DLDD validation confirms the log/query schema and applies query timeouts only when a query declares `timeout`; Healthz retention controls bound the stored artifact set. Artifact generation is asynchronous with respect to local action result, post-action recheck, and `FAULT_INFO` publication.

## Abstract Rule Data Source Extensions - Vendor Extensible

### What are Data Source Extensions

Abstract data source extensions (DSE) provide a way for vendors to extend the schema with granularity at the NOS level. This allows vendors to define their own detailed hardware abstractions that can be used to match against specific events and conditions, while keeping the actual rules source file standardized and uniform. Vendors are not required to implement or use DSE, but they provide a way to better simplify the rules source file and make it more maintainable. Complexity and potential variations in hardware implementations can be abstracted away from the rules source file. Actual integration and usage of the DSE will be done through a vendor implemented hook which the on-device service will operate on. If a rule references a DSE function that is not defined for the target platform, validation fails for that rule.

Data source extensions also allow for the ability to hook into NOS specific APIs and methods. A good example of this would be defining a DSE that resolves to a method to call on the SONiC platform chassis object to retrieve the PSU object, and then using that object to retrieve the PSU output voltage fault register. This allows for the reuse of existing infrastructure the NOS provides wherever possible.

### Data Source Extension Architecture
Abstract rules use symbolic references that are resolved through device-specific DSE files:

#### DSE Reference Grammar

DSE references use a single canonical form:

```text
<selector>:<function>()
{<selector>}:{<function>()}
```

The braced form is recommended when wildcards or template expansion are used. The unbraced form is accepted for simple component references.

| Element | Description | Examples |
|---------|-------------|----------|
| `selector` | Component selector or instance selector understood by the vendor DSE hook | `PSU`, `psu*`, `PSU0` |
| `function` | Vendor-defined DSE function name | `get_output_voltage_fault_register`, `get_output_voltage_failure_value` |
| `()` | Function-call marker. Arguments are not part of schema version `0.0.1`; vendors may extend through DSE data if needed. | `get_status()` |

DSE resolution is vendor extensible. A DSE path may resolve to a concrete Redis, file, sysfs, CLI, I2C, platform API, or vendor-specific source. A DSE evaluation may resolve to an expected value used with a DLDD operator or to a complete vendor-defined comparator contract. When a DSE selector expands across component instances, the resolver output must include the component instance identity for each concrete operation so DLDD can build per-instance correlation groups. Unresolved DSE references fail validation for the affected rule.

In the rules source, the event path would be defined like so:
```yaml
# Abstract rule definition
path: "{psu*}:{get_output_voltage_fault_register()}"
```

A separate datafile on the NOS would include the information needed to convert this to a queryable source of information. This translation layer is vendor specific and consumption is handled by the on-device service through a vendor implemented hook. For example, the above abstract rule could be resolved with the following:
```json
{
  "8122_64ehf-o": {
    "p1": [
      {
        "component": "psu",
        "functions": [
          {
            "name": "get_output_voltage_fault_register",
            "operation": [
              {
                "sw_versions": ["202311.3.0.1", "202311.3.0.2"],
                "platform_object": "{chassis:psu}",
                "type": "i2c",
                "bus": "{platform_object}:get_bus_addr()[0]",
                "chip_addr": "{platform_object}:get_bus_addr()[1]",
                "i2c_type": "get",
                "command": "0x7A",
                "size": "b",
                "scaling": "N/A"
              }
            ]
          },
          {
            "name": "get_output_voltage_failure_value",
            "operation": [
              {
                "sw_versions": ["202311.3.0.1", "202311.3.0.2"],
                "type": "constant",
                "value": "0b10000000"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The example fields represent:
- Product ID: `8122_64ehf-o`
- Hardware revision: `p1`
- Component: `psu`
- Function names: `get_output_voltage_fault_register`, `get_output_voltage_failure_value`
- Operation binding: the first function resolves to an I2C read and derives bus/chip address from the platform object

This is defining that, for this DSE, the process will be running an i2c read operation, deriving the target bus and chip address from the PSU object that is retrieved from the platform chassis, and using the command 0x7A to read the output voltage fault register.

### DSE Benefits
- **Hardware Abstraction**: Rules remain independent of hardware implementation details
- **SW Version Support**: Single rule supports multiple SW versions
- **Maintainability**: Hardware changes require only DSE updates
- **Reusability**: Common patterns can be shared across rules

## Schema Layout Definitions

Schema layout definitions provide the NOS with instructions on how to extract common fields from different schema versions. At its simplest, the layout is a consistently formatted JSON object that defines the underlying YAML/JSON paths used to locate the signature, event, and action objects. This is defined to simplify consumption and allow the rules source to be parsed in a consistent manner. The example below is for SONiC usage, but the same concept can be applied to any NOS. It is the responsibility of the NOS to remove unsupported schema versions from this list because specific software version identifiers can differ from vendor to vendor on the same NOS.

```json
{
  "schemas": [
    {
      "major_0": {
        "schema_data": [
          {
            "0.0.1": {
              "base_paths": {
                "rules_file": "$",
                "signature_object": "$.signatures[*].signature",
                "event_object": "$.signatures[*].signature.conditions.events[*].event",
                "actions_object": "$.signatures[*].signature.actions"
              },
              "schema_version": "$.schema_version",
              "local_action_default_timeout": "$.local_action_default_timeout",
              "signature_name": "$.signatures[*].signature.metadata.name",
              "signature_id": "$.signatures[*].signature.metadata.id",
              "signature_version": "$.signatures[*].signature.metadata.version",
              "fault_description": "$.signatures[*].signature.metadata.description",
              "fault_severity": "$.signatures[*].signature.metadata.severity",
              "fault_symptom": "$.signatures[*].signature.metadata.symptom",
              "fault_error_type": "$.signatures[*].signature.metadata.error_type",
              "rule_priority": "$.signatures[*].signature.metadata.priority",
              "supported_product_ids": "$.signatures[*].signature.metadata.product_ids",
              "supported_sw_versions": "$.signatures[*].signature.metadata.sw_versions",
              "affected_component": "$.signatures[*].signature.metadata.component",
              "tags": "$.signatures[*].signature.metadata.tags",
              "fault_logic": "$.signatures[*].signature.conditions.logic",
              "logic_lookback_time": "$.signatures[*].signature.conditions.logic_lookback_time",
              "event_id": "$.signatures[*].signature.conditions.events[*].event.id",
              "event_type": "$.signatures[*].signature.conditions.events[*].event.type",
              "event_instances": "$.signatures[*].signature.conditions.events[*].event.instances",
              "event_path": "$.signatures[*].signature.conditions.events[*].event.path",
              "event_evaluation": "$.signatures[*].signature.conditions.events[*].event.evaluation",
              "event_match_count": "$.signatures[*].signature.conditions.events[*].event.match_count",
              "event_match_period": "$.signatures[*].signature.conditions.events[*].event.match_period",
              "local_actions": "$.signatures[*].signature.actions.repair_actions.local_actions",
              "remote_actions": "$.signatures[*].signature.actions.repair_actions.remote_actions",
              "log_collection_logs": "$.signatures[*].signature.actions.log_collection.logs",
              "log_collection_queries": "$.signatures[*].signature.actions.log_collection.queries"
            }
          }
        ]
      }
    }
  ]
}
```

The schema layout map is extraction metadata for consumers that need version-specific paths. It is not a substitute for schema validation. Validation still uses the normative field definitions, path schemas, evaluator definitions, and enum tables in this document.

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
- `value_configs.type` must use the canonical enum values defined in this document
- Local actions and log queries must conform to a supported type-specific contract, including timeout handling
- Local actions that omit per-action `timeout` require a top-level rules-source `local_action_default_timeout`
- DSE evaluation references must resolve successfully. If the rule provides an `operator`, it must be compatible with the resolved value type; if the rule omits `operator`, the DSE hook must provide comparator/evaluator semantics.
- Remote activation must fail if the candidate would materialize zero usable rules for the current platform after rule-level materialization.
- Complete examples in this document should be valid YAML or JSON and should be usable as validation fixtures, but examples are not the validation authority.

### Validation Contract

Validation should be driven by versioned, machine-readable contracts rather than by prose examples. For each supported `schema_version`, the consuming NOS should provide:
- A static schema artifact, such as JSON Schema, that defines required fields, field types, enum values, allowed additional fields, and type-specific object shapes for paths, evaluations, actions, and log collection.
- Semantic validators for constraints that are not expressible cleanly in the static schema, including event ID uniqueness, `conditions.logic` parsing, `match_count`/`match_period` ranges, severity/priority ordering, and component/symptom applicability.
- DSE validators that resolve path and evaluator references against the platform DSE file and fail unresolved references.
- Evaluator validators that confirm every event produces deterministic comparison semantics.
- Compatibility validators that check product and software version applicability using the platform/NOS matching contract.

The examples in this document should be included as positive fixtures for the validator, but adding or changing examples must not be required to change validation behavior.

#### Validation Model

Validation has two tiers plus an aggregate activation guard:

1. **File-level activation gate**: Determines whether a candidate rules file is safe to parse and consider for activation. File-level failures include malformed YAML/JSON, missing or unsupported `schema_version`, invalid top-level `signatures` structure, duplicate rule IDs that make rule identity ambiguous, unsupported schema features, and any error that prevents deterministic parsing of the file. These are syntactic or file-structural failures. They reject the candidate generation and trigger rollback or retention of the previous active generation.
2. **Rule-level materialization gate**: Determines whether each individual signature can be materialized into monitor work after the file-level gate passes. Rule-level failures include unresolved DSE references, unexposed paths for the current platform, invalid source path bindings, invalid event/action/query type contracts, invalid evaluator semantics, product/SW mismatch, or a source binding that is not available for that rule. These are rule resolution, path, binding, or per-signature contract failures. They do not require rollback of the entire generation when at least one usable rule remains; the affected rule is marked broken and omitted from monitor work, while valid rules in the same generation may run.
3. **Usable-rule activation guard**: If rule-level materialization leaves zero usable rules for the current platform, activation fails even though the file-level gate passed. A no-rules execution plan is treated as a service activation failure because it would replace a working generation with no diagnostic coverage.

This split lets DLDD reject structurally unsafe candidate files while still surfacing vendor rule authoring or platform binding failures through `broken_rules` telemetry.

### Validation Process
1. **Syntax Validation**: YAML/JSON structure verification
2. **Schema Validation**: Conformance to version-specific schema, including required fields, path shapes, enum values, logic references, and type-specific action/query structures
3. **DSE Validation**: Verifies that DSE paths and DSE evaluations resolve against the platform DSE configuration
4. **Evaluator Contract Validation**: Verifies that each evaluation block can produce a deterministic evaluator, including DSE-provided comparator semantics when `evaluation.type` is `dse` and `operator` is omitted
5. **Hardware Probe Validation**: Optional non-disruptive checks that concrete sources can be sampled on the target hardware
6. **End-to-End Validation**: Optional platform qualification using controlled inputs to ensure that the rule can execute successfully without relying on live fault conditions

Remote activation requires file-level validation and rule-level materialization validation for steps 1 through 4. A file-level failure rejects the candidate generation. A rule-level failure marks the affected rule broken after promotion if the file-level gate passed and at least one usable rule remains. If no rules can be materialized for the current platform, activation fails and DLDD keeps or restores the previous active generation or fallback. Steps 5 and 6 are platform qualification modes and are not required for normal remote rule updates because some sources may exist only under certain component states or fault conditions.

It is the responsibility of the consumer to validate the underlying content of the rules source and ensure that it is compatible with the expected schema version. This does not need to be every time the consumer reads the rules, only when the rules source changes. Depending on the underlying NOS implementation, this can be done as a standalone check or integrated into the final consumer of this content. File-level validation failures reject the candidate rules file. Rule-level validation failures result in failure of the affected rule to load, allowing valid rules in the same promoted generation to run and exposing the invalid rules through service telemetry. A candidate with zero usable rules after rule-level materialization is not considered a valid active generation.

## Backward Compatibility
- **Schema Layout**: Maintain parsing instructions for all supported versions
- **Consumer Ignore**: Ensure that the consumer is able to ignore unknown fields (such as optional fields that can be added in a new minor version)

---

*This document defines the vendor-defined rules for hardware health monitoring. For implementation details of the SONiC-focused DLDD service itself, refer to the companion Device Local Diagnosis Service HLD document.*
