# HLD Name #

## Table of Content 

### 1. Revision  

### 2. Scope  

This section describes the scope of this high-level design document in SONiC.

### 3. Definitions/Abbreviations 

This section covers the abbreviation if any, used in this high-level design document and its definitions.

### 1. Overview 

The purpose of this section is to give an overview of high-level design document and its architecture implementation in SONiC. 

### 2. Requirements

This section list out the basic requirements for the HLD coverage and exemptions (not supported) if any for this design.

### 3. Architecture Design 

This section covers the changes that are required in the SONiC architecture and explains how the module/sub-module fits in the architecture. 

### 4. High-Level Design 

This section covers the high level design of the feature/enhancement. This section covers the following points in detail.
		
		- What are the modules and sub-modules that are modfiied for this design?
        - What are the repositories that would be changed?
		- Module/sub-module interfaces and dependencies. 
		- SWSS and Syncd changes in detail
		- DB and Schema changes (APP_DB, ASIC_DB, COUNTERS_DB, LOGLEVEL_DB, CONFIG_DB, STATE_DB)
		- Sequence diagram if required.
        - Linux dependencies and interface
        - Warm reboot dependencies
        - Scalability and performance requirements/impact
        - Memory requirements
        - Docker dependency
        - Build dependency if any
        - Management interfaces - SNMP, CLI, RestAPI, etc.,
        - Is this change specific to any platform? Are there dependencies for platforms to implement anything to make this feature work? If yes, explain in detail and inform community in advance.
		- SAI API requirements, CLI requirements, ConfigDB requirements. Design is covered in following sections.

### 5. SAI API 

This section covers the changes made or new API added in SAI API for implementing this feature. If there is no change in SAI API for HLD feature, it should be explicitly mentioned in this section.

### 6. CLI Enhancements 

This section covers the addition/deletion/modification of CLI changes needed for the feature in detail. If there is no change in CLI for HLD feature, it should be explicitly mentioned in this section. Note that the CLI changes should ensure downward compatibility with the previous/existing CLI. i.e. Users should be able to save and restore the CLI from previous release even after the new CLI is implemented. 

### 7. Config DB Enhancements  

This section covers the addition/deletion/modification of config DB changes needed for the feature. If there is no change in configuration for HLD feature, it should be explicitly mentioned in this section. This section should also ensure the downward compatibility for the change. 
		
### 8. Restrictions/Limitations  

### 9. Unit Test cases  

### 10. Open/Action items - if any 

	
