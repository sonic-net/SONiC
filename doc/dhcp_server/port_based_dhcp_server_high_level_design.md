# IPv4 Port Based DHCP_SERVER in SONiC
# High Level Design Document
**Rev 0.1**

# Table of Contents
- [Port Based DHCP\_SERVER in SONiC](#port-based-dhcp_server-in-sonic)
- [High Level Design Document](#high-level-design-document)
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
          - [Table 1: Abbreviations](#table-1-abbreviations)
- [1 Overview](#1-overview)
  - [1.1 Functional Requirements](#11-functional-requirements)
  - [1.2 Configuration and Management Requirements](#12-configuration-and-management-requirements)
- [2 Design](#2-design)
  - [2.1 Design Overview](#21-design-overview)
  - [2.2 DB Changes](#22-db-changes)
    - [2.2.1 Config DB](#221-config-db)
      - [2.2.1.1 Yang Model](#2211-yang-model)
      - [2.2.1.2 DB Objects](#2212-db-objects)
    - [2.2.2 State DB](#222-state-db)
      - [2.2.2.1 Yang Model](#2221-yang-model)
      - [2.2.2.2 DB Objects](#2222-db-objects)
  - [2.3 eBPF](#23-ebpf)
    - [2.3.1 Hook and Modify Packet](#231-hook-and-modify-packet)
    - [2.3.2 Packet Counter](#232-packet-counter)
    - [2.3.3 Dependency Libraries](#233-dependency-libraries)
  - [2.4 DhcpMgr Daemon](#24-dhcpmgr-daemon)
  - [2.5 DhcpServ Monitor](#25-dhcpserv-monitor)
  - [2.6 Lease Update Script](#26-lease-update-script)
  - [2.7 Customize DHCP Packet Options](#27-customize-dhcp-packet-options)
  - [2.8 dhcrelay Patch](#28-dhcrelay-patch)
  - [2.9 Flow Diagrams](#29-flow-diagrams)
    - [2.9.1 Config Change Flow](#291-config-change-flow)
    - [2.9.2 Lease Update Flow](#292-lease-update-flow)
    - [2.9.3 Count Table Update Flow](#293-count-table-update-flow)
  - [2.10 CLI](#20-cli)
    - [2.10.1 Config CLI](#2101-config-cli)
    - [2.10.2 Show CLI](#2102-show-cli)
    - [2.10.3 Clear CLI](#2103-clear-cli)
- [3 Unit Test](#3-unit-test)

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
We plan to implement built-in DHCP Server in SONiC to assign IPs based on physical port.

Port-based DHCP Server has below advantages:

1. Relatively more secure and stable, if no other configured interface requests IP, it will not be assigned.
2. Assigning IP based on port can quickly complete a self-made network without external information input.

## Functional Requirements
1. SONiC built-in DHCP Server.
2. Rules to assign IPs based on physical ports.
3. Packet counter for debug purpose.

## Configuration and Management Requirements
Configuration of DHCP server feature can be done via:
* JSON config input
* SONiC CLI

# Design
## Design Overview
We use dnsmasq to reply dhcp request packet. Dnsmasq natively supports mac-based ip assign, but in our scenario dnsmasq need to know which interface this packet come from. And SONiC has integrated dhcrelay, which can add interface info to option82 when it relay DHCP packet. So we use it to add interface information. But we will encounter 2 problems in this scenario:

1. Original dnsmasq and dhcrelay listen to same interface and same UDP port(67), which would cause port conflict.

2. dhcrelay is not supported loopback relay.

So we introduce eBPF to modify DHCP packet contents, including UDP ports, DHCP related information.

<div align="center"> <img src=images/ebpf_dhcp_high_level.png width=450 /> </div>

## DHCP Server Bridge
eBPF (extended Berkeley Packet Filter) can run sandboxed programs in a privileged context such as the operating system kernel. We use eBPF program to implement DHCP Server bridge to connect loopback dnsmasq and dhcrelay.

### Hook and Modify Packet

So we introduce eBPF to resolve conflict of dnsmasq and dhcrelay working on same machine.

<div align="center"> <img src=images/ebpf_flow.png width=650 /> </div>

For problem 1, it's easy to change listening port for dnsmasq by itself config. But it's no convenient to change relay port for dhcrelay. So we use port 67 as listen and relay port for dhcrelay, and use another port (like 1067) as listen port for dnsmasq. In this setting, origin UDP ports in packets between dnsmasq and dhcrelay is like bellow:
| Direction      | UDP source port|UDP destination port|
|--------------------------|--|----|
| dhcrelay to dnsmasq|67| 67 |
| dnsmasq to dhcrelay|1067| 1067 |

In this scenario, they cannot communicate with each other. So we use eBPF program to modify packet UDP port, and the result is as below:
| Direction      | UDP source port|UDP destination port|
|--------------------------|--|----|
| dhcrelay to dnsmasq|67| 1067 |
| dnsmasq to dhcrelay|1067| 67 |

For problem 2, we chose `docker0` as upstream interface of dhcrelay and use eBPF to modify DHCP relay packet from dnsmasq to make it looks like not a loopback DHCP server, and redirect these packet to ingress queue of docker0.

Belows are samples.
```
./dhcrelay -d -m discard -a %h:%p %P --name-alias-map-file /tmp/port-name-alias-map.txt -id Vlan1000 -iu docker0 192.168.0.1
```
dhcrelay listens on port 67, upstream interface of it is docker0 (We need a interface which would not request dhcp ip to be upstream interface), and downtream interface of it is Vlan1000, server ip is ip of Vlan1000. This config will make dhcrelay to relay dhcp packet between Vlan1000 and docker0.
```
bind-interfaces
interface=Vlan1000
dhcp-alternate-port=1067
dhcp-circuitid=set:etp6,"hostname:etp6"
dhcp-range=tag:etp6,192.168.0.5,192.168.0.5,255.255.255.0
```
dnsmasq listens on port 1067, and downstream of it is Vlan1000, it will assign ip by circuit id in option 82. This config will make it reply relayed DHCP request packet from Vlan1000.
<div align="center"> <img src=images/ebpf.png width=670 /> </div>

1. dhcrelay receive DHCP request and relay it to server. Because we have set server ip as it self, so the relayed packet would be sent from <b>lo</b> interface. The dst and src UDP port of this packet both are 67.

2. eBPF program is hooking in ergress queue in this interface, modify the dst and src UDP to 1067, and not do anything else to this packet.

3. dnsmasq recevie this relayed request packet, and send reply packet from <b>lo</b> intferface. The dst and src UDP port of this packet both are 1067.

4. eBPF program modify the dst and src UDP port and some other contents. And redirect this packet to ingress queue of <b>docker0</b>

5. dhcrelay capture the dhcp reply packet in docker0 and would send relayed reply packet to client.

### Dependency Libraries

apt-get install libbpfcc libbpf-dev bpftool

## DhcpMgr Daemon
### Generate Config

For each dhcp interface, a dnsmasq process and an dhcrelay process are started. DhcpMgrd is to manager these processes (start/kill/restart) when configuration in config_db is changed.
<div align="center"> <img src=images/dhcp_server_block_new_diagram.png width=530 /> </div>

### Update Lease

Dnsmasq supports to specify a customize script to execute whenever a new DHCP lease is created, or an old one destroyed. We use this script to send signal to DhcpMgrd to read lease file and update lease table in STATE_DB.
<div align="center"> <img src=images/lease_update_flow_diagram.png width=380 /> </div>

### Packet Counter

Because we have 3 scenarios of packet communication (client to dhcrelay, dhcrelay to dhcp server bridge, dhcp server bridge to dnsmasq), if DHCP sever cannot work well, we need to now which link have issue. So we need 3 counters.

<div align="center"> <img src=images/ebpf_counter_all.png width=600 /> </div>

#### Dnsmasq Counter
dnsmasq would log DHCP packet it received or sent like bellow format. From this log, DhcpMgrd can know the mac address of client it communicate to.
```
dnsmasq-dhcp: DHCPDISCOVER(Vlan1000) 192.168.0.5 10:70:fd:b6:13:05
dnsmasq-dhcp: DHCPOFFER(Vlan1000) 192.168.0.5 10:70:fd:b6:13:05
dnsmasq-dhcp: DHCPREQUEST(Vlan1000) 192.168.0.5 10:70:fd:b6:13:05
dnsmasq-dhcp: DHCPACK(Vlan1000) 192.168.0.5 10:70:fd:b6:13:05 ea621e1fe61c
dnsmasq-dhcp: DHCPRELEASE(Vlan1000) 192.168.0.5 10:70:fd:b6:13:05
dnsmasq-dhcp: DHCPDISCOVER(Vlan1000) 10:70:fd:b6:13:06 no address available
```
Below picture describe how DhcpMgrd update related counter table
<div align="center"> <img src=images/dnsmasq_counter_flow.png width=600 /> </div>

#### DHCP Server Bridge Counter

DHCP server bridge is working on interface `lo`, we can use eBPF map (kind of data structure in eBPF program) to count packet receive in kernel space and read it by `bpftool` in user space. And DhcpServd can get counter information via this tool and update counter table in STATE_DB.
```
root@sonic:/usr# bpftool map dump name discover_counter_map | head -n 5
key: 00 00 00 00  value: 00 00 00 00
key: 01 00 00 00  value: 04 00 00 00
key: 02 00 00 00  value: 03 00 00 00
key: 03 00 00 00  value: 00 00 00 00
key: 04 00 00 00  value: 00 00 00 00
```

#### Dhcrelay Counter

eBPF program can hook on `net_dev_queue` and `netif_receive_skb` for all packets send and receive. And filter to get DHCP packet and then update in eBPF map. Further process is similar to DHCP server bridge counter.

## DhcpServ Monitor
We need to start multiple dnsmasq process and dhcrelay for each DHCP interface, so we need a monitor process DhcpServMon to regularly check whether processes running status consistent with CONFIG_DB.

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
- State tables for the DHCP server counter and lease entries.

### Config DB
Following table changes would be added in Config DB, including **DHCP_SERVER_IPV4** table, **DHCP_SERVER_IPV4_PORT** table and **DHCP_SERVER_IPV4_CUSTOMIZE_OPTION** table.

These new tables are introduced to specify configuration of DHCP Server.

In this section, we assume below config:

Ethernet1 and Ethernet2 are in Vlan1000, Ethernet15 and PortChannel1 are not in Vlan1000.
<div align="center"> <img src=images/vlan_sample.png width=400 /> </div>

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
      }
    }
    /* end of container DHCP_SERVER_IPV4 */
    container DHCP_SERVER_IPV4_IP_RANGE {
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
    /* end of container DHCP_SERVER_IPV4_IP_RANGE */
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
      ]
    },
    "Ethernet15": {
      "gateway": "192.168.1.1",
      "lease_time": "180",
      "mode": "PORT",
      "netmask": "255.255.255.0",
      "customize_options": []
    },
    "PortChannel1": {
      "gateway": "192.168.2.1",
      "lease_time": "180",
      "mode": "PORT",
      "netmask": "255.255.255.0",
      "customize_options": []
    }
  },
  "DHCP_SERVER_IPV4_IP_RANGE": {
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
    "Vlan1000|Ethernet1": {
      "range1": {},
      "range2": {}
    },
    "Vlan1000|Ethernet2": {
      "range3": {}
    },
    "Ethernet15": {
      "range4": {}
    },
    "PortChannel1": {
      "range5": {}
    }
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
  }
}
```

### State DB
Following table changes would be added in State DB, including **DHCP_SERVER_IPV4_COUNTER** table and **DHCP_SERVER_IPV4_LEASE** table.

These new tables are introduced to count different type of DHCP packet and record lease information.

#### Yang Model
```yang
module sonic-dhcp-server-ipv4-counter {
  import ietf-inet-types {
        prefix inet;
  }
  container sonic-dhcp-server-ipv4-counter {
    container DHCP_SERVER_IPV4_COUNTER {
      description "DHCP_SERVER_IPV4_COUNTER part of state_db";
      list DHCP_SERVER_IPV4_COUNTER_LIST {
        key "name";
        leaf name {
          type string;
        }
        list DHCP_SERVER_IPV4_COUNTER_TYPE_LIST {
          key "name";
          leaf name {
            type string;
          }
          leaf recover {
            description "Count of recover packets receive";
            type uint16;
          }
          leaf offer {
            description "Count of offer packets send";
            type uint16;
          }
          leaf request {
            description "Count of request packets receive";
            type uint16;
          }
          leaf ack {
            description "Count of ack packets send";
            type uint16;
          }
          leaf release {
            description "Count of release packets receive";
            type uint16;
          }
        }
      }
    }
    /* end of container DHCP_SERVER_IPV4_COUNTER */
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
    /* end of container DHCP_SERVER_IPV4_COUNTER */
  }
  /* end of container sonic-dhcp-server-ipv4-counter */
}
```

#### DB Objects
```JSON
{
  "DHCP_SERVER_IPV4_COUNTER": {
    "DNSMASQ": { // Counter of dnsmasq
      "Vlan1000|Ethernet1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Vlan1000|Ethernet2": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Ethernet15": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "PortChannel1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      }
    },
    "DHCP_SERVER_BRIDGE": { // Counter of dhcp server bridge
      "Vlan1000|Ethernet1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Vlan1000|Ethernet2": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Ethernet15": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "PortChannel1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      }
    },
    "DHCP_RELAY": { // Counter of dhcrelay
      "Vlan1000|Ethernet1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Vlan1000|Ethernet2": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "Ethernet15": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      },
      "PortChannel1": {
        "recover": "0",
        "offer": "0",
        "request": "0",
        "ack": "0",
        "release": "0"
      }
    },
  },
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
    },
    "Ethernet15|10:70:fd:b6:13:02": {
      "lease_start": "1677640582",
      "lease_end": "1677641481",
      "ip": "192.168.0.3"
    }
  }
}
```

## dhcrelay Patch
Current dhcrelay in SONiC only support add port information to option82 for interfaces who is in VLAN. Need to add support for single physical ports or port channels.

## Flow Diagrams
### Config Change Flow
This sequence figure describe the work flow for config_db changed CLI.
<div align="center"> <img src=images/config_change_new_flow.png width=600 /> </div>

### Lease Update Flow
Below sequence figure describes the work flow how dnsmasq updates lease table while new lease is created.

<div align="center"> <img src=images/lease_update_flow_new.png width=430 /> </div>

### Count Table Update Flow
Below sequence figure describes the work flow about server update counter file.
<div align="center"> <img src=images/ebpf_counter.png width=430 /> </div>

Below sequence figure describes the work flow how to update DHCP_SERVER_IPV4_COUNTER table after log file changed.
<div align="center"> <img src=images/log_counter_flow.png width=480 /> </div>

# CLI
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

**config dhcp_server ip pool**
This command is used to config ip pool.
- Usage
  ```
  config dhcp_server ipv4 ip pool add <pool_name> <ip_start> [<ip_end>]
  config dhcp_server ipv4 ip pool del <pool_name>
  ```

- Example
  ```
   # <ip_end> is not required, if not given, means ip_end is equal to ip_start
  config dhcp_server ipv4 ip pool add pool1 192.168.0.1

  config dhcp_server ipv4 ip pool del pool1
  ```

**config dhcp_server port**

This command is used to config dhcp ip per interface.
- Usage
  ```
  config dhcp_server ipv4 pool bind [<vlan_interface>] <interface> <ip_pool_names>
  config dhcp_server ipv4 pool unbind [<vlan_interface>] <interface> <ip_pool_names>
  ```

- Example
  ```
  config dhcp_server ipv4 pool bind Vlan1000 Ethernet1 pool1 pool2
  config dhcp_server ipv4 pool unbind Vlan1000 Ethernet1 pool1 pool2
  ```

**config dhcp_server option add**

This command is used to add dhcp option per dhcp interface.
Type field can refer to [#2.7 Customize DHCP Packet Options](#27-customize-dhcp-packet-options).
- Usage
  ```
  config dhcp_server ipv4 option add <dhcp_interface> <option> <type> <value>
  ```

- Example
  ```
  config dhcp_server ipv4 option add Vlan1000 12 text host_1
  ```

**config dhcp_server option del**

This command is used to delete dhcp option.
- Usage
  ```
  config dhcp_server ipv4 option del <dhcp_interface> (all | <option>)
  ```

- Exampe
  ```
  config dhcp_server ipv4 option del Vlan1000 all

  config dhcp_server ipv4 option del Vlan1000 42
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

## Show CLI
**show dhcp_server info**

This command is used to show dhcp_server config.
- Usage
  ```
  show dhcp_server ipv4 info [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 info Vlan1000
  +-----------+-----+------------+--------------+--------------+-----------------------------------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |Rules                              |
  |-----------+-----+------------+--------------+----------- --+-----------------------------------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |Ethernet1 192.168.0.2-192.168.0.2  |
  |           |     |            |              |              |Ethernet2 192.168.0.3-192.168.0.5  |
  |           |     |            |              |              |Ethernet3 192.168.0.6-192.168.0.6  |
  +-----------+-----+------------+--------------+--------------+-----------------------------------+

  show dhcp_server ipv4 info
  +-----------+-----+------------+--------------+--------------+-----------------------------------+
  |Interface  |Mode |Gateway     |Netmask       |Lease Time(s) |Rules                              |
  |-----------+-----+------------+--------------+----------- --+-----------------------------------+
  |Vlan1000   |PORT |192.168.0.1 |255.255.255.0 |180           |Ethernet1 192.168.0.2-192.168.0.2  |
  |           |     |            |              |              |Ethernet2 192.168.0.3-192.168.0.5  |
  |           |     |            |              |              |Ethernet3 192.168.0.6-192.168.0.6  |
  +-----------+-----+------------+--------------+--------------+-----------------------------------+
  |Ethernet12 |PORT |192.168.1.1 |255.255.255.0 |180           |Ethernet12 192.168.1.3-192.168.1.3 |
  +-----------+-----+------------+--------------+--------------+-----------------------------------+
  ```

**show dhcp_server option**

This command is used to show dhcp_server customized option.

- Usage
  ```
  show dhcp_server ipv4 option [<dhcp_interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 option Vlan1000
  +-------------+-------+------------+-------------+
  |Interface    |Option |Value       |Type         |
  |-------------+-------+------------+-------------+
  |Vlan1000     |12     |host_1      |text         |
  +-------------+-------+------------+-------------+

  show dhcp_server ipv4 option
  +-------------+-------+------------+-------------+
  |Interface    |Option |Value       |Type         |
  |-------------+-------+------------+-------------+
  |Vlan1000     |12     |host_1      |text         |
  +-------------+-------+------------+-------------+
  |PortChannel1 |12     |host_2      |text         |
  +-------------+-------+------------+-------------+
  ```

**show dhcp_server counter**

This command is used to show dhcp_server counter.
- Usage
  ```
  show dhcp_server ipv4 counter [<interface>]
  ```

- Example
  ```
  show dhcp_server ipv4 counter Vlan1000
  +-----------+------------+------+
  |Interface  |Packet Type |Count |
  |-----------+------------+------+
  |Vlan1000   |DISCOVER    |15    |
  |           |OFFER       |15    |
  |           |REQUEST     |15    |
  |           |ACK         |15    |
  |           |RELEASE     |15    |
  +-----------+------------+------+

  show dhcp_server ipv4 counter
  +-----------+------------+------+
  |Interface  |Packet Type |Count |
  |-----------+------------+------+
  |Vlan1000   |DISCOVER    |15    |
  |           |OFFER       |15    |
  |           |REQUEST     |15    |
  |           |ACK         |15    |
  |           |RELEASE     |15    |
  +-----------+------------+------+
  |Ethernet12 |DISCOVER    |15    |
  |           |OFFER       |15    |
  |           |REQUEST     |15    |
  |           |ACK         |15    |
  |           |RELEASE     |15    |
  +-----------+------------+------+
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
  |           |2b:2b:2b:2b:2b:2b |192.168.0.3 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  +-----------+------------------+------------+--------------------+--------------------+

  show dhcp_server ipv4 lease
  +-----------+------------------+------------+--------------------+--------------------+
  |Interface  |MAC Address       |IP          |Lease Start         |Lease End           |
  +-----------+------------------+------------+--------------------+--------------------+
  |Vlan1000   |2c:2c:2c:2c:2c:2c |192.168.0.2 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  |           |2b:2b:2b:2b:2b:2b |192.168.0.3 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  +-----------+------------------+------------+--------------------+--------------------+
  |Vlan1001   |2e:2e:2e:2e:2e:2e |192.168.8.2 |2023-02-02 10:00:00 |2023-02-02 10:15:00 |
  +-----------+------------------+------------+--------------------+--------------------+

## Clear CLI
**sonic-clear dhcp_server ipv4 counter**

This command is used to clear dhcp_server counter.
- Usage
  ```
  sonic-clear dhcp_server ipv4 counter [<dhcp_interface>]
  ```

- Example
  ```
  sonic-clear dhcp_server ipv4 counter Vlan1000
  ```

# Unit Test
The Unit test case are as below:
| No |                Test case summary                          |
|:----------------------|:-----------------------------------------------------------|
| 1 | Verify that config add/del dhcp_server can work well |
| 2 | Verify that config dhcp_server info can work well |
| 3 | Verify that show dhcp_server info can work well |
