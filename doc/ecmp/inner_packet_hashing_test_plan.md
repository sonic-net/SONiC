# Test Plan for inner packet hashing in ECMP
###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 03/12/2021  |    Anish Narsian   | Initial version                   |

## Overview
The purpose of this test plan is to describe inner packet hashing tests for ECMP nexthops. The test methodology will be similar to the current hash_test in SONiC. The test sends vxlan encapsulated packets and validates hashing is performed per the inner packet's 5 tuple(src ip, dst ip, src port, dst port, ip proto).

## Test information

### Test configuration
Currently this test expects that the inner packet hashing is pre-configured on the DUT. In the future, once dynamic Policy Based Hashing feature is implemented, dynamic configuration can be done on the DUT and packet hashing verified per the config.

Beyond hash configuration, base DUT route table configurations are sufficient to perform the test.

### Supported topology
The test will be supported on the T0 toplogy, it may be enhanced in the future for other topologies.

### High level test methodology
1. Send a lot of packets(1000 packets per nh, so a standard t0 topology would involve sending 4000 packets) to a dest prefix which has ecmp nhs.
2. Vary some tuple of the packet so that the packets hash to different nexthops
3. Identify set of ports on which the packet would have ecmp'd
4. Check which port received the packet and record received packet count per port
5. Calculate the expected number of packets per port
6. Validate if received packet count per port is within a 25% margin of calculated number of packets on the port

### Vxlan inner packet hashing
The test will send vxlan inner packets and validate that varying any single 5-tuple of the inner packet results in hash variation.
Vxlan packets will be sent with both outer IPv4 and outer IPv6.

### Inner packet types for tuple variation
Validate hashing with different inner packet types:
1. IPv4 TCP
2. IPv4 UDP
3. IPv4 ICMP

### Direction agnostic hashing
As an optional mode, the test will also validate direction agnostic packet hashing: 2 directions of a flow land on the same ecmp nexthop. 
This will be tested by sending one direction of the packet, recording the received port, sending the reverse direction of the packet and validate that it is received on the same port.
