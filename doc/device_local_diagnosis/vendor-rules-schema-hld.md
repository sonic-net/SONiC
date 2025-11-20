# Device Local Diagnosis Rules Schema HLD

## Table of Contents

1. [Introduction](#introduction)
2. [Definitions](#definitions)
3. [Requirements](#requirements)
4. [Schema Architecture](#schema-architecture)
5. [Schema Versioning](#schema-versioning)
6. [Rule Structure](#rule-structure)
7. [Abstract Rule Data Source Extensions](#abstract-rule-data-source-extensions)
8. [Schema Layout Definitions](#schema-layout-definitions)
9. [Rule Examples](#rule-examples)
10. [Schema Validation](#schema-validation)
11. [Backward Compatibility](#backward-compatibility)

## Introduction

This document defines the schema and structure for vendor rules consumed by the Device Local Diagnosis (DLD) daemon running on SONiC switches. The rules schema provides a standardized, extensible format for defining fault detection signatures that can be consumed by the DLD daemon running on SONiC switches.

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
- **MINOR**: Backward compatible additions such as new optional fields or evaluation types
- **PATCH**: Minor corrections and clarifications

### Version Header
Every rules source file must begin with a schema version declaration:

```yaml
schema_version: "0.0.1"
```

**CRITICAL**: This header format is immutable and serves as the entry point for schema interpretation.

### Versioning and Compatability with SONiC NOS
 
The schema version does not have explicit associated DLD daemon or SW version requirements. Schema versioning is independent of the software release cycle, allowing for:

- Multiple schema versions supported by a single DLD daemon version
- Backward compatibility across software releases
- Independent evolution of schema structure and daemon implementation

The DLD daemon is responsible for handling schema version compatibility through its schema layout definitions.

## Rule Structure
At the highest level, each rules contains 3 primary sections: `metadata`, `conditions`, and `actions`. A breakdown of the content of each of these can be found below:

### Signature Metadata
Each signature contains comprehensive metadata for identification and applicability. Every field serves a specific purpose in rule processing and system integration:

- **Severity Ordering**: The `severity` field encodes the OpenConfig alarm severity (`CRITICAL`, `MAJOR`, `WARNING`, `MINOR`, `UNKNOWN`). Higher severity signatures always take precedence when multiple rules target the same component/symptom pair.
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
    symptom: "<OC symptom>"                 # Required: OpenConfig symptom enumeration
    severity: "CRITICAL"                    # Required: OpenConfig severity enumeration
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
| `component` | String | Yes | Primary component category affected | `PSU`, `FAN`, `CHASSIS`, `SSD`, `CPU`, `MEMORY` | `"PSU"` |
| `symptom` | String | Yes | OpenConfig alarm symptom enumeration for telemetry | OpenConfig defined symptoms | `"SYMPTOM_OVER_THRESHOLD"` |
| `severity` | String | Yes | OpenConfig alarm severity used for precedence | OpenConfig defined alarms | `"CRITICAL"` |
| `priority` | Integer | No | Numeric priority for rules with matching severity and symptom (lower value = higher priority, default = 5 when omitted) | Non-negative integer | `5` |
| `tags` | List | No | Categorization tags for filtering and organization | Arbitrary strings | `["power", "voltage"]` |

### Condition Logic
Conditions define the logical evaluation framework for determining when a fault has occurred. This section controls how multiple events are correlated and evaluated:

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
| `logic` | String | Yes | Boolean expression defining how events are combined | Boolean operators: `AND`, `OR`, `NOT` with event IDs | `"1 AND 2"`, `"1 OR (2 AND 3)"`, `"NOT 1"` |
| `logic_lookback_time` | Integer | Yes | Time window in seconds for correlating events | 0-86400 (0=instant, 86400=24 hours) | `60` (1 minute window) |
| `events` | List | Yes | Array of event definitions that can trigger the fault | Must contain at least 1 event | See Event Definition below |

#### Logic Expression Rules
- **Event References**: Use numeric IDs that match event `id` fields
- **Operators**: `AND`, `OR`, `NOT` (case sensitive)
- **Precedence**: Use parentheses for complex expressions: `"(1 OR 2) AND 3"`
- **Simple Cases**: Single event: `"1"`, Multiple events: `"1 AND 2"`
- **Time Correlation**: All events must occur within `logic_lookback_time` seconds

### Event Definition
Events specify individual data collection points and their evaluation criteria. Each event represents a specific check that can contribute to fault detection:

```yaml
event:
  id: 1                                    # Required: Unique identifier within signature
  type: "i2c"                             # Required: Data source type
  instances: ['PSU0:IO-MUX-6', 'PSU1:IO-MUX-7'] # Optional: Device instance DSE
  path:                                   # Required: Data source specification (varies by type)
    bus: ['IO-MUX-6', 'IO-MUX-7']        # I2C bus names (resolver notation)
    chip_addr: '0x58'                     # I2C chip address (hex format)
    i2c_type: 'get'                       # I2C operation type
    command: '0x7A'                       # I2C register/command (hex format)
    size: 'b'                             # Data size (b=byte, w=word, l=long)
    scaling: 'N/A'                        # Optional: Value scaling factor
  evaluation:                             # Required: Fault detection criteria
    type: 'mask'                          # Evaluation method
    logic: '&'                            # Logical operation for mask
    value: '10000000'                     # Comparison value (binary string)
  match_count: 1                          # Required: Number of matches needed
  match_period: 0                         # Required: Time window for matches (seconds)
```

#### Event Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `id` | Integer | Yes | Unique identifier within the signature | 1-999 (unique per signature) | `1` |
| `type` | String | Yes | Data source type determining path structure | `i2c`, `redis`, `dse`, `cli`, `sysfs`, etc | `"i2c"` |
| `instances` | List | No | Device instance, can be leveraged to identify device name or specify multiple devices to query | Format: `"DeviceName:PathIdentifier"` (if  PathIdentifier is an empty string, it will be assumed to apply to the entirety of the event) | `["PSU0:IO-MUX-6"]` |
| `path` | Object | Yes | Data source specification (structure varies by type) | See Path Specifications below | See examples below |
| `evaluation` | Object | Yes | Criteria for determining if fault condition is met | See Evaluation Specifications | See examples below |
| `match_count` | Integer | Yes | Number of positive evaluations needed to trigger event | 1-1000 | `1` |
| `match_period` | Integer | Yes | Time window in seconds for accumulating matches | 0-3600 (0=instant) | `0` |

#### Path Specifications by Type

Any change to the schema that results in the structure of the path content changing must update this section accordingly. A running history of older schemas and their layouts can be maintained elsewhere. Currently the below examples are for schema version: "0.0.1":

**I2C Path Structure:**
```yaml
path:
  bus: ['IO-MUX-6', 'IO-MUX-7']          # List of bus names (notation defined by vendor with association to instance, in this case the example is "ACPI_nickname-mux-number")
  chip_addr: '0x58'                       # Hex address of target chip
  i2c_type: 'get'                         # Operation: 'get', 'set'
  command: '0x7A'                         # Register/command in hex
  size: 'b'                               # Data size: 'b'(byte), 'w'(word), 'l'(long)
  scaling: 'N/A'                          # Scaling factor or 'N/A'
```

**Redis Path Structure:**
```yaml
path:
  database: 'STATE_DB'                    # Redis database name
  table: 'PSU_INFO'                       # Table name within database
  key: 'PSU_INFO|PSU 0'                  # Full key or template
  path: 'value/output_voltage'            # JSON path within value
```

**DSE Path Structure (Abstract):**
```yaml
path: "PSU:get_output_voltage_fault_register()"  # Abstract DSE reference
```

**CLI Path Structure:**
```yaml
path:
  command: 'lspci -vvnnt | grep a008'    # Shell command to execute
  timeout: 30                            # Optional: Command timeout in seconds
```

#### Evaluation Specifications

**Mask Evaluation (Bitwise Operations):**
```yaml
evaluation:
  type: 'mask'                            # Evaluation method
  logic: '&'                              # Bitwise operator: '&', '|', '^'
  value: 0b10000000                       # Mask value (binary string)
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

### Action Specification
Actions define the response procedures when a fault is detected. This section specifies both immediate local remediation and escalating remote actions:

```yaml
actions:
  repair_actions:
    local_actions:                        # Optional: Actions performed by DLD daemon
      wait_period: 60                     # Required if local_actions: Wait time after actions before secondary check and further escalation (seconds)
      action_list:                        # Required if local_actions: Vendor defined method calls to execute
        - action: 
            type: 'dse'
            command: 'PSU:reset_output_power()'
        - action: 
            type: 'dse'
            command: 'PSU:clear_faults()'
    remote_actions:                       # Required: Actions for remote controller
      action_list:                        # Required: Escalating sequence of actions
        - ACTION_RESEAT                   # First action: Remove and reinsert the component (if possible)
        - ACTION_COLD_REBOOT              # Second action: System reboot
        - ACTION_POWER_CYCLE              # Third action: Power cycle
        - ACTION_FACTORY_RESET            # Fourth action: Full software reimage
        - ACTION_REPLACE                  # Final action: Return material authorization
      time_window: 86400                  # Required: Duration controller tracks fault history for escalation (seconds)
  log_collection:                         # Required: Diagnostic data to collect on fault
    logs:                                 # Optional: Static log files to capture
      - log: "/var/log/platform.log"      # Log file path
      - log: "/var/log/syslog"            # System log path
    queries:                              # Optional: Dynamic data collection commands
      - query:
          type: "dse"            # Query type
          command: "PSU:get_status()"      # Platform API method to call
      - query:
          type: "cli"                     # CLI command type
          command: "show platform psu"    # CLI command to execute
```

#### Action Field Details

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `repair_actions` | Object | Yes | Container for all local and remote remedial actions | See subfields below | See example above |
| `log_collection` | Object | Yes | Diagnostic data collection specification | See subfields below | See example above |

#### Repair Actions Structure

**Local Actions (Optional):**
```yaml
local_actions:
  wait_period: 60                         # Required: Seconds to wait after executing actions
  action_list:                            # Required: List of vendor defined method calls
    - action:
        type: 'dse'               # Action type
        command: 'PSU:reset_output_power()' # Command to execute
    - action:
        type: 'dse'               # Action type
        command: 'PSU:clear_fault_register()' # Multiple actions executed in sequence
```

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `wait_period` | Integer | Yes | Time in seconds to wait after executing all local actions before allowing remote action escalation. This cooling-off period prevents rapid escalation and allows local actions to take effect. | 30-3600 (30 seconds to 1 hour) | `60` |
| `action_list` | List | Yes | Ordered sequence of vendor-defined remediation actions executed locally by the DLD daemon. Each action contains a type field specifying the execution method and a command field with the actual operation (note that the structure after the type is variable in the same way as the path block in the condition section). Actions are executed sequentially in the order specified. | List of action objects with `type` and `command` fields. Supported types: `dse`, `cli`, `i2c`, etc. | See example above |

**Remote Actions (Required):**
Below example is placeholder of OpenConfig defined enums, actual actions will be defined by associated OpenConfig model. `time_window` defines how long (in seconds) the controller should retain the fault history for escalation decisions; if the fault remains active throughout this window, the next action in `action_list` should be triggered.
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

For comprehensive list of actions, please refer to the OpenConfig fault model. Link to model: TBD


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
  - query:
      type: "cli"                         # Command line interface
      command: "show platform temperature" # Standard CLI command
  - query:
      type: "dse"                      # SDK CLI (disruptive)
      command: "CHASSIS:get_sdk_debug_dump()" # Detailed hardware dump
```

| Field | Type | Required | Description | Valid Values | Example |
|-------|------|----------|-------------|--------------|----------|
| `queries` | List | Yes | Ordered sequence of diagnostic data collection commands executed when a fault is detected. Each query contains a type field specifying the execution method and a command field with the actual operation (note that the structure after the type is variable in the same way as the path block in the condition section). Queries are executed sequentially in the order specified. Outputs/content from these queries are collected and stored within the Healthz artifact.| List of query objects with `type` and `command` fields. Supported types: `dse`, `cli`, `i2c`, etc. | See example above |

## Abstract Rule Data Source Extensions - Vendor Extensible

### What are Data Source Extensions

Abstract data source extensions (DSE) provide a way for vendors to extend the schema with granularity at the NOS level. This allows vendors to define their own detailed hardware abstractions that can be used to match against specific events and conditions, while keeping the actual rules source file standardized and uniform. Vendors are not required to implement or use DSE, but they provide a way to better simplify the rules source file and make it more maintainable. Complexity and potential variations in hardware implementations can be abstracted away from the rules source file. Actual integration and usage of the DSE will be done through a vendor implemented hook which the on-device service will operate on. If this is not defined, DSE rules will be skipped.

Data source extensions also allow for the ability to hook into NOS specific APIs and methods. A good example of this would be defining a DSE that resolves to a method to call on the SONiC platform chassis object to retrieve the PSU object, and then using that object to retrieve the PSU output voltage fault register. This allows for the reuse of existing infrastructure the NOS provides wherever possible.

### Data Source Extension Architecture
Abstract rules use symbolic references that are resolved through device-specific DSE files:

In the rules source, the event path would be defined like so:
```yaml
# Abstract rule definition
path: "{psu*}:{get_output_voltage_fault_register}"
```

A separate datafile on the NOS would include the information needed to convert this to a queryable source of information. This translation layer is vendor specific and consumption is handled by the on-device service through a vendor implemented hook. For example, the above abstract rule could be resolved with the following:
```json
// DSE file content
{
  "8122_64ehf-o": { <-- Product ID (no hw rev)
    "p1": [{ <-- Hardware revision
      "component": "psu", <-- Component
      "functions": [{
        "name": "get_output_voltage_fault_register", <-- Function Name
        "operation": [{
          "sw-version": ["202311.3.0.1", "202311.3.0.2"], <-- SW Version as Defined by Vendor
          "platform_object": "{chassis:psu}", <-- SONiC Platform Object
          "type": "i2c",
          "bus": "{platform_object}:get_bus_addr()[0]", <-- Method to retrieve bus address
          "chip_addr": "{platform_object}:get_bus_addr()[1]", <-- Method to retrieve chip address
          "i2c_type": "get", <-- I2C Operation Command Type
          "command": "0x7A", <-- I2C Command
          "scaling": "N/A" <-- Scaling Factor to Apply to Output
        }]
      }]
    }]
  }
}
```
This is defining that, for this DSE, the process will be running an i2c read operation, deriving the target bus and chip address from the PSU object that is retrieved from the platform chassis, and using the command 0x7A to read the output voltage fault register.

### DSE Benefits
- **Hardware Abstraction**: Rules remain independent of hardware implementation details
- **SW Version Support**: Single rule supports multiple SW versions
- **Maintainability**: Hardware changes require only DSE updates
- **Reusability**: Common patterns can be shared across rules

## Schema Layout Definitions

Schema layout definitions provide the NOS with instructions on how to parse different schema versions. At its simplest, its a consistently formatted JSON object that defines the underlying YAML paths that are used to define the signature, event, and action objects. This is defined to simplify the consumption process and allow for the rules source to be parsed in a consistent manner. The below example is for SONiC's usage but the same concept can be applied to any NOS. It is the responsibility of the NOS to remove unsupported schema versions from this list as specific SW version identifiers can differ from vendor to vendor on the same NOS. Example below:

```json
{
  "schemas": [{ 
    "major_0": { <-- Major version of the schema
      "schema_data": [{ <-- List of full schema versions that contains the necessary info to parse the rules source file
        "0.0.1": {
          "base_paths": { <-- Reused paths for the signature, event, and action objects
            "higher_rule_object": "signatures.signature",
            "event_rule_object": "{higher_rule_object}.conditions.events.event",
            "action_rule_object": "{higher_rule_object}.actions"
          },
          "signature_name": "{higher_rule_object}.metadata.name",
          "signature_id": "{higher_rule_object}.metadata.id",
          "fault_description": "{higher_rule_object}.metadata.description",
          "fault_severity": "{higher_rule_object}.metadata.severity",
          "rule_priority": "{higher_rule_object}.metadata.priority",
          "supported_product_ids": "{higher_rule_object}.metadata.product_ids",
          "supported_sw_versions": "{higher_rule_object}.metadata.sw_versions",
          "affected_component": "{higher_rule_object}.metadata.component",
          "fault_logic": "{higher_rule_object}.conditions.logic",
          "logic_lookback_time": "{higher_rule_object}.conditions.logic_lookback_time",
          "event_*_id": "{event_rule_object}.id",
          "event_*_type": "{event_rule_object}.type",
          "event_*_path": "{event_rule_object}.path",
          "event_*_evaluation": "{event_rule_object}.evaluation",
          "event_*_match_count": "{event_rule_object}.match_count",
          "event_*_match_period": "{event_rule_object}.match_period"
        }
      }]
    }
  }]
}
```

## Rule Examples

### Complete PSU Over-Voltage Rule

```yaml
schema_version: "0.0.1"

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
                value: '10000000'
              match_count: 1
              match_period: 0

          - event:
              id: 2
              type: dse
              path: "{psu*}:{get_output_voltage_fault_register}"
              evaluation:
                type: 'dse'
                value: "{psu*}:{get_output_voltage_failure_value}"
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
            - query: 
                type: "CLI"
                command: "show platform voltage"
```

## Schema Validation

### Validation Requirements
- Schema version must be present and valid
- All required fields must be populated
- Event IDs must be unique within a signature
- Logic expressions must reference valid event IDs
- Product IDs and SW versions must follow defined formats

### Validation Process
1. **Syntax Validation**: YAML/JSON structure verification
2. **Schema Validation**: Conformance to version-specific schema
4. **Hardware Validation**: Compatibility with target hardware
5. **End to End Validation**: End-to-end rule execution testing, ensuring that the rule can be executed successfully.

It is the responsibility of the consumer to validate the underlying content of the rules source and ensure that it is compatible with the expected schema version. This does not need to be every time the consumer reads the rules, only when the rules source changes. Depending on the underlying NOS implementation, this can be done as a standalone check or integrated into the final consumer of this content. Any failure of validation should result in a failure of the rule to load. Validation can be done at a high level or a rule by rule basis, allowing for valid formatted rules to be loaded even if some rules are invalid if the latter approach is taken. 

## Backward Compatibility
- **Schema Layout**: Maintain parsing instructions for all supported versions
- **Consumer Ignore**: Ensure that the consumer is able to ignore unknown fields (such as optional fields that can be added in a new minor version)

---

*This document defines the vendor defined rules for hardware health monitoring. For implementation details of the SONiC focused DLD daemon itself, refer to the companion Device Local Diagnosis Service HLD document.*
