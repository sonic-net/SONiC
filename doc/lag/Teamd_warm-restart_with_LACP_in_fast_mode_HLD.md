# Teamd warm-restart with LACP in fast mode HLD #

## Table of Content 

 * [Scope](#scope)
 * [Overview](#overview)
 * [Limitations](#limitations)
 * [High-Level Design](#high-level-design)
 * [CLI/YANG model Enhancements](#cliyang-model-enhancements)
 * [Testing Requirements/Design](#testing-requirementsdesign)
### Revision 

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 | 10/12/2022  |     timstian       | Initial version                   |
### Scope  

Teamd warm-restart with LACP in slow mode is already supported as described in [SONiC_Warmboot](/doc/warm-reboot/system-warmboot.md). This design is an enhancement to support teamd warm-restart with LACP in fast mode.

unplanned restart for Teamd docker is out of scope.

### Overview 

We expect the restart of teamd docker should not cause link flapping or any traffic loss. All lags at data plane should remain the same. But it's hard to implement in some scenarios.

During teamd warm-restart, the control plane remains up for a maximum of 90 seconds in LACP slow mode. However, in LACP fast mode, the control plane can only remain up for 3 seconds. This is because LACPDUs are sent every second. LACP protocol considers a LAG to be down if three LACPDUs are not received.

Teamd container is not restarted that fast, so teamd warm-restart in LACP fast mode always results in LAG down and the kernel LAG state in mess. However, in a data center, it is necessary to set LACP to fast mode to ensure faster link convergence and less traffic loss.

Let's take a look at the scenario shown in the figure below, there are multiple LAGs between switch_a and switch 1-n and LACP in fast mode, We can only control switch_a, other devices belong to other organizations and are not under our control. we want to upgrade the teamd container of switch_a without causing link flapping on other devices. Therefore, supporting teamd warm-restart in LACP fast mode is very important. With this feature, we can support teamd bug hotfixes and smooth upgrades.

![teamd upgread scenarios](/doc/lag/images/upgrade_scenarios.svg)

This design supports teamd warm-restart by switching between active and standby teamd container.

### Requirements

Support warm-restart teamd in LACP fast/slow mode

LACP protocol is not modified, LACP interaction is not affected

### Limitations

This design does not support the warm-reboot process. The reason is that during warm-reboot process, the kernel has been reset and the local end cannot continue to interact with the peer, which will be aware of the warm-reboot process.

During the teamd warm-restart process, no modification of the teamd-related configuration is allowed.

### Architecture Design 

This feature does not change the existing SONiC architecture.

### High-Level Design 

During the teamd warm-restart process, a new Teamd container is created, and the old and new teamd containers need to be fully synchronized before the old teamd container is killed. After the warm_restart upgrade_docker teamd action, only the new teamd container is left in the system. 

The process is divided into the following stages:

* stage 1: Waiting for ready state. We need to wait for all LAG processes to be created in the new teamd container and wait for processes to synchronize with the kernel module. 

* stage 2: Role change state. The old LAG processes are terminated with SIGUSR1 and the new LAG processes are enabled with SIGRTMIN.

* stage 3: Warm-restart finish state. The old teamd container will exit, and only the new teamd container is left.

![teamd smooth update](/doc/lag/images/teamd_smooth_upgrade.svg)

The teamd container contains multiple processes, such as teamd, teammgrd, teamdctl, teamsyncd, etc. teamd process can send and receive LACPDUs with the peer through the port. teamd can update the kernel module (team.ko) status via Netlink. teamsyncd can receive Netlink events and convert them to ASIC as configuration through SWSS.

![ teamd structure](/doc/lag/images/structure_of_teamd_container.svg)

During the teamd warm-restart process, the module interactions change as follows：

* stage 1: Waiting for ready state. The new teamd only receives data, and the interaction with the teamd container is one-way. The new teamd container does not modify the parameters of the kernel module and ASIC 

![teamd smooth update module interaction](/doc/lag/images/teamd_smooth_upgrade_module_interaction.svg)

* stage 2: Role change state. Old teamd processes receive SIGUSR1 and send the last LACPDU to the partner, Interacting with the new teamd container will become two-way after receive SIGRTMIN. The new teamd container start sending LACPDUs, and start modifying the parameters of the kernel module and ASIC

![teamd smooth update module interaction](/doc/lag/images/teamd_smooth_upgrade_module_interaction1.svg)

* stage 3: Warm-restart finish state. The old teamd container exits without setting parameters for the kernel or ASIC.

![teamd smooth update module interaction](/doc/lag/images/teamd_smooth_upgrade_module_interaction2.svg)


The flow of the teamd warm-restart process is as follows:
* a1. rename teamd container to teamd_bak container
* a2. create a new teamd container. (teamd flow: If teamd starts with the warm-restart flag, LACPDU is not sent and the parameters of the kernel module are not changed, but inconsistent data with kernel parameters need to be recorded in memory.)
* a3. wait for the teamd processes to ok in the new teamd container. Run teamdctl to get the new teamd status.
* b1. use SIGUSR1 to stop the old teamd processes. teamd and teamd_bak containers can share files so that the record files of LACPDU can be passed from the old container to the new one. (teamd flow: When SIGUSR1 is received, the old design is reused, the LACPDU record file is generated, and exit)
* b2. wait for SIGUSR1 processing, which must less than 3 seconds. Otherwise, LAG considers down.
* b3. use SIGRTMIN to apply data with the new teamd processes. (teamd flow: When SIGRTMIN is received, We will compare the data with the kernel and set the new data to the kernel and ASIC, start sending LACPDU, and update the kernel parameters in real-time when the LACP status changes)
* c1. delete teamd_bak container
![The flow of teamd smooth upgrade](/doc/lag/images/teamd_smooth_upgrade_flow.svg)

The process of warm_restart rollback_docker is the same as that for warm-restart above.
### SAI API 

NA

### Configuration and management 

NA

#### Manifest (if the feature is an Application Extension)

NA

#### CLI/YANG model Enhancements 

Several commands will be added.

* warm_restart --help

Usage: warm_restart [OPTIONS] COMMAND [ARGS]...
  docker upgrae manager

Options:
  --help  Show this message and exit.

Commands:
  rollback_docker      Rollback docker image to previous version
  upgrade_docker       Upgrade docker image from local binary or URL

* warm_restart upgrade_docker --help

Usage: warm_restart upgrade_docker [OPTIONS] <container_name> URL

  Upgrade docker image from local binary or URL

Options:
  -y, --yes
  --cleanup_image  Clean up old docker image
  --skip_check     Skip task check for docker upgrade
  --view_check     Enforce asic view check for docker upgrade
  --tag TEXT       Tag for the new docker image
  --warm           Perform warm upgrade
  --help           Show this message and exit.

* warm_restart rollback_docker --help

Usage: warm_restart rollback_docker [OPTIONS] <container_name>

  Rollback docker image to previous version

Options:
  -y, --yes
  --help     Show this message and exit.
#### Config DB Enhancements  

NA
		
### Warmboot and Fastboot Design Impact  

NA

### Restrictions/Limitations  

### Testing Requirements/Design  

Same as regular LAG testbed. LAG Configures LACP in fast mode.

* Running the warm_restart upgrade_docker or rollback command on the DUT is not expected to cause link flapping or traffic loss.

* During warm_restart process, down the physical link，the LAG status is not expected to be mess.
#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

NA