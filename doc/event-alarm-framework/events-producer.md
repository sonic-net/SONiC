# Event Producer via rsyslog

## Goals
1. Identify alertable events
2. Detect those events
3. Stream the event as structured data
4. Have the ability to stream at the max of 10K messages per second
5. Events are unmutable across releases, but can be deprecated
6. Meet the reliability of 99.5% - event generted to end client 
7. Rate of event reporting is in par with rate of syslog reporting.


## Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes.


![image](https://user-images.githubusercontent.com/47282725/156947460-66d08b3d-c981-4413-b0d5-232643dfba01.png)


![image](https://user-images.githubusercontent.com/47282725/158892209-daf6a477-45ce-4051-b2cc-13422b34ead5.png)


## Requirements
### Events
1. Events are defined per process.
2. Every event is identified by tag, which is unique within a process with zero or more event specific parameters.
3. Events are static (*don't change*) across releases, but can be deprecated in newer releases.
4. Every event is described in YANG schema.
5. YANG schema files for all events are available in a single location for NB clients to refer in Switch.

### Event detection
1. The method of detection can be any.
2. This can vary across events
3. Syslog messages could be a source or custom queries or update code to report events directly or ...
4. There can be multiple event detectors running under different scopes

### Event reporting
1. Streaming via UDP (multicast) is required, as that allows scope for multiple clients at the consumer end.
2. Straming via UDP could meet the performance goal.
3. The structured data is per YANG definition
4. RFE: A listener to update redis/anyother persistence destination with current event status

### Event exporter
1. Telemetry container will have a local listener for the events reported.
2. Telemetry provides support for multiple external clients to forward the received events
3. RFE: Telemetry upon restart will use redis-persistence to get the missed updates

## A solution
1. Parse the log messages as app emits it, via rsyslog plugin, hence transparent to App.
2. Push the parsed data as JSON struct of {name: val[, ...]} to telemetry listener via UDP
3. The telemetry would stream the data out to interested clients through SAMPLE or ONCHANGE mode.
4. Now any tool can subscribe to this strteam for live Event updates
5. The tools can consume data with ease, as the switch has done the parsing job.
6. The container image provides the regex to parse the log messages. Hence the app is free to update its log messages however but as well update regex to be in sync.
7. All the containers could start using this solution w/o requiring any code update.</br>
   New builds will include two additional files per container. (*.conf for rsyslog & regex for parsing*)</br>
   We could even update released builds that are running in switches, as all it needs is to add two files and rsyslog restart per container.
8. The rsyslog plugin could use the new macro provided by Event-Alarm FW, when it become available. This will be handy for III party containers.


## Events:

### Defintion

Yang model provides the list of events and the defintions on the structured data

A sample:
module events-bgp {
    ...
    container bgp_status {
        list event_list {
            key "type"
            
            leaf type {
                enum "admin_up";
                enum "admin_down";
                enum "idle";
                enum "active";
                enum "open";
                enum "established";
            }
            
            leaf ip {
                type inet:ip-address;
                description "IP of neighbor";
            }
            
            leaf timestamp {
                type inet::date-and-time;
                description "time of the event"
            }
        }
    }
    
## Design
![image](https://user-images.githubusercontent.com/47282725/157343412-6c4a6519-c27b-459b-896b-7875d8f952b8.png)

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



# Next Step:
When alarm-event FW is functional, the plugin could start using the macros provided by the FW, for identified tags as events.


# CLI
None


# Test
We could upgrade existing test cases to additionally listent to gNMI stream on a different thread to verify expected events were streamed.

