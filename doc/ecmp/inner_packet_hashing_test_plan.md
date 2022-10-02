# Test Plan for inner packet hashing in ECMP
### Rev 1.1

# Table of Contents
  
  * [Revision](#revision)
  * [Overview](#overview)
  * [Test information](#test-information)
    * [Supported topology](#supported-topology)
    * [Test configuration](#test-configuration)
      * [PBH cli coverage](#pbh-cli-coverage)
      * [PBH table configuration](#pbh-table-configuration)
      * [PBH hash field configuration](#pbh-hash-field-configuration)
      * [PBH hash configuration](#pbh-hash-configuration)
      * [PBH rule configuration](#pbh-rule-configuration)
    * [High level test details](#high-level-test-details)
    * [Different outer encapsulation formats tested with various inner packets](#different-outer-encapsulation-formats-tested-with-various-inner-packets)
    * [Different inner encapsulated formats tested with various outer packets](#different-inner-encapsulated-formats-tested-with-various-outer-packets)
    * [Inner packet tuples varied for hash validation](#inner-packet-tuples-varied-for-hash-validation)
      * [Validate hashing with different inner packet tuples](#validate-hashing-with-different-inner-packet-tuples)
      * [Ensure that outer packets are not contributing to the hashing](#ensure-that-outer-packets-are-not-contributing-to-the-hashing)
    * [Symmetric hashing](#symmetric-hashing)
    * [Warm boot testing](#warm-boot-testing)

 
###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 03/12/2021  |    Anish Narsian   | Initial version                   |
| 1.0 | 04/01/2021  |    Anish Narsian   | Incorporate review comments       |
| 1.1 | 07/28/2021  |   Anton Hryshchuk  | Test configs by dynamic PBH       |

## Overview
The purpose of this test plan is to describe inner packet hashing tests for ECMP nexthops. The test methodology will be similar to the current hash_test in SONiC. The test sends encapsulated packets and validates hashing is performed per the inner packet's 5 tuple(src ip, dst ip, src port, dst port, ip proto).

## Test information

### Supported topology
The test will be supported on the T0 toplogy(add and verify others), it may be enhanced in the future for other topologies.

### Test configuration
The inner hashing configuration to the DUT done by dynamic Policy Base Hashing feature.

Beyond hash configuration, base DUT route table configurations are sufficient to perform the test.

#### PBH cli coverage
1. config pbh table add
2. config pbh table delete
3. config pbh hash-field add
4. config pbh hash-field delete
5. config pbh hash add
6. config pbh hash delete
7. config pbh rule add
8. config pbh rule delete

#### PBH table configuration
Create PBH table with vlan ptf ports as members. It will be a list of all ports in t0 topology, which in Up state and not in LAG. 

#### PBH hash field configuration
Hash native field:
```
NAME               FIELD              MASK             SEQUENCE    SYMMETRIC
-----------------  -----------------  ---------------  ----------  -----------
inner_ip_proto     INNER_IP_PROTOCOL  N/A              1           No
inner_l4_dst_port  INNER_L4_DST_PORT  N/A              2           Yes
inner_l4_src_port  INNER_L4_SRC_PORT  N/A              2           Yes
inner_dst_ipv4     INNER_DST_IPV4     255.255.255.255  3           Yes
inner_src_ipv4     INNER_SRC_IPV4     255.255.255.255  3           Yes
inner_dst_ipv6     INNER_DST_IPV6     ::ffff:ffff      4           Yes
inner_src_ipv6     INNER_SRC_IPV6     ::ffff:ffff      4           Yes
```

#### PBH hash configuration
Define hash with field list:
1. inner_ip_proto
2. inner_l4_dst_port
3. inner_l4_src_port
4. inner_dst_ipv4
5. inner_src_ipv4
6. inner_dst_ipv6
7. inner_src_ipv6

#### PBH rule configuration
Created rules:
```
TABLE      RULE             PRIORITY    MATCH                      HASH        ACTION         COUNTER
---------  ---------------  ----------  -------------------------  ----------  -------------  ---------
pbh_table  nvgre_ipv4_ipv4  2           ether_type:        0x0800  inner_hash  SET_ECMP_HASH  ENABLED
                                        ip_protocol:       0x2f
                                        inner_ether_type:  0x0800
pbh_table  nvgre_ipv4_ipv6  2           ether_type:        0x0800  inner_hash  SET_ECMP_HASH  ENABLED
                                        ip_protocol:       0x2f
                                        inner_ether_type:  0x86dd
pbh_table  nvgre_ipv6_ipv4  2           ether_type:        0x86dd  inner_hash  SET_ECMP_HASH  ENABLED
                                        ipv6_next_header:  0x2f
                                        inner_ether_type:  0x0800
pbh_table  nvgre_ipv6_ipv6  2           ether_type:        0x86dd  inner_hash  SET_ECMP_HASH  ENABLED
                                        ipv6_next_header:  0x2f
                                        inner_ether_type:  0x86dd
pbh_table  vxlan_ipv4_ipv4  1           ether_type:        0x0800  inner_hash  SET_ECMP_HASH  ENABLED
                                        ip_protocol:       0x11
                                        l4_dst_port:       0x3412
                                        inner_ether_type:  0x0800
pbh_table  vxlan_ipv4_ipv6  1           ether_type:        0x0800  inner_hash  SET_ECMP_HASH  ENABLED
                                        ip_protocol:       0x11
                                        l4_dst_port:       0x3412
                                        inner_ether_type:  0x86dd
pbh_table  vxlan_ipv6_ipv4  1           ether_type:        0x86dd  inner_hash  SET_ECMP_HASH  ENABLED
                                        ipv6_next_header:  0x11
                                        l4_dst_port:       0x3412
                                        inner_ether_type:  0x0800
pbh_table  vxlan_ipv6_ipv6  1           ether_type:        0x86dd  inner_hash  SET_ECMP_HASH  ENABLED
                                        ipv6_next_header:  0x11
                                        l4_dst_port:       0x3412
                                        inner_ether_type:  0x86dd
```

### High level test details
1. Send packets to a destination prefix which is pointing to multiple ecmp nexthops. For the T0 topology test we will send it to a dest prefix which is pointing to the T1s.
3. Vary some tuple of the packet so that the packets hash to different nexthops. The total packets sent in a test is calcualted as follows: 1000 packets sent per ECMP next hop. This translates to 4000 packets in a T0 topology with 4 T1s(ECMP nexthops). All 4000 packets will have varied tuples to get a good distribution of packets to ports.
4. Identify set of ports on which the packet would have ecmp'd
5. Check which port received the packet and record received packet count per port
6. Calculate the expected number of packets per port
7. Validate if received packet count per port is within a 25% deviation of expected number of packets on the port

### Different outer encapsulation formats tested with various inner packets
The test will send inner packets and validate that varying any single 5-tuple of the inner packet results in hash variation, it will be sent with various outer encapsulation formats listed below
1. IPv4 Vxlan
2. IPv6 Vxlan
3. IPv4 NVGRE
4. IPv6 NVGRE

### Different inner encapsulated formats tested with various outer packets
1. IPv4
2. IPv6


### Inner packet tuples varied for hash validation
#### Validate hashing with different inner packet tuples
1. Src IPv4
2. Dst IPv4
3. Src IPv6
4. Dst IPv6
5. Src Port
6. Dst Port
7. IP Protocol

#### Ensure that outer packets are not contributing to the hashing
Send the inner packets with identical inner tuples, then vary each of the outer packet tuples as 1000s of packets are sent. All packets should be received on a single next-hop ONLY, because of a lack in variation of the inner packet tuples. This way we ensure that only the inner packet tuples are contributing to the hash and that the outer packet tuples are not.

### Symmetric hashing
As an optional mode, the test will also validate symmetric packet hashing: 2 directions of a flow land on the same ecmp nexthop. 
This will be tested by sending one direction of the packet, recording the received port, sending the reverse direction of the packet and validate that it is received on the very same port.

### Warm boot testing
Run inner packet hashing traffic while warm boot is ongoing and ensure that it works just as in the standard non-warm boot case.
Different packets tested with various inner encapsulated and outer encapsulation formats
1. IPv4 IPv4 Vxlan
2. IPv4 IPv6 Vxlan
3. IPv6 IPv4 Vxlan
4. IPv6 IPv6 Vxlan
5. IPv4 IPv4 NVGRE
6. IPv4 IPv6 NVGRE
7. IPv6 IPv4 NVGRE
8. IPv6 IPv6 NVGRE
