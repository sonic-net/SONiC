# SONiC Generic Hash

## High Level Design document

## Table of contents

- [Revision](#revision)
- [About this manual](#about-this-manual)
- [Scope](#scope)
- [Abbreviations](#abbreviations)
- [1 Introduction](#1-introduction)
    - [1.1 Feature overview](#11-feature-overview)
    - [1.2 Requirements](#12-requirements)
        - [1.2.1 Functionality](#121-functionality)
        - [1.2.2 Command interface](#122-command-interface)
        - [1.2.3 Error handling](#123-error-handling)
        - [1.2.4 Event logging](#124-event-logging)
- [2 Design](#2-design)
    - [2.1 Overview](#21-overview)
    - [2.2 SAI API](#22-sai-api)
    - [2.3 Orchestration agent](#23-orchestration-agent)
        - [2.3.1 Overview](#231-overview)
        - [2.3.2 Switch orch](#232-switch-orch)
    - [2.4 DB schema](#24-db-schema)
        - [2.4.1 Config DB](#241-config-db)
            - [2.4.1.1 Switch hash](#2411-switch-hash)
        - [2.4.2 State DB](#242-state-db)
            - [2.4.2.1 Switch hash capabilities](#2421-switch-hash-capabilities)
        - [2.4.3 Data sample](#243-data-sample)
        - [2.4.4 Configuration sample](#244-configuration-sample)
    - [2.5 Flows](#25-flows)
        - [2.5.1 Config section](#251-config-section)
            - [2.5.1.1 GH update](#2511-gh-update)
            - [2.5.1.2 Packet type hash create and update](#2512-packet-type-hash-create-and-update)
            - [2.5.1.3 Packet type hash delete](#2513-packet-type-hash-delete)
        - [2.5.2 Show section](#252-show-section)
            - [2.5.2.1 GH show](#2521-gh-show)
            - [2.5.2.2 GH show capabilities](#2522-gh-show-capabilities)
    - [2.6 CLI](#26-cli)
        - [2.6.1 Command structure](#261-command-structure)
        - [2.6.2 Usage examples](#262-usage-examples)
            - [2.6.2.1 Config command group](#2621-config-command-group)
            - [2.6.2.2 Show command group](#2622-show-command-group)
    - [2.7 YANG model](#27-yang-model)
    - [2.8 Warm/Fast boot](#28-warmfast-boot)
- [3 Test plan](#3-test-plan)
    - [3.1 Unit tests via VS](#31-unit-tests-via-vs)
    - [3.2 Data plane tests via PTF](#32-data-plane-tests-via-ptf)

## Revision

| Rev | Date       | Author         | Description                                     |
|:---:|:----------:|:--------------:|:------------------------------------------------|
| 0.1 | 12/09/2022 | Nazarii Hnydyn | Initial version                                 |
| 0.2 | 05/12/2022 | Nazarii Hnydyn | Capabilities validation                         |
| 0.3 | 25/09/2023 | Nazarii Hnydyn | Hashing algorithm configuration                 |
| 0.4 | 23/01/2025 | Andriy Yurkiv  | Add 'IPv6 flow label' field for hashing packets |
| 0.5 | 11/11/2025 | Anandhi Dhanabalan  | Add support for RoCE hash fields and hashing based on packet types |

## About this manual

This document provides general information about GH implementation in SONiC

## Scope

This document describes the high level design of GH feature in SONiC

**In scope:**  
1. ECMP/LAG switch hash configuration
2. ECMP/LAG switch hash algorithm configuration
3. ECMP/LAG packet type based switch hash

**Out of scope:**  
1. ECMP/LAG switch hash seed configuration
2. ECMP/LAG switch hash offset configuration

## Abbreviations

| Term   | Meaning                                   |
|:-------|:------------------------------------------|
| SONiC  | Software for Open Networking in the Cloud |
| GH     | Generic Hash                              |
| ECMP   | Equal-Cost Multi-Path                     |
| LAG    | Link Aggregation Group                    |
| IP     | Internet Protocol                         |
| SAI    | Switch Abstraction Interface              |
| API    | Application Programming Interface         |
| ASIC   | Application-Specific Integrated Circuit   |
| OA     | Orchestration agent                       |
| DB     | Database                                  |
| CLI    | Сommand-line Interface                    |
| YANG   | Yet Another Next Generation               |
| VS     | Virtual Switch                            |
| PTF    | Packet Test Framework                     |
| RoCE   | Remote Direct Memory Access over Converged Ethernet |

## List of figures

[Figure 1: GH design](#figure-1-gh-design)  
[Figure 2: GH OA design](#figure-2-gh-oa-design)  
[Figure 3: GH update flow](#figure-3-gh-update-flow)  
[Figure 4: Packet type hash create and update flow](#figure-4-Packet-type-hash-create-and-update-flow)  
[Figure 5: Packet Type Hash delete flow](#figure-5-Packet-type-hash-delete-flow)  
[Figure 6: GH show flow](#figure-6-gh-show-flow)  
[Figure 7: GH show capabilities flow](#figure-7-gh-show-capabilities-flow)

## List of tables

[Table 1: Frontend event logging](#table-1-frontend-event-logging)  
[Table 2: Backend event logging](#table-2-backend-event-logging)

# 1 Introduction

## 1.1 Feature overview

The hashing algorithm is used to make traffic-forwarding decisions for traffic exiting the switch.  
It makes hashing decisions based on values in various packet fields, as well as on the hash seed value.  
The packet fields used by the hashing algorithm varies by the configuration on the switch.

For ECMP, the hashing algorithm determines how incoming traffic is forwarded to the next-hop device.  
For LAG, the hashing algorithm determines how traffic is placed onto the LAG member links to manage  
bandwidth by evenly load-balancing traffic across the outgoing links.

GH is a feature which allows user to configure various aspects of hashing algorithm.  
GH provides global switch hash configuration for ECMP and LAG.

## 1.2 Requirements

### 1.2.1 Functionality

**This feature will support the following functionality:**
1. Ethernet packet hashing configuration with inner/outer IP frames
2. Global switch hash configuration for ECMP and LAG
3. Warm/Fast reboot
4. Global switch hash packet-type based configuration for ECMP and LAG
5. RoCE hash fields configuration

### 1.2.2 Command interface

**This feature will support the following commands:**
1. config: set switch hash global configuration
2. show: display switch hash global configuration

### 1.2.3 Error handling

#### 1.2.3.1 Frontend

**This feature will provide error handling for the next situations:**
1. Invalid parameter value

#### 1.2.3.2 Backend

**This feature will provide error handling for the next situations:**
1. Missing parameters
2. Invalid parameter value
3. Parameter removal
4. Configuration removal

### 1.2.4 Event logging

#### 1.2.4.1 Frontend

**This feature will provide event logging for the next situations:**
1. Switch hash update

###### Table 1: Frontend event logging

| Event                       | Severity |
|:----------------------------|:---------|
| Switch hash update: success | NOTICE   |
| Switch hash update: error   | ERROR    |

#### 1.2.4.2 Backend

**This feature will provide event logging for the next situations:**
1. Missing parameters
2. Invalid parameter value
3. Parameter value with duplicate items
4. Parameter removal
5. Configuration removal
6. Switch hash update

###### Table 2: Backend event logging

| Event                                | Severity |
|:-------------------------------------|:---------|
| Missing parameters                   | ERROR    |
| Invalid parameter value              | ERROR    |
| Parameter value with duplicate items | WARNING  |
| Parameter removal                    | ERROR    |
| Configuration removal                | ERROR    |
| Switch hash update: success          | NOTICE   |
| Switch hash update: error            | ERROR    |

# 2 Design

## 2.1 Overview

![GH design](images/gh_design.svg "Figure 1: GH design")

###### Figure 1: GH design

GH will use SAI Hash API to configure various aspects of hashing algorithm to ASIC.  
Hashing policy can be set independently for ECMP and LAG.

**GH important notes:**
1. According to the SAI Behavioral Model, the hash is calculated on ingress to pipeline
2. SAI configuration of hash fields is applicable to original packet before any DECAP/ENCAP,
i.e. configuration is tunnel-agnostic
3. If some configured hash field is not present in an incoming packet, then zero is assumed for hash calculation
4. When both a global hash and a corresponding packet-type hash (e.g., `lag_hash` and `lag_hash_ipv4`) are configured:
    - The packet-type-specific hash should be applied to its respective packet type (for example, `lag_hash_ipv4` for IPv4 packets).
    - The global hash (`lag_hash`) should be used for all other packet types.

## 2.2 SAI API

**SAI native hash fields which shall be used for GH:**

| Field                                   | Comment                        |
|:----------------------------------------|:-------------------------------|
| SAI_NATIVE_HASH_FIELD_IN_PORT           | SWITCH_HASH\|GLOBAL\|ecmp_hash |
| SAI_NATIVE_HASH_FIELD_DST_MAC           | SWITCH_HASH\|GLOBAL\|lag_hash  |
| SAI_NATIVE_HASH_FIELD_SRC_MAC           |                                |
| SAI_NATIVE_HASH_FIELD_ETHERTYPE         |                                |
| SAI_NATIVE_HASH_FIELD_VLAN_ID           |                                |
| SAI_NATIVE_HASH_FIELD_IP_PROTOCOL       |                                |
| SAI_NATIVE_HASH_FIELD_DST_IP            |                                |
| SAI_NATIVE_HASH_FIELD_SRC_IP            |                                |
| SAI_NATIVE_HASH_FIELD_L4_DST_PORT       |                                |
| SAI_NATIVE_HASH_FIELD_L4_SRC_PORT       |                                |
| SAI_NATIVE_HASH_FIELD_INNER_DST_MAC     |                                |
| SAI_NATIVE_HASH_FIELD_INNER_SRC_MAC     |                                |
| SAI_NATIVE_HASH_FIELD_INNER_ETHERTYPE   |                                |
| SAI_NATIVE_HASH_FIELD_INNER_IP_PROTOCOL |                                |
| SAI_NATIVE_HASH_FIELD_INNER_DST_IP      |                                |
| SAI_NATIVE_HASH_FIELD_INNER_SRC_IP      |                                |
| SAI_NATIVE_HASH_FIELD_INNER_L4_DST_PORT |                                |
| SAI_NATIVE_HASH_FIELD_INNER_L4_SRC_PORT |                                |
| SAI_NATIVE_HASH_FIELD_IPV6_FLOW_LABEL   |                                |
| SAI_NATIVE_HASH_FIELD_RDMA_BTH_OPCODE   |                                |
| SAI_NATIVE_HASH_FIELD_RDMA_BTH_DEST_QP  |                                |

**SAI hash algorithms which shall be used for GH:**

| Algorithm                    | Comment                                  |
|:-----------------------------|:-----------------------------------------|
| SAI_HASH_ALGORITHM_CRC       | SWITCH_HASH\|GLOBAL\|ecmp_hash_algorithm |
| SAI_HASH_ALGORITHM_XOR       | SWITCH_HASH\|GLOBAL\|lag_hash_algorithm  |
| SAI_HASH_ALGORITHM_RANDOM    |                                          |
| SAI_HASH_ALGORITHM_CRC_32LO  |                                          |
| SAI_HASH_ALGORITHM_CRC_32HI  |                                          |
| SAI_HASH_ALGORITHM_CRC_CCITT |                                          |
| SAI_HASH_ALGORITHM_CRC_XOR   |                                          |

**SAI attributes which shall be used for GH:**

| API    | Function                                   | Attribute                                   |
|:-------|:-------------------------------------------|:--------------------------------------------|
| OBJECT | sai_query_attribute_capability             | SAI_SWITCH_ATTR_ECMP_HASH                   |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH                    |
|        |                                            | SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST        |
|        |                                            | SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM |
|        |                                            | SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM  |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4              |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV6              |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4_IN_IPV4      |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4_RDMA         |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV6_RDMA         |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4               |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV6               |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4_IN_IPV4       |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4_RDMA          |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV6_RDMA          |
|        | sai_query_attribute_enum_values_capability | SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST        |
|        |                                            | SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM |
|        |                                            | SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM  |
| SWITCH | get_switch_attribute                       | SAI_SWITCH_ATTR_ECMP_HASH                   |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH                    |
|        | set_switch_attribute                       | SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM |
|        |                                            | SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM  |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4              |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV6              |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4_IN_IPV4      |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV4_RDMA         |
|        |                                            | SAI_SWITCH_ATTR_ECMP_HASH_IPV6_RDMA         |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4               |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV6               |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4_IN_IPV4       |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV4_RDMA          |
|        |                                            | SAI_SWITCH_ATTR_LAG_HASH_IPV6_RDMA          |
| HASH   | set_hash_attribute                         | SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST        |

## 2.3 Orchestration agent

### 2.3.1 Overview

![GH OA design](images/gh_swss_design.svg "Figure 2: GH OA design")

###### Figure 2: GH OA design

The existing `SwitchOrch` class will be extended with a new APIs to implement GH feature.  
OA will be extended with a new GH Config DB schema and SAI Hash API support.  
Switch hash updates will be processed by OA based on Config DB changes.  
Some updates will be handled and some will be considered as invalid.

### 2.3.2 Switch orch

Class `SwitchOrch` holds a set of methods matching generic `Orch` class pattern to handle Config DB updates.  
For that purpose a producer-consumer mechanism (implemented in `sonic-swss-common`) is used.  
Method `SwitchOrch::doTask()` will be called on switch hash update. It will distribute handling  
of DB updates between other handlers based on the table key updated (Redis Keyspace Notifications).

This class is responsible for:
1. Processing updates of switch hash
2. Partial input data validation
3. Replicating data from Config DB to SAI DB via SAI Redis
4. Caching objects in order to handle updates

Switch hash object is stored under `SWITCH_HASH|GLOBAL` key in Config DB. On `SWITCH_HASH` update,  
method `SwitchOrch::doCfgSwitchHashTableTask()` will be called to process the change.  
Regular switch hash update will refresh the internal class structures and appropriate SAI objects.

Switch hash capabilities are stored under `SWITCH_CAPABILITY|switch` key in State DB.  
The vendor specific data is being queried by switch OA on init and pushed to both internal cache and DB.  
Any further switch hash update is being validated using vendor specific hash capabilities.

**Skeleton code:**
```cpp

enum class HashPktType
{
    INVALID,
    IPV4,
    IPV6,
    IPV4_IN_IPV4,
    IPV4_RDMA,
    IPV6_RDMA
};

class SwitchOrch : public Orch
{
    ...

private:
    void doCfgSwitchHashTableTask(Consumer &consumer);
    void doTask(Consumer &consumer);

    // Switch hash
    bool setSwitchHashFieldListSai(sai_object_id_t oid, std::vector<sai_int32_t> &hfList) const;
    bool setSwitchHashEcmpHash(const SwitchHash &hash) const;
    bool setSwitchHashLagHash(const SwitchHash &hash) const;
    bool setSwitchHash(const SwitchHash &hash);

    bool getSwitchHashOidSai(sai_object_id_t &oid, bool isEcmpHashOid) const;
    void getSwitchHashEcmpOid();
    void getSwitchHashLagOid();
    void querySwitchHashDefaults();

    // Switch packet-type hash
    bool applySwitchHashConfig(const SwitchHash &hash, HashPktType pktType, bool isEcmpHash);
    bool removeSwitchHashConfig(const SwitchHash &hash, HashPktType pktType, bool isEcmpHash);

    // Switch hash SAI defaults
    struct {
        struct {
            sai_object_id_t oid = SAI_NULL_OBJECT_ID;
        } ecmpHash;
        struct {
            sai_object_id_t oid = SAI_NULL_OBJECT_ID;
        } lagHash;
    } m_switchHashDefaults;

    // Switch packet-type hash for ECMP
    std::map<HashPktType, sai_object_id_t> m_switchHashEcmp;

    // Switch packet-type hash for LAG
    std::map<HashPktType, sai_object_id_t> m_switchHashLag;

    // Switch OA helper
    SwitchHelper swHlpr;

    ...
};
```

## 2.4 DB schema

### 2.4.1 Config DB

#### 2.4.1.1 Switch hash
```abnf
; defines schema for switch hash configuration attributes
key = SWITCH_HASH|GLOBAL ; switch hash global. Must be unique

; field             = value
ecmp_hash           = hash-field-list ; hash fields for hashing packets going through ECMP
lag_hash            = hash-field-list ; hash fields for hashing packets going through LAG
ecmp_hash_algorithm = hash-algorithm  ; hash algorithm for hashing packets going through ECMP
lag_hash_algorithm  = hash-algorithm  ; hash algorithm for hashing packets going through LAG
ecmp_hash_ipv4      = hash-field-list ; hash fields for hashing ipv4 packets going through ECMP
ecmp_hash_ipv6      = hash-field-list ; hash fields for hashing ipv6 packets going through ECMP
ecmp_hash_ipnip     = hash-field-list ; hash fields for hashing ipv4 in ipv4 packets going through ECMP
ecmp_hash_ipv4_rdma = hash-field-list ; hash fields for hashing ipv4 RDMA packets going through ECMP
ecmp_hash_ipv6_rdma = hash-field-list ; hash fields for hashing ipv6 RDMA packets going through ECMP
lag_hash_ipv4       = hash-field-list ; hash fields for hashing ipv4 packets going through LAG
lag_hash_ipv6       = hash-field-list ; hash fields for hashing ipv6 packets going through LAG
lag_hash_ipnip      = hash-field-list ; hash fields for hashing ipv4 in ipv4 packets going through LAG
lag_hash_ipv4_rdma  = hash-field-list ; hash fields for hashing ipv4 RDMA packets going through LAG
lag_hash_ipv6_rdma  = hash-field-list ; hash fields for hashing ipv6 RDMA packets going through LAG

; value annotations
hash-field      = "IN_PORT"
                / "DST_MAC"
                / "SRC_MAC"
                / "ETHERTYPE"
                / "VLAN_ID"
                / "IP_PROTOCOL"
                / "DST_IP"
                / "SRC_IP"
                / "L4_DST_PORT"
                / "L4_SRC_PORT"
                / "INNER_DST_MAC"
                / "INNER_SRC_MAC"
                / "INNER_ETHERTYPE"
                / "INNER_IP_PROTOCOL"
                / "INNER_DST_IP"
                / "INNER_SRC_IP"
                / "INNER_L4_DST_PORT"
                / "INNER_L4_SRC_PORT"
                / "IPV6_FLOW_LABEL"
                / "RDMA_BTH_OPCODE"
                / "RDMA_BTH_DEST_QP"
hash-field-list = hash-field [ 1*( "," hash-field ) ]
hash-algorithm  = "CRC"
                / "XOR"
                / "RANDOM"
                / "CRC_32LO"
                / "CRC_32HI"
                / "CRC_CCITT"
                / "CRC_XOR"
```

### 2.4.2 State DB

#### 2.4.2.1 Switch hash capabilities
```abnf
; defines schema for switch hash configuration capabilities
key = SWITCH_CAPABILITY|switch ; must be unique

; field                     = value
ECMP_HASH_CAPABLE           = capability-knob ; specifies whether switch is ECMP hash capable
LAG_HASH_CAPABLE            = capability-knob ; specifies whether switch is LAG hash capable
HASH|NATIVE_HASH_FIELD_LIST = hash-field-list ; hash field capabilities for hashing packets going through switch
ECMP_HASH_ALGORITHM_CAPABLE = capability-knob ; specifies whether switch is ECMP hash algorithm capable
LAG_HASH_ALGORITHM_CAPABLE  = capability-knob ; specifies whether switch is LAG hash algorithm capable
ECMP_HASH_ALGORITHM         = hash-algorithm  ; hash algorithm capabilities for hashing packets going through ECMP
LAG_HASH_ALGORITHM          = hash-algorithm  ; hash algorithm capabilities for hashing packets going through LAG
ECMP_PKT_TYPE_HASH_CAPABLE  = capability-knob ; specifies whether switch is ECMP packet type hash capable
LAG_PKT_TYPE_HASH_CAPABLE   = capability-knob ; specifies whether switch is LAG packet type hash capable
HASH|ECMP_PKT_TYPE_LIST     = pkt-type-list   ; packet type capabilities for hashing packets going through ECMP
HASH|LAG_PKT_TYPE_LIST      = pkt-type-list   ; packet type capabilities for hashing packets going through LAG



; value annotations
capability-knob = "true" / "false"
hash-field      = ""
                / "N/A"
                / "IN_PORT"
                / "DST_MAC"
                / "SRC_MAC"
                / "ETHERTYPE"
                / "VLAN_ID"
                / "IP_PROTOCOL"
                / "DST_IP"
                / "SRC_IP"
                / "L4_DST_PORT"
                / "L4_SRC_PORT"
                / "INNER_DST_MAC"
                / "INNER_SRC_MAC"
                / "INNER_ETHERTYPE"
                / "INNER_IP_PROTOCOL"
                / "INNER_DST_IP"
                / "INNER_SRC_IP"
                / "INNER_L4_DST_PORT"
                / "INNER_L4_SRC_PORT"
                / "IPV6_FLOW_LABEL"
                / "RDMA_BTH_OPCODE"
                / "RDMA_BTH_DEST_QP"                
hash-field-list = hash-field [ 1*( "," hash-field ) ]
hash-algorithm  = ""
                / "N/A"
                / "CRC"
                / "XOR"
                / "RANDOM"
                / "CRC_32LO"
                / "CRC_32HI"
                / "CRC_CCITT"
                / "CRC_XOR"
pkt-type        = ""
                / "N/A"
                / "IPV4"
                / "IPV6"                
                / "IPV4_IN_IPV4"
                / "IPV4_RDMA"                
                / "IPV6_RDMA"   
pkt-type-list = pkt-type [ 1*( "," pkt-type ) ]                                             
```

### 2.4.3 Data sample

**Config DB:**
```bash
redis-cli -n 4 HGETALL 'SWITCH_HASH|GLOBAL'
1) "ecmp_hash@"
2) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
3) "lag_hash@"
4) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
5) "ecmp_hash_algorithm"
6) "CRC"
7) "lag_hash_algorithm"
8) "CRC"
9) "ecmp_hash@ipv4"
10) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
11) "ecmp_hash@ipv6"
12) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
13) "ecmp_hash@ipnip"
14) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
15) "ecmp_hash@ipv4_rdma"
16) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
17) "ecmp_hash@ipv6_rdma"
18) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
19) "lag_hash@ipv4"
20) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
21) "lag_hash@ipv6"
22) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
23) "lag_hash@ipnip"
24) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
25) "lag_hash@ipv4_rdma"
26) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
27) "lag_hash@ipv6_rdma"
28) "DST_MAC,SRC_MAC,ETHERTYPE,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP,INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
```

**State DB:**
```bash
redis-cli -n 6 HGETALL 'SWITCH_CAPABILITY|switch'
 1) "ECMP_HASH_CAPABLE"
 2) "true"
 3) "LAG_HASH_CAPABLE"
 4) "true"
 5) "HASH|NATIVE_HASH_FIELD_LIST"
 6) "IN_PORT,DST_MAC,SRC_MAC,ETHERTYPE,VLAN_ID,IP_PROTOCOL,DST_IP,SRC_IP,L4_DST_PORT,L4_SRC_PORT, \
INNER_DST_MAC,INNER_SRC_MAC,INNER_ETHERTYPE,INNER_IP_PROTOCOL,INNER_DST_IP,INNER_SRC_IP, \
INNER_L4_DST_PORT,INNER_L4_SRC_PORT,IPV6_FLOW_LABEL,RDMA_BTH_OPCODE,RDMA_BTH_DEST_QP"
 7) "ECMP_HASH_ALGORITHM_CAPABLE"
 8) "true"
 9) "LAG_HASH_ALGORITHM_CAPABLE"
10) "true"
11) "ECMP_HASH_ALGORITHM"
12) "CRC,XOR,RANDOM,CRC_32LO,CRC_32HI,CRC_CCITT,CRC_XOR"
13) "LAG_HASH_ALGORITHM"
14) "CRC,XOR,RANDOM,CRC_32LO,CRC_32HI,CRC_CCITT,CRC_XOR"
15) "ECMP_PKT_TYPE_HASH_CAPABLE" 
16) "true"
17) "LAG_PKT_TYPE_HASH_CAPABLE"
18) "true"
19) "HASH|ECMP_PKT_TYPE_LIST"
20) "IPV4","IPV4_IN_IPV4","IPV6","IPV4_RDMA","IPV6_RDMA" 
19) "HASH|LAG_PKT_TYPE_LIST"
20) "IPV4","IPV4_IN_IPV4","IPV6","IPV4_RDMA","IPV6_RDMA"

```

### 2.4.4 Configuration sample

**Outer/Inner frame hashing:**
```json
{
    "SWITCH_HASH": {
        "GLOBAL": {
            "ecmp_hash": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT",
                "IPV6_FLOW_LABEL",
                "RDMA_BTH_OPCODE",
                "RDMA_BTH_DEST_QP"                 
            ],
            "lag_hash": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT",
                "IPV6_FLOW_LABEL"
            ],
            "ecmp_hash_ipv4": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT"
            ], 
            "ecmp_hash_ipv6": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "IPV6_FLOW_LABEL"                
            ],
            "ecmp_hash_ipnip": [
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT"
            ],                                     
            "ecmp_hash_ipv4_rdma": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "RDMA_BTH_OPCODE",
                "RDMA_BTH_DEST_QP"                 
            ],              
            "ecmp_hash_ipv6_rdma": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "IPV6_FLOW_LABEL", 
                "RDMA_BTH_OPCODE",
                "RDMA_BTH_DEST_QP"                 
            ],            
            "lag_hash_ipv4": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT"
            ], 
            "lag_hash_ipv6": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "IPV6_FLOW_LABEL"                
            ],
            "lag_hash_ipnip": [
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "INNER_DST_MAC",
                "INNER_SRC_MAC",
                "INNER_ETHERTYPE",
                "INNER_IP_PROTOCOL",
                "INNER_DST_IP",
                "INNER_SRC_IP",
                "INNER_L4_DST_PORT",
                "INNER_L4_SRC_PORT"
            ],                                     
            "lag_hash_ipv4_rdma": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "RDMA_BTH_OPCODE",
                "RDMA_BTH_DEST_QP"                 
            ],              
            "lag_hash_ipv6_rdma": [
                "DST_MAC",
                "SRC_MAC",
                "ETHERTYPE",
                "IP_PROTOCOL",
                "DST_IP",
                "SRC_IP",
                "L4_DST_PORT",
                "L4_SRC_PORT",
                "IPV6_FLOW_LABEL",
                "RDMA_BTH_OPCODE",
                "RDMA_BTH_DEST_QP"                 
            ],           
            "ecmp_hash_algorithm": "CRC",
            "lag_hash_algorithm": "CRC"
        }
    }
}
```

## 2.5 Flows

### 2.5.1 Config section

### 2.5.1.1 GH update
![GH update flow](images/gh_apply_flow.svg "Figure 3: GH update flow")

###### Figure 3: GH update flow

**Note:**  

The list of available hash fields will be queried by `sai_query_attribute_enum_values_capability` in two steps.  
The first attempt is used to accommodate the target list size after getting `SAI_STATUS_BUFFER_OVERFLOW` return code.  
And the second one is for getting the actual data.
  

### 2.5.1.2 Packet type hash create and update
![Packet type hash create and update flow](images/pkt_type_hash_update_flow.svg "Figure 4: Packet type hash create and update flow")

###### Figure 4: Packet type hash create and update flow

### 2.5.1.3 Packet type hash delete
![Packet type hash delete flow](images/pkt_type_hash_delete_flow.svg "Figure 5: Packet type hash delete flow")

###### Figure 5: Packet type hash delete flow

1. **Packet-type Option Workflow**

   - If user selects the `packet-type` option:
     - CLI performs capability checks.
     - Only if capabilities exist for the selected packet-type, hash config commands are written into CONFIG_DB

2. **Hash Configuration Handling in switchOrch**
   - switchOrch that subscribes to CONFIG_DB consumes entries from SWITCH_HASH CONFIG_DB.
   - When **switchOrch** receives the HSET configuration, it checks if the packet-type hash is already configured
       - **If not configured:**  _Treat as a create operation._
       - **If configured:** _Treat as an update operation._

   - When **switchOrch** receives the HDEL configuration, it checks if the packet-type hash exists
       - **If not configured:**  _Ignores the operation._
       - **If configured:** _Deletes the packet-type hash._

  
### 2.5.2 Show section

#### 2.5.2.1 GH show

![GH show flow](images/gh_show_flow.svg "Figure 6: GH show flow")

###### Figure 6: GH show flow

#### 2.5.2.2 GH show capabilities

![GH show capabilities flow](images/gh_show_cap_flow.svg "Figure 7: GH show capabilities flow")

###### Figure 7: GH show capabilities flow

## 2.6 CLI

### 2.6.1 Command structure

**User interface**:

```
config
|--- switch-hash
     |--- global
          |--- ecmp-hash [packet-type <pkt-type> <add|del>] ARGS
          |--- lag-hash [packet-type <pkt-type> <add|del>] ARGS
          |--- ecmp-hash-algorithm ARG
          |--- lag-hash-algorithm ARG 
          
show
|--- switch-hash
     |--- global [packet-type <pkt-type>]
     |--- capabilities
```
**Note:-**
- _pkt-type (Supported values):_
  - _all, ipv4, ipv6, ipnip, ipv4-rdma, ipv6-rdma_
- _In config command:_
  - _`packet-type <pkt-type> <add|del>`: Optional parameter, if omitted updates global hash_
    - _`add`: Creates packet type hash if one doesn't exist, else overwrites the hash fields in existing hash_
    - _`del`: Deletes Packet type hash_
- _In show command:_
  - _`packet-type <pkt-type>` is optional; `all` packet-type is valid only for show_
  - _If pkt-type omitted: Shows global hash configuration/capabilities_
  - _If pkt-type is all: Shows all packet type hash configuration/capabilities_

### 2.6.2 Usage examples

#### 2.6.2.1 Config command group

**The following command updates switch hash global defaults:**  
**Note:-**  
_RDMA_BTH_OPCODE and RDMA_BTH_DEST_QP are optional fields in the global hash configuration._  
_They are supported by the design but can be omitted from update commands if not required._

```bash
config switch-hash global ecmp-hash \
'DST_MAC' \
'SRC_MAC' \
'ETHERTYPE' \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'INNER_DST_MAC' \
'INNER_SRC_MAC' \
'INNER_ETHERTYPE' \
'INNER_IP_PROTOCOL' \
'INNER_DST_IP' \
'INNER_SRC_IP' \
'INNER_L4_DST_PORT' \
'INNER_L4_SRC_PORT' \
'IPV6_FLOW_LABEL', \
"RDMA_BTH_OPCODE", \
"RDMA_BTH_DEST_QP"

config switch-hash global lag-hash \
'DST_MAC' \
'SRC_MAC' \
'ETHERTYPE' \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'INNER_DST_MAC' \
'INNER_SRC_MAC' \
'INNER_ETHERTYPE' \
'INNER_IP_PROTOCOL' \
'INNER_DST_IP' \
'INNER_SRC_IP' \
'INNER_L4_DST_PORT' \
'INNER_L4_SRC_PORT' \
'IPV6_FLOW_LABEL' 
```

**The following command creates switch packet-type hash:**
```bash
config switch-hash global ecmp-hash packet-type ipv4-rdma add \
'DST_MAC' \
'SRC_MAC' \
'ETHERTYPE' \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'RDMA_BTH_OPCODE' \
'RDMA_BTH_DEST_QP'

config switch-hash global lag-hash packet-type ipnip add \
'IP_PROTOCOL' \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'INNER_DST_MAC' \
'INNER_SRC_MAC' \
'INNER_ETHERTYPE' \
'INNER_IP_PROTOCOL' \
'INNER_DST_IP' \
'INNER_SRC_IP' \
'INNER_L4_DST_PORT' \
'INNER_L4_SRC_PORT' \
```

**The following command updates switch packet-type hash:**
```bash
config switch-hash global ecmp-hash packet-type ipv4-rdma add \
'DST_IP' \
'SRC_IP' \
'L4_DST_PORT' \
'L4_SRC_PORT' \
'RDMA_BTH_OPCODE' \
'RDMA_BTH_DEST_QP'
```
**The following command removes switch packet-type hash:**
```bash
config switch-hash global ecmp-hash packet-type ipv4-rdma del
config switch-hash global lag-hash packet-type ipnip del

```
**The following command updates switch hash algorithm global:**
```bash
config switch-hash global ecmp-hash-algorithm 'CRC'
config switch-hash global lag-hash-algorithm 'CRC'

```

#### 2.6.2.2 Show command group

**The following command shows switch hash global configuration:**
```bash
root@sonic:/home/admin# show switch-hash global
+--------+-------------------------------------+
| Hash   | Configuration                       |
+========+=====================================+
| ECMP   | +-------------------+-------------+ |
|        | | Hash Field        | Algorithm   | |
|        | |-------------------+-------------| |
|        | | DST_MAC           | CRC         | |
|        | | SRC_MAC           |             | |
|        | | ETHERTYPE         |             | |
|        | | IP_PROTOCOL       |             | |
|        | | DST_IP            |             | |
|        | | SRC_IP            |             | |
|        | | L4_DST_PORT       |             | |
|        | | L4_SRC_PORT       |             | |
|        | | INNER_DST_MAC     |             | |
|        | | INNER_SRC_MAC     |             | |
|        | | INNER_ETHERTYPE   |             | |
|        | | INNER_IP_PROTOCOL |             | |
|        | | INNER_DST_IP      |             | |
|        | | INNER_SRC_IP      |             | |
|        | | INNER_L4_DST_PORT |             | |
|        | | INNER_L4_SRC_PORT |             | |
|        | | IPV6_FLOW_LABEL   |             | |
|        | | RDMA_BTH_OPCODE   |             | |
|        | | RDMA_BTH_DEST_QP  |             | |
|        | +-------------------+-------------+ |
+--------+-------------------------------------+
| LAG    | +-------------------+-------------+ |
|        | | Hash Field        | Algorithm   | |
|        | |-------------------+-------------| |
|        | | DST_MAC           | CRC         | |
|        | | SRC_MAC           |             | |
|        | | ETHERTYPE         |             | |
|        | | IP_PROTOCOL       |             | |
|        | | DST_IP            |             | |
|        | | SRC_IP            |             | |
|        | | L4_DST_PORT       |             | |
|        | | L4_SRC_PORT       |             | |
|        | | INNER_DST_MAC     |             | |
|        | | INNER_SRC_MAC     |             | |
|        | | INNER_ETHERTYPE   |             | |
|        | | INNER_IP_PROTOCOL |             | |
|        | | INNER_DST_IP      |             | |
|        | | INNER_SRC_IP      |             | |
|        | | INNER_L4_DST_PORT |             | |
|        | | INNER_L4_SRC_PORT |             | |
|        | | IPV6_FLOW_LABEL   |             | |
|        | | RDMA_BTH_OPCODE   |             | |
|        | | RDMA_BTH_DEST_QP  |             | |
|        | +-------------------+-------------+ |
+--------+-------------------------------------+

root@sonic:/home/admin# show switch-hash global packet-type ipv4-rdma
+--------+-----------+-----------------------------------+
| Hash   | Pkt-Type  | Configuration                     |
+========+===========+===================================+
| ECMP   | ipv4-rdma | +------------------+------------+ |
|        |           | | Hash Field       | Algorithm  | |
|        |           | |------------------+------------| |
|        |           | | DST_MAC          | CRC        | |
|        |           | | SRC_MAC          |            | |
|        |           | | ETHERTYPE        |            | |
|        |           | | IP_PROTOCOL      |            | |
|        |           | | DST_IP           |            | |
|        |           | | SRC_IP           |            | |
|        |           | | L4_DST_PORT      |            | |
|        |           | | L4_SRC_PORT      |            | |
|        |           | | RDMA_BTH_OPCODE  |            | |
|        |           | | RDMA_BTH_DEST_QP |            | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipv4-rdma | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+

root@sonic:/home/admin# show switch-hash global packet-type ipnip
+--------+-----------+-----------------------------------+
| Hash   | Pkt-Type  | Configuration                     |
+========+===========+===================================+
| ECMP   | ipnip     | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipnip     | +-------------------------------+ |
|        |           | | Hash Field        | Algorithm | |
|        |           | |-------------------+-----------| |
|        |           | | IP_PROTOCOL       | CRC       | |
|        |           | | DST_IP            |           | |
|        |           | | SRC_IP            |           | |
|        |           | | L4_DST_PORT       |           | |
|        |           | | L4_SRC_PORT       |           | |
|        |           | | INNER_DST_MAC     |           | |
|        |           | | INNER_SRC_MAC     |           | |
|        |           | | INNER_ETHERTYPE   |           | |
|        |           | | INNER_IP_PROTOCOL |           | |
|        |           | | INNER_DST_IP      |           | |
|        |           | | INNER_SRC_IP      |           | |
|        |           | | INNER_L4_DST_PORT |           | |
|        |           | | INNER_L4_SRC_PORT |           | |
|        |           | +-------------------+-----------+ |
+--------+-----------+-----------------------------------+

root@sonic:/home/admin# show switch-hash global packet-type all
+--------+-----------+-----------------------------------+
| Hash   | Pkt-Type  | Configuration                     |
+========+===========+===================================+
| ECMP   | ipv4      | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| ECMP   | ipv6      | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| ECMP   | ipnip     | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| ECMP   | ipv4-rdma | +------------------+------------+ |
|        |           | | Hash Field       | Algorithm  | |
|        |           | |------------------+------------| |
|        |           | | DST_MAC          | CRC        | |
|        |           | | SRC_MAC          |            | |
|        |           | | ETHERTYPE        |            | |
|        |           | | IP_PROTOCOL      |            | |
|        |           | | DST_IP           |            | |
|        |           | | SRC_IP           |            | |
|        |           | | L4_DST_PORT      |            | |
|        |           | | L4_SRC_PORT      |            | |
|        |           | | RDMA_BTH_OPCODE  |            | |
|        |           | | RDMA_BTH_DEST_QP |            | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| ECMP   | ipv6-rdma | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipv4      | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipv6      | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipnip     | +-------------------------------+ |
|        |           | | Hash Field        | Algorithm | |
|        |           | |-------------------+-----------| |
|        |           | | IP_PROTOCOL       | CRC       | |
|        |           | | DST_IP            |           | |
|        |           | | SRC_IP            |           | |
|        |           | | L4_DST_PORT       |           | |
|        |           | | L4_SRC_PORT       |           | |
|        |           | | INNER_DST_MAC     |           | |
|        |           | | INNER_SRC_MAC     |           | |
|        |           | | INNER_ETHERTYPE   |           | |
|        |           | | INNER_IP_PROTOCOL |           | |
|        |           | | INNER_DST_IP      |           | |
|        |           | | INNER_SRC_IP      |           | |
|        |           | | INNER_L4_DST_PORT |           | |
|        |           | | INNER_L4_SRC_PORT |           | |
|        |           | +-------------------+-----------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipv4-rdma | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
| LAG    | ipv6-rdma | +-----------------+-------------+ |
|        |           | | Hash Field      | Algorithm   | |
|        |           | |-----------------+-------------| |
|        |           | | N/A             | N/A         | |
|        |           | +------------------+------------+ |
+--------+-----------+-----------------------------------+
```

**The following command shows switch hash capabilities:**
```bash
root@sonic:/home/admin# show switch-hash capabilities
+--------+-----------------------------------------------------------+
| Hash   | Capabilities                                              |
+========+===========================================================+
| ECMP   | +-------------------+-------------+---------------------+ |
|        | | Hash Field        | Algorithm   | Pkt-type            | |
|        | |-------------------+-------------+---------------------| |
|        | | IN_PORT           | CRC         | IPV4                | |
|        | | DST_MAC           | XOR         | IPV6                | |
|        | | SRC_MAC           | RANDOM      | IPNIP               | |
|        | | ETHERTYPE         | CRC_32LO    | IPV4_RDMA           | |
|        | | VLAN_ID           | CRC_32HI    | IPV6_RDMA           | |
|        | | IP_PROTOCOL       | CRC_CCITT   |                     | |
|        | | DST_IP            | CRC_XOR     |                     | |
|        | | SRC_IP            |             |                     | |
|        | | L4_DST_PORT       |             |                     | |
|        | | L4_SRC_PORT       |             |                     | |
|        | | INNER_DST_MAC     |             |                     | |
|        | | INNER_SRC_MAC     |             |                     | |
|        | | INNER_ETHERTYPE   |             |                     | |
|        | | INNER_IP_PROTOCOL |             |                     | |
|        | | INNER_DST_IP      |             |                     | |
|        | | INNER_SRC_IP      |             |                     | |
|        | | INNER_L4_DST_PORT |             |                     | |
|        | | INNER_L4_SRC_PORT |             |                     | |
|        | | IPV6_FLOW_LABEL   |             |                     | |
|        | | RDMA_BTH_OPCODE   |             |                     | |
|        | | RDMA_BTH_DEST_QP  |             |                     | |
|        | +-------------------+-------------+---------------------+ |
+--------+-----------------------------------------------------------+
| LAG    | +-------------------+-------------+---------------------+ |
|        | | Hash Field        | Algorithm   | Pkt-type            | |
|        | |-------------------+-------------+---------------------| |
|        | | IN_PORT           | CRC         | IPV4                | |
|        | | DST_MAC           | XOR         | IPV6                | |
|        | | SRC_MAC           | RANDOM      | IPNIP               | |
|        | | ETHERTYPE         | CRC_32LO    | IPV4_RDMA           | |
|        | | VLAN_ID           | CRC_32HI    | IPV6_RDMA           | |
|        | | IP_PROTOCOL       | CRC_CCITT   |                     | |
|        | | DST_IP            | CRC_XOR     |                     | |
|        | | SRC_IP            |             |                     | |
|        | | L4_DST_PORT       |             |                     | |
|        | | L4_SRC_PORT       |             |                     | |
|        | | INNER_DST_MAC     |             |                     | |
|        | | INNER_SRC_MAC     |             |                     | |
|        | | INNER_ETHERTYPE   |             |                     | |
|        | | INNER_IP_PROTOCOL |             |                     | |
|        | | INNER_DST_IP      |             |                     | |
|        | | INNER_SRC_IP      |             |                     | |
|        | | INNER_L4_DST_PORT |             |                     | |
|        | | INNER_L4_SRC_PORT |             |                     | |
|        | | IPV6_FLOW_LABEL   |             |                     | |
|        | | RDMA_BTH_OPCODE   |             |                     | |
|        | | RDMA_BTH_DEST_QP  |             |                     | |
|        | +-------------------+-------------+---------------------+ |
+--------+-----------------------------------------------------------+
```

## 2.7 YANG model

Existing YANG model template `sonic-types.yang.j2` at `sonic-buildimage/src/sonic-yang-models/yang-templates`  
will be extended with a new common type.

**Skeleton code:**
```yang
    typedef hash-field {
        description "Represents native hash field";
        type enumeration {
            enum IN_PORT;
            enum DST_MAC;
            enum SRC_MAC;
            enum ETHERTYPE;
            enum VLAN_ID;
            enum IP_PROTOCOL;
            enum DST_IP;
            enum SRC_IP;
            enum L4_DST_PORT;
            enum L4_SRC_PORT;
            enum INNER_DST_MAC;
            enum INNER_SRC_MAC;
            enum INNER_ETHERTYPE;
            enum INNER_IP_PROTOCOL;
            enum INNER_DST_IP;
            enum INNER_DST_IPV4;
            enum INNER_DST_IPV6;
            enum INNER_SRC_IP;
            enum INNER_SRC_IPV4;
            enum INNER_SRC_IPV6;
            enum INNER_L4_DST_PORT;
            enum INNER_L4_SRC_PORT;
            enum IPV6_FLOW_LABEL;
            enum RDMA_BTH_OPCODE;
            enum RDMA_BTH_DEST_QP;                        
        }
    }

    typedef hash-algorithm {
        description "Represents hash algorithm";
        type enumeration {
            enum CRC;
            enum XOR;
            enum RANDOM;
            enum CRC_32LO;
            enum CRC_32HI;
            enum CRC_CCITT;
            enum CRC_XOR;
        }
    }
```

New YANG model `sonic-hash.yang` will be added to `sonic-buildimage/src/sonic-yang-models/yang-models`  
in order to extend existing data schema and provide support for GH.

**Skeleton code:**
```yang
module sonic-hash {

    yang-version 1.1;

    namespace "http://github.com/sonic-net/sonic-hash";
    prefix hash;

    import sonic-types {
        prefix stypes;
    }

    description "HASH YANG Module for SONiC OS";

    revision 2022-09-05 {
        description "First Revision";
    }

    typedef hash-field {
        description "Represents native hash field";
        type stypes:hash-field {
            enum IN_PORT;
            enum DST_MAC;
            enum SRC_MAC;
            enum ETHERTYPE;
            enum VLAN_ID;
            enum IP_PROTOCOL;
            enum DST_IP;
            enum SRC_IP;
            enum L4_DST_PORT;
            enum L4_SRC_PORT;
            enum INNER_DST_MAC;
            enum INNER_SRC_MAC;
            enum INNER_ETHERTYPE;
            enum INNER_IP_PROTOCOL;
            enum INNER_DST_IP;
            enum INNER_SRC_IP;
            enum INNER_L4_DST_PORT;
            enum INNER_L4_SRC_PORT;
            enum IPV6_FLOW_LABEL;
            enum RDMA_BTH_OPCODE;
            enum RDMA_BTH_DEST_QP;              
        }
    }

    container sonic-hash {

        container SWITCH_HASH {

            description "SWITCH_HASH part of config_db.json";

            container GLOBAL {

                leaf-list ecmp_hash {
                    description "Hash fields for hashing packets going through ECMP";
                    type hash:hash-field;
                }

                leaf-list ecmp_hash_ipv4 {
                    description "Hash fields for hashing ipv4 packets going through ECMP";
                    type hash:hash-field;
                }

                leaf-list ecmp_hash_ipv6 {
                    description "Hash fields for hashing ipv6 packets going through ECMP";
                    type hash:hash-field;
                }

                leaf-list ecmp_hash_ipnip {
                    description "Hash fields for hashing ipnip packets going through ECMP";
                    type hash:hash-field;
                }
				
                leaf-list ecmp_hash_ipv4_rdma {
                    description "Hash fields for hashing ipv4_rdma packets going through ECMP";
                    type hash:hash-field;
                }	

                leaf-list ecmp_hash_ipv6_rdma {
                    description "Hash fields for hashing ipv6_rdma packets going through ECMP";
                    type hash:hash-field;
                }

                leaf-list lag_hash  {
                    description "Hash fields for hashing packets going through LAG";
                    type hash:hash-field;
                }

                leaf-list lag_hash_ipv4 {
                    description "Hash fields for hashing ipv4 packets going through LAG";
                    type hash:hash-field;
                }

                leaf-list lag_hash_ipv6 {
                    description "Hash fields for hashing ipv6 packets going through LAG";
                    type hash:hash-field;
                }

                leaf-list lag_hash_ipnip {
                    description "Hash fields for hashing ipnip packets going through LAG";
                    type hash:hash-field;
                }
				
                leaf-list lag_hash_ipv4_rdma {
                    description "Hash fields for hashing ipv4_rdma packets going through LAG";
                    type hash:hash-field;
                }

                leaf-list lag_hash_ipv6_rdma {
                    description "Hash fields for hashing ipv6_rdma packets going through LAG";
                    type hash:hash-field;
                }                

                leaf ecmp_hash_algorithm {
                    description "Hash algorithm for hashing packets going through ECMP";
                    type stypes:hash-algorithm;
                }

                leaf lag_hash_algorithm {
                    description "Hash algorithm for hashing packets going through LAG";
                    type stypes:hash-algorithm;
                }

            }
            /* end of container GLOBAL */
        }
        /* end of container SWITCH_HASH */
    }
    /* end of container sonic-hash */
}
/* end of module sonic-hash */
```

## 2.8 Warm/Fast boot

No special handling is required

# 3 Test plan

## 3.1 Unit tests via VS

### 3.1.1 GH basic configuration test:
1. Verify ASIC DB object state after switch ECMP hash update
2. Verify ASIC DB object state after switch LAG hash update
3. Verify ASIC DB object state after switch ECMP hash algorithm update
4. Verify ASIC DB object state after switch LAG hash algorithm update

### 3.1.1 Packet type hash basic configuration test:
1. Verify ASIC DB object state after creating switch ECMP packet type hash
2. Verify ASIC DB object state after creating switch LAG packet type hash
3. Verify ASIC DB object state after updating switch ECMP packet type hash 
4. Verify ASIC DB object state after updating switch LAG packet type hash
5. Verify ASIC DB object state after deleting switch ECMP packet type hash
6. Verify ASIC DB object state after deleting switch LAG packet type hash

## 3.2 Data plane tests via PTF

1. [Generic Hash Test Plan](https://github.com/sonic-net/sonic-mgmt/pull/7524 "Test Plan")
1. [Generic Hash with Packet Type Test plan](https://github.com/sonic-net/sonic-mgmt/pull/21248 "Enhanced Test Plan")