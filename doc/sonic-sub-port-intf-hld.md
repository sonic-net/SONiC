# SONiC sub port interface high level design

# Table of Contents
<!-- TOC -->

  * [Revision history](#revision-history)
  * [Scope](#scope)
  * [Acronyms](#acronyms)
  * [1 Requirements](#1-requirements)
  * [2 Schema design](#2-schema-design)
    * [2.1 Configuration](#21-configuration)
        * [2.1.1 config_db.json](#211-config-db-json)
        * [2.1.2 CONFIG_DB](#212-config-db)
        * [2.1.3 CONFIG_DB schemas](#213-config-db-schemas)
    * [2.2 APPL_DB](#22-appl-db)
    * [2.3 STATE_DB](#23-state-db)
    * [2.4 SAI](#24-sai)
        * [2.4.1 Create a sub port interface](#241-create-a-sub-port-interface)
        * [2.4.2 Set a sub port interface mtu](#242-set-a-sub-port-interface-mtu)
        * [2.4.3 Remove a sub port interface](#243-remove-a-sub-port-interface)
    * [2.5 Linux integration](#25-linux-integration)
        * [2.5.1 Host sub port interfaces](#251-host-sub-port-interfaces)
        * [2.5.2 Route, neighbor subsystems](#252-route-neighbor-subsystems)
  * [3 Event flow diagrams](#3-event-flow-diagrams)
    * [3.1 Sub port interface creation](#31-sub-port-interface-creation)
    * [3.2 Sub port interface runtime mtu change](#32-sub-port-interface-runtime-mtu-change)
    * [3.3 Sub port interface removal](#33-sub-port-interface-removal)
  * [4 CLI](#4-cli)
    * [4.1 Config commands](#41-config-commands)
    * [4.2 Show commands](#42-show-commands)
  * [5 Warm reboot support](#5-warm-reboot-support)
  * [6 Unit test](#6-unit-test)
    * [6.1 Sub port interface creation](#61-sub-port-interface-creation)
        * [6.1.1 Create a sub port interface](#611-create-a-sub-port-interface)
        * [6.1.2 Add an IP address to a sub port interface](#612-add-an-ip-address-to-a-sub-port-interface)
    * [6.2 Sub port interface mtu change](#62-sub-port-interface-mtu-change)
    * [6.3 Sub port interface removal](#63-sub-port-interface-removal)
        * [6.3.1 Remove an IP address from a sub port interface](#631-remove-an-ip-address-from-a-sub-port-interface)
        * [6.3.2 Remove all IP addresses from a sub port interface](#632-remove-all-ip-addresses-from-a-sub-port-interface)
        * [6.3.3 Remove a sub port interface](#633-remove-a-sub-port-interface)
  * [7 Scalability](#7-scalability)
  * [8 Port channel renaming](#8-port-channel-renaming)

<!-- /TOC -->

# Revision history
| Rev |    Date     |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 07/01/2019  | Wenda Ni           | Initial version                   |

# Scope
A sub port interface is a logical interface that can be created on a physical port or a port channel.
A sub port interface serves as an interface to either a .1D bridge or a VRF, but not both.
This design focuses on the use case of creating a sub port interface on a physical port or a port channel and using it as a router interface to a VRF.

![](https://github.com/wendani/SONiC/blob/sub_port_master/images/sub_interface_hld/sub_intf_rif.png)

Multiple L3 sub port interfaces, each characterized by a VLAN id in the 802.1q tag, can be created on a physical port or a port channel.
Sub port interfaces attaching to the same physical port or port channel can interface to different VRFs, though they share the same VLAN id space and must have different VLAN ids.
Sub port interfaces attaching to different physical ports or port channels can use the same VLAN id, even when they interface to the same VRF.
However, there is no L2 bridging between these sub port interfaces; each sub port interface is considered to stay in a separate bridge domain.

# Acronyms
| Acronym                  | Description                                |
|--------------------------|--------------------------------------------|
| VRF                      | Virtual route forward                      |
| RIF                      | Router interface                           |

# 1 Requirements

Manage the life cycle of a sub port interface created on a physical port or a port channel and used as a router interface to a VRF:
* Creation with the specified dot1q vlan id encapsulation and optional mtu
* Runtime mtu change
* Removal

A sub port interface shall support the following features:
* L3 forwarding (both unicast and multicast)
* BGP
* ARP
* VRF
* RIF counters
* QoS setting inherited from parent physical port or port channel
* Per sub port interface mtu config
* mtu inheritance from parent physical port or port channel if mtu is not specified on a sub port interface in the configuration file.

# 2 Schema design

We introduce a new table "DOT1Q_INTERFACE" in the CONFIG_DB to host the attributes of a sub port interface.
For APPL_DB and STATE_DB, we do not introduce new tables for sub port interfaces, but reuse existing tables to host sub port interface keys.

## 2.1 Configuration
### 2.1.1 config_db.json
```
"DOT1Q_INTERFACE": {
    "{{ port_name }}.{{ vlan_id }}": {
        "mtu" : "{{ mtu_size }}"
    },
    "{{ port_name }}.{{ vlan_id }}|{{ ip_prefix }}": {}
},

"VLAN": {
    "Vlan{{ vlan_id }}": {
        "vlanid" : "{{ vlan_id }}"
    }
},
```
A key in the DOT1Q_INTERFACE table is the name of a sub port, which consists of two sections delimited by a "." (symbol dot). The section before the dot is the name of the parent physical port or port channel. The section after the dot is the dot1q encapsulation vlan id.

mtu of a sub port interface should be no greater than that of the parent physical port or port channel. In the case field "mtu" is absent in the config_db.json file, a sub port interface inherits the mtu from its parent physical port or port channel.

Example configuration:
```
"DOT1Q_INTERFACE": {
    "Ethernet64.10": {
        "mtu" : "9100"
    },
    "Ethernet64.10|192.168.0.1/21": {}
},

"VLAN": {
    "Vlan10": {
        "vlanid" : "10"
    }
},
```

### 2.1.2 CONFIG_DB
```
DOT1Q_INTERFACE|{{ port_name }}.{{ vlan_id }}
    "mtu" : "{{ mtu_size }}"

DOT1Q_INTERFACE|{{ port_name }}.{{ vlan_id }}|{{ ip_prefix }}
    "NULL" : "NULL"
```

### 2.1.3 CONFIG_DB schemas
```
; Defines for sub port interface configuration attributes
key             = DOT1Q_INTERFACE|subif_name    ; subif_name is the name of the sub port interface

; subif_name annotations
subif_name      = port_name "." vlan_id         ; port_name is the name of parent physical port or port channel
                                                ; vlanid is DIGIT 1-4094

; field         = value
mtu             = 1*4DIGIT                      ; sub port interface MTU (Optional)
```

```
; Defines for sub port interface configuration attributes
key             = DOT1Q_INTERFACE|subif_name|IPprefix   ; an instance of this key will be repeated for each IP prefix

IPprefix        = IPv4prefix / IPv6prefix               ; an instance of this key/value pair will be repeated for each IP prefix

IPv4prefix      = dec-octet "." dec-octet "." dec-octet "." dec-octet "/" %d1-32
dec-octet       = DIGIT                 ; 0-9
                 / %x31-39 DIGIT        ; 10-99
                 / "1" 2DIGIT           ; 100-199
                 / "2" %x30-34 DIGIT    ; 200-249
                 / "25" %x30-35         ; 250-255

IPv6prefix      =                             6( h16 ":" ) ls32
                 /                       "::" 5( h16 ":" ) ls32
                 / [               h16 ] "::" 4( h16 ":" ) ls32
                 / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
                 / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
                 / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
                 / [ *4( h16 ":" ) h16 ] "::"              ls32
                 / [ *5( h16 ":" ) h16 ] "::"              h16
                 / [ *6( h16 ":" ) h16 ] "::"
h16             = 1*4HEXDIG
ls32            = ( h16 ":" h16 ) / IPv4address
```

Example:
```
DOT1Q_INTERFACE|Ethernet64.10
    "mtu" : "9100"

DOT1Q_INTERFACE|Ethernet64.10|192.168.0.1/21
    "NULL" : "NULL"
```

## 2.2 APPL_DB
```
INTF_TABLE:{{ port_name }}.{{ vlan_id }}
    "mtu" : "{{ mtu_size }}"

INTF_TABLE:{{ port_name }}.{{ vlan_id }}:{{ ip_prefix }}
    "NULL" : "NULL"
```

Example:
```
INTF_TABLE:Ethernet64.10
    "mtu" : "9100"

INTF_TABLE:Ethernet64.10:192.168.0.1/24
    "scope" : "global"
    "family": "IPv4"
```

## 2.3 STATE_DB

Following the current schema, sub port interface state of a physical port is set to the PORT_TABLE, while sub port interface state of a port channel is set to the LAG_TABLE.
```
PORT_TABLE|{{ port_name }}.{{ vlan_id }}
    "state" : "ok"
```
```
LAG_TABLE|{{ port_name }}.{{ vlan_id }}
    "state" : "ok"
```
```
INTERFACE_TABLE|{{ port_name }}.{{ vlan_id }}|{{ ip_prefix }}
    "state" : "ok"
```

Example:
```
PORT_TABLE|Ethernet64.10
    "state" : "ok"
```
```
INTERFACE_TABLE|Ethernet64.10|192.168.0.1/21
    "state" : "ok"
```

## 2.4 SAI
SAI attributes related to a sub port interface are listed in the Table below.

| SAI attributes                                   | attribute value/type                         |
|--------------------------------------------------|----------------------------------------------|
| SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID      | VRF oid                                      |
| SAI_ROUTER_INTERFACE_ATTR_TYPE                   | SAI_ROUTER_INTERFACE_TYPE_SUB_PORT           |
| SAI_ROUTER_INTERFACE_ATTR_PORT_ID                | parent physical port or port channel oid     |
| SAI_ROUTER_INTERFACE_ATTR_VLAN_ID                | VLAN oid                                     |
| SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS        | MAC address                                  |
| SAI_ROUTER_INTERFACE_ATTR_MTU                    | mtu size                                     |

### 2.4.1 Create a sub port interface
```
sai_attribute_t sub_intf_attrs[6];

sub_intf_attrs[0].id = SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID;
sub_intf_attrs[0].value.oid = vrf_oid;

sub_intf_attrs[1].id = SAI_ROUTER_INTERFACE_ATTR_TYPE;
sub_intf_attrs[1].value.s32 = SAI_ROUTER_INTERFACE_TYPE_SUB_PORT;

sub_intf_attrs[2].id = SAI_ROUTER_INTERFACE_ATTR_PORT_ID;
sub_intf_attrs[2].value.oid = parent_port_oid;  /* oid of the parent physical port or port channel */

sub_intf_attrs[3].id = SAI_ROUTER_INTERFACE_ATTR_VLAN_ID;
sub_intf_attrs[3].value.oid = vlan_oid;

sai_mac_t mac = {0x00, 0xe0, 0xec, 0xc2, 0xad, 0xf1};
sub_intf_attrs[4].id = SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS;
memcpy(sub_intf_attrs[4].value.mac, mac, sizeof(sai_mac_t));

sub_intf_attrs[5].id = SAI_ROUTER_INTERFACE_ATTR_MTU;
sub_intf_attrs[5].value.u32 = 9100;

uint32_t sub_intf_attrs_count = 6;
sai_status_t status = create_router_interface(&rif_id, switch_oid, sub_intf_attrs_count, sub_intf_attrs);
```

### 2.4.2 Set a sub port interface mtu
```
sai_attribute_t sub_intf_attr;
sub_intf_attr.id = SAI_ROUTER_INTERFACE_ATTR_MTU;
sub_intf_attr.value.u32 = 9000;

sai_status_t status = set_router_interface_attribute(rif_id, &attr);
```

### 2.4.3 Remove a sub port interface
```
sai_status_t status = remove_router_interface(rif_id);
```

## 2.5 Linux integration
### 2.5.1 Host sub port interfaces

We use iproute2 package to manage host sub port interfaces.
Specifically, we use `ip link add link <parent_port_name> name <subif_name> type vlan id <vlan_id>` to create a host sub port interface.
This command implies the dependancy that a parent host interface must be created before the creation of a host sub port interface.
At creation, a host sub port interface is always set to admin status up.

Example:
```
ip link add link Ethernet64 name Ethernet64.10 type vlan id 10
ip link set Ethernet64.10 mtu 9100
ip link set Ethernet64.10 up
```
```
ip link del Ethernet64.10
```

We use `ip address` and `ip -6 address` to add and remove ip adresses on a host sub port interface.

Example:
```
ip address add 192.168.0.1/24 dev Ethernet64.10
```

### 2.5.2 Route, neighbor subsystems

Once the host sub port interfaces are properly set, route and neighbor subsystems should function properly on sub port interfaces.
fpmsyncd should receive route add/del updates on sub port interfaces from zebra over TCP socket port 2620. These updates are received in the format of netlink messages.
neighsyncd should receive neigh add/del netlink messages on sub port interfaces from its subscription to the neighbor event notification group RTNLGRP_NEIGH.

Internally, a sub port interface is represented as a Port object to be perceived seamlessly by NeighOrch and RouteOrch to create neighor and route entries, respectively, on it.


# 3 Event flow diagrams
## 3.1 Sub port interface creation
![](https://github.com/wendani/SONiC/blob/sub_port_master/images/sub_interface_hld/sub_intf_creation_flow.png)

## 3.2 Sub port interface runtime mtu change
![](https://github.com/wendani/SONiC/blob/sub_port_master/images/sub_interface_hld/sub_intf_set_mtu_flow.png)

## 3.3 Sub port interface removal
![](https://github.com/wendani/SONiC/blob/sub_port_master/images/sub_interface_hld/sub_intf_removal_flow.png)

# 4 CLIs
## 4.1 Config commands
`subinterface` command category is introduced to the `config` command.

```
Usage: config [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'config' command

Options:
  --help  Show this message and exit.

Commands:
  ...
  subinterface           Sub-port-interface-related configuration tasks
```

`add` and `del` commands are supported on a sub port interface.
```
Usage: config subinterface [OPTIONS] COMMAND [ARGS]...

  Sub-port-interface-related configuration tasks

Options:
  --help    Show this message and exit.

Commands:
  add       Add a sub port interface
  del       Remove a sub port interface
  ip        Add or remove an IP address
```
```
Usage: config subinterface add [OPTIONS] <sub_port_interface_name>
```
```
Usage: config subinterface del [OPTIONS] <sub_port_interface_name>
```

Once a sub port interface is added, `add` and `del` ip address commands are supported on it.
```
Usage: config subinterface ip [OPTIONS] COMMAND [ARGS]...

  Add or remove IP address

Options:
  --help    Show this message and exit.

Commands:
  add       Add an IP address towards a sub port interface
  del       Remove an IP address from a sub port interface
```
```
Usage: config subinterface ip add [OPTIONS] <sub_port_interface_name> <ip_addr>
```
```
Usage: config subinterface ip del [OPTIONS] <sub_port_interface_name> <ip_addr>
```

## 4.2 Show commands
```
Usage: show subinterfaces [OPTIONS] COMMAND [ARGS]...

  Show details of the sub port interfaces

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  status       Show sub port interface status information
```
Example:
```
Sub port interface    Speed    MTU    Vlan    Oper    Admin                 Type
------------------  -------  -----  ------  ------  -------  -------------------
     Ethernet64.10     100G   9100      10      up       up  dot1q-encapsulation
```

# 5 Warm reboot support
There is no special runtime state that needs to be kept for sub port interfaces.
This said, current warm reboot infrastructure shall support sub port interfaces naturally without the need for additional extension.
This is confirmed by preliminary trials on a Mellanox device.

# 6 Uinit test
## 6.1 Sub port interface creation
Test shall cover the parent interface being a physical port or a port channel.

### 6.1.1 Create a sub port interface
| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that sub port interface configuration is pushed to CONIFG_DB DOT1Q_INTERFACE table              |
| Verify that sub port interface configuration is synced to APPL_DB INTF_TABLE by Intfmgrd               |
| Verify that sub port interface state ok is pushed to STATE_DB by Intfmgrd                              |
| Verify that a sub port router interface entry is created in ASIC_DB                                    |

### 6.1.2 Add an IP address to a sub port interface
Test shall cover the IP address being an IPv4 address or an IPv6 address.

| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that ip address configuration is pushed to CONIFG_DB DOT1Q_INTERFACE table                      |
| Verify that ip address configuration is synced to APPL_DB INTF_TABLE by Intfmgrd                       |
| Verify that ip address state ok is pushed to STATE_DB INTERFACE_TABLE by Intfmgrd                      |
| Verify that a subnet route entry is created in ASIC_DB                                                 |
| Verify that a ip2me route entry is created in ASIC_DB                                                  |

## 6.2 Sub port interface mtu change
| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that sub port interface mtu change is pushed to CONIFG_DB DOT1Q_INTERFACE table                 |
| Verify that sub port interface mtu change is synced to APPL_DB INTF_TABLE by Intfmgrd                  |
| Verify that sub port router interface entry in ASIC_DB has the updated mtu value                       |

## 6.3 Sub port interface removal
### 6.3.1 Remove an IP address from a sub port interface
Test shall cover the IP address being an IPv4 address or an IPv6 address.

| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that ip address configuration is removed from CONIFG_DB DOT1Q_INTERFACE table                   |
| Verify that ip address configuration is removed from APPL_DB INTF_TABLE by Intfmgrd                    |
| Verify that ip address state ok is removed from STATE_DB INTERFACE_TABLE by Intfmgrd                   |
| Verify that subnet route entry is removed from ASIC_DB                                                 |
| Verify that ip2me route entry is removed from ASIC_DB                                                  |

### 6.3.2 Remove all IP addresses from a sub port interface
| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that sub port router interface entry is removed from ASIC_DB                                    |

### 6.3.3 Remove a sub port interface
Test shall cover the parent interface being a physical port or a port channel.

| Test case description                                                                                  |
|--------------------------------------------------------------------------------------------------------|
| Verify that sub port interface configuration is removed from CONIFG_DB DOT1Q_INTERFACE table           |
| Verify that sub port interface configuration is removed from APPL_DB INTF_TABLE by Intfmgrd            |
| Verify that sub port interface state ok is removed from STATE_DB by Intfmgrd                           |

# 7 Scalability
Scalability is ASIC-dependent.
We enforce a minimum scalability requirement on the number of sub port interfaces that shall be supported on a SONiC switch.

| Name                                                              | Scaling value             |
|-------------------------------------------------------------------|---------------------------|
| Number of sub port interfaces per phyical port or port channel    | 250                       |
| Number of sub port interfaces per switch                          | 750                       |

# 8 Port channel renaming
Linux has the limitation of 16 characters on an interface name.
For sub port interface use cases on port channels, we need to redesign the current naming convention for port channels (PortChannelXXXX, 15 characters) to take shorter names (such as, PoXXXX, 6 characters).
