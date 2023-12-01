# Feature Name 
This is generic Fault Management Infrastructure document aiming at Fault Analysis and Handling

# High Level Design Document
#### Rev 0.1

# Table of contents

# Revision
| Rev |     Date    |       Author                       | Change Description                  |
|:---:|:-----------:|:----------------------------------:|-------------------------------------|
| 0.1 | 11/29/2023  | Shyam Kumar                        | Initial Version                     |


### Definitions/Abbreviations
| **Term**       | **Definition**                                   |
| -------------- | ------------------------------------------------ |
| FM             | Fault Management                                 |
| FDR            | Fault Detection and Reporting                    |
| FAH            | Fault Analysis and Handling                      |

# Background/Context
Any failure or an error impacting a sub-system or system is regarded as a fault. 
Broadly classified into SW (Software) and HW (Hardware) faults:
   - SW faults are the ones that can occur during SW processing of a workflow at process/sub-system or a system level
   - HW faults are those that can occur during SW or HW processing of a workflow at HW (board) level - e.g. HW component/device etc.

They may occur at any of the following stages of system's functioning:
   - system configuration, bring-up
   - feature enablement/configuration
   - during steady state
   - feature disablement/unconfiguration
   - while going-down (config reload, reboot etc.)

# Present State (Problem Definmition)
In SONiC, Fault is represented via an Event or an Alarm.
SONiC has Event Framework HLD (https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/event-alarm-framework.md), 
which can help event-detector to publish its event to the eventD redisDB.

However, there is no Fault Manager/Handler which can take the needed platform-specified action(s) to recover the system from the generated fault.

# Overview (of this feature)
This feature aims at adding a generic FM (Fault Management) Infrastructure which can do the following:
   1) Abstract the platform/HWSKU nuances from an open source NOS (i.e. SONiC) by publishing platform-specific 'Fault-Action Policy table'
   2) Fetch these events (alarms/faults) from the eventD (based on published YANG/schema)
   3) Analyze them (in a generic way) against the above-mentioned Policy Table
   4) Take action based on the lookup/match in Policy Table
   5) Action could either be generic or platform specfic

# Benefits (of adding this feature)
Platform supplied 'Fault-Action Policy table' has a holistic/system-level view of the platform (chassis/board/HWSKU) and can gauge the right action required to recover from the fault.
It can either go with the recommended action (provided by the fault source/detector) or override it with the system-level one.

# High Level Block digram and System Flow

High-Level design (end-to-end workflow) to inject, detect, report, analyze and handle Faults in a SONiC based chassis.
Note: Errors/Failures/Faults are regarded as Faults here.

<img width="896" alt="Screenshot 2023-11-30 at 3 51 26 PM" src="https://github.com/shyam77git/SONiC/assets/69485234/bc92b131-b30f-4848-935b-9243e45c0e3b">

# High Level Work Flow
Following are the main functionalities/tasks of the FM core infra introduced as part of this document:
1. Formulate platform/HWSKU specfic Fault-Action Policy Table (json or yaml file)
2. Introduce a new micro-service at host (Linux Kernel)
3. Subsribe to eventsDB redisDB (once available) and fetch events and alarms from it
4. Parse events against sonic-events yang model
5. Analyze them against Fault-Action Policy Table (file)
6. Handle(i.e. take action) based on action(s) specified in Fault-Action Policy Table
   - action may range from logging (disk, OBFL flash etc.) to reload/shutdown etc.
7. Tabulate event entry (along with action taken) for book-keeping purposes

# References
SONiC Events Yang models (schema): 
- https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-yang-models/yang-models
    - sonic-events-swss.yang
    - sonic-events-host.yang
    - sonic-events-bgp.yang etc.
- SONiC Events Producer and Event/Alarm Framework HLDs
    - https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/events-producer.md
    - https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/event-alarm-framework.md
- EventD docker container
    - https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-eventd/src/eventd.cpp
    - https://github.com/sonic-net/sonic-swss-common/blob/master/common/events.cpp
    - Leveraging ZMQ and providing event_publish() and event_receive() support/definitions etc.
    - https://github.com/sonic-net/sonic-buildimage/blob/202305/dockers/docker-eventd/supervisord.conf 
