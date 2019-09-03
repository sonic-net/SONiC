#   SONiC YANG MODEL GUIDELINES

### Rev 1.0 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 1.0 | 22 Aug 2019             |      Praveen Chaudhary      | Initial version                    |
 | 1.1 | 29 Aug 2019             |      Praveen Chaudhary      | Addressed review comments.



###  This document lists the guidelines, which will be used to write YANG Modules for SONiC. These YANG Modules will be primarily based on or represent the ABNF Schema of SONiC, and the syntax of YANG models must follow RFC 7950.

### These YANG models will be used to verify the configuration for SONiC switches, so a library which supports validation of configuration on SONiC Switch must use these YANG Models. List of such Libraries are: 1.) Configuration Validation Library. (CVL)



### 1. Each primary section of Config DB (i.e a dictionary in config_db.json) for Example, VLAN, VLAN_MEMBER, INTERFACE  in config DB will be mapped to a container in YANG model.

Example:

#### ABNF

```
"INTERFACE": {
        ~~"Ethernet112|2a04:fxxx:40:a709::xxx/126": {
            "scope": "global",
            "family": "IPv6"~~
        }
 }
```
will translate to:

####  YANG
--
```
container INTERFACE {
~~
~~
}
```

### 2. Each leaf in YANG module should have same name as corresponding key in Config DB.

Example:
Leaf names are same PACKET_ACTION, IP_TYPE and PRIORITY.

#### ABNF
```
        "NO-NSW-xxx|xxx": {
            "PACKET_ACTION": "FORWARD",
            "IP_TYPE": "IPv6ANY",
            "PRIORITY": "9xxxx20",
            .....
            ....
        },
```

####  YANG
```
            leaf PACKET_ACTION {
                type xxxx;
            }
            leaf IP_TYPE {
                type xxxx;
            }
            leaf PRIORITY {
                type uint32 {
                    range xxxx;
                }
            }
```


### 3. Data Node/Object Hierarchy of the an objects in YANG models will be same as for all the objects at same hierarchy in Redis. If any exception is created then it must be recorded properly.
For Example:

"Family" of VLAN_INTERFACE and "IP_TYPE" of ACL_RULE should be at same level in YANG model too.

#### ABNF
```
"VLAN_INTERFACE": {
        "Vlan100|2a04:f547:45:6709::1/64": {
            "scope": "global",
            "family": "IPv6"
        }
}
"ACL_RULE": {
        "NO-NSW-PACL-V4|DEFAULT_DENY": {
            "PACKET_ACTION": "DROP",
            "IP_TYPE": "IPv4ANY",
            "PRIORITY": "0"
        }
}
```
####  YANG
In YANG, "Family" of VLAN_INTERFACE and "IP_TYPE" of ACL_RULE is at same level.
```
container VLAN_INTERFACE {
        description "VLAN_INTERFACE part of config_db.json";
        list xxx {
    ......
    ......
            leaf family {
                type sonic-head:ip-family;
            }
        }
}

container ACL_RULE {
        description "ACL_RULE part of config_db.json";
        list xxx {
        ......
    ......
            leaf IP_TYPE {
                type sonic-head:ip_type;
            }
    }
}
```

### 4.  if an object is used as a key in Redis, it should be a key in YANG model. Exception must be recorded in YANG Model.

Example: VLAN_MEMBER dictionary in ABNF.json has both vlan-id and Port part of the key. So YANG model should have the same keys.

#### ABNF
```
 "VLAN_MEMBER": {
        "Vlan100|Ethernet0": {<<<< KEYS
            "tagging_mode": "untagged"
        }
   }
```
#### YANG
```
container VLAN_MEMBER {
    description "VLAN_MEMBER part of config_db.json";
        list xxx {
            key "vlanid port";<<<< KEYS
       }
}
```

### 5.  It is best to categorized YANG Modules based on a networking components. For Example, it is good to have separate modules for VLAN,  ACL, PORT and IP-ADDRESSES etc.
```
sonic-acl.yang
sonic-interface.yang
sonic-port.yang
sonic-vlan.yang
```



### 6.  All must, when, pattern and enumeration constraints can be derived from .h files (or code). If code has the possibility to have unknown behavior with some config, then we should put a constraint in YANG models objects. Also, developr can put any additional constraint to stop invalid configuration.
(This will always be Ongoing effort).

For Example: Enumeration of IP_TYPE comes for aclorch.h
```
#define IP_TYPE_ANY "ANY"
#define IP_TYPE_IP "IP"
#define IP_TYPE_NON_IP "NON_IP"
#define IP_TYPE_IPv4ANY "IPV4ANY"
#define IP_TYPE_NON_IPv4 "NON_IPv4"
#define IP_TYPE_IPv6ANY "IPV6ANY"
#define IP_TYPE_NON_IPv6 "NON_IPv6"
#define IP_TYPE_ARP "ARP"
#define IP_TYPE_ARP_REQUEST "ARP_REQUEST"
#define IP_TYPE_ARP_REPLY "ARP_REPLY"
```
Example of When Statement: Orchagent of SONiC will have unknown behavior if below config is entered, So YANG must have a constraint. Here SRC_IP is IPv4, where as IP_TYPE is IPv6.

#### ABNF:
```
   "ACL_RULE": {
        "NO-NSW-PACL-V4|Rule_20": {
            "PACKET_ACTION": "FORWARD",
            "DST_IP": "10.186.72.0/26",
            "SRC_IP": "10.176.0.0/15",
            "PRIORITY": "999980",
            "IP_TYPE": "IPv6"
        },

```
#### YANG:
```
choice ip_prefix {
                case ip4_prefix {
                    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV4' or .='IPV4ANY' or .='ARP'])";
                    leaf SRC_IP {
                        type inet:ipv4-prefix;
                    }
                    leaf DST_IP {
                        type inet:ipv4-prefix;
                    }
                }
                case ip6_prefix {
                    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV6' or .='IPV6ANY'])";
                    leaf SRC_IPV6 {
                        type inet:ipv6-prefix;
                    }
                    leaf DST_IPV6 {
                        type inet:ipv6-prefix;
                    }
                }
            }
```
Example of Pattern: If PORT Range should be "<0-65365> - <0-65365>"
```
leaf L4_DST_PORT_RANGE {
    type string {
    pattern '([0-9]{1,4}|[0-5][0-9]{4}|[6][0-4][0-9]{3}|[6][5][0-2][0-9]{2}|[6][5][3][0-5]{2}|[6][5][3][6][0-5])-([0-9]{1,4}|[0-5][0-9]{4}|[6][0-4][0-9]{3}|[6][5][0-2][0-9]{2}|[6][5][3][0-5]{2}|[6][5][3][6][0-5])';
        }
}
```
### 7. Comment all must, when and patterns conditions.
Example:
```
leaf family {
                /* family leaf needed for backward compatibility
                   Both ip4 and ip6 address are string in IETF RFC 6020,
                   so must statement can check based on : or ., family
                   should be IPv4 or IPv6 according.
                */
                must "(contains(../ip-prefix, ':') and current()='IPv6') or
                      (contains(../ip-prefix, '.') and current()='IPv4')";
                type sonic-head:ip-family;
            }
```



### 8.  Use IETF data types for leaf type first if applicable (RFC 6021) . Declare new type (say SONiC types) only if IETF type is not applicable. All SONiC Types must be part of same header type or common YANG model.
Example:
```
                    leaf SRC_IP {
                        type inet:ipv4-prefix; <<<<
                    }

                    leaf DST_IP {
                        type inet:ipv4-prefix;
                    }
```


## All above steps are manual right now, in future few of them can be automated. Below tasks are automated already:
###  None
