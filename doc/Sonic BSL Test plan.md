#SONiC BSL Test Plan


## Overview
This document outlines the Sonic BSL test plan. In BSL mode, Sonic device is brought up as an L2 switch. This test plan validates the functionality by running the tests as described in below sections. More details on BSL can be found in this [document](https://github.com/Azure/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode). This must be followed to configure a Sonic device in L2 switch and verify the associated commands before running the below test cases. 

### Scope
---------
This is limited to Sonic device in BSL mode with the minimal functional verification. 


## Test structure 

### Setup configuration
-------------------
L2 configuration on a T0 topology

### Configuration scripts
-------------------------

Configuration is created from https://github.com/Azure/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode. After applying configuration, this also has basic verifications of interfaces and oper status.

The following is an example script to create config file for Mellanox platform
```
sonic-cfggen -t /usr/local/lib/python2.7/dist-packages/usr/share/sonic/templates/l2switch.j2 -p -k Mellanox-SN2700-D48C8
```
The config contains all the ports set to admin-up and configure as untagged member ports of Vlan 1000.

Test cases
----------

### Test case \#1

#### Test objective
Verify basic sanity 

#### Test description
Run sanity test - https://github.com/Azure/sonic-mgmt/blob/master/ansible/roles/test/tasks/base_sanity.yml

### Test case \#2

#### Test objective
Verify FDB learning happens on all ports.

#### Test description
Run fdb test - https://github.com/Azure/sonic-mgmt/blob/master/ansible/roles/test/tasks/fdb.yml 

### Test case \#3

#### Test objective
Verify Vlan configurations, ARP and PING. The current vlan test (vlantb) has two parts - vlan_configure and vlan_test. vlan_configure cannot be run on BSL without modification as it takes into account port-channels. This must be modified to run on BSL configuration. Test must also configure an IP address on Vlan interface. 

This test covers Vlan, ARP and PING tests.

#### Test description
Run fdb test - https://github.com/Azure/sonic-mgmt/blob/master/ansible/roles/test/tasks/vlantb.yml


### Test case \#4

#### Test objective
Verify SNMP. This [document](https://github.com/Azure/SONiC/wiki/How-to-Check-SNMP-Configuration) can be referred for basic SNMP verification and configuring public community string

The current SNMP test must be modified for BSL. The BSL test can cover to get 
  1. MAC table
  2. Interface table
  3. CPU
  4. PSU

#### Test description
Run SNMP test - https://github.com/Azure/sonic-mgmt/blob/master/ansible/roles/test/tasks/snmp.yml

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     |  Sanity              |      Pass           |
| 2.     |  FDB                 |      MAC Learn      |
| 3.     |  VLAN                |   PING,ARP succeeds |
| 4.     |  SNMP                |    Walk succeeds    |
| 5.     |                      |                     |

