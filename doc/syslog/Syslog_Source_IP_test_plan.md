# Syslog Source IP Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| Syslog Source IP HLD | [https://github.com/sonic-net/SONiC/blob/master/doc/syslog/syslog-design.md]|


## Overview

SSIP is a feature which allows user to change UDP packet source IP address.
Any configured address can be used for source IP mangling.
This might be useful for security reasons.

SSIP also extends the existing syslog implementation with VRF device and server UDP port configuration support. The feature doesn't change the existing DB schema which makes it fully backward compatible.

### Scope

The test is to verify SSIP take effect after doing relevant SSIP configuration   

### Scale / Performance

No scale/performance test involved in this test plan

### Related **DUT** CLI commands
```
User interface:

config
|--- syslog
     |--- add <server_ip> OPTIONS
     |--- del <server_ip>

Options:

config syslog add server_ip

-s|--source - source ip address
-p|--port - server udp port
-r|--vrf - vrf device


show
|--- syslog
```

### Supported topology
The tests will be supported on any topo.


### Test cases #1 -  Configure syslog server with VRF/Source:unset/unset
1. Configure syslog server with VRF/Source:unset/unset like below:
```
config syslog add 2.2.2.2 
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     N/A         514     default
```
3. Check the corresponding interface will send syslog message with port 514 on dut
4. Del syslog server config like below:
```
config syslog del 2.2.2.2 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface will not send syslog message with port 514 on dut
7. Repeat steps 1-6 by setting different port and IPv6 address, and check the port of syslog message will be changed to the set one


### Test cases #2 -  Configure syslog server with VRF/Source: unset/set
1. Configure syslog server with VRF/Source: unset/set like below:
```
config syslog add 2.2.2.2 --source 1.1.1.1
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     1.1.1.1      514    default
```
3. Check the corresponding interface will send syslog message with port 514 and src ip 1.1.1.1 on dut
4. Del syslog server config like below:
```
config syslog del 2.2.2.2
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface will not send syslog message with port 514 and src ip 1.1.1.1 on dut
7. Repeat steps 1-6 by setting different port and IPV6 address, and check the port of syslog message will be changed to the set one


### Test cases #3 -  Configure syslog server with VRF/Source: set/unset
1. For vrf: default, mgmt, Vrf-data, Configure syslog server with VRF/Source: set/unset like below:
```
config syslog add 2.2.2.2 --vrf default
config syslog add 3.3.3.3 --vrf mgmt
config syslog add 2222::2222 --vrf Vrf-data
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2       N/A        514     default
3.3.3.3       N/A        514     mgmt
2222::2222    N/A        514     Vrf-data
```
3. Check the corresponding interface will send syslog message with port 514 on dut
4. Del syslog server config like below:
```
config syslog del 2.2.2.2
config syslog del 3.3.3.3
config syslog del 2222::2222 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface will not send syslog message with port 514 on dut
7. Repeat steps 1-6 by setting different port, and check the port of syslog message will be changed to the set one


### Test cases #4 -  Configure syslog server with VRF/Source: set/set
1. For vrf: default, mgmt, Vrf-data, Configure syslog server with VRF/Source: set/set like below:
```
config syslog add 2.2.2.2 ---source 1.1.1.1 --vrf default
config syslog add 3.3.3.3 ---source 5.5.5.5 --vrf mgmt
config syslog add 2222::2222 ---source 1111::1111 --vrf Vrf-data
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     1.1.1.1      514     default
3.3.3.3     5.5.5.5      514     mgmt
2222::2222  1111::1111   514     Vrf-data
```
3. Check the corresponding interface will send syslog message with port 514 and related source IP on dut
4. Del syslog server config like below:
```
config syslog del 2.2.2.2
config syslog del 3.3.3.3
config syslog del 2222::2222 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface will not send any syslog message with related port and source ip
7. Repeat steps 1-6 by setting different port, and check the port of syslog message will be changed to the set one


### Test cases #5 -  Disable mgmt VRF or remove data VRF exists in syslog config, there will be an error prompt
1. Configure syslog sever with VRF/Source: set/set like below:
```
config syslog add 3.3.3.3 --source 5.5.5.5 --vrf mgmt
config syslog add 2222::2222 --source 1111::1111 --vrf Vrf-data
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
3.3.3.3     5.5.5.5      514     mgmt
2222::2222  1111::1111   514     Vrf-data
```
3. Disable mgmt VRF or remove Data VRF
4. Check there is an error prompt such as: VRF exists in syslog config, it can not be disabled or removed.


### Test cases #6 -  Configure syslog server with non-existing source IP
1. Configure syslog server with a source ip not existing in any vrf:
```
config syslog add 2.2.2.2 ---source 100.100.111.12
```
2. Check there is relevant error prompt like blow
```
Error: Invalid value for "-s" / "--source": 100.100.111.12 IP doesn't exist in Linux default VRF
```
3. Check the syslog config doesn't include relevant item


### Test cases #7 -  Configure syslog server with source IP in the other vrf
1. Configure ip on one specified vrf such as default
2. Configure syslog server with source IP in the other vrf such as Vrf-data:
```
config syslog add 2.2.2.2 ---source 10.210.24.128 --vrf Vrf-data
```
3. Check there is relevant error prompt like blow
```
Error: Invalid value for "-s" / "--source": 10.210.24.128 IP doesn't exist in Linux Vrf-data VRF
```
4. Check the syslog config doesn't include relevant item


### Test cases #8-  Configure syslog server with non-existing vrf 
1. Configure syslog server with non-existing vrf:
```
config syslog add 2222::2222  --vrf vrf-non
```
2. Check there is relevant error prompt like blow 
```
Error: Invalid value for "-r" / "--vrf": invalid choice: vrf-non. (choose from default, Vrf-red)
```
 3. Check the syslog config doesn't include relevant item
 
 
### Test cases #9 -  After Configure syslog server and save config, do cold/fast/warm reboot, check syslog config still work
1. Configure syslog server with VRF/Source: set/set like below:
```
config syslog add 2.2.2.2 --source 1.1.1.1 --vrf default
config syslog add 3.3.3.3 --source 5.5.5.5 --vrf mgmt
config syslog add 2222::2222 --source 1111::1111 --vrf Vrf-data
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     1.1.1.1      514     default
3.3.3.3     5.5.5.5      514     mgmt
2222::2222  1111::1111   514     Vrf-data
```
3. Check the corresponding interface will send syslog message with port 514 and related source IP on dut
4. Save config and do cold/fast/warm reboot
5. Check Syslog config still work
