# Distributed Data Plane Verification
# High Level Design Document
#### Rev 0.1

# Table of Contents
TBD in Markdown with links

# Revision

| Rev   | Date  | Author | Change Description |
| ---- | ---------- | -----------| ------------------|
| v0.1 | 02/24/2022 | Qiao Xiang, Chenyang Huang, Ridi Wen, Yuxin Wang, Jiwu Shu@Xiamen University, China| Initial version |


# Scope
This document describes the high-level design of the distributed data plane verification feature.




# Definitions/Abbreviations
###### Table 1: Abbreviations
| Abbreviation |          Full form          |
| ------------ | --------------------------- |
| FIB          | Forwarding Information Base |
| CLI          | Command Line Interface      |
| LEC          | Local Equivalence Class     |
| DPV          | Data plane verification     |

# Overview

Network errors such as forwarding loops, undesired blackholes and waypoint violations are the outcome of various
issues (e.g., software bugs, faulty hardware, protocol misconfigurations, and oversight negligence). They can happen in
all types of networks (e.g., enterprise networks, wide area networks and data center networks), and have both disastrous
financial and social consequences. Data plane verification (DPV) is important for finding such network errors. 
Current DPV tools employ a centralized architecture, where a server collects the data planes of all devices and verifies them. 
Despite substantial efforts on accelerating DPV, this centralized architecture is inherently unscalable because (1) it requires a highly available management network, which is hard build itself; and (2) the server becomes the performance bottleneck and a single point of failure. 

In this HLD, to tackle the scalability challenge of DPV, we propose a distributed
data plane verification feature, which circumvents the scalability bottleneck
of centralized design and performs data plane checking on commodity network
devices.  Our key insight is that DPV can be transformed into a counting problem
on a directed acyclic graph called DVNet, which can be naturally decomposed into lightweight
tasks executed at network devices, enabling scalability. To be concrete, this
feature provides:

* A declarative requirement specification language that allows operators to
  flexibly specify common requirements studied by existing DPV tools (e.g.,
reachability, blackhole free, waypoint and isolation), and more advanced, yet
understudied requirements (e.g., multicast, anycast, no-redundant-delivery and
all-shortest-path availability).
* A verification planner that takes the operator specified requirement as input,
  and systematically decomposes the global verification into lightweight,
on-device computation tasks.
* A distributed verification (DV) protocol that specifies how on-device
  verifiers communicate task results efficiently to collaboratively verify the
requirements.



The picture below demonstrates the architecture and workflow of distributed data plane verification.

[comment]: <> (![architecture]&#40;img/architecture.png&#41;)
![system](img/system-diagram.jpg)


A series of demos of the proposed feature  can be found at [distributeddpvdemo.tech](DDPV-Demos). All demos are conducted on a small testbed of commodity switches installed with SONiC or ONL. 

# Requirements
* The ddpv container needs to have access to the device data plane (i.e., FIB and ACL) stored in the database container.
* The ddpv container at neighboring switches needs to use sockets to exchange verification messages.
* The ddpv container will be developed in Java, and will need a Java Runtime Environment (JRE).
* New CLI commands need to be added to allow the ddpv container to receive the counting tasks from the verification planner and show related information, e.g., verification results, counting numbers, and status.





# Functionality
## Functionality Description
Distributed data plane verification detects a wide range of network errors (e.g., switch operating system errors) by checking the actual 
data plane on the network device, so that the operator can detect the network error in time, take relevant 
measures to correct the error, and reduce the loss as much as possible. Distributed data plane verification can efficiently validate a 
wide range of network forwarding requirements of operators in different scenarios. If the current network 
status does not meet the operator's network forwarding requirements, then prompt the operator network error.
Distributed data plane verification generates a directed acyclic graph called DVnet based on the network topology and requirements, 
and performs a reverse counting process on DVnet, finally determines whether the network is wrong.

## Use Case Examples

We use two examples to demonstrates how the DDPV feature works. More
illustrations can be found at [distributeddpvdemo.tech](DDPV-Demos). The first
example is in a network in Figure 2. 

<img src="img/tore.png" width="50%"  alt="tore" />

Figure 2. An example topology and requirement.

After the operator specifies the requirement in Figure 2, the verification
planner decides the on-device tasks for each device in the network by
constructing a data structure called DVNet.  Informally, DVNet is a DAG that
compactly represents all valid paths in the topology that satisfy an
operator-specified requirement, and is independent of the actual data plane of
the network. Figure 3 gives the computed DVNet of the example in Figure 2. 

<img src="./img/dvnet.png" width="50%"  alt="dvnet" />


Figure 3. The DVNet and the counting process.


Note the devices in the network and the nodes in DVNet have a
1-to-many mapping. For each node u in DVNet, we assign a unique identifier, which is a concatenation of u.dev and an integer.
For example, device W in the network is mapped to two nodes B1 and B2 in DVNet, because the regular expression
allows packets to reach D via [B,W,D] or [W,B,D].

### Example 1-1: Green Start

<img src="./img/dataplane.png" width="30%"  alt="dataplane" />

[comment]: <> (![system]&#40;img/dataplane.png&#41;)

Figure 4. The network data plane.


We first show how DDPV works in the scenario of green start, i.e., all forwarding rules are
installed to corresponding switches all at once. Consider the network data plane
in Figure 4. For simplicity, we use P1, P2, P3 to represent the packet spaces with destination IP
prefixes of 10.0.0.0/23, 10.0.0.0/24, and 10.0.1.0/24, respectively. Note that P2 ∩ P3 = ∅ and P1 = P2 ∪ P3. Each u in DVNet
initializes a packet space → count mapping, (P1, 0), except for D1 that initializes the mapping as (P1, 1) (i.e., one copy of 
any packet in P1 will be sent to the correct external ports). Afterwards, we traverse all the nodes in DVNet in reverse topological 
order to update their mappings. Each node u checks the data plane of u.dev to find the set of next-hop devices 
u.dev will forward P1 to. If the action of forwarding to this next-hop set is of ALL-type, the mapping at u can be updated by adding up the 
count of all downstream neighbors of u whose corresponding device belongs to the set of next-hops of u.dev for forwarding P1. For example, 
node W1 updates its mapping to (P1, 1) and node W2 updates its mapping to (P1, 1) because device W forwards to D, but node B1’s mapping 
is still (P1, 0) because B does not forward P1 to W. Similarly, although W1 has two downstream neighbors B2 and D1, each with an updated 
mapping (P1, 1). At its turn, we update its mapping to (P1, 1) instead of (P1, 2), because device W only forwards P1 to D, not B.

Consider the mapping update at A1. A would forward P2 to either B or W. A forwards P2 to B, the mapping at A1 is (P2, 0), because 
B1’s updated mapping is (P1, 0) and P2 ⊂ P1.  A forwards P2 to W , the mapping at A1 is (P2, 1) because W1’s updated mapping is (P1, 1). 
Therefore, the updated mapping for P2 at A1 is (P2, [0, 1]). In the end, the updated mapping of S1 [(P2, [0, 1]), (P3, 1)] reflects the final 
counting results, indicating that the data plane in Figure 3 does not satisfy the requirements in Figure 2. In other words, the network 
data plane is erroneous.
### Example 1-2: Incremental Update
Consider another scenario in Figure 2, where B updates its data plane to forward P1 to W , instead of to D. The changed mappings of different 
nodes are circled with boxes in Figure 4. In this case, device B locally updates the task results of B1 and B2 to [(P1, 1)] and [(P1, 0)], 
respectively, and sends corresponding updates to the devices of their upstream neighbors, i.e., [(P1, 1)] sent to A following the opposite 
of (A1, B1) and [(P1, 0)] sent to W following the opposite of (W 1, B2).

Upon receiving the update, W does not need to update its mapping for node W1, 
because W does not forward any packet to B. As such, W does not need to send any update to A along the opposite of (A1,W1). In contrast, 
A needs to update its task result for node A1 to [(P1, 1)] because (1) no matter whether A forwards packets in P2 to B or W , 1 copy of 
each packet will be sent to D, and (2) P2 ∪ P3 = P1. After
updating its local result, A sends the update to S along the opposite of (S1,A1). Finally, S updates its local result for S1 to [(P1, 1)], 
i.e., the requirement is satisfied after the update.

### Example 2: Verifying RCDC Local Contracts
In the second example, we show how DDPV verifies the local contracts of the
all-shortest-path availability in Azure RCDC [1]. All-shortest-path availability
requires all pairs of ToR devices in a Clos-based data center should reach each
other along a shortest path, and all ToR-to-ToR shortest paths should be
available in the data plane.  

![system](img/dc.png)

Figure 5: An example datacenter.

We first explain what ToR contracts are using the example in Figure 5, we show that
RCDC is a special case of DDPV.. Each ToR has a default contract with next
hops set to its neighboring leaf devices. For example, the default
contract for ToR1 specifies {A1,A2,A3,A4} as the next hops.
Each ToR has a specific contract for every prefix hosted in the
datacenter besides the prefix that it is configured to announce, and
the next hops are set to its neighboring leaf devices. For example,
ToR1 has specific contracts for PrefixB, PrefixC
, and PrefixD with next hops set to {A1,A2,A3,A4}. 
Aggregation contracts and core contracts are similar to ToR contracts.


![system](img/rcdc_contracts.png)

Figure 6: Example illustrating local contracts.

We select three devices (one edge like ToR1, one aggregation like A1 and one
core like D1)  in a 48-ary Fattree and another operational Clos-based topology
called  NGClos, respectively, and verify their local contracts on three
commodity switches. Figure 7 shows that all local contracts are verified on
commodity switches in less than 320ms, with a CPU load (i.e., CPU time /(total
time * number of cores)) ≤ 0.47 and a maximal memory ≤ 15.2MB.  These results
show that it is feasible to run DDPV on commodity devices to verify local
contracts of data centers.

<img src="./img/dc_total_time.png" width="484px"  alt="dc_total_time" />

[comment]: <> (![system]&#40;img/dc_total_time.png&#41;)

(a) Total time.

<img src="./img/dc_memory.png" width="484px"  alt="dc_memory" />

[comment]: <> (![system]&#40;img/dc_memory.png&#41;)

(b) Maximal memory.

<img src="./img/dc_load.png" width="484px"  alt="dc_load" />

[comment]: <> (![system]&#40;img/dc_load.png&#41;)

(c) CPU load.

Figure 7: Time and overhead of verifying all-shortest-path availability in DC networks from green start on commodity network devices.




# Design

The ddpv container runs two daemon processes: lecbuilderd and vagentd. We give a
brief view on the key classes and their main functionalities of each process.

## lecbuilderd
The core of lecbuilderd is the LECBuilder class.

- LECBuilder

  This class is responsible for converting the data plane (e.g., FIB and ACL) of the residing device to local equivalence classes (LECs).
  Given a device X, a local equivalence class is a set of packets whose actions are identical at X.
  LECBuilder stores the LECs of its residing device using a data structure called binary decision diagram (BDD).
  The main methods in LECBuilder are: 
    
  - `buildLEC()`: read the database container to get the data plane of the device,
    and build the LECs.
  - `updateLEC()`: get the updates of data plane from the database container and update the LECs incrementally.

## vagentd
The vagentd process uses a dispatch-worker thread pool design.

### Dispatcher

The Dispatcher class receives the computation task configurations from the planner and spawns
Worker threads correspondingly. It also establishes socket connections with neighboring devices, dispatches received messages to corresponding Worker threads, and sends the messages from Worker threads to corresponding neighbor devices.

The main methods in Dispatcher include:

  - `receiveInstruction()`: receive instructions on computation tasks from the planner, and spawn corresponding Worker threads. This method is only invoked when the system starts or the planner updates the computation tasks based on operators' instructions. 
  - `receiveMessage()`: receive the verification messages from neighboring devices and dispatch them to the corresponding workers.
  - `receiveLECUpdate()`: receive the updates of LECs from lecbuilderd and dispatch them to corresponding workers.
  - `sendMessage()`: receive the sendResult requests
    from workers and send them to corresponding devices.
  - `sendAlert()`: if a worker specifies in its sendResult request that the result indicates a violation of an
operator-specified requirement, the dispatcher sends an alert to the operators. 

  
### Worker

This class executes the lightweight computation tasks specified by the planner. 
  Each node in DVNet corresponds to a worker thread. 
  The running state of Worker is controlled by the thread pool.
  The main methods in Worker include:
  - `receiveMessage()`: receive the verification message from the dispatcher, and execute the computation task incrementally.
  - `receiveLECUpdate()`: receive the updates of LECs from the dispatcher, and execute the computation task incrementally.
  - `sendResult()`: send the result of the computation task to the dispatcher, which either forwards it to a corresponding neighbor device or sends an alert to the operators, depending on whether a violation of an operator-specified requirement is found by the worker.

  

[comment]: <> (## 4.1 Overview)

[comment]: <> (![system]&#40;img/system-diagram.jpg&#41;)

[comment]: <> (## 4.2 Setup
Before the verification begins, the planner first uses the requirement and the network topology to compute DVNet.
It then transforms the DPV problem into a counting problem on DVNet.
In its turn, each node in DVNet takes as input the data plane of its corresponding device and
the counting results of its downstream nodes to compute for different packets,
how many copies of them can be delivered to the intended destinations along downstream paths in DVNet.
This traversal can be naturally decomposed to on-device counting tasks, one for each node in DVNet,
and distributed to the corresponding network devices' vagentd by the planner. )


[comment]: <> (## 4.3 Green start
Lecbuilderd collects all the data planes from the Database, calculates the LEC, and passes the LEC results to vagentd.
Vagentd uses the node information of DVNet and LEC to calculate the current count result of each node.
The leaf nodes of DVNet will generate messages and send them to the corresponding devices of the precursor nodes of each node through socket.
After receiving the message, each device carries out a new round of calculation according to the content of the message and the counting result calculated before,
then the new result generate messages and sent along the reverse direction in the DVNet.
Finally, green start is complete until each device has finished counting. )

[comment]: <> (## 4.4 Incremental update
When a device's data plane changes, Being lecbuilderd an database subscriber, it will receive the content of the changes,
and then calculate the LEC changes and send them to vagentd.
Vagentd calculates whether each node needs to update its count result,
and if any of the results change, it generates a message and sends it to the node's precursor nodes.
The process is similar to green start. Finally, update is complete until each device has finished counting.)
    

# References
[1] Karthick Jayaraman, Nikolaj Bjørner, Jitu Padhye, Amar Agrawal,
Ashish Bhargava, Paul-Andre C Bissonnette, Shane Foster, Andrew
Helwer, Mark Kasten, Ivan Lee, et al. 2019. Validating Datacenters
at Scale. In Proceedings of the ACM Special Interest Group on Data
Communication. 200–213.
