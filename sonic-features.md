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
 
##In progress
Features currently in development 
 
- Fast reboot (reboot with less than 30 seconds data plane impact)
- Control plane packet rate limiting (in code review)
- VLAN (in code review and testing)
- ACL permit/deny
- Netbouncer (tunnel decap)
- SNMP subagent hardening
- LLDP update for SwSS
- Warm boot (ISSU-like feature, less than 1 second data plane impact)

##Committed Roadmap
- Open source build (make it easier to build sonic)
- Open source mgmt repo (high priority)
- Open source test (high priority)
- DHCP relay agent 
- Buffer monitoring 
- ERSPAN/Everflow (mirror packet via ACL and encap in GRE)
- sFlow
- IPV6
- Hardware table usage and capacity reporting (FIB, ACL, etc)  

##What is not supported
Here we attempt to list some of the features that may be surprising which are not supported, nor in the current roadmap.
  
- Transceiver graceful insertion/removal
- Graceful reconfiguration of breakout cables (qsfp to sfp)
- No plan for OSPF, ISIS, etc, but might work fine as quagga supports these
