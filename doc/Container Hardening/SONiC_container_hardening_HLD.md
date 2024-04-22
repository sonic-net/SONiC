# SONiC Container Hardening #

## Table of Content
- [SONiC Container Hardening](#sonic-container-hardening)
	- [Table of Content](#table-of-content)
	- [List of Tables](#list-of-tables)
	- [Revision](#revision)
	- [Scope](#scope)
	- [Definitions/Abbreviations](#definitionsabbreviations)
	- [1. Overview](#1-overview)
	- [2. Requirements](#2-requirements)
	- [3. Architecture Design](#3-architecture-design)
		- [3.1 Root privileges](#31-root-privileges)
		- [3.2 net=host](#32-nethost)
	- [4. High-Level Design](#4-high-level-design)
		- [4.1 Root privileges removal](#41-root-privileges-removal)
			- [Docker privileges](#docker-privileges)
		- [4.2 net=host optimization](#42-nethost-optimization)
			- [How to check?](#how-to-check)
	- [5. SAI API](#5-sai-api)
	- [6. Configuration and management](#6-configuration-and-management)
		- [6.1. Manifest (if the feature is an Application Extension)](#61-manifest-if-the-feature-is-an-application-extension)
		- [6.2. CLI/YANG model Enhancements](#62-cliyang-model-enhancements)
		- [6.3. Config DB Enhancements](#63-config-db-enhancements)
	- [7. Warmboot and Fastboot Design Impact](#7-warmboot-and-fastboot-design-impact)
	- [8. Restrictions/Limitations](#8-restrictionslimitations)
	- [9. Testing Requirements/Design](#9-testing-requirementsdesign)
		- [9.1 Unit Test cases](#91-unit-test-cases)
		- [9.2 System Test cases](#92-system-test-cases)
	- [10. Open/Action items - if any](#10-openaction-items---if-any)
	- [Appendix A: Further reading](#appendix-a-further-reading)
	- [Appendix B: Linux Capabilities](#appendix-b-linux-capabilities)
 	- [Appendix C: Container List](#appendix-c-container-list)

## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: Abbreviations](#table-2-abbreviations)
* [Table 3: Default Linux capabilities](#table-3-default-linux-capabilities)
* [Table 4: Extended Linux capabilities](#table-4-extended-linux-capabilities)

## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             |                    | Initial version                   |

## Scope

This section describes the requirements, goals, and recommendations of the container hardening item for SONiC.

## Definitions/Abbreviations
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| OS                       | Operating System                           |
| API                      | Application Programmable Interface         |
| SAI                      | Swich Abstraction Interface                |

## 1. Overview

Containers is a method of creating virtualization and abstraction of an OS for a subset of processes/service on top of a single host with the purpose of giving it an environment to run and execute its tasks without effect of nearby containers/processes.

In SONiC, we are deploying containers with full visibility and capabilities as the host Linux.

This poses a security risk and vulnerability as a single breached container means that the whole system is breached.

Addressing this issue – we have composed this doc for container hardening, describing the security hardening requirements and definitions for all containers on top of SONiC.

## 2. Requirements

What are we trying to achieve here?

We would like to increase the security in SONiC so that an attack on a specific container will not compromise the whole system.

To do so, we'll tackle the following areas:
1. Privileges
2. Network
3. Capabilities
4. Mount namespace
5. Cgroups
6. Etc

For now, we will focus on #1 & #2

Further guidelines and requirements will be brought upon in the future on-demand.

## 3. Architecture Design

### 3.1 Root privileges

When removing the root privileges from a specific container - we are required to remove the `--privileged` flag and add the required missing Linux capabilities to the docker, or alternatively adjust the container so that it does not require root privileges to perform any action.

### 3.2 net=host

Removing the `net=host` is required to prevent the container from accessing the full network scope of the host and system.
When doing this removal - we will start getting failures from devices that require external access and packet transfers between the container and the host to the interfaces.
In order to overcome this obstacle - we have a few options here:
- using `--net=bridge` and port forwarding

## 4. High-Level Design

### 4.1 Root privileges removal
Removing the `--privileged` flag is done by editing the docker_image_ctl.j2 file:

docker_image_ctl.j2 file

	docker create {{docker_image_run_opt}} \ # *Need to modify this parameter "docker_image_run_opt" to not contain the --privileged flag*
	{/%- if docker_container_name != "database" /%}
		--net=$NET \
		--uts=host \{# W/A: this should be set per-docker, for those dockers which really need host's UTS namespace #}
	{/%- endif /%}
	{/%- if docker_container_name == "database" /%}
		-p 6379:6379 \
	{/%- endif /%}
		-e RUNTIME_OWNER=local \
	{/%- if install_debug_image == "y" /%}
		-v /src:/src:ro -v /debug:/debug:rw \
	{/%- endif /%}
	{/%- if '--log-driver=json-file' in docker_image_run_opt or '--log-driver' not in docker_image_run_opt /%}
		--log-opt max-size=2M --log-opt max-file=5 \
	{/%- endif /%}

This will cause the docker file to be altered in the following manner:

**database.sh file**

	docker create --privileged -t -v /etc/sonic:/etc/sonic:ro \ # *Need to remove the --privileged flag*
		-p 6379:6379 \
		-e RUNTIME_OWNER=local \
		--log-opt max-size=2M --log-opt max-file=5 \
		--tmpfs /tmp \
		$DB_OPT \
		$REDIS_MNT \
		-v /usr/share/sonic/device/$PLATFORM:/usr/share/sonic/platform:ro \
		--tmpfs /var/tmp \
		--env "NAMESPACE_ID"="$DEV" \
		--env "NAMESPACE_PREFIX"="$NAMESPACE_PREFIX" \
		--env "NAMESPACE_COUNT"=$NUM_ASIC \
		--name=$DOCKERNAME \
		docker-database:latest \
		|| {
			echo "Failed to docker run" >&1
			exit 4
		}

#### Docker privileges
Removing the root privileges from the docker container - will remove some Linux capabilities that are inherited from the root level permissions.

Running the capabilities list command on a privileged container, this includes all capabilities captured in both [Table 3: Default Linux capabilities](#table-3-default-linux-capabilities) and [Table 4: Extended Linux capabilities](#table-4-extended-linux-capabilities)

	root@ce2c36a0b20c:/# capsh --print
	Current: = cap_chown,cap_dac_override,cap_dac_read_search,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_linux_immutable,cap_net_bind_service,cap_net_broadcast,cap_net_admin,cap_net_raw,cap_ipc_lock,cap_ipc_owner,cap_sys_module,cap_sys_rawio,cap_sys_chroot,cap_sys_ptrace,cap_sys_pacct,cap_sys_admin,cap_sys_boot,cap_sys_nice,cap_sys_resource,cap_sys_time,cap_sys_tty_config,cap_mknod,cap_lease,cap_audit_write,cap_audit_control,cap_setfcap,cap_mac_override,cap_mac_admin,cap_syslog,cap_wake_alarm,cap_block_suspend,cap_audit_read+eip

Running the capabilities list command on an un-privileged container, this includes all capabilities captured in [Table 3: Default Linux capabilities](#table-3-default-linux-capabilities):

	root@ce2c36a0b20c:/# capsh --print
	Current: cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap=eip

If, for some reason, a docker must retain a specific capablity functionality on top of the container (which is removed after removing the `--privileged` flag), we can do that with the following:

In the docker-database.mk file adjust this line:

        $(DOCKER_DATABASE)_RUN_OPT += -t –-cap-add NET_ADMIN  # Changed by removing the --privileged flag and adding --cap-add flag

### 4.2 net=host optimization

Here we will provide a detailed example of how to switch from the `--net=host` configuration (host network) to the `--net=bridge` configuration paired with port forwarding in a specific container. We are using the database container as an example for this item.

The original docker creation should be like in the example below:

docker with host sharing:

	docker create --privileged -t -v /etc/sonic:/etc/sonic:ro  \
					--net=$NET \
					-e RUNTIME_OWNER=local \
					--uts=host \
					--log-opt max-size=2M --log-opt max-file=5 \
					--tmpfs /tmp \
					$DB_OPT \
					$REDIS_MNT \
					-v /usr/share/sonic/device/$PLATFORM:/usr/share/sonic/platform:ro \
					--tmpfs /var/tmp \
					--env "NAMESPACE_ID"="$DEV" \
					--env "NAMESPACE_PREFIX"="$NAMESPACE_PREFIX" \
					--env "NAMESPACE_COUNT"=$NUM_ASIC \
					--name=database_no_net \
					--cap-drop=NET_ADMIN \
					docker-database:latest

To disable the sharing of the networking stack between the host and a container we need to remove the flag: `--net=host`. Because we have not specified any `--network` flag, the containers connect to the default bridge network `--net=bridge`.
To support port forwarding we are required to add the flag:  `-p <port>:<port>`

The "new" docker creation file database.sh can be seen in the code block below:

Docker with port forwarding and default bridge network

	docker create --privileged -t -v /etc/sonic:/etc/sonic:ro  \
					**-p 6379:6379** \
					-e RUNTIME_OWNER=local \
					--uts=host \
					--log-opt max-size=2M --log-opt max-file=5 \
					--tmpfs /tmp \
					$DB_OPT \
					$REDIS_MNT \
					-v /usr/share/sonic/device/$PLATFORM:/usr/share/sonic/platform:ro \
					--tmpfs /var/tmp \
					--env "NAMESPACE_ID"="$DEV" \
					--env "NAMESPACE_PREFIX"="$NAMESPACE_PREFIX" \
					--env "NAMESPACE_COUNT"=$NUM_ASIC \
					--name=$DOCKERNAME \
					docker-database:latest \

**How we did it?**

To create a docker with the flags above it is required to set the "new" flag in the file docker_image_ctl.js. Follow the call `docker create {{docker_image_run_opt}} \`: 
and replace the `–--net=$NET`.
docker flag generation

	{/%- if docker_container_name != "database" /%}
					--net=$NET \
	{/%- endif /%}
	{/%- if docker_container_name == "database" /%}
					-p 6379:6379 \
	{/%- endif /%}

#### How to check?

Go into the docker - `docker exec -it docker bash`
Run `ifconfig`.

On a docker with host network - you'll be able to view all physical interfaces.
On a docker without host network - we'll see only eth0 and lo.

Note - we are not committing to user defined bridges at this stage.
Once we manage to stabalize the system without host network and without root privileges on top of the containers we can move to the next step of user defined bridges.
This will either be an expansion of this HLD or an HLD of its own.

## 5. SAI API

N/A

## 6. Configuration and management

N/A - no configuration management/changes are required.

### 6.1. Manifest (if the feature is an Application Extension)

N/A

### 6.2. CLI/YANG model Enhancements

N/A
We are not adding CLI commands or management capabilities to the system with this item.

### 6.3. Config DB Enhancements

N/A - DB should remain the same

## 7. Warmboot and Fastboot Design Impact

No impact on all boot sequences, as this item should be seemlessly integrated into the system and achieve the same functionality level as before.

## 8. Restrictions/Limitations

## 9. Testing Requirements/Design

To define this item completed - we are required to run the full CI and check that nothing has been broken from the changes proposed in this HLD.
In addition - we should test that the mitigations are applicable for the relevant containers.

### 9.1 Unit Test cases

N/A, this feature will be checked on a system level.

### 9.2 System Test cases

For general fucntionality flows-  running the same test cases that we currently have on top of our system and verifying that nothing broke.

For adidtional security test cases, we should check that priviliges and network capabilities have been removed.
Net=$HOST removal test:
1. Login to container with removed network capabilities
2. Run ls /dev/
3. Check that we do not have visibility to all network devices (no tty9/8 no sda, etc')

Privilege removal test:
1. Login to container without --privileged flag
2. Check that you cannot access /etc/shadow
3. Check that you cannot perform vim for /boot folder or any file in it

## 10. Open/Action items - if any

Currently, Nvidia and MSFT have scoped commitment for specific containers.
Redis and SNMP already have these adjustments.
What remains is to perform this container hardening for all other containers in the system so that the whole echo-system will comply to these security hardening requirements.

## Appendix A: Further reading

[Linux Capabilities 101](https://linux-audit.com/linux-capabilities-101/)

[Understanding Linux Capabilities](https://tbhaxor.com/understanding-linux-capabilities/)

[Linux Namespaces Wiki](https://en.wikipedia.org/wiki/Linux_namespaces)

## Appendix B: Linux Capabilities

The following table lists the Linux capability options which are allowed by default and can be dropped.
###### Table 3: Default Linux capabilities
| Capability Key        | Capability Description |
| -----------                   | ----------- |
| AUDIT_WRITE                   | Write records to kernel auditing log                                                                  |
| CHOWN                                 | Make arbitrary changes to file UIDs and GIDs (see chown(2)).                     |
| DAC_OVERRIDE                  | Bypass file read, write, and execute permission checks.        |
| FOWNER                                | Bypass permission checks on operations that normally require the file system UID of the process to match the UID of the file.        |
| FSETID                                | Don’t clear set-user-ID and set-group-ID permission bits when a file is modified.        |
| KILL                                  | Bypass permission checks for sending signals        |
| MKNOD                                 | Create special files using mknod(2).        |
| NET_BIND_SERVICE              | Bind a socket to internet domain privileged ports (port numbers less than 1024).         |
| NET_RAW                               | Use RAW and PACKET sockets        |
| SETFCAP                               | Set file capabilities        |
| SETGID                                | Make arbitrary manipulations of process GIDs and supplementary GID list.        |
| SETPCAP                               | Modify process capabilities        |
| SETUID                                | Make arbitrary manipulations of process UIDs.        |
| SYS_CHROOT                    | Use chroot(2), change root directory.        |

The next table shows the capabilities which are not granted by default and may be added.
###### Table 4: Extended Linux capabilities
| Capability Key        | Capability Description |
| -----------                   | ----------- |
| AUDIT_CONTROL                 | Enable and disable kernel auditing; change auditing filter rules; retrieve auditing status and filtering rules.        |
| AUDIT_READ                    | Allow reading the audit log via multicast netlink socket        |
| BLOCK_SUSPEND                 | Allow preventing system suspends.         |
| BPF                                   | Allow creating BPF maps, loading BPF Type Format (BTF) data, retrieve JITed code of BPF programs, and more.        |
| CHECKPOINT_RESTORE    | Allow checkpoint/restore related operations. Introduced in kernel 5.9.        |
| DAC_READ_SEARCH               | Bypass file read permission checks and directory read and execute permission checks.         |
| IPC_LOCK                              | Lock memory (mlock(2), mlockall(2), mmap(2), shmctl(2)).        |
| IPC_OWNER                             | Bypass permission checks for operations on System V IPC objects.        |
| LEASE                                 | Establish leases on arbitrary files (see fcntl(2)).         |
| LINUX_IMMUTABLE               | Set the FS_APPEND_FL and FS_IMMUTABLE_FL i-node flags.        |
| MAC_ADMIN                             | Allow MAC configuration or state changes. Implemented for the Smack LSM.         |
| MAC_OVERRIDE                  | Override Mandatory Access Control (MAC). Implemented for the Smack Linux Security Module (LSM).        |
| NET_ADMIN                     | Perform various network-related operations.        |
| NET_BROADCAST                 | Make socket broadcasts, and listen to multicasts.        |
| PERFMON                               | Allow system performance and observability privileged operations using perf_events, i915_perf and other kernel subsystems         |
| SYS_ADMIN                             | Perform a range of system administration operations.        |
| SYS_BOOT                              | Use reboot(2) and kexec_load(2), reboot and load a new kernel for later execution.        |
| SYS_MODULE                    | Load and unload kernel modules.        |
| SYS_NICE                              | Raise process nice value (nice(2), setpriority(2)) and change the nice value for arbitrary processes.        |
| SYS_PACCT                             | Use acct(2), switch process accounting on or off.         |
| SYS_PTRACE                    | Trace arbitrary processes using ptrace(2).        |
| SYS_RAWIO                             | Perform I/O port operations (iopl(2) and ioperm(2)).         |
| SYS_RESOURCE                  | Override resource Limits        |
| SYS_TIME                              | Set system clock (settimeofday(2), stime(2), adjtimex(2)); set real-time (hardware) clock.         |
| SYS_TTY_CONFIG                | Use vhangup(2); employ various privileged ioctl(2) operations on virtual terminals.        |
| SYSLOG                                | Perform privileged syslog(2) operations.         |
| WAKE_ALARM                    | Trigger something that will wake up the system        |

## Appendix C: Container List
| Container	| Host Network Recommendation 	| Privilege Recommendation	| Comments |
| -----------   | ----------- 			|-----------			|-----------|
| Database	| Remove host network		|Remove container root privilege| Port forward|
| SNMP	| Remove host network		|Remove container root privilege| Port forward|
| Teamd	| Remove host network		|Remove container root privilege| Retain net_cap_admin|
| FRR	| Retain 		|Remove container root privilege| Retain net_cap_admin|
| LLDP	| Retain 		|Remove container root privilege| Retain net_cap_admin|
| DHCPrelay	| Remove host network		|Remove container root privilege| Retain net_cap_admin|
| Mux | Remove host network		|Remove container root privilege| Retain net_cap_admin|
| Telemetry	| Remove host network		|Remove container root privilege| Port forward for gnmi |
| Radv	| Remove host network		|Remove container root privilege| Might need additional capabilities for L2 data|
| RestAPI	| Remove host network		|Remove container root privilege| Planned for deprecation |
| Eventd	| Remove host network		|Remove container root privilege|  |
| iccpd	| Remove host network		|Remove container root privilege| |
| macsec	| Remove host network		|Remove container root privilege| |
| NAT	| Remove host network		|Remove container root privilege| Retain net_cap_admin |
| SWSS	| Retain 		|Retain root privilege| |
| syncd	| Retain 		|Retain root privilege| |
| PMON	| Remove host network		|Remove container root privilege| Check file descriptor privileges |
| sFlow	| Remove host network		|Remove container root privilege| |
| Management Framework	| TBD		|TBD| |
| P4rt	| TBD		|TBD| |
