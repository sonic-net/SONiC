# SmartSwitch ENI Based Forwarding

## Table of Content ##

- [SmartSwitch ENI Based Forwarding](#smartswitch-eni-based-forwarding)
  - [Table of Content](#table-of-content)
  - [Revision](#revision)
  - [Scope](#scope)
  - [Definitions/Abbreviations](#definitionsabbreviations)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Architecture Design](#architecture-design)
    - [Programming ACL Rules](#programming-acl-rules)
        - [HA Active Mode](#ha-active-mode)
        - [HA Standy Mode](#ha-standby-mode)
    - [ACL Orchagent Design Changes](#acl-orchagent-design-changes)
    - [Configuration and management](#configuration-and-management)
  - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
  - [Memory Consumption](#memory-consumption)
  - [Restrictions/Limitations](#restrictionslimitations)
  - [Testing Requirements/Design](#testing-requirementsdesign)
    - [Unit Test cases](#unit-test-cases)
    - [System Test cases](#system-test-cases)
  - [Open/Action items - if any](#openaction-items---if-any)

## Revision ##

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 10/05/2024 | Vivek Reddy Karri | Initial version |

## Scope ##

This document provides a high-level design for Smart Switch ENI based Packet Forwarding using ACL rules

## Definitions/Abbreviations ##

| Term | Meaning                                                 |
| ---- | ------------------------------------------------------- |
| NPU  | Network Processing Unit                                 |
| DPU  | Data Processing Unit                                    |

## Overview ##

## Requirements ##

<p align="center"><img alt="Current ACL Orchagent Redirect Flow" src="./images/old_acl_redirect_flow.svg"></p>

<p align="center"><img alt="Proposed ACL Orchagent Redirect Flow" src="./images/new_acl_redirect_flow.svg"></p>