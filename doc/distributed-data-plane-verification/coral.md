# Distributed Data Plane Verification
# High Level Design Document
#### Rev 0.1

# Table of Contents
TBD in Markdown with links

# Revision

| Rev   | Date  | Author | Change Description |
| ---- | ---------- | -----------| ------------------|
| v0.1 | 02/24/2022 | Qiao Xiang, Chenyang Huang, Ridi Wen, Jiwu Shu@Xiamen University, China| Initial version |


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
on a directed acyclic graph, which can be naturally decomposed into lightweight
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
<!---![system](img/system-diagram.jpg)-->

[comment]: <> (![architecture]&#40;img/architecture.png&#41;)
![system](img/system-diagram.jpg)

Firstly, DVNet is generated based on specified verification requirement and actual network topology. Then, the counting problem is distributed to individual switches. On each switch, counting result is computed depending on received verification messages and delivered to corresponding upstream node on DVNet. Finally, the source switch would be able to determine whether there is an error on data plane according to received verification messages.

A series of demos of the proposed feature  can be found at [distributeddpvdemo.tech](distributeddpvdemo.tech). All demos are conducted on a small testbed of commodity switches installed with SONiC or ONL. 

# Requirements
* The ddpv container needs to have access to the device data plane (i.e., FIB and ACL) stored in the database container.
* The ddpv container at neighboring switches needs to use sockets to exchange verification messages.
* The ddpv container will be developed in Java, and will need a Java Runtime Environment (JRE).
* New CLI commands need to be added to allow the ddpv container to receive the counting tasks from the verification planner and show related information, e.g., verification results, counting numbers, and status.


# 2 Overview

# 2 Functionality Overview
1. Distributed data plane verification allows user to verify a wide range of requirements, e.g., reachability, isolation, loop-freeness, black hole freeness, waypoint reachability and all shortest-path availability requirement in Azure RCDC [1].
2. Distributed data plane verification is able to verify data plane in the scenario of both burst update and incremental update.


# 3 Functionality
## 3.1 Functionality Description
Distributed data plane verification detects a wide range of network errors (e.g., switch operating system errors) by checking the actual 
data plane on the network device, so that the operator can detect the network error in time, take relevant 
measures to correct the error, and reduce the loss as much as possible. Distributed data plane verification can efficiently validate a 
wide range of network forwarding requirements of operators in different scenarios. If the current network 
status does not meet the operator's network forwarding requirements, then prompt the operator network error.
Distributed data plane verification generates a directed acyclic graph called DVnet based on the network topology and requirements, 
and performs a reverse counting process on DVnet, finally determines whether the network is wrong.

## 3.2 Use Case

![system](img/tore.png)

Figure 2. An example topology and requirement.

![system](img/dataplane.png)

Figure 3. The network data plane.

![system](img/dvnet.png)

Figure 4. The DVNet and the counting process.

Figure 4 gives the computed DVNet in the example shown in figure 2. Note the devices in the network and the nodes in DVNet have a
1-to-many mapping. For each node u in DVNet, we assign a unique identifier, which is a concatenation of u.dev and an integer.
For example, device W in the network is mapped to two nodes B1 and B2 in DVNet, because the regular expression
allows packets to reach D via [B,W,D] or [W,B,D].

### 3.2.1 Green Start Use Case
Distributed data plane verification is used in the scenario of green start, i.e., all forwarding rules are
installed to corresponding switches all at once. For simplicity, we use P1, P2, P3 to represent the packet spaces with destination IP
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
### 3.2.2 Incremental Update Use Case
Consider a scenario in Figure 2, where B updates its data plane to forward P1 to W , instead of to D. The changed mappings of different 
nodes are circled with boxes in Figure 4. In this case, device B locally updates the task results of B1 and B2 to [(P1, 1)] and [(P1, 0)], 
respectively, and sends corresponding updates to the devices of their upstream neighbors, i.e., [(P1, 1)] sent to A following the opposite 
of (A1, B1) and [(P1, 0)] sent to W following the opposite of (W 1, B2).

Upon receiving the update, W does not need to update its mapping for node W1, 
because W does not forward any packet to B. As such, W does not need to send any update to A along the opposite of (A1,W1). In contrast, 
A needs to update its task result for node A1 to [(P1, 1)] because (1) no matter whether A forwards packets in P2 to B or W , 1 copy of 
each packet will be sent to D, and (2) P2 ∪ P3 = P1. After
updating its local result, A sends the update to S along the opposite of (S1,A1). Finally, S updates its local result for S1 to [(P1, 1)], 
i.e., the requirement is satisfied after the update.
### 3.2.3 Verifying RCDC Local Contracts Using Coral

![system](img/dc.png)

Figure 5: An example datacenter.

![system](img/rcdc_contracts.png)

Figure 6: Example illustrating local contracts.

We now explain what are ToR contracts. Each ToR has a default contract with next
hops set to its neighboring leaf devices. For example, the default
contract for ToR1 specifies {A1,A2,A3,A4} as the next hops.
Each ToR has a specific contract for every prefix hosted in the
datacenter besides the prefix that it is configured to announce, and
the next hops are set to its neighboring leaf devices. For example,
ToR1 has specific contracts for PrefixB, PrefixC
, and PrefixD with next hops set to {A1,A2,A3,A4}. 
Aggregation contracts and core contracts are similar to ToR contracts.

![system](img/dc_total_time.png)

(a) Total time.

![system](img/dc_memory.png)

(b) Maximal memory.


![system](img/dc_load.png)

(c) CPU load.

Figure 7: Time and overhead of verifying all-shortest-path availability in DC networks from green start on commodity network devices.

The local contract in Azure RCDC [1] that requires all pairs of ToR devices should reach each other along a shortest path, and all ToR-to-ToR 
shortest paths should be available in the data plane and verifies all the shortest path availability requirements is a special case of the 
counting task in distributed data plane verification. It is assumed that the current data center is shown in figure 5, we use three 
different switches acting as three devices (one edge like ToR1, one aggregation like A1 and one core like D1) whose tasks are to verify their 
local contracts which are similar to what shown in figure 6. 
Actually, we selected the three devices described above in the 48-ary Fattree and the NGClos datasets, respectively, and verify their local contracts on three commodity
switches. Figure 7 shows that all local contracts are verified on commodity switches in less than 320ms, with a CPU load ≤ 0.47 
and a maximal memory ≤ 15.2MB.
The power consumption of all three switches deployed with distributed data plane verification is very low, so it is feasible 
to allow distributed data plane verification planners on the device to verify these local contracts on commodity network devices.

[comment]: <> (# 4 Design)

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
