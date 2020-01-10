# What Just Happened in SONiC HLD

# High Level Design Document

#### Rev 1.0

# Table of Contents
- [What Just Happened in SONiC HLD](#what-just-happened-in-sonic-hld)
- [High Level Design Document](#high-level-design-document)
      - [Rev 1.0](#rev-10)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [List of Figures](#list-of-figures)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [Overview](#overview)
- [Phase 1](#phase-1)
  - [WJH prerequisites](#wjh-prerequisites)
  - [WJH at service level in SONiC](#wjh-at-service-level-in-sonic)
  - [Docker container in SONiC](#docker-container-in-sonic)
  - [WJH feature table](#wjh-feature-table)
  - [Config DB schema](#config-db-schema)
  - [WJH table](#wjh-table)
  - [WJH_CHANNEL table](#wjhchannel-table)
  - [WJH service in SONiC](#wjh-service-in-sonic)
  - [WJH reasons and severity configuration file](#wjh-reasons-and-severity-configuration-file)
  - [WJH and debug counters](#wjh-and-debug-counters)
  - [WJH agent design](#wjh-agent-design)
  - [WJH defaults [Phase 1]](#wjh-defaults-phase-1)
  - [WJH provided data](#wjh-provided-data)
  - [Raw Channel](#raw-channel)
  - [Aggregated channel](#aggregated-channel)
  - [Local debug. CLI considerations](#local-debug-cli-considerations)
    - [WJH channel and Redis channel](#wjh-channel-and-redis-channel)
    - [Raw Channel](#raw-channel-1)
    - [Aggregated Channel](#aggregated-channel)
  - [WJH daemon](#wjh-daemon)
    - [Push vs Pull](#push-vs-pull)
  - [Mapping SDK IDs to SONiC IDs/object names](#mapping-sdk-ids-to-sonic-idsobject-names)
    - [SDK logical port ID/netdev IF_INDEX to SONiC port name mapping](#sdk-logical-port-idnetdev-ifindex-to-sonic-port-name-mapping)
    - [SDK logical LAG ID to SONiC LAG name mapping](#sdk-logical-lag-id-to-sonic-lag-name-mapping)
    - [SDK ACL rule ID to SONiC ACL rule name mapping](#sdk-acl-rule-id-to-sonic-acl-rule-name-mapping)
    - [Classes](#classes)
  - [WJH daemon packet parsing library](#wjh-daemon-packet-parsing-library)
  - [Flows](#flows)
    - [wjhd init flow](#wjhd-init-flow)
    - [wjhd channel create and set flow](#wjhd-channel-create-and-set-flow)
    - [wjhd channel remove flow](#wjhd-channel-remove-flow)
    - [wjhd deinit flow](#wjhd-deinit-flow)
    - [wjhd CLI flow](#wjhd-cli-flow)
    - [wjhd stream to cli decision](#wjhd-stream-to-cli-decision)
  - [CLI](#cli)
    - [Show CLI:](#show-cli)
    - [Show WJH feature status](#show-wjh-feature-status)
    - [Enabled/disable WJH feature](#enableddisable-wjh-feature)
    - [Config WJH global parameters](#config-wjh-global-parameters)
    - [Config WJH channel parameters [Phase 2]](#config-wjh-channel-parameters-phase-2)
  - [Warm Boot Support](#warm-boot-support)
    - [System level](#system-level)
    - [Service level](#service-level)
  - [Fast Boot Support](#fast-boot-support)
  - [Unit testing](#unit-testing)
    - [CLI](#cli-1)
      - [Case 1](#case-1)
    - [Daemon](#daemon)
  - [Regression traffic test](#regression-traffic-test)
- [Phase 2](#phase-2)
- [Phase 3](#phase-3)
- [Open Questions](#open-questions)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)
* [Table 2: Raw Channel Data](#raw-channel-1)
* [Table 3: Aggregated Channel Data](#aggregated-channel)

# List of Figures
* [Init flow](#wjhd-init-flow)
* [Channel create and set flow](#wjhd-channel-create-and-set-flow)
* [Channel remove flow](#wjhd-channel-remove-flow)
* [Deinit flow](#wjhd-deinit-flow)
* [CLI flow](#wjhd-cli-flow)
* [Stream to cli decision](#wjhd-stream-to-cli-decision)

# Revision
| Rev | Date     | Author          | Change Description        |
|:---:|:--------:|:---------------:|---------------------------|
| 0.1 | 01/20    | Stepan Blyschak | Initial version           |

# About this Manual
This document provides an overview of the implementation and integration of What Just Happened feature in SONiC.

# Scope
This document describes the high level design of the What Just Happened feature in SONiC.

# Definitions/Abbreviation
| Abbreviation | Description     |
|--------------|-----------------|
| SONiC        | Software for open networking in the cloud |
| API          | Application programming interface
| WJH           | What Just Happened |
| SAI           | Switch Abstraction Interface |
| SDK           | Software Developement Kit |


# Overview

What Just Happened feature provides the user a way to debug a network problem by providing exact packets that were dropped with detailed reasons.

# Phase 1

- No SONiC+ infrastructure
- WJH available only in debug mode, no streaming
- Non-configurable predefined WJH channels
- Buffer drops are not supported on SPC1

## WJH prerequisites

To enable aggregated mode which is built on eBPF feature in kernel, the following requirements have to be met

- Linux Kernel
  - CONFIG_BPF=y
  - CONFIG_BPF_SYSCALL=y
  - CONFIG_DEBUG_FS=y
  - CONFIG_PERF_EVENTS=y
  - CONFIG_EVENT_TRACING=y
- LLVM
  - llvm >= 3.7.1 (llc with bpf target support)
  - clang >= 3.4.0
- libelf1 [runtime dependency]
- debugfs mounted in container

*NOTE:* Make sure WJH library compiled with *-DWJH_EBPF_PRESENT*

## WJH at service level in SONiC

## Docker container in SONiC

A new docker image will be built for mellanox target called "docker-wjh" and included in Mellanox SONiC build by default.<p>
Build rules for WJH docker will reside under *platform/mellanox/docker-wjh.mk* while actual Dockerfile.j2 and other sources under *platform/mellanox/docker-wjh/* directory.

```
admin@sonic:~$ docker ps
CONTAINER ID        IMAGE                                COMMAND                  CREATED             STATUS              PORTS               NAMES
...
2b199b2309f9        docker-wjh:latest                    "/usr/bin/supervisord"   17 hours ago        Up 11 hours                             wjh
```

* SDK Unix socket needs to be mapped to container at runtime
* SDK /dev/shm needs to be mapped to container at runtime
* *debugfs* mounted inside container (requires RW access to */sys/kernel/debug/*)

## WJH feature table

Community [introduced](https://github.com/Azure/SONiC/blob/master/doc/Optional-Feature-Control.md) a way to enable/disable optional features at runtime and provided a seperate **FEATURE** table in CONFIG DB.



```
admin@sonic:~$ show features 
Feature    Status
---------  --------
telemetry   enabled
wjh         enabled
```

```
admin@sonic:~$ sudo config feature wjh [enabled|disabled]
```

The above config command translates into:

enabled command:
```
sudo systemctl enable wjh
sudo systemctl start wjh
```

disabled command:
```
sudo systemctl stop wjh
sudo systemctl disable wjh
```


## Config DB schema

## WJH table

```
; Describes global configuration for WJH
key          = WJH|global
nice_level   = integer ; wjh daemon process "nice" value
pci_bandwith = percentage ; percent of PCI bandwidth used by WJH, range [0-100]
```

Default configuration:

```json
{
  "WJH": {
    "global": {
      "nice_level": "1",
      "pci_bandwidth": "50"
    }
  }
}
```

Default configuration is stored in /etc/sonic/init_cfg.json. It's generation can be extended to generate WJH table for Mellanox build.
Porcesses inside WJH will have their own defaults, which will be the same. One note here is that /etc/sonic/init_cfg.json may be required to be generated at runtime to know wether buffer drops will be configured based on ASIC type.

## WJH_CHANNEL table

```
## WJH table

; Describes WJH channel configuration
key                = WJH_CHANNEL|<channel name>
type               = string ; raw|aggregated
polling_interval   = uinteger;
drop_category_list = string; comma seperated list of drop groups
```

Default configuration:

```json
"WJH_CHANNEL": {
  "raw_channel": {
      "type": "raw",
      "polling_interval": "5",
      "drop_category_list": "L2,L3,Tunnel,ACL",
  },
  "counter_channel": {
      "type": "aggregated_counter",
      "polling_interval": "1",
      "drop_category_list": "L1",
  },
  "direct_channel": {
      "type": "direct",
      "polling_interval": "1",
      "drop_category_list": "Buffer",
  }
}
```

## WJH service in SONiC

WjH service, as an ASIC-dependent service, should have a hard requirement for syncd service, so it will be started, restarted, stopped when syncd service is.

The following systemd unit configurations and dependencies will be set:

```
Requiers=database.service syncd.service
After=database.service syncd.service
Before=ntpconfig.service
StartLimitIntervalSec=1200
StartLimitBurst=3
```

The following service settings will be set:

```
Restart=always
RestartSec=30
```

## WJH reasons and severity configuration file

WJH requires a CSV formatted file on initialization. The file columns are:
```
ID              : drop reason ID;
REASON          : human readable message describing the reason;
SEVERITY        : severity of the drop;
PROPOSED ACTION : proposed action message (if there is);
```

SONiC has to provide a default CSV. Default CSV will be built into image and put under /etc/sonic/wjh/.
The path /etc/sonic is mapped to every container in RO mode, so WJH daemon will be able read it.

## WJH and debug counters

Debug counters in SAI and WJH are mutually exclusive. WJH works directly through SDK, so SAI cannot know when it’s enabled/disabled.

There are going to be two checks:

1. Upon WJH container start in the start script, check for debug counter entries in DB **DEBUG_COUNTER** table.<br>If found - log the error, abort the operation. Service will not be attempted to be restarted by systemd [S: Check systemd man].
2. In WJH enable CLI, log error and print the message to the user:<br> "Enabling WJH with debug counters is not supported. To enable WJH disable debug counters first".

To support WJH enable/disable at runtime, debug counters configuration producers have to be notified that debug counters became unavailable. The following option to implement this may be considered:

3. Once started, WJH has to reset capability table, speicifically it has to cleanup **DEBUG_COUNTER_CAPABILITIES** table populated by orchagent, in order for **DEBUG_COUNTER** table producers to know that debug counters became unavailable. On teardown, WJH has to restore **DEBUG_COUNTER_CAPABILITIES** table to the original state. Prefered to not put this logic in daemon part but in the service start script by saving table into file in container. Stop will restore the content of table. On unexpected restart the file will persist since the docker container is already created till user explicitelly removes the container.


## WJH agent design

## WJH defaults [Phase 1]

* Raw channel
  * L2, L3, Tunnel, ACL
* Aggregated 5-tuple [SPC2 only]
  * Buffer
* Aggregated counter
  * L1
  
## WJH provided data

## Raw Channel

| Data               | Buffer   | L1       | L2       | Router   | Tunnel   | ACL      |
|:------------------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
| packet             |    x     |          |    x     |    x     |    x     |    x     |
| packet size        |    x     |          |    x     |    x     |    x     |    x     |
| ingress port       |    x     |    x     |    x     |    x     |    x     |    x     |
| egress port        |    x*    |          |          |          |          |          |
| TC                 |    x*    |          |          |          |          |          |
| drop reason        |    x     |          |    x     |    x     |    x     |    x     |
| timestamp          |    x     |    x     |    x     |    x     |    x     |    x     |
| ingress LAG        |          |          |    x     |    x     |    x     |    x     |
| original occupancy |    x*    |          |          |          |          |          |
| original latency   |    x*    |          |          |          |          |          |
| bind point         |          |          |          |          |          |    x     |
| rule ID            |          |          |          |          |          |    x     |
| acl name           |          |          |          |          |          |    x     |
| rule name          |          |          |          |          |          |    x     |

- \* SPC2 only

## Aggregated channel

| Data               | Buffer   | L1       | L2       | Router   | Tunnel   | ACL      |
|:------------------:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
| ingress port       |          |    x     |          |          |          |          |
| 5 tuple            |    x     |          |    x     |    x     |    x     |    x     |
| drop reason        |    x     |          |    x     |    x     |    x     |          |
| aggregate time     |    x     |    x     |    x     |    x     |    x     |    x     |
| flows num          |          |          |          |          |          |    x*    |
| rule ID            |          |          |          |          |          |    x     |
| acl name           |          |          |          |          |          |    x     |
| rule name          |          |          |          |          |          |    x     |
| smac               |          |          |    x     |          |    x     |          |
| dmac               |          |          |    x     |          |    x     |          |
| is port up         |          |    x     |          |          |          |          |
| port down reason   |          |    x     |          |          |          |          |
| description        |          |    x     |          |          |          |          |
| state change count |          |    x     |          |          |          |          |
| symbol error count |          |    x     |          |          |          |          |
| crc error count    |          |    x     |          |          |          |          |

- \* SPC2 only

ACL name and Rule name can be used as description for drop;

e.g.:

```
admin@sonic:~$ show acl rule
Table    Rule            Priority  Action    Match
-------  ------------  ----------  --------  ------------------
DATAACL  RULE_1              9999  DROP      SRC_IP: 1.1.1.1/32
```

WJH ACL rule name is the following:
```
Priority[10001];KEY[SIP: 1.1.1.1/255.255.255.255];ACTION[COUNTER: COUNTER_ID = 9972];ACTION[FORWARD: FORWARD_ACTION = DISCARD]
```

While such description is not aligned with SONiC as it comes from SDK level it may be still usefull for user.
In the future, we can use ACL rule ID and map it to SONiC rule name, which is "RULE_1" from table "DATAACL" in this case. However, such mapping requires SONiC+ infrastructure.

## Local debug. CLI considerations

In this mode, WJH agent will stream the drop data to CLI. Data won't be stored anywhere, CLI will consume them imidiatelly.<br>
For debugging purpose, user can redirect the output to a file, e.g:<p>
  
```
admin@sonic:~$ show wjh raw L3 | tee l3_drops
```

In order to support debug mode, there should be a way to communicate between WJH agent and WJH CLI.<br>
The idea is to avoid developing own IPC (either streaming WJH data to localhost, exposing a Unix socket) we'll make use of SONiC Redis DB as a usual way to do IPC in SONiC. <p> *NOTE*: We won't be storing any data except configuration in DB, the DB is used as a message pipe form WJH agent to WJH CLI. <p> 

The plan is to use PUB/SUB channels model in Redis. This model is considered to be the most suitable way to stream data to CLI:

* No data stored presistently in DB - "send and forget"
* Multiple subscribers
* No streaming to CLI when there are no CLI clients - "PUBSUB NUMSUB"
* Already used in SONiC - NotificationProducer, NotificationConsumer
* Not reliable, however WJH user channels are not reliable as well.

There are following requirements to debug mode:
* WJH daemon does not produce any load to the Redis DB if there are no CLI debug clients
* User is able to pass a type and optionally a drop reason list to filter out drop events
* WJH streaming to collector does not stop when streaming to CLI
* Two or more users are able to debug at the same time

### WJH channel and Redis channel

Right now it is considered to have a single WJH dedicated Redis channel.
<p> [**Q**] Consider having per channel type ? per WJH channel ? per drop reason group ?


CLI has to have a way to tell WJH daemon to start streaming data to the channel. The main WJH daemon thread is subscribed to WJH_REQUEST_CHANNEL channel listents for CLI requests.


### Raw Channel

Raw Channel handling is straightforward. On every received packet via callback a message to Redis channel is sent which is consumed by CLI imidiatelly and output is printed on the screen. The CLI will work in "follow" mode, continuosly printing every received message via channel. User can terminate the CLI by sending SIGTERM, SIGINT, etc.

```
admin@sonic:~$ show wjh raw L3
#      Timestamp                sPort       dPort    VLAN    sMAC               dMAC               EthType    Src IP:Port    Dst IP:Port    IP Proto    Drop Group    Severity    Drop reason - recomended action
----   -----------------------  ----------  -------  ------  -----------------  -----------------  ---------  -------------  -------------  ----------  ------------  ----------  ---------------------------------
1      2019/07/18 11:06:31.277  Ethernet24  N/A      N/A     7C:FE:90:6F:39:BB  00:00:00:00:00:02  IPv4       1.1.1.1:171    127.0.0.1:172  TCP         L3            Critical    Destination IP is loopback

```

Serialized Redis channel message:
```
{
    "timestamp": "1579715858.1579715858",
    "src_port": "Ethernet24",
    "src_mac": "7C:FE:90:6F:39:BB",
    "dst_mac": "00:00:00:00:00:02",
    "eth_type": "IPv4",
    "src_ip_port": "1.1.1.1:171",
    "dest_ip:port": "127.0.0.1:172",
    "ip_proto": "TCP",
    "drop_group": "L3",
    "severity": "Critical",
    "reason": "Destination IP is loopback"
}
```

### Aggregated Channel

Since WJH library API works in READ&CLEAR mode, every event in aggregated channel generated by WJH will reset the counter

```
admin@sonic:~$ show wjh aggregated buffer
#      Period                      sMac           dMac           Src IP:Port    Dst IP:Port    IP Proto    Drop Group    Count    Severity    Drop reason - recomended action
----   -------------------------   -------------  -------------  -------------  -------------  ----------  ------------  ------   ----------  ---------------------------------
1      2019/07/18 11:06:30.277 -   N/A            N/A            1.1.1.1:171    111.0.0.1:172  TCP         Buffer        302      Critical    WRED
       2019/07/18 11:06:31.953
2      2019/07/18 11:06:31.35  -   N/A            N/A            1.1.1.1:171    111.0.0.1:172  TCP         Buffer        230      Critical    WRED
       2019/07/18 11:06:31.925
3      2019/07/18 11:06:32.277 -   N/A            N/A            N/A            N/A            N/A         Buffer        1542     Critical    WRED
       2019/07/18 11:06:33.277
```

Serialized Redis channel message:
```
{
    "first_timestamp": "1579715858.1579715858",
    "last_timestamp": "1579715859.1579715858",
    "eth_type": "IPv4",
    "src_ip_port": "1.1.1.1:171",
    "dest_ip_port": "111.0.0.1:172",
    "ip_proto": "TCP",
    "drop_group": "Buffer",
    "severity": "Critical",
    "reason": "WRED"
}
```

While the above output is not convinient for the user to analyze, user can still save the output to a file and operate on a file dump to count total number of drops for a specific flow and drop reason using awk:

```
admin@sonic:~$ cat drops | awk '{ if ($5=="1.1.1.1:171") count+=$9} END { print count }'
532
```

Another option for user convinience could be to specify a window to accumulate counters within:

```
admin@sonic:~$ show wjh aggregated l3 buffer --window=5sec
Drops within period: 2019/07/18 11:06:31 - 2019/07/18 11:06:36
#      sMac          dMac           Src IP:Port    Dst IP:Port    IP Proto    Drop Group    Count    Severity    Drop reason - recomended action
----   ------------- -------------  -------------  -------------  ----------  ------------  ------   ----------  ---------------------------------
1      N/A           N/A            1.1.1.1:171    127.0.0.1:172  TCP         L3            532      Critical    Dest IP is loopback
2      N/A           N/A            N/A            N/A            N/A         Buffer        1542     Critical    WRED
```

An LRU dictionary to accumulate count can be used, least recently updated packet tuple will be deleted to not consume a lot of memory in case the window is big.
*NOTE*: A window size displayed by the command will be calculated based on ```min(first_timestamps)``` and ```max(last_timestamps)```.

The timeline:

```
                 Actual window
      +-----------------------------------+
      |                                   |
      |              User request window  |
      |     +-----------------------------|----+
      |     |                             |    |
-------------------------------------------------------------------------------- CLI
                  ^                       ^           ^                          ^ - data available in Redis Channel

-------------------------------------------------------------------------------- WJH library timeline
      ^           ^           ^           ^           ^           ^              ^ - WJH library polling
      |           |
      +-----------+
     Channel polling
        interval
```


Same for L1 counters:

```
admin@sonic:~$ show wjh aggregated L1 --events
#   Period                    Port         State      Down Reason                        State Change  Symbol Error     FCS Error  Transceiver Overheat
--- ------------------------- -----------  --------   -------------------------------    ------------  --------------   ---------- --------------------
1   2019/07/18 11:06:30.277 - Ethernet0    Up         N/A                                1             2                8           4
    2019/07/18 11:06:31.277
2   2019/07/18 11:06:30.277 - Ethernet4    Down       Logical mismatch with peer link    1             1                8           2
    2019/07/18 11:06:31.277
3   2019/07/18 11:06:30.277 - Ethernet20   Down       Link training failure              1             0                0           0
    2019/07/18 11:06:31.277
4   2019/07/18 11:06:30.277 - Ethernet0    Down       Port admin down                    1             2                1           1 
    2019/07/18 11:06:31.277

```

```
admin@sonic:~$ show wjh aggregated L1 --window=5sec
Sample Window : 2019/07/18 11:06:31 - 2019/07/18 11:06:36 
#   Port         State      Down Reason                        State Change  Symbol Error     FCS Error  Transceiver Overheat
--- -----------  --------   -------------------------------    ------------  --------------   ---------- --------------------
1   Ethernet4    Down       Logical mismatch with peer link    1             4                8          2
2   Ethernet20   Down       Link training failure              1             0                0          0
3   Ethernet0    Down       Port admin down                    2             2                45         1 

```

*NOTE*: Displaying L1 and other drop group in CLI at the same time will be a CLI limitation, otherwise the table will be too huge for regular screen size to read.

```
admin@sonic:~$ show wjh aggregated L1 Buffer
error: displaying L1 and Buffer at the same time is not supported by CLI
```

## WJH daemon

### Push vs Pull

In push mode, the WJH library periodically queries the dropped packets or statistics and deliver them via user callbacks.
In pull mode, the WJH library stops the periodical query. The dropped packets or statistics can be delivered via user callbacks
which are explicitly triggered by API *wjh_user_channel_pull*. Please note that the user callbacks will be executed in the same
context/thread of the caller of *wjh_user_channel_pull*.


Pull mode is prefered here because no syncronization with WJH library thread will be required.
Channel polling will be performed in Select loop by wjhd; timerfd based SelectableTimer provided by *swss-common* package will be used.

## Mapping SDK IDs to SONiC IDs/object names

### SDK logical port ID/netdev IF_INDEX to SONiC port name mapping

1) WJH_INGRESS_INFO_TYPE_LOGPORT


WJH lib returns logical port ID while we need to provide SONiC port name/alias. Since there is no SONiC+ infrastructure ready yet, the following way of mapping logcal port ID to SONiC port name is suggested: <p>

  On initialization time, WJH agent will read **COUNTERS_PORT_NAME_MAP** from COUNTERS DB. **COUNTERS_PORT_NAME_MAP** has a mapping from SONiC port name to SAI redis virtual OID. Given the virtual SAI redis OID we need to map it to real SAI OID, which can be done using ASIC DB's **VIDTORID** table. By using the Mellanox SAI port OID we can extract SDK logical port ID. To avoid hardcoding SDK logical ID extraction math, wjh agent can link to Mellanox SAI library in order to use *mlnx_object_to_log_port* function. <p>
  Future port breakout is not considered here. It is assumed that in case of port breakout *portsyncd* will generate some kind of event when host interfaces for new ports are created, old ports removed, so WJH agent can subscribe for such kind of events to recreate internal map.

  SDK logical port ID from SONiC port name convertion scheme:

 ```
 
 port name -> VID, VID -> RID, RID ->(mlnx_object_to_log_port)-> SDK logical port ID
 
 ```

2) WJH_INGRESS_INFO_TYPE_IF_INDEX


  WJH daemon will create a map if_index <-> SONiC port name.

  Future port breakout is not considered here. It is assumed that in case of port breakout *portsyncd* will generate some kind of event when host interfaces for new ports are created, old ports moved, so WJH agent can subscribe for such kind of events to recreate internal map.

 
### SDK logical LAG ID to SONiC LAG name mapping
 
There is no table in DB that will map SONiC LAG name to SAI redis virtual OID. Without SONiC+ infrastructure it may be tricky to map SDK LAG ID to SONiC LAG name, while it is still possible. Since WJH library provides ingress logical port ID and ingress LAG ID in case ingress port is a LAG member it is possible to map it to the LAG uniquely by LAG member port. However, in order to simplify developement the LAG ID data provided by WJH library will be ignored. Besides, it is not worth the required effort, since user can map ingress port to LAG on his own.

### SDK ACL rule ID to SONiC ACL rule name mapping

Complex to do such mapping without SONiC+, therefore this data will be ignored.

### Classes

```c++
/* variant(union) based data structure holding either
 * raw/aggregated L1/L2/L3/Buffer/Acl/Tunnel drop information */
struct WjhDropInfo;
```

```c++
class WjhConsumer {
      virtual void onWjhEvent(const WjhDropInfo&) = 0;
};
```

```c++
class WjhCliConsumer {
      virtual void onWjhEvent(const WjhDropInfo&);
};
```

```c++
class WjhGRPCConsumer {
      virtual void onWjhEvent(const WjhDropInfo&);
};
```

In WJH event loop wjh daemon will iterate consumers and invoke *onWjhEvent*, so that WJH event will be send to every consumer - gRPC streaming consumer and CLI streaming consumer.


```c++
class Wjh {
      template<typename RawInfoT>
      static void onRawWjhEvent(const RawInfoT*,
                                uint32_t*,
                                wjh_drop_aggregate_attr_t*);
      
      template<typename AggregatedKeyT, typename AggregatedDataT>
      static void onAggregatedWjhEvent(const AggregatedKeyT*,
                                       const AggregatedDataT*,
                                       uint32_t*,
                                       wjh_drop_aggregate_attr_t*);
}
```


## WJH daemon packet parsing library

CLI requires source, destination MAC, Ethernet type, source, destination IP:port and IP protocol on raw channel. A packet parsing library can be used:

* https://github.com/mfontanini/libtins

## Flows

### wjhd init flow

![wjhd init](/doc/wjh/wjhd_init.svg)

### wjhd channel create and set flow

![wjhd create_set](/doc/wjh/wjhd_channel_create_set.svg)

### wjhd channel remove flow

![wjhd removal](/doc/wjh/wjhd_channel_remove.svg)

### wjhd deinit flow

![wjhd deinit](/doc/wjh/wjhd_deinit.svg)

### wjhd CLI flow

![wjhd cli_flow](/doc/wjh/wjhd_user_flow.svg)

### wjhd stream to CLI decision

![wjhd cli](/doc/wjh/wjhd_cli.svg)


## CLI

### Show CLI:


### Show WJH feature status
```
admin@sonic:~$ show feature wjh
```


```
admin@sonic:~$ show wjh config
admin@sonic:~$ show wjh raw [DROP_GROUP|DROP_GORUP+]
admin@sonic:~$ show wjh aggregated [DROP_GROUP|DROP_GORUP+] [--window=[seconds]|--events]
admin@sonic:~$ show wjh aggregated L1 [--window=[seconds]|--events]
```

### Enabled/disable WJH feature
```
admin@sonic:~$ config feature wjh [enabled|disabled]
```

### Config WJH global parameters

Global parameters will be create only.

### Config WJH channel parameters [Phase 2]

To create a new channel

```
admin@sonic:~$ config wjh channel add [channel_name] [--type=raw|aggregated] [--polling-iterval=<uint>] [--drop_groups=<string>]

```

To set attribute on existing new channel

```
admin@sonic:~$ config wjh channel set [channel_name] [--polling-iterval=<uint>] [--drop_groups=<string>]

```

To remove existing channel
```
admin@sonic:~$ config wjh channel delete [channel_name]
```

## Warm Boot Support

### System level

WJH service will be shutdown prior to syncd as because of systemd dependencies. So before system goes kexec WJH will be able to shutdown properly and clean all resources.

### Service level

WJH service level warm restart has no inpact on traffic.

Other services warm restart (like swss, teamd) won't trigger WJH restart. Only syncd service restart triggers WJH service restart which makes sense because WJH depends on sxkernel service, however syncd service warm restart is not supported in SONiC in any case.

## Fast Boot Support

No special support is required. However, it is required to test the effect on system performance during system *fast* startup to see if the wjh service intense polling will increase the downtime (like flex counters polling does). In that case a systemd timer to delay wjh service may be needed.

## System performance

System overal load has to be mannualy tested when there are a lot amount of raw drops and unique 5-tuples aggregated drops.

## Unit testing

### CLI

List of test cases:

#### Case 1


### Daemon

List of test cases:



## Regression traffic test

TBD

# Phase 2

TBD

# Phase 3

TBD


# Open Questions
