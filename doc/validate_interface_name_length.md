# HLD Validate interface name length



####  Rev 0.1



# Table of Contents

​	-[List of Figures](#list-of-figures)

​	-[Revision](#revision)

​	-[Motivation](#motivation)

​	-[About this Manual](#about-this-manual)

​	-[Design](#design)

​	-[CLI](#cli)

​	-[Flow](#flow)

​	-[Tests](#tests)

# List of Figures
* [flow diagram](#9-Flow)

# Revision
| Rev  |   Date   |    Author    | Change Description |
| :--: | :------: | :----------: | ------------------ |
| 0.1  | 02/22/22 | Eden Grisaro | Initial version    |



# Motivation

The kernel can't configure interfaces with names that longer than `IFNAMSIZ`. Since we have this limitation we want to add validation to the SONiC to check the intrfaces name size.



# About this Manual

This document provides an overview of the implementation of adding a validation of the interfaces names size.


# Design

There are few interfaces that we will add the validation:

## Vxlan 
1. In sonic-utilities/config/vxlan.py, in the "add_vxlan" subcommand we will add validtion of the `vxlan_name`.

## Vrf
1. In the sonic-yang-models/yang-models/sonic-vrf.yang we need to add validition of the length of the name leaf.

##Loopback
1. In the sonic-yang-models/yang-models/sonic-loopback-interface.yang we need to add validition of the length of the name leaf.



There are some interfaces that we allready has validation:

## Vxlan 
1. In the sonic-yang-models/yang-models/sonic-vxlan.yang we allready has validition of the length of the name leaf.

## Vlan 
1. In sonic-utilities/config/vlan.py, in the "add_vlan" subcommand we allready has validition of the length of the vlan name.
2. In the sonic-yang-models/yang-models/sonic-vlan.yang we allready has validition of the length of the name leaf.

## Portchannel
1. In sonic-utilities/config/main.py, in the "is_portchannel_name_valid" subcommand we allready has validition of the length of the portchannel name.
2. In the sonic-yang-models/yang-models/sonic-portchannel.yang we allready has validition of the length of the name leaf.

## Vrf
1. In the sonic-utilities/config/main.py, in the "add_vrf" subcommand we allready has validition of the length of the `vrf_name`.

##Loopback
1. In sonic-utilities/config/main.py, in the "is_loopback_name_valid" subcommand we allready has validition of the length of the loopback name.

Added the marked lines:

![](show_version.png)
![](get_uptime.png)

# CLI

This command displays the "show version" output and in addition, the current date in a new row. 

Usage:
```
show version
```
Example:
```
admin@sonic:~$ show version
SONiC Software Version: SONiC.HEAD.32-21ea29a
Distribution: Debian 9.8
Kernel: 4.9.0-8-amd64
Build commit: 21ea29a
Build date: Fri Mar 22 01:55:48 UTC 2019
Built by: johnar@jenkins-worker-4
Platform: x86_64-mlnx_msn2700-r0
HwSKU: Mellanox-SN2700
ASIC: mellanox
ASIC Count: 1
Serial Number: MT1822K07815
Model Number: MSN2700-CS2FO
Hardware Rev: A1
Uptime: up 3 min,  1 user,  load average: 1.26, 1.45, 0.66
Date: Tue 22 Feb 2022 14:40:15
...
```

# Flow

![](flow.drawio.png)



# Tests

The verification tests and unit tests are not influenced by the add date feature.