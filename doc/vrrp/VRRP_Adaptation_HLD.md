# Virtual Router Redundancy Protocol Adaptation HLD #

## Table of Content 

- [Virtual Router Redundancy Protocol Adaptation HLD](#virtual-router-redundancy-protocol-adaptation-hld)
  - [Table of Content](#table-of-content)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
	  - [Requirements](#requirements)
      - [Functional Requirements](#functional-requirements)
	  - [Feature Description](#feature-description)
      - [Functional Description](#functional-description)
        - [Protocol version selection](#protocol-version-selection)
        - [Pre-emption](#pre-emption)
        - [Virtual Router Owner](#virtual-router-owner)
        - [Virtual MAC Address](#virtual-mac-address)
        - [VRRP Advertisement Frame](#vrrp-advertisement-frame)
        - [Uplink Interface Tracking](#uplink-interface-tracking)
    - [Architecture Design](#architecture-design)
    - [High-Level Design](#high-level-design)
      - [Operating environment](#operating-environment)
      - [Scalability Requirements](#scalability-requirements)
      - [Container](#container)
        - [VRRP container](#vrrp-container)
        - [BGP container](#bgp-container)
        - [SWSS container](#swss-container)
      - [CoPP Configurations](#copp-configurations)
      - [DB changes](#db-changes)
        - [CONFIG_DB changes](#config_db-changes)
        - [APPL_DB changes](#appl_db-changes)
        - [ASIC_DB changes](#asic_db-changes)
      - [Modules Design and Flows](#modules-design-and-flows)
        - [ADD/DEL VRRP instance](#add/del-vrrp-instance)
        - [Tracking interface](#tracking-interface)
    - [SAI API](#sai-api)
    - [Configuration and management](#configuration-and-management)
      - [Manifest](#manifest)
      - [CLI/YANG Model Enhancements](#cliyang-model-enhancements)
        - [SONiC VRRP YANG MODEL](#sonic-vrrp-yang-model)
		- [CLI](#cli)
          - [Config commands](#config-commands)
          - [Show commands](#show-commands)
    - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
    - [Restrictions/Limitations](#restrictionslimitations)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test cases](#unit-test-cases)
    - [Open/Action items](#openaction-items)
 
### Revision  
|  Rev  |  Date            |  Author        | Change Description |
| :---  | :--------------- | :------------- | :----------------  |
|  0.1  |  Aug-16-2023     | Philo-micas    | Initial version    |
| :---  | :--------------- | :------------- | :----------------  |
|  0.2  |  Sept-27-2024    | Vijay-Broadcom | Second version     |


### Scope  

This document describes the high level design of frr-vrrpd adaptation to SONiC.

### Definitions/Abbreviations 

Table 1: Abbreviations

| Abbreviation    | Description                                        |
| :----------     | :------------------------------------------------  |
| VRRP            | Virtual Router Redundency Protocol                 |
| ARP             | Address Resolution Protocol                        |
| FRR             | Free Range Routing Stack                           |
| CLI             | Command Line Interface                             |
| VMAC            | Virtual MAC address                                |
| VIP             | Virtual IP address                                 |
| VRF             | Virtual Routing and Forwarding                     |
| VRID            | Virtual Router Identifier                          |
| VRRP Instance   | An instance of VRRP state machine on an interface. Multiple VRRP state machines can be configured on an interface.         |
| VRRP Owner      | VRRP owner (of a VRRP instance) is the router whose virtual IP address is the same as the real interface IP address        |

### Overview 
This document describes the high level design details of VRRP and its components. VRRP(Virtual Router Redundancy Protocol) specifies an election protocol that dynamically assigns responsibility for a virtual router to one of the VRRP routers on a LAN.
The election provides two basic functionality:
	support dynamic failover in the forwarding responsibility when the Master become unavailable.
	support load sharing among multiple routers by running multiple instances.


### Requirements

#### Functional Requirements

Following requirements are addressed by the design presented in this document:
  1. Support VRRPv2(IPv4) and VRRPv3(IPv4 and IPv6)
  2. Support VRRP on Ethernet, VLAN, sub-interfaces and PortChannel interfaces
  3. Support interface configuration of multiple VRRP instances.
  4. Support configurable priority for VRRP instance
  5. Support configurable preempt mode for VRRP instance
  6. Support uplink interface tracking feature
  7. Support VRRP working on non-default VRF

### Feature Description

FRR has already accomplished the VRRP protocol implementation. The implementation uses Linux macvlan devices to implement the shared virtual MAC feature of the protocol.Each interface on which VRRP will be enabled must have at least one Macvlan device configured with the virtual MAC and placed in the proper operation mode. The addresses backed up by VRRP are assigned to these interfaces.

Suppose you have an interface eth0 with the following configuration:
```
$ ip addr show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 02:17:45:00:aa:aa brd ff:ff:ff:ff:ff:ff
    inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic eth0
       valid_lft 72532sec preferred_lft 72532sec
    inet6 fe80::17:45ff:fe00:aaaa/64 scope link
       valid_lft forever preferred_lft forever
```
Suppose that the IPv4 and IPv6 addresses you want to back up are 10.0.2.16 and 2001:db8::370:7334, and that they will be managed by the virtual router with id 5. A Macvlan device with the appropriate MAC address must be created before VRRP can begin to operate.

If you are using iproute2, the configuration is as follows:
```
ip link add vrrp4-2-1 link eth0 addrgenmode random type macvlan mode bridge
ip link set dev vrrp4-2-1 address 00:00:5e:00:01:05
ip addr add 10.0.2.16/24 dev vrrp4-2-1
ip link set dev vrrp4-2-1 up

ip link add vrrp6-2-1 link eth0 addrgenmode random type macvlan mode bridge
ip link set dev vrrp6-2-1 address 00:00:5e:00:02:05
ip addr add 2001:db8::370:7334/64 dev vrrp6-2-1
ip link set dev vrrp6-2-1 up
```
The created interfaces will look like this:
```
$ ip addr show vrrp4-2-1
5: vrrp4-2-1@eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 00:00:5e:00:01:05 brd ff:ff:ff:ff:ff:ff
    inet 10.0.2.16/24 scope global vrrp4-2-1
       valid_lft forever preferred_lft forever
    inet6 fe80::dc56:d11a:e69d:ea72/64 scope link stable-privacy
       valid_lft forever preferred_lft forever

$ ip addr show vrrp6-2-1
8: vrrp6-2-1@eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
 link/ether 00:00:5e:00:02:05 brd ff:ff:ff:ff:ff:ff
 inet6 2001:db8::370:7334/64 scope global
    valid_lft forever preferred_lft forever
 inet6 fe80::f8b7:c9dd:a1e8:9844/64 scope link stable-privacy
    valid_lft forever preferred_lft forever
```
a few things to note about this interface:
- It is slaved to eth0; any packets transmitted on this interface will egress via eth0
- Its MAC address is set to the VRRP virtual MAC specified by the RFC for VRID 5
- The VIP address 10.0.2.16 must not be present on the parent interface eth0
- The link local address on the interface is not derived from the interface MAC

#### Functional Description

##### Protocol version selection

Optionally specify the protocol version(VRRPv2 or VRRPv3). If the protocol version is not specified, the default is VRRPv3. Note that VRRPv2 does not support IPv6, so any IPv6 configuration will be rejected by FRR when using VRRPv2.

##### Pre-emption

Toggle preempt mode. When enabled, preemption allows Backup routers with higher priority to take over Master status from the existing Master. Enabled by default.

##### Virtual Router Owner

VRRP instance whose virtual IP address (VIP) is same as real interface address is called the owner of virtual router and has the highest priority (255). VRRP owner is supported in SONIC's VRRP implementation. VRRP owner node will pre-empt the active master even when pre-emption is disabled for that particular VRRP instance.

##### Virtual MAC Address

Following virtual MAC address is used by the protocol (as per RFC 5798)

IPv4 case: 00-00-5e-00-01-{vrid}

IPv6 case: 00-00-5e-00-02-{vrid}

where, vrid is user configured 1-byte virtual router identifier. VRID has interface scope; that is, VRID has to be unique among the VRRP instances on an interface.

##### VRRP Advertisement Frame

VRRP control packets have IP protocol type as 112 (reserved for VRRP), for IPv4 network, are sent to VRRP multicast address 224.0.0.18, source MAC in VRRP control packets is virtual MAC address and source IP is interface IP (not the virtual IPv4 address). For IPv6 networks, the source address in the VRRPv6 header is the IPv6 link local address of the sending interface, and the destination address is the IPv6 multicast address FF02:: 02/64 assigned by IANA.

##### Uplink Interface Tracking

The fault point which VRRP safeguards against is the interface on which VRRP instance is present. Even if all of the connectivity of master to the external network fails, VRRP will still not trigger the failover to the backup gateway. Uplink interface tracking feature has been introduced to overcome this limitation.

![VRRP Tracking Interface Scenarios](images/VRRP_Tracking_Interface_Scenarios_Diagram.png "Figure 1: VRRP Tracking Interface Scenarios")

As shown in the figure，Configure VRRP backup groups between RouterA and RouterB, Both RouterA and RouterB operate in preemptive mode. On RouterA, configure to monitor the uplink interface Interface1. When Interface1 fails, RouterA lowers its priority and, through packet negotiation, RouterB preempts and becomes the Master, ensuring that user traffic is forwarded normally.

### Architecture Design 

Below diagram illuminates the interactions between relevant components and the DB involved for VRRP support in SONiC architecture at a high level.

![VRRP Architecture](images/VRRP_Architecture_Diagram.png "Figure 2: VRRP in SONiC Architecture")

Diagram 1. VRRP components.

### High-Level Design

#### Operating environment

Since support for placing macvlan devices into protodown was not added to Linux until version 5.1, the kernel version is required:
- Linux kernel version 5.1+

#### Scalability Requirements

- Max number of VRRP instances: 254
- Max number of VIPS per instance: 4

#### Container

##### BGP container

vrrpd:
  - Responsible for all VRRP protocol related calculations. VRRP packets are sent and received in vrrpd and states are updated accordingly.
  - Match VRRP instance tracking interface and recalculate priority.

zebra:
  - Provide an API for vrrpd to update kernel Macvlan device state.
  - Listen for kernel interface state change events and notify vrrpd.

vrrpsyncd:
  - Listens to MACVLAN interfaces that are added by vrrp, programming in kernel. Vrrpmgrd would add the MACVLAN interface in the kernel with interface name starting with 'vrrp'. Here the status of MACVLAN interface determines Master/Backup state of VRRP instances. VRRP_Table in APPL_DB will be programmed with interface name and VIP for Master instances.
    - For every IP add to MACVLAN interface, adds interface name and Virtual IP in APPL_DB in VRRP_Table.
    - For every IP delete from MACVLAN interface, deletes interface name and Virtual IP in APPL_DB from VRRP_Table.

##### SWSS container

vrrpmgrd:
  - Listens to VRRP create, delete and parameter change in CONFIG_DB. Complete the following tasks:
    - Add/del Linux Macvlan device to kernel. The Macvlan device name starting with 'Vrrp4-' or 'Vrrp6-'.
    - Config virtual MAC to Macvlan device;
    - Add/del VIP to Macvlan device;
    - Update VRRP instance configuration to the APPL DB;
    - Update VRRP instance configuration to vrrpd by using vtysh commands.

vrrporch: 
  - Listens to VRRP_Table in APPL_DB and for entry in VRRP_TABLE, program the VIP as my IP and the VMAC as my MAC(virtual RIF) in ASIC_DB.

#### CoPP Configurations

CoPP will be extended as follows for trapping VRRPs. Whether to install it depends on the FEATURE|vrrp table in Config DB. If the VRRP state is enabled, it will be installed; otherwise, it will not be installed.
```
  "trap.group.vrrp": {
    "cir":"300",
    "cbs":"300",
    "meter_type":"packets",
    "mode":"sr_tcm",
    "red_action":"drop",
    "trap_action":"trap",
    "trap_priority":"7",
    "queue": "7",
    "yellow_action":"drop"
  },
  ...
  "vrrp": {
    "trap_ids": "vrrp", "vrrpv6",
    "trap_group": "trap.group.vrrp"
  },
```

#### DB Changes

##### CONFIG_DB changes

VRRP_TABLE

Producer: config manager

Consumer: vrrpmgrd

Description: New table that stores VRRP configuration for per interface + VRID.

Schema:

```
;New table
;holds the VRRP configuration per interface and VRID

key = VRRP_type:interface_name:vrid
                          ; VRRP_type can be VRRP or VRRP6 to distinguish vrrpv4 or vrrpv6
                          ; Interface name string like Vlan1 or PortChannel002 or Ethernet4
                          ; vrid is an integer
; field = value
vrid     = 1*3DIGIT       ; VRRP Instance Identifier
vip      = ip_address     ; Virtual IP address. This is a list of IP addresses
priority = vrrp_priority  ; Priority of VRRP instance
adv_interval = 1*3DIGITS  ; Advertisement interval for VRRP. Default = 1sec
version  = vrrp_version   ; VRRP version. Value will always be 2 for this release
pre_empt = "true"/"false" ; VRRP pre-emption is enabled? Default is True
track_interface = track_interface ; List of interfaces tracked by a VRRP instance
  <Interface_Name>|weight|<weight>; This is repeated for the configured tracking interfaces 
```

Example:-

admin@sonic:~$ redis-cli -n 4 keys VRRP*

1.	"VRRP|Vlan8|8"
2.	"VRRP|Vlan1|1"
3.	"VRRP|Vlan10|10"
4.	"VRRP|Vlan2|2"
5.	"VRRP|Vlan4|4"
6.	"VRRP|Vlan5|5"
7.	"VRRP6|Vlan3|3"
8.	"VRRP6|Vlan7|7"
9.	"VRRP6|Vlan6|6"
10.	"VRRP6|Vlan9|9"

admin@sonic:~$ redis-cli -n 4 HGETALL "VRRP|Vlan1|1"

1.	"vrid"
2.	"1"
3.	"vip"
4.	"4.1.1.100"
5.	"priority"
6.	"80"
7.	"adv_interval"
8.	"1"
9.	"version"
10.	"2"
11.	"pre_empt"
12.	"True"
13.	"track_interface"
14.	"Ethernet7|weight|10,PortChannel001|weight|10"

Example:- Entery with multiple virtual IPs

admin@sonic:~$ redis-cli -n 4 HGETALL "VRRP6|Vlan1|1"

1.	"vrid"
2.	"1"
3.	"vip"
4.	"4::100,4::200,4::201"
5.	"priority"
6.	"80"
7.	"adv_interval"
8.	"1"
9.	"pre_empt"
10.	"True"
11.	"track_interface"
12.	"Ethernet7|weight|10,PortChannel001|weight|10"

#### APPL_DB Changes

VRRP_TABLE

Producer: vrrpmgrd and vrrpsyncd

Consumer: vrrporch

Description: This is a new table that contains VRRP state information. This entry will be added to APP_DB for each VIP for every Master VRRP instance.

Schema:

```
; New table
; holds the VRRP state and VMAC information

key = VRRP_TABLE:interface_name:vip:type
    interface_name        ; interface name as a string. Vlan, Ethernet or PortChannel
    vip                   ; virtual IP address in a.b.c.d/32 or a::b/128 format
    type                  ; IPv4 or IPv6 address type string.
    
; field = value
vmac = virtual_mac_address ; Virtual MAC address associated with VRRP instance
```

Example:-

Key: VRRP_TABLE:Vlan1000|40.10.8.101/32 Value: "vmac":"00:00:5e:00:01:08"

Key: VRRP_TABLE:Vlan1001|40::1/128 Value: "vmac":"00:00:5e:00:02:08"

#### ASIC_DB Changes

Example:-
```
admin@sonic:~$ redis-cli -n 1 hgetall "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:oid:0x6000000000a80"
 1) "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID"
 2) "oid:0x300000000003a"
 3) "SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS"
 4) "00:00:5E:00:01:06"
 5) "SAI_ROUTER_INTERFACE_ATTR_TYPE"
 6) "SAI_ROUTER_INTERFACE_TYPE_PORT"
 7) "SAI_ROUTER_INTERFACE_ATTR_PORT_ID"
 8) "oid:0x1000000000025"
 9) "SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL"
10) "true"
```

#### Modules Design and Flows

##### ADD/DEL VRRP instance

![VRRP ADD/DEL VRRP instance Flows](images/VRRP_Config_Instance_Flow.png)

vrrpmgrd:
  - Listens to VRRP create, delete and parameter change in CONFIG DB
  - Upon change
    - Add/del VRRP instance corresponding Macvlan device to kernel with IPs and state.
    - Updates VRRP instance configuration to the APPL DB, such as Macvlan device name and Vip.
    - Update changes to vrrpd by using vtysh commands

vrrpd:
  - Listens to VRRP create, delete and parameter change in vrrpcfgd
  - Run VRRP state machine
    - For VRRP instances state transition to Master, set the Macvlan device into protodown off
    - For VRRP instances state transition to non-Master, set the Macvlan interface into protodown on

vrrpsyncd:
  - Listens to Macvlan interface programming in kernel. 
  - Update the kernel Macvlan device's state to the INTF_table entry of APPL DB.

intforch:
  - Listens to INTF_Table in APP_DB and updates Vip and virtual MAC entries in ASIC_DB for VRRP instances

##### Uplink interface tracking

![VRRP Tracking interface Flows](images/VRRP_Tracking_Interface_Flow.png)

zebra:
  - Listen for interfaces state change events notified by the kernel.
  - Notify interface state change events to vrrpd.

vrrpd:
  - Match VRRP instance tracking interface and recalculate priority
    - If track interface goes down, the priority of VRRP instance will be reduced by weight
    - If track interface goes up, the priority of VRRP instance will be added by weight
  - Update VRRP packet priority field
  - Send VRRP packet to Linux Network stack

### SAI API 

VRRP virtual router interface can be created by setting the attribute “SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL” with create_router_interface API.
```
 * @brief RIF creation is a virtual RIF.
 *
 * Create a Virtual RIF object, which only programs the ingress router MAC.
 * This simplifies the management of VRRP master router's configuration in
 * SAI adapter, as defined by RFC 5798 (or similar proprietary protocols).
 * Using a Virtual RIF allows SAI to optimize resources, so neighbor entries
 * cannot be learned on a Virtual RIF. On a virtual RIF following attributes
 * are invalid: ADMIN state, MTU size, packet action and multicast enable.
 * Alternatively VRRP can also be configured using native RIF objects without
 * using VIRTUAL attribute, with the expectation that SAI adapter will consume
 * resources that will not be used.
 *
 * @type bool
 * @flags CREATE_ONLY
 * @default false
 */

SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL,

```
Considering that some particular vendor SAI implementations may not support this attribute. Use sai_query_attribute_capability to judge if ASIC platform support SAI_ROUTER_INTERFACE_ATTR_IS_VIRTUAL attribute. if not support, the attribute will not added when createvirtual interface with sai interface.

### Configuration and management 

#### Manifest

N/A

#### CLI/YANG Model Enhancements

##### SONiC VRRP YANG MODEL

VRRP configuration database scheme is as defined in below yang

https://github.com/sonic-net/SONiC/blob/a58bacebb3362f611818cd3a15042f09366bb5d5/doc/vrrp/sonic-vrrp.yang

##### CLI

SONIC Click based configuration and monitoring CLIs have been introduced in SONIC for VRRP

###### Config commands

- config interface vrrp add/remove <interface_name> <vrrp_id>
    - This command adds/ removes a VRRP instance on an interface.
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
- config interface vrrp backup_forward <interface_name> <vrrp_id> enabled|disabled
    - This command configures  enables/disables the VRRP instance to forward service traffic even if the VRRP instance in the backup state
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - backup_forward: VRRP instance forwarding traffic in the backup state，can be enabled or disabeld. default is disabled.
- config interface vrrp vip add/remove <interface_name> <vrrp_id> <virtual_ip_address>
    - This command adds a virtual IP address for a VRRP instance on an interface.
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - virtual_ip_address: VIP address in dotted decimal IPv4 or IPv6 address
- config interface vrrp priority <interface_name> <vrrp_id> <priority>
    - This command configures priority for a VRRP instance
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - priority: VRRP instance priority, range from 1 to 254, default is 100
- config interface vrrp adv_interval <interface_name> <vrrp_id> <interval>
    - This command configures VRRP periodic advertisement interval for a VRRP instance
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - Interval: VRRP instance packet sending interval, range from 10 to 40950, unit: ms, default is 1000
- config interface vrrp pre_empt enable/disable <interface_name> <vrrp_id>
    - This command enables pre-emption of a Master when a higher priority VRRP router arrives
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
- config interface vrrp track_interface add/remove <interface_name> <vrrp_id> <track_interface>
    - This command adds a track interface to a VRRP Instance.
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - track_interface: Interface to track. Interface can be Ethernet/Vlan/PortChannel
- config interface vrrp priority_decrement <interface_name> <vrrp_id> <decrement_value>
    - This command configures priority_decrement for a VRRP instance
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.
    - decrement_value: decrement the priority of the VRRP instance if the tracking interface goes down. range from 10 to 50, default is 20
- config interface vrrp shutdown/startup <interface_name> <vrrp_id>
    - This command control up/down status of VRRP instance.
    - interface_name:name of interface (Ethernet/Vlan/PortChannel/sub-interface).
    - vrrp_id:VRRP instance identifier.

###### Show commands
- show vrrp {interface <interface_name> } | <vrrp_id>
- show vrrp summary

```
admin@sonic:~$ show vrrp interface Ethernet50

 Virtual Router ID                    5                   
 Protocol Version                     3                   
 Autoconfigured                       No                  
 Shutdown                             No                  
 Interface                            Ethernet50          
 VRRP interface (v4)                  Vrrp4-5             
 VRRP interface (v6)                  None                
 Primary IP (v4)                      10.0.0.98           
 Primary IP (v6)                      ::                  
 Virtual MAC (v4)                     00:00:5e:00:01:05   
 Virtual MAC (v6)                     00:00:5e:00:02:05   
 Status (v4)                          Master              
 Status (v6)                          Initialize          
 Priority                             100                 
 Effective Priority (v4)              100                 
 Effective Priority (v6)              100                 
 Preempt Mode                         Yes                 
 Accept Mode                          Yes                 
 Advertisement Interval               1000 ms             
 Master Advertisement Interval (v4)   1000 ms             
 Master Advertisement Interval (v6)   0 ms                
 Advertisements Tx (v4)               95                  
 Advertisements Tx (v6)               0                   
 Advertisements Rx (v4)               0                   
 Advertisements Rx (v6)               0                   
 Gratuitous ARP Tx (v4)               1                   
 Neigh. Adverts Tx (v6)               0                   
 State transitions (v4)               2                   
 State transitions (v6)               0                   
 Skew Time (v4)                       600 ms              
 Skew Time (v6)                       0 ms                
 Master Down Interval (v4)            3600 ms             
 Master Down Interval (v6)            0 ms                
 IPv4 Addresses                       1                   
 ..................................   10.10.10.10         
 IPv6 Addresses                       0       

admin@sonic:~$ show vrrp summary 

 Interface    VRID   Priority   IPv4   IPv6   State (v4)   State (v6)   
 -----------------------------------------------------------------------
 Ethernet48   6      100        1      0      Backup       Backup       
 Ethernet50   5      100        1      0      Master       Backup    
```

### Warmboot and Fastboot Design Impact  

Warm boot will not be supported. The VRRPv2 (RFC 3768) and VRRPv3 (RFC 5798) standard of VRRP does not define a way to support it as this might cause data flow interruption in the network.

If a user tries to perform a warm boot while VRRP is enabled, an error message will be displayed. User will first need to disable VRRP so the VRRP topology to reelect the Master.

### Restrictions/Limitations

Currently, due to the limitations of FRR, the following functions are not supported:
  1. Virtual Router Owner
  2. Accept Mode configurable function

### Testing Requirements/Design  

#### Unit Test cases  

Unit test cases for this specification are as listed below:
|   Test Cases                  |  UT Action and observation                                                                              |  Remarks  |
| :---------------------------  | :------------------------------------------------------------------------------------                   | :------   |
|  Configuration                |                                                                                                         |           |
|                               |  Validate IPv4 VRRP config on Ethernet/Vlan/PortChannel Interface                                       |           |
|                               |  Validate IPv6 VRRP config on Ethernet/Vlan/PortChannel Interface                                       |           |
|                               |  Validate VRRP on more than one interface                                                               |           |
|                               |  Validate VRRP with more than one VIP per instance                                                      |           |
|                               |  Validate multiple VRRP instance per interface                                                          |           |
|                               |  Validate VMAC is programmed in FDB                                                                     |           |
|                               |  Validate macvlan device is configured in kernel                                                        |           |
|                               |  Validate that VMAC is generated based on VRID                                                          |           |
|                               |  Validate the VRRP packet version is the configuration version                                          | The default version is 3 |
|                               |  Validate the VRRP periodic advertisement interval is the configuration interval time                   | The default advertisement interval is 1000ms |
|  Ping to VIP                  |                                                                                                         |           |
|                               |  Validate ping to VRRP VIP from host, master & non vrrp router works                                    |           |
|  L3 Forwarding with VIP as GW |                                                                                                         |           |
|                               |  Validate that IPv4 traffic forwarding with VIP as gateway works from source to destination host        |           |
|                               |  Validate that IPv6 traffic forwarding with VIP as gateway works from source to destination host        |           |
|                               |  Perform VRRP master failover and check if traffic forwarding continues with new master                 |           |
|  Load Sharing                 |                                                                                                         |           |
|                               |  Perform multiple vrrp instances on one devices to do load sharing, all master can work independently   |           |
|  Uplink Interface Tracking    |                                                                                                         |           |
|                               |  Enable interface tracking in a VRRP group with priority, bring down the port and ensure VRRP session priority comes down and session transition from Master to Backup State    |  |
|                               |  Bring up the tracked interface and check if session priority gets restored and session becomes master  |           |

### Open/Action items

N/A
