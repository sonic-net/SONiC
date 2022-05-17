# Syslog Source IP Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| Syslog Source IP HLD | [will update here once the design HLD is merged to master ]|


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

show
|--- syslog

Options:

config syslog add server_ip

-s|--source - source ip address
-p|--port - server udp port
-r|--vrf - vrf device

```

### Supported topology
The test will be supported on any.


### Test cases #1 -  Configure syslog server with VRF/Source:unset/unset
1. Configure syslog server with VRF/Source:unset/unset like below:
```
config syslog add '2.2.2.2' 
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     N/A         514     default
```
3. Check the corresponding interface of rsyslog server can receive the syslog message with port 514
4. Del syslog server config like below:
```
config syslog del '2.2.2.2' 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface of rsyslog server can not receive any syslog message with port 514
7. Repeat steps 1-6 by setting different port, and check the port of received syslog message will be changed to the set one


### Test cases #2 -  Configure syslog server with VRF/Source: unset/set
1. Configure syslog server with VRF/Source: unset/set like below:
```
config syslog add '2.2.2.2' --source "1.1.1.1"
```
2. Check syslog config by show syslog, the result should like below:
```
# show syslog
SERVER      SOURCE      PORT    VRF
----------  ----------  ------  --------
2.2.2.2     1.1.1.1      514    default
```
3. Check the corresponding interface of rsyslog server can receive the syslog message with port 514 and src ip 1.1.1.1
4. Del syslog server config like below:
```
config syslog del '2.2.2.2' 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface of rsyslog server can not receive any syslog message with port 514 and src ip 1.1.1.1
7. Repeat steps 1-6 by setting different port, and check the port of received syslog message will be changed to the set one


### Test cases #3 -  Configure syslog server with VRF/Source: set/unset
1. For vrf: default, mgmt, Vrf-data, Configure syslog server with VRF/Source: set/unset like below:
```
config syslog add '2.2.2.2' --vrf "default"
config syslog add '3.3.3.3' --vrf "mgmt"
config syslog add '2222::2222' --vrf "Vrf-data"
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
3. Check the corresponding interface of rsyslog server can receive the syslog message with port 514
4. Del syslog server config like below:
```
config syslog del '2.2.2.2'
config syslog del '3.3.3.3'
config syslog del '2222::2222' 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface of rsyslog server can not receive any syslog message with port 514
7. Repeat steps 1-6 by setting different port, and check the port of received syslog message will be changed to the set one


### Test cases #4 -  Configure syslog server with VRF/Source: set/set
1. For vrf: default, mgmt, Vrf-data, Configure syslog server with VRF/Source: set/set like below:
```
config syslog add '2.2.2.2' ---source "1.1.1.1" --vrf "default"
config syslog add '3.3.3.3' ---source "5.5.5.5" --vrf "mgmt"
config syslog add '2222::2222' ---source "1111::1111" --vrf "Vrf-data"
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
3. Check the corresponding interface of rsyslog server can receive the syslog message with correct port and source ip
4. Del syslog server config like below:
```
config syslog del '2.2.2.2'
config syslog del '3.3.3.3'
config syslog del '2222::2222' 
```
5. Check syslog config by show syslog, the relevant config should be removed
6. Check the corresponding interface of rsyslog server can not receive any syslog message with correct port and source ip
7. Repeat steps 1-6 by setting different port, and check the port of received syslog message will be changed to the set one


### Test cases #5 -  Disable mgmt VRF or remove data VRF exists in syslog config, there will an error prompt
1. Configure syslog sever with VRF/Source: set/set like below:
```
config syslog add '3.3.3.3' ---source "5.5.5.5" --vrf "mgmt"
config syslog add '2222::2222' ---source "1111::1111" --vrf "Vrf-data"
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