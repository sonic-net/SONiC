# Sonic Port FEC BER #

## Table of Content 
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviation](#abbreviations)
- [1 Overview](#1-overview)
  - [1.1 Functional requirements](#11-functional-requirements)
  - [1.2 CLI requirements](#12-cli-requirements)
- [2 Architecture Design](#2-architecture-design)
- [3 High level design](#3-high-level-design)
  - [3.1 SAI counters used](#31-sai-counters-used)
  - [3.2 Calculation formulas](#32-calculation-formulas)
    - [3.2.1 Byte rate](#321-byte-rate)
    - [3.2.2 Packet rate](#322-packet-rate)
    - [3.2.3 Utilization](#323-utilization)

### Revision  

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 |             | Vincent (Ping Ching) Ng| Initial version                   |

### Scope  

  This document provide information about the implementation of Port Forward Error Correction (FEC) Bit Error Rate (BER) measurement. 
  This calculation include correctable bits and uncorrectable bits

### Abbreviations 

  FEC        - Forward Error Correction.  
  BER        - Bits Error Rate, measure in bit per second.  
  Pre FEC    - The number of bits which FEC successsfully correct.  
  Post FEC   - The number of bits which FEC fail to correct.  
  Frame      - size of each FEC block.  
  Symbol     - part of the FEC structure which the error detection and correction base on.  
  RS-FEC     - Reed Solomon Forward Error correction, RSFEC-544 = 5440 total size , RSFEC-528 = 5280 total size  

### 1 Overview 

  FEC is a common hardarew feature deployed in a high speed network. Due to the signal integeraty, date ingressing to a port might have bit(s) corrupted.
  The FEC will correct the data's corruptiom and increment error counters to account for corrected bits (Pre FEC) or uncorrected frame (Post FEC)

#### 1.1 Functional Requirements
  This HLD is to   
  - enhance the current "show interface counter fec-stat" to include Pre and Post BER statistic as new columns
  - Add Pre and Post FEC BER per interface into Redis DB for telemetry streaming
  - Calculate the Pre and Post FEC BER at the same intervale as the PORT_STAT poll rate which is 1 sec.

#### 1.2 CLI Requirements

  The existing "show interface counter fec-stat" will enhanced to include two additional columns with unit BER (b/s).   
  - Pre FEC BER
  - Post FEC BER
     
### 2 Architecture Design

There is no changes in the current Sonic Architecture. 


### 3 High-Level Design 

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

### SAI API 

This section covers the changes made or new API added in SAI API for implementing this feature. If there is no change in SAI API for HLD feature, it should be explicitly mentioned in this section.
This section should list the SAI APIs/objects used by the design so that silicon vendors can implement the required support in their SAI. Note that the SAI requirements should be discussed with SAI community during the design phase and ensure the required SAI support is implemented along with the feature/enhancement.

### Configuration and management 
This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.
If there is breaking change which may impact existing platforms, please call out in the design and get platform vendors reviewed. 

#### Manifest (if the feature is an Application Extension)

Paste a preliminary manifest in a JSON format.

#### CLI/YANG model Enhancements 

This sub-section covers the addition/deletion/modification of CLI changes and YANG model changes needed for the feature in detail. If there is no change in CLI for HLD feature, it should be explicitly mentioned in this section. Note that the CLI changes should ensure downward compatibility with the previous/existing CLI. i.e. Users should be able to save and restore the CLI from previous release even after the new CLI is implemented. 
This should also explain the CLICK and/or KLISH related configuration/show in detail.
https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md needs be updated with the corresponding CLI change.

#### Config DB Enhancements  

This sub-section covers the addition/deletion/modification of config DB changes needed for the feature. If there is no change in configuration for HLD feature, it should be explicitly mentioned in this section. This section should also ensure the downward compatibility for the change. 
		
### Warmboot and Fastboot Design Impact  
Mention whether this feature/enhancement has got any requirements/dependencies/impact w.r.t. warmboot and fastboot. Ensure that existing warmboot/fastboot feature is not affected due to this design and explain the same.

### Memory Consumption
This sub-section covers the memory consumption analysis for the new feature: no memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration. 
### Restrictions/Limitations  

### Testing Requirements/Design  
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
