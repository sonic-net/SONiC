# Sonic Smart Counter Poll #

## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#abbreviations)
- [1 Overview](#1-overview)
- [2 Requirements](#2-requirements)
  - [2.1 Functional requirements](#21-functional-requirements)
  - [2.2 CLI requirements](#22-cli-requirements)
- [3 Architecture Design](#3-architecture-design)
- [4 High level design](#4-high-level-design)
  - [4.1 Assumptions](#41-assumptions)
  - [4.2 Counter Capability Set Discovery](#42-counter-capability-set-discovery)
  - [4.3 Counter Capability Sets and Mapping Data Structures](#43-counter-capability-sets-and-mapping-data-structures)
    - [4.3.1 FlexCounters.cpp data structures](#431-flexcounterscpp-data-structures)
    - [4.3.2 Polling logic change - per-port polling](#432-polling-logic-change---per-port-polling)
    - [4.3.3 Polling logic change - bulk polling](#433-polling-logic-change---bulk-polling)
- [5 SAI API](#5-sai-api)
- [6 Unit Test Cases](#6-unit-test-cases)
- [7 System Test Cases](#7-system-test-cases)
- [8 Open/Action items - if any](#8-openaction-items---if-any)
  - [8.1 Add Per-Port Counter Support for Bulk polling](#81-add-per-port-counter-support-for-bulk-polling)



### Revision

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 |             | Justin Wong            | Initial version                   |

### Scope

  This document outlines the implementation of Smart Counter Poll, which is adding dynamic per-port counter support to `syncd`. This feature will allow the maximum port and counter support on switches that have ports with differing counter support.

### Definitions / Abbreviations

 | Term                       |  Definition / Abbreviation                                                                              |
 |----------------------------|---------------------------------------------------------------------------------------------------------|
 | Counter Capability Set     | A set of counters that can be successfully polled from the SAI for a port. Can be different from one port to another.                                                                                |
 | syncd                      | Executable in the docker syncd:/usr/bin/syncd that communicates with the SAI, built from sonic-sairedis |
 | Bulk polling               | Polling method that polls all counters for all ports with a single SAI call                        |

### 1 Overview

Counters are crucial data that gives information on how much traffic is received, transferred, and dropped. There are many counters for various features and types of packets. Counter data is retrieved from the ASIC by `syncd`.

There is an assumption that all ports support the same set of counters. This is not always the case, resulting in some ports having no counter data available.

An example would be ports intended for management or telemetry, which usually differs in form factor compared the other data ports. It is not uncommon for a switch to have 2 to 3 different types of ports, and hence there may be 2 to 3 different sets of ports, each set sharing the same set of supported counters.

## 2 Requirements
### 2.1 Functional Requirements
  This HLD is to:
  - Add logic to discover and store supported counters for each port for polling.
  - Enhance the current counter polling logic to poll different sets of counters depending on the port’s capabilities.

### 2.2 CLI Requirements

There are no changes to the CLI.

## 3 Architecture Design

There are no changes in the current Sonic Architecture.

## 4 High-Level Design

![cntr-high-level-design](/doc/syncd/images/cntr_high_lvl_change.svg)

Instead of checking counter capability for all ports only with one port, use new logic to check if counters work on a per-port basis.

Once per-port counter support is discovered, poll counters like before using new counter sets per-port.

### 4.1 Assumptions

- If a switch's counters support bulk polling, then all counters would have the same capabilities. Therefore, this enhancement's scope will be limited to non-bulk polling methods for now.  
This enhancement can be expanded to support bulk polling for switches with varying counter capabilities across ports in the future.

### 4.2 Counter Capability Set Discovery

![cntr-discovery](/doc/syncd/images/cntr_discovery.svg)

A blanket counter set will first be created to hold all desired counters.

Then for each port, it will attempt to query every available set of supported counters in the order of descending size.  
On success, it will attempt any remaining counters and create a new counter set if there are supported counters.  
If there is no success on any set, it will create a counter set from scratch by querying counters one by one.

At the end, the sets will be stored in an array and each port will be linked to the set representing its largest supported counter set.


### 4.3 Counter Capability Set and Map Data Structures

![cntr-simpledata](/doc/syncd/images/cntr_simpledata.svg)

To minimize memory footprint, the Counter Capability Sets will be stored as an array of sets, and a map will be used to map each port to a Counter Capability set.

#### 4.3.1 FlexCounters.cpp data structures

In `FlexCounters.cpp`, it will be stored as:

![cntr-supportedCounterGroups](/doc/syncd/images/cntr_supportCounterGroups.svg)

![cntr-objectSupportedCountersGroupMap](/doc/syncd/images/cntr_objectSupportedCountersGroupMap.svg)

A vector of `struct CounterGroupRef` is used to sort the counter sets in descending order such that the algorithm will be able to iterate in descending order without changing the order of `m_supportedCounterGroups` - this so that the index map in `m_objectSupportedCountersGroupMap` will be still be valid. The struct and vector are defined as:

![cntr-counterGroupsSorted](/doc/syncd/images/cntr_counterGroupsSorted.svg)

![cntr-CounterGroupRef](/doc/syncd/images/cntr_CounterGroupRef.svg)

#### 4.3.2 Polling logic change - per-port polling

No changes needed, existing counter set variables can be drop-in replaced by port-specific counter sets.

#### 4.3.3 Polling logic change - bulk polling

To be worked on in future work.

## 5 SAI API

No change in the SAI API. No new SAI object accessed.

## 6 Unit Test Cases

## 7 System Test Cases

Various counters-related tests in sonic-mgmt will verify if counters are working as intended. The following sonic-mgmt tests should be run to confirm proper operation:
* `sonic-mgmt/tests/dhcp_relay/test_dhcp_counter_stress.py`
* `sonic-mgmt/tests/drop_packets/test_drop_counters.py`
* `sonic-mgmt/tests/drop_packets/test_configurable_drop_counters.py`
* `sonic-mgmt/tests/gnmi/test_gnmi_countersdb.py`
* `sonic-mgmt/tests/platform_tests/test_advanced_reboot.py`
* `sonic-mgmt/tests/snmp/test_snmp_queue_counters.py`

## 8 Open/Action items - if any

### 8.1 Add Per-Port Counter Support for Bulk polling
`FlexCounters.cpp` is split into two parts where there is per-port polling and bulk polling. Per-port polling makes a SAI call for each port, where bulk polling makes a SAI call for all ports at once.

All switches have counters that are capable of per-port polling, whereas only some switches have counters are capable of bulk polling. For now, Smart Counter Poll support is only added to per-port polling to allow switches with varying counter support to be operational first. Bulk polling can be supported in future work for performance gains.

Bulk polling works by supplying a set of counters for all ports as a SAI call and expects all counters at once. To support Smart Counter Poll, this can be split into multiple SAI calls - one SAI call per group of ports sharing the same counter set. The relevant data structures such as `BulkStatsContext` would have to be expanded to support multiple counter sets and have logic to know which ports to poll for a counter set.



NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.