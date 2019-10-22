#SONiC BSL Test Plan


## Overview
This document outlines the Sonic BSL test plan. In BSL mode, Sonic device is brought up as an L2 switch. This test plan validates the functionality by running the tests as described below.

### Scope
---------
This is limited to Sonic device in BSL mode with the minimal functional verification. 


## Test structure 
=================

### Setup configuration
-------------------
A typical T0 configuration

### Configuration scripts
-------------------------
The following is the script to create config file for Mellanox platform
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

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     |  Sanity              |         Pass        |
| 2.     |  FDB                 |         MAC Learn   |
| 3.     |                      |                     |
| 4.     |                      |                     |
| 5.     |                      |                     |

