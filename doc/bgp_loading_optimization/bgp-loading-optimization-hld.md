<!-- omit in toc -->
# BGP Loading Optimization for SONiC

<!-- omit in toc -->
### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | Aug 16 2023 |   FengSheng Yang   | Initial Draft                     |
| 0.2 | Aug 29 2023 |   Yijiao Qin       | Second Draft                      |
| 0.3 | Sept 5 2023 |   Nikhil Kelapure  | Supplement of Async SAI Part      |

<!-- omit in toc -->
## Table of Contents
- [Goal \& Scope](#goal--scope)
- [Definitions \& Abbreviations](#definitions--abbreviations)
- [Bottleneck Analysis](#bottleneck-analysis)
  - [Problem overview](#problem-overview)
  - [Single-threaded orchagent](#single-threaded-orchagent)
  - [Single-threaded syncd](#single-threaded-syncd)
  - [Redundant APPL\_DB I/O traffic](#redundant-appl_db-io-traffic)
    - [fpmsyncd flushes on every incoming route](#fpmsyncd-flushes-on-every-incoming-route)
    - [APPL\_DB does redundant housekeeping](#appl_db-does-redundant-housekeeping)
  - [Slow Routes decode and kernel thread overhead in zebra](#slow-routes-decode-and-kernel-thread-overhead-in-zebra)
  - [Synchronous sairedis API usage](#synchronous-sairedis-api-usage)
- [Requirements](#requirements)
- [High-Level Proposal](#high-level-proposal)
  - [Modification in orchagent/syncd to enable multi-threading](#modification-in-orchagentsyncd-to-enable-multi-threading)
    - [Ring buffer for low-cost thread coordination](#ring-buffer-for-low-cost-thread-coordination)
    - [Asynchronous sairedis API usage](#asynchronous-sairedis-api-usage)
    - [New ResponseThread in OA](#new-responsethread-in-oa)
  - [Streamlining Redis I/O](#streamlining-redis-io)
    - [Lower frequency of the fpmsyncd flush \& APPL\_DB publish](#lower-frequency-of-the-fpmsyncd-flush--appl_db-publish)
    - [Disable the temporary table mechanism in APPL\_DB](#disable-the-temporary-table-mechanism-in-appl_db)
- [Low-Level Implementation](#low-level-implementation)
  - [Multi-threaded orchagent with a ring buffer](#multi-threaded-orchagent-with-a-ring-buffer)
  - [Syncd \[similar optimization to orchagent\]](#syncd-similar-optimization-to-orchagent)
  - [Asynchronous sairedis API usage and new  ResponseThread in orchagent](#asynchronous-sairedis-api-usage-and-new--responsethread-in-orchagent)
  - [Fpmsyncd](#fpmsyncd)
  - [APPL\_DB](#appl_db)
- [WarmRestart scenario](#warmrestart-scenario)
- [Testing Requirements/Design](#testing-requirementsdesign)
  - [System test](#system-test)
  - [Performance measurements when loading 500k routes](#performance-measurements-when-loading-500k-routes)

## Goal & Scope
The goal of this project is to significantly increase the end-to-end BGP loading speed of SONiC
  - from 10k routes per sec to 20K routes per sec
  
To achieve this, we analyzed factors that may slow down each related module and optimized them accordingly, which would be elaborated in this HLD. The table below compares the loading speed of the interested modules before and after optimization, tested on the Cisco Silicon One Q200 platform. The bottleneck has been lying in `orchagent` and `syncd`, which makes the overal optimized BGP loading speed be around 20k/s. 

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


The scope of this document only covers the performance optimization in `fpmsyncd`, `orchagent`, `syncd` and `zebra` and Redis I/O.
We also observed performance bottleneck in `libsai`, but SAI/ASIC optimaztion is out of our scope since it varies by hardware.

<figure align=center>
    <img src="images/performance.png" >
    <figcaption>Figure 1. The module performance on Alibaba's platform loading 500k routes after optimization <figcaption>
</figure>  

## Definitions & Abbreviations

| Definitions/Abbreviation | Description                             |
| ------------------------ | --------------------------------------- |
| ASIC                     | Application specific integrated circuit |
| BGP                      | Border Gateway Protocol                 |
| SWSS                     | Switch state service                    |
| SYNCD                    | ASIC synchronization service            |
| FPM                      | Forwarding Plane Manager                |
| SAI                      | Switch Abstraction Interface            |
| HW                       | Hardware                                |
| SW                       | Software                                |


## Bottleneck Analysis

### Problem overview
With the rapid growth of network demands, the number of BGP routes on routers rockets up these years and the BGP loading time of SONiC inevitably increases. The current BGP loading time, which is estimated at tens of seconds, is definitely far from satisfatory for routing use cases. Speeding up the BGP loading process is essential for the scalability of SONiC. We need to break down the whole loading process into several steps as shown in the figure below and find the performance bottlenecks in BGP loading:


1. `bgpd` parses the packets received by the socket, processes the `bgp-update` message and notifies `zebra` of new prefixes with their corresponding next hops
2. `zebra` decodes the message from `bgpd`, and delivers this routing message in `netlink` message format to `fpmsyncd` 
3. `fpmsyncd` processes this routing message and pushes it to `APPL_DB`
4. `orchagent` has a subscription to `APPL_DB`, hence would consume the routing message newly pushed to `APPL_DB` 
5. `orchagent` injects its processed routing message into `ASIC_DB` with `sairedis` APIs 
6. `syncd` gets notified of the newly added routing message in `ASIC_DB` due to the subscription
7. `syncd` processes the new routing message, then invokes `SAI` APIs to finally inject the new routing message into the hardware


**NOTE**: This is not the [whole workflow for routing](https://github.com/SONiC-net/SONiC/wiki/Architecture#routing-state-interactions), we ignore the Linux kernel part since we currently focus only on the SONiC part.

<figure align="center">
    <img src="images/sonic-workflow.png" width="60%" height=auto>
    <figcaption>Figure 2. SONiC BGP loading workflow</figcaption>
</figure>


### Single-threaded orchagent

Figure 3 explains how `orchagent` transfers routing data from `APPL_DB` to `ASIC_DB`.

`RouteOrch`, as a component of `orchagent`, has its `ConsumerStateTable` subscribed to `ROUTE_TABLE_CHANNEL` event. With this subscription, whenever `fpmsyncd` injects new routing data into `APPL_DB`, `orchagent` gets notified. Once notified, `orchagent` handles the following 3 tasks in serial.

1. use `pops` to fetch new routes from `APPL_DB`:
     - pop prefix from ROUTE_TABLE_SET 
     - traverse these prefixes and retrieve the temporary key data of _ROUTE_TABLE corresponding to the prefix
     - set key in ROUTE_TABLE 
     - delete temporary key in _ROUTE_TABLE
2. call `addToSync` to record the new routes to a local file `swss.rec`
3. call `doTask` to parse new routes one by one and store the processed data in the EntityBulker, and flush the data in EntityBulker to ASIC_DB as a whole


The main performance bottleneck here lies in the linearity of the 3 tasks.

<br>

<figure align=center>
    <img src="images/orchagent-workflow.png" width="60%" height=auto>
    <figcaption>Figure 3. Orchagent workflow<figcaption>
</figure>  


### Single-threaded syncd

`syncd` shares the similar problem (job linearity) with `orchagent`, the only difference is that `syncd` moves information from `ASIC_DB` to the hardware. 

<br>

<figure align=center>
    <img src="images/syncd-workflow.jpg" width="60%" height=auto>
    <figcaption>Figure 4. Syncd workflow<figcaption>
</figure>  


### Redundant APPL_DB I/O traffic

There is much Redis I/O traffic during the BGP loading process, from which we find two sources of unnecessary traffic.

#### fpmsyncd flushes on every incoming route
In the original design, `fpmsyncd` maintains a variable `pipeline`. Each time `fpmsyncd` receives a route from `zebra`, it processes the route and puts it in the `pipeline`. Every time the `pipeline` receives a route, it flushes the route to `APPL_DB`. If the size of the incoming route exceeds the size of the `pipeline` itself, the `pipeline` performs multiple flushes to make sure the received routes are written into `APPL_DB` completely. 

Each flush corresponds to a redis `SET` operation in `APPL_DB`, which triggers the `PUBLISH` event, then all subscribers get notified of the updates in `APPL_DB`, perform Redis `GET` operations to fetch the new route information from `APPL_DB`. 

That means, a single `pipeline` flush not only leads to redis `SET`, but also `PUBISH` and `GET`, hence a high flush frequency would cause a huge volumn of `REDIS` I/O traffic. However, the original `pipeline` flush frequency is decided by the routes incoming frequency and the `pipeline` size, which is unnecessarily high and hurts performance. 

In the original design, the performance here is not very critical since the bottleneck lies in the downstream modules. But with the downstream `orchagent` getting faster, the performance here then matters, we should avoid flushing on each route arrival to reduce I/O.

#### APPL_DB does redundant housekeeping
When `orchagent` consumes `APPL_DB` with `pops()`, as Figure 3 shows, `pops` function not only reads from `route_table_set` to retrieve route prefixes, but also utilizes these prefixes to delete the entries in the temporary table `_ROUTE_TABLE` and write into the stable table `ROUTE_TABLE`, while at the same time transferring messages to `addToSync` procedure. The transformation from temporary tables to the stable tables causes much traffic but is actually not worth the time. 

### Slow Routes decode and kernel thread overhead in zebra

`zebra` receives routes from `bgpd`. To understand the routing data sent by `bgpd`, it has to decode the received data with `zapi_route_decode` function, which consumes the most computing resources, as the flame graph indicates. This function causes the slow start for `zebra`, since decode only happens at the very beginning of receiving new routes from `bgpd`.


The main thread of `zebra` not only needs to send routes to `fpmsyncd`, but also needs to process the returned results of the child thread which indicate whether data are successfully delivered to `kernel`. Hence when `zebra` is busy dealing with the `kernel` side, the performance of talking to `fpmsyncd` would be affected.


<br>

<figure align=center>
    <img src="images/zebra.jpg" width="60%" height=auto>
    <figcaption>Figure 6. Zebra flame graph<figcaption>
</figure>  
      
### Synchronous sairedis API usage

The interaction between `orchagent` and `syncd` is using synchronous `sairedis` API.
Once `orchagent` `doTask` writes data to ASIC_DB, it waits for response from `syncd`. And since there is only single thread in `orchagent` it cannot process other routing messages until the response is received and processed.

<figure align=center>
    <img src="images/sync-sairedis1.png" width="40%" height=20%>
    <figcaption>Figure 5. Sync sairedis workflow<figcaption>
</figure> 


## Requirements

- All modifications should maintain the time sequence of route loading
- All modules should support the warm restart operations after modified
- With the optimization of this HLD implemented, the end-to-end BGP loading performance should be improved at least by 95%
- The new optimization codes would be turn off by default. It could be turned on via configuration


## High-Level Proposal

### Modification in orchagent/syncd to enable multi-threading
Figure 6 below illustrates the high level architecture modification for `orchagent` and `syncd`, it compares the original architecture and the new pipeline architecture proposed by this HLD. The pipeline design changes the workflow of both `orchagent` and `syncd`, thus enabling them to employ multiple threads to do sub-tasks concurrently.

Take `orchagent` for example, a single task of `orchagent` contains three sub-tasks `pops`, `addToSync` and `doTask`, and originally `orchagent` performs the three sub-tasks in serial. A new `pops` sub-task can only begin after the previous `doTask` is finished. The proposed design utilizes a separate thread to run `pops`, which decouples the `pops` sub-task from `addToSync` and `doTask`. As the figure shows, in the new pipeline architecture, a new `pops` sub-task begins immediately when it's ready, not having to wait for the previous `addToSync` and `doTask` to finish.

<figure align=center>
    <img src="images/pipeline-timeline.png">
    <figcaption>Figure 7. Pipeline architecture compared with the original serial architecture<figcaption>
</figure>  

#### Ring buffer for low-cost thread coordination
Since multiple threads are employed, we take a lock-free design by using a ring buffer as an asynchronous communication channel.

#### Asynchronous sairedis API usage
Asynchronous mode `sairedis` API is used and a list of context of response pending messages is maintained on `orchagent` to process the response when its received

<figure align=center>
    <img src="images/async-sairedis2.png" width="40%" height=20%>
    <figcaption>Figure 8. Async sairedis workflow<figcaption>
</figure> 

#### New ResponseThread in OA
A new `ResponseThread` is used in `orchagent` to process the response when its received so that the other threads can continue processing new routing messages

### Streamlining Redis I/O

The optimization for `orchagent` and `syncd` can theoretically double the BGP loading performance, which makes Redis I/O performance become a new bottleneck.

#### Lower frequency of the fpmsyncd flush & APPL_DB publish

Instead of flushing the `pipeline` on every data arrival and propose to use a flush timer to determine the flush frequency as illustrated below.

<figure align=center>
    <img src="images/pipeline-mode.png" height=auto>
    <figcaption>Figure 9. Proposed new BGP loading workflow<figcaption>
</figure>  

#### Disable the temporary table mechanism in APPL_DB

We propose to disable the temporary/stable table behavior and keep just a single table, so that we don't need to delete the temporary and then write into a stable one, which spares much `HDEL` and `HSET` traffic.

## Low-Level Implementation

### Multi-threaded orchagent with a ring buffer

Orchagent now runs two threads in parallel instead of a single thread.

- `table->pops(entries)` executes in the master thread to maintain the time sequence
- `Consumer->drain()` runs in a slave thread
- `Consumer->addToSync(entries)` is run by slave, as master is assumed to be busier
- `RingBuffer` is used for communication between the master thread and the slave
  - the master thread pops  `entries` to the ring buffer
  - the slave thread fetches `entries` from the ring buffer
  
Since SAI doesn't work well on small piece of data, the slave thread should check data size in ring buffer before it calls `Consumer->addToSync(entries)` to fetch data from the ring buffer, hence ensuring that it gets large enough data.

Routes will still be cached in `Consumer->m_toSync` rather than ring buffer if routeorch fails to push route to ASIC_DB. 

We use a new C++ class `Consumer_pipeline`, which is derived from the original `Consumer` class in `RouteOrch`, which enables the usage of a slave thread and utilizes the ring buffer.

```c++
class Consumer_pipeline : public Consumer {
  public:
    /**
     * Table->pops() should be in execute(). 
     * Called by master thread to maintain time sequence.
     */
    void execute() override;  
    /**
     * Main function for the new thread.
     */
    void drain() override;    
    /**
     * Need modified to support warm restart
     */
    void dumpPendingTasks(std::vector<std::string> &ts) override;
    size_t refillToSync(swss::Table* table) override;
    /**
     * Dump task to ringbuffer and load task from ring buffer
     */
    void dumptask(std::deque<swss::KeyOpFieldsValuesTuple> &entries);
    void loadtask(std::deque<swss::KeyOpFieldsValuesTuple> &entries);
  private:
    /**
     * Use ring buffer to deliver/buffer data
     */
    RingBuffer<swss::KeyOpFieldsValuesTuple> task_RingBuffer;
    /**
     * New thread for drain
     */
    std::thread m_thread_drain;
}
```

### Syncd [similar optimization to orchagent]
Similar case for syncd with orchagent. In our proposal, syncd runs `processBulkEntry` in a slave thread, since this function consumes most of the computing resources and blocks others.

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
      <img src="images/async-sairedis3.png" width="auto" height=auto>
      <figcaption>Figure 10. Async sairedis workflow<figcaption>
  </figure> 

### Fpmsyncd

`fpmsyncd` would flush the pipeline when it's full, `10000` to `15000` is tested to be a good range for the buffer size variable `REDIS_PIPELINE_SIZE` in our use cases. 

In the new design, the flush on the route arrival is cancelled. To avoid critical routing data being stuck in the pipeline, it uses <b>a timer thread</b> to flush data at a fixed frequency defined by `FLUSH_INTERVAL`, mutex is required since both the timer thread and the master thread access `fpmsyncd`'s  `pipeline`. Although we expect a lower flush frequency, it should make sure that the slight data delay in the pipeline doesn't hurt the overall performance, and 200 ms is tested to be a good value for `FLUSH_INTERVAL`.

### APPL_DB
<!-- omit in toc -->
#### sonic-swss-common/common/producerstatetable.cpp
The string variable `luaSet` contains the Lua script for Redis `SET` operation:
```c++
string luaSet =
  "local added = redis.call('SADD', KEYS[2], ARGV[2])\n"
  "for i = 0, #KEYS - 3 do\n"
  "    redis.call('HSET', KEYS[3 + i], ARGV[3 + i * 2], ARGV[4 + i * 2])\n"
  "end\n"
  " if added > 0 then \n"
  "    redis.call('PUBLISH', KEYS[1], ARGV[1])\n"
  "end\n";
```
In our design, the script changes to:
```lua
local added = redis.call('SADD', KEYS[2], ARGV[2])
for i = 0, #KEYS - 3 do
    redis.call('HSET', KEYS[3 + i], ARGV[3 + i * 2], ARGV[4 + i * 2])
end
```
Same modification should be add to `luaDel` for Redis `DEL` operation.

**NOTE:** The original lua script works fine for other modules, we only modify in the fpmsyncd case. 

By this modification, Redis operation `SET/DEL` is decoupled from `PUBLISH`.  

In this proposal, `PUBLISH` is binded with `fpmsyncd`'s flush behavior in `RedisPipeline->flush()` function, so that each time `fpmsyncd` flushes data to `APPL_DB`, the subscribers get notified.


<!-- omit in toc -->
#### sonic-swss-common/common/consumer_state_table_pops.lua
We removed the `DEL` and `HSET` operations in the original script, which optimizes `Table->pops()`:
```lua
redis.replicate_commands()
local ret = {}
local tablename = KEYS[2]
local stateprefix = ARGV[2]
local keys = redis.call('SPOP', KEYS[1], ARGV[1])
local n = table.getn(keys)
for i = 1, n do
   local key = keys[i]
   local fieldvalues = redis.call('HGETALL', stateprefix..tablename..key)
   table.insert(ret, {key, fieldvalues})
end
return ret
```
This change doubles the performance of `Table->pops()` and hence leads to routing from `fpmsyncd` to `orchagent` via APPL_DB 10% faster than before.

**NOTE:** This script change limits to `routeorch` module.

## WarmRestart scenario
This proposal considers the compatibility with SONiC `WarmRestart` feature. For example, when a user updates the config, a warm restart may be needed for the config update to be reflected. SONiC's main thread would call `dumpPendingTasks()` function to save the current system states and restore the states after the warm restart. Since this HLD introduces a new thread and a new structure `ring buffer` which stores some data, then we have to ensure that the data in `ring buffer` all gets processed before warm restart. During warm start, the main thread would modify the variable `m_toSync`, which the new thread also have access to. Therefore we should block the new thread during warm restart to avoid conflict.

Take orchagent for example, we need to make sure ring buffer is empty and the new thread is in idle before we call ```dumpPendingTasks()```. 

## Testing Requirements/Design
### System test
- All modules should maintain the time sequence of route loading.
- All modules should support WarmRestart.
- No routes should remain in redis pipeline longer than configured interval.
- No data should remain in ring buffer when system finishes routing loading.
- System should be able to install/remove/set routes (faster than before).

### Performance measurements when loading 500k routes

- traffic speed via  `zebra` from `bgpd` to `fpmsyncd`
- traffic speed via `fpmsyncd` from `zebra` to `APPL_DB`
- traffic speed via `orchagent` from `APPL_DB` to `ASIC_DB`
- traffic speed via `syncd` from `ASIC_DB` to the hardware

