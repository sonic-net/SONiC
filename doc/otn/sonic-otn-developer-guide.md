# SONiC OTN HLD and Developer Guide

This document provides an HLD for developing a NOS for optical devices based on SONiC. Its description is based on the code base developed by the [SONiC OTN Working Group](https://lists.sonicfoundation.dev/g/sonic-wg-otn). This document can also serve as a developer guideline for anyone interested in developing a SONiC-based optical NOS. It should also be useful for new sonic-otn participants to understand the sonic-otn project in detail.
- Code base of ongoing prototype of [OTN kvm](https://github.com/sonic-otn/sonic-buildimage/tree/202411_otn).
- The build and run instructions for OTN kvm are described in the [README.md](https://github.com/sonic-otn/sonic-buildimage/blob/202411_otn/platform/otn-kvm/README.md).

## Table of Contents

- [SONiC OTN Developer Guide](#sonic-otn-hld-and-developer-guide)
  - [Table of Contents](#table-of-contents)
  - [1 Revision](#1-revision)
  - [2 Scope](#2-scope)
  - [3 Definitions/Abbreviations](#3-definitionsabbreviations)
    - [Table 1: Abbreviations](#table-1-abbreviations)
  - [4. Overview](#4-overview)
    - [4.1 OTN device and components overview](#41-otn-device-and-components-overview)
    - [4.2 Why SONiC for OTN](#42-why-sonic-for-otn)
  - [5 Requirements](#5-requirements)
    - [5.1 Functional requirements](#51-functional-requirements)
    - [5.2 Scaling requirements](#52-scaling-requirements)
    - [5.3 Event and Alarm](#53-event-and-alarm)
    - [5.4 PM Counter](#54-pm-counter)
    - [5.5 Telemetry](#55-telemetry)
  - [6 Architecture Design](#6-architecture-design)
    - [6.1 Design Principles](#61-design-principles)
    - [6.2 SONiC Extension Points for OTN Support](#62-sonic-extension-points-for-otn-support)
  - [7. SAI API](#7-sai-api)
    - [7.1 Functional Scope of SAI for OTN Device](#71-functional-scope-of-sai-for-otn-device)
    - [7.2 SAI Experimental Extension Mechanism](#72-sai-experimental-extension-mechanism)
    - [7.3 OTN Extension To SAI](#73-otn-extension-to-sai)
  - [8 SONiC Container Extension for OTN](#8-sonic-container-extension-for-otn)
    - [8.1 OTN Device Metadata](#81-otn-device-metadata)
    - [8.2 SWSS Extension for OTN Optical Features](#82-swss-extension-for-otn-optical-features)
      - [8.2.1 SWSS Config Manager](#821-swss-config-manager)
      - [8.2.2 SWSS orchagent](#822-swss-orchagent)
      - [8.2.3 OrchAgent Super Class (***Common code optimization***)](#823-orchagent-super-class-common-code-optimization)
    - [8.3 OTN State DB Update](#83-otn-state-db-update)
      - [8.3.1 SONiC SWSS Redis plug-in script](#831-sonic-swss-redis-plug-in-script)
      - [8.3.2 State DB update](#832-state-db-update)
      - [8.3.3 Device specific lua scripts (***Common code optimization***)](#833-device-specific-lua-scripts-common-code-optimization)
    - [8.4 SyncD Extension](#84-syncd-extension)
      - [8.4.1 FlexCounter Extension](#841-flexcounter-extension)
      - [8.4.2 OTN Gauged Value Modeling](#842-otn-gauged-value-modeling)
    - [8.5 PMON](#85-pmon)
      - [8.5.1 PMON Base Class](#851-pmon-base-class)
      - [8.5.2  Device specific platform config and driver](#852-device-specific-platform-config-and-driver)
      - [8.5.3 Linecard Hot-pluggable (***Feature enhancement***)](#853-linecard-hot-pluggable-feature-enhancement)
      - [8.5.4 Firmware Upgrade](#854-firmware-upgrade)
    - [8.6 SONiC host containers](#86-sonic-host-containers)
  - [9. Device Configuration and Management](#9-device-configuration-and-management)
    - [9.1. Manifest (if the feature is an Application Extension)](#91-manifest-if-the-feature-is-an-application-extension)
    - [9.2. OTN YANG Model](#92-otn-yang-model)
      - [9.2.1 OpenConfig Optical Transport Yang Model](#921-openconfig-optical-transport-yang-model)
      - [9.2.2 Generic Translation and Mapping](#922-generic-translation-and-mapping)
      - [9.2.3 REST](#923-rest)
      - [9.2.4 gNMI and Telemetry](#924-gnmi-and-telemetry)
      - [9.2.5 CLI Auto Generation for OTN (***Feature enhancement***)](#925-cli-auto-generation-for-otn-feature-enhancement)
    - [9.3. Config and State DB Schema For OTN](#93-config-and-state-db-schema-for-otn)
    - [9.4 Event and Alarm Support](#94-event-and-alarm-support)
      - [9.4.1 SONiC Notification](#941-sonic-notification)
      - [9.4.2  Notification Extension for OTN](#942-notification-extension-for-otn)
      - [9.4.3 OTN Notification Definition and NBI](#943-otn-notification-definition-and-nbi)
    - [9.5 OTN PM Statistics Support (***New feature***)](#95-otn-pm-statistics-support-new-feature)
      - [9.5.1 PM Design Objective:](#951-pm-design-objective)
      - [9.5.2 Design Proposal](#952-design-proposal)
    - [9.6 Reuse SONiC Existing Features](#96-reuse-sonic-existing-features)
      - [9.6.1 Management and Loopback Interface](#961-management-and-loopback-interface)
      - [9.6.2 TACACS+ AAA](#962-tacacs-aaa)
      - [9.6.3 Syslog](#963-syslog)
      - [9.6.4 NTP](#964-ntp)
      - [9.6.5 SONiC upgrade](#965-sonic-upgrade)
  - [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
  - [11. Memory Consumption](#11-memory-consumption)
  - [12. Restrictions/Limitations](#12-restrictionslimitations)
  - [13. Testing Requirements/Design  (**TBD**)](#13-testing-requirementsdesign-tbd)
    - [13.1. Unit Test cases](#131-unit-test-cases)
    - [13.2. System Test cases](#132-system-test-cases)
  - [14. Open/Action items - if any](#14-openaction-items-if-any)
    - [14.1 Asynchronous Config Validation](#141-asynchronous-config-validation)
    - [14.2 Threshold Management  (**TBD**)](#142-threshold-management-tbd)

## 1 Revision

|  Rev  |    Date    |       Author        | Change Description                        |
| :---: | :--------: | :-----------------: | :---------------------------------------- |
|  0.1  | 02/20/2026 |[sonic-otn-wp](https://lists.sonicfoundation.dev/g/sonic-wg-otn): Alibaba, Microsoft, Molex, Nokia, Cisco and Accelink.   | Initial version |


## 2 Scope

This document describes the architecture and high level design for extending SONiC to support optical transport network (OTN) device.

## 3 Definitions/Abbreviations

### Table 1: Abbreviations

|       |                                                    |
| ----- | --------------------------------------------------- |
|OTN   | Optical Transport Network         |
|NOS   | Network operating system           |
|SA    | Service affect     |
|NSA   | Non service affect    |
|PM    | Performance management   |
|CRUD  | CREATE, READ, UPDATE and DELETE |
|OA    | Optical Amplifier |
|OSC   | Optical Supervisory Channel |
|OLP   | Optical Line Protection |
|VOA   | Variable Optical Attenuator |
|WSS   | Wavelength Selective Switch |
|DGE   | Dynamic Gain Equalization |
|OTDR  | Optical Time Domain Reflectometer |
|DCI   | Data center interconnect  |


### 4. Overview
OTN devices are deployed for Data Center Interconnects (DCIs), serving as the optical transport layer that connects the ports of switches and routers between geographically dispersed data centers. This enables high-speed, low-latency, and reliable optical connections across long distances. 

#### 4.1 OTN device and components overview
OTN devices typically employ 1RU or 2RU chassis housing multiple optical line cards, fans, power supply units (PSUs), and control modules. Most optical line cards are pluggable and support diverse functions.

<img src="../../images/otn/otn-device-overview.png" alt="otn device overview" style="zoom: 35%;" />

These optical linecards are built on a common set of optical component units that provide core transmission functionalities:

* **Variable Optical Attenuator (VOA)** – Adjusts optical signal power levels.
* **Optical Amplifier (OA)** – Boosts optical signals to extend transmission distance.
* **Optical Line Protection (OLP) Switch** – Automatically switches traffic to a backup path when a fault occurs.
* **Optical Supervisory Channel (OSC)** – Transports management and control information.
* **Wavelength Selective Switch (WSS)** – Dynamically routes specific wavelengths in different directions.
* **Optical Channel Monitor (OCM)** – Analyzes the optical spectrum.
* **Optical Time-Domain Reflectometer (OTDR)** – Measures attenuation and reflection losses along fibers.
* **Transponders and Transceivers** – Convert electrical signals into optical signals for fiber transmission.

#### 4.2 Why SONiC for OTN
The **SONiC for OTN project** proposes extending SONiC to support optical transport networks, enabling end-to-end deployment across both packet and optical layers. 

For hyperscale network users and service providers, introducing optical support in SONiC enables consistent end-to-end infrastructure management from the IP layer (switches and routers) to the optical transport layer (OTN devices). This significantly simplifies network management tools and controllers. It also creates the potential for a single SDN controller infrastructure across all layers and enables movement toward an open, converged multi-layer network management solution.

For optical device vendors, existing SONiC NOS infrastructure and generic features, such as user management, security, and management network modules, can be reused. This reduces time to market, improves software quality, and lowers development costs. Joining the SONiC ecosystem also allows vendors and users to collaborate more effectively through the SONiC open-source community.

<img src="../../images/otn/sonic-otn-transponder-open-line-system.png" alt="transponder and open line system with sonic-otn" style="zoom: 35%;" />

<img src="../../images/otn/sonic-otn-packet-optical-system.png" alt="packet optical and open line system with sonic-otn" style="zoom: 35%;" />

This document provides a high-level design for extending SONiC to support OTN devices, including YANG models, SAI APIs, orchestration agent changes, syncd updates, Config DB and APP DB schemas, and other SONiC changes required to bring up a SONiC image on an OTN device.

## 5 Requirements

### 5.1 Functional requirements

At a high level the following should be supported:

- Bring up SONiC image for a new platform, `otn-kvm`, and DEVICE_METADATA type - `OtnOls`
- Bring up swss/syncd containers for switch_type - `otn`
- Able to manage OTN device configured via REST, gNMI client and CLI
- Device Management functions including:
  - Configuration - system (network, ntp, syslog), OTN optical modules.
  - State report - system, OTN optical modules.
  - Chassis management
     - Supervisor card, line card, power module, fan, manufacturing info
     - Operations: restart (warm, cold and power-on), SW/FW upgrade
  - Telemetry: Data streaming for time sensitive state.
  - Alarm notification for system faults.
  - PM statistics counters for important performance parameters.

### 5.2 Scaling requirements

Following are the scaling requirements: [*TBD*]

| Item                          | Expected Max value            |
| ----------------------------- | ----------------------------- |
| Line Cards                    | 16                            |
| Optical Ports                 | 64                            |

### 5.3 Event and Alarm

Alarms listed in the following table should be supported: **[TBD]**

| Alarm name                          | Severity                |  
| ----------------------------- |-----------------------------------|
| OA Loss of Signal                | SA                         |
| PUS Failed                    | NAS        |

### 5.4 PM Counter

Network equipment performance management counters are metrics that monitor and provide insights into the performance of network devices. They help identify potential issues, bottlenecks, and areas for optimization, enabling network administrators to proactively manage and troubleshoot their infrastructure:

For each PM parameter, the following statistics should be available:

- 96 (32) buckets of 15-minute counters including min, max and average.
- 7 bucket of 24-hour counters with min, max and average.

PM parameters listed in the following table should be supported: **[TBD]**

| PM name                          | Data Type                |  
| ----------------------------- |-----------------------------------|
| Chassis Temperature                   | decimal2                         |
| OA1-1 Input Power                | decimal2        |
| Fan-0 Speed                     | uint32        |

### 5.5 Telemetry

OTN should support telemetry features. Both [dial-in](https://github.com/sonic-net/sonic-telemetry/blob/master/doc/grpc_telemetry.md) and [dial-out](https://github.com/sonic-net/sonic-telemetry/blob/master/doc/dialout.md) modes should be supported. Telemetry should support the following features:

- STREAM (Streaming Telemetry): Continuously sends updates as data changes. It includes three sub-modes:
   - ON_CHANGE: Sends updates only when the value of the data changes.
   - SAMPLE (Cadence-based): Sends data at a configured periodic interval.

- ONCE: Retrieves the current state of data exactly once and then terminates the subscription.
- POLL: The collector sends a request, and the target sends the current value in response, allowing on-demand data retrieval

Telemetry subscribe path should support wildcard key for convenient filter for NBI client.

## 6 Architecture Design

This section describes the overall changes needed for supporting OTN devices.

### 6.1 Design Principles

While SONiC is a packet-switch NOS, its modular design and built-in extensibility infrastructure allow developers to add functionality beyond the packet-switching domain.

The following guidelines should be followed while developing a SONiC-based NOS for OTN.

- Fully utilize SONiC's rich extension mechanisms to make changes as seamless as possible, so OTN support becomes an organic part of SONiC.

- Reuse SONiC generic system features as-is, including NBI (REST, CLI, gNMI), telemetry, user management, syslog notifications, SW/FW upgrade, and chassis/PSU/LED/FAN/temperature management.

- Changes for OTN support should be modular and relatively isolated from packet-switching logic, with minimal impact on existing packet-switching functions.

- For major feature gaps, such as PM, alarms, and hot-plug support, enhancements should be designed and implemented generically, not only for OTN.

- All changes should be compatible with the upstream SONiC codebase and ready to merge. The final goal is for all OTN vendors to pull official SONiC code and build SONiC OTN images for their devices.

### 6.2 SONiC Extension Points for OTN Support

The following diagram shows the main changes and SONiC extension points required to support OTN devices:

  <img src="./images/otn-extension.png" alt="OTN Extension" width="700">

1. NBI: Add OTN yang models and support REST API and CLI. OpenConfig [optical transport yang model](https://github.com/openconfig/public/tree/master/release/models/optical-transport) is adopted. 

2. Redis DB: Add new CONFIG, STATE and APP tables for OTN device.

3. SWSS: Add Config manager and Orchagent for OTN device.

4. PMON Drivers: Add user and kernel drivers for Fan, PSU, LED and temperature sensors, FPGA.

5. SAI: Extend SAI to support OTN using SAI experimental extension mechanism.

6. SyncD: SyncD driver supporting extended OTN SAI attributes.

7. Optical Control: Introduce a new application container, optical-control, contains multiple daemons for span and wavelength control loop.

8. ONIE: Create ONIE image for installing SONiC image on OTN devices, support secure boot.

## 7. SAI API

This section covers the changes made or new API added in SAI API for implementing this feature.

In SONiC architecture, SAI (Switch Abstraction Interface) is a core interface layer that decouples SONiC control software from vendor-specific hardware implementations. Upper-layer SONiC components (such as Orchagent via the sairedis/syncd path) use standardized SAI object models and APIs, while each vendor provides its own SAI implementation to map those APIs to device SDK/driver operations.

By using SAI as the hardware abstraction boundary, SONiC can keep most control-plane logic hardware-agnostic, improve portability across different platforms, and reduce vendor-specific changes in the SONiC core.

### 7.1 Functional Scope of SAI for OTN Device

Following the existing SONiC design, SAI is extended to support optical features while generic system functionality remains in the PMON container. This functional division is shown in the following diagram:


```mermaid
%%{init: {'flowchart': {'nodeSpacing': 12, 'rankSpacing': 8}, 'themeVariables': {'fontSize': '11px', 'fontFamily': 'sans-serif'}}}%%
flowchart LR
    subgraph LEFT["Equipment Management"]
        direction TB
        em_bullets["Chassis, PSU, Fan, LED, SFP, Module(SC/LC), Components(BIOS, FPGA, CPLD, OA, OCM, OPS, OTDR), Inventory, Admin-status, restart, SW/FW upgrade, hot-pluggable"]
        subgraph PMON["PMON container"]
            direction TB
            daemon(("daemon"))
            python_base["Python Base Class"]
            platform_drivers["Platform drivers · libotn"]
            daemon --> python_base
            python_base <--> platform_drivers
        end
        em_bullets --- PMON
    end

    separator[" "]
    style separator fill:none,stroke:#0066cc,stroke-width:3px

    subgraph RIGHT["Optical Function"]
        direction TB
        of_bullets["AMP gain/tilt, OVA attenuation, OCM channel power, OTDR scan/SOR, WSS median-channel, OTN channels and interface"]
        subgraph SYNCD["syncd container"]
            direction TB
            syncd(("syncd"))
            sai_api["SAI API"]
            vendor_sai["Vendor SAI · libsaiotn"]
            hal_driver(["HAL driver · libhal-otn"])
            syncd --> sai_api
            sai_api --> vendor_sai
            vendor_sai --> hal_driver
        end
        of_bullets --- SYNCD
    end

    LEFT --- separator --- RIGHT

    style em_bullets fill:#e1bee7,stroke:#7b1fa2
    style of_bullets fill:#e1bee7,stroke:#7b1fa2
    style python_base fill:#b3d9ff,stroke:#0066cc
    style sai_api fill:#b3d9ff,stroke:#0066cc
    style platform_drivers fill:#ffcc99,stroke:#cc6600
    style vendor_sai fill:#ffcc99,stroke:#cc6600
    style hal_driver fill:#ffcc99,stroke:#cc6600
    style PMON stroke:#0066cc,stroke-dasharray: 5 5
    style SYNCD stroke:#0066cc,stroke-dasharray: 5 5
```

Most OTN devices are chassis-based with control cards and line cards. PMON will be enhanced to support the line card hot-pluggable feature described below.

### 7.2 SAI Experimental Extension Mechanism

While SAI APIs support core packet-switching features, they also include built-in extension mechanisms that allow developers to add new objects and APIs. Here is the [SAI experimental extension design](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-Extensions.md). The SAI extension mechanism provides:

- Add new attributes, e.g., add new attributes in saiswitchextensions.h.
- Add new API types in saiextension.h.
- Add new object types in saitypesextensions.h.
- Cannot modify existing SAI.
- Add new attributes for the new APIs (e.g., in experimental headers).

### 7.3 OTN Extension To SAI

The SAI extension for OTN devices is proposed [here](./sai_otn_proposal.md).

## 8 SONiC Container Extension for OTN

This section describes changes at SONiC container level to support OTN devices.

### 8.1 OTN Device Metadata and Simulator

In the DEVICE metadata table, a new type, `OtnOls`, and a new `switch_type`, `otn`, are added:

``` JSON
"DEVICE_METADATA": {
    "localhost": {
        "type": "OtnOls",
        "switch_type": "otn",
     }
}
```

Before vendors are adopting real optical device using sonic-otn NOS, a sonic-otn device simulator is developed for feature develop and testing purpose. It serves a vendor neutral platform for collaboration among sonic-otn as an open source project. 
- A new platform is created for [otn-kvm](https://github.com/sonic-otn/sonic-buildimage/tree/202411_otn/platform/otn-kvm) include all platform specific artifacts (config, build rules and SAI driver code).
- A [new otn device](https://github.com/sonic-otn/sonic-buildimage/tree/202411_otn/device/molex/x86_64-otn-kvm_x86_64-r0) belong to otn-kvm is also created for device specific artifacts. More virtual OTN devices can be add for otm-kvm platform.
- An open source SAI driver simulator is in a [separate repository]((https://github.com/sonic-otn/sonic-otn-libs/tree/main)). Simulator's Debian package will be release vi github release mechanism. An example [here](https://github.com/sonic-otn/sonic-otn-libs/releases/tag/v1.1.0). This follows the same practice that all sonic SAI drivers from different vendors are not part of the SONiC code base. At build time, target platform's SAI driver as a Debian package will be pulled into the SONiC image.

### 8.2 SWSS Extension for OTN Optical Features

Two SONiC built-in containers, swss and syncd, are at the core of data-path control and monitoring, as shown in the following diagram:

<img src="./images/swss-syncd.png" alt="swss and syncd" width="700">

This section describes how SWSS and Syncd support OTN features.

#### 8.2.1 SWSS Config Manager

In the SWSS container, a new config manager daemon, [`otnmgrd`](https://github.com/sonic-otn/sonic-swss/blob/202411_otn/cfgmgr/otnmgrd.cpp), is created to subscribe to changes in OTN tables in the config DB. When a config change is notified, the OTN config manager updates the corresponding tables in APP DB.

#### 8.2.2 SWSS orchagent

Orchagent is extended with a [separate folder](https://github.com/sonic-otn/sonic-swss/tree/202411_otn/orchagent/otn) to support OTN devices.

***Switch Object and SAI initialization***

`switch` is the root object for all other SAI objects and must be created during initialization. OrchAgent initializes SAI objects based on switch type. SAI initialization is split by switch type: OTN uses the OTN API, while everything else uses the standard SAI API:
- OTN: initOtnApi().
- Non-OTN: existing initSaiApi().

```c++
main.cpp

    if (gMySwitchType == SWITCH_TYPE_OTN) {
        SWSS_LOG_NOTICE("OTN platform detected, initializing OTN API");
        initOtnApi();
    } else {
        initSaiApi();
    }
```

***OrchDaemon for OTN***

Currently, SONiC supports two types of Orch Daemon based on `switchType`: orchDaemon and fabricOrchDaemon. A new type, OTNOrchDaemon, is added to support OTN devices. At runtime, `switchType == otn` is used to determine whether [OtnOrchDaemon](https://github.com/sonic-otn/sonic-swss/blob/202411_otn/orchagent/otn/otnorchdaemon.cpp) should be created. Please see the [code here](https://github.com/sonic-otn/sonic-swss/blob/202411_otn/orchagent/main.cpp).

``` c++
    if(gMySwitchType == "otn")
    {
        orchDaemon = make_shared<OtnOrchDaemon>;
    }
    else if (switchType != "fabric")
    {
        orchDaemon = make_shared<OrchDaemon>();
    }
    else
    {
        orchDaemon = make_shared<FabricOrchDaemon>();
    }
```

Creating a new type of OrchDaemon isolates OTN support from the existing logic, resulting in no impact on existing packet features.

#### 8.2.3 OrchAgent Super Class (***Common code optimization***)

OrchAgent performs CRUD operations on SAI objects triggered by APP DB changes. Currently, each SONiC object has its own OrchAgent class, which hard-codes APP DB Redis string object-to-SAI attribute mapping in a static table.
Example here in [oprtsorch.cpp](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp).

```c
static map<string, sai_bridge_port_fdb_learning_mode_t> learn_mode_map =
{
    { "drop",  SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DROP },
    { "disable", SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE },
    { "hardware", SAI_BRIDGE_PORT_FDB_LEARNING_MODE_HW },
    { "cpu_trap", SAI_BRIDGE_PORT_FDB_LEARNING_MODE_CPU_TRAP},
    { "cpu_log", SAI_BRIDGE_PORT_FDB_LEARNING_MODE_CPU_LOG},
    { "notification", SAI_BRIDGE_PORT_FDB_LEARNING_MODE_FDB_NOTIFICATION}
};
```

For OTN devices, a generic superclass, [objectorch](https://github.com/sonic-otn/sonic-swss/blob/202411_otn/orchagent/otn/objectorch.cpp), is defined to support CRUD operations and FlexCounter DB integration. OrchAgent classes corresponding to each SAI object can reuse generic methods in `objectorch` for State DB and FlexCounter DB access.

The following `translateObjectAttr(field, value, attr)` resolves the attribute ID from the maps above, normalizes enums and precision-based numbers, and then uses `sai_deserialize_attr_value` with attribute metadata.

```c++
objectorch.cpp

bool ObjectOrch::translateObjectAttr(
    _In_ const std::string &field,
    _In_ const std::string &value,
    _Out_ sai_attribute_t &attr)
{
    if (m_createandsetAttrs.find(field) != ...) attr.id = m_createandsetAttrs[field];
    else if (m_createonlyAttrs.find(field) != ...) attr.id = m_createonlyAttrs[field];
    ...
    auto meta = sai_metadata_get_attr_metadata(m_objectType, attr.id);
    ...
    /* enum map, precision-based float→int, then */
    sai_deserialize_attr_value(newValue, *meta, attr);
    return true;
```

ObjectOrch provides generic Redis-to-SAI object mapping by driving behavior from SAI object/attribute metadata and existing serialize/deserialize helpers. Instead of hard-coding attribute mappings, OTN OrchAgent classes, such as OA, OCM, and VOA, inherit `ObjectOrch` for State DB and FlexCounter DB operations. This mechanism eliminates redundant, error-prone mapping code in each individual class. If special handling is needed, individual subclasses can still override superclass functions.

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 10, 'rankSpacing': 18}, 'themeVariables': {'fontSize': '10px'}}}%%
flowchart LR
    subgraph ORCH[orchagent]
        direction TB
        OA[oaorch.cpp]
        ATT[attenuatororch.cpp]
        OBJ[objectorch.cpp]
        OA -->|inherit| OBJ
        ATT -->|inherit| OBJ
    end
    OBJ -->|lookup + map| META[SAI metadata]
```

Summary (to be proposed to SONiC community):
- An OrchAgent superclass (`ObjectOrch`) is created for generic translation from Redis strings to SAI attributes using SAI metadata, instead of hard-coded mapping tables.
- All OrchAgent classes should inherit from `ObjectOrch` and override functions when needed.

### 8.3 OTN State DB Update

This section describes how to support OTN state update in STATE DB. Tables in State DB needs to be updated continuously, so that NBI (CLI/REST API) can read the OTN objects state, both discrete values (on/off and enabled/disabled, etc.) and gauged values (gain, attenuation and optical power, etc.) from State DB directly via openconfig yang models. State changes can also be notified via gNMI subscription mechanism.

#### 8.3.1 SONiC SWSS Redis plug-in script

SWSS utilizes Lua scripts for certain operations, particularly within its Producer/Consumer Table framework. These scripts help in atomically writing and reading messages to and from Redis databases.
Examples of Lua scripts within the SWSS can be found in the sonic-swss repository. One notable example is [pfc_restore.](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfc_restore.lua), which uses Redis commands to handle PFC (Priority Flow Control) restoration.

#### 8.3.2 State DB update

It is proposed to use SWSS Lua scripts to support State DB updates for device's real time status changes. This approach has the following benefits:

- Use the existing counter DB as-is; no new OTN specific code is required in Syncd for basic state update.
- SONiC counter DB is designed for storing raw hardware data. Syncd updates counters specified in the FlexCounter DB. State which is northbound visible can be derived from counter DB tables.
- Use the existing SWSS OrchAgent mechanism to install Lua scripts, similar to stored procedures in traditional database systems. These scripts run inside the Redis container and can be invoked whenever counter DB is updated.
- These Lua scripts can be device-specific, so each vendor can provide customized scripts as part of device data. This provides maximum flexibility and keeps status updates.

The following diagram shows the workflow of the Redis plug-in script in SONiC.

<img src="./images/redis-pluggin-script.png" alt="Redis script" width="600">

- First, OrchAgent installs the script and stores its SHA.
- When Syncd adds the counter attribute, it also adds the plug-in SHA.
- When vendor SAI updates counters, it also sends a request to Redis DB to run the script.

#### 8.3.3 Device specific lua scripts (***Common code optimization***)

Currently, some vendor-specific Lua scripts are placed in the SWSS [orchagent](https://github.com/sonic-net/sonic-swss/blob/master/orchagent), which is not ideal:
- Vendor/device-specific scripts are included in the SWSS common codebase.
- Script installation is hard-coded. Only Lua scripts explicitly requested by running code are installed; other files in `/usr/share/swss` are not loaded unless a component is written to load them.

```c++
pfcwdorch.cpp:

    if (this->m_platform == CISCO_8000_PLATFORM_SUBSTRING) {
        restorePluginName = "pfc_restore_" + this->m_platform + ".lua";
    } else {
        restorePluginName = "pfc_restore.lua";
    }
```

For OTN, the script path is under `/usr/share/sonic/platform/<script_path>` (e.g., `otn_oa_plugin.lua`). During SONiC installation, ONIE installs only the scripts for that device. In OrchAgent, `loadRedisScript` is used to install all scripts generically into `COUNTERS_DB`, and the returned SHA is passed into the FlexCounter manager.

```c++
objectorch.cpp
    if (!script_path.empty())
    {
        try
        {
            std::string path("/usr/share/sonic/platform/");
            path += script_path;
            std::string att_script = swss::readTextFile(path);
            std::string att_sha = swss::loadRedisScript(m_countersDb.get(), att_script);
            fv_stat = FieldValueTuple(plugin_field, att_sha);
        }
```

Lua scripts are included as part of device configuration; see [example](https://github.com/sonic-otn/sonic-buildimage/tree/202411_otn/device/molex/x86_64-otn-kvm_x86_64-r0).

Summary:
- Device/vendor Lua scripts should be removed from SWSS common code.
- Device/vendor Lua scripts should be part of device configuration.

### 8.4 SyncD Extension

In the syncd container, SONiC starts the syncd service at startup, which loads the SAI component (driver) present in the system. This component is provided by various vendors, who implement the SAI interfaces based on their hardware platforms, allowing SONiC to use a unified upper-layer logic to control various hardware platforms. Syncd is responsible for communicating with the Redis database, loading SAI implementation, and interacting with it to handle ASIC initialization, configuration, status reporting, and so on.

For OTN devices, Syncd behavior is similar. However, instead of managing an ASIC, each vendor implements SAI OTN extension APIs to control and monitor OTN objects. Notification handlers are also registered to process events from hardware. OTN support is added by extending logic to process new SAI APIs for OTN objects.

#### 8.4.1 FlexCounter Extension
When a SAI object is created, the corresponding FlexCounter is set up to collect object status in Counter DB. For better code maintainability, instead of modifying the existing [FlexCounter](https://github.com/sonic-net/sonic-sairedis/blob/master/syncd/FlexCounter.cpp), a new file, [`FlexCounterOtn.cpp`](https://github.com/sonic-otn/sonic-sairedis/blob/202411_otn/syncd/FlexCounterOtn.cpp), is created for OTN support to isolate code maintenance.

`FlexCounter` manages Counter DB configuration for SAI object monitoring. Separate `FlexCounterOtn` files are created for managing OTN SAI object attributes in Counter DB. This reduces code-change contention between the OTN project and the rest of SONiC development.

```Diff
   --- syncd
    |--- FlexCounter.(h|cpp)
+   |--- FlexCounterOtn.(h|cpp)
```

Similarly, SAI Object (de)serialization is also implemented in separate files `meta/sai_serialize_otn` from the main file `sai-serialize`.

***Run time logical flow isolation***

Processing for OTN SAI objects and APIs is added to existing Syncd infrastructure with clear isolation from existing logic. This is done by placing OTN object processing at the end of current logic, so OTN logic is not in packet-switch code paths. The code snippet for adding the OTN counter plugin is shown below (similar for add/remove counters):

```Diff
FlexCounter.cpp

void FlexCounter::addCounterPlugin {
    ....
    {
            else
            {
+               if (m_flexCounterOtn ->addCounterPlugin(field, shaStrings))
+               {
+                    continue;
+               }

                SWSS_LOG_ERROR("Field is not supported %s", field.c_str());
            }
    }

    // notify thread to start polling
    notifyPoll();
}
```

#### 8.4.2 OTN Gauged Value Modeling 

Many OTN objects include floating-point values (e.g., optical power, attenuation, Pre-FEC BER). These values require different levels of precision — optical power may need two decimal places, while Pre-FEC BER may require up to 18. All NBI-facing DBs (Config DB, State DB, Event DB, etc.) should store the gauged value in decimal format.

Currently, SAI supports only `int64_t` statistics, without float/decimal type support. To support float without breaking compatibility, we propose introducing the `@precision` tag, allowing attributes and statistics to specify required precision. Here are examples:

***SAI @precision [0-18] tag***
```c
    /**
     * @brief The actual attenuation applied by the attenuator in units of 0.01dB.
     *
     * @type sai_int32_t
     * @flags READ_ONLY
     * @precision 2
     */
    SAI_OTN_ATTENUATOR_ATTR_ACTUAL_ATTENUATION,
```

In the SAI meta data, the `valueprecision` field in `attrInfo` is used to represent the precision. Code for double to int conversion:

```c
objectorch.cpp
  // Save precision value for each attribuite if precision is valid.
  if (attr->valueprecision > 0) {
      m_attrPrecisions[name] = attr->valueprecision;
      m_attrPrecisions[hyphen_name] = attr->valueprecision;
  }

  /* Convert float string to int string according to the precision */
  try
  {
      double float_value = std::stod(value);
      size_t precision = m_attrPrecisions[field];
      int64_t int_value = static_cast<int64_t>(float_value * (std::pow(10, precision)));
      newValue = std::to_string(int_value);
  }
```

***Store read-only gauged value in State DB or Counter DB***

Another design issue is whether to model real-time gauged values in SAI `stat_t` or SAI `attr_t`:

```c

// 1. Realtime gauged value using attr_t

  typedef enum _sai_attenuator_attr_t {
    /**
 * @brief The actual attenuation applied by the attenuator
 * in units of 0.01dB.
 *
 * @type sai_int32_t
 *
 * @flags READ_ONLY
 *
 * @precision 2
 */
       SAI_OTN_ATTENUATOR_ATTR_ACTUAL_ATTENUATION
     }

  // 2. Realtime gauged value using stat_t
  typedef enum _sai_attenuator_stat_t {
    /**
 * @brief The actual attenuation applied by the attenuator
 * in units of 0.01dB.
 *
 * @type sai_int32_t
 *
 * @flags READ_ONLY
 *
 * @precision 2
 */
       SAI_OTN_ATTENUATOR_STAT_ACTUAL_ATTENUATION
  }
```

Based on the following analysis, defining read-only gauged values in `enum_xx_attr_t` seems preferable:
  - `stat_t` in current SONiC is all counters (enum), not tagged attributes. Supporting tagged attributes in `stat_t` would require looping through all tags in `SAI/meta/parse.pl`. This introduces major changes and duplicated handling for `stat_t` and `attr_t`.
  - Using attr_t for gauged value requires no change to existing SAI parse infrastructure.
  - Read-only SAI attributes can be stored in state DB, which is updated by registered lua script with a device specific interval (1s).

### 8.5 PMON

SONiC PMON (platform monitor) manages generic hardware independent of device function. PMON infrastructure is implemented in two repositories, [sonic-platform-common](https://github.com/sonic-net/sonic-platform-common) and [sonic-platform-daemon](https://github.com/sonic-net/sonic-platform-daemons), described in [this doc](https://github.com/sonic-net/SONiC/blob/master/doc/platform_api/new_platform_api.md). Vendor platform modules reside under `sonic-buildimage/platform` for each device type.

#### 8.5.1 PMON Base Class

Python classes are implemented to model the generic hardware structure and operations on the hardware. Here is the example of a typical device structure in python classes:

- Chassis
  - System EEPROM info
  - Reboot cause
  - Environment sensors
  - Front panel/status LEDs
  - Power supply unit[0 .. p-1]
  - Fan[0 .. f-1]
  - Module[0 .. m-1] (Line card, supervisor card, etc.)
    - Environment sensors
    - Front-panel/status LEDs
    - SFP cage[0 .. s-1]
    - Components[0 .. n-1] (CPLD, FPGA, MCU, ASIC etc.)
      - name
      - description
      - firmware

#### 8.5.2  Device specific platform config and driver

The JSON file [code here](https://github.com/sonic-otn/sonic-buildimage/blob/202411_otn/device/molex/x86_64-otn-kvm_x86_64-r0/platform.json) is to define the OTN device HW hierarchy described above. This config file is device specific for a particular OTN device, shown as in the following diagram:

<img src="./images/pmon-drivers.png" alt="Redis script" width="600">

An implementation of driver of PMON is [implemented here](https://github.com/sonic-otn/sonic-buildimage/tree/202411_otn/platform/otn-kvm/sonic-platform-modules-otn-kvm/ols-v). driver simulator is [here](https://github.com/sonic-otn/sonic-otn-libs).

#### 8.5.3 Linecard Hot-pluggable (***Feature enhancement***)

Currently, SONiC supports two chassis types:

- Pizza box without pluggable supervisor/control card and line cards
- Multi-ASIC, in which each line card runs an independent SONiC

An OTN device may not fit either architecture above. A typical chassis-based OTN device hosts a control card (supervisor card) and multiple line cards containing various optical modules. When a line card is removed or inserted, OrchAgent should be notified so affected objects are removed from or added to the Syncd monitoring thread. Optical component status should also be updated in State DB.

***SONiC xxxSyncd Mechanism***

In SWSS and other application containers (for example, BGP and LLDP), various `sync` daemons synchronize state from external sources into Redis (mainly APPL_DB, sometimes STATE_DB). OrchAgent (and other SWSS components) then reacts to that state. In this model, sync daemons publish kernel/config/FPM/peer state to Redis so OrchAgent can program the switch.

For OTN devices, line card status changes can be handled in the same way, as shown below:

<img src="./images/linecard-syncd.png" alt="Line Card syncd" width="600">

As shown in the diagram above, new line card sync logic is added to `chassisd` in the PMON container.

The following diagram shows the steps for handling line card insertion or remove/fail events. Note that `linecardsyncd` is implemented as a Python library for each device.

<img src="./images/lc-hot-pluggable.png" alt="Line Card Hot Pluggable" width="600">

***Line card un-plug/failed***

1. `chassisd` in PMON detects a removed line card by polling.
2. It changes the line card status from online to `empty/fault`.
3. The linecardsyncd API (implemented at device level) removes all the optical components on the line card. 
4. OrchAgent is triggered to remove corresponding SAI objects and associated FlexCounter entries.
5. Syncd stops monitoring removed resources for these optical modules.
6. Objects in State DB should also be removed. NBI queries for these components should return empty results.

***Line card insert/recover***

1. PMON detects a line card is back to online (LC communication is OK). 
2. It changes the line card status back to online.
3. `linecardsyncd` APIs add optical components for the line card by restoring configuration from Config DB.
4. OrchAgent is triggered to create corresponding SAI objects and associated FlexCounter entries.
5. Syncd starts monitoring the resources. State DB should also be updated with current component state.

#### 8.5.4 Firmware Upgrade

SONiC provides a generic mechanism to install/upgrade firmware, [fwutil.md](https://github.com/sonic-net/SONiC/blob/master/doc/fwutil/fwutil.md).

OTN vendors need to implement the Python component APIs defined in the base class [`component_base.py`](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/component_base.py):

### 8.6 SONiC host containers

The following containers shall be enabled in SONiC and included in the image. Switch-specific containers shall be disabled for images built for OTN devices. The SONiC build [rule/config](https://github.com/sonic-net/sonic-buildimage/blob/master/rules/config) must be updated accordingly.
  
| Container/Feature Name | Is Enabled? |
| ---------------------- | ----------- |
| SNMP                   | Yes         |
| Telemetry              | Yes         |
| LLDP                   | Yes         |
| Syncd                  | Yes         |
| Swss                   | Yes         |
| Database               | Yes         |
| BGP                    | Yes         |
| Teamd                  | No          |
| Pmon                   | Yes         |
| Nat                    | No          |
| Sflow                  | No          |
| DHCP Relay             | No          |
| Radv                   | No          |
| Macsec                 | No          |
| Resttapi               | Yes         |
| gNMI                   | Yes         |

## 9. Device Configuration and Management

This section contains subsections for all configuration and management-related design topics. Subsections for CLI and Config DB are included below, along with subsections for data models (YANG, REST, gNMI, etc.).

### 9.1. Manifest (if the feature is an Application Extension)

N/A

### 9.2. OTN YANG Model

#### 9.2.1 OpenConfig Optical Transport Yang Model
The OTN project adopts the standard OpenConfig YANG model for [optical transport](https://github.com/openconfig/public/tree/master/release/models/optical-transport).

| Object | Description | OpenConfig Reference |
|--------|-------------|----------------------|
| OA | Optical amplifier | openconfig-optical-amplifier.yang|
| VOA | Optical attenuator | openconfig-optical-attenuator.yang |
| Optical Port | Optical transport port | openconfig-transport-line-common.yang
| OCH | Optical channel | openconfig-terminal-device.yang|
| WSS | Wavelength selective switch | openconfig-wavelength-router.yang |
| OMC | Optical media channel | openconfig-wavelength-router.yang|
| OSC | Optical supervisory channel | openconfig-optical-amplifier.yang|
| OTDR | Optical time-domain reflectometer | Not defined yet |
| OCM | Optical channel monitor | openconfig-channel-monitor.yang |
| APS | Automatic protection switch |openconfig-transport-line-protection.yang|
| APS Port | Automatic protection switch port | openconfig-transport-line-protection.yang |
| Logical Channel | Logical channel | openconfig-terminal-device.yang|

All Northbound APIs (RESTCONF and gNMI) are based on the above YANG model, as described in the sections below.

#### 9.2.2 Generic Translation and Mapping

As SONiC DBs are implemented using [Redis](https://redis.io/), OpenConfig-based NBIs need to be translated and mapped to/from the Redis DB schema. SONiC management framework infrastructure's Translib converts the data models exposed to management clients into the Redis ABNF schema format. See the HLD [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

To support an OpenConfig YANG model:

- Generate the annotation template file:
```bash
goyang --format=annotate --path=/path/to/yang/models openconfig-optical-attenuator.yang > annot/openconfig-optical-attenuator-annot.yang
```
- Annotate YANG extensions to define translation hints. [An example here](https://github.com/sonic-otn/sonic-mgmt-common/blob/202411_otn/models/yang/annotations/openconfig-optical-attenuator-annot.yang).

- Add corresponding sonic yang for CVL (configuration verification layer) purpose. [An example](https://github.com/sonic-otn/sonic-mgmt-common/blob/202411_otn/models/yang/sonic/sonic-optical-attenuator.yang).

- Add the list of Openconfig YANG modules and annotation files to the transformer manifest file, $(SONIC_MGMT_FRAMEWORK)/config/transformer/models_list.

- Implement the overload methods if you need translate data with special handling. See the OTN transformer [here](https://github.com/sonic-otn/sonic-mgmt-common/blob/202411_otn/translib/transformer/xfmr_otn_openconfig.go).

See this [developer guide](https://github.com/project-arlo/sonic-mgmt-framework/wiki/Transformer-Developer-Guide) for details.

#### 9.2.3 REST 

After the translation and mapping are implemented, the SONiC management framework supports the REST API accordingly. The REST API specification can be auto-generated using the [OpenAPI tool](https://github.com/OpenAPITools/openapi-generator).

OTN REST request examples:


```bash
## Get all Amplifiers
curl -k -X GET\
   "https://127.0.0.1/restconf/data/openconfig-optical-amplifier:optical-amplifier/amplifiers" \
   -H "accept: application/yang-data+json" | jq

# Get one VOA object
curl -k -X GET \
   "https://127.0.0.1/restconf/data/openconfig-optical-attenuator:optical-attenuator/attenuators/attenuator=VOA0-0" \
   -H "accept: application/yang-data+json" | jq

## Get from Redis Table directly
curl -k -X GET\
  "https://127.0.0.1/restconf/data/sonic-optical-amplifier:sonic-optical-amplifier/OTN_OA/OTN_OA_LIST" \
  -H "accept: application/yang-data+json" | jq

## Set EDFA gain
curl -k  -X PUT \
    -H "Content-Type: application/yang-data+json" \
    -H "Accept: application/yang-data+json" \
    "https://127.0.0.1/restconf/data/openconfig-optical-amplifier:optical-amplifier/amplifiers/amplifier=OA0-0/config/target-gain" \
    -d '{"openconfig-optical-amplifier:target-gain": "5.0"}' | jq

## Get a leaf node in a nested list
admin@sonic:~$   curl -k -X GET\
   "https://127.0.0.1/restconf/data/openconfig-channel-monitor:channel-monitors/channel-monitor=OCM0-0/channels/channel=196062500,196137500/state/power" \
   -H "accept: application/yang-data+json" | jq
```
```json
{
  "openconfig-channel-monitor:channel": [
    {
      "state": {
        "target-power": "1.5",
      },
    }
  ]
}

```

#### 9.2.4 gNMI and Telemetry

gNMI set/get/telemetry is supported by [gNMI Server](https://github.com/sonic-net/sonic-gnmi). Design doc is [here](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design).

Again, SONiC has a generic gNMI server implementation to support YANG models backed by Redis DB.

Examples:

```bash
## get on the full attenuator tree
    gnmic -a 127.0.0.1:8080 -u admin -p YourPaSsWoRd --insecure \
       get --path openconfig-optical-attenuator:optical-attenuator/attenuators

## get on a specific attenuator
    gnmic -a 127.0.0.1:8080 -u admin -p YourPaSsWoRd --insecure \
       get --path openconfig-optical-attenuator:optical-attenuator/attenuators/attenuator[name=VOA0-0]

## gNMI set on an OTN resource
gnmic -a 127.0.0.1:8080 \
   -u admin -p YourPaSsWoRd --insecure \
   set \
   --update `openconfig-optical-attenuator:/optical-attenuator/attenuators/attenuator[name=VOA0-0]/   config:::json_ietf:::{
     "openconfig-optical-attenuator:config": {
       "attenuation": "6.0" }
   }`
```

***Path wildcard key support***

One of the most useful gNMI capabilities is subscription support in the following modes:
- once (same as get)
- polling (interval controlled by clients)
- streaming (sample, on change)

<img src="./images/gnmi-telemetry.png" alt="Telemetry" width="600">

Here are the examples for telemetry subscription:
```bash
## Sample mode wildcard support:
## 1. In this mode, the client sends a stream subscription request and the server pushes updates at the default server rate. NOTE: the default stream sample rate is 20 seconds.
## 2. Entry Wildcards ([name=*]) You can subscribe to all entries in a list by using the * wildcard in the key field. This triggers the Key Transformer to scan the appropriate database—STATE_DB for dynamic data or CONFIG_DB for settings—and return every discovered instance.

gnmic   --address 127.0.0.1:8080   --username admin   --password YourPaSsWoRd   --insecure   subscribe   --print-request   --mode stream   --stream-mode sample   --target OC-YANG   --path 'openconfig-optical-attenuator:optical-attenuator/attenuators/attenuator[name=*]/state'

## Path Wildcards (Leaf node discovery) By subscribing to a parent container, the Table Transformer recursively discovers all underlying list members. This is useful for fetching the entire hierarchy of a device in one stream.
gnmic --address 127.0.0.1:8080   --username admin   --password YourPaSsWoRd   --insecure   subscribe --mode stream  --stream-mode sample  --target OC-YANG  --path 'openconfig-channel-monitor:channel-monitors/channel-monitor[name=OCM0-0]/channels'

## on change mode for non-frequent status change
gnmic   --address 127.0.0.1:8080   --username admin   --password YourPaSsWoRd   --insecure   subscribe   --print-request   --mode stream   --stream-mode on-change  --target OC-YANG   --path 'openconfig-optical-attenuator:optical-attenuator/attenuators/attenuator[name=*]/state/enabled'

```
As a guideline, 
- For continuously changing optical analog values (power, attenuation, gain, etc.), sampling with an interval (e.g. 5 seconds) should be used.
- For more static status (up/down, enabled/disabled, alarms, and events), on-change mode should be used. 

***gNMI Performance Analysis***
A high-performance system is measured in two aspects:
- Response time, for example, 100 ms for all OCM get requests, 100 ms to set all WSS channels' attenuation, etc.
- Data freshness: Counter DB is updated by syncd thread periodically and lua script then updates the State DB accordingly. Therefore, the data freshness in State DB depends on the syncd thread's polling interval, currently 1 second.
- Reasonable resource usage (CPU/RAM)

When the management framework receives a gNMI subscription request, the framework subscribes to changes in the corresponding Redis DB tables, based on the subscription YANG path. 

```mermaid
sequenceDiagram
    participant HW as HW
    participant SYNC as syncd
    participant DB as stateDB (ATTENUATOR_TABLE)
    participant GNMI as gNMI Server
    participant CLIENT as Data Stream Client

    loop every 1s
        HW->>SYNC: Read/update optical values
        SYNC->>DB: Write ATTENUATOR_TABLE
    end

    alt On-change subscription (>= 1s)
        DB-->>GNMI: Table update notification
        GNMI-->>CLIENT: Push changed values
    else Sampling subscription (5s)
        GNMI->>DB: Poll latest values (every 5s)
        DB-->>GNMI: Current ATTENUATOR_TABLE snapshot
        GNMI-->>CLIENT: Push sampled data
    end
```

As shown in the above diagram:
- With the wildcard key in the path for gNMI subscription. Both on-change and sampling attributes can be stored in the same DB table.
- The SYNCD thread poll interval should be finer granularity than gNMI telemetry so that the STATE DB is refreshed more frequently than the telemetry sampling interval to prevent the stale data. (syncd thread polling interval 1s, and gNMI sampling 5 s).
- As SONiC Redis DB change can only be subscribed at DB Table (Seems). It is possible that gNMI server would be notified change every 1s.

Performance benchmark test will be done when a fully functional kvm ILA device (OA, VOA, OCM, WSS/DEG, with 4 line cards) is completed.

#### 9.2.5 CLI Auto Generation for OTN (***Feature enhancement***)

Most SONiC CLI is implemented in sonic-utility based on the [Python click library](https://click.palletsprojects.com/en/8.1.x/). These CLIs are supported in [sonic-utilities](https://github.com/sonic-net/sonic-utilities). It is preferred that OTN CLI supports auto-generation instead of hard-coded Python for better maintenance and consistency.

SONiC provides a tool for automatically generating click CLIs based SONiC yang, see [SONiC CLI auto-generation tool](https://github.com/sonic-net/SONiC/blob/master/doc/cli_auto_generation/cli_auto_generation.md). However, the current cli auto generation tool only support cli show/config on in Condig DB. A [PR](https://github.com/sonic-net/sonic-utilities/pull/3222) is submitted to enhance the tool for support show in State DB.

***openconfig yang to SONiC yang translation***
Because `sonic-cli-gen` generates CLI python code from sonic-yang and OTN uses openconfig yang, [an auto-translation tool](https://github.com/sonic-otn/sonic-buildimage/blob/202411_otn/platform/otn-kvm/sonic-yanggen/sonic_yanggen.py) is developed to translate openconfig yang to sonic yang. `sonic_yanggen.py` processes an openconfig yang model and its annotation yang, which defines the openconfig yang to Redis table schema. Then a corresponding sonic yang is generated. The generated sonic yang is then used to generate CLI by `sonic-cli-gen`, as shown in the following diagram:

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 15, 'rankSpacing': 20}}}%%
graph LR
    subgraph Build_Env [Build Environment]
        direction TB
        Conf["Config File (device/.../yang_auto_cli)
        openconfig yang"]
        PyScript["sonic_yanggen.py"]
        YANGs["sonic yang"]

        Conf -->|Input| PyScript
        PyScript -->|Generate| YANGs
    end

    subgraph Target_Env [Target Device Run time]
        direction TB
        Service["Service"]
        ShellScript["yang_auto_cli.sh"]
        CLI["SONiC CLI"]

        Service -->|Start| ShellScript
        ShellScript -->|Register| CLI
    end

    YANGs -->|Install via Deb| ShellScript
```

***Device specific CLI generation***
As each device may have different capabilities and only support a subset of OTN functionality, CLI generation must be device specific to avoid including unsupported CLI. 
- The yang model supported by a device is configured in device/{vendor}/{platform}/yang_auto_cli to enable generation.
```bash
# Example: device/molex/x86_64-otn-kvm_x86_64-r0/yang_auto_cli
openconfig-optical-attenuator.yang openconfig-optical-attenuator-annot.yang
openconfig-optical-amplifier.yang openconfig-optical-amplifier-annot.yang
```
Here is the work flow:
- At build time
  - Compiles libyang (and Python bindings) from source.
  - Scans device/ directory for yang_auto_cli config file and converts specified OpenConfig yang and its annotations to SONiC YANG models using sonic_yanggen.py.
  - Packages generated sonic yang files into /usr/share/sonic/device-yang/{platform}/.

- At SONiC startup
  - sonic-yanggen.service runs on startup.
  - Executes yang_auto_cli.sh to register CLI commands. The script only processes files specifically for this `ONIE platform` (ex. x86_64-otn-kvm_x86_64-r0). 
  - As a result, the CLI applicable for that device is generated and available to use. 

Note that yang_auto_cli.sh only supports generating CLI for the config DB; [an enhancement PR](https://github.com/sonic-net/sonic-utilities/pull/3222) is submitted to support CLI access to the State DB. 

***Vertical display support***

Existing sonic-cli-gen displays a Redis table in which each object is in a horizontal format, i.e., a row. This causes an issue when an object has many entries and the data beyond the screen width is truncated. To fix that issue, a vertical option is added for sonic-cli-gen, so that each object will be displayed vertically to show all the attributes. See the following screenshot for the original sonic (horizontal) and improved vertical format. See [this commit](https://github.com/sonic-molex/sonic-utilities/commit/97b19431490e5ca8f151cac7a85ffe6ffba97c99).

```bash
root@sonic:~# show otn-oa-table
NAME   TYPE   TARGET GAIN   MIN GAIN   MAX GAIN   TARGET GAIN TILT   GAIN RANGE       AMP MODE       TARGET OUTPUT POWER   S
----   ----   -----------   --------   --------   ----------------   ----------       --------       -------------------   -
OA0-0  EDFA   12.5          0          25         0.4                FIXED_GAIN_RANGE CONSTANT_GAIN  N/A                   5
OA0-1  EDFA   5.2           5          28         0.5               
root@sonic:~# sonic-cli-gen generate show sonic-optical-amplifier --default-vertical
root@sonic:~# show otn-oa-table
Name OA0-0
   Type                : EDFA
   Target gain         : N/A
   Min gain            : 5
   Max gain            : 28
   Target gain tilt    : 0.4
   Gain range          : FIXED_GAIN_RANGE
   Amp mode            : CONSTANT_GAIN
   Target output power : N/A
   Max output power    : N/A
   Enabled             : true
   Fiber type profile  : N/A
   Component           : N/A
   Ingress port        :
   Egress port         :
   Actual gain         : 20
   Actual gain tilt    : 0.4
   Input power total   : 25
   Input power c band  : -60
   Input power l band  : 25
   Output power total  : 25
   Output power c band : 25
   Output power l band : 25
   Laser bias current  : 25
   Optical return loss : 25

Name OA0-1
   Type                : EDFA
   ...
```

### 9.3. Config and State DB Schema For OTN  

New Config DB and State DB tables are introduced to support OTN devices. The new DB tables are added in [`schema.h`](https://github.com/sonic-otn/sonic-swss-common/blob/202411_otn/common/schema.h) in `sonic-swss-common`. Potentially, OTN tables can be defined in a separate file (**TBD**).

Config DB and State DB schemas are strictly mapped from OpenConfig YANG models. The following new DB tables are defined for optical amplifiers and variable optical attenuators as examples:

```
CONFIG_DB
=========

OTN_ATTENUATOR
;/openconfig-optical-attenuator:optical-attenuators/attenuator/config
;revision "2019-07-19" {reference "0.1.0"}
key                 = ATTENUATOR|VOA<slot>-<num> ; string, numbers are 0 based.
;field              = value
attenuation-mode    = STRING                 ; identityref    
target-output-power = float64                ; yang decimal64, json Number
attenuation         = float64               
enabled             = "true" / "false"       ; boolean    

OTN_OA
;/openconfig-optical-amplifier:optical-amplifiers/amplifier/config
;revision "2019-12-06" {reference "0.5.0"}
key                 = OTN_OA|OA<slot>-<num>  ; string
;field              = value
type                = STRING                 ; identityref
target-gain         = float64                ; yang decimal64, json Number
max-gain            = float64                ; yang decimal64, json Number
min-gain            = float64                ; yang decimal64, json Number
target-gain-tilt    = float64
gain-range          = STRING                 ; identityref
amp-mode            = STRING                 ; identityref
target-output-power = float64                ; yang decimal64, json Number
max-output-power    = float64                ; yang decimal64, json Number
enabled             = "true" / "false"       ; boolean
fiber-type-profile  = STRING                 ; identityref
autolos             = "true" / "false"       ; oplink extension, APSD
apr-enabled         = "true" / "false"       ; oplink extension 

STATE_DB:
=========
OTN_ATTENUATOR_TABLE
;/openconfig-optical-attenuator:optical-attenuators/attenuator/state
key                 = OTN_ATTENUATOR_TABLE|VOA<slot>-<num>  ; string
;field              = value
attenuation-mode    = STRING                 ; identityref
target-output-power = float64                ; yang decimal64, json Number
attenuation         = float64
enabled             = "true" / "false"       ; boolean

component           = STRING                 ; ref to platform component
ingress-port        = STRING                 ; ref to platform component
egress-port         = STRING                 ; ref to platform component
actual-attenuation  = float64                ; instant value only
output-power-total  = float64
optical-return-loss  = float64

OTN_OA_TABLE
;/openconfig-optical-amplifier:optical-amplifiers/amplifier/state
key                 = OTN_OA_TABLE|OA<slot>-<num>  ; string
;field              = value
type                = STRING                 ; identityref
target-gain         = float64                ; yang decimal64, json Number
max-gain            = float64                ; yang decimal64, json Number
min-gain            = float64                ; yang decimal64, json Number
target-gain-tilt    = float64
gain-range          = STRING                 ; identityref
amp-mode            = STRING                 ; identityref
target-output-power = float64                ; yang decimal64, json Number
max-output-power    = float64                ; yang decimal64, json Number
enabled             = "true" / "false"       ; boolean
fiber-type-profile  = STRING                 ; identityref
autolos             = "true" / "false"       ; oplink extension, APSD
apr-enabled         = "true" / "false"       ; oplink extension

component           = STRING                 ; ref to platform component
ingress-port        = STRING                 ; ref to platform component
egress-port         = STRING                 ; ref to platform component
actual-gain         = float64                ; instant value only
actual-gain-tilt    = float64
input-power-total   = float64
input-power-c-band  = float64
input-power-l-band  = float64
output-power-total   = float64
output-power-c-band = float64
output-power-l-band = float64
laser-bias-current  = float64
optical-return-loss  = float64
```
### 9.4 Event and Alarm Support

#### 9.4.1 SONiC Notification
SONiC has a notification mechanism supporting notifications from Vendor SAI (driver) to SWSS. Currently the notification is only supported by the root SAI object (switch), in which all notification callback attributes and prototypes are defined in `saiswitch.h`. When the switch object is created during SWSS startup, all notification attributes are set with the corresponding callbacks in orchagent `main.cpp`. Notification callbacks are defined in `Notification.h|cpp` in orchagent. When Syncd receives switch creation from OrchAgent, it registers its own callbacks to the SAI vendor drivers. When an event is detected by Vendor SAI, the registered Syncd callback will be called with the driver data passed as function parameters. The syncd callback simply sends a message via Redis to SWSS orchagent, which will call the SWSS callback to handle the event.

#### 9.4.2  Notification Extension for OTN

***OTN Notification Extension***
In order to separate OTN notification code from the existing switch code, a notification attribute for OTN is declared in SAI extension `saiswitchextensions.h`. 

```c

/**
 * @brief OTN alarm event notification
 *
 * @count data[count]
 *
 * @param[in] count Number of notifications
 * @param[in] data Array of OTN alarm events
 */
typedef void (*sai_otn_alarm_event_notification_fn)(
        _In_ uint32_t count,
        _In_ const sai_otn_alarm_event_data_t *data);

/**
 * @brief SAI switch attribute extensions.
 *
 * @flags free
 */
typedef enum _sai_switch_attr_extensions_t
{
     ....
     /**
     * @brief OTN alarm event notification callback function passed to the adapter.
     *
     * Use sai_otn_alarm_event_notification_fn as notification function.
     *
     * @type sai_pointer_t sai_otn_alarm_event_notification_fn
     * @flags CREATE_AND_SET
     * @default NULL
     */
    SAI_SWITCH_ATTR_OTN_ALARM_EVENT_NOTIFY,

    SAI_SWITCH_ATTR_EXTENSIONS_RANGE_END

} sai_switch_attr_extensions_t;

```
***OTN Device Object***
Equivalent to switch's root object. it is proposed to have a logical root object `otndevice` for OTN devices in `saiexperimentalotndevice.h`, as shown in the following diagram:

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 15, 'rankSpacing': 20}}}%%
flowchart TB
    subgraph SAI["SAI / Management Layer"]
        direction LR
        saiswitchextension["saiswitchextension"]
        saiswitch["saiswitch"]
        saiexperimentalotndevice["saiexperimentalotndevice"]
        saiswitchextension -->|" "| saiswitch
        note1["OTN notifications"]
        note2["OTN device level SAI attributes"]
        note1 -.-> saiswitchextension
        note2 -.-> saiexperimentalotndevice
    end

    subgraph HW["Hardware / Functional Modules"]
        OTDR["OTDR"] ~~~ OA["OA"] ~~~ VOA["VOA"] ~~~ WSS["WSS"] ~~~ OPS["OPS"]
    end

    saiexperimentalotndevice --> HW
    SAI ~~~ HW
    style SAI stroke:#ff8c00,stroke-dasharray: 5 5
    style saiswitchextension fill:#e8f5e9,stroke:#2e7d32
    style saiswitch fill:#e8f5e9,stroke:#2e7d32
    style saiexperimentalotndevice fill:#e8f5e9,stroke:#2e7d32
    style note1 fill:#ffe0b2,stroke:#ff8c00
    style note2 fill:#ffe0b2,stroke:#ff8c00
    style OTDR fill:#e8f5e9,stroke:#2e7d32
    style OA fill:#e8f5e9,stroke:#2e7d32
    style VOA fill:#e8f5e9,stroke:#2e7d32
    style WSS fill:#e8f5e9,stroke:#2e7d32
    style OPS fill:#e8f5e9,stroke:#2e7d32
```
The functionality of OTN Device object includes:
- Manage (config and state) of device-level global properties, such as administrative and operational state, alarm ACT/DEACT timers, etc.
- Register OTN event notification callbacks. This avoids the need for the OTN project to change existing Orchagent `main.cpp` and isolates the new OTN code from the existing switch code base.

***OTN Event Notification Registration***

OTN event notification reuses the existing SONiC notification mechanism without changing the existing SWSS and Syncd code. The steps are shown in the following diagram:
- During Orchagent startup, when the OTN device object is created, it sets the OTN notification callback in the `saiswitch` object.
- When Syncd receives switch creation from OrchAgent, it registers its own callbacks to the SAI vendor drivers.
- When an event is detected by Vendor SAI, the registered Syncd callback will be called with the driver data passed as function parameters.
- The syncd callback simply sends a message via Redis to SWSS orchagent, which will call the SWSS callback to handle the event.
- Currently, the OTN notification handler in SWSS only writes the event to syslog. The extra business logic to process the event is **TBD**.

```mermaid
sequenceDiagram
    participant HW as Hardware / SDK
    participant SY as Syncd (NotificationHandler)
    participant RD as Redis (ASIC_STATE)
    participant OA as Orchagent / App

    Note over HW,OA: 1. Initialization Phase
    SY->>HW: sai_create_switch(..., attr_list_with_callback)
    Note right of SY: Bind local callback\n(SwitchNotifications::onOtnAlarmEvent)
    HW-->>SY: Success
    Note over HW,OA: SAI_SWITCH_ATTR_OTN_ALARM_EVENT_NOTIFY (Create Switch)

    Note over HW,OA: 2. Event Trigger Phase
    HW->>HW: Detect OTN Alarm
    HW->>SY: Invoke Callback (onOtnAlarmEvent)
    Note right of SY: NotificationHandler::onOtnAlarmEvent
    SY->>SY: Serialize Data (sai_serialize_otn_alarm_event_ntf)
    SY->>SY: Enqueue (enqueueNotification)

    Note over HW,OA: 3. Processing and Distribution Phase
    loop NotificationProcessor Thread
        SY->>RD: PUBLISH ASIC_STATE (Notification Name + Data)
    end
    Note right of RD: Channel: SAI_SWITCH_NOTIFICATION_NAME_OTN_ALARM_EVENT

    Note over HW,OA: 4. Consumption Phase
    RD-->>OA: Message Received
    OA->>OA: Deserialize Data (sai_deserialize_otn_alarm_event_ntf)
    OA->>OA: Handle Business Logic (handle Alarm)
```

#### 9.4.3 OTN Notification Definition and NBI 

***Single Generic Notification for OTN***
As mentioned before, SONiC only support notification mechanism at root `switch` object. Therefore it is more efficient to introduce single generic notification for OTN device, instead of add large number of low level notifications, which would requires code change the existing code path for each notification. 

```c
/**
 * @brief OTN alarm event data
 */
typedef struct _sai_otn_alarm_event_data_t
{
    /** OTN object id */
    sai_object_id_t object_id;
    /** OTN event name, string */
    sai_u8_list_t event_name;
    /** OTN event timestamp */
    sai_timespec_t timestamp;
    /** OTN event severity */
    sai_otn_alarm_severity_t severity;
    /** OTN event action */
    sai_otn_alarm_action_t action;
    /** OTN event description, string */
    sai_u8_list_t description;
    /** OTN event binary data payload */
    sai_u8_list_t data;
} sai_otn_alarm_event_data_t;
```
In the top-level notification handler in `otndeviceorch`, further processing at object level can be performed. By translating the object_id to an NBI component name (e.g. OA0-0), the event handler of each object type can be invoked.

***NBI event delivery and retrieve***
There are a few mechanisms to deliver events/alarms to the NBI:
- gNMI subscription (get and on-change)
- syslog notification to management syslog server
- REST and CLI to get current active alarm or alarm history from Event DB.

OTN currently reuses the existing [SONiC event alarm framework](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md) as is. Note that the [code](https://github.com/sonic-net/sonic-buildimage/pull/22617) has not merged yet. [Other work](https://github.com/sonic-net/sonic-platform-daemons/pull/421) is ongoing on fault management on top of the event alarm framework.

Upon receiving an event from syncd, SWSS can notify the event/alarm by
- Writing the event into syslog. Using the event alarm framework syslog plugin mechanism, each OTN device can specify which syslog events should be written to the Event DB. Example [here](https://github.com/sonic-molex/sonic-buildimage/blob/202411_otn/device/molex/x86_64-otn-kvm_x86_64-r0/default.json)
- SWSS OTN notification handler can also write the event to Event DB directly using event alarm framework APIs.

The following sequence diagram shows OTN alarm/event flow from vendor SAI through orchagent, syslog (SWSS) / rsyslog (host), eventd (eventd-ocs) with default.json (device-specific) mapping, external eventdb (e.g. Redis), to gNMI. Configuration files (`platform.conf`, `platform-regex.json`) are COPY-deployed from the eventd container to the host.

```mermaid
%%{init: {'sequence': {'actorMargin': 14, 'width': 88, 'boxMargin': 6, 'messageMargin': 18}}}%%
sequenceDiagram
    participant vsai as vendor SAI
    participant OA as orchagent
    participant syslog_sw as syslog (SWSS)
    participant rsyslog_host as rsyslog (host)
    participant eventd as eventd
    participant dc as default.json<br/>(device specific)
    participant edbe as eventdb (Redis)
    participant gnmi as gNMI<br/>syslog server

    eventd->>dc: map
    dc->>eventd: map
    eventd->>rsyslog_host: COPY syslog-plugin to host

    vsai->>OA: alarm / event
    OA->>syslog_sw: syslog message
    syslog_sw->>rsyslog_host: forward
    rsyslog_host->>eventd: deliver
    eventd->>edbe: persist
    edbe->>gnmi: notification
```

### 9.5 OTN PM Statistics Support (***New feature***)

This section describes how to support OTN PM statistics counters.

Current SONiC does not support traditional telecom performance management (PM) historical counters.
- 96 (32) buckets of 15-minute counters including min, max and average.
- 7 bucket of 24-hour counters with min, max and average.

#### 9.5.1 PM Design Objective:
- It is an additional new feature should be modular and not coupled with current SONiC logic and code base
- It should be generic and support all vendor's device. 
- Which PM parameters to collect should be configurable at device level. So that each device can specify the PM counter set.

#### 9.5.2 Design Proposal

The first design choice is where the PM mechanism should be hosted. It could be an independent container, or it can run inside the PMON container, which is used more for system monitoring.

Secondly, PM is an application-level feature and should depend on existing data; the status data in State DB tables is an obvious choice.

#### 9.5.3 Yang model and Redis Schema
Since there is no PM standard openconfig yang model for PM management, a new sonic yang is defined for PM management.

Please see [sonic-otn-pm.yang](https://github.com/sonic-molex/sonic-buildimage/blob/jimmy/src/sonic-yang-models/yang-models/sonic-otn-pm.yang) (TBD).

The corresponding Redis schema is shown as following:

```json
Config DB schema
================
OTN_PM
;Config: which PM parameters to collect per resource type. Key = OTN state table name.
;Each attribute name is a pm-name; the table may have any number of such attributes.
key                 = OTN_PM|resource_type   ; resource_type = OTN state table name (e.g. OTN_OA_TABLE, OTN_ATTENUATOR_TABLE)
;field              = value
;attributes         = 0..n, field name = pm-name (e.g. input-power-total, actual-gain, temperature), value = STRING (e.g. "true" to enable)

// PM configuration example, the configuration is part of device level config
{
  "OTN_PM": {
    "OTN_OA_TABLE": {
      "input-power-total": "true",
      "output-power-total": "true",
      "actual-gain": "true",
      "temperature": "true"
    },
    "OTN_ATTENUATOR_TABLE": {
      "actual-attenuation": "true",
      "input-power-total": "true",
      "output-power-total": "true"
    }
  }
}

State DB schema
===============
OTN_PM_TABLE
;/sonic-otn-pm:sonic-otn-pm/OTN_PM/OTN_PM_LIST
;Performance management: current and historical (15min, 24hour) bins. granularity current uses bin-number 0.
key                 = OTN_PM_TABLE|resource-name|pm-name|granularity|bin-number  ; string
;field              = value
resource-name       = STRING                 ; e.g. OA0-0, Chassis, Fan-0, VOA0-0
pm-name             = STRING                 ; e.g. input-power-total, temperature, actual-gain
granularity         = STRING                 ; enum: current, 15min, 24hour
bin-number          = uint16                 ; 0 for current; 1..96 for 15min; 1..7 for 24hour
min                 = float64                ; minimum in period
max                 = float64                ; maximum in period
avg                 = float64                ; average in period
timestamp           = STRING                 ; for current: start time; for historical: completion time (ISO 8601)
validity            = STRING                 ; enum: valid, invalid, questionable
```
Please note that which parameters to collect is device-specific. Following the SONiC design, configuration files for all devices belonging to a platform are included in the SONiC image; at startup, only those for the specific device are used. 

The following diagram shows how sonic-pm in the PMON container interacts with Config DB, State DB, and History DB for PM configuration, real-time collection, and counter updates.

```mermaid
%%{init: {'sequence': {'actorMargin': 22, 'width': 95, 'boxMargin': 5, 'messageMargin': 16, 'useMaxWidth': false}, 'themeVariables': {'fontSize': '10px'}}}%%
sequenceDiagram
    participant cfg as Config DB<br/>PM config
    participant pm as sonic-pm<br/>(PMON container)
    participant state as State DB<br/>OTN object status
    participant hist as History DB<br/>PM counter table

    cfg->>pm: Read config
    state->>pm: Collect real time value periodically
    pm->>hist: Update PM counters
```

### 9.6 Reuse SONiC Existing Features

SONiC is a mature NOS, which provides most system management features. These features can be used for OTN devices as-is without any changes.

#### 9.6.1 Management and Loopback Interface

OTN devices support at least one DCN interface for device management (NBI).

There are a few alternative ways to configure a static IP address for the management interface.

- Use Click CLI:

```
admin@OTN001:~$ config interface ip add eth0 <ip_addr> <default gateway IP>
```

- Use config_db.json and configure the MGMT_INTERFACE key with the appropriate values. See the config of management interface [here](https://github.com/sonic-net/SONiC/wiki/Configuration#management-interface).

- The same method can be used to configure the Loopback interface address.
  - /sbin/ifconfig lo Linux command shall be used. OR,
  - Add the key LOOPBACK_INTERFACE and value in config_db.json and load it.

Additionally, the management interfaces should support L3 routing protocols, OSPF, and BGP.

#### 9.6.2 TACACS+ AAA

Please see [here](https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md).

#### 9.6.3 Syslog

Please see [here](https://github.com/sonic-net/SONiC/blob/master/doc/syslog/syslog-design.md).

#### 9.6.4 NTP

Please see [here](https://github.com/sonic-net/SONiC/blob/master/doc/ntp/ntp-design.md).


#### 9.6.5 SONiC upgrade

Please see [here](https://github.com/sonic-net/SONiC/wiki/SONiC-to-SONiC-update).

## 10. Warmboot and Fastboot Design Impact  

OTN support does not depend on or affect current SONiC warmboot and fastboot behavior. Warm reboot should remain a non-service-affecting (NSA) operation.

## 11. Memory Consumption

In an OTN device, most packet features are not enabled in SWSS (configMgr and Orchagent). Therefore, memory consumption is lower than in a packet switch.

## 12. Restrictions/Limitations  

N/A

## 13. Testing Requirements/Design  (**TBD**)

### 13.1. Unit Test cases  

### 13.2. System Test cases

## 14. Open/Action items - if any

### 14.1 Asynchronous Config Validation 

Currently, the SONiC management framework CVL validates the configuration data from NBI against the Redis schema defined by sonic-yang. This ensures that the data written to Redis is semantically correct.

Sometimes this is not enough due to lack of optical domain business logic check. An example would be the value range check, which can only be done in orchagent or even SAI driver. For example, if a user sets gain to an out-of-range value (40dB), it would be successfully stored in the config DB. But the oaorch or SAI driver would reject it, as shown in the following diagram.

```mermaid
%%{init: {'themeVariables': {'noteBkgColor': '#ffebee', 'noteTextColor': '#c62828', 'noteBorderColor': '#c62828', 'altSectionBkgColor': '#ffebee', 'altSectionTextColor': '#c62828', 'altSectionBorderColor': '#c62828', 'criticalSectionBkgColor': '#ffebee', 'criticalSectionTextColor': '#c62828', 'criticalSectionBorderColor': '#c62828', }}}%%
sequenceDiagram
    participant CLI as CLI/REST/gNMI
    participant ConfigDB as Config-DB
    participant orchagent as orchagent
    participant syncd
    participant Vendor as Vendor driver
    participant StateDB as State DB

    CLI->>ConfigDB: Set (Async)
    ConfigDB->>orchagent: sub
    Note over orchagent: Error
    orchagent->>syncd: update
    syncd->>Vendor: SAI Set
    Note over Vendor: Error
    critical Error from driver
        Vendor-->>syncd: Error
    end
    syncd->>StateDB: update
    StateDB-->>CLI: status
```


How is the failure handled if the config change does not pass the business logic validation? SONiC configuration is managed asynchronously, i.e., the config will be accepted and stored in the config DB even if low-level/HW processing fails. Possible solutions include:
- Make all set requests synchronous.
- Send notification to the NBI for config failure.

### 14.2 Threshold Management  (**TBD**)

Optical devices require various thresholds to check signal quality. 
