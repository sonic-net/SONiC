# High frequency telemetry high level design <!-- omit in toc -->

## Table of Content <!-- omit in toc -->

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements / Constraints](#5-requirements--constraints)
  - [5.1. Phase 1](#51-phase-1)
  - [5.2. Phase 2](#52-phase-2)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
  - [7.1. Modules](#71-modules)
    - [7.1.1. Counter Syncd](#711-counter-syncd)
    - [7.1.2. High frequency telemetry Orch](#712-high-frequency-telemetry-orch)
    - [7.1.3. Netlink Module and DMA Engine](#713-netlink-module-and-dma-engine)
    - [7.1.4. OpenTelemetry Collector (Existing open source solution)](#714-opentelemetry-collector-existing-open-source-solution)
  - [7.2. Data format](#72-data-format)
    - [7.2.1. IPFIX header](#721-ipfix-header)
    - [7.2.2. IPFIX template](#722-ipfix-template)
    - [7.2.3. IPFIX data](#723-ipfix-data)
    - [7.2.4. Netlink message](#724-netlink-message)
    - [7.2.5. OTLP message](#725-otlp-message)
  - [7.3. Bandwidth Estimation](#73-bandwidth-estimation)
  - [7.4. Config DB](#74-config-db)
    - [7.4.1. DEVICE\_METADATA](#741-device_metadata)
    - [7.4.2. HIGH\_FREQUENCY\_TELEMETRY\_PROFILE](#742-high_frequency_telemetry_profile)
    - [7.4.3. HIGH\_FREQUENCY\_TELEMETRY\_GROUP](#743-high_frequency_telemetry_group)
  - [7.5. StateDb](#75-statedb)
    - [7.5.1. HIGH\_FREQUENCY\_TELEMETRY\_SESSION](#751-high_frequency_telemetry_session)
  - [7.6. Work Flow](#76-work-flow)
  - [7.7. SAI API](#77-sai-api)
- [8. Configuration and management](#8-configuration-and-management)
  - [8.1. Manifest (if the feature is an Application Extension)](#81-manifest-if-the-feature-is-an-application-extension)
  - [8.2. CLI/YANG model Enhancements](#82-cliyang-model-enhancements)
    - [8.2.1. Config CLI](#821-config-cli)
    - [8.2.2. Inspect stream CLI](#822-inspect-stream-cli)
    - [8.2.3. YANG](#823-yang)
  - [8.3. Config DB Enhancements](#83-config-db-enhancements)
  - [8.4. Warmboot and Fastboot Design Impact](#84-warmboot-and-fastboot-design-impact)
  - [8.5. Memory Consumption](#85-memory-consumption)
  - [8.6. Restrictions/Limitations](#86-restrictionslimitations)
  - [8.7. Testing Requirements/Design](#87-testing-requirementsdesign)
    - [8.7.1. Unit Test cases](#871-unit-test-cases)
    - [8.7.2. System Test cases](#872-system-test-cases)
  - [8.8. Open/Action items - if any](#88-openaction-items---if-any)

## 1. Revision

| Rev | Date       | Author | Change Description |
| --- | ---------- | ------ | ------------------ |
| 0.1 | 09/06/2024 | Ze Gan | Initial version    |
| 0.2 | 03/01/2025 | Janet Cui | Initial version    |

## 2. Scope

This document outlines the high-level design of high frequency telemetry, focusing primarily on the internal aspects of SONiC rather than external telemetry systems.

## 3. Definitions/Abbreviations

| Abbreviation | Description                               |
| ------------ | ----------------------------------------- |
| SAI          | The Switch Abstraction Interface          |
| IPFIX        | Internet Protocol Flow Information Export |
| TAM          | Telemetry and Monitoring                  |
| BW           | Bandwidth                                 |
| OTLP         | The OpenTelemetry Protocol                |

## 4. Overview

In the context of AI scenarios, we are encountering challenges with switches that have a higher number of ports, such as 512, and the need for more time-sensitive statistics fetching. The existing telemetry solution is unable to fully meet these requirements. This document aims to address these challenges by proposing a high-frequency telemetry solution that enhances the efficiency and accuracy of statistics collection in SONiC. Because the traditional telemetry solution of SONiC relies on the syncd process to proactively query stats and counters via the SAI API. This approach causes the syncd process to spend excessive time on SAI communication. The high frequency telemetry described in this document aims to provide a more efficient method for collecting object stats. The main idea is that selected stats will be proactively pushed from the vendor's driver to the collector via netlink.

## 5. Requirements / Constraints

### 5.1. Phase 1

- The number of SAI object types should not exceed 32,768 ($2^{15}$). This means the value of SAI_OBJECT_TYPE_MAX should be less than 32,768.
- The number of SAI object extension types should not exceed 32,768.
- The number of stats types for a single SAI object type should not exceed 32,768.
- The number of extension stats types for a single SAI object type should not exceed 32,768.
- The number of SAI objects of the same type should not exceed 32,768.
- The vendor SDK should support publishing stats in IPFIX format and its IPFIX template.
- If a polling frequency for stats cannot be supported, the vendor's SDK should return this error.
- The vendor SDK should support querying the minimal polling interval for each counter.
- When reconfiguring any high frequency telemetry settings, whether it is the polling interval or the stats list, the existing high frequency telemetry will be interrupted and regenerated.
- If any of monitored objects is deleted, the existing high frequency telemetry will be interrupted and regenerated.

### 5.2. Phase 2

- Replace the existing solution by integrating the new high-frequency telemetry architecture into the Counter DB, ensuring compatibility with the current system and ecosystem.
- Supports updating configuration without interrupting the stream of high frequency telemetry

## 6. Architecture Design

``` mermaid

---
title: High frequency telemetry architecture
---
flowchart LR
    subgraph Redis
        config_db[(CONFIG_DB)]
        state_db[(STATE_DB)]
        counter_db[(COUNTER_DB)]
    end

    subgraph SONiC service
        subgraph OpenTelemetry container
            otel(OpenTelemetry Collector)
        end
        subgraph SWSS container
            counter_syncd(Counter Syncd)
            subgraph Orchagent
                hft_orch(High frequency telemetry Orch)
            end
        end
        subgraph SYNCD container
            syncd(Syncd)
        end
    end

    subgraph Linux Kernel
        dma_engine(DMA Engine)
        netlink_module(Netlink Module)
    end

    asic[\ASIC\]

    config_db --HIGH_FREQUENCY_TELEMETRY_PROFILE
                HIGH_FREQUENCY_TELEMETRY_GROUP--> hft_orch
    state_db --HIGH_FREQUENCY_TELEMETRY_SESSION--> counter_syncd
    hft_orch --HIGH_FREQUENCY_TELEMETRY_SESSION--> state_db
    hft_orch --SAI_OBJECT_TYPE_TAM_XXXX--> syncd
    syncd --TAM configuration--> dma_engine
    syncd --TAM configuration--> netlink_module
    counter_syncd -- counters --> counter_db
    counter_syncd -- OpenTelemetry message --> otel
    dma_engine --IPFIX record--> netlink_module
    netlink_module --IPFIX record--> counter_syncd
    asic --counters--> dma_engine
    syncd --IPFIX template--> hft_orch
```

## 7. High-Level Design

### 7.1. Modules

#### 7.1.1. Counter Syncd

The `counter syncd` is a new process that runs within the swss container. Its primary responsibility is to receive counter messages via netlink and push them into the OpenTelemetry collector and Counter DB. It subscribes to a socket of a specific family and multicast group of generic netlink. The configuration for generic netlink is defined as constants in `/etc/sonic/constants.yml` as follows.

``` yaml

constants:
    high_frequency_telemetry:
        genl_family: "sonic_stel"
        genl_multicast_group: "ipfix"

```

- Architecture for CounterSyncd:

``` mermaid

flowchart LR
    swss_act((Swss actor: Handle swss message))
    netlink_act((Netlink actor: Receive netlink message from kernel))
    ipfix_act((Ipfix actor: Handle IPFix message))
    cdb_act((Counter DB actor: Store counters to counter DB))
    otel_act((OpenTelemetry actor: Send counters to OpenTelemetry collector))
    cdb[(Counter DB)]
    otel(((OpenTelemetry Collector)))

    swss_act -- IPFix Template --> ipfix_act
    netlink_act -- IPFix Record --> ipfix_act
    ipfix_act -- Counters --> cdb_act
    ipfix_act -- Counters --> otel_act
    cdb_act -- ObjectID-Counters Pair --> cdb
    cdb -. Lazy load: COUNTERS_*_MAP(ObjectID-Name Map) .-> cdb_act
    otel_act -- OpenTelemetry Message --> otel

```

#### 7.1.2. High frequency telemetry Orch

The `High frequency telemetry Orch` is a new object within the Orchagent. It has following primary duties:

1. Maintain the TAM SAI objects according to the high frequency telemetry configuration in the config DB.
2. Generate a unique template ID for each high frequency telemetry profile to ensure distinct identification and management.
3. Register and activate streams on counter syncd.

`High frequency telemetry Orch` leverages `tam_counter_subscription` objects to bind monitoring objects, such as ports, buffers, or queues, to streams. Therefore, this orch must ensure that the lifecycle of `tam_counter_subscription` objects is within the lifecycle of their respective monitoring objects.

#### 7.1.3. Netlink Module and DMA Engine

These two modules need to be provided by vendors. Meanwhile, the new genetlink family and group will be registered through the kernel module provided by the vendor .This document proposes a ring buffer communication model to support all expected TAM configurations as follows.

![netlink_dma_channel](netlink_dma_channel.drawio.svg)

#### 7.1.4. OpenTelemetry Collector (Existing open source solution)

The OpenTelemetry Collector serves as a critical component in modern observability pipelines, acting as a vendor-agnostic middleware that receives, processes, and exports telemetry data. One of OpenTelemetry Collector's key strengths is its flexibility in supporting various open-source telemetry data formats, such as Jaeger and Prometheus, and exporting them to multiple open-source or commercial back-ends.

The collector is deployed as a Docker container with the following responsibilities:

- Receivers: Accepts OTLP metrics via OTLP/gRPC protocol
- Processors: Batches metrics for efficient transmission
- Exporters: Forwards metrics to backend databases for storage and visualization

``` mermaid

flowchart TD;
    CS[CounterSyncd] -->|OTLP/gRPC| R
    subgraph OpenTelemetry Collector
        R[Receivers] --> P[Processors] --> E[Exporters]
    end
    BS@{ shape: fork, label: "Backend service" }
    subgraph Backend Service
        IDB[InfluxDB]
        PM[Prometheus]
        OTH[Other Options]
    end
    E --> |HTTP/API|BS
    BS --> IDB
    BS --> PM
    BS --> OTH

```

For further details on OpenTelemetry and OpenTelemetry Collector, please refer to the official documentation:

- [What is OpenTelemetry?](https://opentelemetry.io/docs/what-is-opentelemetry/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)

### 7.2. Data format

We will use IPFIX as the report format, with all numbers in the IPFIX message in network-order (Big-endian).

For more information on IPFIX, refer to the following resources:

- [Specification of the IP Flow Information Export (IPFIX) Protocol for the Exchange of Flow Information](https://datatracker.ietf.org/doc/html/rfc7011)
- [IP Flow Information Export (IPFIX) Entities](https://www.iana.org/assignments/ipfix/ipfix.xhtml)

#### 7.2.1. IPFIX header

The `Version` and `Observation Domain ID` fields of the IPFIX header are identical for each IPFIX message.

``` mermaid

---
title: stream message IPFIX header
---
packet-beta
0-15: "Version = 0x000a"
16-31: "Message Length = (16 + payload) bytes"
32-63: "Export Timestamp: Second"
64-95: "Sequence Number = 0, start from 0 and incremental sequence counter modulo 2^32"
96-127: "Observation Domain ID = 0, always 0"

```

#### 7.2.2. IPFIX template

``` mermaid

---
title: stream message of IPFIX template
---
packet-beta
0-15: "Set ID = 2"
16-31: "Set Length = (12 + Number of Stats * 8) bytes"
32-47: "Template ID = > 256 configured"
48-63: "Number of Fields = 1 + Number of stats"
64-79: "Element ID=observationTimeNanoseconds (325)"
80-95: "Field length = 8 bytes"
96-96: "1"
97-111: "Element ID = Object index for the stats 1"
112-127: "Field Length = 8 bytes"
128-159: "Enterprise Number = SAI TYPE ID + SAI STATS ID for the stats 1"
160-191: "..."
192-192: "1"
193-207: "Element ID = Object index for the stats N"
208-223: "Field Length = 8 bytes"
224-255: "Enterprise Number = SAI TYPE ID + SAI STATS ID for the stats N"

```

- For high-frequency counters, the native IPFIX timestamp unit of seconds is insufficient. Therefore, we introduce an additional element, `observationTimeNanoseconds`, for each record to meet our requirements.
- The element ID of IPFIX is generated by the orchagent and ranges from 0x8000-0xFFFF. Orchagent will ensure the uniqueness of the element ID in each template.
- The enterprise number is derived from the combination of the [SAI_OBJECT_TYPE](https://github.com/opencomputeproject/SAI/blob/master/inc/saitypes.h) and its corresponding stats ID. The high bits are used to indicate the SAI extension flag. For example, for `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS=0x00000022` of `SAI_OBJECT_TYPE_QUEUE=0x00000015`, the enterprise number will be `0x00000022 << 16 | 0x00000015 = 0x00220015`.

``` mermaid
---
title: Enterprise number encoding
---
packet-beta
0: "EF"
1-15: "SAI TYPE ID"
16: "EF"
17-31: "SAI STATS ID"

```

**EF is the extension flag: If this type or stat is an SAI extension, it should be set to 1.**

For example, if the switch has 8 ports, but we only want to get the `SAI_PORT_STAT_IF_IN_ERRORS = 0x00000004` of `SAI_OBJECT_TYPE_PORT = 0x00000001` on Ethernet2 and Ethernet5, the template will look like this:

``` mermaid

packet-beta
0-15: "Set ID = 2"
16-31: "Set Length = 28 bytes"
32-47: "Template ID = 256"
48-63: "Number of Fields = 3"
64-79: "Element ID=325"
80-95: "Field length = 4 bytes"
96-96: "1"
97-111: "Element ID = 2 (port index)"
112-127: "Field Length = 8 bytes"
128-159: "Enterprise Number = 0x00010004"
160-160: "1"
161-175: "Element ID = 5 (port index)"
176-191: "Field Length = 8 bytes"
192-223: "Enterprise Number = 0x00010004"

```

#### 7.2.3. IPFIX data

An IPFIX data message consists of snapshots that is a binary block that can be interpreted using the IPFIX template mentioned above.

The binary structure of a snapshot is as follows:

``` mermaid

---
title: A snapshot of IPFIX data
---
packet-beta
0-15: "Set ID = Same as template ID"
16-31: "Set Length = (4 + 8 + Number of stats * 8) bytes"
32-95: "Data 1: observationTimeNanoseconds"
96-127: "Data 2: Stats 1"
128-159: "..."
160-191: "Data N + 1: Stats N"
```

- The snapshot structure is derived from the IPFIX template, which is based on the stats we want to record.

Below is an example of an IPFIX message with 3 snapshots for the same stats record as the IPFIX template example:

``` mermaid

---
title: stream message IPFIX
---
packet-beta
0-15: "Version = 0x000a"
16-31: "Message Length = 112 bytes"
32-63: "Export Timestamp = 2024-08-29 20:30:60"
64-95: "Sequence Number = 1"
96-127: "Observation Domain ID = 0"

128-143: "Set ID = 256"
144-159: "Set Length = 36 bytes"
160-223: "observationTimeNanoseconds = 10000"
224-287: "Port 1: SAI_PORT_STAT_IF_IN_ERRORS = 10"
288-351: "Port 2: SAI_PORT_STAT_IF_IN_ERRORS = 0"
352-415: "Port 3: SAI_PORT_STAT_IF_IN_ERRORS = 5"

416-431: "Set ID = 256"
432-447: "Set Length = 36 bytes"
448-511: "observationTimeNanoseconds = 20000"
512-575: "Port 1: SAI_PORT_STAT_IF_IN_ERRORS = 15"
576-639: "Port 2: SAI_PORT_STAT_IF_IN_ERRORS = 0"
640-703: "Port 3: SAI_PORT_STAT_IF_IN_ERRORS = 6"

704-719: "Set ID = 256"
720-735: "Set Length = 36 bytes"
736-799: "observationTimeNanoseconds = 30000"
800-863: "Port 1: SAI_PORT_STAT_IF_IN_ERRORS = 20"
864-927: "Port 2: SAI_PORT_STAT_IF_IN_ERRORS = 0"
928-991: "Port 3: SAI_PORT_STAT_IF_IN_ERRORS = 8"

```

- If the number of stats in a group is small, multiple snapshots may be encoded into a single IPFIX message.
- If the number of stats in a group exceeds 8K, the group must be split across multiple IPFIX messages.

The IPFIX template should be provided by vendors. This document does not restrict how to split or concatenate snapshots, but each separated snapshot must include its own `observationTimeNanoseconds`.

#### 7.2.4. Netlink message

We expect all control messages and out-of-band information to be transmitted by the SAI. Therefore, it is unnecessary to read the attribute header of netlink and the message header of Genetlink from the socket. Instead, we can insert a bulk of IPFIX recordings as the payload of the netlink message. The sample code for building the message from the kernel side is as follows:

``` c

struct genl_multicast_group stel_mcgrps[] = {
    { .name = "ipfix" },
};

// Family definition
static struct genl_family stel_family = {
    .name = "sonic_stel",
    .version = 1,
    // ...
    .mcgrps = stel_mcgrps,
    .n_mcgrps = ARRAY_SIZE(stel_mcgrps),
};


void send_msgs_to_user(/* ... */)
{
    struct sk_buff *skb_out = nlmsg_new(ipfix_msg_len, GFP_KERNEL);

    for (size_t i = 0; i < bulk_count; i++)
    {
        struct ipfix *msg = ring_buffer.pop();
        if (msg == NULL)
        {
            break;
        }
        nla_append(skb_out, msg->data, msg->len);
    }

    genlmsg_multicast(&stel_family, skb_out, 0, 0/* group_id to ipfix group */, GFP_KERNEL);
}

```

#### 7.2.5. OTLP message

OTLP gauge metrics represent a measurement at a specific point in time. Unlike counters, gauges can increase and decrease, making them suitable for metrics like buffer occupancy, port status, and other instantaneous measurements.

Gauge metrics in OTLP usually consist of:

- Metric Name: Unique identifier (e.g., buffer_pool.dropped_packets)
- Data Points: A single metric (identified by name) can contain multiple data points. Each data point includes:
  - Attributes: Key-value pairs providing context (e.g., object_name="Ethernet1|3")
  - Timestamp(time_unix_nano): When the measurement was taken
  - Value: The actual measurement

Example of a simplified OTLP metric:

```
Metric {
  name: "buffer_pool.dropped_packets",
  description: "SAI counter statistic",
  unit: "",
  data: Gauge {
    data_points: [
      {
        attributes: [
          { key: "object_name", value: "Ethernet1|3" }
        ],
        time_unix_nano: 2,
        value: 2
      }
    ]
  }
}
```

For design goals, requirements, and specification of the OTLP, please refer to the official documentation: [OpenTelemetry Protocol (OTLP)](https://github.com/open-telemetry/opentelemetry-proto/tree/main/docs).

For practical OTLP message examples and implementation patterns, see the examples in the OpenTelemetry repository: [OpenTelemetry Protocol Examples](https://github.com/open-telemetry/opentelemetry-proto/tree/main/examples).

### 7.3. Bandwidth Estimation

We estimate the bandwidth based only on the effective data size, not the actual data size. The extra information in a message, such as the IPFIX header (16 bytes), data prefix (4 bytes), and observation time nanoseconds (8 bytes), is negligible. For example, a IPFIX message could include $The Maximal Number Of Counters In One Message = \frac{0xFFFF_{Max Length Bytes} - 16_{Header Bytes} - 4_{DataPrefix Bytes} - 8_{Observation Time Nanoseconds Bytes}}{8_{bytes}} \approx 8188$, So $The Percentage Of Effective Data = \frac{0xFFFF_{Max Length Bytes} - 16_{Header Bytes} - 4_{DataPrefix Bytes} - 8_{Observation Time Nanoseconds Bytes}} {0xFFFF_{Max LengthBytes}} \approx 99.9\%$ .

The following table is an example of telemetry bandwidth of one cluster

| # of stats per port | # of ports per switch | # of switch | frequency (us) | Total BW per switch(Mbps) | Total BW(Mbps) |
| ------------------- | --------------------- | ----------- | -------------- | ------------------------- | -------------- |
| 30                  | 64                    | 10,000      | 10             | 12,288                    | 122,880,000    |

- /$/{Total BW Per Switch/} = \frac/{/{\verb|#| Of Stats Per Port/} \times 8_/{bytes/} \times /{\verb|#| Of Ports Per Switch/} \times /{Frequency/} \times 1,000 \times 8/}/{1,000,000/}$
- /$/{Total BM/} = /{Total BW Per Switch/} \times /{\verb|#| Of Switch/}/$

### 7.4. Config DB

Any configuration changes in the config DB will interrupt the existing session and initiate a new one.

#### 7.4.1. DEVICE_METADATA

```
DEVICE_METADATA|localhost
    "high_frequency_telemetry_chunk_size": {{uint32}}
    "high_frequency_telemetry_chunk_count": {{uint32}} (Optional)
```

```
; field                      = value
high_frequency_telemetry_chunk_size  = uint32; reporting byte size of chunk under the high frequency telemetry.
high_frequency_telemetry_chunk_count = uint32; chunk count under the high frequency telemetry. Some platforms may not support setting this value.
```

#### 7.4.2. HIGH_FREQUENCY_TELEMETRY_PROFILE

```
HIGH_FREQUENCY_TELEMETRY_PROFILE|{{profile_name}}
    "stream_state": {{enabled/disabled}}
    "poll_interval": {{uint32}}
    "otel_endpoint": {{string of endpoint}} (Optional)
    "otel_certs": {{string of path}} (Optional)
```

```
key                = HIGH_FREQUENCY_TELEMETRY_PROFILE|profile_name a string as the identifier of high frequency telemetry
; field            = value
stream_state       = enabled/disabled ; Enabled/Disabled stream.
poll_interval      = uint32 ; The interval to poll counter, unit microseconds.
otel_endpoint      = string ; The endpoint of OpenTelemetry collector. E.G. 192.168.0.100:4318.
                     It will use the local OpenTelemetry collector if this value isn't provided.
otel_certs         = string ; The path of certificates for OpenTelemetry collector. E.G. /etc/sonic/otel/cert.private
                     If this value isn't provided, we will use a non-secure channel.
```

#### 7.4.3. HIGH_FREQUENCY_TELEMETRY_GROUP

```
HIGH_FREQUENCY_TELEMETRY_GROUP|{{profile_name}}|{{group_name}}
    "object_names": {{list of object name}}
    "object_counters": {{list of stats of object}}
```

```
key             = HIGH_FREQUENCY_TELEMETRY_GROUP|group_name|profile_name
                    ; group_name is the object type, like PORT, BUFFER_PG or BUFFER_POOL.
                    ; Multiple groups can be bound to a same high frequency telemetry profile.
; field         = value
object_names    = A list of object name.
                    ; The syntax of object name is top_object_name|index.
                    ; The object_name is the object of the top level, like port, Ethernet0,Ethernet4, or buffer pool, egress_lossless_pool,ingress_zero_pool.
                    ; The index indicates the object in second level, like priority group.
                    ; An example is Ethernet0|0,Ethernet4|3.
object_counters = A list of stats of object;
```

For the schema of `HIGH_FREQUENCY_TELEMETRY_GROUP`, please refer to its [YANG model](sonic-high-frequency-telemetry.yang).

### 7.5. StateDb

#### 7.5.1. HIGH_FREQUENCY_TELEMETRY_SESSION

```
HIGH_FREQUENCY_TELEMETRY_SESSION|{{profile_name}}|{{group_name}}
    "session_status": {{enabled/disabled}}
    "object_names": {{list of object name}}
    "object_ids": {{list of uint16_t}}
    "session_type": {{ipfix}}
    "session_config": {{binary array}}
    "config_version": {{uint32_t}}
```

```
key                 = HIGH_FREQUENCY_TELEMETRY_SESSION:profile_name ; a string as the identifier of high frequency telemetry
; field             = value
session_status      = enable/disable ; Enable/Disable stream.
object_names        = A list of object name.
                      Same as the list of object_names of HIGH_FREQUENCY_TELEMETRY_GROUP in config db
object_ids          = A list of object ID;
                      A IDs list that is generated by orchagent.
                      The IDs in object_ids will correspond one-to-one with the above names in object_names.
session_type        = ipfix ; Specified the session type.
session_config      = binary array;
                      If the session type is IPFIX, This field stores the IPFIX template to interpret the message of this session.
config_version      = uint32_t; Indicates which version is being used. The default value is 0.
                      This value will be increased once the new config was applied by CounterSyncd.
```

### 7.6. Work Flow

``` mermaid

sequenceDiagram
    autonumber
    box Redis
        participant config_db as CONFIG_DB
        participant state_db as STATE_DB
    end
    box OpenTelemetry container
        participant otel as OpenTelemetry Collector
        participant counter as counter syncd
    end
    box SWSS container
        participant port_orch as Port Orch
        participant hft_orch as High Frequency Telemetry Orch
    end
    box SYNCD container
        participant syncd
    end
    box Linux Kernel
        participant netlink_module as Netlink module
        participant dma_engine as DMA Engine
    end
    participant asic as ASIC

    counter --> counter: Initialize genetlink
    hft_orch ->> syncd: Initialize <br/>HOSTIF<br/>TAM_TRANSPORT<br/>TAM_collector<br/>

    config_db ->> hft_orch: HIGH_FREQUENCY_TELEMETRY_PROFILE
    config_db ->> hft_orch: HIGH_FREQUENCY_TELEMETRY_GROUP
    port_orch ->> hft_orch: Port/Queue/Buffer ... object

    hft_orch ->> syncd: Config TAM objects

    syncd ->> dma_engine: Config stats
    syncd ->> hft_orch: Config was applied in the ASIC
    syncd ->> hft_orch: Query IPFIX template
    hft_orch ->> state_db: Update HIGH_FREQUENCY_TELEMETRY_SESSION
    state_db ->> counter: Register IPFIX template
    counter ->> state_db: Update config version
    state_db ->> hft_orch: Notify config version

    alt Is stream status enabled?

        hft_orch ->> syncd: Start telemetry stream

        loop Push stats until stream disabled
            loop collect a chunk of stats
                dma_engine ->> asic: query stats from asic
                asic --) dma_engine: stats
                dma_engine ->> netlink_module: Push stats in IPFIX format
            end
            alt counter syncd is ready to receive?
                netlink_module ->> counter: Push a chunk of stats with IPFIX message
            else
                netlink_module ->> netlink_module: Save data to buffer. if buffer is full, discard
            end
        end
    else
        hft_orch ->> syncd: Disable telemetry stream
        syncd ->> dma_engine: Stop stream
        hft_orch ->> state_db: Update HIGH_FREQUENCY_TELEMETRY_SESSION
        state_db ->> counter: Unrigster IPFIX template
    end
    loop Receive IPFIX message of stats from genetlink
        alt Have this template of IPFIX been registered?
            counter ->> otel: Push message to OpenTelemetry Collector
        else
            counter ->> counter: Discard this message
        end
    end

```

### 7.7. SAI API

[SAI-Proposal-TAM-stream-telemetry.md](https://github.com/opencomputeproject/SAI/blob/master/doc/TAM/SAI-Proposal-TAM-stream-telemetry.md)

## 8. Configuration and management

### 8.1. Manifest (if the feature is an Application Extension)

N/A

### 8.2. CLI/YANG model Enhancements

#### 8.2.1. Config CLI

``` shell

# Add a new profile
sudo config high_frequency_telemetry profile add $profile_name --stream_state=$stream_state --poll_interval=$poll_interval --chunk_size=$chunk_size --chunk_count=$chunk_count --otel_endpoint=$otel_endpoint --otel_certs=$otel_certs

# Change stream state
sudo config high_frequency_telemetry profile set $profile_name --stream_state=$stream_state

# Add a monitor group
sudo config high_frequency_telemetry group "$profile|$group_name" --object_names="$object1,$object2" --object_counters="$object_counters1,$object_counters2"

```

#### 8.2.2. Inspect stream CLI

Fetch all counters on the high-frequency-telemetry

``` shell
sudo high-frequency-telemetry $profile_name --json/--table --duration=$duration
```

#### 8.2.3. YANG

[sonic-high-frequency-telemetry.yang](sonic-high-frequency-telemetry.yang)

### 8.3. Config DB Enhancements

[Config DB](#config-db)

### 8.4. Warmboot and Fastboot Design Impact

Warmboot/fastboot support is not required.

### 8.5. Memory Consumption

In addition to constant memory consumption, dynamic memory consumption can be adjusted by configuring the chunk size and chunk count of the high frequency telemetry profile table in the config DB.

$Dynamic Memory Consumption_{bytes} = \sum_{Profile} ({Chunk count} \times {Chunk Size} \times 8_{bytes} \times \sum_{Group} ({Object Count} \times {Stat Count}))$

### 8.6. Restrictions/Limitations

[Requirements / Constraints](#requirements--constraints)

### 8.7. Testing Requirements/Design

#### 8.7.1. Unit Test cases

- Test that the `HIGH_FREQUENCY_TELEMETRY_GROUP` can be correctly converted to the SAI objects and their corresponding SAI STAT IDs by the Orchagent.

#### 8.7.2. System Test cases

- Test that the counter can be correctly monitored by the counter syncd.
- Verify that the chunk size is accurate when reading messages from the netlink socket.
- By restarting counter syncd, verify whether the cached data during the restart corresponds to the chunk count.
- Ensure that counters can be correctly retrieved using the high frequency telemetry CLI.

### 8.8. Open/Action items - if any
