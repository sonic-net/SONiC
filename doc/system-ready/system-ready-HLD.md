

# System Ready HLD

#### Rev 0.2

# Table of Contents

- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [Definition/Abbreviation](#definitionabbreviation)
- [About This Manual](#about-this-manual)
- [1 Introduction and Scope](#1-introduction-and-scope)
  - [1.1 Limitation of Existing tools](#11-existingtools-limitation)
  - [1.2 Benefits of this feature](#12-benefits-of-this-feature)
- [2 Feature Requirements](#2-feature-requirements)
  - [2.1 Functional Requirements](#21-functional-requirements)
  - [2.2 Configuration and Management Requirements](#22-configuration-and-management-requirements)
  - [2.3 Scalability Requirements](#23-scalability-requirements)
  - [2.4 Warm Boot Requirements](#24-warm-boot-requirements)
- [3 Feature Description](#3-feature-description)
- [4 Feature Design](#4-feature-design)
  - [4.1 Overview](#41-design-overview)
  - [4.2 Sysmonitor](#42-db-changes)
    - [4.2.1 Subtasks in Sysmonitor](#421-subtasks-in-sysmonitor)
  - [4.3 Service Identification and Categorization](#43-service-categorization)
  - [4.4 System ready Framework business logic](#44-systemready-fremework-logic)
  - [4.5 Provision for apps to mark closest UP status](#45-provision-for-apps-to-mark-UP)
    - [4.5.1 CONFIG_DB Changes](#451-config-db-changes)
    - [4.5.2 STATE_DB Changes](#452-state-db-changes)
    - [4.5.3 Feature yang Changes](#453-feature-yang-changes)
  - [4.6 Syslogs](#46-syslogs)
- [5 CLI](#5-cli)
  - [5.1 Output Format](#51-cli-output-format)
  - [5.2 show system status core](#52-system-status-core)
  - [5.3 show system status all](#53-system-status-all)
  - [5.4 show system status all --brief](#54-system-status-all-brief)
  - [5.5 show system status all --detail](#55-system-status-all-detail)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Warm reboot Support](#7-warm-reboot-support)
- [8 Unit Test Cases ](#8-unit-test-cases)
- [9 References ](#9-references)

# List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev  |    Date    |       Author        | Change Description                                           |
|:--:|:--------:|:-----------------:|:------------------------------------------------------------:|
| 0.1  |  | Senthil Kumar Guruswamy   | Initial version                                              |
| 0.2  |  | Senthil Kumar Guruswamy   | Update as per review comments                                              |


# Definition/Abbreviation

### Table 1: Abbreviations

| **Term** | **Meaning**                               |
| -------- | ----------------------------------------- |
| FEATURE  | Docker/Service                            |
| App      | Docker/Service                            |


# About this Manual

This document provides general information about the System Ready feature implementation in SONiC. 


# 1 Introduction and Scope

This document describes the Functionality and High level design of the System Ready feature.

At present, there is no mechanism to know that the system is up with all the essential sonic services and also, all the docker apps are ready along with port ready status to start the network traffic.
With the asynchronous architecture of SONiC, we will not be able to verify if the config has been applied all the way down to the hardware. 
However, if we could get the closest up status of each docker app considering their config receive ready and port ready, the system readiness could be arrived.

A new python based System monitor framework is introduced to monitor all the essential system host services including docker wrapper services on an event based model and declare the system is ready.
This framework gives provision for docker and host apps to notify its closest up status.
CLIs are provided to fetch the current system status and also service running status and its app ready status along with failure reason if any.


## 1.1 Limitation of Existing tools:
 - Monit tool is a poll based approach which monitors the configured services for every 1 minute.
 - Monit tools feature of critical process monitoring was deprecated as supervisor does the job. Hence system-health tool which depends on monit does not work.
 - Container_checker in monit checks only for running status of expected containers.
 - Monits custom script execution can only run a logic to take some action but it is yet again a poll based approach.


## 1.2 Benefits of this feature:
 - Event based model - which does not hog cpu unlike poll based approach.
 - Know the overall system status through syslog and as well through CLIs
 - CLIs just connect to the backend daemon to fetch the details. No redundant codes.
 - Combatibility with application extension framework.
    SONiC package installation process will register new feature in CONFIG DB.
    Third party dockers(signature verified) gets integrated into sonic os and runs similar to the existing dockers accessing db etc.
    Now, once the feature is enabled, it becomes part of either sonic.target or multi-user.target and when it starts, it automatically comes under the system monitor framework watchlist.
    However, app ready status for those dockers cant be tracked unless they comply with the framework logic.
    Hence any third party docker needs to follow the framework logic by including "check_up_status" field while registering itself in CONFIG_DB and also make use of the provision given to docker apps to mark its closest up status in STATE_DB.

    


# 2 Feature Requirements

## 2.1 Functional Requirements

Following requirements are addressed by the design presented in this document:

1. Identify the list of sonic services to be monitored and categorize them into core and all services.
2. A new service for the sysmon framework to check system status of all the service units and receive service state change notifications to declare the system ready status.
3. Provision for apps to notify its closest up status in STATE DB. This should internally cover Port ready status.
4. Appropriate system ready syslogs to be raised.
5. New CLIs to be introduced to know the current system status of core and all services.
   - "show system status core" covers the core services.
   - "show system status all" covers the overall system status.
6. During the techsupport data collection, the new CLIs to be included for debugging.


## 2.2 Configuration and Management Requirements

This feature will support CLI and no configuration command is provided for any congiruations.


## 2.3 Scalability Requirements

NA

## 2.4 Warm Boot Requirements

warmboot-finalizer sonic service to be monitored as part of all services.


# 3 Feature Description

This feature provides framework to determine the current system status to declare the system is (almost) ready for network traffic.

System ready is arrived at considering the following factors.
1. All sonic docker services and its UP status(including Portready status)
2. All sonic host services


# 4 Feature Design
## 4.1 Design Overview

- A new service sysmonitor tracks the sonic host service list, all the docker wrapper services for their running status and also, their app ready status including portready and declare the system is ready.
- When sysmonitor daemon boots up, it polls for the service list status once and maintains a global dictionary in ram and publishes the system ready status in form of syslog and as well as in STATE_DB.
- Subsequently, when any service state changes, sysmonitor gets the event notification for that service to be checked for its status and update the dictionary promptly.
- Hence the system status is always up-to-date to be notifed to user in the form of syslog, STATE_DB update and as well as could be fetched by appropriate CLIs.
- The memory for the dictionary is just ~1Kb.


## 4.2 Sysmonitor 

Sysmonitor is the main service daemon which does the job of checking the service status and updating the system readiness.

### 4.2.1 Subtasks in Sysmonitor

1. subscribe to system dbus
   - With the dbus subscription, any systemd events gets notified to this task and it puts the event in the multiprocessing queue.

2. subscribe to the new FEATURE table in STATE_DB of Redis database
   - With the STATE_DB feature table subscription, any input to the FEATURE table gets notified to this task and it puts the event in the queue.

3. Main task
   - Runs through the polling of all service status check once and listen for events in queue populated by dbus task and statedb task to take appropriate action of checking the specific event unit status 
     and updating system status in the dictionary.

4. Listener task
   - A listener task runs in sysmonitor listening in socket /var/run/sysready.socket.
   - Show command communicates with sysmonitor through this socket to get the current system status information from the dictionary maintained.



## 4.3 Service Identification and Categorization

Services are categorized into core services and all services.
1. core services:
    - swss, bgp, teamd, pmon, syncd, database, mgmt-framework are identified as core services and a list of these services are maintained predefined.

2. all services:
    - It covers the enabled services from FEATURE table of CONFIG_DB.I
    - It also covers the HOST_FEATURE table services of CONFIG_DB.
    - Also, since the idea is to cover only the sonic services but not the general system services, sysmonitor tracks services under "multi-user.target" and "sonic.target"
    - This covers all the sonic docker services and most of the sonic host services.


## 4.4 System ready Framework business logic

The system ready framework design should just not only display the current status of the services in the system 
but align the services within framework to flag the status as "not ok" if the service is not running when it was intended to be running.

- A 'core' service must be active and running and up_status marked by docker app should be true to be considered OK, otherwise flag it as Failed
- For 'all' services:
    - Loaded, enabled/enabled-runtime/static, active & running, active & exited state services are considered 'OK'.
    - For active and running services, up_status marked by docker app should be True to be considered 'OK'.
    - Failed state services are considered 'Not OK'.
    - Activating state services are considered as 'Starting'.
    - Deactivating state services are considered as 'Stopping'.
    - Inactive state services category:
        - oneshot services are considered as 'OK'.
        - Special services with condition pathexists check failure are considered as 'OK'.
        - Other services in inactive state are considered to be 'Not OK'.
    - Any service type other than oneshot if by default goes to inactive state, RemainAfterExit=yes entry needs to be added to their service unit file to be inline with the framework.


## 4.5 Provision for apps to mark closest UP status

The feature provides framework for services to mark its closest UP status. 
In simple, each app is responsible in marking its closest up status in STATE_DB. Sysmonitor tool just reads from it.

### 4.5.1 CONFIG_DB Changes (init_cfg.json)

Docker apps marking their UP status in STATE_DB will input an entry in FEATURE table of CONFIG_DB with check_up_status flag set to true through /etc/sonic/init_cfg.json file change.
Host apps marking their UP status in STATE_DB will input an entry in HOST_FEATURE table of CONFIG_DB with check_up_status flag set to true through /etc/sonic/init_cfg.json file change.
Sysmonitor checks for the check_up_status flag in CONFIG_DB before reading the app ready status from STATE_DB. 
If the flag does not exist or if set to False, then sysmonitor will not read the app ready status but just checks the running status of the service.


```
- Schema in /etc/sonic/init_cfg.json
  This json file will be fed to FEATURE & HOST_FEATURE table of CONFIG_DB during bootup.
  This json file will be factory default and no config command will be provided for "check_up_status" entry to be updated in CONFIG_DB later.
           {
              "FEATURE": {
                 "<dockername>": {
                     ...
                     "state": "enabled",
                     "check_up_status": "true"
                 }
              },
              "HOST_FEATURE": {
                 "<hostappname>": {
                     "check_up_status": "true"
                  }
              }
            }
```

### 4.5.2 STATE_DB Changes
- Docker apps which rely on config, can mark 'up_status' to true in STATE_DB  when they are ready to receive configs from CONFIG_DB and/or some extra dependencies are met.
- Respective apps should mark its up_status considering Port ready status. Hence there is no separate logic check needed by system monitoring tool
- Any docker app which has multiple independent daemons can maintain a separate intermediate key-value in the redis-db for each of the daemons and the startup script that invokes each of these daemons can determine the status from the redis entries by each daemon and finally update the STATE_DB up_status.
- Along with up_status, docker apps should update the fail_reason field with appropriate reason in case of failure or empty string in case of success.
- Also, update_time field to be fed in as well in the format of epoch time.
- Host apps update the same FEATURE table in STATE_DB as sysmonitor subtask subscribes to the table. 
  To reduce redundancy in db table subscription, we update the same table in STATE_DB for host apps as well.


For instances,
- swss docker app can wait for port init done and wait for Vrfmgr, Intfmgr and Vxlanmgr to be ready before marking its up status.
- Other apps like udld,stp etc once after waiting for PortInitDone status and interface db creation, they could mark their UP status.
- Database app which is the first/base app to be up, may set the UP_STATUS to True once all the required number of redis-server instances are in running state. 
  However, as the supervisor monitors all the redis db instances as part of critical process list, there is no need of a separate app ready status in database docker.


STATE_DB:
```
- sonic-db-cli STATE_DB HSET "FEATURE|<dockername>" up_status true
- sonic-db-cli STATE_DB HSET "FEATURE|<dockername>" fail_reason "<some reason in string format>" / ""
- sonic-db-cli STATE_DB HSET "FEATURE|<dockername>" update_time "<epoch time format >"

- Schema in STATE_DB
  sonic-db-dump -n STATE_DB output
          "FEATURE|<dockername>": {
            "type": "hash",
            "value": {
              "up_status": "true",
              "fail_reason": "",
              "update_time": "<epoch timestamp>"

            }
           },

- Example:
  "FEATURE|bgp": {
    "type": "hash",
    "value": {
      "fail_reason": "",
      "update_time": "1634119649.7268105",
      "up_status": "true"
    }
  },

```


In addition to this, sysmonitor posts the 'core' and 'all' system status to SYSTEM_READY table in STATE_DB as below.

```
  "SYSTEM_READY|SYSTEM_STATE_CORE": {
    "type": "hash",
    "value": {
      "status": "up"
    }
  }
  "SYSTEM_READY|SYSTEM_STATE_ALL": {
    "type": "hash",
    "value": {
      "status": "up"
    }
  }
```

### 4.5.3 Feature yang Changes

Following field is added to the sonic-feature.yang file and also new table HOST_FEATURE and its field is introduced.

```
container sonic-feature {

       container FEATURE {
 
                ...

                leaf check_up_status {
                    description "This configuration controls the system ready tool to check
                                the app ready/up status";
                    type boolean;
                    default false;
                }
        }
        container HOST_FEATURE {

            description "host feature table in config_db.json";

            list HOST_FEATURE_LIST {

                key "name";

                leaf name {
                    description "host feature name in host Feature table";
                    type string {
                        length 1..32;
                    }
                }

                leaf check_up_status {
                    description "This configuration controls the system ready tool to check
                                the app ready/up status";
                    type boolean;
                    default false;
                }
            }
        }
}
```

## 4.6 Syslogs:

- Syslog to be generated for any Sonic systemd services that changes event(active/inactive)
- A dedicated task in sysmonitor runs to listen for any service state change events.
  Upon receiving any state change events, the task check for its status and identify the particular event service that caused the change and raise a syslog for that service.
- syslog is generated for "System is ready with core services" and "System is not ready - core services are not ok" for core service category.
- Also, for all services, syslog is generated for "System is ready with all the services" and  "System is not ready - One or more services are not ok" scenario, only when there is a change between the two states.

```
Example 1:
 Jul 02 11:53:51.020133 2021 sonic INFO system#monitor: System is not ready - core services are not ok
 Jul 02 11:53:51.020133 2021 sonic INFO system#monitor: System is not ready - one or more services are not ok
 Jul 02 11:53:51.020133 2021 sonic INFO system#monitor: System is ready with core services
 Jul 02 11:53:51.020133 2021 sonic INFO system#monitor: System is ready with all the services

Example 2:
 Jul 02 17:01:00.454978 2021 sonic INFO system#monitor: hostcfgd.service service state changed to [inactive/dead]
 Jul 02 17:01:28.725101 2021 sonic INFO system#monitor: hostcfgd.service service state changed to [active/running]
```

## 5 CLI:

Only Click commands are supported and not KLISH commands as KLISH will not work if Mgmt-framework service is down.
- show system status core

- show system status all
    Options: --brief/--detail
     - show system status all --brief
     - show system status all --detail

### 5.1 Output Format:
    1. Short message indicating system is ready or not
    2. Header - Service-Name, Service-Status, App-Ready-Status, Fail-Reason
    3. List of servies and it status values
    4. Output Strings for Service-Status and App-Ready-Status:
        "OK" - when a service is up
        "Not OK" - to emphasise a service is not running when it was intended to be running.
        "Starting" - Initializing
        "Stopping" - Deactivating
    5. Fail-Reason will be extracted from "Result" property of systemctl command and then displayed appropriately.
       Different reasons can be:
        start-limit-hit
        exit-code
        Inactive
        custom strings from apps

```
    <"System is ready with all the services"/"System is not ready - one or more services are not up">
    <"System is ready with core services"/"System is not ready - core services are not up">
    Service-Name        Service-Status       App-Ready-Status   Fail-Reason
     <service1>         OK                   OK                 -
     <service2>         Not OK               Not OK             start-limit-hit
     <service3>         OK                   Not OK             Inactive
```


### 5.2 show system status core

```
    [#]show system status core
    System is ready with core services

    Service-Name                   Service-Status       App-Ready-Status     Fail-Reason
    swss                           OK                   OK                   -
    bgp                            OK                   OK                   -
    teamd                          OK                   OK                   -
    pmon                           OK                   OK                   -
    syncd                          OK                   OK                   -
    database                       OK                   OK                   -
    mgmt-framework                 OK                   OK                   -
    [#]


    [#]show system status core
    System is not ready - core services are not ok

    Service-Name                   Service-Status       App-Ready-Status     Fail-Reason
    swss                           OK                   OK                   -
    bgp                            Not OK               Not OK               Inactive
    teamd                          OK                   OK                   -
    pmon                           OK                   OK                   -
    syncd                          OK                   OK                   -
    database                       OK                   OK                   -
    mgmt-framework                 OK                   OK                   -
    [#]
```


### 5.3 show system status all

```
    root@sonic:/# show system status all
    System is ready with all the services

    Service-Name                   Service-Status       App-Ready-Status     Fail-Reason
    as7712-pddf-platform-monitor   OK                   OK                   -
    bgp                            OK                   OK                   -
    caclmgrd                       OK                   OK                   -
    config-setup                   OK                   OK                   -
    containerd                     OK                   OK                   -

    root@sonic:/# show system status all
    System is not ready - one or more services are not ok

    Service-Name                   Service-Status       App-Ready-Status     Fail-Reason
    aaastatsd                      Not OK               Not OK               start-limit-hit
    as7712-pddf-platform-monitor   OK                   OK                   -
    bgp                            OK                   Starting             -
    caclmgrd                       OK                   OK                   -
    config-setup                   OK                   OK                   -
    ntp-config                     Starting             Starting             -
    pmon                           OK                   Not OK               Transceiver daemon is not up
```

### 5.4 show system status all --brief
- The output of this command will just display the brief status of the entire sonic services.
- Output format of the CLI :

```
    <"System is ready with all the services"/"System is not ready - one or more services are not ok">

    Example 1:
    root@sonic:/# show system status all --brief
    System is not ready - one or more services are not ok

    root@sonic:/#
```

### 5.5 show system status all --detail
- This command would display systemctl status output of failed services along with "all" option output.

- Output format of the CLI :

```
    <"System is ready with all the services"/"System is not ready - one or more services are not ok">
    Service-Name        Service-Status       App-Ready-Status   Fail-Reason
     <service1>         OK                   OK                 -
     <service2>         Not OK               Not OK             start-limit-hit
     <service3>         OK                   OK                 -

    ● system-health1.service - SONiC system health monitor
      Loaded: loaded (/lib/systemd/system/system-health.service; enabled-runtime;
      Active: failed (Result: start-limit-hit) since Thu 2019-02-14 11:21:09 UTC;
      Main PID: 4764 (code=exited, status=0/SUCCESS)



    Example:
    root@sonic:/# show system status all --detail
    System is not ready - one or more services are not OK

    Service-Name                   Service-Status       App-Ready-Status     Fail-Reason
    as7712-pddf-platform-monitor   OK                   OK                   -
    bgp                            OK                   OK                   -
    caclmgrd                       OK                   OK                   -
    ...
    telemetry                      OK                   OK                   -
    tpcm                           OK                   OK                   -
    udld                           Not OK               Not OK               exit-code
    updategraph                    OK                   OK                   -
    vrrp                           OK                   OK                   -

    ● udld.service - UDLD container
       Loaded: loaded (/usr/lib/systemd/system/udld.service; enabled; vendor preset: enabled)
       Active: failed (Result: exit-code) since Fri 2021-07-02 11:53:09 UTC; 2h 8min ago
      Process: 1827 ExecStartPre=/usr/bin/udld.sh start (code=exited, status=255)
          CPU: 161ms
```

## 6 Serviceability and Debug

- The system logging mechanisms explained in section 4.6 shall be used.
- The show commands can be used as debug aids.
- Techsupport:
  In generate dump tool, show system status all --detail CLI is included to be saved to the dump in the name of systemstatus.all.detail



## 7 Warm Reboot Support

Sysmonitor monitors the running status of warmboot-finalizer.service
This can be enhanced to hook to the actual completion of warboot-finalizer service later.


## 8 Unit Test Cases

1. Check show system status all
2. Check show system status all --brief
3. Check show system status all --detail
4. Check show system status core
5. Make any of the docker apps down and check failed apps details are shown
6. Make any of the host apps down and check failed apps details are shown
7. Check top command for sysmonitor CPU and memory usage
8. Check syslogs for any service state change.
9. Check syslog for overall system status change.

## 9 References
NA
