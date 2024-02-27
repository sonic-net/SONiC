# SmartSwitch High Availability High Level Design - DPU-Driven-DPU-Scope setup

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 02/26/2024 | Riff Jiang | Initial version |

1. [1. Terminology](#1-terminology)
2. [2. Background](#2-background)
3. [3. DPU-Driven-DPU-Scope setup Overview](#3-dpu-driven-dpu-scope-setup-overview)
4. [4. Network Physical Topology](#4-network-physical-topology)
   1. [4.1. NPU to DPU traffic forwarding](#41-npu-to-dpu-traffic-forwarding)
   2. [4.2. DPU-level HA scope](#42-dpu-level-ha-scope)
5. [5. ENI programming with HA setup](#5-eni-programming-with-ha-setup)
6. [6. DPU liveness detection](#6-dpu-liveness-detection)
7. [7. HA state machine management](#7-ha-state-machine-management)
8. [8. Planned events and operations](#8-planned-events-and-operations)
9. [9. Unplanned events and operations](#9-unplanned-events-and-operations)
10. [10. Flow tracking and replication](#10-flow-tracking-and-replication)
11. [11. Detailed design](#11-detailed-design)
12. [12. Test Plan](#12-test-plan)

## 1. Terminology

| Term | Explanation |
| ---- | ----------- |

## 2. Background

This document adds and describes the high level design of `DPU-Driven-DPU-Scope` setup in SmartSwitch High Availability (HA), as an extension to our main SmartSwitch HA design document [here](../smart-switch-ha.md), which describes only how the ENI-level HA works (or how `NPU-Driven-ENI-Scope` setup works).

Many things in this setup will shares the same or very similar approach as the ENI-level HA, hence, this document will focus on the differences and new things that are specific to this setup.

## 3. DPU-Driven-DPU-Scope setup Overview

In SmartSwitch HA design, there are a few key characteristics that defines the high level behavior of HA:

- **HA pairing**: How the ENIs are placed amoung all DPUs to form the HA set?
- **HA owner**: Who drives the HA state machine on behalf of SDN controller?
- **HA scope**: At which level, the HA state machine is managed? This determines how the traffic is forwarded from NPU to DPU.
- **HA mode**: How the DPUs coordinate with each other to achieve HA?

From these characteristics, here is the main differences between `DPU-owner-DPU-scope` setup and the `NPU-Driven-ENI-Scope` setup in the main HLD:

| Characteristic | `DPU-Driven-DPU-Scope` setup | ENI-level HA setup |
| -------------- | ------------------------ | ------------ |
| HA pairing | Card-level pairing. | Card-level pairing. |
| HA owner | DPU drives the HA state machine. | `hamgrd` in NPU drives HA state machine. |
| HA scope | DPU-level HA scope. | ENI-level HA scope. |
| HA mode | Active-standby | Active-standby |

## 4. Network Physical Topology

The network physical topology for DPU-owner-DPU-scope setup is very similar to the ENI-level HA setup, with the main difference being the HA scope on DPU-level.

This results in the following differences in the network physical topology.

### 4.1. NPU to DPU traffic forwarding

### 4.2. DPU-level HA scope

## 5. ENI programming with HA setup

## 6. DPU liveness detection

## 7. HA state machine management

## 8. Planned events and operations

## 9. Unplanned events and operations

## 10. Flow tracking and replication

## 11. Detailed design

Please refer to the [detailed design doc](./smart-switch-ha-detailed-design.md) for DB schema, telemetry, SAI API and CLI design.

## 12. Test Plan

Please refer to HA test docs for detailed test bed setup and test case design.
