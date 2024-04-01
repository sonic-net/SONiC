# Feature Name
Event and Alarm Framework
# High Level Design Document
#### Rev 0.2

# Table of Contents
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)
      * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
    * [2.1 Target Deployment Use Cases](#21-target-deployment-user-cases)
    * [2.2 Functional Description](#22-functional-description)
  * [3 Design](#3-description)
    * [3.1 Overview](#31-overview)
      * [3.1.1 Event Producers](#311-event-producers)
        * [3.1.1.2 Development Process](#3112-development-process)
      * [3.1.2 Event Consumer](#312-event-consumer)
        * [3.1.2.1 Severity](#3121-severity)
        * [3.1.2.2 Sequence-ID](#3122-sequence-id)
      * [3.1.3 Alarm Consumer](#313-alarm-consumer)
      * [3.1.4 Event Receivers](#314-event-receivers)
        * [3.1.4.1 System LED](#3144-system-led)
        * [3.1.4.2 Event/Alarm flooding](#3145-event/alarm-flooding)
      * [3.1.5 Event Profile](#315-event-profile)
      * [3.1.6 CLI](#316-cli)
      * [3.1.7 Event Table and Alarm Table](#317-event-table-and-alarm-table)
      * [3.1.8 Pull Model](#318-pull-model)
      * [3.1.9 Supporting third party containers](#319-supporting-third-party-containers)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 EVENT DB](#321-event-db)
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 CLI](#332-cli)
        * [3.3.2.1 Exec Commands](#3321-exec-commands)
        * [3.3.2.2 Configuration Commands](#3322-configuration-commands)
        * [3.3.2.3 Show Commands](#3323-show-commands)
      * [3.3.3 REST API Support](#333-rest-api-support)
  * [4 Persistence](#4-persistence)
    * [4.1 Warm reboot](#41-warm-reboot)
       * [4.1.1 Application restart](#411-application-restart)
       * [4.1.2 System warm reboot](#412-system-warm-reboot)
    * [4.2 Fast reboot](#42-fast-reboot)
    * [4.3 Cold reboot](#42-cold-reboot)
    * [4.4 Power reset](#43-power-reset)
  * [5 Scalability](#6-scalability)
  * [6 Showtech Support](#7-showtech-support)
  * [7 Unit Test](#8-unit-test)


# Revision
| Rev |     Date    |       Author       | Change Description                                       |
|:---:|:-----------:|:------------------:|-----------------------------------                       |
| 0.1 | 03/20/2021  | Srinadh Penugonda  | Initial Version                                          |
| 0.2 | 04/30/2021  | Srinadh Penugonda  | Updated with comments from HLD review                    |
| 0.3 | 04/18/2022  | Bhavesh            | Address review comments                                  |

# About this Manual
This document provides a high level design of event and alarm management. It extends the existing event producer framework. 
Refer for the current event framework. https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/events-producer.md  
Note: Wherever CLI is specified, it is the KLISH cli that is referred - SONiC native (CLICK) CLI is not updated for this feature.


# 1 Feature Overview

The Event and Alarm Framework feature provides a centralized framework for applications in SONiC to raise notifications and store them for north bound interfaces for monitoring the device.

Events and alarms are notifications to indicate a change in the state of the system that operator may be interested in.
Such a change has an important metric called *severity* to indicate how critical it is to the health of the system.

*  Events

   Events are "one shot" notifications to indicate an abnormal/important situation.

   Events are "one shot" notifications to indicate an abnormal/important situation.

   User logging in, authentication failure, configuration changed notification are all examples of events.

*  Alarms

   Alarms are notifications raised for conditions that could be cleared by correcting or removal of such conditions.

   Out of memory, temperature crossing a threshold, and so on, are examples of conditions when the alarms are raised.
   Such conditions are dynamic: a faulty software/hardware component encounters the above such condition and **may** come out of that situation when the condition is resolved.

   Events are sent as the condition progresses through being raised and cleared in addition to operator acknowledging/unacknowledging it.
   So, these events have a field called *action*: RAISE, CLEAR or ACKNOWLEDGE/UNACKNOWLEDGE.

   Each of such events for an alarm is characterized by "action" in addition to "severity".

   An application *raises* an alarm when it encounters a faulty condition by sending an event with action: *RAISE*.
   After the application recovers from the condition, that alarm is *cleared* by sending an event with action: *CLEAR*.
   An operator could *ACKNOWLEDGE/UNACKNOWLEDGE* an alarm. This indicates that the operator is aware of the faulty condition.

   The set of alarms and their severities are an indication to health of various applications of the system and System LED can be deduced from alarms.
   An acknowledged alarm means that operator is aware of the condition so, acknowledged alarm will be taken out of consideration.

Both events and alarms get recorded in redis DB.

1.  Event Table

    All events get recorded in the event table, by name, "EVENT". EVENT table contains history of all events generated by the system.
    This table is persisted across system restarts of any kind, including restore to factory defaults and SW upgrades and downgrades.

2. Alarm Table

   All events with an action field of *RAISE* get recorded in a table, by name, "ALARM" in addition to getting recorded in Event Table ( only events corresponding to an alarm has action field ).
   When an application that raised the alarm clears it ( by sending an event with action *CLEAR* ), the alarm record is removed from ALARM table.
   A user acknowledging a particular alarm will NOT remove that alarm record from this table; only when application clears it, the alarm is removed from ALARM table.

   In effect, ALARM table contains outstanding alarms that need to be cleared by those applications who raised them.
   This table is NOT persisted and its contents are cleared with a reload.

In summary, the framework provides both current and historical event status of software and physical entities of the system through ALARM and EVENT tables.

In addition to the above tables, the framework maintains various statisitcs.

1. Event Statistics Table

   Statistics on number of events are maintained in EVENT_STATS table.

2. Alarm Statistics Table

   Statistics on number of alarms per severity are maintained in ALARM_STATS table.
   ALARM_STATS table is not persistent as conditions that triggers an alarm gets cleared on bootup.
   When application raises an alarm, the counter corresponding to that alarm's severity is increased by 1.
   When the alarm is cleared or acknowledged, the corresponding severity counter will be reduced by 1.
   This table categorizes "active" alarms per severity.

As mentioned above, each event has an important characteristic: severity. SONiC uses following severities as defined in opeconfig alarm yang.

- CRITICAL : Requires immediate action. A critical event may trigger if one or more hardware components fail, or one or more hardware components exceed temperature thresholds.
  ( maps to log-alert )
- MAJOR : Requires escalation or notification. For example, a major alarm may trigger if an interface failure occurs, such as a port channel being down.
  ( maps to log-critical )
- MINOR : If left unchecked, might cause system service interruption or performance degradation. An alarm with minor severity requires monitoring or maintenance.
  ( maps to log-error )
- WARNING : It may or may not result in an error condition.
  ( maps to log-warning )
- INFORMATIONAL : Does not impact performance. NOT applicable to alarms.
  ( maps to log-notice )

The following describes how an alarm transforms and how various tables are updated.  
![Alarm Life Cycle](event-alarm-framework-alarm-lifecycle.png)

By default every event will have a severity assigned by the component. 

Template for event profile is as below:
```
{
    "events":[
        {
            "name"     : <name of the event/alarm>,
            "revision" : <revision as a numeric Id>,
            "severity" : <severity of the event/alarm>,
            "enable"   : <flag to indicate whether the framework should ignore event/alarm sent by application>,
            "message"  : <message that describes the condition, possible recovery action. It can be as regular string message or in Json Format.>
        }
    ]
}
```
Event profile only contains declarations of events and their characteristics.

The framework maintains default event profile at /etc/evprofile/default.json.

gNMI clients can subscribe to receive events as they are raised. 

CLI and REST/gNMI clients can query either table with filters - based on severity, delta based on timestamp, sequence-id etc.,

Application owners need to identify various conditions that would be of interest to the operator and use the framework to publish events/alarms.

## 1.1 Requirements


### 1.1.1 Functional Requirements

| ID    | Requirement                                            		                  | Comment             |
| :---  | :----                                                 		                  | :---                |
| 1     | Event Infra to persist all events and alarms in DB.                        |                     |
| 2     | Event Infra to read Event profile ( severity and enable/disable flag ) from a json file. |                    |
| 3     | Event Infra to read Event table parameters (size and # of days) from a config file. |                     |
| 4     | NBI interface (gNMI and REST) and CLI                                           |                     |
| 5.1   | Events                                                        	              |                     |
| 5.1.1 | Openconfig interface to pull event information.                                 |                     |
| 5.1.2 | Openconfig interface to pull event summary information.                         |                     |
|       | Event summary information to contain cumulative counters for:                   |                     |
|       | - Raised-count (events)                                                         |                     |
| 5.1.3 | Openconfig interface to pull events using following filters                     |                     |
|       | - ALL ( pull all events)                                                        |                     |
|       | - Severity.                                                                     |                     |
|       | - Recent records (eg., last 5 minutes, one hour, one day).                      |                     |
|       | - Records between two timestamps,  one timestamp and end, and beginning and a timestamp. |                    |
|       | - All records between two Sequence Numbers (incl begin and end)                 |                     |
| 5.2   | Alarms                                                        	              |                     |
| 5.2.1 | Openconfig interface to pull alarm information.                                 |                     |
| 5.2.2 | Openconfig interface to pull alarm summary information.                         |                     |
|       | Counters for Total, Critical, Major, Minor, Warning, Acknowledged               |                     |
| 5.2.3 | Openconfig interface to pull alarms using following filters                     |                     |
|       | - All (pull all events)                                                         |                     |
|       | - Severity.                                                                     |                     |
|       | - Recent alarms (eg., last 5 minutes, one hour, one day).                       |                     |
|       | - Records between two timestamps, one timestamp and end, and beginning and a timestamp. |                     |
|       | - All records between two Sequence Numbers (incl end and begin)                 |                     |
| 5.2.4 | Openconfig interface  to acknowledge an alarm.                                  |                     |
| 6     | CLI commands                                                                    |                     |
| 6.1   | show alarm [ detail \| summary \| severity \| timestamp <from> <to> \| recent <5min\|1hr\|1day> \| sequence-number <from> <to> \| all]          |                    |
| 6.2   | show event [ detail \| summary \| severity \| timestamp <from> <to> \| recent <5min\|1hr\|1day> \| sequence-number <from> <to>]                 |                     |
| 6.4   | alarm acknowledge <sequence id>                                                 |                     |
| 6.5   | logging server <ip> [ log \| event ]                                             | default is 'log'   |
| 7     | gNMI subscription                                                               |                     |
| 7.1   | Subscribe to openconfig Event container and Alarm container. All events and alarms published to gNMI subscribed clients. |                    |
| 8    | Clear all events                                                                |                     |
| 8    | Any change in open source should be aligned and upstream.                       |                     |

## 1.2 Design Overview

![Block Diagram](eventd-block.png)

### 1.2.1 Basic Approach
The feature involves new development.
EventDB service subscribes to the  zmqproxy service. It processes events as:
It saves the entry in event table; if the event has an action and if it is *RAISE*, record gets added to alarm table, severity counter in ALARM_STATS is increased.
If the received event action is *CLEAR*, record in the ALARM table is removed and severity counter in ALARM_STATS of that alarm is reduced by 1.
If eventd receives an event with action *ACKNOWLEDGE* from mgmt-framework, severity counter in ALARM_STATS is reduced by 1.
If eventd receives an event with action *UNACKNOWLEDGE* from mgmt-framework, severity counter in ALARM_STATS is increased by 1.

Any application like pmon can subscribe to tables like ALARM_STATS to act accordingly.

### 1.2.2 Container
The new service EventDB, will execute in the existing eventd container.

# 2 Functionality
## 2.1 Target Deployment Use Cases

The framework assigns an unique sequence number to each of the events sent by applications.

In addition, the framework provides the following key management services:

- Push model: Event/Alarm information to subscribed gNMI clients
- Pull model: Event/Alarm information from CLI, REST/gNMI interfaces
- Ability to change severity of events, turn off a particular event
- Ability to acknowledge an alarm

## 2.2 Functional Description
Event Management Framework allows applications to store "state" of the system for user to query through various north bound interfaces.

# 3 Design
## 3.1 Overview

Event-DB service in eventd container receives and processes the received events from zmqproxy service.
Event consumer manages received events, updates event table, alarm table, event_stats table and alarm_stats tables.

Through CLI, REST or gNMI, event table and alarm table can be retrieved using various filters.

### 3.1.1 Event Producers

For one-shot events, applications need to provide event-id (name), (source), dynamic message. 

For alarms, applications need to provide event-id (name ), source, dynamic message, and event action (RAISE_ALARM / CLEAR_ALARM / ACK_ALARM /UNACK_ALARM).
The ACK_ALARM/UNACK_ALARM action types are used only by mgmt-framework to provide the functionality to acknowledge/unacknowledge the alarms through NBI.

Eventd maintains a json file of events and alarms at sonic-eventd/var/evprofile/default.json. This is the default event profile that gets installed on the device at /etc/evprofile/default.json.
Developers of new events or alarms need to update this file by declaring name and other characteristics - severity, enable flag and static message that gets appended with dynamic message.

```
{
    "__README__" : "This is default map of events that eventd uses. Developer can modify this file and send
                    SIGINT to eventd to make it read and use the updated file.
                    Developer need to commit default.json file with the new event after testing it out.
                    Supported severities are: CRITICAL, MAJOR, MINOR, WARNING and INFORMATIONAL.
                    Supported enable flag values are: true and false.",
    "events":[
        {
           "name" : "SYSTEM_STATUS",
           "revision" : 0,
		   "severity" : "INFORMATIONAL",
		   "enable" : "true",
		   "message" : "System Status Information"
        },
        {
            "name": "TEMPERATURE_EXCEEDED",
            "revision" : 0,
            "severity": "CRITICAL",
            "enable": "true"
            "message" : "Temperature threshold is 75 degrees."
        }
    ]
}
```

#### 3.1.1.2 Development Process

Declare the event-id of new event/alarm along with revision, severity, enable flag and static message in sonic-eventd/etc/evprofile/default.json

Create a sonic-yang representation of the event as described in the producer framework.

In the source file, the event is published with action as RAISE_ALARM/CLEAR_ALARM (ACK_ALARM/UNACK_ALARM are used by mgmt-framework to allow users to acknowledge/unacknowledge alarms).

The  event publish api introduced by the producer framework  is:
void event_publish(event_handle_t handle, const std:string &event_tag,
        const event_params_t *params=NULL);

For further details of this API, refer to events-producer.md.
The following additional parameters to be given with this api:
1. action - If application has to raise an alarm an "action" attribute has to be given which this api call.
2. resource- The resource on which this event is raised. for e.g., interface name, ip address, etc. 

For e.g call for port down event.
current call:
    event_params_t params = /{/{"ifname",port.m_alias/},/{"status",isUp ? "up" : "down"/}/};
    event_publish(g_events_handle, "if-state", &params);

new call:
    event_params_t params = /{/{"ifname",port.m_alias},{"status",isUp ? "up" : "down"}, {"resource", port.m_alias}, {"event-id", "INTERFACE_OPER_STATUS_CHANGE"}, {"text", isUp? "status:UP" : "status:DOWN"/}/};
    event_publish(g_events_handle, "if-state", &params);


e.g., Sensor temperature critical high
    event_params_t params = /{/{"event-id", "SENSOR_TEMP_CRTICAL_HIGH"}, {"text", "Current temperature {}C, critical high threshold {}C", {"action":"RAISE_ALARM"}, {"resource":"sensor_name"/}/}/} ;
    event_publish(g_events_handle, "sensor_temp_critical_high", &params);
### 3.1.2 Event Consumer
The event consumer is a class in EventDB service that processes the incoming events.

On intitialization, event consumer reads */etc/evprofile/default.json* and builds an internal map of events, called *static_event_map*.
It then subscribes to zmqproxy for events.

On reading the event, using the event-id in the record, event consumer fetches static information from *static_event_map*.
As mentioned above, static information contains severity, static message and event enable flag.
If the enable flag is set to false, event consumer ignores the event by logging a debug message.
If the flag is set to true, it continues to process the event as follows:
- Get source, event-id, sequence id and dynamic msg from the published event. 
- Write the event to Event Table
- It verifies if the event corresponds to an alarm - by checking the *action* field. If so, alarm consumer API is invoked for the event for further processing.
    - If action is RAISE_ALARM, add the record to ALARM table
    - If action is CLEAR_ALARM, remove the entry from ALARM table
    - If action is ACK_ALARM, update *acknowledged* flag of the corresponding raised entry to true in ALARM table and stores timestamp to *acknowledge_time*.
    - If action is UNACK_ALARM, update *acknowledged* flag of the corresponding raised entry to false in ALARM table and stores timestamp to *acknowledge_time*.
    - Event and Alarm Statistics tables are updated


#### 3.1.2.1 Severity
Supported event severities: CRITICAL, MAJOR, MINOR, WARNING and INFORMATIONAL as defined opeconfig alarm yang.
The corresponding syslog severities are: log-alert, log-crit, log-error, log-warning and log-notice respectively.
Severity INFORMATIONAL is not applicable to alarms.

#### 3.1.2.2 Sequence-ID
Every new event should have a unique sequential ID. The sequence-id is of the format <32 bit time_t><5 digit running sequence 00000 to 99999>. These semantics allows applications to layout the logs chronologically. Sequence Id is given by the published event. A  unique id will be associated to every alarm.

#### 3.1.2.3 Revision
Every event/alarm defined in the profile must have a revision specified as a numerical.  If not given, the default revision '0' is assigned to the event/alarm. This revision is to be incremented if the alarm parameters are updated.
For e.g., if TEMPERATURE_EXCEEDED alarm threshold is changed from 65 from original 70, the revision is updated in default.json keeping the name unchanged.
This will allow to redefine the event on an image upgrade. Clients can distinguish events from different sources running different releases.

### 3.1.3 Alarm Consumer
The alarm consume method on receiving the event record, verifies the event action. If it is RAISE_ALARM, it adds the record to Alarm Table.
The counter in ALARM_STATS corresponding to the severity of the incoming alarm is increased by 1.

Eventd maintains a lookup map of *sequence-id* and pair of *event-id* and *resource* fields.
An entry for the newly received event is added to this look up map.

- If the action is CLEAR_ALARM, it removes the previous record of the raised alarm using above lookup map.
  The counter in ALARM_STATS corresponding to the severity of the updated alarm is reduced by 1.

- If the action is ACK_ALARM, alarm consumer finds the raised record of the alarm in the ALARM table using the above lookup map and updates *acknowledged* flag to true. The *acknowledge-time* is updated with the timestamp of ack event.
  ALARM_STATS is updated by reducing the corresponding severity counter by 1.

- If the action is UNACK_ALARM, alarm consumer finds the raised record of the alarm in the ALARM table using the above lookup map and updates *acknowledged* flag to false. The *acknowledge-time* is updated with the timestamp of unack event.
  ALARM_STATS is updated by increasing the corresponding severity counter by 1.

pmon can use ALARM_STATS to update system LED based on severities of outstanding alarms:
```
    Red if any outstanding critical/major alarms, else Yellow if any minor/warning alarms, else Green.
```
An outstanding alarm is an alarm that is either not cleared or not acknowledged by the user yet.

The following illustrates how ALARM table is updated as alarms goes through their life cycle and how can an application use it.
Example here is pmon using ALARM_STATS table to control system LED.

| alarm |  severity  | acknowledged  |
|:-----:|:----------:|:-------------:|
|       |            |               |
|       |            |               |

Alarm table is empty. All counters in ALARM_STATS is 0. System LED is Green.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-1 | CRITICAL   |              |
| ALM-2 | MINOR      |              |

Alarm table now has two alarms. One with *CRITICAL* and other with *MINOR*. ALARM_STATS is updated as: Critical as 1 and Minor as 1. As There is atleast one alarm with *critical/major* severity, system LED is Red.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-2 | MINOR      |              |

The *CRITICAL* alarm is cleared by the application, so alarm consumer removes it from ALARM table, ALARM_STATS is updated as: Critical as 0 and Minor as 1. As there is at least one *minor/warning* alarms in the table, system LED is Amber.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-2 | MINOR      |              |
| ALM-9 | MAJOR      |              |

Now there is an alarm with *MAJOR* severity. ALARM_STATS now reads as: Major as 1 and Minor as 1. So, system LED is Red.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-2 | MINOR      |              |
| ALM-9 | MAJOR      | true         |

The *MAJOR* alarm is acknowledged by user, alarm consumer sets *acknolwedged* flag to true and reduces Major counter in ALARM_STATS by 1, ALARM_STATS now reads as: Major 0 and Minor 1. This way, acknowledged major alarm has no effect on system LED. There are no other *CRITICAL/MAJOR* alarms. There however, exists an alarm with *MINOR/WARNING* severity. System LED is Amber.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-2 | MINOR      | true         |
| ALM-9 | MAJOR      | true         |

The *MINOR* alarm is also acknowledged by user. ALARM_STATS reads: Major as 0, Minor as 0. So it is also taken out of consideration for system LED. System LED is Green.

| alarm |  severity  | acknowledged |
|:-----:|:----------:|:------------:|
| ALM-2 | MINOR      | true         |
| ALM-9 | MAJOR      | false        |

The *MAJOR* alarm is also unacknowledged by user. ALARM_STATS reads: Major as 1, Minor as 0. So it is now considered for system LED. System LED becomes Red.

### 3.1.4 Event Receivers
gNMI clients can subscribe to receive event notifications. 

TODO: add definitions of protobuf spec

#### 3.1.4.1 System LED
The original requirement was to change LED based on severities of the events. But on most of the platforms the system/power/fan LEDs are managed by the BMC.
BMC (baseboard management controller) is an embedded system that manages various platform elements like fan, PSU, temperature sensors.
There is an API that can be invoked to control LED, but not all platforms will support that API if they are fully controlled by the BMC.
So, on certain platforms, system LED could not represent events on the system.

Another issue is: Currently pmon controls LED, and as eventd now tries to change the very same LED, which leads to conflicts.
A mechanism must exist for one of these to be master, which, in this case, is pmon.

The proposed solution is to have pmon use ALAMR_STATS counters in conjunction with existing logic to update system LED.

#### 3.1.4.2 Event/Alarm flooding
There are scenarios when system enters a loop of a fault condition that makes application trigger events continuously. To avoid such
instances flood the EVENT or ALARM tables, eventd maintains a cache of last event/alarm. Every new event/alarm is compared against this cache entry
to make sure it is not a flood. If it is found to be same event/alarm, the newly raised entry will be silently discarded. 


### 3.1.5 Event Profile
The Event profile contains mapping between event-id and severity of the event, enable flag.
Through event profile, operator can set severity and enable/disable an event.

The default profile exists at */etc/evprofile/default.json*
The severity of event is decided by developer while adding the event.

### 3.1.6 CLI
The show CLI require many filters with range specifiers.
Various filters are supported using RPC.

e.g.
```
rpc getEventBySeqeuenceId{
input {
    from sequence-id;
    to sequence-id;
  }
output {
   list event-table-entries;
}
```

The rpc callback needs to access DB with the given set of sequence ids.

The gNMI server (gnoi_client.go, gnoi.go, sonic_proto, transl_utils.go) need to be extended to support the RPC to support similar operations for gNMI.

### 3.1.7 Event Table and Alarm Table
The Event Table (EVENT) and Alarm List Table (ALARM) stored in EVENT_DB.
The size of Event Table is 40k records or 30 days worth of events which ever hits earlier.
A manifest file will be created with parameters to specify the number and number of days limits for
eventd to read and enforce them.


```
root@sonic:/etc# cat eventd.json
{
    "config" :  {
        "no-of-records": 40000,
        "no-of-days": 30
    }
}
```
'no-of-records' indicates maximum number of records EVENT table can hold. The range is 1-40000.
'no-of-days' indicates maximum number of days an event can exist in the EVENT table. The range is 1-30.

When either of the limit is reached, the framework wraps around the table by discarding older records.

User can send SIGINT to eventd process to force read and apply the manifest limits.


An example of an event in EVENT table.
```
EVENT Table:
==============================

Key             : id

id              : Unique sequential ID generated by the system for every event {uint64}
type-id         : Name of the event generated {string}
text            : Dynamic message describing the cause for the event {string}
time-created    : Time stamp at which the event is generated {uint64}
action          : Indicates action of the event; for one-shot events, it is empty. For alarms it could be raise, clear or acknowledge {enum}
resource        : Object which generated the event {string}
severity        : Severity of the event {string}
revision        : Revision of the event {uint64}


127.0.0.1:6379[6]> hgetall "EVENT|1"
1) "time-created"
2) "1696888244771929600"
3) "type-id"
4) "PSU_POWER_STATUS"
5) "text"
6) "PSU 1 is out of power."
7) "action"
8) "RAISE"
9) "resource"
10) "PSU 1"
11) "severity"
12) "WARNING"
13) "id"
14) "21"
15) "acknowledged"
16) "false"
17) "revision"
18) "0"
```

Schema for EVENT_STATS table is as follows:
```
EVENT_STATS Table:
==============================

Key             : id

id              : key {state}
events          : Total events raised {uint64}
raised          : Total alarms raised {uint64}
cleared         : Total alarms cleared {uint64}
acked           : Total alarms acknowledged {uint64}

127.0.0.1:6379[6]> hgetall "EVENT_STATS|state"
1) "events"
2) "1"
3) "raised"
4) "0"
5) "cleared"
6) "0"
7) "acked"
8) "0"
127.0.0.1:6379[6]>
```
Alarm Table will not have any limits as it only contains the snapshot of the alarms during the current run.

Contents of an alarm record. In this case, the alarm was raised temperature crossed a threshold.
```
ALARM Table:
==============================

Key             : id

id              : Unique sequential ID generated by the system for every event {uint64}
revision        : Revision of the alarm {uint64}
type-id         : Name of the event generated {string}
text            : Dynamic message describing the cause for the event {string}
time-created    : Time stamp at which the event is generated {uint64}
acknowledged    : Indicates if alarm has been acknowledged {boolean}
resource        : Object which generated the event {string}
severity        : Severity of the event {string}
acknowledged    : Indicates when alarm has been acknowledged/unacknowledged {uint64}


127.0.0.1:6379[6]> hgetall "ALARM|2"
 1) "type-id"
 2) "TEMPERATURE_EXCEEDED"
 3) "text"
 4) "temperatureCrossedThreshold: Current temperature for sensor/2 is 76 degrees"
 5) "action"
 6) "RAISE"
 7) "resource"
 8) "sensor/2"
 9) "time-created"
10) "1621460371062299951"
11) "severity"
12) "CRITICAL"
13) "id"
14) "2"
15) "acknowledged"
16) "false"
17) "revision"
18) "0"
```

Schema for ALARM_STATS table is as below. When an alarm of particular severity is cleared,
the corresponding severity counter is decremented.
```
ALARM_STATS Table:
==============================

Key                       : id

id                        : key {state}
alarms                    : Number of active alarms {uint64}
critical                  : Number of alarms of severity 'critical' {uint64}
major                     : Number of alarms of severity 'major' {uint64}
minor                     : Number of alarms of severity 'minor' {uint64}
warning                   : Number of alarms of severity 'warning' {uint64}
informational             : Number of alarms of severity 'informational' {uint64}

127.0.0.1:6379[6]> hgetall "ALARM_STATS|state"
 1) "alarms"
 2) "1"
 3) "critical"
 4) "1"
 5) "major"
 6) "0"
 7) "minor"
 8) "0"
 9) "warning"
10) "0"

```
### 3.1.8 Pull Model
All NBIs - CLI, REST and gNMI - can pull contents of alarm table and event table.
The following filters are supported:
- ALL ( pulls all alarms)
- Severity.
- Recent alarms (eg., last 5 minutes, one hour, one day).
- Records between two timestamps, one timestamp and end, and   beginning and a timestamp.
- All records between two Sequence Numbers (incl end and begin)


## 3.2 DB Changes
### 3.2.1 EVENT DB
Event Table (EVENT) and Alarm Table (ALARM) are used to house events and alarms respectively.
To maintain various statistics of events, these two tables are used : EVENT_STATS and ALARM_STATS.


## 3.3 User Interface
### 3.3.1 Data Models

The following is SONiC yang for events.
```

update existing sonic-events-comm.yang
Add attributes type-id and action.
   grouping sonic-events-cmn {
       ....
       ....
        leaf type-id {
            type union {
                type string;
                type identityref {
                   base SONIC_EVENT_TYPE_ID;
                }
            }
            description
            "The abbreviated name of the alarm";
        }
        leaf action {
           type event-action;
           description
           "The action to operation on the event";
        }
    }

module: sonic-event-history
  +--rw sonic-event-history
     +--rw EVENT
     |  +--rw EVENT_LIST* [id]
     |     +--rw id              uint64
     |     +--rw revision        uint64  
     |     +--rw resource?       string
     |     +--rw text?           string
     |     +--rw time-created?   timeticks64
     |     +--rw type-id?        string
     |     +--rw severity?       severity-type
     |     +--rw action?         action-type
     +--rw EVENT_STATS
        +--rw EVENT_STATS_LIST* [id]
           +--rw id         enumeration
           +--rw events?    uint64
           +--rw raised?    uint64
           +--rw acked?     uint64
           +--rw cleared?   uint64

  rpcs:
    +---x show-event-history
       +---w input
       |  +---w (option)?
       |     +--:(time)
       |     |  +---w time
       |     |     +---w begin?   yang-types:date-and-time
       |     |     +---w end?     yang-types:date-and-time
       |     +--:(last-interval)
       |     |  +---w interval?   enumeration
       |     +--:(severity)
       |     |  +---w severity?   severity-type
       |     +--:(id)
       |        +---w id
       |           +---w begin?   string
       |           +---w end?     string
       +--ro output
          +--ro status?          int32
          +--ro status-detail?   string
          +--ro EVENT
             +--ro EVENT_LIST* [id]
                +--ro id              uint64
                +--ro revision        uint64
                +--ro resource?       string
                +--ro text?           string
                +--ro time-created?   timeticks64
                +--ro type-id?        string
                +--ro severity?       severity-type
                +--ro action?         action-type
```

The following is SONiC yang for alarms.
```
module: sonic-alarm
  +--rw sonic-alarm
     +--rw ALARM
     |  +--rw ALARM_LIST* [id]
     |     +--rw id                  uint64
     |     +--rw revision            uint64
     |     +--rw resource?           string
     |     +--rw text?               string
     |     +--rw time-created?       event:timeticks64
     |     +--rw type-id?            string
     |     +--rw severity?           event:severity-type
     |     +--rw acknowledged?       boolean
     |     +--rw acknowledge-time?   event:timeticks64
     +--rw ALARM_STATS
        +--rw ALARM_STATS_LIST* [id]
           +--rw id              enumeration
           +--rw alarms?         uint64
           +--rw critical?       uint64
           +--rw major?          uint64
           +--rw minor?          uint64
           +--rw warning?        uint64
           +--rw acknowledged?   uint64

  rpcs:
    +---x acknowledge-alarms
    |  +---w input
    |  |  +---w id*   string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x unacknowledge-alarms
    |  +---w input
    |  |  +---w id*   string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x show-alarms
       +---w input
       |  +---w (option)?
       |     +--:(time)
       |     |  +---w time
       |     |     +---w begin?   yang-types:date-and-time
       |     |     +---w end?     yang-types:date-and-time
       |     +--:(last-interval)
       |     |  +---w interval?   enumeration
       |     +--:(severity)
       |     |  +---w severity?   event:severity-type
       |     +--:(id)
       |        +---w id
       |           +---w begin?   string
       |           +---w end?     string
       +--ro output
          +--ro status?          int32
          +--ro status-detail?   string
          +--ro ALARM
             +--ro ALARM_LIST* [id]
                +--ro id                  uint64
                +--ro revision            uint64
                +--ro resource?           string
                +--ro text?               string
                +--ro time-created?       event:timeticks64
                +--ro type-id?            string
                +--ro severity?           event:severity-type
                +--ro acknowledged?       boolean
                +--ro acknowledge-time?   event:timeticks64
```

openconfig alarms yang is defined  [here](https://github.com/openconfig/public/blob/master/release/models/system/openconfig-alarms.yang)

### 3.3.2 CLI
#### 3.3.2.1 Exec Commands
```
sonic# alarm acknowledge <seq-id-of-raised-alarm>
```
An operator can acknolwedge a raised alarm. This indicates that the operator is aware of the fault condition and considers the condition not catastrophic.
Acknowledging an alarm updates alarm statistics and thereby applications like pmon can remove the particular alarm from status consideration.

The alarm record in the ALARM table is marked with acknowledged field set to true. There is acknowledge-time field that indicates when that alarm is acknowledged.

```
sonic# alarm unacknowledge <seq-id-of-raised-alarm>
```
An operator can un-acknolwedge a previously acknowledged raised alarm.
Un-acknowledging an alarm updates alarm statistics and thereby applications like pmon can take the particular alarm into status consideration.

The alarm record in the ALARM table is marked with acknowledged field set to false.
There is acknowledge-time field that indicates when that alarm is un-acknowledged.

```
sonic# clear event
```
This command clears all the records in the event table. All the event stats are cleared.
The command will not affect alarm table or alarm statistics.
Eventd generates an event informing that event table is cleared.

#### 3.3.2.3 Show Commands
```
sonic# show event [ details | summary | severity <sev> | start <from-ts> end <to-ts> | recent <5min|60min|24hr> | id <seq-id> | from <seq-id> to <seq-id> ]

'show event' commands would display all the records in EVENT table.

sonic# show event

----------------------------------------------------------------------------------------------------
Id           Action          Severity       Name                           Timestamp
----------------------------------------------------------------------------------------------------
1            RAISE           WARNING        PSU_POWER_STATUS              2023-10-09T21:50:44.771Z
2            -               INFORMATIONAL  SYSTEM_STATUS                 2023-10-09T21:51:02.784Z
3            RAISE           CRITICAL       DUMMY_ALARM                   2023-15-19T21:39:31.622Z
4            CLEAR           CRITICAL       DUMMY_ALARM                   2023-15-19T21:42:34.371Z
5            RAISE           CRITICAL       DUMMY_ALARM                   2023-15-19T21:46:14.371Z
6            ACKNOWLEDGE     CRITICAL       DUMMY_ALARM                   2023-15-19T21:48:05.845Z
7            UNACKNOWLEDGE   CRITICAL       DUMMY_ALARM                   2023-15-19T21:53:24.484Z
8            CLEAR           CRITICAL       DUMMY_ALARM                   2023-15-19T21:55:54.977Z


sonic# show event details

---------------------------------------------
Event Details - 1 
----------------------------------------------
Id:                  1
Action:              RAISE
Severity:            WARNING
Revision:            0 
Type:                PSU_POWER_STATUS
Timestamp:           2023-10-09T21:50:44.771Z
Description:         PSU 1 is out of power.
Source:              PSU 1
 
----------------------------------------------
Event Details - 2 
----------------------------------------------
Id:                  2 
Action:              RAISE 
Severity:            INFORMATIONAL
Revision:            0 
Type:                SYSTEM_STATUS
Timestamp            2023-10-09T21:51:02.784Z
Description:         System is ready
Source:              system_status

----------------------------------------------
Event Details - 3
----------------------------------------------
Id:                  3
Action:              CLEAR
Severity:            CRITICAL
Revision:            1 
Type:                DUMMY_ALARM
Timestamp            2021-05-19T21:42:34.371Z
Description:         signalHandler: Clearing simulated alarm
Source:              simulation

sonic# show event summary
Event summary
---------------------------------
Total:                         14
Raised:                        4
Acknowledged:                  1
Cleared:                       3
----------------------------------

sonic# show event severity critical
----------------------------------------------------------------------------------------------------------------------------
Id           Action          Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
2            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:39:31.622Z    signalHandler: Raising simulated alarm         
3            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:42:34.371Z    signalHandler: Clearing simulated alarm        
4            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:46:14.371Z    signalHandler: Raising simulated alarm         
5            ACKNOWLEDGE     CRITICAL   DUMMY_ALARM                    2021-05-19T21:48:05.845Z    Alarm id 4 ACKNOWLEDGE.                           
6            UNACKNOWLEDGE   CRITICAL   DUMMY_ALARM                    2021-05-19T21:53:24.484Z    Alarm id 4 UNACKNOWLEDGE.                         
7            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:55:54.977Z    signalHandler: Clearing simulated alarm

sonic# show event recent 24hr
----------------------------------------------------------------------------------------------------------------------------
Id           Action          Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
2            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:39:31.622Z    signalHandler: Raising simulated alarm         
3            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:42:34.371Z    signalHandler: Clearing simulated alarm        
4            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:46:14.371Z    signalHandler: Raising simulated alarm         
5            ACKNOWLEDGE     CRITICAL   DUMMY_ALARM                    2021-05-19T21:48:05.845Z    Alarm id 4 ACKNOWLEDGE.                           
6            UNACKNOWLEDGE   CRITICAL   DUMMY_ALARM                    2021-05-19T21:53:24.484Z    Alarm id 4 UNACKNOWLEDGE.                         
7            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:55:54.977Z    signalHandler: Clearing simulated alarm

sonic# show event id 2
----------------------------------------------
Event Details - 2
----------------------------------------------
Id:                  2
Revision:            1
Action:              RAISE
Severity:            CRITICAL
Type:                DUMMY_ALARM
Timestamp            2021-05-19T21:39:31.622Z
Description:         signalHandler: Raising simulated alarm
Source:              simulation

sonic# show event from 2 to 5
----------------------------------------------------------------------------------------------------------------------------
Id           Action          Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
2            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:39:31.622Z    signalHandler: Raising simulated alarm         
3            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:42:34.371Z    signalHandler: Clearing simulated alarm        
4            RAISE           CRITICAL   DUMMY_ALARM                    2021-05-19T21:46:14.371Z    signalHandler: Raising simulated alarm         
5            ACKNOWLEDGE     CRITICAL   DUMMY_ALARM                    2021-05-19T21:48:05.845Z    Alarm id 4 ACKNOWLEDGE.

sonic# show event start 2021-05-19T21:39:31.622Z end 2021-05-19T21:46:14.371Z
----------------------------------------------------------------------------------------------------------------------------
Id           Action          Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
3            CLEAR           CRITICAL   DUMMY_ALARM                    2021-05-19T21:42:34.371Z    signalHandler: Clearing simulated alarm

sonic# show alarm [ acknowledged | all | detail | summary | severity <sev> | id <seq-id> | start <from-ts> end <to-ts> | recent <5min|1hr|1day> | from <from-seq> to <to-seq> ]

'show alarm' command would display all the *active* alarm records in ALARM table. Acknowledged alarms wont be shown here.

sonic# show alarm
----------------------------------------------------------------------------------------------------------------------------
Id           Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
14           WARNING    TEMPERATURE_EXCEEDED           2021-05-20T00:47:52.992Z    temperatureCrossedThreshold: Current temperature of sensor/2 is 76 degrees         
16           WARNING    PSU_FAULT                      2021-05-20T02:16:42.611Z    :- /psu/2 has experienced a fault

sonic# show alarm all
----------------------------------------------------------------------------------------------------------------------------
Id           Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
14           WARNING    TEMPERATURE_EXCEEDED           2021-05-20T00:47:52.992Z    temperatureCrossedThreshold: Current temperature of sensor/2 is 76 degrees         
15           WARNING    DUMMY_ALARM                    2021-05-20T02:16:41.637Z    signalHandler: Raising simulated alarm         
16           WARNING    PSU_FAULT                      2021-05-20T02:16:42.611Z    /psu/2 has experienced a fault


sonic# show alarm detail

alarm details - 14
-------------------------------------------
Id:                14
Revision:          0   
Severity:          CRITICAL
Source:            /sensor/2
Name:              TEMPERATURE_EXCEEDED
Description:       temperatureCrossedThreshold: Current temperature of sensor/2 is 76 degrees
Raise-time:        Wed Feb 10 18:08:24 2021
Ack-time:          
New:               true
Acknowledged:      false

sonic# show alarm from 14 to 16
----------------------------------------------------------------------------------------------------------------------------
Id           Severity   Name                           Timestamp                   Description                                                  
----------------------------------------------------------------------------------------------------------------------------
14           WARNING    TEMPERATURE_EXCEEDED           2021-05-20T00:47:52.992Z    temperatureCrossedThreshold: Current temperature of sensor/2 is 76 degrees         
15           WARNING    DUMMY_ALARM                    2021-05-20T02:16:41.637Z    signalHandler: Raising simulated alarm         
16           WARNING    PSU_FAULT                      2021-05-20T02:16:42.611Z    /psu/2 has experienced a fault

sonic# show alarm summary
Alarm summary
---------------------------------
Total:                         3
Critical:                      0
Major:                         0
Minor:                         0
Warning:                       3
Acnowledged:                   2
----------------------------------
```

### 3.3.3 REST API Support

sonic REST links:
*  /restconf/data/sonic-event:sonic-event-history/EVENT/EVENT_LIST
*  /restconf/data/sonic-event:sonic-event-history/EVENT_STATS/EVENT_STATS_LIST
*  /restconf/data/sonic-alarm:sonic-alarm/ALARM/ALARM_LIST
*  /restconf/operations/sonic-alarm:unacknowledge-alarms

openconfig REST links:
*  /restconf/data/openconfig-system:system/openconfig-event-history:events
*  /restconf/data/openconfig-system:system/openconfig-event-history:event-stats
*  /restconf/data/openconfig-system:system/alarms
*  /restconf/data/openconfig-system:system/openconfig-alarms-ext:alarm-stats


# 4 Persistence
Alarms and Events are stored in ALARM and EVENT tables in a separate Redis DB instance called EventDB.
This instance is configured to periodically persist the EventDB to disk.
It is configured to persist 75 redis db events at 180 seconds. This is equal to ~5-6 Sonic Events.


## 4.1 Warm reboot
### 4.1.1 Application restart
Applications confirming to restart, should store their state and compare current values against previous values.
Such compliant application also "remembers" that it raised an event before for a specific condition.
They would
*  not raise alarms/events for the same condition that it raised pre restart.
*  clear those alarms once current state of a particular condition is recovered (by comparing against the stored state).

### 4.1.2 System warm reboot
On system warm reboot the current EventDB is persisted on disk without the ALARM and ALARM_STATS table. Applications should check the condition after restart, and raise the alarm if condition exists.
Only EVENT table is persisted on disk across system warmboot. This overwrites the DB file from periodic persistence.


## 4.2 Fast reboot
On system fast reboot the current EVENT and EVENT_STATS table from EventDB are persisted on disk. ALARM and ALARM_STATS table are not persisted. Applications have to raise alarm on restart if condition exists.
The Event DB is stored on disk prior to control plane protocol services shutdown, to not impact fast-boot times. This overwrites the DB from periodic persistence.

## 4.3 Cold reboot
The current EVENT and EVENT_STATS table are persisted on disk across cold boot. ALARM and ALARM_STATS table are not persisted, and applications have to raise alarm on restart if condition exists. This overwrites the DB from periodic persistence.

## 4.4 Power reset
In power reset, the EventDB is loaded from the DB on disk. This DB is from periodic persistence. The ALARM and ALARM_STATS table is removed from the table.
Applications have to raise alarm on restart if condition exists. In this case, there can be events missing from previous boot, as the reset may have happened within the periodic persistence timer interval.


# 5 Scalability
In this feature, scalability applies to Event Table (EVENT). As it is persistent and it records every event generated on the system, to protect
against it growing indefinitely, user can limit its size through a manifest file.
By default, the size of Event Table is set to 40k events or events for 30 days - after which, older records are discarded to make way for new records.

# 6 Showtech support
The techsupport bundle is upgraded to include output of "show event recent 60min” and “show alarm all”.
The first command displays all the events that were sent by applications for the last one hour.
The second command displays all the alarms that are waiting to be cleared by applications (this includes alarms that were acknowledged by operator as well).

# 7 Unit Test
- Raise an event and verify the fields in EVENT table and EVENT_STATS table
- Raise an alarm and verify the fields in ALARM table and ALARM_STATS table
- Clear an alarm and verify that record is removed from ALARM and ALARM_STATS tables are udpated
- Ack an alarm and verify that acknowledged flag is set to true in ALARM table and acknowledge-time is set
- Un-Ack an alarm and verify that acknowledged flag is set to false in ALARM table and acknowledge-time is set
- Verify wrap around for EVENT table ( change manifest file to a lower range and trigger that many events )
- Verify sequence-id for events is persistent by restarting
- Verify counters by raising various alarms with different severities
- Verify various show commands
- Verify 'logging-server <ip> event' command forwards only event log messages to the host
