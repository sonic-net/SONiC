<!-- omit in toc -->
# BGP Loading Optimization for SONiC

<!-- omit in toc -->
### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | Aug 16 2023 |   FengSheng Yang   | Initial Draft                     |
| 0.2 | Aug 29 2023 |   Yijiao Qin       | Second Draft                      |
| 0.3 | Sep  5 2023 |   Nikhil Kelapure  | Supplement of Async SAI Part      |
| 1.0 | Feb  1 2024 |   Yijiao Qin       | Update test strategy              |

<!-- omit in toc -->
## Table of Contents

- [Goal \& Scope](#goal--scope)
  - [Similar works](#similar-works)
- [Definitions \& Abbreviations](#definitions--abbreviations)
- [Overview](#overview)
  - [Orchagent consumer execute workflow is single-threaded](#orchagent-consumer-execute-workflow-is-single-threaded)
  - [Syncd is too strictly locked](#syncd-is-too-strictly-locked)
  - [Redundant APPL\_DB I/O traffic](#redundant-appl_db-io-traffic)
    - [producerstatetable publishes every command and fpmsyncd flushes on every select event](#producerstatetable-publishes-every-command-and-fpmsyncd-flushes-on-every-select-event)
    - [APPL\_DB does redundant housekeeping](#appl_db-does-redundant-housekeeping)
  - [Slow Routes decode and kernel thread overhead in zebra](#slow-routes-decode-and-kernel-thread-overhead-in-zebra)
  - [Synchronous sairedis API usage](#synchronous-sairedis-api-usage)
- [Requirements](#requirements)
- [High-Level Proposal](#high-level-proposal)
  - [1. Reduce Redis I/O traffic between Fpmsyncd and Orchagent](#1-reduce-redis-io-traffic-between-fpmsyncd-and-orchagent)
    - [1.1 Remove _PUBLISH_  in the lua script](#11-remove-publish--in-the-lua-script)
    - [1.2 Reduce pipeline flush frequency](#12-reduce-pipeline-flush-frequency)
    - [1.3 Discard the state table with prefix \_](#13-discard-the-state-table-with-prefix-_)
  - [2. Add an assistant thread to the monolithic Orchagent/Syncd main event loop workflow](#2-add-an-assistant-thread-to-the-monolithic-orchagentsyncd-main-event-loop-workflow)
  - [3. Asynchronous sairedis API usage](#3-asynchronous-sairedis-api-usage)
    - [New ResponseThread in OA](#new-responsethread-in-oa)
- [Low-Level Implementation](#low-level-implementation)
  - [Fpmsyncd](#fpmsyncd)
  - [Lua scripts](#lua-scripts)
  - [Multi-threaded orchagent with a singleton ring buffer](#multi-threaded-orchagent-with-a-singleton-ring-buffer)
  - [Syncd \[similar optimization to orchagent\]](#syncd-similar-optimization-to-orchagent)
  - [Asynchronous sairedis API usage and new  ResponseThread in orchagent](#asynchronous-sairedis-api-usage-and-new--responsethread-in-orchagent)
- [WarmRestart scenario](#warmrestart-scenario)
- [Testing and measurements](#testing-and-measurements)
  - [Requirements](#requirements-1)
  - [PerformanceTimer](#performancetimer)
  - [Performance measurements with 1M routes](#performance-measurements-with-1m-routes)

## Goal & Scope

This project aims to accelerate the BGP routes end-to-end loading/withdrawing workflow.
  
We analyzed the performance bottleneck for each related submodule and optimized them accordingly.

The table below compares the loading/withdrawing speed of related submodules before and after optimization, tested on the Cisco Silicon One Q200.

<!-- <style>
table{
  margin:auto;
}
</style> -->
| Module                   |  Original Speed(routes/s)    | Optimized Speed (routes/s) |
| ------------------------ | -----------------------------| -----------------------------|
| Zebra / Fpmsyncd         |  <center>17K                 | <center>25.4K                 |
| Orchagent                |  <center>10.5K               | <center>23.5K                 |
| Syncd                    |  <center>10.5K               | <center>19.6K                 |

This HLD only covers the optimization in `fpmsyncd`, `orchagent`, `syncd` and `zebra` and Redis I/O. SAI/ASIC optimaztion is out of the scope.

### Similar works

Recently, JNPR team has raised BGP loading time to 47K routes per second. <https://community.juniper.net/blogs/suneesh-babu/2023/11/20/mx304-fib-install-rate>
This is an excellent achievement and we would kudo JNPR team to raise this racing bar higher. This JNPR's achievement gives us a new aiming point for the next round optimization.

## Definitions & Abbreviations

| Definitions/Abbreviation | Description                             |
| ------------------------ | --------------------------------------- |
| ASIC                     | Application specific integrated circuit |
| BGP                      | Border Gateway Protocol                 |
| SWSS                     | Switch state service                    |
| SYNCD                    | ASIC synchronization service            |
| FPM                      | Forwarding Plane Manager                |
| SAI                      | Switch Abstraction Interface            |

## Overview

SONiC BGP loading/withdrawing workflow is shown in the figure below:
<figure align="center">
    <img src="images/sonic-workflow.png" width="45%" height=auto>
    <figcaption>SONiC BGP loading/withdrawing workflow</figcaption>
</figure>

1. `bgpd` parses the packets received on the socket, notifies `zebra`
2. `zebra` delivers this route to `fpmsyncd`
3. `fpmsyncd` uses redis pipeline to flush routes to `APPL_DB`
4. `orchagent` consumes `APPL_DB`
5. `orchagent` calls `sairedis` APIs to write into `ASIC_DB`
6. `syncd` consumes `ASIC_DB`
7. `syncd` invokes `SAI` SDK APIs to inject routing data to the hardware asic.

**NOTE**: [Linux kernel](https://github.com/SONiC-net/SONiC/wiki/Architecture#routing-state-interactions) part is ignored here.

### Orchagent consumer execute workflow is single-threaded

Let's take the consumer for `ROUTE_TABLE` for example. In Orchagent's event-triggered main loop, Consumer would be selected to run its `execute()` method which contains three steps.

1. `pops()`
    - pop keys from redis `ROUTE_TABLE_KEY_SET`, which stores all modified keys
    - traverse these modified keys, move its corresponding values from temporary table `_ROUTE_TABLE` to `ROUTE_TABLE`
    - delete temporary table `_ROUTE_TABLE`
    - save these modified information, from redis table, to the local variable `std::deque<KeyOpFieldsValuesTuple> entries`
2. `addToSync()`
    - transfer the data from the local variable `entries` to the consumer instance's internal data structure `m_toSync`
3. `drain()`
    - consumes its `m_toSync`, invokes sairedis API and write these modified data to asic_db

We observe that, the 3 tasks do not share the same redis context, hence have potential for parallel. While the order of these three tasks within a single `execute()` job should be maintained, there could have some overlaps among each `execute()` call. For example, when the first `execute()` call enters step 2, the second `execute()` could begin its step 1 instead of waiting for the step 3 of first `execute()` to be finished. To enable this overlapping among `execute()` calls, we can add a thread to orchagent.

<figure align=center>
    <img src="images/orchagent-workflow.png" width="40%" height=auto>
    <figcaption>Orchagent workflow<figcaption>
</figure>  

### Syncd is too strictly locked

`syncd` shares the similar issue with `orchagent`. It also has a single-threaded workflow to pop data from the upstream redis tables, then invoke asic SDK APIs to inject data into its downstream hardware. We also want to explore its potential for parallel, and separate its communication with the upstream redis and the downstream hardware into two threads. However, this workflow needs careful locks since both communication with its upstream and downstream includes using the same redis context. As we can see in the original codebase, the whole `processEvent()` is locked. While SDK API calls tend to be time-consuming, we should unlock the thread to utilize the idle time here when syncd is waiting for the downstream hardware's responses.

<br>

<figure align=center>
    <img src="images/syncd-workflow.jpg" width="40%" height=auto>
    <figcaption>Syncd workflow<figcaption>
</figure>

### Redundant APPL_DB I/O traffic

There is much Redis I/O traffic during the BGP loading process, from which we find two sources of unnecessary traffic.

#### producerstatetable publishes every command and fpmsyncd flushes on every select event

In the original design, SONiC producers use lua scripts to implement its APIs such as set, delete, etc. We observe that, each lua script here ends with a redis `PUBLISH`. However, since we have already uses the pipeline, even if only the last command in the pipeline contains a redis `PUBLISH`, all the information in the pipeline can be published to the subsribed consumers. Hence, we want to decouple the redis `PUBLISH` from the producers' lua scripts and use a single `PUBLISH` command for a single pipeline flush.

In the original design, apart from redis pipeline flushing itself when it's full, `fpmsyncd` also invokes the redis pipeline `flush()` method every time a select event happens. Since the downstream handling of pipeline flushed data is not that fast, we can slow down the flush while batching more data in a single flush. Since each time a pipeline flushes, we transfer data from two modules via network, which includes `syscall` and context switching, and there is also round-trip-time between two modules. By reducing the flush frequency, we save on the overhead per flush.

#### APPL_DB does redundant housekeeping

When `orchagent` consumes `APPL_DB` with `pops()`, `pops` needs to transfer data from  `_ROUTE_TABLE` to  `ROUTE_TABLE`, we propose to let upstream producers directly write into `ROUTE_TABLE`, which saves `pops` from doing these redis write and delete operations.

### Slow Routes decode and kernel thread overhead in zebra

`zebra` receives routes from `bgpd`. To understand the routing data sent by `bgpd`, it has to decode the received data with `zapi_route_decode` function, which consumes the most computing resources, as the flame graph indicates. This function causes the slow start for `zebra`, since decode only happens at the very beginning of receiving new routes from `bgpd`.

The main thread of `zebra` not only needs to send routes to `fpmsyncd`, but also needs to process the returned results of the child thread which indicate whether data are successfully delivered to `kernel`. Hence when `zebra` is busy dealing with the `kernel` side, the performance of talking to `fpmsyncd` would be affected.

<br>

<figure align=center>
    <img src="images/zebra.jpg" width="60%" height=auto>
    <figcaption>Zebra flame graph<figcaption>
</figure>  

### Synchronous sairedis API usage

The interaction between `orchagent` and `syncd` is using synchronous `sairedis` API.
Once `orchagent` `doTask` writes data to ASIC_DB, it waits for response from `syncd`. And since there is only single thread in `orchagent` it cannot process other routing messages until the response is received and processed.

<figure align=center>
    <img src="images/sync-sairedis1.png" width="20%" height=20%>
    <figcaption>Sync sairedis workflow<figcaption>
</figure>

## Requirements

- All modifications should maintain the time sequence of route loading
- All modules should support the warm restart operations after modified
- With the optimization of this HLD implemented, the end-to-end BGP loading performance should be improved at least by 95%
- The new optimization codes would be turn off by default. It could be turned on via configuration

## High-Level Proposal

### 1. Reduce Redis I/O traffic between Fpmsyncd and Orchagent

#### 1.1 Remove _PUBLISH_  in the lua script
>
> Fpmsyncd uses _ProducerStateTable_ to send data out and Orchagent uses _ConsumerStateTable_ to read data in.  
While the producer has APIs associated with lua scripts for Redis operations, each script ends with a _PUBLISH_ command to notify the downstream consumers.

Since we have employed Redis pipeline to queue commands up and flush them in a batch, it's unnecessary to _PUBLISH_ for each command. We can attach a _PUBLISH_ at the end of the command queue when the pipeline flushes, then the whole batch could share this single _PUBLISH_ and we reduce traffic for O(n) _PUBLISH_ to O(1).
<figure align=center>
    <img src="images/BatchPub.png" height=auto>
</figure>  

#### 1.2 Reduce pipeline flush frequency

> Redis pipeline flushes itself when it's full, otherwise it temporarily holds the redis commands in its buffer.  
The commands would not get stuck in the pipeline since Fpmsyncd would also flush the pipeline, and this behavior is event-triggered with _select_ method.

Firstly, we could increase pipeline buffer size from the default 125 to 10k, which would decrease the frequency of the pipeline flushing itself.  
Secondly, we could skip Fpmsyncd flushes when it's not that long since the last flush and set a _flush timeout_ to determine the threshold.  
To avoid commands lingering in the pipeline due to skip, we change the _select timeout_ of Fpmsyncd from _infinity_ to _flush timeout_ after a successful skip to make sure that these commands are eventually flushed. And after flushing the lingered commands, the _select timeout_ of Fpmsyncd would change back to _infinity_ again.  
To make sure that consumers are able to get all the modified data when the number of _PUBLISH_ is equal to the number of flushes, while still keep the consumer pop size as 125, consumer needs to do multiple pops for a single _PUBLISH_.  
If there is a batch of fewer than 10 routes coming to the pipeline, they would be directly flushed, in case they are important routes.

#### 1.3 Discard the state table with prefix _
>
> Pipeline flushes data into the state table and use the data structure _KeySet_ to mark modified keys.  
When Orchagent is notified of new data coming, it recognized modified keys by _KeySet_, then transfers data from the state table to the stable table, then deletes the state table.

We propose to discard state tables, directly flush data to stable tables, while keep the data structure _KeySet_ to track modified keys.

### 2. Add an assistant thread to the monolithic Orchagent/Syncd main event loop workflow

Take Orchagent for example, there is a while loop in OrchDaemon monitoring events and selecting corresponding consumers.  
Once a consumer gets selected, it calls its execute() method, which consists of three steps, _pops(entries)_ , _addToSync_(entries) and _drain()_.

```c++
void Consumer::execute() 
{
    std::deque<KeyOpFieldsValuesTuple> entries;
    getConsumerTable()->pops(entries);
    addToSync(entries);
    drain();
}
```

When _pops(entries)_ finishes, even if there are already new data ready to be read, the second _pops(entries)_ is blocked until the first _addToSync_(entries) and _drain()_ finish.

<figure align=center>
    <img src="images/execute.png">
</figure>  

The proposed design decouples _pops(entries)_ from _addToSync_(entries) and _drain()_. In our proposal,  _addToSync_(entries) and _drain()_ are removed from execute(), hence execute() is now more lightweight. While it only needs to pop entries from Redis table and push them into the ring buffer, we assign a new thread _rb_thread_ dedicating to pop data out of the ring buffer and then _addToSync_(entries) and _drain()_.

<figure align=center>
    <img src="images/decouple.png">
</figure>  

For Syncd, we also need to decouple _consumer.pop(kco, isInitViewMode())_ from _processSingleEvent(kco)_.

### 3. Asynchronous sairedis API usage

Asynchronous mode `sairedis` API is used and a list of context of response pending messages is maintained on `orchagent` to process the response when its received

<figure align=center>
    <img src="images/async-sairedis2.png" width="20%" height=20%>
    <figcaption>Figure: Async sairedis workflow<figcaption>
</figure>

#### New ResponseThread in OA

A new `ResponseThread` is used in `orchagent` to process the response when its received so that the other threads can continue processing new routing messages

## Low-Level Implementation

### Fpmsyncd

Redis Pipeline would flush itself when it's full, to save TCP traffic, we choose _10000_ despite the default 125 as the pipeline size.

```c++
#define FPMSYNCD_PIPELINE_SIZE 10000
#define FLUSH_TIMEOUT 200
#define BLOCKING -1

RedisPipeline pipeline(&db, FPMSYNCD_PIPELINE_SIZE);

/**
 * @brief fpmsyncd's flush logic
 * 
 * Although ppl flushes itself when it's full, fpmsyncd also flushes it in some cases.
 * This function decides fpmsyncd's flush logic and returns whether it's skipped.
 * 
 * @param pipeline Pointer to the pipeline to be flushed.
 * @param interval The expected interval between each flush.
 * @param force if true, flush is guaranted
 * @return true only if this flush is skipped when pipeline is non-empty
 */
bool flushPPLine(RedisPipeline* pipeline, int interval, bool forced=false);

int select_timeout = BLOCKING;
while (true)
{
    Selectable *temps;
    auto ret = s.select(&temps, select_timeout);
    ....
    if (select_timeout == FLUSH_TIMEOUT && ret==Select::TIMEOUT) {
        flushPPLine(&pipeline, FLUSH_TIMEOUT, true);
        select_timeout = BLOCKING;
    } else if (flushPPLine(&pipeline, FLUSH_TIMEOUT)) {
        select_timeout = FLUSH_TIMEOUT;
    }
}

```

### Lua scripts
<!-- omit in toc -->
#### sonic-swss-common/common/producerstatetable.cpp

Take _luaSet_ for example

```c++
local added = redis.call('SADD', KEYS[2], ARGV[2])  
for i = 0, #KEYS - 3 do  
    redis.call('HSET', KEYS[3 + i], ARGV[3 + i * 2], ARGV[4 + i * 2])  
end  
if added > 0 then  
    redis.call('PUBLISH', KEYS[1], ARGV[1])  
end
```

changed to

```lua
local added = redis.call('SADD', KEYS[2], ARGV[2])
for i = 0, #KEYS - 3 do
    redis.call('HSET', KEYS[3 + i], ARGV[3 + i * 2], ARGV[4 + i * 2])
end
```

<!-- omit in toc -->
#### sonic-swss-common/common/consumer_state_table_pops.lua

```lua
redis.replicate_commands()
local ret = {}
local tablename = KEYS[2]
local keys = redis.call('SPOP', KEYS[1], ARGV[1])

if keys and #keys > 0 then
    local n = #keys
    for i = 1, n do
        local key = keys[i]
        local fieldvalues = redis.call('HGETALL', tablename..key)
        table.insert(ret, {key, fieldvalues})
        end
    end
end

return ret
```


### Multi-threaded orchagent with a singleton ring buffer

OrchDaemon initializes the global ring buffer, _gRingBuffer_ and passes its pointer to both _Orch_ and _Consumer_ as a Class static variable, so that the ring is unique in Orchagent.

```c++
class Consumer2;
typedef std::pair<Consumer2*, swss::KeyOpFieldsValuesTuple> EntryType;
typedef RingBuffer<EntryType> OrchRing;
OrchRing* OrchDaemon::gRingBuffer = OrchRing::Get();

bool OrchDaemon::init()
{
    ...
    Consumer2::gRingBuffer = gRingBuffer;
    Orch::gRingBuffer = gRingBuffer;
}
```

- When OrchDaemon starts, it kicks off a new thread _rb_thread_.
- The main thread still calls Consumer _execute()_ method.
- But _execute()_ now only includes _pops(entries)_ and _addToRing(entries)_, which means reading data from Redis APP_DB and inserting them into the ring buffer.
- The ring buffer thread `rb_thread` executes _popRingBuffer()_ method, which keeps poping the ring and calls _addToSync(entries)_ and _drain()_ for entries popped from the ring.

We implemented a C++ class `Consumer2`, derived from `Consumer`, inheriting all its functions but overrides _execute()_.

```c++
void Consumer2::execute()
{
    std::deque<KeyOpFieldsValuesTuple> entries;
    while (true) {
        getConsumerTable()->pops(entries);
        if (entries.size() == 0)
            break;
        addToRing(entries);
    }
}

void OrchDaemon::popRingBuffer()
{
    ...
    Consumer2* consumer2 = gRingBuffer->HeadEntry().first;
    std::deque<swss::KeyOpFieldsValuesTuple> entries;
    EntryType entry;
    /* Entries in the buffer may belong to different consumers, hence stop when the next entry belongs to other consumers. */
    while (gRingBuffer->IsEmpty() == false && gRingBuffer->HeadEntry().first == consumer2 && gRingBuffer->pop(entry))
    {
        entries.emplace_back(entry.second);
    }
    consumer2->addToSync(entries);
    consumer2->drain();
    ...
}

void OrchDaemon::start()
{
    rb_thread = std::thread(&OrchDaemon::popRingBuffer, this);
}
```

### Syncd [similar optimization to orchagent]

Similar case for syncd with orchagent. In our proposal, consumer.pop and processSingleEvent(kco) is decoupled.

### Asynchronous sairedis API usage and new  ResponseThread in orchagent

`orchagent` now uses synchronous `sairedis` API to send message to `syncd`

**Orchagent**

- RouteOrch sends bulk route add/update/del message as usual
- For each bulk message sent, list of {prefix, Vrf} is preserved in a AckBuffer.
- AckBuffer is added to pending-ACK queue
- AckBuffer has prefixes in the same order as in the bulk message
- OA can push at max N outstanding bulk messages to SAIRedis without waiting for ACK
- Once pending-queue size reaches N, routes are held in m_toSync.
- The CRM Used count will be incremented for each route processed by RouteOrch

**Syncd**

- Processes route bulk message one by one as usual
- Makes bulk SAI api call for each bulk-route message
- SAI api returns bulk status with ack/nack for each prefix
- Response is sent back to OA using NotificationProducer.

**ResponseThread**
New pthread in orchagent

- Tasks performed
  - Listen to bulk-ack messages from syncd using NotificationConsumer
  - Match bulk-ack with bulk-route request message
  
- Shared data-structures protected using mutex
  - Pending-ACK queue
  
- On each mutex lock
  - Pending queue with bulk-route entries is moved to the ResponseThread context.
  - New queue is initialized for main thread to add new entries
  
- ACK/NACK are processed in parallel to orchagent main thread
  - ACK/NACK are added to APP_STATE_DB
  - For NACK case the CRM ERR count will be incremented
  
- CRM resources is calculated by subtracting ERR count from Used count in CRM

  <figure align=center>
      <img src="images/async-sairedis3.png" width="50%" height=auto>
      <figcaption>Async sairedis workflow<figcaption>
  </figure>


## WarmRestart scenario

This proposal considers the compatibility with SONiC `WarmRestart` feature. For example, when a user updates the config, a warm restart may be needed for the config update to be reflected. SONiC's main thread would call `dumpPendingTasks()` function to save the current system states and restore the states after the warm restart. Since this HLD introduces a new thread and a new structure `ring buffer` which stores some data, then we have to ensure that the data in `ring buffer` all gets processed before warm restart. During warm start, the main thread would modify the variable `m_toSync`, which the new thread also have access to. Therefore we should block the new thread during warm restart to avoid conflict.

Take orchagent for example, we need to make sure ring buffer is empty and the ring buffer thread is in idle before we call ```dumpPendingTasks()```.

## Testing and measurements

### Requirements

- All modules should maintain the time sequence of route loading.
- All modules should support WarmRestart.
- No routes should remain in redis pipeline longer than configured interval.
- No data should remain in ring buffer when system finishes routing loading.
- System should be able to install/remove/set routes (faster than before).

### PerformanceTimer
We implemented c++ class PerformanceTimer in swsscommon library sonic-swss-common/common, this timer helps us measure the performance of a specific function or a module, it outputs interval(milliseconds) between each call, the execution time for a single call and how much entries this single call handles in the following format:

`[interval]<num_of_handled_entries>execution_time`.

Here is an example extracted from syslog:
```c++
NOTICE syncd#syncd: inc:88: 10000 (calls 5 : [13ms]<4315>102ms [10ms]<2635>64ms [7ms]<1577>52ms [3ms]<933>20ms [1ms]<540>22ms) Syncd::processBulkCreateEntry(route_entry) CREATE op took: 262 ms
```
We have a timer that measures performance of `processBulkCreateEntry(route_entry)` method, it takes 5 calls to create 10000 entries.

1st call created 4315 entries in 102 ms, started 13 ms after last call ends\
2nd call created 2635 entries in 64 ms, started 10 ms after last call ends\
3rd call created 1577 entries in 52 ms, started 7 ms after last call ends\
4th call created 933 entries in 20 ms, started 3 ms after last call ends\
5th call created 540 entries in 22 ms, started 1 ms after last call ends

Our optimization aims to reduce the interval (idle time) and improve the overall throughput.

### Performance measurements with 1M routes
