
# IEEE 802.1s Multiple Spanning Tree Protocol

**High Level Design** 

## Revision History

[© xFlow Research Inc](https://xflowresearch.com/) 

|Revision No.|Description|Author|Date|
| :- | :- | :- | :- |
|0.1|Intial Design|[Hamna Rauf](https://github.com/hamnarauf), [Muhammad Danish](https://github.com/mdanish-kh), [Rida Hanif](github.com/ridahanif96), [Hafiz Mati ur Rehman](https://github.com/Mati86)  & [Arsalan Ahmad](https://github.com/ahmadarsalan/)|March 20, 2023|

# Table of Contents

* [Scope](#scope)
* [Background](#background)
* [Abbreviations](#abbreviations)
* [Overview](#overview)
* [Introduction](#introduction)
* [Requirements](#requirements)
* [Architecture Design](#architecture-design)
  - [STP Container](#stp-container)
  - [SWSS Container](#swss-container)
  - [CoPP Configurations](#copp-configurations)
* [Database Changes](#database-changes)
  - [CONFIG DB](#config-db)
  - [APP DB](#app-db)
* [SAI](#sai)
* [Sequence Diagrams](#sequence-diagrams)
  - [MSTP global enable](#mstp-global-enable)
  - [MSTP global disable](#mstp-global-disable)
  - [MSTP region name/version change](#mstp-region-nameversion-change)
  - [Instance creation](#instance-creation)
  - [Instance deletion](#instance-deletion)
  - [Add VLAN to instance](#add-vlan-to-instance)
  - [Del VLAN from instance](#del-vlan-from-instance)
* [Configuration Commands](#configuration-commands)
  - [Global Level](#global-level)
  - [Region Level](#region-level)
  - [Instance, Interface Level](#instance-interface-level)
  - [Show Commands](#show-commands)
  - [Clear Commands](#clear-commands)
  - [Debug Commands](#debug-commands)
  - [Disabled Commands](#disabled-commands)
* [YANG Model](#yang-model)
* [Rest API Support](#rest-api-support)
* [Warm Boot](#warm-boot)
* [Testing Requirements](#testing-requirements)
  - [Unit test cases](#unit-test-cases)
* [References](#references)

# Scope
This document describes the High Level Design of Multiple Spanning Tree Protocol.

# Background
This HLD is based on the design provided by PVST HLD.

PVST HLD: https://github.com/sonic-net/SONiC/pull/386

# Abbreviations

|**Term**|**Meaning**|
| :- | :- |
|MSTP|Multiple Spanning Tree Protocol|
|PVST|Per VLAN Spanning Tree|
|STP|Spanning Tree Protocol|
|VLAN|Virtual Local Area Network|
|MSTI|Multiple Spanning Tree Instance|
|CIST|Common Internal Spanning Tree|
|CST|Common Spanning Tree|
|IST|Internal Spanning Tree|
|BPDU|Bridge Protocol Data Unit|
|RSTP|Rapid Spanning Tree Protocol|
|VID|VLAN identifier|
|MSTID|Multiple Spanning Tree Identifier|
|CoPP|Control Plane Policing|

# Overview
Multiple Spanning Tree Protocol (MSTP) enhances the Spanning Tree Protocol (STP) by enabling the creation of multiple spanning tree instances within a network. It provides a mechanism to map VLANs to specific spanning tree instances which offers network segmentation and improved control over traffic flow.

# Introduction
Spanning Tree Protocol (STP) prevents bridge looping on LANs that include redundant links. Per VLAN Spanning Tree (PVST) is a modification of STP that allows for running separate instances of spanning tree for each VLAN. 

Multiple Spanning Tree Protocol (MSTP) allows the mapping of multiple VLANs to a single instance hence allows frames assigned to different VLANs to follow separate paths. These paths are based on independent Multiple Spanning Tree Instances (MSTI) that run inside MST Region. VLANs that are not explicitly assigned to any specific MSTI are automatically managed by the default Internal Spanning Tree (IST) associated with instance 0. MSTP ensures that frames with a given VID are assigned to only one of the MSTIs or the IST within the Region and the assignment is consistent amongst all the Bridges within the region. 

To facilitate the interconnection among MST regions, a Common Spanning Tree (CST) is established, allowing communication between switches in different MST regions. MSTP connects all Bridges and LANs with a single Common and Internal Spanning Tree (CIST). CIST refers to the combination of the Common Spanning Tree (CST) and the Internal Spanning Tree (IST) and it is the overall spanning tree instance that spans the entire MSTP domain.

By providing VLAN-to-instance mapping, MSTP ensures that a limited number of instances are created, allowing for network segregation. In contrast, PVST lacks control over VLAN-to-instance mapping, leading to numerous instances and inefficient memory utilization. 

STP only supports a single instance, resulting in under utilized network bandwidth due to complete link blocking. Therefore, MSTP offers better control over instances, efficient resource usage, and improved network performance compared to PVST and STP.

MSTP calculates spanning trees on the basis of Multiple Spanning Tree Bridge Protocol Data Units (MST BPDUs).

<div align="center">
<img src="images/MSTP_BPDU.png" alt="MSTP BPDU">
<p>MSTP BPDU Format</p>
</div><br>
<div align="center">
<img src="images/MSTI_config_message.PNG" alt="MSTP Config Message">
<p>MSTI Configuration Messages</p>
</div>

*Refer to [RFC IEEE 802.1s-2002](https://standards.ieee.org/ieee/802.1s/1042/) for MSTP BPDU details.* 

# Requirements
1. Support the creation of Multiple Spanning Tree Instances (MSTIs).
1. Support the assignment of one or more VLANs to a specific MSTI within a region.
1. Support the option to assign a region name and revision number to MSTP regions in order to achieve unique identification of VLAN to instance mapping across switches.
1. Support path selection and forwarding behaviour in MSTI to optimize network performance within each instance by configuring a distinct root bridge.
1. Support the configuration of spanning tree parameters such as forward delay, hello timer, hop count and max age.
1. The Destination Mac Address will be 01:80:C2:00:00:00 for MSTP BPDUs.
1. Support compatibility with networks employing different spanning tree protocols, such as STP, RSTP and PVST via Protocol Migration.

# Architecture Design
Following diagram explains the architectural design and linkages for MSTP. MSTP uses multiple existing SONiC containers, configuration details of each is mentioned below as well.

![MSTP Architecture](images/MSTP_architecture.png)

## STP Container
STP Container is responsible for actions taken for BPDU rx and BPDU tx. Following are the details for implementation:

### STPMgr
Subscribes to CONFIG_DB and STATE_DB tables, parsing configurations and passes to STPd.

### STPd
Responsible for all MST protocol related calculations. BPDUs are sent and received in STPd and states are updated accordingly.

### STPSync
A process running as a part of STPD. Responsible for updating all the MSTP states in APP DB.

The BPDU rx/tx, BPDU processing, handling of timers, handling of changes related to port or LAG using netlink events and STP port state sync to Linux Kernel will function the same as PVST.

*Refer to [PVST's STP Container Details](https://github.com/sandeep-kulambi/SONiC/blob/631ab18211e7e396b138ace561b7a04e7f7b49a1/doc/stp/SONiC_PVST_HLD.md#34-stp-container)*

## SWSS Container

SWSS Container is responsible for passing on configurations to SAI as follows:

### STPOrch
Updates SAI via following APIs:

1. Creating/deleting instances via SAI STP API.
2. Assigning VLAN to instance via SAI STP API and SAI VLAN API.
3. Creation of STP Port and assigning port state with respect to each instance via SAI STP API.
4. Flushing FDB entries via SAI FDB API.

## CoPP Configurations
MSTP facilitates the exchange of control packets, known as Bridge Protocol Data Units (BPDUs), among switches to establish and maintain loop-free paths in a network. In order to trap these BPDUs, Control Plane Policing (CoPP) will be extended as follows:
```
"stp": {
    "trap_ids"  : "stp,pvrst,mstp",
    "trap_group": "queue1_group1"
}
```

# Database Changes
MSTP design introduces some new tables for configuration along with slight modification in existing STP tables. Following are details of each individual table:

## CONFIG DB

### Existing Table
Following existing table of CONFIG_DB will be modified for MSTP implementation:

#### STP_GLOBAL_TABLE
A new value of `mstp` for `mode` column and a new column for holding `max-hops`
```
mode 		  = "pvst" / "mstp" / "disable"      ; a new option for mstp (DEF: "disable")
max_hops	  = 1*3DIGIT		             ; max hops (1 to 255, DEF: 20)
```
Other fields of this table i.e rootguard_timeout, forward_delay, hello_time, max_age, priority will also be used to hold the configurations received from CLI.

### New Tables
Following new tables will be added to CONFIG_DB:

#### MSTP_REGION_TABLE
```
;Stores the MSTP Regional operational details
key               = MSTP|REGION 	  ; MSTP REGION key
region_name 	  = 1*32CHAR	          ; region name (DEF: mac-address of switch)
revision	  = 1*5DIGIT 	          ; region revision number(0 to 65535, DEF: 0)
```

#### MSTP_INSTANCE_TABLE
```
;Stores the MSTP instance operational details
key           = MSTP_INSTANCE|"Instance"instanceid	  ; instance id with MSTP_INSTANCE as a prefix
priority      = 1*5DIGIT 			          ; bridge priority (0 to 61440, DEF:32768)
```

#### MSTP_VLAN_TABLE
```
;Stores MSTP VLAN to instance mapping
key               = MSTP_VLAN|"Vlan"vlanid              ; vlan id with MSTP_VLAN as a prefix
instance_id	  = 1*2DIGIT	                        ; instance id vlan is mapped to (0-63, DEF:0)
```

#### MSTP_INSTANCE_PORT_TABLE
```
;Stores STP interface details per Instance
key        = MSTP_INSTANCE_PORT|"Instance"instanceid|ifname   ; instanceid|ifname with prefix MSTP_INSTANCE_PORT, ifname can be physical or portchannel name
priority   = 1*3DIGIT                                         ; port priority (0 to 240, DEF:128)
path_cost  = 1*9DIGIT                                         ; port path cost (1 to 200000000)
```

## APP DB

### New Tables
Following new tables are introduced as part of MSTP Feature:

#### MSTP_REGION_TABLE
```
;Stores the MSTP regional operational details
key                     = MSTP:REGION	      ; MSTP REGION key
region_name 	        = 1*32CHAR            ; region name (DEF: mac-address of switch)
revision	        = 1*5DIGIT            ; region revision (0 to 65535, DEF: 0)
bridge_id	        = 16HEX	              ; bridge id
cist_root_bridge_id	= 16HEX	              ; CIST root’s bridge id
external_path_cost	= 1*9DIGIT	      ; path cost to CIST root bridge
root_port               = ifName	      ; root port name
root_max_age            = 1*2DIGIT	      ; max age as per CIST root bridge
root_hello_time         = 1*2DIGIT	      ; hello time as per CIST root bridge
root_forward_delay      = 1*2DIGIT	      ; forward delay as per CIST root bridge
root_max_hops		= 1*3DIGIT	      ; max hops as per CIST root bridge
max_age                 = 1*2DIGIT            ; maximum age time in secs (6 to 40, DEF: 20)
hello_time              = 1*2DIGIT            ; hello time in secs (1 to 10, DEF: 2)
forward_delay           = 1*2DIGIT            ; forward delay in secs (4 to 30, DEF: 15)
max_hops	        = 1*3DIGIT	      ; max hops (1 to 255; DEF:20)   
last_topology_change    = 1*10DIGIT           ; time in secs since last topology change occured
topology_change_count   = 1*10DIGIT           ; number of times topology change occured
instances_configured    = 1*2DIGIT            ; total number of instances configured (DEF: 1)
```

#### MSTP_INSTANCE_TABLE
```
;Stores the STP instance operational details
key                       = MSTP_INSTANCE:"Instance"instanceid    ; instance id with MSTP_INSTANCE as a prefix
vlanids	                  = vlan_id-or-range[,vlan_id-or-range]   ; list of VLAN IDs
oper_status	          = "active" / "inactive"                 ; instance is active in mstp
bridge_id                 = 16HEXDIG                              ; bridge id
regional_root_bridge_id   = 16HEXDIG                              ; regional root’s bridge id
internal_root_path_cost   = 1*9DIGIT	                          ; port path cost to regional root
root_port                 = ifName	                          ; root port name
last_topology_change      = 1*10DIGIT                             ; time in sec since last topology change occured 
topology_change_count     = 1*10DIGIT                             ; number of times topology change occured
```

#### MSTP_INSTANCE_PORT_TABLE
```
;Stores STP interface details per Instance
key                 = MSTP_INSTANCE_PORT:"Instance"instanceid:ifname    ; instanceid|ifname with prefix MSTP_INSTANCE_PORT
port_num            = 1*3DIGIT                                          ; port number of bridge port
path_cost           = 1*9DIGIT                                          ; port path cost (1 to 200000000)
priority            = 1*3DIGIT                                          ; port priority (0 to 240, DEF:128)
port_state          = "state"                                           ; STP state - disabled, block, listen, learn, forward
port_role           = "role"                                            ; STP port role - root, designated, blocking, alternate, master
desig_root    	    = 16HEXDIG                                          ; designated root
desig_cost   	    = 1*9DIGIT                                          ; designated cost
desig_bridge  	    = 16HEXDIG                                          ; designated bridge
desig_port    	    = 1*3DIGIT                                          ; designated port
fwd_transitions     = 1*5DIGIT                                          ; number of forward transitions
bpdu_sent           = 1*10DIGIT                                         ; bpdu transmitted
bpdu_received       = 1*10DIGIT                                         ; bpdu received
tcn_sent            = 1*10DIGIT                                         ; tcn transmitted
tcn_received        = 1*10DIGIT                                         ; tcn received
root_guard_timer    = 1*3DIGIT                                          ; root guard current timer value
```

### Existing Tables
Following already present APP_DB tables are also used for implementation of MSTP:

#### STP_PORT_STATE_TABLE 
The table holds the state of a port i.e forwarding, learning, blocking with respect to each instance.
#### STP_VLAN_INSTANCE_TABLE 
The table holds the VLAN to instance mapping.
#### STP_FASTAGEING_FLUSH_TABLE 
The table informs when the FDB flushing is required. This is done in case of topology change where the mac entries in FDB become inconsistent and there is a need to flush these entries.

# SAI

## Existing SAI Attributes
Following table shows the existing SAI Attributes that will be used:

|**Component**|**SAI Attribute**|
| :- | :- |
|STP Instance|SAI_STP_ATTR_VLAN_LIST
||SAI_STP_ATTR_BRIDGE_ID|
||SAI_STP_ATTR_PORT_LIST|
|STP Port|SAI_STP_PORT_ATTR_STP |
||SAI_STP_PORT_ATTR_BRIDGE_PORT|
||SAI_STP_PORT_ATTR_STATE|
|STP Port States|SAI_STP_PORT_STATE_LEARNING|
||SAI_STP_PORT_STATE_FORWARDING|
||SAI_STP_PORT_STATE_BLOCKING|
|VLAN STP Instance|SAI_VLAN_ATTR_STP_INSTANCE|
|Switch STP Attributes|SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID|
||SAI_SWITCH_ATTR_MAX_STP_INSTANCE|

## New SAI Attributes
MSTP design requires one new attribute `SAI_HOSTIF_TRAP_TYPE_MSTP` for control trap packets which will be defined in saihostif.h.

[SAI/saihostif.h](https://github.com/opencomputeproject/SAI/blob/master/inc/saihostif.h)

#  Sequence Diagrams
## MSTP global enable
![MSTP Global Enable](images/MSTP_global_enable.png)

## MSTP global disable
![MSTP Global Disable](images/MSTP_global_disable.png)

## MSTP region name/version change
![MSTP Region Config](images/MSTP_region_config.png)

## Instance creation
![MSTP Instance Create](images/MSTP_instance_create.png)

## Instance deletion
![MSTP Instance Del](images/MSTP_instance_del.png)

## Add VLAN to instance
![MSTP VLAN Add](images/MSTP_vlan_add.png)

## Del VLAN from instance
![MSTP VLAN Del](images/MSTP_vlan_del.png)

Update port-state, topology change and instance-interface events remain the same as depicted in [Sequence Diagrams of PVST](https://github.com/sandeep-kulambi/SONiC/blob/631ab18211e7e396b138ace561b7a04e7f7b49a1/doc/stp/SONiC_PVST_HLD.md#4-flow-diagrams).

# Configuration Commands
Following configuration commands will be provided for configuration of MSTP:
## Global Level
- **config spanning_tree {enable|disable} {mstp|pvst}**
  - Enables or disables mstp at global level on all ports of the switch.
  - Only one mode of STP can be enabled at a time.
- **config spanning_tree max_hops \<max-hops-value\>**
  - Specify the number of maximum hops before the BPDU is discarded inside a region.
  - max-hops-value: Default: 20, range: 1-255

## Region Level
Below commands allow configuring on region basis:

- **config spanning_tree region name \<region-name\>**
  - Edit the name of region
  - region-name: Case sensitive, characters should be less than or equal to 32, default: mac-address of bridge
- **config spanning-tree region revision \<revision-number\>**
  - Revision number is used to track changes in the configuration and to synchronize the configuration across the switches in the same region.
  - revision-number: Default: 0, range: 0-65535

## Instance Level

Below commands allow configuration of an instance:

- **config spanning_tree instance (add|del) \<instance-id\>**
  - Creation or deletion of an instance.
  - instance-id: Default: 0, range: 1-63
  - Instance can not be deleted if VLAN(s) are associated with it. 
- **config spanning_tree instance priority \<instance-id\> \<priority-value\>** 
  - Configure priority of bridge for an instance.
  - instance-id: id of the instance for which bridge priority is to be defined. If the provided instance id is not created yet, an error message is displayed.
  - priority-value: Default: 32768, range: 0-61440 (should be multiple of 4096)
- **config spanning_tree instance vlan (add|del) \<instance-id\> \<vlan-id\>**
  - VLAN to instance mapping.
  - instance-id: id of the instance to which VLAN is to be mapped. If the provided instance id is not created yet, an error message is displayed.
  - vlan-id: Range: 1-4094. If the provided VLAN is not created yet, an error message is displayed.
  - Instance is only active when there is at least one VLAN member port configured for one of the mapped VLANs.

## Instance, Interface Level
Following commands are used for spanning-tree configurations on per instance, per interface basis:

- **config spanning_tree instance interface priority \<instance-id\> \<ifname\> \<priority-value\>**
  - Configure priority of an interface for an instance.
  - priority-value: Default: 128, range: 0-240
- **config spanning_tree instance interface cost \<instance-id\> \<ifname\> \<cost-value\>**
  - Configure path cost of an interface for an instance.
  - cost-value: Range: 1-200000000

## Show Commands
- show spanning_tree

    The output of this command will be as follows for `mstp`:
```
Spanning-tree Mode: MSTP

MSTP Region Parameters:
Region Name                     : regionA
Revision                        : 0
CIST Bridge Identifier          : 32768002438eefbc3
CIST Root Identifier            : 32768002438eefbc3
CIST External Path Cost         : 0
Instances configured            : 1
Last Topology Change            : 0s
Number of Topology Changes      : 0
Bridge Timers                   : MaxAge 20s Hello 2s FwdDly 15s MaxHops 20
CIST Root Timers                : MaxAge 20s Hello 2s FwdDly 15s MaxHops 20

MSTP instance 0 - VLANs 10, 20, 30
-------------------------------------------------------------------------------------------------

Bridge              Regional Bridge     RootPath  RootPort    LastTopology  Topology
Identifier          Identifier          Cost      Identifier  Change        Change
hex                 hex                                       sec           cnt
32768002438eefbc3   32768002438eefbc3   0         128.13      0             0

MSTP Port Parameters:

Port        Prio Path Port Uplink State      Role  Designated  Designated          Designated
Num         rity Cost Fast Fast                    Cost        Root                Bridge
Ethernet13  128  4    Y    N      FORWARDING Root  0           32768002438eefbc3   32768002438eefbc3 
```
- show spanning_tree region

```
Region Name                     : regionA
Revision                        : 0
CIST Bridge Identifier          : 32768002438eefbc3
CIST Root Identifier            : 32768002438eefbc3
CIST External Path Cost         : 0
Instances configured            : 1
Last Topology Change            : 0s
Number of Topology Changes      : 0
Bridge Timers                   : MaxAge 20s Hello 2s FwdDly 15s MaxHops 20
CIST Root Timers                : MaxAge 20s Hello 2s FwdDly 15s MaxHops 20
```

- show spanning_tree instance \<instance-id\>

```
MSTP instance 0 - VLANs 10, 20, 30
-------------------------------------------------------------------------------------------------

Bridge              Regional Bridge     RootPath  RootPort    LastTopology  Topology
Identifier          Identifier          Cost      Identifier  Change        Change
hex                 hex                                       sec           cnt
32768002438eefbc3   32768002438eefbc3   0         128.13      0             0
```

- show spanning_tree instance interface \<instance-id\> \<ifname\>

```
Port        Prio Path Port Uplink State      Role  Designated  Designated          Designated
Num         rity Cost Fast Fast                    Cost        Root                Bridge
Ethernet13  128  4    Y    N      FORWARDING Root  0           32768002438eefbc3   32768002438eefbc3 
```

### Statistics Commands
- show spanning_tree statistics instance \<instance-id\>
```
MSTP instance 0 - VLANs 10, 20, 30
--------------------------------------------------------------------
PortNum           BPDU Tx     BPDU Rx     TCN Tx     TCN Rx             
Ethernet13        10	      4           3          4
PortChannel15     20	      6           4          1
```

## Clear Commands
- sonic-clear spanning_tree statistics instance \<instance-id\>
- sonic-clear spanning_tree statistics instance interface \<instance-id\> \<ifname\>

## Debug Commands
Following debug commands will be supported for enabling additional logging which can be viewed in /var/log/stpd.log, orchagent related logs can be viewed in /var/log/syslog.

- debug spanning_tree region
- debug spanning_tree instance \<instance-id\>

Following debug commands will be supported for displaying internal data structures

- debug spanning_tree dump region
- debug spanning_tree dump instance \<instance-id\>
- debug spanning_tree dump instance interface \<instance-id\> \<ifname\>

## Disabled Commands
Following commands are used to configure parameters at VLAN level and these commands are disabled if spanning-tree mode is `mstp`:

- config spanning_tree vlan (enable|disable) \<vlan\>
- config spanning_tree vlan forward_delay \<vlan\> \<fwd-delay-value\>
- config spanning_tree vlan hello \<vlan\> \<hello-value\>
- config spanning_tree vlan max_age \<vlan\> \<max-age-value\>
- config spanning_tree vlan priority \<vlan\> \<priority-value\>
- config spanning_tree vlan interface cost \<vlan\> \<ifname\> \<value\>
- config spanning_tree vlan interface priority \<vlan\> \<ifname\> \<value\>

Also, Region level and Instance level commands will be disabled if spanning-tree mode is `pvst`.


# YANG Model

YANG Model will be extended as follows for MSTP:
```yang
module sonic-stp {

    yang-version 1.1;

    namespace "http://github.com/sonic-net/sonic-stp";
    prefix "stp";

    import sonic-port {
        prefix port;
        revision-date 2019-07-01;
    }

    import sonic-portchannel {
        prefix lag;
        revision-date 2021-06-13;
    }

    import sonic-vlan {
        prefix vlan;
        revision-date 2021-04-22;
    }

    import sonic-device_metadata { 
        prefix device_metadata;
        revision-date 2021-02-27;
    }

    description "STP yang Module for SONiC OS";

    revision 2023-04-18 {
        description "First Revision";
    }

    container sonic-stp {

        container STP_GLOBAL {
            description "Global STP table";

            leaf mode {
                type enumeration {
                    enum "pvst";
                    enum "mstp";
                    enum "disable";
                }
                default "disable";
                description "STP mode";
            }

            leaf forward_delay {
                type uint8 {
                    range "4..30" {
                        error-message "forward_delay value out of range";
                    }
                }
                default 15;
                description "Forward delay in sec";
            }

            leaf hello_time {
                type uint8 {
                    range "1..10" {
                        error-message "hello_time value out of range";
                    }
                }
                default 2;
                description "Hello time in sec";
            }

            leaf max_age {
                type uint8 {
                    range "6..40" {
                        error-message "max_age value out of range";
                    }
                }
                default 20;
                description "Max age";
            }

            leaf rootguard_timeout {
                type uint16 {
                    range "5..600" {
                        error-message "rootguard_timeout value out of range";
                    }
                }
                default 30;
                description "Root guard timeout in sec";
            }

            leaf priority {
                must ". mod 4096 = 0" {
                    error-message "bridge priority must be a multiple of 4096";
                }      

                type uint16 {
                    range "0..61440" {
                        error-message "priority value out of range";
                    }
                }
                default 32768;
                description "Bridge priority";
            }

            leaf max_hops {
                type uint8 {
                    range "1..255" {
                        error-message "max-hops value out of range";
                    }
                }
                default 20;
                description "Max hops";
            }
        }

        container MSTP_REGION {
            description "MSTP Regional operational details";

            leaf region_name {
                type string {
                    length "1..32";
                }
                default "device_metadata:sonic-device_metadata/device_metadata:DEVICE_METADATA/device_metadata:localhost/device_metadata:mac";
                description "Region name";
            }

            leaf revision {
                type uint16 {
                    range "0..65535" {
                        error-message "revision value out of range";
                    }
                }
                default 0;
                description "Region revision";
            }
        }

        container MSTP_INSTANCE {
            description "MSTP instance operational details";

            list MSTP_INSTANCE_LIST {
                key "name";

                leaf name {
                    type string {
                        pattern 'Instance([0-9]|[1-5][0-9]|[6][0-3])';
                    }
                }

                leaf priority {
                    must ". mod 4096 = 0" {
                        error-message "bridge priority must be a multiple of 4096";
                    }

                    type uint16 {
                        range "0..61440" {
                            error-message "priority value out of range";
                        }
                    }
                    default 32768;
                    description "Bridge priority";
                }
            }
        }

        container MSTP_VLAN {
            description "MSTP VLAN to instance mapping";

            list MSTP_VLAN_LIST {
                key "vlan";

                leaf vlan {
                    must "(current() = /vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name)" {
                        error-message "Must condition not satisfied, Try adding Vlan<vlanid>: {}, Example: 'Vlan2': {}";
                    }

                    type leafref {
                        path "/vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name";
                    }
                }

                leaf instance_id {
                    must "(concat('Instance', current()) = ../../../MSTP_INSTANCE/MSTP_INSTANCE_LIST[name=concat('Instance', current())]/name)" {
                        error-message "Must condition not satisfied, Try adding Instance<instanceid>: {}, Example: 'Instance2': {}";
                    }

                    type uint8 {
                        range "0..63";
                    }
                    default 0;
                }
            }
        }

        container MSTP_INSTANCE_PORT {
            description "STP port details per Instance";

            list MSTP_INSTANCE_PORT_LIST {
                key "instance port";

                leaf instance {
                    must "(current() = ../../../MSTP_INSTANCE/MSTP_INSTANCE_LIST[name=current()]/name)" {
                        error-message "Must condition not satisfied, Try adding Instance<instanceid>: {}, Example: 'Instance2': {}";
                    }

                    type leafref {
                        path "/stp:sonic-stp/stp:MSTP_INSTANCE/stp:MSTP_INSTANCE_LIST/stp:name";
                    }
                }

                leaf port {
                    type union {
                        type leafref {
                            path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                        }
                        type leafref {
                            path "/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name";
                        }
                    }
                }

                leaf priority {
                    type uint8 {
                        range "0..240" {
                            error-message "priority value out of range";
                        }
                    }
                    default 128;
                    description "Port priority";
                }

                leaf path_cost {
                    type uint32;
                    description "Port path cost";
                }
            }
        }
    }
}
```

# Rest API Support
Rest API is out of scope for this HLD.

# Warm Boot
Warm boot will not be supported. The IEEE 802.1s standard of MSTP does not define any potential way to support it as this might cause loops in the network. 

User is expected to do a cold reboot when MSTP is running. If a user tries to perform a warm boot while MSTP is enabled, an error message will be displayed. User will first need to disable MSTP so the topology converges and reevaluates the paths.

# Testing Requirements
## Unit test cases
### CLI test cases
1. Verify CLI to enable MSTP globally.
1. Verify CLI to disable MSTP globally.
1. Verify CLI to set bridge max-hops.
1. Verify CLI to set MSTP region name.
1. Verify CLI to set MSTP region revision.
1. Verify CLI to create an instance.
1. Verify CLI to delete an instance
1. Verify CLI to set bridge priority in an instance.
1. Verify CLI to map VLAN to an instance
1. Verify CLI to delete VLAN from an instance.
1. Verify CLI to set interface priority on a per instance basis.
1. Verify CLI to set interface cost on a per instance basis.
1. Verify CLI to display all information related to the region.
1. Verify CLI to display information related to a specific instance.
1. Verify CLI to display information about a specific interface in a specific instance.
1. Verify CLI to display region statistics.
1. Verify CLI to display statistics on a per instance basis.
1. Verify CLI to clear region statistics.
1. Verify CLI to clear statistics on a per instance basis.
1. Verify CLI to clear statistics on a per interface per instance basis.
1. Verify the commands that are disabled for MSTP mode.

### Functional Test Cases
1. Verify CONFIG DB is populated with configured MSTP parameters.
1. Verify multiple VLANs can be mapped to a single instance.
1. Verify instance STP ports are created for its VLAN members.
1. Verify correct format of MSTP BPDU.
1. Verify MSTP traps are created.
1. Verify correct operation of CIST and MSTIs.
1. Verify two bridges are in the same region only if they have the same region name, revision and instance to VLAN mapping.
1. Verify the loop free topology inside and between regions.
1. Verify the operational values of forward delay, max age, hello timer and max hops are of the CIST root.
1. Verify FDB flush as a result of topology change.
1. Verify instance is active only when there is at least one VLAN member of any of the VLANs that are mapped to it.
1. Verify altering bridge priority can alter the selection of CIST root, regional root and MSTI root.
1. Verify altering port priority can alter the selection of designated port.
1. Verify max-hops by changing value.
1. Verify MSTP interoperability with STP, RSTP and PVST.
1. Verify MSTP operational data is synced to APP DB and ASIC DB correctly.
1. Verify MSTP over LAG.
1. Verify MSTP over static breakout ports.

### Logging and Debugging Test Cases
1. Verify debugging logs for a region.
1. Verify debugging logs for an instance.
1. Verify debugging of internal data structure of region.
1. Verify debugging of internal data structure of an instance.
1. Verify debugging of internal data structure of a specific interface in an instance. 

### SAI
1. Verify creation of STP instance.
1. Verify adding VLAN to an instance.
1. Verify deleting VLAN from an instance.
1. Verify adding a port to an instance.
1. Verify deleting port from an instance.
1. Verify port state for different instances.

### L3
1. Verify normal flow of L3 traffic with the MSTP topology.

# References
1. [PVST HLD](https://github.com/sonic-net/SONiC/blob/master/doc/stp/SONiC_PVST_HLD.md)
1. [IEEE 802.1Q-2018](https://standards.ieee.org/ieee/802.1Q/6844/)
1. [IEEE 802.1s-2002](https://standards.ieee.org/ieee/802.1s/1042/)