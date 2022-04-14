# Events reported from SONiC as structured

## Goals
1. Provide a unified way for listing identified alertable events in SONiC switch.
2. Provide a unified way for event detectors to report the events.
3. Enforce a structured format for event data with pre-defined schema.
4. Have the ability to stream at the max of 10K events per second to external clients.
5. Ensure events are immutable across SONiC releases, but can be deprecated.
6. Meet the reliability goal of 99.5% - From event generated to end client.
7. Rate of event reporting can be in par with rate of syslog reporting.


## Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes.


![image](https://user-images.githubusercontent.com/47282725/159573073-06075ee6-40e5-42da-88bf-9f349f64626c.png)


![image](https://user-images.githubusercontent.com/47282725/159061158-30ff3c8a-5fc0-4af2-8822-6bfc67b2329c.png)



## Requirements
### Events
1. Events are defined with schema.
2. Every event is identified by tag, which is unique within a process with zero or more event specific parameters.
3. Events are static (*don't change*) across releases, but can be deprecated in newer releases.
4. Every event is described in YANG schema.
5. YANG schema files for all events are available in a single location for NB clients to refer in Switch.

### Events APIs
The libswsscommon will have the APIs for the following purposes.
1. To report an event.
2. To receive events in a loop with a function callback to pass the message to caller. This implies that the callback function's efficiency affects the receive performance.
3. The reporting API will support multiple listeners.
4. The receiver API will support multiple event reporters.

### Event detection
1. The method of detection can be any.
2. This can vary across events.
3. The events could be reported at run time by the individual components, like orchagent, syncd.
4. The events could be detected from syslog messages. The rsyslog plugin could be an option for live reporting.
5. There can be multiple event detectors running under different scopes (host/containers), concurrently.

### Event reporting
1. Event detectors stream the events with structured data, using the API provided.
2. The streaming out API supports one or more local listeners to receive streams from multiple detectors (many-to-many).
3. The structured data is per YANG definition.

### Event local persistence
1. A host service will receive all events and record the same in redis, using a new EVENTS table.
2. This service will receive events at 10k/sec, but updates to redis will be periodic to ensure minimal impact to control plane.
3. The periodic update will record only the events that changed since last redis write.
4. The periodic update will write the latest value for the event.
5. Any query to redis can be assured to get events as of 0 to N seconds before, where N is the period between two writes. The value of N can be configured via init_cfg.json

### exporter
1. Telemetry container receive all the events reported from all the event detectors.
2. Telemetry container provides support for streaming out received events live to multiple external clients via gNMI.
3. Telemetry container upon restart sends data from redis as current, before switching to live streaming. This helps with any update during telemetry downtime. This may incur sending some duplicate events, if the event has not changed during downtime. 


### Event reliability
There are two kinds of reliability.
1. Events are not modified across releases (*except deprecation*). We may allow addition of new params, as long as they don't affect existing params.
2. Events are verified to fire as expected in every image release. 
3. Ensure the perf goals are met during live streaming.

#### Protection:

1. The unit & nightly tests is provided for every event.
2. The test would hard code the sceham defintion inside the test code and compare it against the YANG definition in file. This would help block accidental YANG updates across releases. 
3. The unit tests are required to simulate the runtime to generate the event with help of mocking. The generated event data is validated against the YANG schema.
4. The unit tests & nightly tests are mandated for every event.
8. A separate stress test is required to ensure the performance rate of 10K events/sec and 99.5% of reliability end-to-end.
</br>

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
module sonic-events-bgp {
    namespace "http://github.com/Azure/sonic-events-bgp";
    prefix "events";
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

    import ietf-yang-types {
        prefix yang;
    }

    revision 2022-03-28 {
        description "BGP alert events.";
    }

    container sonic-events-bgp {
        list event_list {
            key "tag";

            leaf event_source {
                type enumeration {
                    enum "bgp";
                }
                description "Event source; This indicates event source";
            }
            
            leaf event_tag {
                type enumeration {
                    enum "admin_up";
                    enum "admin_down";
                }
                description "Event type/tag for the source";
            }
            
            leaf event_timestamp {
                type yang::date-and-time;
                description "time of the event";
            }
            
            leaf event_index {
                type uint64
                description "A running index per source; This can be used by receiver to detect any message lost";
            }

            leaf ip {
                type inet:ip-address;
                description "IP of neighbor";
            }
        }
    }
}
``` 

### Event detection
The event detection could happen in many ways
- Update the code to directly invoke Event reporter, which will stream it out.
- Run a periodic check (via monit/cron/daemon/...) to identify an event and raise it via event reporter
- Watch syslog messages for specific pattern; Upon match parse the required data out and call event reporter.
- Any other means of getting alerted on an event

#### Log message based detection
At high level:
1. This is a two step process.
2. The process raising the event sends a sylog message out.
3. A watcher scans all the syslog messages emitted and parse/check for events of interest.
4. When matching message arrives, raise the event

Here you have code that sends the log and a watcher who has the regex pattern for that log message to match. Anytime the log messsage is changed the pattern has to be updated for the event to fire consistently across releases.

Though this sounds like a redundant/roundabout way, this helps as below.
- For III party code, not owned by SONiC, this is an acceptable solution
- For code that SONiC own, a code update would take in the order of months to reach thousands of switches, but this approach can be applied instantly to every switch
- A new event addition could be as simple as copying couple of small files to a switch and a rsyslog/container restart.

##### Design at high level
- Configure a rsyslog plugin with rsyslog.
- For logs raised by host processes, configure this plugin at host.
- For logs raised by processes inside the container, configure for rsyslog.d running inside the container.
- The plugin could be configured per process or group of processes.
- Provide the regex patterns to use for matching events as i/p to the plugin (*list of patterns for a process*).
- The plugin could be running in multiple instances.
- Each plugin instance receives messasges **only** for processes that it is configured for.
- For messages that match a pattern, retrieve parameters of interest and fire event using event reporter API.
- The rsyslog plugin binary, which does the parsing & reporting is a single binary in host, shared/used by all plugins.
- The rsyslog plugin binary being under host control, ensures a single/unified behavior across all.
- The unit tests can use hardcoded log messages to validate regex.


![image](https://user-images.githubusercontent.com/47282725/157343412-6c4a6519-c27b-459b-896b-7875d8f952b8.png)

##### Pros & Cons

###### Pro
1) This support is external to app, hence adapts well with III party applications, bgp, teamd, ... 
2) This feature can be added to released builds too, as all it takes is to copy two files into each container and restart rsyslogd in the container
3) The regex for parsing being local to container, it supports any container upgrade transaparently.
4) The rsyslog plugin binary is maintained by host, hence provide a overall control across all containers.
5) The message parsing load is distributed as per container. Within a container parsing could be done at the granularity of per process with no extra cost as rsyslogd already pre-parsed it per-process, *always*

###### con:
1) Two step process for devs, as for each new/updated log message ***for an event***, add/update regex as needed. Updating code directly to raise the event will help avoid this.
2) The rsyslogd is *required*. It should be treated as critical process in each container.
3) Yet, unit/nightly tests can help ensure both steps are done

### Event reporting

#### requirements
- Events are reported from multiple event detectors or we may call event-sources.
- The event detectors could be running in host and/or some/all containers.
- Support multiple local clients to be able to receive the events concurrently.
- Each local client should be able to receive updates from all event detectors w/o being aware of all of the sources.
- The local clients could be operating at different speeds.
- The clients may come and go.
- There may not be any local client to receive the events.
- Events reporting should not be blocked by any back pressure from any local client.
- The reporting should meet the perf goal.
- Event 

#### Design
- Event detectors send UDP messages to a multicast group
- The local clients add themselves as members and receive from the group.

##### Pro
- The senders are never blocked.
- The receivers can be 0 to many.
- Both senders & receivers are neither aware of each other nor has any binding.
- Simple design, hence more reliable.
- Performance goal can be met.

##### con
- Messages could get lost, if the client is slow. It is the client's responsibility to ensure no loss.
- Clients that are slow by design (*like redis-DB updater*), could have a dedicated thread to receive all events and cache the latest. The main thread could be slow, it could miss updates, but it would use/record the latest.


### Event exporting

#### requirements
- Telemetry container receives all locally raised events.
- Telemetry container supports exporting all the locally raised events to one or more external clients.
- RFE: When restarted, ensure to provide the latest on all events that were missed during downtime.
- Supports a max perf rate of 10K events per second.


# Next Step:
When alarm-event FW is functional, the plugin could start using the macros provided by the FW, for identified tags as events.


# CLI
None
RFE: Future persistence to redis could provide CLI to view the latest status on any event or even live dump of events as they were raised.


# Test
Tests are critical to have static events staying static across releases and ensuring the processes indeed fire those events in every release.

## Requirements
1) Each event is covered by Unit test & nightly test
2) Unit test --Hard code the YANG schema and verify that against current schema entry
3) Unit test -- For events based on log messages, have hard coded log message and run it by rsyslog plugin binary with current regex list in the source and validate the o/p reported against schema
4) Nightly test -- Simulate the scenario for the event, look for the event raised by process and validate the event reported against the schema

