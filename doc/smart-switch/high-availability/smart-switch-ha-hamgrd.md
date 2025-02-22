# 1. SmartSwitch High Availability Manager Daemon (HAMgrD) Design

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 2/22/2025 | Riff Jiang | Initial version |

- [1. Overview](#1-overview)
- [2. Key Actors](#2-key-actors)
- [3. HA Scope workflows](#3-ha-scope-workflows)
  - [3.1. DPU-Driven mode](#31-dpu-driven-mode)
  - [3.2. Switch-Driven mode](#32-switch-driven-mode)

## 1. Overview

The High Availability Manager Daemon (HAMgrD) is a core component that manages HA state machines and coordinates failover operations in SmartSwitch. Running in the HA container on the NPU side, its key responsibilities include:

1. **HA State Machine Management**: Drives state transitions and coordinates with peer instances.
2. **Traffic Control**: Programs BFD responders and manages traffic forwarding between NPU/DPUs.
3. **Configuration Management**: Processes SDN controller configs and pushes to NPU/DPUs.
4. **Monitoring and Reporting**: Monitors DPU health and reports HA states/events.
5. **Failure Handling**: Detects and handles failures, coordinates failover operations.

The daemon supports both DPU-driven mode (where it acts mainly as a config/monitoring agent) and NPU-driven mode (where it actively drives HA state machines). And this doc explains the detailed design of the daemon.

For more details, please refer to the [SmartSwitch High Availability HLD](./smart-switch-ha-hld.md) and [SmartSwitch High Availability Detailed Design](./smart-switch-ha-detailed-design.md).

## 2. Key Actors

To simplify the HAMgrD design, we leverage the concept of actor model and build a set of actors to handle different HA related operations. 

Each actors maps to a key concept in the HA design. And they will be communicating with each other via swbus local message bus and save the state in the state DB tables:

| Actor | Description | Actor Resource Path | State DB Table |
|-------|-------------|---------------------|-----------------|
| Global Config | Monitor global HA configurations. | `ha-global/config` | `DASH_HA_GLOBAL_CONFIG_STATE` |
| DPU | Monitor DPU configurations and acting on DPU state changes. | `dpu/<dpu-id>` | `DASH_HA_DPU_STATE:<dpu-id>` |
| VDPU | Monitor VDPU configurations and aggregate DPU state changes. | `vdpu/<vdpu-id>` | `DASH_HA_VDPU_STATE:<vdpu-id>` |
| HA Set | A set of NPUs/DPUs that are managed by the HAMgrD. | `ha-set/<ha-set-id>` | `DASH_HA_SET_STATE:<ha-set-id>` |
| HA Scope | The scope to drive the HA state machine, which can contain a single or multiple ENIs. | `ha-scope/<ha-scope-id>` | `DASH_HA_SCOPE_STATE:<ha-scope-id>` |

The data flow of all the actors inside hamgrd are shown as below:

![HAMgrD Actors](./images/hamgrd-actors.svg)

## 3. HA Scope workflows

### 3.1. DPU-Driven mode

### 3.2. Switch-Driven mode
