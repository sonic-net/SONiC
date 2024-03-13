##  SmartSwitch - NPU-DPU liveness detection using BFD


- [About this Manual](#about-this-manual)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [1. Requirements Overview](#1-requirements-overview)
  - [1.1 Functional Requirements](#11-functional-requirements)
  - [1.2 Scale Requirements](#12-scale-requirements)
  - [1.3 Default values](#13-default-values)
- [2. Modules Design](#2-modules-design)
  - [2.1 SmartSwitch NPU-DPU BFD sessions](#21-smartswitch-npu-dpu-bfd-sessions)
  - [2.2 BFD Active-Passive mode](#22-bfd-active-passive-mode)
  - [2.3 DPU FRR Changes](#23-dpu-frr-changes)
  - [2.4 DPU Linux IPTables](#24-dpu-linux-iptables)
  - [2.5 NPU BFD session and VNET\_ROUTE\_TUNNEL](#25-npu-bfd-session-and-vnet_route_tunnel)
  - [2.6 NPU-DPU midplane state change and BFD session update](#26-npu-dpu-midplane-state-change-and-bfd-session-update)
  - [2.7 VNET Route and BFD session updates](#27-vnet-route-and-bfd-session-updates)

###### Revision

| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 |  03/01/2024 |     Kumaresh Perumal  | Initial version                  |
| 0.2 |  03/12/2024 | Kumaresh Perumal | Update review comments                |

# About this Manual
This document provides general information about the NPU-DPU liveness detection using BFD probes between NPU and DPU.

# Definitions/Abbreviation

|                          |                                          |
|--------------------------|------------------------------------------|
| BFD                      | Bidirectional Forwarding Detection       |
| NPU                      | Network Processing Unit                  |
| DPU                      | Data Processing Unit                     |
| FRR                      | Open source routing stack                |

# 1. Requirements Overview

## 1.1 Functional Requirements

- BFD session(Active mode) in NPU using NPU's BFD H/W offload feature.

- BFD session(Passive mode) in DPU using FRR.

- BFD session between NPU and local DPU and remote DPU based on HA DPU
    pair.

## 1.2 Scale Requirements

- 64 BFD active sessions from NPU to each DPU in a T1 cluster.

- 8 BFD passive sessions from DPU to all NPUs in a T1 cluster.
  
Note: Scale requirements will  double when BFD sessions need to be created for both IPv4 and IPv6.

## 1.3 Default values

- BFD TX_INTERVAL -- 100 msec(might change)

- BFD_RX_INTERVAL - 100 msec(might change)

- BFD session detect time multiplier - 3

- BFD session type: Active on NPU and Passive on DPU

- BFD mode: Multihop mode for sessions between NPU and remote DPU

# 2. Modules Design

## 2.1 SmartSwitch NPU-DPU BFD sessions

In a Smartswitch deployment, BFD sessions are created between NPU and
DPUs. Each T1 cluster has 8 T1s and 8 DPUs in each T1. To detect the
liveness of each DPU in the cluster, NPU creates Active BFD sessions to
all 64 DPUs and each DPU creates passive BFD sessions to all NPUs in the
cluster. When BFD keepalives are not detected for certain interval, BFD
sessions are marked as down and corresponding action is performed.
Multihop BFD sessions are created between NPU and a remote DPU.

<img src="images/NPU_DPU_BFD_sessions.png">

## 2.2 BFD Active-Passive mode

HA manager in NPU creates VNET_ROUTE_TUNNEL_TABLE which in turn creates BFD Active session with local and peer information. NPU supports BFD hardware offload, so hardware starts
generating BFD packets to the peer. HA manager also creates
BFD_SESSION table in DPU with local DPU PA and peer NPU PAs. BfdOrch checks for SAI object platform capability for h/w offload. In DPU, if h/w offload is not supported, FRR is configured to trigger BFD sessions. BfdOrchagent creates BFD_SESSION entry in STATE_DB with 'passive' mode and BgpCfgd checks for the entries in the STATE_DB and configures BFD passive sessions in
FRR stack with local and peer information.

Trigger for HA manager to create BFD sessions will be detailed in HA HLD.

<img src="images/Dash_BFD_FRR.png">

BFD passive sessions in DPU waits for BFD control packets from NPU's
active session. When FRR stack receives BFD packets from active sessions
in NPU, it starts responding. After the initial handshake, BFD sessions
are up. When active session doesn't receive control packets for the
configured BFD timeout period, session is set to DOWN and corresponding
action is taken.

<img src="images/NPU_DPU_BFD_Exchange.png">

## 2.3 DPU FRR Changes

By default BFD Daemon is not enabled in FRR. FRR supervisor config file
has to be updated to start BFDD during FRR initialization.

To configure BFD passive sessions, a profile with 'passive' mode is
created and used for all sessions created in FRR. BgpCfgd configures FRR
stack using vtysh.

```

bfd

profile passive

passive-mode

receive-interval 100

transmit-interval 100

detect multiplier 3

exit

!

peer \<Local/Remote NPU IP\> local-address \<DPU PA\>

profile passive

exit
```

## 2.4 DPU Linux IPTables

New rules need to be added in the kernel to allow BFD packets to be
processed by the kernel and FRR stack. All packets matching BFD UDP(3784
and 4784).

***sudo iptables \--insert INPUT 5 -p udp \--dport 4784 -j ACCEPT***

***sudo iptables \--insert INPUT 5 -p udp \--dport 3784 -j ACCEPT***

These rules can be added as part of caclmgrd script during initialization by checking the DEVICE_METADATA object and attribute "switch_type: DPU" in CONFIG_DB.

## 2.5 NPU BFD session and VNET_ROUTE_TUNNEL

Overlay ECMP HLD describes how BFD session UP/Down changes the route to
VIP of a SDN appliance. In Overlay ECMP feature, all the nexthops are
VxLAN tunnel nexthops and the route to VIP is updated with primary or
secondary ECMP group based on the BFD session up/down state change. In
Smartswitch deployment, when a DPU VIP has nexthop local to
NPU, nexthop will be a regular IP nexthop instead of a VxLAN NH.

When HA manager receives HA config update, it will create VNET Route tunnel table and that triggers BFD session creation in NPU. These BFD sessions are hardware offloaded to NPU.

<img src="images/DB_And_Notification.png">

## 2.6 NPU-DPU midplane state change and BFD session update

When NPU-DPU midplane interface goes down due to some trigger or platform changes, PMON module updates the midplane NetDev interface state in DPU_STATE DB. HA manager listens to NetDev interface state in DPU_STATE DB and updates the NPU-DPU dataplane interface corresponding to that DPU. This will bring down the local and remote BFD sessions between NPU and DPU.

<img src="images/DPU_State_BFD_Changes.png">

## 2.7 VNET Route and BFD session updates
Some of the scenarios when VIP is pointing to Local and Remote nexthops
and the BFD session state changes between NPU and DPU. In the below
scenarios, local NH is the IP nexthop to local DPU and Remote NH is the
VxLAN tunnel nexthop to remote NPU.

```

+-------------------------+--------------+---------------+---------------+
|** VNET Route**          | **Primary**  | **BFD session | **Result**    |
|                         |              | update**      |               |
+=========================+==============+===============+===============+
| VIP: {Local NH, Remote  | Local NH     | Local NH UP   | VIP: Local NH |
| NH}.                    |              |               |               |
|                         |              | Remote NH UP  |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Local NH, Remote  | Local NH     | Local NH Down | VIP: Remote   |
| NH}                     |              |               | NH            |
|                         |              | Remote NH UP  |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Local NH, Remote  | Remote NH    | Local NH UP   | VIP: Remote   |
| NH}                     |              |               | NH            |
|                         |              | Remote NH UP  |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Local NH, Remote  | Remote NH    | Local NH UP   | VIP: Local NH |
| NH}                     |              |               |               |
|                         |              | Remote NH     |               |
|                         |              | Down          |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {local NH, Remote  | Local        | Local NH Down | VIP:Primary NH|
| NH}                     | /Remote NH   |               |               |
|                         |              | Remote NH     |               |
|                         |              | Down          |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Remote NH1,       | Remote NH1   | Remote NH1 UP | VIP: Remote   |
| Remote NH2}             |              |               | NH1           |
|                         |              | Remote NH2 UP |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Remote NH1,       | Remote NH1   | Remote NH1    | VIP: Remote   |
| Remote NH2}             |              | DOWN          | NH2           |
|                         |              |               |               |
|                         |              | Remote NH2 UP |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Remote NH1,       | Remote NH2   | Remote NH1 UP | VIP: Remote   |
| Remote NH2}             |              |               | NH2           |
|                         |              | Remote NH2 UP |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Remote NH1,       | Remote NH2   | Remote NH1 UP | VIP: Remote   |
| Remote NH2}             |              |               | NH1           |
|                         |              | Remote NH2    |               |
|                         |              | Down          |               |
+-------------------------+--------------+---------------+---------------+
| VIP: {Remote NH1,       | Remote       | Remote NH1    | VIP:Primary NH|
| Remote NH2}             | NH1/NH2      | Down          |               |
|                         |              |               |               |
|                         |              | Remote NH2    |               |
|                         |              | Down          |               |
+-------------------------+--------------+---------------+---------------+

```
