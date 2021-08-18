<!-- omit in toc -->
# ACL User Defined Table Type Support #

<!-- omit in toc -->
## Table of Content

### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Stepan Blyshchak   | Initial version                   |

### Scope

The scope of this document covers ACL feature enhancements.

### Definitions/Abbreviations 

| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| ACL                      | Access Control List                        |
| API                      | Application Programmable Interface         |
| Everflow                 | ERSPAN (Encapsulated Remote Switched Port Analysis) mirroring |
| FC                       | Flex Counter                               | 
| VID                      | SAIRedis Virtual object identifier |
| RID                      | SAI Real object identifier |
| SAI                      | Switch Abstraction Interface               |

### Overview 

The current design of ACL list a predefined set of table types - L3, L3V6, MIRROR, PFC_WD etc.
On every new feature added or on every new use case it is required to update ACL orchagent component with
new table type or modify existing table type. The predefined set of ACL match fields allocated for a particular
table type might also consume more HW resources then a use case requires.

This document addresses this limitation by introducing a new concept of user defined ACL table types in SONiC.

### Requirements

- Support user configurable ACL table types.
- Support programming custom ACL tables by using AclOrch public interface without defining a new ACL table type.

### Architecture Design

No SONiC architecture changes are required.

### High-Level Design

### SAI

N/A

### Orchagent

The AclOrch is subscribed to a table ```ACL_TABLE_TYPE``` in CFG DB. This table holds a definition for a table with the matches, actions and bind points.

*AclTableType* Data structure:

```c++
struct AclTableType
{
    std::string m_name;
    std::set<sai_acl_bind_point_type_t> m_bpoint_types;
    std::set<sai_attribute_id_t> m_matches;
    std::set<sai_acl_action_type_t> m_acl_actions;
}
```

*AclTable*:

```c++
class AclTable
{
public:
    // ...
    bool validateAddType(const AclTableType& type);
private:
    // ...
    AclTableType m_type;
}
```

Orchagent's ACL orch AclRule::make_shared makes decision which AclRule child instance to create based on table type.
Since orchagent does not know.

#### Mirror table type: combined/separated table

Orchagent has a special treatment for tables of type MIRROR and MIRRORV6
based on the ASIC platform it is running on. There is either a "combined" or
"seperated" mode for MIRROR tables.

```
+-------------------+------------------------------+
|                   |   CONFIG DB  |   ASIC DB     |
+-------------------+--------------+---------------+
|  combined         |   MIRROR     | Single mirror |
|                   +--------------+ table in HW   |
|                   |   MIRRORV6   | V4 + V6 keys  |
+-------------------+--------------+---------------+
|  seperated        |   MIRROR     | Mirror V4     |
|                   +--------------+---------------+
|                   |   MIRRORV6   | Mirror V6     |
+-------------------+--------------+---------------+
```

This does not play well with the new concept of user defined table types.
To solve this we have few options:

1. Non backward compatible change: let the CONFIG DB table maps 1:1 in ASIC DB table.
User is able to configure either two tables types, one for IPv4, one for IPv6 or single
with IPv4 and IPv6 keys.

2. Maintaing the current behaviour. Orchagent should have the knowledge to act in either
*combined* or *separeted* mode if the table type is named "MIRROR" or "MIRRORV6". 

3. Put this as a configuration in CONFIG DB. E.g, for certain two table types define "combined_v4_v6_mode". This configuration can come from init_cfg.json at start as well
as default table types.

In this design option 2 is chosen since it maintains current behaviour and does not expose different treatment of mirror tables
based on ASIC vendor to the user.

### Syncd

N/A

### CONFIG DB

```abnf
key: ACL_TABLE_TYPE:name           ; key of the ACL table type entry. The name is arbitary name user chooses.
; field         = value
matches         = match-list       ; list of matches for this table
actions         = action-list      ; list of actions for this table
bind_points     = bind-points-list ; list of bind point types for this table

; values annotation
match            = 1*64VCHAR
match-list       = [1-max-matches]*match        
action           = 1*64VCHAR
action-list      = [1-max-actions]*action        
bind-point       = port/lag
bind-points-list = [1-max-bind-points]*bind-point
```

Example:
```json
{
    "ACL_TABLE_TYPE": {
        "L3": {
            "MATCHES": [
                "IN_PORTS",
                "OUT_PORTS",
                "SRC_IP"
            ],
            "ACTIONS": [
                "PACKET_ACTION",
                "MIRROR_INGRESS_ACTION"
            ],
            "BIND_POINTS": [
                "PORT",
                "LAG"
            ]
        }
    },
    "ACL_TABLE": {
        "DATAACL": {
            "STAGE": "INGRESS",
            "TYPE": "L3",
            "PORTS": [
                "Ethernet0",
                "PortChannel1"
            ]
        }
    },
    "ACL_RULE": {
        "DATAACL|RULE0": {
            "PRIORITY": "999",
            "PACKET_ACTION": "DROP",
            "SRC_IP": "1.1.1.1/32",
        }
    }
}
```

Yang container for ACL_TABLE_TYPE table:

```yang
container ACL_TABLE_TYPE {
    list ACL_TABLE_TYPE_LIST {
        key "ACL_TABLE_TYPE_NAME";

        leaf-list MATCHES {
            type stypes:match;
        }

        leaf-list ACTIONS {
            type stypes:actions;
        }

        leaf-list BIND_POINTS {
            type stypes:acl_bind_points;
        }
    }
}
```


### Initial CONFIG DB

The following existing table types defined in init_cfg.json:

- L3
- L3V6
- MIRROR
- MIRRORV6
- MIRROR_DSCP
- DTEL_FLOW_WATCHLIST
- DTEL_DROP_WATCHLIST
- MCLAG

On platforms where certain features are not supported (like in band telemetry) the error is thrown on ACL table creation
of the unsupported type.

### Flows

### Open questions