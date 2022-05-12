# Sonic PIM-SM Support 


# High Level Design Document
#### Rev 0.6


<!-- TOC -->

- [Sonic PIM-SM Support](#sonic-pim-sm-support)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.6](#rev-06)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
    - [Table 1: Abbreviations](#table-1-abbreviations)
- [1 Feature Overview](#1-feature-overview)
  - [1.1 Requirements](#11-requirements)
    - [1.1.1 Functional Requirement](#111-functional-requirement)
    - [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
    - [1.1.3 Scalability Requirements](#113-scalability-requirements)
    - [1.1.4 Interoperability Requirements](#114-interoperability-requirements)
  - [1.2 Design Overview](#12-design-overview)
    - [1.2.1 Basic Approach](#121-basic-approach)
    - [1.2.2 Containers](#122-containers)
- [2 Functionality](#2-functionality)
  - [2.1 PIM-ASM Use Cases](#21-pim-asm-use-cases)
    - [2.1.1 PIM-ASM Shared Path Tree](#211-pim-asm-shared-path-tree)
    - [2.1.2 PIM-ASM Shortest Path Tree](#212-pim-asm-shortest-path-tree)
- [3 Design](#3-design)
  - [3.1 Overview](#31-overview)
      - [Case 1: Flow for (*,G) route update](#case-1-flow-for-g-route-update)
      - [Case 2: Flow for (S,G) route update](#case-2-flow-for-sg-route-update)
      - [Case 3: KAT for (S,G) routes](#case-3-kat-for-sg-routes)
    - [3.1.1 ipmcFpmSyncd](#311-ipmcfpmsyncd)
    - [3.1.2 ipmcorchagent changes](#312-ipmcorchagent-changes)
      - [3.1.2.1 CPU bit update](#3121-cpu-bit-update)
      - [3.1.2.2 IIF expansion in OIF List](#3122-iif-expansion-in-oif-list)
      - [3.1.2.3 IPMC Aging time](#3123-ipmc-aging-time)
    - [3.1.3 Syncd changes](#313-syncd-changes)
      - [3.1.3.1 Changes required to process IPMC entries AGE and DONTAGE data](#3131-changes-required-to-process-ipmc-entries-age-and-dontage-data)
        - [3.1.3.1.2 IPMC Entry deletion](#31312-ipmc-entry-deletion)
        - [3.1.3.1.3 SYNCD WARM restart](#31313-syncd-warm-restart)
  - [3.2 Datastructure Changes](#32-datastructure-changes)
    - [3.2.1 **SAI specific data structure and callback changes**](#321-sai-specific-data-structure-and-callback-changes)
  - [3.3 DB Changes](#33-db-changes)
    - [3.3.1 CONFIG DB](#331-config-db)
      - [3.3.1.1 PIM Global Configuration [Existing]](#3311-pim-global-configuration-existing)
      - [3.3.1.2 PIM Interface-Specific Configuration [Existing]](#3312-pim-interface-specific-configuration-existing)
      - [3.3.1.3 PIM STATIC RP Coniguration [New]](#3313-pim-static-rp-coniguration-new)
    - [3.3.2 APP DB](#332-app-db)
      - [3.3.2.1 IPMC_ROUTE_TABLE [Existing]](#3321-ipmc_route_table-existing)
      - [3.3.2.2 INTF_TABLE [Existing]](#3322-intf_table-existing)
      - [3.3.2.3 SWITCH_TABLE [Existing]](#3323-switch_table-existing)
    - [3.3.3 STATE DB](#333-state-db)
      - [3.3.3.1 IPMC_MROUTE_AGE_TABLE [New]](#3331-ipmc_mroute_age_table-new)
    - [3.3.4 ASIC DB](#334-asic-db)
      - [3.3.4.1 ASIC DB Programmable by PIM](#3341-asic-db-programmable-by-pim)
        - [3.3.4.1.1 SAI_OBJECT_TYPE_IPMC_ENTRY [Existing]](#33411-sai_object_type_ipmc_entry-existing)
        - [3.3.4.1.2 SAI_OBJECT_TYPE_IPMC_GROUP  [Existing]](#33412-sai_object_type_ipmc_group--existing)
        - [3.3.4.1.3 SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER (Snooping Enabled Member) [Existing]](#33413-sai_object_type_ipmc_group_member-snooping-enabled-member-existing)
        - [3.3.4.1.4 SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER (Snooping Disabled Member) [Existing]](#33414-sai_object_type_ipmc_group_member-snooping-disabled-member-existing)
        - [3.3.4.1.5 SAI_OBJECT_TYPE_RPF_GROUP [Existing]](#33415-sai_object_type_rpf_group-existing)
        - [3.3.4.1.6 SAI_OBJECT_TYPE_RPF_GROUP_MEMBER [Existing]](#33416-sai_object_type_rpf_group_member-existing)
      - [3.3.4.2 ASIC DB Supporting snooping entries](#3342-asic-db-supporting-snooping-entries)
        - [3.3.4.2.1 SAI_OBJECT_TYPE_L2MC_GROUP [Existing]](#33421-sai_object_type_l2mc_group-existing)
        - [3.3.4.2.2 SAI_OBJECT_TYPE_L2MC_GROUP_MEMBER  [Existing]](#33422-sai_object_type_l2mc_group_member--existing)
      - [3.3.4.3 ASIC DB Supporting entries [Existing]](#3343-asic-db-supporting-entries-existing)
        - [3.3.4.3.1 SAI_OBJECT_TYPE_ROUTER_INTERFACE [Existing]](#33431-sai_object_type_router_interface-existing)
        - [3.3.4.3.2 SAI_OBJECT_TYPE_VLAN [Existing]](#33432-sai_object_type_vlan-existing)
        - [3.3.4.3.3 SAI_OBJECT_TYPE_BRIDGE_PORT [Existing]](#33433-sai_object_type_bridge_port-existing)
    - [3.3.5 COUNTER DB](#335-counter-db)
  - [3.4 Kernel Iptables](#34-kernel-iptables)
  - [3.5 User Interface](#35-user-interface)
    - [3.5.1 Data Models](#351-data-models)
    - [3.5.2 CLI](#352-cli)
      - [3.5.2.1 Global Configuration Commands](#3521-global-configuration-commands)
        - [3.5.2.1.1 ip pim rp-address](#35211-ip-pim-rp-address)
        - [3.5.2.1.2 ip pim spt-threshold infinity](#35212-ip-pim-spt-threshold-infinity)
      - [3.5.2.2 Show Commands](#3522-show-commands)
        - [3.5.2.2.1 show ip pim rp mapping and show ip pim rp <grp-addr>](#35221-show-ip-pim-rp-mapping-and-show-ip-pim-rp-grp-addr)
        - [3.5.2.2.2 show ip pim assert](#35222-show-ip-pim-assert)
      - [3.5.2.3 Show running-config Commands](#3523-show-running-config-commands)
        - [3.5.2.3.1 show running-configuration igmp](#35231-show-running-configuration-igmp)
        - [3.5.2.3.2 show running-configuration pim](#35232-show-running-configuration-pim)
      - [3.5.2.4 Debug Commands](#3524-debug-commands)
      - [3.5.2.5 IS-CLI Compliance](#3525-is-cli-compliance)
    - [3.5.3 REST API Support](#353-rest-api-support)
    - [3.5.4 gNMI Support](#354-gnmi-support)
- [4 Flow Diagrams](#4-flow-diagrams)
  - [4.1 PIM Config Flow](#41-pim-config-flow)
  - [4.2 PIM Data packet Flow](#42-pim-data-packet-flow)
  - [4.3 PIM KAT system wide Flow](#43-pim-kat-system-wide-flow)
  - [4.4 Process restart](#44-process-restart)
- [5  Design Constraints and Risks](#5--design-constraints-and-risks)
- [6 Error Handling](#6-error-handling)
- [7 Serviceability and Debug](#7-serviceability-and-debug)
- [8 Warm Boot Support](#8-warm-boot-support)
- [9 Scalability](#9-scalability)
          - [Table 3: IP Multicast Scaling limits](#table-3-ip-multicast-scaling-limits)
- [10 Unit Test](#10-unit-test)
- [11  Design expections from Broadcom](#11--design-expections-from-broadcom)
  - [11.1 ACL and COPP requirements](#111-acl-and-copp-requirements)
  - [11.2  IPMC entry deletion event](#112--ipmc-entry-deletion-event)

<!-- /TOC -->


# Revision
| Rev |     Date    |       Author                  | Change Description                |
|-----|-------------|-------------------------------|-----------------------------------|
| 0.1 | 09/27/2021  |   Vidya Chidambaram           | Initial version                   |
| 0.2 | 12/12/2021  | Panjarathina Saranya | Updated Flow diagrams | 
| 0.3 | 24/12/2021 | Gokulnath R | Orchagent changes | 
| 0.4 | 04/01/2022 | Vidya Chidambaram | IpmcFpmSyncd Changes|
| 0.5 | 17/01/2022 | Karuppiah Dharmaraj | Iptable rule Changes|
| 0.6 | 02/03/2022 | Ravisekhar Akkineni | Addressed "ip pim spt-threshold infinity" command specific review comments" |

# About this Manual
This document provides the design information on PIM Any Source Multicast using Sparse mode.


# Scope
This document describes the high level design of PIM Any Source Multicast in SONiC by leveraging FRR. This document covers details about the design changes in FRR, ipmcfpmsyncd,orchagent and also the configuration commands added in Mgmt-framework and their corresponding openconfig and Sonic yang model to support the mentioned functionality.


# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**  | ***Meaning***                                                     |
|-----------|-------------------------------------------------------------------|
| (*,G)     | (Any Source, Group Address)                                       |
| AFI       | Address Family                                                    |
| FRR       | Free Range Routing                                                |
| FHR       | First Hop Router (Router directly connected to the Source/Sender  |
| IIF       | Incoming interface                                                |
| IGMP      | Internet Group Management Protocol                                |
| LHR       | Last Hop Router (Router directly connected to the Host/Receiver   |
| MLD       | Multicast Listener Discovery Protocol                                      |
| RP        | Rendezvous Point                                                  |
| SPT       | Shortest Path Tree                                                |
| RPF       | Reverse Path Forwarding                                           | 
| (S,G)     | (Source address, Group address)                                   |
| NPU       | Network processor (NPU) is analogous to central processing unit in a computer or similar device       |
| OIF/OIL   | Outgoing Interface List                                           |
| PIM-SM    | PIM - Sparse Mode                                                 |
| PIM-ASM   | PIM - Any Source Multicast                                        |
| VRF       | Virtual Router Forwarding                                         |


# 1 Feature Overview

PIM Any Source Multicast(ASM) control plane support is already available in Sonic FRR. But, the interaction of FRR with the other modules for programming (*,G) routes in Hardware, lifting unknown multicast and known multicast routes are not available. These changes are defined in this document. It also covers the configuration support for PIM-ASM through SONIC-CLI.


## 1.1 Requirements
### 1.1.1 Functional Requirement
1. Support trapping of unknown ipv4 multicast data to CPU through a dedicated CoPP queue.
2. Support trapping of known ipv4 multicast data to CPU through a dedicated CoPP queue.
3. Support programming of (*,G) routes into hardware using SAI APIS.
4. Support programming of register interface as CPU port in (*,G) and (S,G) multicast routes
5. Support IPv4 multicast forwarding on Port based, VLAN based and LAG based routing interfaces. It is also supported on the sub-interfaces as well.
6. Provide support for VRF in PIM ASM.
7. Support the liveliness tracking of (S,G) route through HW timers and programming the HW timer value using SAI APIS.
8. Support to stop multicast data forwarding in Kernel to avoid duplication of traffic.
9. Support for static configuration of RP 

### 1.1.2 Configuration and Management Requirements
1. Support to configure and display PIM-SM (IPv4) informations using KLISH CLI commands.
2. Support to configure and GET PIM-SM informations using REST and gNMI.
3. Support for GNMI subscriber
4. Support save and reload of PIM-SM configurations.
5. Support to display PIM SM details in "show running-config" and also add "show running-config pim"

### 1.1.3 Scalability Requirements
The following are the scalability requirements for this feature:
1. Maximum number of PIM neighbors supported is 64.[ User can enable 64 pim interfaces in a single VRF (or) can split across 64 vrfs]   
2. Maximum number of multicast route entries supported is 8K, this is inclusive of snooping and pim routes.

### 1.1.4 Interoperability Requirements
There is no explicit requirement for interoperability. 

## 1.2 Design Overview
### 1.2.1 Basic Approach
 
* PIM SSM functionality is already available in SONiC using FRR stack. The same has been extended to provide the PIM ASM functionality. PIM  daemon updates the learned (*,G) and (S,G) multicast routes to Kernel. Ipmcfpmsyncd listens to these route updates from kernel and updates the APP-DB.
* Orchagent will read these route add/delete notification and updates the ASIC-DB.
* syncd reads these updates and programs the dataplane.
 
### 1.2.2 Containers
No new containers are introduced as part of this design.

# 2 Functionality

## 2.1 PIM-ASM Use Cases

### 2.1.1 PIM-ASM Shared Path Tree
 1) Receiver sends a IGMP membership report to join the multicast group.
 2) LHR creates a (\*,G) entry in the multicast routing table for the joined group and updates the outgoing interface list with interface on which it received the IGMP join and sends a PIM (\*,G) join towards the RP to join the shared tree. RP receives the PIM join and it creates a (\*,G) entry in the multicast routing table and the interface towards the LHR in the outgoing interface list. Even though the shared tree ends at RP, FRR creates the (\*,G) entry with iif as the loopback interface on which the RP is configured and the same is pushed to Kernel. But this (\*,G) entry will not be installed in the hardware as the iif is considered as NULL. A shared tree for multicast group has been constructed from RP to LHR and the receiver.
 3) Source starts to stream the multicast data
 4) FHR DR sends PIM Register message by encapsulating the multicast data and unicast it to RP.
 5) RP on receiving PIM Register message, de-encapsulates the messages and and checks if the packet is for an active multicast group, if so it  forwards the packet down the shared tree. RP joins the SPT for the source by sending (S,G) join to FHR so that it can receive native (S,G) multicast traffic. 
 6) FHR starts to stream native multicast data to RP. RP on receiving native multicast data sends register stop message to FHR.
 7) RP natively forwards the traffic to LHR
 8) LHR forwards the muticast stream to the end Host.
   
   ![PIM_ASM_SHARED_TREE](pim_images/PIM_SM_Shared_Path_Tree.png "Figure 1: IP Multicast deployment with PIM-SM Shared Tree")

  __Figure 1: IP Multicast Deployment with PIM-ASM Shared Tree__

### 2.1.2 PIM-ASM Shortest Path Tree
* Shortest path tree also follows the above steps from 1 to 7. The rest all differences are listed below
8) Shortest Path Tree(SPT) is built from LHR and other transit routers towards the Source. This is achieved by sending an explicit (S,G) join from LHR to source by bypassing the RP. Now LHR has joined the shortest path tree and pull traffic directly from source.
9) FHR updates the outgoing interface of the (S,G) routes with the interface on which (S,G) join is received from LHR. And thereby it pushes the traffic directly to the LHR.
10) LHR also prunes the join towards RP for this group by explicitly sending an (S,G,Rpt) prune once the traffic is received on the (S,G) join.
11) RP on receiving the (S,G,Rpt) prune checks if there are any other interested receivers for this group, if there is no other receiver it sends prune for that group to FHR. And FHR stops streaming the multicast data to RP until any new receiver joins via RP. But, RP maintains the (S,G) state in order to pull the traffic as soon as possbile for any newly joined receiver without the need for registration. To achieve this, FHR periodically sends a NULL register message to RP. Unlike normal PIM register messages, null register messages do not encapsulate the original data packet.NULL registers are sent as long as the source is active.
    
    ![PIM_SPT](pim_images/PIM_SM_Shortest_Path_Tree.png "Figure 2: IP Multicast deployment with PIM-ASM Shortest Path Tree")
 
  __Figure 2: IP Multicast Deployment with PIM-ASM Shortest Path Tree__

# 3 Design 

## 3.1 Overview

The following diagram depicts the interactions among modules in SONIC to achieve PIM ASM functionality 


  ![PIM_ASM_DESIGN_OVERVIEW](pim_images/PIM_ASM_DESIGN_OVERVIEW.png)

   
   __Figure 3: PIM ASM Architecture in SONiC__

The interactions between FRR PIM, Linux kernel, ipmcFpmSyncd and ipmcOrch for updating a multicast (*,G) and (S,G) route entry from PIM to the hardware are explained below:

A small change has been introduced in ipmFpmsyncd for handling the KAT timer expiry of (S,G) routes which is explained in case 3 below.

#### Case 1: Flow for (*,G) route update

1. PIM ASM creates a (*,G) entry in 2 scenarios. First, when LHR node receives an IGMP report message and second, when RP and other transit routers receives a PIM join from the downstream. PIMD listens on a socket for receiving the PIM and IGMP control packets.
   
   1.1.(a) When the LHR receives an IGMP Report, it is passed to the Linux kernel.  Kernel delivers the IGMP Report payload to the Pimd process.  Pimd creates a IGMP group membership entry and checks if the RP address is reachable.  If reachable, Pimd creates a (\*,G) entry with the RPF interface as its IIF and updates the (\*,G) entry's OIF with the interface on which the IGMP Report is received.
   Data packets are needed by Pimd to do SPT switchover in case of LHR, To achieve this, the OIF list is updated with the pimreg interface. <br> <br>

    1.1.(b) When the RP or an intermediate PIM router receives a PIM (\*,G) Join message, the message is passed to the Linux kernel and kernel delivers the PIM Join message and its associated payload to Pimd process.  PIM queries Zebra for RPF validation and then creates a (\*,G) entry with the RPF interface as its IIF. In case of RP, the IIF interface is the interface on which the RP address is configured ideally the loopback interface. PIM queries IGMP database (inside Pimd) and updates the (\*,G) entry's OIF list. To complete the registration process RP needs the data packet in Pimd, so to get the multicast data in Pimd the pimreg interface is updated in the OIF list.  <br> <br>
    
2. After PIM creates the (\*,G) entry with the required information, PIM updates Linux kernel using a socket and kernel creates a mroute entry. In case of RP, pimd sends the (\*,G) entry with loopback interface as iif and kernel creates mroute with the same.<br> <br>
   
3. ipmcFpmSyncd registers with Linux kernel for RT netlink group RTNLGRP_IPV4_MROUTE and listens for RTM_NEWROUTE and RTM_DELROUTE RT netlink events.  When Pimd creates/deletes a multicast route entry, Linux kernel notifies ipmcFpmSyncd about multicast route entry creation/deletion using RTM_NEWROUTE and RTM_DELROUTE events. <br> <br>

4. ipmcFpmsyncd processes the netlink message and updates the (*,G) route entry information into IPMC_ROUTE_TABLE in APPL_DB. <br> <br>

5. ipmcOrch being an subscriber for IPMC_ROUTE_TABLE in APPL_DB , it receives the multicast route entry information  updated by ipmcFpmsyncd. <br> <br>

6. After processing the received information, if the oifs and iifs have valid RPF then the ipmcOrchagent invokes SAI APIs to inject the multicast route entry information into ASIC_DB. In case of RP, as (\*,G) has the loopback interface as iif which does not have a valid RPF, orchagent will not push (\*,G) entry to SAI.<br> <br>

7. Syncd being an ASIC_DB subscriber, it receives the multicast route information updated to ASIC_DB by ipmcOrchagent. <br> <br>

8. Syncd processes the multicast route information and invokes the SAI API to inject the (\*, G)  mroute entry into the corresponding ASIC-driver. <br> <br>

9. The multicast route is finally programmed in the hardware.

#### Case 2: Flow for (S,G) route update

1. PIM ASM creates (S,G) entry once the data traffic starts to flow. <br> <br>
  1.1 When FHR receives the unknown multicast data from a source it traps and delivers the multicast data to the Linux kernel. Kernel delivers this packet to the Pimd process. On reception of data, Pimd starts the registration process. 
As FHR is not aware of the interested receivers,it encapsulates the data packet in a unicast PIM register message and forwards it to RP address. <br> <br> 
  1.2  RP's kernel receives the PIM register packet. It decapsulates the data and forwards the data to the downstream routers and it delivers the register packet to Pimd. Pimd processes the register message and it creates (S,G) join by inheriting the OIF from the (\*,G) route along with cpu port and IIF as the incoming interface of the data and  forwards it towards the FHR.
  
   1.3 FHR receives the (S,G) join and programs the kernel and the ASIC_DRIVER by following the steps (2 to 9) mentioned in case 1. 
  Once the (S,G) is programmed the traffic starts to flow natively in FHR and RP.<br> <br>
    1.4 When LHR receives the multicast data it lifts the data using the programmed (\*,G) and forwards a copy to the receiver. LHR creates (S,G) multicast route with IIF as the RPF interface of the source and OIFs inherited from the (\*,G) route .It forwards the join towards source and it prunes the (\*,G) join towards RP by explicitly sending a (S,G,rpt) prune towards RP.Once the join reaches the FHR the traffic natively flows using the (S,G) join.

#### Case 3: KAT for (S,G) routes

Once the (S,G) routes are learnt and programmed in the hardware, the traffic starts flowing through the data path. To check the liveliness of the (S,G) routes installed in the TIB, the traffic flow for the (S,G) routes in the hardware should be monitored and the status of it should be passed to the Pimd. If the traffic is not flowing for an (S,G) for the default KAT timer of 210 seconds then the entries in the TIB are purged. The flow of(10) to (14) covers this.

10. Once the (S,G) routes are installed in the Hardware, the hardware starts a timer for all the installed (S,G) routes. This timer value is maintained at a lesser value than the original KAT timer and also this timer would be a global timer having the same value across all the VRFs in the hardware.  This value will be updated by FRR once it learns a first ASM route in any VRF and the value would be set to 0 once the last ASM route is deleted across all the VRFs. The hardware KAT timer value is almost 7 times lesser than that of the configured KAT time [say for e.g, if the configured KAT timer value is 210 seconds then the KAT timer in H/W would be 30seconds]. The hardware updates the routes status as and when it changes to DONT_AGE or AGE in the STATE_DB. <br><br>
    
11. The ipmcFpmSyncd process will be registered for the event notification for the multicast routes in the state DB. Once the DONT_AGE/AGE status is updated in the STATE_DB, ipmcFpmSyncd will receive this event and it will update it's local DB with the age and dont_age counter values.This DB would be updated as and when there is a change in the status of the routes in the Hardware. If the route status is toggling in the hardware sending AGE,DONT_AGE status continuously, even if the last received notification was AGE, but if we have seen atleast one DONT_AGE status within the FRR timer value, ipmcfpmsyncd calculates this as DONT_AGE and updates the same to FRR. If the toggling has stopped and last received route status was AGE,ipmcFpmsyncd updates the route status as AGE to FRR in the next KAT timer expiry and FRR purges the route.So, in  a worst case the routes will be retained for (2*KAT) value in TIB. If the status doesn't toggle, then ipmcfpmsyncd sends the route status as AGE and FRR purges it immediately.  <br><br>
    
12. FRR which runs the KAT timer for each of the routes will query the ipmcFpmsyncd for the routes status. IpmcFpmSyncd will do the route status calculation based on the AGE/DONT_AGE counters and update the status to Pimd.<br><br>

13. Pimd will process this route status and if the route status is received as AGE it  purges the route immediately from the TIB and the routes are deleted from Kernel and Hardware too.<br><br>

### 3.1.1 ipmcFpmSyncd 

  ipmcFpmSyncd currently registers with the Linux kernel for RT netlink group RTNLGRP_IPV4_MROUTE and listens for RTM_NEWROUTE and RTM_DELROUTE RT netlink events. When Pimd creates/deletes a multicast route entry, Linux kernel notifies ipmcFpmSyncd about multicast route entry creation/deletion using RTM_NEWROUTE and RTM_DELROUTE events.
 With ASM, ipmcFpmSyncd has to establish a new communication channel with FRR for <br> 1. Setting the KAT timer value in the hardware.
2. Monitoring the keep alive status of each (S,G) routes from the hardware and pass it to FRR.

 ipmcFpmSyncd has only one thread. If a new interface is introduced for fetching the KAT timer status in the same thread,in a highly scaled system there are chances that continuous route updates from Kernel can delay the KAT timer processing from FRR leading to purging of routes in TIB. To overcome this limitation, a new thread will be introduced in ipmcfpmsyncd. This new thread will create the socket for the new interface channel with FRR and wait on its FD. The other NETLINK notification will be handled by the main thread. This new thread will listen to the route status of each (S,G) in state DB and update the cache_age, cache_dont_age and last_route_status values in its local cache. Whenever FRR queries ipmcfpmsyncd for route status, based on the local cache values the route status is calculated and communicated to FRR.  Ipmcfpmsyncd will delete this local cache when the state_DB entries are cleared. 

### 3.1.2 ipmcorchagent changes
As part of the PIM ASM support following functionalities attained by ipmcorchagent,<br> 
1. CPU bit update for (*,G) and (S,G) routes<br> 
2. Updating the KAT timer value for (S,G) routes from FRR to ASIC<br> 

#### 3.1.2.1 CPU bit update

CPU bit must be updated for (*,G) or (S,G) entry to punt the packets to FRR stack using CPU port. <br>
To achieve this functionality during creation of IPMC entry in BCM we need to set the action as SAI_PACKET_ACTION_COPY  .<br>
If CPU port removed from the (*,G) or (S,G) entry then ipmcorchagent need to set action to SAI_PACKET_ACTION_COPY_CANCEL <br>

Following are the sequence of events handled in ipmcorchagent for CPU bit update,<br>
1. ipmcfpmsyncd update APPL_DB with (S,G) or (*,G) and OIF as "pimreg" in APP_IPMC_ROUTE_TABLE_NAME table
2. ipmcorchagent gets notified with APP_IPMC_ROUTE_TABLE_NAME<br>
3. If operation is SET with ifname as "pimreg", set the ACTION as SAI_PACKET_ACTION_COPY
4. If operation is DELETE with ifname as "pimreg", set the ACTIOn as SAI_PACKET_ACTION_COPY_CANCEL<br>

| Existing Entry  |   New Entry | Operation | Action |
| ----------------|-------------|-----------|--------|
| None            | (*,G) or (S,G) OIF as pimreg | SET | SAI_PACKET_ACTION_COPY (IPMC entry created) |
| (*,G) or (S,G) OIF as pimreg | (*,G) or (S,G) OIF as pimreg | DEL | IPMC entry removed |
| None            | (*,G) or (S,G) OIF as Vlan10 | SET | SAI_PACKET_ACTION_FORWARD (IPMC entry created) |
| (*,G) or (S,G) OIF as Vlan10 | (*,G) or (S,G) OIF as Vlan10,pimreg | SET | SAI_PACKET_ACTION_COPY |
| (*,G) or (S,G) OIF as Vlan10,pimreg | (*,G) or (S,G) OIF as Vlan10 | SET | SAI_PACKET_ACTION_COPY_CANCEL |
| (*,G) or (S,G) OIF as Vlan10,pimreg | (*,G) or (S,G) OIF as Vlan10,pimreg | DEL | IPMC entry removed |
| (*,G) or (S,G) OIF as pimreg | (*,G) or (S,G) OIF as pimreg | DEL | IPMC entry removed |

#### 3.1.2.2 IIF expansion in OIF List

IIF member ports to be included in IPMC group member on following cases,
1. L3 multicast case, local receiver on the IIF vlan then add IIF vlan in OIF list
2. Shared case (L3 and Snooping enabled), local receiver on the IIF vlan then add IIF vlan member ports into OIF list

FRR will remove the IIF in OIF list for SG entries. So APPL_DB will have empty OIF list.

Configuration sequence,
1. FRR sends update to ipmcfpmsyncd with IIF as Vlan and OIF as empty
2. ipmcfpmsyncd populates S,G with IIF as VLAN and OIF empty in APPL_DB
3. ipmcorchagent, upon receiving the update adds IIF VLAN to OIF list(class MRouteEntry and member list m_oifs updated with IIF vlan)<br>
    a) calls IPMC group creation incase of L3 VLAN <br>
    b) call L2MC group creation incase of snooping enabled on the VLAN <br>
4. SAI expands the L2/L3 portbitmap for IIF/OIF Vlans

| Source IP       | Group IP        | Incoming Interface   |Outgoing Interface(s)
|----------------|----------------|--------------------| ---------------------
|30.0.0.3 |        225.1.1.1|        Vlan300|              Vlan100
| | | |    Vlan300
|30.0.0.4 |        225.1.1.1|        Vlan300|              Vlan300

#### 3.1.2.3 IPMC Aging time

IPMC aging timeout is switch attribute for SAI. This is global configuration for a switch and applicable to all VRF, all AFI's.

Following the sequence of configuration,
1. FRR sends update to ipmcfpmsyncd with aging value using struct mfpm_kat_info_t.
2. ipmcfpmsyncd populate "ipmc_aging_time" entry in  SWITCH_TABLE (APPL_DB)
3. ipmcorchagent, receives SWITCH_TABLE (APPL_DB) update and calls set_switch_attribute with attr as SAI_SWITCH_ATTR_IPMC_AGING_TIME and value "ipmc_aging_time" <br>

### 3.1.3 Syncd changes
#### 3.1.3.1 Changes required to process IPMC entries AGE and DONTAGE data
Following will be added in the syncd inorder to process the IPMC entry or entries AGE and DONTAGE data,

1. Establish a connection with STATE_DB inorder to add or remove IPMC entries AGE and DONTAGE data.
2. New notification handler (Notificationhandler::onIpmcEvent) API will be defined and registered with SAI to receive IPMC specific AGE and
   DONTAGE notifications.
   IPMC specific notification will be identified with the enum "SAI_SWITCH_NOTIFICATION_NAME_IPMC_EVENT" which will be added 
   newly in SAI layer. 
3. On receiving the IPMC entry/entries AGE or DONTAGE data, required validations will be done after 
   deserializing the received data and then serialized unmodified data will be written to STATE_DB for further processing. A new API
   will be defined to add or delete the data to/from the STATE_DB.

##### 3.1.3.1.2 IPMC Entry deletion
Whenever a IPMC entry is deleted for any reason, AGE and DONTAGE data belongs to that particular IPMC entry will be
cleared from the STATE_DB.
##### 3.1.3.1.3 SYNCD WARM restart
To be updated based on the syncd warm restart feature understanding from broadcom.
## 3.2 Datastructure Changes

Struct mfpm_msg_hdr_t

|    Data Type     | Field_name | Description |
| -----------------| ---------- | ----------- |
|  uint8_t         |  version   | Protocol version |
|  mfpm_msg_type_t |  msg_type  | message type     |
|  uint16_t        |  msg_len   | Length of the entire message including header length |

Enum mfpm_msg_type_t

|   Enum name    | Value |
| --------------- | ---------- | 
|   MFPM_MSG_TYPE_NONE  | 0  | 
|   MFPM_MSG_TYPE_SET    |  1  | 
|   MFPM_MSG_TYPE_GET | 2 |
|   MFPM_MSG_TYPE_MAX | 3 |

Enum mfpm_route_status_t

|   Enum name    | Value |
| ---------------| ---------- | 
|   MFPM_ROUTE_NOT_FOUND  | 0  | 
|   MFPM_ROUTE_ACTIVE   |  1  | 
|   MFPM_ROUTE_INACTIVE | 2 |


struct mfpm_route_info_t

|   Data Type    | Field_name |  Description   |
| -------------- | ---------- | -------------- |
| unit32_t       | vrf_id     | VRF Id         |
| char[INTERFACE_NAMSIZ]      | iif_name   | Incoming interface name |
| struct ip_addr | src        | Source address of the route |
| struct ip_addr | grp        | Group address of the route  |
| mfpm_route_status_t         | entry_status | Entry aliveness status | 

struct mfpm_kat_info_t

|   Data Type    | Field_name |  Description   |
| -------------- | ---------- | -------------- |
| unit32_t       | vrf_id     | VRF Id         |
| unsigned int   | keep_alive_time | Keep alive timer config to be applied in NPU |

union mfpm_data_msg_t

|   Data Type    | Field_name |  Description   |
| -------------- | ---------- | -------------- |
|  mfpm_kat_info_t | kat_info | Keep alive timer config to be set |
|  mfpm_route_info_t | route_info | Info to get Route status from MFPM client |

### 3.2.1 **SAI specific data structure and callback changes**

Following data structures will be included and exposed to SYNCD to receive IPMC entry aliveness data,

typedef enum _sai_ipmc_event_t
{
      
SAI_IPMC_EVENT_AGE,
      
SAI_IPMC_EVENT_DONT_AGE,
      
} sai_ipmc_event_t;

**SAI provide the data in the below mentioned structure format as part of callback.**
      
typedef struct _sai_ipmc_event_notification_data_t
{
      
sai_ipmc_event_t event;
      
sai_ipmc_entry_t ipmc_entry;
      
} sai_ipmc_event_notification_data_t;

**sai_ipmc_entry_t** - This is an existing SAI data structure.

SYNCD registers the following callback API with SAI to receive IPMC entries aliveness data,

typedef void (*sai_ipmc_event_notification_fn)(_In_ uint32_t count,
_In_ const sai_ipmc_event_notification_data_t *data);
      
## 3.3 DB Changes
PIM ASM leverages all the existing DBs. There are few new DBs introduced in CONFIG and STATE DBs like PIM_GLOBALS_STATIC_RP & IPMC_MROUTE_AGE_TABLE for ASM specific functionality.

### 3.3.1 CONFIG DB
#### 3.3.1.1 PIM Global Configuration [Existing]
```diff

Key                       : PIM_GLOBALS|vrf-name|address-family

vrf-Name                  : 1-15 characters ; VRF name
address-family            : enum {ipv4, ipv6}

join-prune-interval       : Join prune interval in seconds. Range (60-600 seconds)
keep-alive-timer          : Keep alive timer in seconds. Range (31-60000 seconds)
ssm-ranges                : Configure Source-Specific-Multicast group range using IP Prefix-list
ecmp-enabled              : To enable PIM ECMP (true/false)
ecmp-rebalance-enabled    : To enable PIM ECMP rebalance (true/false). It can be enabled/disabled only when ECMP is enabled
+spt-action               : To disable or re-enable the SPT switchover
+spt-infinity-prefix-list : Prefix-list for which SPT switchover has to be disabled.
```

#### 3.3.1.2 PIM Interface-Specific Configuration [Existing]
```JSON
Key                       : PIM_INTERFACE|vrf-name|address-family|interface

vrf-Name                  : 1-15 characters ; VRF name
address-family            : enum {ipv4, ipv6}
interface                 : interface-name (Ethernet or Port-channel or Vlan interface-name)

mode                      : enum (sm) ; PIM-mode
dr-priority               : Designated router priority. Range (1-4294967295)
hello-interval            : Hello interval in seconds. Range (1-180)
bfd-enabled               : To enable BFD support for PIM on this interface (true/false)
```
#### 3.3.1.3 PIM STATIC RP Coniguration [New] 

```DIFF
+     Key                       : PIM_GLOBALS_STATIC_RP|vrf-name|address-family|rp-address
+     
+     vrf-Name                  : 1-15 characters ; VRF name
+     address-family            : enum {ipv4, ipv6}
+     rp-address                : IPv4/IPv6 address of rendezvous point
+     prefix-list-name           : String ; Prefix-list to map a range of multicast group address to a static-RP. 
```

### 3.3.2 APP DB 
No new APP DB has been introduced as part of PIM-ASM.

#### 3.3.2.1 IPMC_ROUTE_TABLE [Existing]

```JSON
IPMC_ROUTE_TABLE:{{vrf_id}} | {{source_address}} | {{group_address}}
"incoming interface" : {{ifname}}
"outgoing interface list" : {{list of interfaces}}
```

IPMC_ROUTE_TABLE Schema

```JSON
; Defines schema for multicast route entry table
key = IPMC_ROUTE_TABLE:vrf_id|src_address|grp_address ; Mroute table
; field = value
INCOMING_INTERFACE = ifname ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
OUTGOING_INTERFACE_LIST = intf_names_list ; list of interfaces delimited by ','
```
#### 3.3.2.2 INTF_TABLE [Existing]

```JSON
INTF_TABLE:{{ifname}} ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
"mcast_forwarding" : {{multicast-forwarding-status}}
```

INTF_TABLE Schema
```JSON
; Defines schema for multicast interface table
key = IPMC_INTF_TABLE:ifname ; Interface table ... ifname must be unique across PORT,INTF,VLAN,LAG TABLES
; field = value
mcast_forwarding = "true" / "false"
```
#### 3.3.2.3 SWITCH_TABLE [Existing]
A new attribute called "ipmc_aging_time" has been introduced to push the KAT timer value to Hardware.

```JSON
SWITCH_TABLE:{"switch"}
"ipmc_aging_time" : {{aging time}}
```

SWITCH_TABLE Schema

```diff
+     ; Stores configuration of aging time
+     key = "switch"
+     ipmc_aging_time           = Aging time in seconds. 0 to disable. Supported 1-60000 seconds.
```

### 3.3.3 STATE DB

#### 3.3.3.1 IPMC_MROUTE_AGE_TABLE [New]
```DIFF 
+     Following will be the DB schema for multicast route entry aging,
+     
+     Table Key                IPMC_MROUTE_AGE_TABLE: vrf_id | source_address | group_address
+     State                    age (0) or dont_age (1). 
+                              age (0) - Indicates, there no traffic hit on a specific VRF, SOURCE IP and MULTICAST GROUP in a given time interval.
+                              dont_age (1) - Indicates a traffic hit.               
```

### 3.3.4 ASIC DB
None

#### 3.3.4.1 ASIC DB Programmable by PIM

##### 3.3.4.1.1 SAI_OBJECT_TYPE_IPMC_ENTRY [Existing]

```JSON  
Key :   "ASIC_STATE:SAI_OBJECT_TYPE_IPMC_ENTRY:{\"destination\":\"<group ip>\",\"source\":\"<src ip>\",\"switch_id\":\"oid:<switch_id>\",\"type\":\"<entry_type>\",\"vr_id\":\"oid:<vrf_id_oid>\"}": 
   
    destination: Multicast Group IP address
    source : Source IP address
    switch_id: NPU switch identifier
    type : SAI_IPMC_ENTRY_TYPE_SG or SAI_IPMC_ENTRY_TYPE_XG
    vr_id : VRF ID OID 
    oid: IPMC entry OID

Field:
      SAI_IPMC_ENTRY_ATTR_OUTPUT_GROUP_ID: "oid:<ipmc_group_id>"
      SAI_IPMC_ENTRY_ATTR_PACKET_ACTION: "SAI_PACKET_ACTION_DROP/SAI_PACKET_ACTION_FORWARD/SAI_PACKET_ACTION_COPY/SAI_PACKET_ACTION_COPY_CANCEL"
      SAI_IPMC_ENTRY_ATTR_RPF_GROUP_ID: "oid:<rpf_group_id>"
    
```

##### 3.3.4.1.2 SAI_OBJECT_TYPE_IPMC_GROUP  [Existing]

```JSON

Key:  "ASIC_STATE:SAI_OBJECT_TYPE_IPMC_GROUP:oid :<ipmc_group_id>"
 
   oid : IPMC Group OID
 Field:
    "NULL": "NULL"
```

##### 3.3.4.1.3 SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER (Snooping Enabled Member) [Existing]

```JSON

Key: "ASIC_STATE:SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER: oid:<ipmc_group_member_id>"

  oid: <ipmc_group_member_id>
Field :
      SAI_IPMC_GROUP_MEMBER_ATTR_EXTENSIONS_L2MC_OUTPUT_ID: "oid:<l2_mc_group_id>"
      SAI_IPMC_GROUP_MEMBER_ATTR_IPMC_GROUP_ID: "oid:<ipmc_group_id>"
      SAI_IPMC_GROUP_MEMBER_ATTR_IPMC_OUTPUT_ID: "oid:<rif_id>"
```

##### 3.3.4.1.4 SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER (Snooping Disabled Member) [Existing]

```JSON

Key: "ASIC_STATE:SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER: oid:<ipmc_group_member_id>"

  oid: <ipmc_group_member_id>
Field :
      SAI_IPMC_GROUP_MEMBER_ATTR_IPMC_GROUP_ID: "oid:<ipmc_group_id>"
      SAI_IPMC_GROUP_MEMBER_ATTR_IPMC_OUTPUT_ID: "oid:<rif_id>"
```

##### 3.3.4.1.5 SAI_OBJECT_TYPE_RPF_GROUP [Existing]

```JSON

Key : "ASIC_STATE:SAI_OBJECT_TYPE_RPF_GROUP:oid:<rpf_group_id>"
    oid:<rpf_group_id>
Field:
   "NULL": "NULL"
```

##### 3.3.4.1.6 SAI_OBJECT_TYPE_RPF_GROUP_MEMBER [Existing]

```JSON

Key: "ASIC_STATE:SAI_OBJECT_TYPE_RPF_GROUP_MEMBER:oid:<rpf_group_member_id>"
    oid:<rpf_group_member_id>
Field:
    "SAI_RPF_GROUP_MEMBER_ATTR_RPF_GROUP_ID": "oid:<rpf_group_id>"
    "SAI_RPF_GROUP_MEMBER_ATTR_RPF_INTERFACE_ID": "oid:<rif_id>"
 
```


#### 3.3.4.2 ASIC DB Supporting snooping entries

##### 3.3.4.2.1 SAI_OBJECT_TYPE_L2MC_GROUP [Existing]
```JSON

  Key : "ASIC_STATE:SAI_OBJECT_TYPE_L2MC_GROUP:oid:<l2mc_group_id>"
       oid:<l2mc_group_id>

  Field :
      "NULL": "NULL"
 ``` 

##### 3.3.4.2.2 SAI_OBJECT_TYPE_L2MC_GROUP_MEMBER  [Existing]

```JSON

Key: "ASIC_STATE:SAI_OBJECT_TYPE_L2MC_GROUP_MEMBER:oid:<l2mc_group_member_id>"
    oid:<l2mc_group_member_id>
Field :
      "SAI_L2MC_GROUP_MEMBER_ATTR_L2MC_GROUP_ID": "oid:<l2mc_group_id>",
      "SAI_L2MC_GROUP_MEMBER_ATTR_L2MC_OUTPUT_ID": "oid:<bridge_port_id>"
```

#### 3.3.4.3 ASIC DB Supporting entries [Existing]

##### 3.3.4.3.1 SAI_OBJECT_TYPE_ROUTER_INTERFACE [Existing]

```JSON

Keys: "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:<rif_id_oid>"
    oid: Router Interface OID
Field:
      "SAI_ROUTER_INTERFACE_ATTR_MTU": "<interface_mtu>"
      "SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID": "0"
      "SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS": "<interfac_mac>"
      "SAI_ROUTER_INTERFACE_ATTR_TYPE": "SAI_ROUTER_INTERFACE_TYPE_VLAN"
      "SAI_ROUTER_INTERFACE_ATTR_V4_MCAST_ENABLE": "true"
      "SAI_ROUTER_INTERFACE_ATTR_V6_MCAST_ENABLE": "false"
      "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID": "oid:<vr_id>"
      "SAI_ROUTER_INTERFACE_ATTR_VLAN_ID": "oid:<vlan_id_oid>"
```
##### 3.3.4.3.2 SAI_OBJECT_TYPE_VLAN [Existing]

```JSON

Key : "ASIC_STATE:SAI_OBJECT_TYPE_VLAN:oid:<vlan_id_oid>"
    oid:<vlan_id_oid>
Field:
      "SAI_VLAN_ATTR_CUSTOM_IGMP_SNOOPING_ENABLE": "true",
      "SAI_VLAN_ATTR_VLAN_ID": "104"
```
##### 3.3.4.3.3 SAI_OBJECT_TYPE_BRIDGE_PORT [Existing]

```JSON

Key : "ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:oid:<bridge_port_id>"

    oid:<bridge_port_id>
Field :  
      "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE": "true",
      "SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE": "SAI_BRIDGE_PORT_FDB_LEARNING_MOO
DE_HW",
      "SAI_BRIDGE_PORT_ATTR_PORT_ID": "oid:<port_id>",
      "SAI_BRIDGE_PORT_ATTR_TYPE": "SAI_BRIDGE_PORT_TYPE_PORT"
``` 

### 3.3.5 COUNTER DB
None

## 3.4 Kernel Iptables
kernel has the knowledge about how to forward multicast data traffic. So, whenever multicast data packets are lifted to CPU, the Kernel shouldn't forward them. The data traffic would have already been forwarded by MFIB entries in NPU. Drop rule will be added for each VRF in iptables FORWARD chain to refrain kernel forwarding multicast packets. The multicast data in the Register packets that are sent by FHR alone would be forwarded by the Kernel in RP. This forwarding is essential to avoid loss of traffic till the multicast (S,G) path is established. So, other than this none of the multicast forwarding is allowed by the Kernel.

## 3.5 User Interface
### 3.5.1 Data Models

The existing openconfig-pim.yang and sonic-pim yangs are 
updated with with PIM Rendezvous point and SPT related configuration.Static RP mapping and assert related show commands are added in Sonic-pim.yang 

```diff
       |     +--rw pim
        |     |  +--rw global
        |     |  |  +--rw config
        |     |  |  |  +--rw join-prune-interval?      uint16
        |     |  |  |  +--rw keep-alive-timer?         uint16
        |     |  |  |  +--rw ecmp-enabled?             boolean
        |     |  |  |  +--rw ecmp-rebalance-enabled?   boolean
        |     |  |  +--ro state
        |     |  |  |  +--ro join-prune-interval?      uint16
        |     |  |  |  +--ro keep-alive-timer?         uint16
        |     |  |  |  +--ro ecmp-enabled?             boolean
        |     |  |  |  +--ro ecmp-rebalance-enabled?   boolean
        |     |  |  +--rw ssm
        |     |  |  |  +--rw config
        |     |  |  |  |  +--rw ssm-ranges?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
        |     |  |  |  +--ro state
        |     |  |  |     +--ro ssm-ranges?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
+       |     |  |  +--rw rendezvous-points
+       |     |  |  |  +--rw rendezvous-point* [address]
+       |     |  |  |     +--rw address    -> ../config/address
+       |     |  |  |     +--rw config
+       |     |  |  |     |  +--rw address?            inet:ip-address
+       |     |  |  |     |  +--rw multicast-groups?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
+       |     |  |  |     +--ro state
+       |     |  |  |        +--ro address?            inet:ip-address
+       |     |  |  |        +--ro multicast-groups?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
+       |     |  |  +--rw spt-switchover
+       |     |  |  |  +--rw config
+       |     |  |  |  |  +--rw spt-action?                 enumeration
+       |     |  |  |  |  +--rw spt-infinity-prefix-list?   -> /oc-acl:acl/acl-sets/acl-set/config/name
+       |     |  |  |  +--ro state
+       |     |  |  |     +--ro spt-action?                 enumeration
+       |     |  |  |     +--ro spt-infinity-prefix-list?   -> /oc-acl:acl/acl-sets/acl-s
```
module: sonic-pim-show
```diff
  rpcs:
    +---x show-pim
       +---w input
       |  +---w vrf-name?                      string
       |  +---w address-family?                enumeration
       |  +---w query-type                     show-pim-query-type
       |  +---w (type)?
       |     +--:(RPF)
       |     |  +---w rpf?                     boolean
+      |     +--:(RPINFO)
+      |     |  +---w rpinfo?                  boolean
+      |     |  +---w rpinfo-per-group-addr?   inet:ip-address
+      |     +--:(ASSERT)
+      |        +---w assert?                  boolean
       +--ro output
          +--ro status?   string
module: sonic-pim
  +--rw sonic-pim
     +--rw PIM_GLOBALS
     |  +--rw PIM_GLOBALS_LIST* [vrf-name address-family]
     |     +--rw vrf-name                    union
     |     +--rw address-family              enumeration
     |     +--rw join-prune-interval?        uint16
     |     +--rw keep-alive-timer?           uint16
     |     +--rw ssm-ranges?                 -> /srpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
     |     +--rw ecmp-enabled?               boolean
     |     +--rw ecmp-rebalance-enabled?     boolean
+    |     +--rw spt-action?                 spt-switchover-action-type
+    |     +--rw spt-infinity-prefix-list?   -> /srpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
+    +--rw PIM_GLOBALS_RENDEZVOUS_POINT
+    |  +--rw PIM_GLOBALS_RENDEZVOUS_POINT_LIST* [vrf-name address-family rp-address]
+    |     +--rw vrf-name            union
+    |     +--rw address-family      enumeration
+    |     +--rw rp-address          inet:ip-address
+    |     +--rw prefix-list-name?   -> /srpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
     +--rw PIM_INTERFACE
        +--rw PIM_INTERFACE_LIST* [vrf-name address-family interface]
           +--rw vrf-name          union
           +--rw address-family    enumeration
           +--rw interface         union
           +--rw mode?             enumeration
           +--rw dr-priority?      uint32
           +--rw hello-interval?   uint8
           +--rw bfd-enabled?      boolean
           +--rw bfd-profile?      string
```
### 3.5.2 CLI

#### 3.5.2.1 Global Configuration Commands

##### 3.5.2.1.1 ip pim rp-address 


| ip pim rp-address  |        Configure a static PIM rendezous point (RP) address for a group.                                                                     |
| ------------------------------------------------ | ------------------------------------------------------------ |
| **Syntax**                                                                    | ip pim [vrf vrf-name] rp-address < address > [{ prefix-list prefix-list-name}]                      |
|                                                                               | no ip pim [vrf vrf-name] rp-address < address > [{ prefix-list prefix-list-name}] |
| **Parameters**                                                                |                                                                           |
| vrf vrf-name (OPTIONAL)                                                              |Enter the keyword vrf followed by the name of the VRF                        |
| rp-address                                                                           | Enter the rp-address keyword                |
 address                                                                           | Enter RP address in dotted decimal format(A.B.C.D)                |
   prefix-list                                                                           | Enter the keyword prefix-list then configure with a valid prefix-list-name            |
   |**Note**         | If the group-address/mask is not specified, the given RP address will map to the default group 224.0.0.0/4.
| **Default**                                                                   | None  |
| **Usage Notes**                                                               | PIM-SM specific Rendezous point configuration, .                         |
| **Command mode**                                                              | CONFIG                                                                    |
| **Example**                                                                   |                                               |                 
|                 | a)	To configure a prefix-list to a RP, Sonic(config)# ip pim rp-address 20.1.1.1 prefix-list rp-grp-prefix-list
| |b)	To configure default group (224.0.0.0/4) for an RP,       Sonic(config)# ip pim rp-address 20.1.1.1    
|                                                                           | c)	To remove the rp-maddress mapped to a prefix-list , Sonic(config)# no ip pim rp-address 20.1.1.1 prefix-list rp-grp-prefix-list (d) To remove the rp-address along with its group mapping Sonic(config)# no ip pim rp-address 20.1.1.1 |
**Support**                                                                   | 4.1                                        |



##### 3.5.2.1.2 ip pim spt-threshold infinity  



|ip pim spt-threshold infinity  | Command to disable or re-enable shortest path tree (SPT) swtchover for all the multicast groups or a given prefix-list.|  
| ------------------------------------------------ | ------------------------------------------------------------ |
|                                  **Syntax**                                   | ip pim [vrf vrf-name] spt-threshold infinity { prefix-list prefix-list-name} |     
|                                                                               | no ip pim [vrf vrf-name] spt-threshold infinity       |
| **Parameters**                                                                |                                                                                       |     
| vrf                                                                           | Applies to specific VRF if VRF input is provided       |     
|spt-threshold  | Shortest path tree switchover   |
|infinity       | Disables SPT switchover
|prefix-list   |  Provide the prefix-list or list of multicast groups on which SPT switchover has to be disabled or re-enabled.
**Default**                                                                   | Immediate. By default, SPT swicthover is enabled. |     
| **Usage Notes**                                                               |This command is useful to disable and re-enable SPT switchover.                 |     
| **Command mode**                                                              | CONFIG                                                                  |     
| **Example**                                                                   | a)(sonic-config)# ip pim spt-threshold infinity. This command disables SPT switchover on all multicast groups.       |
|                    |      b) (sonic-config)# ip pim spt-threshold infinity prefix-list < prefix-list name >. This command disables SPT switchover on a given prefix-list. Prefix list has to be configured using "ip prefix-list < prefix-list name >" command. After disabling SPT swithcover on a specific multicast group, incase user wants to disable SPT switchover on all groups, user can do so just by executing "ip pim spt-threshold infinity" command.      
| | c)	(sonic-config)# no ip pim spt-threshold infinity. Default spt-swicthover behaviour will be resumed on all multicast groups upon execution of this command.|  
**Support**                                                                   | 4.1      |

#### 3.5.2.2 Show Commands
##### 3.5.2.2.1 show ip pim rp mapping and show ip pim rp <grp-addr>

| PIM Rendezvous Point (RP) information                                           | |
| ------------------------------------------------------------------------------- |--|
| **Syntax**                                                                      | show ip pim [vrf < vrf-name > ] rp [mapping \| group-address]
| **Parameters**                                                                  |
| group-address                                                                   | Multicast Group Address to display information about |
| mapping                                                                         | Show group-to-RP mappings |
| vrf vrf-name(OPTIONAL)                                                          | Enter the keyword vrf followed by the name of the VRF to show for a specific VRF. |
| NOTE: Applies to specific VRF if input is provided, else applies to Default VRF |
| **Default**                                                                     | None |
| **Command mode**                                                                | EXEC |
| **Example**                                                                     | SONIC# show ip pim rp mapping<br>Group(s): 224.0.0.0/4, Static<br>RP: 20.1.1.1, v2<br><br><br><br>SONIC# show ip pim rp mapping<br>Group(s): group\_prefix\_list, Static<br>RP: 20.1.1.1, v2<br><br><br>SONIC# show ip pim rp <br>Group                 RP<br>224.1.1.1             20.1.1.1 <br>224.2.2.2             30.1.1.1 <br> 224.3.3.3             20.1.1.1 <br> <br><br>SONIC# show ip pim rp 224.1.1.1 <br>Group                 RP<br>224.1.1.1             20.1.1.1 
**Support**                                                                     | 4.1 |



##### 3.5.2.2.2 show ip pim assert

| Command to display assert information                                                    | |
| ------------------------------------------------------------------------------- |---|
| **Syntax**                                                                      | show ip pim [vrf ] [vrf-name] assert |
| **Parameters**                                                                  |
| vrf vrf-name(OPTIONAL)                                                          | Enter the keyword vrf followed by the name of the VRF to show for a specific VRF. |
| NOTE: Applies to specific VRF if input is provided, else applies to Default VRF |
| assert                                                                          | Enter the assert keyword |
| **Default**           | None |
| **Command mode**      | EXEC |
| **Example**           | sonic# show ip pim assert<br>Interface        Address         Source          Group           State  Winner          Uptime   Timer<br>Vlan16           16.1.1.1       \*                   225:1:1::1       NOINFO \*               123:28:36 --:-- <br>sonic# | |
| **Support**           | 4.1 |

#### 3.5.2.3 Show running-config Commands
##### 3.5.2.3.1 show running-configuration igmp

| Command to display current operating igmp configurations | |
| ------------------------------------------------------- |---|
| **Syntax**                                              | show running-configuration igmp |
| **Parameters**                                          |
| **Default**                                             | None |
| **Command mode**                                        | EXEC |
| **Example**                                             | Sonic# show running-configuration igmp<br>!<br>interface vlan2001<br>ip igmp version 2<br>Sonic# |
| **Support**                                             | 4.1 |

##### 3.5.2.3.2 show running-configuration pim

| Command to display current operating pim configurations | |
| ------------------------------------------------------------ |---|
| **Syntax**                                                   | show running-configuration pim |
| **Parameters**                                               |
| **Default**                                                  | None |
| **Command mode**                                             | EXEC |
| **Example**                                                  | Sonic# show running-configuration pim<br>!<br>interface vlan1001<br>ip pim sparse-mode<br>!<br>interface vlan2001<br>ip pim sparse-mode<br>!<br><br>Sonic# |
| **Support**                                                  | 4.1 |

**Note:**  
The FRR PIM stack is enhanced to provide the support for the newly added command "Show ip pim rp < grp-addr >" and json support is added for the existing "show ip pim assert" command.
   
#### 3.5.2.4 Debug Commands
No new debug commands are added as part of PIM-ASM implementation.
#### 3.5.2.5 IS-CLI Compliance
NA

### 3.5.3 REST API Support
Rest API support is there for all the existing fields and the ones that are newly added for PIM-SM like RP and spt-switchover. The sample curl commands for CRUD on RP are given below

1) curl -X POST "https://100.104.98.88/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim" -H "accept: */*" -H "Authorization: Basic YWRtaW46YnJvYWRjb20=" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:global\":{\"rendezvous-points\":{\"rendezvous-point\":[{\"address\":\"4.4.4.4\"}]}}}"
2) curl -X PUT "https://100.104.98.88/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf_green/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Authorization: Basic YWRtaW46YnJvYWRjb20=" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:global\":{\"rendezvous-points\":{\"rendezvous-point\":[{\"address\":\"4.4.4.4\",\"config\":{\"address\":\"4.4.4.4\",\"multicast-groups\":\"P1\"}}]}}}"
3) curl -X PATCH "https://100.104.98.88/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Authorization: Basic YWRtaW46YnJvYWRjb20=" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:global\":{\"rendezvous-points\":{\"rendezvous-point\":[{\"address\":\"4.4.4.4\",\"config\":{\"address\":\"4.4.4.4\",\"multicast-groups\":\"P1\"}}]}}}"
4) curl -X GET "https://100.104.98.88/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: application/yang-data+json" -H "Authorization: Basic YWRtaW46YnJvYWRjb20="
5) curl -X DELETE "https://100.104.98.88/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Authorization: Basic YWRtaW46YnJvYWRjb20="

### 3.5.4 gNMI Support


# 4 Flow Diagrams

## 4.1 PIM Config Flow
![](pim_images/PIM_STATIC_RP_CONFIG_FLOW.png)

## 4.2 PIM Data packet Flow
![](pim_images/2021-12-06-13-10-56.png)

## 4.3 PIM KAT system wide Flow
!![](pim_images/2022-03-14-22-18-55.png)

## 4.4 Process restart
!![](pim_images/2022-03-14-22-37-58.png)


# 5  Design Constraints and Risks

Ipmcfpmsyncd is single threaded. Till now it has only single entry point which is kernel netlink events. Now through MPFM channel it would route status get from FRR which also has to be serivced. This channel get query request is blocking call in FRR,  (i.e) FRR will give a get request and it will wait for response from ipmcfpmsynd. If Ipmcfpmsynd is busy handling netlink events, FRR would be blocked for a long time, this will lead to frr protocol events not being serviced and hence will lead to functionality issue. 
Ipmcfpmsyncd has to be implemented as multi threaded process to handle multiple events... Still coming up with multithreaded design.
          
# 6 Error Handling
# 7 Serviceability and Debug
FRR PIM has debug tracing support. This feature utilizes the same.

# 8 Warm Boot Support

Administrator can initiate Warmboot when PIM is enabled, but there may be an interruption in IP multicast traffic flow. . PIM clears all the existing the IP multicast route entries from APP_DB.So, PIM router will effectively start as in cold-boot.

# 9 Scalability
Below are the IP multicast scaling numbers:

###### Table 3: IP Multicast Scaling limits
| Name                                 | Scaling value |
|--------------------------------------|---------------|
| Number of Multicast Route Entries    | 8192          |
| Number of PIM Neighbours             | 64            |

Linux kernel supports only 32 multicast routing interfaces of which one interface is reserved for PIM register interface.  So, PIM/IGMP can be enabled on only 31 routing interfaces.

# 10 Unit Test
Below list covers the major testcase that would be covered as part of this feature. The rest of the cases are covered in devtest scripts.
 
| S.No |   Testcase Type    |       Summary                                | Comments               |
|------|--------------------|----------------------------------------------|------------------------|
| 1    |   CLI              | PIM Configuration availability and help check|                        |
| 2    |   Functionality    | Verify that router with highest dr-priority value assigned to an interface becomes the designated router| |
| 3    |   Functionality    | Verify that interface with highest ip-address gets elected as DR when dr-priority value assigned to an interfaces are equal||
| 4    |   Functionality    | Add/delete a valid static rp without group-address on local and remote | |
| 5    |   Functionality    | Add/delete a valid static rp with group entries in access-list on local and remote switch  | |
| 6    |   Functionality    | (*,G) state between the last-hop router and the RP when IGMP memberships come in  | |
| 7    |   Functionality    | Sending Register message    | |
| 8    |   Functionality    | RP is the only sender (fhr/rp-lhr)    | |
| 9    |   Functionality    | RP is the only receiver (fhr---Interm---rp/lhr)  | |
| 10   |   Functionality    | Check shared tree on intermediate router for (rp---interm---lhr) scenario  | |
| 11   |   Functionality    | RP in the middle( fhr---rp---lhr )       | |
| 12   |   Functionality    | Inverse topology (lhr---fhr---rp)   | |
| 13   |   Functionality    | Switching from RP-tree to SP-tree   | |
| 14   |   Functionality    | Verify that router generating an Assert with the lowest Administrative distance is elected as forwarder  | |
| 15   |   Functionality    | Verify that best unicast routing metric is used to break a tie if the AD are the same  | |
| 16   |   Functionality    | Verify that device with the highest IP Address will be elected as the PIM Forwarder if the AD and metrics are same  | |
| 17   |   Functionality    | J/P refresh Interval: random start, 60 default, persistency, join/leave latency  | |
| 18   |   Functionality    | J/P Holdtime: 3.5* default, oif time out, state time out  | |
| 19   |   Functionality    | Memory leaking when pim is enabled with multicast traffics| |
| 20   |   Functionality    | Tree switching and route change  | |  
| 21   |   Functionality    | Check pim-sm/ssm functionality on non-default vrf context with overlapping address across VRFs for source and / or group addresses  | |
| 22   |   Functionality    | Jumbo frames validation  | |
| 23   |   Functionality    | Verify PIM configurations using REST API commands  | |
| 24   |   Functionality    | Verify PIM show using REST API commands  | |
| 25   |   Functionality    | Maximum Number of multicast routes/pim group entries supported  | |
| 26   |   Functionality    | Verify that LHR node stops creating source tree for all the groups when spt-threshold infinity is set globally  | |
| 27   |   Functionality    | Verify that LHR node stops creating source tree for all the groups mentioned in prefix-list when spt-threshold infinity is set globally with prefix-list  | |
| 28   |   Functionality    | Verify that no first packet loss is seen with minimal multicast route entries when pim ecmp is configured  | |
           
      
# 11  Design expections from Broadcom
## 11.1 ACL and COPP requirements
An ACL to lift unknown multicast address is required to honor the source traffic. The qualifiers and the corresponding actions are listed below.

|    ACL                          | Qualifiers                      |   Action                     |
|---------------------------------|---------------------------------|------------------------------|
| Unknown IPv4 Multicast packets must be forwarded to the CPU through a dedicated separate CoPP Queue| PacketRes = Unknown Multicast packets Destination IP=224.0.0.0/4 |   (1) CosQCpuNew -QUEUE_ID_1>  (2) GpCopyToCpu |                      |                                 |                                 |                              |
## 11.2  IPMC entry deletion event

As explained above in the section 3.1.3, SAI shall execute a callback to notify the IPMC entries AGE and DONTAGE data. As part of the callback API definition, SAI provided data shall be posted to syncd notification processor thread. As part of syncd notification processor thread, data shall be validated and written to STATE_DB for further processing. Whenever an IPMC entry is getting deleted for any reason other than AGE out, AGE data for that particular IPMC entry should be cleaned up from STATE_DB if exists.

As AGE or DONTAGE data shall be added to STATE_DB in notification processor thread conetxt, deletion must be done from the same thread context to avoid inconsistencies in STATE_DB.

Hence, expection is that SAI shall also invoke a separate call back whenever an IPMC entry is deleted from NPU. As part of this callback API, data shall be posted to notification processor thread for removing AGE or DONTAGE data belongs to a particular IPMC entry from STATE_DB.

