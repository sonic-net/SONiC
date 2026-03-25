# HLD Name #

## Table of Content 

### 1. Revision  

### 2. Scope  

Historically, `sfputil` has assumed a 1:1 relationship between a logical port and a single SFP-like device that exposes a flat EEPROM, power control and low-power mode. With co-packaged optics (CPO), ports can instead be backed by composite SFPs that internally aggregate multiple I2C-configurable devices (typically an optical engine and an external laser source), each of which has its own EEPROM contents and control bits.

The CPO port-mapping HLD (/doc/platform/port_mapping_for_cpo.md) introduces the composite SFP abstraction and the `optical_devices.json` data model that describe how these internal devices are wired to interfaces. This document focuses on the CLI and control-plane aspects: extending `sfputil` so that operators can reason about and manipulate composite SFPs in a predictable way, using familiar commands, regardless of whether a port is backed by a single device or a composite CPO stack.

As a result, `sfputil` needs to support the following:

- Provide a consistent user experience for core xcvr operations (`read-eeprom`, `write-eeprom`, `power`, `lpmode`, `reset`, `show`, and some debug commands) on both single-device and composite SFPs.
- Allow users to explicitly select an underlying device (for example, optical engine vs. external laser source) when operating on a CPO-backed DUT, while still behaving naturally for traditional non-composite ports.
- Handle platforms where CPO hardware is managed either via separate devices or via a joint-mode that presents a unified EEPROM view, including cases where an explicit device selector is required to disambiguate accesses.
- Surface clear, actionable error messages when commands are ambiguous (for example, attempting to read EEPROM on a composite SFP without specifying a device) or when a requested operation is not applicable to a given internal device.
- Integrate with existing platform APIs for composite SFPs to locate the appropriate internal device(s) for a logical port and route operations accordingly, without requiring broader architectural changes. Part of this is already proposed in the CPO port-mapping HLD.

This HLD does not redefine the composite SFP or `optical_devices.json` models themselves; those are covered by the CPO port-mapping HLD. The scope here is limited to changes in `sfputil` and closely-related CLI behavior necessary to make CPO-backed ports manageable in day-to-day operations.

### 3. Definitions/Abbreviations 

This section covers the abbreviation if any, used in this high-level design document and its definitions.

### 4. Overview 

This HLD describes how `sfputil` will be extended to understand composite SFPs introduced by co-packaged optics (CPO) hardware, and how those extensions fit into the existing SONiC platform API and CPO port-mapping model.

From an user's perspective, the goal is that common transceiver workflows continue to "just work" when a port is backed by multiple internal devices (for example, an optical engine and an external laser source), while still preserving full control over each device when needed. Note that this does not mean that the same commands used for non-composite SFPs will always work for composite SFPs.

- `sfputil` must be able to discover and display the set of internal devices associated with a given logical port, including their types, banks and identifying information.
- Core operations such as reading/writing EEPROM, toggling power, entering/exiting low-power mode and resetting a transceiver must work uniformly on:
  - traditional single-device ports, and
  - composite CPO ports where multiple devices share responsibility for a single interface.
- For composite ports, `sfputil` must provide a way to explicitly target a particular internal device (for example, OE vs. ELS) when issuing these operations, while remaining backward compatible for non-composite ports.
- Platforms that implement CPO in different ways (separate devices vs. joint-mode MCU) must be able to plug into the same `sfputil` behavior using the composite SFP platform APIs and `optical_devices.json` topology information defined in the CPO port-mapping HLD.

At a high level, the design in this document introduces:

- A mechanism to enumerate and name the internal devices backing each logical port, exposed via `sfputil`.
- A small set of CLI extensions (for example, an optional device selector argument) that are applied consistently across the relevant `sfputil` subcommands.
- Clear error-reporting semantics for ambiguous or unsupported operations on composite ports.

These changes are intentionally scoped to `sfputil` and its interaction with existing platform APIs. No changes to SAI, the underlying composite SFP abstraction, or the `optical_devices.json` schema are proposed here; those are treated as prerequisites and building blocks for the behavior defined in this HLD.

### 5. Requirements

This section list out all the requirements for the HLD coverage and exemptions (not supported) if any for this design.

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

This section covers the changes made or new API added in SAI API for implementing this feature. If there is no change in SAI API for HLD feature, it should be explicitly mentioned in this section.
This section should list the SAI APIs/objects used by the design so that silicon vendors can implement the required support in their SAI. Note that the SAI requirements should be discussed with SAI community during the design phase and ensure the required SAI support is implemented along with the feature/enhancement.

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

### Warmboot and Fastboot Performance Impact
This sub-section must cover the impact of the functionality on warmboot and fastboot performance, that is control plane and data plane downtime.
As part of the analysis cover the flowing:

- Does this feature add any stalls/sleeps/IO operations to the boot critical chain? Does it change when this feature is disabled/unused? 
- Does this feature add any additional CPU heavy processing (e.g. rendering Jinja templates) in the boot path (process, library or utility used during boot up)? Does it change when this feature is disabled/unused?
- In case this feature updates a third party dependency does it cause any impact on boot time performance?
- Can the feature (service or docker) be delayed?
- What are the possible optimizations and what is the expected boot time degradation if, by the nature of the feature, additional CPU/IO costs can't be avoided?

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