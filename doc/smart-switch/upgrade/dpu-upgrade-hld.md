# Independent DPU Upgrade #

## Table of Content

### 1. Revision

| Rev | Date       | Author           | Change Description |
| --- | ---------- | ---------------- | ------------------ |
| 0.1 | 01/23/2025 | Dawei Huang | Initial version    |

### 2. Scope

This document describes the high-level design of the sequence to independently upgrade a SmartSwitch DPU with minimal impact to other DPUs and the NPU, through GNOI API.

### 3. Definitions/Abbreviations

| Term  | Meaning                                   |
| ----- | ----------------------------------------- |
| DPU   | Data Processing Unit                      |
| gNMI  | gRPC Network Management Interface         |
| gNOI  | gRPC Network Operations Interface         |
| NPU   | Network Processing Unit                   |
| ASIC  | Application Specific Integrated Circuit   |
| HA	| High Availability                         |

### 4. Overview
Smart Switch offers comprehensive network functionality similar to traditional devices, combined with the flexibility and scalability of cloud services. It includes one switch ASIC (NPU) and multiple DPUs, with DPU ASICs connected only to the NPU, and all front panel ports linked to the NPU.

The individual DPU upgrade process is designed to minimize the impact on the network, the NPU and other DPUs. It is orchestrated by external clients through the gNOI API. The upgrade process mainly consists of the following steps:
* Download/Transfer the new firmware image to the DPU.
* Install and activate the new firmware image on the DPU.
* Reboot the DPU to apply the new firmware image.

The main chanllege of the DPU upgrade is that several DPU containers, such as Database, GNMI and HA are offloaded to the NPU. The upgrade process will also need to upgrade these offloaded containers. In addition, since the DPU is only connected to the NPU, additional systems are also needed to facilitate the communication between the external client and the DPU.

### 5. Requirements

1. External client should be able to drive the DPU upgrade process through the gNOI API.
2. The upgrade process should have minimal impact on the network, the NPU and other DPUs.
3. The upgrade process should be able to upgrade the offloaded containers on the DPU.
4. The offloaded containers should always be in sync with the DPU firmware version.

### 6. Architecture Design

This section covers the changes that are required in the SONiC architecture. In general, it is expected that the current architecture is not changed.
This section should explain how the new feature/enhancement (module/sub-module) fits in the existing architecture.

If this feature is a SONiC Application Extension mention which changes (if any) needed in the Application Extension infrastructure to support new feature.

### 7. High-Level Design

This section covers the high level design of the feature/enhancement. This section covers the following points in detail.

	- Is it a built-in SONiC feature or a SONiC Application Extension?
	- What are the modules and sub-modules that are modified for this design?
	- What are the repositories that would be changed?
	- Module/sub-module interfaces and dependencies.
	- SWSS and Syncd changes in detail
	- DB and Schema changes (APP_DB, ASIC_DB, COUNTERS_DB, LOGLEVEL_DB, CONFIG_DB, STATE_DB)
	- Sequence diagram if required.
	- Linux dependencies and interface
	- Warm reboot requirements/dependencies
	- Fastboot requirements/dependencies
	- Scalability and performance requirements/impact
	- Memory requirements
	- Docker dependency
	- Build dependency if any
	- Management interfaces - SNMP, CLI, RestAPI, etc.,
	- Serviceability and Debug (logging, counters, trace etc) related design
	- Is this change specific to any platform? Are there dependencies for platforms to implement anything to make this feature work? If yes, explain in detail and inform community in advance.
	- SAI API requirements, CLI requirements, ConfigDB requirements. Design is covered in following sections.

### 8. SAI API

No change to SAI API is required for this feature.

### 9. Configuration and management
This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.
If there is breaking change which may impact existing platforms, please call out in the design and get platform vendors reviewed.

#### 9.1. Manifest (if the feature is an Application Extension)

Paste a preliminary manifest in a JSON format.

#### 9.2. CLI/YANG model Enhancements

This sub-section covers the addition/deletion/modification of CLI changes and YANG model changes needed for the feature in detail. If there is no change in CLI for HLD feature, it should be explicitly mentioned in this section. Note that the CLI changes should ensure downward compatibility with the previous/existing CLI. i.e. Users should be able to save and restore the CLI from previous release even after the new CLI is implemented.
This should also explain the CLICK and/or KLISH related configuration/show in detail.
https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md needs be updated with the corresponding CLI change.

#### 9.3. Config DB Enhancements

This sub-section covers the addition/deletion/modification of config DB changes needed for the feature. If there is no change in configuration for HLD feature, it should be explicitly mentioned in this section. This section should also ensure the downward compatibility for the change.

### 10. Warmboot and Fastboot Design Impact
Mention whether this feature/enhancement has got any requirements/dependencies/impact w.r.t. warmboot and fastboot. Ensure that existing warmboot/fastboot feature is not affected due to this design and explain the same.

### 11. Memory Consumption
This sub-section covers the memory consumption analysis for the new feature: no memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration.
### 12. Restrictions/Limitations

### 13. Testing Requirements/Design
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below.

#### 13.1. Unit Test cases

#### 13.2. System Test cases

### 14. Open/Action items - if any


NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.