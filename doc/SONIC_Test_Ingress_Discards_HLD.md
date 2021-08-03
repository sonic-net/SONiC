- [Overview](#overview)
    - [Scope](#scope)
    - [Supported topologies](#supported-topologies)
    - [Discard groups covered by test case](#discard-groups-covered-by-test-cases)
    - [Related DUT CLI commands](#related-dut-cli-commands)
    - [SAI attributes](#sai-attributes)
- [General test flow](#general-test-flow)
- [Run test](#run-test)
- [Test cases](#test-cases)
    - [Test case #1](#test-case-1)
    - [Test case #2](#test-case-2)
    - [Test case #3](#test-case-3)
    - [Test case #4](#test-case-4)
    - [Test case #5](#test-case-5)
    - [Test case #6](#test-case-6)
    - [Test case #7](#test-case-7)
    - [Test case #8](#test-case-8)
    - [Test case #9](#test-case-9)
    - [Test case #10](#test-case-10)
    - [Test case #11](#test-case-11)
    - [Test case #12](#test-case-12)
    - [Test case #13](#test-case-13)
    - [Test case #14](#test-case-14)
    - [Test case #15](#test-case-15)
    - [Test case #16](#test-case-16)
    - [Test case #17](#test-case-17)
    - [Test case #18](#test-case-18)
    - [Test case #19](#test-case-19)
    - [Test case #20](#test-case-20)
    - [Test case #21](#test-case-21)
    - [Test case #22](#test-case-22)

#### Overview
The purpose is to test drop counters triggers on receiving specific packets by DUT.

The test assumes control plane traffic is disabled before test run by disabling VMs.

Destination IP address of the injected packet must be routable to ensure packet should not be routed via specific interface but dropped.

##### For Ethernet drop reasons:
```portstat -j``` - check ```RX_DRP```

##### For IP drop reasons:
```intfstat -j``` - check ```RX_ERR```

##### For ACL drop reasons:
```aclshow -a``` - check ```PACKETS COUNT```

#### Scope
The purpose of test cases is to verify that:
- appropriate packet drop counters trigger on SONIC system on expected value
- making sure that specific traffic drops correctly, according to sent packet and configured packet discards

#### Supported topologies:
```
t0
t1
t1-lag
ptf32
```

#### Discard groups covered by test cases
Please refer to the test case for detailed description.

| Test case ID| Drop reason | Group type|
|-------------|-------------|-----------|
| 1 | SMAC and DMAC are equal |Ethernet |
| 2 | Not allowed VLAN TAG| Ethernet|
| 3 | Multicast SMAC | Ethernet|
| 4 | Reserved DMAC | Ethernet|
| 5 | Loop-back filter | IP|
| 6 | Packet exceed router interface MTU| IP|
| 7 | Time To Live (TTL) Expired | IP|
| 8 | Discard at router interface for non-routable packets | IP|
| 9 | Absent IP header | IP|
| 10 | Broken IP header - header checksum or IPver or IPv4 IHL too short | IP|
| 11 | Unicast IP with multicast DMAC or broadcast DST MAC | IP|
| 12 | DST IP is loopback address | IP|
| 13 | SRC IP is loopback address | IP|
| 14 | SRC IP is multicast address | IP|
| 15 | SRC IP address is in class E | IP|
| 16 | SRC IP address is not specified | IP|
| 17 | DST IP address is not specified | IP|
| 18 | SRC IP address is link-local | IP|
| 19 | DST IP address is link-local | IP|
| 20 | ACL SRC IP DROP| IP|
| 21 | No drops when ERIF interface disabled | IP|
| 22 | Ingress Priority Group drop | PG|

#### Related DUT CLI commands
| **Command**                                                      | **Comment** |
|------------------------------------------------------------------|-------------|
| counterpoll port enable               | Enable port counters                   |
| counterpoll rif enable                | Enable RIF counters                    |
| portstat -j                           | Check ```RX_DRP```                     |
| intfstat -j                           | Check ```RX_ERR```                     |
| aclshow -a                            | Check ```PACKETS COUNT```              |
| sonic-clear counters                  | Clear counters                         |
| sonic-clear rifcounters               | Clear RIF counters                     |
| show priority-group drop counters     | Show PG dropped pakets                 |

As different vendors can have diferent drop counters calculation, for example L2 and L3 drop counters can be combined and L2 drop counter will be increased for all ingress discards.
So for valid drop counters verification there is a need to distinguish wheter drop counters are combined or not for current vendor.
This can be done by checking platform name of the DUT.

##### Work need to be done based on this case
Create yml file which will contain list of regular expressions which match platform name of specific vendor who has combined drop counters calculation. Internally test framework will use this regular expressions to match current DUT platform name to determine whether drop counters are combined or not.

##### Example of file content:
tests/drop_counters/combined_drop_counters.yml
```
- "[REGEXP FOR VENDOR X]"
- "[REGEXP FOR VENDOR Y]"
```

#### SAI attributes
```SAI_PORT_STAT_IF_IN_DISCARDS``` - number of L2 discards

```SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS``` - number of L3 discards

#### General test flow
##### Each test case will use the following port types:
- VLAN (T0)
- LAG (T0, T1-LAG)
- Router (T1, T1-LAG, PTF32)

##### Drop counters which are going to be checked
It depends on test objective.

Will be verified one of the following drop counters:
- Drop counter for L2 discards
- Drop counter for L3 discards
- Drop counter for ACL discards

##### Sent packet number:
N=5

##### step #1 - Disable VMs
Before test suite run - disable control plane traffic generation. Use "testbed-cli.sh" script with "disconnect-vms" option.

##### step #2 - Execute test scenario for all available port types depends on run topology (VLAN, LAG, Router)

- Select PTF ports to send and sniff traffic
- Clear counters on DUT. Use CLI command "sonic-clear counters"
- Inject N packet via PTF port selected for TX
- Check specific drop counter incremented on N (depends on test case)
	- If counter was not incremented on N, test fails with expected message
- Check other counters were not incremented on N based on sent packet type, sent port and expected drop reason (depends on test case)
	- If counter was incremented on N, test fails with expected message
- Check the packet was dropped by sniffing packet absence on PTF port selected for RX

##### step #3 - Enable VMs
Enable previously disabled VMs using "testbed-cli.sh" script with "connect-vms" option.

#### Run test
```
py.test --inventory ../ansible/inventory --host-pattern [DEVICE] --module-path ../ansible/library/ --testbed [DEVICE-TOPO] --testbed_file ../ansible/testbed.csv --junit-xml=./target/test-reports/ --show-capture=no --log-cli-level debug -ra -vvvvv ingress_discard/test_ingress_discard.py
```

#### Test cases
Each test case will be additionally validated by the loganalyzer utility.

Each test case will run specific traffic to trigger specific discard reasone.

Pytest fixture - "ptfadapter" is used to construct and send packets.

After packet is sent using source port index, test framework waits during 5 seconds for specific packet did not appear, due to ingress packet drop, on one of the destination port indices.

#### Test case #1
##### Test objective

Verify packet drops when SMAC and DMAC are equal

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [DUT_MAC_ADDR]
  src = [DUT_MAC_ADDR]
  type = 0x800
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet specifying identical src and dst MAC.
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L2 drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented

#### Test case #2
##### Test objective

Verify VLAN tagged packet drops when packet VLAN ID does not match ingress port VLAN ID

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = [auto]
  type = 0x8100
  vid = 2
###[ IP ]###
    version = 4  
    ttl = [auto]
    proto = tcp  
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet specifying VID different then port VLAN
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L2 drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented

#### Test case #3
##### Test objective

Verify packet with multicast SMAC drops

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = 01:00:5e:00:01:02
  type = 0x800
###[ IP ]###
    version = 4  
    ttl = [auto]
    proto = tcp  
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet specifying multicast SMAC.
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L2 drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented

#### Test case #4
##### Test objective

Verify packet with reserved DMAC drops

Packet1 to trigger drop (use reserved for future standardization MAC address)
```
###[ Ethernet ]###
  dst = 01:80:C2:00:00:05
  src = [auto]
  type = 0x800
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```
Packet2 to trigger drop (use provider Bridge group address)
```
###[ Ethernet ]###
  dst = 01:80:C2:00:00:08
  src = [auto]
  type = 0x800
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet1 specifying reserved DMAC
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L2 drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented
---
- PTF host will send IP packet2 specifying reserved DMAC
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L2 drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented

#### Test case #5
##### Test objective

Verify packet drops by loop-back filter. Loop-back filter means that route to the host with DST IP of received packet exists on received interface

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = [auto]
  type = 0x800
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [known_bgp_neighboar_ip]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet specifying DST IP of VM host. Port to send is port which IP interface is in VM subnet.
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #6
##### Test objective

Verify packet which exceed router interface MTU (for IP packets) drops

Note: make sure that configured MTU on testbed server and fanout are greater then DUT port MTU

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = [auto]
  type = 0x800
...
###[ TCP ]###  
    sport = [auto]
    dport = [auto]
    data = [max_mtu + 1]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet which exceed router interface MTU
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #7
##### Test objective

Verify packet with TTL expired (ttl <= 0) drops

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = [auto]
  type = 0x800
...
###[ IP ]###
    version = 4
    ttl = 0
    proto = tcp
    src = [auto]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IP packet with TTL = 0
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #8
##### Test objective

Verify non-routable packets discarded at router interface
Packet list:
- IGMP v1 v2 v3 membership query
- IGMP v1 membership report
- IGMP v2 membership report
- IGMP v2 leave group
- IGMP v3 membership report

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send IGMP v1 v2 v3 membership query
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send IGMP v1 membership report
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send IGMP v2 membership report
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send IGMP v2 leave group
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send IGMP v3 membership report
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #9
##### Test objective

Verify packet with no ip header available - drops

Packet to trigger drop
```
###[ Ethernet ]###
  dst = [auto]
  src = [auto]
  type = 0x800
###[ TCP ]###  
    sport = [auto]
    dport = [auto]
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet without IP header
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #10
##### Test objective

Verify DUT drop packet with broken ip header due to header checksum or IPver or IPv4 IHL too short

Packet1 to trigger drop (Incorrect checksum)
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [auto]
    checksum = [generated_value]
...
```

Packet2 to trigger drop (Incorrect IP version)
```
...
###[ IP ]###
    version = 1
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [auto]
...
```

Packet3 to trigger drop (Incorrect IPv4 IHL)
```
...
###[ IP ]###
    version = 4
    ihl = 1
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet3
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #11
##### Test objective

Verify DUT drops unicast IP packet sent via:
- multicast DST MAC
- broadcast DST MAC

Packet1 to trigger drop
```
###[ Ethernet ]###
  dst = 01:00:5e:00:01:02
  src = [auto]
  type = 0x800
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```

Packet2 to trigger drop
```
###[ Ethernet ]###
  dst = ff:ff:ff:ff:ff:ff
  src = [auto]
  type = 0x800
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = 10.0.0.2
    dst = [get_from_route_info]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #12
##### Test objective

Verify DUT drops packet where DST IP is loopback address

For ipv4: dip==127.0.0.0/8

For ipv6: dip==::1/128 OR dip==0:0:0:0:0:ffff:7f00:0/104

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]]
    dst = [127.0.0.1]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 6
    ttl = [auto]
    proto = tcp
    src = [auto]]
    dst = [::1/128]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #13
##### Test objective

Verify DUT drops packet where SRC IP is loopback address

For ipv4: dip==127.0.0.0/8

For ipv6: dip==::1/128 OR dip==0:0:0:0:0:ffff:7f00:0/104

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [127.0.0.1]
    dst = [auto]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 6
    ttl = [auto]
    proto = tcp
    src = [::1/128]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
 
#### Test case #14
##### Test objective

Verify DUT drops packet where SRC IP is multicast address

For ipv4: sip = 224.0.0.0/4

For ipv6: sip == FF00::/8

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [224.0.0.5]
    dst = [auto]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 6
    ttl = [auto]
    proto = tcp
    src = [ff02::5]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #15
##### Test objective

Verify DUT drops packet where SRC IP address is in class E

SIP == 240.0.0.0/4

SIP != 255.255.255.255

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [240.0.0.1]
    dst = [auto]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [255.255.255.254]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #16
##### Test objective

Verify DUT drops packet where SRC IP address is not specified

IPv4 sip == 0.0.0.0/32

Note: for IPv6 (sip == ::0)

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [0.0.0.0]
    dst = [auto]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 6
    ttl = [auto]
    proto = tcp
    src = [::0]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #17
##### Test objective

Verify DUT drops packet where DST IP address is not specified

IPv4 sip == 0.0.0.0/32

Note: for IPv6 (sip == ::0)

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [0.0.0.0]
...
```

Packet2 to trigger drop
```
...
###[ IP ]###
    version = 6
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [::0]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
---
- PTF host will send packet2
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #18
##### Test objective

Verify DUT drops packet where SRC IP is link-local address

For ipv4: sip==169.254.0.0/16

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [169.254.10.125]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #19
##### Test objective

Verify DUT drops packet where DST IP is link-local address

For ipv4: dip==169.254.0.0/16

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]]
    dst = [169.254.10.125]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get L3 drop counter
- Verify drop counter incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented

#### Test case #20
##### Test objective

Verify DUT drops packet when configured ACL DROP for SRC IP 20.0.0.0/24

Packet1 to trigger drop
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [20.0.0.10]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- PTF host will send packet1
- When packet reaches SONIC DUT, it should be dropped according to the test objective
- Get ACL drop counter
- Verify drop counter incremented
- Get L3 drop counter
- Verify L3 drop counter is not incremented

#### Test case #21
##### Test objective

Verify egress RIF drop counter is not incremented while sending packets that are destined for a neighboring device but the egress link is down

Packet1 to send
```
...
###[ IP ]###
    version = 4
    ttl = [auto]
    proto = tcp
    src = [auto]
    dst = [auto]
...
```

##### Get interfaces which are members of LAG, RIF and VLAN. Repeat defined test steps for each of those interfaces.

##### Test steps
- Disable egress interface on DUT which is linked with neighbouring device
- Check ARP entry is cleared
- PTF host will send packet1
- Verify that no packets appeared/captured on disabled link
- Get L3 drop counter
- Verify drop counter is not incremented
- Get L2 drop counter
- Verify L2 drop counter is not incremented
- Enable back egress interface on DUT which is linked with neighbouring device

#### Test case #22
##### Test objective
Verify ingress Priority Group drop packets counter

Packet to send
```
...
###[ IP ]###
  version= 4
  tos= [(lossless_priority << 2) | ECN]
  src= [neighbor1 ip src]
  dst= [neighbor2 ip dst]
...
```

##### Test description
It is required to have RPC image for this test.
Get interfaces which are members of LAG and RIF. Choose 2 random interfaces (neighbors are linked to them are host A and B).
To make packet dropped on ingress side, we need to:
-	create congestion on egress side by closing port by setting the shaper, which can be done in RPC image only.
-	send enough packet to occupy the shared buffer pool
-	send enough packet to occupy the headroom
-	send extra packet to trigger packet drop


##### Test steps
- limit maximum bandwith rate on the destination port with using SAI port attribute SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID
- choose losless Priority Queue an get appropriate DSCP value
- consruct IP packet
- start data traffic from RX to TX ports
- verify there are drops on apropriate PG on apropriate port
- cleanup (resore maximin bandwith)
