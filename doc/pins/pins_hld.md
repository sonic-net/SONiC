# PINS HLD

_Rev v0.1.1_

## Table of Contents

- [Revision](#revision)
- [Scope](#scope)
- [Definitions / Abbreviations](#definitions--abbreviations)
- [Overview](#overview)
  - [Open Source](#open-source)
  - [Opt-In Path Towards SDN](#opt-in-path-towards-sdn)
  - [Familiar Interface](#familiar-interface)
  - [Unambiguous Documentation](#unambiguous-documentation)
- [Requirements](#requirements)
- [Architecture](#architecture)
- [High-Level Design](#high-level-design)
  - [P4RT Application](#p4rt-application)
  - [P4 Programs & P4 Info](#p4-programs--p4-info)
    - [P4 Compiler and the P4 Info](#p4-compiler-and-the-p4-info)
  - [P4 APPL DB Tables](#p4-appl-db-tables)
  - [P4 Orchagent](#p4-orchagent)
  - [Application Level Responses](#application-level-responses)
  - [Packet IO](#packet-io)
    - [Receiving Packets (Packet Ins)](#receiving-packets-packet-ins)
    - [Transmitting Packet (Packet Outs)](#transmitting-packet-packet-outs)
- [Repositories](#repositories)
- [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
  - [CLI / YANG model Enhancements](#cli--yang-model-enhancements)
  - [Config DB Enhancements](#config-db-enhancements)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions / Limitations](#restrictions--limitations)
- [Testing Requirements / Design](#testing-requirements--design)
- [Open / Action items - if any](#open--action-items---if-any)
- [Supplementary Documents](#supplementary-documents)

<!--
  Initial markdown generated using Docs to Markdown plugin for Google Docs:
    https://workspace.google.com/marketplace/app/docs_to_markdown/700168918607

  Table of contents generated with VSCode extension, Markdown All in One:
    https://marketplace.visualstudio.com/items?itemName=yzhang.markdown-all-in-one

  If you don't have VSCode, table of contents can be generated with markdown-toc:
    http://ecotrust-canada.github.io/markdown-toc/
-->

## Revision

| Rev  | Rev Date   | Author(s)          | Change Description |
|------|------------|--------------------|--------------------|
| v0.1 | 06/24/2021 | Mythil Raman (Google), Waqar Mohsin (Google), Bhagat Janarthanan (Google), Reshma Sudarshan (Intel), Brian O’Connor (ONF)  | Initial version |
| v0.1.1 | 08/11/2021 | Bhagat Janarthanan (Google), Brian O’Connor (ONF) | Update based on feedback from Microsoft SONiC team |

## Scope

This document describes the high level design of PINS - P4 Integrated Network Stack. It provides a detailed explanation of the components that need to be added and modified in the SONiC framework to support a remote controller to program the forwarding tables.

## Definitions / Abbreviations

**P4**: Programming Protocol-independent Packet Processors (P4) is a domain-specific language for network devices, specifying how data plane devices (switches, NICs, routers, filters, etc.) process packets

**P4RT**: P4Runtime (P4RT) is a control plane specification for controlling the data plane elements of a device defined or described by a P4 program. The [latest version of the P4Runtime spec][p4rt-spec-ref] is available on the P4 website.

**PINS**: P4 Integrated Network Stack (PINS) is a project that provides additional components and changes to SONiC and allows the stack to be remotely controlled using P4 and P4RT.

**SAI**: Switch Abstraction Interface (SAI) is a standardized interface which allows programming and managing different switch ASICs in a vendor-independent fashion.

**SDN**: Software Defined Networking (SDN) is the practice of disaggregating the data, control, and management planes of networks, and implementing the control and management planes outside the switch.

## Overview

This document describes **PINS (P4 Integrated Network Stack)**, a P4RT based SDN interface for SONiC. P4RT for SONiC is opt-in, has familiar interfaces, enables rapid innovation, provides automated validation, and serves as unambiguous documentation.

A canonical family of P4 programs documents the packet forwarding pipeline of SAI. Remote SDN controllers will use these P4 programs to control the switch forwarding behavior over the P4RT API.

### Open Source

The family of P4 programs, the P4RT application server, the orchagent code to translate from P4RT to SAI, the validation framework, and any P4 compiler extensions will all be open sourced. The user and vendor specific aspects of a switch pipeline are cleanly separated into extension and configurable tables.

### Opt-In Path Towards SDN

The P4RT Application is completely opt-in. If the P4RT interface is not used, the remaining parts of SONiC will continue to work the way they do today. This new interface allows interested operators to gradually move towards SDN without needing a full-fledged SDN controller right from the start. It is possible to continue relying on SONiC-provided protocols for some aspects, and to start using P4RT for others.

### Familiar Interface

The family of P4 programs models the SAI forwarding pipeline, making the P4RT interface familiar to anyone who has worked with SONiC/SAI before. The P4RT interface provides  essential networking features (L2 bridging, L3 routing, ACLs, etc.) allowing users to quickly get up to speed on how to use this new API.

### Unambiguous Documentation

The SAI P4 programs will serve as an unambiguous documentation of the SAI pipeline. This will help to minimize differences between SAI implementation provided by various vendors, and serve as a reference for the community at large. The P4 program for L3 routing will be modeled after the SAI pipeline for L3. More details on the full SAI pipeline are available in the [SAI Pipeline Object Model][sai-model-ref].

## Requirements

The following components are targeted for the SONiC 2021-11 Release:

* P4RT application that runs in its own container,
* P4RT-Orchagent that runs as part of SWSS, and
* SAI P4 program.

These components will enable the following functionality:

* P4RT clients can use P4RT to program IP route entries, next hop members and groups, and ACL entries to drop or punt packets to the control plane.
* P4RT clients can program ACLs to punt packets received in the ingress pipeline. These packets will be punted to the P4RT application running in the switch and will be forwarded to the client over the P4RT gRPC channel.
* Users can introduce custom private extensions to the pipeline by adding other elements to the P4 program.

Additional functionality will be made available in future releases. Warmboot / fastboot capability will not be supported for the P4RT application in the first MVP release. Support will be added in subsequent releases. Warmboot / fastboot capabilities for other applications will continue to function as normal and will not be impacted by PINS.

For the first release, the P4RT application will be integrated using SONiC’s traditional, monolithic build, but we will explore moving the new application extension framework in a subsequent release.

## Architecture

SONiC is structured into various containers that communicate through multiple logical databases via a shared Redis instance. To add SDN support, PINS introduces a few new components into the SONiC system:

* P4RT: An application that receives P4 programming requests from the controller and programs the requests to the APPL DB.
* P4RT tables: a new APPL DB table that defines the P4 programming requests.
* P4Orch: A new orch that programs the P4RT table from APPL DB to ASIC DB. It also sends response notifications to P4RT and manages the APPL STATE DB.
* APPL STATE DB: A new DB for applications to query the system status. It has the same schema of the APPL DB.

![PINS Architecture Diagram][arch-img]
<!--
  PINS Architecture drawing source:
    https://docs.google.com/drawings/d/1Maxgf2-DyJHi_MpGbYLhgUWnfebJfFHYJPcB8NO_WVE/edit
-->

The P4RT application listens to a remote SDN controller and creates entries in the APPL and CONFIG databases. Following the SONiC architecture, the P4RT application writes its output to a new table in the APPL database. From there, the new P4Orch picks up the changes and writes the entries into the existing ASIC tables, where they get picked up by syncd. This path is highlighted in green in the PINS Architecture figure. The green path builds a parallel path in the orchagent as the current SWSS does not support (1) Response path - which is required by the P4RT application, (2) Ownership tags - which are required when there are more than one writer to the same table. Over the long term, once such features are supported by the SWSS, the green path can be merged with the existing tables.

The red path is used if a new table, match, or action is being added from the P4RT application into the ASIC DB when this table is not present in the SAI pipeline. More detailed information regarding the red path is provided in the supplementary document: [P4 Extensions for SAI][p4ext-hld].

## High-Level Design

The high level architecture can be broken down into a set of modules that interact and work together to provide the functionality.

![PINS Architecture Diagram][arch-full-img]
<!--
  PINS Architecture v2 drawing source:
    https://docs.google.com/drawings/d/1ICKeDqa0_WvQuwWbZ4J4CXcfQ1CowynTh_WgsjPWZ1U/edit
-->

### P4RT Application

The P4RT application runs in its own container and supports multiple gRPC client sessions. The application is responsible for parsing the requests from its clients, verifying them and writing the intent to the new P4 tables in APPL DB and notifying the clients of the eventual success/failure of the intent.  The P4RT application also supports read requests from its clients. The read requests provide clients with current state information of the switch. More detailed information regarding the P4RT application is provided in the supplementary document: [P4RT Application][p4rt-hld].

### P4 Programs & P4 Info

P4 is used in two ways: to describe the existing SAI pipeline and to extend it.

First, P4 can model the fixed and configurable elements of the existing SAI pipeline. The SAI P4 definition will serve as an unambiguous documentation of the SAI pipeline. This will help to minimize differences between SAI implementation provided by various vendors, and serve as a reference for the community at large.

The P4RT Application comes along with a canonical family of P4 programs (also open-source) that outline the packet forwarding pipeline of SAI. Remote SDN controllers will use these P4 programs to control the switch forwarding behavior over the P4RT API.

For existing SAI features, the vendor does not need to support P4 in any way. The P4 entities are mapped to existing SAI API objects that are passed to unmodified vendor SAI implementations. For fixed and configurable SAI features, PINS is designed to work on all of SONiC’s existing targets without modification to SAI.

Second, users can use P4 to define custom extensions to the SAI pipeline. For these extensions, vendors will need to either provide a P4 compiler to map them to their hardware target. Alternatively, the vendor can manually map these extensions to their SDK API in a similar manner to the existing SAI extension mechanism.

#### P4 Compiler and the P4 Info

The SAI pipeline is modeled as a P4 program which can be compiled using a [P4 compiler][p4c-repo]. The output of the compiler is a P4Info file with a description of the various tables and other objects in the P4 program; the P4Info comes from the compiler frontend and is not vendor specific. This is used by the P4RT Application, and it is pushed by the P4RT client on the initial connection to the switch. Assuming a switch vendor supports the SAI pipeline, nothing more is needed. Vendors supporting a P4 backend may use other outputs from the compiler.

![SAI P4 Pipeline][saip4-img]
<!--
  SAI Pipeline drawing source:
    https://docs.google.com/drawings/d/1pJYfH9KL7BmA1Pv8a2ImyV2Mp7cmv1w57Cjsi_iA8K4/edit
-->

Fixed SAI components are modeled after the [SAI Pipeline Object Model][sai-model-ref].

Yellow boxes represent the fixed components of the SAI pipeline. These will be the same in every P4 program. Blue boxes represent the configurable components of the SAI pipeline, namely Access Control Lists (ACLs). Every ACL follows the same basic schema, but can be customized for the use-case by changing the match fields and actions (subject to restrictions w.r.t. what SAI allows). Red boxes represent SAI extensions, that are provided by the vendor or network operators, and consumed by users through P4RT. Detailed information along with example use cases is provided in the supplementary documentation: [SAI P4 Program][saip4-hld] and [P4 Extensions for SAI][p4ext-hld].

The green path (i.e. SAI path) shown in the architecture diagram programs the tables corresponding to the yellow and blue boxes. The red path (i.e. SAI extension path) programs the tables corresponding to the red boxes.

### P4 APPL DB Tables

This is the interface between the P4RT app and the P4RT orch agent. The set of tables are collectively called the _P4RT Tables_.

In SONiC, the APPL DB contains high level details of the programming as compared to the ASIC DB tables. Unlike traditional SONiC applications, the SDN controller provides low level details and such a level of detailed programming is not supported by most of the existing APPL DB tables.

To overcome this limitation, the PINS architecture defines new APPL_DB tables that allow more detailed definitions. The P4RT application writes to these tables. The new tables are written by the P4RT application and consumed by the P4RT Orchagent.

Readability is an important criteria for SONiC DB tables. The new tables are no different in this respect and use consistent formatting. The new tables are named with the prefix P4RT to easily identify them as P4RT application tables.  The naming follows the convention of `P4RT:<TableType><TableName>` where TableType is either FIXED or configurable (only ACL for now) and TableName is the specific table in the SAI pipeline specification like router interface, neighbor, next hop, IPV4/IPV6 tables etc.

Detailed information regarding the schema of the tables and a set of guidelines for consistency are provided in the supplementary documentation: [P4RT APPL DB Schema][p4rt-db-hld].

### P4 Orchagent

The P4 Orchagent (P4Orch) processes the entries added to the new P4 tables in APPL DB by the P4RT application, parses and resolves them and then creates the necessary SAI objects and adds them as entries to ASIC DB. SAI objects created by the P4Orch could refer to SAI objects created by other orchagents. In these cases, the P4Orch will interact with the corresponding orchagents to reference those objects and increase reference counters where necessary. Detailed information regarding the operation of the P4Orch is provided in the supplementary document: [P4 Orchagent][p4orch-hld].

### Application Level Responses

PINS introduces the concept of application level responses. SONiC currently supports synchronous communication between the SWSS and Syncd containers. PINS extends synchronized communication to applications.

Most SDN controllers require an acknowledgement of success or failure for each programming request. Subsequent programming by the controller depends on the response. SDN controllers are intelligent and can adapt to failures quickly. If one of the switches encounters a failure, the controller can utilize the other switches to achieve its goals.

The controller requires state information from the switches to quickly identify any failures. This is accomplished by the addition of application level responses and state. More information regarding this is provided in the supplementary document: [APPL STATE DB and Response Path][appl-state-hld].

### Packet IO

There are multiple scenarios where the remote controller is interested in listening on the ingress pipeline of the switch for specific packets and getting those packets along with additional information. In certain other scenarios, the controller is interested in sending specific packets through the egress pipeline and requires the packet to be routed based on the rules already programmed in the switch.


#### Receiving Packets (Packet Ins)

P4RT clients can program ACLs to punt or copy packets received in the ingress pipeline. These packets will be trapped and sent to the P4RT application running in the switch and will be forwarded to the client over gRPC. 

P4RT clients require additional packet attributes, like the target egress port, which are not available via netdev. To support the above requirements, a model similar to the one used to add sFlow to SONiC is used. The packet receive path creates a genetlink type host interface. The P4RT application programs user defined traps for packets that are interesting to the controller and maps them to the genetlink host interface. A generic ASIC independent model is defined for passing parameters such as “target egress port” to the application container. 

#### Transmitting Packet (Packet Outs)

For packets that should be directly transmitted from a specific port, PINS uses the standard SONIC port netdevs. These packets will bypass ingress pipeline processing.

PINS also requires packet transmission based on the programming present in the ASIC. To support this feature, PINS introduces a new netdev (“send_to_ingress”) that will send packets through the ingress pipeline before they are transmitted.

A detailed description of the receive and transmit paths is present in the supplementary document: [Packet IO][packet-hld].

## Repositories

This design adds the following new repositories:

* P4RT Application <!-- FIXME(bocon): add URL when open -->

It also has modifications in the following existing SONiC repositories:

* [SWSS][swss-repo]
* [SWSS-Common][swss-common-repo]
* [SONiC Build Image][buildimage-repo]

## SAI API

PINS uses existing SAI features without any changes, included fixed functions (e.g. routing) and configurable ones (e.g. ACLs).

For programmable hardware targets, PINS introduces an additional SAI header, saip4ext.h, to map user-defined private P4 extensions to vendor SAI implementations. More details on saip4ext.h can be found in the supplemental document: [P4 Extensions for SAI][p4ext-hld].

## Configuration and management

### CLI / YANG model Enhancements

There are no CLI changes.

### Config DB Enhancements

There will be configuration entries to enable and disable PINS features. For example, writing the  responses to the APPL STATE DB will be controlled by a flag.

The first version of the P4RT application will use a default set of configuration, including gRPC listening port (tcp/9559) and transport security options. These are hardcoded, but can be changed by editing the P4RT application source code. In future releases, we will aim to model this configuration in Config DB using a similar approach as gNMI (sonic-telemetry).

## Warmboot and Fastboot Design Impact

When the P4RT application is not used, warm boot and fastboot will continue to operate as before. There will be no impact on existing warmboot and fastboot design.

When the P4RT application is used, the P4Orch needs to perform specific actions for successful warm boot and fast boot operation. These changes are being planned for the next phase (i.e. the next SONiC release). In the first MVP release, warmboot and fastboot features will not be supported for objects created through the P4RT application. This will not affect warm boot operations for objects created through other orchagents.

## Restrictions / Limitations

In the first MVP release, limited functionality and features will be supported through the P4RT application. The details of supported features are provided in the requirements section.

## Testing Requirements / Design

The entire PINS code, including the P4RT Application and P4Orch, is well unit tested. The coverage goal is at least 90% which is already achieved. Integration tests will be added in the following release.

## Open / Action items - if any

## Supplementary Documents

Here is the full list of supplementary HLD docs:

* [P4RT Application][p4rt-hld]
* [SAI P4 Program][saip4-hld]
* [P4 Extensions for SAI][p4ext-hld]
* [P4RT APPL DB Schema][p4rt-db-hld]
* [P4 Orchagent][p4orch-hld]
* [APPL STATE DB & Response Path][appl-state-hld]
* [Packet IO][packet-hld]

<!-------- LINK REFERENCES -------->

<!-- Supplementary HLD Links -->
<!-- FIXME(bocon): update links when ready -->
[p4rt-hld]: p4rt_app_hld.md
[saip4-hld]: in_progress.md
[p4ext-hld]: in_progress.md
[p4rt-db-hld]: in_progress.md
[p4orch-hld]: p4orch_hld.md
[appl-state-hld]: in_progress.md
[packet-hld]: in_progress.md

<!-- Repository Links -->
[buildimage-repo]: https://github.com/sonic-net/sonic-buildimage
[p4c-repo]: https://github.com/p4lang/p4c
[swss-repo]: https://github.com/sonic-net/sonic-swss
[swss-common-repo]: https://github.com/sonic-net/sonic-swss-common

<!-- Reference Links -->
[p4rt-spec-ref]: https://p4lang.github.io/p4runtime/spec/main/P4Runtime-Spec.html
[sai-model-ref]: https://github.com/opencomputeproject/SAI/blob/master/doc/object-model/pipeline_object_model.pdf

<!-- Image Links -->
[arch-img]: images/pins_arch.svg
[arch-full-img]: images/pins_arch_full.svg
[saip4-img]: images/sai_p4.svg
