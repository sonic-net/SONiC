# HLD Validate interface name length



####  Rev 0.1



# Table of Contents

​	-[Revision](#revision)

​	-[Motivation](#motivation)

​	-[About this Manual](#about-this-manual)

​	-[Design](#design)

​	-[Tests](#tests)



# Revision
| Rev  |   Date   |    Author    | Change Description |
| :--: | :------: | :----------: | ------------------ |
| 0.1  | 10/05/23 | Eden Grisaro | Initial version    |



# Motivation

The kernel can't configure interfaces with names that longer than `IFNAMSIZ`. Since we have this limitation we want to add validation to the SONiC to check the intrfaces name size.



# About this Manual

This document provides an overview of the implementation of adding a validation of the interfaces names size.


# Design

## Add validation to the CLI command
There are few interfaces that we will add the validation:

interface | file path | function name | need to add validation? |
--- | --- | --- | --- |--- |--- |--- |--- |--- |--- |--- |---
Vxlan | sonic-utilities/config/vxlan.py | add_vxlan | yes | 
Vlan | sonic-utilities/config/vlan.py | add_vlan | no |
Vrf | sonic-utilities/config/main.py | add_vrf | no | 
Loopback | sonic-utilities/config/main.py | is_loopback_name_valid | no |
Subinterface | sonic-utilities/config/main.py | add_subinterface | yes | 
Portchannel | sonic-utilities/config/main.py | is_portchannel_name_valid | no |

## Add validation to the Yang model

interface | file path | need to add validation? |
--- | --- | --- | --- |--- |--- |--- |--- |--- |--- |--- |---
Vxlan | sonic-yang-models/yang-models/sonic-vxlan.yang | yes | 
Vlan | sonic-yang-models/yang-models/sonic-vlan.yang | no |
Vrf | sonic-yang-models/yang-models/sonic-vrf.yang | no | 
Loopback | sonic-yang-models/yang-models/sonic-loopback-interface.yang | no |
Subinterface | sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang | yes | 
Portchannel | sonic-yang-models/yang-models/sonic-portchannel.yang | no |


## Subinterface
1. In the sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang we allready has validition of the length of the name leaf.


# Tests
## sonic-utilities:

interface | file path | test name | need to add test? |
--- | --- | --- | --- |--- |--- |--- |--- |--- |--- |--- |---
Vxlan | sonic-utilities/tests/vxlan_test.py | test_config_vxlan_add |yes | 
Vlan | sonic-utilities/tests/vlan_test.py | test_config_vlan_add_member_with_invalid_vlanid | yes |
Vrf | sonic-utilities/tests/vrf_test.py | test_invalid_vrf_name | yes | 
Loopback | sonic-utilities/tests/config_test.py | test_add_loopback_with_invalid_name_adhoc_validation | yes |
Subinterface | sonic-utilities/tests/subintf_test.py | test_invalid_subintf_creation | no | 
Portchannel | sonic-utilities/tests/portchannel_test.py | test_add_portchannel_with_invalid_name_adhoc_validation | yes |

## Yang:
yang tests via YANG or in the utilities

interface | file path | need to add validation? |
--- | --- | --- | --- |--- |--- |--- |--- |--- |--- |--- |---
Vxlan | sonic-yang-models/tests/yang_models_tests/tests/vxlan.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/vxlan.json | yes | 
Vlan | sonic-yang-models/tests/yang_models_tests/tests/vlan.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/vlan.json | yes |
Vrf | sonic-yang-models/tests/yang_models_tests/tests/vrf.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/vrf.json | yes | 
Loopback | sonic-yang-models/tests/yang_models_tests/tests/loopback.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/loopback.json | yes |
Subinterface | sonic-yang-models/tests/yang_models_tests/tests/vlan_sub_interface.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/vlan_sub_interface.json | no | 
Portchannel | sonic-yang-models/tests/yang_models_tests/tests/portchannel.json <br /> sonic-yang-models/tests/yang_models_tests/config_tests/portchannel.json | no |