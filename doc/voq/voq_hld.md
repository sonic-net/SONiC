# VOQ SONiC
# High Level Design Document
### Rev 1.2

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
    * [1.2 Configuration requirements](#12-configuration-requirements)
    * [1.3 Orchagent requirements](#13-orchagent-requirements)
    * [1.4 Host IP Connectivity requirements](#14-host-ip-connectivity-requirements)
    * [1.5 CLI requirements](#15-cli-requirements)
    * [1.6 Scalability requirements](#16-scalability-requirements)
    * [1.7 Warm Restart requirements ](#17-warm-restart-requirements)
  * [2 Modules Design](#2-modules-design)
    * [2.1 System Port Configuration on Sonic Instance](#21-system-port-configuration-on-sonic-instance)
    * [2.2 CHASSIS_APP_DB](#22-chassis_app_db)
      * [2.2.1 System Port interface table](#221-system-port-interface-table)
      * [2.2.2 System Neighbor table](#222-system-neighbor-table)
      * [2.2.3 System PortChannel table](#223-system-portchannel-table)
      * [2.2.4 System PortChannel Member table](#224-system-portchannel-member-table)
      * [2.2.5 CHASSIS_APP_DB Schemas](#225-chassis_app_db-schemas)
    * [2.3 Config DB](#23-config-db)
      * [2.3.1 DEVICE_METADATA](#231-device_metadata)
      * [2.3.2 System Port Table](#232-system-port-table)
      * [2.3.3 ConfigDB Schemas](#233-configdb-schemas)
    * [2.4 Orchestration agent](#24-orchestration-agent)
    * [2.5 Design Options for Host IP connectivity](#25-design-options-for-host-ip-connectivity)
	  * [2.5.1 Inband Recycle Port Option](#251-inband-recycle-port-option)
	    * [2.5.1.1 Routing Protocol Peering between SONiC Instances](#2511-routing-protocol-peering-between-sonic-instances)
	    * [2.5.1.2 SONiC Host IP Connectivity via Network Ports of other asics](#2512-sonic-host-ip-connectivity-via-network-ports-of-other-asics)
	    * [2.5.1.3 Note on Source and Destination MAC Addresses](#2513-note-on-source-and-destination-mac-addresses)
	  * [2.5.2 Inband VLAN Option](#252-inband-vlan-option)
	    * [2.5.2.1 Routing Protocol Peering between SONiC Instances](#2521-routing-protocol-peering-between-sonic-instances)
	    * [2.5.2.2 SONiC Host IP Connectivity via Network Ports of other asics](#2522-sonic-host-ip-connectivity-via-network-ports-of-other-asics)
	  * [2.5.3 Comparing Options](#253-comparing-options)
	  * [2.5.4 Kernel Routing Table Footprint](#254-kernel-routing-table-footprint)
	  * [2.5.5 Configuration Options for Inband](#255-configuration-options-for-inband)
    * [2.6 SAI](#26-sai)
    * [2.7 CLI](#27-cli)
    * [2.8 VOQ Monitoring and Telemetry](#28-voq-monitoring-and-telemetry)
  * [3 Flows](#3-flows)
	* [3.1 Voq Switch Creation and System Port Configurations](#31-voq-switch-creation-and-system-port-configurations)
	* [3.2 Voq System Port Orchestration](#32-voq-system-port-orchestration)
	* [3.3 Voq System Port Router Interface Creation](#33-voq-system-port-router-interface-creation)
	* [3.4 Voq Neighbor Creation](#34-voq-neighbor-creation)
  * [4 Example configuration](#4-example-configuration)
  * [5 Test Considerations](#5-test-considerations)
  * [6 Future Work](#6-future-work)
    * [6.1 Dynamic System Ports](#61-dynamic-system-ports)
  * [7 References](#7-references)

###### Revision
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 06/29/2020  | Sureshkannan Duraisamy, Srikanth Keesara, Vedavinayagam Ganesan (Nokia Sonic Team) | Initial public version            |
| 1.1 | 09/08/2020  | Sureshkannan Duraisamy, Srikanth Keesara, Vedavinayagam Ganesan (Nokia Sonic Team) Eswaran Bhaskaran, Kartik Chandran (Arista Networks) | Updates after reviews             |
| 1.2 | 06/14/2021  | Vedavinayagam Ganesan (Nokia)                                                      | Updates for cli commands, Inband interface port name change      |

# About this Manual
This document describes the design details for supporting SONiC on a Distributed VOQ System. It aligns with the SONiC Distributed VOQ-Architecture and should be read in conjunction with that document. It also adopts the SONiC Multi-ASIC architecture is adopted - which allows each asic within an FSI to be controlled independently by a separate instance of the "SONiC Network Stack" (comprising bgp, swss, syncd, lldp, teamd etc ..).

# Scope
This specification is foussed primarily on IPv4/IPv6 unicast routing over Ethernet. No attempt is made in this specification to discuss how features like L2/L3 Multicast, Routing/Bridging over tunnels etc... might work with SONiC across a Distributed VOQ System. The expectation is that such features could be implemented in subsequent phases and would require additional work in SONiC and possibly additional SAI enhancements. But that is outside the scope of this document.

# 1 Requirements Overview
## 1.1 Functional Requirements

The VOQ feature implementation shall support the following
1.  Distributed VOQ System.
2.  IPv4 and IPv6 unicast routing across any ports in the system
3.  Each switch in the system is controlled by a separate "asic instance" of SONiC.
4.  Host IP reachability to/from the interface IP addresses of any SONiC instance in the system using any network port in the system.
5.  Host IP reachability between the SONiC instances in the system over the datapath.
6.  Routing protocol peering between SONiC instances over the datapath.
7.  Static provisioning of System Ports in the VOQ System Database.
8.  Dynamic discovery of Routing Interfaces and Neighbors on other asics via the VOQ System Database.

## 1.2 Configuration requirements
Phase-1 of the Distributed VOQ System should support static configuration of the following
1. Connection parameters for the Central VOQ System Database (IP address, Port)
2. All the system ports in the entire system. The configuration of each system port should specify - system_port_id, switch_id, cored_index, core_port_index and speed.
3. Maximum number of cores in the system.
4. Switch_ID for each asic

## 1.3 Orchagent requirements
### Switch Creation
 - Should create the switch with the correct values for max_cores and switch_id
 - Should create the switch with complete list of system port for all the system ports during initialization

### PortsOrch:
 - Should be SystemPorts aware
 - Should initialize system ports list and create host interfaces for local ports (including the recycle port if configured)

### IntfsOrch:
- Should create/delete/update router interfaces against local-asic ports
- Should create/delete/update remote-asic router interfaces on the local switch
- Should export local-asic router interface information into the "CHASSIS_APP_DB"

### NeighOrch:
 - Should be aware of Neighbors on other asics
 - Should be able to create/delete/update "remote-asic" Neighbors on the local switch.
 - Should be able to create/delete/update next hops for "remote-asic" neighbors on the local switch.
 - Should export local-asic Neighbor information into the "CHASSIS_APP_DB"

### Switch Fabric Orchestration
 - Should initialize and create switch for fabric (switch type = FABRIC)
 - Should discover Fabric ports, Fabric port neighbor and Fabric port reachability
 - Should monitor Fabric port state, statistics, errors etc

## 1.4 Host IP Connectivity requirements
In a "non-VOQ" Distributed SONiC System (and VOQ SONiC systems with a single VOQ asic) all network communication to/from asic namespace on the SONiC host is supported by creating host interfaces (in the asic namespace) for each of the network ports of the asic. This includes - 
1.  Packets that are trapped to the host asic namespace because of an exception (unresolved ARP for example)
2.  Packets that are sent to the host asic namespace because the destination address on the packet is an interface address for SONiC on the asic and
3.  All packets sent from the host asic namespace and out via the network ports of the asic.

In a Distributed VOQ System, the requirement for network communication for the asic namespace remains the same. But there are some important differences.
1.  Packets that are trapped to the host asic namespace because of an exception - These are only received on network ports of the local asic
2.  Packets that are sent to the host asic namespace because the destination address on the packet is an interface address for SONiC on the asic. These could be
    - Received on a network port of the local asic OR
    - Received on a network port of another asic in the system and sent to the local asic over the fabric interfaces OR
    - Received on the CPU port of another asic in the system and sent to the local asic over the fabric interfaces
3.  Packet sent from host asic namespace could be either
    - Sent out via a network port of the local asic OR
    - Sent over the fabric interfaces to another asic and out via a network port of that asic OR
    - Sent over the fabric interfaces to another asic and out via the CPU port of that asic (to asic namespace of the other asic)

The figure below shows the cpu-to-cpu packet flows that needs to be supported
 ![](../../images/voq_hld/cpu-to-cpu-packet-flow.png)

The figure below shows the cpu-to-network-port packet flows that need to be supported
 ![](../../images/voq_hld/network-to-cpu-packet-flows.png)

## 1.5 CLI requirements
User should be able to display/retrieve the following VOQ information
- system-port id for the system ports
- Switch-id
- max-cores
- Neighbor Encap index

## 1.6 Scalability requirements

###### Table 2: VOQ scalability
| VOQ component            | Expected value              |
|--------------------------|-----------------------------|
| VOQ Switches             | 128                         |
| System Ports             | 4K                          |
| VOQ Neighbors            | 16k                         |

The initial scaling should at least support the requirements of a "large" modular chassis deploying ports based routing interfaces. Virtual interfaces (VLAN based routing interfaces) and directly attached hosts are still supported, but achieving higher scaling for those deployments is not a goal of the initial implementation.

## 1.7 Warm Restart requirements
At this time warm restart capability is not factored into the design. This shall be revisited as a Phase #2 enhancement

# 2 Modules Design
### 2.1 System Port Configuration on Sonic Instance
The system ports are configured on the Line Card. This information is then populated in the "System Port Table" in the "Config DB". On each sonic instance - the "OrchAgent" daemon subscribes to this information and recevies it. 

 ![](../../images/voq_hld/control-card-system-port-config-flow.png)

## 2.2 CHASSIS_APP_DB
This is a **new** database which resides in chassis redis server. This runs on the control/supervisor card and is accessible to the sonic instances in all the FSIs. This database is modeled as Application DB. The OrchAgent in all the sonic instances will write their local information such as INTERFACE, NEIGH, PORTCHANNEL and PORTCHANNEL_MEMBER tables to CHASSIS_APP_DB with hardware identifier's. The OrchAgent also reads sync-ed remote info such as SYSTEM_INTERFACE, SYSTEM_NEIGH, SYSTEM_PORTCHANNEL and SYSTEM_PORTCHANNEL_MEMBER tables of all sonic instances with hardware information such as hardware index.

### 2.2.1 System Port interface table
A table for interfaces of system ports.The schema is same as the schema of "INTERFACE" table in config.
```
SYSTEM_INTERFACE:{{system_interface_name}} 
    {}
```
The system_interface_name is same as the name of the system_port or system_portchannel

### 2.2.2 System Neighbor table
A table for neighbors learned or statically configured on system ports. The schema is same as the schema of "NEIGH" table in config DB with additional attribute for "encap_index".
```
SYSTEM_NEIGH:{{system_port_name}}:{{ip_address}} 
    "neigh": {{mac_address}}
    "encap_index": {{encap_index}}
```

### 2.2.3 System PortChannel Table
A table for system portchannel information. This is populated by OrchAgent.
```
SYSTEM_PORTCHANNEL:{{system_portchannel_name = PORTCHANNEL.portchannel_name}}
    "lag_id": {{index_number}}
    "switch_id": {{index_number}}
```
    
### 2.2.4 System PortChannel Member Table
A table SYSTEM_PORTCHANNEL_MEMBER for members of portchannel in the whole system. This is populated by OrchAgent.
Table schema is same as **existing** PORTCHANNEL_MEMBER table. 

### 2.2.5 CHASSIS_APP_DB Schemas

```
; Defines schema for interfaces for VOQ System ports
key                                   = SYSTEM_INTERFACE:system_port_name:ip_address ; VOQ System port interface
; field                               = value

```

```
; Defines schema for VOQ Neighbor table attributes
key                                   = SYSTEM_NEIGH:system_port_name:ip_address ; VOQ IP neighbor
; field                               = value
neigh                                 = 12HEXDIG                                       ; mac address of the neighbor
encap_index                           = 1*4DIGIT                                       ; Encapsulation index of the remote neighbor.

```

```
; Defines schema for VOQ PORTCHANNEL table attributes
key                                   = SYSTEM_PORTCHANNEL:system_port_name ; VOQ port channel neighbor
; field                               = value
lag_id                                = 1*4DIGIT                            ; lag id
switch_id                             = 1*4DIGIT                            ; switch id

```
## 2.3 Config DB

### 2.3.1 DEVICE_METADATA
 The **existing** DEVICE_METADATA table is enhanced to add new entry to have VOQ related parameters
 
```
DEVICE_METADATA: {
   "localhost": {
      ...
      "switch_type": {{switch_type}}
      "switch_id": {{switch_id}}
      "max_cores" : {{max_cores}}
   }
}
```

CHASSIS_APP_DB and Chassis DB instance will be specified using database_config.json.j2 and it will be generated in control card and linecard differently. Control card will be the server and line card will be connecting to the CHASSIS_APP_DB. DBConnectors will use this config to connect correct Chassis DB instance.

sonic-buildimage/dockers/docker-database/database_config.json.j2

```
    "INSTANCES": {
        "redis":{
            "hostname" : "{{HOST_IP}}",
            "port" : 6379,
            "unix_socket_path" : "/var/run/redis{{NAMESPACE_ID}}/redis.sock",
            "persistence_for_warm_boot" : "yes"
        },
{%- if sonic_asic_platform == "voq" %}
        "redis-chassis_db":{
            "hostname" : "{{HOST_IP}}",
            "port" : 6380,
            "unix_socket_path" : "/var/run/redis{{NAMESPACE_ID}}/redis-chassis_db.sock",
            "persistence_for_warm_boot" : "no",
{%- if sonic_asic_platform_cardtype == "linecard" %}
            "run_server": "no"
{%- endif %}
        }
{%- endif %}
    },
    "DATABASES" : {
        "APPL_DB" : {
            "id" : 0,
            "separator": ":",
            "instance" : "redis"
        },
        ...
        "CHASSIS_APP_DB" : {
            "id" : 11,
            "separator": ":",
            "instance" : "redis-chassis_db"
        },
```
        

### 2.3.2 System Port Table
A **new** table for system port configuration

```
SYSTEM_PORT:{{system_port_name}}
    "system_port_id": {{index_number}}
    "switch_id": {{index_number}}
    "core_index": {{index_number}}
    "core_port_index": {{index_number}}
    "speed": {{index_number}}
```
### 2.3.3 ConfigDB Schemas
**Existing** schema for DEVICE_METADATA in configuration DB
```
key                                   = DEVICE_METADATA|"localhost"      ; 
; field                               = value
switch_type                           = "voq" | "fabric"
switch_id                             = 1*4DIGIT            ; number between 0 and 1023
max_cores                             = 1*4DIGIT            ; max cores 1 and 1024
    
```

```
; Defines schema for VOQ System Port table attributes
key                                   = SYSTEM_PORT:system_port_name ; VOQ system port name
; field                               = value
system_port_id                        = 1*5DIGIT                ; 1 to 32768
switch_id                             = 1*4DIGIT                ; 0 to 1023 attached switch id
core_index                            = 1*4DIGIT                ; 1 to 2048 switch core id
core_port_index                       = 1*3DIGIT                ; 1 t0 256 port index in a core
speed                                 = 1*7DIGIT                ; port line speed in Mbps
```

No changes in the schema of other CONFIG_DB tables. The name of the system ports used as key in the SYSTEM_PORT table is unique across chassis. The system_port_name can be same as the PORT table name as long as the PORT table name is unique across the chassis or it can be any character string which does not include ":". If a system port is used as inband interface, the name of that system port must be a name that will be accepted by kernel for netdevice name.

For router interface and address configurations for the system ports, the existing INTERFACE table in CONFIG_DB is used.

Please refer to the [schema](https://github.com/sonic-net/sonic-swss/blob/master/doc/swss-schema.md) document for details on value annotations. 

## 2.4 Orchestration agent
### VOQ Switch Creation
Prior to switch creation - OrchAgent determines whether or not it is a VOQ Switch by checking if VOQ specific information is present in the CONFIG DB. It could do this by checking for the presence of switch_id (or max_cores or connection information for VOQ System DB) in the VOQ System Information. If it is not a VOQ Switch - switch creation goes ahead as it does currently. VOQ Switch creation requires additional information - max_cores, switch_id and system port list (see previous srctions for table names). It waits until this information is available from the APP DB before going ahead with switch creation. 
### Portsorch
This is made aware of voq system port. During PortOrch initialization, portsorch makes a list of all the system ports created during switch creation (above). After "PortInitDone" for all the local ports, portsorch adds system ports to ports list and creates host interfaces for the local ports (inclduing the recycle port if used for inband). 
### Intfsorch
The router interface creation for system ports is driven by configuration in "INTERFACE" table ConfigDB. The router interface creation and ip address assignments are done as needed in the similar fashion as how they are done for local ports. No changes in IntfsOrh for voq systems.
### NeighOrch
The NeighOrch is made aware of system port. While creating neighbor entry, for the voq neighbors, the encap_index attribute is sent in addition to other attributes sent for local neighbors. The neighbor entry creation and next hop creation use system ports for remote neighbors and local ports for local neighbors. 
## Fabric Ports Orchestration
Fabric port orchestration includes  - discovering all fabric ports, fabric port neighbors and fabric port reachability. This applies to both switch types (NPU and FABRIC). Also Fabric ports should be monitored for - state changes, statistics, errors etc. Phase-1 implementation will not support deleting/creating fabric ports dynamically.
To be specified - The APP DB schema used for fabric ports.

## 2.5 Design Options for Host IP connectivity
IP communication support is required between
- SONiC instances over the Fabric Links. This is required to support routing protocol peering between the SONiC instances.
- A SONiC instance and IP hosts in the network reachable via ports on another asic in the system.

There are two options for supporting these requirements. The proposed configuration model allows the user to select between the two options. The first option (Inband Recycle Port Option) requires the asic to support a special "RECYLE" port (described below). The second option (Inbnad VLAN Option) uses SAI Host interface of type VLAN. Both of the options are described below along with a comparison between the two options. It is recommended that the Inband Recycle Port Option be used if the asic is capable of supporting it and the Inband VLAN Option be used if the asic does not support a "RECYCLE" port.

### 2.5.1 Inband Recycle Port Option
This option proposes that the "recycle" port be used for host IP packets flows that cross an asic boundary. Recycle port is a special port for which the Egress of the port is looped back to the Ingress. It can be used like any other port for forwarding operations (Routing, ACL, Mirror, Queues, Buffers etc..). This option proposes that a SONiC instance should create host interfaces ONLY for the its own system ports (ports that "belong" to its asic). This includes host interfaces for the network ports on the local asic and also the Recycle port.

The following rules are observed in terms of the kernel neighbor tables
1.  Neighbor on a local system-port:
      No changes from existing behavior. It is created on the host interface of that system port
2.  Neighbor on another asic system-port:
      Neighbor record is created on the host interface representing the Recycle port. The MAC address for the neighbor is set equal to that interface mac address.
      Additionally a host route for the neighbor is created with the next-hop specified as the Recycle port

As a result of this choice, the neighbor records in the kernel will be pointing to a different interface ( recycle port) and local-asic mac compared to what is programmed via the SAI into the asic (actual system port on another asic and actual neighbor MAC address). In order to ensure this behavior -
1.  Neighsyncd should be modified to ignore kernel notifications for neighbors on the Recycle port that are from another SONiC instance.

Any additional routes programmed into the kernel will use these neighbor IP addresses as Next-Hop. This part is the same as current sonic model.

#### 2.5.1.1 Routing Protocol Peering between SONiC Instances
The routing information for Recycle port interfaces (Recycle-system-port, RIF, Recycle-neighbor-ip/mac, Recycle-neighbor-host-route) from all the asics is programmed into the SAI. Equivalent information (Recycle-port-host-interface, Recycle-neighbor-ip/mac, host-route) is created in the kernel. There is one important difference in the kernel entries - the interface and mac used for the Recycle port neighbors from the other asics is the local-asic Recycle port and local asic-mac. For injected packets, the kernel resolves next-hop information to be the local Recycle port and local asic-mac. The local asic perform address lookups on injected packets and resolve the next-hop to be the Recycle-system-port of the destination SONiC instance. On the destination asic the packets loop around to the Recycle port ingress. They are then subject host packet trap rules and get trapped to the CPU. This enables routed IP reachabilty between the SONiC instances allowing BGP protocol peering to happen. The tables below show how the Interface, Neighbor and Route tables would be in such an implementation (rcy represents Recycle port). Please note the differences in the neighbor entries in the Kernel Vs SAI.

 ![](../../images/voq_hld/recycle-port-cpu-flow-tables.png)

The figure below shows the packet flows between a pair of SONiC instances using the recycle port.
 ![](../../images/voq_hld/recycle-port-cpu-to-cpu-flows.png)

#### 2.5.1.2 SONiC Host IP Connectivity via Network Ports of other asics
The VOQ System Database allows the routing information for all the neighbors (system-port, rif, neighbor-ip, neighbor-mac, meighbor-encap-index) to be available to all the SONiC instances. This results in the creation of the following in the Linux tables and equivalent entries in asic via the SAI interface. Note the difference in the neighbor entries in the Kernel Vs SAI.

- System Port creation corresponding to every Network port
- Routing interface on the System Port
- Neighbor on the Routing interface. *NOTE - the interface and MAC information in the SAI and the kernel are different for a neighbor.*

Show below are the tables for an example two asic system. Note the difference in the Kernel Vs SAI tables.

 ![](../../images/voq_hld/recycle-port-network-port-tables.png)

The figure below shows the packet flows using the recycle port for host packet flows for the 2-asic system above
 ![](../../images/voq_hld/recycle-port-cpu-to-network-flow.png)

#### 2.5.1.3 Note on Source and Destination MAC Addresses
The following should be noted about the packet flows described above in a packet that is forwarded between the host-ip stack of one ASIC and the CPU or Network port of another ASIC.
- For a packet sent from the host-ip stack of an ASIC, the source and destination MAC addresses on the packet will both be the same and equal to the MAC address of that ASIC. The programming of the neighbor record in the kernel ensures this. This will allow the ingress asic to route the packet.
- When a packet is routed to the recycle port of another ASIC, the destination asic overwrites the source and destination MAC address of that packet, with its own ASIC mac address. This is because the neighbor IP for that routed flow is its own recyle-port IP address.

### 2.5.2 Inband VLAN Option
This is a variation of the Option described above. Each ASIC in the system is provisioned with an Inband CPU port that provides connectivity to other ASICs in the chassis over the internal fabric. The inband CPU port is just a system port. The inband port on each chip is named as LinecardN.K|Cpu where N is the slot number and K is the chip number within the slot. A special "inband" VLAN is provisioned to facilitate L2 connectivity in between the inband CPU ports. This inband vlan has as its members the CPU system port of all the asics in the distributed VOQ system. The 'inband vlan' netdevice in the kernel acts as the L3 endpoint. The inband vlan of each ASIC is assigned a unique IP address within the prefix of this interface.

![](../../images/voq_hld/inband-interfaces.png)

The inband vlan hostif is created in SAI as type 'vlan'. This means that the packets injected into the ASIC from the CPU goes through the forwarding pipeline of the ASIC. The following packet flows are proposed.
1.  The SONiC instances are directly connected neighbors on the "inband" vlan. This allows IP connectivity between them.
2.  For host connectivity via the network ports of another ASIC, the IP stack of the other ASIC is utilized as a software router between the inband VLAN and its network ports.
3.  The kernel and the SAI neighbor records are manipulated to achieve this software routing for host packet flows (see examples below for details)

In the example below VLAN-4094 is used as the "inband" vlan.

The figure below shows vlan (special) being offloaded to hardware and Linecard CPU Software routing for any CPU inbound and outbound packets for remote system ports. 
 ![](../../images/voq_hld/option2b_vlan_lcpu_flow_picture1.png)

#### 2.5.2.1 Routing Protocol Peering between SONiC Instances
The figure below shows inband vlan tables in the kernel and SAI for the four asic system example. Note the difference in Kernel for SAI neighbor records for the inband vlan.
 ![](../../images/voq_hld/option2b-vlan-cpu-flow-tables.png)

The SAI neighbor entries are created for the inband IP addresses because there could be other routes (loopback IPs for example) that use the inband IP addresses as nexthops.

The figure below shows inband vlan net devices and packet flows for the four asic system example
 ![](../../images/voq_hld/option2b-vlan-cpu-to-cpu-packet-flows.png)

### 2.5.2.2 SONiC Host IP Connectivity via Network Ports of other asics
Show below are the tables for the example two asic system which we considered with the other options. Note the difference in the Kernel Vs SAI Neighbor tables for the inband vlan.

 ![](../../images/voq_hld/option2b-vlan-network-port-tables.png)

The figure below shows the inband vlan net device and host packet flows for the network ports for the 2-asic system above.
 ![](../../images/voq_hld/option2b-vlan-network-port-net-device-packet-flows.png)

### 2.5.3 Comparing Options
The table below compares the Inband Recycle Port and Inband VLAN options discussed above. 

 ![](../../images/voq_hld/inband-recycle-port-vs-vlan-comparison.png)

### 2.5.4 Kernel Routing Table Footprint
The use of the Datapath to route host packet flows for ports on other asics raises the question of whether we need the full routing table in the Kernel. The answer (pending a bit more investigation) seems to be that the kernel does NOT need all the routes. In fact seems logical to conclude that the only routes that are needed in the kernel are the direct routes for the interfaces configured on the local SONiC instance. All other routes can be eliminated from the kernel and replaced with the simple default route that points to the local cpu-port-interface as the Next-Hop. This would ensure that all host packet flows (outside of directly attached hosts) could be routed by the datapath. The advantages of this are kind of obvious
1.  Much smaller in the kernel footprint for SONiC(very few routes in kernel)
2.  Much greater fate sharing between terminated and forwarded packet flows.
Note: This is just an observation of what might be possible in terms of reducing kernel routing table footprint. It is not a recommendation to change the implementation.

### 2.5.5 Configuration Options for Inband
```
// VOQ inband interface config in CONFIG DB
{
   “VOQ_INBAND_INTERFACE”: {
       “<inband_interface_name>”: {
            “inband_type”: “port”|”vlan”,
            “vlan_id”: “<vlan id>”,
            “vlan_members”: [
               “<cpu system port 1 name>”,
               “<cpu system port 2 name>”,
               .
               .
               .
            ]
       },
       “<inband_interface_name>|<ip address/mask>”: {} 
     }
 }

```
"inband_interface_name" is the name of the inband system port or inband vlan or any other existing front panel port dedicated for cpu communication. "vlan_id" and "vlan_members" are applicable only when "inband_type" is "vlan".

## 2.6 SAI
Shown below tables represent main SAI attributes which shall be used for VOQ related objects.

###### Table 3.1 Swith SAI attributes related to VOQ system
| Switch component                                                      | SAI attribute                               |
|-----------------------------------------------------------------------|---------------------------------------------|
| Switch type                                                           | SAI_SWITCH_ATTR_TYPE                        |
| Switch id                                                             | SAI_SWITCH_ATTR_SWITCH_ID                   |
| Maximum number of cores in the chassis                                | SAI_SWITCH_ATTR_MAX_SYSTEM_CORES            |
| List of system port configuration for all system ports in the chassis | SAI_SWITCH_ATTR_SYSTEM_PORT_CONFIG_LIST     |

The system port configuration has the parameters listed below.

###### Table 3.2: System Port SAI attributes
| VOQ System Port component | SAI attribute                                         |
|---------------------------|-------------------------------------------------------|
| Sysem port id             | SAI_VOQ_SYSTEM_PORT_ATTR_PORT_ID                      |
| Attached switch id        | SAI_VOQ_SYSTEM_PORT_ATTR_ATTACHED_SWITCH_ID           |
| Core index                | SAI_VOQ_SYSTEM_PORT_ATTR_ATTACHED_CORE_INDEX          |
| Core port index           | SAI_VOQ_SYSTEM_PORT_ATTR_ATTACHED_CORE_PORT_INDEX     |
| Port line speed           | SAI_VOQ_SYSTEM_PORT_ATTR_OPER_SPEED                   |
| Number of VOQs            | SAI_VOQ_SYSTEM_PORT_ATTR_NUM_VOQ                      |


###### Table 3.3: Neighbor Entry SAI attributes (Existing table). Entry key {{ip_address}}:{{rif_id of system_port}}:{{switch_id}}
| Neibhbor component                             | SAI attribute                                         |
|------------------------------------------------|-------------------------------------------------------|
| Destination MAC                                | SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS               |
| Encapsulation index for remote neighbors       | SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX                   |
| Impose encapsulation index if remote neighbor  | SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_IMPOSE_INDEX            |

## 2.7 CLI

CLI commands for VOQ chassis are for system ports and system neighbors. There are only show commands for these objects. As mentioned earlier, for now, since system ports are not dynamically configured and are required to be statically supplied before boot up there is no configuration commands for system ports. Since system neigobors also do not have any configurations there is no configuration commands for system neighbors. 

The show commands are under **show chassis** commands group as shown below

**Help info of show chassis command group**
```
admin@Linecard2:~$ show chassis -h
Usage: show chassis [OPTIONS] COMMAND [ARGS]...

  Chassis commands group

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  modules           Show chassis-modules information
  system-neighbors  Show VOQ system neighbors information
  system-ports      Show VOQ system ports information
admin@Linecard2:~$ 
```
### 2.7.1 System ports show command
The information for the system ports are taken from the **SYSTEM_PORT_TABLE** of **APPL_DB** from a specific namespace 
#### Syntax
```
admin@Linecard2:~$ show chassis system-ports -h
Usage: show chassis system-ports [OPTIONS] [SYSTEMPORTNAME]

  Show VOQ system ports information

Options:
  -n, --namespace TEXT   Namespace name or all  [required]
  --verbose              Enable verbose output
  -h, -?, --help         Show this message and exit.
admin@Linecard2:~$
```
#### Sample output
```
admin@Linecard2:~$ show chassis system-ports -n asic0
            System Port Name    Port Id    Switch Id    Core    Core Port    Speed
----------------------------  ---------  -----------  ------  -----------  -------
       Linecard2|Asic0|Asic0        192            6       0            0      10G
   Linecard2|Asic0|Ethernet0        193            6       0            1     100G
   Linecard2|Asic0|Ethernet1        194            6       0            2     100G
   Linecard2|Asic0|Ethernet2        195            6       0            3     100G
Linecard2|Asic0|Ethernet-IB0        229            6       1           37      10G
.
.
.
       Linecard4|Asic0|Asic0        576           18       0            0      10G
   Linecard4|Asic0|Ethernet0        577           18       0            1     100G
   Linecard4|Asic0|Ethernet1        578           18       0            2     100G
   Linecard4|Asic0|Ethernet2        579           18       0            3     100G
Linecard4|Asic0|Ethernet-IB0        613           18       1           37      10G
.
.
.
```
**Note:**

   - In multi asic voq systems, for system ports since the configurations in all asics are required to be identical, the output of show for a system port is expected to be same in all the namespaces

### 2.7.2 System neighbors show command
The information for the system neighbors are taken from the **SYSTEM_NEIGH_TABLE** of **CHASSIS_APP_DB** in the supervisor card. 
#### Syntax
```
admin@Linecard2:~$ show chassis system-neighbors -h
Usage: show chassis system-neighbors [OPTIONS] [IPADDRESS]

  Show VOQ system neighbors information

Options:
  -x, --asicname TEXT   Asic name
  --verbose             Enable verbose output
  -h, -?, --help        Show this message and exit.
admin@Linecard2:~$ 
```
#### Sample output
```
admin@Linecard2:~$ show chassis system-neighbors 
       System Port Interface    Neighbor                MAC    Encap Index
----------------------------  ----------  -----------------  -------------
  Linecard2|Asic0|Ethernet21    10.0.0.5  fa:6e:44:e3:cf:30     1074790407
  Linecard2|Asic0|Ethernet21     fc00::a  fa:6e:44:e3:cf:30     1074790406
Linecard2|Asic0|Ethernet-IB0     3.3.3.4  40:55:82:a1:fa:c5     1074790404
Linecard2|Asic0|Ethernet-IB0   3333::3:4  40:55:82:a1:fa:c5     1074790405
  Linecard4|Asic0|Ethernet25   10.0.0.11  42:f4:47:d7:71:45     1074790407
  Linecard4|Asic0|Ethernet25    fc00::16  42:f4:47:d7:71:45     1074790406
Linecard4|Asic0|Ethernet-IB0    3.3.3.10  40:55:82:a1:fb:21     1074790404
Linecard4|Asic0|Ethernet-IB0  3333::3:10  40:55:82:a1:fb:21     1074790405
admin@Linecard2:~$
```

## 2.8 VOQ Monitoring and Telemetry
In a distributed VOQ System, queue and buffer utilization statistics for a port are collected separately on all the asics in the system. There may be a need to aggregate these statistics in order to have a view of the statistics against a port. This section will be updated once the scope of such requirements is clear.

# 3 Flows
## 3.1 VoQ Switch Creation and System Port Configurations
![](../../images/voq_hld/switch_creation_static.png)

## 3.2 VOQ System Port Orchestration
- PortsOrch is made aware of the sytem ports. It initializes the system port list, adds system ports list and creates host interfaces for all remote system ports

![](../../images/voq_hld/voq_systemport_orch.png)

## 3.3 VOQ System Port Router Interface Creation
![](../../images/voq_hld/voq_systemport_rif_create_cntrl_flow.png)

## 3.4 VOQ Neighbor Creation
![](../../images/voq_hld/voq_neighbor_create_local_cntrl_flow.png)


![](../../images/voq_hld/voq_neighbor_create_remote_cntrl_flow.png)

## 3.5 VOQ PortChannel Creation 
![](../../images/voq_hld/voq_portchannel_creation.png)

# 4 Example configuration

Example coniguration for voq inband interface type "port" is presented

#### Config DB Objects:

##### In ASIC #0

```
 {
     "DEVICE_METADATA": {
        "localhost": {
	   "switch_type": "voq",
	   "switch_id": "0",
	   "max_cores": "48",
	   "asic_name": "Asci0",
	   "hostname": "Slot1"
	}
     },
     "INTERFACE": {
         "Ethernet1": {},
         "Ethernet2": {},
         "Ethernet3": {},
         "Ethernet1"|"10.0.0.1/16": {},
         "Ethernet2"|"20.0.0.1/16": {},
         "Ethernet3"|"30.0.0.1/16": {}
     },
     "VOQ_INBAND_INTERFACE": {
        "Ethernet-IB0": {
	   "inband_type": "port",
	},
	"Ethernet-IB0|3.3.3.1/32": {}
     }
     "PORT": {
         "Ethernet1": {
            "admin_status": "up",
            "alias": "Ethernet1",
            "index": "1",
            "lanes": "8,9,10,11,12,13,14,15",
            "mtu": "1500",
            "speed": "400000"
        },
        "Ethernet2": {
            "admin_status": "up",
            "alias": "Ethernet2",
            "index": "2",
            "lanes": "0,1,2,3,4,5,6,7",
            "mtu": "1500",
            "speed": "400000"
        },
        "Ethernet3": {
            "admin_status": "up",
            "alias": "Ethernet3",
            "index": "3",
            "lanes": "24,25,26,27,28,29,30,31",
            "mtu": "1500",
            "speed": "400000"
        },
	 "Ethernet-IB0": {
            "admin_status": "up",
            "alias": "Rcy-Asic0",
            "index": "4",
            "lanes": "133",
            "mtu": "1500",
            "speed": "10000"
        },
	.
	.
	.
     },
     "SYSTEM_PORT": {
         "Slot1|Asic0|Ethernet1": {
             "system_port_id": "1",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "1",
             "speed": "400000"
         },
         "Slot1|Asic0|Ethernet2": {
             "system_port_id": "2",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "2",
             "speed": "400000"
         },
         "Slot1|Asic0|Ethernet3": {
             "system_port_id": "3",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "3",
             "speed": "400000"
         },
	 "Slot1|Asic0|Ethernet-IB0": {
             "system_port_id": "63",
             "switch_id": "0",
             "core_index": "1",
             "core_port_index": "6",
             "speed": "10000"
         },
	 .
	 .
	 .
         "Slot1|Asic1|Ethernet1": {
             "system_port_id": "65",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "1",
             "speed": "400000"
         },
         "Slot1|Asic1|Ethernet2": {
             "system_port_id": "66",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "2",
             "speed": "400000"
         },
         "Slot1|Asic1|Ethernet3": {
             "system_port_id": "67",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "3",
             "speed": "400000"
         },
	 "Slot1|Asic1|Ethernet-IB1": {
             "system_port_id": "77",
             "switch_id": "2",
             "core_index": "1",
             "core_port_index": "6",
             "speed": "10000"
         }
     }
 }
```

##### In ASIC #1

```
 {
     "DEVICE_METADATA": {
        "localhost": {
	   "switch_type": "voq",
	   "switch_id": "2",
	   "max_cores": "48",
	   "asic_name": "Asic1",
	   "hostname": "Slot1"
	}
     },
      "INTERFACE": {
         "Ethernet1": {},
         "Ethernet2": {},
         "Ethernet3": {},
         "Ethernet1"|"10.1.0.1/16": {},
         "Ethernet2"|"20.1.0.1/16": {},
         "Ethernet3"|"30.1.0.1/16": {}
     },
     "VOQ_INBAND_INTERFACE": {
        "Ethernet-IB1": {
	   "inband_type": "port",
	},
	"Ethernet-IB1|3.3.3.2/32": {}
     },
     "PORT": {
         "Ethernet1": {
            "admin_status": "up",
            "alias": "Ethernet1",
            "index": "1",
            "lanes": "8,9,10,11,12,13,14,15",
            "mtu": "1500",
            "speed": "400000"
        },
        "Ethernet2": {
            "admin_status": "up",
            "alias": "Ethernet2",
            "index": "2",
            "lanes": "0,1,2,3,4,5,6,7",
            "mtu": "1500",
            "speed": "400000"
        },
        "Ethernet3": {
            "admin_status": "up",
            "alias": "Ethernet3",
            "index": "3",
            "lanes": "24,25,26,27,28,29,30,31",
            "mtu": "1500",
            "speed": "400000"
        },
	 "Ethernet-IB1": {
            "admin_status": "up",
            "alias": "Rcy-Asic1",
            "index": "3",
            "lanes": "133",
            "mtu": "1500",
            "speed": "10000"
        },
	.
	.
	.
     },
     "SYSTEM_PORT": {
         "Slot1|Asic0|Ethernet1": {
             "system_port_id": "1",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "1",
             "speed": "400000"
         },
         "Slot1|Asic0|Ethernet2": {
             "system_port_id": "2",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "2",
             "speed": "400000"
         },
         "Slot1|Asic0|Ethernet3": {
             "system_port_id": "3",
             "switch_id": "0",
             "core_index": "0",
             "core_port_index": "3",
             "speed": "400000"
         },
	 "Slot1|Asic0|Ethernet-IB0": {
             "system_port_id": "63",
             "switch_id": "0",
             "core_index": "1",
             "core_port_index": "6",
             "speed": "10000"
         },
	 .
	 .
	 .
         "Slot1|Asic1|Ethernet1": {
             "system_port_id": "65",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "1",
             "speed": "400000"
         },
         "Slot1|Asic1|Ethernet2": {
             "system_port_id": "66",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "2",
             "speed": "400000"
         },
         "Slot1|Asic1|Ethernet3": {
             "system_port_id": "67",
             "switch_id": "2",
             "core_index": "0",
             "core_port_index": "3",
             "speed": "400000"
         },
	 "Slot1|Asic1|Ethernet-IB1": {
             "system_port_id": "77",
             "switch_id": "2",
             "core_index": "1",
             "core_port_index": "6",
             "speed": "10000"
         }
     }
 }
```

#### CHASSIS_APP_DB Objects:

```
{
   "SYSTEM_INTERFACE": {
      "Slot1|Asic0|Ethernet-IB0": {},
      "Slot1|Asic1|Ethernet-IB1": {},
      "Slot1|Asic0|Ethernet1": {},
      "Slot1|Asic0|Ethernet2": {},
      "Slot1|Asic0|Ethernet3": {},
      "Slot1|Asic1|Ethernet1": {},
      "Slot1|Asic1|Ethernet2": {},
      "Slot1|Asic1|Ethernet3": {}
   },
   "SYSTEM_NEIGH": {
      "Slot1|Asic0|Ethernet1:10.0.0.2": {
         "neigh": "02:01:00:00:00:01",
	 "encap_index": "8193",
      },
      "Slot1|Asic0|Ethernet2:20.0.0.2": {
         "neigh": "02:01:00:00:00:02",
	 "encap_index": "8194",
      },
      "Slot1|Asic0|Ethernet-IB0:3.3.3.1": {
         "neigh": "02:01:00:00:00:00",
	 "encap_index": "8195",
      },
      "Slot1|Asic1|Ethernet1:10.1.0.2": {
         "neigh": "02:01:01:00:00:01",
	 "encap_index": "8193",
      },
       "Slot1|Asic1|Ethernet2:20.1.0.2": {
         "neigh": "02:01:01:00:00:02",
	 "encap_index": "8194",
      },
      "Slot1|Asic1|Ethernet-IB1:3.3.3.2": {
         "neigh": "02:01:01:00:00:00",
	 "encap_index": "8195",
      }
   }
}
```
# 5 Test Considerations

## 5.1 test_virtual_chassis.py 
This is the top level test driver that executes testcases against the virtual chassis. System Port handling is tested by test_chassis_sysport which validates that
* System ports can be populated in CONFIG_DB
* Orchagent programs the correct SAI Redis ASIC_DB state to represent the configured sysport in a multi-instance environment

# 6 Future Work
## 6.1 Dynamic System Ports 

Dynamic system port support is required to support the following forwarding scenarios

* Addition of a new forwarding module into an existing running system
* Replacing a forwarding module with another module of a different hardware SKU (such as replacing a linecard with a new linecard of a different SKU in a chassis slot).

Both these scenarios can be supported smoothly as long as the global system port numbering scheme is maintained and the modifications to system ports can be performed without impacting the System Port IDs of the running system.

Support for dynamic system ports requires SAI support for the `create_port` and `remove_port` calls. In addition, forwarding features that are dependent on System Ports need to react to these changes and reprogram the related forwarding plane state such as routing nexthops, LAG membership etc.

# 7 References
To be completed
