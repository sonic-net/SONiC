# Crash Capture Support #
#### Rev 1.0


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/15/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |


## About this Manual
This document describes the details of the system in place which facilitates the crash capture support in SONiC when the NOS generates a core dump.

## 1. Overview
Currently, techsupport invocation is done by invoking `show techsupport` either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall All the high-level enhancements are summarized in the next section

## 2. High Level Requirements
* Techsupport invocation should also be made event-driven based on core dump generation
* This capability should be made optional and is disabled by default
* Users should have the abiliity to turn this capability on and off.

## 3. Core Dump Generation in SONiC
In SONiC, the core dumps generated from any process crash across the dockers and the base host are directed to the location `/var/core` and will have the name `/var/core/*.core.gz`. 
The naming format and compression is governed by the script `/usr/local/bin/coredump-compress`.

## 4. Design

### 4.1 Script to invoke the techsupport CLI
A new python script `/usr/local/bin/crash-capture` will be added for this purpose and when invoked, it checks if a core-dump file has been generated within the last 20 sec and if yes, will invoke the techsupport dump. 
Additionally, the CLI invocation will also have a `since` flag indicating the last time the tech support was run, if any.

### 4.1 Event-trigger for Core-dump generation
To Monitor and respond for the file-change events in `/var/core/`, systemd path unit will be used. This unit will start a corresponding systemd unit, which inturn invokes the crash-capture python script
