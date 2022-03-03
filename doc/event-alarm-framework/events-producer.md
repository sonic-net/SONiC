# Event Producer via rsyslog

## Goals
1. Ability to stream syslog messages from apps as structured data via streaming telemetry
2. Adapt III party applications to Events/alarm framework

## Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes, oftent 10+.

### Current
![image](https://user-images.githubusercontent.com/47282725/156665693-c701c4da-27a7-4257-9236-548898ff8092.png)

### Desired
![image](https://user-images.githubusercontent.com/47282725/156665731-c61d29bd-91f0-4626-b830-5fbbb50c781d.png)


## A solution
1. Parse the log messages as app emits it, via rsyslog plugin, hence transparent to App.
2. Push the parsed data as JSON struct of {name: val[, ...]} to a redis DB table.
3. Now any tool can subscribe to that table for events. External tools can use gNMI streaming telemetry for poll or OnChange.
4. The tools can consume data with ease, as the switch has done the parsing job.
5. The container image provides the regex to parse the log messages. Hence the app can update the log however and as well update regex to be in sync.
6. All the containers could start using this solution w/o requiring any code update.</br>
   New builds will include two additional files per container.</br>
   We could even update released builds that are running in switches, as all it needs is to add two files and rsyslog restart per container.
8. RFE: The containers that SONiC owns, like swss & syncd, could switch to using new macro provided by event-Alarm framework over time.
10. The containers that use event-Alarm framework could still use this solution to add new events until a code update/new build occurs in future.
11. The III party containers could always use this approach.
12. The rsyslog plugin would use the new macro provided by Event-Alarm FW, when it become available.

## Pros & Cons

### Pro
1) This support is external to app, hence adapts well with III party applications, bgp, teamd, ... 
2) This feature can be added to released builds too, as all it takes is to copy two files into each container and restart rsyslogd in the container
3) The regex for parsing being local to container, it supports any container upgrade transaparently.
4) The rsyslog plugin can be a shared copy that the container can run from shared folder in host. This helps provide a overall control across all containers.
5) The data being structured, the nightly tests can ensure the data integrity across releases.
6) The message parsing load is distributed as per container. Within a container parsing is done at the granularity of per process with no extra cost as rsyslogd already pre-parsed it per-process, *always*
7) The regex file provides the unique identity for each event. The structured JSON data is easier for tools to parse.
8) Being structured data, the apps are free to add more or less data elements across releases. Tools can be tolerant for missing or additional data, as use it if exists.
9) Streaming telemetry support is already available

### con:
1) Two step process for devs, as for each new/updated log message ***for an event***, add/update regex as needed. The adoption to new Event-Alarm FW will avoid this.
2) The rsyslogd is *required*. It should be treated as critical process in each container.

# Design

![image](https://user-images.githubusercontent.com/47282725/156477501-7bc587a5-b5e0-4b2b-bfe5-1a4894482f16.png)

# Next Step:
When alarm-event FW is functional, the plugin would start using the macros provided by the FW.
The regex inside the continer will match the event/alarm name to regex for that message. This provides the container freedom to evolve w/o updating the central config.
The additional config supported by the FW like enable/disable, priority, ... will be availablein the centralized per image config file as proposed in the FW.

# CLI
This work is only a backend support to retrieve message from apps to redis-DB, which is consumed by external tools via gNMI.
The new FW which offers higher level functionality by qualifying messages as EVENTS & ALARMS will provide the required CLI support for configuration & view.


# Test
We could upgrade existing test cases to additionally look for structured messages in redis for each scenario being tested.

