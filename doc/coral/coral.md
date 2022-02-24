# Coral in SONiC
# High Level Design Document
#### Rev 0.1

# Table of Contents
todo

# Revision

| Rev   | Date  | Author | Change Description |
| :---: | :---: | :----- | :----------------- |
|       |       |        |                    |

# About this Manual
This document describes the design details of Coral feature.

TODO

# Scope
This document describes the high level design details about how Coral works.

# Definitions/Abbreviations
###### Table 1: Abbreviations
| Abbreviation |          Full form          |
| ------------ | --------------------------- |
| NAT          | Network Address Translation |
| ACL          | Access Control List         |
| FIB          | Forwarding Information Base |
| CLI          | Command Line Interface      |
| LEC          | Local Equivalence Class     |
| DPV          | Data plane verification     |

# 1 Motivation

Network errors such as forwarding loops, undesired blackholes and waypoint violations are the outcome of various
issues (e.g., software bugs, faulty hardware, protocol misconfigurations, and oversight negligence). They can happen in
all types of networks (e.g., enterprise networks, wide area networks and data center networks), and have both disastrous
financial and social consequences. Data plane verification (DPV) is important for finding such network errors. 
Current DPV tools employ a centralized architecture, where a server collects the data planes of all devices and verifies them. 
Despite substantial efforts on accelerating DPV, this centralized architecture is inherently unscalable. 

In order to tackle the scalability challenge of DPV, Coral is designed, a generic, distributed,
on-device DPV framework, which circumvents the scalability bottleneck of centralized design. The key insight is as follows. A
directed acyclic graph (DAG), which represents all valid paths in
the network, is called DVNet. The problem of DPV can be transformed into a counting problem in DVNet; the latter can then be decomposed into small tasks at nodes on the DVNet, which can be distributively executed at corresponding network devices, enabling scalability.

The picture below demonstrates the architechture and workflow of Coral.
<center>
<img src="./img/architecture.png" width="60%" /><br/>
Figure 1. The architecture and workflow of Coral.
</center><br/>

Firstly, DVNet is generated based on specified verification requirement and actual network topology. Then, the counting problem is distributed to individual switches. On each switch, counting result is computed depending on received verification messages and delivered to corresponding upstream node on DVNet. Finally, the source switch would be able to determine whether there is an error on data plane according to received verification messages.


# 2 Overview

## 2.1 Functionality Overview
1. Coral feature allows user to verify a wide range of requirements, e.g., reachability, isolation, loop-freeness, black hole freeness and waypoint reachability.
2. Coral is able to verify data plane in the scenario of both burst update and incremental update.
3. Coral is also able to verify RCDC local contracts.
## 2.2 Requirements Overview
1. In order to compute Local Equivalence Class (LEC) table, Coral needs to have access to FIB stored in kernel.
2. An agent is needed to deliver verification messages containing counting result to upstream switch.
3. New CLI commands need to be added to specify data plane verification requirements and show related information, e.g., verification results, counting numbers, and status.

# 3 Functionality

# 4 Design

![system](img/system-diagram.jpg)

```text
; Defines schema for node's config

key                      = NODE_TABLE:node_index
predecessor              = string                 ; List of predecessor 
successor                = string                 ; List of successor
accepted                 = boolean
```
