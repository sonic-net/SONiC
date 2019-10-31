# Feature Name
VRF Support in Management Framework

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
| Rev |     Date      |       Author       | Change Description         |
|:---:|:-------------:|:------------------:|----------------------------|
| 0.1 |   10/30/2019  |   Bing Sun         | Initial version            |

    

# About this Manual
This document provides information about the VRF related configurations using management framework.  

# Scope
This document covers the "configuration" and "show" commands supported for VRF based on the OpenConfig YANG model. The document also list the unit test cases.   
The configurations discussed in this document should match and facilitate the functional requirements listed in the SONiC VRF HLD (https://github.com/Azure/SONiC/blob/master/doc/vrf/sonic-vrf-hld.md).   
Rev 0.1 covers the following requirements from SONiC VRF HLD:
- Add or Delete VRF instance
- Bind L3 interface to a VRF. 
  L3 interface types include port interface, vlan interface, LAG interface and loopback interface.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          VRF             |  Virtual Routing and Forwarding     |

   

# 1 Feature Overview
Add support for VRF create/delete/get via CLI, REST and gNMI using openconfig-network-instance.yang and sonic-mgmt-framework container.

## 1.1 Requirements
Provide management framework capabilities to handle:
- add/delete VRF instance
- bind/unbind L3 interface to a VRF
  This applies to port interface, vlan interface, port channel interface and loopback interface
- show VRF

### 1.1.1 Functional Requirements
Provide management framework support to existing SONiC capabilities with respect to VRF. 

### 1.1.2 Configuration and Management Requirements
- CLI style configuration and show commands
- REST API support
- gNMI Support

Details described in Section 3.

### 1.1.3 Scalability Requirements

### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach
Implement VRF support using transformer in sonic-mgmt-framework, including VRF create/delete and L3 interface bind/unbind.

### 1.2.2 Container
All code changes will be done in management-framework container including:
- XML file for the CLI
- Python script to handle CLI request (actioner)
- Jinja template to render CLI output (renderer)
- OpenConfig YANG model for VRF
- SONiC YANG model for VRF based on Redis DB schema of VRF 
  (based on DB schemas provided in SONiC VRF HLD)
- SONiC YANG model modification for SONiC YANG models including port interface, vlan interface, port channel interface and loopback interface
- transformer functions to 
   * convert OpenConfig YANG model to SONiC YANG model for VRF configuration
   * convert from SONiC YANG models to OpenConfig YANG model for VRF show

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure VRF and L3 interface binding with VRF via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide CLI, gNMI and REST supports for VRF related handling

# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for VRF related handling

## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow the user to make/show VRF related configuration changes to CONFIG DB

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
YANG models needed for VRF handling in the management framework:
1. **openconfig-network-instance.yang**  
2. **sonic-vrf.yang**
3. **sonic-interface.yang**

Note that sonic-interface.yang already has VRF binding information and is used here as an example. 
Other interface SONiC Yang models, such as vlan interface, port channel interface and loopback interface, will not be listed here. 
They should provide the same SONiC YANG model change to accomodate the VRF binding.

Supported yang objects and attributes:

case 1 **For VRF create/delete**
 - openconfig-network-instance.yang  
      VRF name must start with "Vrf"
      config type must be "L3VRF"
 - sonic-vrf.yang   
      per SONiC VRF HLD, fallback is not supported in this release for the VRF. So it won't be configurable via management framework. 
      Set it to the default value "false".

```diff

module: openconfig-network-instance.yang
+    +--rw network-instances
+       +--rw network-instance* [name]
+          +--rw name                       -> ../config/name
           ...
+          +--rw config
+          |  +--rw name?                       string
+          |  +--rw type?                       identityref
+          |  +--rw enabled?                    boolean
           |  +--rw description?                string
           |  +--rw router-id?                  yang:dotted-quad
           |  +--rw route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--rw enabled-address-families*   identityref
           |  +--rw mtu?                        uint16
...

+          +--ro state
+          |  +--ro name?                       string
+          |  +--ro type?                       identityref
+          |  +--ro enabled?                    boolean
           |  +--ro description?                string
           |  +--ro router-id?                  yang:dotted-quad
           |  +--ro route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--ro enabled-address-families*   identityref
           |  +--ro mtu?                        uint16
           +--rw encapsulation

module: sonic-vrf
    +--rw sonic-vrf
       +--rw VRF
          +--rw VRF_LIST* [vrf-name]
             +--rw vrf-name    string
             +--rw fallback?   boolean

```

case 2: **Bind/unbind L3 interface to VRF**
- openconfig-network-instance.yang
- sonic-interface.yang 
  The same change should be done for SONiC vlan interface YANG model, SONiC port channel YANG mode and SONiC loopback YANG model.

```diff
module: openconfig-network-instance
+    +--rw network-instances
+       +--rw network-instance* [name]
+          +--rw name                       -> ../config/name
          ...
+         +--rw config
+          |  +--rw name?                       string
+          |  +--rw type?                       identityref
+          |  +--rw enabled?                    boolean
           |  +--rw description?                string
           |  +--rw router-id?                  yang:dotted-quad
           |  +--rw route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--rw enabled-address-families*   identityref
           |  +--rw mtu?                        uint16
           +--ro state
           |  +--ro name?                       string
           |  +--ro type?                       identityref
           |  +--ro enabled?                    boolean
           |  +--ro description?                string
           |  +--ro router-id?                  yang:dotted-quad
           |  +--ro route-distinguisher?        oc-ni-types:route-distinguisher
           |  +--ro enabled-address-families*   identityref
           |  +--ro mtu?                        uint16
          ...
+          +--rw interfaces
+          +--rw interface* [id]
+          |     +--rw id        -> ../config/id
+          |     +--rw config
+          |     |  +--rw id?                            string
+          |     |  +--rw interface?                     -> /oc-if:interfaces/interface/name
+          |     |  +--rw subinterface?                  -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
+          |     |  +--rw associated-address-families*   identityref
+          |     +--ro state
+          |        +--ro id?                            string
+          |        +--ro interface?                     -> /oc-if:interfaces/interface/name
+          |        +--ro subinterface?                  -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
+          |        +--ro associated-address-families*   identityref

module: sonic-interface
     +--rw sonic-interface
        +--rw INTERFACE
           +--rw INTERFACE_LIST* [portname]
           |  +--rw portname    -> /prt:sonic-port/PORT/PORT_LIST/ifname
+          |  +--rw vrf-name?   string
          +--rw INTERFACE_IPADDR_LIST* [portname ip_prefix]
             +--rw portname     -> /prt:sonic-port/PORT/PORT_LIST/ifname
             +--rw ip_prefix    inet:ip-prefix

```

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

### Create VRF
```
sonic(config)#ip vrf
  management                  Default management
  String(Max: 32 characters)  VRF Name (max 32 chars)

sonic(config)# ip vrf Vrf_red
sonic(conf-vrf)#

```

### Delete VRF
```
sonic(config)# no ip vrf
  management                  Management vrf name
  String(Max: 32 characters)  VRF Name (max 32 chars)

sonic(config)# no ip vrf Vrf_red

```

### Bind/unbind L3 interface to VRF
The binding of L3 interface to VRF applies to
- port interface
- vlan interface
- port channel inteface
- loopback interface

Only port interface is shown here as an example. These other types should have the same behavior.

VRF must be configured already before binding L3 interface to it.

```
sonic(config)# interface
  ...
  Ethernet     Select an interface
  Loopback     Loopback Interface Configuration
  PortChannel  Port channel Interface Configuration
  Vlan         Vlan Interface Configuration
  ...
```

```
Bind L3 interface of port interface

sonic(config)#interface Ethernet 100
sonic(conf-if-Ethernet100)#
    ip             Interface Internet Protocol config commands
sonic(conf-if-Ethernet100)# ip
    vrf             Add interface to specified VRF domain
sonic(conf-if-Ethernet100)# ip vrf
    forwarding  Configure forwarding table
sonic(conf-if-Ethernet100)# ip vrf forwarding 
    String(Max: 32 characters)  VRF name (max 32 char)
sonic(conf-if-Ethernet100)# ip vrf forwarding Vrf_red
Success

sonic(conf-if-Ethernet100)# ip vrf forwarding Vrf_blue
%Error: vrf Vrf_blue doesnt exists
```

```
Unbind L3 interface of port interface

sonic(conf-if-Ethernet100)#no ip vrf forwarding
Success

```

#### 3.6.2.2 Show Commands
##### Show all VRFs
```
sonic#show ip vrf
VRF-Name                          Interfaces
............................................
Vrf_red                           Vlan100
                                  Loopback2

Vrf_blue                          Ethernet100
                                  Loopback3
                          
Vrf_green                         Loopback4
                                  po10
```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing VRF configuration information from CONFIG DB, including VRF name and L3 interface to VRF binding
POST - Add VRF configuration into CONFIG DB, including VRF instance and L3 interface to VRF binding
PATCH - Update existing VRF configuraiton information in CONFIG DB, including VRF instance and L3 interface to VRF binding
DELETE - Delete a existing VRF configuration from CONFIG DB.    
         If the L3 interface binding is deleted, the VRF name will be removed from the interface table   
         If the VRF itself is removed, the VRF will be removed from the VRF table
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
| Configure VRF | Verfiy VRF is configured in configDB with the VRF name in the VRF table |
| Delete VRF | Verify VRF is deleted in configDB VRF table |
| Bind L3 interface to VRF | Verify that vrf-name is in the respective interface table in the configDB |
| Unbind L3 interface to VRF | Verify that the vrf-name is deleted in the respective interface table in the configDB |
| show VRF | Verify VRF is displayed correctly with its associated L3 interfaces |

#### Show sFlow configuration via CLI

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information



