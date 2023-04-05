#SONiC Basic L2 Mode Test Plan


## Overview
This document outlines the test plan for SONiC as a basic L2 switch. This test plan validates the functionality by running the tests as described in below sections. More details can be found in this [document](https://github.com/sonic-net/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode). This must be followed to configure a Sonic device in L2 switch and verify the associated commands before running the below test cases. 

### Scope
---------
This is limited to Sonic device in basic L2 mode with the minimal functional verification. 


## Test structure 

### Setup configuration
-------------------
L2 configuration on a T0 topology

### Configuration scripts
-------------------------

Configuration is created from https://github.com/sonic-net/SONiC/wiki/L2-Switch-mode#3-generate-a-configuration-for-l2-switch-mode. After applying configuration, this also has basic verifications of interfaces and oper status.

The following is an example script to create config file for Mellanox platform
```
sonic-cfggen -H -p -k $HWSKU --preset l2
```

We make sure that the config has a mac by providing `-H` option, and correct ports (based on port_config.ini) by providing HWSKU to `-k` and `-p` options.
The config contains all the ports set to admin-up and configure as untagged member ports of Vlan 1000.

Test cases
----------

### Test case \#1

#### Test objective
Verify basic sanity. This checks if the orchagent and syncd processes are running and the links are up.
 Triggered before and after each test case

#### Test description
Run sanity check - https://github.com/sonic-net/sonic-mgmt/blob/master/tests/common/sanity_check.py

### Test case \#2

#### Test objective
Verify FDB learning happens on all ports.

#### Test description
Run fdb test - https://github.com/sonic-net/sonic-mgmt/blob/master/tests/fdb/test_fdb.py

### Test case \#3

#### Test objective
Verify Vlan configurations, ARP and PING. The current vlan test (vlantb) has two parts - vlan_configure and vlan_test. vlan_configure cannot be run on basic L2 mode without modification as it takes into account port-channels. Test must also configure an IP address on Vlan interface. 

This test covers Vlan, ARP and PING tests.

#### Test description
Run fdb test - https://github.com/sonic-net/sonic-mgmt/blob/master/tests/vlan/test_vlan.py



### Test case \#4

#### Test objective
Verify SNMP. This [document](https://github.com/sonic-net/SONiC/wiki/How-to-Check-SNMP-Configuration) can be referred for basic SNMP verification and configuring public community string

 The Basic L2 mode test can cover to get 
  1. MAC table
  2. Interface table
  3. CPU
  4. PSU

#### Test description
Run SNMP tests:
 - https://github.com/sonic-net/sonic-mgmt/tree/master/tests/snmp/test_snmp_interfaces.py
 - https://github.com/sonic-net/sonic-mgmt/tree/master/tests/snmp/test_snmp_cpu.py
 - https://github.com/sonic-net/sonic-mgmt/tree/master/tests/snmp/test_snmp_psu.py

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     |  Sanity              |      Pass           |
| 2.     |  FDB                 |      MAC Learn      |
| 3.     |  VLAN                |   PING,ARP succeeds |
| 4.     |  SNMP                |    Walk succeeds    |
| 5.     |                      |                     |

