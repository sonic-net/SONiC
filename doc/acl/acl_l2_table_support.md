# L2 ACL table support 

# Table of Contents

#### Revision
| Rev |  Date   |       Author       | Change Description |
|:---:|:-------:|:------------------:|:------------------:|
| 0.1 | 2022-12 |   Arthi Govindaraj  | Initial Version    |

## Overview
In current design of orchagent, there is no support for L2 ACL table with match fields in Ethernet and Vlan header like source mac, destination mac, outer vlan priority/PCP and outer vlan CFI/DEI. So if a user wants to filter based on these fields then the support does not exist. 

## High Level Design

**Requirement :** New table of type L2 with L2 match fields and default actions needs to be defined. 
For this, we need to define CONFIG DB schema for the new L2 fields. In orchagent, we need to define SAI table attributes for the L2 table and add definitions for L2 fields in ACL entry qualifier validations. Also acl-loader needs to be updated to support the same in CLICK command.

**Proposed L2 table :**

Table of type "L2"
###### **Table 1: Matches allowed in the table of the type "L2"**

Keyword for the match criteria | Type | Description
-------------------------------|------|------------
ETHER_TYPE | uint16_t | Hexadecimal integer [0..FFFF]
IP_TYPE | string | One of: "IPv4"/"NON_IPv4"/"ARP"
SRC_MAC | string | MAC address format (MAC value/ MAC mask)
DST_MAC | string | MAC address format (MAC value/ MAC mask)
VLAN    | uint16_t | Decimal values from 1-4094
VLAN_PCP | uint8_t | Decimal value or value/mask [0..7 (or) 0..7/0..7]
VLAN_DEI | uint8_t | Decimal value of 0 or 1 [0..1]

###### **Table 2: Actions allowed in the table of the type "L2"**
Keyword for the action type    | Type | Description
-------------------------------|------|------------
PACKET_ACTION | string | Packet action value: "FORWARD" or "DROP"
REDIRECT_ACTION | string | Redirect ip next : Next hop ip address


### CONFIG_DB schema definitions :

**L2 table type defined in ACL_TABLE:**
```
In table, ACL_TABLE field:type new value "L2" is defined along with existing types "L3 or L3V6"
```
**New L2 fields are added to the ACL_RULE table:**
```
key: ACL_RULE:table_name:rule_name   ; key of the rule entry in the table,
;field         = value
/* New fields */
SRC_MAC        = mac address                     ; options of the source mac
                                                 ; address/mask field
DST_MAC        = mac address                     ; options of the destination mac
                                                 ; address/mask field
VLAN_PCP       = 1*3DIGIT (or) 1*3DIGIT/1*3DIGIT ; Outer VLAN pcp/priority field value (0-7) or value/mask (0-7/0-7)
VLAN_DEI       = 1*1DIGIT                        ; Outer VLAN DEI/CFI field value:0 or 1
/* Existing fields */
ETHER_TYPE     = h16                             ; Ethernet type field                                                 
VLAN_ID        = h16                             ; vlan id field ranging from 1-4094
IP_TYPE       = ip_types                         ; options of the l2_protocol_type
                                                 ; field. 
;value annotations
ip_types = any | ip | ipv4 | ipv4any | non_ipv4 | ipv6any | non_ipv6
```

**Example:**
```
{
    "ACL_TABLE": {
        "DATAACL": {
            "STAGE": "INGRESS",
            "TYPE" : "L2",
            "PORTS": [
                "Ethernet0",
                "PortChannel1"
            ]
        }
    },
    "ACL_RULE": {
        "DATAACL|RULE0": {
        "SRC_MAC": "00:00:00:11:11:11/00:00:00:ff:ff:ff",
	    "DST_MAC": "00:00:00:22:22:22/00:00:00:ff:ff:ff",
	    "ETHER_TYPE": "0x0800",
	    "VLAN_ID": "100",
	    "VLAN_PCP": "5/7",
	    "VLAN_DEI": "1",
	    "PRIORITY": "5",
	    "PACKET_ACTION": "DROP"
        }
    }
}
```
### orchagent changes

- Need to define new predefined ACLTableType "L2" with L2 fields and default actions packet_action and redirect.
- validateAddMatch() function needs to be updated to handle L2 fields
  SAI_ACL_ENTRY_ATTR_FIELD_SRC_MAC
  SAI_ACL_ENTRY_ATTR_FIELD_DST_MAC
  SAI_ACL_ENTRY_ATTR_FIELD_OUTER_VLAN_PRI
  SAI_ACL_ENTRY_ATTR_FIELD_OUTER_VLAN_CFI

### acl-loader

##### ACL loader table configuration:
```
config acl add table -s <stage> -p <ports> <table_name> <table_type>
```
table_type needs to be passed as "L2" to create new L2 table.
```
Example : config acl add table -s ingress -p Ethernet0 L2_TABLE L2
```
##### ACL loader rule configuration:
**Default rule:**
If user configures table type as L2, then the table is identified as L2 table and default rule is added with match field ip_type="any" and packet action as drop. This ensures that packet of any type matching the given incoming port will be dropped.

**config acl update full/incremental <json file>**
For adding rules to the L2 table, fields src mac, dst mac, ether type, vlan, ip type are pre-defined in openconfig acl.
Whereas fields vlan pcp and vlan dei are not defined in existing openconfig. 
So these 2 fields are not being supported in open config format in command "config acl update". To update these fields, we need to load the configs directly to config db.

Ether type, vlan and ip type will be used as in other existing L3/L3V6 tables.
For new fields:
"source-mac": "MAC ADDRESS",
"source-mac-mask": "MAC ADDRESS",
"destination-mac": "MAC ADDRESS",
"destination-mac-mask": "MAC ADDRESS"

The source mac and mask needs to be combined as source-mac/source-mac-mask for configuring SRC_MAC in CONFIG DB. 
Similarly destination mac and mask needs to combined as destination-mac/destination-mac-mask for configuring DST_MAC in CONFIG_DB.
This conversion and the fields updation in the CONFIG DB needs to be handled by acl-loader.

Other new fields like "vlan-pcp" and "vlan-dei" are not supported in update command. Since openconfig acl doesnt support these fields.

### VS test
VS test cases update to check for L2 table creation with match fields and actions.


