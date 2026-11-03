# OpenConfig Support for L3 SubInterface

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
      * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
      * [1.1.3 Scalability Requirements](#113-scalability-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)
      * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
      * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
  * [5 Enhancements over OpenConfig_Interfaces.md](#5-enhancements-over-openconfig_interfacesmd)
  * [6 Error Handling](#6-error-handling)
  * [7 Unit Test Cases](#7-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
  * [Table 1: Abbreviations](#table-1-abbreviations)
  * [Table 2: CONFIG_DB VLAN_SUB_INTERFACE / INTERFACE Mapping](#table-2-config_db-vlan_sub_interface--interface-mapping)
  * [Table 3: OpenConfig to SONiC Mapping Table](#table-3-openconfig-to-sonic-mapping-table)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 07/22/2026  | Soumya Gargari        | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of L3 subinterfaces (VLAN-tagged subinterfaces with IPv4/IPv6 addresses) in SONiC.

# Scope
- This document describes the high level design of L3 subinterface configuration using OpenConfig models via REST and gNMI.
- This does not cover the SONiC KLISH CLI or legacy SONiC YANG-only configuration paths.
- Configuration is supported under:
  `/interfaces/interface/subinterfaces/subinterface`
- Subinterfaces and addresses are mapped to the existing CONFIG_DB `VLAN_SUB_INTERFACE` and `INTERFACE` tables; no new DB schema is introduced.
- **Subinterface index determines table mapping**: index 0 maps to the main `INTERFACE` table; index > 0 maps to `VLAN_SUB_INTERFACE` for VLAN tagging and `INTERFACE` for L3 addresses.
- Supported attributes in OpenConfig YANG tree:

<pre>
module: openconfig-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw subinterfaces
           +--rw subinterface* [index]
              +--rw index     -> ../config/index
              +--rw config
              |  +--rw index?   uint32
              +--ro state
              |  +--ro index?   uint32
              +--rw openconfig-vlan:vlan
              |  +--rw config
              |  |  +--rw vlan-id?   oc-vlan-types:vlan-id
              |  +--ro state
              |     +--ro vlan-id?   oc-vlan-types:vlan-id
              +--rw openconfig-if-ip:ipv4
              |  +--rw addresses
              |     +--rw address* [ip]
              |        +--rw ip       -> ../config/ip
              |        +--rw config
              |        |  +--rw ip?              oc-inet:ipv4-address
              |        |  +--rw prefix-length?   uint8
              |        +--ro state
              |           +--ro ip?              oc-inet:ipv4-address
              |           +--ro prefix-length?   uint8
              +--rw openconfig-if-ip:ipv6
                 +--rw addresses
                    +--rw address* [ip]
                       +--rw ip       -> ../config/ip
                       +--rw config
                       |  +--rw ip?              oc-inet:ipv6-address
                       |  +--rw prefix-length?   uint8
                       +--ro state
                          +--ro ip?              oc-inet:ipv6-address
                          +--ro prefix-length?   uint8
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format |
| REST                     | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface |
| VLAN                     | Virtual Local Area Network |
| L3                       | Layer 3 (Network Layer) |
| IEEE 802.1Q              | IEEE standard for VLAN tagging |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide OpenConfig YANG support for L3 subinterfaces with VLAN tagging.
2. Support create, read, update, and delete of subinterfaces with VLAN ID and IPv4/IPv6 addresses via REST and gNMI.
3. Support index-based routing: index 0 uses main `INTERFACE` table, index > 0 uses `VLAN_SUB_INTERFACE` table.
4. Validate parent interface existence before subinterface creation.
5. Support multiple IPv4 and IPv6 addresses per subinterface.

### 1.1.2 Configuration and Management Requirements
L3 subinterface configuration is done via REST and gNMI. Invalid configurations return an error. No new management methods are introduced beyond the Management Framework.

### 1.1.3 Scalability Requirements
Subinterface scale follows the existing CONFIG_DB `VLAN_SUB_INTERFACE` / `INTERFACE` schema and platform limits for the number of subinterfaces per port.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC supports VLAN subinterfaces through native CONFIG_DB. This feature adds OpenConfig `interfaces/interface/subinterfaces/subinterface` support using a transformer-based implementation in *sonic-mgmt-common*.

### 1.2.2 Container
The feature is delivered in the *Management Framework* container (REST server and gNMI in *sonic-mgmt-common*).

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST clients performing GET, PUT, PATCH, POST, and DELETE on supported subinterface YANG paths.
2. gNMI clients using get, set, and delete on the same OpenConfig paths.

# 3 Design
## 3.1 Overview
This HLD is aligned with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md).

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition. OpenConfig subinterfaces map to existing `VLAN_SUB_INTERFACE` and `INTERFACE` tables.

#### Table 2: CONFIG_DB VLAN_SUB_INTERFACE / INTERFACE Mapping
| CONFIG_DB item | Value / format |
|----------------|----------------|
| Table `VLAN_SUB_INTERFACE` | One row per VLAN subinterface (index > 0) |
| Key `VLAN_SUB_INTERFACE` | `{parent_interface}.{index}` e.g. `Ethernet4.100` |
| Field `vlan` | VLAN ID (e.g. `100`) |
| Table `INTERFACE` | One row per L3 address on any interface |
| Key `INTERFACE` | `{interface_name}\|{ip_address}/{prefix_length}` e.g. `Ethernet4\|1.1.0.124/32` |
| Field `family` | `IPv6` for IPv6 addresses; omitted / `NULL` for IPv4 |

Example:

```
VLAN_SUB_INTERFACE|Ethernet4.100
  vlan: 100

INTERFACE|Ethernet4|1.1.0.124/32
  NULL: NULL

INTERFACE|Ethernet8|2001:db8::1/64
  family: IPv6
```

### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
- openconfig-interfaces.yang
- openconfig-if-ip.yang
- openconfig-vlan.yang

### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at container, list, and leaf levels.

Sample GET on a subinterface:
```
curl -X GET -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100" -H "accept: application/yang-data+json"
```

Sample GET on VLAN state:
```
curl -X GET -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100/openconfig-vlan:vlan/state" -H "accept: application/yang-data+json"
```

#### 3.3.2.2 PUT
Supported. PUT on a subinterface replaces the targeted resource per RESTCONF rules.

Sample PUT to update VLAN ID:
```
curl -X PUT -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100/openconfig-vlan:vlan/config/vlan-id" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-vlan:vlan-id\":150}"
```

#### 3.3.2.3 POST
POST creates subinterfaces or merges addresses into an existing subinterface.

Sample POST to create a subinterface with VLAN and IPv4 address:
```
curl -X POST -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d '{
  "openconfig-interfaces:subinterface": [{
    "index": 100,
    "config": {"index": 100},
    "openconfig-vlan:vlan": {
      "config": {"vlan-id": 100}
    },
    "openconfig-if-ip:ipv4": {
      "addresses": {
        "address": [{
          "ip": "1.1.0.124",
          "config": {"ip": "1.1.0.124", "prefix-length": 32}
        }]
      }
    }
  }]
}'
```

Sample POST to create a subinterface with IPv6 address:
```
curl -X POST -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet8/subinterfaces" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d '{
  "openconfig-interfaces:subinterface": [{
    "index": 200,
    "config": {"index": 200},
    "openconfig-vlan:vlan": {
      "config": {"vlan-id": 200}
    },
    "openconfig-if-ip:ipv6": {
      "addresses": {
        "address": [{
          "ip": "2001:db8::1",
          "config": {"ip": "2001:db8::1", "prefix-length": 64}
        }]
      }
    }
  }]
}'
```

#### 3.3.2.4 PATCH
Supported at leaf level (e.g. VLAN ID, IP address prefix-length).

Sample PATCH to update VLAN ID:
```
curl -X PATCH -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100/openconfig-vlan:vlan/config/vlan-id" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-vlan:vlan-id\":150}"
```

#### 3.3.2.5 DELETE
Supported at subinterface, address, and VLAN configuration levels.

Delete an IPv4 address:
```
curl -X DELETE -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100/openconfig-if-ip:ipv4/addresses/address=1.1.0.124" -H "accept: */*"
```

Delete VLAN configuration:
```
curl -X DELETE -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100/openconfig-vlan:vlan/config/vlan-id" -H "accept: */*"
```

Delete entire subinterface:
```
curl -X DELETE -k "https://192.168.1.1:8080/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet4/subinterfaces/subinterface=100" -H "accept: */*"
```

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf get --path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]"
```

Leaf GET example (`vlan-id`):
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf get --path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]/vlan/state/vlan-id"
```

#### 3.3.3.2 SET
Create subinterface with VLAN and IPv4 address:
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf set --update-path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]" --update-value '{
  "config": {"index": 100},
  "openconfig-vlan:vlan": {
    "config": {"vlan-id": 100}
  },
  "openconfig-if-ip:ipv4": {
    "addresses": {
      "address": [{
        "ip": "1.1.0.124",
        "config": {"ip": "1.1.0.124", "prefix-length": 32}
      }]
    }
  }
}'
```

#### 3.3.3.3 DELETE
Delete a subinterface:
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf set --delete "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]"
```

#### 3.3.3.4 SUBSCRIBE
On-change subscription on subinterfaces:
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf sub --path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces" --stream-mode on-change
```

Sample subscription (periodic sample):
```
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure --target OC-YANG -e json_ietf sub --path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces" --stream-mode sample --sample-interval 30s
```

# 4 OpenConfig to SONiC Mapping Table
Mapping attributes between OpenConfig YANG and CONFIG_DB `VLAN_SUB_INTERFACE` / `INTERFACE`:

#### Table 3: OpenConfig to SONiC Mapping Table

**Database tables:** `VLAN_SUB_INTERFACE`, `INTERFACE`
**Key patterns:** `VLAN_SUB_INTERFACE|{parent}.{index}`; `INTERFACE|{interface_name}|{ip}/{prefix-length}`

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/interfaces/interface/subinterfaces/subinterface/config/index` | VLAN_SUB_INTERFACE | Key component `{index}` | Index > 0 only |
| `subinterface/vlan/config/vlan-id` | VLAN_SUB_INTERFACE | vlan | VLAN ID (1–4094) |
| `subinterface/ipv4/addresses/address/config/ip` | INTERFACE | Key component `{ip}` | |
| `subinterface/ipv4/addresses/address/config/prefix-length` | INTERFACE | Key component `{prefix-length}` | Combined as `{ip}/{prefix-length}` |
| `subinterface/ipv6/addresses/address/config/ip` | INTERFACE | Key component `{ip}` | |
| `subinterface/ipv6/addresses/address/config/prefix-length` | INTERFACE | Key component `{prefix-length}` | Combined as `{ip}/{prefix-length}` |

Translation Notes:
1. **Index-based table mapping**: Index 0 maps to the main `INTERFACE` table. Index > 0 creates an entry in `VLAN_SUB_INTERFACE` with key `{parent_interface}.{index}`.
2. **Parent interface validation**: The parent interface must exist in the `PORT` table before a subinterface can be created.
3. **VLAN ID range**: Must be between 1–4094 per IEEE 802.1Q.
4. **IP address format**: Valid IPv4 or IPv6 address with proper prefix length.
5. **Duplicate IP detection**: An IP address already assigned to an interface is rejected.
6. **Dependency protection**: A parent interface with active subinterfaces cannot be deleted.

Representative errors (non-exhaustive):

| Condition | Error (representative) |
|-----------|-------------------------|
| Parent interface missing | `Parent interface Ethernet4 does not exist` |
| Invalid VLAN ID | `Invalid VLAN ID: must be between 1-4094` |
| Duplicate IP address | `IP address 1.1.0.124/32 already exists on interface Ethernet4` |
| Invalid subinterface index | `Invalid subinterface index: must be greater than 0 for VLAN subinterfaces` |

# 5 Enhancements over OpenConfig_Interfaces.md

The existing [OpenConfig_Interfaces.md](OpenConfig_Interfaces.md) provides subinterface support only at **index 0**, which maps directly to the base `INTERFACE` table. This HLD (`Openconfig_L3SubInterface.md`) extends that foundation with the following enhancements:

| # | Area | OpenConfig_Interfaces.md (index 0 only) | Openconfig_L3SubInterface.md (this HLD) |
|:-:|------|----------------------------------------|----------------------------------------|
| 1 | **Subinterface index range** | Only index 0 is supported | Index 0 **and** index > 0 are supported |
| 2 | **VLAN tagging** | No VLAN tagging; index 0 represents the untagged parent interface | Index > 0 creates a VLAN-tagged subinterface with configurable `vlan-id` (IEEE 802.1Q) |
| 3 | **DB table mapping** | All operations use the `INTERFACE` table | Index 0 → `INTERFACE` table; index > 0 → `VLAN_SUB_INTERFACE` table (key `{parent}.{index}`) with addresses under `VLAN_SUB_INTERFACE|{parent}.{index}|{ip}/{prefix}` |
| 4 | **VLAN configuration** | `openconfig-vlan:vlan/config/vlan-id` not applicable | Full CRUD on `vlan-id` per subinterface; stored as `vlan` field in `VLAN_SUB_INTERFACE` |
| 5 | **Multiple subinterfaces per parent** | Single subinterface (index 0) per physical interface | Multiple subinterfaces (e.g. index 100, 200, 300) on the same parent interface |
| 6 | **Multiple IP addresses per subinterface** | Single or limited address on the base interface | Multiple IPv4 and IPv6 addresses per subinterface |
| 7 | **GET all subinterfaces** | Returns only index 0 data | Returns index 0 **plus** all VLAN subinterfaces with their VLAN IDs and addresses |
| 8 | **Granular DELETE** | Delete address or base interface config | Delete individual addresses, VLAN config leaf, or entire subinterface (cascading removal of all associated DB rows) |
| 9 | **Parent interface validation** | Not explicitly required (index 0 is the interface itself) | Parent interface must exist in `PORT` table before a subinterface can be created |
| 10 | **VLAN ID validation** | Not applicable | VLAN ID must be 1–4094; invalid values are rejected |

### Summary
`OpenConfig_Interfaces.md` remains the baseline for index-0 (untagged) interface operations. `Openconfig_L3SubInterface.md` builds on top of it to deliver full L3 VLAN subinterface lifecycle management for index > 0, including VLAN tagging, multi-address support, and fine-grained CRUD operations across both `VLAN_SUB_INTERFACE` and `INTERFACE` tables.

# 6 Error Handling
Invalid configurations and unsupported operations report an error with a descriptive message (see §4 Translation Notes).

# 7 Unit Test Cases
## 6.1 Functional Test Cases
1. Create, verify, and delete subinterfaces with VLAN ID using POST, PUT, PATCH, GET, and DELETE via REST/gNMI.
2. Verify IPv4 and IPv6 address assignment on subinterfaces.
3. Verify index 0 maps to `INTERFACE` table and index > 0 maps to `VLAN_SUB_INTERFACE` table.
4. Verify multiple addresses per subinterface.
5. Verify VLAN ID update via PATCH.
6. Verify deleting an entire subinterface removes both `VLAN_SUB_INTERFACE` and associated `INTERFACE` address rows.
7. Verify GET on VLAN state returns correct `vlan-id`.

## 6.2 Negative Test Cases
1. Verify creating a subinterface on a non-existent parent interface is rejected.
2. Verify invalid VLAN ID (0, 4095, negative) is rejected.
3. Verify duplicate IP address assignment is rejected.
4. Verify invalid subinterface index (negative values) is rejected.
5. Verify deleting a parent interface with active subinterfaces is rejected.
6. Verify invalid IP address format is rejected.
7. Verify invalid prefix length is rejected.