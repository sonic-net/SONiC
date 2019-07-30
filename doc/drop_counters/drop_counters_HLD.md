# Configurable Drop Counters in SONiC

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Overview](#1-overview)
    - [1.1 Types of Drop Counters](#11-types-of-drop-counters)
* [2 Requirements](#2-requirements)
    - [2.1 Functional Requirements](#21-functional-requirements)
    - [2.2 Configuration and Management Requirements](#2.2-configuration-and-management-requirements)
    - [2.3 Scalability Requirements](#23-scalability-requirements)
* [3 Design](#3-design)
    - [3.1 Counters DB](#31-counters-db)
    - [3.2 Config DB](#32-config-db)
        - [3.2.1 DEBUG_COUNTER Table](#321-debug_counter-table)
        - [3.2.2 PACKET_DROP_COUNTER Table](#322-packet_drop_counter-table)
    - [3.3 App DB](#33-app-db)
    - [3.4 SWSS](#34-swss)
    - [3.5 CLI](#35-CLI)
        - [3.5.1 CLI show](#351-cli-show)
        - [3.5.2 CLI clear](#352-cli-clear)
        - [3.5.3 CLI configuration](#353-cli-configuration)
* [4 Flows](#4-flows)
    - [4.1 General Flow](#41-general-flow)
* [5 Unit Tests](#5-unit-tests)
* [6 Open Questions](#6-open-questions)



# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)
* [Table 2: Types of Drop Counters](#11-types-of-drop-counters)

# List of Figures
* [Figure 1: General Flow](#41-general-flow)

# Revision
| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 07/30/19 | Danny Allen | Initial version    |

# About this Manual
This document provides an overview of the implementation of configurable packet drop counters in SONiC.

# Scope
This document describes the high level design of the configurable drop counter feature.

# Definitions/Abbreviation
| Abbreviation | Description     |
|--------------|-----------------|
| RX           | Receive/ingress |
| TX           | Transmit/egress |

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
    1. Supported drop reasons will be available in App DB
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
The contents of the drop counters will be added to Counters DB by flex counters.

## 3.2 Config DB
We'll add two new tables to Config DB:
* DEBUG_COUNTER to track which counters have been configured and for what purpose
    * At this point the only supported type is PACKET_DROP
* PACKET_DROP_COUNTER to save drop counters that have been configured by the user

### 3.2.1 DEBUG_COUNTER Table
Example:
```
{
    "DEBUG_COUNTER": {
        "DEBUG_0": {
            "configured": true,
            "type": "PACKET_DROP"
        },
        "DEBUG_1": {
            "configured": true,
            "type": "PACKET_DROP"
        },
        "DEBUG_2": {
            "configured": true,
            "type": "PACKET_DROP"
        },
        "DEBUG_3": {
            "configured": false
        }
    }
}
```

### 3.2.2 PACKET_DROP_COUNTER Table
Example:
```
{
    "PACKET_DROP_COUNTER": {
        "LEGAL_RX_DROPS": {
            "counter": "DEBUG_0",
            "type": "ingress",
            "reasons": [
                SMAC_EQUALS_DMAC,
                INGRESS_VLAN_FILTER
            ],
            "desc": "Legal RX pipeline drops"
        },
        "LEGAL_TX_DROPS": {
            "counter": "DEBUG_1",
            "type": "egress",
            "reasons": [
                EGRESS_VLAN_FILTER
            ],
            "desc": "Legal TX pipeline drops"
        }
    }
}
```

## 3.3 App DB
App DB will store information about:
* Whether drop counters are available on this device
* How many drop counters are available on this device
* What drop reasons are supported by this device

## 3.4 SWSS
Portorch should be extended to support a variable number of SAI_PORT_STAT_IN/OUT_DROP_REASON counters.

Debugcountsorch should be implemented to handle debug counter creation and configuration.

## 3.5 CLI
The CLI tool will provide the following functionality:
* Show drop counts: ```show drops```
* Clear drop counters: ```clear drops```
* See drop counter config: ```show drops config```
* Initialize a new drop counter: ```config drops init```
* Add drop reasons to a drop counter: ```config drops add```
* Remove drop reasons from a drop counter: ```config drops remove```
* Delete a drop counter: ```config drops delete```

### 3.5.1 CLI show

```
$ show drops
     IFACE    STATE    RX_ERR    RX_DRP    RX_DISC    RX_LEGAL    TX_ERR    TX_DRP    TX_DISC    TX_LEGAL
----------  -------  --------  --------  ---------  ----------  --------  --------  ---------  ----------
 Ethernet0        U        0         0       1500        1500         0         0          0           0
 Ethernet4        U        0         0        300         250         0         0          0           0
 Ethernet8        U        0         0          0           0         0         0          0           0
Ethernet12        U        0         0       1200         400         0         0          0           0

$ show drops --include "LEGAL"
     IFACE    STATE    RX_LEGAL    TX_LEGAL
----------  -------  ----------  ---------- 
 Ethernet0        U           0           0       
 Ethernet4        U           0           0       
 Ethernet8        U           0           0          
Ethernet12        U           0           0       
```

### 3.5.2 CLI clear
```
$ clear drops
$ clear drops RX_LEGAL
$ clear drops RX_LEGAL TX_LEGAL
```

### 3.5.3 CLI Configuration
```
$ show drops config
Drop Counters: supported
Available Counters: 3

Name      Type     Reasons              Description
--------  -------  -------------------  --------------
RX_LEGAL  ingress  SMAC_EQUALS_DMAC     Legal RX pipeline drops
                   INGRESS_VLAN_FILTER
TX_LEGAL   egress  EGRESS_VLAN_FILTER   Legal TX pipeline drops
DEBUG_2      OPEN                 NONE  Available debug counter
 
$ config drops init --counter=DEBUG_2 --name=EXAMPLE --type=ingress --desc="example"
Initializing DEBUG_2 as EXAMPLE...
DONE!

Name      Type     Reasons              Description
--------  -------  -------------------  --------------
EXAMPLE   ingress                 NONE  example

$ config drops add --counter=EXAMPLE --reasons="SMAC_MULTICAST,DMAC_RESERVED"
Configuring EXAMPLE...
DONE!

Name      Type     Reasons              Description
--------  -------  -------------------  --------------
EXAMPLE   ingress       SMAC_MULTICAST  example
                        DMAC_RESERVED

$ config drops remove --counter=EXAMPLE --reasons="DMAC_RESERVED"
Configuring EXAMPLE...
DONE!

Name      Type     Reasons              Description
--------  -------  -------------------  --------------
EXAMPLE   ingress       SMAC_MULTICAST  example

$ config drops delete --counter=EXAMPLE
Deleting EXAMPLE...
DONE!
```

# 4 Flows
## 4.1 General Flow
![alt text](./drop_counters_general_flow.png)
The overall workflow is shown above in figure 1.

(1) Users configure drop counters using the CLI. Configurations are stored in the PACKET_DROP_COUNTER Config DB table.

(2) The debug counts orchagent subscribes to the Config DB table. Once the configuration changes, the orchagent uses the debug SAI API to configure the drop counters.

(3) The debug counts orchagent publishes counter configurations to Flex Counter DB.

(4) Syncd subscribes to Flex Counter DB and sets up flex counters. Flex counters periodically query ASIC counters and publishes data to Counters DB.

(5) CLI uses counters DB to satisfy CLI requests.

(6) (not shown) CLI uses App DB to display hardware capabilities (e.g. how many counters are available, supported drop reasons, etc.)

# 5 Unit Tests
A separate test plan will be uploaded and reviewed by the community.

# 6 Open Questions
* There's still an open question in the SAI proposal over whether counter indices will be managed by the SAI or the user. This doc is currently written as if the user is managing the indices, but if this changes then the design (specifically, the Config DB schema) will need to be revised.