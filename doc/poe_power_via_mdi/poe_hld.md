# SONiC PoE Power via MDI #

## Table of Content 

- [Revision](#revision)
- [Scope](#scope)
- [Definition/Abbreviation](#definitions_abbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
  - [PoE interaction](#poe-interaction)
  - [SWSS changes](#swss-changes)
  - [PoE SYNCD](#poe-syncd)
  - [PoE Manager](#poe-manager)
  - [LLDP Manager](#lldp-manager-modified)
  - [LLDP Syncd](#lldp-syncd-modified)
- [High-Level Design](#high-level-design)
- [SAI API](#sai-api)
- [PoE AI](#poe-abstraction-interface)
- [Configuration and management](#configuration-and-management)
  - [CLI/YANG model Enhancements](#cli_yang-model-enhancements)
    - [Show commands](#show-commands)
    - [Config commands](#config-commands)
  - [Config DB Enhancements](#config-db-enhancements)
  - [Application DB Enhancements](#application-db-enhancements)
  - [State DB Enhancements](#state-db-enhancements)
- [Restrictions/Limitations](#restrictions_limitations)

### Revision

 | Rev | Date |     Author     | Change Description |
 |:---:|:----:|:--------------:|--------------------|
 | 0.1 | 01-02-2026 | Saravanan I |  Initial version |


### Scope  

This document provides general information about the PoE Power via MDI (Power over Ethernet) feature implementation in SONiC.

### Definitions/Abbreviations 

|                          |                                |
|--------------------------|--------------------------------|
| PoE                      | Power over Ethernet |
| MDI                      | Media Dependent Interface |
| LLDP                     | Link Level Disconvery Protocol |
| PD                       | Powered Devices |
| TLV                      | Type Length Value |
| PSE                      | Power Supplying Equipment |

### Overview 

SoNiC switches with PoE capability can be augmented to support Power via MDI functionality. Once the port connected to an PD reaches delivering power stage, PD can adjust it's power limit (called as Dynamic Power Limit) by exchanging LLDP packets to the switch. 
It prevents overloading the PSE’s power budget, which can lead to port shutdowns thus ensuring stable and efficient operation of all connected devices.

### Requirements

- Support new CLI configurations to enable or disable Power via MDI feature at individual port level as mentioned in [config section](#config-commands)
- Support in LLDP module to handle exchange of Power via MDI TLVs between PSE and PD

### Architecture Design 
This section covers the high level design of this feature.

This section covers the following points in detail.

	- Existing modules that were modified by this design and new modules that were added
	- Repositories that will be changed: sonic-buildimage, ...
	- Module/sub-module interfaces and dependencies. 
	- This design doesn't change existing DB Schema, only new are added.
	- Linux dependencies and interface
	- Fastboot requirements & dependencies
	- Scalability and performance requirements/impact
	- Memory requirements
	- Management interfaces - CLI, etc.,

#### PoE interaction

This section describes the detail interaction of PoE componnents, DB and PoE hardware (controller) in SONiC subsytem.

![poe-interaction](poe_lldp_diagram_data_flow.png)

#### SWSS changes

To support setting dynamic power limit in ASIC, SWSS container needs to be enhanced to set the attribute in SAI.

#### PoE manager

PoE manager will need to  implement the following functionality:

- apply dynamic power limit configuration in PoE controller;
- Listen to the LLDP_MDI_POWER table in APPL_DB and then process the setting of dynamic power limit attribute in SAI via poesyncd. After setting the dynamic power limit, update the LLDP_MDI_POWER table in State db to inform the PD about setting of dynamic power limt


#### LLDP manager (modified)

To exchange the PoE information with peer about power supply capability, the LLDP protocol is used. To support
that, LLDP manager is required to be modified as following:

- LLDP manager gets PoE information (from state db PoE database).
- LLDP manager adds LLDP TLV with PoE information into LLDP packet.

#### LLDP syncd (modified)

To inform the PD's requirement of dynamic power limit,
LLDP syncd is required to be modified as following:

- LLDP syncd application appends the APPLICATION DB with received TLVs from PD


### High-Level Design 

To be added

###### LLDP flows

1) lldpmgrd updates the APPL_DB with the power via MDI LLDP packet received from PD.
2) poemgrd subscribed to related tables in APPL_DB and upon receiving the notification from APPL_DB and then processes the dynamic power limit request by propagating the same in PoE hardware.
3) After setting the power limit in PoE hardware, poemgrd updates the outgoing TLV information in STATE_DB
4) lldp_syncd subscribed to related table in STATE_DB and upon receiving the update notification, it appends the outgoing LLDP packet (to the PD) with  the Power via MDI TLV.

![lldp-poe-interaction](lldp_poe_flow.png)

###### PoE configuration
- New PoE CLI configurations were introduced to enable power via mdi capability.

### SAI API 

- SAI API is defined and configured to set the dynamic power limit for PoE

### PoE Abstraction Interface

The PoE Manager uses a new SAI PoE library that implements the PoE Abstraction Interface.

#### Device Capabilities

#### Port Capabilities

| Capabilities       		 | SAI attributes                                |
| -------------------        | --------------------------------------------- |
| Dynamic Power Limit        | * SAI_POE_PORT_ATTR_DYNAMIC_POWER_LIMIT         |

* - SAI_POE_PORT_ATTR_DYNAMIC_POWER_LIMIT - Currently this SAI attribute is yet to be added in SAI PoE definition in OpenComputeProject (https://github.com/opencomputeproject/SAI/blob/v1.17.4/inc/saipoe.h)

### Configuration and management 

#### Manifest (if the feature is an Application Extension)
Yes. This feature extends existing PoE functionalities to support Power via MDI capabilities.

#### CLI

##### Show commands
Existing show command is updated to display the dynamic power limit set.

- show poe interface \<ifname\>
```

Port         Status      En/Dis  Priority Protocol      Class  PWR Consump  PWR Limit   Voltage   Current DYN_PWR Limit
------------ ----------- ------- -------- ------------- ----- ------------ ---------- --------- --------- -------------
Ethernet0    delivering  enable  high     802.3BT/High      4      6.100 W   80.600 W  54.000 V   0.113 A     60.5 W
Ethernet1    delivering  enable  crit     802.3BT/High      4      6.500 W   80.600 W  54.000 V   0.120 A     60.5 W
Ethernet2    searching   enable  low      802.3BT/High      0      0.000 W   80.600 W   0.000 V   0.000 A     60.5 W
Ethernet3    searching   enable  crit     802.3BT/High      0      0.000 W   80.600 W   0.000 V   0.000 A     60.5 W
```

##### Config commands

- config poe interface power-via-mdi \<ifname\> {enable | disable}

Examples:
```
$ config poe interface power-via-mdi Ethernet0 enable
```

**TODO**: update CLI reference https://github.com/sonic-net/sonic-utilities/blob/master/doc/Command-Reference.md

#### YANG model Enhancements

TBD

#### Config DB Enhancements  

POE port table has been enhanced to support power via mdi capability:

##### POE_PORT_TABLE
~~~
    ;Stores PoE port configuration
    key         = POE_PORT|ifname         ; ifname with prefix POE_PORT
    ; field     = value
	power-via-mdi     = "enable" / "disable"    ; enable/disable PoE on port, default "disable"
~~~

#### APPLICATION DB Enhancements  

New table LLDP_MDI_POWER introduced in Application DB. This table will be written by LLDP manager daemon after processing incoming LLDP TLVs from PD. And, the PoE manager application after listening to this table, will process and configure the same in hardware using SAI.

#### LLDP_MDI_POWER
```
    ; Defines LLDP TLV information to be sent to PD on receipt of Dynamic Power Limit request from PD
	key         						= LLDP_MDI_POWER:ifname		;ifname with prefix LLDP_MDI_POWER
    ; field     						= value

	standard							= "af"/"at"/"bt"	;POE standard advertised by PSE

	power-type							= "PSE"/"Type-1-PSE"/"Type-2-PSE"	;Type advertised  by PSE, value "PSE" is valid when standard is "af", other values are valid when standard is "at"/"bt"
	
	power-source						= "Primary"/"Backup"	;Power source advertised by PSE
	
	power-priority						= "Critical"/"High"/"Low		;Power priority advertised by PSE
	
	power-value							= 1*3.3DIGIT    ;Power consumed advertised by PSE, field is applicable when standard is "af"
	
	mdi-power-supported			    	= BOOLEAN 	;MDI power negotiation is supported in PSE or not, applicable when standard is "af"
	
	mdi-power-support-state				= BOOLEAN 	;MDI power negotiation is supported in PSE or not, applicable when standard is "af"
	
	pair-control						= BOOLEAN	;Pair control in PSE is supported or not, set as "true" always
	
	power-pair							= "primary"/"secondary" /"both"		;Power pair in PSE 
	
	power-class							= UINT8 "Class4"/"Class3"/"Class2"/"Class1"/"Class0"	;Power class advertised by
	PSE, applicable when standard is "at"

	pd-requested-power			    	= STRING	;Requested power (in Milli watts) from PD, applicable when standard is "at"/"bt"
	
	pd-requested-power-primary			= STRING	;Requested power from PD on primary channel, applicable when standard is "bt"
	
	pd-requested-power-secondary		= STRING	;Requested power from PD on secondary channel, applicable when poe-standard is "bt"
	
	pse-allocated-power					= STRING 	;Allocated power from PSE, applicable when poe-standard is "at"/"bt"
	
	pse-allocated-power-primary			= STRING	;Allocated power from PSE on primary channel, applicable when standard is "bt"
	
	pse-allocated-power-secondary		= STRING 	;Allocated power from PSE on secondary channel, applicable when standard is "bt"
	
	power-type-extension				= "Type 3 PSE"/	"Type 4 PSE"	;Extended type advertised by PSE, applicable when standard is "bt"
	
	pd-load								= STRING  	;Set as "0" always by PSE, applicable when standard is "bt"
	
	power-class-extension				= "Dual Signature PD"/ "Class8"/ "Class7"/ "Class6"/ "Class5"/ "Class4"/ "Class3"/ "Class2"/ "Class1"	;Power class advertised by PSE, applicable when standard is "bt"
	
	power-class-extension-primary		= "Single Signature PD"/ Class5"/ "Class4"/ "Class3"/ "Class2"/ "Class1"	;Power class advertised by PSE on primary channel, applicable when standard is "bt"

	power-class-extension-secondary		= "Single Signature PD"/ "Class5"/ "Class4"/ "Class3"/ "Class2"/"Class1"	;Power class advertised by PSE on primary channel, applicable when standard is "bt"
	
	pse-power-status					= "4-pair powering dual-signature PD"/ "4-pair powering single-signature PD"/ "2-pair powering"		;Powered status advertised by PSE, applicable when standard is "bt"        
										  				 
	pd-powered-status					= STRING	;Set as "0" always by PSE, applicable when standard is "bt"
	
	pse-max-power						= STRING	;Maximum power available in PSE for this port, applicable when standard is "at"/"bt"
```

#### STATE DB Enhancements  

New table LLDP_MDI_POWER introduced in State DB to enable to PoE manager to communicate with the PD. Once the dynamic power limit is set in hardware, then the poe manager will write the same in STATE_DB. This DB will be subscribed by 
lldp manager to fill the outgoing power via mdi TLVs in LLDP protocol packets.

#### LLDP_MDI_POWER
```
	; Defines LLDP TLV information to be sent to PD on receipt of Dynamic Power Limit request
	key         						= LLDP_MDI_POWER:ifname   								; ifname with prefix LLDP_MDI_POWER
	; field     						= value

	standard							= "af"/"at" "bt"	;POE standard advertised by PD
	
	power-type							= "PD"/"Type-1-PD"/"Type-2-PD"	;Type advertised by PD, value "PD" is 	  valid when standard is "af", other values are valid when standard is "at"/"bt"
	
	power-source						= "Primary"/"Backup"	;Power source advertised by PD
	
	power-priority						= "Critical"/"High"/"Low	;Power priority advertised by PD
	
	power-value							= 1*3.3DIGIT	;Power consumed advertised by PD, field is applicable when standard is "af"
	
	mdi-power-supported			    	= STRING 	;Set as "0" always as per IEEE 802.3 Standard
	
	mdi-power-support-state				= STRING 	;Set as "0" always as per IEEE 802.3 Standard
	
	pair-control						= STRING	;Set as "0" always as per IEEE 802.3 Standard
	
	power-pair							= STRING	;Set as "0" always as per IEEE 802.3 Standard

	power-class							= UINT8	    ;Set as "0" always as per IEEE 802.3 Standard

	pd-requested-power			    	= STRING	;Requested power (in Milli watts) from PD, applicable when standard is "at"/"bt"
	
	pd-requested-power-primary			= STRING	;Requested power from PD on primary channel, applicable when standard is "bt"

	pd-requested-power-secondary		= STRING	;Requested power from PD on secondary channel, applicable when poe-standard is "bt"

	pse-allocated-power					= STRING 	;Allocated power from PSE, applicable when poe-standard is "at"/"bt"

	pse-allocated-power-primary			= STRING	;Allocated power from PSE on primary channel, applicable when standard is "bt"

	pse-allocated-power-secondary		= STRING	;Allocated power from PSE on secondary channel, applicable when standard is "bt"

	power-type-extension				= "Type 3 PSE"/	"Type 4 PSE"	;Extended type advertised by PD,applicable when standard is "bt"

	pd-load								= "Single Signature"/ "Dual Signature"  	;Signature type advertised by PD,  applicable when standard is "bt"

	power-class-extension				= "Dual Signature PD"/ "Class8"/ "Class7"/ "Class6"/ "Class5"/ "Class4"/"Class3"/ "Class2"/ "Class1"	;Power class advertised by PD, applicable when standard is "bt"
										           
	power-class-extension-primary		= "Single Signature PD"/ "Class5"/ "Class4"/ "Class3"/ "Class2"/ "Class1"	;Power class advertised by PD on primary channel, applicable when standard is "bt"

	power-class-extension-secondary		= "Single Signature PD"/ "Class5"/ "Class4"/ "Class3"/ "Class2"/"Class1"	;Power class advertised by PD on primary channel, applicable when standard is "bt"

	pse-power-status					= "4-pair powering dual-signature PD"/"4-pair powering single-signature PD"/ "2-pair powering"	;Powered status advertised by PD, applicable when standard is "bt"        
		 
	pd-powered-status					= STRING	;Set as "0" always by PD, applicable when standard is "bt"

	pse-max-power						= STRING	;Set as "0" always by PD, applicable when standard is "at"/"bt"

```





#### POE_PORT_STATE_TABLE
    ; Defines information for a PoE port state
    key         		= POE_PORT_STATE|ifname   ; ifname with prefix POE_PORT_STATE
    ; field     		= value
    dynamic_pwr_limit   = 1*3.3DIGIT              ; dynamic power limit of the PoE port set via LLDP message


### Warmboot and Fastboot Design Impact  

Post reboot, the PD can again exchange message with PSE to finetune it's power requirements.

### Memory Consumption
This sub-section covers the memory consumption analysis for the new feature: no memory consumption is expected when the feature is disabled via compilation and no growing memory consumption while feature is disabled by configuration. 

### Restrictions/Limitations  

This HLD assumes an Endpoint PSE (Switch). If a Midspan PSE is used between the SONiC switch and the PD, LLDP-based power negotiation will likely fail as Midspans typically do not terminate or proxy LLDP TLVs.

### Testing Requirements/Design  

#### Unit Test cases

PDs(AF/AT/BT) power via mdi requirements sent via (LLDP TLVs) can be mocked to validate the functionality

#### System Test cases

System testing can be done on systems with PoE power via mdi capability and the PD (with Power via MDI) support

### Open/Action items

- SONiC Yang models needs to be added
- SAI PoE definition needs to be updated in the OpenComputingProject to support Dynamic Power Limit
