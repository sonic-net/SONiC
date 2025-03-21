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
| 0.2  | 12/20/2024 |      Changrong Wu         | Update to use two tables per SONiC Routing WG discussion |
| 0.3  | 03/17/2025 |      Changrong Wu         | Add Bgpcfgd configuration compilation examples |


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

This document provides general information about the design of the enhancements in SONiC to support static configuration of Segment Routing over IPv6 protocol, which is crucial for SRv6 SDN deployment (without usage of BGP).

# 1 Introuduction and Scope

This document describes the high-level design of the new features in SONiC to support SRv6 SDN.
The new features include the addtion of a new table in CONFIG_DB to enable configuration of SRv6 and the enhancement of bgpcfgd to program FRR with input from CONFIG_DB.
Besides, this document also define new YANG model specification and unit-test cases used to validate the aforementioned features.

Note: frrcfgd in SONiC is also able to program SRv6 configurations to FRR but it is designed for scenarios where BGP is used to propagate SRv6 SIDs. SONiC users can choose either bgpcfgd or frrcfgd to program FRR configurations according to their own use cases freely.


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

In this document, we define two new tables in CONFIG_DB, i.e. **SRV6_MY_LOCATORS** and **SRV6_MY_SIDS**, which serves as the configuration source of SRv6 in SONiC.
Then, we design a new SRv6 Manager module in bgpcfgd to subscribe to the two tables and compile changes in CONFIG_DB to changes in the configurations of FRR (Note: the new SRv6 Manager relies on the new configuration CLI brought in by [FRR PR#16894](https://github.com/FRRouting/frr/pull/16894)).
To verify the correctness of the aforementioned flow, we also define the corresponding YANG model specification.
The workflow of the new mechanism is shown in the following diagram.

![Static SRv6 Config flow](images/SRv6_bgpcfgd.png)

The design details of each step is described in the following subsections.

## 3.1 New Table in ConfigDB

**SRV6_MY_LOCATORS**

Description: New table to hold the locators configured to the node.

Schema:

```
; New table
; holds SRv6 locators configured to the local node.

key = SRV6_MY_LOCATORS|locator_name
; field = value
prefix = locator_prefix      ; ipv6 address that represents the locator, which is also the IPv6 prefix for all SIDs under the locator
block_len = blen             ; bit length of block portion in address, default 32
node_len = nlen              ; bit length of node ID portion in address, default 16
func_len = flen              ; bit length of function portion in address, default 16
arg_len = alen               ; bit length of argument portion in address, default 0
vrf = VRF_TABLE.key          ; the VRF that the locator belongs to, default "default"

For example:
   "SRV6_MY_LOCATORS" : {
      "loc1" : {
         "prefix" : "FCBB:BBBB:20::"
      },
      "loc2" : {
         "prefix" : "FCBB:BBBB:21::"
      }
   }
```


**SRV6_MY_SIDS**

Description: New table to hold local SID definition and SID to behavior mapping.

Schema:

```
; New table
; holds local SID to behavior mapping, the keys are the locator name plus the full IPv6 addresses of the SIDs

key = SRV6_MY_SIDS|locator|ip_prefix
; field = value
action = behavior            ; behaviors defined for the SID, default uN
decap_dscp_mode = decap_dscp_mode  ; Mandatory, the parameter that specifies how the node should handle DSCP bits when it performs decapsulation
decap_vrf = VRF_TABLE.key          ; Optional, VRF name for decapsulation actions, default "default", only applicable to uDT4/uDT46/uDT6 actions

For example:
    "SRV6_MY_SIDS" : {
        "loc1|FCBB:BBBB:20::/48" : {
           "action": "uN",
           "decap_dscp_mode": "pipe"
        },
        "loc1|FCBB:BBBB:20:F1::/64" : {
           "action": "uDT46",
           "decap_dscp_mode": "pipe"
        },
        "loc2|FCBB:BBBB:21::/48" : {
           "action": "uN",
           "decap_dscp_mode": "uniform"
        },
    }
```

We plan to support the staic configurations of the SRv6 behaviors in the system gradually.
The current list of supported SRv6 behaviors allowed to be define in CONFIG_DB is as follows:

| Alias | SRv6 Behaviors |
| :------ | :----- |
| uN | End with NEXT-CSID |
| uDT46 | End.DT46 with CSID |

## 3.2 Bgpcfgd changes

To enable automatic programming SRv6 configurations from CONFIG_DB to FRR, we need to add a new module in bgpcfgd to watch changes in **SRV6_MY_LOCATORS** and **SRV6_MY_SIDS** and compile the corresponding changes in FRR's configurations.
Following the naming convention of modules in bgpcfgd, we call this new module SRv6 Manager.
The new SRv6 Manager are supposed to verify the validity of the configuration entries coming from the CONFIG_DB.
If it gets an invalid configuration input, it should log the event in the syslog and not compile the configuration into FRR.
To help users understand how bgpcfgd programs the configuration, we show two examples of the configuration respectively for locator and SIDs.

## 3.2.1 Bgpcfgd Locator Configuration Compilation

For the following locator configuration entry in CONFIG_DB:
```
"SRV6_MY_LOCATORS" : {
   "loc1" : {
      "prefix" : "FCBB:BBBB:20::"
   }
}
```
Bgpcfgd will compile the following configuration in FRR:
```
segment-routing
   srv6
      locators
         locator loc1
            prefix fcbb:bbbb:20::/48 block-len 32 node-len 32 func-bits 16
            behavior usid
```

## 3.2.2 Bgpcfgd Static SIDs Configuration Compilation
For the following SIDs configuration entries in CONFIG_DB:
```
"SRV6_MY_SIDS" : {
   "loc1|FCBB:BBBB:20::/48" : {
      "action": "uN",
      "decap_dscp_mode": "pipe"
   },
   "loc1|FCBB:BBBB:20:F1::/64" : {
      "action": "uDT46",
      "decap_vrf": "Vrf1",
      "decap_dscp_mode": "pipe"
   },
}
```
Bgpcfgd will compile the following configuration in FRR:
```
segment-routing
   srv6
      static-sids
         sid fcbb:bbbb:20::/48 locator loc1 behavior uN
         sid fcbb:bbbb:20:f1::/64 locator loc1 behavior uDT46 vrf Vrf1
```

## 3.3 YANG Model
The simplified version of the YANG model is defined below.
```
module: sonic-srv6
  +--rw sonic-srv6
     +--rw SRV6_MY_LOCATORS
     |  +--rw SRV6_MY_LOCATORS_LIST* [locator_name]
     |     +--rw locator_name    string
     |     +--rw prefix          inet:ipv6-address
     |     +--rw block_len?      uint8
     |     +--rw node_len?       uint8
     |     +--rw func_len?       uint8
     |     +--rw arg_len?        uint8
     |     +--rw vrf?            union
     +--rw SRV6_MY_SIDS
        +--rw SRV6_MY_SIDS_LIST* [locator ip_prefix]
           +--rw ip_prefix          inet:ipv6-prefix
           +--rw locator            -> /sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/locator_name
           +--rw action?            enumeration
           +--rw decap_vrf?         union
           +--rw decap_dscp_mode?   enumeration
```
Refer to [sonic-yang-models](https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-yang-models) for the YANG model defined with standard IETF syntax.

## 4 Unit Test

|Test Cases | Test Result |
| :------ | :----- |
|add config for a SID with uN action in CONFIG_DB | verify the locator config entry is created in FRR config|
|add config for a SID with uDT46 action in CONFIG_DB | verify the opcode config entry is created in FRR config with default VRF|
|(Negative case) add config for a SID without action in CONFIG_DB | verify that the configuration did not get into FRR config |
|(Negative case) add config for a SID with an unsupported action in CONFIG_DB | verify that the configuration did not get into FRR config |
|delete config for a SID with uN action in CONFIG_DB | verify the locator config entry is deleted in FRR config|
|delete config for a SID with uDT46 action in CONFIG_DB | verify the opcode config entry for the uDT46 action is deleted in FRR config|


## 5 References


