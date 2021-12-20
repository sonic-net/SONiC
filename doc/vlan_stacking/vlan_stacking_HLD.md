 ### Rev 0.1

# Table of Contents

- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
  - [VLAN Stacking Deployment Use Cases](#vlan-stacking-deployment-use-cases)
    - [QinQ Use Case](#qinq-use-case)
    - [VLAN Translation Use Case](#vlan-translation-use-case)
- [Architecture Design](#architecture-design)
- [Requirements](#requirements)
  - [Configuration](#configuration)
- [High-Level Design](#high-level-design)
  - [VlanMgr](#vlanmgr)
  - [DB](#db)
    - [CONFIG_DB](#config_db)
    - [APPL_DB](#appl_db)
  - [SAI API](#sai-api)
- [Configuration and management](#configuration-and-management)
  - [CLI/YANG model Enhancements](#cliyang-model-enhancements)
    - [CLI](#cli)
    - [Yang model](#yang-model)
  - [Examples](#examples)
    - [Examples of QinQ Configuration](#examples-of-qinq-configuration)
    - [Examples of VLAN Translation Configuration](#examples-of-vlan-translation-configuration)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions/Limitations](#restrictionslimitations)
- [Testing Requirements/Design](#testing-requirementsdesign)
  - [System Test Cases](#system-test-cases)

# List of Tables

* [Table 1: Revision](#revision)
* [Table 2: Definitions/Abbreviations](#definitionsabbreviations)
* [Table 3: SAI attributes related to VLAN stacking](#sai-api)

# Revision

###### Table 1: Revision

| Rev   |   Date     | Author        | Change Description |
|:-----:|:----------:|:-------------:|--------------------|
| 0.1   | 8-Oct-2020 | Tommy Tseng   | Initial version    |

# Scope

This document describes the high level design of VLAN stacking feature.

# Definitions/Abbreviations

###### Table 2: Definitions/Abbreviations

| Abbreviation | Full form              |
|--------------|------------------------|
| VID          | Virtual LAN Identifier |
| S-VLAN       | Service Provider VLAN  |
| C-VLAN       | Customer VLAN          |
| S-TAG        | S-VLAN tag             |
| C-TAG        | C-VLAN tag             |

# Overview

This document describes the design details of the VLAN stacking feature. VLAN stacking is a feature designed for service providers who carry traffic of multiple customers across  their networks and are required to maintain the VLAN and Layer 2 protocol configurations of each customer without impacting the traffic of other customers. VLAN stacking include QinQ feature and VLAN Translation feature.

IEEE 802.1Q tunneling (QinQ tunneling) uses a single Service Provider VLAN (SPVLAN) for customers who have multiple VLANs. Customer VLAN IDs are preserved and traffic from different customers is segregated within the service provider’s network even when they use the same customer-specific VLAN IDs. QinQ tunneling expands VLAN space by using a VLAN-in-VLAN hierarchy, preserving the customer’s original tagged packets, and adding SPVLAN tags to each frame (also called double tagging).

QinQ tunneling uses double tagging to preserve the customer’s VLAN tags on traffic crossing the service provider’s network. However, if any switch in the path crossing the service provider’s network does not support this feature, then the switches directly connected to that device can be configured to swap the customer’s VLAN ID with the service provider’s VLAN ID for upstream traffic, or the service provider’s VLAN ID with the customer’s VLAN ID for downstream traffic.

## VLAN Stacking Deployment Use Cases

### QinQ Use Case

The following example maps C-VLAN 10 to S-VLAN 100, C-VLAN 20 to S-VLAN 200 and C-VLAN 30 to S-VLAN 300 for ingress traffic on port 1 of Switches A and B.

Figure 1. Mapping QinQ Service VLAN to Customer VLAN

![QinQ use case](./images/QinQ_usecase.png)

### VLAN Translation Use Case

For example, assume that the upstream switch does not support QinQ tunneling. Select Port 1, and set the Old VLAN to 10 and the New VLAN to 100 to map VLAN 10 to VLAN 100 for upstream traffic entering port 1, and VLAN 100 to VLAN 10 for downstream traffic leaving port 1 as shown below.

Figure 2. Configuring VLAN Translation

![VLNA translate use case](./images/vlan_xlate_usecase.png)

# Architecture Design

The overall SONiC architecture will not be changed and no new sub-modules will be introduced.

# Requirements

* User **_shall_** be able to configure VLAN stacking on each Ethernet port and and channel port interface.
* A VLAN stacking configuration describes how to determine the service that the specific traffic belongs to and what rewrite action **_will_** be done for the frames. Each configuration include the following:
  * Service - A VLAN ID that the specified traffic **_will_** be applied to. Range 1 ~ 4094.
  * Direction - Traffic direction.
  * Action - The rewrite action for the frames, support the following actions:
    * push
      * Apply for all tagged frames, single or double tagged frames, at ingress direction.
      * Add an outer VLAN with TPID=8100, COS=0, VLAN=<specified-S-VLAN> (range 1 ~ 4094).
      * If the ingress frames (including untagged frames) not match the criteria, the frames **_will_** be forwarded using port VLAN (or call default VLAN, PVID).
    * pop
      * Apply for all tagged frames, single or double tagged frames, at egress direction.
      * Remove outer VLAN.
    * swap
      * Apply for all tagged frames, single or double tagged frames.
      * Replace the outer VLAN ID to <specified-S-VLAN> (range 1 ~ 4094). The TPID and COS are not changed.
      * If the ingress frames not match the criteria,
        * the untagged frames **_will_** be forwarded using port VLAN.
        * the tagged frames (including double tagged frames) **_will_** be forwarded using its outer VLAN.

    The summary of rewrite action support on service interface as shown in the following table:

    | Rewrite | Ingress Direction | Egress Direction |
    |---------|-------------------|------------------|
    | push    | Supported         | Not supported    |
    | pop     | Not supported     | Supported        |
    | swap    | Supported         | Supported        |

* Swap rewrite action **_will_** become invalid if configured (push, swap) at ingress direction or (pop, swap) at egress direction on the specified interface at the same time.
* Only outer TPID 8100 is supported. The frames with TPID = 8100 **_will_** be taken as tagged (single or double) frames.
* For egress direction on channel port, each match criteria **_will_** use one hardware entry per member port.

## Configuration

* It is able to configure VLAN stacking by modifying CONFIG_DB or reload configuration by "config load" CLI command.
* Invalid configuration with **_will_** be ignored and written an error in syslog. E.g., port is not exist.

# High-Level Design

## VlanMgr

VlanMgr is used for check user configuration by DB schema, the VlanStack **_will_** parsing user configuration to SAI attributes and call SAI API.

![VLAN Stacking create flow](./images/VlanStack%20config%20flow.png)

VlanStack defined in Orch agent is used for all VLAN stacking related operations and keep the user configurations.

* addEntry is used for add a C-VLAN ↔ S-VLAN mapping on the specified interface by user configuration. It function is used for updating the exist mapped, too. The update operation is implemented by remove old and then add new one, so it **_will_** effect the forwarding traffic when an entry be updating.
* removeEntry is used to remove a C-VLAN ↔ S-VLAN mapping on the specified interface.

```c++
struct VlanStack
{
    std::map<VlanStackKey, VlanStackEntry> vlan_stack_map;

    void addEntry(const VlanStackCfg& cfg);
    void deleteEntry(const VlanStackKey& entry_key);
};
```

## DB

### CONFIG_DB

A new table `VLAN_STACKING` is added in Config DB.

```
VLAN_STACKING|{{interface_name}}|{{stage}}|{{vlanid}}
"action":     {{action}}
"s_vlanid":   {{s_vlanid}}  (optional)
```

```
`interface_name`  Ethernet port and and channel port name
`stage`           Traffic direction
                  ingress - ingress direction
                  egress  - egress direction
`vlanid`          Service VLAN ID
                  C-VLAN for ingress direction
                  S-VLAN for egress direction
`action`          Rewrite action
                  push - Adds a s_vlanid tag to an ingress packet.
                  pop  - Pop (remove) the outermost tag.
                  swap - Swap outermost tag by s_vlanid.
`s_vlanid`        S-VLAN ID for push and swap action
```

DB schema of VLAN_STACKING table:

```
; Defines schema for VLAN_STACKING configuration attributes
key               = VLAN_STACKING:interface_name:stage:vlanid
interface_name    = 
stage             = ingress/egress
vlanid            = 1*4DIGIT   ; a number between 1 and 4094
; field           = value
action            = push/pop/swap
s_vlanid          = 1*4DIGIT   ; a number between 1 and 4094
```

### APPL_DB

A new table `VLAN_STACKING` is added in APP DB.

```
VLAN_STACKING_TABLE:{{interface-name}}:{{stage}}:{{vlanid}}
"action": {{action}}
"s_vlanid":   {{s_vlanid}}  (optional)
```

```
`interface_name`  Ethernet port and and channel port name
`stage`           Traffic direction
                  ingress - ingress direction
                  egress  - egress direction
`vlanid`          Service VLAN ID
                  C-VLAN for ingress direction
                  S-VLAN for egress direction
`action`          Rewrite action
                  push -  Adds a s_vlanid tag to an ingress packet.
                  pop  - Pop (remove) the outermost tag.
                  swap - Swap outermost tag by s_vlanid.
`s_vlanid`        S-VLAN ID for push and swap action
```

DB schema of VLAN_STACKING table:

```json
; Defines schema for VLAN_STACKING_TABLE configuration attributes
key                        = VLAN_STACKING_TABLE:interface_name:stage:vlanid
interface_name             = 
stage                      = ingress/egress
vlanid                     = 1*4DIGIT   ; a number between 1 and 4094
; field                    = value
action                     = push/pop/swap
s_vlanid                   = 1*4DIGIT   ; a number between 1 and 4094
```

## SAI API

Table shown below represents the SAI attributes which **_shall_** be used for VLAN stacking.

###### Table 3: SAI attributes related to VLAN stacking

| VLAN Stacking Component | SAI attribute                                              | Description                     |
| ----------------------- | ---------------------------------------------------------- | ------------------------------- |
| VLAN Stacking entry     | SAI_VLAN_STACK_ATTR_STAGE                                  | VLAN Stack stage                |
|                         | SAI_VLAN_STACK_ATTR_ACTION                                 | VLAN Stack action               |
|                         | SAI_VLAN_STACK_ATTR_MATCH_TYPE                             | VLAN Stack match type           |
|                         | SAI_VLAN_STACK_ATTR_VLAN_APPLIED_PRI                       | COS of the vlan tag             |
|                         | SAI_VLAN_STACK_ATTR_ORIGINAL_VLAN_ID                       | Original Vlan ID                |
|                         | SAI_VLAN_STACK_ATTR_PORT                                   | Port ID                         |
|                         | SAI_VLAN_STACK_ATTR_APPLIED_VLAN_ID                        | Applied Vlan ID                 |


For example, to create a ingress VLAN stacking push entry, Ports orchagent invokes the following SAI APIs with the necessary SAI attributes:

```json
"VLAN_STACKING": {
    "Ethernet10|ingress|21": {
        "action": "push",
        "s_vlanid": "22"
}
```

```c++
/* Create a ingress VLAN Stacking push entry object:
 * ------------------------------------------ */
sai_object_id_t vlan_stacking_oid;
sai_attribute_t attr;
vector<sai_attribute_t> vlan_stacking_entry_attrs;

attr.id = SAI_VLAN_STACK_ATTR_STAGE;
attr.value.s32 = SAI_VLAN_STACK_STAGE_INGRESS;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ACTION;
attr.value.s32 = SAI_VLAN_STACK_ACTION_PUSH
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_MATCH_TYPE;
attr.value.s32 = SAI_VLAN_STACK_MATCH_TYPE_INNER;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ORIGINAL_VLAN_ID;
attr.value.u16 = 21;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_PORT;
attr.value.oid = 10;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_APPLIED_VLAN_ID;
attr.value.u16 = 22;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_VLAN_APPLIED_PRI;
attr.value.u8 = 0;
vlan_stacking_entry_attrs.push(attr);

sai_vlan_api->create_vlan_stack(&vlan_stacking_oid, gSwitchId, (uint32_t)vlan_stacking_entry_attrs.size(), vlan_stacking_entry_attrs.data());
```

For example, to create a egress VLAN stacking pop entry, Ports orchagent invokes the following SAI APIs with the necessary SAI attributes:

```json
"VLAN_STACKING": {
    "Ethernet10|egress|22": {
        "action": "pop"
}
```

```c++
/* Create a egress VLAN Stacking pop entry object:
 * ------------------------------------------ */
sai_object_id_t vlan_stacking_oid;
sai_attribute_t attr;
vector<sai_attribute_t> vlan_stacking_entry_attrs;

attr.id = SAI_VLAN_STACK_ATTR_STAGE;
attr.value.s32 = SAI_VLAN_STACK_STAGE_EGRESS;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ACTION;
attr.value.s32 = SAI_VLAN_STACK_ACTION_POP
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_MATCH_TYPE;
attr.value.s32 = SAI_VLAN_STACK_MATCH_TYPE_OUTER;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ORIGINAL_VLAN_ID;
attr.value.u16 = 22;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_PORT;
attr.value.oid = 10;
vlan_stacking_entry_attrs.push(attr);

sai_vlan_api->create_vlan_stack(&vlan_stacking_oid, gSwitchId, (uint32_t)vlan_stacking_entry_attrs.size(), vlan_stacking_entry_attrs.data());
```

For example, to create a ingress VLAN stacking swap entry, Ports orchagent invokes the following SAI APIs with the necessary SAI attributes:

```json
"VLAN_STACKING": {
    "Ethernet30|ingress|10": {
        "action": "swap",
        "s_vlanid": "20"
} 
```

```c++
/* Create a ingress VLAN Stacking swap entry object:
 * ------------------------------------------ */
sai_object_id_t vlan_stacking_oid;
sai_attribute_t attr;
vector<sai_attribute_t> vlan_stacking_entry_attrs;

attr.id = SAI_VLAN_STACK_ATTR_STAGE;
attr.value.s32 = SAI_VLAN_STACK_STAGE_INGRESS;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ACTION;
attr.value.s32 = SAI_VLAN_STACK_ACTION_SWAP
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_MATCH_TYPE;
attr.value.s32 = SAI_VLAN_STACK_MATCH_TYPE_OUTER;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ORIGINAL_VLAN_ID;
attr.value.u16 = 10;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_PORT;
attr.value.oid = 30;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_APPLIED_VLAN_ID;
attr.value.u16 = 20;
vlan_stacking_entry_attrs.push(attr);

sai_vlan_api->create_vlan_stack(&vlan_stacking_oid, gSwitchId, (uint32_t)vlan_stacking_entry_attrs.size(), vlan_stacking_entry_attrs.data());
```

For example, to create a egress VLAN stacking swap entry, Ports orchagent invokes the following SAI APIs with the necessary SAI attributes:

```json
"VLAN_STACKING": {
    "Ethernet30|egress|20": {
        "action": "swap",
        "s_vlanid": "10"
}
```

```c++
/* Create a egress VLAN Stacking swap entry object:
 * ------------------------------------------ */
sai_object_id_t vlan_stacking_oid;
sai_attribute_t attr;
vector<sai_attribute_t> vlan_stack_entry_attrs;

attr.id = SAI_VLAN_STACK_ATTR_STAGE;
attr.value.s32 = SAI_VLAN_STACK_STAGE_EGRESS;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ACTION;
attr.value.s32 = SAI_VLAN_STACK_ACTION_SWAP
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_MATCH_TYPE;
attr.value.s32 = SAI_VLAN_STACK_MATCH_TYPE_OUTER;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_ORIGINAL_VLAN_ID;
attr.value.u16 = 20;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_PORT;
attr.value.oid = 30;
vlan_stacking_entry_attrs.push(attr);

attr.id = SAI_VLAN_STACK_ATTR_APPLIED_VLAN_ID;
attr.value.u16 = 10;
vlan_stacking_entry_attrs.push(attr);

sai_vlan_api->create_vlan_stack(&vlan_stacking_oid, gSwitchId, (uint32_t)vlan_stacking_entry_attrs.size(), vlan_stacking_entry_attrs.data());
```

# Configuration and management

## CLI/YANG model Enhancements

### CLI

CLI commands for VLAN stacking are not supported yet.

### Yang model

New yang model `sonic-vlan-stacking.yang` is defined to describe VLAN stacking configuration.

```json
module sonic-vlan-stacking {

    yang-version 1.0;

    namespace "http://github.com/Azure/sonic-vlan-stacking";
    prefix vlan-stacking;

    import sonic-extension {
        prefix ext;
        revision-date 2019-07-01;
    }

    import sonic-port {
        prefix port;
        revision-date 2019-07-01;
    }

    import sonic-portchannel {
        prefix lag;
        revision-date 2019-07-01;
    }

    import sonic-vlan {
        prefix vlan;
        revision-date 2019-07-01;
    }

    description "VLAN Stacking YANG Module for SONiC OS";

    revision 2021-12-15 {
        description "First Revision";
    }

    container sonic-vlan-stacking {
        container VLAN_STACKING {
            description "VLAN_STACKING part of config_db.json";

            list VLAN_STACKING_LIST {
                key "INTERFACE_NAME STAGE VLAN_ID";

                ext:key-regex-configdb-to-yang "^([a-zA-Z0-9_-]+)|([a-zA-Z0-9_-]+)|([0-9]+)$";

                ext:key-regex-yang-to-configdb "<INTERFACE_NAME>|<STAGE>|<VLAN_ID>";

                leaf INTERFACE_NAME {
                    type union {
                        type leafref {
                            path /port:sonic-port/port:PORT/port:PORT_LIST/port:port_name;
                        }
                        type leafref {
                            path /lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:portchannel_name;
                        }
                    }
                }

                leaf STAGE {
                    type string {
                        pattern 'ingress|egress';
                    }
                }

                leaf VLAN_ID {
                    type leafref {
                        path /vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:vlanid;
                    }
                }

                leaf action {
                    type string {
                        pattern 'push|pop|swap';
                    }
                }

                leaf s_vlanid {
                    type leafref {
                        path /vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:vlanid;
                    }
                }
            }
        }
    }
}
```

## Examples

### Examples of QinQ Configuration

The following configuration example shows C-VLAN 10 to S-VLAN 100 and C-VLAN 50 to S-VLAN 500 for ingress traffic on Ethernet1. And strips S-VLAN 100 and S-VLAN 500 for egress traffic on Ethernet1.

```json
"VLAN_STACKING": {
    "Ethernet1|ingress|10": {
        "action": "push",
        "s_vlanid": "100"
    },
    "Ethernet1|ingress|50": {
        "action": "push",
        "s_vlanid": "500"
    },
    "Ethernet1|egress|100": {
        "action": "pop"
    },
    "Ethernet1|egress|500": {
        "action": "pop"
    }
}
```

For port channel, the following configuration example shows C-VLAN 20 to S-VLAN 200 and C-VLAN 60 to S-VLAN 600 for ingress traffic on PortChannel01. And strips S-VLAN 200 and S-VLAN 600 for egress traffic on PortChannel01.

```json
"VLAN_STACKING": {
    "PortChannel01|ingress|20": {
        "action": "push",
        "s_vlanid": "200"
    },
    "PortChannel01|ingress|60": {
        "action": "push",
        "s_vlanid": "600"
    },
    "PortChannel01|egress|200": {
        "action": "pop"
    },
    "PortChannel01|egress|600": {
        "action": "pop"
    }
}
```

### Examples of VLAN Translation Configuration

For example, assume that the upstream switch does not support QinQ tunneling. As the following configuration example, select Ethernet1, and set the Old VLAN to 10 and the New VLAN to 510 to map VLAN 10 to VLAN 510 for upstream traffic entering Ethernet1, and VLAN 510 to VLAN 10 for downstream traffic leaving Ethernet1.

```json
"VLAN_STACKING": {
    "Ethernet1|ingress|10": {
        "action": "swap",
        "s_vlanid": "510"
    },
    "Ethernet1|egress|510": {
        "action": "swap",
        "s_vlanid": "10"
    }
}
```

As the following configuration example for port channel, select PortChannel01, and set the Old VLAN to 20 and the New VLAN to 620 to map VLAN 20 to VLAN 620 for upstream traffic entering PortChannel01, and VLAN 620 to VLAN 20 for downstream traffic leaving PortChannel01.

 ```json
"VLAN_STACKING": {
    "PortChannel01|ingress|20": {
        "action": "swap",
        "s_vlanid": "620"
    },
    "PortChannel01|egress|620": {
        "action": "swap",
        "s_vlanid": "20"
    }
}
```

# Warmboot and Fastboot Design Impact

Not impacted by the changes.

# Restrictions/Limitations

There is no restriction or limitation.

# Testing Requirements/Design

## System Test Cases

* Verify that the max N / M mapping for ingress / egress frames are able to configure.
* Verify that the max number of VLAN stacking configuration are able to configure.
* Verify that the configuration is working on only Ethernet and port channel interfaces.
* Verify that the invalid configuration doesn't take effect and an error is logged in syslog. (e.g., the port is not exist)
* Verify the rewrite action **_will_** be done if match C-VLAN,
  * push action for ingress frames
  * pop action for egress frames
  * swap action for ingress and egress frames

  | Inject frames on edge interface                     | push                        | pop              | swap (ingress)               | swap (egress)            |
  | --------------------------------------------------- | --------------------------- | ---------------- | ---------------------------- | ------------------------ |
  | untagged                                            | Forward using port VLAN     | N/A              | Forward using port VLAN      | N/A                      |
  | single tagged (with non-supported TPID, e.g., 9100) | Forward using port VLAN     | noop             | Forward using port VLAN      | noop                     |
  | single tagged (not match the mapping)               | Forward using port VLAN     | noop             | Forward using pkt outer VLAN | noop                     |
  | double tagged (not match the mapping)               | Forward using port VLAN     | noop             | Forward using pkt outer VLAN | noop                     |
  | single tagged (matched the mapping)                 | Add S-VLAN tag              | Remove outer tag | Replace C-VLAN as S-VLAN     | Replace S-VLAN as C-VLAN |
  | double tagged (matched the mapping)                 | Add S-VLAN tag (triple tag) | Remove outer tag | Replace C-VLAN AS S-VLAN     | Replace S-VLAN as C-VLAN |

* Verify that the double frame will be L2/L3 forwarded on any not enable interface (Ethernet and port channel interfaces). Outer TPID = 8100, others **_will_** be drop.
* Verify multiple mappings of different C-VLAN to separate S-VLANs per port. Include the combinations:
  * C-VLAN: One and multiple C-VLANs
  * S-VLAN: One and multiple S-VLANs
  * Interface for C-VLAN and S-VLAN as Ethernet port and channel port.
 