# Feature Name
Deterministic Approach for Interface Link bring-up sequence on SFF compliant modules

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Abbreviation](#abbreviation)
  * [References](#references)
  * [Problem Definition](#problem-definition)
  * [Background](#background)
  * [Objective](#objective)
  * [Plan](#plan)
  * [Breakout handling](#breakout-handling)
  * [Feature enablement](#feature-enablement)
  * [Pre-requisite](#pre-requisite)
  * [Proposed Work-Flows](#proposed-work-flows)

# List of Tables
  * [Table 1: Definitions](#table-1-definitions)
  * [Table 2: References](#table-2-references)

# Revision
| Rev |     Date    |       Author                       | Change Description                  |
|:---:|:-----------:|:----------------------------------:|-------------------------------------|
| 0.1 | 07/12/2023  | Longyin Huang                      | Initial version                     |


# About this Manual
This is a high-level design document describing the need to have determinstic approach on SFF compliant modules for Interface link bring-up sequence and workflows for use-cases around it

# Abbreviation

# Table 1: Definitions
| **Term**       | **Definition**                                   |
| -------------- | ------------------------------------------------ |
| pmon           | Platform Monitoring Service                      |
| xcvr           | Transceiver                                      |
| xcvrd          | Transceiver Daemon                               |
| gbsyncd        | Gearbox (External PHY) docker container          |

# References

# Table 2 References

| **Document**                                            | **Location**  |
|---------------------------------------------------------|---------------|
| Deterministic Approach for Interface Link bring-up sequence for CMIS and SFF modules | [Interface-Link-bring-up-sequence.md](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md) |



# Problem Definition

1.	Presently in SONiC, for SFF compliant modules (100G/40G), there is no synchronization between enabling Tx of optical module and enabling ASIC (NPU/PHY) Tx which may cause link instability during administrative interface enable “config interface startup Ethernet” configuration and bootup scenarios. According to parent [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md#plan), potential problems are:
    - link stability issue which will be difficult to chase in the production network. e.g. If there is a PHY device in between, PHY may adapt to a bad signal or interface flaps may occur when the optics tx/rx enabled during PHY initialization.
    - there is a possibility of interface link flaps with non-quiescent optical modules <QSFP+/SFP28/SFP+>

2.  During administrative interface disable “config interface shutdown Ethernet”, only the ASIC(NPU) Tx is disabled and not the opticcal module Tx/laser.
      This will lead to power wastage and un-necessary fan power consumption to keep the module temperature in operating range

# Background

  Refer to parent [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md#background)

# Objective

According to parent [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md#objective), have a determistic approach for Interface link bring-up sequence for SFF compliant modules (100G/40G) i.e. below sequence to be followed:
  1. Initialize and enable NPU Tx and Rx path
  2. For system with 'External' PHY: Initialize and enable PHY Tx and Rx on both line and host sides; ensure host side link is up
  3. Then perform optics Tx enable

# Plan

Plan is to follow this high-level work-flow sequence to accomplish the Objective:
- Add a new thread SFF task manager (called sff_mgr) inside xcvrd to subscribe to existing field “host_tx_ready” in port table state-DB
- “host_tx_ready” is set to true only when admin_status is true and setting admin_status to syncd/gbsyncd is successful. (As part of setting admin_status to syncd/gbsyncd successfully, the NPU/PHY Tx is enabled/disabled)
- sff_mgr processes the “host_tx_ready” value change event and do optics Tx enable/disable using tx_disable API

# Breakout Handling

Refer to parent [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md#breakout-handling)

# Feature enablement

  This feature (optics Interface Link bring-up sequence) would be enabled on per platform basis.
  There could be cases where vendor(s)/platform(s) may take time to shift from existing codebase to the model (work-flows) described in this document.
- By default, sff_mgr feature is disabled.
- In order to enable sff_mgr feature, the platform would set ‘enable_xcvrd_sff_mgr’ to ‘true’ in their respective pmon_daemon_control.json. Xcvrd would parse ‘enable_xcvrd_sff_mgr’ and if found 'true', it would launch SFF task manager (sff_mgr).

# Pre-requisite

In addition to parent HLD's [pre-requisite](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md#pre-requisite),

> **_Pre-requisite for enabling sff_mgr:_**
Platform needs to leave the transceiver (if capable of disabling Tx) in Tx disabled state when an module inserted or during boot-up. This is to make sure the transceiver is not transmitting with Tx enabled before host_tx_ready is True.

# Proposed Work-Flows

  - ### Flow of pre-requisite for platform in insertion/bootup cases
  ```mermaid
  graph TD;
  A[platfrom brings module out of RESET]
  B[platform keeps module in Tx disabled state immediately after module out-of-RESET]
  C[xcvrd detects module insertion via platform API get_transceiver_change_event, and update module status/info to DB]
  D[Upon module insertion event, sff_mgr takes action accordingly if needed]

  Start --> A
  A --> B
  B --> C
  C --> D
  D --> End
  ```
  - ### Feature enablment flow -- how xcvrd spawns sff_mgr thread based on enable_sff_mgr flag
  ```mermaid
  graph TD;
  A[wait for PortConfigDone]
  B[check if enable_sff_mgr flag exists and is set to true]
  C[spawn sff_mgr]
  D[proceed to other thread spawning and tasks]

  Start --> A
  A --> B
  B -- true --> C
  C --> D
  B -- false --> D
  D --> End
  ```
  - ### Flow of calculating target tx_disable value:
      - When ```tx_disable value/status``` is ```True```, it means Tx is disabed
      - when ```tx_disable value/status``` is ```False```, it means Tx is enabled
  ```mermaid
  graph TD;

  A[check if both host_tx_ready is True AND admin_status is UP]
  B[target tx_disable value is set to False, Tx should be turned ON]
  C[target tx_disable value is set to True, Tx should be turned OFF]

  Start --> A
  A -- true --> B
  A -- false --> C
  B --> End
  C --> End
  ```
  - ### Main flow of sff_mgr, covering below cases:
      - system bootup
      - transceiver insertion
      - admin enable/disable configurations
  ```mermaid
  graph TD;
  A[subscribe to events]
  B[while task_stopping_event is not set]
  C[check insertion event, host_tx_ready change event and admin_status change event for each intended port]
  D[double check if module is present]
  E[fetch DB and update host_tx_ready value in local cahce, if not available locally]
  E2[fetch DB and update admin_status value in local cahce, if not available locally]
  F[calculate target tx_disable value based on host_tx_ready and admin_status]
  G[check if tx_disable status on module is already the target value]
  H[go ahead to enable/disable Tx based on the target tx_disable value]

  Start --> A
  A --> B
  B -- true --> C
  C -- if either event happened --> E
  C -- if neither event happened --> B
  E --> E2
  E2 --> D
  D -- true --> F
  D -- false --> B
  F --> G
  G -- true --> B
  G -- false --> H
  H --> B
  B -- false --> End
  ```

# Out of Scope
Refer to parent [HLD](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md)
