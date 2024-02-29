# SmartSwitch High Availability High Level Design - DPU-Driven-DPU-Scope setup

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 02/26/2024 | Riff Jiang | Initial version |

1. [1. Terminology](#1-terminology)
2. [2. Background](#2-background)
3. [3. DPU-Driven-DPU-Scope setup Overview](#3-dpu-driven-dpu-scope-setup-overview)
4. [4. Network Physical Topology](#4-network-physical-topology)
   1. [4.1. DPU-level HA scope](#41-dpu-level-ha-scope)
   2. [4.2. DPU-level NPU to DPU traffic forwarding](#42-dpu-level-npu-to-dpu-traffic-forwarding)
5. [5. ENI programming with HA setup](#5-eni-programming-with-ha-setup)
6. [6. DPU liveness detection](#6-dpu-liveness-detection)
   1. [6.1. Card level NPU-to-DPU liveness probe](#61-card-level-npu-to-dpu-liveness-probe)
   2. [6.2. DPU-to-DPU liveness probe](#62-dpu-to-dpu-liveness-probe)
7. [7. HA state machine management](#7-ha-state-machine-management)
   1. [7.1. HA state](#71-ha-state)
8. [8. Planned events and operations](#8-planned-events-and-operations)
   1. [8.1. Launch](#81-launch)
   2. [8.2. Planned switchover](#82-planned-switchover)
   3. [8.3. Planned shutdown](#83-planned-shutdown)
   4. [8.4. ENI migrawtion](#84-eni-migrawtion)
9. [9. Unplanned events and operations](#9-unplanned-events-and-operations)
   1. [9.1. Unplanned failover](#91-unplanned-failover)
10. [10. Flow tracking and replication](#10-flow-tracking-and-replication)
    1. [10.1. Inline flow tracking](#101-inline-flow-tracking)
    2. [10.2. Bulk sync](#102-bulk-sync)
11. [11. Detailed design](#11-detailed-design)
12. [12. Test Plan](#12-test-plan)

## 1. Terminology

| Term | Explanation |
| ---- | ----------- |
| HA | High Availability. |
| NPU | Network Processing Unit. |
| DPU | Data Processing Unit. |
| ENI | Elastic Network Interface. |
| SDN | Software Defined Network. |
| VIP | Virtual IP address. |

## 2. Background

This document adds and describes the high level design of `DPU-Driven-DPU-Scope` setup in SmartSwitch High Availability (HA), as an extension to our main SmartSwitch HA design document [here](../smart-switch-ha.md), which describes only how the ENI-level HA works (or how `NPU-Driven-ENI-Scope` setup works).

Many things in this setup will shares the same or very similar approach as the ENI-level HA, hence, this document will focus on the differences and new things that are specific to this setup.

## 3. DPU-Driven-DPU-Scope setup Overview

In SmartSwitch HA design, there are a few key characteristics that defines the high level behavior of HA:

- **HA pairing**: How the ENIs are placed amoung all DPUs to form the HA set?
- **HA owner**: Who drives the HA state machine on behalf of SDN controller?
- **HA scope**: At which level, the HA state machine is managed? This determines how the traffic is forwarded from NPU to DPU.
- **HA mode**: How the DPUs coordinate with each other to achieve HA?

From these characteristics, here is the main differences between `DPU-Driven-DPU-scope` setup and the `NPU-Driven-ENI-Scope` setup in the main HLD:

| Characteristic | `DPU-Driven-DPU-Scope` setup | ENI-level HA setup |
| -------------- | ------------------------ | ------------ |
| HA pairing | Card-level pairing. | Card-level pairing. |
| HA owner | DPU drives the HA state machine. | `hamgrd` in NPU drives HA state machine. |
| HA scope | DPU-level HA scope. | ENI-level HA scope. |
| HA mode | Active-standby | Active-standby |

## 4. Network Physical Topology

The network physical topology for `DPU-Driven-DPU-Scope` setup will be the same as the ENI-level HA setup, e.g. where the NPU/DPU is placed and wired. The  main difference being the HA scope on DPU-level.

This results in the following differences in the network physical topology and the figure below captures the essence of the differences:

![](./images/ha-scope-dpu-level.svg)

### 4.1. DPU-level HA scope

With the HA scoped moved from ENI-level to DPU-level, all ENIs on the active DPU will be treated as active and handles traffic, as the figure shows below:

### 4.2. DPU-level NPU to DPU traffic forwarding

With the DPU-level HA scope, the traffic forwarding from NPU to DPU will be done on DPU level:

- Each DPU pair will use a dedicated VIP for traffic forwarding from NPU to DPU.
- All VIPs for all DPUs in the SmartSwitch will be pre-programmed into the NPU and advertised to the network as a single VIP range (or subnet).
- NPU will setup a route to match the packet on the destination VIP, instead of ACLs to match both the VIP and inner MAC.

The data path and packet format will follow the same as the ENI-level HA setup [as described in the main HA design doc](./smart-switch-ha-hld.md#421-eni-level-npu-to-dpu-traffic-forwarding).

## 5. ENI programming with HA setup

The services and high level architecture that are used in the `DPU-Driven-DPU-Scope` setup will be the same as the ENI-level HA setup, such as, `hamgrd` and etc.

The high level workflow also follows the main HA design doc, more specifically:

- Before programming the ENIs, SDN controller creates the DPU pair by programming the HA set into all the NPUs that receives the traffic. `hamgrd` will get notified and call `swss` to setup all the traffic forwarding rules on NPU as well as send the DPU pair information to the DPU.
- After HA set is programmed, SDN controller can create the ENIs and program all the SDN policies for each ENI independently.

For more details on the contract and design, please refer to the detailed design section.

## 6. DPU liveness detection

In `DPU-Driven-DPU-Scope` setup, `hamgrd` will not drive the HA state machine and DPU will drive the HA at DPU level, hence we don't have the ENI-level traffic control, but the [Card level NPU-to-DPU liveness probe based on BFD](./smart-switch-ha-hld.md#61-card-level-npu-to-dpu-liveness-probe) and [DPU-to-DPU liveness probe](./smart-switch-ha-hld.md#63-dpu-to-dpu-liveness-probe) will still be used.

### 6.1. Card level NPU-to-DPU liveness probe

In `DPU-Driven-DPU-Scope` setup, the BFD probe will still be used for controlling the traffic forwarding behavior from NPU to DPU, and won't be used as the health signal for triggering any failover inside DPU.

Unlike the ENI-level HA setup, BFD probe can work alone to make the traffic forwarding decision without ENI level info. To achieve this, the SDN controller will program the HA set to NPU with the preferred DPU as active/standby setting.

Here is the how the probe works in details (with the DPU0 as preferred DPU):

| DPU0 | DPU1 | Preferred DPU | Next hop | Comment |
| --- | --- | --- | --- | --- |
| Down | Down | DPU0 | DPU0 | Both down is essentially the same as both up, hence effect is the same as Up+Up. |
| Down | Up | DPU0 | DPU1 | NPU will forward all traffic to DPU1, because DPU0 is not reachable. |
| Up | Down | DPU0 | DPU0 | NPU will forward all traffic to DPU0, since DPU0 is preferred and reachable. |
| Up | Up | DPU0 | DPU0 | If both DPU is up, then we respect the preferred DPU. |

### 6.2. DPU-to-DPU liveness probe

In `DPU-Driven-DPU-Scope` setup, the DPU-to-DPU liveness probe will still be used as health signal for triggering DPU failover.

However, unlike the ENI-level HA setup, upon DPU-to-DPU probe failure, DPU will drive the HA state machine and failover by itself, without the help of `hamgrd`.

## 7. HA state machine management

In `DPU-Driven-DPU-Scope` setup, the HA state machine will be managed by DPU itself, and `hamgrd` will not drive the HA state machine, but only be used for generating the configurations for NPU and DPU, as well as collecting the telemetry and report in the context of HA whenever is needed.

### 7.1. HA state

Although DPU will be driving the HA state machine transition, any HA state change will still needs to be reported.

With this setup, all HA states we defined for the ENI-level HA setup can be used to map the undering states, not only `Dead`, `Active`, `Standby` and `Standalone`.

For details on the states and the expected behavior, please refer to the [HA states defined in main HA design doc](./smart-switch-ha-hld.md#71-ha-state-definition-and-behavior).

## 8. Planned events and operations

### 8.1. Launch

### 8.2. Planned switchover

### 8.3. Planned shutdown

### 8.4. ENI migrawtion

## 9. Unplanned events and operations

### 9.1. Unplanned failover

## 10. Flow tracking and replication

### 10.1. Inline flow tracking

### 10.2. Bulk sync

## 11. Detailed design

Please refer to the [detailed design doc](./smart-switch-ha-detailed-design.md) for DB schema, telemetry, SAI API and CLI design.

## 12. Test Plan

Please refer to HA test docs for detailed test bed setup and test case design.
