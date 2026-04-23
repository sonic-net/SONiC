# Label-port to Interfaces/Lanes mapping and status CLI

## Table of contents

- [Background](#1-background)
- [Method](#2-method)
- [Requirements (platform.json content)](#3-requirements-platformjson-content)
- [Error Handling](#4-error-handling)
- [Unit Tests](#5-unit-tests)
  - [Positive tests](#positive-tests)
  - [Negative tests](#negative-tests)

## 1. Background

On SONiC systems, the relationship between front-panel label ports, their physical lanes, and the correlated SONiC interface names change by platform and by breakout configuration. With more complex setups, such as multi-ASIC systems, this mapping becomes even more complicated, which raised the need for a CLI that provides a single, standardized view that shows, for each front-panel label port, how it maps to lanes and SONiC interfaces under the current split mode.

## 2. Method

1. Get Label-port → lanes mapping from platform.json.
2. Get the running ports configuration and lane splits from CONFIG_DB.
3. Get ports status from APPL_DB .
4. Create and print a table that shows the current Label-ports → ports mapping (based on the current configuration and platform lanes map).

Note - for multi-ASIC systems, the output also shows to which ASIC each port belongs to.

Example output:

Single-ASIC ( 2 x 4x)

```text
>> show interfaces label-port status

Label-port | Lane 1        | Lane 2        | Lane 3        | Lane 4
-----------|---------------|---------------|---------------|---------------
1          | Ethernet0(UP) | Ethernet0(UP) | Ethernet0(UP) | Ethernet0(UP)
2          | Ethernet4(UP) | Ethernet4(UP) | Ethernet4(UP) | Ethernet4(UP)
3          | Ethernet8(UP) | Ethernet8(UP) | Ethernet8(UP) | Ethernet8(UP)
...
128        | Ethernet508(UP) | Ethernet508(UP) | Ethernet508(DN) | Ethernet508(UP)
```

Single-ASIC ( 4 x 2x)

```text
>> show interfaces label-port status

Label-port | Lane 1        | Lane 2        | Lane 3        | Lane 4
-----------|---------------|---------------|---------------|---------------
1          | Ethernet0(UP) | Ethernet0(UP) | Ethernet2(UP) | Ethernet2(UP)
2          | Ethernet4(UP) | Ethernet4(UP) | Ethernet6(UP) | Ethernet6(UP)
3          | Ethernet8(UP) | Ethernet8(UP) | Ethernet10(UP) | Ethernet10(UP)
...
128        | Ethernet508(UP) | Ethernet508(UP) | Ethernet510(DN) | Ethernet510(UP)
```

Multi-ASIC

```text
>> show interfaces label-port status

Label-port | Lane 1              | Lane 2              | Lane 3              | Lane 4
-----------|---------------------|---------------------|---------------------|---------------------
1          | Ethernet0/asic0(UP) | Ethernet512/asic1(UP) | Ethernet1024/asic2(UP) | Ethernet1536/asic3(UP)
2          | Ethernet1/asic0(UP) | Ethernet513/asic1(UP) | Ethernet1025/asic2(UP) | Ethernet1537/asic3(UP)
3          | Ethernet2/asic0(UP) | Ethernet514/asic1(UP) | Ethernet1026/asic2(UP) | Ethernet1538/asic3(UP)
...
512        | Ethernet511/asic0(UP) | Ethernet1023/asic1(UP) | Ethernet1535/asic2(DN) | Ethernet2047/asic3(UP)
```

## 3. Requirements (platform.json content)

For all supported platforms, platform.json should be extended with:

1. label_port_lanes_mapping (object):
   a. Key: Label-port identifiers (strings, e.g., "1", "2").
   b. Values: list of lane numbers (strings, e.g., ["1", "2", "3", "4"] ).
2. For multi-ASIC platforms only - number_of_lanes_per_asic (stringified integer) - Used to compute global lane offsets on multi-ASIC systems: global_lane = local_lane + (asic_index × number_of_lanes_per_asic).

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

## 4. Error Handling

- Missing platform JSON: "No platform data found" → abort.

- Missing Label-port _lanes_mapping: "No Label-port mapping found in platform data" → abort.

- Missing/invalid number_of_lanes_per_asic on multi-ASIC: clear error → abort.

- Lane not present in mapping (mismatch): skip that lane placement; continue.

- Missing oper_status displays as DOWN.

## 5. Unit Tests

### Positive tests

- Basic single-ASIC test: renders correct header and lane placements with `<port>`(UP|DOWN).

- Basic multi-ASIC test: renders correct header and lane placements with `<port>/<asic>`(UP|DOWN).

- Mixed splits (4/2/1): lane positions reflect split sizes and ordered mapping, counts match fanout.

### Negative tests

- Platform JSON read error: returns non-zero exit and shows "No platform data found".

- Missing Label-port _lanes_mapping: returns non-zero exit and shows "No Label-port mapping found in platform data".

- Multi-ASIC missing number_of_lanes_per_asic: returns non-zero exit and shows "No number of lanes per ASIC found in platform data".

- One ASIC down (multi-ASIC): rows for the down ASIC render "-". other ASIC lanes map correctly with namespace suffix.

- Missing oper_status: port displays as DOWN.
