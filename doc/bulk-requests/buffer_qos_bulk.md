# Bulk Qos/Buffer Requests in SWSS #

## Table of Content 

[Table of Content](#table-of-content)
* [Revision](#revision)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitionsabbreviations)
* [Overview](#overview)
* [Requirements](#requirements)
* [High-Level Design](#high-level-design)
  + [Preparation](#preparation)
    + [Define bulk API in bulker.h](#define-bulk-api-in-bulkerh)
    + [Enable bulk API](#enable-bulk-api)
  + [Execution](#execution)
  + [BufferOrch](#bufferorch)
  + [QosOrch](#qosorch)
    + [Scheduler Bulk Request Handler](#scheduler-bulk-request-handler)
    + [Port QoS Map Bulk Request Handler](#port-qos-map-bulk-request-handler)
    + [Queue Bulk Request Handler](#queue-bulk-request-handler)
* [SAI API](#sai-api)
* [Configuration and management](#configuration-and-management)
* [Config DB Enhancements](#config-db-enhancements)
* [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
* [Restrictions/Limitations](#restrictions-limitations)
* [Testing Requirements/Design](#testing-requirements-design)
  + [Unit Test](#unit-test)
  + [System Test Cases](#system-test-cases)
* [Open/Action items - if any](#open-action-items---if-any)

### Revision  
Rev  | Rev Date  | Author(s)                | Change Description
---- | --------- | ------------------------ | ------------------
v0.1 | 6/21/2024 | Yilan Ji | Initial version

### Scope  

This documents describes the high-level design of aggregating buffer ans qos APPL/CONFIG DB requests to use bulk SAI API in bufferorch and qosorch for performance improvement on configuration convergence time. 

### Definitions/Abbreviations

N/A

### Overview 

As part of the performance optimization during config push, QoS and Buffer config requests can be bulked to reduce overall number of SAI calls. The goal of this doc is to analyze the capability and efficiency of bulking QoS and Buffer requests in SWSS by reducing the overall SAI calls using bulk SAI APIs. 

### Requirements

SWSS uses bufferorch and qosorch to handle Qos/Buffer requests in APPL/CONFIG DB. Currently, qosorch handles qos maps and their application on ports, wred profiles/schedulers and their applications on queues/priority groups/scheduler groups, bufferorch handles buffer pools, profiles and their application on buffer queues/priority groups or ports.  

For some configurations, Qos/BufferOrchs can iterate through queues, priority groups, scheduler groups and ports at magnitudes of 10 or 100, calling the same SAI API. As experiments using the SAI bulk API on Broadcom show, bulking these SAI calls can potentially reduce 67% of SAI calls times.

To enabling the SAI bulk API for qos/buffer requests in SWSS, it has requirements and restrictions:

* SAI bulk API availability. e.g.  `sai_port_api` supports `create_ports`, `remove_ports`, etc.
* The max number of SAI API calls that can be bulked will be impacted by the order of CONFIG DB entries in different tables and consumer batch size(1024). 
* The max number of SAI API calls that should be bulked is to be determined. The SAI bulk API call is blocking, the allowed max blocking call duration is 100ms(TBD).
* Backward compatibility is needed to give option to fall back to individual SAI calls for SONiC community adaption.
* Buffer/Qos requests allow retries.

### High-Level Design

#### Preparation
##### Define bulk API in bulker.h
Below SAI bulk APIs are required. 
```
sai_port_api->set_ports_attribute() - (API is available)
sai_port_api->get_ports_attribute() - (API is available)
sai_queue_api->set_queues_attribute() - (API is WIP)
sai_scheduler_group_api->set_scheduler_groups_attribute() - (API is WIP)
sai_scheduler_group_api->get_scheduler_groups_attribute() - (API is WIP)
sai_scheduler_api->create_schedulers() - (API is WIP)
sai_scheduler_api->set_schedulers_attribute() - (API is WIP)
sai_scheduler_api->remove_schedulers() - (API is WIP)
```
The wrapped EntityBulker will be defined in the `builker.h`
```
template <>
inline EntityBulker<sai_queue_api>::EntityBulker(sai_queue_api *api, size_t max_bulk_size) :
    max_bulk_size(max_bulk_size)
{
    set_entries_attribute = api->set_queues_attribute;
}


template <>
inline EntityBulker<sai_scheduler_group_api>::EntityBulker(sai_scheduler_group_api *api, size_t max_bulk_size) :
    max_bulk_size(max_bulk_size)
{
    set_entries_attribute = api->set_scheduler_groups_attribute;
    get_entries_attribute = api->get_scheduler_groups_attribute;
}

template <>
inline EntityBulker<sai_scheduler_api>::EntityBulker(sai_scheduler_api *api, size_t max_bulk_size) :
    max_bulk_size(max_bulk_size)
{
    set_entries_attribute = api->set_schedulers_attribute;
    create_entries = api->create_schedulers;
    remove_entries = api->remove_schedulers;
}

template <>
inline EntityBulker<sai_port_api>::EntityBulker(sai_port_api *api, size_t max_bulk_size) :
    max_bulk_size(max_bulk_size)
{
    set_entries_attribute = api->set_ports_attribute;
    get_entries_entries = api->get_ports_attribute;
}
```

##### Enable bulk API
To enable the bulk processing of Buffer and QoS requests, a knob in `rules/config` can be defined. It will be passed as an environment parameter in docker-orchagent Dockerfile and be used as parameter upon starting swss in orchagent.sh. QosOrch/BufferOrch will be initialized with EntityBulker APIs defined in builker.h. When bulk API is enabled, queuing SAI requests in EntityBulker(e.g.`gQueueBuilker`), otherwise execute individual SAI request.This approach ensures backward compatibility, thus avoiding disruptive changes across various platforms and hardware.

```
# rules/config
# BULK_API_QOS - flag to enable/disable SAI bulk API in qosorch
BULK_API_QOS = y
# BULK_API_BUFFER - flag to enable/disable SAI bulk API in bufferorch
BULK_API_BUFFER = y
```


The bulk handlers aggregate SAI requests calling the same API. During `doTask()` execution, multiple requests are grouped together in `consumer.m_toSync`.  for the same APPL/CONFIG DB table.

#### Execution

The processing of aggregated APPL/CONFIG DB requests involves several stages:

![Bulk QoS/Buffer Requests Diagram](./Bulk%20QoS_Buffer%20Requests.png)

* **Prerequisites Checks**:
    * Iterate through each request and verify prerequisites, such as dependency object creation and port readiness.
    * Record need_retry or failure task status if a prerequisite is not met.
    * Otherwise, prepare the cache required for post-SAI call processing and organize SAI attribute lists based on SAI object and operation type, including `remove_<object>s`, `set_<object>s_attribute`, and `create_<object>s`.
* **Bulk SAI Call Execution**:
    * `m_toSync` is a multimap where the same entry key can have one or two entries (SET or DEL only) or (DEL then SET)[[code](https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orch.cpp#L63-L144)]. DEL requests' SAI attribute lists (typically `remove_<object>s`) are processed before SET requests (`create_<object>s` or `set_<object>s_attributes`) to maintain logical order.
    * SAI bulk operations are processed in `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` mode, as requests are orthogonal, and retries are permitted for Buffer/QoS requests.
    * SAI call statuses are mapped to task status lists. If an APPL/CONFIG DB request has multiple SAI call requests, the first failure task status is recorded to maintain consistency with non-bulking request handlers.
* **Cache Management and Post SAI Call Process**:
    * Update the software cache state based on bulk SAI calls responses.
    * Process other orchagent callback requests (e.g., Pfc watchdog state) and return a list of task statuses.
* **Handle Task Statuses**:
    * For requests requiring retries, queue them in a temporary `m_bulkRetryEntries`, clear `consumer.m_toSync`, and add the retry entries back to m_toSync.
    * Otherwise, write task status to APPL STATE DB and publish notifications.

#### BufferOrch

Add a knob in CONFIG DB or as argument when starting swss in orchagent.sh as the initial flag to enable bulk calls by default.

Considering the number of buffer pool and buffer profiles created is usually O(1). Bulk API usage rarely improves performance and may even introduce overheads. Therefore, we will enable bulk API support when setting buffer queues and priority groups to gain more performance optimization.

DB request example:
```
//swss.rec
BUFFER_QUEUE_TABLE:Ethernet1/21/1:0|SET|profile:staggered_8queue.default_egress.0.d1

//sairedis.rec
s|SAI_OBJECT_TYPE_QUEUE:oid:0x15000000000055|SAI_QUEUE_ATTR_BUFFER_PROFILE_ID=oid:0x1900000000089b
```

**Process Steps**
When bulk API is enabled, drain m_toSync requests for buffer queues using SAI bulk API:

* Prerequisite Checks:
    * Verify if ports are ready, unlocked, and buffer profiles exist.
    * Add task failure status to the statuses list if a retry is necessary or invalid arguments are given.
* SAI Call Analysis:
    * Determine if a SAI call is required. If yes, save the index of the APPL DB request in the m_toSync queue and push it to the sai_attrs list during preparation.
    * For DEL requests on the BUFFER_QUEUE table, set the `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` attribute to NULL oid.
    * Since the order of requests for the same table key is guaranteed in m_toSync, all buffer queue requests can be saved to a single SAI attribute list for the set_queues_attribute SAI call.
* SAI Call Invocation:
    * Trigger the `sai_queue_api->set_queues_attribute()` call in `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` mode.
    * Add SAI statuses back to the task statuses list by APPL DB request indexes.
    * For APPL DB requests with multiple SAI calls, set the first error SAI status as the APPL DB request task status in the task statuses list.
* Cache Updates:
    * Update buffer queue to profile mapping and buffer profile object references in the cache m_buffer_type_maps.
    * Process buffer queue counters based on SAI statuses and request type (del or set).
* Cleanup:
    * Clear `m_toSync` requests for buffer queues.
    * Backfill `m_toSync` with `m_bulkRetryEntries`.

#### QosOrch

To enable bulk calls by default, add a knob in the CONFIG DB or as an argument when starting swss in orchagent.sh as the initial flag.
The total number of QoS maps and WRED objects created is usually O(1). Using bulk API rarely improves performance and may even worsen it due to overheads. Therefore, we will support bulk API only when the following CONFIG DB table requests are made:

- `SCHEDULER|<key>`
- `QUEUE|<queue>`
- `PORT_QOS_MAP|<port>`

During QosOrch initialization, initialize the CONFIG DB table name to the bulk requests handler.

```
void QosOrch::initBulkTableHandlers()
{
    SWSS_LOG_ENTER();
    m_qos_bulk_handler_map.insert(qos_bulk_handler_pair(CFG_SCHEDULER_TABLE_NAME, &QosOrch::handleSchedulers));
    m_qos_bulk_handler_map.insert(qos_bulk_handler_pair(CFG_QUEUE_TABLE_NAME, &QosOrch::handleQueues));
    m_qos_bulk_handler_map.insert(qos_bulk_handler_pair(CFG_PORT_QOS_MAP_TABLE_NAME, &QosOrch::handlePortQosMaps));
}
```

When the bulk knob is enabled, drain m_toSync requests for the specified tables. Pass a list of requests for the same table with similar operations to the bulk request handler. Based on the task status list returned by the bulk request handler, manage the status for each type:

- For need_retry status, maintain a m_bulkRetryEntries queue to add back to consumer.m_toSync after the bulk process.
- For other statuses, record the status in the APPL STATE DB and publish a notification.


##### Scheduler Bulk Request Handler

DB request examples:
```
// swss.rec
SCHEDULER|cpu_scheduler1|SET|cbs:0|cir:0|id:CPU_QUEUE_1|input-type:QUEUE|meter_type:packets|pbs:4|pir:120|queue:CPU_QUEUE_1|type:STRICT

// sairedis.rec
c|SAI_OBJECT_TYPE_SCHEDULER:oid:0x1600000000091a|SAI_SCHEDULER_ATTR_METER_TYPE=SAI_METER_TYPE_PACKETS|SAI_SCHEDULER_ATTR_SCHEDULING_TYPE=SAI_SCHEDULING_TYPE_STRICT|SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE=0|SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE=120|SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_BURST_RATE=0|SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_BURST_RATE=4|SAI_SCHEDULER_ATTR_LABEL=1712253732226525
```
`SCHEDULER` table operations allow creation, modification, and deletion of scheduler objects. When sending multiple requests, it's important to indicate whether SET requests are for creating or updating.
As detailed in the High-Level Design session, step 2 specifies that DEL requests should be handled before SET requests. For SET requests, create and set SAI bulk calls can be made in any order. This is because the SET request will be merged into a single SET operation in consumer.m_toSync when creating or updating the same table entry. Therefore, the processing order of SET requests in the queue is not crucial.

**Process Steps**
- Check if prerequisites are met or not. If not add retry or failure status in task statuses list, otherwise prepare SAI attributes lists.
- Check the type of SAI call: create scheduler objects, set scheduler attributes or remove scheduler objects. Group the SAI calls by type and save the index of entry and push it to the sai_attrs list per type during preparation.
- Trigger `sai_scheduler_api->set_schedulers_attribute()` OR  `sai_scheduler_api->create_schedulers()`  OR  `sai_scheduler_api->remove_schedulers()` call by type in `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR mode`, save SAI status list by type.
- Map sai statuses back to task statuses list by CONFIG DB request  indexes.
- If SAI call succeeds, process scheduler labels based on sai statuses for create and remove requests, update scheduler name to oid mapping in cache `m_qos_maps`.

##### Port QoS Map Bulk Request Handler

DB request examples:
```
// swss.rec
PORT_QOS_MAP|Ethernet1|SET|dscp_to_tc_map:dscp_classifier_1|tc_to_uc_mc_queue_map:tc_to_uc_mc_queue_map_1

// sairedis.rec
s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000053|SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP=oid:0x14000000000918
s|SAI_OBJECT_TYPE_PORT:oid:0x1000000000053|SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP=oid:0x14000000000973
```

**Process Steps**
- Check if prerequisites are met or not. If not add retry or failure status in task statuses list, otherwise prepare SAI attributes lists.
- DEL request on `PORT_QOS_MAP` table is to set a list of SAI_PORT attributes in `qos_to_attr_map` to NULL oid. And the order of request for the same table key is guaranteed in m_toSync, all port qos map requests can be saved to the single SAI attribute list for `set_ports_attributes` SAI call. Extra information for SET or DEL requests are saved to be processed after SAI bulk call.
- Trigger `sai_port_api->set_ports_attribute()` in `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` mode, save SAI status list. Map sai statuses back to task statuses list by CONFIG DB request  indexes.
- Update port to qos map mapping in cache m_qos_maps based on sai statuses and request type(del or set). Update port pfc watchdog status.



##### Queue Bulk Request Handler

DB request examples:
```
// Front panel ports in swss.rec
QUEUE|Ethernet1|7|SET|scheduler:scheduler_1|wred_profile:wred_profile_1

// sairedis.rec
// Get the number of scheduler_group for the port
g|SAI_OBJECT_TYPE_PORT:oid:0x1000000000002|SAI_PORT_ATTR_QOS_NUMBER_OF_SCHEDULER_GROUPS=254962432
G|SAI_STATUS_SUCCESS|SAI_PORT_ATTR_QOS_NUMBER_OF_SCHEDULER_GROUPS=13

// Get the parent scheduler group oid for the port given previous queries number.
g|SAI_OBJECT_TYPE_PORT:oid:0x1000000000002|SAI_PORT_ATTR_QOS_SCHEDULER_GROUP_LIST=13:oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0
G|SAI_STATUS_SUCCESS|SAI_PORT_ATTR_QOS_SCHEDULER_GROUP_LIST=13:oid:0x17000000000090,...

// Get the scheduler group child count given previous queried parent scheduler group oid.
g|SAI_OBJECT_TYPE_SCHEDULER_GROUP:oid:0x17000000000090|SAI_SCHEDULER_GROUP_ATTR_CHILD_COUNT=13
G|SAI_STATUS_SUCCESS|SAI_SCHEDULER_GROUP_ATTR_CHILD_COUNT=12

// Get the scheduler group child oids given previous queried child group count. 
g|SAI_OBJECT_TYPE_SCHEDULER_GROUP:oid:0x17000000000090|SAI_SCHEDULER_GROUP_ATTR_CHILD_LIST=12:oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0,oid:0x0
G|SAI_STATUS_SUCCESS|SAI_SCHEDULER_GROUP_ATTR_CHILD_LIST=12:oid:0x170000000000e3,...

// Get the queue id by previous queried scheduler group oids and requested queue index. g|SAI_OBJECT_TYPE_SCHEDULER_GROUP:oid:0x170000000000e3|SAI_SCHEDULER_GROUP_ATTR_CHILD_COUNT=12
G|SAI_STATUS_SUCCESS|SAI_SCHEDULER_GROUP_ATTR_CHILD_COUNT=1
g|SAI_OBJECT_TYPE_SCHEDULER_GROUP:oid:0x170000000000e3|SAI_SCHEDULER_GROUP_ATTR_CHILD_LIST=1:oid:0x0
G|SAI_STATUS_SUCCESS|SAI_SCHEDULER_GROUP_ATTR_CHILD_LIST=1:oid:0x150000000000db

// Apply scheduler to the scheduler group oid and apply wred profile to queue oid. 
s|SAI_OBJECT_TYPE_SCHEDULER_GROUP:oid:0x170000000000e3|SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID=oid:0x16000000000962
s|SAI_OBJECT_TYPE_QUEUE:oid:0x150000000000db|SAI_QUEUE_ATTR_WRED_PROFILE_ID=oid:0x13000000000974
```

QUEUE table contains scheduler and wred profile configuration for scheduler groups on ports. 
When applying config to scheduler groups, the scheduler group oids need to be queried by steps:
- Query total number of scheduler groups per port.
- Query parent scheduler group oid given total number.
- Query total number of child scheduler groups given parent group oid.
- Query child scheduler group oids given total number.
- Query total number of  queues given child group oid.
- Query queue oids given total number.
- Apply scheduler profile to scheduler group oid given child group oid and queue index in CONFIG DB request.
- Apply wred profile to queue oid.

The above SAI calls have dependencies, thus the bulk SAI calls need to be done by steps as well. The scheduler group oids are saved to cache m_scheduler_group_port_info after query. Currently QosOrch only query and cache scheduler group info when scheduler group configuration request comes in CONFIG DB.

**Process Steps**
- Check if prerequisites are met or not: ports readiness and are unlocked, wred profiles and schedulers creation. If not add retry or failure status in task statuses list, otherwise prepare SAI attributes lists.
- DEL request on `QUEUE` table is to set a list of SAI_SCHEDULER_GROUP/SAI_QUEUE attributes to NULL oid. Thus the requests can be queued together for bulk SAI calls. For scheduler group knob type, bulk SAI calls to query port attributes and scheduler groups in order and save the scheduler groups per group in cache. Then trigger `sai_scheduler_group_api->set_scheduler_groups_attribute()` and  `sai_queue_api->set_queues_attribute()` in `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` mode, save SAI status list per type.
- Add sai statuses back to task statuses list by need sai call entry indexes.
- Update queue to scheduler/wred profile mapping in cache `m_qos_maps` for create and remove requests.

### SAI API 

```
sai_queue_api->set_queues_attribute() 
sai_scheduler_group_api->set_scheduler_groups_attribute()
sai_scheduler_group_api->get_scheduler_groups_attribute() 
sai_scheduler_api->create_schedulers()
sai_port_api->set_ports_attribute()
sai_port_api->get_ports_attribute()
sai_scheduler_api->set_schedulers_attribute() 
sai_scheduler_api->create_schedulers()
sai_scheduler_api->remove_schedulers()
```

### Configuration and management 

N/A

### Config DB Enhancements  

A knob will be added in CONFIG DB to enable bulk requests feature by DB table.

```
# CONFIG DB knob
BULK_API_FEATURE:
  BUFFER_QUEUE:enabled
  SCHEDULER:enabled
  PORT_QOS_MAP:enabled
  QUEUE:enabled
```

### Warmboot and Fastboot Design Impact

N/A

### Restrictions/Limitations

The support is restricted by SAI bulk API support and vender implementation.

### Testing Requirements/Design  

TBA

#### Unit Test cases  

TBA

#### System Test cases

TBA

### Open/Action items - if any 

TBA