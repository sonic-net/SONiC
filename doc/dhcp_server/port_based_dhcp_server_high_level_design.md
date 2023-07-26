# IPv4 Port Based DHCP_SERVER in SONiC
# High Level Design Document
**Rev 0.1**

# Table of Contents
<!-- TOC -->

- [IPv4 Port Based DHCP_SERVER in SONiC](#ipv4-port-based-dhcp_server-in-sonic)
- [High Level Design Document](#high-level-design-document)
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
                    - [Table 1: Abbreviations](#table-1-abbreviations)
                    - [Table 2: Definitions](#table-2-definitions)
- [Overview](#overview)
    - [Background](#background)
    - [Functional Requirements](#functional-requirements)
    - [Configuration and Management Requirements](#configuration-and-management-requirements)
- [Design](#design)
    - [Design Overview](#design-overview)
    - [Container](#container)
    - [DHCP Server Daemon](#dhcp-server-daemon)
        - [Generate Config](#generate-config)
        - [Update Lease](#update-lease)
    - [Customize DHCP Packet Options](#customize-dhcp-packet-options)
    - [DB Changes](#db-changes)
        - [Config DB](#config-db)
            - [Yang Model](#yang-model)
            - [DB Objects](#db-objects)
        - [State DB](#state-db)
            - [Yang Model](#yang-model)
            - [DB Objects](#db-objects)
    - [Flow Diagrams](#flow-diagrams)
        - [DHCP Server Flow](#dhcp-server-flow)
        - [Config Change Flow](#config-change-flow)
        - [Lease Update Flow](#lease-update-flow)
- [CLI](#cli)
    - [Config CLI](#config-cli)
    - [Show CLI](#show-cli)
- [Test](#test)
    - [Unit Test](#unit-test)
    - [Test Plan](#test-plan)
- [Implement Detail](#implement-detail)

<!-- /TOC -->

# Revision

| Rev |     Date    |       Author       | Change Description                  |
|:---:|:-----------:|:-------------------|:-----------------------------------|
| 0.1 |  2023/02/08 | Yaqiang Zhu, <br> Jing Kan       | Initial version                     |

# About this Manual

This document describes the design details of **ipv4 port based DHCP server** feature.
Dynamic Host Configuration Protocol (DHCP) server is used to centrally manage and configure IP addresses of clients dynamically. When server receives requests from DHCP-enabled clients, it would offer information to client about IP address, subnet mask, gateway etc.

# Scope
This document describes the high level design details about how **ipv4 port based DHCP server** works.

# Definitions/Abbreviations
###### Table 1: Abbreviations
| Abbreviation             | Full form                        |
|--------------------------|----------------------------------|
| DHCP                      | Dynamic Host Configuration Protocol      |

###### Table 2: Definitions
| Definitions             | Description                        |
|--------------------------|----------------------------------|
| kea-dhcp-server    | Open source DHCP server process distributed by ISC      |
| dhcrelay | Open source DHCP relay process distributed by ISC |

# Overview
A DHCP Server is a server on network that can automatically provide and assign IP addresses, default gateways and other network parameters to client devices. 

## Background
We plan to implement built-in DHCP Server in SONiC to assign IPs based on interface index.

Port-based DHCP Server has below advantages:

1. Relatively more secure and stable, if other no-configured interface requests IP, it will not be assigned.
2. Assigning IP based on port can quickly complete a self-made network without external information input.

## Functional Requirements
1. SONiC built-in DHCP Server.
2. Rules to assign IPs based on physical ports.

## Configuration and Management Requirements
Configuration of DHCP server feature can be done via:
* JSON config input
* SONiC CLI

# Design
## Design Overview
We use kea-dhcp-server to reply DHCP request packet. kea-dhcp-server natively supports to assign IPs by mac or contents in DHCP packet (like client id or other options), but in our scenario kea-dhcp-server need to know which interface this packet come from. And SONiC has integrated dhcrelay, which can add interface information to option82 in packet when it relay DHCP packet. So we use it to add interface information.

<div align="center"> <img src=images/overview_kea.png width=570 /> </div>

In our design, dhcp_relay container works on host network mode as before. And dhcp_server container works on bridge network mode, means that it can communicate with switch network only via eth0.

For broadcast packet (discover, request) sent by client, obviously it would be routed to the related DHCP interface. For unicast packet (release), client will get server IP from Option 54 (server identifier) in DHCP reply packet receivced previously. But in our scenario, server identifier is the ip of `eth0` inside dhcp_server container (240.127.1.2), packet with this destination IP cannot be routed successfully. So we need to specify that kea-dhcp-server replies DHCP request with Option 54 filled with IP of DHCP interface (which is the downstream interface IP of dhcrelay), to let client take relay as server and send unicast packet to relay, and relay would transfer this packet to the real server.

Belows are sample configurations for dhcrelay and kea-dhcp-server:

- dhcprelay:
  ```CMD
  ./dhcrelay -d -m discard -a %h:%p %P --name-alias-map-file /tmp/port-name-alias-map.txt -id Vlan1000 -iu docker0 240.127.1.2
  ```

- kea-dhcp-server
  ```JSON
  {
    "Dhcp4": {
      ...
      "interfaces-config": {
        // Listen on eth0
        "interfaces": ["eth0"]
      },
      "client-classes": [
          {
              // Check sub-options of option82, if circuit-id equals to "hostname:etp1",
              // tag it as "hostname-etp1"
              "name": "hostname-etp1",
              "test": "relay4[1].hex == 'hostname:etp1'"
          }
      ],
      "subnet4": [
        {
          "subnet": "192.168.0.0/24",
          "pools": [
            {
              // Assign ip from this pool for packet tagged as "hostname-etp1"
              "pool": "192.168.0.1 - 192.168.0.1",
              "client-class": "hostname-etp1"
            }
          ]
        }
      ]
      ...
    }
  }
  ```

## Container
A new container dhcp_server based on debian:bookworm, is created to hold DHCP Server logic.

## DHCP Server Daemon
### Generate Config

DhcpServd is to generate configuration file for kea-dhcp-server while DHCP Server config in CONFIG_DB changed, and then send SIGHUP signal to kea-dhcp-server process to let new config take affect.
<div align="center"> <img src=images/dhcp_server_block_new_diagram.png width=530 /> </div>

### Update Lease

kea-dhcp-server supports to specify a customize script (`/tmp/lease_update.sh`) to execute whenever a new DHCP lease is created, or an old one destroyed. We use this script to send signal to DhcpServd to read lease file and update lease table in STATE_DB.
<div align="center"> <img src=images/lease_update_flow_diagram.png width=380 /> </div>

```JSON
{
  "Dhcp4": {
    "hooks-libraries": [
      {
          "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_run_script.so",
          "parameters": {
              "name": "/tmp/lease_update.sh",
              "sync": false
          }
      }
    ]
  }
}
```

## Customize DHCP Packet Options

We can customize DHCP Packet options per DHCP interface by kea-dhcp-server. 

We can set customized options for each DHCP interface, all DHCP clients connected to this interface share one configuration, and DHCP server would add DHCP options by config to each DHCP packet sent to client.
```JSON
{
  "Dhcp4": {
    "subnet4": [
      {
        "option-data": [
            {
                "code": 223,
                "data": "'1,1,1,1,1,1,,1,1,1,1,1'",
                "always-send": true
            }
        ],
      }
    ]
  }
}
```
Have to be aware of is that below options are not supported to customize, because they are specified by other config or they are critical options.
| Option code             | Name                        |
|--------------------------|----------------------------------|
| 1                      | Subnet Mask      |
| 3                      | Router           |
| 51                      | Lease Time      |
| 53                      | Message Type           |
| 54                      | DHCP Server ID      |

Currently support text, ipv4-address, uint8, uint16, uint32.

## DB Changes
We have two mainly DB changes:
- Configuration tables for the DHCP server entries.
- State tables for the DHCP server lease entries.

### Config DB
Following table changes would be added in Config DB, including **DHCP_SERVER_IPV4** table, **DHCP_SERVER_IPV4_RANGE** table, **DHCP_SERVER_IPV4_PORT** table and **DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS** table.

These new tables are introduced to specify configuration of DHCP Server.

Below is the sample:
<div align="center"> <img src=images/config_example.png width=530 /> </div>

#### Yang Model
[[yang][dhcp_server] Add dhcp_server_ipv4 yang model](https://github.com/sonic-net/sonic-buildimage/pull/15955)
```yang
module sonic-dhcp-server-ipv4 {
    yang-version 1.1;
    namespace "http://github.com/sonic-net/sonic-dhcp-server-ipv4";
    prefix dhcp-server-ipv4;
    import ietf-inet-types {
        prefix inet;
    }
    import sonic-vlan {
        prefix vlan;
    }
    import sonic-port {
        prefix port;
    }
    import sonic-portchannel {
        prefix lag;
    }
    description "DHCP_SERVER_IPV4 YANG module for SONiC OS";
    revision 2023-07-19 {
        description "Initial version";
    }
    container sonic-dhcp-server-ipv4 {
        container DHCP_SERVER_IPV4 {
            description "DHCP_SERVER_IPV4 part of config_db.json";
            list DHCP_SERVER_IPV4_LIST {
                description "DHCP_SERVER_IPV4 list part of config_db.json";
                key "name";
                leaf name {
                    description "Interface name for DHCP server";
                    type leafref {
                        path "/vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name";
                    }
                }
                leaf gateway {
                    description "Gateway IP for DHCP server";
                    mandatory true;
                    type inet:ipv4-address;
                }
                leaf lease_time {
                    description "Lease time of DHCP IP";
                    mandatory true;
                    type uint32 {
                        range "1..4294967295";
                    }
                }
                leaf mode {
                    description "Mode of assigning IP";
                    mandatory true;
                    type string {
                        pattern "PORT" {
                            error-message "Invalid mode for DHCP server";
                            error-app-tag dhcp-server-mode-invalid;
                        }
                    }
                }
                leaf netmask {
                    description "Subnet mask value for DHCP server";
                    mandatory true;
                    type inet:ipv4-address-no-zone;
                }
                leaf-list customized_options {
                    description "Customized options list";
                    type leafref {
                        path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS/dhcp-server-ipv4:DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS_LIST/dhcp-server-ipv4:name";
                    }
                }
                leaf state {
                    description "State of DHCP server";
                    mandatory true;
                    type enumeration {
                        enum enabled;
                        enum disabled;
                    }
                }
            }
            /* end of DHCP_SERVER_IPV4_LIST */
        }
        /* end of DHCP_SERVER_IPV4 container */
        container DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS {
            description "DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS part of config_db.json";
            list DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS_LIST {
                description "DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS list part of config_db.json";
                key "name";
                leaf name {
                    description "Name of customized option";
                    type string {
                        length 1..255 {
                            error-message "Invalid length for the customized options name";
                        }
                    }
                }
                leaf id {
                    description "Customized PortChannel0003option ID";
                    mandatory true;
                    type uint8 {
                        range "1..254";
                    }
                }
                leaf type {
                    description "Type of customized option";
                    mandatory true;
                    type enumeration {
                        enum text;
                        enum ipv4-address;
                        enum uint8;
                        enum uint16;
                        enum uint32;
                        enum uint64;
                    }
                }
                leaf value {
                    description "Value of customized option";
                    mandatory true;
                    type union {
                        type string {
                            length 0..255;
                        }
                        type inet:ipv4-address;
                        type uint8;
                        type uint16;
                        type uint32;
                        type uint64;
                    }
                }
            }
            /* end of DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS_LIST */
        }
        /* end of DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS container */
        container DHCP_SERVER_IPV4_RANGE {
            description "DHCP_SERVER_IPV4_RANGE part of config_db.json";
            list DHCP_SERVER_IPV4_RANGE_LIST {
                description "DHCP_SERVER_IPV4_RANGE list part of config_db.json";
                key "name";
                leaf name {
                    description "Name of IP range";
                    type string {
                        length 1..255 {
                            error-message "Invalid length for the IP range name";
                        }
                    }
                }
                leaf-list ranges {
                    description "Range of IPs";
                    type inet:ipv4-address;
                }
                must "((count(ranges) <= 2) and (count(ranges) >= 1))";
            }
            /* end of DHCP_SERVER_IPV4_RANGE_LIST */
        }
        /* end of DHCP_SERVER_IPV4_RANGE */
        container DHCP_SERVER_IPV4_PORT {
            description "DHCP_SERVER_IPV4_PORT part of config_db.json";
            list DHCP_SERVER_IPV4_PORT_LIST {
                description "DHCP_SERVER_IPV4_PORT list part of config_db.json";
                key "vlan port";
                leaf vlan {
                    description "Name of vlan";
                    type leafref {
                      path "/vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name";
                    }
                }
                leaf port {
                    description "Interface under vlan";
                    type union {
                      type leafref {
                        path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                      }
                      type leafref {
                        path "/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name";
                      }
                    }
				        }
                leaf-list ips {
                    description "Assigned IPs";
                    must "(not(boolean(../ranges)))"{
                        error-message "Statement of 'ip' and 'ranges' cannot both exist";
                    }
                    type inet:ipv4-address;
                }
                leaf-list ranges {
                    description "IP ranges";
                    must "(not(boolean(../ip)))"{
                        error-message "Statement of 'ip' and 'ranges' cannot both exist";
                    }
                    type leafref {
                        path "/dhcp-server-ipv4:sonic-dhcp-server-ipv4/dhcp-server-ipv4:DHCP_SERVER_IPV4_RANGE/dhcp-server-ipv4:DHCP_SERVER_IPV4_RANGE_LIST/dhcp-server-ipv4:name";
                    }
                }
            }
            /* end of DHCP_SERVER_IPV4_PORT_LIST */
        }
        /* end of DHCP_SERVER_IPV4_PORT container */
    }
}
```

#### DB Objects
```JSON
{
  "DHCP_SERVER_IPV4": {
      "Vlan100": {
          "gateway": "100.1.1.1",
          "lease_time": "3600",
          "mode": "PORT",
          "netmask": "255.255.255.0",
          "customized_options": [
              "option60"
          ],
          "state": "enabled"
      }
  },
  "DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS": {
      "option60": {
          "id": "60",
          "type": "text",
          "value": "dummy_value"
      }
  },
  "DHCP_SERVER_IPV4_RANGE": {
      "range1": {
          "ranges": [
              "100.1.1.3",
              "100.1.1.5"
          ]
      }
  },
  "DHCP_SERVER_IPV4_PORT": {
      "Vlan100|PortChannel0003": {
          "ips": [
              "100.1.1.10"
          ]
      },
      "Vlan100|PortChannel2": {
          "ranges": [
              "range1"
          ]
      }
  }
}
```

### State DB
Following table changes would be added in State DB, including table and **DHCP_SERVER_IPV4_LEASE** table.

These new tables are introduced to count different type of DHCP packet and record lease information.

#### Yang Model
```yang
module sonic-dhcp-server-ipv4 {
  import ietf-inet-types {
        prefix inet;
  }
  container sonic-dhcp-server-ipv4 {
    container DHCP_SERVER_IPV4_LEASE {
      description "DHCP_SERVER_IPV4_LEASE part of state_db";
      list DHCP_SERVER_IPV4_LEASE_LIST {
        key "name";
        leaf name {
          type string;
        }
        leaf lease_start {
          description "Unix time of lease start";
          type uint64
        },
        leaf lease_end {
          description "Unix time of lease end";
          type uint64
        }
        leaf ip {
          description "DHCP ip address assigned to this client";
          type inet:ipv4-address
        }
      }
    }
    /* end of container DHCP_SERVER_IPV4_LEASE */
  }
  /* end of container sonic-dhcp-server-ipv4 */
}
```

#### DB Objects
```JSON
{
  "DHCP_SERVER_IPV4_LEASE": {
    "Vlan1000|10:70:fd:b6:13:00": {
      "lease_start": "1677640581", // Start time of lease, unix time
      "lease_end": "1677641481", // End time of lease
      "ip": "192.168.0.1"
    },
    "Vlan1000|10:70:fd:b6:13:01": {
      "lease_start": "1677640581",
      "lease_end": "1677641481",
      "ip": "192.168.0.2"
    }
  }
}
```

## Flow Diagrams
### DHCP Server Flow
This sequence figure describe the work flow for reply DHCP packet.
<div align="center"> <img src=images/server_flow.png width=500 /> </div>

### Config Change Flow
This sequence figure describe the work flow for config_db changed CLI.
<div align="center"> <img src=images/config_change_new_flow.png width=600 /> </div>
<div align="center"> <img src=images/config_change_new_flow_vlan.png width=680 /> </div>

### Lease Update Flow
Below sequence figure describes the work flow how kea-dhcp-server updates lease table while new lease is created.

<div align="center"> <img src=images/lease_update_flow_new.png width=480 /> </div>

# CLI
* config CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 (add \| del \| update) | Add or delete or update DHCP server config |
  | config dhcp_server ipv4 (enable \| disable) | Enable or disable in DHCP server |
  | config dhcp_server ipv4 range (add \| del) | Add or delete DHCP server ip range |
  | config dhcp_server ipv4 ip (bind \| unbind) | Bind or unbind DHCP server with ip or range |
  | config dhcp_server ipv4 option (add \| del) | Add or delete customized DHCP option |
  | config dhcp_server ipv4 option (bind \| unbind) | Bind or unbind DHCP server with option |

* show CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | show dhcp_server ipv4 info | Show DHCP server config |
  | show dhcp_server range | Show ip range |
  | show dhcp_server option | Show customized DHCP options |
  | show dhcp_server lease | Show lease information of DHCP server |

## Config CLI
**config dhcp_server add**

This command is used to add dhcp_server for DHCP interface.

**Notice**: Adding dhcp_server would enable dhcp_server feature automatically, it require that dhcp_relay feature is disabled.
- Usage
  ```
  config dhcp_server ipv4 add [--mode <mode>] [--infer_gw_nm] [--lease_time <lease_time>] [--gateway <gateway>] [--netmask <netmask>] <dhcp_interface>

  Options:
     mode: Specify mode of assign IP, currently only support 'PORT'. [required]
     lease_time: Time that the client can lease IP once. [not required, default value is 900(s)]
     infer_gw_nm: Indicate whether to use gateway and netmask of server interface. [not required if gateway and netmask is given]
     gateway: Gateway of DHCP server. [ignored if infer_gw_nm is given]
     netmask: Netmask of DHCP server. [ignored if infer_gw_nm is given]
  ```

- Example
  ```
  config dhcp_server ipv4 add --mode PORT --infer_gw_nm --lease_time 300 Vlan1000
  config dhcp_server ipv4 add --mode PORT --lease_time 300 --gateway 192.168.0.1 --netmask 255.255.255.0 Vlan1000
  ```

**config dhcp_server del**

This command is used to delete all dhcp_server config for DHCP interface.
- Usage
  ```
  config dhcp_server ipv4 del <dhcp_interface>
  ```

- Example
  ```
  config dhcp_server ipv4 del Vlan1000
  ```

**config dhcp_server enable/disable**

This command is used to enable or disable dhcp_server for DHCP interface.
- Usage
  ```
  config dhcp_server ipv4 (enable | disable) <dhcp_interface>
  ```

- Example
  ```
  config dhcp_server ipv4 enable Vlan1000
  ```


**config dhcp_server update**

This command is used to update dhcp_server config.
- Usage
  ```
  config dhcp_server ipv4 update [--mode <mode>] [--infer_gw_nm] [--lease_time <lease_time>] [--gateway <gateway>] [--netmask <netmask>] <dhcp_interface>
  ```

- Example
  ```
  config dhcp_server ipv4 update --mode PORT --infer_gw_nm --lease_time 300 Vlan1000
  ```

**config dhcp_server range add/del**

This command is used to config ip range.
- Usage
  ```
  # <ip_end> is not required, if not given, means ip_end is equal to ip_start
  config dhcp_server ipv4 range add <range_name> <ip_start> [<ip_end>]
  config dhcp_server ipv4 range del <range_name>
  ```

- Example
  ```
  config dhcp_server ipv4 range add range1 192.168.0.1

  config dhcp_server ipv4 range del range1
  ```

**config dhcp_server ip bind/unbind**

This command is used to config dhcp ip per interface.
- Usage
  ```
  config dhcp_server ipv4 ip bind [<vlan_interface>] <interface> (<ip_range_list> | <ip_list>)
  config dhcp_server ipv4 ip unbind [<vlan_interface>] <interface> (<ip_range_list> | <ip_list> | all)
  ```

- Example
  ```
  config dhcp_server ipv4 ip bind Vlan1000 Ethernet1 range1
  config dhcp_server ipv4 ip bind Vlan1000 Ethernet2 192.168.0.5 192.168.0.6
  config dhcp_server ipv4 ip unbind Vlan1000 Ethernet1 range1 range1
  ```

**config dhcp_server option add**

This command is used to add dhcp option.
Type field can refer to [Customize DHCP Packet Options](#customize-dhcp-packet-options).

- Usage
  ```
  config dhcp_server ipv4 option add <option_name> <option_id> <type> <value>
  ```

- Example
  ```
  config dhcp_server ipv4 option add option_1 12 text host_1
  ```

**config dhcp_server option del**

This command is used to del dhcp option.

- Usage
  ```
  config dhcp_server ipv4 option del <option_name> (<option_id> <type> <value> | all)
  ```

- Example
  ```
  config dhcp_server ipv4 option del option_1 12 text host_1
  config dhcp_server ipv4 option del option_1
  ```

**config dhcp_server option bind**

This command is used to bind dhcp option per dhcp interface.
- Usage
  ```
  config dhcp_server ipv4 option bind <dhcp_interface> <option_list>
  ```

- Example
  ```
  config dhcp_server ipv4 option bind Vlan1000 option_1
  ```

**config dhcp_server option unbind**

This command is used to unbind dhcp option.
- Usage
  ```
  config dhcp_server ipv4 option unbind <dhcp_interface> (all | <option_name>)
  ```

- Exampe
  ```
  config dhcp_server ipv4 option unbind Vlan1000 all

  config dhcp_server ipv4 option unbind Vlan1000 option_1
  ```

## Show CLI
**show dhcp_server info**

This command is used to show dhcp_server config.
- Usage
  ```
  show dhcp_server ipv4 info [--with_customize_option] [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 info Vlan1000
  +-----------+-----+------------+--------------+--------------+---------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Bind  |
  |-----------+-----+------------+--------------+----------- --+---------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |range_1  |
  |           |     |            |              |              |range_2  |
  |           |     |            |              |              |range_3  |
  +-----------+-----+------------+--------------+--------------+---------+

  show dhcp_server ipv4 info --with_customize_option Vlan1000
  +-----------+-----+------------+--------------+--------------+---------+-----------------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Bind  |Customize Option |
  |-----------+-----+------------+--------------+----------- --+---------+-----------------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |range_1  |option_1         |
  |           |     |            |              |              |range_2  |option_2         |
  |           |     |            |              |              |range_3  |                 |
  +-----------+-----+------------+--------------+--------------+---------+-----------------+

  show dhcp_server ipv4 info
  +-----------+-----+------------+--------------+--------------+------------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Bind     |
  |-----------+-----+------------+--------------+----------- --+------------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |range_1     |
  |           |     |            |              |              |range_2     |
  |           |     |            |              |              |range_3     |
  +-----------+-----+------------+--------------+--------------+------------+
  |Vlan2000   |PORT |192.168.1.1 |255.255.255.0 |180           |192.168.1.2 |
  +-----------+-----+------------+--------------+--------------+------------+
  ```

**show dhcp_server range**

This command is used to show dhcp_server ip range.
- Usage
  ```
  show dhcp_server ipv4 range [<range_name>]
  ```

- Example
  ```
  show dhcp_server ipv4 range range_1
  +-------------+-------------+-------------+---------+
  |IP Range Name |IP Start     |IP End       |IP count |
  |--------------+-------------+-------------+---------+
  |range_1        |192.168.0.5  |192.168.0.10 |6        |
  +--------------+-------------+-------------+---------+

  show dhcp_server ipv4 range
  +--------------+-------------+-------------+---------+
  |IP Range Name |IP Start     |IP End       |IP count |
  |--------------+-------------+-------------+---------+
  |range_1        |192.168.0.5  |192.168.0.10 |6        |
  +--------------+-------------+-------------+---------+
  |range_2        |192.168.0.20 |192.168.0.30 |11       |
  +--------------+-------------+-------------+---------+
  ```

**show dhcp_server option**

This command is used to show dhcp_server customized option.

- Usage
  ```
  show dhcp_server ipv4 option [<option_name>]
  ```

- Example
  ```
  show dhcp_server ipv4 option option_1
  +-------------+-------+------------+------------+
  |Option Name  |Option |Value       |Type        |
  |-------------+-------+------------+------------+
  |option_1     |12     |host_1      |text        |
  +-------------+-------+------------+------------+

  show dhcp_server ipv4 option
  +-------------+-------+------------+------------+
  |Option Name  |Option |Value       |Type        |
  |-------------+-------+------------+------------+
  |option_1     |12     |host_1      |text        |
  +-------------+-------+------------+------------+
  |option_2     |60     |host_1      |text        |
  +-------------+-------+------------+------------+
  ```

**show dhcp_server lease**

This command is used to show dhcp_server lease.
- Usage
  ```
  show dhcp_server ipv4 lease [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 lease Vlan1000
  +-----------+------------------+------------+--------------------+--------------------+
  |Interface  |MAC Address       |IP          |Lease Start         |Lease End           |
  |-----------+------------------+------------+--------------------+--------------------+
  |Vlan1000   |2c:2c:2c:2c:2c:2c |192.168.0.2 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  |           |2b:2b:2b:2b:2b:2b |192.168.0.3 |2023-02-02 10:20:00 |2023-02-02 10:35:00 |
  +-----------+------------------+------------+--------------------+--------------------+

  show dhcp_server ipv4 lease
  +-----------+------------------+------------+--------------------+--------------------+
  |Interface  |MAC Address       |IP          |Lease Start         |Lease End           |
  +-----------+------------------+------------+--------------------+--------------------+
  |Vlan1000   |2c:2c:2c:2c:2c:2c |192.168.0.2 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  |           |2b:2b:2b:2b:2b:2b |192.168.0.3 |2023-02-02 10:20:00 |2023-02-02 10:35:00 |
  +-----------+------------------+------------+--------------------+--------------------+
  |Vlan1001   |2e:2e:2e:2e:2e:2e |192.168.8.2 |2023-02-02 09:00:00 |2023-02-02 09:15:00 |
  +-----------+------------------+------------+--------------------+--------------------+

# Test
## Unit Test
The Unit test case are as below:
| No |                Test case summary                          |
|:----------------------|:-----------------------------------------------------------|
| 1 | Verify that config add/del/update dhcp_server can work well |
| 2 | Verify that config dhcp_server ip bind/unbind can work well |
| 3 | Verify that config dhcp_server option can work well |
| 4 | Verify that config dhcp_server range can work well|
| 5 | Verify that show dhcp_server info can work well |
| 6 | Verify that show dhcp_server lease can work well |
| 7 | Verify that lease update script can work well |
| 8 | Verify that config files for kea-dhcp-server and dhcrelay generated by DhcpServd are correct |

## Test Plan
Test plan will be published in [sonic-net/sonic-mgmt](https://github.com/sonic-net/sonic-mgmt)

# Implement Detail

|Step|Status|
|:-------------|:---|
|Publish HLD|https://github.com/sonic-net/SONiC/pull/1282 (Open)|
|Add yang model in **sonic-buildimage**|https://github.com/sonic-net/sonic-buildimage/pull/15955 (Draft)|
|Add dhcp_server docker container in **sonic-buildimage**|In progress|
|Implement DhcpServd in **sonic-buildimage**|To be done|
|Add support for dhcp_server in minigraph parser in **sonic-buildimage**|To be done||
|Enhance dhcp_relay container to support dhcp_server in **sonic-buildimage**|To be done|
|Add cli in **sonic-buildimage**/**sonic-utilities**|To be done|
|Public test plan in **sonic-mgmt**|To be done|
|Implement test plan in **sonic-mgmt**|To be done|
