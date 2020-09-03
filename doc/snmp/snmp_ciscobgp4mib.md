# CiscoBgp4MIB implementation changes

This document captures the current implementation design for CiscoBgp4MIB and propose new design change required to support multi-asic platform.

## Current Design
Snmp docker has two main processes snmpd (master agent), snmp_ax_impl (sub-agent) providing data for some of the MIB tables.  Snmp_ax_impl mostly gets data from redis database. For multi-asic platform, changes are made so that snmp_ax_impl connects to all namespace redis databases and provide cumulative result for SNMP query. Currently the data required for CiscoBgp4MIB is retrieved from bgpd deamon. snmp_ax_impl connects to bgpd daemon via tcp socket and retreives the BGP neighbor information required for CiscoBgp4MIB.
Sample output:
```
sonic:/# snmpwalk -v2c -c msft 127.0.0.1 iso.3.6.1.4.1.9.9.187
iso.3.6.1.4.1.9.9.187.1.2.5.1.3.1.4.10.0.0.1 = INTEGER: 6
iso.3.6.1.4.1.9.9.187.1.2.5.1.3.2.16.252.0.0.0.0.0.0.0.0.0.0.0.0.0.0.1 = INTEGER: 6
```

## Design considerations for multi-asic platform
### Extending current design
In multi-asic platform, SNMP docker will be running on the host. BGP docker will be running per asic, in corresponding network namespaces. If the currrent design has to be extended, then SNMP docker will have to connect to each BGP via TCP or unix socket. As each BGPd is in a different namespace, BGP docker in each namespace can interact with the snmp_ax_impl in host using docker0 bridge. Docker0 bridge has veth pairs with one interface of the pair on the host and another interface(eth0) inside the namespace. BGPd inside the BGP docker in namespace can open TCP socket to listen on eth0 IP address of the namespace instead of localhost. Snmp_ax_impl can then connect to TCP sockets on each namespace and retrieve data. Another option is to use UNIX socket /var/run/bgpd.vty. For TCP socket, Bgpd in each BGP docker will open socket 240.127.1.x 2065 to talk to VTYSH, currently socket is opened on localhost. If Unix socket is to be used, then /var/run/bgpd.vty of each BGP docker can be used by snmp_ax_impl to get the required data. The issue with this approach is that there will be N number of sockets opened for N asic platform. Also, each BGP docker will have to be updated to use the docker0 IP address network to open the socket.

### New design proposal using STATE_DB
To avoid multiple-socket approach, the data required by CiscoBgp4MIB can be populated in STATE_DB by a new daemon in BGP docker. This data can be retrieved by snmp_ax_impl from each namespace for multi-asic platform. Current implementaion of CiscoBgp4MIB in SONiC retrives the below information from the device:
1. Neighbor IP address 
2. Neighbor BGP state
Currently snmp_ax_impl parses the data from Bgpd vtysh to get 'neighbor ip' and 'state'.

Proposal is to add a new daemon called 'bgpmon' which will populate STATE_DB with the above infomration. 
Schema:
```
NEIGH_STATE_TABLE {
    "<neigh_ip>" { 
        "State" : "Idle/Idle (Admin)/Connect/Active/OpenSent/OpenConfirm/Established/Clearing"
    }
}
```
Currently, NEIGH_STATE_TABLE will be used by SNMP. This table can be used by telemetry or any other docker in future.

### Bgpmon daemon to update STATE_DB
This is the new daemon that runs inside of each BGP docker.  It will periodically (every 15 seconds) check if there are any BGP activities by examining the modified timestamp of "/var/log/frr/frr.log" file against the cached timestamp value from last detected activities. If BGP activity detected, this new daemon will then pull the bgp neighbor information by calling "show bgp summary json" and use the output to update the State DB accordingly.  In order to prevent unnecessary update to the State DB, a copy of each neighbor state is also cached and used to check for delta changes from each newly pulled neighbor state.  Only when there is a change, then that particular entry in the state DB is updated.  In a steady state situation, there is rarely a need to pulled the BGP states nor update made to the state DB.  If the neighbor is deleted from configuration, the corresponding state DB entry will also be cleaned up.
In the future, if there are features that require additional neighbor information other then the BGP neighbor IP address and its state, we can raise a new PR to add those new required attributes to the state DB table.

### Changes in SNMP
snmp_ax_impl will be updated to talk to STATE_DB and retrieve NEIGH_STATE_TABLE. This change will affect both single and multi asic platforms. In case of multi-asic platforms, snmp_ax_impl will retrive data from STATE_DB of all namespaces.


### Future work
SONiC uses snmpd implementation for Bgp4MIB(1.3.6.1.2.1.15). This implemenation uses bgpd as a subagent for this MIB tree. This implementation cannot be extended for multi-asic platform where multiple bgpd exists. Multiple entries exist within Bgp4MIB and is currently not supported for multi-asic platform. Bgp4MIB In order to support this MIB, bgpmon can be extended in future, to add the required data in STATE_DB which can be retrieved by snmp_ax_impl. 
