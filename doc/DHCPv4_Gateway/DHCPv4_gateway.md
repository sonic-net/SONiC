# DHCPv4 - Specify Gateway explicitly #

## Table of Content 
1. [Scope](#Scope)
2. [Definitions](#Definitions/Abbreviations)
3. [Overview](#Overview)
4. [Requirements](#Requirements)
5. [High Level Design](#High-Level-Design)
6. [Test](#Testing-Considerations)

### Revision  

### Scope  

This document describes the High Level Design of 'Subnets' of vlan and use of same in dhcpv4.
This HLD document represent the changes in PR: https://github.com/sonic-net/sonic-buildimage/pull/15969.

### Definitions/Abbreviations 



### Overview 

'Subnets' specify the primary subnet of a vlan (IPv4;IPv6). When a dhcpv4 packet is forwarded via dhcprelayagent, it embeds its own gateway address as 'giaddr' for return communication.
In case of multiple interfaces, dhcprelayagent misconfigures this giaddr to any of the interfaces. 
This change fixes this behaviour by explicitly specifying the primary interface/gateway.
This primary subnet is stored in db as 'subnets' of VLAN.

### Requirements

1. Support a new member 'Subnets' of VLAN in config_db.
2. Support parsing and assignment of subnets from minigraph to config_db. 
3. Support specifying subnet's first address as gateway address to command line arguments to /usr/sbin/dhcrelay as -g.
4. isc-dhcp/dhcrelay to support '-g gateway' argument, by porting an existing patch.

### Architecture Design 

This HLD doesn't propose any sonic architectural changes. It follows the existing architecture of sonic - open source asc-dhcp is used for its dhcpv4 requirements.
This HLD prposes to enhance the dhcpv4 capability by avoiding ambiguity in dhcpv4 packets wrt giaddr field.

### High-Level Design 

This section covers the high level design of the feature/enhancement. This section covers the following points in detail.
		
	- Is it a built-in SONiC feature or a SONiC Application Extension? - Built in feature.
	- What are the modules and sub-modules that are modified for this design? - isc-dhcp.
	- What are the repositories that would be changed? - sonic-subnet/sonic-buildimage.
	- Module/sub-module interfaces and dependencies. 
	- SWSS and Syncd changes in detail - N/A.
	- DB and Schema changes (APP_DB, ASIC_DB, COUNTERS_DB, LOGLEVEL_DB, CONFIG_DB, STATE_DB) - sonic-vlan/sonic-vlan/VLAN/VLAN_LIST/Subnets.
	- Sequence diagram if required. - N/A.
	- Linux dependencies and interface - N/A.
	- Warm reboot requirements/dependencies - N/A.
	- Fastboot requirements/dependencies - N/A.
	- Scalability and performance requirements/impact - N/A.
	- Memory requirements - N/A.
	- Docker dependency - N/A,
	- Build dependency if any - N/A.
	- Management interfaces - SNMP, CLI, RestAPI, etc.,
	- Serviceability and Debug (logging, counters, trace etc) related design
	- Is this change specific to any platform? Are there dependencies for platforms to implement anything to make this feature work? If yes, explain in detail and inform community in advance. - N/A.
	- SAI API requirements, CLI requirements, ConfigDB requirements. Design is covered in following sections. - ConfigDB requirement is captured below.

### SAI API 

No change in SAI API.

### Configuration and management 
(This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.)

#### Minigraph 

<<Redis DB Structure | Json Style>>
{
"VLAN": {
	"Vlan1000": {
		"dhcp_servers": [
			"192.0.0.1"
		],
		"members": [
			"Ethernet0"
		],
		"vlanid": "1000",
		“subnets”: “192.168.0.1/27”
	}
  }
}
<<End Json Style>>

#### Manifest (if the feature is an Application Extension)

N/A


#### CLI/YANG model Enhancements 

There is no change in CLI.

#### Config DB Enhancements  

Support a new member 'Subnets' of VLAN in config_db.


### Warmboot and Fastboot Design Impact  
This feature doesnt impact warmboot/fastboot. This feature is limited to dhcpv4 relay agent behaviour, which doesnt affect warmboot/fastboot. 

### Memory Consumption
No memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration. 

### Restrictions/Limitations  

### Testing Requirements/Design  
Explain what kind of unit testing, system testing, regression testing, warmboot/fastboot testing, etc.,
Ensure that the existing warmboot/fastboot requirements are met. For example, if the current warmboot feature expects maximum of 1 second or zero second data disruption, the same should be met even after the new feature/enhancement is implemented. Explain the same here.
Example sub-sections for unit test cases and system test cases are given below. 

#### Unit Test cases  

Sonic has an extensive set of unit tests to validate dhcpv4 scenarios. Few test cases were modified with additional 'subnets', to validate existing test cases.

#### System Test cases
N/A.

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
