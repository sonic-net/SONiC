# ALPINE High Level Design

## Table of Contents
## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations]
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
