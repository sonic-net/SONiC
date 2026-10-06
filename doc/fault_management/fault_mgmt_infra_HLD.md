# Feature Name 
This is a platform independent **Fault Management Infrastructure** document aiming at Fault Analysis and Handling

# High Level Design Document
#### Rev 1.0

# Table of contents
* [Revision](#revision)
* [Definitions](#definitions)
* [Background/Context](#background/context)
* [Present State (Problem Definition)](#present-state-(problem-definition))
* [Overview](#overview)
* [Objective](#objective)
* [High Level Block diagram and System Flow](#high-level-block-diagram-and-system-flow)
* [High Level Work Flow](#high-level-work-flow)
* [Fault's End-to-End WorkFlow Sequence](#fault's-end-to-end-workflow-sequence)
* [Fault-Action Policy Table (sample)](#fault-action-policy-table-(sample))
* [References](#references)



# Revision
| Rev |     Date    |       Author                       | Change Description                  |
|:---:|:-----------:|:----------------------------------:|-------------------------------------|
| 0.1 | 11/29/2023  | Shyam Kumar                        | Draft Version                       |
| 1.0 | 12/04/2023  | Shyam Kumar                        | Initial Version                     |


### Definitions
| **Term**       | **Definition**                                   |
| -------------- | ------------------------------------------------ |
| HLD            | High Level Design                                |
| FM             | Fault Management                                 |
| FDR            | Fault Detection and Reporting                    |
| FAH            | Fault Analysis and Handling                      |
| F-A            | Fault-Action                                     |

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

# Present State (Problem Definition)
In SONiC, Fault is represented via an Event or an Alarm.
SONiC has Event Framework HLD https://github.com/sonic-net/SONiC/pull/1409 (https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/event-alarm-framework.md), 
which can help event-detector to publish its event to the eventD redisDB.

However, there is no Fault Manager/Handler which can take the needed platform-specified action(s) to recover the system from the generated fault.

# Overview
This feature aims at adding a generic FM (Fault Management) Infrastructure which can do the following:
   1) Abstract the platform/HWSKU nuances from an open source NOS (i.e. SONiC) by publishing platform-specific 'Fault-Action Policy table'
   2) Fetch these events (alarms/faults) from the eventD (based on published YANG/schema)
   3) Analyze them (in a generic way) against the above-mentioned Policy Table
   4) Take action based on the lookup/match in Policy Table
   5) Action could either be generic or platform specific

# Objective
Objective of producing this document is two-fold:

   a) Every SONiC NOS deployment may not have External Controller to take the action upon fault occurence. 
      In that case, SONiC (with its underlying platform) is expected to take the required action to recover the system/chassis from the fault.
      
   b) Platform supplied 'Fault-Action Policy table' has a holistic/system-level view of the platform (chassis/board/HWSKU) 
      and can gauge the right action required to recover the system from the fault.
      It can either go with the recommended action (provided by the FDR - fault source/detector) or override it with the system-level one.

**Fault Manager** module (as described in below block diagram) would serve the purpose of taking necessary action(s) to log and handle the faults.

# High Level Block diagram and System Flow

High-Level design (end-to-end workflow) to inject, detect, report, analyze and handle Faults in a SONiC based chassis.

Note: Errors/Failures/Faults are regarded as Faults here.

<img width="892" alt="Screenshot 2023-11-30 at 5 36 53 PM" src="https://github.com/shyam77git/SONiC/assets/69485234/47a5fa4a-7f3d-4d45-86a4-81cb3fb893f1">

**Block diagram's markers/steps (#1 through #9) explanation:**
|      Markers        |                   Brief Description                                    | State                                                  |
| --------------------|------------------------------------------------------------------------|--------------------------------------------------------|
| Markers 1 through 3 | Fault detector (source) publishes its events(faults, alarms) to eventD | Available in SONiC 202305
| Marker 4            | Storing the events to eventD's redisDB instance                        | codeflow to be committed as part of revised HLD: https://github.com/sonic-net/SONiC/pull/1409 |                                                                            
| Marker 5 through 9  | This is the beige oval-shaped box (on the right) representing the FM (Fault Managment) infrastructure module being added and developed as part of this HLD/Feature| This HLD|
                                                                    

# High Level Work Flow
Following are the main functionalities/tasks of the **FM infrastructure module** being introduced as part of this document:
1. Formulate platform/HWSKU specific Fault-Action Policy Table (json or yaml file)
   - There would be generic (default) table if none provided by platform
   - A platform supplied file would override the default one
2. Introduce a new micro-service (fault_manager) at host (Linux Kernel)
3. This service to subscribe to eventsD redisDB instance (once available) and fetch events and alarms from it
4. Parse events against event_tag in sonic-events yang model 
5. Analyze them against Fault-Action Policy Table (file)
   - Take fault_type and fault_severity as input from the fetched event and perform lookup
     on these fields in Fault-Action Policy Table to determine the action(s) needed
6. Handle the fault (i.e. take action) based on action(s) specified in Fault-Action Policy Table
   - action may range from logging (disk, OBFL flash etc.) to reload/shutdown etc.
   - Taking action would either be by itself (i.e. in ts own micro-service) or delegating it to action's owner
7. Tabulate event entry (along with action taken) for book-keeping purposes


# Fault's End-to-End WorkFlow Sequence
Following workflow depicts the end-to-end fault (event) flow from Fault generation to Fault Handling
![Fault Management (FM) Workflow sequence](https://github.com/shyam77git/SONiC/assets/69485234/2b453a1b-6e14-48c6-bf61-ab978e62a3bf)


# Fault-Action Policy Table (fault_action_policy.json)

{

    "chassis": {
        "name": "PID or HWSKU",
        "faults": [
            {
        
                 "type" : "CUSTOM_EVPROFILE_CHANGE",
                 "severity" : "MAJOR",
                 "action" : ["syslog"]
            },
            {
                 "type" : "TEMPERATURE_EXCEEDED",
                 "severity" : "CRITICAL",
                 "action" : ["syslog", "obfl", "reload"]
            },
            {
                 "type": "FANS MISSING",
                 "severity": "CRITICAL",
                 "action" : ["syslog", "obfl", "shutdown"]
            }
        ]
    }
}

# Use-cases
Following are some of the Faults' uses-cases 
| Sr # | Fault Type                    | FDR (Fault source/detector)  |  Fault informant   |  FAH (Fault Analyzer & Handler) |
|------|-------------------------------|------------------------------|--------------------|---------------------------------|
| 1.   | Thermal sensors (Temperature) | thermalctld                  |  eventD            |  FM (this HLD/module)           |
| 2.   | Voltage & Current sensors     | sensormond                   |  eventD            |  FM                             |
| 3.   | FanTrays and Fans             | thermalctld                  |  eventD            |  FM                             |
| 4.   | PowerTrays and PSUs           | psud                         |  eventD            |  FM                             |
| 5.   | transceivers                  | xcvrd                        |  eventD            |  FM                             |
| 6.   | PCIe faults                   | Host's PCIEd bin/util        |  eventD            |  FM                             |
| 7.   | Ethernet Switch faults        | platform's ethSwitch service |  eventD            |  FM                             |

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
 - Following yet to be committed to sonic mainline (202305, master etc.). Still in PR https://github.com/sonic-net/sonic-mgmt-common/pull/48
    - sonic-event.yang
      - https://github.com/sonic-net/sonic-mgmt-common/pull/48/files#diff-79e2d8d548330caba6bf4578fd5319cd27c7f27f0576ed7558c8197ffe262049
    - sonic-alarm.yang
      - https://github.com/sonic-net/sonic-mgmt-common/pull/48/files#diff-b8e4e92cd1215ac998304fafecb94406af73185f07a055b7bde9dfbb8acebc82
