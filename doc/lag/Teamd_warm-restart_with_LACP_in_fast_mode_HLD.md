# Teamd warm-restart with LACP in fast mode HLD #

## Table of Content 

### Revision  

### Scope  

This design supports teamd warm-restart in fast mode.

### Definitions/Abbreviations 

NA

### Overview 

We expect that the restart of teamd docker should not cause link flapping or any traffic loss. All lags at data plane should remain the same. But it's hard to implement in some scenarios.

During teamd warm-restart, the control plane remains up for a maximum of 90 seconds in LACP slow mode. However, in LACP fast mode, the control plane can only remain up for 3 seconds. This is because LACPDUs are sent every second. LACP protocol considers a LAG to be down if three LACPDUs are not received.

Teamd containers are not restarted that fast, so teamd warm-restart in LACP fast mode always results in lag down and the kernel LAG state in mess. However, in a data center, it is necessary to set LACP to fast mode to ensure faster link convergence and less traffic loss.

Therefore, supporting teamd warm-restart in LACP fast mode is very important. With this feature, we can support teamd bug hotfix and smooth upgrades.

This design supports teamd warm-restart in fast mode by switching between active and standby teamd container.

### Requirements

Support warm-restart teamd in LACP fast mode

LACP protocol is not modified, Lacp interaction is not affected

### Limitations

This design does not support the warm-reboot process. The reason is that during warm-reboot process, the kernel has been reset and the local end cannot continue to interact with the peer, which will be aware of the warm-reboot process.

During the teamd warm-restart process, no modification of the teamd-related configuration is allowed.

### Architecture Design 

NA

### High-Level Design 
During the teamd warm-restart process, a new Teamd container is created, and the old and new Teamd containers need to be fully synchronized before the old Teamd container is killed. After the warm-restart action, only the new teamd is run.

![teamd smooth update](/doc/lag/images/teamd_smooth_upgrade.svg)

Teamd container contains multiple processes, such as teamd, teammgrd, teamdctl, teamsyncd etc. teamd process can send and receive LACPDUs with the peer through the port. teamd can update kernel module (team.ko) status via netlink. teamsyncd can receive netlink events and convert them to ASIC as configuration.

![ teamd structure](/doc/lag/images/structure_of_teamd_container.svg)

During the teamd warm-restart process, the modules interact as follows
![teamd smooth update module interaction](/doc/lag/images/teamd_smooth_upgrade_module_interaction.svg)



The flow of teamd warm-restart
![The flow of teamd smooth upgrade](/doc/lag/images/teamd_smooth_upgrade_flow.svg)

The flow of sonic_installer or warm_restart is :
1. rename teamd container to teamd_bak container
2. create new teamd container
3. wait for teamd process ok in new teamd container
4. use SIGUSR1 to stop old teamd process.(teamd and teamd_bak container can share files so that the record files of lacpdu can be passed from the old container to the new one )
5. delete teamd_bak container
6. use SIGUSR2 to apply data with new teamd process

The flow of teamd process is:
1. If  teamd start with the warm-restart flag, lacpdu is not sent and the parameters of the kernel module are not changed, but inconsistent data with kernel parameters need to be recorded in memory.

2. When SIGUSR2 is received, compare the data and set it to the kernel and ASIC, start sending lacpdu, and update the kernel parameters in real time when the lacp status changes

3. When SIGUSR1 is received, the old design is reused, LACPDU record file is generated, and exit

### SAI API 

NA

### Configuration and management 

NA

#### Manifest (if the feature is an Application Extension)

NA

#### CLI/YANG model Enhancements 

NA

#### Config DB Enhancements  

NA
		
### Warmboot and Fastboot Design Impact  

NA

### Restrictions/Limitations  

### Testing Requirements/Design  
NA

#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

NA