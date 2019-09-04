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
* [2 Requirements](#2-requirements)
    - [2.1 Functional Requirements](#21-functional-requirements)
    - [2.2 Configuration and Management Requirements](#2.2-configuration-and-management-requirements)
    - [2.3 Scalability Requirements](#23-scalability-requirements)
* [3 Design](#3-design)
    - [3.1 Counters DB](#31-counters-db)
    - [3.2 Config DB](#32-config-db)
        - [3.2.1 DEBUG_COUNTER Table](#321-debug_counter-table)
        - [3.2.2 PACKET_DROP_COUNTER_REASON Table](#322-packet_drop_counter_reason-table)
    - [3.3 State DB](#33-state-db)
        - [3.3.1 SAI APIs](#331-sai-apis)
    - [3.4 SWSS](#34-swss)
        - [3.4.1 SAI APIs](#341-sai-apis)
    - [3.5 syncd](#35-syncd)
    - [3.6 CLI](#36-CLI)
        - [3.6.1 CLI show](#361-cli-show)
        - [3.6.2 CLI clear](#362-cli-clear)
        - [3.6.3 CLI configuration](#363-cli-configuration)
* [4 Flows](#4-flows)
    - [4.1 General Flow](#41-general-flow)
* [5 Warm Reboot Support](#5-warm-reboot-support)
* [6 Unit Tests](#6-unit-tests)
* [7 Open Questions](#7-open-questions)



# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)
* [Table 2: Types of Drop Counters](#11-types-of-drop-counters)

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
The goal of this feature is to provide better packet drop visibility in SONiC by providing a mechanism to count and classify packet drops that occur due to different reasons. Because different types of packet drops are important to track in different use cases, it is also key for this feature to be easily configurable.

# 2 Requirements

## 2.1 Functional Requirements
1. Users can configure debug counters to track one or more drop reason(s).
    1. Supported drop reasons will be available in State DB
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
Two new tables will be added to Config DB:
* DEBUG_COUNTER to store general debug counter metadata
* PACKET_DROP_COUNTER_REASON to store drop reasons for debug counters that have been configured to track packet drops

### 3.2.1 DEBUG_COUNTER Table
Example:
```
{
    "DEBUG_COUNTER": {
        "DEBUG_0": {
            "alias": "PORT_RX_LEGIT",
            "type": "PORT_INGRESS_DROPS",
            "desc": "Legitimate port-level RX pipeline drops"
        },
        "DEBUG_1": {
            "alias": "PORT_TX_LEGIT",
            "type": "PORT_EGRESS_DROPS",
            "desc": "Legitimate port-level TX pipeline drops"
        },
        "DEBUG_2": {
            "alias": "SWITCH_RX_LEGIT",
            "type": "SWITCH_INGRESS_DROPS",
            "desc": "Legitimate switch-level RX pipeline drops"
        }
    }
}
```

### 3.2.2 PACKET_DROP_COUNTER_REASON Table
Example:
```
{
    "PACKET_DROP_COUNTER_REASON": {
        "DEBUG_0|SMAC_EQUALS_DMAC": {},
        "DEBUG_0|INGRESS_VLAN_FILTER": {},
        "DEBUG_1|EGRESS_VLAN_FILTER": {},
        "DEBUG_2|TTL": {},
    }
}
```

## 3.3 State DB
State DB will store information about:
* Whether drop counters are available on this device
* How many drop counters are available on this device
* What drop reasons are supported by this device

### 3.3.1 SAI APIs
We will use the following SAI APIs to get this information:
* `sai_query_attribute_enum_values_capability` to query support for different types of counters
* `sai_object_type_get_availability` to query the amount of available debug counters

## 3.4 SWSS
A new orchestrator will be created to handle debug counter creation and configuration.

### 3.4.1 SAI APIs
This orchestrator will interact with the following SAI Debug Counter APIs:
* `sai_create_debug_counter_fn` to create/configure new drop counters.
* `sai_remove_debug_counter_fn` to delete/free up drop counters that are no longer being used.
* `sai_get_debug_counter_attribute_fn` to gather information about counters that have been configured (e.g. index, drop reasons, etc.).
* `sai_set_debug_counter_attribute_fn` to re-configure drop reasons for counters that have already been created.

## 3.5 syncd
Flex counter will be extended to support switch-level SAI counters.

## 3.6 CLI
The CLI tool will provide the following functionality:
* Show drop counts: ```show drops```
* Clear drop counters: ```sonic-clear drops```
* See drop counter config: ```show drops config```
* Initialize a new drop counter: ```config drops init```
* Add drop reasons to a drop counter: ```config drops add```
* Remove drop reasons from a drop counter: ```config drops remove```
* Delete a drop counter: ```config drops delete```

### 3.6.1 CLI show

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

$ show drops --contains "LEGIT"
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

### 3.6.2 CLI clear
```
$ sonic-clear drops
```

### 3.6.3 CLI Configuration
```
$ show drops config
Drop Counters: supported
Available Counters: 4

Name      Type            Reasons              Description
--------  ------------    -------------------  --------------
RX_LEGIT  PORT_INGRESS    SMAC_EQUALS_DMAC     Legitimate port-level RX pipeline drops
                          INGRESS_VLAN_FILTER
TX_LEGIT  PORT_EGRESS     EGRESS_VLAN_FILTER   Legitimate port-level TX pipeline drops
RX_LEGIT  SWITCH_INGRESS  TTL                  Legitimate switch-level RX pipeline drops
 
$ config drops init --counter="DEBUG_3" --name="EXAMPLE" --type="SWITCH_EGRESS" --desc="example"
Initializing DEBUG_3 as EXAMPLE...
DONE!

Name      Type           Reasons              Description
--------  -------------  -------------------  --------------
EXAMPLE   SWITCH_EGRESS  NONE                 example

$ config drops add --counter=EXAMPLE --reason="SMAC_MULTICAST"
Configuring EXAMPLE...
DONE!

Name      Type           Reasons              Description
--------  -------------  -------------------  --------------
EXAMPLE   SWITCH_EGRESS  SMAC_MULTICAST       example

$ config drops add --counter=EXAMPLE --reason="DMAC_RESERVED"
Configuring EXAMPLE...
DONE!

Name      Type           Reasons              Description
--------  -------------  -------------------  --------------
EXAMPLE   SWITCH_EGRESS  SMAC_MULTICAST       example
                         DMAC_RESERVED

$ config drops remove --counter=EXAMPLE --reason="DMAC_RESERVED"
Configuring EXAMPLE...
DONE!

Name      Type           Reasons              Description
--------  -------------  -------------------  --------------
EXAMPLE   SWITCH_EGRESS  SMAC_MULTICAST       example

$ config drops delete --counter=EXAMPLE
Deleting EXAMPLE...
DONE!
```

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
The debug counts orchagent will restore counter configurations after a warm reboot. It will get the current configuration from the SAI and check this against the configuration saved in config DB, reconfiguring the debug counters if necessary.

# 6 Unit Tests
A separate test plan will be uploaded and reviewed by the community.

# 7 Open Questions
None at this time.