# Monitoring and Auto-Mitigating the Unhealthy of Containers in SONiC

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
    - [1.1 Use Cases](#11-use-cases)
        - [1.1.1 A flexible "drop filter"](#111-a-flexible-"drop-filter")
        - [1.1.2 A helpful debugging tool](#112-a-helpful-debugging-tool)
        - [1.1.3 More sophisticated monitoring schemes](#113-more-sophisticated-monitoring-schemes)
* [2 Requirements](#2-requirements)
    - [2.1 Functional Requirements](#21-functional-requirements)
    - [2.2 Configuration and Management Requirements](#22-configuration-and-management-requirements)
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
* [7 Platform Support](#7-platform-support)
    - [7.1 Known Limitations](#7.1-known-limitations)
* [8 Open Questions](#8-open-questions)
* [9 Acknowledgements](#9-acknowledgements)
* [10 References](#10-references)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# List of Figures
* [Figure 1: General Flow](#41-general-flow)

# Revision
| Rev |    Date    |          Author        |     Change Description    |
|:---:|:----------:|:----------------------:|---------------------------|
| 0.1 | 02/18/2020 | Yong Zhao, Joe Leveque |      Initial version      |

# About this Manual
This document provides the design and implementation of monitoring and auto-mitigating
the unhealthy of docker containers in SONiC.

# Scope
This document describes the high level design of the feature to monitor and auto-mitigate
the unhealthy of docker containers.

# Definitions/Abbreviation
| Abbreviation |         Description          |
|--------------|------------------------------|
| Config DB    | SONiC Configuration Database |
| CLI          | Command Line Interface       |

# 1 Feature Overview
SONiC is a collection of various switch applications which are held in docker containers
such as BGP and SNMP. Each application usually includes several processes which are 
working together to provide the services for other modules. As such, the healthy of
critical processes in each docker container are the key for the intended functionalities of
SONiC switch.

The main purpose of this feature includes two parts: the first part is to monitor the
running status of each process and critical resource usage such as CPU, memory and disk
of each docker container. The second part is to auto-mitigate the unhealthy of docker
container if one of its critical process crashed or exited unexpectedly.

We implemented this feature by employing the existing monit and supervisord system tools.
* we used monit system tool to detect whether a process is running or not and whether 
  the resource usage of a docker container is beyond the pre-defined threshold.
* we leveraged the mechanism of event listener in supervisord to auto-restart a docker container
  if one of its critical processes exited unexpectedly. 
* we also added a knob to make this auto-restart feature dynamically configurable.
  Specifically users can run CLI to configure this feature residing in Config_DB as
  enabled/disabled state.

## 1.1 Requirements

### 1.1.1 Functional Requirements
1. The monit must provide the ability to generate an alert when a critical process is not
    running.
2. The monit must provide the ability to generate an alert when the resource usage of
    a docker contaier is larger than the pre-defined threshold.
3. The event listener in supervisord must receive the signal when a critical process in 
    a docker container crashed or exited unexpectedly and then restart this docker 
    container.
4. CONFIG_DB can be configured to enable/disable this auto-restart feature for each docker
    container.. 
5. Users can access this auto-restart information via the CLI utility
    1. Users can see current auto-restart status for docker containers.
    2. Users can change auto-restart status for a specific docker container.

### 1.1.2 Configuration and Management Requirements
Configuration of the auto-restart feature can be done via:
* init_cfg.json
* CLI

### 1.1.3 Scalability Requirements

# 2 Design

## 2.1 Basic Approach
Monitoring the running status of critical processes and resource usage of docker containers
are heavily depended on the monit system tool. Since monit already provided the mechanism
to check whether a process is running or not, it will be straightforward to integrate this into monitoring 
the critical processes in SONiC. However, monit only gives the method to monitor the resource
usage per process level not container level. As such, monitoring the resource usage of a docker 
container will be an interesting and challenging problem. In our design, we adopted the way
that monit will check the returned value of a script which reads the resource usage of docker 
container, compares it with pre-defined threshold and then exited. The value 0 signified that
the resource usage is less than threshold and non-zero means we should send an alert since
current usage is larger than threshold.

The second part in this feature is docker containers can be automatically shut down and
restarted if one of critical processes running in the container exits unexpectedly. Restarting
the entire container ensures that configuration is reloaded and all processes in the container
get restarted, thus increasing the likelihood of entering a healthy state.

## 2.1 CLI (and usage example)
The CLI tool will provide the following functionality:
* See available drop counter capabilities: `show dropcounters capabilities`
* See drop counter config: `show dropcounters configuration`
* Show drop counts: `show dropcounters counts`
* Clear drop counters: `sonic-clear dropcounters`
* Initialize a new drop counter: `config dropcounters install`
* Add drop reasons to a drop counter: `config dropcounters add_reasons`
* Remove drop reasons from a drop counter: `config dropcounters remove_reasons`
* Delete a drop counter: `config dropcounters delete`

### 3.1.1 Displaying available counter capabilities
```
admin@sonic:~$ show dropcounters capabilities
Counter Type            Total
--------------------  -------
PORT_INGRESS_DROPS          3
SWITCH_EGRESS_DROPS         2

PORT_INGRESS_DROPS:
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

SWITCH_EGRESS_DROPS:
      L2_ANY
      L3_ANY
      A_CUSTOM_REASON
```

### 3.1.2 Displaying current counter configuration
```
admin@sonic:~$ show dropcounters configuration
Counter   Alias     Group  Type                 Reasons              Description
--------  --------  -----  ------------------   -------------------  --------------
DEBUG_0   RX_LEGIT  LEGIT  PORT_INGRESS_DROPS   SMAC_EQUALS_DMAC     Legitimate port-level RX pipeline drops
                                                INGRESS_VLAN_FILTER
DEBUG_1   TX_LEGIT  None   SWITCH_EGRESS_DROPS  EGRESS_VLAN_FILTER   Legitimate switch-level TX pipeline drops

admin@sonic:~$ show dropcounters configuration -g LEGIT
Counter   Alias     Group  Type                 Reasons              Description
--------  --------  -----  ------------------   -------------------  --------------
DEBUG_0   RX_LEGIT  LEGIT  PORT_INGRESS_DROPS   SMAC_EQUALS_DMAC     Legitimate port-level RX pipeline drops
                                                INGRESS_VLAN_FILTER
```

### 3.1.3 Displaying the current counts

```
admin@sonic:~$ show dropcounters counts
    IFACE    STATE    RX_ERR    RX_DROPS    TX_ERR    TX_DROPS   RX_LEGIT
---------  -------  --------  ----------  --------  ----------  ---------
Ethernet0        U        10         100         0           0         20
Ethernet4        U         0        1000         0           0        100
Ethernet8        U       100          10         0           0          0

DEVICE  TX_LEGIT
------  --------
sonic       1000

admin@sonic:~$ show dropcounters counts -g LEGIT
    IFACE    STATE    RX_ERR    RX_DROPS    TX_ERR    TX_DROPS   RX_LEGIT
---------  -------  --------  ----------  --------  ----------  ---------
Ethernet0        U        10         100         0           0         20
Ethernet4        U         0        1000         0           0        100
Ethernet8        U       100          10         0           0          0

admin@sonic:~$ show dropcounters counts -t SWITCH_EGRESS_DROPS
DEVICE  TX_LEGIT
------  --------
sonic       1000
```

### 3.1.4 Clearing the counts
```
admin@sonic:~$ sonic-clear dropcounters
Cleared drop counters
```

### 3.1.5 Configuring counters from the CLI
```
admin@sonic:~$ sudo config dropcounters install DEBUG_2 PORT_INGRESS_DROPS [EXCEEDS_L2_MTU,DECAP_ERROR] -d "More port ingress drops" -g BAD -a BAD_DROPS
admin@sonic:~$ sudo config dropcounters add_reasons DEBUG_2 [SIP_CLASS_E]
admin@sonic:~$ sudo config dropcounters remove_reasons DEBUG_2 [SIP_CLASS_E]
admin@sonic:~$ sudo config dropcounters delete DEBUG_2
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
            "count": "3",
            "reasons": "[L2_ANY, L3_ANY, SMAC_EQUALS_DMAC]"
        },
        "SWITCH_EGRESS_DROPS": {
            "count": "3",
            "reasons": "[L2_ANY, L3_ANY]"
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
On resource-constrained platforms, debug counters can be deleted prior to warm reboot and re-installed when orchagent starts back up. This is intended to conserve hardware resources during the warm reboot. This behavior has not been added to SONiC at this time, but can be if the need arises.

# 6 Unit Tests
This feature comes with a full set of virtual switch tests in SWSS.
```
=============================================================================================== test session starts ===============================================================================================
platform linux2 -- Python 2.7.15+, pytest-3.3.0, py-1.8.0, pluggy-0.6.0 -- /usr/bin/python2
cachedir: .cache
rootdir: /home/daall/dev/sonic-swss/tests, inifile:
collected 14 items

test_drop_counters.py::TestDropCounters::test_deviceCapabilitiesTablePopulated remove extra link dummy
PASSED                                                                                                                       [  7%]
test_drop_counters.py::TestDropCounters::test_flexCounterGroupInitialized PASSED                                                                                                                            [ 14%]
test_drop_counters.py::TestDropCounters::test_createAndRemoveDropCounterBasic PASSED                                                                                                                        [ 21%]
test_drop_counters.py::TestDropCounters::test_createAndRemoveDropCounterReversed PASSED                                                                                                                     [ 28%]
test_drop_counters.py::TestDropCounters::test_createCounterWithInvalidCounterType PASSED                                                                                                                    [ 35%]
test_drop_counters.py::TestDropCounters::test_createCounterWithInvalidDropReason PASSED                                                                                                                     [ 42%]
test_drop_counters.py::TestDropCounters::test_addReasonToInitializedCounter PASSED                                                                                                                          [ 50%]
test_drop_counters.py::TestDropCounters::test_removeReasonFromInitializedCounter PASSED                                                                                                                     [ 57%]
test_drop_counters.py::TestDropCounters::test_addDropReasonMultipleTimes PASSED                                                                                                                             [ 64%]
test_drop_counters.py::TestDropCounters::test_addInvalidDropReason PASSED                                                                                                                                   [ 71%]
test_drop_counters.py::TestDropCounters::test_removeDropReasonMultipleTimes PASSED                                                                                                                          [ 78%]
test_drop_counters.py::TestDropCounters::test_removeNonexistentDropReason PASSED                                                                                                                            [ 85%]
test_drop_counters.py::TestDropCounters::test_removeInvalidDropReason PASSED                                                                                                                                [ 92%]
test_drop_counters.py::TestDropCounters::test_createAndDeleteMultipleCounters PASSED                                                                                                                        [100%]

=========================================================================================== 14 passed in 113.65 seconds ===========================================================================================
```

A separate test plan will be uploaded and review by the community. This will consist of system tests written in pytest that will send traffic to the device and verify that the drop counters are updated correctly.

# 7 Platform Support
In order to make this feature platform independent, we rely on SAI query APIs (described above) to check for what counter types and drop reasons are supported on a given device. As a result, drop counters are only available on platforms that support both the SAI drop counter API as well as the query APIs, in order to preserve safety.

# 7.1 Known Limitations
* BRCM SAI:
    - ACL_ANY, DIP_LINK_LOCAL, SIP_LINK_LOCAL, and L3_EGRESS_LINK_OWN are all based on the same underlying counter in hardware, so enabling any one of these reasons on a drop counter will (implicitly) enable all of them.

# 8 Open Questions
- How common of an operation is configuring a drop counter? Is this something that will usually only be done on startup, or something people will be updating frequently?

# 9 Acknowledgements
I'd like to thank the community for all their help designing and reviewing this new feature! Special thanks to Wenda, Ying, Prince, Guohan, Joe, Qi, Renuka, and the team at Microsoft, Madhu and the team at Aviz, Ben, Vissu, Salil, and the team at Broadcom, Itai, Matty, Liat, Marian, and the team at Mellanox, and finally Ravi, Tony, and the team at Innovium.

# 10 References
[1] [SAI Debug Counter Proposal](https://github.com/itaibaz/SAI/blob/a612dd21257cccca02cfc6dab90745a56d0993be/doc/SAI-Proposal-Debug-Counters.md)
