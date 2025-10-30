# Vxlan configs for CPU traffic
# High Level Design Document
### Rev 1.3

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)

  * [Overview](#overview)
 
  * [Requirements Overview](#5-requirements-overview)

  * [Architecture design](#6-architecture-design)

  * [Cofiguration and management](#7-configuration-and-management)

# 1 Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             |  Bharath Veeranna  | Initial version                   |


# 2 Scope
This document is an extension to the VxLAN feature implementation defined in [VxLAN HLD](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md). This documents specifically deals with kernel routes and interfaces that are required by the CPU to communicate to a VxLAN endpoint. This is for a specific use case where CPU generated packets (such as BGP, ping etc) shoud be encapped/decapped with VxLAN. Transit traffic (which are not destined to CPU) are not in the scope of this document. NPU config required for transit traffic are discussed in [VxLAN HLD](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md).

# 3 Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| BGP                      | Border Gateway Protocol        |
| VNI                      | Vxlan Network Identifier       |
| VTEP                     | Vxlan Tunnel End Point         |
| VNet                     | Virtual Network                |

# 4 Overview
This document provides information about kernel routes required for SONiC to encap/decap VxLAN traffic originated/destined to CPU. For scenarios where SONiC needs to communicate to an endpoint that is behind a VTEP, the kernel needs to be aware of the VTEP and have routes to encap/decap the packets before sending it over the wire. For example, if SONiC needs to establish BGP over VxLAN, the kernel should know the VTEP and overlay routes to send and receive the packet. If the kernel is unaware of the VTEP, it will treat it as unreachable and drop the packets in kernel. 

Currently, SONiC creates kernel routes, bridge and vxlan interfaces for a VNET. For example, consider a VNET `Vnet_1000` as defined below:

```
--- CONFIG_DB
 |--- VNET
 |     |--- Vnet_1000
 |            |--- VNI = 1000
 |            |--- source_tunnel
 |
 |--- VNET_ROUTE_TUNNEL
          |--- Vnet_1000|10.0.0.2/32
                |--- endpoint = 100.100.100.1
                |--- vni = 2000

--- Kernel
  |--- Vnet_1000
         |--- Brvxlan1000  -> A bridge for Vnet that terminates Vxlan and does L2 forwarding
         |--- Vxlan1000 -> vxlan interface
```

For the above config, SONiC creates kernel configs for a L2 bridge and a VxLAN interface. For the vxlan routes that are added using `VXLAN_ROUTE_TUNNEL`, there are no kernel configurations applied. The kernel cannot initiate communication to the vnet endpoints behind VTEP since the kernel interface and routes for these prefixes are not installed on the kernel. This document enhances the VxLAN capabilities of SONiC to have the kernel routes and vxlan P2P interface to communicate with the remote endpoints defined in `VNET_ROUTE_TUNNEL`. This can be used for traffic originated by CPU (like BGP, ping etc) and destined to a remote VTEP endpoint.

Additionally, SONiC may need Loopback interfaces attached to the VNET which can be used as the overlay source for any communication to external VTEPs. 

# 5 Requirements Overview
## 5.1 Functional requirements
This section describes the SONiC requirements for Vxlan kernel interface and routes required for the OS to handle VxLAN encap/decap for traffic originated/destined to CPU.
 - SONiC should be able to encap/decap VxLAN traffic originated/destined to CPU
 - Processes on CPU could leverage these routes to communicate to VxLAN endpoints (establish BGP, ping etc)

## 5.2 Config Manager requirements

### Vnet Manager:
A new component called VnetMgr will be introduced that will handle kernel programming for `VNET_ROUTE_TUNNEL` endpoints. 
- VnetMgr should handle vxlan interface creation and deletion for routes defined in VNET_ROUTE_TUNNEL.
- VnetMgr should install/delete kernel routes for the  VTEP endpoints.

 
## 5.3 CLI requirements
- User should be able to specify if vnet tunnel routes should be installed on kernel.
- User should be able to bind the loopback interface to a VNET

```
  - config vnet add-route <vnet-name> <prefix> <endpoint> <vni> <mac_address> <install_on_kernel>
  - config interface vnet bind <interface> <vnet>
```

# 6 Architecture Design

## 6.1 Config DB
Following new flag will be added to VNET_ROUTE_TUNNEL table to indicate if the flag has to installed on the kernel. By default the flag would be false.

### 6.1.1 VXLAN ROUTE TUNNEL
```
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address}} 
    "mac_address":{{mac_address}} (OPTIONAL) 
    "vni": {{vni}}(OPTIONAL) 
    "install_on_kernel": "true" / "false" (OPTIONAL)
```

### 6.1.2 Loopback interfaces
```
LOOPBACK_INTERFACE_TABLE:{{loopback_name}} 
    "vnet_name": {{vnet_name}}   (OPTIONAL)

LOOPBACK_INTERFACE_TABLE:{{loopback_name}}:{{ip_address}}
```

### 6.1.3 ConfigDB Schemas
```
; Defines schema for VNet Route tunnel table attributes
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = ipv4                          ; Host VM IP address
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet (Optional)
VNI                                   = DIGITS                        ; VNI value in encapsulated packet (Optional)
INSTALL_ON_KERNEL                     = true/false                    ; Indicates if this route should be installed on kernel
```

```
; Defines schema for Loopback interface table
key                                   = LOOPBACK_INTERFACE_TABLE:loopback_name:prefix ; Loopback interface with prefix
; field                               = value
vnet_name                             = string                        ; vnet name
```

Please refer to the [schema](https://github.com/sonic-net/sonic-swss/blob/master/doc/swss-schema.md) document for details on value annotations. 


### 6.2.1 APP DB Schemas

```
; Defines schema for VNet Route tunnel table attributes
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = ipv4                          ; Host VM IP address
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet (Optional)
VNI                                   = DIGITS                        ; VNI value in encapsulated packet (Optional)
INSTALL_ON_KERNEL                     = true/false                    ; Indicates if this route should be installed on kernel
```

## 6.3 Config Manager
A new config manager called VnetMgr will be added which will handle kernel routes programming for `VNET_ROUTE_TUNNEL`. 

 ### VnetMgr
![](https://github.com/sonic-net/SONiC/blob/master/images/vxlan_hld/vxlan_kernel_routes.png)

For the config below:

```
VXLAN_TUNNEL|{{tunnel_name}} 
    "src_ip": {{ip_address}} 
    "dst_ip": {{ip_address}} (OPTIONAL)

VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "src_mac": {{src_mac}}

VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{endpoint_ip_address}} 
    "mac_address":{{overlay_dmac_address}} (OPTIONAL) 
    "vni": {{route_vni}}(OPTIONAL) 
    "install_on_kernel": "true"
```

the following linux kernel interface and routes will be added:

```
sudo ip link add Vxlan{{route_vni}} address {{src_mac}} type vxlan id {{route_vni}} local {{tunnel_src_ip}} remote {{endpoint_ip_address}}
sudo ip link set Vxlan_{{vnet_name}}_{{prefix}} vrf {{vnet_name}}
sudo ip link set Vxlan_{{vnet_name}}_{{prefix}} up
sudo ip route add {{prefix}} dev Vxlan_{{vnet_name}}_{{prefix}} vrf {{vnet_name}}
sudo ip neigh add {{prefix}} lladdr {{overlay_dmac_address}} dev Vxlan_{{vnet_name}}_{{prefix}}
```
 
# 7 Configuration and management

## 7.1 YANG model
Yang model for vnet and loopback will be changed to include the new fields. In [sonic-vnet.yang](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vnet.yang), VNET_ROUTE_TUNNEL will include `install_on_kernel` flag:

```
        container VNET_ROUTE_TUNNEL {

            description "ConfigDB VNET_ROUTE_TUNNEL table";
            
            list VNET_ROUTE_TUNNEL_LIST {
                key "vnet_name prefix";

                leaf vnet_name {
                    description "VNET name";
                    type leafref {
                        path "/svnet:sonic-vnet/svnet:VNET/svnet:VNET_LIST/svnet:name";
                    }
                }
                
                leaf prefix {
                    description "IPv4 prefix in CIDR format";
                    type stypes:sonic-ip4-prefix;
                }
                
                leaf endpoint {
                    description "Endpoint/nexthop tunnel IP";
                    type inet:ipv4-address;
                    mandatory true;
                }

                leaf mac_address {
                    description "Inner dest mac in encapsulated packet";
                    type yang:mac-address;
                }

                leaf vni {
                    description "A valid and active vni value in encapsulated packet";
                    type stypes:vnid_type;
                }

                leaf install_on_kernel {
                    description "Flag to install this route on kernel.";
                    type  boolean;
                }
            }
            /* end of list VNET_ROUTE_TUNNEL_LIST */
        }
```

The yang model for loopback interface [sonic-loopback-interface.yang](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-loopback-interface.yang) will include vnet_name field:

```
            list LOOPBACK_INTERFACE_LIST {
                key "name";

                leaf name{
                    type stypes:interface_name;
                }

                leaf vrf_name {
                    type leafref {
                        path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
                    }
                }

                leaf vnet_name {
                    type leafref {
                        path "/svnet:sonic-vnet/svnet:VNET/svnet:VNET_LIST/svnet:name";
                    }
                }

                leaf nat_zone {
                    description "NAT Zone for the loopback interface";
                    type uint8 {
                        range "0..3" {
                            error-message "Invalid nat zone for the loopback interface.";
                            error-app-tag nat-zone-invalid;
                        }
                    }
                    default "0";
                }

                leaf admin_status {
                    type stypes:admin_status;
                    default up;
                }
            }
```


