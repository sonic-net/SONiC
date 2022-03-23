# Fast-reboot new HLD

# Table of Contents
- [Fast-reboot new HLD](#fast-reboot-new-hld)
- [Table of Contents](#table-of-contents)
- [List of Figures](#list-of-figures)
- [1 Overview](#1-overview)
- [2 Functional Requirements](#2-functional-requirements)
- [3 Use Cases](#3-use-cases)
  - [3.1 In-Service restart and upgrade](#31-in-service-restart-and-upgrade)
- [4 Reconciliation at syncd](#4-reconciliation-at-syncd)
  - [4.1 Orchagent Point Of View](#41-orchagent-point-of-view)
  - [4.2 Syncd Point Of View - INIT/APPLY view framework](#42-syncd-point-of-view---initapply-view-framework)
  - [4.3 Reboot finalizer](#43-reboot-finalizer)

# List of Figures
* [System Flow](#42-syncd-point-of-view---initapply-view-framework)
* [Finalizer](#43-reboot-finalizer)

# 1 Overview

The goal of SONiC fast-reboot is to be able to restart and upgrade SONiC software with a data plane disruption less than 30 seconds and control plane less than 90 seconds. Today we don't have any indication of the fast-reboot status and some flows are delayed with a timer because of it, like enablement of flex counters. In order to have such indicator, re-use of the fastfast-reboot infrastructure can be used.

Each network application will experience similar processing flow.
Application and corresponding orchagent sub modules need to work together to restore the original data and push it to the ASIC.
Take neighbor as an example, upon restart operation every neighbor we had prior the reboot should be created again after resetting the ASIC.
We should also synchronize the actual neighbor state after recovering it, the MAC of the neighbor could have changed, went down for some reason etc.
In this case, restore_neighbors.py script will align the network state with the switch state by sending ARP/NDP to all known neighbors prior the reboot.
neighsyncd will update the internal cache with all neighbors and push all to APP DB, orchagent will then add/remove/update any neighbor and get syncd to program the HW with the new data.

In addition to the recover mechanism, the warmboot-finalizer can be enhanced to finalize fast-reboot as well and introduce a new flag indicating the process is done.
This new flag can be used later on for any functionality which we want to start only after init flow finished in case of fast-reboot.
This is to prevent interference in the fast-reboot reconciliation process and impair the performance, for example enablement of flex counters.

# 2 Functional Requirements

The new Fast-reboot design should meet the following requirments:

- Reboot the switch into a new SONiC software version using kexec.
- Upgrade the FW by the new SONiC image if needed.
- Recover all applications state with the new image to the previous state prior the reboot.
- Recover ASIC state after reset to the previous state prior the reboot.
- Control plane downtime will not exceed 90 seconds.
- Data plane downtime will not exceed 30 seconds.

# 3 Use Cases

## 3.1 In-Service restart and upgrade

### SWSS docker

When swss docker start with the new kernel, all the port/LAG, vlan, interface, arp and route data should be restored from CONFIG DB, APP DB, Linux Kernel and other reliable sources. There could be ARP, FDB changes during the restart window, proper sync processing should be performed.

### Syncd docker

The restart of syncd docker should leave data plane intact until it starts again with the new kernel. After restart, syncd configure the HW with the state prior the reboot by all network applications.

# 4 Reconciliation at syncd

## 4.1 Orchagent Point Of View

When orchagent start with the new SONiC image, the same infrastructure we use to reconsile fastfast-boot will start.
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

![System Flow](/doc/fast-reboot/Flow.svg)

## 4.3 Reboot finalizer

Today we have a tool used for warm-reboot to collect all reconsiliation flags from the different network applications.
This tool can be enhanced to consider fast-reboot as well and introduce a new flag indicating the end of the process.
This flag can be used to trigger any flow or application we want to delay until init flow has finished.

![Finalizer](/doc/fast-reboot/Finalizer.svg)
