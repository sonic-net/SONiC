# FRR-ISIS SONIC CONFIG SUPPORT #

## Table of Content 

- [FRR-ISIS SONIC CONFIG SUPPORT](#frr-isis-sonic-config-supportt)
  - [Table of Content](#table-of-content)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
	- [Requirements](#requirements)
	  - [Functional and Configuration Requirements](#functional-and-configuration-requirements)
	  - [Exemptions](#exemptions)
    - [Architecture Design](#architecture-design)
    - [High-Level Design](#high-level-design)
      - [Design Overview](#design-overview)
      - [Change Overview](#change-overview)
      - [Container](#container)
    - [SAI API](#sai-api)
    - [Configuration and management](#configuration-and-management)
      - [Manifest](#manifest)
      - [CLI/YANG Model Enhancements](#cliyang-model-enhancements)
      - [Config DB Enhancements](#config-db-enhancements)
      - [Config DB Yang Model Changes](#config-db-yang-model-changes)
      - [FRR Template Changes](#frr-template-changes)
    - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
    - [Restrictions/Limitations](#restrictionslimitations)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test cases](#unit-test-cases)
      - [System Test cases](#system-test-cases)
    - [Open/Action items](#openaction-items)
 
### Revision  
|  Rev  |  Date           |  Author  | Change Description |
| :---  | :-------------- | :------  | :----------------  |
|  0.1  | January-11-2022 | C Choate | Initial version    |

### Scope  

This document describes the scope of updates needed to support adding SONiC config support for FRR-ISIS in SONiC.

### Definitions/Abbreviations 

Table 1: Abbreviations

| Abbreviation | Description                                        |
| :----------  | :------------------------------------------------  |
| BGP          | Border Gateway Protocol                            |
| BGPCFGD      | Template based legacy config daemon                |
| FRR          | Free Range Routing Stack                           |
| FRRCFGD      | FRR config daemon fully based on config-DB events  |
| ISIS         | Intermediate System to Intermediate System         |

### Overview 

This document provides information about the initial support for FRR-ISIS SONiC config support in the SONiC infrastructure.

This is an addition to previous feature work to support FRR-BGP. Details on the initial feature design can be found at [SONiC FRR-BGP Extended Unified Configuration Management Framework](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md)

### Requirements

#### Functional and Configuration Requirements

  1. Extend config and management in SONiC for FRR-ISIS.
  2. Ability to configre FRR-ISIS based on configurations from config DB with frrcfgd (sonic-buildimage/src/sonic-frr-mgmt-framework) with the field frr_mgmt_framework_config set to "true" in the DEVICE_METADATA table.
  3. Retain access to FRR UI (vtysh) for managing FRR configs
  4. Configure FRR-ISIS based on configurations from config DB based on defined template files.
  5. Upon an FRR container reboot, ISIS template files will restore FRR-ISIS configs read from config DB.
  6. Provide support for config and management of FRR-ISIS features used in SONIC with new ISIS YANG models.

#### Exemptions
SONiC CLI support for ISIS show commands are not yet included.

### Architecture Design 

There are no changes to the existing SONiC architecture. This new feature enhances existing code to include configuration support for the isisd daemon within the FRR container. 

### High-Level Design 

#### Design Overview

This feature will extend functionality implemented in [SONiC FRR-BGP Extended Unified Configuration Management Framework](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md) to support additional SONiC FRR-ISIS features. 

The Management framework will convert the YANG-based config data into requests that will write the configs into Redis DB. Redis DB events will trigger frrcfgd when the field frr_mgmt_framework_config set to "true" in the DEVICE_METADATA table, and then frrcfgd will configure FRR-ISIS using FRR CLI commands.

#### Change Overview

This enhancement will support FRR-ISIS features used in SONiC and all changes will reside in the sonic-buildimage repository. Changes include:

- SONiC FRR-ISIS YANG models and YANG validation tests
  - /src/sonic-yang-models
- FRR-ISIS config template files and isisd enabled by default in the FRR container
  - /dockers/docker-fpm-frr
- Enable ISIS trap messages
  - /files/image_config/copp
- Added support for ISIS tables in frrcfgd and extended frrcfgd unit tests for FRR-ISIS configs
  - /src/sonic-frr-mgmt-framework

#### Container

There will be changes in following containers,
- Extend frrcfgd support for FRR-ISIS
  - sonic-mgmt-framework
- Enable the isisd daemon by default
  - bgp

### SAI API 

N/A - software feature

### Configuration and management 

#### Manifest

N/A

#### CLI/YANG Model Enhancements

There are no CLI changes made in this feature thus far.

#### Config DB Enhancements  

Following section describes the changes to DB.

Added new configuration tables specific to FRR_ISIS features:

- ISIS_GLOBAL
  - ISIS router globally applicable configurations
- ISIS_LEVEL
  - ISIS router level specific configurations
- ISIS_INTERFACE
  - ISIS router interface specific configurations

#### Config DB Yang Model Changes

Detailed Yang model changes can be found at

- isis-yang-hld

#### FRR Template Changes

A new FRR-ISIS template, "isisd.conf.j2" has been made to support the non-integrated config management feature and will be saved in "/etc/frr/isisd.conf" on an FRR container startup. The FRR template, "frr.conf.j2" has been updated to include FRR-ISIS template file "isisd.conf.j2" to support the unified config managemnt feature.

### Warmboot and Fastboot Design Impact  

There are no changes made to warmboot/fastboot impacting features.

### Restrictions/Limitations  

When deleting or adding configs that have dependencies built within the yang models, those dependencies must be maintained while adding or deleting configs. If those dependencies are not met, frrcfgd may have trouble deleting the configs properly.

### Testing Requirements/Design  

#### Unit Test cases  

Extended unit test cases to cover FRR-ISIS config features
 - Test frrcfgd changes
   - /src/sonic-frr-mgmt-framework/tests/test_config.py
- Test new ISIS YANG model Validation
   - /src/sonic-yang-models/tests/test_sonic_yang_models.py
   - /src/sonic-yang-models/tests/yang_model_tests/test_yang_model.py

#### System Test cases
Extensive system test cases to cover FRR-ISIS config features
- Verify every YANG config input matches the desired FRR config output for frrcfgd
  and template based configuration methods
- Verify configs can be deleted by config table name and individual fields
- Verify configs persist in the FRR container post container reboot

### Open/Action items

Is there a way to better align the custom yang models designed for SONiC FRR-ISIS with Open Config ISIS models. Not all FRR-ISIS features are compatible with Open Configs' models ?

Could the FRR container be renamed from 'bgp' to 'frr' ?
