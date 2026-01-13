# SmartSwitch High Availability High Level Design - DPU-Scope-NPU-Driven setup

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 02/26/2024 | Changrong Wu | Initial version |

1. [1. Terminology](#1-terminology)
2. [2. Background](#2-background)
3. [3. NPU-driven HA State Machine Management](#3-npu-driven-ha-state-machine-management)
	1. [3.1 NPU-driven HA state transition](#31-npu-driven-ha-state-transition)
	2. [3.2 HA role activation](#32-ha-role-activation)
4. [4. DPU Health Signals](#4-dpu-health-signals)


## 1. Terminology

| Term | Explanation |
| ---- | ----------- |
| HA | High Availability. |
| NPU | Network Processing Unit. |
| DPU | Data Processing Unit. |
| SDN | Software Defined Network. |

## 2. Background

This document adds and describes the high level design of `DPU-Scope-NPU-Driven` setup in SmartSwitch High Availability (HA), as an extension to our main [SmartSwitch HA design document](../smart-switch-ha.md) and [DPU-Scope-DPU-Driven HLD](./smart-switch-ha-hld.md). This document will focus on the additional content that makes a difference.

## 3. NPU-driven HA State Machine Management

In NPU-driven HA, the state machine is managed by the HAmgrd running on NPU. So, the implementation of this state machine need to be transparent and vendor-independent. Hence, we intend to fully specify the HA state machine in this section.

### 3.1 NPU-driven HA state transition

The state transition graph for DPU-scope-NPU-driven HA is shown as below:

<p align="center"><img alt="HA state transition" src="./images/dpu-scope-npu-driven-ha-state-transition.svg"></p>

### 3.2 HA role activation

In [DPU-scope-DPU-driven HA design](./smart-switch-ha-dpu-scope-dpu-driven-setup.md#72-ha-role-activation), we have detailed why we need the approval from upstream services for activating `Active/Standby` and the addition of `PendingActive/Standby/StandaloneActivation`. In NPU-driven HA, the only difference is that the HAmgrd will send the requests to the SDN controller directly and drive the state machine transition upon approvals. The DPU only needs to react to the instructions from HAmgrd.

### 3.3 Atomicity of state transition

We intend to enforce no concurrency and preemption between state-transition events. This is achieved via the Actor model in [HAmgrd Design](./smart-switch-ha-hamgrd.md#2-key-actors)

## 4. DPU Health Signals

Although the state machine is driven by HAmgrd running on the NPU, the health signals that triggers the unplanned state machine transition are still expected to be driven by the DPU.
Specifically, we expect the DPU to perform the following two health monitoring mechanisms:
1. DPU-to-DPU liveness probing: The data path and packet format of the DPU-to-DPU probe will be the same as the one defined in the main HA design doc. Please refer to the [DPU-to-DPU data plane channel design](./smart-switch-ha-hld.md#4352-dpu-to-dpu-data-plane-channel). Upon detecting remote DPU failure events, the local DPU should notify the local HAmgrd via [DASH SAI event notification API](https://github.com/opencomputeproject/SAI/blob/master/experimental/saiswitchextensions.h). The health signal will be relected in `dp_channel_is_alive` field in `DASH_HA_SET_STATE` table of `STATE_DB` (per-DPU).
2. DPU self health check: The DPU should monitor the health of itself and try to report failures via pmon if it can. The health signals from PMON are reflected in the `DPU_STATE` table of `CHASSIS_STATE_DB` ([details](../pmon/smartswitch-pmon.md#2-dpu-state)).