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
    - [DHCP Server Bridge](#dhcp-server-bridge)
        - [Hook and Modify Packet](#hook-and-modify-packet)
        - [Dependency Libraries](#dependency-libraries)
    - [DhcpMgr Daemon](#dhcpmgr-daemon)
        - [Generate Config](#generate-config)
        - [Update Lease](#update-lease)
    - [DhcpServ Monitor](#dhcpserv-monitor)
    - [Customize DHCP Packet Options](#customize-dhcp-packet-options)
    - [DB Changes](#db-changes)
        - [Config DB](#config-db)
            - [Yang Model](#yang-model)
            - [DB Objects](#db-objects)
        - [State DB](#state-db)
            - [Yang Model](#yang-model)
            - [DB Objects](#db-objects)
    - [Flow Diagrams](#flow-diagrams)
        - [Config Change Flow](#config-change-flow)
        - [Lease Update Flow](#lease-update-flow)
- [CLI](#cli)
    - [Config CLI](#config-cli)
    - [Show CLI](#show-cli)
- [Test](#test)
    - [Unit Test](#unit-test)
    - [Test Plan](#test-plan)

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
| eBPF| extended Berkeley Packet Filter |

###### Table 2: Definitions
| Definitions             | Description                        |
|--------------------------|----------------------------------|
| dnsmasq                      | A lightweight DHCP and caching DNS server      |
| dhcrelay | DHCP relay |

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
We use dnsmasq to reply dhcp request packet. Dnsmasq natively supports mac-based ip assign, but in our scenario dnsmasq need to know which interface this packet come from. And SONiC has integrated dhcrelay, which can add interface information to option82 in packet when it relay DHCP packet. So we use it to add interface information. But we will encounter 2 problems in this scenario:

1. Original dnsmasq and dhcrelay listen to same interface and same UDP port(67), which would cause port conflict.

2. dhcrelay is not supported loopback relay.

So we introduce DHCP Server Bridge(implemented by eBPF) to modify DHCP packet contents, including UDP ports, DHCP related information.

<div align="center"> <img src=images/ebpf_dhcp_high_level.png width=570 /> </div>

## DHCP Server Bridge
eBPF (extended Berkeley Packet Filter) can run sandboxed programs in a privileged context such as in kernel space. We use eBPF program to implement DHCP Server bridge to connect loopback dnsmasq and dhcrelay.

### Hook and Modify Packet

We introduce eBPF to resolve conflict of dnsmasq and dhcrelay working on same machine.

<div align="center"> <img src=images/ebpf_flow.png width=650 /> </div>

For problem 1, it's easy to change listening port for dnsmasq by itself configuration. But it's no convenient to change relay port for dhcrelay. So we use port 67 as listen and relay port for dhcrelay, and use another port (like 10067) as listen port for dnsmasq. In this setting, origin UDP ports in packets between dnsmasq and dhcrelay is like bellow:
| Direction      | UDP source port|UDP destination port|
|--------------------------|--|----|
| dhcrelay to dnsmasq|67| 67 |
| dnsmasq to dhcrelay|10067| 10067 |

In this scenario, they cannot communicate with each other. DHCP server bridge will modify packet UDP port, for packet from dhcrelay to dnsmasq, the UDP port will be modified from 67 to 10067 and for dnsmasq to dhcrelay, the UDP port will be modified from 10067 to 67.

For problem 2, we chose `docker0` as upstream interface of dhcrelay and use eBPF to modify DHCP relay packet from dnsmasq to make it looks like not a loopback DHCP server, and redirect these packet to ingress queue of docker0.

Belows are samples.
```
./dhcrelay -d -m discard -a %h:%p %P --name-alias-map-file /tmp/port-name-alias-map.txt -id Vlan1000 -iu docker0 192.168.0.1
```
dhcrelay listens on port 67, upstream interface of it is docker0 (We need a interface which would not request dhcp ip to be upstream interface), and downtream interface of it is Vlan1000, server ip is ip of Vlan1000. This config will make dhcrelay to relay dhcp packet between Vlan1000 and docker0.
```
bind-interfaces
interface=Vlan1000
dhcp-alternate-port=10067
dhcp-circuitid=set:etp6,"hostname:etp6"
dhcp-range=tag:etp6,192.168.0.5,192.168.0.5,255.255.255.0
```
dnsmasq listens on port 10067, and downstream of it is Vlan1000, it will assign ip by circuit id in option 82. This config will make it reply relayed DHCP request packet from Vlan1000.
<div align="center"> <img src=images/ebpf.png width=670 /> </div>

1. dhcrelay receive DHCP request and relay it to server. Because we have set server ip as it self, so the relayed packet would be sent from <b>lo</b> interface. The dst and src UDP port of this packet both are 67.

2. DHCP server bridge is hooking in ergress queue of interface `lo`, modify the dst and src UDP to 10067, and not do anything else to this packet.

3. dnsmasq recevie this relayed request packet, and send reply packet from <b>lo</b> intferface. The dst and src UDP port of this packet both are 10067.

4. DHCP server bridge modify the dst and src UDP port and some other contents. And redirect this packet to ingress queue of <b>docker0</b>

5. dhcrelay capture the DHCP reply packet in docker0 and would send relayed reply packet to client.

### Dependency Libraries

apt-get install libbpfcc libbpf-dev bpftool

## DhcpMgr Daemon
### Generate Config

For each dhcp interface, a dnsmasq process and an dhcrelay process are started. DhcpMgrd is to manager these processes (start/kill/restart) when configuration in config_db is changed.
<div align="center"> <img src=images/dhcp_server_block_new_diagram.png width=530 /> </div>

### Update Lease

Dnsmasq supports to specify a customize script to execute whenever a new DHCP lease is created, or an old one destroyed. We use this script to send signal to DhcpMgrd to read lease file and update lease table in STATE_DB.
<div align="center"> <img src=images/lease_update_flow_diagram.png width=380 /> </div>

## DhcpServ Monitor

If we enable a new DHCP interface, we should interface config of dnsmasq and dhcrelay, it requires process restart. In order to avoid affecting the existing DHCP interface, we will start another couple of dnsmasq and dhcrelay process. For this reason, we need a monitor process DhcpServMon to regularly check whether processes running status consistent with CONFIG_DB.

## Customize DHCP Packet Options

We can customize DHCP Packet options per DHCP interface by dnsmasq. 

We can set tag for each DHCP interface, all DHCP clients connected to this interface share one tag, and DHCP server would add DHCP options by config to each DHCP packet sent to client. Have to be aware of is that below options are not supported to customize, because they are specified by other config or they are critical options.
| Option code             | Name                        |
|--------------------------|----------------------------------|
| 1                      | Subnet Mask      |
| 3                      | Router           |
| 51                      | Lease Time      |
| 53                      | Message Type           |
| 54                      | DHCP Server ID      |

Currently only support text, ipv4-address.

## DB Changes
We have two mainly DB changes:
- Configuration tables for the DHCP server entries.
- State tables for the DHCP server lease entries.

### Config DB
Following table changes would be added in Config DB, including **DHCP_SERVER_IPV4** table, **DHCP_SERVER_IPV4_POOL** table, **DHCP_SERVER_IPV4_PORT** table and **DHCP_SERVER_IPV4_CUSTOMIZE_OPTION** table.

These new tables are introduced to specify configuration of DHCP Server.

Below is the sample:
<div align="center"> <img src=images/config_example.png width=530 /> </div>

#### Yang Model
```yang
module sonic-dhcp-server-ipv4 {
  import ietf-inet-types {
        prefix inet;
  }
  container sonic-dhcp-server-ipv4 {
    container DHCP_SERVER_IPV4 {
      description "DHCP_SERVER_IPV4 part of config_db.json";
      list DHCP_SERVER_IPV4_LIST {
        key "name";
        leaf name {
          type string;
        }
        leaf gateway {
          description "Gateway of the DHCP server";
          type inet:ipv4-address;
        }
        leaf lease_time {
          description "Lease time of client for this DHCP server";
          type uint16;
        }
        leaf mode {
          description "Mode of assigning IP address";
          type string;
        }
        leaf netmask {
          description "Netmask of this DHCP server";
          type inet:ipv4-address;
        }
        leaf customize_options {
          description "Customize DHCP options";
          type string;
        }
        leaf state {
          description "Enable DHCP server for this interface or not";
          type string;
        }
      }
    }
    /* end of container DHCP_SERVER_IPV4 */
    container DHCP_SERVER_IPV4_POOL {
      description "DHCP_SERVER_IPV4_IP_RANGE part of config_db.json";
      list DHCP_SERVER_IPV4_IP_RANGE_LIST {
        key "name";
        leaf name {
          type string;
        }
        leaf ip_start {
          description "Start ip";
          type inet:ipv4-address;
        }
        leaf ip_end {
          description "End ip";
          type inet:ipv4-address;
        }
      }
    }
    /* end of container DHCP_SERVER_IPV4_POOL */
    container DHCP_SERVER_IPV4_PORT {
      description "DHCP_SERVER_IPV4_PORT part of config_db.json";
      list PORT_LIST {
        key "name";
        leaf name {
          type string;
        }
        list IP_RANGE_LIST {
          description "List of IP range";
          key "name";
          leaf name {
            type string;
            description "Option name";
          }
        }
      }
    }
    /* end of container DHCP_SERVER_IPV4_PORT */
  }
  container DHCP_SERVER_IPV4_CUSTOMIZE_OPTION {
    description "DHCP_SERVER_IPV4_OPTION part of config_db.json";
    list OPTION_LIST {
      key "name";
      leaf name {
        type string;
      }
      leaf id {
        description "Option ID";
        type uint8;
      }
      leaf value {
        description "Option value";
        type string;
      }
      leaf type {
        description "Type of option value";
        type string;
      }
    }
  }
  /* end of container sonic-dhcp-server-ipv4 */
}
```

#### DB Objects
```JSON
{
  "DHCP_SERVER_IPV4": {
    "Vlan1000": {
      "gateway": "192.168.0.1", // server ip
      "lease_time": "180", // lease time
      "mode": "PORT", // in this mode, server will assign ip by port index
      "netmask": "255.255.255.0",
      "customize_options": [
        "option12", // refer to DHCP_SERVER_IPV4_CUSTOMIZE_OPTION
        "option60"
      ],
      "state": "enable"
    },
  },
  "DHCP_SERVER_IPV4_CUSTOMIZE_OPTION": {
    "option12": { // Option 12 setting
      "id": 12,
      "value": "host_1",  // option value
      "type": "text" // option type
    },
    "option60": { // Option 60 setting
      "id": 60,
      "value": "class_1",  // option value
      "type": "text" // option type
    }
  },
  "DHCP_SERVER_IPV4_POOL": {
    "range1": {
      "ip_start": "192.168.0.2", //This range only contains 3 IPs, 192.168.0.2
      "ip_end": "192.168.0.4"    // 192.168.0.3 and 192.168.0.4
    },
    "range2": {
      "ip_start": "192.168.0.5",
      "ip_end": "192.168.0.5"
    },
    "range3": {
      "ip_start": "192.168.1.6",
      "ip_end": "192.168.1.6"
    },
    "range4": {
      "ip_start": "192.168.1.7",
      "ip_end": "192.168.1.7"
    },
    "range5": {
      "ip_start": "192.168.0.9",
      "ip_end": "192.168.0.9"
    }
  },
  "DHCP_SERVER_IPV4_PORT": {
    "Vlan1000|Ethernet1": [
      "range1",
      "range2"
    ],
    "Vlan1000|Ethernet2": [
      "range3"
    ]
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
### Config Change Flow
This sequence figure describe the work flow for config_db changed CLI.
<div align="center"> <img src=images/config_change_new_flow.png width=600 /> </div>

### Lease Update Flow
Below sequence figure describes the work flow how dnsmasq updates lease table while new lease is created.

<div align="center"> <img src=images/lease_update_flow_new.png width=430 /> </div>

# CLI
* config CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | config dhcp_server ipv4 (add \| del \| update) | Add or delete or update DHCP server config |
  | config dhcp_server ipv4 (enable \| disable) | Enable or disable in DHCP server |
  | config dhcp_server ipv4 pool (add \| del) | Add or delete DHCP server ip pool |
  | config dhcp_server ipv4 pool (bind \| unbind) | Bind or unbind DHCP server with ip pool |
  | config dhcp_server ipv4 option (add \| del) | Add or delete customized DHCP option |
  | config dhcp_server ipv4 option (bind \| unbind) | Bind or unbind DHCP server with option |

* show CLI
  | CLI |               Description                        |
  |:----------------------|:-----------------------------------------------------------|
  | show dhcp_server ipv4 info | Show DHCP server config |
  | show dhcp_server pool | Show ip pool |
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

**config dhcp_server pool add/del**

This command is used to config ip pool.
- Usage
  ```
  # <ip_end> is not required, if not given, means ip_end is equal to ip_start
  config dhcp_server ipv4 pool add <pool_name> <ip_start> [<ip_end>]
  config dhcp_server ipv4 pool del <pool_name>
  ```

- Example
  ```
  config dhcp_server ipv4 pool add pool1 192.168.0.1

  config dhcp_server ipv4 pool del pool1
  ```

**config dhcp_server pool bind/unbind**

This command is used to config dhcp ip per interface.
- Usage
  ```
  config dhcp_server ipv4 pool bind [<vlan_interface>] <interface> <ip_pool_names>
  config dhcp_server ipv4 pool unbind [<vlan_interface>] (<interface> <ip_pool_names> | all)
  ```

- Example
  ```
  config dhcp_server ipv4 pool bind Vlan1000 Ethernet1 pool1 pool2
  config dhcp_server ipv4 pool unbind Vlan1000 Ethernet1 pool1 pool2
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
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Pools |
  |-----------+-----+------------+--------------+----------- --+---------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |pool_1   |
  |           |     |            |              |              |pool_2   |
  |           |     |            |              |              |pool_3   |
  +-----------+-----+------------+--------------+--------------+---------+

  show dhcp_server ipv4 info --with_customize_option Vlan1000
  +-----------+-----+------------+--------------+--------------+---------+-----------------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Pools |Customize Option |
  |-----------+-----+------------+--------------+----------- --+---------+-----------------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |pool_1   |option_1         |
  |           |     |            |              |              |pool_2   |option_2         |
  |           |     |            |              |              |pool_3   |                 |
  +-----------+-----+------------+--------------+--------------+---------+-----------------+

  show dhcp_server ipv4 info
  +-----------+-----+------------+--------------+--------------+---------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |IP Pools |
  |-----------+-----+------------+--------------+----------- --+---------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |pool_1   |
  |           |     |            |              |              |pool_2   |
  |           |     |            |              |              |pool_3   |
  +-----------+-----+------------+--------------+--------------+---------+
  |Vlan2000   |PORT |192.168.1.1 |255.255.255.0 |180           |pool_4   |
  +-----------+-----+------------+--------------+--------------+---------+
  ```

**show dhcp_server pool**

This command is used to show dhcp_server ip pool.
- Usage
  ```
  show dhcp_server ipv4 pool [<pool_name>]
  ```

- Example
  ```
  show dhcp_server ipv4 pool pool_1
  +-------------+-------------+-------------+---------+
  |IP Pool Name |IP Start     |IP End       |IP count |
  |-------------+-------------+-------------+---------+
  |pool_1       |192.168.0.5  |192.168.0.10 |6        |
  +-------------+-------------+-------------+---------+

  show dhcp_server ipv4 pool
  +-------------+-------------+-------------+---------+
  |IP Pool Name |IP Start     |IP End       |IP count |
  |-------------+-------------+-------------+---------+
  |pool_1       |192.168.0.5  |192.168.0.10 |6        |
  +-------------+-------------+-------------+---------+
  |pool_2       |192.168.0.20 |192.168.0.30 |11       |
  +-------------+-------------+-------------+---------+
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
| 1 | Verify that config add/del dhcp_server can work well |
| 2 | Verify that config dhcp_server info can work well |
| 3 | Verify that config dhcp_server option can work well |
| 4 | Verify that config dhcp_server pool can work well|
| 5 | Verify that show dhcp_server info can work well |
| 6 | Verify that show dhcp_server lease can work well |
| 7 | Verify that lease update script can work well |
| 8 | Verify that config files for dnsmasq and dhcrelay generated by DhcpMgrd are correct |

## Test Plan
Test plan will be published in [sonic-net/sonic-mgmt](https://github.com/sonic-net/sonic-mgmt)
