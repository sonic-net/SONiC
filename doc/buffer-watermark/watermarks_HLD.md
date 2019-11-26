# Watermark counters in SONiC
# High Level Design Document
### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definitions/Abbreviation](#definitionsabbreviation)

  * [1 Overview](#1-overview)
    * [1.1 System Chart](#11-system-chart)
    * [1.2 Modules description](#12-modules-description)
      * [1.2.1 gRPC](#121-grpc)
      * [1.2.2 Counter DB](#122-counter-db)
      * [1.2.3 Orchestration Agent](#123-orchestration-agent)
      * [1.2.4 SAI Redis](#124-sai-redis)
      * [1.2.5 SAI DB](#125-sai-db)
      * [1.2.6 syncd](#126-syncd)
      * [1.2.7 SAI (Redis and Switch)](#127-sai-redis-and-switch)

  * [2 Requirements](#2-requirements)
    * [2.1 Watermark requirements](#21-watermark-requirements)

  * [3 Modules Design](#3-modules-design)
    * [3.1 Modules that need to be updated](#31-modules-that-need-to-be-updated)
      * [3.1.1 CLI](#311-cli)
      * [3.1.2 Counter DB](#312-counter-db)
      * [3.1.3 Lua scripts and plugins](#313-lua-scripts-and-plugiins)
      * [3.1.4 Orchestration Agent](#314-orchestration-agent)
      * [3.1.5 SAI Redis](#315-sai-redis)
      * [3.1.6 ASIC DB](#316-asic-db)
      * [3.1.7 Syncd](#317-syncd)
      * [3.1.8 SAI](#318-sai)
      * [3.1.9 gRPC](#319-grpc)
      
  * [4 Flows](#4-flows)

  * [5 Open questions](#5-open-questions)

# List of Tables
* [Table 1: Revision](#revision)
* [Table 2: Abbreviations](#definitionsabbreviation)
* [Table 3: COUNTERS_DB Table details](#table-details)
* [Table 4: Virtual paths](#virtual-paths)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Mykola Faryma      | Initial version                   |

# About this Manual
This document provides general information about the watermark feature implementation in SONiC.
# Scope
This document describes the high level design of the watermark feature.
# Definitions/Abbreviation
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| gRPC                     | gRPC Remote Procedure Calls                |
| gNMI                     | gRPC Network Management Interface          |
| API                      | Application Programmable Interface         |
| SAI                      | Switch Abstraction Interface               |

# 1 Overview
## 1.1 System Chart
Following diagram describes a top level overview of the architecture:

![](https://github.com/mykolaf/SONiC/blob/master/images/watermark_HLD/SystemOverview.png)

## 1.2 Modules description
### 1.2.1 gRPC
System data telemetry infrastructure. Basically allows to getRequest data from SONiC DBs (and more).
### 1.2.2 Counter DB
Located in the Redis DB instance #2 running inside the container "database". Redis DB works with the data in format of key-value tuples, needs no predefined schema and holds various counters like port counters, ACL counters, etc.
### 1.2.3 Orchestration Agent
This component is running in the "orchagent" docker container and is responsible for processing updates of the APP DB and do corresponding changes in the SAI DB via SAI Redis.
### 1.2.4 SAI Redis
SAI Redis is an implementation of the SAI API which translates API calls into SAI objects which are stored in the ASIC DB.
### 1.2.5 ASIC DB
Redis DB instance #1. Holds serialized SAI objects.
### 1.2.6 syncd
Reads SAI DB data (SAI objects) and performs appropriate calls to Switch SAI.
### 1.2.7 SAI (Redis and Switch)
An unified API which represent the switch state as a set of objects. In SONiC represented in two implementations - SAI DB frontend and ASIC SDK wrapper.
# 2 Requirements
The following watermarks should be supported:
## 2.1 Watermark counters requirements
|                                          | SAI attribute mapping  |
|------------------------------------------|------------------------|
| Ingress headroom per PG                  | SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES            |
| Ingress shared pool occupancy per PG                | SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES            |
| Egress shared pool occupancy per queue (including both unicast queues and multicast queues)      | SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES         |

System behavior:
We consider a maximum of one regular user and a maximum of one special user that comes from streaming telemetry (grpc)

Streaming telemetry is only interested in periodic watermark, i.e., it queries the watermark at regular intervals. The interval is configurable. Streaming telemetry does not care about persistent watermark. 
Regular user is able to query the watermark. Regular user is able to reset the watermark. When the watermark is reset, watermark starts a new recording from the time reset is issued.
Regular user is able to query the persistent watermark. Regular user is able to reset the persistent watermark. When the persistent watermark is reset, persistent watermark starts a new recording from the time reset is issued.

When one regular user and the streaming telemetry coexist, they do not interfere with each other. Their behaviors stay the same as described above. So the software should be able to handle the following situations and return the correct watermark values to each user:

![](https://github.com/mykolaf/SONiC/blob/master/images/watermark_HLD/timeline2.png)


t0 - clear user watermark event

t1 - show user watermark event. Shows highest watermark value for the period t0-t1

t2 - show user watermark event. Shows highest watermark value for the period t0-t2

t3 - clear perisitent watermark event

t4 - show persistent watermark event. Shows highest watermark value for the period t3-t4

t5 - show persistent watermark event. Shows highest watermark value for the period t3-t5

t6 - clear perisitent watermark event

t7 - clear user watermark event

t8 - show user watermark event. Shows highest watermark value for the period t7-t8

t9 - show persistent watermark event. Shows highest watermark value for the period t6-t9

# 3 Modules Design
## 3.1 Modules that need to be updated

### 3.1.1 Counter DB

#### The following new Queue counters should be available for each queue entry in the DB:
- "COUNTERS:queue_vid"
  - SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES
#### For every Ingress PG the following should be available in the DB:
- "COUNTERS:pg_vid"
  - SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES
  - SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES
#### Additionally a few mappings should be added:
- "COUNTERS_PG_PORT_MAP" - map PG oid to port oid
- "COUNTERS_PG_NAME_MAP" - map PG oid to PG name
- "COUNTERS_PG_INDEX_MAP" - map PG oid to PG index

The watermark counters are provided via Flex Counter, with a period of 1s. Flex Counter does clear the value from HW. 

#### New tables will be introduced: 

| Table  | Updated by | Cleared by | Used by | Purpose |
| ------------- | ------------- | --- | --- | --- |
| COUNTERS  | Flex counter  | No need to clear, Flex Counter clears the value on HW every 1s(by default) and overwrites the DB | Lua plugins(Flex counter plugins) | Contains the counters updated by Flex counters |
| PERIODIC_WATERMARKS  | Flex counter lua plugins  | Cleared on telemetry period (watermark orch handles the timer) | Used by Cli (show queue\|priority-group watermark, accessible for telemetry via virtual path | Contains the telemetry watermarks |
| PERSISTENT_WATERMARKS | Flex counter lua plugins | Cleared by user using clear Cli (clear queue\|priority-group persistent-watermark) | Used by Cli (show queue\|priority-group persistent-watermark), accessible for telemetry via virtual path | Contains the highest watermark from switch boot or last clear of persistent watermark |
| USER_WATERMARKS | flex counter lua plugins | Cleared on user request (clear queue\|priority-group watermark) | Used by CLI (show queue\|priority-group watermark |


The structure of all three this tables is the same as COUNTERS table, but the hashes only contain watermark counters.
 
For example: 

 - "PERIODIC_WATERMARKS:queue_vid"
   - "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES"
 - "PERIODIC_WATERMARKS:pg_vid"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES"
 - "PERSISTENT_WATERMARKS:queue_vid"
   - "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES"
 - "PERSISTENT_WATERMARKS:pg_vid"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES"
 - "USER_WATERMARKS:queue_vid"
   - "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES"
 - "USER_WATERMARKS:pg_vid"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES"
   - "SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES"


### 3.1.2 CLI

The CLI flow does not incolve any logic, the cli only gets the data from a related table in DB (see table above).
It does not do any comparison between watermark values.

#### 3.1.2.1 CLI show

New script and alias should be implemented to provide watermark values:

$ show priority-group [watermark|persistent-watermark] headroom

```
Ingress headroom per PG:
Interface                    PG0   PG1   PG2   PG3   PG4   PG5   PG6   PG7
Ethernet0                     0     0     0    23     0     0     0     0
…
Ethernet128                   0     0     0     0     0     0     0     0
```
$ show priority-group [watermark|persistent-watermark] shared

```
Ingress shared pool occupancy per PG:
Interface                   PG0   PG1   PG2   PG3   PG4   PG5   PG6   PG7
Ethernet0                   0  1092     0   380     0     0     0     0
…
Ethernet128                 0     0     0     0     0     0     0     0
```
$ show queue [watermark|persistent-watermark] unicast

```
Egress shared pool occupancy per unicast queue:
Interface                    UC0   UC1   UC2   UC3   UC4   UC5   UC6   UC7
Ethernet0                      0    14     0    11     0     1     0     0
…
Ethernet128                    0     0     0     0     0     0     0     0
```
$ show queue [watermark|persistent-watermark] multicast

```
Egress shared pool occupancy per multicast queue:
Interface                    MC0   MC1   MC2   MC3   MC4   MC5   MC6   MC7
Ethernet0                      0     3     0     0     0     0     0     0
…
Ethernet128                    0     0     0     0     0     0     0     0
```

#### 3.1.2.2 CLI clear

In addition clear functionality will be added:

```
# clear priority-group [watermark|persistent-watermark] headroom

# clear priority-group [watermark|persistent-watermark] shared

# clear queue [watermark|persistent-watermark] unicast

# clear queue [watermark|persistent-watermark] mutlicast
```

The user can clear the persistent watermark, and the "user" watermark. The user can not clear the periodic(telemetry) watermark. The clear command requires sudo, as the watermark is shared for 
all users, and clear will affect every user(if a number of people are connected through ssh).

#### 3.1.2.3 Show/configure telemetry interval

The telemetry interval will be available for viewing and configuring with the folowing CLI:

```
$ show watermark telemetry interval

# config watermark telemetry interval <value>
```

Note: after the new interval is configured, it will be changed only when the current telemetry interval ends.

### 3.1.3 Lua plugins

In order to keep track of highest watermark plugins for queue and priority groups will be implemented.
They will read the new watermark value from COUNTERS table, compare and overwrite the values in PERIODIC_WATERMARKS, PERSISTENT_WATERMARK and USER_WATERMARK table. 

The plugin logic as pseudo code:

```
lua:

    PERIODIC_WATERMARKS[object_vid][watermark_name] = max(COUNTERS[object_vid][watermark_name], PERIODIC_WATERMARKS[object_vid][watermark_name])
    PERSISTENT_WATERMARK[object_vid][watermark_name] = max(COUNTERS[object_vid][watermark_name], PERSISTENT_WATERMARK[object_vid][watermark_name])
    USER_WATERMARK[object_vid][watermark_name] = max(COUNTERS[object_vid][watermark_name], USER_WATERMARK[object_vid][watermark_name])
        
```

### 3.1.4 SWSS

Portorch should be updated:
 - implement new flex counter groups for queue and PG watermarks. This groups are configured with read and clear stats mode, meaning clear from HW every time it's read.
 - implement PG to port map generation

New watermark orch should be implemented with the following functionality:
 - Handle watermarks configuration, for example configuring TELEMETRY_INTERVAL.
 - Listen to CLEAR_WATERMARK notification channel, handle clear watermark requests for USER_WATERMARKS and for HIGHEST_WATERMARKS for every type: PG_HEADROOM, PG_SHARED, QUEUE_UNICAST, QUEUE_MULTICAST.
Clear request only means clearing the data from the related table.
 - Create and manage a timer, which clears the telemetry watermark every TELEMETRY_INTERVAL.

### 3.1.5 SAI Redis

Flex counter should be extended to support new PG counters. 

### 3.1.6 CONFIG DB

Add new table WATERMARK_TABLE with fields like TELEMETRY_PERIOD

### 3.1.7 Syncd

FlexCounter should be extended:

to collect PG stats.
generate maps (PG to port, PG to index, PG to name)
support a new attribute STATS_MODE
use get_*_stats_ext() calls for counter collection to support read_and_clear stats mode.
To for the stats mode the flex counter group schema will be extended:
1) "POLL_INTERVAL"                                                                                     
2) "1000"                                                                                              
3) "STATS_MODE"                                                                                        
4) "STATS_MODE_READ_AND_CLEAR"                                                                         
5) "FLEX_COUNTER_STATUS"                                                                               
6) "disable"  


### 3.1.8 SAI

The sai APIs anf calls are:

 - sai_queue_api

   sai_get_queue_stats_ext()

 - sai_buffer_api
   
   sai_get_ingress_priority_group_stats_ext()

### 3.1.9 gRPC

Sonic-telemetry will have acess to data in WATERMARK an HIGHEST_WATERMARK tables. For this the virtual db should be extended to access the said tables, virual path should should support mapping 
ports to queues and priority groups. The exact syntax of the virtual paths is TBD.

Examples of virtual paths:

|     |      |     |
|---- |:----:| ----| 
| COUNTERS_DB | "WATERMARKS/Ethernet*/Queues/PERIODIC_WATERMARKS" | Queue watermarks on all Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet``<port number``>/Queues/PERIODIC_WATERMARKS" | Queue watermarks on one Ethernet ports | 
| COUNTERS_DB | "WATERMARKS/Ethernet*/PriorityGroups/PERIODIC_WATERMARKS" | PG watermarks on all Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet``<port number``>/PriorityGroups/PERIODIC_WATERMARKS" | PG watermarks on one Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet*/Queues/PERSISTENT_WATERMARKS" | Queue highest watermarks on all Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet``<port number``>/Queues/PERSISTENT_WATERMARKS" | Queue highest  watermarks on one Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet*/PriorityGroups/PERSISTENT_WATERMARKS" | PG highest watermarks on all Ethernet ports |
| COUNTERS_DB | "WATERMARKS/Ethernet``<port number``>/PriorityGroups/PERSISTENT_WATERMARKS" | PG highest watermarks on one Ethernet ports |

### 4 Flows

#### 4.1 Watermark general flow

![](https://github.com/mykolaf/SONiC/blob/master/images/watermark_HLD/WM_general.png)

The core components are the flex counter, watermark orch, DB, CLI. 

The flex counter reads and clears the watermarks on a peroid of 1s by default. The values are put directly to COUNTERS table. The flex counter also has plugins configured for queue and pg, which will be triggered on every flex counter group interval. The lua plugin will update PERIODIC_WATERMARKS, PERSISTENT_WATERMARKS and USER_WATERMARKS with if the new value exceeds the vlaue that was read from the table.  

The watermark orch has 2 main functions:
 - Handle the Timer that clears the PERIODIC_WATERMARKS table. Handle the configuring of the interval for the timer.
 - Handle Clear notificatons. On clear event the orch should just zero-out the corresponding watermarks from the table. It will be soon repopulated by lua plugin.  

The DB contains all the tables with watemarks, and the configuration table.

The Cli reads the watermarks from the tables, formats and outputs it.

#### 4.2 Resetting the telemetry period flow

![](https://github.com/mykolaf/SONiC/blob/master/images/watermark_HLD/WM_period.PNG)

The watermark orch handles notifications on changes in WATERMARK_TABLE in config DB. The new interval will be assigned to the timer during the timer handling, so the orch will reset the interval only when the current timer expires.

#### 4.3 Cli flow

![](https://github.com/mykolaf/SONiC/blob/master/images/watermark_HLD/WM_cli.png)

### 5 Open questions

#### Does the addintion of watermark counters to flex counter influence the performance of the PFC WD counters?
