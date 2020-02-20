# Monitoring and Auto-Mitigating the Unhealthy of Containers in SONiC

# High Level Design Document
#### Rev 0.1

# Table of Contents
* [List of Tables](#list-of-tables)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Feature Overview](#1-feature-overview)
    - [1.1 Requirements](#11-requirements)
        - [1.1.1 Functional Requirements](#111-functional-requirements)
        - [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
        - [1.1.3 Scalability Requirements](#113-scalability-requirements)
    - [1.2 Design](#12-design)
        - [1.2.1 Basic Approach](#121-basic-approach)
* [2 Functionality](#2-functionality)
    - [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
    - [2.2 Functional Description](#22-functional-description)
        - [2.2.1 Monitoring Critical Processes](#221-monitoring-critical-processes)
        - [2.2.2 Monitoring Critical Resource Usage](#222-monitoring-critical-resource-usage)
        - [2.2.3 Auto-restart Docker Container](#223-auto-restart-docker-container)
            - [2.2.3.1 CLI (and usage example)](#2231-cli-and-usage-example)
                - [2.2.3.1.1 Show the Status of Auto-restart](#22311-show-the-status-of-auto-restart)
                - [2.2.3.1.2 Configure the Status of Auto-restart](#22312-configure-the-status-of-auto-restart)
                - [2.2.3.1.3 CONTAINER_FEATURE Table](#22313-container-feature-table)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# Revision
| Rev |    Date    |          Author        |     Change Description    |
|:---:|:----------:|:----------------------:|---------------------------|
| 0.1 | 02/18/2020 | Yong Zhao, Joe Leveque |      Initial version      |

# About this Manual
This document provides the design and implementation of monitoring and auto-mitigating
the unhealthy of docker containers in SONiC.

# Scope
This document describes the high level design of the feature to monitor and auto-mitigate
the unhealthy of docker containers.

# Definitions/Abbreviation
| Abbreviation |         Description          |
|--------------|------------------------------|
| Config DB    | SONiC Configuration Database |
| CLI          | Command Line Interface       |

# 1 Feature Overview
SONiC is a collection of various switch applications which are held in docker containers
such as BGP and SNMP. Each application usually includes several processes which are 
working together to provide the services for other modules. As such, the healthy of
critical processes in each docker container are the key not only for this docker
container working correctly but also for the intended functionalities of whole SONiC switch.
On the other hand, profiling the resource usages and performance of each docker
container are also important for us to understand whether this container is in healthy state
or not and furtherly to provide us with deep insight about networking traffic.

The main purpose of this feature includes two parts: the first part is to monitor the
running status of each process and critical resource usage such as CPU, memory and disk
of each docker container.
The second part is docker containers can be automatically shut down and
restarted if one of critical processes running in the container exits unexpectedly. Restarting
the entire container ensures that configuration is reloaded and all processes in the container
get restarted, thus increasing the likelihood of entering a healthy state.

We implemented this feature by employing the existing Monit and supervisord system tools.
1. We used Monit system tool to detect whether a process is running or not and whether 
  the resource usage of a docker container is beyond the pre-defined threshold.
2. We leveraged the mechanism of event listener in supervisord to auto-restart a docker container
  if one of its critical processes exited unexpectedly. 
3. We also added a knob to make this auto-restart feature dynamically configurable.
  Specifically users can run CLI to configure this feature residing in Config_DB as
  enabled/disabled state.

## 1.1 Requirements

### 1.1.1 Functional Requirements
1. The Monit must provide the ability to generate an alert when a critical process is not
    running.
2. The Monit must provide the ability to generate an alert when the resource usage of
    a docker contaier is larger than the pre-defined threshold.
3. The event listener in supervisord must receive the signal when a critical process in 
    a docker container crashed or exited unexpectedly and then restart this docker 
    container.
4. CONFIG_DB can be configured to enable/disable this auto-restart feature for each docker
    container.. 
5. Users can access this auto-restart information via the CLI utility
    1. Users can see current auto-restart status for docker containers.
    2. Users can change auto-restart status for a specific docker container.

### 1.1.2 Configuration and Management Requirements
Configuration of the auto-restart feature can be done via:
1. init_cfg.json
2. CLI

### 1.1.3 Scalability Requirements
`Place holder`

## 1.2 Design

### 1.2.1 Basic Approach
Monitoring the running status of critical processes and resource usage of docker containers
are heavily depended on the Monit system tool. Since Monit already provided the mechanism
to check whether a process is running or not, it will be straightforward to integrate this into monitoring 
the critical processes in SONiC. However, Monit only gives the method to monitor the resource
usage per process level not container level. As such, monitoring the resource usage of a docker 
container will be an interesting and challenging problem. In our design, we adopted the way
that Monit will check the returned value of a script which reads the resource usage of docker 
container, compares it with pre-defined threshold and then exited. 

We employed the mechanism of event listener in supervisord to achieve auto-restarting of docker 
container. Currently supervisord will monitor the running status of each process in SONiC
docker containers. If one critical process exited unexpectedly, supervisord will catch such signal
and send it to event listener. Then event listener will kill the process supervisord and
the entire docker container will be shut down and restarted.

# 2 Functionality
## 2.1 Target Deployment Use Cases
This feature is used to perform the following functions:
1. Monit will write an alert message into syslog if one if critical process exited unexpectedly.
2. Monit will write an alert message into syslog if the usage of memory is larger than the
    pre-defined threshold for a docker container.
3. A docker container will auto-restart if one of its critical processes crashed or exited
    unexpectedly.

## 2.2 Functional Description


### 2.2.1 Monitoring Critical Processes
Monit has implemented the mechanism to monitor whether a process is running or not. In detail,
Monit will periodically read the target processes from configuration file and tries to match 
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

### 2.2.2 Monitoring Critical Resource Usage
Similar to monitoring the critical processes, we can employ Monit to monitor the resource usage
such as CPU, memory and disk for each process. Unfortunately Monit is unable to do the resource monitoring
in the container level. Thus we propose a new design to achieve such monitoring based on Monit.
Specifically Monit will monitor a script and check its exit status. This script
will correspondingly read the resource usage of docker containers, compare it with
pre-defined threshold and then return a value. The value 0 signified that
the resource usage is less than threshold and non-zero means Monit will send an alert since
current usage is larger than threshold.

Below is an example of Monit configuration file for lldp container to pass the pre-defined 
threshold (bytes) to the script and check the exiting value.

```bash
check program memory_checker with path "/usr/bin/memory_checker lldp 104857600"
    if status != 0 then alert
```

### 2.2.3 Auto-restart Docker Container
The design principle behind this auto-restart feature is docker containers can be automatically shut down and
restarted if one of critical processes running in the container exits unexpectedly. Restarting
the entire container ensures that configuration is reloaded and all processes in the container
get restarted, thus increasing the likelihood of entering a healthy state.

Currently SONiC used superviord system tool to manage the processes in each
docker container. Actually auto-restarting docker container is based on the process 
monitoring/notification framework. Specifically
if the state of process changes for example from running to exited,
an event notification `PROCESS_STATE_STOPPED` will be emitted by supervisord.
This event will be received by event listener. If the exited process is critical
one, then the event listener will terminate supervisord and the container will be stopped 
and restarted.

We also introduced a knob which can enable or disable this auto-restart feature
dynamically according to the requirement of users. In detail, we created a table 
named `CONTAINER_FEATURE` in Config_DB and this table includes the status of
auto-restart feature for each docker container. Users can easily use CLI to
see and configure the corresponding status.


#### 2.2.3.1 CLI (and usage example)
The CLI tool will provide the following functionality:
1. Show current status of auto-restart feature for docker containers.
2. Configure the status of a specific docker container.

##### 2.2.3.1.1 Show the Status of Auto-restart
```
admin@sonic:~$ show container feature autorestart
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

##### 2.2.3.1.2 Configure the Status of Auto-restart
```
admin@sonic:~$ sudo config container feature autorestart database enabled
```


##### 2.2.3.1.3 CONTAINER_FEATURE Table
Example:
```
{
    "CONTAINER_FEATURE": {
        "database": {
            "auto_restart": "enabled",
        },
        "lldp": {
            "auto_restart": "disabled",
        },
        "radv": {
            "auto_restart": "disabled",
        },
        "pmon": {
            "auto_restart": "disabled",
        },
        "sflow": {
            "auto_restart": "enabled",
        },
        "snmp": {
            "auto_restart": "enabled",
        },
        "telemetry": {
            "auto_restart": "enabled",
        },
        "bgp": {
            "auto_restart": "disabled",
        },
        "dhcp_relay": {
            "auto_restart": "disabled",
        },
        "rest-api": {
            "auto_restart": "enabled",
        },
        "teamd": {
            "auto_restart": "disabled",
        },
        "syncd": {
            "auto_restart": "enabled",
        },
        "swss": {
            "auto_restart": "disabled",
        },
   
    }
}
```
