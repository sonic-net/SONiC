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

### High level test details
1. Send packets to a destination prefix which is pointing to multiple ecmp nexthops. For the T0 topology test we will send it to a dest prefix which is pointing to the T1s.
3. Vary some tuple of the packet so that the packets hash to different nexthops. The total packets sent in a test is calcualted as follows: 1000 packets sent per ECMP next hop. This translates to 4000 packets in a T0 topology with 4 T1s(ECMP nexthops). All 4000 packets will have varied tuples to get a good distribution of packets to ports.
4. Identify set of ports on which the packet would have ecmp'd
5. Check which port received the packet and record received packet count per port
6. Calculate the expected number of packets per port
7. Validate if received packet count per port is within a 25% deviation of expected number of packets on the port

### Different outer encapsulation formats tested with various inner packets
1. The test will send inner packets and validate that varying any single 5-tuple of the inner packet results in hash variation, it will be sent with various outer encapsulation formats listed below
2. IPv4 Vxlan
3. IPv6 Vxlan
4. IPv4 NVGRE
5. IPv6 NVGRE

### Inner packet tuples varied for hash valdiation:
Validate hashing with different inner packet tuples:
1. Src IP
2. Dst IP
3. Src Port
4. Dst Port
5. IP Protocol

### Direction agnostic hashing
As an optional mode, the test will also validate direction agnostic packet hashing: 2 directions of a flow land on the same ecmp nexthop. 
This will be tested by sending one direction of the packet, recording the received port, sending the reverse direction of the packet and validate that it is received on the same port.
