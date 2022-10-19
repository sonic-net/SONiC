# Fabric port support on Sonic

# High Level Design Document
#### Rev 1

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitionsabbreviations)
* [1 Requirements](#1-requirements)
* [2 Design](#2-design)
* [3 Testing](#3-testing)
* [4 Future Work](#4-future-work)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviations)

# List of Figures

# Revision
| Rev |     Date    |       Author       | Change Description |      
|:---:|:-----------:|:------------------:|--------------------|
| 1 | Aug-28 2020 | Ngoc Do, Eswaran Baskaran (Arista Networks) | Initial Version |
| 1.1 | Sep-1 2020 | Ngoc Do, Eswaran Baskaran (Arista Networks) | Add hotswap handling |
| 2 | Oct-20 2020 | Ngoc Do, Eswaran Baskaran (Arista Networks) | Update counter information |
| 2.1 | Nov-17 2020 | Ngoc Do, Eswaran Baskaran (Arista Networks) | Minor update on container starts |

# About this Manual

This document provides an overview of the SONiC support for fabric ports that are present in a VOQ-based chassis. These fabric ports are used to interconnect the forwarding Network Processing Units within the VOQ chassis.

# Scope

This document covers:
 
- Bring up of fabric ports in a VOQ chassis.
- Monitoring the fabric ports in forwarding and fabric chips. 

This document builds on top of the VOQ chassis architecture discussed [here](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) and the multi-ASIC architecture discussed [here](https://github.com/sonic-net/SONiC/blob/2f320430c8199132c686c06b5431ab93a86fb98f/doc/multi_asic/SONiC_multi_asic_hld.md). 

# Definitions/Abbreviations

|      |                    |                                |
|------|--------------------|--------------------------------|
| SSI | Supervisor SONiC Instance | SONiC OS instance on a central supervisor module that controls a cluster of forwarding instances and the interconnection fabric. |
| NPU | Network Processing Unit | Refers to the forwarding engine on a device that is responsible for packet forwarding. |
| ASIC | Application Specific Integrated Circuit | In addition to NPUs, also includes fabric chips that could forward packets or cells. | 
| cell | Fabric Data Units | The data units that traverse a cell-based chassis fabric. |

# 1 Requirements

Fabric ports are used in systems in which there are multiple forwarding ASICs are required to be connected. Traffic passes from one front panel port in a forwarding ASIC over a fabric network to one or multiple front panel ports on one or other ASICs. The fabric network is formed using fabric ASICs. Fabric links on the fabric network connect fabric ports on forwarding ASICs to fabric ports on fabric ASICs. 

High level requirements:

- SONiC needs to form a fabric network among forwarding ASICs, monitor and manage it. Monitoring could include link statistics, error monitoring and reporting, etc.  
- SONiC should be able to initialize fabric asics and manage them similar to how forwarding ASICs are managed - using syncd and sairedis calls. 

# 2 Design

## 2.1 Fabric ASICs

Fabric asics are used to form a fabric network for connecting forwarding ASICs. For each fabric port on a forwarding ASIC, there is a fabric link in the fabric network connecting to a fabric port on a fabric ASIC. There are typically multiple fabric links between a pair of (NPU, fabric ASIC) to balance traffic. We use the same approach to initializing and managing fabric ASICs as we are doing today for forwarding ASICs. A typical chassis implementation will be to manage all the fabric ASICs in a chassis from the control card or the Supervior Sonic Instance (SSI). We will leverage the work done in the multi-ASIC HLD and instantiate groups of containers for the fabric ASICs.

For each fabric ASIC, there will be:

- Database container
- Swss container
- Syncd container

Unlike forwarding ASICs, fabric ASICs do not have any front panel ports, but only fabric ports. So all the front panel port related containers like lldp, teamd and bgpd can be disabled for fabric ASICs. 

## 2.2 Database Schemas

```
DEVICE_METADATA|localhost: {
  "switch_type": “fabric”
  "switch_id": {{switch_id}}
}
```

Each fabric ASIC must be assigned a unique switch_id. The SAI VOQ specification recommends that this number be assigned to be different than the switch_id assigned to the forwarding ASICs in the chassis.

Fabric port status will be polled periodically and stored in table STATE_DB|FABRIC_PORT_TABLE. Typically, fabric port status about a fabric port includes:

- Status: Up or down
- If port is down, we may have some more information indicating reason e.g. CRC or misaligned
- If port is up, we should know remote peer information including peer switch_id and peer fabric port.

```
STATE_DB:FABRIC_PORT_TABLE:{{fabric_port_name}}
    "lane": {{number}}
    "status": “up|down”
    "crc": “yes”                           # if status: down
    "misaligned": “yes”                    # if status: down
    "remote_switch_id": {{number}}         # if status: up
    "remote_lane": {{number}}              # if status: up
```

Fabric port statistics include the following port counters:

```
    SAI_PORT_STAT_IF_IN_OCTETS,
    SAI_PORT_STAT_IF_IN_ERRORS,
    SAI_PORT_STAT_IF_IN_FABRIC_DATA_UNITS,
    SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES,
    SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES,
    SAI_PORT_STAT_IF_IN_FEC_SYMBOL_ERRORS,
    SAI_PORT_STAT_IF_OUT_OCTETS,
    SAI_PORT_STAT_IF_OUT_FABRIC_DATA_UNITS
```

FabricPortsOrch defines the port counters in FLEX_COUNTER_DB and syncd's existing FlexCounters thread periodically collects and saves these counters in COUNTER_DB. “show” cli commands read COUNTER_DB and display statistics information.

Fabric port also has a couple of queue counters. Similar to the port counters, the queue counters are also polled with FLEX_COUNTER_DB.
```
    SAI_QUEUE_STAT_WATERMARK_LEVEL,
    SAI_QUEUE_STAT_CURR_OCCUPANCY_BYTES,
    SAI_QUEUE_STAT_CURR_OCCUPANCY_LEVEL
```

Note that Linecard Sonic instances will also have STATE_DB|FABRIC_PORT_TABLE as well as port/queue counters because there are fabric ports in forwarding ASICs as well.

## 2.3 System Initialization

As part of multi-ASIC support, /etc/sonic/generated_services.conf contains the list of services which will be created for each asic when the system boots up. This is read by systemd-sonic-generator to generate the service files for each container that needs to run. 

Since the fabric ASIC doesn’t need lldp, bgpd and teamd containers to run, systemd-sonic-generator will be modified to not start these services for the fabric ASICs. A per-platform file called `asic_disabled_services` can list the services that are not needed for a given ASIC and systemd-sonic-generator will not generate the service files for these containers. For example,
```
0,lldp,teamd,bgp
1,lldp,teamd,bgp
2,lldp,teamd,bgp
```
will not start lldp, teamd and bgp containers for ASICs 0, 1 and 2.

NOTE: Longer term, we would like to use the FEATURE table to control which containers need to be started for fabric chips. However, that requires multi-ASIC support for the FEATURE table. This will be pursued as a separate project.

## 2.4 Fabric Card Hotswap

PMON will be responsible for detecting card presence and hotswap events using the get_change_event API. A new systemd service will be responsbile for turning on/off the service files for the syncd, database and swss containers that manage each fabric ASIC. When the fabric card is removed, the containers that manage the fabric ASICs that are part of that fabric card will be stopped. These will be re-started when the fabric card is inserted later.

## 2.5 Orchagent

Orchagent creates the switch using the SAI API similar to creating the switch for a forwarding ASIC, except that the switch type will be fabric. When the ASIC is initialized, all the fabric ports are initialized by default. The fabric ports are a subtype of SAI Port object and it can be obtained by getting all the fabric port objects from SAI. Since there are no front panel ports on a fabric ASIC, port_config.ini will be empty and portsyncd will not run. 

On fabric ASICs, OrchDaemon will only monitor and manage fabric ports. It will not maintain cpu port and front panel port related ochres, such as PortsOrch, IntfsOrch, NeighborOrch, VnetOrch, QosOrch, TunnelOrch, and etc. To simplify the change, we will just create FabricOrchDaemon inheriting OrchDaemon for fabric ASICs and this will only run FabricPortsOrch, the module responsible for managing fabric ports.

## 2.6 Fabric Ports in Forwarding ASICs

When a forwarding ASIC is initialized, the fabric ports are initialized by default by SAI. Orchagent will run FabricPortsOrch in addition to all the other orchs that needs to be run to manage the forwarding ASIC. Fabric port monitoring and handling is identical to what happens on a Fabric ASIC.

## 2.7 Cli commands

```
> show fabric counters -n <asic_namespace> [port_id]

asic2 fabric port counter (number of fabric ports: 192)

PORT            RxCells     TxCells      Crc       Fec  Corrected
-------------------------------------------------------------------------
 0           : 71660578         2         0         0         0
 1           : 71659798         1         0         0       213
 2           :        0         1         0         0       167
 3           :        0         2         0         0       193
```

### 2.7.1 Fabric Status

In a later phase, a `show fabric status` command will be added to show the remote switch ID and link ID for each fabric link of an ASIC. This will be obtained from the SAI_PORT_ATTR_FABRIC_REACHABILITY port attribute of the fabric port. Note that for fabric links that do not have a link partner because of the configuration of the chassis, this will show the status as `down`. The status will also be `down` for fabric links that are down due to some other physical error. To identify links that are down due to error vs links that are not expected to be up because of the chassis connectivity, we need to build up a list of expected fabric connectivity for each ASIC. This can be computed ahead of time based on the vendor configuration and populated in the minigraph. This will be implemented in a later phase.

# 3 Testing

Fabric port testing will rely on sonic-mgmt tests that can run on chassis hardware. 

- Test fabric port mapping: To verify the fabric mapping, we can inspect the remote switch ID that are saved in the STATE_DB and match that with the known chassis architecture. 

- Test traffic and counters: Send traffic through the chassis and verify traffic going through fabric ports via counters. 

# 4 Future Work

- In this proposal, all fabric ports on fabric ASICs or forwarding ASICs that join to form the fabric network will be enabled even when there are no peer ports available. We could provide a config model for the platforms to express the expected fabric connectivity and turn off unnecessary fabric ports. 

- Fabric ports that do not have a peer port will show up as a ‘down’ port. Fabric ports that do have a peer port could also go ‘down’ and there is no current way to differentiate this from a fabric port that does not have a peer port. This can be detected if the config model can express the expected fabric connectivity.

- Monitor, detect and disable fabric ports that consistently show errors.

