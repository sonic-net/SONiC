# Configure Policer and bind it to interface or ACL table HLD #

## 1.Table of Content 
- [Policer configure HLD](#Policer-configure-hld)
  - [1.Table of Content](#1table-of-content)
    - [1.1. Revision](#11-revision)
    - [1.2. Scope](#12-scope)
    - [1.3. Definitions/Abbreviations](#13-definitionsabbreviations)
    - [1.4. Overview](#14-overview)
    - [1.5. Requirements](#15-requirements)
    - [1.6. Architecture Design](#16-architecture-design)
    - [1.7. High-Level Design](#17-high-level-design)
    - [1.8. SAI API](#18-sai-api)
    - [1.9. Configuration and management](#19-configuration-and-management)
      - [1.9.1. CLI/YANG model Enhancements](#191-cliyang-model-enhancements)
        - [1.9.1.1. CLI](#1911-cli)
        - [1.9.1.2. YANG](#1912-yang)
      - [1.9.2. Config DB Enhancements](#192-config-db-enhancements)
      - [1.9.3. Orchagent changes](#193-orchagent-changes)
    - [1.10. Warmboot and Fastboot Design Impact](#110-warmboot-and-fastboot-design-impact)
    - [1.11. Memory Consumption](#111-memory-consumption)
    - [1.12. Restrictions/Limitations](#112-restrictionslimitations)
    - [1.13. Testing Requirements/Design](#113-testing-requirementsdesign)
      - [1.13.1. Unit Test cases](#1131-unit-test-cases)
      - [1.13.2. System Test cases](#1132-system-test-cases)
    - [1.14. Open/Action items - if any](#114-openaction-items---if-any)

### 1.1. Revision 
| Rev | Date       | Author     | Description     |
|:---:|:----------:|:----------:|:----------------|
| 0.1 | 12/04/2024 | PinghaoQu  | Initial version | 

### 1.2. Scope  

Support command-line configuration for policer

Support creating policer ACL

Support binding policer to interface

### 1.3. Definitions/Abbreviations 

NA.

### 1.4. Overview 

In the current Sonic system, configuring a policer via the command line is not supported. In Orchagent, attaching a policer to an interface or ACL is also not supported.

### 1.5. Requirements

New table of PORT_POLICER needs to be defined. New ACL table of type POLICER with policer match fields and default actions needs to be defined. 

### 1.6. Architecture Design 

The overall architecture of SONiC will remain unchanged, and no new sub-modules will be introduced.

### 1.7. High-Level Design 

We will modify few touch few areas in the system:

  1. sonic-utilites - Add policer configuration and show command, add configuration for binding policer to an interface. Also acl-loader needs to be updated to support POLICER type in CLICK command
  2. config-db -  to include a dedicated table(PORT\_POLICER) for configurations
  3. orchagent -  policerorch, subscribe to the PORT_POLICER entries and process them. aclorch, add processing for POLICER type ACL entries, similar to MIRROR.

### 1.8. SAI API 

NA.

### 1.9. Configuration and management 

#### 1.9.1. CLI/YANG model Enhancements 

##### 1.9.1.1. CLI

**config commands**

**config policer add**

This command configures the possible fields in a particular policer. The list of the policer fields that are configurable is listed in the below "Usage".

- Usage:
  ```
  admin@sonic:~$ sudo config policer add --help
  Usage: config policer add [OPTIONS] <policer_name>

    Add traffic policing configuration

  Options:
    -mode <mode>                    Token bucket model  [required]
    -mtype <meter_type>             Unit of measurement  [required]
    -csource <color_source>         Handling of colored packets
    -cir <cir>                      Committed information rate  [required]
    -cbs <cbs>                      Committed burst size  [required]
    -pir <pir>                      Peak rate
    -pbs <pbs>                      Exceeds burst size
    -gaction <green_packet_action>  Actions on green packets
    -yaction <yellow_packet_action>
                                    Actions on red packets
    -raction <red_packet_action>    Actions on yellow packets
    -?, -h, --help                  Show this message and exit.
  ```

- Notes:
  - <mode\> could be "sr_tcm/tr_tcm".
  - <meter_type\> could be "packets/bytes".
  - <color_source\> could be "blind/aware". "Blind" indicates that the policer uses a color-blind mode to mark traffic packets, while "aware" indicates that the policer uses a color-aware mode to mark traffic packets.
  - <green_packet_action\> could be "drop/forward/copy/copy_cancel/trap/log/deny/transit". The same applies to <yellow_packet_action\> and <red_packet_action\>.

- Example:
  ```
  admin@sonic:~$ sudo config policer add policer_1 -mode sr_tcm -mtype packets -csource blind -cir 1024 -cbs 2048
  admin@sonic:~$ sudo config policer add policer_2 -mode tr_tcm -mtype bytes -csource aware -cir 102400 -cbs 204800 -pir 204800 -pbs 409600 -yaction drop -raction drop 
  ```

**config policer del**

This command is used to delete the policer configured.

- Usage:
  ```
  config policer del <policer_name>
  ```

- Example:
  ```
  admin@sonic:~$ sudo config policer del policer_1
  ```

**config interface policer add**

This command applies the policer to the interface.

- Usage:
  ```
  config interface policer add <interface_name> <policer_name>
  ```

- Example:
  ```
  admin@sonic:~$ sudo config interface policer add Ethernet0 policer_1
  ```

**config interface policer del**

This command removes the policer from the interface.

- Usage:
  ```
  config interface policer del <interface_name>
  ```

- Example:
  ```
  admin@sonic:~$ sudo config interface policer remove Ethernet0
  ```

**config acl add table**

The command already existed, and this update merely adds "POLICER" type for the "table_type".

- Usage:
  ```
  config acl add table [OPTIONS] <table_name> POLICER [-d <description>] [-p <ports>] [-s (ingress | egress)]
  ```

- Examples:
  ```
  admin@sonic:~$ sudo config acl add table EXAMPLE POLICER -p Ethernet0 -s ingress
  ```

**acl-loader update full**

The command already existed, and this update only adds the "--policer" option to allow ACL to bind the policer.

When "--policer" optional argument is specified, command sets the policer for the ACL table with this policer. It fails if the specified policer does not exist.

- Usage:
  ```
   acl-loader update full [--table_name <table_name>] [--session_name <session_name>] [--mirror_stage (ingress | egress)] [--max_priority <priority_value>] [--policer <policer_name>] <acl_json_file_name>
  ```

**acl-loader update incremental**

The command already existed, and this update only adds the "--policer" option to allow ACL to bind the policer.

When "--policer" optional argument is specified, command sets the policer for the ACL table with this policer. It fails if the specified policer does not exist.

- Usage:
  ```
   acl-loader update incremental [--table_name <table_name>] [--session_name <session_name>] [--mirror_stage (ingress | egress)] [--max_priority <priority_value>] [--policer <policer_name>] <acl_json_file_name>
  ```

**config acl update full**

The command already existed, and this update only adds the "--policer" option to allow ACL to bind the policer.

When "--policer" optional argument is specified, command sets the policer for the ACL table with this policer. It fails if the specified policer does not exist.

- Usage:
  ```
  config acl update full [--table_name <table_name>] [--session_name <session_name>] [--mirror_stage (ingress | egress)] [--max_priority <priority_value>] [--policer <policer_name>] <acl_json_file_name>
  ```

- Examples:
  ```
  admin@sonic:~$ sudo config acl update full "--policer policer_1 /etc/sonic/acl_full_policer_1.json"
  ```

**config acl update incrementall**

The command already existed, and this update only adds the "--policer" option to allow ACL to bind the policer.

When "--policer" optional argument is specified, command sets the policer for the ACL table with this policer. It fails if the specified policer does not exist.

- Usage:
  ```
  config acl update incremental [--session_name <session_name>] [--mirror_stage (ingress | egress)] [--max_priority <priority_value>] [--policer <policer_name>] <acl_json_file_name>
  ```

- Examples:
  ```
  admin@sonic:~$ sudo config acl update incremental "--policer policer_1 /etc/sonic/acl_incremental_policer_1.json"
  ```


**show commands**

**show policer**

The command originally existed; this time, it only adds the display of new fields.

- Usage:
  ```
  show policer [POLICER_NAME]
  ```

- Example:
  ```
  admin@sonic:~$ show policer
  Name       Mode    Type     Color_source    CIR     CBS     PIR     PBS     Green    Yellow    Red    Mirror    Acl_rule    Interface
  ---------  ------  -------  --------------  ------  ------  ------  ------  -------  --------  -----  --------  ----------  -----------
  policer_1  sr_tcm  packets  blind           1024    2048                                                                    Ethernet1
  policer_2  tr_tcm  bytes    aware           102400  204800  204800  409600           drop      drop   mirror_2
  ```

##### 1.9.1.2. YANG

**Interface Policer Config**

Add PORT_POLICER container node to the sonic-policer.yang file.


	//filename:  sonic-policer.yang

	import sonic-types {
	  prefix stypes;
	}

	import sonic-port {
		prefix port;
	}

	...

          }
          /* end of container POLICER */

          container PORT_POLICER {

              description "PORT_POLICER part of config_db.json";

              list PORT_POLICER_LIST {

                  key "port";

                  leaf port {
                      type leafref {
                          path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                      }
                  }

                  leaf policer_name {
                      type leafref {
                          path "/policer:sonic-policer/policer:POLICER/policer:POLICER_LIST/policer:name";
                      }
                  }
              }
              /* end of list PORT_POLICER_LIST */
          }
          /* end of list PORT_POLICER */
  	...


**ACL Table Config**

Add a new acl\_table_type, POLICER, to the sonic-types.yang file.

 	//filename:  sonic-types.yang

  	...

	  typedef acl_table_type {
	      type enumeration {
	          enum L2;
	          enum L3;
	          enum L3V6;
	          enum MIRROR;
	          enum MIRRORV6;
	          enum MIRROR_DSCP;
	          enum CTRLPLANE;
	          enum MIRROR;
	          enum POLICER;
	      }
	  }

  	...


Add POLICER_ACTION leaf node to the sonic-acl.yang.

	//filename:  sonic-acl.yang
	
	  import sonic-mirror-session {
	      prefix sms;
	  }
	
	  import sonic-policer {
	      prefix policer;
	  }

  		...

                  leaf MIRROR_EGRESS_ACTION {
                      type leafref {
                          path "/sms:sonic-mirror-session/sms:MIRROR_SESSION/sms:MIRROR_SESSION_LIST/sms:name";
                      }
                  }

                  leaf POLICER_ACTION {
                      type leafref {
                          path "/policer:sonic-policer/policer:POLICER/policer:POLICER_LIST/policer:name";
                      }
                  }

  		...

#### 1.9.2. Config DB Enhancements  

**Interface Policer Config**

	PORT_POLICER|{ifname}
	; Defines schema for interface policer configuration attributes
	key                   = POLICER:ifname ; Interface name
	; field               = value
	policer_name          = string , Policer name


 - Example:

		{
		  "PORT_POLICER": {
		      "Ethernet0": {
		          "policer_name": "policer_1"
		      }
		  }
		}

**POLICER table type defined in ACL_TABLE:**

In table, ACL_TABLE field:type new value "POLICER" is defined along with existing types "L3" or "MIRROR"

 - Example:

		{
		  "ACL_TABLE": {
		      "POLICER_ACL": {
		          "STAGE": "INGRESS",
		          "TYPE" : "POLICER",
		          "PORTS": [
		              "Ethernet0"
		          ]
		      }
		  }
		}


#### 1.9.3. Orchagent changes  

**PolicerOrch**

Create a new function, *handlePortPolicerTable()*, similar to *handlePortStormControlTable()*, to implement the feature of binding a policer to an interface.

**AclOrch**

 - Add the table_type "POLICER" to the *initDefaultTableTypes()* function, including ipv4 and ipv6.
 - Similar to the *AclRuleMirror* class, create the *AclRulePolicer* class. The basic process is quite similar.
		
### 1.10. Warmboot and Fastboot Design Impact  
NA

### 1.11. Memory Consumption
NA
### 1.12. Restrictions/Limitations  

### 1.13. Testing Requirements/Design  

#### 1.13.1. Unit Test cases  

TODO
#### 1.13.2. System Test cases
	
TODO

### 1.14. Open/Action items - if any 
	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
