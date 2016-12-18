#SONIC Feature List
##Current 
Features which are implemented, tested and deployed in production. 
 
- Compatible with image install using ONIE and Aboot (Arista bootloader)
- Incremental software update
- BGP 
- ECMP 
- QOS - ECN
- Priority Flow Control (PFC - 802.1Qbb)
- WRED
- COS
- SNMP
- Syslog 
- LLDP
- NTP 
- LAG
- tcpdump for packets sent to CPU 
- AD based AAA
- Netbouncer (tunnel decap)
- SNMP subagent hardening 
- COPP
- QOS - RDMA
- DHCP Relay Agent

##In progress
Features currently in development 
 
- Fast reboot (reboot with less than 30 seconds data plane impact)
- Control plane packet rate limiting
- VLAN (in testing)
- ACL permit/deny
- LLDP update for SwSS
- IPV6 (in testing)
- Hardware table usage and capacity reporting (FIB, ACL, etc) 
- ERSPAN/Everflow (mirror packet via ACL and encap in GRE)

##Committed Roadmap
- Warm Reboot
- Buffer monitoring 
- sFlow
- VxLAN

##What is not supported
Here we attempt to list some of the features that may be surprising which are not supported, nor in the current roadmap.
  
- Transceiver graceful insertion/removal
- Graceful reconfiguration of breakout cables (qsfp to sfp)
- No plan for OSPF, ISIS, etc, but might work fine as quagga supports these
