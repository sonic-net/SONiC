# DHCPv4 Relay Agent

# High Level Design Document


## Table of Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [DHCPv4 Relay Agent](#dhcpv4-relay-agent)
- [High Level Design Document](#high-level-design-document)
  - [Table of Contents](#table-of-contents)
    - [1. Revision](#1-revision)
    - [2. Scope](#2-scope)
    - [3. Definitions](#3-definitions)
    - [4. Overview](#4-overview)
      - [4.1 DHCPv4 relay](#41-dhcpv4-relay)
      - [4.2 DHCPv4 Packet Forwarding with relay](#42-dhcpv4-packet-forwarding-with-relay)
    - [5. Requirements](#5-requirements)
      - [5.1 Design Considerations](#51-design-considerations)
        - [5.1.1 Co-existence with ISC-DHCP Code](#511-co-existence-with-isc-dhcp-code)
        - [5.1.2 Alignment with DHCPv6 Relay](#512-alignment-with-dhcpv6-relay)
        - [5.1.3 Interop with Port-Based DHCP Server](#513-interop-with-port-based-dhcp-server)
        - [5.1.4 DHCP Monitor](#514-dhcp-monitor)
        - [5.1.5 Dual-Tor Support](#515-dual-tor-support)
    - [6. Detailed Design](#6-detailed-design)
      - [6.1 DHCPv4 Config Manager](#61-dhcpv4-config-manager)
      - [6.2 Relay Main](#62-relay-main)
        - [6.2.1 Client->Server Packet Handling](#621-client-server-packet-handling)
        - [6.2.2 Server->Client Packet Handling](#622-server-client-packet-handling)
      - [6.3 Stats Manager](#63-stats-manager)
    - [7. Yang Model](#7-yang-model)
    - [8. DB Changes](#8-db-changes)
      - [8.1 Config-DB](#81-config-db)
      - [8.2 Counter-DB](#82-counter-db)
    - [9. CLI and Usage](#9-cli-and-usage)
      - [9.1 Configuration CLI](#91-configuration-cli)
        - [9.1.1 Existing CLI to add/del relay configuration in the VLAN table](#911-existing-cli-to-adddel-relay-configuration-in-the-vlan-table)
        - [9.1.2 New CLI to write into a DHCPV4_RELAY table with VLAN as the key](#912-new-cli-to-write-into-a-dhcpv4_relay-table-with-vlan-as-the-key)
      - [9.2 Show CLI](#92-show-cli)
        - [9.2.1 Existing show CLI output for dhcpv4 relay configuration](#921-existing-show-cli-output-for-dhcpv4-relay-configuration)
        - [9.2.2 New show CLI output for dhcpv4 relay configuration](#922-new-show-cli-output-for-dhcpv4-relay-configuration)
        - [9.2.3 New Show CLI to report per-VLAN interface counters](#923-new-show-cli-to-report-per-vlan-interface-counters)
    - [10. Configuration Migration](#10-configuration-migration)
      - [10.1 Configuration Migration](#101-configuration-migration)
    - [11. Performance](#11-performance)
    - [12. Limitations](#12-limitations)
    - [13. Testing](#13-testing)

<!-- /code_chunk_output -->

### 1. Revision
| Rev |     Date    |         Author        |          Change Description      |
|:---:|:-----------:|:---------------------:|:--------------------------------:|
| 1.0 | 02/28/2025  | Ashutosh Agrawal      | Initial Version                  |

### 2. Scope

This document describes high level design details of SONiC's new DHCPv4 relay agent.

### 3. Definitions

DHCP: Dynamic Host Configuration Protocol
DORA: Discovery, Offer, Request, and Acknowledgement

### 4. Overview

SONiC currently implements DHCPv4 Relay functionality using the open-source ISC DHCP package. However, since 2022, ISC has ceased development and maintenance of the ISC DHCP software, transitioning to a new DHCP server called Kea, which does not include relay functionality for either IPv4 or IPv6. The ISC DHCP relay agent (hereafter referred to as ISC-DHCP) used in SONiC has several limitations:
- **Lack of VLAN and VRF Awareness:** The ISC-DHCP implementation requires a distinct process for each VLAN because it lacks native support for VLAN or VRF separation. This limitation imposes significant scalability constraints on the number of VLANs a system can effectively manage. Running a separate process per VLAN increases resource consumption and complexity, making it difficult for a SONiC device to support a large number of VLANs.
- **Configuration Model:** The ISC-DHCP implementation employs a command-line configuration model, which requires the DHCP container to be relaunched whenever configuration changes are made. This process can be cumbersome and disruptive, as it interrupts DHCP services during the restart, potentially affecting client connectivity while the container is restarting. Also these scheme doesn't allow for any config validation.
- **Lack of Monitoring and Debugging Tools:** ISC-DHCP does not provide any statistics, making it challenging to monitor and debug.
- **Limited Support for DHCP Options:** ISC-DHCP lacks support for various DHCP options and sub-options essential for features like EVPN and Static Anycast Gateway.
- **Complex Patch Management:** Over the years, approximately 20 patches have been applied to the open-source ISC package in the SONiC implementation to address feature enhancements and security concerns. This patching process is error-prone, difficult to manage, and cumbersome when adding new features and capabilities to the relay agent.

To address some of these limitations for DHCPv6, the SONiC community has developed a new relay agent. This document outlines a similar initiative to implement a DHCPv4 relay agent that will replace the current ISC-DHCP relay agent with a SONiC-native solution. This new implementation will interact with Redis-DB to download configurations and upload statistics. It will also add support for the features required for a DHCPv4 relay to operate in an EVPN topology.

#### 4.1 DHCPv4 relay

DHCP (Dynamic Host Configuration Protocol) is a key component in network management, enabling the automatic allocation of IP addresses to devices within a network. In IPv4 environments, DHCP relay functionality becomes particularly important when the DHCP server is located on a different subnet than the client devices. To facilitate seamless IP address distribution across various subnets, network devices such as switches and routers can be configured to function as DHCP relays.

When a DHCP client broadcasts a request for an IP address, the nature of broadcast traffic confines this request to its local subnet. If the DHCP server is situated on a different subnet, the request would not reach the server without intervention. This is where a network switch with DHCP relay capabilities is essential. The switch intercepts the broadcast DHCP request and forwards it as a unicast message to the designated DHCP server, often using the IP address of its own interface on the client's subnet as the source address.

The relay process involves adding crucial information, such as the 'giaddr' (gateway IP address) field in the packet, which aids the DHCP server in identifying the subnet from which the request originated. Once the DHCP server assigns an IP address, the switch relays the server's response back to the client, completing the DHCP transaction. This relay functionality is crucial for ensuring efficient and organized IP address allocation in complex network environments with multiple subnets, thereby supporting seamless network operations and management.

#### 4.2 DHCPv4 Packet Forwarding with relay

A DHCP relay agent is an essential component in networks where clients and DHCP servers are on different subnets, enabling communication by forwarding DHCP messages across subnet boundaries. Here's how a DHCP relay agent manages the four basic DHCP messages:

- **DHCP Discover:** When a DHCP client broadcasts a Discover message to locate available DHCP servers, the message is confined to the local subnet. The DHCP relay agent, typically configured on a router or Layer 3 switch, intercepts this broadcast. It encapsulates the Discover message in a unicast packet directed to the DHCP server and updates the 'giaddr' (gateway IP address) field with its own IP address on the originating subnet. This helps the DHCP server identify the correct subnet for IP allocation. The relay agent also replaces the source IP field with its own IP address to ensure the server's response is routed back to the relay. Additionally, the relay agent can insert DHCP relay agent option 82 into the packet if configured to do so.

- **DHCP Offer:** The DHCP server, using the relay agent's IP address in the giaddr field of the DHCP Discover message, selects an IP address from its pool to allocate to the client and sends a DHCP Offer message to the relay agent's IP address. The relay agent receives this unicast Offer, decapsulates it, and forwards it as a broadcast message on the local subnet where the client is located. This ensures the client receives the Offer message, even though the server resides on a different subnet.

- **DHCP Request:** The DHCP client, upon receiving the DHCP Offer, broadcasts a DHCP Request message on the local Ethernet subnet to request network configuration information such as an IP address. The DHCP relay agent intercepts this message, updates the fields as it did in the DHCP Discover message, and unicasts the packet to the DHCP server.

- **DHCP Acknowledgment (ACK):** The DHCP server responds with a DHCP Ack message, setting the destination IP address to the relay agent's IP address (giaddr). Upon receiving this message, the DHCP relay agent updates the packet's fields similar to the Offer message and forwards it as a unicast message to the DHCP client, completing the DHCP transaction.

<div align="center"> <img src=images/DHCPv4_Relay_Basic_Flow.png width=600 /> </div>

### 5. Requirements

- **R0:** Support basic DHCP Relay Functionality described in the previous section.

- **R1:** Support clients in multiple VLANs from the same process.

- **R2:** Support client and servers in both default and non-default VRFs.

- **R3:** In VXLAN environments, the relay agent must be able to relay DHCP packets between clients and servers located in different L3 VXLAN segments. If client and server are in the same extended VLAN (L2VNI case), DHCP relay functionality is not required.

- **R4:** In MC-LAG (Multi-Chassis Link Aggregation) environments, the relay agent must ensure that DHCP requests and responses are handled correctly across the MC-LAG peer switches.

- **R5:** DHCP relay between VRFs: Support forwarding client requests to a server located in a different VRF (Virtual Routing and Forwarding instance).

- **R6:** Support DHCP relay in networks using Static Anycast Gateways(SAG), where multiple switches route packets using a common gateway address.

- **R7:** Support relaying DHCP packets between the relay agent and DHCP server on point-to-point links configured as unnumbered interfaces. [RFC 5549](https://datatracker.ietf.org/doc/html/rfc5549)

- **R8:** Support the DHCP Relay Information option (Option 82), which allows network administrators to include additional information in relayed DHCP messages. Following relay sub-options will be supported.

      - **Circuit ID and Remote ID sub-option**: Allows the relay agent to insert specific information related to the location of the client in the relay requests. These sub-options will be inserted by default into every relay packet.

    * **Link Selection sub-option** [RFC 3527](https://datatracker.ietf.org/doc/html/rfc3527): Specifies the subnet on which the DHCP client resides, allowing servers to allocate addresses from the correct pool.

    * **Server ID Override sub-option** [RFC 5107](https://datatracker.ietf.org/doc/html/rfc5107): Allows the relay agent to specify a new value for the server ID option. This sub-option allows the relay agent to act as the DHCP server, ensuring that renewal requests are sent to the relay agent rather than directly to the DHCP server.

      - **Virtual Subnet Selection option** [RFC 6607](https://datatracker.ietf.org/doc/html/rfc6607): Specifies the VRF/VPN from which the DHCP request came from.

- **R9:** Support configuration of the source interface (giaddr) for the relayed packets.

- **R10:** Support handling of DHCP packets that have already been relayed by other agents. Three options are available:

    - Discard: Discard the incoming packet (default).

    * Append: Append its own set of relay options to the packet, leaving the incoming options intact. If the length of relay agent information exceeds the max limit of 255 bytes, the packet is discarded.

    - Replace: Remove the incoming options and add its own set of options to the packet.

- **R11:** Support Dual-TOR use case

- **R12:** Support multiple subnets/interfaces on a VLAN. If multiple interfaces are configured on a vlan, DHCP4 relay will insert only the primary address as giaddr in dhcp request packets.

- **R13:** Scalability: The relay agent must be able to handle a large number of DHCP clients and servers. It should be able to support:

    - Number of VRFs - 1024
    - Number of VLANs - 4096
    - Number of DHCP Servers per VLAN - 32

-  **R14:** This proposed DHCP relay agent will need to support all the functionality that has been added over the years in the community through various patches. The complete backward compatibitlity with ISC DHCP is an aspirational goal.


#### 5.1 Design Considerations

##### 5.1.1 Co-existence with ISC-DHCP Code
To facilitate a smooth transition for users migrating from ISC-DHCP to the new SONiC-DHCPv4-Relay, both implementations will coexist within the SONiC codebase for a period of time. A new configuration flag, has_sonic_dhcpv4_relay, will be introduced in the dhcp_relay feature within the config-db. This flag will allow users to select either the ISC-DHCP or the SONiC-DHCPv4-Relay implementation, with the default set to the existing ISC-DHCP. Once the new design has been validated as a functional superset of ISC-DHCP, both the feature flag and the ISC-DHCP implementation will be deprecated.

##### 5.1.2 Alignment with DHCPv6 Relay
The new DHCPv4 relay design will aim to mirror the design structure of the existing DHCPv6 relay as closely as possible, ensuring consistency and ease of integration. Code for the DHCPv4 relay will be maintained in a new sub-directory in the existing dhcp relay repository: [https://github.com/sonic-net/sonic-dhcpv-relay](https://github.com/sonic-net/sonic-dhcpv-relay). Also, current DHCPv6 relay code will be moved to a parallel subdirectory.

##### 5.1.3 Interop with Port-Based DHCP Server
In the current ISC-DHCP design, a daemon process named `dhcprelayd` operates within the dhcp_relay container. If `dhcp_server` feature is enabled, this daemon is responsible for monitoring the `dhcpv4_server` configuration and managing the lifecycle of the `dhcrelay` process, including actions such as starting, stopping, and restarting it.

The new DHCPv4 Relay design aims to continue this integration with the port-based DHCPv4 server feature by not requiring the need for explicit relay configuration. Instead of depending on an external daemon, the new design will rely on a DHCPv4 CfgMgr thread (described later in this document), which will continuously monitor both the ConfigDb and StateDb for any port-based DHCP server configurations. This thread will dynamically configure the relay functionality as needed, ensuring that changes in server configurations are seamlessly integrated without extra configuration.

##### 5.1.4 DHCP Monitor
The existing DHCP monitor will be enhanced in-order to support monitoring of DHCPv4 packets being handled by the new implementation.

##### 5.1.5 Dual-Tor Support
In a dual-TOR (Top-of-Rack) architecture, it's possible for DHCP request packets from a client to reach the server through one TOR, while the server's response might arrive at the peer TOR. If the peer TOR has its link in standby mode, it won't be able to relay the response back to the originating client. This issue can be addressed by configuring the DHCPv4 relay with the link-selection and source-interface options.

By enabling the link-selection option, the DHCP relay will use the interface specified by the source-interface option to populate the giaddr field in the packet. When the loopback interface is set as the source-interface, the DHCP request packet sent from the client will have the loopback IP of the originating TOR in the giaddr field. If the DHCP response arrives at the peer TOR, which is in standby mode, it will simply route the packet to the originating ToR. Once the originating TOR receives the response, it can forward the packet to the client through its active interface, as it normally would.

### 6. Detailed Design

DHCPv4 relay process will run in the dhcp_relay container along with DHCPv6 processes and DhcpMon. A single instance of the process will handle DHCPv4 relay functionality of all the VLANs that are configured. This process will listen to Redis for all the necessary configuration updates and will not require restarting of the container. The design is split into 3 sub-modules and the following diagram provides an overview of how they interact with each other:

<div align="center"> <img src=images/DHCPv4_Relay_sequence_diagram.png width=700 /> </div>

#### 6.1 DHCPv4 Config Manager

The Config Manager thread is responsible for subscribing to the Redis database to receive updates on necessary configurations and synchronizing these updates with the main thread. The following is a non-exhaustive list of the tables monitored by the Config Manager thread.:
- **DHCPV4_RELAY Table**: For relay configuration on VLAN interfaces
- **INTF Table:** For mapping source interfaces to IP addresses when the source-interface parameter is enabled in the relay configuration.
- **VRF Table:** For creating sockets to send packets to Server.
- **FEATURE Table:** To check if port based `dhcp_server` feature is enabled.
- **DEVICE_METADATA Table:** To populate hostname and device mac in circuit-id/remote-id and also to check if device is a smartSwitch.
- **DHCP_SERVER_IPV4_SERVER_IP Table:** From StateDB to get server-IP for port-based dhcp_server.
- **DHCP_SERVER_IPV4 Table:** For per-VLAN port-based DHCP server configuration
- **VLAN Table:** To ensure that VLAN exists before starting any DHCPv4 relay functionality and get associated VRF id.

#### 6.2 Relay Main

The DHCPv4 relay main thread manages both the reception and transmission of packets between the DHCP client and server. It coordinates with the Config Manager for updates on VLAN, VRF, and L3-Interface configurations and interacts with the Stats Manager to export statistics.

Depending on the configurations, Relay Main establishes sockets to receive and transmit packets from the kernel:

<div align="center"> <img src=images/DHCPv4_Relay_Rx_and_Tx_Sockets.png width=700 /> </div>

- **Capturing Rx Packets:** It opens a socket listening on UDP port 67 with the ETH_ALL option to capture DHCPv4 packets on all the interfaces. This socket will capture packets from both server and client.

- **Sending Packets to the Server:** For transmitting packets to the server, Relay Main opens and binds a socket for the server VRF. If no server VRF is specified in the DHCPV4_RELAY table, the client and server are assumed to be in the same VRF and client-side VLAN_interface table's VRF field is used to bind the socket.

- **Sending Packets to the Client:** A socket is opened on the client-side VLAN to forward DHCPv4 packets to the client. This socket is used to broadcast DHCP Offer and Ack packets in the client's VLAN.

When the DHCPv4 relay feature is enabled, the Control Plane Policing (CoPP) manager will configure appropriate trap rules, ensuring that DHCPv4 packets are trapped and rate-limited by the Network Processing Unit (NPU). Once these packets reach the kernel, the DHCP relay main process captures them through the previously described socket mechanisms.

The relay process first inspects the Opcode in the DHCP header to decide how to handle the packet:
- **BOOTREQUEST:** If the Opcode indicates a BOOTREQUEST, the packet is processed through the Client-to-Server packet handling pathway. This involves forwarding the client's DHCP request to the appropriate DHCP server, potentially adding relay information options as configured.
- **BOOTREPLY :** If the Opcode is not a BOOTREQUEST, the packet is assumed to be a response from a DHCP server and is processed through the Server-to-Client packet handling pathway. This involves relaying the DHCP server's response back to the client on the originating subnet.

##### 6.2.1 Client->Server Packet Handling

The processing steps are as follows:
-	**Packet Validation:** The relay process parses the packet headers to check for any invalid fields, such as hlen or hop_count.
-	**Interface Identification:** It identifies the incoming interface from the socket structure and retrieves the associated VLAN and DHCPv4 relay configuration.
-	**Configuration Check:** If the interface IP is absent or there is no DHCPv4 relay configuration, the packet is returned to the kernel.
-   **giaddr selection:** If source-interface is programmed in the ConfigDB entry, corresponding interface IP is used as the giaddr of the relayed packet. Otherwise, giaddr is set to the incoming interface IP address.
-	**Adding Relay Sub-options:** Depending on the configuration, various relay sub-options are added to the packet:
    - Circuit-ID: Always inserted, it includes the `hostname` from the Device Metadata table, interface alias from the Port Table, and VLAN ID, all separated by a colon. If `hostname` is not present in the Device Metadata table, `sonic` is used as hostname instead.


        | Subopt | Len | Circuit ID |
        | -------|-----|-------------------------------|
        |    1   |  n  | hostname:interface_alias:vlan |

    - Remote-ID: Also always inserted, this option carries the MAC address from the localhost|mac field in the DEVICE_METADATA table.

        | Subopt | Len | Remote ID |
        | -------|-----|-----------|
        |    2   |  6  | my_mac |

    - Link-Selection: If the corresponding flag is enabled in the ConfigDB entry, the link-selection sub-option (0x5) is added, carrying the client-side subnet IP. The server is expected to use this value to assign an IP address instead of relying on the giaddr value.

        | Subopt | Len | Subnet IP Address |
        | -------|-----|-------------------|
        |    5   |  4  | Client-Subnet-IP |

    - Server-ID Override: If enabled, this sub-option carries the interface IP of the client VLAN.

        | Subopt | Len | Overriding Server Identified Address |
        | -------|-----|--------------------
        |    11   |  4  | Client-Interface-IP   |

    - Virtual Subnet Selection (VSS): If enabled, this option carries the VRF of the client VLAN. Please note that RFC6607 has slightly different format for this sub-option and includes a `type` field Len and VSS Info. The exact format for this sub-option will be updated after further testing.

        | Subopt | Len | VSS Info  |
        | -------|-----|-----------|
        |  151   |  len  | vrf-name |

##### 6.2.2 Server->Client Packet Handling

For packets arriving with an Opcode of BOOTREPLY, the DHCP relay agent undertakes the following steps to ensure proper handling and forwarding:
- **Parse Relay Sub-options:** The relay agent parses and extracts all relay sub-options from the packet, which may include information such as Circuit-ID, Remote-ID, and other relevant details.
- **Identify Downstream Interface**
		- Using Circuit-ID: If the packet contains a Circuit-ID sub-option, the relay agent uses the VLAN portion of the Circuit-ID to identify the appropriate downstream interface through which to forward the packet to the client. This method provides a direct and efficient way to determine the correct path for the packet.
		- Fallback to giaddr: If the Circuit-ID is absent, the relay agent falls back on the giaddr (gateway IP address) field. It loops through each interface IP and compares it with the giaddr value to identify the corresponding downstream interface. This ensures that even without a Circuit-ID, the packet can still be accurately directed to the client.


#### 6.3 Stats Manager

The Stats Manager operates as a separate thread within the DHCPv4 relay process and periodically updates per-VLAN relay statistics in the Counters DB. Additionally, an optional CLI or signal handler allows for on-demand updates to the Counters DB.

The Stats Manager focuses on packet counting within the context of the client-side VLAN only. For client-to-server traffic, both Rx and Tx counters increase for the incoming VLAN. If multiple DHCPv4 servers are configured on a VLAN, the Rx count increases once, while the Tx count increments multiple times (once for each server copy). For server-to-client traffic, the client-side VLAN interface is identified from the DHCP header, and then the Rx/Tx counters are updated in the context of the client-side VLAN.

It's important to note that the DHCPv4 relay process relies on the kernel for packet forwarding and is unaware of the destination physical interface, thus lacking support for per-physical interface counters. Additionally, if the DHCP server is not directly attached to the switch and requires a VXLAN tunnel for reachability in EVPN topologies, packets are sent/received on an L3VNI interface, and the relay process does not provide counters for the server-side interface context.

A proposed enhancement, as outlined in the DHCPv4 Relay Per-Interface Counter document, aims to address the need for detailed per-interface and additional counters necessary for monitoring and debugging the DHCPv4 relay process.

- **Example 1:** Consider a scenario where Vlan10 is configured with a DHCPv4 relay pointing to a single server IP. Upon the completion of the initial DORA (Discover, Offer, Request, Acknowledgment) exchange, executing the command show dhcpv4relay_counter would display a count of 1 in both the Rx and Tx directions for each of the DORA messages on Vlan10. Importantly, there would be no increment in counters on the server-facing VLAN interface, as the counters are specific to the client-facing interface interactions.

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

- **Example 2:** In the case where Vlan11 is configured with a DHCPv4 relay pointing to three servers, the relay will send a copy of the Discover packet to each of the three servers. Assuming all three servers respond, the command show dhcpv4relay_counters would display the following counts after the initial DORA exchange is completed:

        +-------------+-------+-------+-------+-------+
        | Vlan (RX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan11      |    1  |    3  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

        +-------------+-------+-------+-------+-------+
        | Vlan (TX)   |   Dis |   Off |   Req |   Ack |
        +=============+=======+=======+=======+=======+
        | Vlan11      |    3  |    3  |    1  |    1  |
        +-------------+-------+-------+-------+-------+

### 7. Yang Model

A new YANG model for DHCPv4 will be introduced, complementing the existing sonic-dhcpv6-relay YANG model, which includes a table named DHCP_RELAY for DHCPv6. To enhance clarity and ensure consistent naming conventions, the existing DHCP_RELAY table could potentially be renamed to DHCPV6_RELAY.

sonic-dhcpv4-relay.yang

```
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
                    must "(current()/../server_id_override = 'enable' and
                          current()/../link_selection = 'enable')" {
                        description "when server_vrf is set, link_selection and server_id_override must be enabled";
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
                    description "Enable link-selection sub-option 5";
                    type stypes:mode-status;
                    default disable;
                    must "current() = 'disable' or exists(current()/../source_interface)" {
                        description "if link_selection is enabled, source_interface must be set";
                    }
                }

                leaf vrf_selection {
                    description "Enable VRF selection sub-option 151";
                    type stypes:mode-status;
                    default disable;
                    must "current() = 'disable' or exists(current()/../server_vrf)" {
                        description "if vrf_selection is enabled, server_vrf must be set";
                    }
                }

                leaf server_id_override {
                    description "Enable server id override sub-option 11";
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

### 8. DB Changes

#### 8.1 Config-DB

A new table, named DHCPV4_RELAY, will be introduced in the config-db to define DHCP relay configurations on a VLAN. This table will act as the authoritative source for DHCPv4 relay settings. For backward compatibility, existing configurations through VLAN mode will remain supported. The current VLAN-based CLI, which adds a dhcpv4_servers field to the VLAN table, will continue to function temporarily. The existing config CLI will be enhanced to add dhcpv4 server configuration to both VLAN and DHCPv4 tables. Once the ISC-DHCP code is deprecated, this CLI will be updated to record server information in the DHCPV4_RELAY table only. Similarly, a VLAN show command will retrieve the relevant DHCPv4 configuration from the DHCPV4_RELAY table instead of the VLAN table, ensuring that users can seamlessly transition to the new configuration model without disruption.

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

#### 8.2 Counter-DB

A new DHCPV4_RELAY_COUNTER table will be added in the Counter DB.

```
{
  'DHCPV4_RELAY_COUNTER_TABLE': {
    'Vlan1000': {
      'RX': '{"Un":"0","Dis":"0","Off":"1","Req":"0","Nack":"0","Rel":"0","Inf":"0","Dec":"0","Mal":"0","Drp":"0"}',
      'TX': '{"Un":"0","Dis":"0","Off":"1","Req":"0","Nack":"0","Rel":"0","Inf":"0","Dec":"0","Mal":"0","Drp":"0"}'
    }
  }
}
```

### 9. CLI and Usage

#### 9.1 Configuration CLI

DHCPv4 relay configurations can be established using VLAN mode or directly through DHCPV4_RELAY settings.

##### 9.1.1 Existing CLI to add/del relay configuration in the VLAN table

These existing CLIs can be used to ```add``` or ```delete``` DHCPv4 Relay helper address to a VLAN. Note that the `update` operation is not supported. Also, these CLIs can be used to only add a list of server IP addresses. They will not allow configuration of any DHCP relay suboptions or other optional parameters that were introduced in sonic-dhcpv4-relay.

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

##### 9.1.2 New CLI to write into a DHCPV4_RELAY table with VLAN as the key
- **Usage**<br>

    -  Add dhcpv4 relay configuration on a VLAN<br>

        ```CMD
        root@sonic:/home/cisco# config dhcpv4_relay ipv4 helper add -h
        Usage: config dhcp_relay ipv4 helper add [OPTIONS] NAME

          Add object in DHCPV4_RELAY.

        Options:
          --server-vrf <vrf_name>                    Server VRF
          --source-interface <interface_name>        Used to determine the source IP address of the
                                                     relayed packet
          --link-selection <enable|disable>          Enable link selection
          --vrf-selection  <enable|disable>          Enable VRF selection
          --server-id-override <enable|disable>      Enable server id override
          --agent-relay-mode <forward_and_append|
                              forward_and_replace|
                              forward_untouched|
                              discard>              How to forward packets that already have a relay
                                                    option
          --max-hop-count <1..16>                   Maximum hop count for relayed packets
          --dhcpv4-servers <ipv4_address_list>      Server IPv4 address list
          -h, -?, --help                            Show this message and exit.
        ```

    - Delete an existing relay configuration<br>
        ```
        sudo config dhcp_relay ipv4 helper del Vlan<vlan_num>
        ```

    - Update relay configuration for an existing entry<br>

        ```
        sudo config dhcpv_relay ipv4 helper update Vlan<vlan_num> [OPTIONS]
        ```

- **Examples**
    * Add a list of dhcpv4 servers to Vlan11<br>
        ```
        config dhcp_relay ipv4 helper add Vlan11 --dhcpv4-servers 192.168.11.1,192.168.11.2
        ```

    * Specify Source Interface of the DHCP relay agent<br>

        ```CMD
        sudo config dhcp_relay ipv4 helper update Vlan11 --source-interface Loopback0
        ```

    - Add a dhcpv4 server configuration where server and clients are in different VRFs. VRF of the DHCP Server is specified through CLI and Client VRF is derived from the interface on which dhcp_relay is configured. Specifying server-vrf also requires link-selection, vrf-selection and server-id-override sub-options to be enabled and source-interface to be listed.

        ```CMD
        sudo config dhcp_relay ipv4 helper add Vlan12 --dhcpv4-servers 192.168.12.1 --server-vrf Vrf01 --link-selection enable --server-id-override enable --vrf-selection enable --source-interface Loopback0
        ```

    - Update max-hop-count to limit the number of dhcp relays that a packet can go through after which it's dropped.

        ```CMD
        sudo config dhcp_relay ipv4 helper update Vlan12 --max-hop-count 4
        ```

    - Update the list of dhcp servers configure on a VLAN

        ```CMD
        sudo config dhcp_relay ipv4 helper update Vlan12 --dhcpv4-servers 192.168.12.1,192.168.12.2
        ```

    - Update dhcpv4 relay configuration to replace relay-options if it receives a packet that already contains relay-options

        ```
        sudo config dhcp_relay ipv4 helper update Vlan12 --agent-relay-mode forward_and_replace
        ```

#### 9.2 Show CLI

##### 9.2.1 Existing show CLI output for dhcpv4 relay configuration

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

##### 9.2.2 New show CLI output for dhcpv4 relay configuration

```
root@sonic:/home/cisco# show dhcp_relay ipv4 helper
NAME    SERVER VRF    SOURCE INTERFACE    LINK SELECTION    VRF SELECTION    SERVER ID OVERRIDE    AGENT RELAY MODE       MAX HOP COUNT  DHCPV4 SERVERS
------  ------------  ------------------  ----------------  ---------------  --------------------  -------------------  ---------------  ----------------
Vlan12  Vrf01         Loopback0           enable            enable           enable                forward_and_replace                4  192.168.12.1
                                                                                                                                         192.168.12.2
```

##### 9.2.3 New Show CLI to report per-VLAN interface counters

These CLIs show the number of DHCPv4 packets received and transmitted in the context of a client side VLAN interface.

- Usage

    * Show counters syntax
        ```
        # show dhcp4relay_counters counts --help
        Usage: show dhcp4relay counters counts [OPTIONS] VLAN_INTERFACE

        Options:
          -d, --direction [TX|RX]         Specify TX(egress) or RX(ingress)
          -t, --type [Unknown|Discover|Offer|Request|Acknowledge|Release|Inform|Decline|Malformed]
                                          Specify DHCP packet counter type
          -?, -h, --help                  Show this message and exit.
        ```

    * Clear counters syntax
        ```
        # sonic-clear dhcp4relay counters --help
        Usage: sonic-clear dhcp4relay counters [OPTIONS] [VLAN_INTERFACE]

          Clear dhcp4relay message counts

        Options:
          -d, --direction [TX|RX]         Specify TX(egress) or RX(ingress)
          -t, --type [Unknown|Discover|Offer|Request|Acknowledge|Release|Inform|Decline|Malformed]
                                          Specify DHCP packet counter type
          -?, -h, --help                  Show this message and exit.
        ```

   * Alternate Show counters syntax
        ```
        # show dhcp_relay ipv4 counters --help
        Usage: show dhcp_relay ipv4 counters [OPTIONS] VLAN_INTERFACE

        Options:
          -d, --direction [TX|RX]         Specify TX(egress) or RX(ingress)
          -t, --type [Unknown|Discover|Offer|Request|Acknowledge|Release|Inform|Decline|Malformed]
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
                  Ack - Acknowledge, Nack - Negative Acknowledge, Rel - Release,
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
        | Vlan10      |    0 |    10 |    10 |    10 |    10 |      0 |     0 |     0 |     0 |     0 |     0 |
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

### 10. Configuration Migration

In the current isc-dhcp based design, dhcp relay configuration is achieved through a combination of the VLAN table in ConfigDb and command line arguments supplied to isc-dhcrelay process itself. In the new design, all the configuration will be consolidated to DHCPV4_RELAY table in the ConfigDB. Following table illustrates how the existing configuration will be migrated to the new schema.

#### 10.1 Configuration Migration
The table below lists the various isc-dhcp command-line options currently used in SONiC and outlines how they will be migrated in the new design.

| Existing isc cmd line arg | New Configuration | Comments |
|-|-|-|
| -m discard | --agent-relay-mode with the same default value| |
| -a %%h:%%p | Not required | Always insert agent-relay-options in hostname:int-alias:vlan-id format |
| %%P | Not Required | Always insert remote-id in the agent-relay-options |
| --name-alias-map-file | Not Required | Interface Alias is dynamically retrieved from ConfigDB |
| -id <vlan_name> | Not required | Not needed anymore since a common process is used for all the VLANs |
| -U <Loopback0> | --source-interface Loopback0 | TODO: If DualToR flag is set in the DEVICE_METADATA, set source_interface to Loopback 0 |
| -dt | None | New design will take DualToR config from the DEVICE_METADATA table |
| -si | | |
| -iu <interface_name> | None | No need to separate out upstream/downstream interfaces |
| -pg <primary_gateway_ip> | None | New design will automatically pick up the primary gateway IP from VLAN_INTERFACE table |
| dhcp_server | --dhcpv4-servers \<server-list> |db_migrator.py will migrate dhcp_server list from VLAN table to DHCPV4_RELAY in the ConfigDB|


### 11. Performance
DHCP relay packets are clubbed with LLPD and UDLD in a copp bucket with 300 packets/sec rate-limiter. Accordingly, dhcpv4_relay process should be able to handle 300 packets/sec with minimal cpu impact.

### 12. Limitations

- Unlike ISC-DHCP design, the new relay will not require users to split interfaces between upstream and downstream. Accordingly, it will not support the capability to limit dhcp requests or replies on certain interfaces only.


### 13. Testing
- Unit tests for dhcpv4-relay
- Unit tests for Yang-model and CLIs
- Existing SONiC Management tests for:
    - basic dhcp-relay functionality
    - dual-tor support
    - interop with port-based dhcp-server
- New Spytests for:
    - New Option 82 sub-options introduced in sonic-dhcpv4-relay
    - dhcp relay functionality in an EVPN topology with clients and servers on different leafs
