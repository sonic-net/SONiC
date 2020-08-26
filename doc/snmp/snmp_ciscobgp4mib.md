# 1. CiscoBGP4MIB implementation changes

This document captures the current implementation design for CiscoBgp4MIB and propose new design change required to support multi-asic platform.

## 2. Current Design
Snmp docker has two main processes snmpd (master agent), snmp_ax_impl (sub-agent) providing data for some of the MIB tables.  Snmp_ax_impl mostly gets data from redis database. For multi-asic platform, changes are made so that snmp_ax_impl connects to all namespace redis databases and provide cumulative result for SNMP query. Currently the data required for CiscoBgp4MIB is retrieved from Bgpd using VTYSH socket. snmp_ax_impl connects to bgpd vtysh via tcp socket and retreives the BGP neighbour information required for CiscoBgp4MIB.
Sample output:
```
sonic:/# snmpwalk -v2c -c msft 127.0.0.1 iso.3.6.1.4.1.9.9.187
iso.3.6.1.4.1.9.9.187.1.2.5.1.3.1.4.10.0.0.1 = INTEGER: 6
iso.3.6.1.4.1.9.9.187.1.2.5.1.3.2.16.252.0.0.0.0.0.0.0.0.0.0.0.0.0.0.1 = INTEGER: 6
```

## 3. Design considerations for multi-asic platform
### 3.1 Extending current desing
In multi-asic platform, SNMP docker will be running on the host. BGP docker will be running per asic, in separate network namespace. If the currrent design has to be extended, then SNMP docker will have to connect to each BGP via TCP or unix socket. As each BGPd is in a different namespace, BGP docker in each namespace can interact with the snmp_ax_impl in host using docker0 bridge. Docker0 bridge has veth pairs with one interface of the pair on the host and another interface(eth0) inside the namespace. BGPd inside the BGP docker in namespace can open TCP socket to listen on eth0 IP address of the namespace instead of localhost. Snmp_ax_impl can then connect to TCP sockets on each namespace and retrieve data. Another option is to use UNIX socket /var/run/bgpd.vty. For TCP socket, Bgpd in each BGP docker will open socket 240.127.1.x 2065 to talk to VTYSH, currently socket is opened on localhost. If Unix socket is to be used, then /var/run/bgpd.vty of each BGP docker can be used by snmp_ax_impl to get the required data. The issue with this approach is that there will be N number of sockets opened for N asic platform. Also, each BGP docker will have to be updated to use the docker0 IP address network to open the socket.

### 3.2 New design proposal using STATE_DB
To avoid multiple-socket approach, the data required by CiscoBgp4MIB can be populated by a new daemon in STATE_DB. This data can be retrieved by snmp_ax_impl from each namespace for multi-asic platform. Currently, the information required by CiscoBgp4MIB are:
1. Neighbor IP address 
2. Neighbor BGP state 

Proposal is to add a new daemon called 'bgpmond' which will populate STATE_DB with the above infomration. 
Schema:
```
NEIGH_STATE_TABLE {
    "<neigh_ip>" { 
  		"State" : "active/connect/idle/etc"
    }
}
```  

### 3.2.1 Bgmond daemon to update STATE_DB


### 3.2.2 Changes in SNMP

### 4. Future work


