# Custom ACL Based Metering

### Table Of Content
- [Custom ACL Based Metering](#custom-acl-based-metering)
    - [Table Of Content](#table-of-content)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
    - [Requirements](#requirements)
      - [Functional Requirements](#functional-requirements)
    - [Scalability Requirements:](#scalability-requirements)
      - [CLI Requirements](#cli-requirements)
    - [Architecture Design](#architecture-design)
    - [High-Level Design](#high-level-design)
      - [Modules and Sub-Modules](#modules-and-sub-modules)
        - [*Image 1: Configuration Flow Overview*](#image-1-configuration-flow-overview)
    - [Configuration and Management](#configuration-and-management)
      - [Config DB Enhancements](#config-db-enhancements)
        - [ACL table](#acl-table)
          - [Custom ACL Table Type --\> no change](#custom-acl-table-type----no-change)
        - [ACL rule](#acl-rule)
      - [YANG Model Enhancements](#yang-model-enhancements)
      - [CLI Config Commands](#cli-config-commands)
      - [CLI Show Commands](#cli-show-commands)
    - [SAI API](#sai-api)
    - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
    - [Restrictions/Limitations](#restrictionslimitations)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test Cases](#unit-test-cases)
      - [System Test Cases](#system-test-cases)
      - [CLI Level Tests](#cli-level-tests)
      - [DB validation](#db-validation)
    - [Open/Action Items](#openaction-items)
      - [Related HLDs](#related-hlds)
---

### Revision

| Version | Date       | Author                       | Description   |
| ------- | ---------- | ---------------------------- | ------------- |
| 1.0     | 2024-10-13 | Shay Goldshmit (**Marvell**) | Initial Draft |

---
### Scope

This document describes the Custom ACL Based Metering (CABM) feature design in SONiC.

---
### Definitions/Abbreviations

| Term | Definition                         |
| ---- | ---------------------------------- |
| ACL  | Access Control List                |
| NAT  | Network Address Translation        |
| SAI  | Switch Abstraction Interface       |
| CIR  | Committed Information Rate         |
| CBS  | Committed Burst Size               |

---
### Overview

Policers in networking are responsible for **metering** (Monitoring the rate of traffic) and **marking** (Flagging traffic that exceeds defined limits) traffic based on predefined criteria.
By applying policers to ACL rules, SONiC can effectively control the flow of network traffic, ensuring fairness, optimizing bandwidth utilization, and preventing network congestion.

Usage examples:
- **Security**: Custom ACL Based Metering can be used to guard against **network storms or DDoS attacks** by limiting traffic rates.
- **Fair Bandwidth Distribution**: Ensures bandwidth is allocated effectively across applications and services.

---
### Requirements
#### Functional Requirements
- Backward compatibility for existing ACL features - If policer is not set, the system will function as it did previously.
- Ability to config policers with ACL entries.
- Support existing Policer types (Policer mode, meter_type).
- Support custom ACL type mechanism with policers.
### Scalability Requirements:
- Support multiple rules within ACL to be bound to one policer.
- Query and validate SAI capabilities.
#### CLI Requirements
- Bind policers with ACL rules.
- Unbind policer from ACL rules.
- Show ACLs with policers
---
### Architecture Design

No SONiC architecture changes are required as the existing infrastructure is being used.

---
### High-Level Design

#### Modules and Sub-Modules

- **SWSS**
  - ACL-Orch
    - Set or disable policer action.
    - Query from SAI the ACL actions capability.
    - Allow policer action only when the capability is enabled.
    - Parse policer action fields.
  - Policer-Orch
    - Validate policer info.
    - Map policer name to policer object ID.
    - Prevent from deleting policer that bound to ACLs.

##### *Image 1: Configuration Flow Overview*

![alt text](Config_Flow.jpg)


---

### Configuration and Management
#### Config DB Enhancements

##### ACL table
- When a new ACL is created, SAI API should get a packet-action list of supported actions that could be used in the rules belonging to this table.
- An existing mechanism allows defining **custom ACL table types** and specifying the desired combination of actions and match fields (ACL User Defined Table Type HLD).
- To support the new policer action, the custom table type will be extended with the policer action attribute - SAI_ACL_ACTION_TYPE_SET_POLICER.

###### Custom ACL Table Type --> no change
```
key: ACL_TABLE_TYPE|<TYPE_NAME>               ; key of the ACL table type entry.
                                              ; the name is arbitary name user chooses.
; field       = value
matches       = match-list                    ; list of matches for this table.
                                              ; matches are same as in ACL_RULE table.
actions       = action-list                   ; list of actions for this table.
                                              ; actions are same as in ACL_RULE table.
bind_points   = bind-points-list              ; list of bind point types for this table.
```

##### ACL rule
- The CONFIG_DB ACL rules table schema will be updated with a new attribute **"policer_action"** with the value of one of the existing policer object names.
- This proposed schema is flexible and can support rules with more than a single action.
  - The existing design of SONiC ACL allows only one action to be defined per rule, this consept will be kept.

```
key: ACL_RULE|<TABLE_NAME>|<RULE_NAME>        ; key of the rule entry in the table,
                                              ; seq is the order of the rules
                                              ; when the packet is filtered by the
                                              ; ACL "policy_name".
                                              ; A rule is always associated with a policy.
;field        = value
priority      = 1*3DIGIT                      ; rule priority. Valid values range
                                              ; could be platform dependent

packet_action = "FORWARD"/"DROP"/"DO_NOT_NAT" ; action when the fields are matched

redirect_action = 1*255CHAR                   ; redirect parameter
                                              ; This parameter defines a destination for redirected packets
                                              ; it could be:
                                              : name of physical port.          Example: "Ethernet10"
                                              : name of LAG port                Example: "PortChannel5"
                                              : next-hop ip address (in global) Example: "10.0.0.1"
                                              : next-hop ip address and vrf     Example: "10.0.0.2@Vrf2"
                                              : next-hop ip address and ifname  Example: "10.0.0.3@Ethernet1"
...
+ policer_action = 1*255VCHAR                 ; refer to the policer object name
```

#### YANG Model Enhancements

sonic-yang-models/yang-templates/**sonic-acl**.yang.j2:
```c++
    ...
+   import sonic-policer {
+       prefix policer;
+   }
    ...
    container sonic-acl {
        container ACL_RULE {
            ...
+           leaf POLICER_ACTION {
+               type leafref {
+                   path "/policer:sonic-policer/policer:POLICER/policer:POLICER_LIST/policer:name";
+               }
+           }
        }

        container ACL_TABLE_TYPE {
            ...
            leaf-list ACTIONS {
                type string;
                default "";
            }
            ...
          }
      }
```

sonic-yang-models/yang-templates/**sonic-policer**.yang.j2:
```c++
    ...
+   import sonic-acl {
+       prefix acl;
+   }
    ...
    container sonic-policer {
        container POLICER {
        ...
+        /* prevent deletion of policer that referenced by ACL rule.
+           Note that new policer won't be referenced by any ACL rules initially */
+           must "not(../acl:sonic-acl/acl:ACL_RULE/acl:ACL_RULE_LIST[acl:policer_action=current()/name])" {
+               error-message "Policer cannot be deleted when referenced by an ACL rule.";
+           }
        }
    }
```

#### CLI Config Commands

- **Policers configuration** - No changes (no CLI commands).

- **ACL configuration:**
Two options to bind policer with ACL rules:

1. Use the "config load" command to load the complete JSON file to CONFIG_DB.
   This method enables flexibility to bind different policers to different rules in the same ACL:
```JSON
    /* Example for JSON file 'acl_with_policer_example.json': */
    {
        /* create 2 policers */
        "POLICER_TABLE|M_POLICER_7": {
            "meter_type": "packets",
            "mode": "tr_tcm",
            "color": "aware",
            "cir": "5000",
            "cbs": "5000",
            "green_packet_action": "forward",
            "red_packet_action": "drop"
        },
        "POLICER_TABLE|M_POLICER_93": {
            "meter_type": "packets",
            "mode": "tr_tcm",
            "color": "aware",
            "cir": "73000",
            "cbs": "82000",
            "red_packet_action": "drop"
        },

        /* create custom ACL table type */
        "ACL_TABLE_TYPE": {
          "CUSTOM_1_POLICER": {
            "MATCHES": [
                "IN_PORTS",
                "SRC_IP",
            ],
            "ACTIONS": [
                "POLICER_ACTION"
            ],
        }

        /* create ACL policer type table */
        "ACL_TABLE|MY_ACL_1": {
            "policy_desc": "Limit some traffic flows",
            "type": "CUSTOM_1_POLICER",
            "ports": [
                "Ethernet2",
                "Ethernet4",
                "Ethernet7"
            ],
            "OP": "SET"
        },

        /* create 2 rules with polcier action */
        "ACL_RULE|MY_ACL_1|MY_RULE_1": {
            "priority": "70",
          + "policer_action": "M_POLICER_7",
            "IP_PROTOCOL": "TCP",
            "SRC_IP": "10.2.130.0/24",
            "DST_IP": "10.5.170.0/24",
            "L4_SRC_PORT_RANGE": "1024-65535",
            "L4_DST_PORT_RANGE": "80-89",
            "OP": "SET"
        },
        "ACL_RULE|MY_ACL_1|MY_RULE_2": {
            "priority": "80",
          + "policer_action": "M_POLICER_93",
            "IP_PROTOCOL": "TCP",
            "SRC_IP": "192.168.1/24",
            "DST_IP": "10.5.170.0/24",
            "L4_SRC_PORT_RANGE": "1024-65535",
            "L4_DST_PORT_RANGE": "80-89",
            "OP": "SET"
        }
    }

    /* load the file to CONFIG_DB */
    config load acl_with_policer_example.json
```

2. Extending the existing "config acl" CLI to support a new optional argument **"policer_name"**.
   All rules that belong to that table (as part of the JSON file) will be bound with that policer object.
```bash
    # Config a new ACL table --> no change
    config acl add table [OPTIONS] <table_name> <table_type>

    # Config new ACL rules --> new optional field 'policer_name'
    config acl update full [OPTIONS] [--policer_name <policer_name>] <FILE_NAME>
    config acl update incremental [OPTIONS] [--policer_name <policer_name>] <FILE_NAME>

    # Example:
    config acl add table "MY_ACL_1" "Custom_1_POLICER"
    config acl update full "MY_ACL_2" --policer_name "M_POLICER_7" rules_example.json

    # note that these commands wrapps "AclLoader" utility script that uses the external "open_config" lib
```

#### CLI Show Commands
```bash
# Show existing policers --> no change
show policer [OPTIONS] [POLICER_NAME]

# Show existing ACL tables --> no change
show acl table [OPTIONS] [TABLE_NAME]

# Show existing ACL rules --> prints are contained the new proposal field
show acl rule [OPTIONS] [TABLE_NAME] [RULE_ID]

# note that these commands wrraps "AclLoader" utility script


# Example:
admin@sonic:~$ show acl table
Name           Type               Binding    Description                 Stage    Status
-----------    ---------------    ---------  -------------------------- -------  -----------------
MY_ACL_1       CUSTOM_1_POLICER   Ethernet2  Limit some traffic flows    Ingress  ACTIVE
                                  Ethernet4
                                  Ethernet7

MY_ACL_2       CUSTOM_3           Ethernet8  Limit AND redirect traffic  Ingress  ACTIVE


admin@sonic:~$ show acl rule
Table         Rule          Priority      Actions                    Match
--------      ------------  ----------    -------------------------  ----------------------------
MY_ACL_1      MY_RULE_1     70            POLICER: M_POLICER_7       IP_PROTOCOL: 17


MY_ACL_2      MY_RULE_2     80            POLICER: M_POLICER_93      L4_SRC_PORT: 80


MY_ACL_2      MY_RULE_3     90            REDIRECT: Ethernet8        L4_SRC_PORT: 25
```

---

### SAI API

Use these **existing** SAI attributes for ACL actions and ACE action:

| SAI Table Attribute                       | Description                                                                 |
| ---------------------------------------   | --------------------------------------------------------------------------- |
|   SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST | List of action types that can be applied in the ACL table                   |
|   SAI_ACL_ACTION_TYPE_PACKET_ACTION       | Action type (Forward, Drop, etc) that can be taken in that ACL entry        |
| + SAI_ACL_ACTION_TYPE_SET_POLICER         | Action type (policer) that can be taken in that ACL entry                   |


| SAI Rule Attribute                        | Description                                                                 |
| ---------------------------------------   | --------------------------------------------------------------------------- |
|   SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION | Action (Forward, Drop, etc) to be executed on packets matching the ACL rule |
| + SAI_ACL_ENTRY_ATTR_ACTION_SET_POLICER   | Action (policer) to be executed on packets matching the ACL rule            |

---

### Warmboot and Fastboot Design Impact
During warmboot or fastboot, both ACL rules and policers configurations are restored from the CONFIG_DB.

---
### Restrictions/Limitations

- Policers must be supported.
- PRE/POST INGRESS stage isn't supported (not supported by the existing ACL creation logic).
- Single Action per Rule - each ACL rule performs one action due to the existing ACL-Orch implementation.

---
### Testing Requirements/Design
#### Unit Test Cases
- Test ACL-Orch and Policer-Orch logic for correct processing.
#### System Test Cases
- Ensure correct packet marking based on policer configurations.
- Test different traffic patterns and rates to ensure consistent marking.
- Warm/Fast reboot tests
  - verify that policer configurations are preserved across reboots
  - verify that ACL configurations are preserved across reboots
#### CLI Level Tests
- Verify command run successfully with valid parameter enable/disable.
- Verify command abort with invalid policer parameter.
- Verify command output.
- Verify binding and unbinding policers with ACL rules.
#### DB validation
- Verify CONFIG DB is correctly updated.
---
### Open/Action Items

---
#### Related HLDs
- [Everflow](https://github.com/sonic-net/SONiC/blob/master/doc/everflow/SONiC%20Everflow%20Always-on%20HLD.pdf) - Creating and managing policers.
- [ACL User Defined Table Type Support](https://github.com/sonic-net/SONiC/blob/master/doc/acl/ACL-Table-Type-HLD.md) - Introducing a new concept of user defined ACL table types in SONiC.
- [Policer Counter](https://github.com/sonic-net/SONiC/blob/e3f439dcfe2857540a02e4449fce247d4167b621/doc/policer_counter/PolicerCounter-HLD.md#Architecture-Design) - Display and check matching policer statistics.