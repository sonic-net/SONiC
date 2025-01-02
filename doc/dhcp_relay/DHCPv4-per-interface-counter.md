# DHCPv4 Relay Per-Interface Counter
# High Level Design Document

# Revision

| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:-----------------------------------|
| 1.0 |  05/29/2023 | Jie Cai       | Initial version                     |
| 1.1 |  11/01/2024 | Yaqiang Zhu, <br> Jing Kan       | Revise                 |

# About this Manual

This document describes the design details of DHCPv4 Relay per-interface counter feature. It provides capability to count DHCPv4 relay packets based on packets type and ingress / egress interface.

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
| dhcrelay | Open source DHCP relay process distributed by ISC  |
| dhcpmon | DHCPv4 relay monitor process |
| Context interface | downlink, uplink and mgmt intfs specified in dhcpmon parameters: /usr/sbin/dhcpmon -id **Vlan1000** -iu **PortChannel101** -iu **PortChannel102** -iu **PortChannel103** -iu **PortChannel104** -im **eth0** |

# Overview

## Problem Statement

Currently, DHCPv4 counter in dhcpmon mainly focus on Vlan / PortChannel interface packet statistics and it store count statics in memory. Also dhcpmon only reports issue in syslog for DHCPv4 packets relayed disparity. It has below disadvantages:
1. The counting granularity is Vlan/PortChannel, the data for physical interface is missing.
2. There is no API for User to actively query packets count. When issue like DHCP client cannot get ip happens, we need to do some packets capture and analyze to fingure out whether the packets received in switch and whether the packets has been relayed.

## Functional Requirements

1. Count ingress and egress DHCPv4 packets based on interface and store it in STATE_DB.
2. SONiC CLI to show / clear counter.

# Design

## Design Overview

To address above 2 issues, we propose below design, it could be devided into 3 parts: `Init`, `Per-interface counting` and `Persist`

### Init

<div align="center"> <img src=images/init.png width=530 /> </div>

1. There are **2 sockets for all interfaces** to capture DHCPv4 packets. We bind callback to the network events to process packets.
2. Read from `PORTCHANNEL_MEMBER` and `VLAN_MEMBER` table CONFIG_DB to construct mapping between physical interface and PortChannel/Vlan. It's used to query context interface by physical interface.
3. We have 2 kinds of counters, one is persisted in STATE_DB, another is stored in process memory, they are initialized when process startup.
4. Initialize a timer to periodically sync counter data from cache counter to DB counter.

### Per-interface counting

<div align="center"> <img src=images/per_intf_counting.png width=600 /> </div>

* From socket, we can fingure out which physical interface does the packet came from.
* Context interface name could be obtained by querying context interface counter.
* Then cache counter for corresponding physical interface and context would increase **immediately**.

### Persist

<div align="center"> <img src=images/persist.png width=450 /> </div>

DB update timer would be invoked periodically (**every 20s**), it will obtain the counter data increased during the statistical period from the cache counter

## Counter Logic

### Overview

Below pictures are samples for expected counter increasing for both directions.

<div align="center"> <img src=images/counter_sample.png width=600 /> </div>

dhcpmon would main focus on comparing below 3 fields in packet when counting packets. Point 1 and point 2 is used for counting context interface, **we only count client-sent packets which come from downlink Vlan and server-sent packets which come from uplink interfaces**. And point 3 is used to get packet type.
1. `Destination ip Address` in **IP header**
2. `Gateway IP Address` in **DHCPv4 header**
3. `Option 53` in **DHCPv4 header**

Counter for context interface should be increased in below scenarios, and they can correspond to the above picture.

|              | Packets sent by DHCP client | Packets sent by DHCP server |
|--------------------------|----------------------------------|--|
| RX packet | **A**: If context interface is not uplink (Vlan) | **B**: If dst ip in ip header equals to context gateway and context interface is uplink (PortChannel) |
| TX packet | **C**: If gateway ip in dhcp header equals to context gateway ip and context interface is uplink | **D**: If context interface is not uplink (Vlan) |

### Dual-ToR Specified

In Dual-ToR there are some behaviors different with single ToR:
1. We wouldn't count packets come from standby interfaces (Refer to `HW_MUX_CABLE_TABLE` in STATE_DB).
2. In above counting logic, we would compare `gateway` in DHCP packets. In single ToR, the gateway is Vlan ip, but in Dual-ToR, it's device's Loopback ip.

## Counter Reset

* Container restart
  * One dhcpmon process would only listen on one downlink Vlan interface, hence dhcpmon process restart will initialize (counter set to zero) for interface in below list:
    * Downlink / Uplink context interfaces given by startup parameter
    * Related Vlan member interfaces from CONFIG_DB table `VLAN_MEMBER|Vlanxxx`
    * Related PortChannel member interfaces from CONFIG_DB table`
* Vlan add/del
  * For now, after vlan adding or deleting, it requires dhcp_relay container be restarted to take effect. Vlan del Cli would automatically restart dhcp_relay container, other scenarios need manually restart. Then it could be referred to above `container restart` part
* Vlan / PortChannel member change
  * Member add: It's expected to set add entry and set counter to zero for member interface.
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
    sonic-clear dhcp_relay ipv4 counter [--dir (TX|RX)] [<vlan_interface>]
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
