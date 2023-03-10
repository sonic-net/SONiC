# gNMI Subscription for YANG Data

This document describes the high level design for SONiC Telemetry service and Translib infrastructure
to support gNMI subscriptions and wildcard paths for YANG defined paths.

## Table of Contents

## Revision History

| Rev |     Date    |       Author       | Change Description                                     |
|-----|-------------|--------------------|--------------------------------------------------------|
| 0.1 | 03/02/2023  | Sachin Holla       | Initial draft                                          |

## Definition and Abbreviation

| **Term**       | **Meaning**                         |
|----------------|-------------------------------------|
| gNMI           | gRPC Network Management Interface   |
| gRPC           | gRPC Remote Procedure Call (it is a recursive acronym!!)   |
| RPC            | Remote Procedure Call.. In this document it mostly refers to the operations defined by gNMI specification |
| YGOT           | [YANG Go Tools](https://github.com/openconfig/ygot); a Golang library to process YANG data |

## 1 Feature Overview

### 1.1 Introduction

SONiC Telemetry service suports gNMI Get, Set and Subscribe RPCs for DB paths and sonic-yang based paths.
It also suppots Get and Set for OpenConfig and IETF yang based paths that are part of **sonic-mgmt-common** repository.
This design document describes proposed enhancements to support gNMI Subscribe RPC for such YANG paths.

### 1.2 Requirements

#### 1.2.1 ON_CHANGE subscription for eligible paths

Infrastructure should support ON_CHANGE subscription for YANG paths based on redis keyspace notifications.
It should provide APIs for apps to specify ON_CHANGE unsupported paths.
An `INVALID_ARGUMENT` status should be returned if the target path or any of its descendent paths do not support ON_CHANGE.

#### 1.2.2 SAMPLE subscription for all paths

Infrastructure should support SAMPLE subscription for all YANG paths.
It should provide APIs for apps to indicate minimum `sample_interval` supported for the path.
An `INVALID_ARGUMENT` status should be returned if the minimum `sample_interval` of target path or any of its descendent paths is more than the requested `sample_interval`.

#### 1.2.3 TARGET_DEFINED subscription for all paths

Infrastructure should support TARGET_DEFINED subscription for all YANG paths.
Subscribe request should be treated as ON_CHANGE or SAMPLE based on the app's preferences for the target path.
It should split into multiple requests if the target path supports ON_CHANGE
but some of its descendent paths do not.

#### 1.2.4 POLL and ONCE subscriptions

Infrastructure should support SAMPLE subscription for all YANG paths.

#### 1.2.5 Support Wildcard Keys

Infrastructure should support wild cards in **path key** for all subscription modes.
Example: `/openconfig-interfaces:interfaces/interface[name=*]/config`.
Path can contain any number of wildcard key values.
Apps should be allowed to indicate wildcard unsupported paths.
An `INVALID_ARGUMENT` status should be returned if wildcard key cannot be supported for the target path.

Wildcard in path element (like `/interfaces/*/config` or `/interfaces/.../config`) is a stretch goal.

#### 1.2.6 Scalar encoding for telemetry updates

All telemetry updates should be encoded as gNMI scalar types.
Each update entry should be a {leaf path, scalar value} pair.
Scalar type encoding is explained in gNMI specification [section 2.2.3](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#223-node-values).

#### 1.2.7 Co-exist with existing gNMI server functionality

Proposed enhancements should not affect any of the existing functionalities of the SONiC Telemetry Service.

### 1.3 Translib Overview

Translib is a golang library for reading and writing YANG model based data to redis DB or non-DB data source.
Applications would plugin the YANG models and their translation code into the translib.
These application components are called *app modules*.
Northbound API servers, like REST/gNMI servers, can call translib functions likes `Get()`, `Create()`, `Delete()` to process the request they received.
Translib then invokes corresponding app modules to translate the YANG and and perform actual read/write operations.
Following diagram provides a very high level summary;
[Management Framework HLD](../Management%20Framework.md) contains more details.

![Translib Overview](images/Translib_overview.png)

Translib will be enhanced to provide new functions for supporting subscription.
There will be new requirements on app modules for providing additional details to translib to handle subscription.
gNMI server will be enhanced to identify the Subscribe requests for translib YANG paths and use the new translib functions to service it.

### 1.4 References

SONiC Management Framework<br>
https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md

SONiC GRPC Telemetry<br>
https://github.com/sonic-net/SONiC/blob/master/doc/system-telemetry/grpc_telemetry.md

SONiC gNMI Server Interface Design<br>
https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md

gNMI Specification<br>
https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md

gNMI Protobuf Definition<br>
https://github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto

## 2 High Level Design

### 2.1 Role of Framework and App Components

- gNMI server will manage subscribe RPC life cycle, timers, validations, response encoding.

- Translib will provide APIs to monitor and retrieve subscribed YANG data.
  Following new translib APIs will be implemented:
  - `IsSubscribeSupported()` to return subscription preferences for given paths.
  - `Stream()` to return current data for given paths through a queue
  - `Subscribe()` to handles ON_CHANGE subscriptions.
    It starts monitoring the mapped DB key patterns using redis PSUBSCRIBE operations.
    Subsequent changes to the DB will be stream asynchronously using a queue.

- App modules are only required to provide YANG path to DB entry mappings and vice-versa.

- App modules should implement app interface function `translateSubscribe()` to provide
  YANG path to DB/non-DB mappings.
  - Should include mappings for given YANG node and all its child nodes
  - Should handle wildcard keys in the yang paths.
  - Mapped DB key can have a redis wildcard pattern.
  - One YANG path can have multiple DB/non-DB mappings.

- App modules can also return subscription preferences in `translateSubscribe()` response.
  Translib will assume default values if app did not specify the preferences.
  Preferences includes:
  - Whether ON_CHANGE enabled
  - Minimum SAMPLE interval.
  - Preferred subscription mode during TARGET_DEFINED

- Transformer common_app will discover the mappings and preferences from the annotations.
  Subtree transformers should implement `Subscribe_xxx()` callback function to specify
  the mappings and preferences.
  Table and key transformers should handle wildcard paths.

- App modules should implement `processSubscribe()` app interface function to resolve YANG keys for a DB entry.
  This is required to get a specific YANG path from a wildcard path template.

- Transformer common_app will automatically support this for simple cases.
  Apps should implement a *path transformer* to handle special cases --
  subtree transformer or when there is no one-to-one mapping of YANG key to DB key.

### 2.2 Identifying YANG Based Subscriptions

Today the gNMI server supports subscription based on SONiC specific "DB paths" and "virtual paths"
as described in the [GRPC Telemetry HLD](../../system-telemetry/grpc_telemetry.md).
It uses the request `target` value to identify type of the subscribe paths.
A subscribe request will be rejected if `target` was not specified.

This is not in sync with the [gNMI specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#2221-path-target).
`target` is optional and is supposed to be an opaque data for the server.
However, the current behavior will not be removed completely for the sake of backward compatibility.
The request `target` will be made optional.
Request will be processed as described in [GRPC Telemetry HLD](../../system-telemetry/grpc_telemetry.md)
if the `target` is specified and matches one of the reserved keywords listed in that HLD.
If `target` is not specified or not one of the reserved ones, the subscribe path will be treated as tarnslib YANG path.

### 2.3 Manage Subscription RPC Lifecycle

Existing subscription RPC management code will be re-used as is.
Subscription RPCs, except ONCE, will be active until client cancels it or an error is encountered in translib.
RPC will not survive the switch reboot or telemetry service/process restart events.

### 2.4 Streaming Data from Translib

Unlike Get, translib will be returning multiple responses while processing the subscribe request.
To handle this, the gNMI server would pass a queue to translib and wait for the response on it.
Translib will push response objects or the error info to that queue as a `SubscribeResponse` object.
It contains following information:

- Event timestamp
- Path and YGOT object containing updated values
- List of deleted paths
- *SyncComplete* flag indicating all current values have been streamed out.
- *IsTerminated* flag indicating that translib encountered an error and stopped processing the subscription.

gNMI server will dequeue the `SubscribeResponse`, prepare a gNMI notification message and stream it back to the client.
If *IsTerminated* flag is set, gNMI server will end the subscription with an error status.

### 2.5 Collecting Subscription Preferences for YANG Paths

gNMI server would collect the subscription preferences for the requested YANG paths
by calling the translib API `IsSubscribeSupported()`.
It returns following preferences for each requested path:

- Whether ON_CHANGE supported
- Minimum sample interval
- Preferred stream mode to be used for TARGET_DEFINED

gNMI server would reject the subscription with `INVALID_ARGUMENT` status if:

- `IsSubscribeSupported()` returned an error, indicating invalid path or app is not ready to handle subscription
- ON_CHANGE subscription is requested but path does not support ON_CHANGE
- Requested `sample_interval` is less than the minimum sample interval for the path

These validations will be performed for each path in the subscribe request.
If success, the gNMI server would call translib `Stream()` and `Subscribe()` APIs to process the subscription --
discussed in subsequent sections.

### 2.6 Collecting YANG Path to DB Mappings

Translib collects YANG path to DB mappings when `IsSubscribeSupported()` is called.
Translib invokes app module's `translateSubscribe()` function to collect DB mappings for a path.
It should return array of notificationAppInfo objects containing following data:

- Path to mapped YANG node.
  Should be same as request path or one of its descendent paths.
- Mapped DB index, table name, DB key pattern
- DB field name to YANG leaf subpath mappings.
- Whether ON_CHANGE supported
- Minimum SAMPLE interval
- Preferred subscription mode for TARGET_DEFINED

Mapping should be returned even if the YANG node does not map to a DB entry.
The DB index should set to unknown db to indicate the non-DB mapping.

In many scenarios, few child paths of a YANG path may be mapped to a different table.
Additional `notificationAppInfo` objects should be should be created for such sub-paths.

An example with a simplified openconfig-interfaces YANG model:

```text
module: openconfig-interfaces
  +--rw interfaces
     +--rw interface*       ==> CONFIG_DB:PORT
        +--rw name
        +--rw config
        |  +--rw enabled
        +--ro state         ==> APPL_DB:PORT_TABLE
        |  +--ro enabled
        |  +--ro oper-status
```

| **YANG Path**                         | **DB mappings**                         |
|---------------------------------------|-----------------------------------------|
| /interfaces/interface[name=\*]         | {CONFIG_DB, PORT, \*, {admin_status=config/enabled}}<br> {APPL_DB, PORT_TABLE, \*, {admin_status=state/enabled, oper_status=state/oper-status}} |
| /interfaces/interface[name=Ethernet0]/config  | {CONFIG_DB, PORT, Ethernet0, {admin_status=enabled}} |
| /interfaces/interface[name=\*]/state/oper-status  | {APPL_DB, PORT_TABLE, \*, {oper_status=oper-status}} |
| /interfaces/interface[name=Ethernet0]/config      | {CONFIG_DB, PORT, Ethernet0, {admin_status=enabled}} |

There is also a possibility of leaf path getting mapped to multiple DB tables.
E.g, real life `/interfaces/interface[name=*]` will map to (CONFIG_DB, PORT, \*, {...}), (CONFIG_DB, PORTCHANNEL, \*, {...}) and so on.

### 2.7 Subscribe Session

ON_CHANGE and SAMPLE are long running subscriptions; they will be active till the gNMI client closes the RPC.
Translib will need the subscription preferences and DB mappings at multiple stages.
To avoid calling app module's `translateSubscribe()` multiple times, translib caches these translated path info
in a `SubscribeSession` object.
gNMI server should create a `SubscribeSession` when a subscription RPC is started and keep passing it to all the translib APIs invoked for processing that RPC.
This enables translib to re-use the DB mappings collected during `IsSubscribeSupport()` in subsequent `Stream()` and `Subscribe()` calls.
Contents of `SubscribeSession` are opaque to the gNMI server.
The session must be closed while existing the RPC to cleanup the cached information.

### 2.8 Handling ON_CHANGE

#### 2.8.1 Basic Approach

Translib relies on redis keyspace notifications to support ON_CHANGE subscription for the YANG data.
gNMI Server uses translib `Subscribe()` API to starts the ON_CHANGE subscription for given YANG paths.
It starts monitoring all the redis keys mapped to given path and its sub-paths using redis PSUBSCRIBE operation.
Redis notifies translib when any of the monitored DB entries are updated/deleted.
Translib will translate this back to YANG data, prepare a `SubscribeResponse` object and
send it to the gNMI server over the response queue.
gNMI server will dequeue the `SubscribeResponse`, prepare a gNMI notification message and send it back to the client.
Following sequence diagram indicates overall flow of ON_CHANGE processing.

![ON_CHANGE High Level Design](images/Subscribe_ONCHANGE.png)

#### 2.8.2 Translib `Subscrine()` API

The `Subscribe()` API manages redis subscriptions and notifications for given YANG paths.
It expects following information from gNMI server:

- YANG paths
- A queue for sending back responses
- A *channel* object that signals subscription cancellation
- Subscribe Session object

DB mappings cached in `SubscribeSession` will be used to compute all corresponding redis key patterns.
Translib will start monitoring those redis keys using PSUBSCRIBE operation.
Notification handler will run in a separate goroutine.

gNMI Subscribe PRC requires server to stream current data values before it could send incremental updates.
To send the current data, translib will collect all existing redis keys using SCAN operation on the mapped redis key patterns.
These keys will be translated to YANG paths as described in section [2.8.3](#283-db-key-to-yang-path-mapping).
App Module's `processGet()` will be invoked for each such YANG paths and each YANg data will be pushed to the response queue one-by-one.
This approach tends to result in Translib sending stream of smaller chunks of data.

Once the initial data responses are complete, the `Subscribe()` function ends.
But the notification handler will continue to run until gNMI servers sends a cancel signal (through the cannel it passed to the `Subscribe()` function) or a redis PubSub read fails.

#### 2.8.3 DB key to YANG Path mapping

If the subscribed path had wildcard keys, those wildcards need to be resolved in the response YANG paths.
Translib will use App Module's `processSubscribe()` function to achieve this.
This is inverse of YANG path to DB key mapping ([2.6](#26-collecting-yang-path-to-db-mappings)).
Following information will be passed to the `processSubscribe()` function:

- Original path containing wildcards
- Actual DB entry info -- redis key and its values.

App module should return the YANG path by filling all the wildcard keys of the input path.

#### 2.8.4 OnChange Cache

Not all keyspace notifications should be treated a valid notifications.
Translib may be interested in only few fields of a table depending on the subscribed YANG paths.
Redis only notifies which key was modified, but does not indicate which fields were modified.
Hence, translib maintains a cache of all the DB entries it is monitoring.
This cache is initialized while sending initial updates from `Subscribe()` function.
Later when a redis keyspace notification is received, translib reads latest entry value from DB for that key
and compares with the cache to identify modified fields.
Cache is also updated with the new value in this process.
Notification will be ignored if none of the subscribed fields are changed.
This helps to suppress noises close to the source.

Each subscribe session will have its own cache.
It will be destroyed when the session is closed (i.e, when Subscribe RPC ends).

#### 2.8.5 Sending Notifications

Translib notification handler will calculate the modified DB fields by comparing the latest DB entry with the OnChange cache entry.
Notification is ignored if there are no changes relevant to current subscribe paths.
Redis key create/delete and create/update/delete of any of the fields peresent in the DB mapping are considered processed further.
A `SubscribeResponse` object will be constructed as listed below:

| Redis event type    | SubscribeResponse contents                                         |
|---------------------|--------------------------------------------------------------------|
| Key delete          | DeletedPath = subscribed path                                      |
| Key create          | UpdateValue = `processGet()` output of subscribed YANG path        |
| Field delete        | DeletedPath = subscribed path + mapped relative path of that field |
| Field create/update | UpdateValue = `processGet()` output of subscribed path + mapped relative path of that field |

If subscriber path had wildcard keys, they will be resolved by calling app module's `processSubscribe()` function.

gNMI server will dequeue the `SubscribeResponse`, prepare a gNMI notification message and stream it to the client.

App module functions normally load the DB entry to construct the YANG data.
Translib would have already loaded the same entry as part of cache diff computation.
A special DB Access object will be passed to app module's `processSubscribe()` and `processGet()` functions, which returns the values from OnChange cache.
This avoids multiple DB reads of a same key as part of one notification handling.

#### 2.8.6 Notification Timestamp

Time at which the notification handler receives the keyspace notification event from the redis will used as notification timestamp.

### 2.9 Handling SAMPLE

#### 2.9.1 Basic Approach

SAMPLE subscription will be handled similar to ON_CHANGE's initial data sync.
But there will not be any redis subscriptions and DB cache.
New `Stream()` API will be introduced in translib for SAMPLE handling.
gNMI server will manage the sample timer and invoke the `Stream()` function on every timer tick.
Following sequence diagram describes the overall flow.

![SAMPLE High Level Design](images/Subscribe_SAMPLE.png)

#### 2.9.2 Translib `Stream()` API

The `Stream()` will returns current data snapshot for specified YANG paths.
This will be similar to the `Subscribe()` API, but without redis subscription and notification handler.
Unlike `Get()`, `Stream()` will not coalesce all YANG data into one big blob.
Instead it streams smaller chunks (YGOT object) through the response queue.

If the subscribe path is not mapped to any DB table (non-DB data) and does not have wildcard keys, then
`Stream()` will fallback to `Get()`.

#### 2.9.3 YGOT Cache

To detect deleted resources, gNMI server will maintain previous iteration's snapshot in a {path, YGOT object} cache.
Current iteration's data is compared against this cache to identify deleted objects or attributes.
YGOT API `ygot.Diff()` can be used to compare two YGOT objects.
Cache will be updated wih the current values at the end of each iteration.

gNMI client can set `suppress_redundant` flag in the request to avoid receiving duplicate updates at every sample interval.
Server should not send an update for a leaf unless its value is modified since last update.
YGOT snapshot cache will also be used to resolve updated attributes.

YGOT based diff can be heavier and slower compared to DB entry based cache, like the one used for ON_CHANGE.
However such cache cannot be used for non-DB data.
SAMPLE subscription must be supported for every YANG path, irrespective of whether it maps to a DB entry or not.
YGOT snapshot cache approach is chosen to keep the implementation simple.
A mixed approach (DB entry cache in translib for DB data and YGOT cache in gNMI server for non-DB data) can be considered in future releases if we run into performance issues with YGOT cache.

#### 2.9.4 Notification Timestamp

SONiC database does not maintain last updated timestamp for DB fields or even keys.
Translib cannot determine the actual timestamp for the data.
Hence it will always use the timestamp at which `Stream()` read the DB entry as notification timestamp.

### 2.10 Handling TARGET_DEFINED

TARGET_DEFINED subscription flow is similar to that of ON_CHANGE and SAMPLE.
Preferred subscription mode for the path is discovered from the metadata returned by `IsSubscribeSupported()` API.
ON_CHANGE or SAMPLE subscriptions are created based on these preferences.

- If the subscribe path and its descendent nodes prefer ON_CHANGE, then the request is treated as an ON_CHANGE subscription request.
- If the subscribe path prefers SAMPLE, then the request is treated as a SAMPLE subscription request.
- If the subscribe path prefers ON_CHANGE but few of its descendent nodes prefer SAMPLE,
  then the request is treated as multiple requests internally.
  Server starts SAMPLE subscription for the descendent nodes that prefer SAMPLE.
  An ON_CHANGE subscription will be created for rest of the nodes.

Few examples with a simplified openconfig-interfaces YANG model:

```text
module: openconfig-interfaces
  +--rw interfaces
     +--rw interface*
        +--rw name
        +--rw config        ==> CONFIG_DB:PORT
        |  +--rw enabled
        +--ro state         ==> APPL_DB:PORT_TABLE
        |  +--ro enabled
        |  +--ro oper-status
        |  +--ro counters   ==> COUNTERS_DB:COUNTERS (on_change not supported)
        |  |  +--ro in-octets
```

Here container /interfaces/interface/state/counters maps to COUNTERS_DB and does not support ON_CHANGE.
Other nodes support ON_CHANGE.
Below table lists the gNMI server's behavior for different combinations of subscription modes and paths.

| **Mode**       | **Subscribe Path**                       | **Result** |
|----------------|------------------------------------------|------------|
| TARGET_DEFINED | /interfaces/interface[name=\*]           | SAMPLE for /interfaces/interface[name=\*]/state/counters;<br>ON_CHANGE for other paths |
| TARGET_DEFINED | /interfaces/interface[name=\*]/config    | ON_CHANGE |
| TARGET_DEFINED | /interfaces/interface[name=\*]/state     | SAMPLE for /interfaces/interface[name=\*]/state/counters;<br>ON_CHANGE for other paths |
| TARGET_DEFINED | /interfaces/interface[name=\*]/state/enabled         | ON_CHANGE  |
| TARGET_DEFINED | /interfaces/interface[name=\*]/state/counters        | SAMPLE     |
| ON_CHANGE      | /interfaces/interface[name=\*]           | error (counters does not support ON_CHANGE) |
| ON_CHANGE      | /interfaces/interface[name=\*]/config    | ON_CHANGE |
| ON_CHANGE      | /interfaces/interface[name=\*]/state     | error (counters does not support ON_CHANGE) |
| ON_CHANGE      | /interfaces/interface[name=\*]/state/enabled         | ON_CHANGE  |
| SAMPLE         | /interfaces/interface[name=\*]           | SAMPLE    |
| SAMPLE         | /interfaces/interface[name=\*]/config    | SAMPLE    |
| SAMPLE         | /interfaces/interface[name=\*]/state     | SAMPLE    |

Following sequence diagram describes the overall flow.

![TARGET_DEFINED Subscription Design](images/Subscribe_STREAM.png)

Detailed flow of `Subscribe()` and `Stream()` APIs are not shown for the sake simplicity.
Please refer to previous sections for details.

### 2.11 Handling ONCE

ONCE subscription also uses `Stream()` API, but does not create a YGOT cache.
RPC is closed after sending all updates for the current data.
Following sequence diagram describes the overall flow.

![ONCE Subscription Design](images/Subscribe_ONCE.png)

### 2.12 Handling POLL

POLL subscription is handled similar to ONCE subscription.
Every poll message will use `Stream()` API to notify current data to the client.
There will not be any timer or YGOT cache.

### 2.13 Scalar Encoding

Translib `SubscribeResponse` always returns updated values as a YGOT object.
It can have one or multiple attribute set.
gNMI server will use `ygot.TogNMINotifications()` function to serialize this YGOT object directly into gNMI notification messages having scalar encoded update values.

Both `Subscribe()` and `Stream()` APIs will use app module's `processGet()` function to retrieve YANG data.
Current implementation of `processGet()` always returns YANG data in RFC7951 JSON format.
These will be enhanced to return either RFC7951 or YGOT depending on a *output format* argument.
Default value will be RFC7951 for backward compatibility.
`Subscribe()` and `Stream()` will pass the *output format* as YGOT.

### 2.14 Handling YANG Paths without Module Prefix

### 2.15 Wildcard Keys for Non-DB paths

SAMPLE, POLL and ONCE subscriptions are supported for non-DB data only if the subscribe path
does not contain wildcards.
Translib `Stream()` API current data is through the existing `Get()` flow.
Wildcard paths cannot be passed to these functions due to limitations in the YGOT.

An alterante approach is to extend app module's `processSubscribe()` scope to return all specific paths of a wildcard path.
However this will not be practical for the app modules if non-DB data source does not provide APIs to retrive object keys (equivalent of redis KEYS or SCAN).
There is no standard "non-DB data access" layer in translib today.
Hence the current design does not support wildcard paths for non-DB data.
Future releases can enhance this based on how non-DB data access evolves in translib.

## 3 Design Details

### 3.1 Translib APIs

### 3.2 App Interface

### 3.3 Transformer

### 3.4 gNMI Server

## 4 User Interface

### 4.1 CLIs

No CLIs will be added or modified.

### 4.2 gNOI APIs

#### 4.2.1 GetSubscribePreferences

## 5 Serviceability and Debug

## 6 Scale Considerations

SAMPLE, ON_CHANGE, TARGET_DEFINED are long running subscriptions and they maintain a data cache per session.
Cache size is not deterministic; it depends on number of clients and the subscribed paths.
E.g, If clients subscribe for specific leaf nodes (like `/interfaces/interface[name=*]/state/oper-status`), the cache would hold only that leaf related data (or DB entry in case of ON_CHANGE).
But if clients subscribe for top level YANG containers/lists (like `/interfaces/interface[name=*]`) the cache would hold information for the entire data tree.
This can lead to high memory consumption in telemetry service there were too many subscriptions.
We are considering throttling subscriptions based on the current cache size.
gNMI server can close a subscribe RPC with `RESOURCE_EXHAUSTED` status if the subscription cache exceeds a certain threshold.
This will be implemented in a future release.

Another possible memory optimization is to have a shared OnChange cache for all subscriptions.
However this requires translib to PSUBSCRIBE for all keys.
Every db change will be notified to translib, which will have to check whether any of the subscribe session is interested in that change.
Can result in high CPU consumption in the telemetry service.

CPU consumption can also increase if the DB entries monitored through ON_CHANGE subscriptions change frequently.
E,g. interface counters.
Applications should disable ON_CHANGE for such YANG paths.

## 7 Limitations

- ON_CHANGE can be supported for YANG nodes that are mapped to DB tables only
- Wildcard keys in subscribe paths can be supported for YANG nodes that are mapped to DB tables only
- Subscribe not supported for paths with wildcard element names.
  Only wildcard keys are allowed.
- Cannot produce accurate notification timestamps

## 8 Unit Tests

Following unit test cases require app code changes to handle subscription.
Test YANGs will be used to simulate these conditions.
Each test will cover value create/update/delete cases wherever possible.

ON_CHANGE test cases:

- ON_CHANGE subscription for top level container path
- ON_CHANGE subscription for list node with wildcard key
- ON_CHANGE subscription for list node with specific key
- ON_CHANGE subscription for list node with specific, but non-existing key
- ON_CHANGE subscription for nested list node with wildcard key
- ON_CHANGE subscription for nested list node with specific key
- ON_CHANGE subscription for top level leaf nodes (without any keys)
- ON_CHANGE subscription for container inside a list
- ON_CHANGE subscription for leaf node inside a list, with an initial value
- ON_CHANGE subscription for leaf node inside a list, value does not exits
- ON_CHANGE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- ON_CHANGE subscription for leaf-list node inside a list; with leaf-list mapped to its own DB entry
- ON_CHANGE subscription for an unsupported path - for non-transformer app
- ON_CHANGE subscription for an unsupported path - marked through transformer annotation
- ON_CHANGE subscription for an unsupported path - marked through subtree transformer code
- ON_CHANGE subscription for a non-DB path
- ON_CHANGE subscription with unknown path
- ON_CHANGE subscription with `updates_only` set to true

SAMPLE subscription test cases:

- SAMPLE subscription for top level container path
- SAMPLE subscription for list node with wildcard key
- SAMPLE subscription for list node with specific key
- SAMPLE subscription for nested list node with wildcard key
- SAMPLE subscription for nested list node with specific key
- SAMPLE subscription for top level leaf nodes (without any keys)
- SAMPLE subscription for container inside a list
- SAMPLE subscription for leaf node inside a list
- SAMPLE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- SAMPLE subscription for leaf-list node inside a list; with leaf-list mapped to its own DB entry
- SAMPLE subscription for a non-DB path, with wildcard keys
- SAMPLE subscription for a non-DB path, without wildcard keys
- SAMPLE subscription with unknown path
- SAMPLE subscription with sample_interval less than min interval supported by YANG
- SAMPLE subscription with `suppress_redundant` set to true
- SAMPLE subscription with `updates_only` set to true.
- Both ON_CHANGE and SAMPLE subscriptions in a single request.

TARGET_DEFINED subscription test cases:

- TARGET_DEFINED for a node that prefers ON_CHANGE
- TARGET_DEFINED for a node that prefers SAMPLE -- preference set through transformer annotation
- TARGET_DEFINED for a node that prefers SAMPLE -- preference set through subtree transformer
- TARGET_DEFINED for a node that prefers SAMPLE -- for non-transformer app
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- preference set through transformer annotation
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- preference set through subtree transformer
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- for non-transformer app
- TARGET_DEFINED for non-DB path
- TARGET_DEFINED for unknown path

ONCE subscription test cases:

- ONCE subscription for top level container path
- ONCE subscription for list node with wildcard key
- ONCE subscription for list node with specific key
- ONCE subscription for top level leaf nodes (without any keys)
- ONCE subscription for container inside a list
- ONCE subscription for leaf node inside a list
- ONCE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- ONCE subscription for a non-DB path, with wildcard keys
- ONCE subscription for a non-DB path, without wildcard keys
- ONCE subscription with unknown path

GetSubscribePreferences gNOI API:

- Get preferences for a container path that supports ON_CHANGE and all its subpaths also support ON_CHANGE
- Get preferences for a container path that supports ON_CHANGE but some of its child paths do not
- Get preferences for a path that do not support ON_CHANGE
- Get preferences for a leaf path (with and without ON_CHANGE support)
- Get preferences for multiple paths
- Get preferences with include_subpaths=true
- Get preferences with on_change_supported filter (both TRUE and FALSE)
- Get preferences for a non-db path
- Get preferences without wildcard keys and without module prefixes
- Check error response for an invalid path
- Send request and close the client stream immediately (manual verification of server logs)
- Send request and close the channel immediately (manual verification of server logs)
