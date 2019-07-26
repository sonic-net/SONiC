# Configurable Drop Counters in SONiC

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)

# List of Tables
Placeholder

# Revision
| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 07/24/19 | Danny Allen | Initial version    |

# About this Manual
This document provides an overview of the implementation of configurable packet drop counters in SONiC.

# Scope
This document describes the high level design of the configurable drop counter feature.

# Definitions/Abbreviation
Placeholder

# 1 Overview
The goal of this feature is to provide better packet drop visibility in SONiC by providing a mechanism to count and classify packet drops that occur due to different reasons. Because different types of packet drops are important to track in different use cases, it is also key for this feature to be easily configurable.

## 1.1 Types of Drop Counters
| Drop Category                | SAI Counter                                  | Configurable? |
|------------------------------|----------------------------------------------|:-------------:|
| RX Layer-2 packet corruption | SAI_PORT_STAT_IF_IN_ERRORS                   | No            |
| TX Layer-2 packet corruption | SAI_PORT_STAT_IF_OUT_ERRORS                  | No            |
| RX MMU packet drop           | SAI_PORT_STAT_IF_IN_DROPPED_PKTS             | No            |
| TX MMU packet drop           | SAI_PORT_STAT_IF_OUT_DROPPED_PKTS            | No            |
| All RX pipeline drops        | SAI_PORT_STAT_IF_IN_DISCARDS                 | No            |
| All TX pipeline drops        | SAI_PORT_STAT_IF_OUT_DISCARDS                | No            |
| Specified RX pipeline drops  | SAI_DEBUG_COUNTER_TYPE_PORT_IN_DROP_REASONS  | Yes           |
| Specified TX pipeline drops  | SAI_DEBUG_COUNTER_TYPE_PORT_OUT_DROP_REASONS | Yes           |

# 2 Requirements

## 2.1 Functional Requirements
1. Users can configure debug counters to track one or more drop reason(s).
    1. Supported ingress drop reasons are specified in sai_port_in_drop_reason_t.
    2. Supported egress drop reasons are specified in sai_port_out_drop_reason_t.
2. Users can access debug counter information via a CLI command
    1. Users can see what types of drops each counter contains
    2. Users can assign aliases to counters
    3. Users can clear counters

## 2.2 Configuration and Management Requirements
Configuration of the drop counters can be done via:
* CLI
* JSON input

## 2.3 Scalability Requirements
Users must be able to use all counters and drop reasons provided by the underlying hardware.

# 3 Design

## 3.1 Counters DB
The contents of the drop counters will be added to Counters DB by the port stat flex counters.

## 3.2 Config DB
We'll add a new table to Config DB to save counters that have been configured by the user.

### 3.2.1 DROP_COUNTER Table
Example:
```
{
    "DROP_COUNTER": {
        "LEGAL_RX_DROPS": {
            "offset": "0",
            "type": "ingress",
            "reasons": [
                SAI_PORT_IN_DROP_REASON_SMAC_EQUALS_DMAC,
                SAI_PORT_IN_DROP_REASON_INGRESS_VLAN_FILTER
            ]
        },
        "LEGAL_TX_DROPS": {
            "offset": "1",
            "type": "egress",
            "reasons": [
                SAI_PORT_IN_DROP_REASON_EGRESS_VLAN_FILTER
            ]
        }
    }
}
```

## 3.3 State DB
State DB will store information about:
* Whether drop counters are available on this device
* How many drop counters are available on this device
* What drop reasons are supported on this device

## 3.4 SWSS (WIP)
Drop counter orch should be implemented with following functionality:
* Handle drop counter configuration
* Handle requests to clear drop counters

## 3.5 CLI (WIP)