# SONiC 200G SerDes/1.6T Support

## Table of Content

### 1\. Revision

| Rev | Date | Author | Change Description |
| :---- | :---- | :---- | :---- |
| 1.0 | \<date of posting\> | bobby-nexthop | Initial Version |

### 2\. Scope
This document describes the following enhancements to the SONiC OS:

- Changes required to support 1.6T operation and speeds utilizing 200G SerDes rates.
- Support for new transceiver types.
- Updates to utilities and show commands.

### 3\. Definitions/Abbreviations

| Rev | Date | 
| :---- | :---- |
| SFF | Small Form Factor |
| SerDes | Serializer/Deserializer |

### 

### 4\. Overview

The IEEE P802.3dj taskforce is working on finalizing the amendment to the 802.3 spec. This amendment includes Media Access Control parameters for 1.6 Tb/s and Physical Layers and management parameters for 200 Gb/s, 400 Gb/s, 800 Gb/s, and 1.6 Tb/s operation. 

### 5\. Requirements

This section lists out all the requirements for the HLD coverage and exemptions (not supported) if any for this design.

### 7\. High-Level Enchancements

### 7.1 SFF-8024 Additions

Changes need to be made to the SFF Api to support the required host electrical interface IDs, MMF media interface IDs, and SMF media interface IDs.

#### 7.1.1 Host Electrical Interface

| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **Host Electrical Interface (Specification Reference)** | **Application Bit Rate (Gb/s)** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 30 | 200GBASE-CR1 (Clause179) | 212.5 | 1 | 106.25 | PAM4 |
| 31 | 400GBASE-CR2 (Clause179) | 425 | 2 | 106.25 | PAM4 |
| 87 | 800GBASE-CR4 (Clause179) | 850 | 4 | 106.25 | PAM4 |
| 88 | 1.6TBASE-CR8 (Clause179) | 1700 | 8 | 106.25 | PAM4 |
| 128 | 200GAUI-1 (Annex176E) | 212.5 | 1 | 106.25 | PAM4 |
| 129 | 400GAUI-2 (Annex176E) | 425 | 2 | 106.25 | PAM4 |
| 130 | 800GAUI-4 (Annex176E) | 850 | 4 | 106.25 | PAM4 |
| 131 | 1.6TAUI-8 (Annex176E) | 1700 | 8 | 106.25 | PAM4 |

#### 7.1.2 MMF Media Interface
| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **MM Media Interface (Specification Reference)** | **Application Rate** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 33 | 800G-VR4.2 | 850 | 8 | 53.125 | PAM4 |
| 34 | 800G-SR4.2 | 850 | 8 | 53.125 | PAM4 |

#### 7.1.3 SMF Media Interface
| |  |  |  |  |  |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **ID** | **SM Media Interface (Specification Reference)** | **Application Bit Rate (Gb/s)** | **Lane Count** | **Lane Signaling Rate (GBd)** | **Modulation** |
| 115 | 200GBASE-DR1 (Clause 180\) | 212.5 | 1 | 106.25 | PAM4 |
| 116 | 200GBASE-DR1-2 (Clause 181\) | 212.5 | 1 | 113.4375 | PAM4 |
| 117 | 400GBASE-DR2 (Clause 180\) | 425 | 2 | 106.25 | PAM4 |
| 118 | 400GBASE-DR2-2 (Clause 181\) | 425 | 2 | 113.4375 | PAM4 |
| 119 | 800GBASE-DR4 (Clause 180\) | 850 | 4 | 106.25 | PAM4 |
| 120 | 800GBASE-DR4-2 (Clause 181\) | 850 | 4 | 113.4375 | PAM4 |
| 121 | 800GBASE-FR4-500 (Clause 183\) | 850 | 4 | 106.25 | PAM4 |
| 122 | 800GBASE-FR4 (Clause 183\) | 850 | 4 | 113.4375 | PAM4 |
| 123 | 800GBASE-LR4 (Clause 183\) | 850 | 4 | 113.4375 | PAM4 |
| 127 | 1.6TBASE-DR8 (Clause 180\) | 1700 | 8 | 106.25 | PAM4 |
| 128 | 1.6TBASE-DR8-2 (Clause 181\) | 1700 | 8 | 113.4375 | PAM4 |

### 7.2 sonic-platform-daemons Support
sonic-platform-daemons will need to add 1.6T speed support to xcvrd.

### 7.3 sonic-utilities Support
CLI utilities will need to be updated to validate 1.6T speed tokens.

### 7.4 FLR Calculation

This is an enhancement 

```
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
```

### 8\. SAI API

This section covers the changes made or new API added in SAI API for implementing this feature. If there is no change in SAI API for HLD feature, it should be explicitly mentioned in this section. This section should list the SAI APIs/objects used by the design so that silicon vendors can implement the required support in their SAI. Note that the SAI requirements should be discussed with SAI community during the design phase and ensure the required SAI support is implemented along with the feature/enhancement.

### 9\. Configuration and management

This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required. If there is breaking change which may impact existing platforms, please call out in the design and get platform vendors reviewed.

#### 9.1. Manifest (if the feature is an Application Extension)

Paste a preliminary manifest in a JSON format.

#### 9.2. CLI/YANG model Enhancements

This sub-section covers the addition/deletion/modification of CLI changes and YANG model changes needed for the feature in detail. If there is no change in CLI for HLD feature, it should be explicitly mentioned in this section. Note that the CLI changes should ensure downward compatibility with the previous/existing CLI. i.e. Users should be able to save and restore the CLI from previous release even after the new CLI is implemented. This should also explain the CLICK and/or KLISH related configuration/show in detail. [https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md](https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md) needs be updated with the corresponding CLI change.

#### 9.3. Config DB Enhancements

This sub-section covers the addition/deletion/modification of config DB changes needed for the feature. If there is no change in configuration for HLD feature, it should be explicitly mentioned in this section. This section should also ensure the downward compatibility for the change.

### 10\. Warmboot and Fastboot Design Impact

Mention whether this feature/enhancement has got any requirements/dependencies/impact w.r.t. warmboot and fastboot. Ensure that existing warmboot/fastboot feature is not affected due to this design and explain the same.

### Warmboot and Fastboot Performance Impact

This sub-section must cover the impact of the functionality on warmboot and fastboot performance, that is control plane and data plane downtime. As part of the analysis cover the flowing:

- Does this feature add any stalls/sleeps/IO operations to the boot critical chain? Does it change when this feature is disabled/unused?  
- Does this feature add any additional CPU heavy processing (e.g. rendering Jinja templates) in the boot path (process, library or utility used during boot up)? Does it change when this feature is disabled/unused?  
- In case this feature updates a third party dependency does it cause any impact on boot time performance?  
- Can the feature (service or docker) be delayed?  
- What are the possible optimizations and what is the expected boot time degradation if, by the nature of the feature, additional CPU/IO costs can't be avoided?

### 11\. Memory Consumption

This sub-section covers the memory consumption analysis for the new feature: no memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration.

### 12\. Restrictions/Limitations

### 13\. Testing Requirements/Design

Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc., Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here. Example sub-sections for unit test cases and system test cases are given below.

#### 13.1. Unit Test cases

#### 13.2. System Test cases

### 14\. Open/Action items \- if any

NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.  
