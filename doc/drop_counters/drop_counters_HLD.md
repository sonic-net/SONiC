# Configurable Drop Counters in SONiC

# High Level Design Document
#### Rev 0.2

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Overview](#1-overview)
* [2 Requirements](#2-requirements)
    - [2.1 Functional Requirements](#21-functional-requirements)
    - [2.2 Configuration and Management Requirements](#2.2-configuration-and-management-requirements)
    - [2.3 Scalability Requirements](#23-scalability-requirements)
    - [2.4 Supported Debug Counters](#24-supported-debug-counters)
* [3 Design](#3-design)
    - [3.1 CLI (and usage example)](#31-cli-and-usage-example)
        - [3.1.1 Displaying available counter capabilities](#311-displaying-available-counter-capabilities)
        - [3.1.2 Displaying current counter configuration](#312-displaying-current-counter-configuration)
        - [3.1.3 Displaying the current counts](#313-displaying-the-current-counts)
        - [3.1.4 Clearing the counts](#314-clearing-the-counts)
        - [3.1.5 Configuring counters from the CLI](#315-configuring-counters-from-the-CLI)
    - [3.2 Config DB](#32-config-db)
        - [3.2.1 DEBUG_COUNTER Table](#321-debug_counter-table)
        - [3.2.2 PACKET_DROP_COUNTER_REASON Table](#322-packet_drop_counter_reason-table)
    - [3.3 State DB](#33-state-db)
        - [3.3.1 DEBUG_COUNTER_CAPABILITIES Table](#331-debug-counter-capabilities-table)
        - [3.3.2 SAI APIs](#332-sai-apis)
    - [3.4 Counters DB](#34-counters-db)
    - [3.5 SWSS](#35-swss)
        - [3.5.1 SAI APIs](#351-sai-apis)
    - [3.6 syncd](#34-syncd)
* [4 Flows](#4-flows)
    - [4.1 General Flow](#41-general-flow)
* [5 Warm Reboot Support](#5-warm-reboot-support)
* [6 Unit Tests](#6-unit-tests)
* [7 Open Questions](#7-open-questions)



# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# List of Figures
* [Figure 1: General Flow](#41-general-flow)

# Revision
| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 07/30/19 | Danny Allen | Initial version    |
| 0.2 | 09/03/19 | Danny Allen | Review updates     |

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
The main goal of this feature is to provide better packet drop visibility in SONiC by providing a mechanism to count and classify packet drops that occur due to different reasons. 

The other goal of this feature is for users to be able to track the types of drop reasons that are important for their scenario. Because different users have different priorities, and because priorities change over time, it is important for this feature to be easily configurable.

We will accomplish both goals by adding support for SAI debug counters to SONiC. 
* Support for creating and configuring port-level and switch-level debug counters will be added to orchagent and syncd. 
* A CLI tool will be provided for users to manage and configure their own drop counters

# 2 Requirements

## 2.1 Functional Requirements
1. CONFIG_DB can be configured to create debug counters
2. STATE_DB can be queried for debug counter capabilities
3. Users can access drop counter information via a CLI tool
    1. Users can see what capabilities are available to them
        1. Types of counters (i.e. port-level and/or switch-level)
        2. Number of counters
        3. Supported drop reasons
    2. Users can see what types of drops each configured counter contains
    3. Users can add and remove drop reasons from each counter
    4. Users can read the current value of each counter
    5. Users can assign aliases to counters
    6. Users can clear counters

## 2.2 Configuration and Management Requirements
Configuration of the drop counters can be done via:
* config_db.json 
* minigraph.xml
* CLI

## 2.3 Scalability Requirements
Users must be able to use all debug counters and drop reasons provided by the underlying hardware.

Interacting with debug counters will not interfere with existing hardware counters (e.g. portstat). Likewise, interacting with existing hardware counters will not interfere with debug counter behavior.

## 2.4 Supported Debug Counters
* PORT_INGRESS_DROPS: port-level ingress drop counters
* PORT_EGRESS_DROPS: port-level egress drop counters
* SWITCH_INGRESS_DROPS: switch-level ingress drop counters
* SWITCH_EGRESS_DROPS: switch-level egress drop counters

# 3 Design

## 3.1 CLI (and usage example)
The CLI tool will provide the following functionality:
* See available drop counter capabilities: `show drops available`
* See drop counter config: `show drops config`
* Show drop counts: `show drops`
* Clear drop counters: `sonic-clear drops`
* Initialize a new drop counter: `config drops init`
* Add drop reasons to a drop counter: `config drops add`
* Remove drop reasons from a drop counter: `config drops remove`
* Delete a drop counter: `config drops delete`

### 3.1.1 Displaying available counter capabilities
```
$ show drops available
          TYPE  FREE  IN-USE
--------------  ----  ------
  PORT_INGRESS     2       1
   PORT_EGRESS     2       1
SWITCH_INGRESS     1       1
 SWITCH_EGRESS     2       0

PORT_INGRESS:
    L2_ANY
    SMAC_MULTICAST
    SMAC_EQUALS_DMAC
    INGRESS_VLAN_FILTER
    EXCEEDS_L2_MTU
    SIP_CLASS_E
    SIP_LINK_LOCAL
    DIP_LINK_LOCAL
    UNRESOLVED_NEXT_HOP
    DECAP_ERROR

PORT_EGRESS:
    L2_ANY
    L3_ANY
    A_CUSTOM_REASON

SWITCH_INGRESS:
    L2_ANY
    SMAC_MULTICAST
    SMAC_EQUALS_DMAC
    SIP_CLASS_E
    SIP_LINK_LOCAL
    DIP_LINK_LOCAL

SWITCH_EGRESS:
    L2_ANY
    L3_ANY
    A_CUSTOM_REASON
    ANOTHER_CUSTOM_REASON

$ show drops available --type=PORT_EGRESS
          TYPE  TOTAL FREE  IN-USE
--------------  ----- ----  ------
   PORT_EGRESS      3    2       1

PORT_EGRESS:
    L2_ANY
    L3_ANY
    A_CUSTOM_REASON

```

### 3.1.2 Displaying current counter configuration
```
$ show drops config
Counter   Alias     Group  Type            Reasons              Description
--------  --------  -----  --------------  -------------------  --------------
DEBUG_0   RX_LEGIT  LEGIT  PORT_INGRESS    SMAC_EQUALS_DMAC     Legitimate port-level RX pipeline drops
                                           INGRESS_VLAN_FILTER
DEBUG_1   TX_LEGIT  LEGIT  PORT_EGRESS     EGRESS_VLAN_FILTER   Legitimate port-level TX pipeline drops
DEBUG_2   RX_LEGIT  LEGIT  SWITCH_INGRESS  TTL                  Legitimate switch-level RX pipeline drops
```

### 3.1.3 Displaying the current counts

```
$ show drops
          IFACE    STATE      RX_ERR     RX_DRP    RX_DISC    RX_LEGIT    TX_ERR    TX_DRP    TX_DISC    TX_LEGIT
---------------  -------  ----------   --------  ---------  ----------  --------  --------  ---------  ----------
      Ethernet0        U           0          0       1500        1500         0         0          0           0
      Ethernet4        U           0          0        300         250         0         0          0           0
      Ethernet8        U           0          0          0           0         0         0          0           0
     Ethernet12        U           0          0       1200         400         0         0          0           0

         DEVICE    STATE    RX_LEGIT  
---------------  -------  ----------  
ABCDEFG-123-XYZ        U        2000

$ show drops --type=PORT
     IFACE    STATE    RX_ERR    RX_DRP    RX_DISC    RX_LEGIT    TX_ERR    TX_DRP    TX_DISC    TX_LEGIT
----------  -------  --------  --------  ---------  ----------  --------  --------  ---------  ----------
 Ethernet0        U        0         0       1500        1500         0         0          0           0
 Ethernet4        U        0         0        300         250         0         0          0           0
 Ethernet8        U        0         0          0           0         0         0          0           0
Ethernet12        U        0         0       1200         400         0         0          0           0

$ show drops --group "LEGIT"
          IFACE    STATE    RX_LEGIT    TX_LEGIT
---------------  -------  ----------  ---------- 
      Ethernet0        U           0           0       
      Ethernet4        U           0           0       
      Ethernet8        U           0           0          
     Ethernet12        U           0           0 

         DEVICE    STATE    RX_LEGIT
---------------  -------  ----------  
ABCDEFG-123-XYZ        U        2000
```

### 3.1.4 Clearing the counts
```
$ sonic-clear drops
```

### 3.1.5 Configuring counters from the CLI
```
$ config drops init --counter="DEBUG_3" --alias="TX_LEGIT" --group="LEGIT" --type="SWITCH_EGRESS" --desc="Legitimate switch-level TX pipeline drops" --reasons=["L2_ANY", "L3_ANY"]
Initializing DEBUG_3 as TX_LEGIT...

Counter   Alias     Group  Type           Reasons  Description
-------   --------  -----  -------------  -------  -----------
DEBUG_3   TX_LEGIT  LEGIT  SWITCH_EGRESS  L2_ANY   Legitimate switch-level TX pipeline drops
                                          L3_ANY

$ config drops add --counter="DEBUG_3" --reasons=["A_CUSTOM_REASON", "ANOTHER_CUSTOM_REASON"]
Configuring DEBUG_3...

Counter   Alias     Group  Type           Reasons                Description
-------   --------  -----  -------------  -------                -----------
DEBUG_3   TX_LEGIT  LEGIT  SWITCH_EGRESS  L2_ANY                 Legitimate switch-level TX pipeline drops
                                          L3_ANY
                                          A_CUSTOM_REASON
                                          ANOTHER_CUSTOM_REASON

$ config drops remove --counter="DEBUG_3" --reasons=["A_CUSTOM_REASON"]
Configuring DEBUG_3...

Counter   Alias     Group  Type           Reasons                Description
-------   --------  -----  -------------  -------                -----------
DEBUG_3   TX_LEGIT  LEGIT  SWITCH_EGRESS  L2_ANY                 Legitimate switch-level TX pipeline drops
                                          L3_ANY
                                          ANOTHER_CUSTOM_REASON

$ config drops delete --counter="DEBUG_3"
```

## 3.2 Config DB
Two new tables will be added to Config DB:
* DEBUG_COUNTER to store general debug counter metadata
* DEBUG_COUNTER_DROP_REASON to store drop reasons for debug counters that have been configured to track packet drops

### 3.2.1 DEBUG_COUNTER Table
Example:
```
{
    "DEBUG_COUNTER": {
        "DEBUG_0": {
            "alias": "PORT_RX_LEGIT",
            "type": "PORT_INGRESS_DROPS",
            "desc": "Legitimate port-level RX pipeline drops",
            "group": "LEGIT"
        },
        "DEBUG_1": {
            "alias": "PORT_TX_LEGIT",
            "type": "PORT_EGRESS_DROPS",
            "desc": "Legitimate port-level TX pipeline drops"
            "group": "LEGIT"
        },
        "DEBUG_2": {
            "alias": "SWITCH_RX_LEGIT",
            "type": "SWITCH_INGRESS_DROPS",
            "desc": "Legitimate switch-level RX pipeline drops"
            "group": "LEGIT"
        }
    }
}
```

### 3.2.2 DEBUG_COUNTER_DROP_REASON Table
Example:
```
{
    "DEBUG_COUNTER_DROP_REASON": {
        "DEBUG_0|SMAC_EQUALS_DMAC": {},
        "DEBUG_0|INGRESS_VLAN_FILTER": {},
        "DEBUG_1|EGRESS_VLAN_FILTER": {},
        "DEBUG_2|TTL": {},
    }
}
```

## 3.3 State DB
State DB will store information about:
* What types of drop counters are available on this device
* How many drop counters are available on this device
* What drop reasons are supported by this device

### 3.3.1 DEBUG_COUNTER_CAPABILITIES Table
Example:
```
{
    "DEBUG_COUNTER_CAPABILITIES": {
        "SWITCH_INGRESS_DROPS": {
            "total": 3,
            "used":  1,
            "reasons": [L2_ANY, L3_ANY, SMAC_EQUALS_DMAC]
        },
        "SWITCH_EGRESS_DROPS": {
            "total": 3,
            "used": 1,
            "reasons": [L2_ANY, L3_ANY]
        }
    }
}
```

This information will be populated by the orchestrator (described later) on startup.

### 3.3.2 SAI APIs
We will use the following SAI APIs to get this information:
* `sai_query_attribute_enum_values_capability` to query support for different types of counters
* `sai_object_type_get_availability` to query the amount of available debug counters

## 3.4 Counters DB
The contents of the drop counters will be added to Counters DB by flex counters.

Additionally, we will add a mapping from debug counter names to the appropriate port or switch stat index called COUNTERS_DEBUG_NAME_PORT_STAT_MAP and COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP respectively.

## 3.5 SWSS
A new orchestrator will be created to handle debug counter creation and configuration. Specifically, this orchestrator will support:
* Creating a new counter
* Deleting existing counters
* Adding drop reasons to an existing counter
* Removing a drop reason from a counter

### 3.5.1 SAI APIs
This orchestrator will interact with the following SAI Debug Counter APIs:
* `sai_create_debug_counter_fn` to create/configure new drop counters.
* `sai_remove_debug_counter_fn` to delete/free up drop counters that are no longer being used.
* `sai_get_debug_counter_attribute_fn` to gather information about counters that have been configured (e.g. index, drop reasons, etc.).
* `sai_set_debug_counter_attribute_fn` to re-configure drop reasons for counters that have already been created.

## 3.6 syncd
Flex counter will be extended to support switch-level SAI counters.

# 4 Flows
## 4.1 General Flow
![alt text](./drop_counters_general_flow.png)
The overall workflow is shown above in figure 1.

(1) Users configure drop counters using the CLI. Configurations are stored in the DEBUG_COUNTER Config DB table.

(2) The debug counts orchagent subscribes to the Config DB table. Once the configuration changes, the orchagent uses the debug SAI API to configure the drop counters.

(3) The debug counts orchagent publishes counter configurations to Flex Counter DB.

(4) Syncd subscribes to Flex Counter DB and sets up flex counters. Flex counters periodically query ASIC counters and publishes data to Counters DB.

(5) CLI uses counters DB to satisfy CLI requests.

(6) (not shown) CLI uses State DB to display hardware capabilities (e.g. how many counters are available, supported drop reasons, etc.)

# 5 Warm Reboot Support
On resource-constrained platforms, debug counters will be deleted prior to warm reboot and re-installed when orchagent starts back up. This is intended to conserve hardware resources during the warm reboot.

# 6 Unit Tests
A separate test plan will be uploaded and reviewed by the community. This will include both virtual switch tests to verify that ASIC_DB is configured correctly as well as pytest to verify overall system correctness.

# 7 Open Questions
- How common of an operation is configuring a drop counter? Is this something that will usually only be done on startup, or something people will be updating frequently?