# ALPINE High Level Design

## Table of Contents
## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations]
- [Overview]
- Requirements
- Architecture Design
- High-Level Design
  * Alpine Virtual Switch (AVS)
    + SwitchStack Container
    + ASIC Simulation Container
    + Ports
    + Why 2-containers?
  * Alpine KNE Deployment (AKD)
    + Nodes
    + Links
- SAI API
- Configuration and management
- Warmboot and Fastboot Design Impact
- Memory Consumption
- Restrictions/Limitations
- Testing Requirements/Design
- Open/Action items

## 1. Revision
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
|v0.1 |05/01/2019  |Padmanabhan Narayanan | Initial version
|v0.2 |05/20/2019  |Padmanabhan Narayanan | Updated based on internal review comments
|v0.3 |06/11/2019  |Padmanabhan Narayanan | Update CLIs, remove sflowcfgd
|v0.4 |06/17/2019  |Padmanabhan Narayanan | Add per-interface configurations, counter mode support and <br /> unit test cases. Remove genetlink CLI
|v0.5 |07/15/2019  |Padmanabhan Narayanan | Update CLI and DB schema based on comments from InMON : <br> Remove max-datagram-size from collector config <br/>Add CLI for counter polling interval <br/>Remvoe default header-size <br/>Add "all" interfaces option <br/> Separate CLI to set agent-id<br/>
|v1.0 |09/13/2019  |Sudharsan | Updating sequence diagram for various CLIs
|v1.1 |10/23/2019  |Padmanabhan Narayanan | Update SAI section to use SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME instead of ID. Note on genetlink creation. Change admin_state values to up/down instead of enable/disable to be consistent with management framework's sonic-common.yang.
|v1.2 |03/07/2021  | Garrick He | Add VRF support and fix interface admin-status output.
|v1.3 |01/24/2023  | Rajkumar (Marvell) | Add Egress Sflow support.

Initial version

Scope
This document captures the high-level design of an Alpine Virtual Switch (AVS). AVS is part of ALPINE - a switchstack simulation framework which also consists of a deployment model (AKD).
# ALPINE High Level Design

## Table of Contents
## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitions-abbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
  * [Alpine Virtual Switch](#alpine-virtual-switch)
    + [SwitchStack Container](#switchstack-container)
    + [ASIC Simulation Container](#asic-simulation-container)
    + [Ports](#ports)
    + [Why 2-containers](#why-2-containers)
  * [Alpine KNE Deployment](#alpine-kne-deployment)
    + [Nodes](#nodes)
    + [Links](#links)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Memory Consumption](#memory-consumption)
- [Restrictions/Limitations](#restrictions-limitations)
- [Testing Requirements/Design](#testing-requirements-design)
- [Open/Action items - if any](#open-action-items---if-any)

## 1. Revision
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
|v0.1 |05/01/2019  |Sonika Jindal | Initial version

## Scope
This document captures the high-level design of an Alpine Virtual Switch (ALViS). ALViS is part of ALPINE - a switchstack simulation framework which also consists of a deployment model (AKD).

## Definitions/Abbreviations

<table>
  <tr>
   <td><strong>ALViS</strong>
   </td>
   <td>Alpine Virtual Switch
   </td>
  </tr>
  <tr>
   <td><strong>AKD</strong>
   </td>
   <td>Alpine KNE Deployment
   </td>
  </tr>
  <tr>
   <td><strong>KNE</strong>
   </td>
   <td>Kubernetes Network Emulation
   </td>
  </tr>
    <tr>
   <td><strong>UPM</strong>
   </td>
   <td>Userspace Packet Module
   </td>
  </tr>
</table>

## Overview

ALPINE comprises a Virtual Switch (ALViS) and a Deployment Model (AKD). ALViS is a SONiC switch that comes with a virtualized ASIC to provide dataplane switch capabilities in software. ALViS supports plugging in other vendor implementations for virtual ASIC. This document describes the internals of the ALViS design and also discusses the deployment model used for ALViS. 

## Requirements

The current design covers the internals of an Alpine Virtual Switch and its unique features to cater to following requirements:
1. Pluggable software data path
    * For example, software pipeline, high performance pipeline, ASIC simulator
    * Support for forwarding and packet I/O
2. Flexible deployment from a single image
    * Allow users to select the “hardware” SKU at runtime
    * Consistent with SONiC images for hardware switches 
3. Identical application and orchestration software layers 
    * Leverage as much shared code as possible
4. Modest resource requirements
    * Deployable in a developer’s environment
    * Scalable in the cloud
