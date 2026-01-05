# Add support for IPv6 Router Advertisement on VLAN Interfaces using OpenConfig YANG.

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
  * [4 Error Handling](#4-error-handling)
  * [5 Unit Test Cases](#5-unit-test-cases)
    * [5.1 Functional Test Cases](#51-functional-test-cases)
    * [5.2 Negative Test Cases](#52-negative-test-cases)
  * [6 References](#6-references)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
[Table 2: OpenConfig YANG to SONiC YANG Mapping](#table-2-openconfig-yang-to-sonic-yang-mapping)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 01/05/2026  | Anukul Verma          | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of IPv6 Router Advertisement parameters on VLAN interfaces in SONiC.

# Scope
- This document describes the high level design of configuration of IPv6 Router Advertisement on VLAN interfaces using OpenConfig models via REST & gNMI. 
- This does not cover the SONiC KLISH CLI.
- This covers only IPv6 Router Advertisement configuration on VLAN interfaces (routed-vlan).
- This does not support Router Advertisement configuration on Ethernet or PortChannel interfaces.
- Supported attributes in OpenConfig YANG tree:

<pre>
module: openconfig-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw oc-vlan:routed-vlan
           +--rw oc-ip:ipv6
              +--rw oc-ip:router-advertisement
              |  +--rw oc-ip:config
              |  |  +--rw oc-ip:suppress?       boolean
              |  |  +--rw oc-ip:managed?        boolean
              |  |  +--rw oc-ip:other-config?   boolean
              |  +--ro oc-ip:state
              |  |  +--ro oc-ip:suppress?       boolean
              |  |  +--ro oc-ip:managed?        boolean
              |  |  +--ro oc-ip:other-config?   boolean
              |  +--rw oc-ip:prefixes
              |     +--rw oc-ip:prefix* [prefix]
              |        +--rw oc-ip:prefix    -> ../config/prefix
              |        +--rw oc-ip:config
              |        |  +--rw oc-ip:prefix?                      oc-inet:ipv6-prefix
              |        |  +--rw oc-ip:disable-autoconfiguration?   boolean
              |        +--ro oc-ip:state
              |           +--ro oc-ip:prefix?                      oc-inet:ipv6-prefix
              |           +--ro oc-ip:disable-autoconfiguration?   boolean
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| IPv6                     | Internet Protocol version 6   |
| RA                       | Router Advertisement   |
| ND                       | Neighbor Discovery   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models for IPv6 Router Advertisement configuration.
2. Configure/Set, GET, and Delete IPv6 Router Advertisement parameters on VLAN interfaces.
3. Support configuration of suppress-ra flag to suppress router advertisements.
4. Support configuration of managed-config-flag (M-flag) for stateful DHCPv6.
5. Support configuration of other-config-flag (O-flag) for DHCPv6 other information.
6. Support configuration of per-prefix autoconfiguration settings.
7. Map OpenConfig router-advertisement model to SONiC VLAN_INTERFACE and VLAN_INTERFACE_ND_PREFIX tables.

### 1.1.2 Configuration and Management Requirements
The IPv6 Router Advertisement configurations can be done via REST and gNMI. The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists.

**Important Notes:**
- Router Advertisement is only supported on VLAN interfaces (routed-vlan).
- Attempting to configure router-advertisement on non-VLAN interfaces (Ethernet, PortChannel, Loopback) will result in an error.

### 1.1.3 Scalability Requirements
- Supports multiple VLAN interfaces with router-advertisement configuration.
- Supports multiple IPv6 prefixes per VLAN interface for ND prefix configuration.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports IPv6 Router Advertisement configurations via SONiC YANG models. This feature adds support for OpenConfig based YANG models using transformer based implementation in the Management Framework.

The implementation provides mapping between:
- OpenConfig router-advertisement config parameters → SONiC VLAN_INTERFACE table fields
- OpenConfig router-advertisement prefix parameters → SONiC VLAN_INTERFACE_ND_PREFIX table

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform PATCH, DELETE, POST, PUT, and GET operations on IPv6 Router Advertisement configuration paths.
2. gNMI client with support for capabilities, get and set operations based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

The implementation uses transformer functions in `translib/transformer/xfmr_intf.go` to map between OpenConfig and SONiC data models.

### 3.1.1 Mapping Details

#### Table 2: OpenConfig YANG to SONiC YANG Mapping

| OpenConfig Path | SONiC Table | SONiC Field | Transformer Function |
|----------------|-------------|-------------|---------------------|
| `/interfaces/interface[name=VlanX]/routed-vlan/ipv6/router-advertisement/config/suppress` | VLAN_INTERFACE | nd_suppress_ra | Direct field mapping |
| `/interfaces/interface[name=VlanX]/routed-vlan/ipv6/router-advertisement/config/managed` | VLAN_INTERFACE | nd_managed_config_flag | Direct field mapping |
| `/interfaces/interface[name=VlanX]/routed-vlan/ipv6/router-advertisement/config/other-config` | VLAN_INTERFACE | nd_other_config_flag | Direct field mapping |
| `/interfaces/interface[name=VlanX]/routed-vlan/ipv6/router-advertisement/prefixes/prefix[prefix=X]/config/prefix` | VLAN_INTERFACE_ND_PREFIX | Key (name\|prefix) | vlan_interface_nd_prefix_key_xfmr |
| `/interfaces/interface[name=VlanX]/routed-vlan/ipv6/router-advertisement/prefixes/prefix[prefix=X]/config/disable-autoconfiguration` | VLAN_INTERFACE_ND_PREFIX | disable_autoconfiguration | Direct field mapping |

**Key Transformers:**
- **YangToDb_vlan_interface_nd_prefix_key_xfmr**: Converts OpenConfig interface name and prefix into SONiC key format `"VlanX|prefix"`.
- **DbToYang_vlan_interface_nd_prefix_key_xfmr**: Converts SONiC key format back to OpenConfig structure with separate name and prefix fields.

Example Key Transformation:
```
OpenConfig: interface[name=Vlan100], prefix[prefix=2001:db8::/64]
SONiC Key:  "Vlan100|2001:db8::/64"
```

## 3.2 DB Changes

Changes are made in **frrcfgd** daemon to subscribe to the `VLAN_INTERFACE` and `VLAN_INTERFACE_ND_PREFIX` tables in CONFIG_DB and configure the corresponding IPv6 Neighbor Discovery CLIs in FRR (Free Range Routing).

### 3.2.1 CONFIG DB

The **sonic-vlan.yang** schema is updated to add router advertisement fields in the `VLAN_INTERFACE` table and introduce the new `VLAN_INTERFACE_ND_PREFIX` table.

**SONiC YANG Schema:**

```yang
module: sonic-vlan
  +--rw sonic-vlan
     +--rw VLAN
     |  +--rw VLAN_LIST* [name]
     |     +--rw name              string
     +--rw VLAN_INTERFACE
     |  +--rw VLAN_INTERFACE_LIST* [name]
     |  |  +--rw name                        -> /sonic-vlan/VLAN/VLAN_LIST/name
     |  |  +--rw nd_suppress_ra?             boolean
     |  |  +--rw nd_managed_config_flag?     boolean
     |  |  +--rw nd_other_config_flag?       boolean
     +--rw VLAN_INTERFACE_ND_PREFIX
        +--rw VLAN_INTERFACE_ND_PREFIX_LIST* [name prefix]
           +--rw name                         -> /sonic-vlan/VLAN/VLAN_LIST/name
           +--rw prefix                       inet:ipv6-prefix
           +--rw disable_autoconfiguration    boolean
```

**Notes:**
- The `VLAN_INTERFACE` table pre-exists in SONiC; three new leaves (`nd_suppress_ra`, `nd_managed_config_flag`, `nd_other_config_flag`) are added to support router advertisement configuration.
- The `VLAN_INTERFACE_ND_PREFIX` table is newly introduced to support per-prefix Neighbor Discovery configuration.

**CONFIG_DB Examples:**

**VLAN_INTERFACE Table:**
```
VLAN_INTERFACE|Vlan100
  "nd_managed_config_flag": "true"
  "nd_other_config_flag": "false"
  "nd_suppress_ra": "false"
  "NULL": "NULL"
```

**VLAN_INTERFACE_ND_PREFIX Table:**
```
VLAN_INTERFACE_ND_PREFIX|Vlan100|2001:db8::/64
  "disable_autoconfiguration": "true"
```

### 3.2.2 APP DB
There are no changes to APP DB schema definition for this feature.

### 3.2.3 STATE DB
There are no changes to STATE DB schema definition for this feature.

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models
The implementation uses standard OpenConfig YANG models:
- **openconfig-interfaces.yang**: Main interface model
- **openconfig-if-ip.yang**: IPv6 and router-advertisement definitions
- **openconfig-vlan.yang**: VLAN interface (routed-vlan) augmentation

Annotations are defined in:
- **openconfig-interfaces-annot.yang**: Contains sonic-ext annotations for field mapping

### 3.3.2 REST API Support

#### 3.3.2.1 GET
Supported at all levels (container, list, and leaf).

**Example 1: GET router-advertisement config**
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:config": {
    "suppress": false,
    "managed": true,
    "other-config": false
  }
}
```

**Example 2: GET router-advertisement state**
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/state" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:state": {
    "managed": true,
    "other-config": false
  }
}
```

**Example 3: GET specific field - managed flag**
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config/managed" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:managed": true
}
```

**Example 4: GET all prefixes**
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:prefixes": {
    "prefix": [
      {
        "prefix": "2001:db8::/64",
        "config": {
          "prefix": "2001:db8::/64",
          "disable-autoconfiguration": true
        },
        "state": {
          "prefix": "2001:db8::/64",
          "disable-autoconfiguration": true
        }
      },
      {
        "prefix": "2001:db8:1::/64",
        "config": {
          "prefix": "2001:db8:1::/64",
          "disable-autoconfiguration": false
        },
        "state": {
          "prefix": "2001:db8:1::/64",
          "disable-autoconfiguration": false
        }
      }
    ]
  }
}
```

**Example 5: GET specific prefix**
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes/prefix=2001:db8::/64" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:prefix": [
    {
      "prefix": "2001:db8::/64",
      "config": {
        "prefix": "2001:db8::/64",
        "disable-autoconfiguration": true
      },
      "state": {
        "prefix": "2001:db8::/64",
        "disable-autoconfiguration": true
      }
    }
  ]
}
```

#### 3.3.2.2 POST
Used to create new configuration. Supported at container and leaf levels.

**Example 1: POST router-advertisement config with all parameters**
```bash
curl -X POST -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"suppress": false, "managed": true, "other-config": false}'
```

**Example 2: POST a new prefix**
```bash
curl -X POST -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "prefix": [
      {
        "prefix": "2001:db8::/64",
        "config": {
          "prefix": "2001:db8::/64",
          "disable-autoconfiguration": true
        }
      }
    ]
  }'
```

Verify with GET:
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" -H "accept: application/yang-data+json"
```

#### 3.3.2.3 PUT
Used to replace entire configuration. Supported at container and leaf levels.

**Example 1: PUT router-advertisement config**
```bash
curl -X PUT -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "config": {
      "managed": true,
      "other-config": true
    }
  }'
```

**Example 2: PUT specific prefix config**
```bash
curl -X PUT -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes/prefix=2001:db8::/64/config" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "config": {
      "prefix": "2001:db8::/64",
      "disable-autoconfiguration": false
    }
  }'
```

#### 3.3.2.4 PATCH
Used to modify specific fields without replacing entire configuration. Supported at all levels.

**Example 1: PATCH managed flag**
```bash
curl -X PATCH -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config/managed" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"managed": false}'
```

**Example 2: PATCH other-config flag**
```bash
curl -X PATCH -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config/other-config" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"other-config": true}'
```

**Example 3: PATCH disable-autoconfiguration for a specific prefix**
```bash
curl -X PATCH -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes/prefix=2001:db8::/64/config/disable-autoconfiguration" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"disable-autoconfiguration": false}'
```

Verify with GET:
```bash
curl -X GET -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" -H "accept: application/yang-data+json"
```

Response:
```json
{
  "openconfig-if-ip:config": {
    "suppress": false,
    "managed": false,
    "other-config": true
  }
}
```

**Example 4: PATCH suppress flag**
```bash
curl -X PATCH -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config/suppress" \
  -H "accept: */*" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"suppress": true}'
```

#### 3.3.2.5 DELETE
Supported at all levels.

**Example 1: DELETE specific prefix**
```bash
curl -X DELETE -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/prefixes/prefix=2001:db8::/64" \
  -H "accept: */*"
```

**Example 2: DELETE all router-advertisement config**
```bash
curl -X DELETE -k "https://192.168.1.1/restconf/data/openconfig-interfaces:interfaces/interface=Vlan100/routed-vlan/ipv6/router-advertisement/config" \
  -H "accept: */*"
```

**Note:** Deleting individual mandatory fields like `disable-autoconfiguration` from a prefix entry is not allowed and will return an error. You must delete the entire prefix entry instead.

### 3.3.3 gNMI Support

#### 3.3.3.1 GET

**Example 1: GET router-advertisement config**
```bash
gnmi_get -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config
```

Response:
```json
[
  {
    "source": "localhost:8080",
    "timestamp": 1736064000000000000,
    "time": "2025-01-05T12:00:00Z",
    "target": "localhost:8080",
    "updates": [
      {
        "Path": "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config",
        "values": {
          "openconfig-interfaces:interfaces/interface/routed-vlan/ipv6/router-advertisement/config": {
            "openconfig-if-ip:config": {
              "suppress": false,
              "managed": true,
              "other-config": false
            }
          }
        }
      }
    ]
  }
]
```

**Example 2: GET specific managed flag**
```bash
gnmi_get -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config/managed
```

Response:
```json
[
  {
    "source": "localhost:8080",
    "timestamp": 1736064000000000000,
    "time": "2025-01-05T12:00:00Z",
    "target": "localhost:8080",
    "updates": [
      {
        "Path": "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config/managed",
        "values": {
          "openconfig-interfaces:interfaces/interface/routed-vlan/ipv6/router-advertisement/config/managed": {
            "openconfig-if-ip:managed": true
          }
        }
      }
    ]
  }
]
```

**Example 3: GET all prefixes**
```bash
gnmi_get -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes
```

Response:
```json
[
  {
    "source": "localhost:8080",
    "timestamp": 1736064000000000000,
    "time": "2025-01-05T12:00:00Z",
    "target": "localhost:8080",
    "updates": [
      {
        "Path": "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes",
        "values": {
          "openconfig-interfaces:interfaces/interface/routed-vlan/ipv6/router-advertisement/prefixes": {
            "openconfig-if-ip:prefixes": {
              "prefix": [
                {
                  "prefix": "2001:db8::/64",
                  "config": {
                    "prefix": "2001:db8::/64",
                    "disable-autoconfiguration": true
                  },
                  "state": {
                    "prefix": "2001:db8::/64",
                    "disable-autoconfiguration": true
                  }
                }
              ]
            }
          }
        }
      }
    ]
  }
]
```

#### 3.3.3.2 SET

**Example 1: SET router-advertisement config**
```bash
# Create radv_config.json:
{
  "openconfig-if-ip:config": {
    "suppress": false,
    "managed": true,
    "other-config": false
  }
}

gnmi_set -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath_target OC-YANG \
  -update /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config:@/tmp/radv_config.json
```

Response:
```json
[
  {
    "source": "localhost:8080",
    "timestamp": 1736064000000000000,
    "time": "2025-01-05T12:00:00Z",
    "target": "localhost:8080",
    "results": [
      {
        "operation": "UPDATE",
        "path": "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config"
      }
    ]
  }
]
```

**Example 2: SET prefix**
```bash
# Create prefix_config.json:
{
  "openconfig-if-ip:prefix": [
    {
      "prefix": "2001:db8::/64",
      "config": {
        "prefix": "2001:db8::/64",
        "disable-autoconfiguration": true
      }
    }
  ]
}

gnmi_set -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath_target OC-YANG \
  -update /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes:@/tmp/prefix_config.json
```

**Example 3: SET managed flag only**
```bash
# Create managed_flag.json:
{
  "openconfig-if-ip:managed": false
}

gnmi_set -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath_target OC-YANG \
  -update /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config/managed:@/tmp/managed_flag.json
```

Verify with GET:
```bash
gnmi_get -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config
```

#### 3.3.3.3 DELETE

**Example 1: DELETE specific prefix**
```bash
gnmi_set -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath_target OC-YANG \
  -delete /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes/prefix[prefix=2001:db8::/64]
```

Response:
```json
[
  {
    "source": "localhost:8080",
    "timestamp": 1736064000000000000,
    "time": "2025-01-05T12:00:00Z",
    "target": "localhost:8080",
    "results": [
      {
        "operation": "DELETE",
        "path": "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes/prefix[prefix=2001:db8::/64]"
      }
    ]
  }
]
```

**Example 2: DELETE all router-advertisement config**
```bash
gnmi_set -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath_target OC-YANG \
  -delete /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config
```

Verify deletion with GET:
```bash
gnmi_get -insecure -logtostderr -username admin -password password \
  -target_addr localhost:8080 \
  -xpath /openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config
```

#### 3.3.3.4 SUBSCRIBE

gNMI subscription is supported for monitoring configuration changes on router-advertisement parameters.

**Example 1: Subscribe to managed flag changes**
```bash
gnmic -a localhost:8080 -u admin -p password --insecure --target OC-YANG \
  sub --path "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config/managed"
```

Response:
```json
{
  "source": "localhost:8080",
  "subscription-name": "default-1767604549",
  "timestamp": 1767604550005727146,
  "time": "2026-01-05T14:45:50.005727146+05:30",
  "prefix": "openconfig-interfaces:interfaces/interface[name=Vlan100]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/router-advertisement/config",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "managed",
      "values": {
        "managed": true
      }
    }
  ]
}
{
  "sync-response": true
}
```

**Example 2: Subscribe to all router-advertisement config changes**
```bash
gnmic -a localhost:8080 -u admin -p password --insecure --target OC-YANG \
  sub --path "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/config"
```

**Example 3: Subscribe to prefix configuration changes**
```bash
gnmic -a localhost:8080 -u admin -p password --insecure --target OC-YANG \
  sub --path "openconfig-interfaces:interfaces/interface[name=Vlan100]/routed-vlan/ipv6/router-advertisement/prefixes"
```

# 4 Error Handling

The implementation handles various error scenarios and returns appropriate error responses:

## 4.1 VLAN Not Configured
Attempting to configure router-advertisement on a non-existent VLAN interface will return an error indicating the resource was not found.

## 4.2 Non-VLAN Interface
Attempting to configure router-advertisement on non-VLAN interfaces (Ethernet, PortChannel, Loopback) will return an error indicating an invalid interface name.

## 4.3 Mandatory Field Deletion
Attempting to delete a mandatory field (such as `disable-autoconfiguration`) from a prefix entry will return an error. The entire prefix entry must be deleted instead.

## 4.4 Invalid IPv6 Prefix Format
Providing an invalid IPv6 prefix format will return an error indicating the prefix format is invalid.



# 5 Unit Test Cases

Comprehensive test cases are available in `translib/transformer/xfmr_vlan_radv_test.go`.

## 5.1 Functional Test Cases

### 5.1.1 Router Advertisement Configuration Tests

- POST router-advertisement config with suppress=false, managed=true, other-config=false
- GET router-advertisement config
- PATCH router-advertisement config to modify managed flag
- PUT router-advertisement config to replace all values
- DELETE router-advertisement config
- PATCH suppress flag and verify storage
- PATCH managed flag to false and verify storage

### 5.1.2 Prefix Configuration Tests

- POST prefix with disable-autoconfiguration=true
- GET all prefixes
- GET specific prefix
- POST prefix with disable-autoconfiguration=false
- PATCH disable-autoconfiguration for existing prefix
- DELETE specific prefix
- Configure multiple prefixes on same VLAN
- PUT prefix config to replace settings

### 5.1.3 Integration Tests

- Configure router-advertisement and multiple prefixes together
- Delete one prefix while others remain
- Configure router-advertisement on multiple VLANs
- Modify router-advertisement config without affecting prefixes
- GET entire router-advertisement container

## 5.2 Negative Test Cases

- Configure router-advertisement on non-existent VLAN
- Configure router-advertisement on Ethernet interface
- Configure router-advertisement on PortChannel interface
- Configure router-advertisement on Loopback interface
- DELETE disable-autoconfiguration field directly
- DELETE non-existing prefix
- POST prefix with invalid IPv6 prefix format
- Configure prefix without creating VLAN_INTERFACE entry first
- POST duplicate prefix

### 5.2.1 CVL Validation Tests

- Validate boolean field values (true/false only)
- Validate prefix format (must be valid IPv6 prefix)
- Validate VLAN interface name format
- Validate mandatory fields are present

# 6 References

1. [OpenConfig Interfaces YANG Model](https://github.com/openconfig/public/tree/master/release/models/interfaces)
2. [OpenConfig IP YANG Model](https://github.com/openconfig/public/tree/master/release/models/interfaces)
3. [SONiC Management Framework HLD](https://github.com/project-arlo/SONiC/blob/master/doc/mgmt/Management%20Framework.md)
4. [RFC 4861 - Neighbor Discovery for IP version 6 (IPv6)](https://tools.ietf.org/html/rfc4861)
5. [RFC 4862 - IPv6 Stateless Address Autoconfiguration](https://tools.ietf.org/html/rfc4862)
