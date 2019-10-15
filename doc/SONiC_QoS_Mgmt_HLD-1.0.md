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
- Associated show commands.

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
  

- Scheduler Policy  
	openconfig-qos-elements.yang::qos-scheduler-policy-config
     

- DSCP to TC map  
    No Open Config YANG available.  
    Augment Open Config YANG model with new definitions similar to [SONIC YANG for DSCP-to-TC-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-dscp-tc-map.yang)
  

- TC to Queue map  
     No Open Config YANG available.   
     Augment Open Config YANG model with new definition similar to [SONIC YANG for TC-to-Queue-map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-tc-queue-map.yang)
  

- Interface QoS  
	openconfig-qos-interfaces.yang:: qos-interfaces-config
	openconfig-qos-elements.yang:: qos-queue-config

  

- QoS Statistics  
    openconfig-qos-interfaces.yang:: qos-interfaces/interface/interface-id/output/queues/queue/state  
    Augment Open Config YANG model with new definitions for queue statistics and watermark statistics.

     
- Threshold  
    Augment Open Config YANG model with new definitions of Queue Thresholds.



### 3.2.2 CLI

#### 3.2.2.1 Configuration Commands

- Configuring WRED
````
sonic(config)# wred <name>
sonic(conf-wred-<name>)# random-detect color [green|yellow|red] minimum-threshold 100 maximum-threshold 300
drop-probability 40
sonic(conf-wred-<name>)# random-detect ecn

    sonic(config)# no wred <name>
````

- Configure Scheduler Policy
````
  sonic(config)# scheduler-policy <name>
  sonic(conf-sched-policy)# scheduler <q#> 
  sonic(conf-sched-policy-q)# priority level <val>
  sonic(conf-sched-policy-q)# shape-bandwidth min <val> min-burst <val> max <val> max-burst <val> 
  sonic(conf-sched-policy-q)# bandwidth-percent <val>

  sonic(conf-sched-policy)# no scheduler <q#>
  sonic(config)# no scheduler-policy <name>   
````


- Config DSCP to Traffic Class map  
````
  sonic(config)# qos-map dscp-to-tc-map <name>
  sonic(conf-qos-map)# traffic-class <1..8> dscp  {<dscp-value>}

  sonic(config)# no dscp-to-tc-map <name>
````

- Config Traffic Class to Queue map
````
  sonic(config)# qos-map tc-to-queue-map <name>
  sonic(conf-qos-map)# queue 3 traffic-class 0-3
````

- Config interface QoS
````
  sonic(config)# interface <name>
  sonic(conf-if-name)# dscp-to-tc-map <name>
  sonic(conf-if-name)# tc-to-queue-map <name>
  sonic(conf-if-name)# scheduler-policy <name>
  sonic(conf-if-name)# queue <q#> wred-profile <wred-profile-name>
  sonic(conf-if-name)# queue <q#> [ucast|mcast] threshold <val> 
     
  sonic(conf-if-name)# no dscp-to-tc-map <name>
  sonic(conf-if-name)# no tc-to-queue-map <name>
  sonic(conf-if-name)# no scheduler-policy <name>
  sonic(conf-if-name)# no queue <q#> wred-profile <wred-profile-name>
  sonic(conf-if-name)# no queue <q#> [ucast|mcast] threshold 

````


#### 3.2.2.2 Show Commands

- Show WRED
````
  >show wred {<name>}
  Sample Output:
     > show wred wred_1
    Profile Name | Green            | Yellow           | Red              |       |    
                 |------------------|------------------|------------------|       |    
                 | MIN MAX DROP-RATE| MIN MAX DROP-RATE| MIN MAX DROP-RATE|  ECN  |
                 | KB  KB  %        | KB  KB  %        | KB  KB  %        |       |  
    -------------|------------------|------------------|------------------|-------|
      wred_1     | 100 1000 100     | 50 100 100       | 50 100 100       | All   |
    -------------|------------------|------------------|------------------|-------|
````


- Show Scheduler Policy  
````    
  >show scheduler-policy <name>   
  Sample output:
    Scheduler <q0>:
      Type: Priority
      Bandwidth Percent: N/A
      Priority Level: 1
      Shape Bandwidth: min 100mbps, min-burst 16kBytes, max 200mbps, max-burst 16kBytes
    Scheduler <q1>:
      Type: WRR
      Bandwidth Percent: 40
      Shape Bandwidth: min 200mbps, min-burst 16kBytes, max 1000mbps, max-burst 16kBytes
    ...
````	


- Show interface QoS configuration
````
  >show qos interface <name>  	
  Sample Output:
      Ethernet 1/1/10
      DSCP-to-Traffic-Class map: dscp-to-tc-map_1
      Traffic-Class-to-Queue map: tc-to-queue-map_1
      Scheduler policy: scheduler-policy_1
      Q1 WRED profile:  wred-profile_1
      Q5 WRED profile:  wred-profile_2
      Q1 threshold: 2500
      Q5 threshold: 2500 
````

- Show DSCP to TC map
````
  >show qos-map dscp-to-tc-map <name>   
  Sample Output:
	DSCP Priority to Traffic-Class Map : dscp-trustmap1
        Traffic-Class | DSCP Priority
        --------------|---------------
         0            |	8-15
         2            |	16-23
         1            |	0-7
````

- Show TC to Queue map
````
  >show qos-map tc-to-queue-map <name>
  Sample Output:
        Traffic-Class to Queue Map: queue-map1
        Queue | Traffic-Class
        ------|-------------------
        1     | 5
        2     | 6
        3     | 7
````

- Show QoS statistics

````
  > show queue statistics interface ethernet <name> queue {ucast|mcast} <qid>
  Sample Output:
    	> show queue statistics interface ethernet 1/1/1 queue 3
	Interface ethernet1/1/1:  
	Queue | Packets | Bytes | DroppedPackets | Dropped-Bytes
	---   | ---     | ---   | ---            | ---
	3     | 0       | 0     | 0              | 0


  > show queue wred statistics interface ethernet <name> queue <qid> (*) 
  Sample Output:
	> show queue wred statistics interface ethernet 1/1/1 
	Interface ethernet1/1/1 (All queues)
	Description Packets Bytes
	Output 0 0
	Dropped 0 0
	Green Drop 0 0
	Yellow Drop 0 0
	Red Drop 0 0
	ECN marked count 0 0
  (*) WRED statistics is not supported in SONiC. It is not supported in Buzznik release.

  > show queue buffer-watermark interface ethernet <name> queue {ucast|mcast} <qid>
  Sample Output:
        >show queue buffer-watermark interface ethernet 1/1/1 queue 3
        Egress shared pool occupancy in bytes:
        Queue | Watermark | Persistent-Watermark
        ---   | --------- | --------------------
        UC3   | 2124      | 3500
        MC3   | 1520      | 3140

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

   [SONiC YANG for WRED profile](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-wred-profile.yang) will be converted to Open Config YANG format 1-to-1 following Open Config convention.   
  

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

  [SONiC YANG for DSCP-to-TC map](https://github.com/project-arlo/sonic-mgmt-framework/blob/transformer-phase1/src/cvl/testdata/schema/sonic-dscp-tc-map.yang) will be converted to Open Config YANG format 1-to-1 following Open Config convention.  
  
  
- Interface QoS

   The following two YANG containers are used to model interface QoS configuration:
````
       openconfig-qos-interfaces.yang:: qos-interfaces-config
       openconfig-qos-elements.yang:: qos-queue-config  
````

   A summary of the supported attributes or new attributes added to the tree:
````
   /qos-interfaces/interface/interface-id
   /qos-interfaces/interface/interface-id/input/dscp-to-tc-map (New!)
   /qos-interfaces/interface/interface-id/output/scheduler-policy/name    

   /qos-queue/queues/queue/name = “intf-name + q#”
   /qos-queue/queues/queue/name/config/queue-type
   /qos-queue/queues/queue/name/config/wred-profile (New!)  

   /qos-interfaces/interface/interface-id/input/state/*
   /qos-interfaces/interface/interface-id/output/state/*
   /qos-queue/queues/queues/name/state/*  
````


- QoS Statistics  
  The following Open Config YANG container will be used and augmented to support QoS Statistics
````
   openconfig-qos-interfaces.yang:: qos-interfaces/interface/interface-id/output/queues/queue/state  
````

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

The Scheduler Profile is identified as “Policy_name + q#”. Such naming convention makes it possible to associate each interface queue with a unique Scheduler Profile later on.  

When a scheduler Policy is configured on an interface in Open Config YANG model, backend creates SONiC “interface.q#” in SONiC QueueDB if such entity has not yet been created. Backup also looks up the scheduler Profiles within the Scheduler Policy and attaches the Scheduler Profiles to the corresponding interface queues.  

When WRED profile is configured on an interface queue in Open Config YANG model, backend writes the information into SONiC Queue DB.  

When queue state query comes from Open Config YANG, a valid queue name can be in the form of "Q#", "UC-Q#" or "MC-Q#". "Q#" will include both Unicast and Multicast queue statistics, while "UC-Q#" and "MC-Q#" will be specific to either Unicast or Multicast queue.
 
