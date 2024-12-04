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
| Context interface | downstream, upstream and mgmt intfs specified in dhcpmon parameters: /usr/sbin/dhcpmon -id **Vlan1000** -iu **PortChannel101** -iu **PortChannel102** -iu **PortChannel103** -iu **PortChannel104** -im **eth0** |

# Overview

## Problem Statement

Currently, DHCPv4 counter in dhcpmon mainly focus on Vlan / PortChannel interface packet statistics and it store count statics in memory. Also dhcpmon only reports issue in syslog for DHCPv4 packets relayed disparity. User cannot actively query packets count. When issue like DHCP client cannot get ip happens, we need to do some packets capture and analyze to fingure out whether the packets received in switch and whether the packets has been relayed.

Below picture describe the workflow of current dhcpmon.

<div align="center"> <img src=images/old_dhcpmon.png width=480 /> </div>

## Functional Requirements

1. Count ingress and egress DHCPv4 packets based on interface and store it in STATE_DB.
2. SONiC CLI to show / clear counter.

# Design

## Design Overview

Below picture describe the new counter work flow. The highlighting part is what we change for per-interface counter.

<div align="center"> <img src=images/new_dhcpmon_block_incre.png width=630 /> </div>

1. Initialize rx/tx socket.
2. Update Vlan-physical interface and PortChannel-physical interface map.
3. Add timer events.
4. Initialize cache counter.
5. Different event callbacks handle packet event and timer event.

Below is sequence picture for it.
- Startup process is similar as previous. The different is that cache counter contains more interfaces' data and it's incremental data rather than full data.
- In libevent timer, dhcpmon would update STATE_DB by incremental cache counter and clear counter after healthy check.

<div align="center"> <img src=images/new_dhcpmon_seq.png width=600 /> </div>

### Counter Logic

Below pictures are samples for expected counter increasing for both directions.

<div align="center"> <img src=images/counter_sample.png width=800 /> </div>

dhcpmon would main focus on comparing below 3 fields in packet when counting packets. Point 1 and point 2 is used for counting context interface. And point 3 is used to get packet type.
1. `Destination ip Address` in **IP header**
2. `Gateway IP Address` in **DHCPv4 header**
3. `Option 53` in **DHCPv4 header**

Counter for context interface should be increased in below scenarios, and they can correspond to the above picture.

|              | Packets sent by DHCP client | Packets sent by DHCP server |
|--------------------------|----------------------------------|--|
| RX packet | **A**: If context interface is not uplink (Vlan) | **B**: If dst ip in ip header equals to context gateway and context interface is uplink (PortChannel) |
| TX packet | **C**: If gateway ip in dhcp header equals to context gateway ip and context interface is uplink | **D**: If context interface is not uplink (Vlan) |

Below picture shows work flow for counting.

<div align="center"> <img src=images/counter_logic.png width=800 /> </div>

1. Get physical interface name
2. Get context interface name by physical interface
3. Update physical interface counter
4. Update context interface counter with above logic

### Alert Logic

When the unhealthy situation persists for a period of time, dhcpmon should report an alarm in syslog. Below is how dhcpmon determine unhealthy situation:

1. For packets sent by client (Discover / Request / Decline / Release / Inform), the expected TX count depends on the number of DHCP server configured. Take below picture as example, there are 2 DHCP servers configured. If there is 1 RX Discover packet, then there should 2 TX Discover packets be found. Hence when **`[RX number] * [DHCP server number] > [TX number]`**, dhcpmon would treat it as unhealthy.

<div align="center"> <img src=images/client_to_server.png width=800 /> </div>

2. For packets sent by server (Offer / Ack / Nak), the expected TX count should be equal to RX count. Hence when **`[RX number] > [TX number]`**, dhcpmon would treat it as unhealthy.
<div align="center"> <img src=images/server_to_client.png width=800 /> </div>

3. TX packets are expected to go through downstream or upstream route, but if there is issue with default route, TX packets maybe go through management port. Hence when **`TX number of management port is increasing`**, dhcpmon would treat it as unhealthy.

## Counter aging

* Container restart
  * One dhcpmon process would only listen on one downstream Vlan interface, hence dhcpmon process restart will initialize (counter set to zero) for interface in below list:
    * Downstream / Upstream context interfaces given by startup parameter
    * Related Vlan member interfaces from CONFIG_DB table `VLAN_MEMBER|Vlanxxx`
    * Related PortChannel member interfaces from CONFIG_DB table`
* Vlan add/del
  * For now, after vlan adding or deleting, it requires dhcp_relay container be restarted to take effect. Vlan del Cli would automatically restart dhcp_relay container, other scenarios need manually restart. Then it could be referred to above `container restart` part
* Vlan / PortChannel member change
  * Member add: It's expected to set add entry and set counter to zero for member interface.
  * Member del: It's expected to delete related counter entry.
  * **Note: This requires db change subscription support. In early stage, we will mainly focus on key functionality. This feature maybe be supported in future.**
* Vlan member interface flapping: keep counting.

## DB Change

### State DB

Following table changes would be added in State DB, including **DHCP_COUNTER_TABLE** table.

```
{
  'DHCP_COUNTER_TABLE': {
    'Ethernet4': {
      'RX': '{"Ack":"0","Decline":"0","Discover":"1","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}',
      'TX': '{"Ack":"0","Decline":"0","Discover":"1","Inform":"0","Nak":"0","Offer":"0","Release":"0","Request":"0","Unknown":"0"}'
    }
  }
}
```

```JSON
{
  "DHCP_COUNTER_TABLE": {
    "Ethernet4|RX": {
        "Ack":"0",
        "Decline":"0",
        "Discover":"1",
        "Inform":"0",
        "Nak":"0",
        "Offer":"0",
        "Release":"0",
        "Request":"0",
        "Unknown":"0"
    },
    "Ethernet4|TX": {
        "Ack":"0",
        "Decline":"0",
        "Discover":"1",
        "Inform":"0",
        "Nak":"0",
        "Offer":"0",
        "Release":"0",
        "Request":"0",
        "Unknown":"0"
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
    show dhcp_relay ipv4 counter [--dir (TX|RX)] [<interface>]
    ```

- Example
    ```
    show dhcp_relay ipv4 counter Vlan1000
        Message Type       Vlan1000(RX)
    -------------------  -----------------
                Unknown                  0
            Discover                  0
                Offer                  0
                Request                  0
                    Ack                  0
                Release                  0
                Inform                  0
                Decline                  0
                    Nak                  0

            Message Type       Vlan1000(TX)
    -------------------  -----------------
                Unknown                  0
            Discover                  0
                Offer                  0
                Request                  0
                    Ack                  0
                Release                  0
                Inform                  0
                Decline                  0
                    Nak                  0
    ```

## Clear Cli

**sonic-clear dhcp_relay ipv4 counter**

This command is used to clear DHCPv4 counter

- Usage
    ```
    sonic-clear dhcp_relay ipv4 counter [--dir (TX|RX)] [<interface>]
    ```

- Example
    ```
    sonic-clear dhcp_relay ipv4 counter Vlan1000
    ```

# Test
## Unit Test
- show dhcp_relay ipv4 counter [--dir (TX|RX)] [\<interface\>]
    |Case Description|Expected res|
    |:-|:-|
    |Show without specifying interface and without specifying direction|Display counter of all interfaces|
    |Show without specifying interface and with specifying direction|Display corresponding direction counter of all interfaces|
    |Show with specifying interface without specifying direction|Display counter of specified interface|
    |Show with specifying interface with specifying direction|Display corresponding direction counter of specified interface|
- sonic-clear dhcp_relay ipv4 counter [--dir (TX|RX)] [<interface>]
    |Case Description|Expected res|
    |:-|:-|
    |clear without specifying interface and without specifying direction|clear counter of all interfaces|
    |clear without specifying interface and with specifying direction|clear corresponding direction counter of all interfaces|
    |clear with specifying interface without specifying direction|clear counter of specified interface|
    |clear with specifying interface with specifying direction|clear corresponding direction counter of specified interface|

## sonic-mgmt
Enhance current test cases and add new test cases for per-interface counter.
