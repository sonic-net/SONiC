# Unified Teamd Process for PortChannels

# High Level Design Document

# Revision
| Rev |     Date    |         Author               |          Change Description      |
|:---:|:-----------:|:----------------------------:|:--------------------------------:|
| 1.0 | 09/05/2025  | Praveen HM, Ashutosh Agrawal | Initial Version                  |

## Table of Contents

- [Unified Teamd Process for PortChannels](#unified-teamd-process-for-portchannels)
- [High Level Design Document](#high-level-design-document)
- [Revision](#revision)
  - [Table of Contents](#table-of-contents)
  - [Scope](#scope)
  - [Definitions](#definitions)
- [Overview](#overview)
  - [Teamd](#teamd)
  - [Current Design](#current-design)
  - [Problem Statement](#problem-statement)
  - [Requirements](#requirements)
- [Detailed Design](#detailed-design)
  - [Architecture Overview](#architecture-overview)
  - [TeamD](#teamd-1)
  - [Libteam](#libteam)
  - [Teamd Config Manager](#teamd-config-manager)
  - [Teamsyncd](#teamsyncd)
  - [tlm\_teamd](#tlm_teamd)
  - [Interaction Flow](#interaction-flow)
    - [Portchannel Add/Del Configuration Flow](#portchannel-adddel-configuration-flow)
    - [Portchannel Member Add/Del Configuration Flow](#portchannel-member-adddel-configuration-flow)
    - [State DB Update Flow for LAG and Member](#state-db-update-flow-for-lag-and-member)
    - [Link Event Flow](#link-event-flow)
  - [teamd operating mode](#teamd-operating-mode)
    - [DB Changes](#db-changes)
      - [Config DB](#config-db)
      - [CLI](#cli)
      - [YANG](#yang)
- [Testing](#testing)
  - [Test Cases](#test-cases)
- [References](#references)

## Scope

This document describes the high-level design for optimizing the teamd implementation in SONiC by consolidating multiple teamd processes into a single process to improve resource utilization and system performance.

## Definitions

- **TEAMD**: Team Daemon, a user-space application part of the Libteam project that manages network interface bonding.
- **LAG**: Link Aggregation Group, a method of combining multiple physical network connections into a single logical link.
- **LACP**: Link Aggregation Control Protocol, a protocol that controls the bundling of several physical ports to form a single logical channel.
- **AVL**: Adelson-Velsky and Landis, a self-balancing binary search tree used for efficient data management.
- **IPC**: Inter-Process Communication, methods for the exchange of data between multiple threads in one or more processes.

# Overview

## Teamd

Teamd (Team Daemon) is a user-space application that is part of the Libteam project, responsible for managing network interface bonding through the Team softdev Linux driver. It runs as a background service, managing team network devices (e.g., team0) and utilizes the Libteam library for communication and configuration. 

By working with multiple network interfaces, teamd enables link aggregation, load balancing, and high availability, ensuring efficient traffic distribution and redundancy. It operates through a runner-based architecture, allowing flexible and dynamic network interface management.

## Current Design

In the current SONiC implementation, a dedicated `teamd` process is spawned for each PortChannel interface inside the teamd container. Each instance handles its own:

- Runner (for LACP protocol handling)
- Link monitoring (via ethtool)
- Libteam interface for kernel communication

Communication between teamd and the team kernel driver happens via libteam. Configuration management is handled by teammgrd, which interacts with multiple teamd instances.

<div align="center"> <img src=images/architecture.png width=600 /> </div>

## Problem Statement

The current design of spawning a separate `teamd` process for each port channel can lead to increased memory and CPU usage, especially in large-scale deployments with many PortChannels.

------------------------------------------------
```
root@sonic:/# ps -aef 

UID          PID    PPID  C STIME TTY          TIME CMD 

root           1       0  0 Feb17 pts/0    00:03:32 /usr/bin/python3 /usr/local/bin/supervisord 

root           8       1  0 Feb17 pts/0    00:00:59 python3 /usr/bin/supervisor-proc-exit-listener --container-name teamd 

root          14       1  0 Feb17 pts/0    00:00:06 /usr/sbin/rsyslogd -n -iNONE

root          18       1  0 Feb17 pts/0    00:01:03 /usr/bin/teammgrd 

root          19       1  0 Feb17 pts/0    00:01:27 /usr/bin/tlm_teamd 

root          22       1  0 Feb17 pts/0    00:01:04 /usr/bin/teamsyncd 

root         128       1  0 Feb26 ?        00:00:30 /usr/bin/teamd -r -t PortChannel1 -c {"device":"PortChannel1","hwaddr":"22

root         133       0  0 Feb26 pts/1    00:00:00 bash 

root         281       1  0 13:03 ?        00:00:00 /usr/bin/teamd -r -t PortChannel2 -c {"device":"PortChannel2","hwaddr":"22

root         286       0  1 13:03 pts/2    00:00:00 bash 

root         292     286 50 13:03 pts/2    00:00:00 ps -aef 
```
-----------------------------------------------

## Requirements

The requirement is to consolidate the management of all PortChannel interfaces into a single teamd process. This unified process shall dynamically handle the configuration and state of all PortChannels, with the goal of reducing resource utilization and enhancing system maintainability.

All the teamd implementation shall be done as a patch and maintained under sonic community repo.

# Detailed Design

## Architecture Overview

The new architecture implements a single teamd process that manages multiple port channels:

<div align="center"> <img src=images/new_architecture.png width=600 /> </div>

The redesigned architecture focuses on improving resource efficiency and scalability through the following mechanisms:

- A single teamd process will manage all PortChannels, replacing the need for multiple per-instance processes.
- An AVL tree data structure will be used internally to enable fast and efficient lookups, insertions, and deletions.
- Shared resources such as netlink sockets will be reused across all managed PortChannels to reduce system overhead.
- Configuration updates from teammgrd will be handled via IPC messages.
- A new CLI command will be added to notify teamd to operate in multi-process (legacy) mode 

## TeamD
teamd shall support both unified and multi-process (legacy) operation modes. Upon startup, teammgrd determines the current mode of operation. If the mode is unified, teammgrd launches a single teamd instance using the following command:
```
/usr/bin/teamd -t teamd-unified -L /var/warmboot/teamd/ -g -d
```
In multi-process mode (the legacy behavior), teammgrd will spawn a separate teamd process for each PortChannel as they are created.

Refer section <PHM> for more details on how to set the mode.

During initialization, 
- The -t option and the argument to it is used to differentiate between single-process and multi-process modes of operation.
- When -t option with value "teamd-unified" is specified, the process runs in single-process mode, managing multiple PortChannels within a single teamd instance.
- When -t option with value "portdevname" is provided (e.g., -t PortChannel01), it runs in multi-process mode, where each PortChannel is managed by its own separate teamd process.

- A new global_context structure will be defined to store global configuration and state relevant to the entire teamd process. It maintains an AVL tree data structure for efficiently managing and accessing multiple team devices (portchannels).
- Common netlink sockets are created to handle all interface events from kernel.
- A single event loop will be defined to handle kernel events for all portchannels.
- A new unix socket is created for IPC communication with teammgrd and tlm_teamd. 

Once initialized, teamd can dynamically manage port channels based on configuration updates from teammgrd.

**Docker Container restart**

When the system starts, teamd operates in the new design where it runs in single-process mode and manages all PortChannels through IPC. To downgrade to the legacy design, the mode must be explicitly set to "multi-process" and the Docker container must be restarted. Similarly, to upgrade back to the new design, the "multi-process" mode configuration should be removed, followed by a Docker restart. Therefore, the mode setting must be correctly configured before restarting the container to ensure the system comes up in the desired operation mode.

Refer section <PHM> for more details on how to set the mode.

## Libteam

Libteam is a user-space library that provides APIs for creating, configuring, and managing team devices while interfacing with the kernel through netlink sockets. It also applies the runner logic to control link aggregation behavior in the kernel.

**Introduction of team_netlink Structure**

A new structure "team_netlink" will be defined in the libteam layer to hold all shared netlink socket details. This structure enables reuse of common socket connections across multiple team devices, avoiding the creation of individual netlink sockets for each instance.

**Optimized Netlink Communication**

A shared set of netlink sockets will be created once and used for communication with the kernel. These sockets will handle team-related control messages and events for all team (portchannel) devices, by maintaining a map between ifindex to corresponding portchannels.


### Teamd Config Manager

Teammgrd is responsible for listening the portchannel configuration and sends IPC messages to teamd using a Unix socket.
The format of the IPC message will be as follows:
```
| <opcode> | <msg_type> | <portchannel_name> | <data>
```

### Teamsyncd

Teamsyncd ensures seamless synchronization of LAG status by updating both STATE_DB and APP_DB with the latest operational information. It receives link state updates from the kernel via Netlink communication, processes them, and updates the databases to ensure the system accurately reflects the current status of LAG interfaces.
Teamsyncd uses libteam for creating netlink sockets. Abstraction apis will be implemented in libteam to store created netlink sockets accordingly. Apart from this, there will be no other change required in Teamsyncd module.

### tlm_teamd

tlm_teamd subscribes to the LAG table in STATE_DB to monitor changes and maintain accurate state synchronization. In the legacy design, libteamdctl was being used to fetch portchannel information from teamd and update to the STATE_DB. 
Alternatively, now tlm_teamd communicates with teamd over a Unix socket to retrieve detailed portchannel information. It sends IPC message to teamd and gets response back which it then uses to update STATE_DB with the latest portchannel information.

## Interaction Flow 

### Portchannel Add/Del Configuration Flow

When a new PortChannel is configured in the system, an entry is created in the CONFIG_DB, which teammgrd monitors. teammgrd sends PortChannelAdd IPC meesage to the teamd process.
Upon receiving this request, teamd communicates with the kernel to create the appropriate team network device interface. This involves several steps: first, teamd requests the kernel to create the team netdev interface, then it retrieves the ifindex from the kernel. Once the interface is created, teamd adds team-context data to the AVL tree with the retrieved ifindex and team device name as keys. After successful completion of these operations, teamd sends a REPLY_SUCCESS message back to teammgrd. If an error occurs during this process, the system is designed to retry the operation.

**IPC message for Portchannel addition**

```
| REQUEST  | PortChannelAdd    | <portchannel_name> | <config_json> |
  <opcode>     <msg_type> 

Sample config_json:
{"device":"PortChannel3","hwaddr":"22:26:87:a5:19:db","runner":{"active":true,"name":"lacp","min_ports":1}}

```
Similarly, when a PortChannel is deleted from CONFIG_DB, teammgrd sends a PortChannelRemove IPC to teamd. In response, teamd requests the kernel to delete the team netdev interface. Once the interface is removed, teamd removes the PortChannel context from its internal data structures and deletes the team device name and ifindex from the AVL tree. Upon successful completion, teamd sends a REPLY_SUCCESS message back to teammgrd, confirming that the deletion has been properly executed.

**IPC message for Portchannel Deletion**

msg_type - PortChannelRemove 

```
| REQUEST  | PortChannelRemove | <portchannel_name> | 
  <opcode>     <msg_type> 
```

<div align="center"> <img src=images/portchannel_add_del.png width=600 /> </div>


### Portchannel Member Add/Del Configuration Flow
When a member port is added to a PortChannel in CONFIG_DB, Teammgrd sends two IPC messages, PortConfigUpdate and PortAdd to the teamd process. Upon receiving these requests, teamd first looks up the teamd_context data structure from the AVL tree using the team_devname as a key. After locating the appropriate context, teamd communicates with the kernel to configure the specified port as a team member. Once the kernel successfully completes this configuration, teamd sends a REPLY_SUCCESS message back to teammgrd. If an error occurs during this process, the system is designed to retry the operation.


**IPC message for Portchannel member addition**

```
| REQUEST  |  PortAdd  | <portchannel_name> | <port_member>
  <opcode>   <msg_type> 

| REQUEST  | PortConfigUpdate | <portchannel_name> | <config_json> |
  <opcode>     <msg_type> 

Sample config_json:
{"lacp_key":12,"link_watch": {"name": "ethtool"} }
```

Similarly, when a member port is removed from a PortChannel in CONFIG_DB, teammgrd sends PortRemove IPC to teamd. Upon receiving this request, teamd again looks up the teamd_context from the AVL tree using the team_devname. After finding the context, teamd interacts with the kernel to remove the specified member from the PortChannel. When the kernel successfully completes the removal operation, teamd sends a REPLY_SUCCESS message back to teammgrd, confirming that the deletion has been properly executed.

**IPC message for Portchannel Member Deletion**

```
| REQUEST  | PortRemove  | <portchannel_name> | <port_member>
  <opcode>   <msg_type> 
```

In addition to these, the existing IPC message formats for port member addition and removal are reused. The key change is that these messages are now initiated by teammgrd instead of teamd_ctl calls. Furthermore, each message now includes the name of the associated port channel.

<div align="center"> <img src=images/portchannel_member_add_del.png width=600 /> </div>

### State DB Update Flow for LAG and Member

When a port goes UP/Down, the Linux kernel notifies teamsyncd via netlink. Teamsyncd processes the event and updates the relevant LAG entries in the STATE_DB and APP_DB , reflecting the operational status. The tlm_teamd component, which has subscribed to the LAG_TABLE in STATE_DB, gets notified of the update. Additionally, tlm_teamd sends a state dump request to teamd over a UNIX domain socket (IPC), prompting teamd to return its current view of LAG states. This flow ensures end-to-end synchronization of LAG status between the kernel, database layers, and the teamd process, maintaining accurate and consistent LAG state information throughout the system.

**IPC Request**

msg_type - StateDump

```
| REQUEST  | StateDump  | <portchannel_name> | <ipc_response>
  <opcode>   <msg_type> 
```

**IPC Response**
```
REPLY_SUCCESS <response>
```

<div align="center"> <img src=images/link_state.png width=600 /> </div>

### Link Event Flow
When a link state change occurs, the kernel sends a netlink notification, which is received by the registered libteam callback. Libteam parses the netlink message, extracts the index of the affected link, and invokes a lookup function registered by teamd. Teamd then retrieves the corresponding team_dev structure from its internal AVL tree and returns it to libteam. Using this structure, libteam processes the state change and informs teamd through its change handlers. Teamd then triggers the appropriate LACP logic to handle the link state transition, and any updates to link aggregation are communicated back to the kernel via libteam.

<div align="center"> <img src=images/link_event_flow.png width=600 /> </div>



## teamd operating mode 

teamd shall support both unified and multi-process (legacy) operation modes. By default teamd will operate in unified process mode. But if an user wants to revert to legacy teamd, then user has to update this mode into config DB.

### DB Changes

#### Config DB 
A new table named TEAMD will be introduced in the Config DB to support both the legacy and the new design.

```
{
  "TEAMD" : {
    "GLOBAL" : {
          "mode" : "multi-process"
      }
  }
}
```
In this schema, "mode": "multi-process" indicates the legacy design, where each teamd instance manages separate PortChannels. In contrast, the absence of this entry implies unified teamd.

To config the portchannel the existing cli is reused.

#### CLI

A new CLI command has been introduced to allow users to explicitly configure teamd operating mode.

The following CLI syntax is provided:

```
config portchannel mode multi-process enable/disable
```

#### YANG

```
module sonic-teamd {
    yang-version 1.1;

    namespace "http://github.com/sonic-net/sonic-teamd";
    prefix teamd;

    organization "SONiC";
    contact "SONiC";
    description "TEAMD global configuration for SONiC";

    revision 2025-05-06 {
        description "Initial revision with only multi-process mode";
    }

    container sonic-teamd {
        container TEAMD {
            description "TEAMD section of config_db.json";

            container GLOBAL {
                description "Global TEAMD configuration section";

                leaf mode {
                    description "TEAMD operation mode (fixed as multi-process)";
                    type string {
                        pattern "multi-process";
                    }
                    default "multi-process";
                    must "true()" {
                         description "WARNING: Changing or removing the mode will require a Docker restart for the changes to take effect.";
                    }
                }
            }
            /* end of GLOBAL */
        }
        /* end of TEAMD */
    }
    /* end of sonic-teamd */
}
```

# Testing

## Test Cases

The new implementation will be validated using existing test cases from the sonic-mgmt test suite.
These tests verify core LAG (PortChannel) functionality such as creation, member addition/removal, LACP negotiation, traffic forwarding, and state validation.

While the fundamental logic of LAG handling remains the same, necessary modifications will be made to the test cases to account for the new multi-device mode configuration. For instance, the setup steps may need to be updated to launch teamd with the -t all option when testing multi-device scenarios.


| Test Case | Description |
|-----------|-------------|
| Min-Link Verification | This test ensures that LAG interfaces maintain stability when links go down. It involves shutting down a LAG port on the DUT and verifying that the corresponding LAG interface is down. Traffic should be evenly distributed among remaining active LAGs, and after bringing the port back up, normal functionality should resume. |
| LACP Verification | This test ensures that LACP slow mode is correctly negotiated between DUT and VMs. Initially, VMs start with a fast LACP rate while the DUT is set to slow. After negotiation, all devices should align to the slow mode, where packets are sent at a rate of one per 30 seconds. |

**Testsuite and testscript path**

https://github.com/sonic-net/SONiC/wiki/LAG-Feature-Test-Suite
https://github.com/sonic-net/sonic-mgmt/tree/master/tests/pc

# References

1. [Infrastructure Specification - jpirko/libteam GitHub Wiki](https://github.com/jpirko/libteam/wiki/Infrastructure-Specification)
2. [SONiC/doc/Incremental IP LAG Update.md at master · sonic-net/SONiC](https://github.com/sonic-net/SONiC/blob/master/doc/Incremental%20IP%20LAG%20Update.md)
