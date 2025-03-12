# Improve Orchagent Route performance with ZMQ

### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 1.1 | Mar  4 2024 |   Hua Liu          | Improve Orchagent with ZMQ        |

## Table of Contents

- [Goal \& Scope](#goal--scope)
- [Definitions \& Abbreviations](#definitions--abbreviations)
- [High-Level Proposal](#high-level-proposal)
- [Low-Level Implementation](#low-level-implementation)
  - [Fpmsyncd](#fpmsyncd)
  - [Orchagent](#orchagent)
- [WarmRestart scenario](#warmrestart-scenario)
- [Debugability](#debugability)
- [Error recovery](#error-recovery)
- [References](#references)
  * [BGP Loading Optimization for SONiC](#bgp-loading-optimization-for-sonic)
  * [ZMQ producer/consumer state table design](#zmq-producer/consumer-state-table-design)
  * [ZMQ](#zmq)

## Goal & Scope

The goal of this project is improve route operation performance between fpmsyncd and orchagent.

Following change will be make to archive this goal:
1. Enable ZMQ between fpmsyncd and orchanget.
2. Enable Ring Buffer for route table, this feature develop by Alibaba.
3. Enable multiple-db support.

## Definitions & Abbreviations

| Definitions/Abbreviation | Description                             |
| ------------------------ | --------------------------------------- |
| BGP                      | Border Gateway Protocol                 |
| FPM                      | Forwarding Plane Manager                |
| ZMQ                      | ZeroMQ                                  |

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

## BGP route performance issue
Alibaba analyze and identify performance issues with this document:
 - BGP Loading Optimization for SONiC: https://github.com/a114j0y/SONiC/blob/master/doc/bgp_loading_optimization/bgp-loading-optimization-hld.md

Issue:
 - Orchagent consumer execute workflow is single-threaded
    - Alibaba add async ringbuffer to router consumer:
    https://github.com/sonic-net/sonic-swss/pull/3242
 - Syncd is too strictly locked, It also has a single-threaded workflow to pop data from the upstream redis tables.
 - Redundant APPL_DB I/O traffic: producerstatetable publishes every command and fpmsyncd flushes on every select event, APPL_DB does redundant housekeeping.
 - Slow Routes decode and kernel thread overhead in zebra
 - Synchronous sairedis API usage

## Enable ZMQ between fpmsyncd and orchanget.

Based on alibaba's team analyze result: "BGP Loading Optimization for SONiC", the route operation performance between fpmsyncd and orchagent can be improved by switch to ZMQ producer/consumer table.

<!-- <style>
table{
  margin:auto;
}
</style> -->
| Module                   |  Original Speed(routes/s)    | Optimized Speed (routes/s) |
| ------------------------ | -----------------------------| -----------------------------|
| Zebra / Fpmsyncd         |  <center>17K                 | <center>25.4K                 |
| Orchagent                |  <center>10.5K               | <center>30.7K                 |


### High-Level Proposal

This HLD aims to enhance the performance between fpmsyncd and orchagent by replace Redis based channel to ZMQ based channel.

Orchagent subscribe data with redis based ConsumerStateTable, sonic-swss-common has ZMQ based ZmqConsumerStateTable, here are compare with redis based tables:
<img src="./zmq-diagram.png" style="zoom:100%;" />

Orchagent already integrated with ZMQ:
1. ZmqConsumer inherited from ConsumerBase.
2. ZmqConsumer support warm-reboot.
3. All ZmqConsumer share same ZMQ connection.
<img src="./OrchagenZmq.png" style="zoom:100%;" />

Pros:
1. 30 times faster than Redis based table, ZMQ table can transfer 100K route entry per-second, redis table can only transfer 3.7K route entry per-second.
2. Fully compatible with ProducerStateTable/ConsumerStateTable.
3. Asynchronous update redis DB with background thread.

Cons:
1. Performance depends on network bandwidth.
2. Server side need start before client side. Client side need handle server side crash issue.

### Low-Level Implementation

#### Fpmsyncd

Change from ProducerStateTable to ZmqProducerStateTable:

```c++

class RouteSync : public NetMsg
{
...
private:
    /* regular route table */
    unique_ptr<ProducerStateTable> m_routeTable;
    /* label route table */
    unique_ptr<ProducerStateTable> m_label_routeTable;
...

RouteSync::RouteSync(RedisPipeline *pipeline, ZmqClient *zmqClient) :
    m_vnet_routeTable(pipeline, APP_VNET_RT_TABLE_NAME, true),
    m_vnet_tunnelTable(pipeline, APP_VNET_RT_TUNNEL_TABLE_NAME, true),
    m_nl_sock(NULL), m_link_cache(NULL)
{
    if (zmqClient != nullptr) {
        m_routeTable = unique_ptr<ProducerStateTable>(new ZmqProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, *zmqClient, true));
        m_label_routeTable = unique_ptr<ProducerStateTable>(new ZmqProducerStateTable(pipeline, APP_LABEL_ROUTE_TABLE_NAME, *zmqClient, true));
    }
    else {
        m_routeTable = make_unique<ProducerStateTable>(pipeline, APP_ROUTE_TABLE_NAME, true);
        m_label_routeTable = make_unique<ProducerStateTable>(pipeline, APP_LABEL_ROUTE_TABLE_NAME, true);
    }
    
...
}
```

#### Orchagent

Change RouteOrch inherit from ZmqOrch:

```c++
class RouteOrch : public ZmqOrch, public Subject
{
public:
    RouteOrch(DBConnector *db, vector<table_name_with_pri_t> &tableNames, SwitchOrch *switchOrch, NeighOrch *neighOrch, IntfsOrch *intfsOrch, VRFOrch *vrfOrch, FgNhgOrch *fgNhgOrch, Srv6Orch *srv6Orch, swss::ZmqServer *zmqServer = nullptr);

...
```

- ZmqOrch class inherit from Orch class.
- When zmqServer is not nullptr, ZmqOrch will create consumer with ZmqConsumerStateTable
- ZmqConsumerStateTable will create background thread for async APPL_DB update

ZmqOrch and ZmqConsumer provide ZMQ support:
```c++
class ZmqOrch : public Orch
{
public:
    ZmqOrch(swss::DBConnector *db, const std::vector<std::string> &tableNames, swss::ZmqServer *zmqServer);
    ZmqOrch(swss::DBConnector *db, const std::vector<table_name_with_pri_t> &tableNames_with_pri, swss::ZmqServer *zmqServer);

    virtual void doTask(ConsumerBase &consumer) { };
    void doTask(Consumer &consumer) override;

private:
    void addConsumer(swss::DBConnector *db, std::string tableName, int pri, swss::ZmqServer *zmqServer);
};

class ZmqConsumer : public ConsumerBase {
public:
    ZmqConsumer(swss::ZmqConsumerStateTable *select, Orch *orch, const std::string &name)
        : ConsumerBase(select, orch, name)
    {
    }

    swss::TableBase *getConsumerTable() const override
    {
        // ZmqConsumerStateTable is a subclass of TableBase
        return static_cast<swss::ZmqConsumerStateTable *>(getSelectable());
    }

    void execute() override;
    void drain() override;
};
```

#### Multi-namespace
For T2 device, there are multiple namespace, which means there are multiple orchagent/fpmsyncd instance running on device.

Each orchagent should listen on a unique ZMQ port, which configured on database_config{asic_id}.json
```json
{
    "INSTANCES": {
        "redis":{
            "hostname" : "127.0.0.1",
            "port": 6379,
            "unix_socket_path": "/var/run/redis0/redis.sock"
        },
        "zmq":{
            "hostname" : "127.0.0.1",
            "port": 8101
        }
    },
    "DATABASES" : {
```

The ZMQ port for default namespace is '8100'
For each asic namespace, the ZMQ port is '8100 + asic_index'

### WarmRestart scenario
Orchagent support warm-reboot by ConsumerBase::refillToSync() method. ZmqConsumer inherit from ConsumerBase, so switch to ZmqOrch and ZmqConsumer will support warm-reboot.

## Enable Ring Buffer for route table
 - Ring buffer feature enable/disable flag in CONFIG_DB:
 
```json
        container DEVICE_METADATA {
            container localhost{
                leaf ring_thread_enabled {
                    type boolean;
                    description "Enable gRingMode of OrchDaemon, which would set up its ring thread to accelerate task execution.";
                    default "false";
                }

            }
        }
```

 - Ring buffer design doc: https://github.com/sonic-net/SONiC/pull/1521

 - Ring buffer performance improve:
 The table below compares the loading speed of fpmsyncd and orchagent before and after optimization, tested with loading 2M routes on the Alibaba SONiC based eSR platform:

<!-- <style>
table{
  margin:auto;
}
</style> -->
| Module                   |  Original Speed(routes/s)    | Optimized Speed (routes/s) |
| ------------------------ | -----------------------------| -----------------------------|
| Fpmsyncd                 |  <center>17K                 | <center>25.4K                 |
| Orchagent                |  <center>9.7K               | <center>13.9K            |

## Enable multiple-db support
 - Today SONiC by default only has one redis database instance created and all the databases use this unique database instance, like APPL_DB, ASIC_DB, CONF_DB and so on. when there are huge writes operations during a short time period (like huge routes created), this only database instance is very busy.

 - By enable multiple-db, the huge write operation will be separate into different database instances. According to design doc, test result shows the performance (time) improved 20-30%.

 - Multiple-db example:
```
admin@DEVICE:~$ cat /var/run/redis/sonic-db/database_config.json
{
    "INSTANCES": {
        "redis": {
            "hostname": "127.0.0.1",
            "port": 6379,
            "unix_socket_path": "/var/run/redis/redis.sock",
            "persistence_for_warm_boot": "yes"
        },
        "redis1": {
            "hostname": "127.0.0.1",
            "port": 6378,
            "unix_socket_path": "/var/run/redis/redis1.sock",
            "persistence_for_warm_boot": "yes"
        },
        "redis2": {
            "hostname": "127.0.0.1",
            "port": 6377,
            "unix_socket_path": "/var/run/redis/redis2.sock",
            "persistence_for_warm_boot": "yes"
        },
        "redis3": {
            "hostname": "127.0.0.1",
            "port": 6376,
            "unix_socket_path": "/var/run/redis/redis3.sock",
            "persistence_for_warm_boot": "yes"
        },
        "redis4": {
            "hostname": "127.0.0.1",
            "port": 6375,
            "unix_socket_path": "/var/run/redis/redis4.sock",
            "persistence_for_warm_boot": "yes"
        },
        "redis_bmp": {
            "hostname": "127.0.0.1",
            "port": 6400,
            "unix_socket_path": "/var/run/redis/redis_bmp.sock",
            "persistence_for_warm_boot": "yes"
        }
    },
    "DATABASES": {
        "APPL_DB": {
            "id": 0,
            "separator": ":",
            "instance": "redis1"
        },
        "ASIC_DB": {
            "id": 1,
            "separator": ":",
            "instance": "redis2"
        },
        "COUNTERS_DB": {
            "id": 2,
            "separator": ":",
            "instance": "redis3"
        },
        "LOGLEVEL_DB": {
            "id": 3,
            "separator": ":",
            "instance": "redis"
        },
        "CONFIG_DB": {
            "id": 4,
            "separator": "|",
            "instance": "redis"
        },
        "PFC_WD_DB": {
            "id": 5,
            "separator": ":",
            "instance": "redis3"
        },
        "FLEX_COUNTER_DB": {
            "id": 5,
            "separator": ":",
            "instance": "redis3"
        },
        "STATE_DB": {
            "id": 6,
            "separator": "|",
            "instance": "redis"
        },
        "SNMP_OVERLAY_DB": {
            "id": 7,
            "separator": "|",
            "instance": "redis"
        },
        "SYSMON_DB": {
            "id": 10,
            "separator": "|",
            "instance": "redis"
        },
        "BMC_DB": {
            "id": 12,
            "separator": ":",
            "instance": "redis4"
        },
        "RESTAPI_DB": {
            "id": 8,
            "separator": "|",
            "instance": "redis"
        },
        "GB_ASIC_DB": {
            "id": 9,
            "separator": ":",
            "instance": "redis"
        },
        "GB_COUNTERS_DB": {
            "id": 10,
            "separator": ":",
            "instance": "redis"
        },
        "GB_FLEX_COUNTER_DB": {
            "id": 11,
            "separator": ":",
            "instance": "redis"
        },
        "APPL_STATE_DB": {
            "id": 14,
            "separator": ":",
            "instance": "redis"
        },
        "BMP_STATE_DB": {
            "id": 20,
            "separator": "|",
            "instance": "redis_bmp"
        }
    },
    "VERSION": "1.0"
}
```
 - Multiple-db feature need enabled with build-time flag: 
```
 ## Enable MULTIDB
{% if ENABLE_MULTIDB == "y" %}
sudo touch $FILESYSTEM_ROOT_ETC_SONIC/enable_multidb
{% endif %}
```

 - Multiple-db design doc: https://github.com/sonic-net/SONiC/blob/master/doc/database/multi_database_instances.md

## Performance improve result

Performance test on Mellanox 4600 T1 device with 'sudo config bgp startup all':
```
Neighbhor      V     AS    MsgRcvd    MsgSent    TblVer    InQ    OutQ  Up/Down      State/PfxRcd  NeighborName
-----------  ---  -----  ---------  ---------  --------  -----  ------  ---------  --------------  --------------
10.0.0.1       4  65200       3204       3225     19923      0       0  00:00:43             6370  ARISTA01T2
10.0.0.5       4  65200       3204       3225     19923      0       0  00:00:42             6370  ARISTA03T2
10.0.0.9       4  65200       3204       3225     19923      0       0  00:00:42             6370  ARISTA05T2
10.0.0.13      4  65200       3204       3225     19923      0       0  00:00:43             6370  ARISTA07T2
10.0.0.33      4  64001         20       3225     19923      0       0  00:00:43                3  ARISTA01T0
10.0.0.35      4  64002         20       3225     19923      0       0  00:00:43                3  ARISTA02T0
10.0.0.37      4  64003         21       3225     19923      0       0  00:00:43                4  ARISTA03T0
10.0.0.39      4  64004         20       3225     19923      0       0  00:00:42                3  ARISTA04T0
10.0.0.41      4  64005         21       3225     19923      0       0  00:00:42                4  ARISTA05T0
10.0.0.43      4  64006         20       3225     19923      0       0  00:00:42                3  ARISTA06T0
10.0.0.45      4  64007         20       3225     19923      0       0  00:00:42                3  ARISTA07T0
10.0.0.47      4  64008         20       3225     19923      0       0  00:00:42                3  ARISTA08T0
10.0.0.49      4  64009         20       3225     19923      0       0  00:00:42                3  ARISTA09T0
10.0.0.51      4  64010         20       3225     19923      0       0  00:00:42                3  ARISTA10T0
10.0.0.53      4  64011         20       3225     19923      0       0  00:00:42                3  ARISTA11T0
10.0.0.55      4  64012         20       3225     19923      0       0  00:00:42                3  ARISTA12T0
10.0.0.57      4  64013         20       3225     19923      0       0  00:00:42                3  ARISTA13T0
10.0.0.59      4  64014         20       3225     19923      0       0  00:00:42                3  ARISTA14T0
10.0.0.61      4  64015         20       3225     19923      0       0  00:00:42                3  ARISTA15T0
10.0.0.63      4  64016         20       3225     19923      0       0  00:00:42                3  ARISTA16T0
10.0.0.65      4  64017         19       3225     19923      0       0  00:00:42                1  ARISTA17T0
10.0.0.67      4  64018         19       3225     19923      0       0  00:00:42                1  ARISTA18T0
10.0.0.69      4  64019         19       3225     19923      0       0  00:00:42                1  ARISTA19T0
10.0.0.71      4  64020         19       3225     19923      0       0  00:00:42                1  ARISTA20T0
```

Before, 13 seconds:
```
2025 Mar 12 02:55:25.776947 DEVICENAME DEBUG bgp#bgpcfgd: Received message : '('10.0.0.1', 'SET', (('admin_status', 'up'), ('asn', '65200'), ('holdtime', '10'), ('keepalive', '3'), ('local_addr', '10.0.0.0'), ('name', 'ARISTA01T2'), ('nhopself', '0'), ('rrclient', '0')))'

...

2025 Mar 12 02:55:38.643445 DEVICENAME ERR swss#orchagent: :- doTask: [TEST] RouteOrch::doTask, handle route from m_toSync: 20c1:bc0:0:80::/64 - SET
```

After, 4 seconds:
```
2025 Mar 12 05:37:16.750408 DEVICENAME DEBUG bgp#bgpcfgd: Received message : '('10.0.0.1', 'SET', (('admin_status', 'up'), ('asn', '65200'), ('holdtime', '10'), ('keepalive', '3'), ('local_addr', '10.0.0.0'), ('name', 'ARISTA01T2'), ('nhopself', '0'), ('rrclient', '0')))'

...

2025 Mar 12 05:37:20.414067 DEVICENAME ERR swss#orchagent: :- doTask: [TEST] RouteOrch::doTask, handle route from m_toSync: 193.6.216.128/25 - SET
```

## Debuggability
ZMQ can be debug with TCP dump:
https://github.com/whitequark/zmtp-wireshark

## References
 - BGP Loading Optimization for SONiC: https://github.com/a114j0y/SONiC/blob/eruan-new/doc/bgp_loading_optimization/bgp-loading-optimization-hld.md
 - ZMQ producer/consumer state table design: https://github.com/sonic-net/SONiC/blob/master/doc/sonic-swss-common/ZMQ%20producer-consumer%20state%20table%20design.md
 - ZMQ: https://zguide.zeromq.org/docs/
 - Multiple-db design doc: https://github.com/sonic-net/SONiC/blob/master/doc/database/multi_database_instances.md