# L3 SubInterface Implementation High-Level Design

## Revision History

| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 12/03/2025  | Soumya Gargari        | Initial version                   |

## Table of Contents

1. [Overview](#overview)
2. [Feature Requirements](#feature-requirements)
3. [Database Schema](#database-schema)
4. [YANG Model Mapping](#yang-model-mapping)
5. [API Examples](#api-examples)
6. [Error Handling](#error-handling)
7. [Performance and Scaling](#performance-and-scaling)
8. [References](#references)

## Overview

This document describes the implementation of L3 SubInterface functionality in SONiC using OpenConfig YANG models. The feature enables configuration of VLAN-tagged subinterfaces with IPv4/IPv6 addresses through gNMI/REST APIs.

### Key Features

- **VLAN SubInterface Creation**: Support for VLAN-tagged subinterfaces with index > 0
- **L3 Address Configuration**: IPv4 and IPv6 address assignment on subinterfaces
- **Database Integration**: Mapping to SONiC `VLAN_SUB_INTERFACE` and `INTERFACE` tables
- **CRUD Operations**: Complete support for CREATE, READ, UPDATE, DELETE operations
- **Index-based Logic**: Different behavior for index 0 vs index > 0

## Feature Requirements

### Functional Requirements

1. **SubInterface Creation**
   - Create VLAN subinterfaces with configurable index values
   - Support VLAN ID assignment to subinterfaces
   - Handle parent interface dependency validation

2. **L3 Address Management**
   - Configure IPv4 addresses with prefix length
   - Configure IPv6 addresses with prefix length
   - Support multiple addresses per subinterface

3. **Database Mapping**
   - Map to `VLAN_SUB_INTERFACE` table for index > 0
   - Map to `INTERFACE` table for L3 addresses
   - Maintain proper key formatting and relationships

4. **API Support**
   - gNMI SET/GET/DELETE operations
   - REST API PATCH/PUT/POST/DELETE operations
   - Proper error handling and validation

### Non-Functional Requirements

- **Performance**: Efficient handling of multiple subinterfaces
- **Scalability**: Support for large numbers of subinterfaces per port
- **Reliability**: Consistent database state management
- **Maintainability**: Clean transformer code with proper error handling

## Architecture and Design

The L3 SubInterface feature follows SONiC's standard management architecture, utilizing OpenConfig YANG models for northbound API compatibility and mapping to SONiC native database schema. The implementation supports VLAN-tagged subinterfaces with configurable index values and proper L3 address assignment.

### Core Logic

- **Index-based Behavior**: Different table mapping based on subinterface index
  - Index 0: Uses main `INTERFACE` table
  - Index > 0: Uses `VLAN_SUB_INTERFACE` table for VLAN tagging
- **Database Integration**: Seamless mapping to SONiC CONFIG_DB tables
- **Address Family Support**: Both IPv4 and IPv6 address configuration
- **Dependency Management**: Proper validation of parent interface existence

## Database Schema

### VLAN_SUB_INTERFACE Table

**Purpose**: Stores VLAN subinterface configuration for index > 0

**Key Format**: `{interface_name}.{index}`

**Example Keys**:
```
VLAN_SUB_INTERFACE|Ethernet4.100
VLAN_SUB_INTERFACE|Ethernet8.200
```

**Fields**:
- `vlan`: VLAN ID for the subinterface
- `NULL`: Placeholder when no VLAN is configured

**Example Data**:
```json
{
  "VLAN_SUB_INTERFACE": {
    "Ethernet4.100": {
      "vlan": "100"
    },
    "Ethernet8.200": {
      "vlan": "200"
    }
  }
}
```

### INTERFACE Table

**Purpose**: Stores L3 address configuration

**Key Format**: `{interface_name}|{ip_address}/{prefix_length}`

**Example Keys**:
```
INTERFACE|Ethernet4|1.1.0.124/32
INTERFACE|Ethernet8|2001:db8::1/64
```

**Fields**:
- `family`: Address family (IPv4 or IPv6)

**Example Data**:
```json
{
  "INTERFACE": {
    "Ethernet4|1.1.0.124/32": {
      "NULL": "NULL"
    },
    "Ethernet8|2001:db8::1/64": {
      "family": "IPv6"
    }
  }
}
```

## YANG Model Mapping

### OpenConfig Paths

#### SubInterface Configuration
```
/openconfig-interfaces:interfaces/interface[name=<INTF>]/subinterfaces/subinterface[index=<INDEX>]
```

#### VLAN Configuration
```
/openconfig-interfaces:interfaces/interface[name=<INTF>]/subinterfaces/subinterface[index=<INDEX>]/vlan/config/vlan-id
```

#### IPv4 Address Configuration
```
/openconfig-interfaces:interfaces/interface[name=<INTF>]/subinterfaces/subinterface[index=<INDEX>]/ipv4/addresses/address[ip=<IP>]/config
```

#### IPv6 Address Configuration
```
/openconfig-interfaces:interfaces/interface[name=<INTF>]/subinterfaces/subinterface[index=<INDEX>]/ipv6/addresses/address[ip=<IP>]/config
```

## Transformer Implementation

The L3 SubInterface feature utilizes SONiC's transformer framework to map OpenConfig YANG model to native SONiC database schema. The implementation includes proper validation, database key generation, and atomic transaction handling.

## API Examples

### Create SubInterface with VLAN

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --update-path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]" \
  --update-file subintf.json
```

**JSON Payload** (`subintf.json`):
```json
{
  "openconfig-interfaces:subinterface": [
    {
      "index": 100,
      "config": {
        "index": 100
      },
      "vlan": {
        "config": {
          "vlan-id": 100
        }
      },
      "ipv4": {
        "addresses": {
          "address": [
            {
              "ip": "1.1.0.124",
              "config": {
                "ip": "1.1.0.124",
                "prefix-length": 32
              }
            }
          ]
        }
      }
    }
  ]
}
```

**Expected Database Result**:
```bash
redis-cli -n 4 HGETALL "VLAN_SUB_INTERFACE|Ethernet4.100"
1) "vlan"
2) "100"

redis-cli -n 4 HGETALL "INTERFACE|Ethernet4|1.1.0.124/32"
1) "NULL"
2) "NULL"
```

### Create IPv6 SubInterface

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --update-path "/openconfig-interfaces:interfaces/interface[name=Ethernet8]/subinterfaces/subinterface[index=200]" \
  --update-file subintf_ipv6.json
```

**JSON Payload** (`subintf_ipv6.json`):
```json
{
  "openconfig-interfaces:subinterface": [
    {
      "index": 200,
      "config": {
        "index": 200
      },
      "vlan": {
        "config": {
          "vlan-id": 200
        }
      },
      "ipv6": {
        "addresses": {
          "address": [
            {
              "ip": "2001:db8::1",
              "config": {
                "ip": "2001:db8::1", 
                "prefix-length": 64
              }
            }
          ]
        }
      }
    }
  ]
}
```

**Expected Database Result**:
```bash
redis-cli -n 4 HGETALL "VLAN_SUB_INTERFACE|Ethernet8.200"
1) "vlan"
2) "200"

redis-cli -n 4 HGETALL "INTERFACE|Ethernet8|2001:db8::1/64"
1) "family"
2) "IPv6"
```

### Read SubInterface Configuration

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure get \
  --path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]/vlan/state"
```

**Expected Response**:
```json
{
  "openconfig-vlan:state": {
    "vlan-id": 100
  }
}
```

### Update VLAN ID

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --update-path "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]/vlan/config/vlan-id" \
  --update-value "150"
```

### Delete IPv4 Address

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --delete "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]/ipv4/addresses/address[ip=1.1.0.124]"
```

### Delete VLAN Configuration

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --delete "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]/vlan/config/vlan-id"
```

### Delete Entire SubInterface

**gNMI Command**:
```bash
gnmic -a 192.168.1.1:8080 -u admin -p admin --insecure set \
  --delete "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]"
```

## Error Handling

### Common Error Scenarios

#### 1. Parent Interface Not Found
**Error Message**: `Parent interface Ethernet4 does not exist`
**Resolution**: Create the parent interface first in the PORT table

#### 2. Invalid VLAN ID
**Error Message**: `Invalid VLAN ID: must be between 1-4094`
**Resolution**: Provide a valid VLAN ID within the acceptable range

#### 3. Duplicate IP Address
**Error Message**: `IP address 1.1.0.124/32 already exists on interface Ethernet4`
**Resolution**: Use a different IP address or remove the existing configuration

#### 4. Invalid Subinterface Index
**Error Message**: `Invalid subinterface index: must be greater than 0 for VLAN subinterfaces`
**Resolution**: Use index > 0 for VLAN subinterfaces

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_ARGUMENT", 
    "message": "Parent interface Ethernet4 does not exist",
    "details": {
      "path": "/openconfig-interfaces:interfaces/interface[name=Ethernet4]/subinterfaces/subinterface[index=100]",
      "field": "interface_name"
    }
  }
}
```

### Validation Rules

1. **Parent Interface Validation**: Must exist in PORT table
2. **VLAN ID Range**: 1-4094 (standard IEEE 802.1Q range)
3. **IP Address Format**: Valid IPv4/IPv6 format with proper prefix length
4. **Index Constraints**: Index 0 for main interface, index > 0 for subinterfaces
5. **Dependency Checking**: Cannot delete parent interface with active subinterfaces

## Testing

The L3 SubInterface implementation includes comprehensive testing to ensure functionality, reliability, and proper error handling across all supported operations.

## References

### Related Documentation

1. **OpenConfig Interface Model**: [openconfig-interfaces.yang](https://github.com/openconfig/public/tree/master/release/models/interfaces)
2. **OpenConfig VLAN Model**: [openconfig-vlan.yang](https://github.com/openconfig/public/tree/master/release/models/vlan)
3. **SONiC Database Schema**: [SONiC Configuration Database](https://github.com/sonic-net/SONiC/wiki/Configuration)
4. **gNMI Specification**: [gNMI Protocol](https://github.com/openconfig/reference/tree/master/rpc/gnmi)

### Standards Compliance

- **IEEE 802.1Q**: VLAN tagging standards
- **RFC 4291**: IPv6 addressing architecture
- **RFC 791**: IPv4 addressing specification
- **OpenConfig**: Network device configuration standards
