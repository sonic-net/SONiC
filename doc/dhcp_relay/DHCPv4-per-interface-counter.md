# DHCPv4 Relay Per-Interface Counter
# High Level Design Document

# Revision

| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:-----------------------------------|
| 1.0 |  05/29/2023 | Jie Cai       | Initial version                     |
| 1.1 |  11/01/2024 | Yaqiang Zhu, <br> Jing Kan       | Revise                 |

# About this Manual

This document describes the design details of DHCPv4 Relay per-interface counter feature. It provides capability to count DHCPv4 packets based on packets type and ingress / egress interface.

# Scope

This document describes the high level design details about how **DHCPv4 Relay per-interface counter** works.

# Definitions/Abbreviations

###### Table 1: Abbreviations

| Abbreviation             | Full form                        |
|--------------------------|----------------------------------|
| DHCP                      | Dynamic Host Configuration Protocol      |

###### Table 2: Definitions
| Definitions             | Description                        |
|--------------------------|----------------------------------|
| dhcpmon | DHCPv4 monitor process |
| Context interface | downlink, uplink intfs specified in dhcpmon parameters: /usr/sbin/dhcpmon -id **Vlan1000** -iu **PortChannel101** -iu **PortChannel102** -iu **PortChannel103** -iu **PortChannel104** -im **eth0** |

# Overview

## Problem Statement

Currently, DHCPv4 counter in dhcpmon mainly focus on Vlan / PortChannel interface packet data and it store count data in process memory. Also dhcpmon only reports issue in syslog for DHCPv4 packets relayed disparity. It has below disadvantages:
1. The counting granularity is Vlan/PortChannel, the data for physical interface is missing.
2. There is no API for User to actively query packets count. When issue like DHCP client cannot get ip happens, we need to do some packets capture and analyze to fingure out whether the packets received in switch and whether the packets have been relayed.

## Functional Requirements

1. Count ingress and egress DHCPv4 packets based on interface and store it in STATE_DB.
2. SONiC CLI to show / clear counter.

# Design

## Design Overview

To address above 2 issues, we propose below design, it could be divided into 4 parts: `Init`, `Per-interface counting`, `Persist` and `clear counter`.

### Init

<div align="center"> <img src=images/init_multi_thread.png width=700 /> </div>

1. There are **2 sockets for all interfaces** to capture DHCPv4 packets. We bind callback to the network events to process packets.
2. Read from `PORTCHANNEL_MEMBER` and `VLAN_MEMBER` table from CONFIG_DB to construct mapping between physical interface and PortChannel/Vlan. It's used to query context interface by physical interface.
3. There are 2 kinds of counters, one is persisted in STATE_DB, another is stored in process memory, they are initialized when process startup.
4. A signal callback would be added to listen for counter cleaning signal to clear counter in process memory.
5. Initialize a timer to periodically sync counter data from cache counter to DB counter in another thread.

With above structure, packets processing and all write actions to cache counter in process memory would be done in **main thread**, and all write actions to STATE_DB would be done in **DB update thread**.

### Per-interface counting (Main thread)

<div align="center"> <img src=images/per_intf_counting.png width=620 /> </div>

* From socket, we can fingure out which physical interface does the packet came from.
* Context interface name could be obtained by querying context interface counter.
* Then cache counter for corresponding physical interface and context interface would increase **immediately**.

### Persist (DB update thread)

<div align="center"> <img src=images/persist_multi_thread.png width=440 /> </div>

DB update timer would be invoked periodically (**every 20s**) in another thread which is different with main thread. It would sync **all data** from cache couonter to STATE_DB.

### Clear Counter

<div align="center"> <img src=images/clear_counter.png width=480 /> </div>

When user invokes SONiC Cli to clear counter, it would directly clear corresponding data in STATE_DB, then write a temp file which contains counters of specified direction / packet type / interface need to be cleared, then a signal to clear cache counter would be sent to dhcpmon process.

After receiving signal to clear cache, dhcpmon process would clear counter in process memory in `main thread`.

## Counter Logic

### Overview

dhcpmon would mainly focus on comparing below 3 fields in packet when counting packets. Point 1 and point 2 is used for counting context interface, **we only count client-sent packets which come from downlink Vlan and server-sent packets which come from uplink interfaces**. And point 3 is used to get packet type.
1. `Option 53` in **DHCPv4 header**
2. `Destination ip Address` in **IP header**
3. `Gateway IP Address` in **DHCPv4 header**

The point 1 is used to get packet type. Point 2 and point 3 are used for counting interface, **we only count when below 2 conditions are all matched**
1. client-sent packets which come from downlink Vlan or server-sent packets which come from uplink interfaces.
2. If packets are relayed to DHCP server or received from DHCP server, the gateway ip configred in DHCP header should match gateway in device.

Below pictures are samples for expected counter increasing for both directions.

- For traffic flow from DHCP client to DHCP server, the egress packets count in context interface should be aligned with dhcp server number configured.
- For traffic flow from DHCP server to DHCP client, the egress packets count should be equal to ingress packet counts.

<div align="center"> <img src=images/counter_sample.png width=630 /> </div>

Counter for interface should be increased in below scenarios, and they can be corresponded to the above picture.

|              | DHCP client -> DHCP server | DHCP server -> DHCP client |
|--------------------------|----------------------------------|--|
| RX packet | **A**: If interface is downlink and \[destination ip in ip header is broadcast ip or gateway ip\] | **B**: If dst ip in ip header equals to gateway and ingress interface is uplink |
| TX packet | **C**: If gateway ip in dhcp header equals to gateway ip and interface is uplink | **D**: If interface is downlink|

### Dual-ToR Specified

In Dual-ToR there are some behaviors different with single ToR:
1. We wouldn't count packets come from standby interfaces (Refer to `HW_MUX_CABLE_TABLE` in STATE_DB).
2. In above counting logic, we would compare `gateway` in DHCP packets. In single ToR, the gateway is Vlan ip, but in Dual-ToR, it's device's Loopback ip.

## Counter Reset

* Container restart
  * One dhcpmon process would only listen on one downlink Vlan interface, hence dhcpmon process restart will initialize (counter set to zero) for interface in below list:
    * Downlink / Uplink context interfaces given by startup parameter.
    * Related Vlan member interfaces from CONFIG_DB table `VLAN_MEMBER|Vlanxxx`.
    * Related PortChannel member interfaces from CONFIG_DB table `PORTCHANNEL_MEMBER|PortChannelxxx`.
* Vlan add/del
  * For now, after vlan adding or deleting, it requires dhcp_relay container be restarted to take effect. Vlan del Cli would automatically restart dhcp_relay container, other scenarios need manually restart. Then it could be referred to above `container restart` part
* Vlan / PortChannel member change
  * Member add: It's expected to add entry and set counter to zero for member interface.
  * Member del: It's expected to delete related counter entry.
  * **Note: This requires db change subscription support. In early stage, we will mainly focus on key functionality. This feature maybe be supported in future.**

## DB Change

### State DB

Following table changes would be added in State DB, including **DHCP_COUNTER_TABLE** table.

```
{
  'DHCP_COUNTER_TABLE': {
    'Vlan1000': {
      'RX': '{"Ack":"0","Decline":"0","Discover":"1","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}',
      'TX': '{"Ack":"0","Decline":"0","Discover":"0","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}'
    }
    'Vlan1000|Ethernet4': {
      'RX': '{"Ack":"0","Decline":"0","Discover":"1","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}',
      'TX': '{"Ack":"0","Decline":"0","Discover":"0","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}'
    }
    'Vlan1000|PortChannel1': {
      'RX': '{"Ack":"0","Decline":"0","Discover":"0","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}',
      'TX': '{"Ack":"0","Decline":"0","Discover":"1","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}'
    }
  }
}
```

# Cli

## Show Cli

**show dhcp_relay ipv4 counter**

This command is used to show dhcp_relay counter.

- Usage
    ```
    show dhcp_relay ipv4 counter [--dir (TX|RX)] [--type <type>] <vlan_interface>

    Options:
        dir: Specify egress or ingress
        type: Specify DHCP packet type
    
    Note: At least one of dir and type must be specified
    ```

- Example
    ```
    show dhcp_relay ipv4 counter Vlan1000 --dir TX
    Packet type Abbr: Un - Unknown, Dis - Discover, Off - Offer, Req - Request,
                      Ack - Acknowledge, Rel - Release, Inf - Inform,
                      Dec - Decline
    +-----------------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+
    | Vlan1000 (TX)         | Un  | Dis | Off | Req | Ack | Rel | Inf | Dec | Nak |
    ------------------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+
    | Downlink - Ethernet1  | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   |
    | Downlink - Ethernet2  | 0   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   |
    | Uplink - Ethernet46   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   |
    | Uplink - Ethernet47   | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   |
    | Uplink - PortChannel1 | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   |
    | Uplink - PortChannel2 | 0   | 2   | 0   | 2   | 0   | 0   | 0   | 0   | 0   |
    +-----------------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+

    show dhcp_relay ipv4 counter Vlan1000 --type Discover
    +----------------------+----+----+
    |Vlan1000 (Discover)   | TX | RX |
    +----------------------+----+----+
    |Downlink - Ethernet1  | 0  | 2  |
    |Downlink - Ethernet2  | 0  | 0  |
    |Uplink - Ethernet46   | 2  | 0  |
    |Uplink - Ethernet47   | 0  | 0  |
    |Uplink - PortChannel1 | 2  | 0  |
    |Uplink - PortChannel2 | 0  | 0  |
    +----------------------+----+----+

    show dhcp_relay ipv4 counter Vlan1000 --type Discover --dir TX
    +----------------------+----+
    |Vlan1000 (Discover)   | TX |
    +----------------------+----+
    |Downlink - Ethernet1  | 0  |
    |Downlink - Ethernet2  | 0  |
    |Uplink - Ethernet46   | 2  |
    |Uplink - Ethernet47   | 0  |
    |Uplink - PortChannel1 | 2  |
    |Uplink - PortChannel2 | 0  |
    +----------------------+----+
    ```

## Clear Cli

**sonic-clear dhcp_relay ipv4 counter**

This command is used to clear DHCPv4 counter

- Usage
    ```
    sonic-clear dhcp_relay ipv4 counter [--dir (TX|RX)] [--type <type>] [<vlan_interface>]

    Notice: dir / type / vlan_interface are all no-required parameters
    ```

- Example
    ```
    sonic-clear dhcp_relay ipv4 counter Vlan1000
    ```

# Test
## Unit Test
- show dhcp_relay ipv4 counter [--dir (TX|RX)] [--type \<type\>] \<vlan_interface\>
    |Case Description|Expected res|
    |:-|:-|
    |Show without specifying direction and without specifying type|Fail to display|
    |Show without specifying Vlan interface|Fail to display|
    |Show without specifying packet type and with specifying direction and with specifying Vlan interface|Display corresponding direction counter of Vlan interface|
    |Show with specifying interface with type and without specifying direction and with specifying Vlan interface|Display corresponding type of counter of specified interface|
    |Show with specifying type with specifying direction with specifying Vlan interface |Display corresponding direction and type counter of Vlan interface|
- sonic-clear dhcp_relay ipv4 counter [--dir (TX|RX)] [\<interface\>]
    |Case Description|Expected res|
    |:-|:-|
    |clear without specifying interface and without specifying direction|Fail to clear|
    |clear without specifying interface and with specifying direction|Fail to clear|
    |clear with specifying interface without specifying direction|clear counter of specified interface|
    |clear with specifying interface with specifying direction|clear corresponding direction counter of specified interface|

## sonic-mgmt
1. Basic counter functionatility test
2. Stress test for counter
