# ACL support in SONiC

## Requirements

The feature sets is classified into Must Have (M) and Should Have (S). The Must Have features are features we are enabled in our test and production networks. They must be supported by the next release. The Should Have features are the features are not partially configured in our test networks, and are going to be enabled in production. The features should be either already in the current image or is in their production plan.

- Support data plane ACL in SONiC (M)
- Support ACL table which contains a set of ACL rules (M)
- ACL table has predefined type, each type defines the a set of match fields and actions available for the table. For example, mirror acl table only supports mirror as an action. (M)
- Support binding ACL table to ports, initially only support for front panel physical port binding (M)
- Support binding multiple ACL tables to ports. The use case is to have data plane ACL table which do permit/deny while have mirror ACL table do packet mirror for a same packet. Initial, there will be no conflicting actions between two ACL tables bound to the same set of ports. (M)
- Support matching ip src/dst, ip protocol, tcp/udp port in ACL rules (M)
- Support port range matching in ACL rules (M)
- Support permit/deny action in ACL rules (M)
- Support packet erspan mirror action in ACL rules (M)   
- Packet counters for each acl rule (M)
- Byte counters for each acl rule (S)


## Scale/performance 

- Scale to 1K acl rules for l3 acl table
- Scale to 256 acl rules for mirror
 
## Design

### SWSS Schema

### ACL\_TABLE
  
Define ACL Table  
  
    key           = ACL_TABLE:name                        ; acl_table_name must be unique
    ;field        = value  
    policy_desc   = 1*255VCHAR                            ; name of the ACL policy table description  
    type          = "mirror"/"l3"                         ; type of acl table, every type of table defines the match/action a specific set of match and actions.
    ports         = [0-max_ports]*port_name               ; the ports to which this ACL table is applied, can be empty
    mirror_session_name = mirror_session_name             ; refer to the mirror session (only available to mirror

    ;value annotations  
    port_name     = 1*64VCHAR                             ; name of the port, must be unique  
    max_ports     = 1*5DIGIT                              ; number of ports supported on the chip  
   
---------------------------------------------  
### ACL\_RULE  

Define rules associated with a specific ACL Policy  
  
    key: ACL_RULE_TABLE:table_name:seq                    ; key of the rule entry in the table, seq is the order of the rules   
                                                          ; when the packet is filtered by the ACL "policy_name".   
                                                          ; A rule is always assocaited with a policy.

    ;field        = value   
    action        = "permit"/"deny"                       ; action when the fields are matched (mirror action only available to mirror acl table type)
     acl table type)
    l2_prot_type  = "ipv4"                                ; options of the l2_protocol_type field. Only v4 is support for this stage.  
    l3_prot_type  = "icmp"/"tcp"/"udp"/"any"              ; options of the l3_protocol_type field   
    ipv4_src      = ipv4_prefix/"any"                     ; options of the source ipv4 address (and mask) field  
    ipv4_dst      = ipv4_prefix/"any"                     ; options of the destination ipv4 address (and mask) field  
                                                          ; l2_prot_type detemines which set of the addresses taking effect, v4 or v6.  
    l4_src_port   = port_num/[port_num_L-port_num_H]      ; source L4 port or the range of L4 ports field   
    l4_dst_port   = port_num/[port_num_L-port_num_H]      ; destination L4 port or the range of L4 ports field  

    ;value annotations
    seq           = DIGITS                                ; unique sequence number of the rules assocaited within this ACL policy.  
                                                          ; When applying this ACL policy, the seq determines the order of the   
                                                          ; rules applied.   
    port_num      = 1*5DIGIT                              ; a number between 0 and 65535  
    port_num_L    = 1*5DIGIT                              ; a number between 0 and 65535, port_num_L < port_num_H  
    port_num_H    = 1*5DIGIT                              ; a number between 0 and 65535, port_num_L < port_num_H  
    ipv6_prefix   =                                6( h16 ":" ) ls32  
                      /                       "::" 5( h16 ":" ) ls32  
                      / [               h16 ] "::" 4( h16 ":" ) ls32  
                      / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32  
                      / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32  
                      / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32  
                      / [ *4( h16 ":" ) h16 ] "::"              ls32  
                      / [ *5( h16 ":" ) h16 ] "::"              h16  
                      / [ *6( h16 ":" ) h16 ] "::"  
    h16           = 1*4HEXDIG  
    ls32          = ( h16 ":" h16 ) / IPv4address  
    ipv4_prefix   = dec-octet "." dec-octet "." dec-octet "." dec-octet “/” %d1-32    
    dec-octet     = DIGIT                     ; 0-9  
                      / %x31-39 DIGIT         ; 10-99  
                      / "1" 2DIGIT            ; 100-199  
                      / "2" %x30-34 DIGIT     ; 200-249  

### Supported operations

- Create an ACL table with type
- Create ACL rules and attach them to the ACL table
- Attach ACL table to ports
- Detach ACL table from ports
- Remove ACL rules

### Interaction with other modules

- Since ACL table are bound to certain ports, there could be some potential interaction with port changes.
- Port oper status up/down will not ACL table binding. Even when a port is down, ACL table is still bound to the port.
- Upon Port deletion, ACL table are then unbound to the removed port. (not needed in the initial release)
- ACL table could potential bound to a LAG port. (not needed in the initial release)

### Configuration

- User generate json based configuration file based on the schema defined above, and then use the swssconfig to configure the ACl table and rules.
- swssconfig should have two configuration mode, *full* and *partial*. In full configuration mode, all existing acl rules and table are removed and replaced by the new configuration. In partial configuration mode, new configuration are delta to current configuration. 


 