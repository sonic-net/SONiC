# Monitoring High Memory Usage of Dock Containers in SONiC

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Feature Overview](#1-feature-overview)
    - [1.1 Monitoring](#11-monitoring-memory-usage-of-containers)
    - [1.2 Requirements](#12-requirements)
        - [1.2.1 Functional Requirements](#121-functional-requirements)
        - [1.2.2 Configuration and Management Requirements](#122-configuration-and-management-requirements)
        - [1.2.3 Fast-Reboot/Warm-Reboot requirements](#123-fast-rebootwarm-reboot-requirements)
    - [1.4 Design](#14-design)
        - [1.4.1 Basic Approach](#141-basic-approach)
* [2 Functionality](#2-functionality)
    - [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
    - [2.2 Functional Description](#22-functional-description)
        - [2.2.1 Monitoring Memory Usage of Containers](#221-monitoring-memory-usage-of-containers)
        - [2.2.2 CLI (and usage example)](#222-cli-and-usage-example)
            - [2.2.2.1 Show High Memory Alerting of Container(s)](#2221-show-high-memory-alerting-of-containers)
            - [2.2.2.2 Show Memory Threshold of Container(s)](#2222-show-memory-threshold-of-containers)
            - [2.2.2.3 Show High Memory Alerting of a Specific Container](#2223-show-high-memory-alerting-of-a-specific-container)
            - [2.2.2.4 Show Memory Threshold of a Specific Container](#2224-show-memory-threshold-of-a-specific-container)
            - [2.2.2.5 Configure High Memory Alerting of a Specific Container](#2225-configure-high-memory-alerting-of-a-specific-container)
            - [2.2.2.6 Configure Memory Threshold of a Specific Container](#2226-configure-memory-threshold-of-a-specific-container)
        - [2.2.3 CONTAINER_FEATURE Table](#223-container_feature-table)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# Revision
| Rev |    Date    |          Author        |     Change Description    |
|:---:|:----------:|:----------------------:|---------------------------|
| 0.1 | 06/08/2022 |        Yong Zhao       |       Initial version     |

# Scope
This document describes the high level design to monitor high memory
usage of containers in SONiC.

# Definitions/Abbreviation
| Abbreviation |         Description          |
|--------------|------------------------------|
| Config DB    | SONiC Configuration Database |
| CLI          | Command Line Interface       |

# 1 Feature Overview
SONiC is a collection of various switch applications which are held in docker
containers such as BGP container and SNMP container. Each application usually
includes several processes which are working together to provide and receive
the services from other modules. 

Due to limited memory size on deivce, monitoring memory usage of containers and
generating corresponding alert messages are the key not only for timely involving
external mitigation effort but also for the intended functionalities of entire
SONiC switch. As such, we propose this high memory alerting mechanism which includes 
two components: the first component will provide the configuration options
to enable or disable high memory alerting of each container; second component is
used to do monitor memory usage of containers and alert. Specifically, if 
memory usage of a container increases continuously during a period of time, 
there will be high probability that memory leak occurs in this container. 
The second component is able to detect such issue and generate alert messages 
into syslog if high memory alerting of this container is enabled.

## 1.1 Monitoring Memory Usage of Containers
This mechanism is employed to monitor and alert high memory usage of containers 
as well as provide user's an ability to enable or disable the alerting on demand.
Monit system tool is leveraged to detect whether the memory usage of a
docker container is beyond the pre-defined threshold.

Be default, high memory alerting of each container is enabled and memory usage 
threshold of each container is initialized in `CONFIG_DB`. Monit in background 
will compare the runtime memory usage of a container with configured threshold 
periodically. If memory usage of a container is continuously beyond the threshold 
during the specified monitoring interval, then alerting messages will be written 
into syslog.

We also provide configuration options for users such that the alerting status
and memory threshold of each container can be changed. Specifically, `show` 
command can be issued to retrieve the current alerting status and
the threshold value of containers from `CONFIG_DB` while `config` command
is implemented to configure the alerting status and threshold value of containers,

## 1.2 Requirements

### 1.2.1 Functional Requirements
1. Monit must provide the ability to generate an alert if the memory usage of
   a docker container is larger than the pre-defined threshold for a specified
   number of times during the monitoring interval. 
   If memory usage of the container is still larger than thershold after the
   monitoring interval, Monit should generate and write alert into syslog periodically.
2. `CONFIG_DB` can be configured to retrieve and set alerting status of each container.
3. `CONFIG_DB` can be configured to retrieve and set memory threshold of each container.
4. Users can access the alerting status of each container via the CLI utility
    1. Users can retrieve alerting status of a container.
    2. Users can configure alerting status of a container.
5. Users can access the memory threshold of each container via the CLI utility
    1. Users can retrieve memory threshold of a container.
    2. Users can configure memory threshold of a container.

### 1.2.2 Configuration and Management Requirements
The default alerting status and memory threshold of containers should be initialized 
in the `init_cfg.json.j2` file. Configuration of this feature can be changed via:
1. config_db.json
2. CLI

### 1.2.3 Fast-Reboot/Warm-Reboot Requirements
This feature will not affect the Fast-Reboot/Warm-Reboot procedures.

## 1.3 Design

### 1.3.1 Basic Approach
Monitoring the running status of critical processes and resource usage of
docker containers depend on the Monit system tool. Since Monit natively
provides the mechanism to check whether a process is running or not, it will
be straightforward to monitor the critical processes in SONiC. 

However, Monit only provides a mechanism to monitor the resource usage in a
per-process level not a per-container level. As such, monitoring the resource
usage of a docker container is not as straightforward as monitoring processes.
In this design, we propose to utilize the mechanism with which Monit can spawn
a process and check its return value. We will have Monit
launch a script which reads the resource usage of a container and compares
the resource usage with a configured threshold value of that container.
If the current resource usage is less than the configured threshold value,
the script will return 0 and Monit will not take action. However, if the
resource usage exceeds the threshold, the script will return a non-zero value
and Monit will log an alert message into the syslog.

Specifically, for monitoring memory usage of a container, the workflow can be
described as the following steps:
1.  Monit spawns a process to execute the script `memory_checker` every 1 minute
2.  `memory_checker` accepts <container_name> as a parameter and retrieves 
    alerting status and memory threshold of this container from `CONFIG_DB`.
3.  If high memory alerting is enabled and the container is running, `memory_checker` 
    retrieves its runtime memory usage from command output of `docker stats`; 
    Otherwiese, `memory_checker` exits and logs an message indicating
    either alerting is disabled or specified container is not running.
4.  If runtime memory usage is larger than memory threshold, then `memory_checker`
    exits with non-zero value; Otherwise, `memory_checker` exits with zero value.
5.  Monit will write an alerting message into syslog if it receives non-zero
    value from `memory_checker` for specified number of times during a monitoring
    interval.
6.  After the monitoring interval, Monit will write alerting messages into syslog
    every 1 minute if it receives non-zero value from `memory_checker` in every
    1 minute polling cycle.

# 2 Functionality
## 2.1 Target Deployment Use Cases
This mechanism is used to perform monitoring memory usage of docker containers:
1.  Monit will write an alerting message into syslog if it receives non-zero
    value from `memory_checker` for specified number of times during a monitoring
    interval.
    A non-zero value indicates runtime memory usage of a docker container is
    larger than its memory threshold.
2.  After the monitoring interval, Monit will write alerting messages into syslog
    every 1 minute if it receives non-zero value from `memory_checker` in every
    1 minute polling cycle.


## 2.2 Functional Description


### 2.2.1 Monitoring Memory Usage of Containers
Monit can be employed to monitor the resource usage such as CPU, memory and disk
of each process. Unfortunately Monit is unable to do the resource monitoring
in the container level. Thus we propose a mechanism to monitor memory usage of
docker containers based on Monit.

Specifically, Monit will launch a script `memory_checker` and check its exit value.
A non-zero value indicates runtime memory usage of a docker container is larger than
its memory threshold. Monit will write an alerting message into syslog if it receives
non-zero value from `memory_checker` for specified number of times during a monitoring
interval. After the monitoring interval, Monit will write alerting messages into syslog
every 1 minute if it receives non-zero value from `memory_checker` in every 1 minute
polling cycle.

Below is an example showing Monit configuration file of lldp container:

```bash
check program container_memory_lldp with path "/usr/bin/memory_checker lldp"
    if status == 3 for 10 times within 20 minutes then alert repeat every 1 cycles
```

### 2.2.2 CLI (and usage example)
The CLI tool will provide the following functionality:
1. Show alerting status of docker container(s).
2. Configure alerting status of a docker container.
3. Show memory threshold of docker container(s).
4. Configure memory threshold of a docker container.


#### 2.2.2.1 Show High Memory Alerting of Containers 
```
admin@sonic:~$ show feature high_memory_alerting
Container Name              HighMemAlerting
--------------------  -------------------------
database               	      enabled
lldp                          enabled
radv                          enabled
pmon                          enabled
snmp                          enabled
telemetry                     enabled
bgp                           enabled
dhcp_relay                    enabled
teamd                         enabled
syncd                         enabled
swss                          enabled
```


#### 2.2.2.2 Show Memory Threshold of Containers 
```
admin@sonic:~$ show feature memory_threhsold
Container Name               MemThreshold
--------------------  -------------------------
database               	      1073741824
lldp                          1073741824
radv                          1073741824
pmon                          1073741824
snmp                          1073741824
telemetry                     1073741824
bgp                           1073741824
dhcp_relay                    1073741824
teamd                         1073741824
syncd                         1073741824
swss                          1073741824
```

#### 2.2.2.3 Show High Memory Alerting status of a Specific Container
```
admin@sonic:~$ show feature high_memory_alerting database
Container Name              HighMemAlerting
--------------------  -------------------------
database               	      enabled
```

#### 2.2.2.4 Show Memory Threshold of a Specific Container
```
admin@sonic:~$ show feature memory_threhsold database
Container Name               MemThreshold
--------------------  -------------------------
database               	      1073741824
```

#### 2.2.2.5 Configure High Memory Alerting of a specific container
```
admin@sonic:~$ sudo config feature high_memory_alerting database <enabled|disabled>
```

#### 2.2.2.6 Configure Memory Threshold of a specific container
```
admin@sonic:~$ sudo config feature memory_threshold database <threshold_value_in_bytes>
```

### 2.2.3 FEATURE Table
Example:
```
{
    "FEATURE": {
        "database": {
            "state": "always_enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": true,
            "high_mem_alert": "enabled",
            "mem_threshold": 157286400,
        },
        "lldp": {
            "state": "enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": false,
            "high_mem_alert": "enabled",
            "mem_threshold": 104857600,
        },
    }
}
```