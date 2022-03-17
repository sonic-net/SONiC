# Event Producer via rsyslog

## Goals
1. Provide a unified way for storing identified alertable events in SONiC switch.
2. Provide a unified way for event detectors to report the events.
3. Enforce a structured format for event data with pre-defined schema.
4. Have the ability to stream at the max of 10K events per second to external clients
5. Ensure events are unmutable across SONiC releases, but can be deprecated
6. Meet the reliability of 99.5% - event generated to end client 
7. Rate of event reporting can be in par with rate of syslog reporting.


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
4. There can be multiple event detectors running under different scopes.

### Event reporting
1. Event detectors stream the events with structured data
2. The streaming supports one or more local listeners to receive streams from multiple detectors
3. The structured data is per YANG definition
4. RFE: A listener to update redis/anyother persistence destination with current event status

### Event exporter
1. Telemetry container will receive all the events reported from multiple detectors.
2. Telemetry provides support for streaming the received events out to multiple external clients.
3. RFE: Telemetry upon restart will use redis-persistence to get the missed updates

### Event reliability
There are two kinds of reliability
1. Events are not modified across releases (except deprecation)
2. Events are verified to fire as expected in every release. 
3. Ensure that the perf goals are met

#### Protection:
1. The unit tests are required to hard code the YANG definition for an event and verify that against current to ensure it is unchanged.
2. The unit tests are required to send a hard coded message for an event to the reporting tool and validate the reported data against YANG schema.
4. The nightly tests are required to simulate the scenario for process to fire the event, verify that the event is fired and the data is validated against schema.
5. The unit tests & nightly tests are required for every event.
6. A separate stress test is required to ensure the performance rate of 10K events/sec and 99.5% of reliability end-to-end.


## Design

### YANG schema
1. Schema defines the description of the event, its unique tag and all the possible parameters.
2. Schema can be maintained in multiple files, preferably one per process/continer/host.
3. All the schema files are copied into one single location (e.g. /usr/shared/sonic/events).
4. The schema for processes running in host are copied into this location at image creation/install time.
5. The schema for processes running inside the containers are held inside the containers and copied into the shared location on the first run. This allows for independent container upgrade scenarios.
6. NB clients could use the schema to understand/analyze the events

#### A sample Defintion
A sample:
```
module events-bgp {
    . . .
    container bgp_status {
        list event_list {
            key "type ip"
            
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
``` 

### Event detection
The event detectors could happen in many ways
- Update the code to directly invoke Event reporter, which will stream it out.
- Run a periodic check (via monit/cron/daemon/...) to identify an event and raise it via event reporter
- Watch syslog messages for specific pattern; Upon match parse the required data out and call event reporter.
- Syslog watcher could run per process in host and as well in containers
- Any other means of getting alerted on an event

#### log message based detection
1. Use the plug
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

