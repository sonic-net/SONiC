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
        - [COPP_TRAP](#copp_trap)
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
|  0.1  | May-11-2023     | C Choate | Initial version    |

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
Adding support for multi-linecard chassis is out of scope for this document. 

### Architecture Design 

There are no changes to the existing SONiC architecture. This new feature enhances existing code to include configuration support for the isisd daemon within the FRR container. Testing showed that with the isisd deamon enabled, ISIS routes are being learned directly from the FRR container without needing any changes to the existing orchagent or swss. It was observed that fpmsyncd works to push all of the ISIS learned routes from the FRR container to SONiC DB’s. 

### High-Level Design 

#### Design Overview

This feature will extend functionality implemented in [SONiC FRR-BGP Extended Unified Configuration Management Framework](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md) to support additional SONiC FRR-ISIS features. 

![FRR-BGP-Unified-mgmt-frmwrk](https://user-images.githubusercontent.com/114622132/222537856-eefb1a13-bcc0-495b-938a-7ea3abee0c18.png)

Diagram 1. Diagram showing the existing framework that is being extended to include support for now ISIS config schemas. This diagram is taken from and further explained in it's original feature introduction in [SONiC FRR-BGP Extended Unified Configuration Management Framework](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md) to support additional SONiC FRR-ISIS features. 

The Management framework will convert the YANG-based config data into requests that will write the configs into Redis DB. Redis DB events will trigger frrcfgd when the field frr_mgmt_framework_config set to "true" in the DEVICE_METADATA table, and then frrcfgd will configure FRR-ISIS using FRR CLI commands.

#### Change Overview

This enhancement will support FRR-ISIS features used in SONiC and all changes will reside in the sonic-buildimage repository. Changes include:

- SONiC FRR-ISIS YANG models and YANG validation tests
  - /src/sonic-yang-models
- Enable isisd daemon and add 'isis' to the COPP_TRAP table when frr_mgmt_framework_config is set to "true"
  - /dockers/docker-fpm-frr
- Added support for ISIS tables in frrcfgd and extended frrcfgd unit tests for FRR-ISIS configs. Added template files to allow configuration of ISIS tables and add 'isis' to the COPP_TRAP table on FRR container startup
  - /src/sonic-frr-mgmt-framework
- Support ISIS show commands and show command unittests
  - sonic-utilities/show
  - sonic-utilities/tests

##### COPP_TRAP
There is existing support in SONiC to add additional trap_ids to the COPP_TRAP table outlined in [Sonic Control Plane Policing configuration and management](https://github.com/sonic-net/SONiC/blob/master/doc/copp/CoPP%20Config%20and%20Management.md). To support isis within the COPP_TRAP table, 'isis' needs to be added under the 'bgp' container within the 'trap_ids' leaf like below. On startup of the FRR container (bgp), if frr_mgmt_framework_config is set to "true", isis will automatically be added to the COPP_TRAP table using the template file isis_copp_trap_config.j2. On startup of the FRR container, if frr_mgmt_framework_config is set to "false", 'isis' will automatically be removed from the COPP_TRAP table.
'''
"COPP_TRAP": {
  "bgp": {
    "trap_ids": "bgp,bgpv6,isis",
    "trap_group": "queue4_group1",
    "always_enabled": "true"          
  }
}
'''

#### Container

There will be changes in following containers,
- Extend frrcfgd support for FRR-ISIS
  - sonic-mgmt-framework
- Enable the isisd daemon only when frr_mgmt_framework_config is set to "true"
  - bgp

### SAI API 

N/A - software feature

### Configuration and management 

#### Manifest

N/A

#### CLI/YANG Model Enhancements

New SONiC ISIS show commands

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show state information for all ISIS neighbors or a specified neighbor |show isis neighbors [system_id] {--verbose} |

```
sonic:~$ show isis neighbors
Area 1:
 System Id           Interface   L  State        Holdtime SNPA
sonic1         PortChannel01202  Up            25       2020.2020.2020
sonic2         PortChannel01212  Up            25       2020.2020.2020
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show the ISIS database globally or for a specific LSP |show isis database [lsp_id] {--verbose} |

```
sonic:~$ show isis database
Area 1:
IS-IS Level-2 link-state database:
LSP ID                  PduLen  SeqNumber   Chksum  Holdtime  ATT/P/OL
sonic1.00-00             1284   0x0000020e  0x3d7e   48072    0/0/0
sonic1.00-01             197   0x00000136  0x4474   64797    0/0/0
sonic2.00-00             1192   0x000001ae  0xd970   47837    0/0/0
sonic2.00-01             367   0x00000136  0xe315   31986    0/0/0
sonic3.00-00             1319   0x000001a9  0x3349   47881    0/0/0
sonic3.00-00             1115   0x000002e7  0x1b38   54629    0/0/0
    6 LSPs 
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show information about an ISIS node |show isis hostname |

```
sonic:~$ show isis hostname
vrf     : default
Level  System ID      Dynamic Hostname
2      1000.2000.4000 sonic2    
     * 1000.2000.3000 sonic
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show state and configuration of ISIS for all interfaces or a specified interface |show isis interface [interface] {--verbose} {--display}|

```
sonic:~$ show isis interface
Area 1:
  Interface   CircId   State    Type     Level
  PortChannel01200x0      Up       p2p      L2 
  
sonic:~$ show isis interface --display 
[INTERFACE] options: ['Loopback0', 'Ethernet0', 'Ethernet4', 'Ethernet8', 'Ethernet12', 'Ethernet16', 'Ethernet20', 'Ethernet24', 'Ethernet28', 'Ethernet32', 'Ethernet36', 'Ethernet40', 'Ethernet44', 'Ethernet48', 'Ethernet52', 'Ethernet56', 'Ethernet60', 'Ethernet64', 'Ethernet68', 'Ethernet72', 'Ethernet76', 'Ethernet80', 'Ethernet84', 'Ethernet88', 'Ethernet92', 'Ethernet96', 'Ethernet100', 'Ethernet104', 'Ethernet108', 'Ethernet112', 'Ethernet116', 'Ethernet120', 'Ethernet124', 'PortChannel0002', 'PortChannel0003', 'PortChannel0120']
Area 1:
  Interface   CircId   State    Type     Level
  PortChannel01200x0      Up       p2p      L2 
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show topology IS-IS paths globally or for level-1 or level-2 specifically |show isis topology {--level-1} {--level-2} |

```
sonic:~$ show isis topology
Area 1:
IS-IS paths to level-2 routers that speak IP
Vertex               Type         Metric Next-Hop             Interface Parent
sonic1                                                          
172.20.53.0/31       IP internal  0                           sonic1(4)
172.20.52.0/31       IP internal  0                           sonic1(4)
sonic2               TE-IS        10     sonic2               PortChannel0121 sonic1(4)
10.3.159.80/32       IP TE        10     sonic2               PortChannel0121 sonic2(4)
10.3.159.81/32       IP TE        10     sonic2               PortChannel0121 sonic2(4)
......
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show summary of ISIS information |show isis summary |

```
sonic:~$ show isis summary
vrf             : default
Process Id      : 4663
System Id       : 0000.0000.0000
Up time         : 00:04:31 ago
Number of areas : 1
Area 1:
  Net: 10.0000.0000.0000.0000.0000.0000.0000.0000.0000.00
  TX counters per PDU type:
     L2 IIH: 144
     L2 LSP: 4
    L2 CSNP: 29
   LSP RXMT: 0
  RX counters per PDU type:
     L2 IIH: 143
     L2 LSP: 4
  Drop counters per PDU type:
     L2 IIH: 1
  Advertise high metrics: Disabled
  Level-1:
    LSP0 regenerated: 3
         LSPs purged: 0
    SPF:
      minimum interval  : 1
    IPv4 route computation:
      last run elapsed  : 00:04:25 ago
      last run duration : 111 usec
      run count         : 3
    IPv6 route computation:
      last run elapsed  : 00:04:25 ago
      last run duration : 23 usec
      run count         : 3
  Level-2:
    LSP0 regenerated: 4
         LSPs purged: 0
    SPF:
      minimum interval  : 1
    IPv4 route computation:
      last run elapsed  : 00:04:21 ago
      last run duration : 45 usec
      run count         : 9
    IPv6 route computation:
      last run elapsed  : 00:04:21 ago
      last run duration : 14 usec
      run count         : 9
......
```

|Command Description|CLI Command      |
|:------------------|:-----------------|
|Show ISIS running configuration |show run isis  {--verbose} {--config_db} {--namespace}|

```
sonic:~$ show run isis
"""Building configuration...
Current configuration:
!
frr version 8.2.2
frr defaults traditional
hostname vlab-01
log syslog informational
log facility local4
no service integrated-vtysh-config
!
password zebra
enable password zebra
!
interface PortChannel101
 ip router isis 1
 ipv6 router isis 1
 isis network point-to-point
exit
!
router isis 1
 is-type level-2-only
 net 49.0001.1720.1700.0002.00
 lsp-mtu 1383
 lsp-timers level-1 gen-interval 30 refresh-interval 900 max-lifetime 1200
 lsp-timers level-2 gen-interval 30 refresh-interval 305 max-lifetime 900
 log-adjacency-changes
exit
!
end
  
sonic:~$ show run isis  --config_db 
{ 
  "ISIS_GLOBAL": { 
    "1": { 
      "net": "49.0001.1720.1700.0002.00", 
      "lsp_mtu_size": "1383",   
      "spf_time_to_learn": "25"  
    } 
  }, 
	"ISIS_LEVEL": { 	
    "1|level-2": { 
      "lsp_refresh_interval": "305", 
      "lsp_maximum_lifetime": "900"
    } 
  }, 
	"ISIS_INTERFACE": { 
    "1|PortChannel0101": { 
      "instance":"1", 
      "ifname": "PortChannel0120", 
      "network_type": "point-to-point", 
      "ipv4_routing_instance": "1", 
      "ipv6_routing_instance": "1", 
    } 
  } 
} 
```

#### Config DB Enhancements  

Following section describes the changes to DB.

Added new configuration tables specific to FRR_ISIS features:

- ISIS_GLOBAL
  - ISIS router globally applicable configurations
- ISIS_LEVELS
  - ISIS router level specific configurations
- ISIS_INTERFACE
  - ISIS router interface specific configurations

#### Config DB Yang Model Changes

Detailed Yang model changes can be found at


- [ISIS Yang Model for SONiC High Level Design Document](https://github.com/sonic-net/SONiC/blob/073e72079bbeee3f454e65b817816c9c1bb955a0/doc/isis/frr-isis-sonic-yang-model-hld.md)


#### FRR Template Changes

A new FRR-ISIS template, "isisd.conf.j2" has been made to support the non-integrated config management feature and will be saved in "/etc/frr/isisd.conf" on an FRR container startup when frr_mgmt_framework_config is set to "true". The FRR template, "frr.conf.j2" has been updated to include FRR-ISIS template file "isisd.conf.j2" to support the unified config managemnt feature.

### Warmboot and Fastboot Design Impact  

There are no changes made to warmboot/fastboot impacting features.

### Restrictions/Limitations  

When deleting or adding configs that have dependencies built within the yang models, those dependencies must be maintained while adding or deleting configs. If those dependencies are not met, frrcfgd may have trouble deleting the configs properly.

### Testing Requirements/Design  

#### Unit Test cases  

Extended unit test cases to cover FRR-ISIS config features
 - Test frrcfgd changes
   - sonic-buildimage/src/sonic-frr-mgmt-framework/tests/test_config.py
- Test new ISIS YANG model Validation
   - sonic-buildimage/src/sonic-yang-models/tests/test_sonic_yang_models.py
   - sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/test_yang_model.py
- Test show commands for isis
   - sonic-utilities/tests/isis_frr_test.py

#### System Test cases
Extensive system test cases to cover FRR-ISIS config features
- Verify every YANG config input matches the desired FRR config output for frrcfgd
  and template based configuration methods
- Verify configs can be deleted by config table name and individual fields
- Verify configs persist in the FRR container post container reboot

New tests will also be published into sonic-mgmt for ISIS

### Open/Action items

Could the FRR container be renamed from 'bgp' to something like 'frr' ?
