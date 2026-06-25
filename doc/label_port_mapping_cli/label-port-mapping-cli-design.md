# Label-port to Interfaces/Lanes mapping CLI

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
  - [Manifest (if the feature is an Application Extension)](#manifest-if-the-feature-is-an-application-extension)
  - [CLI/YANG model Enhancements](#cliyang-model-enhancements)
  - [Config DB Enhancements](#config-db-enhancements)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
  - [Warmboot and Fastboot Performance Impact](#warmboot-and-fastboot-performance-impact)
- [Memory Consumption](#memory-consumption)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
  - [Unit Test cases](#unit-test-cases)
  - [System Test cases](#system-test-cases)
- [Open/Action items - if any](#openaction-items---if-any)

### Revision


| Rev | Date       | Author       | Change Description |
| --- | ---------- | ------------ | ------------------ |
| 1   | 06/09/2026 | Zili Bombach | Initial version    |


### Scope

This document covers the design of the read-only `show interfaces label-port status` CLI, including platform.json mapping requirements and multi-ASIC display behavior.
Config commands are out of scope.

### Definitions/Abbreviations

### Overview

On SONiC systems, the relationship between front-panel label ports, their physical lanes, and the correlated SONiC interface names changes by platform and by breakout configuration. With more complex setups, such as multi-ASIC systems, this mapping becomes even more complicated, which raised the need for a CLI that provides a single, standardized view that shows, for each front-panel label port, how it maps to lanes and SONiC interfaces under the current split mode.

### Requirements

- Provide a read-only CLI (`show interfaces label-port status`) that maps each front-panel label port to its lanes, SONiC interfaces, and operational status under the current breakout configuration.
- Support single-ASIC and multi-ASIC platforms.
- Require platform vendors to supply `label_port_lanes_mapping` in platform.json; multi-ASIC platforms also require `number_of_lanes_per_asic` (see [Requirements (platform.json content)](#requirements-platformjson-content)).

### Architecture Design

### High-Level Design

1. Get Label-port → lanes mapping from platform.json.
2. Get the running ports configuration and lane splits from CONFIG_DB.
3. Get port status from APPL_DB.
4. Create and print a table that shows the current label-port → ports mapping (based on the current configuration and platform lanes map).

Note - for multi-ASIC systems, the output also shows to which ASIC each port belongs to.

Example output:

Single-ASIC (2 x 4x)

```text
>> show interfaces label-port status

Label Port | Lane 1        | Lane 2        | Lane 3        | Lane 4
-----------|---------------|---------------|---------------|---------------
1          | Ethernet0(UP) | Ethernet0(UP) | Ethernet0(UP) | Ethernet0(UP)
2          | Ethernet4(UP) | Ethernet4(UP) | Ethernet4(UP) | Ethernet4(UP)
3          | Ethernet8(UP) | Ethernet8(UP) | Ethernet8(UP) | Ethernet8(UP)
...
128        | Ethernet508(UP) | Ethernet508(UP) | Ethernet508(DOWN) | Ethernet508(UP)
```

Single-ASIC (4 x 2x)

```text
>> show interfaces label-port status

Label Port | Lane 1        | Lane 2        | Lane 3        | Lane 4
-----------|---------------|---------------|---------------|---------------
1          | Ethernet0(UP) | Ethernet0(UP) | Ethernet2(UP) | Ethernet2(UP)
2          | Ethernet4(UP) | Ethernet4(UP) | Ethernet6(UP) | Ethernet6(UP)
3          | Ethernet8(UP) | Ethernet8(UP) | Ethernet10(UP) | Ethernet10(UP)
...
128        | Ethernet508(UP) | Ethernet508(UP) | Ethernet510(DOWN) | Ethernet510(UP)
```

Multi-ASIC

```text
>> show interfaces label-port status

Label Port | Lane 1              | Lane 2              | Lane 3              | Lane 4
-----------|---------------------|---------------------|---------------------|---------------------
1          | Ethernet0|asic0(UP) | Ethernet512|asic1(UP) | Ethernet1024|asic2(UP) | Ethernet1536|asic3(UP)
2          | Ethernet1|asic0(UP) | Ethernet513|asic1(UP) | Ethernet1025|asic2(UP) | Ethernet1537|asic3(UP)
3          | Ethernet2|asic0(UP) | Ethernet514|asic1(UP) | Ethernet1026|asic2(UP) | Ethernet1538|asic3(UP)
...
512        | Ethernet511|asic0(UP) | Ethernet1023|asic1(UP) | Ethernet1535|asic2(DOWN) | Ethernet2047|asic3(UP)
```

#### Requirements (platform.json content)

For all supported platforms, platform.json should be extended with:

1. label_port_lanes_mapping (object):
  a. Key: Label-port identifiers (strings, e.g., "1", "2").
   b. Values: list of lane numbers (strings, e.g., ["0", "1", "2", "3"] ).
2. For multi-ASIC platforms only - number_of_lanes_per_asic - Used to compute global lane offsets on multi-ASIC systems: global_lane = local_lane + (asic_index × number_of_lanes_per_asic).

Example:

platform.json

```json
// Single-ASIC

"label_port_lanes_mapping": {
   "1": ["0", "1", "2", "3"],
   "2": ["4", "5", "6", "7"],
   ...
   "127": ["504", "505", "506", "507"],
   "128": ["508", "509", "510", "511"]
}
```

```json
// Multi-ASIC

"number_of_lanes_per_asic": "512",
"label_port_lanes_mapping": {
   "1": ["0", "512", "1024", "1536"],
   "2": ["1", "513", "1025", "1537"],
   ...
   "511": ["510", "1022", "1534", "2046"],
   "512": ["511", "1023", "1535", "2047"]
}
```

#### Error Handling

- Missing platform JSON: "No platform data found" → abort.
- Missing `label_port_lanes_mapping` in platform.json: "No Label-port mapping found in platform data" → abort.
- Missing/invalid `number_of_lanes_per_asic` on multi-ASIC: "No number of lanes per ASIC found in platform data" → abort.
- Lane not present in mapping (mismatch): skip that lane placement; cell displays `-`; continue.
- Missing oper_status displays as DOWN.

### SAI API

### Configuration and management

#### Manifest (if the feature is an Application Extension)

#### CLI/YANG model Enhancements

#### Config DB Enhancements

### Warmboot and Fastboot Design Impact

#### Warmboot and Fastboot Performance Impact

### Memory Consumption

### Restrictions/Limitations

### Testing Requirements/Design

#### Unit Test cases

##### Positive tests

- Basic single-ASIC test: renders correct header and lane placements with `<port>`(UP|DOWN).
- Basic multi-ASIC test: renders correct header and lane placements with `<port>|<asic>`(UP|DOWN).
- Mixed splits (4/2/1): lane positions reflect split sizes and ordered mapping, counts match fanout.

##### Negative tests

- Platform JSON read error: returns non-zero exit and shows "No platform data found".
- Missing `label_port_lanes_mapping` in platform.json: returns non-zero exit and shows "No Label-port mapping found in platform data".
- Multi-ASIC missing number_of_lanes_per_asic: returns non-zero exit and shows "No number of lanes per ASIC found in platform data".
- One ASIC down (multi-ASIC): rows for the down ASIC render "-". other ASIC lanes map correctly with namespace suffix.
- Missing oper_status: port displays as DOWN.

#### System Test cases

### Open/Action items - if any

