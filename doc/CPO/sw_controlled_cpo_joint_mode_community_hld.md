# SW-controlled CPO in Joint Mode

## Table of Contents

1. [Revision](#1-revision)
2. [Overview](#2-overview)
3. [Definitions/Abbreviations](#3-definitionsabbreviations)
4. [Scope](#4-scope)
5. [Requirements](#5-requirements)
6. [Architecture Design](#6-architecture-design)
7. [High-Level Design](#7-high-level-design)
8. [SAI API](#8-sai-api)
9. [Configuration and management](#9-configuration-and-management)
   - 9.1. [Manifest (if the feature is an Application Extension)](#91-manifest-if-the-feature-is-an-application-extension)
   - 9.2. [CLI/YANG model Enhancements](#92-cliyang-model-enhancements)
   - 9.3. [Config DB Enhancements](#93-config-db-enhancements)
10. [Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
11. [Memory Consumption](#11-memory-consumption)
12. [Restrictions/Limitations](#12-restrictionslimitations)
13. [Testing Requirements/Design](#13-testing-requirementsdesign)
14. [Open/Action items](#14-openaction-items---if-any)

---
<br>

## 1. Revision

| Rev | Date       | Author       | Change Description |
|-----|------------|--------------|--------------------|
| 0.1 | 2026-03-31 | Tomer Shalvi | Initial version.   |

<br>

## 2. Overview

**CPO (Co-Packaged Optics)** is a system architecture in which optical components are integrated directly with the switch ASIC, rather than implemented as external pluggable transceivers (e.g., QSFP-DD, OSFP). This integration reduces electrical trace length and improves overall system power efficiency.

At the hardware level, a CPO module is composed of:
* **Optical Engine (OE)** — responsible for electrical-to-optical and optical-to-electrical signal conversion.
* **External Laser Source (ELS)** — providing continuous laser light used by the Optical Engines for transmission.

CPO systems support two operational models:
* **Separate Mode**, where the host directly accesses and manages the underlying components (e.g., OEs and ELSs). See *port_mapping_for_cpo.md* section 2 and *CPO-support-in-SONiC.mds* section 2.
* **Joint Mode**, where the host interacts with aCPO module abstraction, without directly managing the underlying components.

To preserve compatibility with existing SONiC and SAI workflows, we introduce a **Virtual CPO Module (or vModule)** that mimcs the behavior of a trandtional optical module by providing a logical abstraction that exposes a single unified CMIS interface for both the integrated Optical Engine (OE) and External Laser Sources (ELS).

A vModule exposes **32 lanes**, compared to 8 lanes in standard pluggable modules. transceiver. More information regarding 32-lane modules support can be found in *cmis_banking_support.md* section 7.8.

<br>


![vModule3.png](vModule3.png)

## 3. Definitions/Abbreviations

| Term   | Definition |
|--------|------------|
| CPO    | Co-Packaged Optics |
| CMIS   | Common Management Interface Specification |
| vModule| Virtual Module |
| ELS    | External Laser Source |
| OE     | Optical Engine |
| SM     | State Machine |
| FW     | Firmware |
| SW     | Software |
| EEPROM | Electrically Erasable Programmable Read-Only Memory |
| DOM    | Digital Optical Monitoring |

<br>


## 4. Scope

This document defines the **SW-controlled CPO in Joint Mode**, where SONiC sees CPO modules and interacts with them through the CPO abstraction layer, leveraging the existing CMIS-based host management flows.

Note: the **Separate Mode**, where the host system directly interacts with and manages the underlying optical hardware components is defined in *port_mapping_for_cpo.md* section 2 and *CPO-support-in-SONiC.mds* section 2.

The main objective of this document is to demonstrate that supporting Joint Mode:
* Does **not require fundamental changes** to the SONiC architecture.
* Requires only **minor extensions in the generic CMIS host management logic**.
* Relies on **platform-level implementations as defined in existing community HLDs**, with platform-specific behavior described where applicable.

This document builds on existing community HLDs and extends them to support Joint Mode, without redefining them:
* [port_mapping_for_cpo](https://github.com/nexthop-ai/SONiC/blob/274228b44de9edbbf6f1585c9bb7392853cbbc08/doc/platform/port_mapping_for_cpo.md)
* [cmis_banking_support](https://github.com/bobby-nexthop/SONiC/blob/0b09f1cc3e91853fcbabb29efb76fa6ea4b9647d/doc/layer1/cmis_banking_support.md)
* [CPO-support-in-SONiC](https://github.com/KroosMicas/SONiC/blob/41a20d3a4bd62a56292c58f5813e6dd6f58a109f/doc/cpo/CPO-support-in-SONiC.md)  

### Out of Scope (Current Revision):

This revision of the HLD focuses on the **link-up flow for SW-controlled CPO ports in Joint Mode**.  
The following aspects are **not covered in this revision**, are currently **under development**, and will be addressed in future updates:

* DOM: Future support will extend the existing DOM flow to include additional ELS monitoring statistics, requiring access to ELS data exposed via the CPO abstraction EEPROM and publishing it to the relevant databases.  
* Error handling: A protection mechanism will be introduced to handle CPO-related faults (e.g., thermal events and laser power anomalies).  
* Firmware upgrade: Firmware upgrade support for CPO modules is out of scope for this revision and will be defined in a future update.  
* CLI enhancements: Additional CLI command for CPO vendor-specific error statuses.  

<br>


## 5. Requirements

**Functional Requirements:**
* Support CPO abstraction layer that exposes one or more CPO (virtual) modules, each module has OE and ELS, and is accessible via a single CMIS interface. 
* While working in CPO Joint Mode, the system shall work directly with the CPO abstraction.
* The system shall support correct instantiation of the transceiver object for CPO modules (module type id 0x80).
* The system shall allow CPO modules to be configured via the existing CMIS state machine.
* The system shall support a CPO-specific CMIS memory map, extending the standard CMIS memory map to include ELS-related fields and support vendor-specific field definitions.
* The system shall support vendor-specific EEPROM layouts within the CPO memory map.

**Non-Functional Requirements:**
* The solution shall maximize the reuse of existing CMIS infrastructure to avoid changing generic code.
* The solution shall remain aligned with existing community HLDs without redefining them.

<br>


## 6. Architecture Design

## 7. High-Level Design

In Joint Mode, SONiC continues to operate using the existing CMIS host management architecture, using exactly the same xcvrd threads, without introducing changes to the overall control flow.

As a result, the following extensions are needed:

**1. Extending the module type ID ↔ transceiver API mapping** to include the CPO module type 0x80 (xcvr_api_factory).

```python
def create_xcvr_api(self):
    id = self._get_id()

    id_mapping = {
        0x18: (self._create_cmis_api, ()),
        0x19: (self._create_cmis_api, ()),
        0x80: (self._create_cmis_api, (CmisCpoMemoryMap)),
        ...
    }
```

This change also introduces a new memory map: **CmisCpoMemoryMap**.

The EEPROM exposes both the standard CMIS data and additional ELS-related information. To support this, CmisCpoMemoryMap extends the existing CMIS memory map by:
* Incorporating ELS-related fields based on the ELSFP specification.
* Allowing vendor-specific fields to be defined and accessed through this memory map.

Unlike existing generic CMIS memory maps, the CPO memory map supports vendor-specific fields. It accepts an optional dictionary of field definitions at init time, allowing each vendor to inject its own page layouts.

Note: This simplifies things to the NOS in comparison to Separate mode, where two new memory maps are suggested - see section 6.2.5 in *CPO-support-in-SONiC.md*.


**2. Extending the list of recognized CMIS module types** to allow CPO modules to be handled by the CMIS state machine.  
<br>

**Platform Implementation Alignment**  
From the platform implementation perspective, the design aligns completely with the approaches described in the community HLDs:

* As described in the *cmis_banking_support.md* (section 7.8.2), the platform will expose one SFP object per bank. This structure in Joint mode is illustrated below:

    ![sfp_object_structure_2.png](sfp_object_structure_2.png)

    * Lane-to-SFP object mapping is not handled in generic SONiC logic and is instead implemented in the platform layer.
    * Platform code also handles plug-in/plug-out events: The CPO abstraction in Joint mode allows SONiC to interact with the module as if it were a traditional pluggable device, including handling plug-in and plug-out events of the ELS. The chassis continues to listen for change events from the lower layers and notifies *xcvrd* accordingly. The key difference is that, instead of monitoring physical pluggable modules, the system now monitors CPO modules. This approach enables maximal reuse of the existing codebase and results in minimal changes required to support SW-controlled operation in Joint mode.
    * This structure explains why no changes are required in the CMIS state machine logic: The CMIS state machine operates at the **logical port level**, where the list of logical ports is derived from the *CONFIG_DB.PORT table*. This model remains unchanged in Joint Mode. With the SFP-per-bank approach:
        * Each SFP object continues to represent up to 8 lanes.
        * Multiple logical ports may share the same module index, as in existing pluggable module implementations.
        * As a result, from the CMIS state machine perspective, the system behavior remains unchanged, regardless of whether the underlying 8-lane unit is a traditional pluggable transceiver or an sfp object.

* As described in the *port_mapping_for_cpo.md* section 7.3.2, the SFP objects will follow the same structure, including references to the underlying OE and ELS components, together with the associated bank index (*cmis_banking_support.md* section 7.8.3). The instantiation of these SFP objects will be done in platform chassis (*port_mapping_for_cpo.md* section 7.3.3) and rely on platform configuration files (e.g., a JSON file similar to `optical_devices.json`, as proposed in *port_mapping_for_cpo.md* section 7.1).

<br>


## 8. SAI API

## 9. Configuration and management

### 9.1. Manifest (if the feature is an Application Extension)

### 9.2. CLI/YANG model Enhancements

In addition to the bank-aware EEPROM access commands introduced in *cmis_banking_support.md* (section 7.9), and the `show interfaces transceiver` CLI enhancements introduced in *CPO-support-in-SONiC.md* (section 6.2.11), this design introduces an update to the following CLI command for monitoring CPO-specific error statuses:

**Syntax:**
`show interfaces transceiver error-status [<interface_name>] [-hw]`

This command extends the existing transceiver status reporting to include **CPO vendor-specific error conditions**, such as laser or fiber-related failures.

```text
show interfaces transceiver error-status [<interface_name>] [-hw]

Port         Error Status
-----------  ---------------
Ethernet0    OK
Ethernet4    OK
Ethernet8    Laser high power
Ethernet12   Fiber check failure
...
```

### 9.3. Config DB Enhancements

No Config DB changes are required (Except for the *associated_devices* field added to the *CONFIG_DB.PORT table*, mentioned in *port_mapping_for_cpo.md*, section 9.2).

<br>


## 10. Warmboot and Fastboot Design Impact

## 11. Memory Consumption

## 12. Restrictions/Limitations

## 13. Testing Requirements/Design

## 14. Open/Action items - if any

