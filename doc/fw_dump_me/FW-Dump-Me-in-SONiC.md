# FW Dump Me in SONiC HLD

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [FW Dump Me in SONiC HLD](#fw-dump-me-in-sonic-hld)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.1](#rev-01)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [List of Figures](#list-of-figures)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [1. Overview](#1-overview)
- [2 Requirements Overview](#2-requirements-overview)
  - [2.1 Functional requirements](#21-functional-requirements)
- [3 Modules design](#3-modules-design)
  - [3.1 FW Dump Me build and runtime dependencies](#31-fw-dump-me-build-and-runtime-dependencies)
  - [3.2 FW Dump Me docker container in SONiC](#32-fw-dump-me-docker-container-in-sonic)
  - [3.3 FW Dump Me in SONiC overview](#33-fw-dump-me-in-sonic-overview)
  - [3.4 FW Dump Me service in SONiC](#34-fw-dump-me-service-in-sonic)
  - [3.5 FW Dump Me feature table](#35-fw-dump-me-feature-table)
  - [3.6 FW Dump Me provided data](#36-fw-dump-me-provided-data)
  - [3.7 FW Dump Me output file](#37-fw-dump-me-output-file)
  - [3.8 CLI](#38-cli)
    - [3.8.1 Enabled/disable FW Dump Me feature](#381-enableddisable-fw-dump-me-feature)
  - [3.9 FW Dump Me daemon](#39-fw-dump-me-daemon)
    - [3.9.1 Main thread](#391-main-thread)
    - [3.9.2 FW Dump Me communication with CLI](#392-fw-dump-me-communication-with-cli)
- [4 Flows](#4-flows)
  - [4.1 FW dump taking logic "trap handling"](#41-fw-dump-taking-logic-trap-handling)
  - [4.2 FW trap generation](#42-fw-trap-generation)
  - [4.3 SDK trap generation](#43-sdk-trap-generation)
  - [4.4 Error flow - Dump taking failed (or timed out)](#44-error-flow---dump-taking-failed-or-timed-out)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)

# List of Figures
* [FW Dump Me in SONiC overview](#33-fw-dump-me-in-sonic-overview)
* [FW Dump Me general flow](#4-flows)

# Revision
| Rev | Date     | Author          | Change Description                 |
|:---:|:--------:|:---------------:|------------------------------------|
| 0.1 | 08/11    | Shlomi Bitton   | Initial version                    |

# About this Manual
This document provides an overview of the implementation and integration of FW Dump Me feature in SONiC.

# Scope
This document describes the high level design of the FW Dump Me feature in SONiC.

# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| SONiC         | Software for open networking in the cloud |
| API           | Application programming interface         |
| SAI           | Switch Abstraction Interface              |
| SDK           | Software Developement Kit                 |
| FW            | Firmware                                  |

# 1. Overview

FW Dump Me feature gives the user a way to generate a full FW dump, even if the FW is stuck, as such we would like to "communicate" directly with the HW and not use the FW to get the info

# 2 Requirements Overview

## 2.1 Functional requirements

FW Dump Me feature in SONiC should meet the following high-level functional requirements:

- FW Dump Me feature provides functionality as a seperate docker container built in Mellanox SONiC image.
- FW Dump Me feature is optional in SONiC, thus can be enabled or disabled per user request at runtime.
- FW Dump Me will create the dump by three possible cases:
  - FW originated trap.
  - SDK originated trap.
  - User specifically requested for a dump.

# 3 Modules design

## 3.1 FW Dump Me build and runtime dependencies

####################################

## 3.2 FW Dump Me docker container in SONiC

A new docker image will be built for mellanox target called "docker-fw-dump-me" and included in Mellanox SONiC build by default.<p>
Build rules for FW Dump Me docker will reside under *platform/mellanox/docker-fw-dump-me.mk*.

```
admin@sonic:~$ docker ps
CONTAINER ID        IMAGE                                COMMAND                  CREATED             STATUS              PORTS               NAMES
...
2b199b2309f9        docker-fw-dump-me:latest             "/usr/bin/supervisord"   17 hours ago        Up 11 hours                             docker-fw-dump-me
```

* SDK Unix socket needs to be mapped to container (for CLI support).
* */var/log/mellanox/* mounted inside container (used for writing dump files)
* */var/run/fw_dump_me/* mounted inside container (used for Unix domain socket)

## 3.3 FW Dump Me in SONiC overview 

![FW Dump Me in SONiC overview](/doc/fw_dump_me/overview.svg)

## 3.4 FW Dump Me service in SONiC

####################################

## 3.5 FW Dump Me feature table

Community [introduced](https://github.com/Azure/SONiC/blob/master/doc/Optional-Feature-Control.md) a way to enable/disable optional features at runtime and provided a seperate **FEATURE** table in CONFIG DB.

```
admin@sonic:~$ show features 
Feature               Status
-------------------   --------
telemetry             enabled
fw-dump-me            enabled
```

```
admin@sonic:~$ sudo config feature fw-dump-me [enabled|disabled]
```

The above config command translates into:

enabled command:
```
sudo systemctl enable fw-dump-me
sudo systemctl start fw-dump-me
```

disabled command:
```
sudo systemctl stop fw-dump-me
sudo systemctl disable fw-dump-me
```

By default FW Dump Me feature will be disabled.

## 3.6 FW Dump Me provided data

- The generating cause & time (the cause of the “FW dump me now trap” or the reason the high level decided to take the dump).
- FW trace, I.E the FW configuration done to the HW from the beginning of time (boot). 
- GDB core files of all irisc’s.
- As much of the CR space according to priority defined in the ADB file.

## 3.7 FW Dump Me output file

The output file will be generated in "/var/log/mellanox/" if triggered by FW or SDK cause.
If the user will trigger the dump taking, it will be generated under the path provided by the user.
If no path provided, the default location will be used.

The new dump file name will be: <device_id>/<module_name>_<time_stamp>

## 3.8 CLI

Since the FW Dump Me daemon is running on a seperate container, CLI will be provided by an additional thread communicating with the host with a socket. The thread is running on the docker, recieve and process requests from the host to trigger dump generating.

The command to create a new dump:
```
admin@sonic:~$ fwdumpme <desired_path>
```

### 3.8.1 Enabled/disable FW Dump Me feature

Already implemented as part of "optional features" feature:

Config CLI:
```
admin@sonic:~$ config feature fw-dump-me [enabled|disabled]
```
Show CLI:
```
admin@sonic:~$ show features 
Feature               Status
-------------------   --------
telemetry             enabled
fw-dump-me            enabled
```

## 3.9 FW Dump Me daemon

### 3.9.1 Main thread

The main thread will register to the relevant trap group and listen to events generated by FW/SDK/User.
Upon event arrival, a proper message will be logged in the system log containing all event information.
The dump will be automaticaly generated on event.

Log messages example as they appear on 'systemlog':

```
Aug 13 09:03:17.429153 r-tigon-04 INFO fw-dump-me#fw_dumpd: Dump taking started, Cause: "register: XXX gobit not cleared"
Aug 13 09:03:17.429153 r-tigon-04 INFO fw-dump-me#fw_dumpd: Dump taking started, Cause: "register: XXX failed, FW RC: YYY"
Aug 13 09:03:17.429153 r-tigon-04 INFO fw-dump-me#fw_dumpd: Dump taking finished, File path: /var/log/mellanox/fw_dump_r-tigon-04_20200813_013434
Aug 13 09:03:17.429153 r-tigon-04 ERR fw-dump-me#fw_dumpd: Dump taking failed, Cause: "Timeout reached"
```

### 3.9.2 FW Dump Me communication with CLI

In order to not produce additional load in Redis DB or bringing another Redis instance specifically for FW Dump Me another IPC mechanism will be used.
A suggested alternative is a Unix domain socket. It may be placed under */var/run/fw-dump-me/dump.sock* which will be mapped to FW Dump Me container.

On CLI request FW Dump Me daemon trigger dump generation from FW and save it on the requested path.

CLI/FW Dump Me daemon communication protocol will be text based in the following format:

```
path    = string ; location for saving output files
```

Since the design is focused on one CLI client, only one connection will be handled at the time.

A considerable timeout has to be set on socket so that send/recv will not block CLI or daemon if one side unexpectedly terminates.

# 4 Flows

![FW Dump Me general flow](/doc/fw_dump_me/flow.svg)

## 4.1 FW dump taking logic "trap handling"

SONiC will handle the "fw dump me trap" as well as the action from the CLI by activating the "sx_fw_dump" flow.
1.	set a timer
2.	call: "sx_fw_dump <device_id> <file_path> <extra_info>"
3.	move the "fw dump file" to a designated (new) location: /var/opt/tms/fwdumps/system/<file> and add the info from the trap (cause + buffer) into the dump file

SDK will handle the "sx_fw_dump <device_id> <file_path> <extra_info>" generated by OS and will implement the "mstdump"+"gdb_dump"+"mlxtrace" logic to the "dump" logic

## 4.2 FW trap generation

The FW will generate the MFDE trap for internal FW causes (see FW ARCH)

## 4.3 SDK trap generation

The SDK will generate the MFDE trap for internal SDK causes when it encounters:
"go bit not cleared", FW timeout

## 4.4 Error flow - Dump taking failed (or timed out)

The "sx_fw_dump" will be executed with timeout that will close the application if it took too long.
in such a case a log error will be added

## Open Questions

* Should we limit the amount of generated dump files on the system?
If yes, should we replace old ones with new ones?

* "show techsupport" command - Should we take a FW dump even if the feature is disabled?
Filter the command output by date should exclude old fw dump files?

