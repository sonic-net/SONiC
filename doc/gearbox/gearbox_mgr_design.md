
# Feature Name
SONiC Gearbox Manager

# High Level Design Document
#### Rev 0.3 (Draft)

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definition_abbreviation)
  * [Document/References](#document_references)
  * [Requirement Overview](#1-requirement-overview)

# List of Tables
- [Table 1: Abbreviations](#table-1-abbreviations)
- [Table 2: References](#table-2-references)
- [Table 3: SAI Port Mapping](#table-3-sai-port-mapping)
- [Table 4: Platform Configuration](#table-4-platform-configuration)
- [Table 5: PHY Configuration](#table-5-phy-configuration)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 10/22/2019  | Dan Arsenault      | Initial Draft                     |
| 0.2 | 12/12/2019  | Dan Arsenault      | Minor internal review edits       |
| 0.3 | 03/19/2020  | Dan Arsenault      | New CLI, File, and Notifications  |


# About this Manual
This document provides general information about the new Gearbox Manager functionality and infrastructure in utilizing the new OCP External PHY Abstraction Interface for SONiC.

# Scope
This document describes the high level design of the Gearbox Manager feature. This feature primarily consists of two new processes or tasks running within the SWSS Docker which utilizes and depends on the availability of the new OCP External PHY Interface. Please refer to the OCP External PHY Abstraction Interface for additional information.

# Definition/Abbreviation

# Table 1 Abbreviations

| **Term**         | **Meaning**                                                                |
|------------------|----------------------------------------------------------------------------|
| gearbox          | PHY silicon to merge PHY Tx side and to split apart PHY Rx side            |
| GEARSYNCD        | New ORCHAGENT daemon servicing gearbox configuration processing            |
| line-side        | Connection between the PHY and Ethernet line cards                         |
| NETLINK          | Communication channel between kernel and user space containing port status |
| ORCHAGENT        | Core daemon thread which manages similar Orch agents                       |
| PHY              | Physical Layer chip devices (commonly found on Ethernet devices)           |
| REDIS            | Open source, in-memory data structure store, used as a database            |
| SAI              | Switch Abstraction Interface                                               |
| SWSS             | SWitch State Service                                                       |
| system-side      | Connection between the PHY and switching silicon                           |

# Document/References

# Table 2 References

| **Document**                       | **Location**  |
|------------------------------------|---------------|
| Gearbox Manager Requirements       | [Gearbox Manager Requirements](http://gerrit-lvn-07.lvn.broadcom.net:8083/plugins/gitiles/sonic/documents/+/refs/changes/34/12034/1/base/gearbox_mgr_req.md) |
| External PHY Abstraction Interface | [External PHY Abstraction Interface](https://github.com/opencomputeproject/SAI/pull/1004) |

# 1 Requirement Overview
The Ethernet switches of today have evolved and are entering several key segments providing switch chips for enterprise, data-center, and carrier, as well as optical transceivers, Gearbox PHYs and 25Gbps  Re-timers. If the platform/hardware supports it, the PHY may be configurable to speeds including 10G, 25G, 40G, 50G, and 100G, and beyond. Some platforms contain an external PHY, while others have PHYs embedded in the switch ASIC (Internal PHY). An External PHY is used to serve different purposes like gearbox,  Re-timer, MACSEC and multi gigabit Ethernet PHY transceivers, etc.

The Abstraction Interface contains a set of SAI APIs providing new functionality in support of the most recent PHY advancements and requirements. Through utilizing this new external PHY interface, this project adds configuration and management capabilities for these new external PHY requirements.

## 1.1 Functional Requirements
1. Introduce configuration schema supporting external gearbox and PHY configurations
2. Support multiple external PHYs
3. Administer CRUD services for external PHYs
4. Administer Re-timer configuration for external PHYs
5. Coordinates port configuration between system and line side and External PHYs
6. Abstracts the system side configuration from the SONiC application
7. Consolidate link status from ASIC and PHY port side if PHY driver doesn't support status propagation
8. Support removable line cards with any PHY configuration (*future*)
9. Warm-boot support

## 1.2 Configuration and Management Requirements
1. Existing CLI interface commands are not affected.
2. Show commands to display the gearbox port configuration, as described in "Show Commands" section below.
3. Debug commands as described in "Debug Commands" section below.

## 1.3 Warm Boot Requirements
Functionality should continue to work across warm boot.
- To support planned system warm boot.
- To support SWSS docker warm boot.

# 2 Functionality

## 2.1 Target Deployment Use Cases
The Gearbox Manager infrastructure is used to manage and configure the external PHYs which are used to serve different purposes like gearbox,  Re-timer, and multi gigabit ethernet PHY transceivers, etc.

### 2.1.1 Gearbox Use Cases
A gearbox is essentially a kind of multiplexer/de-multiplexer that's used to convert multiple serial data streams at one rate to multiple streams at another rate. Here is just a sample of possible gearbox use cases.

#### 2.1.1.1 40GbE Quad Port Gearbox PHY
A high-density gearbox physical layer transceiver (PHY) converts 20 Gbps signals to multiple lanes running at 10 Gbps. Using the companion PHY, customers have the option to provide legacy 40GbE ports while leveraging the full bandwidth of the switch.

### 2.1.2 Re-timer Use Case
A  Re-timer is essentially a kind of clock change without effect the rates.

#### 2.1.2.1 Dual 100GbE PHY/Octal 25G  Re-timer
A low-power, low-latency PHY integrating  Re-timer and equalizer functions that support 100-Gigabit Ethernet (GbE), 40GbE and 10GbE applications.

### 2.1.3 vSONiC
Virtual SONiC or vSONiC is an infrastructure that is based on the Linux QEMU/KVM hypervisor that enables creation, management and interconnections of VMs that are running SONiC. When creating an instance of a chassis, a new gearbox chip-type has been added and is identified as "82764 - Sesto Gearbox". When using this chassis (and other gearbox PHY types), the associated platform and PHY configuration files are copied to the VM. In addition, the associated SAI PHY object library has been modified to mock simple APIs in order to test and validate basic Gearbox functionality.

## 2.2 Functional Description
The external PHY capabilities are platform specific and are defined in 2 files; the gearbox platform and the PHY configuration file. The Gearbox Manager reads the configuration files for the given platform, constructs the gearbox topology and initializes both the system-side and line-side of the PHY(s). The Gearbox Manager also receives and processes select configuration requests as well the consolidation of system-side and line-side operational state port events.

# 3 Design

## 3.1 Overview
In order to isolate gearbox functionality and complexity, the Gearbox Manager implementation is an *infrastructure* of new gearbox specific Linux processes. In addition to the new Gearbox processes, the SYNCD Docker has been enhanced to support the new External PHY Abstraction Interface extensions.

![Gearbox Overview](images/gearbox_overview.png)

### 3.1.1 ORCHAGENT (modified)
Upon startup or reboot, portsyncd is started as well as the new gearsyncd deamon. The Orchagent is still responsible for creating the ASIC switch and the associated host interfaces. The internal doPortTask has been modified to support both internal port and Gearbox related events.

![Gearbox ORCHAGENT FLOW](images/gearbox_orchagent_flow.png)

### 3.1.2 GEARSYNCD (new)
This component essentially provides the same database services as provided by PORTSYNCD but for gearbox configurations. Specifically, GEARSYNCD reads the Gearbox configuration files and creates the associated GEARBOX tables in the APPL_DB database. Upon completion, GEARSYNCD sends a GearboxConfigDone notification (similar to the PORTSYNCD PortConfigDone).

![Gearbox GEARSYNCD Flow](images/gearbox_gearsyncd_flow.png)

### 3.1.3 PORTSYNCD (modified)
The existing PORTSYNCD daemon has been modified to detect the presence of the Gearbox Manager. If enabled, PORTSYNCD simply waits for GearboxConfigDone before it begins its processing.

![Gearbox PORTSYNCD Flow](images/gearbox_portsyncd_flow.png)

### 3.1.4 PORTSORCH (modified)
If the Gearbox Manager is enabled, the PORTSORCH agent has been modified to load and initialize all the external PHYs as well their associated SAI APIs. The PORTSORCH doPortTask has been modified to filter on Gearbox events. Given the gearbox platform and PHY configurations and by utilizing the new SAI PHY APIs, the actual device topology (how these gearbox devices are physically connected) is configured. The following is a high-level interaction between this agent and the SAI APIs.

![Gearbox PORTSORCH & SAI Interaction](images/gearbox_portsorch_sai_interaction.png)

The following sequence diagram shows the PHY initialization process; which also establishes a map structure that is used by the enhanced doPortTask(). The doPortTask() creates the external PHY ports and their connections using the associated external SAI PHY API library.

![Gearbox PORTSORCH & SAI Sequence](images/gearbox_portsorch_sequence.png)

### 3.1.4.1 Port Parameter To SAI Port Mapping

The following table identifies the available parameters and their associated SAI port attributes.

# Table 3 SAI Port Mapping

| **Parameter**     | **sai_port_attr_t**
|-------------------|------------------------------------------------|
| admin state       | SAI_PORT_ATTR_ADMIN_STATE                      |
| speed             | SAI_PORT_ATTR_SPEED                            |
| fec               | SAI_PORT_ATTR_FEC_MODE                         |
| auto neg          | SAI_PORT_ATTR_AUTO_NEG_MODE                    |
| interface type    | SAI_PORT_ATTR_INTERFACE_TYPE                   |
| internal loopback | SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE           |
| link training     | SAI_PORT_ATTR_LINK_TRAINING_ENABLE             |
| media type        | SAI_PORT_ATTR_MEDIA_TYPE                       |
| adver speed       | SAI_PORT_ATTR_ADVERTISED_SPEED                 |
| adver fec         | SAI_PORT_ATTR_ADVERTISED_FEC_MODE              |
| adver auto neg    | SAI_PORT_ATTR_ADVERTISED_AUTO_NEG_MODE         |
| adver asym pause  | SAI_PORT_ATTR_ADVERTISED_ASYMMETRIC_PAUSE_MODE |
| adver media type  | SAI_PORT_ATTR_ADVERTISED_MEDIA_TYPE            |
| prbs polynomial   | SAI_PORT_ATTR_PRBS_POLYNOMIAL                  |
| prbs config       | SAI_PORT_ATTR_PRBS_CONFIG                      |
| ingess macsec     | SAI_PORT_ATTR_INGRESS_MACSEC_ACL               |
| egress macsec     | SAI_PORT_ATTR_EGRESS_MACSEC_ACL                |

## 3.2 Gearbox Platform Configuration
The Gearbox Platform configuration file includes one or more PHYs including its host interfaces. Each interface is linked to its associated PHY using the phy_id.

# Table 4 Platform Configuration

The following table identifies the parameters specified in the Gearbox platform configuration files.
Please note that all the parameters listed in the following table are mandatory.

| **gearbox_config.json** | **Type** |  **Comments**                                             |
|-------------------------|----------|-----------------------------------------------------------|
| **phys**                |          |                                                           |
| phy_id                  | integer  | Arbitrary, but unique index to map phy and its ports      |
| name                    | string   | Vendor specific                                           |
| address                 | hexstr   | Vendor specific, typically a hex based address            |
| lib_name                | string   | FQN to shared object .so file                             |
| firmware_path           | string   | FQN to firmware .bin file                                 |
| config_file             | string   | FQN to PHY config .json file                              |
| sai_init_config_file    | string   | FQN to SAI initialization file                            |
| phy_access              | string   | "mdio", "i2c", or "cpld" ("" - not currently implemented) |
| bus_id                  | integer  | Vendor specific                                           |
| **interfaces**          |          |                                                           |
| index                   | integer  | Physical interface index (same as port_config.ini)        |
| phy_id                  | integer  | PHY index using gearbox_config.json id field              |
| system_lanes            | string   | Comma delimited list of lane indexes                      |
| line_lanes              | string   | Comma delimited list of lane indexes                      |

## 3.3 Gearbox PHY Configuration
Multiple PHYs are supported. Each PHY is described in it's own configuration file. The configuration includes the individual lanes, as well as the logical port configuration consisting of multiple lanes and their lane maps. This file is used to construct the PHY system-side to line-side port hierarchy.

# Table 5 PHY Configuration

The following table identifies the parameters specified in the Gearbox PHY configuration files.
Please note that all the parameters listed in the following table are mandatory.

| **\<phy_config.json>** | **Type** | **Comments**                                                                                   |
|------------------------|----------|------------------------------------------------------------------------------------------------|
| **lanes**              |          |                                                                                                |
| index                  | integer  | A PHY unique lane number                                                                       |
| system_side            | boolean  | Set true if lane is a system-side lane                                                         |
| line_to_system_lanemap | integer  | Reference to associated system lane number                                                     |
| line_tx_lanemap        | integer  | Reference to associated TX lane (line-side only)                                               |
| line_rx_lanemap        | integer  | Reference to associated RX lane                                                                |
| tx_polarity            | integer  | TX polarity value ```0 - not currently implemented```                                          |
| rx_polarity            | integer  | RX polarity value ```0 - not currently implemented```                                          |
| mdio_address           | hexstr   | Vendor specific, typically a hex based address                                                 |
| **ports**              |          |                                                                                                |
| index                  | integer  | A PHY unique lane number                                                                       |
| mdio_addr              | hexstr   | Vendor specific ```typically a hex based address```                                            |
| system_speed           | integer  | System-side lane speed                                                                         |
| system_fec             | string   | System-side FEC mode ```"none", "rs", or "fc"```                                               |
| system_auto_neg        | boolean  | System-side auto-negotiation enabled ```true or false```                                       |
| system_loopback        | boolean  | System-side loopback enabled ```"none", "phy", "mac"```                                        |
| system_training        | boolean  | System-side link training mode enabled ```true or false```                                     |
| line_speed             | integer  | Line-side lane speed                                                                           |
| line_fec               | string   | Line-side FEC mode ```"none", "rs", or "fc"```                                                 |
| line_auto_neg          | boolean  | Line-side auto-negotiation enabled ```true or false```                                         |
| line_media_type        | string   | Line-side media type ```"not present", "unknown", "fiber", "copper", "backplane"```            |
| line_intf_type         | string   | Line-side interface type ```"none", "cr", "cr4", "sr", "sr4", "lr", "lr4", "kr", "kr4"```      |
| line_loopback          | boolean  | Line-side loopback enabled ```"none", "phy", "mac"```                                          |
| line_training          | boolean  | Line-side link training mode enabled ```true or false```                                       |
| line_adver_speed       | string   | Line-side advertised lane speed ```comma delimited list of speeds```                           |
| line_adver_fec         | string   | Line-side advertised FEC mode ```comma delimited list of FEC```                                |
| line_adver_auto_neg    | boolean  | Line-side advertised auto-negotiation enabled ```true or false```                              |
| line_adver_asym_pause  | boolean  | Line-side advertised asymmetric pause mode ```true or false```                                 |
| line_adver_media_type  | string   | Line-side advertised media type ```"not present", "unknown", "fiber", "copper", "backplane"``` |

## 3.4 DB Changes

### 3.4.1 CONFIG DB
No gearbox specific configurations are necessary at this time.

### 3.4.2 APP DB
A new GEARBOX_TABLE has been added to the application database for the purpose of storing the related gearbox
platform and PHY related configuration parameters. This table is populated by the newly modified PORTSORCH.

#### 3.4.2.1 GEARBOX_TABLE - Platform Instance

REDIS example:
~~~
redis-dump -d 0 -k "_GEARBOX_TABLE:phy:0" -y
{
  "_GEARBOX_TABLE:phy:0": {
    "type": "hash",
    "value": {
      "address": "0x1000",
      "bus_id": "0",
      "config_file": "/usr/share/sonic/hwsku/sesto-1.json",
      "firmware_path": "/tmp/phy-sesto-1.bin",
      "lib_name": "libsai_phy_sesto-1.so",
      "name": "sesto-1",
      "phy_access": "",
      "phy_id": "0",
      "phy_oid": "1234",
      "sai_init_config_file": "/usr/share/sonic/hwsku/sesto-1.bcm"
    }
  }
~~~

#### 3.4.2.2 GEARBOX_TABLE - Platform Host Interfaces

REDIS example:
~~~
redis-dump -d 0 -k "_GEARBOX_TABLE:interface:49" -y
{
  "_GEARBOX_TABLE:interface:49": {
    "type": "hash",
    "value": {
      "index": "49",
      "line_lanes": "204,205",
      "phy_id": "0",
      "system_lanes": "200,201,202,203"
    }
  }
}
~~~

#### 3.4.2.3 GEARBOX_TABLE - Platform PHY Lanes

REDIS Example:
~~~
redis-dump -d 0 -k "_GEARBOX_TABLE:phy:0:lanes:200" -y
{
  "_GEARBOX_TABLE:phy:0:lanes:200": {
    "type": "hash",
    "value": {
      "index": "200",
      "line_rx_lanemap": "0",
      "line_to_system_lanemap": "0",
      "line_tx_lanemap": "0",
      "local_lane_id": "0",
      "mdio_addr": "0x0200",
      "rx_polarity": "0",
      "system_side": "true",
      "tx_polarity": "0"
    }
  }
}
~~~

#### 3.4.2.4 GEARBOX_TABLE - Platform PHY Ports

REDIS Example:
~~~
redis-dump -d 0 -k "_GEARBOX_TABLE:phy:0:ports:49" -y
{
  "_GEARBOX_TABLE:phy:0:ports:49": {
    "type": "hash",
    "value": {
      "index": "49",
      "line_adver_asym_pause": "false",
      "line_adver_auto_neg": "false",
      "line_adver_fec": "",
      "line_adver_media_type": "fiber",
      "line_adver_speed": "",
      "line_auto_neg": "true",
      "line_fec": "none",
      "line_intf_type": "none",
      "line_loopback": "none",
      "line_media_type": "fiber",
      "line_speed": "50000",
      "line_training": "false",
      "mdio_addr": "0x2000",
      "system_auto_neg": "true",
      "system_fec": "none",
      "system_loopback": "none",
      "system_speed": "25000",
      "system_training": "false"
    }
  }
}
~~~

### 3.4.3 STATE DB
No modifications made.

### 3.4.4 ASIC DB
No modifications made.

### 3.4.5 COUNTER DB
No modifications made.

## 3.5 Docker SAIPHY SYNCD (new)
A key feature of the External PHY Abstraction Interface is the separation and mapping of
system-to-line side ports for each PHY (switch). The ability to configure and re-configure
the ports are represented in a new object model where each port object is attached to each
other by using a port connector object.

A new SAIPHY SYNCD docker has been created to support multiple external PHYs. Each PHY is controlled
by a separate physyncd daemon that has been extended to support the new SAI APIs.

~~~
typedef enum _sai_api_t
{
    SAI_API_UNSPECIFIED      =  0, /**< unspecified API */
    SAI_API_SWITCH           =  1, /**< sai_switch_api_t */
    SAI_API_PORT             =  2, /**< sai_port_api_t */
    .
    .
    SAI_API_PORT_CONNECTOR   =  40, /**< sai_phy_port_api_t */
} sai_api_t;
~~~

The following diagram shows the overall object model for which the new SAI External Abstraction Interface provides.

![Gearbox SAI Object Model](images/gearbox_sai_object_model.png)

Each external PHY is represented and packaged within its own docker-syncd-phy daemon. Each daemon is uniquely identified by its PHY address and is linked with its own SAI PHY library. A new PHYSYNCD Docker has been created to detect the available PHYs and starts each new syncd-phy daemon within its container. Note that the DATABASE docker has also been modified to replicate the databases which are dedicated for each syncd-phy. Please see the following flow between the ORCHAGENT and the new/modified DATABASE and PHYSYNCD dockers.

![Gearbox ORCHAGENT and SYNCD Flow](images/gearbox_portsorch_syncd_flow.png)

## 3.6 SAI
The Gearbox Manager utilizes and is dependent on the new SAI library which shall include the External PHY Abstraction Interface.

## 3.7 CLI
### 3.7.1 Data Models
### 3.7.2 Configuration Commands

### Existing Click-based CLI Command Modifications

For convenience, if Gearbox is enabled, the Click-based interface startup and shutdown CLI commands have been modified
to configure the associated Gearbox Line-side ports.

**Gearbox Line-side Only**
```
config interface startup <interface_name>
config interface shutdown <interface_name>
```

*The default behavior is to determine if the associated interface has Gearbox ports and will configure them accordingly;*
1. The MAC-side port is applied for non-Gearbox ports
2. The Line-side is applied for Gearbox ports

```
config interface fec   <interface_name> <fec>
config interface speed <interface_name> <speed>
```

### New Click-based CLI Commands

The following Click-based CLI commands have been added in order to extend general configuration capability which compliments
the new Gearbox commands.

*The default behavior is to determine if the associated interface has Gearbox ports and will configure them accordingly;*
1. The MAC-side port is applied for non-Gearbox ports
2. The Line-side is applied for Gearbox ports

**Default Operational Commands**
```
config interface autoneg <interface_name> <autoneg>
config interface loopback <interface_name> <loopback>
config interface link-training <interface_name> <training>
config interface media-type <interface_name>  <media>
config interface interface-type <interface_name> <type>
config interface advertised-speed <interface_name> <speed>
config interface advertised-fec <interface_name>  <fec>
config interface advertised-autoneg <interface_name> <autoneg>
config interface advertised-asym-pause <interface_name> <pause>
config interface advertised-media-type <interface_name> <type>
```

If desired, advanced commands are available to fine tune the ports.

**Advanced Gearbox Commands (available for MAC, PHY, and Line-side ports)**
```
config interface speed <interface_name> [mac <speed>] [phy <speed>] [line <speed>]
config interface autoneg <interface_name> [mac <autoneg>] [phy <autoneg>] [line <autoneg>]
config interface fec <interface_name> [mac <fec>] [phy <fec>] [line <fec>]
config interface loopback <interface_name> [mac <loopback>] [phy <loopback>] [line <loopback>]
config interface link-training <interface_name> [mac <training>] [phy <training>] [line <training>]
```

**Advanced Gearbox Commands (available for MAC and Line-side ports only)**
```
config interface media-type <interface_name> [mac <type>] [line <type>]
config interface interface-type <interface_name> [mac <type>] [line <type>]
config interface advertised-speed <interface_name> [mac <speed>] [line <speed>]
config interface advertised-fec <interface_name> [mac <fec>] [line <fec>]
config interface advertised-autoneg <interface_name> [mac <autoneg>] [line <autoneg>]
config interface advertised-asym-pause <interface_name> [mac <pause>] [line <pause>]
config interface advertised-media-type <interface_name> [mac <type>] [line <type>]
```

**Gearbox Show**

```
show gearbox phys status

Phy Id   Firmware       MAC Address         Name
------   -------- -----------------  -----------
     0        1.2 52:54:00:36:BF:6B      sesto-1
     1       8.7a 00:00:00:00:00:01    th_32_100
```

New gearutil.py script obtains the attribute values from the source below;

| Attribute | Source  |
| --------- | --------|
| phy_id    | APPL_DB |
| firmware  | ASIC_DB |
| MAC       | ASIC_DB |
| name      | APPL_DB |

```
show gearbox interfaces status

Phy Id       Name      Lanes   Speed  Line Lanes  Line Speed  System Lanes  System Speed  Oper  Admin
------  ----------  --------  ------  ----------  ----------  ------------  ------------  ----  -----
     0   Ethernet0   101,102     40G     200,201         20G           202           40G  down   down
     0   Ethernet1   103,104     40G     203,204         20G           205           40G  down   down
     1  Ethernet21       210    100G     212,213         50G       214,215           50G  down   down
```

The new gearutil.py script obtains all the interface status values from the APPL_DB database.

```
show gearbox interfaces counters (TBD)

Phy Id       Name
------  ----------  --------  ------  ----------  ----------  ------------  ------------  ----  -----
     0   Ethernet0
     0   Ethernet1
     1  Ethernet21
```

### Existing Klish-based CLI Command Modifications

If Gearbox is enabled, the following Klish-based CLI commands have been modified accordingly.

*Please note: The command syntax is unchanged and the Line-side ports are automatically configured.*

**Gearbox Line-side Only**
```
interface <port> [no]shutdown
interface Ethernet <port> [no]mtu <mtu>
```

### New Klish-based CLI Commands

The following Klish-based CLI commands have been added in order to extend general configuration capability which compliments
the new Gearbox commands.

*The default behaviour is to determine if the associated interface has Gearbox ports and will configure them accordingly;*
1. The MAC-side port is applied for non-Gearbox ports
2. The Line-side is applied for Gearbox ports

**Default Operational Commands**
```
[no] interface Ethernet <port> speed <speed>
[no] interface Ethernet <port> autoneg <autoneg>
[no] interface Ethernet <port> fec <fec>
[no] interface Ethernet <port> loopback <loopback>
[no] interface Ethernet <port> link-training <training>
[no] interface Ethernet <port> media-type <media>
[no] interface Ethernet <port> interface-type <type>
[no] interface Ethernet <port> advertised-speed <speed>
[no] interface Ethernet <port> advertised-fec <fec>
[no] interface Ethernet <port> advertised-autoneg <autoneg>
[no] interface Ethernet <port> advertised-asym-pause <pause>
[no] interface Ethernet <port> advertised-media-type <type>
```

If desired, advanced commands are available to fine tune the ports.

**Advanced Gearbox Commands (available for MAC, PHY, and Line-side ports)**
```
[no] interface Ethernet <port> speed [mac <speed>] [phy <speed>] [line <speed>]
[no] interface Ethernet <port> autoneg [mac <autoneg>] [phy <autoneg>] [line <autoneg>]
[no] interface Ethernet <port> fec [mac <fec>] [phy <fec>] [line <fec>]
[no] interface Ethernet <port> loopback [mac <loopback>] [phy <loopback>] [line <loopback>]
[no] interface Ethernet <port> link-training [mac <training>] [phy <training>] [line <training>]
```

**Advanced Gearbox Commands (available for MAC and Line-side ports only)**
```
[no] interface Ethernet <port> media-type [mac <type>] [line <type>]
[no] interface Ethernet <port> interface-type [mac <type>] [line <type>]
[no] interface Ethernet <port> advertised-speed [mac <speed>] [line <speed>]
[no] interface Ethernet <port> advertised-fec [mac <fec>] [line <fec>]
[no] interface Ethernet <port> advertised-autoneg [mac <autoneg>] [line <autoneg>]
[no] interface Ethernet <port> advertised-asym-pause [mac <pause>] [line <pause>]
[no] interface Ethernet <port> advertised-media-type [mac <type>] [line <type>]
```

**Gearbox Show**
```
show interface Gearbox status
-----------------------------------------------------------------------------------------------
Name       Lanes    Speed  Line-Lanes  Line-Speed  System-Lanes  System-Speed  Oper  Admin
---------------------------------------------------------------------------------------------
Ethernet0  101,102  40G    200,201     20G         202           40G           down  down
Ethernet1  103,104  40G    203,204     20G         205           40G           down  down
```

```
show interface Gearbox counters
-----------------------------------------------------------------------------------------------
TBD
-----------------------------------------------------------------------------------------------
```

### 3.7.4 Debug Commands

### 3.7.5 REST API Support

# 4 Serviceability and Debug
Standard logging is instrumented for existing components (as well as the Gearbox Manager), for example;
1. SWSS/ORCHAGENTs:
  * *SWSS_LOG_XXX*
2. syncd:
  * *SAI_LOG_LEVEL_XXX*

# 5 Warm Boot Support
The Gearbox configuration is present in the ASIC database and therefore should be compatible with existing SYNCD and its warm boot capabilities.

# 6 PHY Init Notifications
It may be desired to download new firmware and/or to re-initialize the PHY. PORTSORCH therefore listens for
*SAI_SWITCH_ATTR_SWITCH_STATE_CHANGE_NOTIFY* notifications to include the new *SAI_SWITCH_OPER_STATUS_INITIALIZE*
operational status. Upon notification, PORTSORCH will re-create the PHY with the newly specified configuration.

~~~
/**
 * @brief Attribute data for #SAI_SWITCH_ATTR_OPER_STATUS
 */
typedef enum _sai_switch_oper_status_t
{
    /** Unknown */
    SAI_SWITCH_OPER_STATUS_UNKNOWN,

    /** Up */
    SAI_SWITCH_OPER_STATUS_UP,

    /** Down */
    SAI_SWITCH_OPER_STATUS_DOWN,

    /** Switch encountered a fatal error */
    SAI_SWITCH_OPER_STATUS_FAILED,

    /** Switch received initialization request */
    SAI_SWITCH_OPER_STATUS_INITIALIZE,

} sai_switch_oper_status_t;
~~~

# 7 Scalability
- The Gearbox Manager and its implementation is not specific to any platform, but rather the existence of External PHYs.
- Although untested (due to limited gearbox capabilities) the Gearbox Manager should be able to support multiply-connected gearbox PHYs.

# 7 Unit Test
The Gearbox Manager has been instrumented to include unit tests such that each component can be tested and validated in isolation using mock SAI APIs.
Gearbox Manager has several categories relating to unit test.
- REDIS database mock testing
- SAI API Simulation
- Warm boot test cases


