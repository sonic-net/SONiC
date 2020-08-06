# Distributed Forwarding in a Virtual Output Queue (VOQ) Architecture

# High Level Design Document
#### Rev 2.0

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definitions/Abbreviation](#definitionsabbreviation)
* [1 Requirements](#1-requirements)
* [2 Design](#2-design)
* [3 Testing](#3-testing)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# List of Figures
* [Figure 1: VoQ Distributed Forwarding Architecture](#41-general-flow)

###### Revision
| Rev |     Date    |       Author       | Change Description |      
|:---:|:-----------:|:------------------:|--------------------|
| 0.1 | May-19 2020 | Kartik Chandran (Arista Networks) | Initial Version |
| 0.2 | June-22 2020 | Kartik Chandran (Arista Networks) | First set of review comments from public review |
| 1.0 | June-26 2020 | Kartik Chandran (Arista Networks) | Final set of review comments from public review |
| 2.0 | Aug-5 2020 | Kartik Chandran (Arista Networks)   | Revisions after further community review including description of global DB structure, removing sections on system ports, testing and future work to be covered in other documents |

# About this Manual

This document provides an overview of the implementation of SONiC support for distributed  packet forwarding across a set of devices that have a VOQ (Virtual Output Queue) architecture interconnected by an internal fabric.

# Scope

Support for distributed forwarding encompasses the following aspects
- Physical interfaces and VOQs
- Logical interfaces such as link aggregation groups (LAGs)
- The internal interconnection fabric  
- The packet forwarding data plane
- The control plane, both internal (within the devices in the system) and with external devices.

This document covers
 - The basic SONiC architecture enhancements to support  distributed VOQ based forwarding 
 - Representation and management of physical ports across the system.
 
The other aspects listed above are expected to be covered in separate self-contained design proposals that build on this architecture. 

The initial target for this work is a VOQ chassis system in which linecards running SONiC are interconnected over a fabric and the overall system is controlled by a supervisor module that also runs SONiC. 

However, this architecture makes no hard assumptions about operating within a chassis and can be extended to other form factors with the same VOQ architecture. 


# Definitions/Abbreviations

|      |                    |                                |
|------|--------------------|--------------------------------|
| FSI  | Forwarding SONiC Instance |  SONiC instance on a packet forwarding module like a linecard.
| SSI | Supervisor SONiC Instance |  SONiC instance on a central supervisor module that controls a cluster of forwarding instances and the interconnection fabric.
| Forwarding Device | A unit of hardware that runs SONiC and is responsible for packet forwarding |
| ASIC | Application Specific Integrated Circuit | Refers to the forwarding engine on a device that is responsible for packet forwarding. 
| NPU | Network Processing Unit | An alternate term for ASIC often used in SONiC vocabulary 


# 1 Requirements

# 1.1 Functional Requirements

## 1.1.1 Distributed Operation

Each forwarding device must run an independent SONiC instance (called the Forwarding SONiC Instance or FSI) which controls the operation of one or more ASICs on the device, including the front panel and internal fabric ports conn ected to the ASICs.

* A Forwarding device must act as a fully functional router that can run routing protocols and other networking services just like single box SONiC devices. 
* The system of forwarding devices should be managed by a single central Supervisor SONiC instance (SSI) that also manages the internal fabric that interconnects the forwarding devices.

## 1.1.2 Intra-System Control Plane

* Each FSI should be able to connect to other FSIs over the internal fabric in order to be able to run protocols like BGP within the system. 

* This connection must be fate shared with the data path so that a loss of connectivity in the internal fabric is reflected as loss of internal control plane connectivity as well.

## 1.1.3 Intra-System Management Plane

Every FSI must have a management interface over which it can reach the supervisor and the rest of the network outside the system. This network must be completely separate from the internal control plane network described above.

## 1.2 Configuration and Management Requirements

* Each SONiC instance must be independently configurable and manageable through standard SONiC management interfaces.
 
* The physical configuration of the entire system is fixed at startup. This includes
  * The Hardware SKU that is used for each forwarding device
  * The Physical port organization of the entire system

* Live replacement of forwarding devices or pluggable modules like transceivers must be supported as long as the part being replaced is an identical SKU.

# 2 Design

## 2.1 Design Assumptions

In order for the system to function correctly, some state that provides the global view of the system to all the FSIs is necessary. This state is stored in the SSI and all FSIs connect to the SSI over the internal management network to access this state.

## 2.2 SAI Support

Support for VOQ based forwarding in SONiC is dependent on the [SAI VOQ API](https://github.com/opencomputeproject/SAI/blob/master/doc/VoQ/SAI-Proposal-VoQ-Switch.md)

## 2.3 State Sharing

![](../../images/chassis/architecture.png)

All state of global interest to the entire system is stored in the SSI in a new Redis instance with a database called “Global DB”. This instance is accessible over the internal management network. FSIs connect to this instance in addition to their own local Redis instance to access and act on this global state.


##  2.3.1 Global DB Organization

The Global DB runs in a new container known as ‘docker-database-global’ as a separate Redis instance. This ensures both that the Global state is isolated from the rest of the databases in the instance and can also be conditionally started only on the SSI.

Multiple databases can be instantiated inside the Global DB analogous to the existing CONFIG_DB, STATE_DB structure in SONiC Today. However, at this time the expectation is that _all_ static configuration including globally applicable conifguration is stored in the FSI CONFIG_DB and only operational application state that needs to be shared between FSIs is stored in the Global DB instance. Accordingly, there is a single DB within the Global DB instance called "GLOBAL_APP_DB" to clearly mark the difference between this DB and the local APP_DB which is accessed by OrchAgent.

A new systemd service `config-globaldb` starts the docker-database-global container in the SSI. In the FSI, the config-globaldb service reads the contents of default_config.json and populate /etc/hosts with the IP address for the “redis_chassis.server” host.

The server name “redis_chassis.server” is used in database_config.json to describe the reachability of the redis_chassis redis instance.

**database_config.json**
```
    "redis_global":{
            "hostname" : "redis_global.server",
            "port": 6385,
            "unix_socket_path": "/var/run/redis-chassis/redis_global.sock",
            "unix_socket_perm" : 777
    }

    "GLOBAL_APP_DB" : {
           "id" : 8,
           "separator": "|",
           "instance" : "redis_global"
    }
```

The following information is present in default_config.json, which is loaded into CONFIG_DB

```
    "DEVICE_METADATA": {
        "localhost": {
            “global_db_address" : <IP Address of redis-global instance>,
            “start_global_db” : “1”,
        }
    }

```

This indicates to the SSI that the Global DB instance is to be started.

## 2.3.2 FSI CONFIG_DB Additions 

Two new attributes are added to the DEVICE_METADATA object in Config DB. These are used to convey to an FSI that a Global DB exists in the system. 
```
    "DEVICE_METADATA": {
        "localhost": {
            ….
            “global_db_address" : "10.8.1.200",
            “connect_to_global_db” : “1”,
            ….
        }
    }
```

The `connect_to_global_db` flag is distinct from the `start_global_db` flag to signal which instance owns the DB and which instance is supposted to connect to it.

### 2.3.4 DB Connectivity

The platform implementation is responsible for providing IP connectivity to the redis_global.server throughout the chassis. For example, this IP address could be in a 127.1/16 subnet so that the traffic is limited to staying within the system. The exact mechanisms for this IP connectivity is considered implementation specific and outside the scope of this document. 


## 2.4 Chip Management
There are two kinds of chips that are of interest 

### 2.4.1 Forwarding ASIC 

The ASIC (also referred to as NPU in SONiC terminology) performs all the packet reception, forwarding, queueing and transmission functions in the system. 

### 2.4.2 Fabric Chip

The internal fabric that interconnects forwarding engines is made up of multiple fabric chips that are responsible for moving packets from the source to destination forwarding engine.

ASICs are connected to fabric chips over internal links that terminate on fabric ports at each end. 

Fabric chips do not play any role in packet forwarding and do not need to be explicitly configured once initialized. All subsequent interactions with fabric chips are for monitoring only. 

All chips are managed based on the existing Multi-ASIC paradigm in SONiC, in which there is one instance of syncd (and SAI), swss and other related agents per chip. 

### 2.4.3 Switch Numbering

* Each chip in the system (ASIC and Fabric Chip) in the system is given a global ID called a Switch ID. 
* Each chip consumes C consecutive switch IDs, where C is the number of switching cores.
* Each core on a chip has a core ID between 0 and C.

Please see the SAI VoQ spec for more detailed examples.

## 2.5 SONiC Instance and ASIC Naming

### Forwarding SONiC Instance

Each FSI has a globally unique name that represents that SONiC instance. In a modular chassis, the name would conventionally be "Linecard-N", where N is the slot in which the linecard is inserted.

### ASIC Name

In addition, each ASIC has a globally unique name which would conventionally be "Linecard-N.K", where K is a slot local identifier of the ASIC.

## 2.6 Port Management 

There are four types of ports that need to be managed

### 2.6.1 Local Ports 

These are front panel interfaces that are directly attached to each FSI. They are modeled and represented in SONiC exactly as they are with existing fixed configuration devices.

### 2.6.2 System Ports

Every port on the system requires a global representation in addition to its existing local representation. This is known as a System Port (AKA sysport). Every system port is assigned an identifier that is globally unique called a system_port_id. In addition, every port is assigned a local port ID within a core called a “Core Port Id”. The scope of the Local Port Id is _within_ a core of a forwarding engine.

### 2.6.3 Inband Ports

Inband ports are required to provide control plane connectivity between  forwarding engines. They are connected to the forwarding device local CPU on one side and the internal fabric on the other. 

Every inband port is assigned a System Port ID just like front panel ports which is known to all the forwarding devices. Thus, every inband port is reachable from every forwarding engine.

### 2.6.4 Fabric Ports

The provisioning and management of Fabric ports is outside the scope of this document and will be documented as a separate proposal.


The details regarding the schemas, Orch agent logic changes and flows are described in more specific documents

# 3 Testing

Test coverage for the distributed VoQ architecture is achieved by extending the existing virtual switch based SWSS pytest infrastructure.

The distributed switching architecture is represented as multiple VS instances connected with each other and called as Virtual Chassis, where one of the instance plays the role of the SSI and the remaining instances as FSIs.  Existing SWSS pytests can be executed against any of the instances in the virtual chassis to ensure that existing SONiC functionality is not affected while operating in a distributed environment.

More detailed test cases are covered in other HLDs.

# 4 Future Work

## 4.1 Dynamic System Ports 

Dynamic system port support is required to support the following forwarding scenarios

* Addition of a new forwarding device into an existing running system
* Replacing a forwarding device with another device of a different hardware SKU (such as replacing a linecard with a new linecard of a different SKU in a chassis slot).

Both these scenarios can be supported smoothly as long as the global system port numbering scheme is maintained and the modifications to system ports can be performed without impacting the System Port IDs of the running system.

Support for dynamic system ports requires SAI support for the `create_port` and `remove_port` calls. 

## 4.2 Dual Supervisor Support

Dual supervisor modules are a common feature in chassis based systems where one supervisor acts as the active and the other as a standby. The presence of the standby supervisor allows the system
to continue functioning without manual intervention in case of a hard failure (such as a hardware failure) on the active supervisor by transferring control to the standby.

The standby supervisor has its own console, internal and external management IP address.

There are typically two forms of redundancy

### Warm Standby

In this mode, the standby supervisor has booted into the OS and is waiting to take over. No configuration or operational status is known. When a switchover occurs, the processing is very similar to what happens after a fresh boot of a supervisor. 

Warm standby can be supported in SWSS as follows

- Gracefully handle the loss of connectivity to the SSI and terminate OrchAgent, syncd and all related containers
- Process device configuration and populate standby Chassis DB with static information
- Modify the ChassisDB address in DEVICE_META
- Start all the containers which will now connect to the standby Chassis DB and continue operation.

### Hot Standby

In the hot standby mode, the standby supervisor has the control plane running in standby mode, such that it can take over with minimal (or no) disruption to forwarding device.

At a high level, hot standby mode requires

- Starting Chassis DB on standby SSI in standby mode where it mirrors the Chassis DB.
- Live sync of Chassis DB state between active and standby Chassis DB.
- Graceful handling in OrchAgent of loss of connectivity to SSI and continuing to operate autonomously.
- Reconnecting to Chassis DB when Standby SSI is ready.
- Reconciling relevant Chassis DB state with SAI Asic DB state and modifying SAI state as appropriate to be in sync with Chassis DB.
  
