# SONiC SNMP Changes to support IPv6 #

This document captures the changes required to support SNMP over IPv6.

## Motivation ##

SNMP query over IPv6 address fails in certain scenarios on single asic platforms.
Ideally, SNMP over IPv6 should be successful over both IPv4 and IPv6.

## Current configurtion for SNMP ##

Currently, snmpd process inside SNMP docker uses snmpd.conf as the configuration file.
One of the configuration directives in snmpd.conf is *agentaddress*.
*agentaddress* defines list of listening address on which SNMP request can be received.
In SONiC, the default listening address is 'any ip'. 
```
agentAddress udp:161
agentAddress udp6:161
```
The other method is to use the below configuration command to configure agent address.
```
config snmpagentaddress add <ip>
```

## Issue seen with IPv6 ##
In case of SNMP query over IPv6, the SNMP query fails with timeout.
This SNMP query fails over IPv6 because SNMP response goes out with the incorrect SRC IP.
This SRC IP is incorrect in SNMP packet as snmpd does not keep track of the DST IP from the SNMP request packet.
Below is a packet capture showing SNMP request packet sent to DUT Loopback IPV6 address with  SRC IP as port-channel IP of cEOS neighbor. The SNMP response packet goes out with SRC address as DUT port-channel IP whereas it should have been the DUT Loopback IPv6 address.

```
23:18:51.620897  In 22:26:27:e6:e0:07 ethertype IPv6 (0x86dd), length 105: fc00::72.41725 > fc00:1::32.161:  C="msft" GetRequest(28)  .1.3.6.1.2.1.1.1.0
23:18:51.621441 Out 28:99:3a:a0:97:30 ethertype IPv6 (0x86dd), length 241: fc00::71.161 > fc00::72.41725:  C="msft" GetResponse(162)  .1.3.6.1.2.1.1.1.0="SONiC Software Version: SONiC.xxx - HwSku: xx - Distribution: Debian 10.13 - Kernel: 4.19.0-12-2-amd64"
```
**Sequence of SNMP request and response**

1. SNMP request will be sent with SRC IP fc00::72 DST IP fc00:1::32
2. SNMP request is received at SONiC device is sent to snmpd which is listening on port 161 :::161/
3. snmpd process will parse the request create a response and sent to DST IP fc00::72.
4. snmpd process does not track the DST IP on which the SNMP request was received, which in this case is Loopback IP.
snmpd process will only keep track what is tht IP to which the response should be sent to.
5. snmpd process will send the response packet.
Kernel will do a route look up on destination IP and find the best path.
ip -6 route get fc00::72
fc00::72 from :: dev PortChannel101 proto kernel src fc00::71 metric 256 pref medium
6. Using the "src" ip from above, the response is sent out. This SRC ip is that of the PortChannel and not the device Loopback IP.

The same issue is seen when SNMP query is sent from a remote server over Management IP.
SONiC device eth0 --------- Remote server
SNMP request comes with SRC IP <Remote_server> DST IP
If kernel finds best route to Remote_server_IP is via BGP neighbors, then it will send the response via front-panel interface with SRC IP as Loopback IP instead of Management IP.


Main issue is that in case of IPv6, snmpd ignores the IP address to which SNMP request was sent, in case of IPv6.
In case of IPv4, snmpd keeps track of DST IP of SNMP request, it will keep track if the SNMP request was sent to mgmt IP or Loopback IP.
Later, this IP is used in ipi_spec_dst as SRC IP which helps kernel to find the route based on DST IP using the right SRC IP.
https://github.com/net-snmp/net-snmp/blob/master/snmplib/transports/snmpUDPBaseDomain.c#L300
ipi.ipi_spec_dst.s_addr = srcip->s_addr
Reference: https://man7.org/linux/man-pages/man7/ip.7.html

**This issue is not seen on multi-asic platform, why?**

On multi-asic platform, there exists different network namespaces.
SNMP docker with snmpd process runs on host namespace.
Management interface belongs to host namespace.
Loopback0 is configured on asic namespaces.
Additional inforamtion on how the packet coming over Loopback IP reaches snmpd process running on host namespace: #5420
Because of this separation of network namespaces, the route lookup of destination IP is confined to routing table of specific namespace where packet is received.
If packet is received over management interface, SNMP response also is sent out of management interface. Same goes with packet received over Loopback Ip.

## Changes done to fix the issue ##

Currently snmpd listens on any ip by default, this default behavior is changed to listen on management and Loopback0 IP addresses. 
Before the change:
snmpd listens on any IP, snmpd binds to IPv4 and IPv6 sockets as below:
```
netsnmp_udpbase: binding socket: 7 to UDP: [0.0.0.0]:0->[0.0.0.0]:161
trace: netsnmp_udp6_transport_bind(): transports/snmpUDPIPv6Domain.c, 303:
netsnmp_udpbase: binding socket: 8 to UDP/IPv6: [::]:161
```
When IPv4 response is sent, it goes out of fd 7 and IPv6 response goes out of fd 8.
When IPv6 response is sent, it does not have the right SRC IP and it can lead to the issue described.

When snmpd listens on specific Loopback/Management IPs, snmpd binds to different sockets:
```
trace: netsnmp_udpipv4base_transport_bind(): transports/snmpUDPIPv4BaseDomain.c, 207:
netsnmp_udpbase: binding socket: 7 to UDP: [0.0.0.0]:0->[10.250.0.101]:161
trace: netsnmp_udpipv4base_transport_bind(): transports/snmpUDPIPv4BaseDomain.c, 207:
netsnmp_udpbase: binding socket: 8 to UDP: [0.0.0.0]:0->[10.1.0.32]:161
trace: netsnmp_register_agent_nsap(): snmp_agent.c, 1261:
netsnmp_register_agent_nsap: fd 8
netsnmp_udpbase: binding socket: 10 to UDP/IPv6: [fc00:1::32]:161
trace: netsnmp_register_agent_nsap(): snmp_agent.c, 1261:
netsnmp_register_agent_nsap: fd 10
netsnmp_ipv6: fmtaddr: t = (nil), data = 0x7fffed4c85d0, len = 28
trace: netsnmp_udp6_transport_bind(): transports/snmpUDPIPv6Domain.c, 303:
netsnmp_udpbase: binding socket: 9 to UDP/IPv6: [fc00:2::32]:161
```

When SNMP request comes in via Loopback IPv4, SNMP response is sent out of fd 8
```
trace: netsnmp_udpbase_send(): transports/snmpUDPBaseDomain.c, 511:
netsnmp_udp: send 170 bytes from 0x5581f2fbe30a to UDP: [10.0.0.33]:46089->[10.1.0.32]:161 on fd 8
```
When SNMP request comes in via Loopback IPv6, SNMP response is sent out of fd 10
```
netsnmp_ipv6: fmtaddr: t = (nil), data = 0x5581f2fc2ff0, len = 28
trace: netsnmp_udp6_send(): transports/snmpUDPIPv6Domain.c, 164:
netsnmp_udp6: send 170 bytes from 0x5581f2fbe30a to UDP/IPv6: [fc00::42]:43750 on fd 10
```
This separation of socket fd will ensure that SNMP response goes out with the right SRC address.

This change is also more secure approach instead of listening over any ip.


### Effects of this change ###
1. By default, SNMP will listen on Management and Loopback0 IPs configured via config_db.
2. By default, SNMP will no longer listen on any IP.

### Known issue with this approach ##
SNMP query will not work over management IP if DHCP is used to confiure management IP.
https://github.com/sonic-net/sonic-buildimage/issues/16165

**Possible solution**

Update STATE_DB with DHCP configured management IP address.
Modify SNMP to get notified on the change in IP address and restart SNMP service if IP address is modified and snmpd should listen on the newly obtained management IP address.

### Pull request to support this change ###

1. [SNMP][IPv6]: Fix SNMP IPv6 reachability issue in certain scenarios https://github.com/sonic-net/sonic-buildimage/pull/15487
2. [SNMP][IPv6]: Fix to use link local IPv6 address as snmp agentAddress https://github.com/sonic-net/sonic-buildimage/pull/16013
3. [SNMP][IPv6][202012]: Fix SNMP IPv6 reachability issue in certain scenarios https://github.com/sonic-net/sonic-buildimage/pull/16329 https://github.com/sonic-net/sonic-buildimage/pull/16329


