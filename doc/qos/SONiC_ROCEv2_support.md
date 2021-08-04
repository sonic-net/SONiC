# Feature Name
RDMA (Remote Direct Memory Access) over Converged Ethernet (ROCEv2) support

# High Level Design Document

#### Rev 0.3
# Table of Contents

  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/17/2021 |   Venkatesan Mahalingam         | Initial version                   |
| 0.2 | 07/16/2021 |   Venkatesan Mahalingam         | Addressed review comments                   |
| 0.3 | 08/03/2021 |   Venkatesan Mahalingam         | Added sample configurations                   |

# About this Manual

This document introduces the support of ROCEv2 in mgmt-framework,
this provides the North Bound Interface (NBI) interfaces i.e REST/gNMI/KLISH for the ROCEv2 configurations.

# Scope

This document covers the following,

1) NBI interface to initialize QoS buffers for PFC \
2) NBI interface to create/delete buffer pool \
3) NBI interface to create/delete buffer profile \
4) NBI interface to map/unmap priority group to buffer profile \
5) NBI interface to set/unset PORT table for default buffer profile creation
   based on cable length and speed
6) Unit Testcases

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| RDMA                     | Remote Direct Memory Access         |
|          ROCEv2            |  RDMA over Converged Ethernet version 2           |
|          PFC            |  Priority Flow Control|


# 1 Feature Overview

ROCE provides the ability to transport Infiniband (IB) protocol traffic using RDMA over lossless converged Ethernet
across storage or compute nodes.
ROCEv2 stands for RDMA over Converged Ethernet version 2, this is an extension of ROCE protocol a.k.a routable ROCE,
This overcomes the limitation of ROCEv1 bounded to a single broadcast domain (VLAN),
ROCEv2 encapsulates an RDMA transport packet within the Ethernet/IPv4/UDP packet,
ROCEv2 uses PFC to prevent buffer overflow.

## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities using mgmt-framework interfaces (MF-CLI/REST/gNMI)

#### 1.1.1.1 QoS buffer init/clear
This requirement is to follow the default buffer settings defined for a particular platform.

#### 1.1.1.2 QoS buffer pool add/delete
This requirement is to add/delete the buffer pool for ingress & egress QoS operations.

#### 1.1.1.3 QoS buffer profile add/delete
This requirement is to add/delete the buffer profile for priority group (ingress) & queue(egress) QoS operations.

#### 1.1.1.4 QoS buffer priority group (ingress) to buffer profile map/unmap
This requirement is to map/unmap priority group (ingress) with buffer profile.

#### 1.1.1.5 QoS buffer queue (egress) to buffer profile map/unmap
This requirement is to map/unmap queue (egress) with buffer profile.

#### 1.1.1.5 Get operation on QoS buffer and it's mapping
This displays the output of the buffer pool/profile and it's mapping with priority group and queue.

#### 1.1.1.6 Allow user defined lossless profile based on cable length and speed
This requirement is to add a field in the PORT table to avoid automatic creation of buffer profile
for lossless profile based on the cable length and speed so that user can create the profile based on the particular use-case.

### 1.1.2 Backend mechanisms to support configuration and get
 QoS buffer init populates/clears the following tables in the Redis ConfigDB by default, the size & xoff values vary based on HW capabilities.

```
"BUFFER_POOL": {
 "egress_lossless_pool": {
     "mode": "static",
     "size": "32575488",
     "type": "egress"
 },
 "ingress_lossless_pool": {
     "mode": "dynamic",
     "size": "26284032",
     "type": "ingress",
     "xoff": "6291456"
 }
},
"BUFFER_PROFILE": {
 "egress_lossless_profile": {
     "mode": "static",
     "pool": "[BUFFER_POOL|egress_lossless_pool]",
     "size": "0",
     "static_th": "32575488"
 },
 "egress_lossy_profile": {
     "dynamic_th": "3",
     "mode": "dynamic",
     "pool": "[BUFFER_POOL|egress_lossless_pool]",
     "size": "0"
 },
 "ingress_lossy_profile": {
     "dynamic_th": "3",
     "pool": "[BUFFER_POOL|ingress_lossless_pool]",
     "size": "0"
 },
 "pg_lossless_100000_40m_profile": {
     "dynamic_th": "-3",
     "pool": "[BUFFER_POOL|ingress_lossless_pool]",
     "size": "1248",
     "xoff": "177632",
     "xon": "2288",
     "xon_offset": "2288"
 },
 "pg_lossless_10000_40m_profile": {
     "dynamic_th": "-3",
     "pool": "[BUFFER_POOL|ingress_lossless_pool]",
     "size": "1248",
     "xoff": "37024",
     "xon": "2288",
     "xon_offset": "2288"
 }
},
"BUFFER_PG": {
       "Ethernet0|0": {
           "profile": "[BUFFER_PROFILE|ingress_lossy_profile]"
       },
       "Ethernet0|3-4": {
           "profile": "[BUFFER_PROFILE|pg_lossless_100000_40m_profile]"
       },
       ........
       .......
}

"BUFFER_QUEUE": {
  "Ethernet0|0-2": {
          "profile": "[BUFFER_PROFILE|egress_lossy_profile]"
   },
  "Ethernet0|3-4": {
          "profile": "[BUFFER_PROFILE|egress_lossless_profile]"
   },
  "Ethernet0|5-6": {
          "profile": "[BUFFER_PROFILE|egress_lossy_profile]"
  },
  .......
  .......
}                                                                                                                                                                        48        563,7         19%

```
The above tables are populated by default already in the SONiC system upon executing
the 'config qos buffer reload' Click command, we are providing the following configuration options to fine tune the values
and the get support will be provided to dump the buffer information.

### 1.1.3 Functional Requirements

Provide management framework support to
- Configure buffer pool and buffer profile
- Associate PG & Queue with buffer profile

### 1.1.4 Configuration and Management Requirements
- CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

### 1.1.6 Scalability Requirements

### 1.1.7 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach
- Implement QoS buffer configuration and get support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
The front end code change will be done in management-framework container including:
- XML file for the CLI
- Python script to handle CLI request (actioner)
- Jinja template to render CLI output (renderer)
- OpenConfig YANG model for QoS buffer openconfig-qos.yang
- SONiC QOS buffer model on Redis DB schema
- transformer functions to
   * convert OpenConfig YANG model to SONiC YANG model for buffer related configurations

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure QoS buffer configurations via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide CLI, gNMI and REST support for QoS buffer onfigurations.

## 2.3 Backend change to support new configurations
Provide change in management framework and buffermgrd modules.

## 2.4 Configurations already supported in QoS for TC mapping

## 2.4.1 dot1p & DSCP to Traffic Class mapping: -
DSCP is preferred over dot1p when both are present in the data traffic but both is not expected to co-exist.
```
sonic(config)# qos map dot1p-tc rocev2_dot1p-to-tc
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 4 traffic-class 4
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)#

sonic(config)# qos map dscp-tc rocev2_dscp-to-tc
sonic(conf-dscp-tc-map-rocev2_dscp-to-tc)# dscp 6 traffic-class 4
sonic(conf-dscp-tc-map-rocev2_dscp-to-tc)#
```
### 2.4.2 Traffic class to dot1p & DSCP mapping:
```
sonic(config)# qos map tc-dot1p rocev2_tc-to-dot1p
sonic(conf-tc-dot1p-map-rocev2_tc-to-dot1p)# traffic-class 4 dot1p 4
sonic(conf-tc-dot1p-map-rocev2_tc-to-dot1p)#

sonic(config)# qos map tc-dscp rocev2_tc-to-dscp
sonic(conf-tc-dscp-map-rocev2_tc-to-dscp)# traffic-class 4 dscp 6
sonic(conf-tc-dscp-map-rocev2_tc-to-dscp)#
```
## 2.4.3 Traffic Class to Queue mapping:
```
sonic(config)# qos map tc-queue rocev2_tc-q
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 4 queue 4
```
### 2.4.4 Traffic Class to Queue mapping: (PFC Pause frames priority only 3 & 4 are supported HW)

```
sonic(config)# qos map tc-pg rocev2_tc-pg
sonic(conf-tc-pg-map-rocev2_tc-pg)# traffic-class 4 priority-group 4
```

### 2.4.5 ECN configuration:
```
sonic(config)# qos wred-policy rocev2_wred
sonic(conf-wred-rocev2_wred)# green minimum-threshold 1048 maximum-threshold 2097 drop-probability 5
sonic(conf-wred-rocev2_wred)# ecn all

PFC watchdog configuration: (PFC pause frame storm control)
---------------------------
sonic(config)# priority-flow-control watchdog polling-interval 300
sonic(config)# priority-flow-control watchdog counter-poll
```
# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for QoS buffer.

## 3.2 DB Changes

### 3.2.1 CONFIG DB
Existing QoS buffer tables will be used and a new field (default_lossless_buffer_profile) will be introduced in PORT table to avoid the creation of profile based
on cable length and speed e.g [BUFFER_PROFILE|pg_lossless_40000_300m_profile]

**PORT table**
* Producer: Mangement framework/config_db.json/Click command
* Consumer: buffermgrd
* Description: Update existing table to store 'default_lossless_buffer_profile' configuration.
* Schema:
```
;Existing table
;defines PORT information. Store default_lossless_buffer_profile configuration
;
;Status: stable
key = PORT|ifname;
default_lossless_buffer_profile = true/false ; default value - true
```

### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Configuration Manager - buffermgrd
  Avoid the default buffer profile creation based on cable length and speed when the field 'default_lossless_buffer_profile' in PORT table is set to false.
### 3.3.2 Orchestration Agent

### 3.3.3 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models

YANG model needed for QoS buffer handling in the management framework:

**openconfig-qos-deviation.yang** - RPC for buffer initialization \
**openconfig-qos-buffer.yang** - YANG objects for fine tuning the system defaults

Supported yang objects and attributes:
```diff

module: openconfig-qos-deviation

  rpcs:
    +---x qos-buffer-config
       +---w input
       |  +---w operation?   enumeration
       +--ro output
          +--ro status?          uint32
          +--ro status-detail?   string

module: openconfig-qos
    +--rw qos
      |
      +--rw interfaces
      |  +--rw interface* [interface-id]
      |     |
      |     +--rw oc-qos-dev:buffer
      |        +--rw oc-qos-dev:config
      |        |  +--rw oc-qos-dev:default-lossless-buffer-profile?   boolean
      |        +--ro oc-qos-dev:state
      |           +--ro oc-qos-dev:default-lossless-buffer-profile?   boolean
      +--rw oc-qos-ext:buffer
         +--rw oc-qos-ext:buffer-pools
         |  +--rw oc-qos-ext:buffer-pool* [name]
         |     +--rw oc-qos-ext:name      -> ../config/name
         |     +--rw oc-qos-ext:config
         |     |  +--rw oc-qos-ext:name?   string
         |     |  +--rw oc-qos-ext:type    qos-buffer-type
         |     |  +--rw oc-qos-ext:size    uint32
         |     |  +--rw oc-qos-ext:xoff?   uint32
         |     |  +--rw oc-qos-ext:mode                       qos-buffer-mode
         |     +--ro oc-qos-ext:state
         |        +--ro oc-qos-ext:name?   string
         |        +--ro oc-qos-ext:type    qos-buffer-type
         |        +--ro oc-qos-ext:size    uint32
         |        +--ro oc-qos-ext:xoff?   uint32
         |        +--rw oc-qos-ext:mode                       qos-buffer-mode
         +--rw oc-qos-ext:buffer-profiles
         |  +--rw oc-qos-ext:buffer-profile* [name]
         |     +--rw oc-qos-ext:name      -> ../config/name
         |     +--rw oc-qos-ext:config
         |     |  +--rw oc-qos-ext:name?                      string
         |     |  +--rw oc-qos-ext:pool                       -> ../../../../buffer-pools/buffer-pool/name
         |     |  +--rw oc-qos-ext:type                       qos-buffer-type
         |     |  +--rw oc-qos-ext:size                       uint32
         |     |  +--rw oc-qos-ext:static-threshold           uint32
         |     |  +--rw oc-qos-ext:dynamic-threshold          uint32
         |     |  +--rw oc-qos-ext:pause-threshold?           uint32
         |     |  +--rw oc-qos-ext:resume-threshold?          uint32
         |     |  +--rw oc-qos-ext:resume-offset-threshold?   uint32
         |     +--ro oc-qos-ext:state
         |        +--ro oc-qos-ext:name?                      string
         |        +--ro oc-qos-ext:pool                       -> ../../../../buffer-pools/buffer-pool/name
         |        +--ro oc-qos-ext:type                       qos-buffer-type
         |        +--ro oc-qos-ext:size                       uint32
         |        +--ro oc-qos-ext:static-threshold           uint32
         |        +--ro oc-qos-ext:dynamic-threshold          uint32
         |        +--ro oc-qos-ext:pause-threshold?           uint32
         |        +--ro oc-qos-ext:resume-threshold?          uint32
         |        +--ro oc-qos-ext:resume-offset-threshold?   uint32
         +--rw oc-qos-ext:buffer-priority-groups
         |  +--rw oc-qos-ext:buffer-priority-group* [ifname priority-group]
         |     +--rw oc-qos-ext:ifname            -> ../config/ifname
         |     +--rw oc-qos-ext:priority-group    -> ../config/priority-group
         |     +--rw oc-qos-ext:config
         |     |  +--rw oc-qos-ext:ifname?           oc-if:base-interface-ref
         |     |  +--rw oc-qos-ext:profile           -> ../../../../buffer-profiles/buffer-profile/name
         |        +--ro oc-qos-ext:ifname?           oc-if:base-interface-ref
         |        +--ro oc-qos-ext:priority-group?   string
         |        +--ro oc-qos-ext:profile           -> ../../../../buffer-profiles/buffer-profile/name
         +--rw oc-qos-ext:buffer-queues
            +--rw oc-qos-ext:buffer-queue* [ifname queue]
               +--rw oc-qos-ext:ifname    -> ../config/ifname
               +--rw oc-qos-ext:queue     -> ../config/queue
              +--rw oc-qos-ext:config
              |  +--rw oc-qos-ext:ifname?    oc-if:base-interface-ref
              |  +--rw oc-qos-ext:queue?     string
              |  +--rw oc-qos-ext:profile    -> ../../../../buffer-profiles/buffer-profile/name
              +--ro oc-qos-ext:state
                 +--ro oc-qos-ext:ifname?    oc-if:base-interface-ref
                 +--ro oc-qos-ext:queue?     string
                 +--ro oc-qos-ext:profile    -> ../../../../buffer-profiles/buffer-profile/name

```

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```
##### 3.6.2.1.1 Initialize the buffer based on system defaults
Initialize the buffer defaults based on platform specific values (ingress/ingress buffer pools size, buffer profile, priority-group, queue..etc)
```
sonic(config)# qos buffer init

```

##### 3.6.2.1.2 Delete buffer pool
Clear default buffer initialization.
```
sonic(config)# no qos buffer init

```
##### 3.6.2.1.3 Configure buffer pool
Configure shared head room size for the ingress buffer pool (fixed name - ingress_lossless_pool), other settings such as pool size and egress pool are automatically created during buffer init.
Please refer user guide for platform specific defaults and based on that use these CLIs to fine-tune the numbers for the use-case.
```
sonic(config)# qos buffer pool ingress_lossless_pool shared-headroom-size shared-headroom-size <xoff>

Note: We use fixed pool name due to the backend restriction to use fixed pool name, once that's relaxed, any pool-name can be used from NBI.
```

##### 3.6.2.1.4 Delete buffer pool
Delete buffer pool.
```
sonic(config)# no qos buffer-pool <name>

```
##### 3.6.2.1.5 Configure buffer profile
Configure buffer profile and associate with buffer pool.
```
sonic(config)# qos buffer-profile <name> <pool-name> <qmin/pgmin reserved-buffer-size-in-bytes> [threshold-mode {static | dynamic}]   { static-threshold <value> | dynamic-threshold <signed-integer-value>}}  [pause [pause-threshold <xoff>] [resume-threshold <xon>] [resume-offset-threshold <xon_offset>] ]

```

##### 3.6.2.1.6 Delete buffer profile
Delete buffer profile.
```
sonic(config)# no qos buffer-profile <name>

```
##### 3.6.2.1.7 Associate priority-group with buffer profile
Associate priority group (ingress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# qos buffer priority-group <pg-value-range> <profile-name(depend on profile config)>
```
##### 3.6.2.1.8 Dissociate priority-group from buffer profile
Dissociate priority-group (ingress) from buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# no qos buffer priority-group <pg-value-range>
```
##### 3.6.2.1.9 Associate queue with buffer profile
Associate queue (egress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# qos buffer queue <pg-value-range> <profile-name(depend on profile config)>
```
##### 3.6.2.1.10 Dissociate queue from buffer profile
Dissociate queue (egress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# no qos buffer queue <pg-value-range>
```
##### 3.6.2.1.11 Enable/disable default lossless buffer profile
New field (default_lossless_buffer_profile) will be introduced in PORT table to avoid creation of buffer profile based
on cable length and speed e.g [BUFFER_PROFILE|pg_lossless_40000_300m_profile] for lossless traffic in SWSS buffermgrd.


```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# [no] qos default-lossless-buffer-profile
```
#### 3.6.2.2 Show Commands
#### 3.6.2.2.1 Show Buffer Pool
The below command shows buffer pool information.
```
sonic# show buffer pool
Pool egress_lossless_pool:
   mode : static
   size : 32575488 bytes
   type : egress
Pool ingress_lossless_pool:
   mode             : dynamic
   size             : 26284032 bytes
   type             : ingress
   shared head room : 6291456 bytes
```
#### 3.6.2.2.2 Show Buffer Profile
The below command shows buffer profile information.
```
sonic# show buffer profile
Profile egress_lossless_profile:
   mode             : static
   pool             : egress_lossless_pool
   size             : 0
   static_threshold : 32575488 bytes
```
#### 3.6.2.2.3 Show interface to priority group mapping
The below command shows all interfaces to priority group or particular interface
```
sonic# show buffer interface all priority-group
Interface   Priority-group     Profile
Ethernet0        0             ingress_lossy_profile
Ethernet4        3-4           ingress_lossless_profile
.......
.......

sonic# show buffer interface Ethernet0 priority-group
Interface   Priority-group     Profile
Ethernet0        0             ingress_lossy_profile
sonic# show buffer interface all queue
Interface       Queue          Profile
Ethernet0        0             ingress_lossy_profile
Ethernet4        3-4           ingress_lossless_profile
.......
.......
````
#### 3.6.2.2.4 Show interface to queue mapping
The below command shows all interfaces to queue or particular interface
```
sonic# show buffer interface all queue
Interface       Queue     Profile
Ethernet0        0             ingress_lossy_profile
Ethernet4        3-4           ingress_lossless_profile
.......
.......
sonic# show buffer interface Ethernet0 queue
Interface       Queue          Profile
Ethernet0        0             ingress_lossy_profile (edited)
```
#### 3.6.2.3 Sample configurations
The below configurations are already supported and should be configured along with above buffer configuration for ROCEv2 Functionality.

| CoS/DSCP |     Traffic Class  |    Priority Group          |Queue|PFC (supported only for 3 & 4 Traffic Class)|Scheduling |
|---|-----------|------------------|-----------------------------------|----|---|
| 0-1,5-6 | 6 |   0         | 6                   | No | DWRR - 40% |
|2	|1|	0	|3	|No	|DWRR - 25%|
|3	|3	|3	|1	|Yes|	DWRR - 10%|
|4	|4	|4	|4	|Yes	|DWRR - 25%|
|7	|7	|0	|7	|No	|Strict|

###### 3.6.2.3.1	dot1p to Traffic Class mapping
```
sonic(config)# qos map dot1p-tc rocev2_dot1p-to-tc
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 0-1,5-6 traffic-class 6
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 2 traffic-class 1
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 3 traffic-class 3
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 4 traffic-class 4
sonic(conf-dot1p-tc-map-rocev2_dot1p-to-tc)# dot1p 7 traffic-class 7

     Note: Similar mapping can be for DSCP to TC as well.
```
###### 3.6.2.3.2	Traffic Class to Queue mapping
```
sonic(config)# qos map tc-queue rocev2_tc-q
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 6 queue 6
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 1 queue 3
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 3 queue 1
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 4 queue 4
sonic(conf-tc-queue-map-rocev2_tc-q)# traffic-class 7 queue 7
```
###### 3.6.2.3.3 Traffic Class to Priority Group mapping
```
sonic(config)# qos map tc-pg rocev2_tc-pg
sonic(conf-tc-pg-map-rocev2_tc-pg)# traffic-class 0-2,5-7 priority-group 0
sonic(conf-tc-pg-map-rocev2_tc-pg)# traffic-class 3 priority-group 3
sonic(conf-tc-pg-map-rocev2_tc-pg)# traffic-class 4 priority-group 4
```
###### 3.6.2.3.4	PFC priority to Queue mapping
```
sonic(config)# qos map pfc-priority-queue rocev2_pfc-to-q
sonic(conf-pfc-priority-queue-map-rocev2_pfc-to-q)# pfc-priority 3 queue 1
sonic(conf-pfc-priority-queue-map-rocev2_pfc-to-q)# pfc-priority 4 queue 4
```
###### 3.6.2.3.5	ETS (Enhanced Transmission Selection) configurations
```
sonic(config)# qos scheduler-policy rocev2_sched1
sonic(conf-sched-policy-rocev2_sched1)#
sonic(conf-sched-policy-rocev2_sched1)# queue 6
sonic(conf-scheduler-rocev2_sched1-queue-6)# type dwrr
sonic(conf-scheduler-rocev2_sched1-queue-6)# weight 40
sonic(conf-scheduler-rocev2_sched1-queue-6)# exit
sonic(conf-sched-policy-rocev2_sched1)# queue 3
sonic(conf-scheduler-rocev2_sched1-queue-3)# type dwrr
sonic(conf-scheduler-rocev2_sched1-queue-3)# weight 25
sonic(conf-scheduler-rocev2_sched1-queue-3)# exit
sonic(conf-sched-policy-rocev2_sched1)# queue 1
sonic(conf-scheduler-rocev2_sched1-queue-1)# type dwrr
sonic(conf-scheduler-rocev2_sched1-queue-1)# weight 10
sonic(conf-scheduler-rocev2_sched1-queue-1)# exit
sonic(conf-sched-policy-rocev2_sched1)# queue 4
sonic(conf-scheduler-rocev2_sched1-queue-4)# type dwrr
sonic(conf-scheduler-rocev2_sched1-queue-4)# weight 25
sonic(conf-scheduler-rocev2_sched1-queue-4)# exit
sonic(conf-sched-policy-rocev2_sched1)# queue 7
sonic(conf-scheduler-rocev2_sched1-queue-7)# type strict
sonic(conf-scheduler-rocev2_sched1-queue-7)#
```
###### 3.6.2.3.6	Apply QoS templates on interface
```
sonic(config)# interface Ethernet <id>
sonic(conf-if-Ethernet0)# qos-map dot1p-tc  rocev2_dot1p-to-tc
sonic(conf-if-Ethernet0)# qos-map tc-queue  rocev2_tc-q
sonic(conf-if-Ethernet0)# qos-map tc-pg  rocev2_tc-pg
sonic(conf-if-Ethernet0)# qos-map pfc-priority-queue rocev2_pfc-to-q
sonic(conf-if-Ethernet0)# scheduler-policy rocev2_sched1
sonic(conf-if-Ethernet0)# priority-flow-control priority 3
sonic(conf-if-Ethernet0)# priority-flow-control priority 4
```
#### 3.6.2.4 Debug Commands

#### 3.6.2.5 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing buffer configuration information from CONFIG DB.
POST - Add buffer configuration into CONFIG DB.
PATCH - Update existing buffer Configuration information in CONFIG DB.
DELETE - Delete a existing buffer configuration from CONFIG DB.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support
This support is added in the hostcfgd and hence no explicit handling is needed.

# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### 9.1 Configuration via CLI
1) Initialize buffer settings to populate various buffer tables and make sure all the tables are populated.\
2) Remove buffer settings and check whether all the default tables are removed \
3) Create buffer pool (type ingress & egress) and check the config-DB \
4) Remove buffer pool and verify that buffer pool entry is not present in the config-DB \
5) Disable default buffer profile under interface and verify that default lossless profile
   based on able length and speed is not created.

#### 9.2 Configuration via gNMI

Same test as CLI configuration Test but using gNMI request.
Additional tests will be done to set buffer configuration at different levels of Yang models.

#### 9.3 Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done to get buffer configuration and buffer states at different levels of Yang models.

#### 9.4 ONCHANGE/SAMPLE/TARGET_DEFINED subscription support

Below is the list of URIs supported at the top level for gNMI subscription request,
all subsequent paths from parent are expected to support the same subscription request as that of the parent.

|     Paths                                                                        | ON_CHANGE/SAMPLE/TARGET_DEFINED Supported yes(y)/no(n) |
|---------------------------------------------------------------------------| -------------|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-pools"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-pools/buffer-pool[name=*]"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-profiles"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-profiles/buffer-profiles[name=*]"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-priority-groups"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-priority-groups/buffer-priority-group[ifname=*, priority-group=*]"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-queues"|y|
|"/openconfig-qos:qos/openconfig-qos-buffer:buffer/buffer-queues/buffer-queue[ifname=*, queue=*]"|y|

#### 9.4 Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request
Additional tests will be done to set buffer configuration at different levels of Yang models.

**URIs for REST configurations:**
Buffer init/clear RPC -  /restconf/data/openconfig-qos:qos-buffer-config
Buffer configuration parent URI  - /restconf/data/openconfig-qos/openconfig-qos-ext:buffer
Default lossless profile configuration under interface - /restconf/data/openconfig-qos/oc-qos:interfaces/oc-qos:interface/oc-qos-dev:buffer/oc-qos-dev:config/oc-qos-dev:default-lossless-buffer-profile
#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done to get buffer configuration and buffer states at different levels of Yang models.


# 10 Internal Design Information
