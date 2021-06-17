# Feature Name
RDMA (Remote Direct Memory Access) over Converged Ethernet (ROCEv2) support

# High Level Design Document

#### Rev 0.1
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



# About this Manual

This document introduces the support of ROCEv2 in mgmt-framework,
this provides the North Bound Interface (NBI) interfaces i.e REST/gNMI/KLISH for the ROCEv2 configurations.

# Scope

This document covers the following,

1) NBI interface to initialize QoS buffers for PFC \
2) NBI interface to create/delete buffer pool \
3) NBI interface to create/delete buffer profile \
4) NBI interface to map/unmap priority group to buffer profile \
5) Unit Testcases

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
ROVEv2 uses PFC to prevent buffer overflow.

## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities

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
- Configure buffer pool and buffer pool
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
Existing QoS buffer tables will be used and a new field will be introduced in PORT table to avoid taking the buffer-mgr created profile based
on cable length and speed e.g [BUFFER_PROFILE|pg_lossless_40000_300m_profile]

### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models

YANG model needed for QoS buffer handling in the management framework:
 **openconfig-qos-buffer.yang**

Supported yang objects and attributes:
```diff

module: openconfig-qos
    +--rw qos
      |
      +--rw oc-qos-ext:buffer
         +--rw oc-qos-ext:buffer-pools
         |  +--rw oc-qos-ext:buffer-pool* [name]
         |     +--rw oc-qos-ext:name      -> ../config/name
         |     +--rw oc-qos-ext:config
         |     |  +--rw oc-qos-ext:name?   string
         |     |  +--rw oc-qos-ext:type    qos-buffer-type
         |     |  +--rw oc-qos-ext:size    uint32
         |     |  +--rw oc-qos-ext:xoff?   uint32
         |     +--ro oc-qos-ext:state
         |        +--ro oc-qos-ext:name?   string
         |        +--ro oc-qos-ext:type    qos-buffer-type
         |        +--ro oc-qos-ext:size    uint32
         |        +--ro oc-qos-ext:xoff?   uint32
         +--rw oc-qos-ext:buffer-profiles
         |  +--rw oc-qos-ext:buffer-profile* [name]
         |     +--rw oc-qos-ext:name      -> ../config/name
         |     +--rw oc-qos-ext:config
         |     |  +--rw oc-qos-ext:name?                      string
         |     |  +--rw oc-qos-ext:pool                       -> ../../../../buffer-pools/buffer-pool/name
         |     |  +--rw oc-qos-ext:type                       qos-buffer-type
         |     |  +--rw oc-qos-ext:size                       uint32
         |     |  +--rw oc-qos-ext:mode                       qos-buffer-mode
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
         |        +--ro oc-qos-ext:mode                       qos-buffer-mode
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

##### 3.6.2.1.1 Configure buffer pool
Configure ingress and egress type buffer pools.
```
sonic(config)# qos buffer-pool <name> <shared-buffer-size-in-bytes> { [type ingress shared-headroom-size <xoff (included in the shared-buffer-size-in-bytes)>]  | [type egress ]}

```

##### 3.6.2.1.2 Delete buffer pool
Delete buffer pool.
```
sonic(config)# no qos buffer-pool <name>

```
##### 3.6.2.1.3 Configure buffer profile
Configure buffer profile and associate with buffer pool.
```
sonic(config)# qos buffer-profile <name> <pool-name> <qmin/pgmin reserved-buffer-size-in-bytes> [threshold-mode {static | dynamic}]   { static-threshold <value> | dynamic-threshold <signed-integer-value>}}  [pause [pause-threshold <xoff>] [resume-threshold <xon>] [resume-offset-threshold <xon_offset>] ]

```

##### 3.6.2.1.4 Delete buffer profile
Delete buffer profile.
```
sonic(config)# no qos buffer-profile <name>

```
##### 3.6.2.1.5 Associate priority-group with buffer profile
Associate priority group (ingress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# qos buffer priority-group <pg-value-range> <profile-name(depend on profile config)>
```
##### 3.6.2.1.6 Dissociate priority-group from buffer profile
Dissociate priority-group (ingress) from buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# no qos buffer priority-group <pg-value-range>
```
##### 3.6.2.1.7 Associate queue with buffer profile
Associate queue (egress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# qos buffer queue <pg-value-range> <profile-name(depend on profile config)>
```
##### 3.6.2.1.8 Dissociate queue from buffer profile
Dissociate queue (egress) with buffer profile.
```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# no qos buffer queue <pg-value-range>
```
##### 3.6.2.1.8 Enable/disable default lossless buffer profile
New field will be introduced in PORT table to avoid taking the buffer-mgr created profile based
on cable length and speed e.g [BUFFER_PROFILE|pg_lossless_40000_300m_profile]

```
sonic(config)# interface Ethernet0
sonic(conf-if-Ethernet0)# [no] qos default-lossless-buffer-profile
```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

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
#### Configuration via CLI
1) Initialize buffer settings to populate various buffer tables and make sure all the tables are populated.
2) Remove buffer settings and check whether all the default tables are removed
3) Create buffer pool (type ingress & egress) and check the config-DB
4) Remove buffer pool and verify that buffer pool entry is not present in the config-DB
5) Create

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request.
Additional tests will be done to set buffer configuration at different levels of Yang models.

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done to get buffer configuration and buffer states at different levels of Yang models.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request
Additional tests will be done to set buffer configuration at different levels of Yang models.

**URIs for REST configurations:**

Buffer configuration parent URI  - /restconf/data/openconfig-qos/openconfig-qos-ext:buffer

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done to get buffer configuration and buffer states at different levels of Yang models.


# 10 Internal Design Information
