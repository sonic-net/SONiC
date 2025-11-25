# Vxlan configs for CPU traffic
# High Level Design Document
### Rev 1.3

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#1-revision)

  * [Scope](#2-scope)

  * [Definitions/Abbreviation](#3-definitionsabbreviation)

  * [Overview](#4-overview)

  * [Usecase](#5-usecase)
 
  * [Requirements](#6-requirements-overview)

  * [Architecture design](#7-architecture-design)

  * [Limitations](#8-limitations)

  * [Cofiguration and management](#9-configuration-and-management)

  * [Test plan](#10-test-plan)

  * [Example configuration and outputs](#11-example-configuration-and-outputs)

# 1 Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |  11/25/2025 |  Bharath Veeranna  | Initial version                   |


# 2 Scope
This document is an extension to the VxLAN feature implementation defined in [VxLAN HLD](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md). This documents specifically deals with kernel routes and interfaces that are required by the CPU to communicate to a VxLAN endpoint. This is for a specific use case where CPU generated packets (such as BGP, ping etc) shoud be encapped/decapped with VxLAN. Transit traffic (which are not destined to CPU) are not in the scope of this document. NPU config required for transit traffic are discussed in [VxLAN HLD](https://github.com/sonic-net/SONiC/blob/master/doc/vxlan/Vxlan_hld.md).

# 3 Definitions/Abbreviation
###### Table 1: Abbreviations
|                          |                                |
|--------------------------|--------------------------------|
| BGP                      | Border Gateway Protocol        |
| P2P                      | Point to Point                 |
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

# 5 Usecase

Consider a sample vnet configuration as below:
```
    "VNET": {
        "Vnet_test": {
            "vni": "1000",                  // VNET's VNI is 1000  
            "vxlan_tunnel": "tunnel_v4"
        }
    },
    "VNET_ROUTE_TUNNEL": {
        "Vnet_test|20.0.0.2/32": {
            "endpoint": "200.200.200.2",
            "vni": "1000"                  // Route uses same VNI as VNET
        },
        "Vnet_test|20.0.0.3/32": {
            "endpoint": "200.200.200.3",
            "vni": "2000"                  // Route has VNI 2000
        }
    }
```

In the above config, there is a VNET with name `Vnet_test` having a VNI `1000`. When this VNET is created, SONiC creates a linux bridge and vxlan interface on the kernel to encap and decap vxlan packets with VNI 1000. The above config also has two routes in the same VNET: one route to 20.0.0.2 behind a VTEP 200.200.200.2 having VNI 1000 and another route to 20.0.0.3 behind a VTEP having VNI 2000.

Consider a usecase where SONiC has to establish BGP to both the devices: 20.0.0.2 and 20.0.0.3. CPU can initiate traffic to endpoints in this VNET which have the same VNI as the VNET since the kernel routes and interfaces are configured. For example, SONiC can send/receive traffic to 20.0.0.2 VM which is behind VTEP 200.200.200.2 using VNI 1000. So SONiC can establish BGP session with 20.0.0.2 device on the VNET.

However, the VM having IP 20.0.0.3 is behind a VTEP 200.200.200.3 having VNI 2000. SONiC does not have any kernel routes and interfaces configured for VNI 2000. Any traffic destined to 20.0.0.3 will be dropped in the kernel since there are no routes or interfaces configured for VxLAN 2000. 

# 6 Requirements Overview
## 6.1 Functional requirements
This section describes the SONiC requirements for Vxlan kernel interface and routes required for the OS to handle VxLAN encap/decap for traffic originated/destined to CPU.
 - SONiC should be able to encap/decap VxLAN traffic originated/destined to CPU
 - Processes on CPU could leverage these routes to communicate to VxLAN endpoints (establish BGP, ping etc)

## 6.2 Config Manager requirements

### Vnet Manager:
A new component called VnetMgr will be introduced that will handle kernel programming for `VNET_ROUTE_TUNNEL` endpoints. 
- VnetMgr should handle vxlan interface creation and deletion for routes defined in VNET_ROUTE_TUNNEL.
- VnetMgr should install/delete kernel routes for the  VTEP endpoints.
- VnetMgr should subscribe to CONFIG_DB changes to VNET_ROUTE_TUNNEL and update the same in APPL_DB

 
## 6.3 CLI requirements
- User should be able to specify if vnet tunnel routes should be installed on kernel.

```
  config vnet add-route <vnet-name> <prefix> <endpoint> <vni> <mac_address> <install_on_kernel>
```

## 6.4 Scale requirement

SONiC will support a maximum of 2000 kernel configs for `VNET_ROUTE_TUNNEL`. Kernel config includes the vxlan P2P interface and the kernel routes for the prefix defined in the `VNET_ROUTE_TUNNEL`.

# 7 Architecture Design

## 7.1 Config DB
Following new flag will be added to VNET_ROUTE_TUNNEL table to indicate if the flag has to installed on the kernel. By default the flag will be false.

### 7.1.1 VXLAN ROUTE TUNNEL
```
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address}} 
    "mac_address":{{mac_address}} (OPTIONAL) 
    "vni": {{vni}}(OPTIONAL) 
    "install_on_kernel": "true" / "false" (OPTIONAL)
```

### 7.1.3 ConfigDB Schemas
```
; Defines schema for VNet Route tunnel table attributes
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = ipv4                          ; Host VM IP address
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet (Optional)
VNI                                   = DIGITS                        ; VNI value in encapsulated packet (Optional)
INSTALL_ON_KERNEL                     = true/false                    ; Indicates if this route should be installed on kernel
```


Please refer to the [schema](https://github.com/sonic-net/sonic-swss/blob/master/doc/swss-schema.md) document for details on value annotations. 


### 7.2.1 APP DB Schemas

```
; Defines schema for VNet Route tunnel table attributes
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = ipv4                          ; Host VM IP address
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet (Optional)
VNI                                   = DIGITS                        ; VNI value in encapsulated packet (Optional)
INSTALL_ON_KERNEL                     = true/false                    ; Indicates if this route should be installed on kernel
```

## 7.3 Config Manager
A new config manager called VnetMgr will be added which will handle kernel routes programming for `VNET_ROUTE_TUNNEL`. 

 ### VnetMgr
VnetMgr is a new config manager introduced to handle the config changes for `VNET_ROUTE_TUNNEL`. VnetMgr will do the following:

- Subscribe for config changes to `VNET_ROUTE_TUNNEL`
- Handle kernel interface and route (create and delete) if the routes have `install_on_kernel` flag is set.
- Publish the routes to APPL_DB

The diagram below shows the flow for the route creation:

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

the following linux kernel interface and routes will be added by the VnetMgr:

```
sudo ip link add Vxlan{{route_vni}} address {{src_mac}} type vxlan id {{route_vni}} local {{tunnel_src_ip}} remote {{endpoint_ip_address}}
sudo ip link set Vxlan_{{vnet_name}}_{{prefix}} vrf {{vnet_name}}
sudo ip link set Vxlan_{{vnet_name}}_{{prefix}} up
sudo ip route add {{prefix}} dev Vxlan_{{vnet_name}}_{{prefix}} vrf {{vnet_name}}

(OPTIONAL: only if the prefix is /32 IPv4 or /128 IPv6, the MAC entry will be added)
sudo ip neigh add {{prefix}} lladdr {{overlay_dmac_address}} dev Vxlan_{{vnet_name}}_{{prefix}}
```

## 7.4 Orch Agent

### VNetCfgRouteOrch
VNetCfgRouteOrch is an orch agent that currently subscribes to the CONFIG_DB tables: VNET_ROUTE_TUNNEL_TABLE and VNET_ROUTE_TABLE. This orch agent publishes the entries from these two tables to the APPL_DB. This orch agent is just a pass through which publishes to APPL_DB. This orch agent will be removed completely and the functionality performed by this orch agent will be handled by VnetMgr as described in the above section. 

In addition to the tasks mentioned in the previous section, VnetMgr will also do the following tasks that are currently performed by VNetCfgRouteOrch:
- Subscribe to VNET_ROUTE CONFIG_DB table and publish to APPL_DB
- Subscribe to VNET_ROUTE_TUNNEL CONFIG_DB table and publish to APPL_DB

## VNetRouteOrch
There are no changes to VNetRouteOrch. This orch agent performs the south-bound programming of the vnet routes in the NPU. 

# 8 Limitations
- Linux kernel allows only one vxlan interface per VNI. There can be at most one `VNET_ROUTE_TUNNEL` with a given  VNI and `install_on-kernel: true`. In other words, two routes having same VNI cannot have `install_on_kernel` flag set to true.
- Kernel interface and routes will be created for `VNET_ROUTE_TUNNEL` only if the VNI specified in the route is differnet from the VNET's VNI. This is because, when VNET is created, there is a default vxlan interface created for the VNET using the VNI specified in the VNET. Hence when the the tunnel routes are created using the same VNI as the VNET, there is no need to create another interface with the same VNI (kernel will not accept new interface since there is already an interface with the same VNI).
- If `VNET_ROUTE_TUNNEL` has overlay dmac specified, a static mac entry will be added in the kernel only if it is a /32 IPv4 or /128 IPv6 route. 


# 9 Configuration and management

## 9.1 YANG model
Yang model for vnet will be changed to include the new fields. In [sonic-vnet.yang](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vnet.yang), VNET_ROUTE_TUNNEL will include `install_on_kernel` flag:

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

# 10 Test Plan

Pre-requisite:

Create VNET and Vxlan tunnel as an below:

```
{ 
    "VXLAN_TUNNEL": {
        "tunnel_v4": {
            "src_ip": "10.1.0.32"
        }
    },

    "VNET": {
        "Vnet_3000": {
            "vxlan_tunnel": "tunnel_v4",
            "vni": "3000",
            "scope": "default"
        }
    }
}
```
Similarly for IPv6 tunnels

```
{ 
    "VXLAN_TUNNEL": {
        "tunnel_v6": {
            "src_ip": "fc00:1::32"
        }
    },

    "VNET": {
        "Vnet_3001": {
            "vxlan_tunnel": "tunnel_v6",
            "vni": "3001",
            "scope": "default"
        }
    }
}
```

The below testcases will be executed for both IPv4 and IPv6 routes.

| Step | Goal | Expected results |
|-|-|-|
| Create a tunnel route with a /32 IPv4 or /128 IPv6 with install_on_kernel to true, specify overlay dmac in the route| Kernel route creation with static ARP/ND entry| Kernel vxlan interface and routes should be created with nexthop as the endpoint defined in the route. Static ARP/ND entry should be added for the route with the dmac mentioned in the route.|
| Create a tunnel route which is not /32 IPv4 or /128 IPv6 address. Set install_on_kernel to true with overlay dmac specified in the route | Kernel route creation without static ARP/ND entry | Kernel routes will be created if the install_on_kernel is true. But the ARP/ND entry will not created since the route is not for /32 IPv4 or /128 IPv6 address|
| Create a tunnel route without the install_on_kernel flag. After the route is created, update the route with install_on_kernel = true | Route update should install the kernel routes| When the route is created initially, the kernel should not have the vxlan interface and the routes. After the route is updated with the flag, verify if the kernel routes are created|
| Create a tunnel route with install_on_kernel = true. Update the route to set install_on_kernel = false | Route update should delete the kernel routes and interfaces when the install_on_kernel is removed from the route| When the route is created initially, kernel should have a vxlan interface and routes. After the route is updated, the kernel interface and route should be removed |
| Create a tunnel route with same VNI as the VNET and have install_on_kernel = true | Tunnel routes with same VNI as the VNET should not have additional kernel routes | If the tunnel route is having the same VNI as the VNET, then there is no additional kernel configs required. This is because the vxlan interface for the VNET's VNI is created during VNET creation| 
| Create multiple routes using differnet VNIs on the same VNET and all of the routes are having install_on_kernel = true. All routes will have different VNIs and also different from VNET's VNI | Kernel should support multiple vxlan interfaces in the same VNET | Verify that each route get configured on the kernel with a unique vxlan interface and all the routes are programmed on the kernel |
| Create multiple routes with same VNI (but different from VNET's VNI). Set install_on_kernel = true on all the routes | Kernel should have only one interface per VNI | Verify that the first route that is created will have kernel routes. Subsequent routes created will not have kernel interface or routes added |
| Delete tunnel routes that were created with install_on_kernel = true | Kernel config should be cleaned up after route delete | Verify that the kernel routes are deleted when the tunnel route config are removed |


# 11 Example configuration and outputs

Consider a sample config for a VNET `Vnet500` having VNI 5000. 
```
{
    "LOOPBACK_INTERFACE": {
        "Loopback20": {},
        "Loopback20|10.2.146.116/32": {}
    },
    "VXLAN_TUNNEL": {
        "Vxlan0": {
            "src_ip": "10.2.146.116"
        }
    },
    "VNET": {
        "Vnet5000": {
            "vni": "5000",
            "vxlan_tunnel": "Vxlan0",
            "src_mac": "12:34:56:78:9a:bc"
        }
    },
    "VNET_ROUTE_TUNNEL": {
        "Vnet5000|100.100.100.2/32": {
            "endpoint": "10.2.146.117",
            "mac_address": "00:12:34:56:78:9a",
            "vni": "4000",
            "install_on_kernel": "true"
        }
    },
    "VLAN": {
        "Vlan100": {
            "vlanid": "100"
        }
    },
    "VLAN_INTERFACE": {
        "Vlan100": {
            "vnet_name": "Vnet5000"
        },
        "Vlan100|100.100.100.1/24": {}
    }
}
```

For the above config, since the tunnel route for prefix `100.100.100.2/32` has `install_on_kernel` set to true, the following kernel routes will be installed:

```
sudo ip link add Vxlan4000 address 12:34:56:78:9a:bc type vxlan id 4000 local 10.2.146.116 remote 10.2.146.117 dstport 4789 
sudo ip link set Vxlan4000 vrf Vnet5000
sudo ip link set Vxlan4000 up
sudo ip route add 100.100.100.2/32 dev Vxlan4000 vrf Vnet5000
sudo ip neigh add 100.100.100.2/32 lladdr 00:12:34:56:78:9a dev Vxlan4000
```

Output of kernel configs:

```
admin@sonic:~$ show vnet routes all
vnet name    prefix            nexthop    interface
-----------  ----------------  ---------  -----------
Vnet5000     100.100.100.0/24  0.0.0.0    Vlan100
Vnet5000     100.100.100.2     0.0.0.0    Vxlan4000

vnet name    prefix            endpoint      mac address          vni
-----------  ----------------  ------------  -----------------  -----
Vnet5000     100.100.100.2/32  10.2.146.117  00:12:34:56:78:9a   5000
admin@sonic:~$ 

admin@sonic:~$ sudo ip link show Vxlan4000
214: Vxlan4000: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master Vnet5000 state UNKNOWN mode DEFAULT group default qlen 1000
    link/ether 12:34:56:78:9a:bc brd ff:ff:ff:ff:ff:ff
admin@sonic:~$

admin@sonic:~$ sudo ifconfig Vxlan4000
Vxlan4000: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet6 fe80::1034:56ff:fe78:9abc  prefixlen 64  scopeid 0x20<link>
        ether 12:34:56:78:9a:bc  txqueuelen 1000  (Ethernet)
        RX packets 10616  bytes 667730 (652.0 KiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 9387  bytes 603940 (589.7 KiB)
        TX errors 591  dropped 0 overruns 0  carrier 591  collisions 0

admin@sonic:~$

admin@sonic:~$ sudo arp -a 
? (100.100.100.2) at 00:12:34:56:78:9a [ether] PERM on Vxlan4000
admin@sonic:~$

admin@sonic:~$ sudo bridge fdb show | grep -i vxlan
00:00:00:00:00:00 dev Vxlan4000 dst 10.2.146.117 self permanent
00:12:34:56:78:9a dev Vxlan4000 dst 10.2.146.117 self
admin@sonic:~$

admin@sonic:~$ ip route show vrf Vnet5000
100.100.100.0/24 dev Vlan100 proto kernel scope link src 100.100.100.1 
100.100.100.2 dev Vxlan4000 scope link
admin@sonic:~$
```