# NVGRE tunnel in SONIC #

## Table of Content 

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)

### Revision  

|  Rev  |  Date   |      Author      | Change Description |
| :---: | :-----: | :--------------: | ------------------ |
|  1.0  | 08/2021 | Vadym Hlushko    | Phase 1 Design     |

### Scope  

This document provides general information about the NVGRE tunnel feature implementation in SONiC.

### Definitions/Abbreviations 

| Abbreviation | Definition                            |
|--------------|---------------------------------------|
| SONiC        | Software for Open Networking in Cloud |
| NVGRE        | Network Virtualization using Generic Routing Encapsulation |
| VxLAN        | Virtual Extensible LAN                | 
| VSID         | Virtual Subnet Identifier |
| DB           | Database                              |
| API          | Application Programming Interface     |
| SAI          | Switch Abstraction Interface          |
| YANG         | Yet Another Next Generation           |
| CLI          | Command-line interface                |
| NOS          | Network operating system              |
| RIF          | Router interface              |

### Overview 

NVGRE is a network virtualization method that uses encapsulation and tunneling to create large numbers of virtual LANs (VLANs) for subnets that can extend across dispersed data centers and layer 2 (the data link layer) and  layer 3 (the network layer). The SONIC has no support of NVGRE tunnel feature and appropriate SAI implementation for it. 

From the arhitecture point of view the new orchagent will be added to cover the NVGRE functionality. From the architecture point of view the new orchagent daemon will be added to cover the NVGRE functionality. New daemon should handle the configuration taken from config DB, and call an appropriate SAI API, which will create tunnel.

The new YANG model should be created in order to auto-generate CLI by using the [SONiC CLI Auto-generation tool](https://github.com/Azure/SONiC/blob/master/doc/cli_auto_generation/cli_auto_generation.md).

### Requirements

This section describes the SONiC requirements for NVGRE feature.

#### Functional requirements

At a high level the following should be supported:

- Phase #1
  - NVGRE tunnel should be able to work in parallel to VxLAN tunnel
- Phase #2
  - CLI for NVGRE tunnel

#### Orchagent requirements

NVGRE orchagent:

- Phase #1
  - Should be able to create Bridge/VLAN to VSID mapping
  - Should be able to create tunnels and encap/decap mappers.

### Architecture Design 

The new tables will be added to Config DB. Unless otherwise stated, the attributes are mandatory.

#### NVGRE configDB table

```
NVGRE_TUNNEL|{{tunnel_name}} 
    "src_ip": {{ip_address}} 

NVGRE_TUNNEL_MAP|{{tunnel_name}}|{{tunnel_map}}
    "vsid": {{vsid_id}}
    "vlan": {{vlan_id}}
```

#### ConfigDB schemas

```
; Defines schema for NVGRE Tunnel configuration attributes
key                                   = NVGRE_TUNNEL:name             ; NVGRE tunnel configuration
; field                               = value
SRC_IP                                = ipv4                          ; IPv4 source address

;value annotations
ipv4          = dec-octet "." dec-octet "." dec-octet "." dec-octet
dec-octet     = DIGIT                     ; 0-9  
                  / %x31-39 DIGIT         ; 10-99  
                  / "1" 2DIGIT            ; 100-199  
                  / "2" %x30-34 DIGIT     ; 200-249
```

```
; Defines schema for NVGRE Tunnel map configuration attributes
key                                   = NVGRE_TUNNEL:tunnel_name:name ; NVGRE tunnel configuration
; field                               = value
VSID                                  = DIGITS                        ; 1 to 16 million values
VLAN                                  = 1\*4DIGIT                     ; 1 to 4094 Vlan id
```

#### Orchestration agent

##### Figure 1. Orchestration agents

The following orchestration agents will be added or modified. The flow diagrams are captured in a later section.

<p align=center>
<img src="images/nvgre_orch.svg" alt="Figure 1. Orchestration agents">
</p>

#### NvgreOrch

`nvgreorch` - it is an orchestration agent that handles the configuration requests directly from ConfigDB. The `nvgreorch` is responsible for creates the tunnel and attaches encap and decap mappers. Separate tunnel maps are created for L3 NVGRE and can attach different VLAN/VSID or Bridge/VSID to a respective tunnel.

#### Orchdaemon

`orchdaemon` - it is the main orchestration agent, which handles all Redis DB's updates then calls appropriate orchagent, the new `nvgreorch` should be registered inside an `orchdaemon`.

### High-Level Design 

#### CLI tree

Commands summary (Phase #2):

```
	- config nvgre <nvgre_name> vlan <vlan_id> vsid <vsid_id>
	- config nvgre <nvgre_name> src_if <interface>
	- show mac nvgre <nvgre_name> <vsid_id>
	- show nvgre <nvgre_name>
```

##### Config CLI command

Config command should be extended in order to add "nvgre" alias

```
Usage: config [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'config' command

Options:
  --help  Show this message and exit.

Commands:
...
  nvgre               nvgre related configuration.
```

##### Show CLI command

Show command should be extended in order to add "nvgre" alias

```
Usage: show [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'show' command

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  ...
  nvgre                   Show nvgre related information
```

#### Flows

##### Figure 2. NVGRE Tunnel creation flow

<p align=center>
<img src="images/nvgre_tunnel_create_uml.svg" alt="Figure 2. NVGRE Tunnel creation flow">
</p>

##### Figure 3. NVGRE Tunnel Map creation flow

<p align=center>
<img src="images/nvgre_tunnel_map_create_uml.svg" alt="Figure 2. NVGRE Tunnel Map creation flow">
</p>


##### Figure 4. NVGRE Tunnel CLI config

<p align=center>
<img src="images/nvgre_cli_config.svg" alt="Figure 4. NVGRE Tunnel CLI config">
</p>

##### Figure 5. NVGRE Tunnel CLI show

<p align=center>
<img src="images/nvgre_cli_show.svg" alt="Figure 5. NVGRE Tunnel CLI show">
</p>

### SAI API 

| NVGRE component | SAI attribute |
|--------------|---------------------------------------|
| NVGRE tunnel type | SAI_TUNNEL_TYPE_NVGRE |
| Encap mapper | SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VSID |
| Decap mapper | SAI_TUNNEL_MAP_TYPE_VSID_TO_VLAN_ID |
| Encap mapper | SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VSID |
| Decap mapper | SAI_TUNNEL_MAP_TYPE_VSID_TO_BRIDGE_IF |

### Configuration and management 

This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.

#### CLI/YANG model Enhancements 

This sub-section covers the addition/deletion/modification of CLI changes and YANG model changes needed for the feature in detail. If there is no change in CLI for HLD feature, it should be explicitly mentioned in this section. Note that the CLI changes should ensure downward compatibility with the previous/existing CLI. i.e. Users should be able to save and restore the CLI from previous release even after the new CLI is implemented. 
This should also explain the CLICK and/or KLISH related configuration/show in detail.

#### Config DB Enhancements  

This sub-section covers the addition/deletion/modification of config DB changes needed for the feature. If there is no change in configuration for HLD feature, it should be explicitly mentioned in this section. This section should also ensure the downward compatibility for the change. 
		
### Warmboot and Fastboot Design Impact  
Mention whether this feature/enhancement has got any requirements/dependencies/impact w.r.t. warmboot and fastboot. Ensure that existing warmboot/fastboot feature is not affected due to this design and explain the same.

### Restrictions/Limitations  

### Testing Requirements/Design  
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.