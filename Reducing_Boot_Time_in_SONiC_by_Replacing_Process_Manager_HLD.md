# Reducing Boot Time in SONiC by Replacing Process manager #


## Revision
###### Table 1: Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             |                    | Initial version                   |

## Table of Content
-
    - [Table of Content](#table-of-content)
    - [List of Tables](#list-of-tables)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [1. Overview](#1-overview)
    - [2. Requirements](#2-requirements)
    - [3. Architecture Design](#3-architecture-design)
    - [4. High-Level Design](#4-high-level-design)
        - [4.1 Supervisord Boot time measurement using Flamegraph](#41-supervisord-boot-time-measurement-using-flamegraph)
        - [4.2 Comparison between Different process manager](#42-comparison-between-different-process-manager)
        - [4.3 Boot time improvement using runit method](#43-boot-time-improvement-using-runit-method)
        -[4.4 Traffic resumption time using runit method](#44-traffic-resumption-time-using-runit-method)
        - [4.5 Supervisord to Runit config translation](#45-supervisord-to-runit-config-translation)
        - [4.6 Enabling Runit as the process manager](#46-enabling-runit-as-the-process-manager)
        - [4.7 Managing Critical Processes with runit](#47-managing-critical-processes-with-runit)
        - [4.8 System Health Monitoring](#48-system-health-monitoring)
        - [4.9 Disabling runit and Re-enabling Supervisord](#49-disabling-runit-and-re-enabling-supervisord)
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


## List of Tables
* [Table 1: Revision](#table-1-revision)
* [Table 2: Abbreviations](#table-2-abbreviations)




## Scope
This document outlines the high-level design for replacing the current process manager (e.g., `supervisord`) in SONiC with a more efficient alternative to reduce boot times.

## Definitions/Abbreviations
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| SONiC                    | Software for Open Networking in the Cloud    |


## 1. Overview
Rapid network availability is essential, and SONiC's boot time directly impacts this. To improve startup speed, this project focuses on optimizing service initialization by replacing the existing process manager with a higher-performance alternative. This is particularly crucial for switches leveraging the ASIC's internal CPU to run SONiC.

## 2. Requirements
* Minimize SONiC boot time.
* Maintain compatibility with existing SONiC services and configurations.
* Ensure the stability and reliability of the new process manager.
* Implement a seamless transition with minimal disruption.

## 3. Architecture Design
To enhance performance, the current process manager inside docker will be replaced with runit. Existing service configurations will be converted to the runit format, and the system's init process will be modified to use runit.

## 4. High-Level Design

### 4.1 Supervisord Boot time measurement using Flamegraph
Boot time analysis on a 48-port device with a dual-core ARM-v8.2 Cortex-A55 CPU cluster revealed the following breakdown:


```
| Operation                     | Total Time (mm:ss) | Time Delta (mm:ss) |
|-------------------------------|------------------- |--------------------|
| Reboot to BIOS Print          | 02:09              |                    |
| BIOS Print to SONiC Login     | 02:45              | 00:36              |
| SONiC System Up Time          | 07:45              | 05:00              |
| Show Interface with Link Up   | 11:45              | 04:00              |
```
Initialization performance analysis revealed that supervisord and supervisorctl contribute significantly to boot time, consuming roughly 20% of the total initialization period. This suggests that migrating away from these Python-based tools might offer a performance improvement. Generally, Python applications can exhibit slower startup times in these types of scenarios.

![alt text](perf-supervisorctl.png)

Potential replacement process managers will be evaluated based on criteria such as speed, resource consumption, and ease of integration with SONiC:
* **runit:**  Simple, robust, and performant.
* **tini:** Minimalistic, ideal for containerized environments, if applicable to SONiC's services.



### 4.2 Comparison between Different process managers

```
| Feature                       | Supervisord                             | Runit                               |
|-------------------------------|-----------------------------------------|-------------------------------------|
| Language                      | Python                                  | C                                   |
| Goal                          | Feature-rich process management   	  | Simple & robust service supervision |
| Resource                      | Low overhead                            | High overhead                       |
| Boot time                     | Slow                                    | Fast                                |
| Configuration                 | File based                              | Directory based                     |
| Process Control               | Extensive process control               | Service Monitoring                  |

```

Tini is not explored since it doesnt have monitoring capability.

### 4.3 Boot time improvement using runit method

Replacing supervisord with runit on a 48-port device featuring a dual-core ARM-v8.2 Cortex-A55 CPU cluster yielded a 15-20% improvement in overall boot time and interface link-up time. Baseline measurements were:



```
|                               | Runit                                   | Supervisord                             |
--------------------------------------------------------------------------------------------------------------------
| Operation                     | Total Time (mm:ss) | Time Delta (mm:ss) | Total Time (mm:ss) | Time Delta (mm:ss) |
|-------------------------------|------------------- |--------------------|------------------- |--------------------|
| Reboot to BIOS Print          | 01:55              |                    | 02:09              |                    |
| BIOS Print to SONiC Login     | 02:26              | 00:31              | 02:45              | 00:36              |
| SONiC System Up Time          | 06:45              | 04:20              | 07:45              | 05:00              |
| Show Interface with Link Up   | 09:45              | 03:00              | 11:45              | 04:00              |
```

Runit, usage is very minimal it didnt show up in the perf run.

![alt text](perf-runit.png)

Supervisor bootchart 

![alt text](Bootchart_supervisor.png)
 Runit bootchart
![alt text](image-1.png)


### 4.4 Traffic resumption time using runit method
Runit demonstrated improved reboot performance compared to supervisord, as measured by data traffic loss time on a dual-core ARM-v8.2 Cortex-A55 CPU cluster. The following measurements detail runit's data traffic loss time:

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
| Function                   | Total Frames sent | Sent Rate (packets/sec) | Total Frames Received | Frames difference  | Recovery time (secs)  
|-------------------------------|------------------- |--------------------|------------------- |--------------------| -------|
|Runit          | 120000000             |    100000               |     93983209       |   26016904                 | 260
| Supervisor    |  120000000             |  100000           |  82543323         | 37456737                | 374
| 

### 4.5 Supervisord to Runit config translation

One option we are choosing is to use a Python script to automate the conversion of existing process manager (specifically supervisord) configurations into the runit format. This script, executed as part of a Docker entrypoint, transforms the provided supervisord configuration into runit service directories. This approach facilitates migration for Docker applications utilizing Jinja2 templated configuration files alongside traditional supervisord.conf files. There can be other options as well like static sv scripts etc.

```
A Supervisord configuration defines a program named orchagent. This program, /usr/bin/orchagent.sh, depends on the portsyncd service. The conversion script translates this dependency into a runit run script for the orchagent service. The generated /etc/service/orchagent/run script waits for portsyncd to reach a running state before executing /usr/bin/orchagent.sh. This ensures the dependency is met before the orchagent process starts.

Example 1:

[program:orchagent]                         
command=/usr/bin/orchagent.sh               
priority=4                                  
autostart=false                             
autorestart=false                           
stdout_capture_maxbytes=1MB                 
stdout_logfile=syslog                       
stderr_logfile=syslog                       
dependent_startup=true                      
dependent_startup_wait_for=portsyncd:running

This will be converted as follows in the transition script
cat /etc/service/orchagent/run
#!/bin/sh  
while ! sv status portsyncd | grep -q 'run:'; do
    sleep 1
done

exec /usr/bin/orchagent.sh
```
```
Example 2:

neighsyncd has to be started only after swssconfig is exited is handled as follows.

[program:neighsyncd]                         
command=/usr/bin/neighsyncd                  
priority=7                                   
autostart=false                              
autorestart=false                            
stdout_logfile=syslog                        
stderr_logfile=syslog                        
dependent_startup=true                       
dependent_startup_wait_for=swssconfig:exited 

root@Celestica-ES1000-24P:/# cat /etc/service/neighsyncd/run   
#!/bin/sh                                                      
                                                               
while ! sv status swssconfig | grep -q 'down:'; do             
    sleep 1                                                    
done                                                           
                                                               
exec /usr/bin/neighsyncd                                       
```


### 4.6 Enabling Runit as the process manager

To enable runit as the process manager, create an empty file named /etc/runit-manager and then trigger a configuration reload. This can be achieved by executing the command config reload or by reloading the device.

```
touch /etc/runit-manager
config reload [or] reload the device
```

This process triggers the following:

1. When the service is restarted using systemctl, the existing Docker service is removed.
2. A new Docker service is created with the Docker label sonic_docker_config="runit" and the Docker environment variable sonic_docker_config="runit". sonic_docker_config label has 2 purposes
```
a) This option marks the container instances as "runit" instead of "supervisord," allowing further enable/disable operations to skip removing the container if it is already configured to run with the specified process manager.

b) This label option is also used to determine the process health status. Please refer to section 4.7 for more details.
```
3. When Docker starts, it verifies the above environment variable and chooses whether to execute the Docker process with runit or supervisord as the process manager.

### 4.7 Managing Critical Processes with runit
SONiC includes a feature to restart the Docker container if a critical process exits due to system signals (such as SIGTERM, SIGSEGV, etc.). This is managed by /usr/bin/supervisor-proc-exit-listener running inside the container.

This functionality is achieved using a runit finish script for critical processes, which terminates the Docker container by sending a signal to process ID 1, as shown below:

```
root@Celestica-ES1000-24P:/# cat /etc/service/orchagent/finish
#!/bin/sh                                                     
sv stop orchagent                                             
exec kill -s SIGTERM 1                                        
exit 0                     
```

### 4.8 System Health Monitoring
SONiC continuously monitors Docker health status using a system-health checker script. This script executes supervisorctl status inside the Docker container to fetch the running status of each process, as shown below:

```
show system-health detail
swss:orchagent             OK        Process
swss:portsyncd             OK        Process
swss:neighsyncd            OK        Process
swss:fdbsyncd              OK        Process
...
```

To achieve this functionality, the system-health checker has been enhanced to handle both supervisorctl and runit. It uses separate classes depending on the system configuration, validated by checking the Docker container label "sonic_docker_config"

service status can be fetched using following commands

```
sv status /etc/service/*
run: /etc/service/buffermgrd: (pid 84) 2394s
run: /etc/service/orchagent: (pid 99) 2394s
```


### 4.9 Disabling runit and Re-enabling Supervisord
Removing /etc/runit-manager and then rebooting (or executing config reload) will restore Supervisord as the process manager. The system will then launch containers configured to use supervisord, effectively reversing the migration to runit.


```
rm /etc/runit-manager
reboot [or] config reload
```

## 5. SAI API
N/A - This change is not directly related to the SAI API.

## 6. Configuration and management
### 6.1. Manifest (if the feature is an Application Extension)
N/A -  Not applicable if not implemented as an application extension.

### 6.2. CLI/YANG model Enhancements
Any necessary CLI commands for managing the new process manager will be defined and implemented.  Corresponding YANG models will be updated or created.

### 6.3. Config DB Enhancements
Any changes required to the configuration database schema will be documented and implemented.

## 7. Warmboot and Fastboot Design Impact
N/A

## 8. Restrictions/Limitations
Any limitations or restrictions imposed by the chosen process manager will be documented.

## 9. Testing Requirements/Design
### 9.1 Unit Test cases
1. Verify whether all process starts up in all dockers
2. Verify when critical process exits docker are restarted
3. Verify system-healthd command works fine with runit
4. Verify moving from supervisord to runit works fine
5. Verify moving from runit to supervisord works fine
6. Verify boot time improved with runit
7. config reload and system reboot works fine
8. Verify traffic loss improvement with runit after device reload.
9. Verify warmboot and fastboot works fine with runit.

### 9.2 System Test cases
Comprehensive system tests will be conducted to measure boot time improvements and ensure the stability and functionality of SONiC with the new process manager.

## 10. Open/Action items - if any
Any open issues or action items will be tracked here.  This may include tasks like benchmarking different process managers, developing the configuration conversion tool, and updating the init process.

```
Currently, runit doesn't offer equivalent functionality to Supervisord supervisor-proc-exit-listener for syslog alerting based on process states. This is a gap in functionality we need to address.
```



[def]: image.png
[def2]: #41-candidate-supervisors