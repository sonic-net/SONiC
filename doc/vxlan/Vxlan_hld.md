# Vxlan SONiC
# High Level Design Document
### Rev 1.2

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
    * [1.2 Orchagent requirement](#12-orchagent-requirements)
    * [1.3 CLI requirements](#13-cli-requirements)
    * [1.4 Scalability requirements](#14-scalability-requirements)
    * [1.5 Warm Restart requirements ](#15-warm-restart-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
    * [2.2 App DB](#22-app-db)
    * [2.3 Orchestration Agent](#23-orchestration-agent)
    * [2.4 SAI](#24-sai)
	* [2.5 CLI](#25-cli)
	  * [2.5.1 Vxlan utility interface](#251-vxlan-utility-interface)
	  * [2.5.2 Config CLI command](#252-config-cli-command)
	  * [2.5.3 Show CLI command](#253-show-cli-command)
  * [3 Flows](#3-flows)
	* [3.1 Functional flow](#31-vxlan-vnet-peering)
	* [3.2 CLI flow ](#32-vxlan-cli-flow)
  * [4 Example configuration](#4-example-configuration)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             |     Prince Sunny   | Initial version                   |
| 1.0 |             |     Prince Sunny   | Review comments/feedback          |
| 1.1 |             |     Prince Sunny   | Review comments                   |
| 1.2 |             |     Prince Sunny   | Design change for VNET Table flow |

# About this Manual
This document provides general information about the Vxlan feature implementation in SONiC.
# Scope
This document describes the high level design of the Vxlan feature. Kernel VRF (L3mdev) programming for VNET peering is beyond the scope of this document. 

# Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| VNI                      | Vxlan Network Identifier       |
| VTEP                     | Vxlan Tunnel End Point         |
| VM                       | Virtual Machine                |
| VRF                      | Virtual Routing and Forwarding |
| VNet                     | Virtual Network                |

# 1 Requirements Overview
## 1.1 Functional requirements
This section describes the SONiC requirements for Vxlan feature primarily in the context of VNet. 

At a high level the following should be supported:

Phase #1
- Should be able to perform the role of Vxlan Tunnel End Point (VTEP)
- VNet peering between customer VMs and Baremetal servers [VNet Requirements](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-Proposal-QinQ-VXLAN.md).
- Distributed Vxlan routing with Symmetric IRB model (RIOT)

Phase #2
- Integration with BGP EVPN 
- Should support untagged or tagged traffic (Overlay layer 2 networks over layer 3 underlay)
- Should be able to do HER for unicast traffic based on configured flood list
- CLI commands to configure Vxlan


## 1.2 Orchagent requirements
### Vxlan orchagent:
 - Should be able to create VRF/BRIDGE/VLAN to VNI mapping.
 - Should be able to create NH Tunnel and Tunnel termination tables.  
 - Should be able to create tunnels and encap/decap mappers. 

### Vnet orchagent:
 - Should be able to create VRFs per VNET tables. 
 - Should be able to track peering configurations.
 - Should be VNet/VRF aware
 
### Vnet Route orchagent:
 - Should be able to handle routes within a VNet 
 - Should be able to create NH tunnels for the endpoints
 - Should be VNet/VRF aware

### FDB orchagent:
 - Should be VTEP aware
 - Should support static configuration of FDB entries learnt on remote VTEP
 
### INTFs orchagent:
 - Should be VRF aware
 - Should be able to create router interfaces in a specific VRF
 
## 1.3 CLI requirements
- User should be able to get FDB learnt per VNI
- User should be able to configure Vxlan tunnels and VTEPs (Overlay)

In summary:
```
	- config vxlan <vxlan_name> vlan <vlan_id> vni <vni_id>
	- config vxlan <vxlan_name> src_if <interface>
	- config vxlan <vxlan_name> vlan <vlan_id> flood vtep <ip1, ip2, ip3>
	- show mac vxlan <vxlan_name> <vni_id>
	- show vxlan <vxlan_name>
```
Configuring VNet peering via CLI is beyond the scope

## 1.4 Scalability requirements

### 1.4.1 VNet Peering
###### Table 2: VNet peering scalability
| Vxlan component          | Expected value              |
|--------------------------|-----------------------------|
| VNI                      | 8k                          |
| Tunnel encaps            | 128k                        |
| VMs                      | 512k                        |
| VRFs                     | 128                         |
| Routes                   | 512k                        |

## 1.5 Warm Restart requirements
Phase #1 shall not include warm restart capabilities. SAI VR objects are not compliant with warm restart currently. This shall be revisited in Phase #2. 

# 2 Modules Design

## 2.1 Config DB
Following new tables will be added to Config DB. Unless otherwise stated, the attributes are mandatory

### 2.1.1 VXLAN Table
```
VXLAN_TUNNEL|{{tunnel_name}} 
    "src_ip": {{ip_address}} 
    "dst_ip": {{ip_address}} (OPTIONAL)

VXLAN_TUNNEL_MAP|{{tunnel_name}}|{{tunnel_map}}
    "vni": {{ vni_id}}
    "vlan": {{ vlan_id }}
```
### 2.1.2 VNET/Interface Table
```
VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "peer_list": {{vnet_name_list}} (OPTIONAL)

INTERFACE|{{intf_name}} 
    "vnet_name": {{vnet_name}} 
    
INTERFACE|{{intf_name}}|{{prefix}}  
    { }
    
VLAN_INTERFACE|{{intf_name}} 
    "vnet_name": {{vnet_name}} 
    
VLAN_INTERFACE|{{intf_name}}|{{prefix}}  
    { }
    
NEIGH_TABLE|{{intf_name}}|{{ip_address}}
    "family": "IPv4" 
```

### 2.1.3 ConfigDB Schemas
```
; Defines schema for VXLAN Tunnel configuration attributes
key                                   = VXLAN_TUNNEL:name             ; Vxlan tunnel configuration
; field                               = value
SRC_IP                                = ipv4                          ; Ipv4 source address, lpbk address for tunnel term
DST_IP                                = ipv4                          ; Ipv4 destination address, for P2P

;value annotations
ipv4          = dec-octet "." dec-octet "." dec-octet "." dec-octet     
dec-octet     = DIGIT                     ; 0-9  
                  / %x31-39 DIGIT         ; 10-99  
                  / "1" 2DIGIT            ; 100-199  
                  / "2" %x30-34 DIGIT     ; 200-249
		  
```

```
; Defines schema for VXLAN Tunnel map configuration attributes
key                                   = VXLAN_TUNNEL:tunnel_name:name ; Vxlan tunnel configuration
; field                               = value
VNI                                   = DIGITS                        ; 1 to 16 million values
VLAN                                  = 1\*4DIGIT                     ; 1 to 4094 Vlan id
```

```
; Defines schema for VNet configuration attributes
key                                   = VNET:name                     ; Vnet name
; field                               = value
VXLAN_TUNNEL                          = tunnel_name                   ; refers to the Vxlan tunnel name
VNI                                   = DIGITS                        ; 1 to 16 million VNI values
PEER_LIST                             = \*vnet_name                   ; vnet names seperate by "," 
                                                                             (empty indicates no peering)
```

```
; Defines schema for VNet Interface configuration attributes
key                                   = INTERFACE:name                ; Vnet interface name. This can be port, vlan 
                                                                        or port-channel interface
; field                               = value
VNET_NAME                             = vnet_name                     ; vnet name where the interface belongs to

; Defines schema for VNet Interface configuration attributes
key                                   = INTERFACE:name:prefix         ; Vnet interface name with IP prefix. No change to 
                                                                        existing schema. 
; field                               = value

; Defines schema for VNet Neighbor configuration attributes
key                                   = NEIGH_TABLE:name:ip_address   ; Vnet neighbor with IP address. Swss shall resolve
                                                                        the mac addresss for this configuration
; field                               = value
family                                = IPv4/IPv6                     ; Address family
```

Please refer to the [schema](https://github.com/Azure/sonic-swss/blob/master/doc/swss-schema.md) document for details on value annotations. 

## 2.2 APP DB
Two new tables would be introduced to specify routes and tunnel end points in VNet domain. 

```
VNET_ROUTE_TABLE:{{vnet_name}}:{{prefix}} 
    "nexthop": {{ip_address}} (OPTIONAL) 
    "ifname": {{intf_name}} 
 
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address}} 
    "mac_address":{{mac_address}} (OPTIONAL) 
    "vxlanid": {{vni}}(OPTIONAL) 
```

```
VXLAN_FDB_TABLE::{{tunnel_name}}:{{vni_id}}:{{mac_address}}
    "remote_vtep": {{ip_address}} 
```

VRFMgrD creates the following VNET Table

```    
VNET_TABLE:{{vnet_name}}
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "peer_list": {{ vnet_name_list }}
```

### 2.2.1 APP DB Schemas

```
; Defines schema for VNet Route table attributes
key                                   = VNET_ROUTE_TABLE:vnet_name:prefix ; Vnet route table with prefix
; field                               = value
NEXTHOP                               = ipv4                          ; Nexthop IP address
IFNAME                                = ifname                        ; Interface name
```

```
; Defines schema for VNet Route tunnel table attributes
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = ipv4                          ; Host VM IP address
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet (Optional)
VXLANID                               = DIGITS                        ; VNI value in encapsulated packet (Optional)
```

```
; Defines FDB entries for remote VTEP
key                                   = VXLAN_FDB_TABLE:tunnel_name:vni_id:mac_address ; Remotely learnt mac-address
REMOTE_VTEP                           = ipv4                          ; Remote VTEP where the host resides
```

```
; Defines schema for VXLAN VRF Tunnel map attributes
key                                   = VXLAN_TUNNEL:tunnel_name:name ; Vxlan tunnel map
; field                               = value
VNI                                   = DIGITS                        ; 1 to 16 million values
VRF                                   = vrf_name                      ; VRF name 
```

```
; Defines schema for VNET Table attributes
key                                   = VNET_TABLE:name               ; VNet table name
; field                               = value
VXLAN_TUNNEL                          = tunnel_name                   ; refers to the Vxlan tunnel name
VNI                                   = DIGITS                        ; 1 to 16 million VNI values
PEER_LIST                             = \*vnet_name                   ; vnet names seperate by "," 
                                                                             (empty indicates no peering)
```

## 2.3 Orchestration Agent
Following orchagents shall be modified. Flow diagrams are captured in a later section. 


![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/vnet_vxlan_orch.png)

 ### VxlanOrch
 This is the major subsystem for Vxlan that handles configuration request. Vxlanorch creates the tunnel and attaches encap and decap mappers. Seperate tunnels are created for L2 Vxlan and L3 Vxlan and can attach different VLAN/VNI or VRF/VNI to respective tunnel. 
 	
 ### VrfMgrD
 VrfMgrD gets the VNET Table config and creates the L3mdev interface in kernel. VrfMgrD updates the APP_DB with VNET_TABLE later to be used by VnetOrch. VrfMgrD also updates the STATE_DB for the status of VRF created. 
 
 ### VrfOrch
 VrfOrch creates VRF in SAI from APP_DB updates from VrfMgrD for the regular VRF configurations. RouterOrch fetch this information for programming routes based on VRF.

 ### VnetOrch/VnetRouteOrch
 VnetOrch is another major component introduced for the VNet usecase. VnetOrch creates ingress/Egress (based on context) VRF or BRIDGE in SAI for a VNet and also maintains the peering list. VnetOrch call VxlanOrch API to create the encap/decap mappers for the VNet. VnetRouterOrch fetch the VRF and peering information for replicating the routes, if applicable. When app-route-table has new updates for the VNet, VnetRouteOrch gets the VNet objects (VRF or BRIDGE) from VnetOrch and programs SAI.  
 	- VNET_ROUTE_TABLE is translated to create subnet/local route entries  
	- VNET_ROUTE_TUNNEL_TABLE is translated to create routes with tunnel nexthop

 ### IntfMgrD
 IntfMgrD creates the kernel routing interface and enslave it to the VRF L3mdev. IntfMgrD waits for VRF creation update in STATE_DB and updates the APP_DB INTF_TABLE with the Vrf/VNet name.
 
 ### IntfsOrch
 Add VrfOrch as a member of IntfsOrch. IntfsOrch creates Router Interfaces based on interface table (INTF_TABLE) and the VRF information. For VNet usecase, IntfOrch calls VnetOrch API to handle router interface creation. 
 
 ### FdbOrch
 Add VxlanOrch as a member of FDBOrch. For FDB entries learnt on remote VTEP, app-fdb-table shall be updated and programmed to SAI by getting the BridgeIf/RemoteVTEP mapping from VxlanOrch. (TBD)
 
 The overall data flow diagram is captured below for all TABLE updates. 
 
 ![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/vnet_vxlan_data_flow.png)
 
 
## 2.4 SAI
Shown below table represents main SAI attributes which shall be used for Vxlan

###### Table 3: VNet peering SAI attributes
| Vxlan component          | SAI attribute                                         |
|--------------------------|-------------------------------------------------------|
| Vxlan Tunnel type        | SAI_TUNNEL_TYPE_VXLAN                                 |
| Encap mapper             | SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI          |
| Decap mapper             | SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID          |
| Nexthop tunnel           | SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP                        |
| Tunnel term type         | SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP                 |
| Vxlan MAC                | SAI_SWITCH_ATTR_VXLAN_DEFAULT_ROUTER_MAC              |
| Vxlan port               | SAI_SWITCH_ATTR_VXLAN_DEFAULT_PORT                    |

## 2.5 CLI

Commands summary (Phase #2):

```
	- config vxlan <vxlan_name> vlan <vlan_id> vni <vni_id>
	- config vxlan <vxlan_name> src_if <interface>
	- config vxlan <vxlan_name> vlan <vlan_id> flood vtep <ip1, ip2, ip3>
	- show mac vxlan <vxlan_name> <vni_id>
	- show vxlan <vxlan_name>
```

### 2.5.1 Vxlan utility interface
```
vxlan
Usage: vxlan [OPTIONS] COMMAND [ARGS]...

  Utility to operate with Vxlan configuration.

Options:
  --help  Show this message and exit.

Commands:
  config   Set Vxlan configuration.
  show     Show Vxlan information.
```

### 2.5.2 Config CLI command
Config command should be extended in order to add "vxlan" alias 
```
Usage: config [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'config' command

Options:
  --help  Show this message and exit.

Commands:
...
  vxlan               vxlan related configuration.
```
### 2.5.3 Show CLI command
Show command should be extended in order to add "vxlan" alias
```
show
Usage: show [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'show' command

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  ...
  vxlan                   Show vxlan related information
```

# 3 Flows

## 3.1 Vxlan VNet peering 
![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/vnet_vxlan_cntrl_flow_1.png)

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/vnet_vxlan_cntrl_flow_2.png)

## Layer 2 Vxlan 
TBD 

## 3.2 Vxlan CLI flow
TBD
  
# 4 Example configuration
### Vnet Configurations

	Vnet 1 
		□ VNI - 2000
		□ VMs
			VM1. CA: 100.100.1.1/32, PA: 10.10.10.1, MAC: 00:00:00:00:01:02
		□ BM1 
			Connected on Ethernet1 
			Ip: 100.100.3.2/24
			MAC: 00:00:AA:AA:AA:01

	Vnet 2 
		□ VNI - 3000
		□ VMs
			VM2. CA: 100.100.2.1/32, PA: 10.10.10.2, MAC: 00:00:00:00:03:04
		□ BM2 
			Connected on Ethernet2 in Vlan2000
			Ip: 100.100.4.2/24
			MAC: 00:00:AA:AA:AA:02

### ConfigDB objects: 
```
{ 
    "VXLAN_TUNNEL|tunnel1": { 
        "src_ip": "10.10.10.10", 
    }, 

    "VNET|Vnet_2000": { 
        "vxlan_tunnel": "tunnel1", 
        "vni": "2000", 
        "peer_list": "Vnet_3000", 
    }, 

    "INTERFACE|Ethernet1": { 
        "vnet_name": "Vnet_2000", 
    }, 
     
    "INTERFACE|Ethernet1|100.100.3.1/24": { 
    }, 

    "NEIGH_TABLE|Ethernet1|100.100.3.2": { 
        "family": "IPv4" 
    },
    
    "VNET|Vnet_3000": { 
        "vxlan_tunnel": "tunnel1", 
        "vni": "3000", 
        "peer_list": "Vnet_2000", 
    },  

    "VLAN|Vlan2000": {
        "vlanid": "2000"
    },
    
    "VLAN_MEMBER|Vlan2000|Ethernet2": {
        "tagging_mode": "untagged"
    },

    "VLAN_INTERFACE|Vlan2000": {
         "vnet_name": "Vnet_3000",
    },

    "VLAN_INTERFACE|Vlan2000|100.100.4.1/24": {
    },
    
    "NEIGH_TABLE|Vlan2000|100.100.4.2": { 
        "family": "IPv4" 
    },
 ```
### APPDB Objects: 
```
{  
    "VNET_ROUTE_TABLE:Vnet_2000:100.100.3.0/24": { 
        "ifname": "Ethernet1", 
    }, 

    "VNET_ROUTE_TABLE:Vnet_3000:100.100.4.0/24": { 
        "ifname": "Vlan2000", 
    }, 

    "VNET_ROUTE_TUNNEL_TABLE:Vnet_2000:100.100.1.1/32": { 
        "endpoint": "10.10.10.1", 
    }, 

    "VNET_ROUTE_TUNNEL_TABLE:Vnet_3000:100.100.2.1/32": { 
        "endpoint": "10.10.10.2", 
        "mac_address": "00:00:00:00:03:04"
    }, 
}
```
