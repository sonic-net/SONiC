# SONiC OOM daemon

# Table of Contents
- [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
- [1 Functional Requirements](#1-functional-requirement)
- [2 Configuration and Management Requirements](#2-configuration-and-management-requirements)
  * [2.1 SONiC CLI](#21-sonic-cli)
  * [2.2 Config DB](#22-config-db)
- [3 Design](#design)
  * [3.1 OOMD Implementation](#31-oomd-Implementation)
  * [3.2 Default OOMD config](#32-default-oomd-config)
  * [3.3 ConfigDB Schema](#34-configdb-schema)
  * [3.4 CLI](#35-cli)
- [4 Error handling](#error-handling)
- [5 Serviceability and Debug](#serviceability-and-debug)
- [6 Unit Test](#unit-test)
- [8 References](#references)


# About this Manual
This document provides a detailed description on the new features for:
 - Protect SONiC system memory by OOM daemon.
 - Re-start docker container when container in OOM.
 - OOM daemon config command.
 - OOM daemon high level design.
 - OOM daemon ConfigDB schema

### SONiC memory issue sloved by this feature.
 - Currently SONiC enabled OOM killer, and set /proc/sys/vm/panic_on_oom to 2, which will trigger kernal panic when OOM. This is by design to protect SONiC key process and container.
 - A typical switch device have 4 GB memory and sonic usually will use 1.5 GB for dockers, and 500 MB for system process. so there will be 2 GB free memory for user. 
 - sonic not enable swap for most device.
 - When user run some command trigger OOM, SONiC will kernel panic. for example:
   - Multiple user login to device, some service may create 10+ concurrent sessions login to device.
   - Some user script/command take too much memory, currently 'show' command will take 70 MB memory.
 - To fix this issue, we need 2 feature: login session limit and OOM daemon.

# 1 Functional Requirement
 - Monitor docker OOM status and re-start docker when OOM happen.
     - Some docker container will set memory limit and disable trigger system OOM killer.
     - These docker container will hang when OOM happen.
     - OOMD will subscribe OOM event of these docker, and re-start container when container OOM happen.
 - Monitor system memory utilization, protect system by terminate user process:
     - When exceed memory high-water mark, terminate user process to free memory and protect device from OOM happen.
     - Can set system memory high-water mark and low-water mark.
     - Can set memory protect policy:
        - User/group list, their process can be terminate safely.
        - Terminate policy: terminate user session or terminate user process.
    - All process start by local user will not be terminate by OOMD, unless they add to user/group list.
- Provide default setting to minimize customer side change.
  - Customers may have pipelines to initialize device configuration, because this feature add new commands, the pipeline may need update. The default limitation is designed to cover most scenario to minimize the customer side change.

# 2 Configuration and Management Requirements
## 2.1 SONiC CLI
 - Manage login session or memory  limit settings
```
    # config OOMD enable/disable status
    config oomd { enable/disable}
    
    # config oomd policy
    config oomd policy { policyname } { add|del } <value>
```
 - Show oomd config
```
    show oomd policy
    show oomd status
```

## 2.2 Config DB
 - OOMD feature can be enable/disable by config DB
 - OOMD policy are fully configurable by config DB.

# 3 Design
 - High-level design diagram:

```mermaid
graph TD;
%% SONiC CLI update config DB
CLI[SONiC CLI] -- update OOMD config --> CONFDB[(Config DB)];


%% HostCfgd/OOMD subscribe config DB change
CONFDB -.-> HOSTCFGD[Hostcfgd];
CONFDB -. config change event .-> OOMD[OOMD];

%% HostCfgd start/stop OOMD
HOSTCFGD -- start/stop OOMD --> systemd[systemd];
systemd --> OOMD;

%% OOMD subscript memory utilzation event from cgroup
CGROUP(cgroup) -. memory utilzation event .-> OOMD; 

%% OOMD subscript oom_control event from cgroup
DOCKERCGROUP(docker cgroup) -. oom_control event .-> OOMD; 

%% OOMD get user info from /etc/passwd
passwd(/etc/passwd) -. user information .-> OOMD;

%% OOMD terminate user session/procress when memory utilzation reach high-water mark
OOMD -- terminate signal --> process[process]

%% OOMD re-start docker container when container OOM happen
OOMD -- restart container --> container[container]

```

## 3.1 OOMD Implementation
 - OOMD will be a service managed by systemd.
 - System memory monitor and protect
     - Get system memory information from /proc/meminfo.
     - Subscript cgroup memory utilization event from /sys/fs/cgroup/memory/memory.usage_in_bytes.
     - Get user information from /etc/passwd.
     - OOMD will send SIGKILL/SIGTERM to kill/terminate process.
     - OOMD can config to terminate user session, this is because when swap not enabled, Linux system may enters a livelocked state much more quickly and may prevent oomd from responding in a reasonable amount of time. 
 - Docker container monitor and re-start
     - Subscript docker container OOM event from memory.oom_control
     - OOMD will run 'docker restart' command to restart docker container
 - The following diagram show how OOMD work:
    - UserInfoProvider will get user information from /etc/passwd
    - ConfigProvider will subscript config DB change event and update OOMD config.
    - MemMonitor will monitor cgroup event and trigger OomHandler.
    - ContainerMonitor will monitor container OOM event and re-start container
    - When memory utilization reach high-water mark, OomHandler will terminate user process to prevent OOM happen. 

```mermaid
graph TD;
%% USER information provider response for get user information from /etc/passwd
passwd(/etc/passwd) -. read user info .-> userinfoprovider[UserInfoProvider];
userinfoprovider -- update --> oomhandler[OomHandler];

%% Memory monitor response for minitor memory utilzation
cgroup(cgroup) -. subscribe event .-> memmonitor[MemMonitor]
memmonitor -- reach high-water mark --> oomhandler[OomHandler]

%% Container monitor response for minitor memory utilzation
containercgroup(container cgroup) -. subscribe OOM event .-> containermonitor[ContainerMonitor]
containermonitor -- restart container --> docker[Docker]

%% Config provider response for monitor and get latest OOMD config
confdb[(Config DB)] -. config change event .-> confprovider[ConfigProvider]
confprovider --> memmonitor
confprovider --> oomhandler
confprovider --> containermonitor

%% OOM handler will terminate process
oomhandler -- SIG_TERM--> process[process]

```
### Other solution for user space OOMD

|                      | Cons                                                         | URL                                                          |
| -------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| earlyoom             | Designed to free swap, SONiC not have swap.                  | [rfjakob/earlyoom: earlyoom - Early OOM Daemon for Linux (github.com)](https://github.com/rfjakob/earlyoom) |
| oomd                 | Developed by Facebook, Highly customizable by support plugin. Too heavy for SONiC. | [facebookincubator/oomd: A userspace out-of-memory killer (github.com)](https://github.com/facebookincubator/oomd) |
| systemd-oomd.service | Require cgroupv2, not scalable, can't customize to only termi. | [systemd-oomd.service(8) - Linux manual page (man7.org)](https://man7.org/linux/man-pages/man8/systemd-oomd.service.8.html) |



## 3.2 Default OOMD config
- OOMD will be enabled by default.
- Default high-water mark: 90
- Default low-water mark: 60
- Default user/group list is empty.
- Terminate domain user process by default.
- Monitor all container with memory limit and disable OOM.

## 3.3 ConfigDB Schema
 - OOMD setting table.
```
; Key
key                      = "policies"         ; OOMD policies
; Attributes
enable_memory_monitor    = Boolean            ; Enable status, true for enable.
enable_container_monitor = Boolean            ; Enable status, true for enable.
high_water_mark          = 3*DIGIT            ; Memory utilzation high-water mark
low_water_mark           = 3*DIGIT            ; Memory utilzation low-water mark
domain_account           = Boolean            ; OOMD will terminate process run by domain account
terminate_scope          = LIST(1*32VCHAR)    ; OOMD terminate scope: "process" or "session"
allow_user_list          = LIST(string)    ; OOMD can terminate process start by users in this list 
allow_group_list         = LIST(string)    ; OOMD can terminate process start by group users in this list 
```
 - Yang model: [sonic-system-oomd.yang](./sonic-system-oomd.yang)

## 3.4 CLI
 - Add following command to change OOMD setting.
```
    // config OOMD enable/disable status
    config oomd memory    { enable/disable}
    config oomd container { enable/disable}
    
    // config OOMD high-water mark and low-water mark, number are memory utilzation percentage.
    config oomd policy { highwatermark|lowwatermark } <number>
    
    // config which user/group can be terminate
    config oomd policy { users|groups } { add|del } <name>
    
    // config if OOMD can terminate domain account process/session
    config oomd policy domainaccount { enable|disable }
    
    // config OOMD terminate user session or process
    config oomd policy terminatescope { session|process }
    
    // config OOMD log level
    config oomd policy loglevel { debug|standard }

```

 - Add following command to show OOMD setting.
```
    // show oomd setting
    show oomd policy

    // show oomd enable/disable status
    show oomd status
```

# 4 Error handling
 - OOMD will write errors to syslog.

# 5 Serviceability and Debug
 - OOMD  can be debugged by enabling the debug flag OOMD config.

# 6 Unit Test

## 6.1 Enable/disable OOMD test

  - Enable/disable OOMD and check the OOMD service status:
  ```
      Verify the OOMD service started when OOMD enabled.
      Verify the OOMD service stopped when OOMD disabled.
  ```

## 6.2 OOMD policy test

  - Change OOMD high-water/low-water mark and check the OOMD will be triggered correctly:
  ```
      Verify when system memory utilzation reach high-water mark OOMD triggered.
      Verify when OOMD triggered, procress been terminated to free enough memory to low-water mark.
      Verify when OOMD triggered, the system procress are healthy.
  ```

  - Change OOMD user/group config and check the OOMD terminate process correctly:

  ```
    Verify when OOMD triggered, the procresses run by target user been terminated correctly.
    Verify when OOMD triggered, the procresses not run by target user are healthy.
  ```

  - Change OOMD terminate domain account config and check the OOMD terminate process correctly:

  ```
    Verify when OOMD triggered, the procresses run by domain account been terminated correctly.
  ```

  - Change OOMD terminate process/session config and check the OOMD terminate process/session correctly:

  ```
    Verify when OOMD triggered, and config is terminate process, the user process been terminated correctly.
    Verify when OOMD triggered, and config is terminate session, the user session been terminated correctly.
  ```

  - Change OOMD log level config and check the OOMD write system log correctly:

  ```
    Verify when log level set to debug, syslog contains OOMD debug information.
    Verify when log level set to standard, syslog not contains OOMD debug information.
  ```

  - Trigger docker container OOM, check the docker container restarted:

  ```
    Verify when enable container monitor, docker container restarted.
    Verify when disable container monitor, docker container not restart.
  ```


# 7 References
## Linux OOM
https://www.kernel.org/doc/gorman/html/understand/understand016.html

## cgroup
https://man7.org/linux/man-pages/man7/cgroups.7.html

