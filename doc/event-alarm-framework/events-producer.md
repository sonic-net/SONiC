# Events reported from SONiC as structured

## Goals
1. Provide a unified way for listing and defining alertable events in SONiC switch.
2. Provide a unified way for event detectors to report the events.
3. Provide support for exporting events to external gNMI clients via Subscribe
4. Enforce a structured format for event data with pre-defined schema.
5. Have the ability to stream at the max of 10K events per second to external clients.
6. Ensure events are immutable across SONiC releases, but can be deprecated.
7. Meet the reporting goal of 99.5% of reliability - From event generated to end client.


## Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes.


![image](https://user-images.githubusercontent.com/47282725/159573073-06075ee6-40e5-42da-88bf-9f349f64626c.png)


![image](https://user-images.githubusercontent.com/47282725/165796196-ca89a72f-21ad-4dfa-aae8-34f458b2ff62.png)


## A Use case
The BGP state change is taken for a sample use case.

### BGP syslogs:
When BGP state changes, the event is reported in syslog messages as below

```
bgpd.log.2.gz:Aug 17 02:39:21.286611 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.90 Down Neighbor deleted
bgpd.log.2.gz:Aug 17 02:46:42.615668 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.90 Up
bgpd.log.2.gz:Aug 17 04:46:51.290979 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.78 Down Neighbor deleted
bgpd.log.2.gz:Aug 17 05:06:26.871202 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.78 Up

```

### BGP State event model
An event is defined for BGP state change in YANG model as below.

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

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC BGP events";

    container sonic-events-bgp {

        container bgp-state {
            list event_list {
                key "IP";

                leaf source {
                    type enumeration {
                        enum "bgp";
                    }
                    description "Source is BGP";
                }
        
                leaf tag {
                    type enumeration {
                        enum "state";
                    }
                    description "Event type/tag";
                }

                leaf ip {
                    type inet:ip-address;
                    description "IP of neighbor";
                }

                leaf status {
                    type enumeration {
                        enum "up";
                        enum "down";
                    }
                    description "Provides the status as up (true) or down (false)";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container bgp-hold-timer {
            list event_list {
                leaf source {
                    type enumeration {
                        enum "bgp";
                    }
                    description "Source is BGP";
                }
        
                leaf tag {
                    type enumeration {
                        enum "hold_timer_expiry";
                    }
                    description "BGP Hold timer expiry";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }
    }
}
    
```

### BGP State event 
The above set of logs will now be published as following structured events per schema
```
{ "source": "bgp", "tag": "state", "ip": "100.126.188.90", "status": "down", "timestamp": "2022-08-17T02:39:21.286611" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.90", "status": "up", "timestamp": "2022-08-17T02:46:42.615668" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.78", "status": "down", "timestamp": "2022-08-17T04:46:51.290979" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.78", "status": "up "timestamp": "2022-08-17T05:06:26.871202" }
```    
### gNMI client
The client could subscribe for events with optional filter on event source in streaming mode
```
gnmic --target events --path "/events/" --mode STREAM --stream-mode ON_CHANGE

o/p
{
  "EVENTS": {
    "/events/bgp/state": {
      "timestamp": "2022-08-17T02:39:21.286611",
      "ip": "100.126.188.90",
      "status": "down"
    }
}
{
  "EVENTS": {
    "/events/bgp/state": {
      "timestamp": "2022-08-17T02:46:42.615668",
      "ip": "100.126.188.90",
      "status": "up"
    }
  }
}
{
  "EVENTS": {
    "/events/bgp/state": {
      "timestamp": "2022-08-17T04:46:51.290979",
      "ip": "100.126.188.78",
      "status": "down"
    }
}
{
  "EVENTS": {
    "/events/bgp/state": {
      "timestamp": "2022-08-17T05:06:26.871202",
      "ip": "100.126.188.78",
      "status": "up"
    }
  }
}
        
```

### redis entries
The updates are periodic, like once every N seconds, which is far less than supported events publish rate of 10K events/second.
Hence for repeated events, only the last incidence at the time of redis update is recorded. The repetition of an event is identified with key fields as declared in YANG model.
As the updates periodic, there will be a notable latency between event publish and reflection in redis, which can be between 0 to redis-update frequency.
```
key=<source>|<tag>|<contatenated keys>

The redis-entries would be as below, as IP is key for BGP state changes.

key: bgp|state|100.126.188.90  value: { "timestamp": "2022-08-17T02:46:42.615668"; "status": "up"}
key: bgp|state|100.126.188.78  value: { "timestamp": "2022-08-17T05:06:26.871202"; "status": "up"}
```
## Requirements
### Events
1. Events are defined with schema.
2. Events are classified with source of event (as BGP, swss, ...) and type of event as tag within that source.
3. An event is defined with zero or more event specific parameters. A subset of the parameters are identified as key.
4. An instance of an event can be uniquely identified by source, tag and key parameters of that event. This can help identify events repetition.
5. Events are static (*don't change*) across releases, but can be deprecated in newer releases.
6. YANG schema files for all events are available in a single location for NB clients in the installed image.

### Events APIs
The libswsscommon will have the APIs for reporting & receiving.
1. To report an event.
2. To receive events.
3. Event is reported with source, tag and optionally additional params.
4. The reporting supports multiple subscribers/receivers. The reporting API is transparent to listening subscribers. The subscribers could come and go anytime.
5. The subscribers call receive events API. This supports all publishing sources transparently. The publishing sources could come and go anytime.
6. The receiving API supports filtering by source. A receiver may choose to receive events from "BGP" & "SWSS" sources only.
7. The events are sequenced internally to assess missed messages by receivers.
8. The events reported are validated against YANG schema. Any invalid messages is reported via syslog & event for alerting.

### Event detection
1. The method of detection can be any.
2. This can vary across events.
3. The events could be reported at run time by the individual components, like orchagent, syncd. The code is updated to call the event-publish API.
4. The events could be detected from syslog messages. The rsyslog plugin could be an option for live reporting, which can parse syslog messages as they arrive and raise events for messages that indicate an event.
5. There can be multiple event detectors running under different scopes (host/containers), concurrently.

### Event local persistence
1. A service will record the events in redis, using a new EVENTS-DB.
3. This service will receive events at 10k/sec, but updates to redis will be periodic as every N seconds, to ensure minimal impact to control plane.
4. The periodic update will record only the last incidence of an event for repeated events.
5. The latency between receiving the event to redis-update can vary between 0 to N, where N is the pause between 2 updates.
6. The value of N can be modified via init_cfg.json

### Events cache service
1. An on-demand cache service is provided to cache events for a period in transient cache.
2. This service can be started/stopped and retrieve cached data via an libswsscommon API.
3. A receiver could use this, during its downtime and use the cache upon restart.
4. The service caches only last incidence for repeated incidences of an event.
5. The max size of the cache is same max count of possible events, hence there is no overflow possibility.

### exporter
1. Telemetry container receive all the events reported from all the event publishers.
2. Telemetry container provides support for streaming out received events live to multiple external clients via gNMI-subscribe.
3. Telemetry container uses cache service during its downtime and as well external receiver's downtime (_implying between external receiver connectiondrop & re-connect_).

### Event reliability
1. The internal sequencing helps assess the count of messages by receivers.
2. This count is recorded in STATE-DB along with total count of events.
3. Goal: At the max rate of 10K messages per second, meet the reliability score of 95.5%.

### Protection:
1. The unit & nightly tests is provided for every event.
2. These tests simulate code to fire the event and the data is validated against schema.
3. A separate stress test is provided to verify the performance reliability goals.
</br>

## Design

### overall View

![image](https://user-images.githubusercontent.com/47282725/165818319-771c2af2-55ab-4fc7-a3af-e22d3db78b2b.png)

### YANG schema
1. Schema defines each event.
2. An event is identified by source & tag.
3. Each event is defined with all the possible parameters for that event and timestamp.
4. Schema is maintained in multiple files as one per source (src/sonic-yang-models/yang-events/events-bgp.yang)
5. All the schema files are copied into one single location (e.g. /usr/shared/sonic/events) in the install image.
6. The schema for processes running in host are copied into this location at image creation/install time.
7. The schema for processes running inside the containers are held inside the containers and copied into the shared location on the first run. This allows for independent container upgrade scenarios.
8. NB clients could use the schema to understand/analyze the events


### Event APIs
The Event API is provided as part of libswsscommon with API definition in a header file.

#### Reporting API
- APIs for event reporting is provided. 
- An API to initialize once and and event-send API is called for each event send. 
- The event reporting API accepts, event-sender, source, tag, hash-params & parameters. The timestamp could be provided too.
- The event reporting API adds "timestamp" if not provided and "index".
- Event index is coined per source per sender. 
- The event-index could be used by receivers to gauge the count of missed/lost messages from a source.
- The index will be formatted such that a restart at the publisher would be distinguished to avoid false reporting.


### Receiving API
- APIs for event receive are provided.
- An init API to initialize once and receive is called for each event read. 
- The receiver API uses the index to compute missed count of message per source per reader and pass it along with the message in read call, as optional o/p val.


### Event detection
The event detection could happen in many ways
- Update the code to directly invoke Event reporter, which will stream it out.
- Run a periodic check (via monit/cron/daemon/...) to identify an event and raise it via event reporter
- Watch syslog messages for specific pattern; Upon match parse the required data out and call event reporter.
- Any other means of getting alerted on an event

#### Code update
- This is the preferred approach.
- Use the API for event reporting.
- This method is used in all SONiC owned code.

##### Pro
- Direct reporting from run time is the most efficient way for performance & resource usage.

##### con
- A code update could take months to get into production.

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
- For logs raised by processes inside the container, configure for rsyslog running inside the container.
- The plugin is configured per event source or many or all. An event source could be one or multiple processes.
- The plugin could be running in multiple instances.
- Each plugin instance receives messasges **only** for processes that it is configured for.
- The plugin is provided with the list of regex patterns to use for matching messages. Each pattern is associated with the name of event source and the tag, which is unique within the source.
- For messages that match a pattern, retrieve parameters of interest per regex and fire event using event reporter API.
- The event reporting API is called with event source & tag from matching regex and data parsed out from message.
- The rsyslog plugin binary, which does the parsing & reporting is a single binary in host, shared/used by all plugins.
- The rsyslog plugin binary being under host control, ensures a single/unified behavior across all. This is critical as event exporters and receivers are running across multiple containers and host.
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
- Each event includes to the minimum "event sender", "event source", "event tag", "event timestamp, "event hash" and "event index"
- Supports multiple local clients to be able to receive the events concurrently.
- Each local client should be able to receive updates from all event detectors w/o being aware of all of the sources.
- The local clients could be operating at different speeds.
- The clients may come and go.
- There may not be any local client to receive the events.
- Events reporting should not be blocked by any back pressure from any local client.
- The reporting should meet the perf goal.


#### Design
- To handle multiple publishers and receiver, ZMQ proxy runs as host service via XPUB/XSUB.
- Publishers connect to this proxy service XSUB end point to publish messages.
- Publishers send event-source as topic (_which receivers can use for filtering_)
- Subscribers/receivers connect to XPUB endpoint to register subscription and receive messages.
- Receivers can send subscription to filter on topic. In other words set filter to receive messages from only a subset of event-sources.

##### Pro
- The senders are never blocked.
- The receivers can be 0 to many.
- Both senders & receivers are neither aware of each other nor has any binding.
- Performance goal can be met.

##### con
- Messages could get lost, if the client is slow. It is the client's responsibility to ensure no loss.
- Event-index could be used to get the count of missed messages per source.
- Clients that are slow by design (*like redis-DB updater*), could have a dedicated thread to receive all events and cache the latest. The main thread could be slow, it could miss updates, but it would use/record the latest.

### Local persistence
- This is to maintain a events status locally.
- A service running in host would accomplish this.
- It persists the events into EVENTS table in EVENTS-DB.
- Runs in 2 threads.
- The event receiver thread receives the updates and caches it locally in-memory, as just one copy per event. In case of multiple updates, that copy is written with latest.
- The event writer thread, wakes up periodically.
- The redis key is coined as {event-source | event-tag | event-hash}
- The redis value is { timestamp:... [, param0: ... [param1: ...]] }
- The key helps tracks all unique event instances
- Though the writer wakes up every N seconds, it writes the value as of at the timepoint of it waking up.
- Writer will be diligent to write only updates that it missed in the last cycle. 
- The writer's default redis update frequency can be modified via init-cfg.json.

### Event exporting
The telemetry container helps with exporting events to external collectors/clients.

#### requirements
- Telemetry container hosts gNMI server for streaming events to external receivers.
- The external clients subscribe and receive messages via gNMI connection/protocol.
- Telemetry container creates a new thread for each external client that subscribes for events.
- A subscription connection is created per external client. This way a slow client will not block others.
- Each message received is synchronously written to external client. Hence the performance depends on the external client.
- The receive API returns the cumulative missed message count per source per sender, along with received message. This counter is reset on sender restart.
- This cumulative counter is logged.
- The external client could subscribe by a subset of event sources or any/all.
- The client will receive only events from subscribed sources.
- Upon telemetry container restart, on the first writer run, for events that are not received yet, send the last status from the redis. The knowledge of all possible events are obtained from redis. NOTE: This may result in some duplicate events to external receivers.
- Supports a max perf rate of 10K events per second.
- The effective performance is tied to the client's perf.


# Next Step:
When alarm-event FW is functional, the plugin could start using the macros provided by the FW, for identified tags as events.


# CLI
Show command is provided to view events with optional parameter to filter by source.

# Test
Tests are critical to have static events staying static across releases and ensuring the processes indeed fire those events in every release.

## Requirements
1) Each event is covered by Unit test & nightly test
2) Unit test -- For events based on log messages, have hard coded log message and run it by rsyslog plugin binary with current regex list in the source and validate the o/p reported against schema. This ensures the data fired is per schema.
3) Unit test -- For events reported by code, mock it as needed to exercise the code that raises the event. Verify the received event data against the schema.
4) Nightly test: For each event, hardcode the sample event data and validate against the schema. This is the *fool-proof* way to validate the immutability of the schema.
5) Nightly test -- For events that can be simulated, simulate the scenario for the event, look for the event raised by process and validate the event reported against the schema. This may not be able to cover every event, but unit tests can.
6) Unit & nightly tests are mandated for every event.

### caveat:
For III party sources (non-sonic owned sources) where we don't control unit tests, simulating the error scenario may not be possible. Here if the code has changed the log message format, there is no reliable defense.

 
