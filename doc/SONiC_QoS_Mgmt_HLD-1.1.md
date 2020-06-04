# QoS

# High Level Design Document
#### Rev 1.0

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
| 1.0 | 10/15/2019  | Oliver Hu, Ashok Daparthi, Srinadh Penugondaa, Eddy Lem | Initial version  |


# About this Manual
This document provides general information about QoS configuration in SONiC using the management framework.

# Scope
Covers Northbound interface for the QoS feature, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|:-------------------------|:------------------------------------|
| QoS                      | Quality of Service                 |

# 1 Feature Overview

Provide management framework capabilities to handle:
- Traffic classification
- Queue management
- Traffic scheduling
- Buffer Threshold configuration
- Watermark statistics
- Associated show and clear commands.

## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide management framework support to existing SONiC capabilities with respect to QoS.

### 1.1.2 Configuration and Management Requirements
- IS-CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

## 1.2 Design Overview

### 1.2.1 Basic Approach
QoS deals with the traffic prioritization and scheduling.

The basic approach is to classify different traffic to different service category, ie. putting traffic to different queues.

In addition defining different queue behavior controls how the traffic is serviced.   

### 1.2.2 Container
Management container

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases

Anywhere user wants to give different traffic with different treatment.

## 2.2 Functional Description

Functionally QoS provides user the capability to handle different traffic with different level of service, from separate queuing to different scheduling behavior.  

# 3 Design
## 3.1 Overview

To support quality of service, first user has to have a way to differentiate different types of traffic. Provided here is the method based on the DSCP value of the packet. Packets are classified into different internal traffic class based on their DSCP value and will be sent to different queues for scheduling.

To manage the queue overflow situtation, WRED configuration is provided to allow queue to drop packet early before the queue is completely full. Or else packet will always be dropped when the queue is full.

Once packets enter the queue, they will be eligible to be scheduled to be sent out to the wire. Scheduling the queue for transmit is done via Strict Priority (SP) method or Weighted Round Robin (WRR). Minimum guaranteed bandwidth, maximum allowed bandwidth and burst size are configurable for each queue to ensure guaranteed service and allow oversubscription for extra bandwidth.



## 3.2 User Interface
### 3.2.1 Data Models

Open config defines a data model for [QoS](https://github.com/openconfig/public/tree/master/release/models/qos)

This data model lacks certain definitions for SONIC QoS feature. Some features that the data model supports also has limitations for future feature expansion.

As a result, our data model will be loosely based on Open Config YANG, with our enhancement and  modifications on top of it.
Here is a list of proposed new data model or existing data models from Open Config.

- WRED profile  

    No Open Config YANG available.  
    Augment Open Config YANG model with new definitions similar to [SONIC YANG for WRED profile](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-wred-profile.yang)
    Configuring WRED on Green color only supported in this release.


- Scheduler Policy  

	openconfig-qos-elements.yang::qos-scheduler-policy-config


- DSCP to TC map  
  No Open Config YANG available.  
  Augment Open Config YANG model with new definitions similar to [SONIC YANG for DSCP-to-TC-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-dscp-tc-map.yang)


- Dot1p to TC map  

  No Open Config YANG available.  
  Augment Open Config YANG model with new definitions similar to [SONIC YANG for DOT1P-to-TC-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-dot1p-tc-map.yang)


- TC to Queue map  

  No Open Config YANG available.   
  Augment Open Config YANG model with new definition similar to [SONIC YANG for TC-to-Queue-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-tc-queue-map.yang)



- TC to Priority group  

  No Open Config YANG available.   
  Augment Open Config YANG model with new definition similar to [SONIC YANG for TC-to-priority-group-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-tc-priority-group-map.yang)


- PFC priority to Queue  

  No Open Config YANG available.   
  Augment Open Config YANG model with new definition similar to [SONIC YANG for PFC-pirority-to-queue-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-pfc-priority-queue.yang)


- PFC Configuration

  No open config support for enable PFC priorities on interface.
  Augment Open Config YANG model with new attribute for PFC priorities and PFC Asynchronous mode.


- Interface QoS  

  openconfig-qos-interfaces.yang:: qos-interfaces-config
  openconfig-qos-elements.yang:: qos-queue-config


- QoS Statistics  

  openconfig-qos-interfaces.yang:: qos-interfaces/interface/interface-id/output/queues/queue/state  
  Augment Open Config YANG model with new definitions for queue statistics and watermark statistics.


- QoS Clear Statistics  

  No Open Config YANG available.   
  RPC based sonic YANG model with new definitions for clear QOS statistics and watermark statistics.


- Threshold Breach  

  Augment Open Config YANG model with new definitions of Thresholds breach get.



### 3.2.2 CLI

#### 3.2.2.1 Configuration Commands

- Configuring WRED
````
  sonic(config)# wred <name>
  sonic(conf-wred-<name>)# random-detect color [green|yellow|red] minimum-threshold 100 maximum-threshold 300
  drop-probability 40
  sonic(conf-wred-<name>)# random-detect ecn <ecn_none/green/all>

  sonic(config)# no wred <name>
````
- Configure Scheduler Policy for queues
````
  sonic(config)# scheduler-policy <name>
  sonic(conf-sched-policy)# scheduler queue <q#>
  sonic(conf-sched-policy-q)# priority
  sonic(conf-sched-policy-q)# min <val>
  sonic(conf-sched-policy-q)# min-burst <val>
  sonic(conf-sched-policy-q)# max <val>
  sonic(conf-sched-policy-q)# max-burst <val>
  sonic(conf-sched-policy-q)# weight <val>

  sonic(conf-sched-policy)# no scheduler <q#>
  sonic(config)# no scheduler-policy <name>   
````
- Configure Scheduler Policy for port shaper

````
  sonic(config)# scheduler-policy <name>
  sonic(conf-sched-policy)# scheduler port
  sonic(conf-sched-policy-port)# max <val>
  sonic(conf-sched-policy-port)# max-burst <val>
````

- Config DSCP to Traffic Class map  
````
  sonic(config)# qos-map dscp-to-tc-map <name>
  sonic(conf-qos-map)# dscp {<dscp-value>} traffic-class <0..7>  
  sonic(conf-qos-map)# no dscp {<dscp-value>}

  sonic(config)# no dscp-to-tc-map <name>
````
- Config DOT1P to Traffic Class map  
````
  sonic(config)# qos-map dot1p-to-tc-map <name>
  sonic(conf-qos-map)# dot1p {<dot1p-value>} traffic-class <0..7>  
  sonic(conf-qos-map)# no dot1p {<dscp-value>}

  sonic(config)# no dot1p-to-tc-map <name>
````

- Config Traffic Class to Queue map
````
  sonic(config)# qos-map tc-to-queue-map <name>
  sonic(conf-qos-map)# traffic-class {<tc-value>} queue <0..7>
````

- Config interface QoS
````
  sonic(config)# qos interface <name>
  sonic(conf-if-name)# dscp-to-tc-map <name>
  sonic(conf-if-name)# dot1p-to-tc-map <name>
  sonic(conf-if-name)# tc-to-queue-map <name>
  sonic(conf-if-name)# pfc-priority <0-7>
  sonic(conf-if-name)# pfc asymmetric
  sonic(conf-if-name)# scheduler-policy <name>
  sonic(conf-if-name)# queue <q#> wred-profile <wred-profile-name>
  sonic(conf-if-name)# queue <q#> [ucast|mcast] threshold <val>

  sonic(conf-if-name)# no dscp-to-tc-map <name>
  sonic(conf-if-name)# no dot1p-to-tc-map <name>
  sonic(conf-if-name)# no tc-to-queue-map <name>
  sonic(conf-if-name)# no scheduler-policy <name>
  sonic(conf-if-name)# no queue <q#> wred-profile <wred-profile-name>
````

#### 3.2.2.2 Show Commands

- Show WRED
````
  >show wred {<name>}
  Sample Output:
    ---------------------------------------------------
    Profile                : test
    ecn                    : ecn_all
    green-min-threshold    : 1048576
    green-max-threshold    : 2097152
````
- Show Scheduler Policy  

````
>show scheduler-policy <name>   
Sample output:
sonic# show scheduler-policy
 Scheduler Policy: test
   Scheduler: 0
              Weight: 10
              Cir: 100000
              Pir: 200000
              Min-burst: 100
              Max-burst: 200
   Scheduler: port
              Pir: 300000
              Max-burst: 2000
````

- Show interface QoS configuration
````
  >show qos interface <name>  	
  Sample Output:
      Ethernet 1/1/10
      DSCP-to-Traffic-Class map: dscp-to-tc-map_1
      DOT1P-to-Traffic-Class map: dot1p-to-tc-map_1
      Traffic-Class-to-Queue map: tc-to-queue-map_1
      Scheduler policy: scheduler-policy_1

  >show qos interface <name> queue 1   	
      Sample Output:
          Q1 WRED profile:  wred-profile_1
          Q5 WRED profile:  wred-profile_2
````

- Show DSCP to TC map

````
>show qos-map dscp-to-tc-map <name>   
Sample Output:
sonic# show dscp-tc-map
DSCP-TC-MAP: test
----------------------------
    DSCP TC
----------------------------
    0    0
    1    1
----------------------------

````
- Show DOT1P to TC map

````
>show qos-map dot1p-to-tc-map <name>   
 Sample Output:
 sonic# show dot1p-tc-map
 DOT1P-TC-MAP: test
 ----------------------------
            DOT1P TC
 ----------------------------
             0    0
             1    1
----------------------------

````
- Show TC to Queue map

````
>show tc-queue-map <name>
  Sample Output:
  sonic# show tc-queue-map
    TC-Q-MAP: test
  ----------------------------
                  TC  Q
 ----------------------------
                  0    0
                  1    1
----------------------------

````

- Show QoS statistics

````
show queue counters {interface ethernet <name> {queue <qid>}}

show queue (watermark|persistent-watermark) (multicast | unicast) interface[<interface-name>]

show priority-group (watermark|persistent-watermark) (headroom | shared) interface [<interface-name>]

show queue buffer-threshold-breaches

  > show queue counters interface ethernet <name> queue <qid>
  Sample Output:
    	> show queue counters interface ethernet 1/1/1 queue 3
  sonic# show queue counters interface Ethernet 0 queue 0
  -------------------------------------------------------------------
  TxQ  Counter/pkts   Counter/bytes  Drop/pkts   Drop/bytes
  -------------------------------------------------------------------
  UC0  0              0              0           0

  sonic# show queue watermark unicast interface Ethernet 0
  Egress queue watermark per unicast queue:
  -----------------------------------------------
  UC0  UC1  UC2  UC3  UC4  UC5  UC6  UC7
  -----------------------------------------------
  0    0    0    0    0    0    0    0

  sonic# show queue watermark multicast  interface Ethernet 0
  Egress queue watermark per multicast queue:
  -----------------------------------------------
  MC8  MC9  MC10 MC11 MC12 MC13 MC14 MC15
  -----------------------------------------------
  0    0    0    0    0    0    0    0

  sonic# show priority-group watermark headroom/shared interface Ethernet 0
  Ingress headroom watermark per PG:
  -------------------------------------------------------------------
  PG0  PG1  PG2  PG3  PG4  PG5  PG6  PG7
  -------------------------------------------------------------------
  0    0    0    0    0    0    0    0

   > show queue buffer-threshold-breaches
   Sample Output:
        >show queue buffer-threshold-breaches
        Interface | Queue | breach-value | watermark-bytes | time-stamp
        Ethernet0 | UC3  | 82           | 8100            | 2019-06-14 - 11:29:33
        Ethernet1 | UC1  | 80           | 8100            | 2019-06-14 - 11:20:19
        ...

````
#### 3.2.2.3 Clear QoS statistis
````
  sonic# clear queue statistics [interface ethernet <name>] <qid>
  sonic# clear queue wred statistics [interface ethernet <name>] <qid>
  sonic# clear queue [buffer-watermark | buffer-persistent-watermark] [interface ethernet <name>] <qid>

````
#### 3.2.2.4 Debug Commands
N/A

#### 3.2.2.5 IS-CLI Compliance
N/A

### 3.2.3 REST API Support

The "PATCH" operation is available to the YANG model attributes except those */state/*.

The "GET" operation is available to the YANG model attributes with */state/*.  

The "DELETE" operation is available to the key(s) of a list in the YANG model.  

- WRED profile

   ````
   +--rw oc-qos-ext:wred-profiles
       |  +--rw oc-qos-ext:wred-profile* [name]
       |     +--rw oc-qos-ext:name      -> ../config/name
       |     +--rw oc-qos-ext:config
       |     |  +--rw oc-qos-ext:name?                  string
       |     |  +--rw oc-qos-ext:green_min_threshold?   uint64
       |     |  +--rw oc-qos-ext:green_max_threshold?   uint64
       |     |  +--rw oc-qos-ext:ecn?                   enumeration
       |     |  +--rw oc-qos-ext:wred_green_enable?     boolean
       |     |  +--rw oc-qos-ext:green_drop_rate?       uint64
       |     +--ro oc-qos-ext:state
       |        +--ro oc-qos-ext:name?                  string
       |        +--ro oc-qos-ext:green_min_threshold?   uint64
       |        +--ro oc-qos-ext:green_max_threshold?   uint64
       |        +--ro oc-qos-ext:ecn?                   enumeration
       |        +--ro oc-qos-ext:wred_green_enable?     boolean
       |        +--ro oc-qos-ext:green_drop_rate?       uint64
````
- Scheduler Policy
   Scheduler Policy configuration uses the following Open Config YANG:

````
   openconfig-qos-elements.yang::qos-scheduler-policy-config

````
   A summary of the supported attributes or new attributes added to the tree:  

````
     /scheduler-policy/name   
     /scheduler-policy/name/config/scheduler/sequence  
     /scheduler-policy/name/config/scheduler/sequence/config/priority  
     /scheduler-policy/name/config/scheduler/sequence/config/weight (New!)  
     /scheduler-policy/name/config/scheduler/sequence/cir  
     /scheduler-policy/name/config/scheduler/sequence/pir  
     /scheduler-policy/name/config/scheduler/sequence/bc  
     /scheduler-policy/name/config/scheduler/sequence/be  
     /scheduler-policy/name/state/*  

````

- DSCP to TC map  

````
+--rw oc-qos-maps-ext:dscp-maps
    |  +--rw oc-qos-maps-ext:dscp-map* [name]
    |     +--rw oc-qos-maps-ext:name                -> ../config/name
    |     +--rw oc-qos-maps-ext:config
    |     |  +--rw oc-qos-maps-ext:name?   string
    |     +--ro oc-qos-maps-ext:state
    |     |  +--ro oc-qos-maps-ext:name?   string
    |     +--rw oc-qos-maps-ext:dscp-map-entries
    |        +--rw oc-qos-maps-ext:dscp-map-entry* [dscp]
    |           +--rw oc-qos-maps-ext:dscp      -> ../config/dscp
    |           +--rw oc-qos-maps-ext:config
    |           |  +--rw oc-qos-maps-ext:dscp?        uint8
    |           |  +--rw oc-qos-maps-ext:fwd_group    -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
    |           +--ro oc-qos-maps-ext:state
    |              +--ro oc-qos-maps-ext:dscp?        uint8
    |              +--ro oc-qos-maps-ext:fwd_group    -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/nam
````

- DOT1P to TC map  

````
+--rw oc-qos-maps-ext:dot1p-maps
    |  +--rw oc-qos-maps-ext:dot1p-map* [name]
    |     +--rw oc-qos-maps-ext:name                 -> ../config/name
    |     +--rw oc-qos-maps-ext:config
    |     |  +--rw oc-qos-maps-ext:name?   string
    |     +--ro oc-qos-maps-ext:state
    |     |  +--ro oc-qos-maps-ext:name?   string
    |     +--rw oc-qos-maps-ext:dot1p-map-entries
    |        +--rw oc-qos-maps-ext:dot1p-map-entry* [dot1p]
    |           +--rw oc-qos-maps-ext:dot1p     -> ../config/dot1p
    |           +--rw oc-qos-maps-ext:config
    |           |  +--rw oc-qos-maps-ext:dot1p?       uint8
    |           |  +--rw oc-qos-maps-ext:fwd_group    -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
    |           +--ro oc-qos-maps-ext:state
    |              +--ro oc-qos-maps-ext:dot1p?       uint8
    |              +--ro oc-qos-maps-ext:fwd_group    -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name

````

- Traffic class to queue map  

````
+--rw oc-qos-maps-ext:forwarding-group-queue-maps
    |  +--rw oc-qos-maps-ext:forwarding-group-queue-map* [name]
    |     +--rw oc-qos-maps-ext:name                                  -> ../config/name
    |     +--rw oc-qos-maps-ext:config
    |     |  +--rw oc-qos-maps-ext:name?   string
    |     +--ro oc-qos-maps-ext:state
    |     |  +--ro oc-qos-maps-ext:name?   string
    |     +--rw oc-qos-maps-ext:forwarding-group-queue-map-entries
    |        +--rw oc-qos-maps-ext:forwarding-group-queue-map-entry* [fwd_group]
    |           +--rw oc-qos-maps-ext:fwd_group    -> ../config/fwd_group
    |           +--rw oc-qos-maps-ext:config
    |           |  +--rw oc-qos-maps-ext:fwd_group?            -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
    |           |  +--rw oc-qos-maps-ext:output-queue-index    uint8
    |           +--ro oc-qos-maps-ext:state
    |              +--ro oc-qos-maps-ext:fwd_group?            -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
    |              +--ro oc-qos-maps-ext:output-queue-index    uint8

````

- Traffic class to priority group map  

````
+--rw oc-qos-maps-ext:forwarding-group-priority-group-maps
     |  +--rw oc-qos-maps-ext:forwarding-group-priority-group-map* [name]
     |     +--rw oc-qos-maps-ext:name                                           -> ../config/name
     |     +--rw oc-qos-maps-ext:config
     |     |  +--rw oc-qos-maps-ext:name?   string
     |     +--ro oc-qos-maps-ext:state
     |     |  +--ro oc-qos-maps-ext:name?   string
     |     +--rw oc-qos-maps-ext:forwarding-group-priority-group-map-entries
     |        +--rw oc-qos-maps-ext:forwarding-group-priority-group-map-entry* [fwd_group]
     |           +--rw oc-qos-maps-ext:fwd_group    -> ../config/fwd_group
     |           +--rw oc-qos-maps-ext:config
     |           |  +--rw oc-qos-maps-ext:fwd_group?              -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
     |           |  +--rw oc-qos-maps-ext:priority-group-index    uint8
     |           +--ro oc-qos-maps-ext:state
     |              +--ro oc-qos-maps-ext:fwd_group?              -> ../../../../../../oc-qos:forwarding-groups/forwarding-group/config/name
     |              +--ro oc-qos-maps-ext:priority-group-index    uint8
````

- PFC priority to queue map  

````
+--rw oc-qos-maps-ext:pfc-priority-queue-maps
       +--rw oc-qos-maps-ext:pfc-priority-queue-map* [name]
          +--rw oc-qos-maps-ext:name                              -> ../config/name
          +--rw oc-qos-maps-ext:config
          |  +--rw oc-qos-maps-ext:name?   string
          +--ro oc-qos-maps-ext:state
          |  +--ro oc-qos-maps-ext:name?   string
          +--rw oc-qos-maps-ext:pfc-priority-queue-map-entries
             +--rw oc-qos-maps-ext:pfc-priority-queue-map-entry* [dot1p]
                +--rw oc-qos-maps-ext:dot1p     -> ../config/dot1p
                +--rw oc-qos-maps-ext:config
                |  +--rw oc-qos-maps-ext:dot1p?                uint8
                |  +--rw oc-qos-maps-ext:output-queue-index    uint8
                +--ro oc-qos-maps-ext:state
                   +--ro oc-qos-maps-ext:dot1p?                uint8
                   +--ro oc-qos-maps-ext:output-queue-index    uint8
````

- Interface QoS

   The following two YANG containers are used to model interface QoS configuration:
       openconfig-qos-interfaces.yang:: qos-interfaces-config
       openconfig-qos-elements.yang:: qos-queue-config  

   A summary of the supported attributes or new attributes added to the tree:
````
   /qos-interfaces/interface/interface-id
   /oc-qos:qos/oc-qos:interfaces/oc-qos:interface/interface-maps/config/dscp-to-forwarding-group
   /oc-qos:qos/oc-qos:interfaces/oc-qos:interface/interface-maps/config/dot1p-to-forwarding-group
   /oc-qos:qos/oc-qos:interfaces/oc-qos:interface/interface-maps/config/forwarding-group-to-queue
   /oc-qos:qos/oc-qos:interfaces/oc-qos:interface/interface-maps/config/pfc-priority-to-queue
   /oc-qos:qos/oc-qos:interfaces/oc-qos:interface/interface-maps/config/forwarding-group-to-priority-group

   /qos-interfaces/interface/interface-id/output/scheduler-policy/name    

   /qos-queue/queues/queue/name = intf-name:q
   /qos-queue/queues/queue/name/config/queue-type
   /qos-queue/queues/queue/name/config/wred-profile (New!)  

   /qos-interfaces/interface/interface-id/input/state/*
   /qos-interfaces/interface/interface-id/output/state/*
   /qos-queue/queues/queues/name/state/*  
````

- QoS Statistics  

  The following Open Config YANG container will be used and augmented to support QoS Statistics

  openconfig-qos-interfaces.yang:: qos-interfaces/interface/interface-id/output/queues/queue/state  



# 4 Flow Diagrams
N/A

# 5 Error Handling
N/A

# 6 Serviceability and Debug
N/A

# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
- Create WRED profile, verify it with Show command
- Delete WRED profile that is not used by any queue
- Delete WRED profile while it is being used by some queue. Should reject the operation.
- Create Scheduler Policy, verify it with Show command
- Delete Scheduler Policy that is not used by any queue
- Delete Scheduler Policy while it is being used by some queue. Should reject the operation
- Create DSCP-to-TC-map, verify it with Show command
- Delete DSCP-to-TC-map that is not used by any interface
- Delete DSCP-to-TC-map while it is being used by some interface. Should reject the operation
- Configure DSCP-to-TC-map on an interface; check it with Show command
- Create TC-to-Queue-map, verify it with Show command
- Delete TC-to-Queue-map that is not used by any interface
- Delete TC-to-Queue-map while it is being used by some interface. Should reject the operation
- Configure TC-to-Queue-map on an interface; check it with Show command
- Configure WRED profile on an interface queue; check it with Show command
- Configure Scheduler Policy on an interface; check it with Show command.
- Update DSCP-to-TC-map content; check the map with Show command
- Update WRED-profile content; check interface queue is updated with new WRED parameters
- Update Scheduler-policy content; check interface is updated with new scheduler policy settings.
- Read QoS Queue statistics
- Clear QoS Queue statistics


# 10 Internal Design Information

For Scheduler Policy created via Open Config YANG model, each Scheduler within a Scheduler Policy is transformed into a Scheduler Profile defined by SONiC DB.  

The Scheduler Profile is identified as "Policy_name + q#"". Such naming convention makes it possible to associate each interface queue with a unique Scheduler Profile later on.  

When a scheduler Policy is configured on an interface in Open Config YANG model, backend creates SONiC interface.q# in SONiC QueueDB if such entity has not yet been created. Backup also looks up the scheduler Profiles within the Scheduler Policy and attaches the Scheduler Profiles to the corresponding interface queues.  

When WRED profile is configured on an interface queue in Open Config YANG model, backend writes the information into SONiC Queue DB.  

When queue state query comes from Open Config YANG, a valid queue name can be in the form of "Q#", "UC-Q#" or "MC-Q#". "Q#" will include both Unicast and Multicast queue statistics, while "UC-Q#" and "MC-Q#" will be specific to either Unicast or Multicast queue.
