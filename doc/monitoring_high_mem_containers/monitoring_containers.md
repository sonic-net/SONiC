# Monitoring Containers' High Memory Usage in SONiC

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Feature Overview](#1-feature-overview)
    - [1.1 Monitoring](#11-monitoring-memory-usage-of-containers)
    - [1.2 Requirements](#13-requirements)
        - [1.2.1 Functional Requirements](#131-functional-requirements)
        - [1.2.2 Configuration and Management Requirements](#132-configuration-and-management-requirements)
        - [1.2.3 Fast-Reboot/Warm-Reboot requirements](#133-fast-rebootwarm-reboot-requirements)
    - [1.4 Design](#14-design)
        - [1.4.1 Basic Approach](#141-basic-approach)
* [2 Functionality](#2-functionality)
    - [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
    - [2.2 Functional Description](#22-functional-description)
        - [2.2.1 Monitoring Critical Processes](#221-monitoring-critical-processes)
        - [2.2.2 Monitoring Critical Resource Usage](#222-monitoring-critical-resource-usage)
        - [2.2.3 Restarting Docker Container per Crash of Critical Process](#223-restarting-docker-container-per-crash-of-critical-process)
        - [2.2.4 Restarting Docker Container per High Memory Usage](#223-restarting-docker-container-per-high-memory-usage)
        - [2.2.5 CLI (and usage example)](#224-cli-and-usage-example)
            - [2.2.5.1 Show the Status of Auto-restart](#2241-show-the-status-of-auto-restart)
            - [2.2.5.2 Show the Status of High Memory Restart](#2241-show-the-status-of-high-memory-restart)
            - [2.2.5.3 Show the Memory Threshold of High Memory Restart](#2241-show-the-memory-threshold-of-high-memory-restart)
            - [2.2.5.4 Configure the Status of Auto-restart](#2242-configure-the-status-of-auto-restart)
            - [2.2.5.5 Configure the Status of High Memory Restart](#2242-configure-the-status-of-high-memory-restart)
            - [2.2.5.6 Configure the Memory Threshold of High Memory Restart](#2242-configure-the-memory-threshold-of-high-memory-restart)
        - [2.2.6 CONTAINER_FEATURE Table](#225-container_feature-table)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# Revision
| Rev |    Date    |          Author        |     Change Description    |
|:---:|:----------:|:----------------------:|---------------------------|
| 0.1 | 06/08/2022 |        Yong Zhao       |       Initial version     |

# Scope
This document describes the high level design of feature to monitor high memory
usage of containers in SONiC.

# Definitions/Abbreviation
| Abbreviation |         Description          |
|--------------|------------------------------|
| Config DB    | SONiC Configuration Database |
| CLI          | Command Line Interface       |

# 1 Feature Overview
SONiC is a collection of various switch applications which are held in docker containers
such as BGP container and SNMP container. Each application usually includes several processes which are 
working together to provide and receive the services from other modules. 

Due to limited memory size on deivce, monitoring memory usage of containers and
generating corresponding alert messages are the key not only for timely involving external
mitigation effort but also for the intended functionalities of entire SONiC switch.

If memory usage of a container increases continuously during a period of time,
there will be high probability that memory leak occurs in this container.
This feature will detect such issue and write alerting messages into syslog.

## 1.1 Monitoring Mmeory Usage of Containers
This feature is used to monitor and alert high memory usage of containers in SONiC.

We leverage Monit system tool to detect whether the memory usage of a docker container 
is beyond the pre-defined threshold.

We define a threshold of memory usage for each container and Monit in background will
compare the current memory usage of a container with this threshold periodically. If memory usage
of a container is continuously beyond the threshold during the specified monitoring interval, 
then alerting messages will be written into syslog.

We also add configuration options to enable this memory threshold to be configurable on demand. 
Specifically, `show` command can be issued to retrieve the threshold value of each container from 
`CONFIG_DB` while `config` command is implemented to configure threshold value of containers 
residing in `Config_DB`.

## 1.2 Requirements

### 1.2.1 Functional Requirements
1. Monit must provide the ability to generate an alert when the memory usage of
   a docker container is larger than the pre-defined threshold during a
   specified monitoring interval. If memory usage of the container continuously increase, 
   Monit should generate and write alert into syslog periodically.
2. `CONFIG_DB` can be configured to set memory threshold of each docker container.
3. Users can access the memory threshold of each docker cotnainer via the CLI utility
    1. Users can retrieve current memory threshold of docker containers.
    2. Users can configure memory threshold for a specific docker container.

### 1.2.2 Configuration and Management Requirements
The default memory threshold of each container should be configured in the `init_cfg.json.j2` file.
Configuration of these features can be changed via:
1. config_db.json
2. CLI

### 1.2.3 Fast-Reboot/Warm-Reboot Requirements
During the fast-reboot/warm-reboot/warm-restart procedures in SONiC, a select number of processes
and the containers they reside in are stopped in a special manner (via a signals or similar).
In this situation, we need ensure these containers remain stopped until the fast-reboot/warm-reboot/warm-restart
procedure is complete. Therefore, in order to prevent the auto-restart mechanism from restarting 
the containers prematurely, it is the responsibility of the fast-reboot/warm-reboot/warm-restart 
procedure to explicitly stop the systemd service which manages the container immediately after stopping
and critical processes/container. Once the systemd service is explicitly stopped, it will not attempt
to automatically restart the container.


## 1.3 Design

### 1.3.1 Basic Approach
Monitoring the running status of critical processes and resource usage of docker containers
depends on the Monit system tool. Since Monit natively provides a mechanism
to check whether a process is running or not, it will be straightforward to integrate this into monitoring 
the critical processes in SONiC. 

However, Monit only provides a method to monitor the resource
usage on a per-process level not a per-container level. As such, monitoring the resource usage of a docker 
container is not straightforward as monitoring process. In our design, we propose to utilize the mechanism with
which Monit can spawn a process and check the return value of the process. We will have Monit
launch a script which reads the resource usage of the container and compares the resource usage
with a configured threshold value for that container. If the current resource usage is less than
the configured threshold value, the script will return 0 and Monit will not log a message.
However, if the resource usage exceeds the threshold, the script will return a non-zero value
and Monit will log an alert message to the syslog.

Similalr to the mechanism of monitoring resource usage of a docker container, first we have
Monit launch a monitoring script which reads the memory usage of a container and compares it with the
memeory threshold. If the current memory usage is less than threshold, the monitoring script will
return 0 and Monit will not take any action. If the current memory usage is equal to or larger
than threshold, the monitoring script will return exit code 3. Monit will record this exit code
and do next round monitoring afte 1 minute. If this scenario occurred 15 times within
20 minutes, Then Monit will launch a restarting script which will first check whether the state of high
memory restart was enabled or not. If high memory restart of the docker container was enabled, then
the restarting script will restart this docker container.

# 2 Functionality
## 2.1 Target Deployment Use Cases
These features are used to perform the following functions:
1. Monit will write an alert message into syslog if the usage of memory is larger than the
    pre-defined threshold for a docker container.

## 2.2 Functional Description


### 2.2.2 Monitoring Critical Resource Usage
Similar to monitoring the critical processes, we can employ Monit to monitor the resource usage
such as CPU, memory and disk for each process. Unfortunately Monit is unable to do the resource monitoring
in the container level. Thus we propose a new design to achieve such monitoring based on Monit.

Specifically, Monit will launch a script and check its exit status. This script
will correspondingly read the resource usage of docker containers, compare it with
pre-defined threshold and then return a value. The value 0 signified that
the resource usage is less than threshold and non-zero means Monit will send an alert since
current usage is larger than threshold.

Below is an example of Monit configuration file for lldp container to pass the pre-defined 
threshold (bytes) to the script and check the exiting value.

```bash
check program container_memory_lldp with path "/usr/bin/memory_checker lldp 104857600"
    if status != 0 then alert repeat every 1 cycles
```

### 2.2.3 CLI (and usage example)
The CLI tool will provide the following functionality:
3. Show current memory threshold of docker containers.
6. Configure the memory threshold of a specific docker container.


#### 2.2.3.1 Show memory threshold of containers 
```
admin@sonic:~$ show feature mem_threhsold
Container Name         Memory Threshold (Bytes)
--------------------  -------------------------
database               	      157286400 
lldp                          104857600
radv                          31457280
pmon                          104857600
snmp                          104857600
telemetry                     209715200
bgp                           314572800
dhcp_relay                    62914560
teamd                         73400320
syncd                         629145600
swss                          104857600
```


#### 2.2.3.1 Show memory threshold of a specific container
```
admin@sonic:~$ show feature mem_threhsold database
Container Name         Memory Threshold (Bytes)
--------------------  -------------------------
database               	      157286400 
```

#### 2.2.3.2 Configure the Memory Threshold of a specific container
```
admin@sonic:~$ sudo config feature mem_threshold database <threshold_value_in_bytes>
```

### 2.2.4 FEATURE Table
Example:
```
{
    "FEATURE": {
        "database": {
            "state": "always_enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": true,
            "auto_restart": "enabled",
            "mem_threshold": 157286400,
        },
        "lldp": {
            "state": "enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": false,
            "auto_restart": "enabled",
            "mem_threshold": 104857600,
        },
    }
}
```
