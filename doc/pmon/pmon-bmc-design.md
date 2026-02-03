# SONiC BMC Platform Management & Monitoring #

# Table of Contents

  * [Revision](#revision)
  * [Scope](#scope)
  * [Acronyms](#acronyms)
  * [1. SONiC Platform Management and Monitoring](#1-sonic-platform-management-and-monitoring)
    * [1.1 Functional Requirements](#11-functional-requirements)
    * [1.2 BMC Platform Stack](#12-bmc-platform-stack)
  * [2. Detailed Workflow](#2-detailed-workflow)
    * [2.1 BMC Boot Process](#21-bmc-boot-process)
      * [2.1.1 BMC Rack Manager Interaction](#211-bmc-rack-manager-interaction)
      * [2.1.2 Midplane Ethernet](#212-midplane-ethernet)
      * [2.1.3 BMC Host CPU Interaction](#213-bmc-host-cpu-interaction)
      * [2.1.4 BMC thermal policy](#214-bmc-thermal-policy)
    * [2.2 BMC Platform Management](#22-bmc-platform-management)
      * [2.2.1 BMC Monitoring and bmcctld](#221-bmc-monitoring-and-bmcctld)
      * [2.2.2 Thermalctld](#222-thermalctld)
      * [2.2.3 Hw watchdog](#223-hw-watchdog)
      * [2.2.4 Platform APIs](#224-platform-apis)
  * [3 Future Items](#3-future-items)
      
### Revision ###

 | Rev |     Date    |       Author                                                            | Change Description                |
 |:---:|:-----------:|:-----------------------------------------------------------------------:|-----------------------------------|
 | 1.0 |             |       SONiC BMC team                                                    | Initial version                   |

# Scope
This document provides design requirements and interactions between platform drivers and PMON for SONiC on BMC 

# Acronyms
BMC - Baseboard Management Controller
Redfish - standard REST API for managing hardware
PMON - Platform Monitor. Used in the context of Platform monitoring docker/processes.
Rack Manager - Rack controller where the switch is mounted.

## 1. SONiC BMC Platform Management and Monitoring
### 1.1. Functional Requirements
This section captures the functional requirements for platform monitoring and management in sonic BMC 
* BMC will manage the Host CPU to support operations like power up/down, get operational status.
* BMC will read board leak sensors and take appropriate actions based on policy.
* BMC will get inputs on liquid temperature, pressure, flow rate etc from Rack Manager via redfish protocol and take action based on policy
* The policy application workflow will be defined in bmcctld daemon which is introduced in sonic BMC
* Board thermal sensor thresholds can be defined per sku in platform.json
* BMC can be accessed via the external management interface and from the Host CPU via the internal midplane ethernet.
* Platform APIs are defined for HostCPU to talk to BMC and viceversa

### 1.2. BMC Platform Stack
 - 
## 2. Detailed Workflow

### 2.1 BMC Boot Process
- power on first time BMC boot sequence


#### 2.1.1 BMC Rack Manager Interaction
redfish interaction, new docker 

#### 2.1.2 Midplane Ethernet


#### 2.1.3 BMC Host CPU Interaction


#### 2.1.4 BMC thermal policy


### 2.2 BMC Platform Management


#### 2.2.1 BMC Monitoring and bmcctld


#### 2.2.2 Thermalctld


#### 2.2.3 Hw watchdog


#### 2.2.4 Platform APIs



## 3 Future Items
