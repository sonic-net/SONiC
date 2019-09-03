# SONiC YANG MODEL DEVELOPMENT GUIDE

### Rev 0.1



## Revision

| Rev |     Date    |       Author            | Change Description                |
|:---:|:-----------:|:-----------------------:|-----------------------------------|
| 0.1 | 09/03/2019  | Partha Dutta            | Initial draft version                   |


## References
| References 				|     Date/Version    |       Link      	|
|:-------------------------:|:-------------------:|:-----------------------------------:|
| RFC 7950                  | August 2016         | https://tools.ietf.org/html/rfc7950 |
| Management Framework      | 0.9                 | TBD                                 |


## Overview 
This document provides guideline for developing SONiC YANG model. [RFC 7950](https://tools.ietf.org/html/rfc7950) (YANG 1.1 Data Modeling Language) is used as the main reference for writing SONiC YANG model. SONiC YANG models are used in configuration management in [SONiC Management Framework](https://github.com/Azure/SONiC/pull/436). At Northbound the entire YANG model is used. At Southbound, the configuration objects are used for validating ABNF based configuration and it is called CVL (Configuration Validation Library) YANG. CVL YANG is derived from SONiC YANG model. Please refer to "[Management Framework](https://github.com/Azure/SONiC/pull/436)" for further details on CVL and usage of SONiC YANG model.

## Guidelines 

1. SONIC YANG schema is 1:1 mapping of ABNF schema. So ABNF schema is taken as reference and SONiC YANG model is written based on it.

2. All related data definitions should be written in a single YANG model file. YANG model file is named as 'sonic-<feature>.yang', e.g. for ACL feature sonic-acl.yang is the file name. It is mandatory to define a top level YANG container named as 'sonic-<feature>' i.e. same as YANG model name. For example, sonic-acl.yang should have 'sonic-acl' as top level container. All other definition should be written inside the top level container.

Example :
```
module sonic-acl {
	container sonic-acl {
		.....
		.....
	}
}
```

3. Define common data types in a common YANG model like sonic-common.yang file. All YANG extensions are also defined in sonic-common.yang.

4. Define namespace as "http://github.com/Azure/<model-name>" and define a shorter(preferably within 3-4 letters) namespace prefix. Use the prefix in XPath for referring to any node present in other model.

Example :
```
module sonic-mirror-session {
	namespace "http://github.com/Azure/sonic-mirror-session";
	prefix sms;
	.....
	.....
}
```

5. Use 'revision' to record revision history. This needs to be updated with appropriate details whenever YANG model is changed.

Example :
```
module sonic-acl {
	revision 2019-09-02 {
		description
			"Added must expression for ACL_RULE_LIST.";
	}
	
	revision 2019-09-01 {
		description
			"Initial revision.";
	}

	container sonic-acl {
		.....
		.....
	}
}
```

6. Provide proper description for schema node definition using 'description' keyword wherever required. Description text provided in ABNF schema can be used here.

#### ABNF
```
ports         = [0-max_ports]*port_name ; the ports to which this ACL
                                        ; table is applied
```

#### YANG
```
module sonic-acl {
	.....
	.....
	
	leaf-list ports {
		type string;
		description "The ports to which this ACL table is applied";
	}
	.....
	.....

}
```

7. Define a YANG 'list' for each table in ABNF schema. The list name should exactly same as the table name including its case and a suffix "_LIST" or "_list" should be appended depending on the ABNF table name's case. The list should have container as its parent and name should be same as the table name in ABNF schema. Note that adding containers still keeps the hierarchy of the objects storing data same as in ABNF schema. 

Example : 

#### ABNF
```
key           = ACL_TABLE:name          ; acl_table_name must be unique
.....
.....
```

#### YANG
```
container ACL_TABLE {
	list ACL_TABLE_LIST {
	.....
	.....
	}
}
```
8. By default table is defined in CONFIG_DB, if needed use extension 'scommon:db-name' for defining the table in other DB.
   Example - 'scommon:db-name "APPL_DB"'.
   
9. The default separator used in table key pattern is "|". If it is different, use  'scommon:key-delim <separator>;' YANG extension.

Example : 
```
container ACL_TABLE {
	list ACL_TABLE_LIST {
		scommon:key-delim ":";
		.....
		.....
	}
}
```

10. Define same number of key elements as specified in table in ABNF schema. Though, key names are not stored in Redis DB, use the same key name as in ABNF schema.

Example : 

#### ABNF
```
key: ACL_TABLE:aclname
.....
.....
```

#### YANG
```
container ACL_TABLE {
	list ACL_TABLE_LIST {
		key aclname;
		
		leaf aclname {
			type string;
		}
		.....
		.....
	}
}
```

11. If any key refers to other table, use leafref type for the key leaf definition. 

Example : 
#### ABNF

```
key: ACL_RULE_TABLE:table_name:rule_name
.....
.....
```
#### YANG
```
container ACL_TABLE {
	list ACL_TABLE_LIST {
		key aclname;
			
		leaf aclname {
			type string;
		}
		.....
		.....
	}
}

container ACL_RULE {
	list ACL_RULE_LIST {
		key "aclname rulename";
		
		leaf aclname {
			type leafref {
				path "../../../ACL_TABLE/ACL_TABLE_LIST/aclname";
			}
		}
		
		leaf rulename {
			type string;
		}
		.....
		.....
	}
}
```

12. Generally the default key pattern is '{table_name}|{key1}|{key2}. However, if needed use '*' for repetitive key pattern e.g. 'scommon:key-pattern QUEUE|({ifname},)*|{qindex}'. 

Example :

#### ABNF
```
key  = "QUEUE:"port_name":queue_index' 
```

#### YANG
```
	list QUEUE {
		key "ifname qindex";
		scommon:key-pattern "QUEUE|({ifname},)*|{qindex}";
		leaf ifname {
			type leafref {
				path "/prt:sonic-port/prt:PORT/prt:ifname";
			}
		}
		leaf qindex {
			type string {
				pattern "[0-8]((-)[0-8])?";
			}
		}
	}
```


13. Mapping tables in Redis are defined using nested 'list'. Use 'scommon:map-list "true";' to indicate that the 'list' is used for mapping table. The outer 'list' is used for multiple instances of mapping. The inner 'list' is used for mapping entries for each outer list instance.

Example :

#### ABNF
```
; TC to queue map
;SAI mapping - qos_map with SAI_QOS_MAP_ATTR_TYPE == SAI_QOS_MAP_TC_TO_QUEUE. See saiqosmaps.h
key                    = "TC_TO_QUEUE_MAP_TABLE:"name
;field
tc_num = 1*DIGIT
;values
queue  = 1*DIGIT; queue index

```

#### YANG
```
	container TC_TO_QUEUE_MAP {
		list TC_TO_QUEUE_MAP_LIST {
			key "name";
			scommon:map-list "true"; //special annotation for map table

			leaf name {
				type string;
			}

			list TC_TO_QUEUE_MAP_LIST { //this is list inside list for storing mapping between two fields
				key "tc_num qindex";
				leaf tc_num {
					type string {
						pattern "[0-9]?";
					}
				}
				leaf qindex {
					type string {
						pattern "[0-9]?";
					}
				}
			}
		}
	}
```

14. Each field in table instance i.e. hash entries in Redis is defined as a leaf in YANG list. Use appropriate data type for each field. Use enum, range and pattern as needed for defining data syntax constraint. 'leaf-list' is defined when array of values are used. Use IETF data types for leaf type wherever possible. Declare new type in common YANG model only if IETF type is not available. For existing feature enum values can be referenced from source code i.e. header file.


Example :
#### ABNF
```
key           = ACL_TABLE:name          ; acl_table_name must be unique
;field        = value
policy_desc   = 1*255VCHAR              ; name of the ACL policy table description
type          = "MIRROR"/"L2"/"L3"/"L3v6"    ; type of acl table, every type of
                                        ; table defines the match/action a
                                        ; specific set of match and actions.
stage 		  = "INGRESS"/"EGRESS" 	    ; Stage at which policy is applied
ports         = [0-max_ports]*port_name ; the ports to which this ACL
                                        ; table is applied, can be emtry
                                        ; value annotations
port_name     = 1*64VCHAR               ; name of the port, must be unique
max_ports     = 1*5DIGIT                ; number of ports supported on the chip
```

#### YANG
```
container ACL_TABLE {
	list ACL_TABLE_LIST {
		key aclname;
			
		leaf aclname {
			type string;
		}

		leaf policy_desc {
			type string {
				length 1..255 {
					error-app-tag policy-desc-invalid-length;
				}
			}
		}

		leaf stage {
			type enumeration {
				enum INGRESS;
				enum EGRESS;
			}
		}

		leaf type {
			type enumeration {
				enum MIRROR;
				enum L2;
				enum L3;
				enum L3V6;
			}
		}

		leaf-list ports {
			type leafref {
				path "/prt:sonic-port/prt:PORT/prt:ifname";
			}
		}
	}
}
```

15. Use 'leafref' to build relationship between two tables.

Example:

	leaf MIRROR_ACTION {
		 type leafref {
			 path "/sms:sonic-mirror-session/sms:MIRROR_SESSION/sms:name";
		 }
	}


16. 'ref_hash_key_reference' in ABNF schema is defined using 'leafref' to the referred table.

Example : 

#### ABNF
```
; QUEUE table. Defines port queue.
; SAI mapping - port queue.

key             = "QUEUE_TABLE:"port_name":queue_index
queue_index     = 1*DIGIT
port_name       = ifName
queue_reference = ref_hash_key_reference

;field            value
scheduler    = ref_hash_key_reference; reference to scheduler key
wred_profile = ref_hash_key_reference; reference to wred profile key

```

#### YANG
```
container sonic-queue {
	container QUEUE {
		list QUEUE_LIST {
			key "ifname qindex";

			leaf ifname {
				type leafref {
					path "/prt:sonic-port/prt:PORT/prt:ifname";
				}
			}

			leaf qindex {
				type string {
					pattern "[0-8]((-)[0-8])?";
				}
			}

			leaf scheduler {
				type leafref {
					path "/sch:sonic-scheduler/sch:SCHEDULER/sch:name";
				}
			}

			leaf wred_profile {
				type leafref {
					path "/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:name";
				}
			}
		}
	}
}
```

17. To establish complex relationship and constraints among multiple tables use 'must' expression. Define appropriate error message for reporting to Northbound when condition is not met. For existing feature, code logic could be  reference point for deriving 'must' expression.
Example:

```
	must "(/scommon:operation/scommon:operation != 'DELETE') or " +
		"count(../../ACL_TABLE[aclname=current()]/ports) = 0" {
			error-message "Ports are already bound to this rule.";
	}
```

18. Define appropriate 'error-app-tag' and 'error' messages for in 'length', 'pattern', 'range' and 'must' statement so that management application can use it for error processing.

Example:
```
	leaf vlanid {
		mandatory true;
		type uint16 {
			range "1..4095" {
				error-message "Vlan ID out of range";
				error-app-tag vlanid-invalid;
			}
		}
	}
```	


19. Use 'when' statement for conditional data definition.

Example :

```
container ACL_RULE {
	list  ACL_RULE_LIST {
	....
	....
	
	leaf IP_TYPE {
		type enumeration {
				enum ANY;
				enum IP;
				enum IPV4;
				enum IPV4ANY;
				enum NON_IPV4;
				enum IPV6ANY;
				enum NON_IPV6;
		}
	}

	....
	....
	choice ip_src_dst {
		case ipv4_src_dst {
				when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV4' or .='IPV4ANY'])";
				leaf SRC_IP {
						mandatory true;
						type inet:ipv4-prefix;
				}
				leaf DST_IP {
						mandatory true;
						type inet:ipv4-prefix;
				}
		}
		case ipv6_src_dst {
				when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV6' or .='IPV6ANY'])";
				leaf SRC_IPV6 {
						mandatory true;
						type inet:ipv6-prefix;
				}
				leaf DST_IPV6 {
						mandatory true;
						type inet:ipv6-prefix;
				}
		}
		}
	}
	
	....
	....
}
```

20. Add read-only nodes for state data using 'config false' statement. Define a separate top level container for state data.

Example:
```
container ACL_RULE {
	list  ACL_RULE_LIST {
	....
	....
		container state {
			config false;
			description "State data";

			leaf MATCHED_PACKETS {
				type yang:counter64;
			}

			leaf MATCHED_OCTETS {
				type yang:counter64;
			}
		}
	}
}
```

21. Define custom RPC for executing command like clear, reset etc. No configuration should change through such RPCs. Define 'input and 'output' as needed, however they are optional.

Example:
```
container sonic-acl {
	....
	....
	rpc clear-stats {		
		input {
			leaf aclname {
					type string;
			}
			
			leaf rulename {
				type string;
			}
		}
	}
}
```

22. Define Notification for sending out events generated in the system, e.g. link up/down or link failure event. 

Example:
```
module sonic-port {
	....
	....
	notification link_event {
		leaf port {
			type leafref {
				path "../../PORT/PORT_LIST/ifname";
			}
		}
	}
}
```

23. Once YANG file is written, place it inside 'models/yang/' folder in 'sonic-mgmt-framework' framework repository.
