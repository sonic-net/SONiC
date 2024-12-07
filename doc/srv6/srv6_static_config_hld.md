# Static Configuration of SRv6 in SONiC HLD  

# Table of Contents

- [Revision](#revision)
- [Definition/Abbreviation](#definitionabbreviation)
- [About This Manual](#about-this-manual)
- [1 Introuduction and Scope](#1-introuduction-and-scope)
- [2 Feature Requirements](#2-feature-requirements)
- [2.1 Functional Requirements](#21-functional-requirements)
- [2.2 Configuration and Managment Requirements](#22-configuration-and-management-requirements)
- [2.3 Warm Boot Requirements](#23-warm-boot-requirements)
- [3 Feature Design](#3-feature-design)
- [3.1 New Table in ConfigDB](#31-new-table-in-configdb)
- [3.2 Bgpcfgd Changes](#32-bgpcfgd-changes)
- [3.3 YANG Model](#33-yang-model)
- [4 Unit Test](#4-unit-test)
- [5 References ](#5-references) 

# Revision

| Rev  |   Date    |           Author           | Change Description      |
| :--: | :-------: | :------------------------: | :---------------------: |
| 0.1  | 12/5/2024 |       Changrong Wu         |  Initial version        |


# Definition/Abbreviation

### Table 1: Abbreviations

| ****Term**** | ****Meaning**** |
| -------- | ----------------------------------------- |
| BGP  | Border Gateway Protocol |
| SID  | Segment Identifier  |
| SRv6 | Segment Routing IPv6  |
| SDN | Software Defined Network |
| uSID | Micro Segment |
| VRF  | Virtual Routing and Forwarding  |

# About this Manual

This document provides general information about the design of the enhancements in SONiC to support static configuration of Segmentation Routing over IPv6 protocol, which is crucial for SRv6 SDN deployment (without usage of BGP).

# 1 Introuduction and Scope

This document describes the high-level design of the new features in SONiC to support SRv6 SDN.
The new features include the addtion of a new table in CONFIG_DB to allow static configuration of SRv6 and the enhancement of bgpcfgd to program FRR with input from CONFIG_DB.
Besides, this document also define new YANG model specification and unit-test cases used to validate the aforementioned features.


# 2 Feature Requirements

## 2.1 Functional Requirements

Provide ability to statically configure SRv6 SIDs for block IDs, locators and local functions from CONFIG_DB.

## 2.2 Configuration and Management Requirements

1. User should be able to statically configure block length, locator length and function length for SRv6.

2. User should be able to statically configure a number of SIDs/uSIDs for the local functions of the switch.

## 2.3 Warm Boot Requirements

Warm reboot is intended to be supported for planned system warm reboot.

 

# 3 Feature Design

At the time of writing this document, FRR has been able to program the SRv6 related tables in APPL_DB through fpmsyncd.
However, there is still one gap preventing SONiC being utilized for SRv6 SDN deployment.
Specifically, there is no mechamism in SONiC allowing SDN controllers or users to directly add configuration for SRv6 without involving BGP.

In this document, we first define a new **SRV6_MY_SID_TABLE** table in CONFIG_DB that serves as the configuration source of SRv6 in SONiC.
Then, we design a new SRv6 Manager module in bgpcfgd to subscribe to the **SRV6_MY_SID_TABLE** table and compile changes in CONFIG_DB to changes in the configurations of FRR.
To verify the correctness of the aforementioned flow, we also define the relevant YANG model specification.
The workflow of the new mechanism is shown in the following diagram.

![Static SRv6 Config flow](images/SRv6_bgpcfgd.png)

The design details of each step is described in the following subsections.

## 3.1 New Table in ConfigDB


**SRV6_MY_SID_TABLE**

Description: New table to hold local SID definition and SID to behavior mapping. (A simplified redefinition of SRV6_MY_SID_TABLE in [SRv6_HLD](./srv6_hld.md))

Schema:

```
; New table
; holds local SID to behavior mapping, allow 1:1 or n:1 mapping

key = SRV6_MY_SID_TABLE|ipv6address
; field = value
block_len = blen             ; bit length of block portion in address, default 32
node_len = nlen              ; bit length of node ID portion in address, default 16
func_len = flen              ; bit length of function portion in address, default 16
arg_len = alen               ; bit length of argument portion in address, default 0
action = behavior            ; behaviors defined for the SID, default uN
vrf = VRF_TABLE.key          ; Optional, VRF name for decapsulation actions, only applicable to "uDT6" and "uDT46" by now, default "default"

For example:
    "SRV6_MY_SID_TABLE" : {
        "FCBB:BBBB:20::" : {
           "action": "uN"
        },
        "FCBB:BBBB:20:F1::" : {
           "action": "uDT46",
        },
        "FCBB:BBBB:20:F2::" : {
           "action": "uDT46",
           "vrf":  "VRF-1001"
        },
    }
```


## 3.2 Bgpcfgd changes

To enable automatic programming SRv6 configurations from CONFIG_DB to FRR, we need to add a new module in bgpcfgd to watch changes in **SRV6_MY_SID_TABLE** and compile the corresponding changes in FRR's configurations.
Following the naming convention of modules in bgpcfgd, we call this new module SRv6 Manager.
The new SRv6 Manager are supposed to verify the validity of the configuration entries coming from the CONFIG_DB.
If it gets an invalid configuration input, it should log the event in the syslog and not compile the configuration into FRR.

## 3.3 YANG Model
The simplified version of the YANG model is defined below.
```
module: sonic-srv6
  +--rw sonic-srv6
     +--rw SRV6_MY_SID
     |  +--rw SRV6_MY_SID_LIST* [ip-address]
     |     +--rw ip-address    inet:ipv6-address
     |     +--rw block_len?    uint8
     |     +--rw node_len?     uint8
     |     +--rw func_len?     uint8
     |     +--rw arg_len?      uint8
     |     +--rw action?       enum
     |     +--rw vrf?          -> /vrf:sonic-vrf/VRF/VRF_LIST/name
```
Refer to [sonic-srv6.yang](./sonic-srv6.yang) for the YANG model defined with standard IETF syntax.

## 4 Unit Test

|Test Cases (done on default instance and VRF)| Test Result |
| :------ | :----- |
|add config for a SID with uN action in CONFIG_DB | verify the locator config entry is created in FRR config|
|add config for a SID with uDT46 action associated with VRF-1001 in CONFIG_DB | verify the opcode config entry is created in FRR config with correct VRF|
|add config for a SID with uDT46 action without VRF parameter in CONFIG_DB | verify the opcode config entry is created in FRR config with default VRF|
|(Negative case) add config for a SID without action in CONFIG_DB | verify that the configuration did not get into FRR config |
|(Negative case) add config for a SID with an unsupported action in CONFIG_DB | verify that the configuration did not get into FRR config |
|(Negative case) add config for a decap SID with an invalid VRF name in CONFIG_DB | verify that the configuration did not get into FRR config |
|delete config for a SID with uN action in CONFIG_DB | verify the locator config entry is deleted in FRR config|
|delete config for a SID with uDT46 action associated with VRF-1001 in CONFIG_DB | verify the opcode config entry for the uDT46 action is deleted in FRR config|


## 5 References


