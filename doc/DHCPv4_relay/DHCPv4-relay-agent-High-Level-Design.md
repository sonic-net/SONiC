# DHCPv4 Relay Agent

# High Level Design Document

# Revision
| Rev |     Date    |         Author        |          Change Description      |
|:---:|:-----------:|:---------------------:|:--------------------------------:|
| 1.0 | 02/28/2025  | Ashutosh Agrawal      | Initial Version                  |

## Table of Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [DHCPv4 Relay Agent](#dhcpv4-relay-agent)
- [High Level Design Document](#high-level-design-document)
- [Revision](#revision)
  - [Table of Contents](#table-of-contents)
  - [Scope](#scope)
  - [Definitions](#definitions)
- [Overview](#overview)
  - [DHCPv4 relay](#dhcpv4-relay)
  - [DHCPv4 Packet Forwarding with relay](#dhcpv4-packet-forwarding-with-relay)
  - [Requirements](#requirements)
  - [Design Considerations](#design-considerations)
- [Detailed Design](#detailed-design)
    - [Config Manager](#config-manager)
    - [Relay Main](#relay-main)
    - [Stats Manager](#stats-manager)
- [Yang Model](#yang-model)
- [DB Changes](#db-changes)
  - [Config-DB](#config-db)
  - [State-DB](#state-db)
- [CLI and Usage](#cli-and-usage)
  - [Configuration CLI](#configuration-cli)
  - [Show CLI](#show-cli)
- [Performance](#performance)
- [Limitations](#limitations)
- [Testing](#testing)

<!-- /code_chunk_output -->


## Scope

This document describes high level design details of SONiC's new DHCPv4 relay agent.

## Definitions

DHCP: Dynamic Host Configuration Protocol
DORA: Discovery, Offer, Request, and Acknowledgement

# Overview

SONiC currently supports DHCPv4 Relay functionality using the open-source ISC DHCP package. Since 2022, ISC has stopped development and maintenance of the ISC DHCP implementation and transitioned to a new DHCP server called Kea, which does not include a relay for either IPv4 or IPv6. The ISC DHCP relay agent (herafter referred to as ISC-DHCP) used in SONiC has several limitations:

- ISC-DHCP is not VLAN or VRF aware, requiring a separate process for each VLAN.
- ISC-DHCP uses a command-line configuration model that necessitates relaunching the DHCP container after any configuration changes.
- ISC-DHCP does not provide any statistics for debugging for monitoring.
- ISC-DHCP lacks support for many DHCP options and sub-options needed for features like EVPN and Static Anycast Gateway.
- In the SONiC implementation, about 20 patches have been applied to the open-source ISC package over the years for feature enhancements and security concerns. This patching mechanism is error-prone, difficult to understand, and cumbersome for adding new features and capabilities to the relay agent.

For IPv6, the SONiC community has developed a new relay agent to address some of these limitations. This document describes a similar effort to implement a DHCPv4 relay agent that will replace the current ISC-DHCP relay agent with a new SONiC-native implementation. This new implementation will interact with Redis-DB to download configuration and upload statistics.

## DHCPv4 relay

DHCP (Dynamic Host Configuration Protocol) is essential in network management, facilitating the automatic assignment of IP addresses to devices within a network. In IPv4 networks, DHCP relay functionality plays a crucial role, especially when the DHCP server is not in the same subnet as the client devices. Network devices like switches and routers, can be configured to act as DHCP relays to ensure seamless IP address allocation across different subnets.

When a DHCP client sends out a broadcast request for an IP address, that request is limited to its local subnet due to the nature of broadcast traffic. In scenarios where the DHCP server resides in a different subnet, the request would never reach it without assistance. Here, the network switch with DHCP relay functionality comes into play. The switch intercepts the broadcast DHCP request and forwards it as a unicast message to the specified DHCP server, often using the IP address of its own interface on the client's subnet as the source.

This process involves encapsulating the original DHCP request within a new IP packet, adding essential information, such as the 'giaddr' (gateway IP address) field, which helps the DHCP server identify the subnet from which the request originated. Once the DHCP server allocates an IP address, the switch relays the response back to the client, thus completing the DHCP transaction. This relay functionality is vital for maintaining efficient and organized IP address distribution in complex network environments with multiple subnets.


## DHCPv4 Packet Forwarding with relay

A DHCP relay agent is a crucial component in networks where clients and DHCP servers reside on different subnets. It facilitates the communication between clients and servers by forwarding DHCP messages across subnet boundaries. Here's how a DHCP relay agent handles the four basic DHCP messages:

1.	**DHCP Discover**: When a DHCP client broadcasts a Discover message to find available DHCP servers, the message is limited to the local subnet. The DHCP relay agent, typically configured on a router or a Layer 3 switch, intercepts this broadcast. It then encapsulates the Discover message in a unicast packet directed towards the DHCP server. The relay agent updates the 'giaddr' (gateway IP address) field in the message with its own IP address on the subnet from which the message originated. This helps the DHCP server identify the appropriate subnet for IP allocation. It also replaces source IP field with it's own IP address, so that response from the server will be routed back to the relay. The relay agent will also inserts DHCP relay agent option 82 in the packet if configured to do so.
<br>
2.	**DHCP Offer**: The DHCP server, by referring to the relay agent IP address (giaddr) in a DHCP Discover message, selects an IP address to allocate to the DHCP client from an IP pool, and sends a DHCP Offer message with the destination IP address set as the relay agent IP address. The relay agent receives this unicast Offer and decapsulates it, then forwards it as a broadcast message on the local subnet where the client resides. This ensures the client receives the Offer message, even though the server is on a different subnet.
<br>
3.	**DHCP Request**: The DHCP client which received the DHCP Offer message broadcasts a DHCP Request message on the physical Ethernet subnet to request network information data such as IP addresses. The DHCP relay agent, upon receiving this message, replaces the values in the fields (same as in the DHCP Discover message) of the packets, and then unicasts the message to the DHCP server.
<br>
4.	**DHCP Acknowledgment (ACK)**: The DHCP server sends a DHCP Ack message with the destination IP address set as the relay agent IP address (giaddr). The DHCP relay agent, upon receiving this message, replaces the values in the fields of the packets similar to Offer packet, and then unicasts the message to the DHCP client.

<div align="center"> <img src=images/DHCPv4_Relay_Basic_Flow.png width=600 /> </div>

## Requirements

- **R0:** Support basic DHCP Relay Functionality described in the previous section.

- **R1:** Support clients in multiple VLANs from the same process.

- **R2:** Support client and servers in both default and non-default VRFs.

- **R3:** In VXLAN environments, the relay agent must be able to relay DHCP packets between clients and servers located in different L3 VXLAN segments. If client and server are in the same extended VLAN (L2VNI case), DHCP relay functionality is not required.

- **R4:** In MC-LAG (Multi-Chassis Link Aggregation) environments, the relay agent must ensure that DHCP requests and responses are handled correctly across the MC-LAG peer switches.

- **R5:** DHCP relay between VRFs: Support forwarding client requests to a server located in a different VRF (Virtual Routing and Forwarding instance).

- **R6:** Support DHCP relay in networks using Static Anycast Gateways(SAG), where multiple switches route packets using a common gateway address.

- **R7:** Support relaying DHCP packets between the relay agent and DHCP server on point-to-point links configured as unnumbered interfaces. [RFC 5549](https://datatracker.ietf.org/doc/html/rfc5549)

- **R8:** Support the DHCP Relay Information option (Option 82), which allows network administrators to include additional information in relayed DHCP messages. Following relay sub-options will be supported.

    - **Circuit ID and Remote ID sub-option**: Allows relay agent to insert specific information related to location of the client in the relay requests. **These sub-options will be inserted by default into every relay packet.

    * **Link Selection sub-option** [RFC 3527](https://datatracker.ietf.org/doc/html/rfc3527): Specifies the subnet on which the DHCP client resides, allowing servers to allocate addresses from the correct pool.

    * **Server ID Override sub-option** [RFC 5107](https://datatracker.ietf.org/doc/html/rfc5107): Allows the relay agent to specify a new value for the server ID option. This sub-option allows the relay agent to act as the DHCP server, ensuring that renewal requests are sent to the relay agent rather than directly to the DHCP server.

    - **Virtual Subnet Selection option** [RFC 6607](https://datatracker.ietf.org/doc/html/rfc6607): Specifies the VRF/VPN from which the DHCP request came from

- **R9:** Support configuration of the source interface to specify the source IP address for relayed packets.

- **R10:** Support handling of DHCP packets that have already been relayed by other agents. Three options are available:

    - Discard: Discard the incoming packet (default).

    * Append: Append its own set of relay options to the packet, leaving the incoming options intact. If the length of relay agent information exceeds the max limit of 255 bytes, the packet is discarded.

    - Replace: Remove the incoming options and add its own set of options to the packet.

- **R11:** Support Dual-TOR use case

- **R12:** Scalability: The relay agent must be able to handle a large number of DHCP clients and servers. It should be able to support:

    - Number of VRFs - 1024
    - Number of VLANs - 4096
    - Number of DHCP Servers per VLAN - 32

-  **R13:** This proposed DHCP relay agent will need to support all the functionality that has been added over the years in the community through various patches. The complete backward compatibitlity with ISC DHCP is an aspirational goal.


## Design Considerations

- Co-existence with ISC-DHCP code. In order to allow users to seamlessly migrate from isc-dchp to sonic-dhcpv4-relay, both designs will be present in the SONiC codebase for some time. A new flag called ```has_sonic_dhcpv4_relay``` will be added to ```dhcp_relay``` feature in the config-db for the users to select one of the designs and default will be set to existing isc-dchp. Once the new design is proven to be a functional superset of isc-dhcp, both the feature flag and isc-dhcp can be deprecated.
- Alignment with DHCPv6 relay - The new DHCPv4 relay design will try to follow the same design structure as existing dhcp6 relay as much as possible but the code will be added in a new repository https://github.com/sonic-net/sonic-dhcpv4-relay
- Interop with port-based DHCP server - TBD

# Detailed Design

DHCPv4 relay process will run in the DHCP container along with DHCPv6 processes and DhcpMon. A single instance of the process will handle DHCPv4 relay functionality of all the VLANs that are configured. This process will listen to Redis for all the necessary configuration updates and will not require restarting of the container. The design is split into 3 sub-modules and the following diagram provides an overview of how they interact with each other:

<div align="center"> <img src=images/DHCPv4_Relay_sequence_diagram.png width=700 /> </div>

### Config Manager

The Config Manager thread will subscribe to redis-DB for updates to any required configurations and then synchronize the updates with the main thread. It will monitor the following tables:
- DHCPV4_RELAY table for relay configuration on VLAN interface
- INTF table for source interface to IP address mapping when source-interface paramenter is enabled in the relay configuration.
- VRF table for creating sockets to send packets to Server.

### Relay Main

The DHCPv4 relay main thread handles both Rx and Tx packets from the DHCP client and server. It interacts with the Config Manager for VLAN/VRF/L3-Interface updates and with Stats Manager to export stats.

Based on configurations, the Relay Main creates these sockets to receive and inject packets from the Kernel:

<div align="center"> <img src=images/DHCPv4_Relay_Rx_and_Tx_Sockets.png width=700 /> </div>

- Capture Rx Packets: It opens a socket listening on UDP port 67 with the ETH_ALL option to capture DHCPv4 packets on all the interfaces. This socket will capture packets from both server and client.

- Sending packets to server: For transmitting packets to server, the Relay Main opens and binds a socket for server VRF. If server VRF is not speficied as part of DHCP4_RELAY table, then client and server are assumed to be in the same VRF.

- Sending packets to client: A socket is opened on the client-side VLAN to forward DHCPv4 packets to the client.

### Stats Manager

The stats manager runs as a separate thread within the DHCPV4 relay process and periodicallys updates the per-VLAN relay statistics in the State DB. Additionally, an optional CLI/signal handler allows for on-demand stats to be updated to the State DB as well.

The stats manager will count packets in the context of client-side VLAN only. For client-to-server traffic, Both Rx and Tx counters will increment for the incoming VLAN only. If multiple dhcpv4 servers are configured on a VLAN, then Rx count will increment once and TX count will increment multiple times (once for each server copy). For server-to-client traffic, first the client side VLAN interface will be identified from DHCP header and then RX/TX counters will incremented in the context of the client-side VLAN.

Note that DHCPv4 relay process uses Kernel for forwarding of packets and is not aware of the destination physical interface. So, there is no support for per physical interface counters. Also, DHCP server may not be directly attached to the switch and may require a VXLAN tunnel for reachability in EVPN topologies. In this case, packets are sent/received on a L3VNI interface and relay process will not provide any counters in the context of server-side interface.

A proposed enhancement detailed in the [DHCPv4 Relay Per-Interface Counter](https://github.com/sonic-net/SONiC/blob/d0180d8e5ddefbbe50aad4e3b21f56f173f446cd/doc/dhcp_relay/DHCPv4-per-interface-counter.md) will take care of per-interface and other counters deemed necessary for DHCPv4 relay monitoring and debugging needs.

- Example 1: Vlan10 has a DHCPv4 relay configuration with a single server IP. After the initial DORA exchange has been completed, `show dhcpv4relay_counter` would display a count of 1 in both Rx and Tx directions for Discover/Offer/Request/Ack on Vlan 10. There will be no counter increments on the server facing vlan interface.

        +-------------+-------+-------+-------+-------+
        | Vlan (RX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan10      |    1  |    1  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

        +-------------+-------+-------+-------+-------+
        | Vlan (TX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan10      |    1  |    1  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

- Example 2: Vlan11 has a DHCPv4 relay configuration with there servers. In this case, relay will send a copy of the discover packet to each of the three servers and assuming all 3 responds, this is what `show dhcpv4relay_counters` will print after the initial DORA exchange has been completed,.

        +-------------+-------+-------+-------+-------+
        | Vlan (RX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan10      |    1  |    3  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

        +-------------+-------+-------+-------+-------+
        | Vlan (TX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan10      |    3  |    3  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

# Yang Model

A new yang-model for DHCPv4 will be added. This will be in addition to existing sonic-dhcpv6-relay yang model that has a table named DHCP_RELAY for DHCPv6. The existing DHCP_RELAY can be potentially renamed to DHCPV6_RELAY for more clarity and conistent naming.

sonic-dhcpv4-relay.yang

```JSON
module sonic-dhcpv4-relay {

    namespace "http://github.com/sonic-net/sonic-dhcpv4-relay";
    prefix dhcpv4relay;
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

    import sonic-types {
        prefix stypes;
    }

    import sonic-vrf {
        prefix vrf;
    }

    import sonic-port {
        prefix port;
    }

    import sonic-portchannel {
        prefix lag;
    }

    import sonic-loopback-interface {
        prefix loopback;
    }

    organization "SONiC";
    contact "SONiC";
    description "DHCPv4 Relay yang Module for SONiC OS";

    revision 2024-12-30 {
        description "First Revision";
    }

    container sonic-dhcpv4-relay {
        container DHCPV4_RELAY {
            description "DHCPV4_RELAY part of config_db.json";

            list DHCPV4_RELAY_LIST {
                key "name";

                leaf name {
                    description "VLAN ID";
                    type union {
                        // Comment VLAN leaf reference here until libyang back-links issue is resolved and use VLAN string pattern
                        // type leafref {
                        //     path "/vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name";
                        // }
                        type string {
                            pattern 'Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])';
                        }
                    }
               }

                leaf-list dhcpv4_servers {
                    description "Server IPv4 address list";
                    min-elements 1;
                    type inet:ipv4-address;
                }

                leaf server_vrf {
                    description "Server VRF";
                    type leafref {
                        path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
                    }
                    must "current()/../vrf_selection = 'enable' and
                          current()/../server_id_override = 'enable' and
                          current()/../link_selection = 'enable')" {
                        description "when server_vrf is set, link_selection, vrf_selection and server_id_override must be enabled";
                    }
                }

                leaf source_interface {
                    description "Used to determine the source IP address of the relayed packet";
                    type union {
                        type leafref {
                            path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                        }
                        type leafref {
                            path "/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name";
                        }
                        type string {
                            pattern 'Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][0-4])';
                        }
                        type leafref {
                            path "/loopback:sonic-loopback-interface/loopback:LOOPBACK_INTERFACE/loopback:LOOPBACK_INTERFACE_LIST/loopback:name";
                        }
                    }
                }

                leaf link_selection {
                    description "Enable link-selection sub-option 11";
                    type stypes:mode-status;
                    default disable;
                    must "current() = 'disable' or current()/../source_interface != ''" {
                        description "if link_selection is enabled, source_interface must be set";
                    }
                }

                leaf vrf_selection {
                    description "Enable VRF selection sub-option 151";
                    type stypes:mode-status;
                    default disable;
                    must "current() = 'disable' or current()/../server_vrf != ''" {
                        description "if vrf_selection is enabled, server_vrf must be set";
                    }
                }

                leaf server_id_override {
                    description "Enable server id override sub-option 5";
                    type stypes:mode-status;
                    default disable;
                }

                leaf agent_relay_mode {
                    description "How to forward packets that already have a relay option";
                    type stypes:relay-agent-mode;
                    default forward_untouched;
                }

                leaf max_hop_count {
                    description "Maximum hop count for relayed packets";
                    type uint8 {
                        range "1..16";
                    }
                    default 4;
                }
            }
            /* end of DHCPV4_RELAY_LIST */
        }
        /* end of container DHCPV4_RELAY */
    }
    /* end of container sonic-dhcpv4-relay */
}
/* end of module sonic-dhcpv4-relay */

```

# DB Changes

## Config-DB

A new table will be added in config-db to specify the dhcp-relay configuration on a vlan. The DHCPV4 relay table will serve as the authoritative source for DHCPv4 relay configurations. For backward compatibility, configurations via VLAN mode are still supported. The existing VLAN based CLI that adds a ```dhcpv4_servers``` field to VLAN table will continue to be supported for now. Once ISC-DHCP code is deprecated, this CLI will be be updated to add the server information to DHCPV4_RELAY table. Similarily, a VLAN show command will fetch the relevant dhcpv4 configuration from DHCPV4_table.


```JSON
{
    "DHCPV4_RELAY": {
        "Vlan11": {
            "dhcpv4_servers": "192.168.20.100",
            "server_vrf": "VRF-RED",
            "source_interface": "Loopback0",
            "link_selection": "enable",
            "vrf_selection": "enable",
            "server_id_override": "enable",
            "agent_relay_mode": "forward_untouched"
        }
    }
}
```

## State-DB

A new DHCPV4_RELAY_COUNTER table will be added in the State DB.

```JSON
{
  'DHCPV4_RELAY_COUNTER_TABLE': {
    'Vlan1000': {
      'RX': '{"Un":"0","Dis":"0","Off":"1","Req":"0","Nack":"0","Rel":"0","Inf":"0","Dec":"0","Mal":"0","Drp":"0"}',
      'TX': '{"Un":"0","Dis":"0","Off":"1","Req":"0","Nack":"0","Rel":"0","Inf":"0","Dec":"0","Mal":"0","Drp":"0"}'
    }
  }
}
```

# CLI and Usage

## Configuration CLI

DHCPv4 relay configurations can be established using VLAN mode or directly through DHCPV4_RELAY settings.

**Existing manual CLI to add/del relay configuration in the VLAN table**

These existing CLIs can be used to ```add``` or ```delete``` DHCPv4 Relay helper address to a VLAN. Note that the `update` operation is not supported. Also, these CLIs can be used to only add a list of server IP addresses. They will not allow configuration of any DHCP relay suboptions or other optional parameters that were introduced in sonic-dchpv4-relay.

- **Usage**
```CMD
sudo config vlan dhcp_relay ipv4 (add | del) <vlan_id> <dhcp_relay_destination_ips>
sudo config dhcp_relay ipv4 helper (add | del) <vlan_id> <dhcp_helper_ips>
```

- **Examples**
```
sudo config vlan dhcp_relay add 1000 7.7.7.7
sudo config dhcp_relay ipv4 helper add 1000 7.7.7.7 1.1.1.1
sudo config vlan dhcp_relay del 1000 7.7.7.7
sudo config dhcp_relay ipv4 helper del 1000 7.7.7.7
```

**New Yang-model validated CLI to write into a DHCPV4_RELAY table with VLAN as the key**
- **Usage**<br>

    -  Add dhcpv4 relay configuration on a VLAN<br>

        ```CMD
        root@sonic:/home/cisco# config dhcpv4-relay add -h
        Usage: config dhcpv4-relay add [OPTIONS] Vlan<vlan_num>

          Add object in DHCPV4_RELAY.

        Options:
          --server-vrf         <VrfName>                        Server VRF
          --source-interface   <ifname>                         Used to determine the source IP         address of the
                                                                relayed packet
          --link-selection     <enable|disable>                 Enable link selection
          --vrf-selection      <enable|disable>                 Enable VRF selection
          --server-id-override <enable|disable>                 Enable server id override
          --agent-relay-mode   <forward_and_append|
                                forward_and_replace|
                                forward_untouched|
                                discard>                        How to forward packets that         already have a relay
                                                                option
          --max-hop-count      <hop-cnt>                        Maximum hop count for relayed         packets
          --dhcpv4-servers     <comma-separated-ipv4-list>      Server IPv4 address list
        ```

    - Delete an existing relay configuration<br>
        ```
        sudo config dhcpv4-relay del Vlan<vlan_num>
        ```

    - Update relay configuration for an existing entry<br>

        ```
        sudo config dhcpv4-relay update Vlan<vlan_num> [OPTIONS]
        ```

- **Examples**
    * Add a list of dhcpv4 servers to Vlan11<br>
        ```
        config dhcpv4-relay add Vlan11 --dhcpv4-servers 192.168.11.1,192.168.11.2
        ```

    * Specify Source Interface to change the source IP of DHCP relay agent<br>

        ```CMD
        sudo config dhcpv4-relay update Vlan11 --source-interface Loopback0
        ```

    - Add a dhcpv4 server configuration where server and clients are in different VRFs. VRF of the DHCP Server is specified through CLI and Client VRF is derived from the interface on which dhcp_relay is configured. Specifying server-vrf also requires link-selection, vrf-selection and server-id-override sub-options to be enabled and source-interface to be listed.

        ```CMD
        sudo config dhcpv4-relay add Vlan12 --dhcpv4-servers 192.168.12.1 --server-vrf Vrf01         --link-selection enable --server-id-override enable --vrf-selection enable         --source-interface Loopback0
        ```

    - Update max-hop-count to limit the number of dhcp relays that a packet can go through after which it's dropped.

        ```CMD
        sudo config dhcpv4-relay update Vlan12 --max-hop-count 4
        ```

    - Update the list of dhcp servers configure on a VLAN

        ```CMD
        sudo config dhcpv4-relay update Vlan12 --dhcpv4-servers 192.168.12.1,192.168.12.2
        ```

    - Update dhcpv4 relay configuration to replace relay-options if it receives a packet that already contains relay-options

        ```
        sudo config dhcpv4-relay update Vlan12 --agent-relay-mode forward_and_replace
        ```

## Show CLI

**Existing CLI to show dhcpv4 relay configuration**

- Show dhcpv4 relay configuration for a VLAN

```
root@sonic:/home/cisco# show vlan brief
+-----------+--------------+---------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports   | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+=========+================+=============+=======================+
|        10 |              |         |                | disabled    | 10.10.10.10           |
+-----------+--------------+---------+----------------+-------------+-----------------------+
```

```
root@sonic:/home/cisco# show dhcp_relay ipv4 helper
+-------------+----------------------+
|   Interface |   DHCP Relay Address |
+=============+======================+
|      Vlan10 |          10.10.10.10 |
+-------------+----------------------+
```

**New CLI to show dhcpv4 relay configuration**

```
root@sonic:/home/cisco# show dhcpv4-relay
NAME    SERVER VRF    SOURCE INTERFACE    LINK SELECTION    VRF SELECTION    SERVER ID OVERRIDE    AGENT RELAY MODE       MAX HOP COUNT  DHCPV4 SERVERS
------  ------------  ------------------  ----------------  ---------------  --------------------  -------------------  ---------------  ----------------
Vlan12  Vrf01         Loopback0           enable            enable           enable                forward_and_replace                4  192.168.12.1
                                                                                                                                         192.168.12.2
```

**New Show CLI to report per-VLAN interface counters**

These CLIs show the number of DCHPv4 packets received and transmitted in the context of a client side VLAN interface.

- Usage

    * Show counters syntax
        ```
        # show dhcp4relay_counters --help
        Usage: show dhcp4relay counters [OPTIONS] VLAN_INTERFACE

        Options:
          -d, --direction [TX|RX]         Specify TX(egress) or RX(ingress)
          -t, --type [Unkown|Discover|Offer|Request|Acknowledge|Release|Inform|Decline|Malformed]
                                          Specify DHCP packet counter type
          -?, -h, --help                  Show this message and exit.
        ```

    * Clear counters syntax
        ```
        # sonic-clear dhcp4relay counters --help
        Usage: sonic-clear dhcp_relay counters [OPTIONS] [VLAN_INTERFACE]

          Clear dhcp4relay message counts

        Options:
          -d, --direction [TX|RX]         Specify TX(egress) or RX(ingress)
          -t, --type [Unkown|Discover|Offer|Request|Acknowledge|Release|Inform|Decline|Malformed]
                                          Specify DHCP packet counter type
          -?, -h, --help                  Show this message and exit.
        ```

- Examples

    * Show all counters
        ```
        show dhcpv4relay_counter counts
        ```

    * Show only counters for Vlan10
        ```
        show dhcpv4relay_counter counts Vlan10
        ```
        ```
        Packet type Abbr: Un - Unknown, Dis - Discover, Off - Offer, Req - Request,
                  Ack - Acknowledge, Nack - NegativeAcknowledge, Rel - Release,
                  Inf - Inform, Dec - Decline, Mal - Malformed, Drp - Dropped

        +-------------+------+-------+-------+-------+-------+--------+-------+-------+-------+-------+-------+
        | Vlan (RX)   |   Un |   Dis |   Off |   Req |   Ack |   Nack |   Rel |   Inf |   Dec |   Mal |   Drp |
        +=============+======+=======+=======+=======+=======+========+=======+=======+=======+=======+=======+
        | Vlan10      |    0 |    32 |    10 |    10 |    10 |      0 |     0 |     0 |     0 |     0 |    22 |
        +-------------+------+-------+-------+-------+-------+--------+-------+-------+-------+-------+-------+
        Packet type Abbr: Un - Unknown, Dis - Discover, Off - Offer, Req - Request,
                          Ack - Acknowledge, Nack - NegativeAcknowledge, Rel - Release,
                          Inf - Inform, Dec - Decline, Mal - Malformed, Drp - Dropped

        +-------------+------+-------+-------+-------+-------+--------+-------+-------+-------+-------+-------+
        | Vlan (TX)   |   Un |   Dis |   Off |   Req |   Ack |   Nack |   Rel |   Inf |   Dec |   Mal |   Drp |
        +=============+======+=======+=======+=======+=======+========+=======+=======+=======+=======+=======+
        | Vlan10      |    0 |    10 |    10 |    10 |    10 |      0 |     0 |     0 |     0 |     0 |       |
        +-------------+------+-------+-------+-------+-------+--------+-------+-------+-------+-------+-------+
        ```

    * Show only Rx packets for Vlan10
        ```
        show dhcpv4relay_counter counts Vlan10 --direction RX
        ```
    * Show only discover packets received for Vlan10
        ```
        show dhcpv4relay_counter counts Vlan10 --direction RX --t Dis
        ```


# Performance
DHCP relay packets are clubbed with LLPD and UDLD in a copp bucket with 300 packets/sec rate-limiter. Accordingly, dhcpv4_relay process should be able to handle 300 packets/sec with minimal cpu impact.

# Limitations

- Unlike ISC-DHCP design, the new relay will not require users to split interfaces between upstream and downstream. Accordingly, it will not support the capability to limit dhcp requests or replies on certain interfaces only.


# Testing
- Unit tests for dhcpv4-relay
- Unit tests for Yang-model and CLIs
- Existing SONiC Management tests for:
    - basic dhcp-relay functionality
    - dual-tor support
    - interop with port-based dhcp-server
- New Spytests for:
    - New Option 82 sub-options introduced in sonic-dhcpv4-relay
    - dhcp relay functionality in an EVPN topology with clients and servers on different leafs
