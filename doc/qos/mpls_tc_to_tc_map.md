# MPLS TC to TC map

## 1. Table of Content

- [MPLS TC to TC map](#mpls-tc-to-tc-map)
  - [1. Table of Content](#1-table-of-content)
  - [2. Revision](#2-revision)
  - [3. Scope](#3-scope)
  - [4. Definitions/Abbreviations](#4-definitionsabbreviations)
  - [5. Overview](#5-overview)
  - [6. Requirements](#6-requirements)
  - [7. Architecture Design](#7-architecture-design)
  - [8. High-Level Design](#8-high-level-design)
    - [8.1. DB](#81-db)
    - [8.2. sonic-swss-common](#82-sonic-swss-common)
    - [8.3. sonic-swss](#83-sonic-swss)
    - [8.4. sonic-utilities](#84-sonic-utilities)
    - [8.5. Other implications](#85-other-implications)
  - [9. SAI API](#9-sai-api)
  - [10. Configuration and management](#10-configuration-and-management)
    - [10.1. CLI/YANG model Enhancements](#101-cliyang-model-enhancements)
    - [10.2. Config DB Enhancements](#102-config-db-enhancements)
  - [11. Warmboot and Fastboot Design Impact](#11-warmboot-and-fastboot-design-impact)
  - [12. Restrictions/Limitations](#12-restrictionslimitations)
  - [13. Testing Requirements/Design](#13-testing-requirementsdesign)
    - [13.1. Unit Test cases](#131-unit-test-cases)
    - [13.2. System Test cases](#132-system-test-cases)
  - [14. Open/Action items - if any](#14-openaction-items---if-any)

## 2. Revision

| Rev |     Date    |       Author            | Change Description                         |
|:---:|:-----------:|:-----------------------:|--------------------------------------------|
| 0.1 | 16/08/2021  |     Alexandru Banu      | Initial version                            |
| 0.2 | 21/09/2021  |     Alexandru Banu      | Renamed MPLS EXP to MPLS TC per RFC 5462   |
| 0.3 | 22/09/2021  |     Alexandru Banu      | Added per-port binding configuration       |

## 3. Scope

This HLD extends SONiC to support MPLS TC to TC mappings.

## 4. Definitions/Abbreviations

TC = Traffic Class
QoS = Quality of Service

## 5. Overview

This new enhancement adds support to SONiC for MPLS TC to TC map which allows QoS to work on MPLS packets.

## 6. Requirements

User can configure MPLS TC to TC map at start-of-day via configuration file. CLI support will exist to offer the same amount of support as for DSCP to TC map.

## 7. Architecture Design

The overall SONiC architecture will not be changed and no new sub-modules will be introduced.

## 8. High-Level Design

### 8.1. DB

The CONFIG DB will be updated to include a new "MPLS_TC_TO_TC_MAP" similar to the existing "DSCP_TO_TC_MAP". This will have the following format:
```
### MPLS_TC_TO_TC_MAP
    ; MPLS TC to TC map
    ;SAI mapping - qos_map object with SAI_QOS_MAP_ATTR_TYPE == sai_qos_map_type_t::SAI_QOS_MAP_MPLS_EXP_TO_TC
    key        = "MPLS_TC_TO_TC_MAP|"name
    ;field    value
    mpls_tc_value = 1*DIGIT
    tc_value      = 1*DIGIT

    Example:
    127.0.0.1:6379> hgetall "MPLS_TC_TO_TC_MAP|Mpls_tc_to_tc_map1"
     1) "3" ;mpls tc
     2) "3" ;tc
     3) "6"
     4) "5"
     5) "7"
     6) "5"
```

In order to allow a user to bind such a map to a port, the existing `PORT_QOS_MAP` table will be enhanced to allow a new field-value pair, where the field is going to be named `mpls_tc_to_tc_map` and the value will be the `MPLS_TC_TO_TC_MAP.key` of the map to use.

### 8.2. sonic-swss-common

sonic-swss-common's schema will be updated to include a CFG_MPLS_TC_TO_TC_MAP_TABLE_NAME define for the new table name.

### 8.3. sonic-swss

sonic-swss's QoS orch will be updated to include a new handler for MPLS TC to TC map, similar to the existing DSCP to TC map but with extra input validations, checking that the values are in the correct numeric range and that no MPLS TC value is mapped to more than one TC value. Among debugging logs, appropriate error logs will be introduced to let the user know if they miss-configured a map.

Also, the QoS orch will be enhanced to configure the new field-value pair in `PORT_QOS_MAP` mentioned at section 8.1.

### 8.4. sonic-utilities

sonic-utilities will be updated to offer the same amount of support for CLI commands that DSCP to TC map already provide.

### 8.5. Other implications

There are no other implications. SAI and sairedis already support for MPLS TC to TC map. In terms of warm restart / fastboot / scalability / performance and so on, this should not represent an impact.

## 9. SAI API

MPLS TC to TC map are already supported in SAI.

## 10. Configuration and management

### 10.1. CLI/YANG model Enhancements

CLI config commands will be updated to include the same level of support for MPLS TC to TC maps as for DSCP to TC maps. Namely, `config reload` and `config clear` will be updated to include the new mapping table as well.

### 10.2. Config DB Enhancements

The relevant changes have been described in HLD's DB sub-section.

## 11. Warmboot and Fastboot Design Impact

Not impacted by the changes.

## 12. Restrictions/Limitations

- User can't configure MPLS TC to TC map via CLI (only via reload command).
- User can't configure per-switch or per-inseg MPLS TC to TC maps.

## 13. Testing Requirements/Design

### 13.1. Unit Test cases

The QoS UTs present in sonic-swss will be extended to accommodate the new MPLS TC to TC map. These will largely follow the DSCP to TC map example but will add input validation checks as well. The new code will have full code coverage as far as the UT framework allows it.

### 13.2. System Test cases

No system test cases will be added.

## 14. Open/Action items - if any

N/A
