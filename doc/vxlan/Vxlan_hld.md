# Vxlan SONiC
# High Level Design Document
### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Subsystem Requirements Overview](#1-subsystem-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)

	* [1.2 CLI requirements](#12-cli-requirements)

  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
      * [2.1.1 Vxlan Table](#211-Vxlan-table)
    * [2.2 App DB](#22-counters-db)
      * [2.2.1 VNET Table](#221-Vnet_table)
    * [2.4 Orchestration Agent](#24-orchestration-agent)
    * [2.6 SAI](#26-sai)
	* [2.7 CLI](#27-cli)
	  * [2.7.1 Vxlan utility interface](#271-vxlan-utility-interface)
	    * [2.7.1.1 Vxlan utility config syntax](#2711-vxlan-utility-config-syntax)
		* [2.7.1.2 Vxlan utility show syntax](#2712-vxlan-utility-show-syntax)
      * [2.7.2 Config CLI command](#272-config_cli_command)
	  * [2.7.3 Show CLI command](#273-show_cli_command)

  * [3 Flows](#3-flows)
	* [3.1 Vxlan flow](#31-vxlan-monitoring)
	* [3.2 Vxlan CLI config](#32-vxlan-cli-config)
	* [3.3 Vxlan CLI show](#33-vxlan-cli-show)


###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             |     Prince Sunny   | Initial version                   |

# About this Manual
This document provides general information about the Vxlan feature implementation in SONiC.
# Scope
This document describes the high level design of the Vxlan feature. EVPN for Vxlan and configuring Linux kernel with Vxlan interface is currently beyond the scope of this document
# Definitions/Abbreviation
###### Table 2: Abbreviations

# 1 Subsystem Requirements Overview
## 1.1 Functional requirements
Detailed description of the Vxlan feature requirements is here: [VNET Requirements](https://github.com/lguohan/SAI/blob/vni/doc/SAI-Proposal-QinQ-VXLAN.md).

This section describes the SONiC requirements for Vxlan feature. 

At a high level the following should be supported:

- VNET peering between customer VMs and Baremetal servers
- Symmetric model of IRB
- CLI commands to configure Vxlan

## 1.2 Orchagent requirements
Vxlan orchagent:
 - Should be able to create VRF/VLAN to VNI mapping and also monitor for peering configurations. 
 - Should be able to create tunnels and encap/decap mappers. 

Route orchagent:
 - Should be able to handle routes within a VNET 
 - Should be VRF aware

FDB orchagent:
 - Should be VTEP aware
 
## 1.3 CLI requirements
- User should be able to get FDB learnt per VNI
- User should be able to configure VTEPs

# 2 Modules Design
## 2.1 Config DB
### 2.1.1 VXLAN Table
New table will be added to Config DB
 
 VXLAN_TUNNEL:{{tunnel_name}} 
    "src_ip": {{ip_address}} 
    "dst_ip": {{ip_address}}


VXLAN_TUNNEL_MAP|{{tunnel_name}}|{{tunnel_map}}
       "vni_id": {{ vni_id}}
       "vlan_id": {{ vlan_id }}

 
 




