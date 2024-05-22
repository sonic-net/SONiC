# DHCP Relay (v4) - Specify gaaddr as Primary Interface's Gateway explicitly #

## Table of Content 
1. [Scope](#Scope)
2. [Definitions](#Definitions/Abbreviations)
3. [Overview](#Overview)
4. [Requirements](#Requirements)
5. [High Level Design](#High-Level-Design)
6. [Test](#Testing-Considerations)

### Revision  

### Scope  

This document describes the High Level Design of 'secondary' interfaces of vlan and use of primary (non-secondary) interface as gateway for dhcpv4 relay.

### Definitions/Abbreviations 



### Overview 

A vlan can support multiple subnets/interfaces. Some of these interfaces (ideally all except one) can be marked as 'secondary'.

Secondary addresses do not support DHCP (with dhcp relay). Dhcp relay agent will insert its primary address in dhcp request, and dhcp server should assign addresses from primary range only. 

When a dhcpv4 packet is forwarded via (isc) dhcprelayagent, it embeds its interface's gateway address as 'giaddr' for return communication.
In case of multiple (primary) interfaces, dhcprelayagent randomly (mis)configures this giaddr to any of the interfaces. 
This design fixes this behaviour by marking some interfaces as secondary, and explicitly specifying the primary interface for dhcp relay agent's gateway.

Secondary interface increases the number of IPs supported by switch without affecting live workloads. Such IPs will be used for virtualized machines on existing baremetals. This also provides finer control for different workloads from network security.

This feature is limited to IPv4-only.

### Requirements

1. Support a new member 'secondary' of VLAN_INTERFACE in config_db.
2. Support parsing and assignment of subnets from minigraph/json/cli to config_db. 
3. Support specifying non-secondary interfaces' gateway address to command line arguments to /usr/sbin/dhcrelay as -pg (primary gateway).
4. isc-dhcp/dhcrelay to support '-pg gateway' argument.

### Architecture Design 

This HLD doesn't propose any sonic architectural changes. It follows the existing architecture of sonic - open source asc-dhcp is used for its dhcpv4 requirements.
This HLD proposes to enhance the dhcp-relay (v4) capability by avoiding ambiguity in dhcpv4 request packet's giaddr field.

### High-Level Design 

This section covers the high level design of the feature/enhancement. This section covers the following points in detail.
		
	- Is it a built-in SONiC feature or a SONiC Application Extension? - Built in feature.
	- What are the modules and sub-modules that are modified for this design? - isc-dhcp.
	- What are the repositories that would be changed? - sonic-subnet/sonic-buildimage.
	- Module/sub-module interfaces and dependencies. 
	- SWSS and Syncd changes in detail - N/A.
	- DB and Schema changes (APP_DB, ASIC_DB, COUNTERS_DB, LOGLEVEL_DB, CONFIG_DB, STATE_DB) - CONFIG_DB sonic-vlan/sonic-vlan/VLAN_INTERFACE.
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

Redis DB Structure | Json Style
```
{
"VLAN_INTERFACE": {
	"Vlan1000": {},
	"Vlan1000|20.11.12.13/27": {"secondary": "true"},
	"Vlan1000|20.11.10.13/27": {},
	}
}
```

#### Manifest (if the feature is an Application Extension)

N/A


#### CLI/YANG model Enhancements 

Extend CLI to specify an interface ip as secondary during add:

	$ sudo config interface ip add Vlan1000 20.11.12.13/27 20.11.12.254 --secondary
	Usage: config interface ip add <interface_name> <ip_addr> <default gateway IP address> <secondary>

Extend yang (sonic-vlan.yang):
```
	list VLAN_INTERFACE_IPPREFIX_LIST {

				leaf secondary	{
					description "Optional field to specify if the prefix is secondary subnet";
					type boolean;
				}
			}
```

#### Config DB Enhancements  

Support a new optional member 'secondary' of VLAN_INTERFACE in config_db. Type: bool, Default: false.
No upgrade/action required in config_db for existing interfaces during upgrade.


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

```
1. [sonic-buildimage] yang - model validation test case: 
		src/sonic-config-engine/tests/test_minigraph_case.py::test_minigraph_vlan_interfaces - to check if secondary flag is added.
		src/sonic-config-engine/tests/test_minigraph_case.py:::test_minigraph_vlan_interfaces_keys - to check if secondary subnet is added in IPInterfaces.
2. [sonic-utilities] cli validation test cases: all the below cases are covered in tests/ip_config_test.py
		validating --secondary flag in the command
		validating -s flag in the command
		Check if a primary subnet is present and only if it is add the secondary flag - if not fail
3. [sonic-mgmt] dhcp relay test case: Modify the existing two_vlan scenario to extend and have secondary subnet field in the minigraph
		ansible/templates/minigraph_dpg.j2 - changes to add SecondarySubnets xml entry
		ansible/vars/topo_t0.yml - changes to add secondary_subnet to the vlan
4. [sonic-buildimage] test dhcp-relay j2 file generation:
		src/sonic-config-engine/tests/test_j2files.py::test_dhcp_relay - add a test case to read minigraph file with secondary subnet field present and validate it against the expected generated file.
		src/sonic-config-engine/tests/t0-sample-graph-secondary-subnets.xml - minigraph with secondary subnets in Vlan1000
		docker-dhcp-relay-secondary-subnets.supervisord.conf - expected output file in sample-output folder
```

#### System Test cases
N/A.

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
