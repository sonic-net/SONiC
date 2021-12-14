# IEEE 802.1Q Tunneling Support
>
>
>
## Revision History

[© xFlow Research Inc](https://xflowresearch.com/)  

|  Revision No| Description | Author  | Contributors |Date |  
| :-------------: |:-------------:| :-----:|:----------:|:-----:|
|1.0| IEEE 802.1Q Tunneling Support| [Muhammad Hamza Iqbal](https://github.com/ham-xa)| [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)| 14 Dec 2021|
  
## Table of Contents

- Scope  
- Definitions/Abbreviations  
- Overview  
- Introduction  
- Features Description  
  - Functional Features  
  - Functional Feature Description  
    - L2 VLAN Tunneling Support  
    - Integration of SONiC with other open-source Implementation  
    - Enabling VLAN pruning  
- Feature Design  
  - Sample Topology  
  - Flow Chart  
    - Flow Chart Explanation  
  - Architecture Design  
- High-level Design  
  - Part 1  
  - Part 2  
  - DB & Schema Changes  
  - Warm Reboot Requirements  
  - Fast reboot Requirements  
- SAI API  
  - Configuration and Management  
  - VLAN DOT1Q Configuration Commands  
  - VLAN DOT1Q Show Commands  
- Warm Boot and Fastboot Design Impact  
- Restrictions/Limitations  
  - Testing Requirements/Design  
    - Unit Test cases  

## Scope

This high-level design document describes the integration of VLAN tunneling encapsulation protocol IEEE 802.1Q in SONiC.  

## Definitions/Abbreviations

| **Sr No** |  **Term**   |  **Definition**                      |
| :------------- |:-------------| :-----|
|  1       |  VLAN_ID      |  Unique identifier for each VLAN     |  
|  2       |  Dot1q        |  IEEE 802.1Q Protocol                |  
|  3       |  Trunk Link   |  The link between different switches that carries the traffic from different VLANs  |  
|  4       | Encapsulation |  Addition of dot.1q tag in the normal ethernet frame.|  
|  5       |  Egress Port  |  Outbound port                       |  
|  6       |  Ingress Port |  Inbound port                        |  
|  7       |  BGP          |  Border gateway protocol             |  
|  8       |  DHCP         |  Dynamic Host Configuration Protocol |  
|  9       |  LAG          |  Link Aggregation                    |  
|  10      |  VID          |  VLAN Identifier                     |  
|  11      |  TPID         |  Tag Protocol Identifier             |  

## Overview

L2 DOT1Q (802.1Q) is an IEEE standard for tunnel encapsulation to support transport of different VLAN frames on the tunnel link. This document covers the key aspects of IEEE 802.1Q Tunneling protocol which will be implemented in the existing architecture of the SONiC. 802.1Q support is very fundamental for the forwarding of different VLANs frames on the tunnel links. It is also mentioned in the backlog of the SONiC roadmap that the addition of [L2 IEEE 802.1Q Tunneling Support](https://github.com/Azure/SONiC/wiki/Sonic-Roadmap-Planning) in SONiC is yet to be done. Thus, this HLD is prepared to provide design and implementation details of L2 Dot1Q tunneling support in SONiC.  

## Introduction

IEEE 802.1Q is a networking standard which defines the VLANs tagging on an ethernet network. The Ethernet frame contains a TAG with fields that specify VLAN membership and user priority. As seen in the below Ethernet frame, the TAG is inserted between the Source MAC address and Type/Length. The TAG is of 16-bit length. The 802.1Q tags are inserted into the frames before  transmitting out of the interface and similarly, the tags are removed from frames received from the interface. The frames are transmitted and received from the interfaces that are configured with VLAN and they are tagged with VID.  

Original Ethernet Frame  
|  Preamble |  Dest MAC |  Source MAC |  Type/Length |  Data |  CRC |

802.1Q Frame from Customer  
| Preamble |  Dest MAC |  Source MAC |  TAG |  Type/ Length |  Data |  CRC |

802.1Q Frame on Trunks between Service Provider Switches  
| Preamble |  Dest MAC |  Source MAC |  TAG |  TAG | Type/ Length |  Data |  CRC |  
IEEE 802.1 TAG:  
|  TPID (16 bit) | User Priority (PCP) (3 bits) | CFI (1 bit) |  VID (12 bits) |  

- TPID  
A 16-bit field was set to a value of 0x8100 in order to identify the frame as an IEEE 802.1Q-tagged frame. This field is located at the same position as the EtherType field in untagged frames, and is thus used to distinguish the frame from untagged frames.  

- User Priority (PCP)  
A 3-bit field which refers to the IEEE 802.1p class of service and maps to the frame priority level. Different PCP values can be used to prioritize different classes of traffic.

- CFIA  
1-bit field. May be used separately or in conjunction with PCP to indicate frames eligible to be dropped in the presence of congestion.  

- VIDA  
A 12-bit field specifying the VLAN to which the frame belongs. The values of 0 and 4095 (0x000 and 0xFFF in hexadecimal) are reserved. All other values may be used as VLAN identifiers, allowing up to 4,094 VLANs. The reserved value 0x000 indicates that the frame does not carry a VLAN ID; in this case, the 802.1Q tag specifies only a priority (in PCP and DEI fields) and is referred to as a priority tag. On bridges, VID 0x001 (the default VLAN ID) is often reserved for a network management VLAN; this is vendor-specific. The VID value 0xFFF is reserved for implementation use; it must not be configured or transmitted. 0xFFF can be used to indicate a wildcard match in management operations or filtering database entries.  

## Features Description

### Functional Features

- L2 VLAN tunneling support

- Interoperability of SONiC

- Enable VLAN pruning

### Functional Feature Description

1\. L2 VLAN Tunneling Support
SONiC currently supports VLAN and its management. Hosts within the same VLAN can communicate easily without requiring extra configuration. On the other hand, hosts from different VLANs residing on different switches can not communicate due to the unavailability of L2 tunneling on the tunnel links between switches. This HLD is designed to implement L2 tunneling support in SONiC.

2\. Integration of SONiC with other open-source Implementations
802.1Q is an IEEE standard for vlan tagging on the tunnel links. Implementation of 802.1Q on SONiC will enable it to interoperate with other network operating systems from different vendors.

3\. Enabling VLAN pruning  
In addition to L2 tunneling support, we will add a VLAN pruning feature on the tunnel links as well. VLAN pruning helps users to allow or disallow VLANs on the tunnel links as per requirement.

## Feature Design

### Sample Topology

![Topology](media/sampletopology.png)  
__*Figure 1: Sample Topology*__

 This sample topology shows the basic VLANs and the dot1q tunneling
 protocol working. The figure shows that 3 different VLANs are
 configured with 6 different hosts. Ethernet switches can forward the
 frames from the same VLANs if the host is connected to the same
 switch. On the contrary, if the hosts are in the same VLANs are
 connected via different switches then frames can only be forwarded if
 any one of the following is available:

1\. A link between switches with the same VLAN ID.  
2\. A tunnel link with 802.1Q encapsulation.

 Practically option 1 is not feasible as it requires a separate link
 between switches for each VLAN. Option 2 is accepted and more
 practical where only one link is known as tunnel link between switches
 with 802.1Q encapsulation is sufficient for carrying any possible
 number of VLANs.

## Flow Chart

![Flow Chart of the main Process](media/flowchart.png)  
__*Figure 2: Flow Chart*__

### Flow Chart Explanation
>
1\. Frame arrives at the ingress port of the switch from a Host.

2\. Look up the destination MAC address in the MAC address table of the switch.

3\. If the destination MAC is not found in the MAC address table then switch initiates MAC learning procedure e.g arp.

4\. Is the Egress port configured with the same VLAN ID as the ingress port?

5\. If yes, forward the packet to the egress port.

6\. Else check if the egress port is a trunk link?

7\. If the egress port is not a trunk link the switch will initiate the inter vlan communication process.

8\. If the Egress port is a trunk link then it will call for the encapsulation process. After the frame is encapsulated it will be forwarded on the Trunk link.

 NOTE: MAC LEARNING PROCESS, FORWARDING TO EGRESS PORT, AND INTER VLAN
 COMMUNICATION IS NOT IN THE SCOPE OF THIS HLD.

## Architecture Design

 The existing architecture of SONiC is not changed. We are only using
 the existing components and modules of SONiC as shown in the following
 diagram.

![Architecture Design](media/architecture.png)  
*Figure 3: Architecture Design*

The Redis server has 5 databases:  
 **1.** APPL_DB\
 **2.** CONFIG_DB\
 **3.** STATE_DB\
 **4.** ASIC_DB\
 **5.** COUNTERS_DB

 The databases that we will be using in this protocol are

 **1. APPL_DB**: Stores the state generated by all application
 containers \-- routes, next-hops, neighbors, etc. This is the
 south-bound entry point for all applications wishing to interact with
 other SONiC subsystems.

 **2. CONFIG_DB**:  
Stores the configuration state created by SONiC applications \-- port configurations, interfaces, VLANs, etc.

 **3. STATE_DB:**  
Stores \" key\" operational state for entities
 configured in the system. This state is used to resolve dependencies
 between different SONiC subsystems. For example, a LAG port-channel
 (defined by teamd submodule) can potentially refer to physical ports
 that may or may not be present in the system. Another example would be
 the definition of a VLAN (through vlanmgrd component), which may
 reference port-members whose presence is undetermined in the system.
In essence, this DB stores all the state that is deemed necessary to
 resolve cross-module dependencies.

 **4. ASIC_DB**:  
Stores the necessary state to drive ASIC\'s
 configuration and operation \-- state here is kept in an ASIC-friendly
 format to ease the interaction between syncd (see details further
 below) and ASIC SDKs.

 SONiC breaks its main functional components into the following docker
 containers:

 **1.** DHCP-relay\
 **2.** Pmon\
 **3.** Snmp\
 **4.** Lldp\
 **5.** BGP\
 **6.** Teamd\
 **7.** Database\
 **8.** Swss\
 **9.** Syncd

 The containers that we will be interacting with are\
 **1.** Swss\
 **2.** Syncd\
 **3.** Database

### Syncd container

 Syncd's container goal is to provide a mechanism to allow the
 synchronization of the switch\'s network state with the switch\'s
 actual hardware/ASIC. This includes the initialization, the
 configuration, and the collection of the switch\'s ASIC current status.

Following are the main logical components present in the syncd container:

- Syncd  
Process in charge of executing the synchronization logic mentioned above. Syncd links
with the ASIC SDK library provided by the hardware vendor, and injects state to the
ASICs by invoking the interfaces provided for such effect. Syncd subscribes to ASIC_DB to
receive state from SWSS actors, and at the same time registers as a publisher to push
state coming from the hardware.  
- SAI API
The Switch Abstraction Interface (SAI) defines the API to provide a vendor-independent
way of controlling forwarding elements, such as a switching ASIC, an NPU, or a software
switch in a uniform manner.  
- ASIC SDK
Hardware vendors are expected to provide an SAI-friendly implementation of the SDK
required to drive their ASICs. This implementation is typically provided in the form of a
dynamic-linked-library which hooks up to a driving process (syncd in this case)
responsible for driving its execution.  

### Swss container

 The Switch State Service (SWSS) container comprises a collection of
 tools to allow effective communication among all SONiC modules. If the
 database container excels at providing storage capabilities, Swss
 mainly focuses on offering mechanisms to foster communication and
 arbitration between all the different parties.

 Swss also hosts the processes in charge of the north-bound interaction
 with the SONiC application layer. The exception to this, as previously
 seen, is fpmsyncd, teamsyncd, and lldp_syncd processes which run
 within the context of the BGP, teamd, and lldp containers
 respectively. Regardless of the context under which these processes
 operate (inside or outside the swss container), they all have the same
 goals: provide the means to allow connectivity between SONiC
 applications and SONiC\'s centralized message infrastructure
 (Redis-engine).

- Portsyncd  
Listens to port-related Netlink events. During boot-up, portsyncd obtains physical-port
information by parsing the system's hardware-profile config files. In all these cases,12
portsyncd ends up pushing all the collected states into APPL_DB. Attributes such as port
speeds, lanes and, MTU are transferred through this channel. Portsyncd also injects the
state into STATE_DB.  
- IntfMgrd  
Reacts to state arriving from APPL_DB, CONFIG_DB, and STATE_DB to configure
interfaces in the Linux kernel. This step is only accomplished if there is no conflicting or
inconsistent state within any of the databases being monitored.  
- VlanMgrd  
Reacts to state arriving from APPL_DB, CONFIG_DB, and STATE_DB to configure
VLAN-interfaces in the Linux kernel. As in IntfMgrd's case, this step will be only
attempted if no dependent state/conditions are being unmet.

#### Database container  

 Hosts the Redis-database engine. Databases held within this engine are
 accessible to SONiC applications through a UNIX socket exposed for
 this purpose by the Redis-daemon.

#### CLI & sonic-cfggen Modules

 We will be adding a few commands to the SONiC CLI for configuration
 and management of L2 Dot1Q encapsulation. The details of the commands
 are given in the configuration and management section below. CLI and
 sonic-cfggen modules are two inter-related modules that are
 implemented outside all of the sonic containers, these modules are
 used for configuration and management of sonic.

## High-level Design

### Part 1

![Sequence 1](media/part1.png)  
__*Figure 4: Sequence Diagram Part 1*__

The sequence of messages that will flow in between the containers are:

 **1.** The configuration database will send a message to the VLAN manager for adding VLANs and VLAN tunnel configuration.

 **2.** The VLAN manager which is a part of the swss container will
 send a message to the network state database to add the VLAN table and
 also add the VLAN tunnel's configurations. After the configuration
 state is updated in the STATE_DB the configurations are updated in the
 APPL_DB as well.

 **3.** The application database will now send the message to the VLAN orchestrator which is a part of the swss container that will add the VLAN mapping to the table.

 **4.** Now the VLAN orchestrator sends two separate messages to the
 port orchestrator andthe ASIC database. These messages are:
- Message to the ASIC database to create the tunnel or create a
 tunnel termination.  
- The second message the VLAN orchestrator will
 send is to the port orchestrator which is also a part of the swss
 container is to add the tunnel to the list. This way when the frame
 arrives and looks for the port with the tunnel SONiC will already know
 about it and will forward the frame accordingly.  

**5.** Lastly, the ASIC database will give the port information back to
the port orchestrator.

### Part 2

 This is the second phase of the sequence diagram (NOTE: These two
 sequence diagrams are running in parallel)

![Sequence 2](media/part2.png)  
__*Figure 5: Sequence Diagram Part 2*__

 The sequence of messages that will flow between the databases and the
 containers are

 **1.** CLI/sonic-cfggen module will send a message to the cfg_scripts
 process in the swss container.  

 **2.** Configuration scripts that are a part of the swss container
 will send the configuration command to add the VLAN tunneling configuration in the configuration
database.

 **3.** The configuration database after keeping a copy of the
 configuration detail will send the same command to the vlanmgrd which
 is also a part of the swss container. This will update the local VLAN
 tunneling configuration.

 **4.** The vlanmgrd module will send a message in the kernel for vlan
 tunnel and device configurations. The kernel will program the VLAN devices
 which will take all the necessary information and configuration files
 from the swss container & the configuration database container.

 **5.** The kernel will then update the CLI about the status of vlan
 device creation and tunnel configurations.

### DB & Schema Changes

 Following tables from different databases will be used in our
 implementation. An addition of port mode ***access*** or ***trunk***
 in the Port_Table from APPL_DB, STATE_DB and CONFIG_DB will be
 defined.

#### Application Database

| **VLAN_Table** | **Port_Table**| **INTF_Table**     |
|:-----------:|:---------:|:-------------:|
|For VLAN to port mapping work is still in progress.|Physical Ports managed by switch chip.|Cfgmgrd manages this table. Management port, logical ports (VLAN, Loopback, LAG) declared in /etc/network/interface and /etc/sonic/configdb.json and these are loaded into the INTF_TABLE.|

#### State Database  

|Port_Table|  
|:---------------------------------------------------:|  
|Physical Ports managed by switch chip|

#### Config Database

|Port_Table|  
|:---------------------------------------------------:|  
|Physical Ports managed by switch chip|

### Warm Reboot Requirements

This phase shall not include warm reboot capabilities.

### Fast reboot Requirements

This phase shall not include warm reboot capabilities.

## SAI API

No SAI API change or addition is needed for this HLD. We will be using the existing SAI API.

### Configuration and Management

#### VLAN DOT1Q Configuration Commands

 **1.** config interface mode \<physical port\> access or trunk\
 **2.** config interface encapsulation dot1q \<physical port\>\
 **3.** config interface trunk add vlan \<all, except, comma separated list, range> <physical port\>
 **4.** config interface trunk remove vlan <all, except, comma separated list, range> <physical port\>  

#### VLAN DOT1Q Show Commands

 **1.** Show interface trunk \<all, physical port\>

## Warm Boot and Fastboot Design Impact

 The existing warm boot/fast boot feature is not affected due to this
 design.

## Restrictions/Limitations

 This HLD is restricted to the addition of L2 dot1q encapsulation
 support in SONiC. Discussion and requirements of inter vlan
 communication are beyond the scope of this HLD. Implementation details
 of the configuration and management commands are also not included in
 this HLD. This HLD doesn't include support for Dot1q encapsulation on
 the LAG interface.

## Testing Requirements/Design

### Unit Test cases

 Unit testing will be done at two levels CLI level and Functional Level

#### CLI Level Tests

- Verify CLI to set the mode of an interface to access or trunk  
- Verify CLI to enable dot1q encapsulation at trunk port  
- Verify CLI to add a vlan on a trunk  
- Verify CLI to add a range of vlan on a trunk link  
- Verify CLI to add a comma-separated list of VLANs on a trunk link  
- Verify CLI to add all VLANs to a trunk link  
- Verify CLI to add all VLANs except given comma-separated list of VLANs  
- Verify CLI to remove a vlan on a trunk
- Verify CLI to remove a range of vlan on a trunk link  
- Verify CLI to remove a comma-separated list of VLANs on a trunk link  
- Verify CLI to remove all VLANs to a trunk link  
- Verify CLI to remove all VLANs except given comma-separated list of VLANs  
- Verify CLI to show all trunk ports  
- Verify CLI to show trunking configuration of a port  

#### Functional Level Tests

- Verify change of status of port mode in CONFIG-DB and STATE_DB  
- Verify dot1q tag insertion in the ethernet frame  
- Verify intra-vlan communication between hosts on a single switch  
- Verify intra-vlan communication between hosts on two different switches  
- Repeat the above step for different VLANs  
- Verify vlan pruning by removing a few VLANs from the trunk  
- Verify interoperability of SONiC with other OS by creating a trunk between the SONiC switch and any other switch running a different OS other than SONiC

