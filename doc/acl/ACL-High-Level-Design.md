# ACL in SONiC
# High Level Design Document
### Rev 0.4

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definitions/Abbreviation](#definitionsabbreviation)
  * [1 Sub-system Overview](#1-sub-system-overview)
    * [1.1 System Chart](#11-system-chart)
    * [1.2 Modules description](#12-modules-description)
      * [1.2.1 swssconfig](#121-swssconfig)
      * [1.2.2 App DB](#122-app-db)
      * [1.2.3 Orchestration Agent](#123-orchestration-agent)
      * [1.2.4 SAI Redis](#124-sai-redis)
      * [1.2.5 SAI DB](#125-sai-db)
      * [1.2.6 syncd](#126-syncd)
      * [1.2.7 SAI (Redis and Switch)](#127-sai-redis-and-switch)
  * [2 ACL Subsystem Requirements Overview](#2-acl-subsystem-requirements-overview)
    * [2.1 Functional requirements](#21-functional-requirements)
    * [2.2 Scalability requirements](#22-scalability-requirements)
    * [2.3 Requirements implementation schedule](#23-requirements-implementation-schedule)
  * [3 Modules Design](#3-modules-design)
    * [3.1 Phase 1](#31-phase-1)
      * [3.1.1 swssconfig](#311-swssconfig)
      * [3.1.2 App DB](#312-app-db)
        * [3.1.2.1 App DB Schema Reference](#3121-app-db-schema-reference)
          * [3.1.2.1.1 ACL Tables Table](#31211-acl-tables-table)
          * [3.1.2.1.2 ACL Rules Table](#31212-acl-rules-table)
        * [3.1.2.2 ACL Table](#3122-acl-table)
        * [3.1.2.3 ACL Rule](#3123-acl-rule)
        * [3.1.2.4 Table of type "L3"](#3124-table-of-type-l3)
        * [3.1.2.5 Table of type "Mirror"](#3125-table-of-type-mirror)
      * [3.1.3 Orchestration Agent](#313-orchestration-agent)
        * [3.1.3.1 Class AclOrch](#3131-class-aclorch)
        * [3.1.3.2 Acl Table Create or Delete](#3132-acl-table-create-or-delete)
        * [3.1.3.3 Acl Rule Create or Delete](#3133-acl-rule-create-or-delete)
      * [3.1.4 SAI Redis](#314-sai-redis)
      * [3.1.5 SAI DB](#315-sai-db)
      * [3.1.6 syncd](#316-syncd)
      * [3.1.7 General updates](#317-general-updates)
    * [3.2 Phase 2](#32-phase-2)
      * [3.2.1 Orchestration Agent](#321-orchestration-agent)
        * [3.2.1.1 Counters](#3211-counters)
        * [3.2.1.2 ACL Table Update](#3212-acl-table-update)
        * [3.2.1.3 ACL Rule Update](#3213-acl-rule-update)
        * [3.2.1.4 Configuration update](#3214-configuration-update)
    * [3.3 Phase 3](#33-phase-3)
      * [3.3.1 Orchestration Agent](#331-orchestration-agent)
        * [3.3.1.1 ACL Ranges support:](#3311-acl-ranges-support)
        * [3.3.1.2 Binding ACL Table to Port](#3312-binding-acl-table-to-port)
        * [3.3.1.3 ACL and LAG](#3313-acl-and-lag)
        * [3.3.1.4 ACL mirroring](#3314-acl-mirroring)
  * [4 Flows](#4-flows)
    * [4.1 Creating of ACL Objects](#41-creating-of-acl-objects)
    * [4.2 Deleting of ACL Objects](#42-deleting-of-acl-objects)
    * [4.3 Updating of ACL Objects](#43-updating-of-acl-objects)
    * [4.4 Creating of ACL Mirror rules](#44-creating-of-acl-mirror-rules)
    * [4.5 Deleting of ACL Mirror rules](#45-deleting-of-acl-mirror-rules)
    * [4.6 Mirror state change handling](#46-mirror-state-change-handling)
  * [5 swssconfig input file format and restrictions](#5-swssconfig-input-file-format-and-restrictions)
  * [6 Testing](#6-testing)
    * [6.1 Testing environment](#61-testing-environment)
    * [6.2 List of tests to cover basic functionality](#62-list-of-tests-to-cover-basic-functionality)
    * [6.3 Additional tests for Pase 2/3](#63-additional-tests-for-pase-23)
  * [Appendix A:Keywords for matches and actions](#appendix-akeywords-for-matches-and-actions)
  * [Appendix B: Sample input json file](#appendix-b-sample-input-json-file)
  * [Appendix C: Code sample](#appendix-c-code-sample)

# List of Tables
* [Table 1: Revision](#revision)
* [Table 2: Abbreviations](#definitionsabbreviation)
* [Table 3: Implementation schedule](#23-requirements-implementation-schedule)
* [Table 4: Matches allowed in the table of the type "L3"](#3124-table-of-type-l3)
* [Table 5: Actions allowed in the table of the type "L3"](#table-5-actions-allowed-in-the-table-of-the-type-l3)
* [Table 6: Matches allowed in the table of the type "mirror"](#3125-table-of-type-mirror)
* [Table 7: Actions allowed in the table of the type "mirror"](#table-7-actions-allowed-in-the-table-of-the-type-mirror)
* [Table 8: Json file keywords](#table-8-json-file-keywords)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Andriy Moroz       | Initial version                   |
| 0.2 | 4-Nov-2016  | Andriy Moroz       | Fixes after pre-DR                |
| 0.3 | 10-Nov-2016 | Andriy Moroz       | Updated according to the comments |
| 0.4 | 20-Dec-2016 | Oleksandr Ivantsiv | Update data structures            |

# About this Manual
This document provides general information about the ACL feature implementation in SONiC.
# Scope
This document describes the high level design of the ACL feature.
# Definitions/Abbreviation
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| ACL                      | Access Control List                        |
| API                      | Application Programmable Interface         |
| SAI                      | Swich Abstraction Interface                |
| ERSPAN                   | Encapsulated Remote Switched Port Analysis |
| JSON                     | JavaScript Object Notation                 |

# 1 Sub-system Overview
## 1.1 System Chart
Following diagram describes a top level overview of the SONiC Switch components:
![](../raw/gh-pages/images/acl_hld/sonic_sub.png)
## 1.2 Modules description
### 1.2.1 swssconfig
Reads prepared json-files with ACL configuration and injects it into App DB.
### 1.2.2 App DB
Located in the Redis DB instance #0 running inside the container "database". Redis DB works with the data in format of key-value tuples, needs no predefined schema and can hold various types of data.
### 1.2.3 Orchestration Agent
This component is running in the "orchagent" docker container and is resdponsible for processing updates of the App DB and do corresponding changes in the SAI DB via SAI Redis.
### 1.2.4 SAI Redis
SAI Redis is an implementation of the SAI API which translates API calls into SAI objects which are stored in the SAI DB. Already hadles ACL data.
### 1.2.5 SAI DB
Redis DB instance #1. Holds serialized SAI objects.
### 1.2.6 syncd 
Reads SAI DB data (SAI objects) and performs appropriate calls to Switch SAI.
### 1.2.7 SAI (Redis and Switch)
An unified API which represent the switch state as a set of objects. In SONiC represented in two implementations - SAI DB frontend and ASIC SDK wrapper.
# 2 ACL Subsystem Requirements Overview
## 2.1 Functional requirements
*Mostly copy-paste from the provided acl.md*

- Support data plane ACL in SONiC (M)
- Support ACL table which contains a set of ACL rules (M)
ACL table has predefined type, each type defines the a set of match fields and actions available for the table. For example, mirror acl table only supports mirror as an action. (M)
- Support binding ACL table to ports, initially only support for front panel physical port binding (M)
- Support binding multiple ACL tables to ports. The use case is to have data plane ACL table which do permit/deny while have mirror ACL table do packet mirror for a same packet. Initial, there will be no conflicting actions between two ACL tables bound to the same set of ports. (M)
- Support matching ip src/dst, ip protocol, tcp/udp port in ACL rules (M)
- Support port range matching in ACL rules (M)
- Support permit/deny action in ACL rules (M)
- Support packet erspan mirror action in ACL rules (M)
- Packet counters for each acl rule (M)
- Byte counters for each acl rule (S)

## 2.2 Scalability requirements
- 1K ACL rules for L3 acl table
- 256 ACL rules for mirror
## 2.3 Requirements implementation schedule
###### **Table 3: Implementation schedule**
Requirement| Implementation Phase |Comment
-----------|----------------------|-------
Support data plane ACL in SONiC (M) | Phase 1
Support ACL table which contains a set of ACL rules (M) | Phase 1
ACL table has predefined type, each type defines the a set of match fields and actions available for the table. For example, mirror acl table only supports mirror as an action. (M) | Phase 1
Support binding ACL table to ports, initially only support for front panel physical port binding (M) | Phase 3 | Phase 1 ?
Support binding multiple ACL tables to ports. The use case is to have data plane ACL table which do permit/deny while have mirror ACL table do packet mirror for a same packet. Initial, there will be no conflicting actions between two ACL tables bound to the same set of ports. (M) | Phase 3
Support matching ip src/dst, ip protocol, tcp/udp port in ACL rules (M) | Phase 1
Support port range matching in ACL rules (M) | Phase 3 | Phase 1 ?
Support permit/deny action in ACL rules (M) | Phase 1
Support packet erspan mirror action in ACL rules (M) | Phase 1 | Phase 3
Packet counters for each acl rule (M) | Phase2
Byte counters for each acl rule (S) | Phase2
ACL and LAG | Phase 3
Configuration update | Phase 2

# 3 Modules Design
## 3.1 Phase 1
In the Phase 1 there will be implemented basic ACL functionality: complete data flow (from input json file to ASIC), creating/removing ACL Tables and ACL Rules, rules will support simple matching (all except ranges) and permit/deny actions.
### 3.1.1 swssconfig
Swssconfig is generic enough and probably needs no update to support ACL.
Make sure it supports the ACL configuration json provided in the Appendix B
### 3.1.2 App DB
No update is needed to support ACL.
#### 3.1.2.1 App DB Schema Reference
##### 3.1.2.1.1 ACL Tables Table
    key           = ACL_TABLE:name          ; acl_table_name must be unique
    ;field        = value
    policy_desc   = 1*255VCHAR              ; name of the ACL policy table description
    type          = "mirror"/"l3"           ; type of acl table, every type of
                                            ; table defines the match/action a
                                            ; specific set of match and actions.
    ports         = [0-max_ports]*port_name ; the ports to which this ACL
                                            ; table is applied, can be emtry
                                            ; value annotations
    port_name     = 1*64VCHAR               ; name of the port, must be unique
    max_ports     = 1*5DIGIT                ; number of ports supported on the chip
##### 3.1.2.1.2 ACL Rules Table
    key: ACL_RULE_TABLE:table_name:rule_name   ; key of the rule entry in the table,
                                               ; seq is the order of the rules
                                               ; when the packet is filtered by the
                                               ; ACL "policy_name".
                                               ; A rule is always assocaited with a
                                               ; policy.

    ;field        = value
    PRIORITY      = 1*3DIGIT                   ; rule priority. Valid values range
                                               ; could be platform dependent

    PACKET_ACTION = "forward"/"drop"/"mirror"  ; action when the fields are
                                               ; matched (mirror action only
                                               ; available to mirror acl table
                                               ; type)

    MIRROR_ACTION = 1*255VCHAR                 ; refer to the mirror session
                                               ; (only available to mirror acl
                                               ; table type)

    ETHER_TYPE    = h16                        ; Ethernet type field

    IP_TYPE       = ip_types                   ; options of the l2_protocol_type
                                               ; field. Only v4 is support for
                                               ; this stage.

    IP_PROTOCOL   = h8                         ; options of the l3_protocol_type field

    SRC_IP        = ipv4_prefix                ; options of the source ipv4
                                               ; address (and mask) field

    DST_IP        = ipv4_prefix                ; options of the destination ipv4
                                               ; address (and mask) field

    L4_SRC_PORT   = port_num                   ; source L4 port or the
    L4_DST_PORT   = port_num                   ; destination L4 port

    L4_SRC_PORT_RANGE = port_num_L-port_num_H  ; source ports range of L4 ports field
    l4_DST_PORT_RANGE = port_num_L-port_num_H  ; destination ports range of L4 ports field

    TCP_FLAGS     = h8/h8                      ; TCP flags field and mask
    DSCP          = h8                         ; DSCP field (only available for mirror
                                               ; table type)

    ;value annotations
    ip_types = any | ip | ipv4 | ipv4any | non_ipv4 | ipv6any | non_ipv6
    port_num      = 1*5DIGIT   ; a number between 0 and 65535
    port_num_L    = 1*5DIGIT   ; a number between 0 and 65535,
                               ; port_num_L < port_num_H
    port_num_H    = 1*5DIGIT   ; a number between 0 and 65535,
                               ; port_num_L < port_num_H
    ipv6_prefix   =                 6( h16 ":" ) ls32
       /                       "::" 5( h16 ":" ) ls32
       / [               h16 ] "::" 4( h16 ":" ) ls32
       / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
       / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
       / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
       / [ *4( h16 ":" ) h16 ] "::"              ls32
       / [ *5( h16 ":" ) h16 ] "::"              h16
       / [ *6( h16 ":" ) h16 ] "::"
    h8          = 1*2HEXDIG
    h16         = 1*4HEXDIG
    ls32        = ( h16 ":" h16 ) / IPv4address
    ipv4_prefix = dec-octet "." dec-octet "." dec-octet "." dec-octet “/” %d1-32
    dec-octet   = DIGIT                     ; 0-9
                    / %x31-39 DIGIT         ; 10-99
                    / "1" 2DIGIT            ; 100-199
                    / "2" %x30-34 DIGIT     ; 200-249
#### 3.1.2.2 ACL Table
ACL Tables will be added to the App DB under the key ACL_TABLE:table_id. table_id is some string which will be specified by the user and should be unique across the App DB. table__id will be used to refer the table when adding rules and updating or deleting the table.
Tables will have the following properties:

- policy_desc name of the ACL policy table description
- type one of the two predefined table types: "L3" or "mirror"
- ports the list or ports bound to the table

Table type defines also a list of supported matches that could be used in rules belonging to this table.
#### 3.1.2.3 ACL Rule
ACLRules will be added to the App DB under the key ACL_RULE_TABLE:table_id:rule_id. table_id is the table ID the rule belongs to and the rule_id is some string which should be unique across the Table. rule_id will be used to refer the Rule when it is needed to update or delete the Rule.
Rules will have the following properties:

- priority - rule priority in the table
- match:value - packet properties this rule will match
- action:value - action to be applied to the rule if match was successful

The list of allowed matches and actions depends on the table the rule will go to. Complete list of supported matches and actions provided in chapters 3.1.3.4 and 3.1.3.5.
#### 3.1.2.4 Table of type "L3"
###### **Table 4: Matches allowed in the table of the type "L3"**
Keyword for the match criteria | Type | Description
-------------------------------|------|------------
ETHER_TYPE | uint16_t | Hexadecimal integer [0..FFFF]
IP_TYPE | string | One of: "IPv4"/"NON_IPv4"/"ARP"
IP_PROTOCOL | uint8_t | Hexadecimal unsigned integer [0..FF]
SRC_IP | ip_address | A valid IPv4 subnet in format IP/Mask
DST_IP | ip_address | A valid IPv4 subnet in format IP/Mask
L4_SRC_PORT | uint16_t | Decimal unsigned integer [0..65535]
L4_DST_PORT | uint16_t | Decimal unsigned integer [0..65535]
TCP_FLAGS | uint8_t | Hexadecimal unsigned integer [0..FF]
L4_SRC_PORT_RANGE | uint16_t, uint16_t | Two dash separated decimal unsigned integers [0..65535]
L4_DST_PORT_RANGE | uint16_t, uint16_t | Two dash separated decimal unsigned integers [0..65535]

###### **Table 5: Actions allowed in the table of the type "L3"**
Keyword for the action type    | Type | Description
-------------------------------|------|------------
PACKET_ACTION | string | Packet action value: "FORWARD" or "DROP"

#### 3.1.2.5 Table of type "Mirror"
###### **Table 6: Matches allowed in the table of the type "mirror"**
Keyword for the match criteria | Type | Description
-------------------------------|------|------------
IP_PROTOCOL | uint8_t | IP protocol type in hexadecimal format [0..FF]
DSCP | uint8_t | Hexadecimal unsigned integer [0..FF]
SRC_IP | ip_addr/mask | A valid IPv4 subnet in format IP/Mask
DST_IP | ip_addr/mask | A valid IPv4 subnet in format IP/Mask
L4_SRC_PORT | uint16_t | Decimal unsigned integer [0..65535]
L4_DST_PORT | uint16_t | Decimal unsigned integer [0..65535]
###### **Table 7: Actions allowed in the table of the type "mirror"**
Keyword for the action type    | Type | Description
-------------------------------|------|------------
MIRROR_ACTION | string | Mirror session name

### 3.1.3 Orchestration Agent
Orchestration Agent needs to be updated in order to support ACL in the AppDB and the SAI ACL API. There will be class AclOrch and a set of data structures implemented to handle ACL feature.
Tables or rules create, delete and update Orchestration Agent will process basing on App DB changes. Some object updates updates will be handled and some will be considered as invalid.
See Chapter 5 for the details.

#### 3.1.3.1 Class AclOrch
Class AclOrch will hold a set of methods matching generic Orch class pattern to hanle App DB updates. The class will be initialized with the list of ACL tables to subscribe to the appropriate App DB updates. doTask() method will be called on tables update and will distribute handling DB update between the other handlers basing on a table which was updated.  
Below is the skeleton of the AclOrch class:
```cpp
    struct AclRule {
    	sai_object_id_t saiId;
    	string rule_id;
    	map <matchName, matchValue> matches;
    	string action; // array?
    };
    
    Struct/class AclTable {
    	sai_object_id_t saiId;
    	string table_id;
    	string description;		// needed?
    	table_type_t m_type;
    	vector <AclRule> m_rules;
    };
    
    class AclOrch : public Orch {
    	void doTask();
    	void doAclTableTask();
    	void doAclRuleTask();
    	...
    	vector <AclTable> m_AclTables; 
    }
```
This class will be responsible for:

- processing updates of the ACL tables (create/delete/update)
- partial input data (App DB) validation (including cross-table validation)
- replicating ACL data from the App DB to the SAI DB via SAIRedis
- caching of the ACL objects in order to detect objects update and perform state dump.
#### 3.1.3.2 Acl Table Create or Delete
AclOrch class will inherit and reuse Orch class functionality which exploits producer-consumer mechanism (implemented in swss-common) to track changes in the Redis database tables. ACL Tables are stores under ACL_TABLE:* keys in App DB. On ACL_TABLE update in the App DB AclOrch::doAclTableTask() will be called to process the change. On table create AclOrch will verify if the table already exists (using table_id) creating of the table which already exists will be processed as update. Regular create or delete will update the internal class structures and appropriate SAI objects will be created or deleted.  
Validation: on create validate table type.
#### 3.1.3.3 Acl Rule Create or Delete
ACL Rules are stores under ACL_RULE_TABLE:* keys in App DB. On ACL_RULE_TABLE update in the App DB AclOrch::doAclRuleTask() will be called to process the change. On table create AclOrch will verify if the rule already exists (using rule_id) creating of the rule which already exists will be processed as update. Regular create or delete will update the internal class structures and appropriate SAI objects will be created or deleted.  
Validation: make sure the table exists, the list of match criterias is valid and fits the table, the list of actions is valid.
### 3.1.4 SAI Redis
No updates in Phase 1.
### 3.1.5 SAI DB
No updates in Phase 1.
### 3.1.6 syncd
No updates in Phase 1.
### 3.1.7 General updates
Add definitions for the table names "ACL_TABLE" and "ACL_RULE_TABLE" to the schema.h
## 3.2 Phase 2
### 3.2.1 Orchestration Agent
#### 3.2.1.1 Counters
Add handling of counter action for tables and rules. This assumes automatic counter object creation and adding it to each rule on create and removing on delete.
```c++
    struct AclRule {
    	sai_object_id_t saiId;
    	sai_object_id_t counter_oid;
    	string rule_id;
    	map <matchName, matchValue> matches;
    	string action; // array?
    };
```
There will counters to register number of packets and number of bytes processed by the rule.  
Counters will be stored to the DB #2 with the predefined period. Update period will be hard coded. The default value will be 10 seconds.  
DB Schema for ACL counters is the following:

	COUNTERS:ACL_TABLE_NAME:ACL_RULE_NAME
	Packets : <packets_counter_value>
	Bytes : <bytes_counter_value>

#### 3.2.1.2 ACL Table Update
If an update refers the table which already exists, this change will be considered as update. This will cause updating of internal records as well as corresponding SAI objects. Updating SAI objects may require recreating them.
#### 3.2.1.3 ACL Rule Update
If an update refers the rule which already exists, this change will be considered as update. This will cause updating of internal records as well as corresponding SAI objects.  
Validation: similar to the one performed on create.
#### 3.2.1.4 Configuration update
Besides strait forward "delete-create" way of update need to consider performing "safe update" when a new configuration will be created prior to removing the old one. And switch to the new configuration only if it is successfully created. This will require resolving at least two issues:

- need to be sure there are enough hardware resources to hold both old and new configurations
- update should be "atomic". I.e. Orchestration Agent should receive an entire update before starting an update.

Validation: similar to the one performed on create.

## 3.3 Phase 3
In Phase 3 there will be implemented ACL Ranges support and ACLTable to port binding.
### 3.3.1 Orchestration Agent
#### 3.3.1.1 ACL Ranges support:
In Orchestration Agent in class AclOrch:
```c++
	struct AclRange {
		sai_object_id_t saiId;
		tuple<min,max> range;
	}

	struct AclCounter {
		sai_object_id_t saiId;
	}

	struct AclRule {
		sai_object_id_t saiId;
		string rule_id;
		map <matchName, matchValue> matches;
		string action; // array?
		AclCounter byteCounter;
		AclCounter packetCounter;
	};
	
	struct/class AclTable {
		sai_object_id_t saiId;
		string table_id;
		string description;		// needed?
		table_type_t m_type;
		vector <string> m_ports;
		vector <AclRule> m_rules;
	};

	class AclOrch : public Orch {
		void doTask();
		void doAclTableTask();
		void doAclRuleTask();
		...
		vector <AclTable> m_AclTables;
		map <tuple<min, max>, AclRange> m_AclRanges;
	}
```
Add handling, caching and validation of range matching. This also includes detecting and reusing of identical ranges in order to save hardware resources.

#### 3.3.1.2 Binding ACL Table to Port
While declaring ACL table in a json config file it is mandatory to specify a port or the list of ports this table will be bound to. Starting from the SAI v1.0 multiple tables cannot be bound to one port. To implement this feature tables first have to be added to a group and then group could be bound to the port.  
Groups will be created and managed by Ports (`class Port`, implemented in `orchagent/port.cpp`). `PortsOrch` class API will be extended with the method `getPort` to return an appropriate Port class instance. The Port class will provide method `bindAclTable` which will handle creation of the group, binding this group to the port and adding given ACL table to the corresponding group.    

Code sample which binds table to the port:

    sai_status_t AclOrch::bindAclTable(sai_object_id_t table_oid,..)
    {
        for (const auto& portOid : aclTable.ports)
        {
            Port port;
            gPortsOrch->getPort(portOid, port);
            
            sai_object_id_t group_member_oid;
            status = port.bindAclTable(group_member_oid, table_oid);
        ...
If LAG port not created yet when bind ACL table to it, LAG port will be added to an internal pending port list, after LAG port created, AclOrch will get notification from STATE_DB, and will bind the ACL table to the LAG port. This is implemented by adding a "doAclTablePortUpdateTask" to handle the port configured notification from STATE_DB.

#### 3.3.1.3 ACL and LAG

- LAG member port shall not be added to the ACL Tables, or will be considered as invalid configuration and return fail.
- LAG ACL configurations will be automatically applied to all the LAG members, this is done by SAI/SDK.

#### 3.3.1.3 ACL mirroring
```c++
	class AclRule
	{
	public:
	    AclRule(AclOrch *aclOrch, string rule, string table);
	    virtual bool validateAddPriority(string attr_name, string attr_value);
	    virtual bool validateAddMatch(string attr_name, string attr_value);
	    virtual bool validateAddAction(string attr_name, string attr_value) = 0;
	    virtual bool validate() = 0;
	    bool processIpType(string type, sai_uint32_t &ip_type);
	
	    virtual bool create();
	    virtual bool remove();
	    virtual void update(SubjectType, void *) = 0;
	
	    string getId()
	    {
	        return id;
	    }
	
	    string getTableId()
	    {
	        return table_id;
	    }
	
	    sai_object_id_t getCounterOid()
	    {
	        return counter_oid;
	    }
	
	    static shared_ptr<AclRule> makeShared(acl_table_type_t type, AclOrch *acl, MirrorOrch *mirror, string rule, string table);
	    virtual ~AclRule() {};
	
	protected:
	    virtual bool createCounter();
	    virtual bool removeCounter();
	
	    AclOrch *aclOrch;
	    string id;
	    string table_id;
	    sai_object_id_t table_oid;
	    sai_object_id_t rule_oid;
	    sai_object_id_t counter_oid;
	    uint32_t priority;
	    map <sai_acl_entry_attr_t, sai_attribute_value_t> matches;
	    map <sai_acl_entry_attr_t, sai_attribute_value_t> actions;
	};
	
	class AclRuleL3: public AclRule
	{
	public:
	    AclRuleL3(AclOrch *aclOrch, string rule, string table);
	
	    bool validateAddAction(string attr_name, string attr_value);
	    bool validate();
	    void update(SubjectType, void *);
	};
	
	class AclRuleMirror: public AclRule
	{
	public:
	    AclRuleMirror(AclOrch *aclOrch, MirrorOrch *mirrorOrch, string rule, string table);
	    bool validateAddAction(string attr_name, string attr_value);
	    bool validate();
	    bool create();
	    bool remove();
	    void update(SubjectType, void *);
            AclRuleCounters getCounters();
	
	protected:
	    bool m_state;
	    string sessionName;
            acl_stage_type_t m_tableStage;
            AclRuleCounters counters;
	    MirrorOrch *m_pMirrorOrch;
	};
	
	struct AclTable {
	    string id;
	    string description;
	    acl_table_type_t type;
	    ports_list_t ports;
	    // Map rule name to rule data
	    map<string, shared_ptr<AclRule>> rules;
	    AclTable(): type(ACL_TABLE_UNKNOWN) {}
	};
```
To support mirror action bind to both ingress and egress ACL rule,  an member "acl_stage_type_t m_tableStage" added
to class AclRuleMirror to indicate the stage the ACL mirror rule, according to the stage can select proper mirror
action, "SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS" for ingress ACL rule, "SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS"
for egress ACL rule.  
Add possibility to receive updates about mirror sessions state change and perform mirroring rules state change accordingly.
# 4 Flows
## 4.1 Creating of ACL Objects
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/acl_create.png)
## 4.2 Deleting of ACL Objects
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/acl_delete.png)
## 4.3 Updating of ACL Objects
Depending on the number of changed properties in the updated ACL object, update may include one or more extra delete/create calls to the SAI Redis.  
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/acl_update.png)
## 4.4 Creating of ACL Mirror rules
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/acl_mirror_rule_flow.svg)
## 4.5 Deleting of ACL Mirror rules
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/mirror_delete.png)
## 4.6 Mirror state change handling
![](https://github.com/sonic-net/SONiC/blob/master/images/acl_hld/mirror_state_change.png)
# 5 swssconfig input file format and restrictions
- Valid json file. The file should be in the format swssconfig can process. This assumes lists surrounded by square brackets, dictionaries with curly brackets (braces), tuples inside dictionary separated with semicolon and enumerated elements separated with the comma.
- Logical consistency. The configuration provided should be complete. Rules should not refer non-existing tables, etc.
- Order: Tables should appear before Rules.
- The list of keywords to be used to address different match criterias and actions provided in Appendix A
- Rules should have at least one match criteria and one action
- List of ports to bind to the table should contain physical port names.
- Maximum number of rules allowed: 1000 rules total in the all "L3" tables and 256 rules total in all "Mirror" tables.  
See json file example is in Appendix B.
# 6 Testing
## 6.1 Testing environment
Ansible + PTF
## 6.2 List of tests to cover basic functionality
- simple permit (any)
- simple deny (any)
- permit/deny with matching (IP, port, ethertype, etc)
## 6.3 Additional tests for Pase 2/3
- permit/deny and counter
- permit/deny with range
- permit/deny with two ranges (src, dst)

# Appendix A:Keywords for matches and actions
###### **Table 8: Json file keywords**
|Keyword     | Description|
|------------|------------|
|policy_desc | ACL Table property, contains human readable table description string
|type        | ACL Table property. Could be "L3" or "Mirror"
|ports       | ACL Table property. String with comma separated port names.
|priority    | ACL Rule property. Rule priority in the table
|            | MATCHES
|src_ip      | ACL Rule property. Source IP address
|dst_ip      | ACL Rule property. Destination IP address
|l4_src_port | ACL Rule property. L4 source port
|l4_dst_port | ACL Rule property. L4 destination port
|l4_src_port_range | ACL Rule property. L4 source ports range. Valid for rules in "L3" tables only
|l4_dst_port_range | ACL Rule property. L4 destination ports range. Valid for rules in "L3" tables only
|ether_type    | ACL Rule property. Ethernet type
|ip_protocol   | ACL Rule property. Ip protocol
|tcp_flags     | ACL Rule property. TCP flags
|ip_type       | ACL Rule property. IP type
|dscp          | ACL Rule property. Dscp field. Valid for rules "mirror" tables only
|              | ACTIONS
|packet_action | ACL Rule property. Packet actions "forward" or "drop". Valid for rules in "L3" tables only
|mirror_action | Action "mirror". Valid for rules in "mirror" tables only
*Keywords derived from the SAI ACL attributes.*
# Appendix B: Sample input json file
```
	[
	    {
	        "ACL_TABLE:0d41db739a2cc107": {
			"policy_desc" : "Permit some traffic, for the customer #4",
			"type" : "L3"
			"ports" : [
                            "port1", 
                            "port2", 
                            "port3"
                        ] # physical port names
	        },
	        "OP": "SET"
	    },
	    {
	        "ACL_RULE_TABLE:0d41db739a2cc107:3f8a10ff": {
			"priority" : "55",
			"IP_PROTOCOL" : "TCP",
	            "SRC_IP" : "20.0.0.0/25",
	            "DST_IP" : "20.0.0.0/23",
	            "L4_SRC_PORT_RANGE: "1024-65535",
	            "L4_DST_PORT_RANGE: "80-89",
			"PACKET_ACTION" : "FORWARD"
	        },
	        "OP": "SET"
	    },
	]
```
# Appendix C: Code sample
Below is the pseudo-code in C which shows how the configuration described in the Appendix B will be applied using SAI API.
```c++
	// SAI API query...
	sai_acl_api_t  *acl_api;
	sai_port_api_t *port_api;
		
	// Create table
	sai_attribute_t table_attrs[] =
	{
	   {.id = SAI_ACL_TABLE_ATTR_STAGE,
	    .value.s32 = SAI_ACL_STAGE_INGRESS},
	   {.id = SAI_ACL_TABLE_ATTR_PRIORITY,
	    .value.u32 = 10},
	   {.id = SAI_ACL_TABLE_ATTR_SIZE, 
	    .value.u32 = 0},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_ETHER_TYPE,
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_IP_TYPE, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_IP_PROTOCOL, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_SRC_IP, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_DST_IP, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_L4_SRC_PORT, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_L4_DST_PORT, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_TCP_FLAGS, 
	    .value.booldata = true},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_RANGE, 
	    .value.s32 = SAI_ACL_RANGE_L4_SRC_PORT_RANGE},
	   {.id = SAI_ACL_TABLE_ATTR_FIELD_RANGE, 
	    .value.s32 = SAI_ACL_RANGE_L4_DST_PORT_RANGE}
	};
	
	size_t attrs_num = sizeof(table_attrs)/sizeof(table_attrs[0]);
	
	sai_status_t status;
	sai_object_id_t acl_table;
	
	status = acl_api->create_acl_table(&acl_table, attrs_num, table_attrs);
	
	// Create ranges
	sai_object_id_t acl_ranges[2];
	
	sai_attribute_t range_attrs[] =
	{
	   {.id = SAI_ACL_RANGE_ATTR_TYPE,
	     .value.s32 = SAI_ACL_RANGE_L4_SRC_PORT_RANGE},
	   {.id = SAI_ACL_RANGE_ATTR_LIMIT,
	    .value.u32range = (sai_u32_range_t) {.min = 1024, .max = 65535}}
	};
	
	attrs_num = sizeof(range_attrs)/sizeof(range_attrs[0]);
	status = acl_api->create_acl_range(&acl_ranges[0],attrs_num,range_attrs);
	status = acl_api->create_acl_range(&acl_ranges[1],...);
	
	
	// Create Entry (rule)
	sai_object_id_t entry;
	
	sai_attribute_t entry_attrs[] = {
	    {.id = SAI_ACL_ENTRY_ATTR_TABLE_ID,
	     .value.oid = acl_table},
	    {.id = SAI_ACL_ENTRY_ATTR_PRIORITY,
	     .value.u32 = 55},
	    {.id = SAI_ACL_ENTRY_ATTR_ADMIN_STATE,
	     .value.booldata = true},
	    {.id = SAI_ACL_ENTRY_ATTR_FIELD_SRC_IP,
	     .value.aclfield.data.ip4 = 0x14000000;
	     .value.aclfield.mask.ip4 = 0xFFFFFF80;
	    },
	    {.id = SAI_ACL_ENTRY_ATTR_FIELD_DST_IP,
	     .value.aclfield.data.ip4 = 0x14000000;
	     .value.aclfield.mask.ip4 = 0xFFFFFE00;
	    },
	    {.id = SAI_ACL_ENTRY_ATTR_FIELD_RANGE,
	     .value.aclfield.data.objlist.list = acl_ranges,
	     .value.aclfield.data.objlist.count = 2},
	    {.id = SAI_ACL_ENTRY_ATTR_PACKET_ACTION,
	     .value.aclaction.enable = true,
	     .value.aclaction.parameter.s32 = SAI_PACKET_ACTION_FORWARD}
	};
	
	attrs_num = sizeof(entry_attrs)/sizeof(entry_attrs[0]);
	status = acl_api->create_acl_entry(&entry, attrs_num, entry_attrs));
	
	
	// Bind ACL table to port
	sai_attribute_t port_attr = 
	{
	    .id = SAI_PORT_ATTR_INGRESS_ACL_LIST,
	    .value.objlist.list = acl_table,
	    .value.objlist.count = 1
	};
	
	status = port_api->set_port_attribute(port_object_id, &port_attr);
```
