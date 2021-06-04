# Crash Capture Support #
#### Rev 1.0

## Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [1. Overview](#1-overview)
  * [2. High Level Requirements](#2-high-level-requirements)
  * [3. Core-Dump-Generation-in-SONiC](#3-core-dump-generation-in-sonic)
  * [4. Design](#4-design)
      * [4.1 Script to invoke the techsupport CLI](#41-Script-to-invoke-the-techsupport-CLI)
      * [4.2 Event trigger for Core-dump generation](#42-Event-trigger-for-Core-dump-generation)
      * [4.3 Crash Capture ecosystem should be configurable](#43-crash-capture-ecosystem-should-be-configurable)
      * [4.4 CLI Enhancements](#44-CLI-Enhancements)


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/04/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |


## About this Manual
This document describes the details of the system in place which facilitates the crash capture support in SONiC when the NOS generates a core dump.

## 1. Overview
Currently, techsupport is run by invoking `show techsupport` either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall idea behind this HLD. All the high-level requirements are summarized in the next section

## 2. High Level Requirements
* Techsupport invocation should also be made event-driven based on core dump generation
* This capability should be made optional and is disabled by default
* Users should have the abiliity to configure this capability.

## 3. Core Dump Generation in SONiC
In SONiC, the core dumps generated from any process crash across the dockers and the base host are directed to the location `/var/core` and will have the name `/var/core/*.core.gz`. 
The naming format and compression is governed by the script `/usr/local/bin/coredump-compress`.

## 4. Design

### 4.1 Script to invoke the techsupport CLI
A new python script `/usr/local/bin/crash-capture` will be added for this purpose and when invoked, it checks if a core-dump file has been generated within the last 20 sec and if yes, will invoke the techsupport dump. 
Additionally, the CLI invocation will also have a `since` flag indicating the last time the tech support was run, if any.

### 4.2 Event-trigger for Core-dump generation
To Monitor and respond for the file-change events in `/var/core/`, systemd path unit will be used. This unit will start a corresponding systemd unit, which inturn invokes the crash-capture python script

#### crash-capture.path
```
[Unit]
Description=Triggers the Unit when a core is dumped
After=database.service, crash-capture-configure.service
Requires=database.service, crash-capture-configure.service

[Path]
PathExists=/var/core/
Unit=crash-capture.service

[Install]
WantedBy=multi-user.target
```

#### crash-capture.service
```
[Unit]
Description=Executes the crash-capture script when triggered
After=database.service, crash-capture-configure.service
Requires=database.service, crash-capture-configure.service

[Service]
Type=simple
ExecStart=/usr/local/bin/crash-capture

[Install]
WantedBy=multi-user.target
```

Note: Both of these will have strict ordering dependency on database.service and not swss or sonic.target, because the crashes might occur during the swss/syncd bringup etc. And for this to be captured the service should be active before the start of these services. The other dependency is `crash-capture-configure.service` which will be explained in the next section.

### 4.3 crash-capture ecosystem should be configurable.

Turning on this feature would just mean unmasking or enabling  both of crash-capture.{path, service} and starting crash-capture.path
Similarly, turning this off would be masking or disabling these two.

A new schema is added to Cfg DB which is defined below. 

#### Schema additions to Config DB
```
key = "CRASH_CAPTURE|global"
state = enabled;
```

To monitor the config changes pushed by the user, a crash-capture-daemon will be started. 
This'll be started using crash-capture-configure.service.

#### crash-capture-configure.service
```
[Unit]
Description=Starts the daemon which monitors the crash-capture config changes
After=database.service
Requires=database.service

[Service]
Type=simple
Restart=always
ExecStart=/usr/local/bin/crash-capture-daemon

[Install]
WantedBy=multi-user.target
```

This service starts the crash-capture-daemon. The crash-capture-daemon script subscribes to Config DB and listens for changes made to `CRASH_CAPTURE|global` key. 
It then enables or disables the service accordingly 

### 4.4 CLI Enhancements.

### config cli

`config crash-capture <enabled/disabled>`

### show cli

`show crash-capture status`



