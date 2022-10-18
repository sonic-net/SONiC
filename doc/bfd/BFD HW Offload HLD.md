# BFD HW Offload
## High Level Design Document
### Rev 1.0

# Table of Contents

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
    * [1.2 CLI requirements](#12-cli-requirements)
    * [1.3 Scalability and Default Values](#13-scalability-and-default-values)
    * [1.4 Warm Restart requirements ](#14-warm-restart-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
    * [2.2 App DB](#22-app-db)
    * [2.3 BFD State transition](#23-bfd-state-transition)
    * [2.4 Orchestration Agent](#24-orchestration-agent)
    * [2.5 Control plane BFD](#25-control-plane-bfd)
    * [2.6 CLI](#26-cli)

###### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1|  09/29/2021  |     Prince Sunny   | Initial version                   |
| 1.0 | 10/07/2021  |     Prince Sunny   | Revised to add Flow Diagram  |

# About this Manual
This document provides general information about the BFD HW offload support. Control plane BFD support and configurations via CLI/Config_db are beyond the scope of this document. 

# Definitions/Abbreviation
###### Table 1: Abbreviations

|                          |                                |
|--------------------------|--------------------------------|
| BFD                      | Bidirectional Forwarding Detection       |


# 1 Requirements Overview

## 1.1 Functional requirements

At a high level the following should be supported:

- Create BFD sessions for HW offload
- Notifications on BFD session state

## 1.2 CLI requirements
- User should be able to show the BFD session and the corresponding status
- Config CLI and session creation via Config DB is not planned for first phase. 

## 1.3 Scalability and Default Values

As a phase #1 scalability requirement, the propsed support is to have upto **4000** BFD sessions offloaded to Hardware.

The default values for BFD configs if not specified explicitly shall be

|  Attribute               |  Value                         |
|--------------------------|--------------------------------|
| BFD_SESSION_DEFAULT_TX_INTERVAL | 1 Sec  |
| BFD_SESSION_DEFAULT_RX_INTERVAL | 1 Sec |
| BFD_SESSION_DEFAULT_DETECT_MULTIPLIER | 3 |
| BFD_SESSION_DEFAULT_MULTIHOP | False |
| BFD_SESSION_DEFAULT_LOCAL_ADDR | Loopback0 |

## 1.4 Warm Restart requirements
No special handling for Warm restart support.

# 2 Modules Design

The following are the schema changes. 

## 2.1 Config DB

TBD - Note: BFD session via Config_DB is not considered for first phase. A BFD manager is expected to be introduced when we support Config DB session configurations.

## 2.2 APP DB

```
BFD_SESSION:{{vrf}}:{{ifname}}:{{ipaddr}}
    "tx_interval": {{interval}} (OPTIONAL) 
    "rx_interval": {{interval}} (OPTIONAL)  
    "multiplier": {{detection multiplier}} (OPTIONAL) 
    "shutdown": {{false}} 
    "multihop": {{false}} 
    "local_addr": {{ipv4/v6}}
    "type": {{string}} (active/passive..) 
; Defines APP DB schema to initiate BFD session.

'vrf' is mandatory key and if not intended, provide name as 'default'
'ifname' is mandatory key and if not intended by user (e.g: multihop session), provide the name as 'default'
'ipaddr' is mandatory key and user must provide the specific ipaddr value (IPv4 or IPv6)

```

## 2.3 BFD state transition

An example state transition diagram is as below

![](https://github.com/sonic-net/SONiC/blob/master/images/bfd/BFD_States.png)


## 2.4 Orchestration Agent
Following orchagents shall be introduced/modified. 

### BfdOrch
Sonic shall offload the BFD session handling to hardware that has BFD capabilities.  A new module, BfdOrch shall be introduced to handle BFD session to monitoring endpoints and check the health of remote endpoints. BfdOrch shall offload the session initiation/sustenance to hardware via SAI APIs and gets the notifications of session state from SAI. The session state shall be updated in STATE_DB and to any other observer orchestration agents.  

![](https://github.com/sonic-net/SONiC/blob/master/images/bfd/BFD_FlowDiagram.png)


#### SAI Attributes

For offloading, the following shall be the SAI attributes programmed by BfdOrch.  

|  Attribute Type          |  Value                         |
|--------------------------|--------------------------------|
| SAI_BFD_SESSION_ATTR_TYPE | SAI_BFD_SESSION_TYPE_ASYNC_ACTIVE  |
| SAI_BFD_SESSION_ATTR_OFFLOAD_TYPE | SAI_BFD_SESSION_OFFLOAD_TYPE_FULL |
| SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE | SAI_BFD_ENCAPSULATION_TYPE_NONE |
| SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS | Loopback0 IPv4 or v6 address |
| SAI_BFD_SESSION_ATTR_DST_IP_ADDRESS | Remote IPv4 or v6 address |
| SAI_BFD_SESSION_ATTR_MULTIHOP | True |

Sai shall notify via notification channel on the session state as one of ```sai_bfd_session_state_t```. BfdOrch shall listen to these notifications and update the StateDB for the session state.

In the multihop session, for bfd packet forwarding, this design expects that the HW shall lookup the destination IP in the underlay routing table associated to VIRTUAL_ROUTER as specified in SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER. This shall be the default virtual router (SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID), if not specified. H/W implementation is also expected to handle the underlay ECMP path resolution. Extended details of ASIC/HW lookup are beyond the scope of this document. 

The flow of BfdOrch is presented in the following figure. BfdOrch subscribes to the BFD_SESSION_TABLE of APPL_DB and send the corresponding request to program the BFD sessions to syncd accordingly. The BfdOrch also creates the STATE_DB entry of the BFD session which includes the BFD parameters and an initial state. Upon receiving bfd session state change notifications from syncd, BfdOrch update the STATE_DB field to update the BFD session state. 

![](https://github.com/sonic-net/SONiC/blob/master/images/bfd/BFD_Notification.png)

## 2.5 Control plane BFD

A control plane BFD approach is to use FRR BFD and enable bfdctl module. This shall be part of the Sonic BGP container. For the initial usecases, the BFD HW offload is being considered and control plane BFD using FRR is not scoped in this document.

This design does not limit the co-existance of control plane BFD and HW offload sessions. However, it shall assume the presence of a BFD manager that determines what sessions to be offloaded based on HW capabilites and scaling limits and what sessions to be managed by control plane BFD. It is not expected to have both control plane and HW offload BFD session created for the same destination IP. With BFD trap installed to enable control plane BFD, it is possible that all BFD packets shall get trapped to CPU. Since sessions are managed independently, in such case, some packets shall be silently dropped. 

## 2.6 CLI

The following commands shall be modified/added :

```
	- show bfd session <session name>
```

Config commands for BFD session is not considered in this design. This shall be added later based on requirement. It is taken into consideration of future BFD enhancement to have the sessions created via config_db. 
