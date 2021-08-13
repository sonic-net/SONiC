# P4RT APPL DB Schema

_Rev v0.1_


## Revision

Rev  | RevDate    | Author(s)   | Change Description
---- | ---------- | ----------- | ------------------
v0.1 | 07/19/2021 | Google, ONF | Initial Version


#
Scope

This document captures the schema changes done for supporting the P4RT app in Sonic. 


# 
Overview

As part of the PINS effort, a new P4RT table is introduced into the APPL_DB. The P4RT application and P4Orch will communicate through this newly introduced table. The new table organises entries into sub-tables based on the functionality the table caters to, based on the P4 program.

As part of the PINS effort there are also extensions made to the existing SWITCH_TABLE and a new HASH_TABLE added for the hashing parameters.


# 
P4RT Tables

P4RT application introduces new tables with the prefix P4RT in the APPL_DB that holds the definitions and entries for the various types of entities that it programs in the DB. It follows the convention of **P4RT:&lt;TableType>&lt;TableName>** where TableType is of **FIXED** or configurable (only **ACL** for now) and TableName is the specific table in the SAI pipeline specification like router interface, neighbor, nexthop, IPV4/IPV6 tables etc. 

The key and value entries in the table are generally formatted according to the P4 program of the corresponding table. The table entries are uniformly represented in both the fixed SAI and configurable SAI aspects (ACL tables) or P4 extensions. The table format is compatible with other tables in SONiC and follows a human readable format to aid debugging. 


# 
Common definitions

Every table entry is stored using a key made up of the table name, all match keys and the priority (if there is one). Then the value in the Redis DB is a hash map, mapping `action` to the name of the action and mapping all parameter names to the parameter values. Every key and the value in the Redis DB is represented as a JSON object that makes it consistent with the ASIC_DB representation and permitting the use of any char with variable length. 

**Match Fields**

Match fields may be formatted as one of three types:



* **Exact** (`"<value>"`)
    * Available to all tables.
    * Example: `"match/ether_type": "0x8000"`
* **Ternary** (`"<value> & <mask>"`)
    * Available for ACL tables.
    * Example: `"match/ether_type": "0x8000 & 0xFFFF"`
* **LPM** (`"<value>/<prefix_length>"`)
    * Used for IP fields in FIXED_* tables (`ipv4_route` and `ipv6_route` specifically).
    * Example: `"match/ip_6_dst": "2001:db8:85a3::/64"`

Note that exact, ternary and LPM here refer not to the match kind of the match field in P4, but instead on the value/mask used:



* Exact is matching on a value exactly (i.e., no mask). This is available for P4 match kinds `exact`, `optional`, and `ternary`. For `ternary`, it implies a mask of all-ones.
* Ternary is matching on a masked value. This is only available for P4 match kinds of `ternary`.
* LPM is matching on a value with a given prefix length. This is only available for P4 match kinds `lpm`.

**Value Formatting**

Values are formatted according to their type (e.g. IPv4 addresses as `10.0.0.1`). The list of formats and their description are detailed below. 


```
// Describes the format of a value which has a bit width `num_bits` (unless for

// the STRING format, which has no limit in the number of characters).
enum Format {
 // Hex string, e.g. 0x0a8b. All lowercase, and always of length
 // ceil(num_bits/4)+2 (1 character for every 4 bits, zero-padded to be
 // divisible by 4, and 2 characters for the '0x' prefix).
 HEX_STRING = 0;
 // MAC address, e.g. 00:11:ab:cd:ef:22. All lowercase, and always 17
 // characters long.
 MAC = 1;
 // IPv4 address, e.g. 10.0.0.2.
 IPV4 = 2;
 // IPv6 address, e.g. fe80::21a:11ff:fe17:5f80. All lowercase, formatted
 // according to RFC5952. This can be used for any num_bits of 128 or less. If
 // num_bits is less than 128, then by convention only the upper num_bits bits
 // can be set.
 IPV6 = 3;
 // String format, only printable characters.
 STRING = 4;
}
```


**Port names:**

Port names refer to the ports used in SONiC and use `Format::STRING`, example “Ethernet0”.


# 
Schema definition


## APP_DB


## P4RT Table

All data in the Application Database (APPL DB) published by the P4RT application resides in  the P4RT table. Logically, the P4RT table is divided into **subtables**:



* **DEFINITION** tables describe configuration of the logical tables.
* **ACL_*** tables contain the runtime entries for ACL tables.
* **FIXED_*** tables contain the runtime entries fixed SAI pipeline tables.


### 1. DEFINITION Tables

Definition tables describe the configuration of logical tables. Each key represents a separate logical table. Definition tables provide more details about the table, like which stage of the pipeline they fit into, one or more match/action parameters and values. This helps the P4Orch layer to interpret the actual table entries (when they arrive later as part of the P4 Write request processing) and program them accordingly into the ASIC_DB. Currently, fixed tables do not need a definition and only ACL tables have corresponding DEFINITION tables.

**DEFINITION Table Keys**

The keys of a DEFINITION table represent the dynamic table name or the pipeline stage of the table that it defines. 

; defines the P4RT DEFINITION table used for defining a dynamic table.

| key                     = | P4RT:DEFINITION:table_name | ; Dynamic table name |
|---------------------------|----------------------------|----------------------|
  


```
127.0.0.1:6379> keys P4RT*
1) "P4RT:DEFINITION:ACL_ACL_PRE_INGRESS_TABLE"
2) "P4RT:DEFINITION:ACL_ACL_INGRESS_TABLE"
```


**DEFINITION Table Values**

The values of a DEFINITION table represent table configuration parameters. The table below describes the key,value pairs for this table.

|                              |                                |                                                                                                                                                                                                                                                                   |
|------------------------------|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| stage                    =   | PRE_INGRESS / INGRESS / EGRESS | ; Pipeline stage for this ACL table.                                                                                                                                                                                                                              |
| match/     =                 |                                |  is the alias from the P4Info and can be seen in the P4 program as the @name annotation. Multiple match entries may be declared.                                                                                                                                  |
| JSON                    =    | {{kind}{format}{bitwidth}}     | ; JSON object with at least the specified members.                                                                                                                                                                                                                |
| kind                       = | sai_field / udf / composite    | ; See below for more details                                                                                                                                                                                                                                      |
| format                   =   | STRING / HEX_STRING            | ; See the formatting section for more details.                                                                                                                                                                                                                    |
| bitwidth                 =   |                                | ; number of bits for this match field in decimal.                                                                                                                                                                                                                 |
| kind:sai_field:<json>              |                                | ; additional json members for sai_field kind.                                                                                                                                                                                                                     |
|        <json>          =           | sai_field:                     | ; mapped to the  [SAI ACL Match](https://github.com/opencomputeproject/SAI/blob/master/inc/saiacl.h) field name.                                                                                                                                                                                                                        |
| kind:udf:<json>                    |                                | ; additional json members for udf kind                                                                                                                                                                                                                            |
|            <json>     =            | base / bitwidth / group        | ; base:  The base of the UDF, one of values from the sai_udf_base_t enum. ; bitwidth: Length in bytes. Note that all UDFs in a group must use the same length. This is enforced by the orch agent on table creation. ; group: The group that this ACL belongs to. |
| kind:composite               |                                | ; a composite field                                                                                                                                                                                                                                               |
| elements:<json>                    |                                | ; mapping to a list of JSON objects, each describing a sai_field or udf match field element. Elements cannot have kind: composite (i.e. composite fields are not nested), and they do not require the format member since it would be unused.                     |
| action/<name>                      |  <name>is from the P4 program        | ; Declares an action for use by entries in the ACL table, each action entry maps to a SAI action. Multiple actions can be declared.                                                                                                                               |
| meter_unit          =        |   <string>                             | ; Configures the meter units for each metered entry in the table                                                                                                                                                                                                  |
|     <string>           =             | BYTES / PACKETS                | ; Count bytes or packets                                                                                                                                                                                                                                          |
| counter_unit      =          |    <string>                            | ; Configures a counter for each entry in the table.                                                                                                                                                                                                               |
|     <string>           =             | BYTES / PACKETS / BOTH         | ; Count bytes or packets or both.                                                                                                                                                                                                                                 |
| size                     =   |   <integer>                             | ; Maximum number of entries for this table.                                                                                                                                                                                                                       |
| priority               =     |    <integer>                            | ; Table priority relative to other ACL tables in the same stage.                                                                                                                                                                                                    |


```
127.0.0.1:6379> hgetall "P4RT:DEFINITION:ACL_ACL_PRE_INGRESS_TABLE"
 1) "stage"
 2) "PRE_INGRESS"
 3) "match/dst_ipv6"
 4) "{\"bitwidth\":128,\"format\":\"IPV6\",\"kind\":\"sai_field\",\"sai_field\":\"SAI_ACL_TABLE_ATTR_FIELD_DST_IPV6\"}"
 5) "match/in_port"
 6) "{\"format\":\"STRING\",\"kind\":\"sai_field\",\"sai_field\":\"SAI_ACL_TABLE_ATTR_FIELD_IN_PORT\"}"
 7) "match/is_ipv4"
 8) "{\"bitwidth\":1,\"format\":\"HEX_STRING\",\"kind\":\"sai_field\",\"sai_field\":\"SAI_ACL_TABLE_ATTR_FIELD_ACL_IP_TYPE/IPV4ANY\"}"
..

127.0.0.1:6379> hgetall "P4RT:DEFINITION:ACL_ACL_INGRESS_TABLE"
 1) "match/arp_tpa"
 2) "{\"bitwidth\":32,\"elements\":[{\"base\":\"SAI_UDF_BASE_L3\",\"bitwidth\":16,\"kind\":\"udf\",\"offset\":24},{\"base\":\"SAI_UDF_BASE_L3\",\"bitwidth\":16,\"kind\":\"udf\",\"offset\":26}],\"format\":\"HEX_STRING\",\"kind\":\"composite\"}"
 3) "action/mirror"
 4) "[{\"action\":\"SAI_PACKET_ACTION_FORWARD\"},{\"action\":\"SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS\",\"param\":\"mirror_session_id\"}]"
 5) "match/is_ipv4"
 6) "{\"bitwidth\":1,\"format\":\"HEX_STRING\",\"kind\":\"sai_field\",\"sai_field\":\"SAI_ACL_TABLE_ATTR_FIELD_ACL_IP_TYPE/IPV4ANY\"}"
 7) "action/trap"
 8) "[{\"action\":\"SAI_PACKET_ACTION_TRAP\"},{\"action\":\"QOS_QUEUE\",\"param\":\"qos_queue\"}]"

```



### 2. ACL_* Tables

Each entry in the ACL_* tables represent a single match/action rule in an ACL table. Entry** **keys uniquely identify and describe the rule. The table values 

**ACL_* Table Keys**

Table keys follow the format:

; defines the P4RT:ACL_* table entries that correspond to a matching DEFINITION table.


|                           |                                                                                               |                                                                                                        |
|---------------------------|-----------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| key                     = | P4RT:ACL_<table_name>:<Entry_ID_JSON>                                                         | ; Dynamic table name as used in the DEFINITION entry.                                                  |
| <Entry_ID_JSON> =         | match/<name>: "<value>( & <mask>)"   ... match/<name>: "<value>( & <mask>)" priority: <value> | ; One or more match fields and a priority value. The JSON components are described in the table below. |

| KEY          | Format           | Description                                                                                                                                                                                                                                                                                                                                                                                      |
|--------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| match/<name> | String / Integer | Describes a match parameter for the rule. The match/<name> comes from the DESCRIPTION table. Matches may be exact or ternary values. See the Match Fields formatting section for details. Certain types may only appear as exact matches: SAI_ACL_TABLE_ATTR_FIELD_ACL_IP_TYPE/* SAI_ACL_TABLE_ATTR_FIELD_IN_PORT SAI_ACL_TABLE_ATTR_FIELD_OUT_PORT The value format depends on the match type.  |
|     priority | Integer          | The priority of the ACL rule relative to other rules in the ACL table.                                                                                                                                                                                                                                                                                                                           |


```
127.0.0.1:6379> keys P4RT:ACL_ACL_INGRESS*
 1) "P4RT:ACL_ACL_INGRESS_TABLE:{\"match/dst_mac\":\"33:33:00:00:00:02&ff:ff:ff:ff:ff:ff\",\"match/icmpv6_type\":\"0x87&0xff\",\"match/ip_protocol\":\"0x3a&0xff\",\"match/is_ipv6\":\"0x1\",\"priority\":2070}"

127.0.0.1:6379> keys P4RT:ACL_ACL_PRE_INGRESS*
 1) "P4RT:ACL_ACL_PRE_INGRESS_TABLE:{\"match/dst_ip\":\"10.53.192.0&255.255.240.0\",\"match/is_ipv4\":\"0x1\",\"priority\":1132}"

```


**ACL_* Table Values**

The values of the ACL_* Table list the action meter settings for the rule. as described in the table below.

|                         |                  |                                                                                                                                                                                                                                                                                                                    |
|-------------------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| action                  | String           | ;The name of the action to apply to matching packets.The value must be an action name from the DESCRIPTION table.                                                                                                                                                                                                  |
| param/<name>            |                  | ; The value of an action parameter. The param/<name> comes from the DESCRIPTION table JSON for the action.                                                                                                                                                                                                         |
| <name>              =   | String / Integer | ;  The value format comes from the action type.                                                                                                                                                                                                                                                                    |
| meter/cir            =  | <integer>        | ; Committed Information Rate. Packets meeting this rate limit are treated as GREEN. All other packets are marked RED or YELLOW (see meter/pir).                                                                                                                                                                    |
| meter/cburst       =    | <integer>        | ; Committed Burst Rate. [Required if meter/cir is present.] Packets meeting this rate limit are treated as GREEN.                                                                                                                                                                                                  |
| meter/pir             = | <integer>        | ; Peak Information Rate. Packets meeting this rate limit and not meter/cir, meter/cburst are treated as YELLOW. Packets not meeting this rate limit are treated as RED. For RED/GREEN-only processing, meter/pir & meter/pburst can be omitted or set to the same values as meter/cir & meter/cburst respectively. |
| meter/pburst       =    | <integer>        | ; Peak Burst Rate. [Required if meter/pir is present.] See meter/pir for more information.                                                                                                                                                                                                                         |

```
127.0.0.1:6379> hgetall "P4RT:ACL_ACL_INGRESS_TABLE:{\"match/dst_mac\":\"33:33:00:00:00:02&ff:ff:ff:ff:ff:ff\",\"match/icmpv6_type\":\"0x87&0xff\",\"match/ip_protocol\":\"0x3a&0xff\",\"match/is_ipv6\":\"0x1\",\"priority\":2070}"
 1) "action"
 2) "trap"
 3) "param/qos_queue"
 4) "0x6"
 5) "meter/cir"
 6) "28000"
 7) "meter/cburst"
 8) "7000"
 9) "meter/pir"
10) "28000"
11) "meter/pburst"
12) "7000"
13) "controller_metadata"
14) "my metadata"
 
127.0.0.1:6379> hgetall "P4RT:ACL_ACL_PRE_INGRESS_TABLE:{\"match/dst_ip\":\"10.53.192.0&255.255.240.0\",\"match/is_ipv4\":\"0x1\",\"priority\":1132}"
1) "param/vrf_id"
2) "p4rt-vrf-80"
3) "action"
4) "set_vrf"
5) "controller_metadata"
6) "my metadata"


```



### 3. FIXED_* Tables

FIXED_* Tables are similar to ACL_* Tables. However, FIXED_* Tables have a predefined set of matches & actions. This prevents the need for a DEFINITION table for these tables.

**FIXED_* Table Keys**

FIXED_* Table keys follow the same format as ACL_* Table keys with the exception of using P4RT:FIXED_ instead of P4RT:ACL_.


```
127.0.0.1:6379> keys P4RT:FIXED_ROUTER_*
 1) "P4RT:FIXED_ROUTER_INTERFACE_TABLE:{\"match/router_interface_id\":\"router-interface-49\"}"

127.0.0.1:6379> keys P4RT:FIXED_NEIGHBOR*
 1) "P4RT:FIXED_NEIGHBOR_TABLE:{\"match/neighbor_id\":\"fe80::21a:11ff:fe17:5f80\",\"match/router_interface_id\":\"router-interface-8\"}"

127.0.0.1:6379> keys P4RT:FIXED_NEXTHOP*
 1) "P4RT:FIXED_NEXTHOP_TABLE:{\"match/nexthop_id\":\"nexthop-6\"}"

127.0.0.1:6379> keys P4RT:FIXED_IPV4*
1) "P4RT:FIXED_IPV4_TABLE:{\"match/ipv4_dst\":\"10.206.105.32/27\",\"match/vrf_id\":\"p4rt-vrf-114\"}"

127.0.0.1:6379> keys P4RT:FIXED_WCMP*
1) "P4RT:FIXED_WCMP_GROUP_TABLE:{\"match/wcmp_group_id\":\"group-4294934539\"}"

127.0.0.1:6379> keys P4RT:FIXED_MIRROR*
1) "P4RT:FIXED_MIRROR_SESSION_TABLE:{\"match/mirror_session_id\":\"mirror-session-201326594\"}"
```


See ACL_* Table Keys section(above) for more information.

**FIXED_* Table Values**

Fixed table values follow the same format as ACL_* tables (see Section ACL_* Table Values above). However, the parameters are predefined per table. The match and action values for each fixed table can directly be deduced from the corresponding P4 programs.


```
127.0.0.1:6379> hgetall "P4RT:FIXED_ROUTER_INTERFACE_TABLE:{\"match/router_interface_id\":\"router-interface-49\"}"
1) "action"
2) "set_port_and_src_mac"
3) "param/port"
4) "Ethernet144"
5) "param/src_mac"
6) "02:2a:10:00:00:06"
7) "controller_metadata"
8) "my metadata"


127.0.0.1:6379> hgetall  "P4RT:FIXED_NEIGHBOR_TABLE:{\"match/neighbor_id\":\"fe80::21a:11ff:fe17:5f80\",\"match/router_interface_id\":\"router-interface-8\"}"
1) "action"
2) "set_dst_mac"
3) "param/dst_mac"
4) "00:1a:11:17:5f:80"
5) "controller_metadata"
6) "my metadata"


127.0.0.1:6379> hgetall "P4RT:FIXED_NEXTHOP_TABLE:{\"match/nexthop_id\":\"nexthop-6\"}"
1) "action"
2) "set_nexthop"
3) "param/router_interface_id"
4) "router-interface-6"
5) "param/neighbor_id"
6) "fe80::21a:11ff:fe17:5f80"
7) "controller_metadata"
8) "my metadata"

127.0.0.1:6379> hgetall "P4RT:FIXED_IPV4_TABLE:{\"match/ipv4_dst\":\"10.206.105.32/27\",\"match/vrf_id\":\"p4rt-vrf-114\"}"
1) "action"
2) "set_wcmp_group_id"
3) "param/wcmp_group_id"
4) "group-4294934547"
5) "controller_metadata"
6) "my metadata"

127.0.0.1:6379> hgetall "P4RT:FIXED_WCMP_GROUP_TABLE:{\"match/wcmp_group_id\":\"group-4294934539\"}"
1) "actions"
2) "[{\"action\":\"set_nexthop_id\",\"param/nexthop_id\":\"nexthop-21\",\"watch_port\":\"Ethernet120\",\"weight\":1},{\"action\":\"set_nexthop_id\",\"param/nexthop_id\":\"nexthop-39\",\"watch_port\":\"Ethernet252\",\"weight\":1}]"
3) "controller_metadata"
4) "my metadata"

127.0.0.1:6379> hgetall "P4RT:FIXED_MIRROR_SESSION_TABLE:{\"match/mirror_session_id\":\"mirror-session-201326594\"}"
 1) "action"
 2) "mirror_as_ipv4_erspan"
 3) "param/port"
 4) "Ethernet0"
 5) "param/src_ip"
 6) "10.206.196.0"
 7) "param/dst_ip"
 8) "172.20.0.203"
 9) "param/src_mac"
10) "00:02:03:04:05:06"
11) "param/dst_mac"
12) "00:1a:11:17:5f:80"
13) "param/ttl"
14) "0x40"
15) "param/tos"
16) "0x00"
17) "controller_metadata"
18) "
```



## Switch/Hash table

The entry represents the hashing related parameters written to the existing SWITCH_TABLE and a new HASH_TABLE. 

**HASH_TABLE_Key**

; defines the HASH_TABLE used for defining the hashing fields.
|                            |                              |                                                                          |
|----------------------------|------------------------------|--------------------------------------------------------------------------|
| key                      = | HASH_TABLE:<hash_key_string> | ; Key used to define the hash fields and to be used in the SWITCH_TABLE. |
 


**HASH_TABLE_Values**

|                                   |                                                                                  |                                                                                           |
|-----------------------------------|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| hash_field_list     =             | List of one or more <src_ip, dst_ip, l4_src_port, l4_dst_port, ipv6_flow_label,  | ; Specifies the list of fields to be included in the hashing computation for this object. |
                                                                   

```
127.0.0.1:6379> keys HASH_TABLE*
1) "HASH_TABLE:compute_ecmp_hash_ipv4"
2) "HASH_TABLE:compute_ecmp_hash_ipv6"
127.0.0.1:6379> hgetall HASH_TABLE:compute_ecmp_hash_ipv4
1) "hash_field_list"
2) "[\"src_ip\",\"dst_ip\",\"l4_src_port\",\"l4_dst_port\"]"
127.0.0.1:6379> hgetall HASH_TABLE:compute_ecmp_hash_ipv6
1) "hash_field_list"
2) "[\"src_ip\",\"dst_ip\",\"l4_src_port\",\"l4_dst_port\",\"ipv6_flow_label\"]"
127.0.0.1:6379> 
```


**SWITCH_TABLE_Key**

; defines the hashing related parameters in the SWITCH table.

|                                     |                     |                                                               |
|-------------------------------------|---------------------|---------------------------------------------------------------|
| key                   =             | SWITCH_TABLE:switch | ; Modifies existing Switch table key to include hash objects. |
  

**SWITCH_TABLE_Values**

The new fields added to the switch table represent the ecmp_hash_&lt;protocol> which represents the protocol for which this key is used and the value references the corresponding entry with the same key in HASH_TABLE. 


|                                           |                 |                                                                                                          |
|-------------------------------------------|-----------------|----------------------------------------------------------------------------------------------------------|
| ecmp_hash_ipv4=                          | hash_key_string | ; Defines the hash object to be used for IPv4 packets which was created with the same key in HASH_TABLE. |
| ecmp_hash_ipv6=                          | hash_key_string | ; Defines the hash object to be used for IPv6 packets which was created with the same key in HASH_TABLE. |



```
127.0.0.1:6379> keys SWITCH_TABLE:switch
1) "SWITCH_TABLE:switch"
127.0.0.1:6379> hgetall SWITCH_TABLE:switch
 1) "ecmp_hash_seed"
 2) "0"
 3) "fdb_aging_time"
 4) "600"
 5) "lag_hash_seed"
 6) "10"
 7) "ecmp_hash_algorithm"
 8) "crc_32lo"
 9) "ecmp_hash_offset"
10) "0"
11) "ecmp_hash_ipv6"
12) "compute_ecmp_hash_ipv6"
13) "ecmp_hash_ipv4"
14) "compute_ecmp_hash_ipv4"

```



## CountersDB

**COUNTERS:P4RT:ACL_* Tables**

The entry represents the packets and/or bytes counts for the ACL entry. 

**COUNTERS:P4RT:ACL_* Table Keys**

Table keys follow the format:

; defines the counters table for the P4RT ACL entries.

|                            |                                                |                                                                                                                                     |
|----------------------------|------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| key                      = | COUNTERS:P4RT:ACL_<Table_Name>:<Entry_ID_JSON> | ; The P4RT:ACL_<Table_Name>:<Entry_ID_JSON> is the key of the ACL entries in APPL_DB defined in the ACL_* Table keys section above. |
  


**COUNTERS:P4RT:ACL_* Table Values**

The values of the COUNTERS:P4RT:ACL_* Table list the ACL entry counter statistics as described in the table below.

|                                 |           |                                                                                                                                                                                          |
|---------------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| packets                =        | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit only and in PACKETS/BOTH and the meter does not specify packet color, this value should be populated in counter statistics. |
| bytes                   =       | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit only and in BYTES/BOTH and the meter does not  specify packet color, this value should be populated in counter statistics.  |
| yellow_packets   =              | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit in  PACKETS/BOTH and the packet color is YELLOW in meter, this value should be populated in counter statistics.             |
| yellow_bytes      =             | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit in  PACKETS/BOTH and the packet color is YELLOW in meter, this value should be populated in counter statistics.             |
| red_packets       =             | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit in PACKETS/BOTH and the packet color is RED in meter, this value should be populated in counter statistics.                 |
| red_bytes         =             | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit in BYTES/BOTH and the packet color is RED in meter, this value should be populated in counter statistics.                   |
| green_packets   =               | <integer> | ;If the ACL rule is in a DEFINITION table with counter_unit in PACKETS/BOTH and the packet color is GREEN in meter, this value should be populated in counter statistics.                |
| green_bytes       =             | <integer> | ; If the ACL rule is in a DEFINITION table with counter_unit in BYTES/BOTH and the packet color is GREEN in meter, this value should be populated in counter statistics.                 |



