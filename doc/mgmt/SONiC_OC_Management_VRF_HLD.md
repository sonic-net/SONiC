# Feature Name
Management VRF Support in Management Framework

# High Level Design Document

#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 10/10/2019  |   Bing Sun         | Initial version                   |
  
  
# About this Manual
This document provides information about the Management VRF configuration using management framework.

# Scope
This document covers the "configuration" and "show" commands supported for Management VRF based on the OpenConfig YANG model. The document also list the unit test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          VRF             |  Virtual Routing and Forwarding     |


# 1 Feature Overview
Add support for Management VRF create/delete/get via CLI, REST and gNMI using openconfig-network-instance.yang and sonic-mgmt-framework container.

## 1.1 Requirements
Provide management framework capabilities to handle:
- add/delete Management VRF
- show Management VRF

### 1.1.1 Functional Requirements
Provide management framework support to existing SONiC capabilities with respect to Management VRF.
Here is the link for the Management VRF HLD in SONiC, 
https://github.com/Azure/SONiC/blob/310de5a9d649481e23ec3b048cbe90242c6e063f/mgmt-vrf-design-doc.md  

### 1.1.2 Configuration and Management Requirements
- CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

Configurations not supported by this feature using management framework:

- this feature does not provide the configuration option of binding Management VRF to a SNMP server. This is because the management framework does not support SNMP.

- this feature does not provide the configuration option of using Management VRF for NTP. This is because SONiC NTP uses Management VRF automatically when configured, and uses default VRF if Management VRF is not configured.  
It is up to the user to configure NTP server correctly. This feature does not have dependency on the NTP server configuration.

- no support of configuring Management VRF for other IP services such as DNS, tftp, ftp etc.

### 1.1.3 Scalability Requirements

### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach
Implement Management VRF support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
All code changes will be done in management-framework container including:
- XML file for the CLI
- Python script to handle CLI request (actioner)
- Jinja template to render CLI output (renderer)
- OpenConfig YANG model for Management VRF
- SONiC YANG model for Management VRF based on Redis DB schema of Management VRF 
  (https://github.com/Azure/SONiC/wiki/Configuration#management-vrf)
- transformer functions to 
   * convert OpenConfig YANG model to SONiC YANG model for Management VRF configuration
   * convert from SONiC YANG model to OpenConfig YANG model for Management VRF show

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure Management VRF via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide CLI, gNMI and REST supports for Management VRF handling

# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for Management VRF Handling

## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow the user to make/show Management VRF configuration changes to CONFIG DB

### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models
YANG models needed for Management VRF handling in the management framework:
1. **openconfig-network-instance.yang**  

   **Note that Management VRF and data VRF use the same OpenConfig YANG model. Since Management VRF uses a subset of it, only the portion applicable to the Management VRF handling is shown below.**
2. **sonic-mgmt-vrf.yang**

Supported yang objects and attributes:
```diff

module: openconfig-network-instance.yang
 +   +--rw network-instances
 +      +--rw network-instance* [name]
 +         +--rw name                       -> ../config/name
           +--rw fdb
           |  +--rw config
           |  |  +--rw mac-learning?      boolean
           |  |  +--rw mac-aging-time?    uint16
           |  |  +--rw maximum-entries?   uint16
           |  +--ro state
           |  |  +--ro mac-learning?      boolean
           |  |  +--ro mac-aging-time?    uint16
           |  |  +--ro maximum-entries?   uint16
           |  +--rw mac-table
           |     +--rw entries
           |        +--rw entry* [mac-address vlan]
           |           +--rw mac-address    -> ../config/mac-address
           |           +--rw vlan           -> ../config/vlan
           |           +--rw config
           |           |  +--rw mac-address?   yang:mac-address
           |           |  +--rw vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
           |           +--ro state
           |           |  +--ro mac-address?   yang:mac-address
           |           |  +--ro vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
           |           |  +--ro age?           uint64
           |           |  +--ro entry-type?    enumeration
           |           +--rw interface
           |              +--rw interface-ref
           |                 +--rw config
           |                 |  +--rw interface?      -> /oc-if:interfaces/interface/name
           |                 |  +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
           |                 +--ro state
           |                    +--ro interface?      -> /oc-if:interfaces/interface/name
           |                    +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
+          +--rw config
+          |  +--rw name?                       string
+          |  +--rw type?                       identityref
+          |  +--rw enabled?                    boolean
+          |  +--rw description?                string
           |  +--rw router-id?                  yang:dotted-quad
           |  +--rw route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--rw enabled-address-families*   identityref
           |  +--rw mtu?                        uint16
+          +--ro state
+          |  +--ro name?                       string
+          |  +--ro type?                       identityref
+          |  +--ro enabled?                    boolean
+          |  +--ro description?                string
           |  +--ro router-id?                  yang:dotted-quad
           |  +--ro route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--ro enabled-address-families*   identityref
           |  +--ro mtu?                        uint16
           +--rw encapsulation

module: sonic-mgmt-vrf
    +--rw sonic-mgmt-vrf
       +--rw MGMT_VRF_CONFIG
          +--rw MGMT_VRF_CONFIG_LIST* [mgmt-vrf-name]
             +--rw mgmt-vrf-name     string
             +--rw mgmtVrfEnabled?   boolean 
```

### 3.6.2 CLI
Note that the final CLI configuration and show will change based on the final data VRF configuration and show format

#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

### Create Management VRF
```
sonic(config)#ip vrf
  management               Management VRF
  ...
sonic(config)#ip vrf management
sonic(config)#
```

### Delete Management VRF
```
sonic(config)#no ip vrf
  management               Management VRF
  ...
sonic(config)#no ip vrf management
sonic(config)#
```

#### 3.6.2.2 Show Commands
##### Show all VRFs
```
sonic#show ip vrf
VRF-Name                          Interfaces
--------------------------------------------
Vrf_blue                          Ethernet0
mgmt                              eth0
```

##### Show Management VRF only
```
sonic#show ip vrf
 management       Management VRF information
 ...

sonic#show ip vrf management
VRF-Name                          Interfaces
---------------------------------------------
mgmt                              eth0
```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing Management VRF configuration information from CONFIG DB.
POST - Add Management VRF configuration into CONFIG DB.
PATCH - Update existing Management VRF configuraiton information in CONFIG DB.
DELETE - Delete a existing Management VRF configuration from CONFIG DB. This will cause some configurations to return to default value.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### Configuration via CLI

| Test Name | Test Description |
| :-------- | :----- |
| Configure Management VRF | Verfiy Management VRF is configured in configDB with mgmtVrfEnabled set to true |
| Delete Management VRF | Verify Management VRF is updated in configDB with mgmtVrfEnabled set to false |
| show Management VRF | Verify Management VRF is displayed correctly |


#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information



