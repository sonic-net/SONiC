# Fast-reboot Flow Improvements HLD

# Table of Contents
- [Fast-reboot Flow Improvements HLD](#fast-reboot-flow-improvements-hld)
- [Table of Contents](#table-of-contents)
- [List of Figures](#list-of-figures)
- [1 Overview](#1-overview)
- [2 Functional Requirements](#2-functional-requirements)
- [3 Use Cases](#3-use-cases)
  - [3.1 In-Service restart and upgrade](#31-in-service-restart-and-upgrade)
- [4 Reconciliation at syncd](#4-reconciliation-at-syncd)
  - [4.1 Orchagent Point Of View](#41-orchagent-point-of-view)
  - [4.2 Syncd Point Of View - INIT/APPLY view framework](#42-syncd-point-of-view---initapply-view-framework)
  - [4.3 neighsyncd Point Of View](#43-neighsyncd-point-of-view)
  - [4.4 fpmsyncd Point Of View](#44-fpmsyncd-point-of-view)
  - [4.5 Reboot finalizer](#45-reboot-finalizer)
- [5 SONiC Application Extension Infrastructre Integration](#5-sonic-application-extension-infrastructre-integration)

# List of Figures
* [Syncd and Orchagent](#42-syncd-point-of-view---initapply-view-framework)
* [Neighbors](#43-neighsyncd-point-of-view)
* [BGP](#44-fpmsyncd-point-of-view)
* [Finalizer](#45-reboot-finalizer)

# 1 Overview

The goal of SONiC fast-reboot is to be able to restart and upgrade SONiC software with a data plane disruption less than 30 seconds and control plane less than 90 seconds.
With current implementation there is no indication of the fast-reboot status, meaning we don't have a way to determine if the flow has finished or not.
Some feature flows in SONiC are delayed with a timer to keep the CPU dedicated to the fast-reboot init flow for best perforamnce, like enablement of flex counters.
In order to have such indicator, re-use of the fastfast-reboot infrastructure can be used.

Each network application will experience similar processing flow.
Application and corresponding orchagent sub modules need to work together to restore the preboot state and push it to the ASIC.
Take neighbor as an example, upon restart operation every neighbor we had prior to the reboot should be created again after resetting the ASIC.
We should also synchronize the actual neighbor state after recovering it, the MAC of the neighbor could have changed, went down for some reason etc.
In this case, restore_neighbors.py script will align the network state with the switch state by sending ARP/NDP to all known neighbors prior the reboot.
neighsyncd will update the internal cache with all neighbors and push all to APP DB, orchagent will then add/remove/update any neighbor and get syncd to program the HW with the new data.

In addition to the recover mechanism, the warmboot-finalizer can be enhanced to finalize fast-reboot as well and introduce a new flag indicating the process is done.
This new flag can be used later on for any functionality, we want to start only after init flow finished in case of fast-reboot.
This is to prevent interference in the fast-reboot reconciliation process and impair the performance, for example enablement of flex counters.

References:
https://github.com/Azure/SONiC/blob/master/doc/fast-reboot/fastreboot.pdf
https://github.com/Azure/sonic-swss/blob/master/neighsyncd/restore_neighbors.py
https://github.com/Azure/sonic-buildimage/blob/master/dockers/docker-orchagent/enable_counters.py

# 2 Functional Requirements

The new Fast-reboot design should meet the following requirments:

- Reboot the switch into a new SONiC software version using kexec - less than 5 seconds.
- Upgrade the switch FW by the new SONiC image if needed.
- Recover all application's state with the new image to the previous state prior the reboot.
- Recover ASIC state after reset to the previous state prior the reboot.
- Recover the Kernel internal DB state after reset to the previous state prior the reboot.
- Sync the Kernel and ASIC with changes on the network which happen during fast-reboot.
- Control plane downtime will not exceed 90 seconds.
- Data plane downtime will not exceed 30 seconds.

# 3 Use Cases

## 3.1 In-Service restart and upgrade

### SWSS docker

When swss docker starts with the new kernel, all the port/LAG, vlan, interface, arp and route data should be restored from CONFIG DB, APP DB, Linux Kernel and other reliable sources. There could be ARP, FDB changes during the restart window, proper sync processing should be performed.

### Syncd docker

The restart of syncd docker should leave data plane intact until it starts again with the new kernel. After restart, syncd configures the HW with the state prior the reboot by all network applications.

# 4 Reconciliation at syncd

## 4.1 Orchagent Point Of View

When orchagent starts with the new SONiC image, the same infrastructure we use to reconcile fastfast-boot will start.
After INIT_VIEW and create_switch functions sent to syncd (reset of the ASIC took place here), 'warmRestoreAndSyncUp' will be executed.
This function will populate m_toSync with all tasks for syncd, by APP DB and CONFIG DB prior the reboot.
To verify orchagent reached the same state as before the reboot, 'warmRestoreValidation' will verify no pending tasks left in the queue, meaning all proccessed succesfully and in the pipeline for syncd to configure the HW.
At the end APPLY_VIEW will be sent to syncd to finalize the process, from this point orchagent enter the main loop and operates normally.

### NOTICE

'warmRestoreValidation' might fail the operation just like in fastfast-reboot case, if the way orchagent process an event from the DB is handled differently with the new software version the task will fail to execute and fast-reboot will fail along with it.
This is solvable by the db migrator.

## 4.2 Syncd Point Of View - INIT/APPLY view framework

Syncd starts with the fast-reboot flag, trigger the ASIC reset when create_switch is requested from orchagent.
In addition, on this case temp view flag will set to false since it is not required, no comparison logic needed since current view is empty.
Basically INIT and APPLY view requests from orchagent are ignored by syncd, but bound the process from start to end.
During reconsilations process of orchagent, syncd will recieve all tasks to restore the previous state.
All other network applications will do the same as we do today for warm-reboot.

![Syncd](/doc/fast-reboot/Orchagent_Syncd.svg)

## 4.3 neighsyncd Point Of View

Neighbors configuration is a crucial part of the L3 switch software. It is best when the neighbor configuration on the hardware is in sync with the actual switch neighbors on the network. It can't be assumed that neighbors won't change during warm restart window, while the software is restarting, the SONiC switch software has to be ready for scenarios in which during the restart window:
 - Existing neighbors went down, e.g: VMs crashed on the server connected to ToR switch which undergoes fast-reboot.
 - New neighbors appeared on the network, e.g: VMs created on the server connected to ToR switch which undergoes fast-reboot.
 - MAC changes, e.g: VMs re-created or re-configured on the server connected to ToR switch which undergoes fast-reboot.

![Neighbors](/doc/fast-reboot/Neighbors.svg)

## 4.4 fpmsyncd Point Of View

 - When BGP on a router restarts, all the BGP peers detect that the session went down and then came up. This "down/up" transition results in a "routing flap" and causes BGP route re-computation, generation of BGP routing updates, and unnecessary churn to the forwarding tables.
 - BGP capability, termed "Graceful Restart Capability", is defined that would allow a BGP speaker to express its ability to preserve forwarding state during BGP restart.
 - An UPDATE message with no reachable Network Layer Reachability Information (NLRI) and empty withdrawn NLRI is specified as the End-of-RIB marker that can be used by a BGP speaker to indicate to its peer the completion of the initial routing update after the session is established.

![BGP](/doc/fast-reboot/BGP.svg)

## 4.5 Reboot finalizer

Today we have a tool used for warm-reboot to collect all reconsiliation flags from the different network applications.
This tool can be enhanced to consider fast-reboot as well and introduce a new flag indicating the end of the process.
This flag can be used to trigger any flow or application we want to delay until init flow has finished.

![Finalizer](/doc/fast-reboot/Finalizer.svg)

# 5 SONiC Application Extension Infrastructre Integration

A SONiC package can specify an order of shutdown on fast-reboot for a service. A "bgp" may specify "radv" in this field in order to avoid radv to announce departure and cause hosts to lose default gateway, while "teamd" service has to stop before "syncd", but after "swss" to be able to send the last LACP PDU through CPU port right before CPU port becomes unavailable.

The fast-reboot service shutdown script has to be auto-generated from a template /usr/share/sonic/templates/fast-shutdown.sh.j2. The template is derived from the fast-reboot script from sonic-utlities.

A services shutdown is an ordered executions of systemctl stop {{ service }} commands with an exception for "swss" service after which a syncd pre-shutdown is requested and database backup is prepared for next boot. A service specific actions that are executed on fast-shutdown are hidden inside the service stop script action.

NOTE: the assumption here is that syncd pre-shutdown is bound to swss service stop when swss service is doing system level shutdown.

The *-shutdown.sh are imported and executed in corresponding *-reboot scripts.

###### fast-shutdown.sh.j2 snippet
```
...
{% for service in shutdown_orider %}
systemctl stop {{ service }}
{% endfor %}
...
```

reboot-finalizer.sh (warm-finalizer.sh) script must also be templatized and updated based on process reconciles flag.

###### manifest path

| Path                          | Value           | Mandatory | Description                                                                                                          |
| ----------------------------- | --------------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| /service/fast-shutdown/       | object          | no        | Fast reboot related properties. Used to generate the fast-reboot script.                                             |
| /service/fast-shutdown/after  | lits of strings | no        | Same as for warm-shutdown.                                                                                           |
| /service/fast-shutdown/before | lits of strings | no        | Same as for warm-shutdown.                                                                                           |
| /processes                    | object          | no        | Processes infromation                                                                                                |
| /processes/[name]/reconciles  | boolean         | no        | Wether process performs warm-boot reconciliation, the warmboot-finalizer service has to wait for. Defaults to False. |


This chapter it taken from SONiC Application Extension Infrastructure HLD:
https://github.com/Azure/SONiC/blob/master/doc/sonic-application-extension/sonic-application-extention-hld.md#warmboot-and-fastboot-design-impact
