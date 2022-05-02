SONiC streaming events as structured via gNMI
=============================================

# Goals
1. Provide a unified way for listing and defining alertable events in SONiC switch.
2. Provide a unified way for event detectors to publish the events.
3. Provide support for exporting events to external gNMI clients via Subscribe
4. Provide a structured format for event data with pre-defined schema.
5. Provide the ability to stream at the max of 10K events per second to external clients.
6. provide a way to ensure events are immutable across SONiC releases, but can be deprecated.
7. Provide 99.5% of reliability - From event generated to end client.


# Problems to solve
The external tools that monitor system health often use syslog messages to look for events that need alert raised.
The syslog messages being text string could potentially **change** across releases. Some log messages could get split into multiple different ones.
This poses a challenge to the external tools as they are forced to adapt for multiple different versions and parse a message based on the OS version of the producer.
This would become even more challenging, when we upgrade individual container images via kubernetes/app-package-manager.

The tools that use syslog messages face higher latency, as they have to wait for syslog messages to arrive to an external repository. 
This latency could run in the order of minutes.


![image](https://user-images.githubusercontent.com/47282725/166261116-d5aa2592-ed85-44c6-9e9e-3dd027b6f886.png)


![image](https://user-images.githubusercontent.com/47282725/165796196-ca89a72f-21ad-4dfa-aae8-34f458b2ff62.png)


# A Use case
The BGP state change is taken for a sample use case.

## BGP syslogs:
When BGP state changes, the event is reported in syslog messages as below

```
bgpd.log.2.gz:Aug 17 02:39:21.286611 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.90 Down Neighbor deleted
bgpd.log.2.gz:Aug 17 02:46:42.615668 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.90 Up
bgpd.log.2.gz:Aug 17 04:46:51.290979 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.78 Down Neighbor deleted
bgpd.log.2.gz:Aug 17 05:06:26.871202 SN6-0101-0114-02T0 INFO bgp#bgpd[62]: %ADJCHANGE: neighbor 100.126.188.78 Up

```

## BGP event YANG model
An event is defined for BGP state change in YANG model as below.

```
module sonic-events-bgp {
    namespace "http://github.com/sonic-net/sonic-events-bgp";
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

## BGP State event 
The above set of logs will now be published as following structured events per schema
```
{ "source": "bgp", "tag": "state", "ip": "100.126.188.90", "status": "down", "timestamp": "2022-08-17T02:39:21.286611" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.90", "status": "up", "timestamp": "2022-08-17T02:46:42.615668" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.78", "status": "down", "timestamp": "2022-08-17T04:46:51.290979" }
{ "source": "bgp", "tag": "state", "ip": "100.126.188.78", "status": "up "timestamp": "2022-08-17T05:06:26.871202" }
```    
## gNMI client
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

## redis entries
The updates are periodic, like once every N seconds, which is far less than supported events publish rate of 10K events/second.
Hence for repeated events, only the last incidence at the time of redis update is recorded. The repetition of an event is identified with key fields as declared in YANG model.
As the updates periodic, there will be a notable latency between event publish and reflection in redis, which can be between 0 to redis-update frequency.
```
key=<source>|<tag>|<contatenated keys>

The redis-entries would be as below, as IP is key for BGP state changes.

    key: bgp|state|100.126.188.90  value: { "ip": "100.126.188.90", "timestamp": "2022-08-17T02:46:42.615668", "status": "up"}
    key: bgp|state|100.126.188.78  value: { "ip": "100.126.188.78", "timestamp": "2022-08-17T05:06:26.871202", "status": "up"}
```
# Requirements
## Events
1. Events are defined with schema.
2. Events are classified with source of event (as BGP, swss, ...) and type of event as tag within that source.
3. An event is defined with zero or more event specific parameters. A subset of the parameters are identified as key.
4. An event is identified by source, tag and key parameters of that event. This can help identify events repetition.
5. Events are static (*don't change*) across releases, but can be deprecated in newer releases.
6. YANG schema files for all events are available in a single location for NB clients in the installed image.

## Event APIs
The libswsscommon will have the APIs for publishing & receiving.
1. To publish an event.
2. To receive events.
3. Event is published with source, tag and optionally additional params.
4. The publishing supports multiple subscribers/receivers. The publishing API is transparent to listening subscribers. The subscribers could come and go anytime.
5. The subscribers call receive events API. This supports all publishing sources transparently. The publishing sources could come and go anytime.
6. The receiving API supports filtering by source. For an example, a receiver may choose to receive events from "BGP" & "SWSS" sources only.
7. The events are sequenced internally to assess missed messages by receivers.
8. The events published are validated against YANG schema. Any invalid messages is reported via syslog & event for alerting.

## Event detection
1. The method of detection can be any.
2. This can vary across events.
3. The events could be published at run time by the individual components, like orchagent, syncd. The code is updated to call the event-publish API.
4. The events could be inferred indirectly from syslog messages. The rsyslog plugin could be an option for live publishing, which can parse syslog messages as they arrive and raise events for messages that indicate an event.
5. There can be multiple event detectors running under different scopes (host/containers), concurrently.

## Event local persistence
1. A service will record the events in redis in a new DB, "EVENTS-DB".
3. This service will receive events at 10k/sec, but updates to redis will be periodic as every N seconds, to ensure minimal impact to control plane.
4. The periodic update will record only the last incidence of an event for repeated events.
5. The latency between receiving the event to redis-update can vary between 0 to N, where N is the pause between 2 updates.
6. The value of N can be modified via init_cfg.json

## Events cache service
1. An on-demand cache service is provided to cache events for a period in transient cache.
2. This service can be started/stopped and retrieve cached data via an libswsscommon API.
3. A receiver could use this, during its downtime and use the cache upon restart.
4. The service caches only last incidence for repeated incidences of an event.
5. The repeated incidences are counted in missed-events-count.
6. The max size of the cache is same max count of possible events, hence there is no overflow possibility.

## exporter
1. Telemetry container runs a internal listener to receive all the events published from all the event publishers in the switch.
2. Telemetry container runs a gNMI serveer to export events to external receivers/collectors via SUBSCRIBE request.
3. Multiple external collectors could connect with filters on event-sources. Only one collector could subscribe for all events (_no filtering by source_), in otherwords the main-receiver.
4. Telemetry ensures reliability to main receiver only.
   - Durung the main receiver down/disconnect period make use of local events-cache service to cache all events during its downtime and send these events upon next connect.
   - For slow main receiver, when it reaches overflow/queue-full state, only the repeated events are dropped and keep the last instance of the event for later queueing.
   - Various stats, like total count of events, missed count, latency from event publish to event send are collected and recorded in STATE-DB.


## Tests:
1. The unit & nightly tests is provided for every event.
2. These tests simulate code to fire the event and the data is validated against schema.
3. A separate stress test is provided to verify the performance reliability goals.
</br>

# Design

## overall View

![image](https://user-images.githubusercontent.com/47282725/165867413-ad261d86-42e0-41f9-8100-35f03d0dfe71.png)


## YANG schema
1. YANG schema is written for every event.
2. Schema is maintained in multiple files as one per source (src/sonic-yang-models/yang-events/events-bgp.yang)
3. All the schema files are copied into one single location (e.g. /usr/shared/sonic/events) in the install image.
4. The schema for processes running in host are copied into this location at image creation/install time.
5. The schema for processes running inside the containers are held inside the containers and copied into the shared location on the first run. This allows for independent container upgrade scenarios.
6. NB clients could use the schema to understand/analyze the events


## Event APIs
The Event API is provided as part of libswsscommon with API definition in a header file.

```
/*
 * Events library 
 *
 *  APIs are for publishing & receiving events with source, tag and params along with timestamp.
 *
 */


class events_base;

typedef events_base* event_handle_t;

/*
 * Initialize an event publisher instance for an event source.
 *
 * NOTE:
 *  The initialization occurs asynchronously.
 *  The event published before init is complete, is blocked until the init
 *  is complete. Hence recommend, do the init as soon as the process starts.
 *
 *  A single publisher instance is maintained for a source.
 *  Any duplicate init call for a source will return the same instance.
 *
 * Input:
 *  event_source
 *      All events published with the handle returned by this call is
 *      tagged with this source, transparently.
 *
 * Return 
 *  Non NULL handle
 *  NULL on failure
 */

event_handle_t events_init_publisher(const std::string &event_source);

/*
 * De-init/free the publisher
 *
 * Input: 
 *  Handle returned from events_init_publisher
 *
 * Output: 
 *  None
 */
void events_deinit_publisher(event_handle_t &handle);


typedef std::map<std::string, std::string> event_params_t;

/*
 * Publish an event
 *
 * input:
 *  handle -- As obtained from events_init_publisher
 *  tag -- Event tag
 *  params -- Params associated with event;
 *  timestamp -- Timestamp for the event; optional; 
 *              format:"2022-08-17T02:39:21.286611"
 *              default: time at the point of this call.
 *
 */
void event_publish(event_handle_t handle, const string &tag,
        const event_params_t *params=NULL,
        const char *timestamp=NULL);



typedef std::vector<std::string> event_subscribe_sources_t;

/*
 * Initialize subscriber.
 *  Only one subscriber is accepted with NULL/empty subscription list.
 *  This subscriber is called the main receiver.
 *  The main receiver gets the privilege of caching events whenever the
 *  connection is dropped until reconnect and cached events are sent 
 *  upon re-connect.
 *  Another additional privilege is all stats/SLA is collected for
 *  this receiver.
 *
 * Input:
 *  lst_subscribe_sources_t
 *      List of subscription sources of interest.
 *      Absence implies for alll
 *
 * Return:
 *  Non NULL handle on success
 *  NULL on failure
 */
event_handle_t events_init_subscriber(     
        const event_subscribe_sources_t *sources=NULL);

/*
 * De-init/free the subscriber
 *
 * Input: 
 *  Handle returned from events_init_subscriber
 *
 * Output: 
 *  None
 */
void events_deinit_subscriber(event_handle_t &handle);


/*
 * Revieve an event
 *
 * input:
 *  handle -- As obtained from events_init_subscriber
 *
 * output:
 *  source -- Event's source.
 *  tag -- Event's tag.
 *  params -- Params associated with event, if any
 *  timestamp -- Event's timestamp.
 *
 */
void event_receive(event_handle_t handle, std::string &source, std::string& tag,
        event_params_t &params, std::string& timestamp);
        
        typedef enum {
    TOTAL_CNT = 0,
    MISSED_CNT,
    CACHE_CNT,
    CACHE_MISSED_CNT,
    MIN_LATENCY,
    MAX_LATENCY,
    AVG_LATENCY
} stats_type_t;

typedef std::map<stats_type_t, uint64_t> stats_t;

/*  
 * return stats collected.
 *   
 * Stats are only collected for subscription with no filter, the
 * main receiver.
 *   
 * Output:
 *  Copy of collected stats
 */  
stats_t get_stats(event_handle_t &handle);
```

## Event detection
The event detection could happen in many ways
- Update the code to directly invoke Event publisher, which will stream it out.
- Run a periodic check (via monit/cron/daemon/...) to identify an event and raise it via event publisher
- Watch syslog messages for specific pattern; Upon match parse the required data out and call event publisher.
- Any other means of getting alerted on an event

### Code update
- This is the preferred approach.
- Use the API for event publishing.
- This method is used in all SONiC owned code.

#### Pro
- Direct publishing from run time is the most efficient way for performance & resource usage.

#### con
- A code update could take months to get into production.

### Log message based detection
At high level:
1. This is a two step process.
2. The process raising the event sends a sylog message out.
3. A watcher scans all the syslog messages emitted and parse/check for events of interest.
4. When matching message arrives, publish the event

Here you have code that sends the log and a watcher who has the regex pattern for that log message to match. Anytime the log messsage is changed the pattern has to be updated for the event to fire consistently across releases.

Though this sounds like a redundant/roundabout way, this helps as below.
- For III party code, not owned by SONiC, this is an acceptable solution.
- A new event addition could be as simple as copying couple of small files to a switch and a rsyslog/container restart.
- For code that SONiC own, a code update would take in the order of months to reach thousands of switches, but this approach can be applied instantly to every switch


#### Design at high level
- A rsyslog plugin is provided to raise events by parsing log messages.
- Configure the rsyslog plugin with rsyslog via .conf file.
- For logs raised by host processes, configure this plugin at host.
- For logs raised by processes inside the container, configure for rsyslog running inside the container, more for load distribution.
- The plugin can be more specifically configured using rsyslog properties, so as to restrict the set of logs to parse and log distribution across multiple instances. One way could be to run a plugin instance per process.
- The plugin could be running in multiple instances.
- Each plugin instance could receive messasges **only** for processes that it is configured for.
- The plugin is provided with the list of regex patterns to use for matching messages. Each pattern is associated with the name of event source and the tag.
- The regex pattern is present as files as one per plugin instance, so an instance sees only the regex expressions that it could match.
- For messages that match a pattern, retrieve parameters of interest per regex and fire event using event publisher API.
- The event publishpublishing API is called with event source & tag from matching regex and data parsed out from message.
- The unit tests can use hardcoded log messages to validate regex.

#### How
1. Copy a rsyslog's .conf file with plugin info into /etc/rsyslog.d/
2. Copy regex files as one per plugin instance. Each files carries expressions of interest to an instance only.
3. Restart rsyslog.
4. The rsyslog.d starts the plugin instance when an message arrives for that instance.
5. rsyslog.d feeds instances with every message destined for it.

![image](https://user-images.githubusercontent.com/47282725/165850058-76ed4806-f43b-4959-8b33-b8365ac6348c.png)

##### Pros & Cons

###### Pro
1) This support is external to app, hence adapts well with III party applications, bgp, teamd, ... 
2) This feature can be added to released builds too, as all it takes is to copy two files into each container and restart rsyslogd in the container
3) The regex for parsing being local to container, it supports any container upgrade transaparently.
4) The message parsing load is distributed as per container. Within a container parsing could be done at the granularity of per process with no extra cost as rsyslogd already pre-parsed it per-process.

##### con:
1) Two step process for devs. For each new/updated log message ***for an event*** in the code, remember to add/update regex as needed. 

## Event publishing & receiving

### requirements
- Events are published as many to many.
- Multiple receivers for messages published by multiple publishers running in hosts and containers.
- A receiver should be transparent to all publishers and vice versa
- A slow receiver should not impact either other receivers.
- Publishers should never be blocked.
- Receivers should be able to learn the count of messages they have missed to receive.
- Receivers & publishers could go down and come up anytime.
- A publishing API validates every event per YANG schema by default. This default behavior can be turned off via /etc/sonic/init-cfg.json. In case of turning off, offline validation occurs.
  - The events that failed validation are not published.
  - The failed validations are logged via syslog and event is raised 

### Design
- Use ZMQ PUB/SUB for publish & subscribe
- To help with transparency across publishers & receivers, run a central ZMQ proxy with XPUB/XSUB.
- Run the zmq proxy service in a dedicated eventd container.
- The systemd ensures the availability of eventd container.
- The publishers and subscribers connect to the *always* available, single instance ZMQ proxy.
- This proxy could transparently feed every messages to a side-car component.
- Run the events-cache service as the side component.
- The events cache service is accessible via REQ/REP

### Details
1. All the zmq paths' defaults are hardcoded in the libswsscommon lib as part of APIs code.
2. These can be overridden with config from /etc/sonic/init_cfg.json
3. The publish API adds sequence number to the message which is stripped off by receiver before forwarding the message to caller.
   - Sequence: < runtime id in high 32 bits > < 32 bits of sequence number starting with 0 >
   - runtime-id = epoch time in milliseconds, truncated to low 32 bits 
   - Send as multipart message with event-source in part1, which allows using ZMQ's filtering by event-sources.
 4. The receiver API:
    - Reads & returns one event at a time, in blocking mode.
    - For receive with no filtering, it creates stats as listed in SLA section for this receive session.
    - It computes missed message count with expected sequence number and the sequence in the received event and expected.
    - It saves the timestamp/diff to compute latency.
 
## Events cache service
1. This is a singleton service that runs in eventd container.
2. It has access to all messages received by zmq proxy via an internal listener tied to the proxy.
3. The caching can be started/stopped.
4. When started all events are cached. The repeated events are cached with last incidence. The repetitions are counted as missed.
5. The API uses ZMQ REQ/REP pattern for communication w.r.t start/stop and replying with cached data.

Supports the following APIs
```
/*
 * Start events cache service
 *
 * return:
 *  0 -- started or already running
 *  -1 -- service not available.
 */
int cache_service_start(void);


typedef struct {
    std::string source;
    std::string tag;
    std::string timestamp;
    event_params_t params;
} cache_message_t;

/* Map of event_key vs the message */
typedef std::map<std::string, cache_message_t> lst_cache_message_t;


/*
 * Stop events cache service
 *
 * output:
 *  lst_msgs -- list of cached messages.
 *
 *  missed_cnt -- Repeated events are counted as missed, as cache persists
 *                only the last incidence.
 *
 * return:
 *  0 -- stopped.
 *  1 -- Nothing to stop, as it is not running.
 *  -1 -- service not available.
 */
int cache_service_stop(lst_cache_message_t &lst, uint32_t &missed_cnt);
```

## Local persistence
- This is to maintain a events status locally.
- A service running in eventd would accomplish this.
- It gets access to all events via a local listener attached to zmq proxy.
- It persists the events into EVENTS table in EVENTS-DB.
- It does a periodic update of every N seconds.
- The N is defaulted to hard coded value in code, which can be overriden via /etc/sonic/init_cfg.json
- In case of repeated events, the last incidence at the time of update is recorded.
- For each event
  - Key = <event source>|<event tag>[|<concatenated value key params using '|' to join>]
  - key params are obtained from YANG and the names are sorted to get the ordering of concatenation (e.g <IP value>|<status value>)
  - value {<ist of all params  as key-val pairs>, "timestamp": "..."}
  - e.g. 
    ```
    key: bgp|state|100.126.188.90  value: { "ip": "100.126.188.90", "timestamp": "2022-08-17T02:46:42.615668", "status": "up"}
    key: bgp|state|100.126.188.78  value: { "ip": "100.126.188.78", "timestamp": "2022-08-17T05:06:26.871202", "status": "up"}
    ```
- In the scenario, where publishing API does not do YANG validation (_turned off via init_cfg.json_), this service validates every event.
  - Invalid events are reported via syslog and by raising an event to alert.
  - Invalid events are not persisted.
  

## Event exporting
The telemetry container runs gNMI server service to export events to gNMI clients via subscribe command.

- Telemetry container hosts gNMI server for streaming events to external receivers.
- The external clients subscribe and receive messages via gNMI connection/protocol.
- For each client connected, a listener is spawned to receive messages at the max rate of 10K/sec.
- The received messages are sent to the connected client at the client's rate.
- Any overflow due to back-pressure/rate-limit is confined to suppression of events repeat.
 
### gNMI protocol
- Use SUBSCRIBE request 
  - Use paths as 
    - "/events" to receive all events.
    - "/events/<source> to receive all events from a source.
    - Multiple paths can be accepted.
  - Subscribe options
    - Target = EVENTS
    - Mode = STREAM
    - StreamMode: OnChange
    - Updates_only = True  
  - Sample: subscribe:{prefix:{target:"EVENTS"} subscription:{path:{element:"BGP" } mode:ON_CHANGE}}
	
- Restriction
  - There can be only one client for all events.
  - The client for all events is called the main receiver.
  - The goal of 95.5% is assured only for the main receiver and stats are collected for the main receiver

- The gnMI o/p is prefixed with \events\
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
```
### Message reliability
The message reliability is ensured only for main receiver. There are 3 kinds of missed message scenarios.
1. A slow receiver that reaches overflow state causes drop of repeated events and send only the last instance.
2. During downtime of main receiver, the events cache service, drops repeated events and provide only the last instance.
3. The internal listener for published events missed to receive an event.
   - This could be due to one/more publishers publishing at a combined rate going above 10K/second.
   - The eventd service is down.
   - An overloaded internal control plane state making the local listener for events running too slow.
     
Among the three, only the third scenario is a real message drop. In the cases 1 & 2, it can be seen as suppression of repeats to conserve resource with no real loss of data as last incidence is sent. Hence only messages missed by listener, is accounted into reliability measure computation.
	
All stats related to main receiver is recorded in STATE-DB. Refer STATS section for details.

### Rate-limiting
- The gNMI clients do need rate-limiting support to avoid overwhelming. The inherent/transparent limit via TCP back pressure is an option.
- For clients who would like some explicit rate limiting, a custom option is provided.
- The subscribe request does not have an option to provide rate-limiting, hence a reserved path is used to specify a rate-limit
- path: /events/rate-limit/< N > -- This would be interpreted by telemetry's gNMI server as "_event export rate is <= N events/second_".
- The rate-limiting/backpressure would only drop repeated events.
	

# STATS update
The following stats are collected. These stats can be used to assess the performance and SLA (_Service Level Agreement_) compliance.</br>
The stats are collected by telemetry service that serves the main receiver. Hence the stats update occur only when main receiver is connected.</br>

- The counters are persisted in STATE-DB with keys as "EVENT-STATS|< counter name >"
- The counters are cumulative.
- The counters lifetime is tied with lifetime of STATE-DB.
- The telemetry supports streaming of EVENT-STATS table ON-CHANGE in streaming mode.

## counters
- events-sent-cnt:
  - The count of all events / messages sent to the main receiver. In other words count of events the receiver is expected to receive.
  - This would not include suppressed events-repeat (_read reliability section above for details_).
  
- events-missed-cnt:
  - The count of events, the telemetry service missed to receive from the publishers (_read reliability section above for details_).
	
- events-suppressed-cnt:
  - The count of events suppressed (_read reliability section above for details_).
    
- events-cached-cnt:
  - The count of events provided from cache.
    
- Max_receiver_duration_secs:
  - The max time in seconds the main receiver remain connected in a single connection while the telmetry's gNMI service is running.
  	
- Min_receiver_duration_secs:
  - The min time in seconds the main receiver remain connected in a single connection while the telmetry's gNMI service is running.
	
- avg_receiver_duration_secs:
  - The average time in seconds the main receiver remain connected in a single connection while the telmetry's gNMI service is running.
	
- receiver_connect_cnt:
  - The count of connections made by main receiver
	
- cache_duration_in_secs:
  - The total duration of cache use in seconds
  - This includes telemetry container downtime and main receiver downtime, while telemetry's gNMI service is up.
	
- telemetry_restart_cnt:
  - Count of telemetry restarts.
	
- telemetry_service_runtime_secs:
  - Count of seconds the telemetry service has been active.
  - This is updaed periodically, while telemetry service is running. Assuming a period of every N seconds, it could miss a max of N seconds in this count in each run, which is often way too negligible compared to runtime duration.
	
- min_latency
  - The minimum time taken from event publish to event write into receiver connection

- max_latency
  - The maximum time taken from event publish to event write into receiver connection
	
- avg_latency
  - The average time taken from event publish to event write into receiver connection
	
	
# CLI
- Show command is provided to view events with optional parameter to filter by source.
- Show commands is provided to vew STATS collected

# Alerts & YANG models
The following alerts are planned for implementation

## Source: BGP
Events sourced by BGP. There could be multiple publishers raising BGP events.
The publishing is done via parsing syslogs, as this is III party code.
	

### YANG model
```
module sonic-events-bgp {
    namespace "http://github.com/sonic-net/sonic-events-bgp";
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
            description "
                Declares an event for BGP state for a neighbor IP
                IP is the key parameter
                The status says "up" or "down"
                Repeat events are identified by IP";

            list event_list {
                key "IP";

                leaf source {
                    type enumeration {
                        enum "bgp";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "state";
                    }
                    description "Event tag";
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
            description "
                Declares an event for BGP hold timer expiry.
                This event does not have any other parameter.
                Hence source + tag identifies an event";

            list event_list {
                leaf source {
                    type enumeration {
                        enum "bgp";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "hold_timer_expiry";
                    }
                    description "Event tag";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container zebra-no-buff {
            description "
                Declares an event for zebra running out of buffer.
                This event does not have any other parameter.
                Hence source + tag identifies an event";
                
            list event_list {
                leaf source {
                    type enumeration {
                        enum "bgp";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "zebra_no_buffer";
                    }
                    description "Event tag";
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

## Source: dhcp-relay
Events sourced by processes from dhcp-relay container. There could be multiple publishers raising host events. The services that detect these events are updated to directly call the publishing API in C or python.
	
### YANG model
```
module sonic-events-dhcp-relay {
    namespace "http://github.com/sonic-net/sonic-events-dhcp-relay";
    prefix "events";
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

        import ietf-yang-types {
                prefix yang;
        }

    revision 2022-03-28 {
        description "dhcp-relay alert events.";
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC dhcp-relay events";

    container sonic-events-dhcp-relay {

        container dhcp-relay-discard {
            description "
                Declares an event for dhcp-relay discarding packet on an
                interface due to missing IP address assigned.
                Params:
                    name of the interface discarding.
                    class of the missing IP address as IPv4 or IPv6.
                Both params are used as key
                Hence source + tag + all params identifies an event";

            list event_list {
                key "ip_class ifname";

                leaf source {
                    type enumeration {
                        enum "dhcp-relay";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "discard_no_ip";
                    }
                    description "Event tag";
                }

                leaf ip_class {
                    type enumeration {
                        enum "ipV4";
                        enum "ipV6";
                    }
                    description "Class of IP address missing";
                }

                leaf ifname {
                    type string;
                    description "Name of the i/f discarding";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container dhcp-relay-disparity {
            description "
                Declares an event for disparity detected in
                DHCP Relay behavior by dhcpmon.
                parameters:
                    vlan that shows this disdparity
                    Additional data 
                vlan is the only key param.
                Hence source + tag + vlan identifies an event";

            list event_list {
                key "vlan";

                leaf source {
                    type enumeration {
                        enum "dhcp-relay";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "disparity";
                    }
                    description "Event tag";
                }

                leaf vlan {
                    type string;
                    description "Name of the vlan affected";
                }

                leaf duration {
                    type uint32;
                    description "Duration of disparity";
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
	
## Source: host
Events sourced by services running in host. There could be multiple publishers raising host events. The services that detect these events are updated to directly call the publishing API in C or python.
	
### YANG model
```
module events-host {
    namespace "http://github.com/sonic-net/sonic-events-host";
    prefix "events";
    yang-version 1.1;

        import ietf-yang-types {
                prefix yang;
        }

    revision 2022-03-28 {
        description "BGP alert events.";
    }

    container sonic-events-host {
        container event-usage {
            description "
                Declares an event for usage crossing set limit
                for disk or memory.
                The parameters describe the usage & limit set.
                The usage_type defines the affected entity as system memory
                or file system.
                
                The usage_type is the key.
                Hence source + tag + usage_type identifies an event";

            list event_usage {
                key "usage_type";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "usage";
                    }
                    description "Event tag";
                }

                leaf usage_type {
                    enum "disk_usage";
                    enum "mem_usage";
                }

                leaf fs {
                    type  string;
                    description "Name of the file system";
                    default "";
                }

                leaf usage {
                    type uint8 {
                        range "0..100" {
                            error-message "Incorrect val for %";
                        }
                    }
                    description "Percentage in use";
                }

                leaf limit {
                    type uint8 {
                        range "0..100" {
                            error-message "Incorrect val for %";
                        }
                    }
                    description "Percentage limit set";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }
        container event-sshd {
            description "
                Declares an event reported by sshd.
                The fail type declares the type of failure.
                INCORRECT_PASSWORD - denotes that sshd is sending
                wrong password to AAA to intentionally fail this 
                login.
                fail_type is the key param.
                Hence source + tag + fail_type identifies an event";

            list event_sshd {
                key "fail_type";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "sshd";
                    }
                    description "Event tag";
                }

                leaf fail_type {
                    type enumeration {
                        enum "INCORRECT_PASSWD";
                    }
                    description "Type of failure";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }
        container event-disk {
            description "
                Declares an event reported by disk check.
                The fail type declares the type of failure.
                read-only - denotes that disk is in RO state.

                fail_type is the key param.
                Hence source + tag + fail_type identifies an event";

            list event_disk {
                key "fail_type";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "disk";
                    }
                    description "Event tag";
                }

                leaf fail_type {
                    type enumeration {
                        enum "read_only";
                    }
                    description "Type of failure";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }
        container event-kernel {
            description "
                Declares an event reported by kernel.
                The fail type declares the type of failure.

                fail_type is the key param.
                Hence source + tag + fail_type identifies an event";

            list event_kernel {
                key "fail_type";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }

                leaf tag {
                    type enumeration {
                        enum "kernel";
                    }
                    description "Event tag";
                }

                leaf fail_type {
                    type enumeration {
                        enum "write_failed";
                        enum "write_protected";
                        enum "remount_read_only";
                        enum "aufs_read_lock";
                        enum "invalid_freelist";
                        enum "zlib_decompress";
                    }
                    description "Type of failure";
                }

                leaf msg {
                    type string;
                    description "human readable hint text";
                    default "";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container event-monit-proc {
            description "
                Declares an event reported by monit for a process
                that is not running.
        
                Params: 
                    Name of the process that is not running.
                    The ASIC-index of that process.
                   
                proc_name & asic_index are key params.
                Hence source + tag + key-params identifies an event";

            list event_proc {

                key "proc_name asic_index";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "monic_proc_not_running";
                    }
                    description "Event tag";
                }

                leaf proc_name {
                    type string;
                    description "Name of the process not running";
                    default "";
                }

                leaf asic_index {
                    type uint8;
                    description "ASIC index in case of multi asic platform";
                    default 0;
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container event-monit-status {
            description "
                Declares an event reported by monit for status check
                failure for a process
        
                Params: 
                    Name of the process that is not running.
                    The ASIC-index of that process.
                   
                proc_name & asic_index are key params.
                Hence source + tag + key-params identifies an event";

            list event_status {

                key "entity asic_index";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "monit_status_fail";
                    }
                    description "Event tag";
                }

                leaf entity {
                    type string;
                    description "Name of the failing entity";
                    default "";
                }

                leaf asic_index {
                    type uint8;
                    description "ASIC index in case of multi asic platform";
                    default 0;
                }

                leaf reason {
                    type string;
                    description "Human readble text explaining failure";
                    default "";
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container event-platform {
            description "
                Declares an event for platform related failure.
                Params: 
                    fail_type provides the type of failure.
                   
                fail_type is the key param.
                Hence source + tag + key-param identifies an event";

            list event_platform {
                key "fail_type";

                leaf source {
                    type enumeration {
                        enum "host";
                    }
                    description "Event source";
                }
        
                leaf tag {
                    type enumeration {
                        enum "platform";
                    }
                    description "Event tag";
                }

                leaf fail_type {
                    type enumeration {
                        enum "watchdog_timeout";
                        enum "switch_parity_error";
                        enum "SEU_error";
                    }
                    description "Type of failure";
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
## Source: pmon
Events sourced by platform monitor services.
	
### YANG model	
```
module sonic-events-pmon {
    namespace "http://github.com/sonic-net/sonic-events-pmon";
    prefix "events";
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

        import ietf-yang-types {
                prefix yang;
        }

    revision 2022-03-28 {
        description "pmon alert events.";
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC pmon events";

    container sonic-events-pmon {

        container pmon-exited {
            description "
                Declares an event reportes by pmon for an unexpected exit.
                The exited entity is the only param and as well the key param.
                Hence source + tag + entity identifies an event";

            list event_list {
                key "entity";

                leaf source {
                    type enumeration {
                        enum "pmon";
                    }
                    description "Source is BGP";
                }
        
                leaf tag {
                    type enumeration {
                        enum "exited";
                    }
                    description "An unexpected exit";
                }

                leaf entity {
                    type string;
                    description "entity that had unexpected exit";
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
## Source: swss
Events sourced by services running in swss container. There could be multiple publishers raising host events. The services that detect these events are updated to directly call the publishing API in C or python.

### YANG model	
```
module sonic-events-swss {
    namespace "http://github.com/sonic-net/sonic-events-swss";
    prefix "events";
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

    import ietf-yang-types {
        prefix yang;
    }

    revision 2022-03-28 {
        description "SWSS alert events.";
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC SWSS events";

    container sonic-events-swss {

        container redis-generic {
            description "
                Declares an event for a fatal error encountered by swss.
                The asic-index of the failing process is the only param.
                Hence source + tag + asic_index identifies an event";

            list event_list {
                key "asic_index;

                leaf source {
                    type enumeration {
                        enum "swss";
                    }
                    description "Source is SWSS";
                }
        
                leaf tag {
                    type enumeration {
                        enum "redis_generic_get";
                    }
                    description "Event type/tag";
                }

                leaf asic_index {
                    type uint8;
                    description "ASIC index in case of multi asic platform";
                    default 0;
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }
        container if-state {
            description "
                Declares an event for i/f flap.
                
                The name of the flapping i/f and status are the only params.
                The i/f name is the key param.

                Hence source + tag + if-name identifies an event";

            list event_list {
                key "ifname";

                leaf source {
                    type enumeration {
                        enum "swss";
                    }
                    description "Source is SWSS";
                }
        
                leaf tag {
                    type enumeration {
                        enum "if_state";
                    }
                    description "Event type/tag";
                }

                leaf ifname {
                    type string;
                    description "Interface name";
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

        container pfc-storm {
            description "
                Declares an event for PFC storm.
                
                The name of the i/f facing the storm is the only param.
                The i/f name is the key param.

                Hence source + tag + if-name identifies an event";

            list event_list {
                key "ifname;

                leaf source {
                    type enumeration {
                        enum "swss";
                    }
                    description "Source is SWSS";
                }
        
                leaf tag {
                    type enumeration {
                        enum "pfc_storm";
                    }
                    description "Event type/tag";
                }

                leaf ifname {
                    type string;
                    description "Interface name";
                }

                leaf queue_index {
                    type uint8;
                }

                leaf queue_id {
                    type uint64_t;
                }

                leaf port_id {
                    type uint64_t;
                }

                leaf timestamp {
                    type yang::date-and-time;
                    description "time of the event";
                }
            }
        }

        container chk_crm_threshold {
            description "
                Declares an event for CRM threshold.
                This event does not have any other parameter.
                Hence source + tag identifies an event";

            list event_list {

                leaf source {
                    type enumeration {
                        enum "swss";
                    }
                    description "Source is SWSS";
                }
        
                leaf tag {
                    type enumeration {
                        enum "crm_threshold_exceeded";
                    }
                    description "Event type/tag";
                }

                leaf percent {
                    type uint8 {
                         range "0..100" {
                            error-message "Invalid percentage value";
                        }
                    }
                    description "percentage used";
                }

                leaf used_cnt {
                    type uint8;
                }

                leaf free_cnt {
                    type uint64_t;
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

## Source: syncd
Events sourced by services running in syncd container. There could be multiple publishers raising host events. The services that detect these events are updated to directly call the publishing API in C or python.
	
### YANG mode
```
module sonic-events-syncd {
    namespace "http://github.com/sonic-net/sonic-events-syncd";
    prefix "events";
    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

        import ietf-yang-types {
                prefix yang;
        }

    revision 2022-03-28 {
        description "syncd alert events.";
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC syncd events";

    container sonic-events-syncd {

        container failure {
            description "
                Declares an event for all types of syncd failure.
                The type of failure and the asic-index of failing syncd are
                provided along with a human readable message to give the
                dev debugging additional info.
                The fail-type & asic-index are key params.
                Hence source + tag + key params identifies an event";

            list event_list {
                key "asic_index fail_type;

                leaf source {
                    type enumeration {
                        enum "syncd";
                    }
                    description "Source is syncd";
                }
        
                leaf tag {
                    type enumeration {
                        enum "failure";
                    }
                    description "Event type/tag";
                }

                leaf asic_index {
                    type uint8;
                    description "ASIC index in case of multi asic platform";
                    default 0;
                }

                leaf fail_type {
                    type enumeration {
                        enum "route_add_failed";
                        enum "switch_event_2";
                        enum "brcm_sai_switch_assert";
                        enum "assert";
                        enum "mmu_err";
                    }
                }

                leaf msg {
                    type string;
                    description "human readable hint text"
                    default "";
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
# Test
Tests are critical to have static events staying static across releases and ensuring the processes indeed fire those events in every release.

## Requirements
1) Each event is covered by Unit test & nightly test
2) Unit test -- For ||| party code that raises events based on log messages, have hard coded log message and run it by rsyslog plugin binary with current regex list in the source and validate the o/p reported against schema. This ensures the data fired is per schema.
3) Unit test -- For events reported by code, mock it as needed to exercise the code that raises the event. Verify the received event data against the schema.
4) Nightly test: For each event, hardcode the sample event data and validate against the schema. This is additional layer of protection to validate the immutability of the schema.
5) Nightly test -- For each event simulate the scenario for the event, look for the event raised by process and validate the event reported against the schema. This may not be able to cover every event, but unit tests can.



 
