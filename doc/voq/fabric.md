# Fabric port support on SONiC

# High Level Design Document

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitionsabbreviations)
* [Overview](#overview)
* [1 Requirements](#1-requirements)
* [2 Design](#2-design)
* [3 SAI API](#3-sai-api)
* [4 Configuration and management](#4-configuration-and-management)
* [5 Warmboot and Fastboot Design Impact](#5-warmboot-and-fastboot-design-impact)
* [6 Testing](#6-testing)
* [7 Open/Action items - if any](#7-openaction-items---if-any)
* [8 Restrictions/Limitations](#8-restrictionslimitations)

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
| 3 | Jun-3 2022 | Cheryl Sanchez, Jie Feng (Arista Networks) | Update on fabric link monitoring |
| 3.1 | Mar-30 2023 | Jie Feng (Arista Networks) | Update Overview, SAI API and Configuration and management section |
| 3.2 | May-01 2023 | Jie Feng (Arista Networks) | Update Counter tables information |
| 3.3 | Oct-31 2023 | Jie Feng (Arista Networks) | Update clear fabric counter commands |
| 3.4 | May-05 2024 | Jie Feng (Arista Networks) | Update CLI |

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

# Overview

This document provides an overview of the SONiC support for fabric ports that are present in a VOQ-based chassis. These fabric ports are used to interconnect the forwarding Network Processing Units within the VOQ chassis.

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

Fabric port is numbered as the chip fabric port number, the its status will be polled periodically and stored in table STATE_DB|FABRIC_PORT_TABLE. Typically, fabric port status about a fabric port includes:

- Status: Up or down
- If port is down, we may have some more information indicating reason e.g. CRC or misaligned
- If port is up, we should know remote peer information including peer switch_id and peer fabric port.

```
STATE_DB:FABRIC_PORT_TABLE:{{fabric_port_name}}
    "lane": {{number}}
    "status": “up|down”
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

FabricPortsOrch defines the port counters in FLEX_COUNTER_DB and syncd's existing FlexCounters thread periodically collects and saves these counters in COUNTER_DB. The counter oid is get from sai_serialize_object_id of the port. A “show” cli commands read COUNTER_DB and display statistics information. The example output of the cli is in section 2.7.

***Example***
"FLEX_COUNTER_TABLE:FABRIC_PORT_STAT_COUNTER:oid:0x10000000000df"

Fabric port also has a couple of queue counters. Similar to the port counters, the queue counters are also polled with FLEX_COUNTER_DB.
```
    SAI_QUEUE_STAT_WATERMARK_LEVEL,
    SAI_QUEUE_STAT_CURR_OCCUPANCY_BYTES,
    SAI_QUEUE_STAT_CURR_OCCUPANCY_LEVEL
```

***Example***
"FLEX_COUNTER_TABLE:FABRIC_QUEUE_STAT_COUNTER:oid:0x15000000000219"

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
> show fabric counters port
  ASIC    PORT    STATE    IN_CELL    IN_OCTET    OUT_CELL    OUT_OCTET    CRC    FEC_CORRECTABLE    FEC_UNCORRECTABLE    SYMBOL_ERR
------  ------  -------  ---------  ----------  ----------  -----------  -----  -----------------  -------------------  ------------
     0       0       up          1         135           0            0      0                 10           2009682570             0
     0       1     down          0           0           0            0      0                  0           5163529467             0
     0       2       up          1         206           2          403      0                 10           2015665810             0
```

```
> show fabric counters queue
  ASIC    PORT    STATE    QUEUE_ID    CURRENT_BYTE    CURRENT_LEVEL    WATERMARK_LEVEL
------  ------  -------  ----------  --------------  ---------------  -----------------
     0       0       up           0               0                0                 24
     0       1     down           0               0                0                 24
     0       2     down           0               0                0                 24
     0       3       up           0               0                0                 24
```

### 2.7.1 Fabric Status

In a later phase, a `show fabric reachability` command will be added to show the remote switch ID and link ID for each fabric link of an ASIC. The command will be added for both forwarding ASICs on Linecards and fabric ASICs on Fabric cards. This will be obtained from the SAI_PORT_ATTR_FABRIC_REACHABILITY port attribute of the fabric port. Note that for fabric links that do not have a link partner because of the configuration of the chassis, this will not shown in the command.

```
> show fabric reachability

asic0
  Local Link    Remote Module    Remote Link    Status
------------  ---------------  -------------  --------
          49                4             86        up
          50                2             87        up
          52                4             85        up
          54                2             93        up
....
```

## 2.8 Fabric Link Monitor

SONiC needs to monitor the fabric link status and take corresponding actions once an unhealthy link is detected to avoid traffic loss. Once the fabric link monitoring feature is enabled, SONiC needs to monitor the fabric capacity of a forwarding ASIC and take corresponding action once the capacity goes below the configured threshold.

The design of fabric link monitor is intentionally scoped to use local component state such as information local to a linecard or information local to a supervisor. This design simplifies the need for inter-component communication.

### 2.8.1 Monitor Fabric Link Status

Unhealthy fabric links may lead to traffic drops. Fabric link monitoring is an important tool to minimize traffic loss. The fabric link monitor algorithm monitors fabric link status and isolates the link if one or more criteria are true. By isolating a fabric link, the link is still up in the physical layer, but is taken out of service and does not distribute traffic. This feature is needed on both fabric ASICs and forwarding ASICs.

#### 2.8.1.1 Fabric link monitoring criteria

The fabric link monitoring algorithm checks two type of errors on a link: crc errors and uncorrectable errors.

The criteria can be extended to include checking other errors later.

#### 2.8.1.2 Monitoring algorithm

Instead of reacting to the counter changes, Orchagent adds a new poller and periodically polls status of all fabric links. By default, the total number of received cells, cells with crc errors, cells with uncorrectable errors are fetched from all serdes links periodically and the error rates are calculated using these numbers. If any one of the error rates is above the threshold for a number of consecutive polls, the link is identified as an unhealthy link. Then the link is automatically isolated to not distribute traffic.

#### 2.8.1.1 Cli commands

Several commands will be added to set fabric link monitor config parameters.
```
> config fabric port monitor error threshold <#crcCells> <#rxCells>
```
The above command can be used to set a fabric link monitoring error threshold.

#crcCells: Number of errors over specified number of received cells.
#rxCells: Total number of received cells in which errors are monitored.

If more than #crcCells out of #rxCells received cells seen with error, the fabric link needs to be isolated.

```
> config fabric port monitor poll threshold isolation <#polls>
```
The above command can be used to set the number of consecutive polls in which the threshold needs to be detected to isolate a link.

```
> config fabric port monitor poll threshold recovery <#polls>
```
The above command sets the number of consecutive polls in which no error is detected to unisolate a link .

```
> config fabric port isolate [port_id]
```

```
> config fabric port unisolate [port_id]
```


```
> config fabric port unisolate [port_id] --force
```

Besides the fabric link monitoring algorithm, the above two commands are added. The commands can be used to manually isolate and unisolate a fabric link ( i.e. take the link out of service and put the link back into service ). The two commands can help us debug on the system as well as a force option to unisolate a fabric link.


An additional show command is also added to show the fabric link isolation status of a system.

```
> show fabric isolation
asic0
  Local Link    Auto Isolated    Manual Isolated    Isolated
------------  ---------------  -----------------  ----------
           0                0                  1           1
           1                0                  0           0
           2                1                  0           1
....
```

### 2.8.2 Monitor Fabric Capacity

When the fabric link monitoring feature is enabled, fabric links may not be operational in a system due to link down, or link isolation by the monitoring algorithm. As a result, the effective capacity of total fabric links may be less than required bandwidth, and lead to performance degradation. Implementing a capacity monitoring algorithm in Orchagent will be useful to alert capacity changes. This feature is for forwarding ASICs on Linecards.

#### 2.8.2.1 Cli command

```
> config fabric monitor capacity threshold <5-100>
```
The above command is used to configure a capacity threshold to trigger alerts when total fabric link capacity goes below it.

A show command is added to display the fabric capacity on a system.

```
> show fabric monitor capacity
Monitored fabric capacity threshold: 90%

ASIC     Operating   Total #      %       Last Event   Last Time
         Links       of Links
-----    ------      --------     ----    ----------   ---------
0        110         112          98      None          Never
1        112         112          100     None          Never
....
```

#### 2.8.2.2 Monitoring algorithm

Orchagent will track the total number of fabric links that are isolated. Once the number of total operational fabric links is below a configured threshold, alert users with a system log. The action is very conservative in this document, and can be extended to other actions like shutdown the ASIC in the future.

### 2.8.3 Monitor Traffic on Fabric Links

Monitoring traffic on fabric links is another important tool to diagnose fabric hardware issues. It is useful to identify when traffic is unbalanced among fabric links which are connected to the same forwarding ASIC. It can also help identify miswired links.

#### 2.8.3.1 Cli command

The following proposed CLI is used to show the traffic among fabric links on both fabric ASICs and forwarding ASICs.

```
> show fabric counters rate

  ASIC    Link ID    Rx Data Mbps    Tx Data Mbps
------  ---------  --------------  --------------
 asic0          0               0            19.8
 asic0          1               0            19.8
 asic0          2               0            39.8
 asic0          3               0            39.8
 ....
```

# 3 SAI API

The fabric port monitoring adds a new attribute, SAI_PORT_ATTR_FABRIC_ISOLATE. The new API can be used to isolate fabric ports.

# 4 Configuration and management

## 4.1 Config DB Enhancements

Two tables are added into CONFIG DB for this feature.

The FABRIC_PORT table contains information on a fabric port's alias, isolated status, and lanes. Below is an example CONFIG DB snippet:

```
{
"FABRIC_PORT": {
    "Fabric0": {
        "alias": "Fabric0",
        "isolateStatus": "False",
        "lanes": "0"
    },
    "Fabric1": {
        "alias": "Fabric1",
        "isolateStatus": "False",
        "lanes": "1"
    }
}
```

The FABRIC_MONITOR table contains information related to fabric port monitoring. An sample CONFIG DB snippet is shown below.

```
{
"FABRIC_MONITOR": {
    "FABRIC_MONITOR_DATA": {
        "monErrThreshCrcCells": "1",
        "monErrThreshRxCells": "61035156",
        "monPollThreshIsolation": "1",
        "monPollThreshRecovery": "8"
    }
  }
}
```

## 4.2 CLI/YANG model Enhancements

A new module, sonic-fabric-port, is added for Fabric port table. Three new leaves added to this module, called isolateStatus, alias, and lanes.

Snippet of sonic-fabric-port.yang:

```
module sonic-fabric-port{
    ...
    container sonic-fabric-port {
        container FABRIC_PORT {
            description "FABRIC_PORT part of config_db.json";
            list FABRIC_PORT_LIST {
                key "name";

                leaf name {
                    type string {
                        length 1..128;
                    }
                }

                leaf isolateStatus {
                    type string {
                        pattern "False|True";
                    }
                }

               leaf alias {
                   type string {
                       length 1..128;
                   }
               }

               leaf lanes {
                   type string {
                       length 1..128;
                   }
               }
            } /* end of list FABRIC_PORT_LIST */
        } /* end of container FABRIC_PORT */
    } /* end of container sonic-fabric-port */
} /* end of module sonic-fabric-port */
```

Module sonic-fabric-monitor is added for FABRIC_MONITOR. New leaves are added as well for fabric port monitoring.

Snippet of sonic-fabric-monitor.yang:

```
module sonic-fabric-monitor{
    ...
    description "FABRIC_MONITOR yang Module for SONiC OS";

    container sonic-fabric-monitor {
        container FABRIC_MONITOR {
            description "FABRIC_MONITOR part of config_db.json";
            container FABRIC_MONITOR_DATA {

                leaf monErrThreshCrcCells {
                    type uint32;
                    default 1;
                }

                leaf monErrThreshRxCells {
                    type uint32;
                    default 61035156;
                }

                leaf monPollThreshIsolation {
                    type uint32;
                    default 1;
                }

                leaf monPollThreshRecovery {
                    type uint32;
                    default 8;
                }
            } /* end of container FABRIC_MONITOR_DATA */
        } /* end of container FABRIC_MONITOR */
    } /* end of container sonic-fabric-monitor */
} /* end of module sonic-fabric-monitor */

```


## 4.3 CLI

Several new CLI commands are added for this feature.

Command to display fabric counters port.

```
> show fabric counters port
```

Command to display fabric counters queue.

```
> show fabric counters queue
```

Command to clear fabric counters port.

```
sonic-clear fabriccountersport
```

Command to clear fabric counters queue.

```
sonic-clear fabriccountersqueue
```

Command to display fabric status.

```
> show fabric reachability
```

Command to set a fabric link monitoring error threshold.

```
> config fabric port monitor error threshold <#crcCells> <#rxCells>
```

Command to set the number of consecutive polls in which the threshold needs to be detected to isolate a link.

```
> config fabric port monitor poll threshold isolation <#polls>
```

Command to set the number of consecutive polls in which no error is detected to unisolate a link.

```
> config fabric port monitor poll threshold recovery <#polls>
```

Commands to manually isolate and unisolate a fabric link.

```
> config fabric port isolate [port_id]

> config fabric port unisolate [port_id]
```

Command to display the fabric link isolated status.

```
> show fabric isolation
```

Command to display the fabric capacity on a system.

```
> show fabric monitor capacity
```

Command to configure a capacity threshold to trigger alerts when total fabric link capacity goes below it.

```
> config fabric monitor capacity threshold < threshold >
```

Command to show the traffic among fabric links.

```
> show fabric counters rate mbps
```


# 5 Warmboot and Fastboot Design Impact

The existing warmboot/fastboot feature is not affected due to this design.

# 6 Testing

Fabric port testing will rely on sonic-mgmt tests that can run on chassis hardware.

- Test fabric port mapping: To verify the fabric mapping, we can inspect the remote switch ID that are saved in the STATE_DB and match that with the known chassis architecture. More comprehensive information about this testing can be found in the Chassis Fabric Test Plan document, which is available at testplan/Chassis-fabric-test-plan.md.

- Test traffic and counters: Send traffic through the chassis and verify traffic going through fabric ports via counters.

- Test fabric port monitoring:
  * Use the CLI to isolate/unisolate fabric ports, and verify whether the corresponding STATE_DB entries are updated.
  * Create simulated errors (e.g., CRC errors) on a fabric port, and confirm that the algorithm takes appropriate action and updates the corresponding STATE_DB entries.
  * Test fabric capcity monitoring: This test involves isolating/unisolating fabric ports on the system and checking that the 'show fabric capacity' command updates its output correctly to reflect the changes.

# 7 Open/Action items - if any

- In this proposal, all fabric ports on fabric ASICs or forwarding ASICs that join to form the fabric network will be enabled even when there are no peer ports available. We could provide a config model for the platforms to express the expected fabric connectivity and turn off unnecessary fabric ports.

- Fabric ports that do not have a peer port will show up as a ‘down’ port. Fabric ports that do have a peer port could also go ‘down’ and there is no current way to differentiate this from a fabric port that does not have a peer port. This can be detected if the config model can express the expected fabric connectivity.

# 8 Restrictions/Limitations

TBD
