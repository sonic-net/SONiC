# Monitoring and Auto-Mitigating Unhealthy Containers in SONiC

# High Level Design Document
#### Rev 0.2

# Table of Contents
* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Feature Overview](#1-feature-overview)
    - [1.1 Monitoring](#11-monitoring)
        - [1.1.1 Monitoring Critical Processes by Monit](#111-monitoring-critical-processes-by-monit)
        - [1.1.2 Monitoring Critical Processes by Supervisor](#112-monitoring-critical-processes-by-supervisor)
    - [1.2 Auto-mitigating](#12-auto-mitigating)
        - [1.2.1 Restarting Container per Crash of Critical Process](#121-restarting-container-per-crash-of-critical-process)
        - [1.2.2 Restarting Container per High Memory Usage](#122-restarting-container-per-high-memory-usage)
    - [1.3 Requirements](#13-requirements)
        - [1.3.1 Functional Requirements](#131-functional-requirements)
        - [1.3.2 Configuration and Management Requirements](#132-configuration-and-management-requirements)
        - [1.3.3 Fast-Reboot/Warm-Reboot requirements](#133-fast-rebootwarm-reboot-requirements)
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
| 0.1 | 02/18/2020 | Yong Zhao, Joe Leveque |       Initial version     |
| 0.2 | 07/19/2020 |        Yong Zhao       |       Second version      |

# Scope
This document describes the high level design of features to monitor and auto-mitigate
the unhealthy containers in SONiC.

# Definitions/Abbreviation
| Abbreviation |         Description          |
|--------------|------------------------------|
| Config DB    | SONiC Configuration Database |
| CLI          | Command Line Interface       |

# 1 Feature Overview
SONiC is a collection of various switch applications which are held in docker containers
such as BGP container and SNMP container. Each application usually includes several processes which are 
working together to provide and receive the services from other modules. As such, the health of
critical processes in each docker container is imperative not only for the docker
container working correctly but also for the intended functionalities of entire SONiC switch.

## 1.1 Monitoring

### 1.1.1 Monitoring Critical Processes by Monit
This feature is used to monitor the running status of critical processes in containers.

We used Monit system tool to detect whether a critical process is running or not and whether 
the resource usage of a docker container is beyond the pre-defined threshold.

### 1.1.2 Monitoring Critical Processes by Supervisor
This feature demonstrated 'event listener' provided by Supervisord can be leveraged to do
the critical processes monitoring. Specifically 'event listener' can subscribe to 'event notification'
which indicates that something happened related to a sub-process controlled by Supervisord.

We designed an 'event listener' which subscribed to the events 'PROCESS_STATE_EXITED'
and 'PROCESS_STATE_RUNNING'. If a critical process exited unexpectedly, then Supervisor will
emit the event 'PROCESS_STATE_EXITED' which will be received by 'event listener'. After
that, the 'event listener' will check whether an alerting message should be written into
the syslog.

## 1.2 Auto-Mitigating

### 1.2.1 Restarting Docker Container per Crash of Critical Process
This feature demonstrated docker container can be automatically shut down and
restarted if one of critical processes running in docker container exits unexpectedly. Restarting
the entire docker container ensures that configuration is reloaded and all processes in 
docker container get restarted, thus increasing the likelihood of entering a healthy state.

We leveraged the 'event listener' mechanism in supervisord to auto-restart a docker container
if one of its critical processes exited unexpectedly. We also added a configuration option to make this 
auto-restart feature dynamically configurable. Specifically users can run CLI to configure this 
feature residing in Config_DB as enabled/disabled status.

### 1.2.2 Restarting Docker Container per High Memory Usage
This feature demonstrated docker container can be shut down and restarted if memory usage
of it is continuously beyond the threshold during monitoring interval. Restarting
the entire docker container ensures that configuration is reloaded and all processes in 
docker container get restarted, thus increasing the likelihood of entering a healthy state.

We defined a threshold of memory usage for each container and Monit in background will
compare the current memory usage of a container with this threshold periodically. If memory usage
of a container is continuously beyond the threshold during monitoring interval, then it
will be restarted to avoid bringing down the device due to the out-of-memory issue.

We also added configuration options to make this high memory restart feature and memory
threshold dynamically configurable. Specifically `show` command can be used to get the
state of this restart feature and threshold value of each container. `config` command
is leveraged to configure this restart feature residing in Config_DB as 'enabled/disabled'
status and change the threshold of each container.

## 1.3 Requirements

### 1.3.1 Functional Requirements
1. Monit must provide the ability to generate an alert when a critical process has not
    been alive for 5 minutes.
2. Monit must provide the ability to generate an alert when the resource usage of
    a docker container is larger than the pre-defined threshold.
3. The event listener in supervisord must receive the signal when a critical process in 
    a docker container crashed or exited unexpectedly and then restart this docker 
    container.
4. The event listener in supervisord must receive the signal when a critical process in 
    a docker container crashed or exited unexpectedly and then check whether an alerting 
    message should be written into syslog. 
5. CONFIG_DB can be configured to enable/disable the auto-restart feature related to 
    process crash of each docker container.
6. CONFIG_DB can be configured to enable/disable the restart feature related to high
    memory usage of each docker container.
7. CONFIG_DB can be configured to set memory threshold of each docker container.
8. Users can access the status of auto-restart feature via the CLI utility
    1. Users can retrieve current auto-restart status of docker containers.
    2. Users can configure auto-restart status for a specific docker container.
9. Users can access the status of high memory restart feature via the CLI utility
    1. Users can retrieve current high memory restart status of docker containers.
    2. Users can configure high memory restart status for a specific docker container.
10. Users can access the memory threshold of each docker cotnainer via the CLI utility
    1. Users can retrieve current memory threshold of docker containers.
    2. Users can configure memory threshold for a specific docker container.

### 1.3.2 Configuration and Management Requirements
The default state of auto-restart, high memory restart and default memory threshold of
each container can be configured in the file init_cfg.json.j2 file.
Configuration of these features can be changed via:
1. config_db.json
2. CLI

### 1.3.3 Fast-Reboot/Warm-Reboot Requirements
During the fast-reboot/warm-reboot/warm-restart procedures in SONiC, a select number of processes
and the containers they reside in are stopped in a special manner (via a signals or similar).
In this situation, we need ensure these containers remain stopped until the fast-reboot/warm-reboot/warm-restart
procedure is complete. Therefore, in order to prevent the auto-restart mechanism from restarting 
the containers prematurely, it is the responsibility of the fast-reboot/warm-reboot/warm-restart 
procedure to explicitly stop the systemd service which manages the container immediately after stopping
and critical processes/container. Once the systemd service is explicitly stopped, it will not attempt
to automatically restart the container.


## 1.4 Design

### 1.4.1 Basic Approach
Monitoring the running status of critical processes and resource usage of docker containers
depends on the Monit system tool. Since Monit natively provides a mechanism
to check whether a process is running or not, it will be straightforward to integrate this into monitoring 
the critical processes in SONiC. 

However, Monit only provides a method to monitor the resource
usage on a per-process level not a per-container level. As such, monitoring the resource usage of a docker 
container is not as straightforward. In our design, we propose to utilize the mechanism with
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

We employed the 'event listener' mechanism in Supervisor to achieve critical process monitoring and 
auto-restarting docker containers. We configure an 'event listener' to listen for process exit events.
When a supervised process in docker container exits, supervisord will emit this event and notify 
customized event listener. Then the event listener determines whether the process is a critical process
and it exited unexpectedly. If both of these conditions are true, the event listener will check whether
the auto-restart of this docker container was enabled or not. If it was disabled, then 'event listener'
will do the alerting and check whether an message should be written into syslog or not. If it was enabled,
'event listener' will kill the supervisord process. Since supervisord runs as PID 1 process inside the docker
container, the docker container will stop if supervisord process exits. Once the docker
container stops, the systemd service which manages this container will also stop. As this service is
configured to automatically restart, systemd will start it after 30 seconds and thus the corresponding 
docker container will be restarted again.

# 2 Functionality
## 2.1 Target Deployment Use Cases
These features are used to perform the following functions:
1. Monit will write an alert message into syslog if one if critical process has not been
    alive for 5 minutes.
2. Monit will write an alert message into syslog if the usage of memory is larger than the
    pre-defined threshold for a docker container.
3. A docker container will auto-restart if one of its critical processes crashed or exited
    unexpectedly.
4. If auto-restart of a docker container is disabled and one of its critical processes has
    not been alive for more than 1 minute, then 'event listener' will write an alerting message 
    into syslog periodically.
5. If memory usage of a docker container is larger than the threshold for 15 times within 20 minutes,
    then it will be restarted.

## 2.2 Functional Description


### 2.2.1 Monitoring Critical Processes
Monit natively implements a mechanism to monitor whether a process is running or not. In detail,
Monit will periodically read the target processes from configuration file and try to match 
those process with the processes tree in Linux kernel.

Below is an example of Monit configuration file to monitor the critical processes in lldp
container.

*/etc/monit/conf.d/monit_lldp*
```bash
###############################################################################
# Monit configuration file for lldp container
# Process list:
#   lldpd
#   lldp_syncd
#   lldpmgrd
###############################################################################
check process lldp_monitor matching "lldpd: "
    if does not exit for 5 times within 5 cycles then alert
check process lldp_syncd matching "python2 -m lldp_syncd"
    if does not exit for 5 times within 5 cycles then alert
check process lldpmgrd matching "python /usr/bin/lldpmgrd"
    if does not exit for 5 times within 5 cycles then alert
```
However, Monit is unable to monitor multiple processes executing the same command but with
different arguments. For example, in teamd container, there are multiple teamd processes 
running the same command ```/usr/bin/teamd``` but using different port channel as argument.
Since there exists 1:1 mapping between a port channel and a teamd process, we employ Monit to 
monitor a script which retrieves all the port channels from Config_DB and then determine
whether there exists a teamd process in Linux for each port channel. If succeed, that means
all teamd processes are live. Otherwise, we will know at least teamd process exited unexpectedly
and then Monit will write an alert message into syslog. Similarly we can also use this method
to solve the same issue in dhcp_relay container.

### 2.2.2 Monitoring Critical Resource Usage
Similar to monitoring the critical processes, we can employ Monit to monitor the resource usage
such as CPU, memory and disk for each process. Unfortunately Monit is unable to do the resource monitoring
in the container level. Thus we propose a new design to achieve such monitoring based on Monit.
Specifically Monit will launch a script and check its exit status. This script
will correspondingly read the resource usage of docker containers, compare it with
pre-defined threshold and then return a value. The value 0 signified that
the resource usage is less than threshold and non-zero means Monit will send an alert since
current usage is larger than threshold.

Below is an example of Monit configuration file for lldp container to pass the pre-defined 
threshold (bytes) to the script and check the exiting value.

```bash
check program container_memory_lldp with path "/usr/bin/memory_checker lldp 104857600"
    if status != 0 then alert
```

We will employ similar mechanism for CPU and disk utilization. Thresholds for each resource,
per container can be determined by the operator by examining averages of resource usage in
a production environment. The value `0` in table represents the corresponding feature in 
the docker container is in `disabled` status.


### 2.2.3 Restarting Docker Container per Crash of Critical Process
The design principle behind this auto-restart feature is docker containers can be automatically shut down and
restarted if one of critical processes running in the container exits unexpectedly. Restarting
the entire container ensures that configuration is reloaded and all processes in the container
get restarted, thus increasing the likelihood of entering a healthy state.

Currently SONiC used supervisord system tool to manage the processes in each
docker container. Actually auto-restarting docker container is based on the process 
monitoring/notification framework. Specifically
if the state of process changes for example from running to exited,
an event notification `PROCESS_STATE_EXITED` will be emitted by supervisord.
This event will be received by event listener. The event listener determines if the process is
critical process and whether it exited unexpectedly. If both of
these conditions are true, the event listener will kill the supervisord process. Since supervisord
runs as PID 1 inside the containers, when supervisord exits, the container will stop. When the
container stops, the systemd service which manages the container will also stop, but it is
configured to automatically restart the service, thus it will restart the container.

We also introduced a configuration option which can enable or disable this auto-restart feature
dynamically according to the requirement of users. In detail, we created a table 
named `CONTAINER_FEATURE` in Config_DB and this table includes the status of
auto-restart feature for each docker container. Users can easily use CLI to
check and configure the corresponding docker container status.

### 2.2.4 Restarting Docker Container per High Memory Usage
The design principle behind this high memory restart is docker container will be restarted
if memory usage of it is continuously larger than the threshold during a monitoring interval.
Restarting the entire container ensures that configuration is reloaded and all processes in the container
get restarted, thus increasing the likelihood of entering a healthy state and avoiding the device
was down due to the out-of-memory (OOM) issue.

We have Monit launch a monitoring script which reads the memory usage of a container and compares it with the
memeory threshold. If the current memory usage is less than threshold, the monitoring script will
return 0 and Monit will not take any action. If the current memory usage is equal to or larger
than threshold, the monitoring script will return exit code 3. Monit will record this exit code
and do next round monitoring afte 1 minute. If this scenario occurred 15 times within
20 minutes, Then Monit will launch a restarting script which will first check whether the state of high
memory restart was enabled or not. If high memory restart of the docker container was enabled, then
the restarting script will restart this docker container.

We also introduced configuration options which can enable or disable this high memory restart feature
and set the memory threshold dynamically according to the requirement of users. In detail, we add two
fields 'high_mem_restart' and 'mem_threhsold' in 'FEATURE' table of each container in Config_DB.
Users can easily use CLI to retrieve and set these two configuration option of each docker container.

```bash
check program container_memory_lldp with path "/usr/bin/memory_checker lldp"
    if status == 3 for 15 times within 20 cycles then exec "/usr/bin/restart_service lldp"
```

### 2.2.5 CLI (and usage example)
The CLI tool will provide the following functionality:
1. Show current status of auto-restart feature for docker containers.
2. Show current status of high memory restart feature for docker containers.
3. Show current memory threshold of high memory restart feature for docker containers.
4. Configure the auto-restart status of a specific docker container.
5. Configure the high memory restart status of a specific docker container.
6. Configure the memory threshold of a specific docker container.

#### 2.2.5.1 Show the Status of Auto-restart
```
admin@sonic:~$ show feature autorestart
Container Name         Status 
--------------------  --------
database               disabled
lldp                   disabled
radv                   disabled
pmon                   disabled
sflow                  enabled
snmp                   enabled
telemetry              enabled
bgp                    disabled
dhcp_relay             disabled
rest-api               enabled
teamd                  disabled
syncd                  enabled
swss                   disabled
```

#### 2.2.5.2 Show the Status of High Memory Restart
```
admin@sonic:~$ show feature high_mem_restart
Container Name         Status 
--------------------  --------
database               disabled
lldp                   disabled
radv                   disabled
pmon                   disabled
sflow                  enabled
snmp                   enabled
telemetry              always_enabled
bgp                    disabled
dhcp_relay             disabled
rest-api               enabled
teamd                  disabled
syncd                  enabled
swss                   disabled
```

#### 2.2.5.3 Show the Memory Threshold of High Mmemory Restart
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

#### 2.2.5.4 Configure the Status of Auto-restart
```
admin@sonic:~$ sudo config feature autorestart database enabled
```

#### 2.2.5.5 Configure the Status of High Memory Restart
```
admin@sonic:~$ sudo config feature high_mem_restart database enabled
```

#### 2.2.5.6 Configure the Memory Threshold of High Memory Restart
```
admin@sonic:~$ sudo config feature mem_threshold database <threshold_value_in_bytes>
```

### 2.2.6 FEATURE Table
Example:
```
{
    "CONTAINER_FEATURE": {
        "database": {
            "state": "always_enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": true,
            "auto_restart": "enabled",
            "high_mem_restart": "disabled",
            "mem_threshold": 157286400,
        },
        "lldp": {
            "state": "enabled",
            "has_timer": false,
            "has_global_scope": true,
            "has_per_asic_scope": false,
            "auto_restart": "enabled",
            "high_mem_restart": "disabled",
            "mem_threshold": 104857600,
        },
    }
}
```
