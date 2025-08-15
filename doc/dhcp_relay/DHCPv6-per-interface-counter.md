# DHCPv6 Relay Per-Interface Counter
# High Level Design Document

# Revision
| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:-----------------------------------|
| 1.1 |  11/01/2024 | Yaqiang Zhu, <br> Jing Kan       | Initial version                 |

# About this Manual

This document describes the design details of DHCPv6 Relay per-interface counter feature. It provides capability to count DHCPv6 packets based on packets type and ingress / egress interface.

# Scope

This document describes the high level design details about how **DHCPv6 Relay per-interface counter** works

# Definitions/Abbreviations

### Abbreviations

| Abbreviation             | Description                        |
|--------------------------|----------------------------------|
| DHCP                      | Protocol to automatically assign IP address and other communication information |
| LLA | Link Local Address |
| GUA | Global Unique Address |

### Definitions

| Definition             | Description                        |
|--------------------------|----------------------------------|
| dhcpmon                      | DHCP monitor process |
| dhcp6relay  | DHCPv6 relay process |

# Overview

## Problem Statement

Currently, DHCPv6 counter is embedded in dhcp6relay. It has below shortages:
1. Combining relay functionality and counter in one process increases risk of failure, reduces performance, and makes the system harder to maintain and scale.
2. The counting granularity is Vlan/PortChannel, the data for physical interface is missing.

## Functional Requirements

1. Decouple relay functionality and per-interface counter.
2. Count ingress and egress DHCPv6 packets based on interface and store it in COUNTERS_DB.
3. SONiC CLI to show / clear counter.

# Design

## Design Overview

Notice: Parts of workflow for DHCPv6 per-interface counter are similar to DHCPv4. The design could be referenced to DHCPv4 per-interface counter: [DHCPv4-per-interface-counter](DHCPv4-per-interface-counter.md). But to make current HLD more readable, those parts would be included too, but there would be a mark in sub-title.

To address issue 1, we plan to enhance dhcpmon process to support DHCPv6 per-interface counter. 

To Address issue 2, we propose below design, it could be divided into 4 parts: `Init`, `Per-interface counting`, `Persist` and `Clear Counter`.

### Init

Below picture show initialization for dhcpmon.

<div align="center"> <img src=images/init_multi_thread_dhcpv6.png width=700 /> </div>

There are 2 points need to be highlighted, the rest parts are similar to DHCPv4 counter.

1. Init RX/TX socket and bind network event. We will add 2 new sockets to capture packets
    - Socket with `tcpdump -dd "outbound and ip6 && (udp port 547 || udp port 546)"`. This socket is used to capture egress packets.
    - Socket with `tcpdump -dd "inbound and ip6 && (udp port 547 || udp port 546)"`. This socket is used to capture ingress packets.

2. When initializing DB / cache counter, add new counter for DHCPv6.

### Per-interface counting (Similar with DHCPv4)

<div align="center"> <img src=images/per_intf_counting.png width=620 /> </div>

* From socket, we can figure out which interface does the packet came from.
* Context interface name could be obtained by querying context interface map.
* Then cache counter for corresponding socket interface and context interface would increase **immediately**.

### Persist (Similar with DHCPv4)

<div align="center"> <img src=images/persist_multi_thread.png width=440 /> </div>

DB update timer would be invoked periodically (**every 20s**) in another thread which is different with main thread. It would sync **all data** from cache counter to COUNTERS_DB.

### Clear Counter (Similar with DHCPv4)

<div align="center"> <img src=images/clear_counter_dhcpv6.png width=650 /> </div>

When user invokes SONiC Cli to clear counter, it would directly clear corresponding data in COUNTERS_DB, then a signal to clear cache counter would be sent to dhcpmon process.

After receiving signal to clear cache, dhcpmon process would sync counter data from COUNTERS_DB into process memory. This operation is done in `main thread`.

## Counter Logic

### Overview

The counting workflow is similar with DHCPv4. dhcpmon would use pcapplusplus to parse DHCPv6 header and mainly focus on `Message-type` field in DHCPv6 header. It indicates the type of DHCPv6 packets.

### Packets Type

Except valid types, We add two another types for invalid packets: `Unknown` and `Malformed`

| Type             | Direction                        |
|--------------------------|----------------------------------|
| Solicit                      | Client -> Server |
| Request                      | Client -> Server |
| Confirm                      | Client -> Server |
| Renew                      | Client -> Server |
| Rebind                      | Client -> Server |
| Release                      | Client -> Server |
| Decline                      | Client -> Server |
| Information-Request                      | Client -> Server |
| Advertise                      | Server -> Client |
| Reply                      | Server -> Client |
| Reconfigure                      | Server -> Client |
| Relay-Forward                      | Relay -> Server or Relay -> Relay |
| Relay-Reply                      | Relay -> Client or Relay -> Relay |
| Unknown                      | * |
| Malformed                      | * |

### Dual-ToR Specified

In Dual-ToR there are some behaviors different with single ToR:
1. Packets come from standby interfaces should be dropped.
2. In single ToR, packets are sent to server via Vlan GUA socket. But in Dual ToR, packets are sent to server via Loopback socket.
3. Option 18 would be added in packets sent by Dual ToR or received from server to DualToR, which includes Vlan's LLA.

### Packet Validation
In some scenarios, packets shouldn't be relayed and should be ignored by counter.

#### Common
We have below common validation for all packets, packets match any of below conditions shouldn't be counted.
1. From invalid Physical interface or Context interface.
2. Packets structure invalid (Cannot be parsed / option with incorrect length or only have length), packets would be dropped and `Malformed` counter would be increased.
3. There is no next-header in the ext_header of IPv6 that is UDP.
4. No any valid DHCPv6 type, packets would be dropped and `Unknown` counter would be increased.
5. Invalid DHCPv6 Option ID (> 147), packets would be dropped and `Malformed` counter would be increased. Refer http://www.iana.org/assignments/dhcpv6-parameters/dhcpv6-parameters.xhtml, packets would be dropped and `Malformed` counter would be increased.

#### Client-Sent Packets
For packets sent by client and match any of below conditions, dhcpmon wouldn't count them.
1. From standby interface in DualToR.
2. For RELAY_FORW packets, hop_count in DHCPv6 relay header >= 8 (Hop limit defined in RFC8415).

#### Packets Sent to Server
For packets sent to server and match any of below conditions, dhcpmon wouldn't count them.
1. Src IP is not Vlan GUA in single ToR or not Loopback IPv6 address in DualToR.
2. Link address in DHCPv6 header is not Vlan LLA (Option 9 is non Relay-forw packet) nor :: (Option 9 is Relay-forw packet)

#### Server-Sent Packets
For packets sent by server and match any of below conditions, dhcpmon wouldn't count them.
1. For DualToR
    - Cannot map Option 18 to Vlan or cannot map Link address in relay header to Vlan in non-Option 18 scenario.
    - Dst ip is not Lo ipv6 address.
2. For single ToR
    - Dst ip is not Vlan ipv6 GUA.
3. Common check
    - Not option 9 in option lists.

#### Packets Sent to Client
For packets sent to client and match any of below conditions, dhcpmon wouldn't count them.
1. Src ip is no LLA or GUA of VLAN.

## DB Change

### Counters DB

Following table changes would be added in Counters DB, including **DHCPV6_COUNTER_TABLE** table.

```
{
  "DHCPV6_COUNTER_TABLE": {
    "Vlan1000": {
      "RX": { "Unknown": "0", "Solicit": "1", "Advertise": "0", "Request": "0", "Confirm": "0", "Renew": "0", "Rebind": "0", "Reply": "0", "Release": "0", "Decline": "0", "Reconfigure": "0", "Information-Request": "0", "Relay-Forward": "0", "Relay-Reply": "0", "Malformed": "0" },
      "TX": { "Unknown": "0", "Solicit": "0", "Advertise": "0", "Request": "0", "Confirm": "0", "Renew": "0", "Rebind": "0", "Reply": "0", "Release": "0", "Decline": "0", "Reconfigure": "0", "Information-Request": "0", "Relay-Forward": "0", "Relay-Reply": "0", "Malformed": "0" }
    },
    "Vlan1000:Ethernet4": {
      "RX": { "Unknown": "0", "Solicit": "1", "Advertise": "0", "Request": "0", "Confirm": "0", "Renew": "0", "Rebind": "0", "Reply": "0", "Release": "0", "Decline": "0", "Reconfigure": "0", "Information-Request": "0", "Relay-Forward": "0", "Relay-Reply": "0", "Malformed": "0" },
      "TX": { "Unknown": "0", "Solicit": "0", "Advertise": "0", "Request": "0", "Confirm": "0", "Renew": "0", "Rebind": "0", "Reply": "0", "Release": "0", "Decline": "0", "Reconfigure": "0", "Information-Request": "0", "Relay-Forward": "0", "Relay-Reply": "0", "Malformed": "0" }
    }
  }
}

```

To be noticed that key of uplink interfaces would be added with vlan prefix. It's for multi-vlans scenario to distinguish shared uplink interfaces between different Vlans, below is a sample.

<div align="center"> <img src=images/db_change_dhcpv6.png width=750 /> </div>

# Cli

## Show Cli

**show dhcp_relay ipv6 counters**

This command is used to show dhcp_relay counter.

- Usage
    ```
    show dhcp_relay ipv6 counters [--dir (TX|RX)] [--type <type>] <vlan_interface>

    Options:
        dir: Specify egress or ingress
        type: Specify DHCP packet type
    
    Note: At least one of dir and type must be specified
    ```

- Example
    ```
    show dhcp_relay ipv6 counters Vlan1000 --dir RX
    Packet type Abbr: Un - Unknown, Sol - Solicit, Adv - Advertise,
                      Req - Request, Con - Confirm, Ren - Renew,
                      Reb - Rebind, Rep - Reply, Rel - Release,
                      Dec - Decline, Inf-Req - Information-Request,
                      Rec - Reconfigure, Relay-Forw - Relay-forward,
                      Relay-Rep - Relay-Reply, Mal - Malformed
    +---------------+-----------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+---------+------------+-----------+
    | Vlan1000 (RX) | Intf Type | Un  | Sol | Adv | Req | Con | Ren | Reb | Rep | Rel | Dec | Rec | Mal | Inf-Req | Relay-Forw | Relay-Rep |
    ----------------+-----------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+---------+------------+-----------+
    | Ethernet1     | Downlink  | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    | Ethernet2     | Downlink  | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    | Ethernet46    | Uplink    | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    | Ethernet47    | Uplink    | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    | PortChannel1  | Uplink    | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    | PortChannel2  | Uplink    | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   | 0   | 0   | 0       | 0          | 0         |
    +---------------+-----------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+---------+------------+-----------+

    show dhcp_relay ipv6 counters Vlan1000 --type Solicit
    +-------------------+-----------+----+----+
    |Vlan1000 (Solicit) | Intf Type | TX | RX |
    +-------------------+-----------+----+----+
    |Ethernet1          | Downlink  | 0  | 2  |
    |Ethernet2          | Downlink  | 0  | 0  |
    |Ethernet46         | Uplink    | 2  | 0  |
    |Ethernet47         | Uplink    | 0  | 0  |
    |PortChannel1       | Uplink    | 2  | 0  |
    |PortChannel2       | Uplink    | 0  | 0  |
    +--------------------+-----------+----+----+

    show dhcp_relay ipv6 counters Vlan1000 --type Solicit --dir TX
    +-------------------+-----------+----+
    |Vlan1000 (Solicit) | Intf Type | TX |
    +-------------------+-----------+----+
    |Ethernet1          | Downlink  | 0  |
    |Ethernet2          | Downlink  | 0  |
    |Ethernet46         | Uplink    | 2  |
    |Ethernet47         | Uplink    | 0  |
    |PortChannel1       | Uplink    | 2  |
    |PortChannel2       | Uplink    | 0  |
    +--------------------+-----------+----+
    ```

## Clear Cli

**sonic-clear dhcp_relay ipv6 counters**

This command is used to clear DHCPv6 counters

- Usage
    ```
    sonic-clear dhcp_relay ipv6 counters [--dir (TX|RX)] [--type <type>] [<vlan_interface>]

    Notice: dir / type / vlan_interface are all no-required parameters
    ```

- Example
    ```
    sonic-clear dhcp_relay ipv6 counters Vlan1000 --dir RX
    ```

# Test (Similar with DHCPv4)
## Unit Test
- show dhcp_relay ipv6 counters [--dir (TX|RX)] [--type \<type\>] \<vlan_interface\>
    |Case Description|Expected res|
    |:-|:-|
    |Show without specifying direction and without specifying type|Fail to display|
    |Show without specifying Vlan interface|Fail to display|
    |Show without specifying packet type and with specifying direction and with specifying Vlan interface|Display corresponding direction counter of Vlan interface|
    |Show with specifying interface with type and without specifying direction and with specifying Vlan interface|Display corresponding type of counter of specified interface|
    |Show with specifying type with specifying direction with specifying Vlan interface |Display corresponding direction and type counter of Vlan interface|
- sonic-clear dhcp_relay ipv6 counters [--dir (TX|RX)] [\<interface\>]
    |Case Description|Expected res|
    |:-|:-|
    |clear without specifying interface and without specifying direction|Fail to clear|
    |clear without specifying interface and with specifying direction|Fail to clear|
    |clear with specifying interface without specifying direction|clear counter of specified interface|
    |clear with specifying interface with specifying direction|clear corresponding direction counter of specified interface|

## sonic-mgmt
1. Basic counter functionality test
2. Test to verify counter table initialization and resetting
3. Stress test for counter

