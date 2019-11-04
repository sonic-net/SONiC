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
| 0.2 |   10/31/2019  |   Bing Sun         | Add more requirements &    |
|     |               |                    | dependencies, specifically |
|     |               |                    | for dynamic inter-VRF      |
|     |               |                    | route leaking              |


# About this Manual
This document provides information about the VRF related configurations using management framework.  

# Scope
This document covers the "configuration" and "show" commands supported for VRF based on the OpenConfig YANG model. The document also list the unit test cases.   
The configurations discussed in this document should match and facilitate the functional requirements listed in the SONiC VRF HLD (https://github.com/Azure/SONiC/blob/master/doc/vrf/sonic-vrf-hld.md).   

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          VRF             |  Virtual Routing and Forwarding     |

   

# 1 Feature Overview
   
Add support for VRF related create/delete/get via CLI, REST and gNMI using openconfig-network-instance.yang and sonic-mgmt-framework container.

Following table shows the requirements from the SONiC VRF HLD that should be supported in the management framework and dependencies on the existing features.


| **SONiC HLD Requirements**              | **Mgmt Frmk Support**| **Dependency**                                 |
|-----------------------------------------|----------------------|------------------------------------------------|
|  Add or Delete VRF instance             |       yes            |     none                                       |
| `Add IPv4 and IPv6 host addr on lo intf`|      `yes`           | `lo intf config and IP addr on them`           |
|  Bind L3 interface to a VRF             |                      |                                                |
|          port interface                 |       yes            |     none                                       |
|          vlan interface                 |       yes            |    `????`                                      |
|          portchannel                    |       yes            |    `????`                                      |
|         `loopback interface`            |      `yes(must have)`| `lo intf with IP(V4&V6) must be avail`         |
| `Static IP route with VRF`              |      `not in Buzznik`| `static route support in mgmt frmk`            |       
|  Inter-VRF route leaking                |                      |                                                |
|         `static VRF route leak`         |      `not in Buzznik`| `static route support in mgmt frmk`            |
|         `dynamic VRF route leak`        |      `yes`           | `expand VRF DB schema to include route-map `   |
|                                         |                      | `route-map config in mgmt frmk`                |
|                                         |                      | `route-map DB schema`                          |
|                                         |                      | `hdlr to write route-map via frr upon DB chg`  |
|                                         |                      | `hdlr to assoc route-map with VRF upon DB chg` |
| `Enable BGP VRF aware`                  |  `yes(coverred in bgp feature)`                                       |
   


## 1.1 Requirements
Provide management framework capabilities to handle:
- add/delete VRF instance
- bind/unbind L3 interface to a VRF   
  This applies to port interface, vlan interface, port channel interface and loopback interface
- apply/remove route-map to a VRF
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
Implement VRF support using transformer in sonic-mgmt-framework, including VRF create/delete, L3 interface bind/unbind, and apply/remove route-map on a VRF.

### 1.2.2 Container
All code changes will be done in management-framework container including:
- XML file for the CLI
- Python script to handle CLI request (actioner)
- Jinja template to render CLI output (renderer)
- OpenConfig YANG model for VRF
- SONiC YANG model for VRF based on Redis DB schema of VRF 
- SONiC YANG model modification to add vrf-name if not already added.   
  This applies for port interface, vlan interface, port channel interface and loopback interface
- transformer functions to 
   * convert OpenConfig YANG model (openconfig-network-instance.yang) to SONiC YANG model (sonic-vrf.yang)
   * convert OpenConfig YANG model (openconfig-network-instance.yang) to vrf-name in SONiC YANG model (for L3 interfaces)
   * convert from SONiC YANG models (L3 interfaces) to OpenConfig YANG model (openconfig-network-instance.yang) for show commands

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure VRF and L3 interface binding with VRF via gNMI, REST and CLI interfaces.
Manage/configure route-map on VRF via gNMI, REST and CLI interfaces.

## 2.2 Functional Description
Provide CLI, gNMI and REST supports for VRF related handling

# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for VRF related handlings

## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow the user to make/show VRF related configuration changes to CONFIG DB

#### VRF DB
VRF config DB schema provided by the SONiC VRF HLD is shown below, 
```
"VRF": {   
    "Vrf-blue": {   
        "fallback":"false"   
    }
}
```

To support dynamic route leak and apply a route map with the VRF, propose to add "route-map-import" in the VRF DB schema. "Route-map-export" can be 
added as well for completeness.
```
"VRF": {
    "Vrf-blue": {   
        "fallback":"false"   
        "route-map-import":"import_pol1"    
        "route-map-export":"export_pol1"    
    },   
    "Vrf-red": {   
        "fallback":"false"   
        "route-map-import":"import_pol2"    
    }   
}   
```
#### L3 interface DB
```
"INTERFACE":{   
    "Ethernet0":{   
       "vrf_name":"Vrf-blue"    
    },
    "Ethernet1":{   
       "vrf_name":"Vrf-red"  
    },
    "Ethernet2":{},
    "Ethernet0|11.11.11.1/24": {},   
    "Ethernet0|12.12.12.1/24": {},   
    "Ethernet1|12.12.12.1/24": {},   
    "Ethernet2|13.13.13.1/24": {}   
},   

"LOOPBACK_INTERFACE":{   
    "Loopback0":{   
       "vrf_name":"Vrf-yellow"    
    },     
    "Loopback0|14.14.14.1/32":{}   
},   

"VLAN_INTERFACE": {   
    "Vlan100":{   
       "vrf_name":"Vrf-blue" 
    },   
    "Vlan100|15.15.15.1/24": {}  
},   

"PORTCHANNEL_INTERFACE":{   
    "Portchannel0":{   
       "vrf_name":"Vrf-yellow"  
    }   
}   
```    


### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

Upon VRF route-map-import/route-map-export config DB change, a backend handler should associate the route-map to the VRF via FRR command.
When the prefix list is changed in the route-map, a backend handler should modify the route-map via FRR command.     

The set of FRR command to apply the route-map to a specific VRF is as below:
     
sonic(config)# router bgp 12345 vrf Vrf_blue   
sonic(config-router)#    
sonic(config-router)# address-family ipv4 unicast     
sonic(config-router-af)#     
sonic(config-router-af)# route-map     
  vpn  Between current address-family and vpn     
sonic(config-router-af)# route-map vpn     
  export  For routes leaked from current address-family to vpn     
  import  For routes leaked from vpn to current address-family     
sonic(config-router-af)# route-map vpn import     
  RMAP  name of route-map     
sonic(config-router-af)# route-map vpn import import_pol1     
sonic(config-router-af)#     
sonic(config-router-af)# route-map vpn export     
  RMAP  name of route-map     
sonic(config-router-af)# route-map vpn export export_pol1     
sonic(config-router-af)#     


router bgp 12345 vrf Vrf_blue     
 !     
 address-family ipv4 unicast     
  route-map vpn import import_pol1     
  route-map vpn export export_pol1     
 exit-address-family     
 !
 address-family ipv6 unicast     
  route-map vpn import import_pol2     
  route-map vpn export export_pol2     
 exit-address-family     
!     

   
## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models
YANG models needed for VRF handling in the management framework:
1. **openconfig-network-instance.yang**  
2. **sonic-vrf.yang (new)**
3. **sonic-interface.yang (existing)**

sonic-interface.yang already has VRF binding information and is used here as an example. 
Other interface SONiC Yang models, such as vlan interface, port channel interface and loopback interface, will not be listed here. 
They should provide the same SONiC YANG model change to accomodate the VRF binding.

Supported yang objects and attributes:

####case 1 **For VRF create/delete**
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
+    +--rw sonic-vrf
+       +--rw VRF
+          +--rw VRF_LIST* [vrf-name]
+             +--rw vrf-name            string
+             +--rw fallback?           boolean
              +--rw route-map-import*   string
              +--rw route-map-export*   string
```

####case 2: **Bind/unbind L3 interface to VRF**
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
+          |  +--rw route-distinguisher?        oc-ni-types:route-distinguisher
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

####case 3: apply/remove route-map to a VRF

Note that route-map and prefix set configuration will be done with openconfig-routing-policy.yang, which is not in the scope of this HLD.     

```diff

module: openconfig-network-instance
+   +--rw network-instances
+      +--rw network-instance* [name]
+         +--rw name                       -> ../config/name
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
+         +--rw inter-instance-policies
+          |  +--rw apply-policy
+          |     +--rw config
+          |     |  +--rw import-policy*           -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
+          |     |  +--rw default-import-policy?   default-policy-type
           |     |  +--rw export-policy*           -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name+
           |     |  +--rw default-export-policy?   default-policy-type
           |     +--ro state
           |        +--ro import-policy*           -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
           |        +--ro default-import-policy?   default-policy-type
           |        +--ro export-policy*           -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
           |        +--ro default-export-policy?   default-policy-type

module: sonic-vrf
     +--rw sonic-vrf
        +--rw VRF
           +--rw VRF_LIST* [vrf-name]
              +--rw vrf-name            string
              +--rw fallback?           boolean
+             +--rw route-map-import*   string
+             +--rw route-map-export*   string

```
      
### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

##### Create VRF
```
sonic(config)#ip vrf
  management                  Default management
  String(Max: 32 characters)  VRF Name (max 32 chars)

sonic(config)# ip vrf Vrf_red
sonic(conf-vrf)#

```

##### Delete VRF
```
sonic(config)# no ip vrf
  management                  Management vrf name
  String(Max: 32 characters)  VRF Name (max 32 chars)

sonic(config)# no ip vrf Vrf_red

```

##### Bind/unbind L3 interface to VRF
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

##### Add/delete VRF route distinguisher
```
sonic(conf-vrf)#ip 
    rd            Route distinguisher
sonic(conf-vrf)#ip rd
    A.B.C.D:[1..65535]  4-octet-ipv4addr:2-octet-number
sonic(conf-vrf)#ip rd 1.2.3.4:100

```

##### Apply/remove import/export route-target communities
```
sonic(conf-vrf)# ip
  route-export  VRF IP config subcommands
  route-import  VRF IP config subcommands
sonic(conf-vrf)# ip route-import
  1..65535:1..65535  Configure RT community value
sonic(conf-vrf)# ip route
route-export route-import
sonic(conf-vrf)# ip route-import 1111:11
sonic(conf-vrf)# ip route
route-export route-import
sonic(conf-vrf)# ip route-export 1111:22
sonic(conf-vrf)#

S10(conf-vrf)# no ip route-import
  1..65535:1..65535  Configure RT community value
S10(conf-vrf)# no ip route-export
  1..65535:1..65535  Configure RT community value

sonic(conf-vrf)# no ip route-import 1111:11
sonic(conf-vrf)# no ip route-export 1111:22

sonic(conf-vrf)# ipv6
  route-export  VRF IPv6 config subcommands
  route-import  VRF IPv6 config subcommands


sonic(conf-vrf)# ipv6
  route-export  VRF IPv6 config subcommands
  route-import  VRF IPv6 config subcommands

sonic(conf-vrf)# ipv6 route-import
  1..65535:1..65535  Configure RT community value

sonic(conf-vrf)# ipv6 route-import 1111:11
sonic(conf-vrf)# ipv6 route-export 1111:22
sonic(conf-vrf)#
sonic(conf-vrf)# no ipv6 route-import 1111:11
sonic(conf-vrf)# no ipv6 route-export 1111:22
```

##### Apply/remove route-map to VRF
route-map has to be already configured before it can be applied on a VRF   

```
sonic(conf-vrf)# ip
  route-map-import  VRF IP config subcommands
  route-map-export  VRF IP config subcommands
sonic(conf-vrf)# ip route-map-import
  RMAP      name of route-map
sonic(conf-vrf)# ip route-map-import import_pol1
sonic(conf-vrf)# ip route-map-export
  RMAP      name of route-map
sonic(conf-vrf)# ip route-map-export export_pol1

sonic(conf-vrf)# no ip route-route-import import_pol1
sonic(conf-vrf)# no ip route-route-export export_pol1

sonic(conf-vrf)# ipv6
  route-map-import  VRF IPv6 config subcommands
  route-map-export  VRF IPv6 config subcommands
sonic(conf-vrf)# ipv6 route-map-import
  RMAP      name of route-map
sonic(conf-vrf)# ipv6 route-map-import import_pol2
sonic(conf-vrf)# ipv6 route-map-export
  RMAP      name of route-map
sonic(conf-vrf)# ipv6 route-map-export export_pol2

sonic(conf-vrf)# no ipv6 route-route-import import_pol2
sonic(conf-vrf)# no ipv6 route-route-export export_pol2

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

##### Show a specific VRF
```
sonic#show ip vrf Vrf_blue
name:     Vrf_blue
    Route-Targets       : 1111:11
    Route-Distinguisher : 1.2.3.4:100
    Route-map-import    : import_pol1
    Route-map-export    :
    Interfaces          : Loopback3
                          Ethernet100
```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - For option "all", get existing VRF configuration information from CONFIG DB, including VRF name and L3 interface to VRF binding
      For option to get a specific VRF, get existing VRF configuration information from CONFIG_DB, including VRF name, L3 interface binding, route-target, route distinguisher and route-map
POST - Add VRF configuration into CONFIG DB, including VRF instance, L3 interface to VRF binding, route-target, route distinguisher and route-map
PATCH - Update existing VRF configuraiton information in CONFIG DB, including VRF instance, L3 interface to VRF binding, route-target, route distinguisher and route-map
DELETE - Delete a existing VRF configuration from CONFIG DB.    
             If the L3 interface binding is deleted, the VRF name will be removed from the interface table   
             If the VRF itself is removed, the VRF will be removed from the VRF table
         Delete route-target of VRF
         Delete route distinguisher of VRF
         Delete route-map of VRF
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
| Apply route-map to VRF | Verify that the route-map name is in the VRF table and FRR route-map VRF association is correct |
| Remove route-map from VRF | Verify that the route-map name is removed from the VRF table and FRR route-map VRF is empty | 
| show VRF | Verify VRF is displayed correctly with its associated L3 interfaces |

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information

