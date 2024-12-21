# DHCPv4 Relay Agent

# High Level Design Document

# Table of Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [DHCPv4 Relay Agent](#dhcpv4-relay-agent)
- [High Level Design Document](#high-level-design-document)
- [Table of Contents](#table-of-contents)
- [Scope](#scope)
- [Definitions](#definitions)
- [Overview](#overview)
- [DHCPv4 relay](#dhcpv4-relay)
- [DHCPv4 Packet Forwarding with relay](#dhcpv4-packet-forwarding-with-relay)
- [Requirements](#requirements)
- [Topology](#topology)
- [Design Considerations](#design-considerations)
- [Configuration and Management](#configuration-and-management)
  - [Yang Model](#yang-model)
  - [CLI and Usage](#cli-and-usage)
  - [Config-DB Schema](#config-db-schema)
- [Performance](#performance)
- [Limitations](#limitations)
- [Testing](#testing)

<!-- /code_chunk_output -->


# Scope

This document describes high level design details of SONiC's new DHCPv4 relay agent.

# Definitions

DHCP: Dynamic Host Configuration Protocol
DORA: Discovery, Offer, Request, and Acknowledgement

# Overview

SONiC currently supports DHCPv4 Relay functionality using the open-source ISC DHCP package. Since 2022, ISC has stopped development and maintenance of the ISC DHCP implementation and transitioned to a new DHCP server called Kea, which does not include a relay for either IPv4 or IPv6. The ISC DHCP relay agent used in SONiC has several limitations:

- It is not VLAN or VRF aware, requiring a separate process for each VLAN.
- It uses a command-line configuration model that necessitates relaunching the DHCP container after any configuration changes.
- It does not provide statistics for debugging.
- It lacks support for many DHCP options and sub-options needed for features like EVPN and Static Anycast Gateway.
- In the SONiC implementation, over 20 patches have been applied to the open-source ISC package over the years for feature enhancements and security concerns. This patch mechanism is error-prone, difficult to understand, and cumbersome for adding new features and capabilities to the relay agent.

For IPv6, the SONiC community has developed a new relay agent to address some of these limitations. This document describes a similar effort to implement a DHCPv4 relay agent that will replace the current ISC DHCP relay agent with a new SONiC-native implementation. This new implementation will interact with Redis-DB to download configuration and upload statistics.

# DHCPv4 relay

DHCP (Dynamic Host Configuration Protocol) is essential in network management, facilitating the automatic assignment of IP addresses to devices within a network. In IPv4 networks, DHCP relay functionality plays a crucial role, especially when the DHCP server is not in the same subnet as the client devices. Network devices like switches and routers, can be configured to act as DHCP relays to ensure seamless IP address allocation across different subnets.

When a DHCP client sends out a broadcast request for an IP address, that request is limited to its local subnet due to the nature of broadcast traffic. In scenarios where the DHCP server resides in a different subnet, the request would never reach it without assistance. Here, the network switch with DHCP relay functionality comes into play. The switch intercepts the broadcast DHCP request and forwards it as a unicast message to the specified DHCP server, often using the IP address of its own interface on the client's subnet as the source. This process involves encapsulating the original DHCP request within a new IP packet, adding essential information, such as the 'giaddr' (gateway IP address) field, which helps the DHCP server identify the subnet from which the request originated. Once the DHCP server allocates an IP address, the switch relays the response back to the client, thus completing the DHCP transaction. This relay functionality is vital for maintaining efficient and organized IP address distribution in complex network environments with multiple subnets.


# DHCPv4 Packet Forwarding with relay

A DHCP relay agent is a crucial component in networks where clients and DHCP servers reside on different subnets. It facilitates the communication between clients and servers by forwarding DHCP messages across subnet boundaries. Here's how a DHCP relay agent handles the four basic DHCP messages:

1.	DHCP Discover: When a DHCP client broadcasts a Discover message to find available DHCP servers, the message is limited to the local subnet. The DHCP relay agent, typically configured on a router or a Layer 3 switch, intercepts this broadcast. It then encapsulates the Discover message in a unicast packet directed towards the DHCP server. The relay agent updates the 'giaddr' (gateway IP address) field in the message with its own IP address on the subnet from which the message originated. This helps the DHCP server identify the appropriate subnet for IP allocation. It also replaces source IP field with it's own IP address, so that response from the server will be routed back to the relay. The relay agent will also inserts DHCP relay agent option 82 in the packet if configured to do so.
2.	DHCP Offer: The DHCP server, by referring to the relay agent IP address (giaddr) in a DHCP Discover message, selects an IP address to allocate to the DHCP client from an IP pool, and sends a DHCP Offer message with the destination IP address set as the relay agent IP address. The relay agent receives this unicast Offer and decapsulates it, then forwards it as a broadcast message on the local subnet where the client resides. This ensures the client receives the Offer message, even though the server is on a different subnet.
3.	DHCP Request: The DHCP client (PC) which received the DHCP Offer message broadcasts a DHCP Request message on the physical Ethernet subnet to request network information data such as IP addresses. The DHCP relay agent, upon receiving this message, replaces the values in the fields (same as in the DHCP Discover message) of the packets, and then unicasts the message to the DHCP server.
4.	DHCP Acknowledgment (ACK): The DHCP server sends a DHCP Ack message with the destination IP address set as the relay agent IP address (giaddr). The DHCP relay agent, upon receiving this message, replaces the values in the fields of the packets similar to Offer packet, and then unicasts the message to the DHCP client (PC).

# Requirements

- Support basic DHCP Relay Functionality described in the previous section.

- Support clients in multiple VLANs from the same process.

- Support client and servers in both default and non-default VRFs.

- In VXLAN environments, the relay agent must be able to relay DHCP packets between clients and servers located in different L3 VXLAN segments. If client and server are in the same extended VLAN (L2VNI case), DHCP relay functionality is not required.

- In MC-LAG (Multi-Chassis Link Aggregation) environments, the relay agent must ensure that DHCP requests and responses are handled correctly across the MC-LAG peer switches.

- DHCP relay between VRFs: Support forwarding client requests to a server located in a different VRF (Virtual Routing and Forwarding instance).

- Support DHCP relay in networks using Static Anycast Gateways(SAG), where multiple switches route packets using a common gateway address.

- Support relaying DHCP packets between the relay agent and DHCP server on point-to-point links configured as unnumbered interfaces. [RFC 5549](https://datatracker.ietf.org/doc/html/rfc5549)

- Support the DHCP Relay Information option (Option 82), which allows network administrators to include additional information in relayed DHCP messages.

    * Circuit ID and Remote ID sub-option: Allows relay agent to insert specific information related to location of the client in the relay requests.

    * Link Selection sub-option [RFC 3527](https://datatracker.ietf.org/doc/html/rfc3527): Specifies the subnet on which the DHCP client resides, allowing servers to allocate addresses from the correct pool.

    * Server ID Override sub-option [RFC 5107](https://datatracker.ietf.org/doc/html/rfc5107): Allows the relay agent to specify a new value for the server ID option. This sub-option allows the relay agent to act as the DHCP server, ensuring that renewal requests are sent to the relay agent rather than directly to the DHCP server.

    * Virtual Subnet Selection option [RFC 6607](https://datatracker.ietf.org/doc/html/rfc6607): Specifies the VRF/VPN from which the DHCP request came from

- Support configuration of the source interface to specify the source IP address for relayed packets.

- Support handling of DHCP packets that have already been relayed by other agents. Three options are available:

    * Discard: Discard the incoming packet (default).

    * Append: Append its own set of relay options to the packet, leaving the incoming options intact. If the length of relay agent information exceeds the max limit of 255 bytes, the packet is discarded.

    * Replace: Remove the incoming options and add its own set of options to the packet.

- Support Dual-TOR use case

- Scalability: The relay agent must be able to handle a large number of DHCP clients and servers. It should be able to support:

    * Number of VRFs - 1024
    * Number of VLANs - 4096
    * Number of DHCP Servers per VLAN - 32

- Complete backward compatibitlity with ISC DHCP is an aspirational goal.


# Topology

# Design Considerations

Open questions:
- How to handle co-existence with ISC-DHCP code
- Separate report DHCPv4 relay or combine with existing DHCPv6 agent

# Configuration and Management



## Yang Model

sonic-dhcpv4-relay.yang

```
module sonic-dhcpv4-relay
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
                    type inet:ipv4-address;
                }

                leaf server_vrf {
                    description "Server VRF";
                    type leafref {
                        path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
                    }
                    must "(current() = '' or (current()/../vrf_selection = 'enable' and
                                               current()/../server_id_override = 'enable' and
                                               current()/../link_selection = 'enable'))" {
                        description "when server_vrf set, link_selection, vrf_selection and server_id_override must be enabled";
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
                    description "Enable link selection";
                    type stypes:mode-status;
                    default disable;
                    must "current() = 'disable' or current()/../source_interface != ''" {
                        description "if link_selection is enabled, source_interface must be set";
                    }
                }

                leaf vrf_selection {
                    description "Enable VRF selection";
                    type stypes:mode-status;
                    default disable;
                }

                leaf server_id_override {
                    description "Enable server id override";
                    type stypes:mode-status;
                    default disable;
                }

                leaf agent_relay_mode {
                    description "How to forward packets that already have a relay option";
                    type stypes:relay-agent-mode;
                    default forward_untouched;
                }
            }
            /* end of DHCPV4_RELAY_LIST */
        }
        /* end of container DHCPV4_RELAY */
    }
```

## CLI and Usage


- Existing manual CLI to add relay configuration in the VLAN table

```
config vlan dhcp_relay ipv4 (add | del) <vlan_id> <dhcp_relay_destination_ips>
config vlan dhcp_relay ipv6 destination (add | del) <vlan_id> <dhcp_destination_ips>
```

- New Yang-model validated CLI to write into a new table with VLAN as the key

```
config dhcpv4-relay (add | del) Vlan<vlan_id> --dhcpv4-servers 192.168.20.10
```

- Specify Source Interface to change the source IP of DHCP relay agent

```
config vlan dhcp-relay-src add Vlan<vlan_id> --source_intrface <interface_name> --dhcp-servers <dhcp_destination_ips>
```

- Client VRF is derived from the interface on which dhcp_relay is configured. Specify VRF of the DHCP Server

```
config vlan dhcp_relay ipv4 add Vlan<vlan_id> <dhcp_relay_destination_ips> server_vrf <server_vrf>
```

## Config-DB Schema

```
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

# Performance

# Limitations

# Testing
