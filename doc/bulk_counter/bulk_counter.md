# SONiC Bulk Counter Design #

## Table of Content

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |
 | 0.2 | Dec 6, 2024 |        Stephen Sun | Support setting bulk chunk size   |

### Scope

This document is the design document for bulk counter feature on SONiC.

### Definitions/Abbreviations

N/A

### Overview

PR https://github.com/opencomputeproject/SAI/pull/1352/files introduced new SAI APIs that supports bulk stats:

- sai_bulk_object_get_stats
- sai_bulk_object_clear_stats

SONiC flex counter infrastructure shall utilize bulk stats API to gain better performance. This document discusses how to integrate these two new APIs to SONiC.

### Requirements

- Syncd shall use bulk stats APIs based on object type. E.g. for a counter group that queries queue and pg stats, queue stats support bulk while pg stats does not, in that case queue stats shall use bulk API, pg stats shall use non bulk API
- For a certain object in a counter group, it shall use bulk stats only if all counter IDs support bulk API
- Syncd shall automatically fall back to old way if bulk stats APIs are not supported
- Syncd shall utilize sai_bulk_object_get_stats/sai_bulk_object_clear_stats to query bulk capability. Syncd shall treat counter as no bulk capability if API return error
- Syncd shall call bulk stats API in flex counter thread and avoid calling it in main thread to make sure main thread only handles short and high priority tasks. (This is the default behavior in current flex counter infrastructure)
- In phase 1, the change is limited to syncd only, no CLI/swss change. Syncd shall deduce the bulk stats mode according to the stats mode defined in FLEX DB:
  - SAI_STATS_MODE_READ -> SAI_STATS_MODE_BULK_READ
  - SAI_STATS_MODE_READ_AND_CLEAR -> SAI_STATS_MODE_BULK_READ_AND_CLEAR
- Support setting bulk chunk size for the whole counter group or a sub set of counters.

  Sometimes it can be time consuming to poll a group of counters for all ports in a single bulk counter polling API, which can cause time-sensitive counter groups polling miss deadline if both counter groups compete a critical section in vendor's SAI/SDK.
  To address the issue, the bulk counter polling can be split into smaller chunk sizes. Furthermore, different counters within a same counter group can be split into different chunk sizes.

  By doing so, all the counters of all ports will still be polled in each interval but it will be done by a lot of smaller bulk counter polling API calls, which makes it faster and the time-sensitive counter group have more chance to be scheduled on time.
- Provide an accurate timestamp when counters are polled.

  Currently, the timestamps are collected in the Lua plugin for time-sensitive counter groups, like PFC watchdog. However, there can be a gap between the time when the counters were polled and the timestamps were collected.
  We can collect timestamps immediately after polling counters in sairedis and push them into the COUNTER_DB.

### Architecture Design

For each counter group

1. different statistic type is allowed to choose bulk or non-bulk API based on vendor SAI implementation.
2. bulk chunk size can be configure for the group of a set of counters in the group

![architecture](bulk_counter.svg).

> Note: In the picture,
> 1. PG/queue watermark statistic use bulk API and buffer watermark statistic uses non-bulk API.
> 2. Ports statistic counters are split into smaller chunks: IF_OUT_QLEN counter is polled for all ports and the rest counters are polled for each 32-port group
> 3. This is just an example to show the design idea.

### High-Level Design

Changes shall be made to sonic-sairedis to support this feature. No CLI change.

> Note: Code present in this design document is only for demonstrating the design idea, it is not production code.

#### sonic-sairedis

##### Bulk Statistic Context

A new structure shall be added to FlexCounter class.

This structure is created because:

- Meet the signature of sai_bulk_object_get_stats and sai_bulk_object_clear_stats
- Avoid constructing these information each time collecting statistic. The bulk context shall only be updated under below cases:
  - New object join counter group. E.g. adding a new port object.
  - Existing object leave counter group. E.g removing an existing port object.
  - Other case such as counter IDs is updated by upper layer.

```cpp
struct BulkStatsContext
/{
    sai_object_type_t object_type;
    std::vector<sai_object_id_t> object_vids;
    std::vector<sai_object_key_t> object_keys;
    std::vector<sai_stat_id_t> counter_ids;
    std::vector<sai_status_t> object_statuses;
    std::vector<uint64_t> counters;
    std::string name;
    uint32_t default_bulk_chunk_size;
/};
```
- object_type: object type.
- object_vids: virtual IDs.
- object_keys: real IDs.
- counter_ids: SAI statistic IDs that will be queried/cleared by the bulk call.
- object_statuses: SAI bulk API return value for each object.
- counters: counter values that will be fill by vendor SAI.
- name: name of the context for pushing accurate timestamp into the COUNTER_DB.
- default_bulk_chunk_size: the bulk chunk size of this context.

The flow of how to updating bulk context will be discussed in following section.

For a given object type, different object instance may support different stats capability, so, a map of BulkStatsContext shall be added to FlexCounter class for each object type.

```cpp
std::map<std::vector<sai_port_stat_t>, BulkStatsContext> m_portBulkContexts;
...

```

##### Set bulk chunk size for a counter group and per counter IDs

The bulk chunk size can be configured for a counter group. Once configured, each bulk will poll counters of no more than the configured number of ports.

Furthermore, the bulk chunk size can be configured on a per counter IDs set basis using string in format `<COUNTER_NAME_PREFIX>:<bulk_chunk_size>/{,<COUNTER_NAME_PREFIX_I>:<bulk_chunk_size_i>/}`.
Each `COUNTER_NAME_PREFIX` defines a set of counter IDs by matching the counter IDs with the prefix. All the counter IDs in each set share a unified bulk chunk size and will be polled in a series of bulk counter polling API calls with the same counter IDs set but different port set.
All such sets of counter IDs form a partition of counter IDs of the flex counter group. The partition of a flex counter group is represented by the keys of map `m_portBulkContexts`.

To simplify the logic, it is not supported to change the partition, which means it does not allow to split counter IDs into a differet sub sets once they have been split.

Eg. `SAI_PORT_STAT_IF_IN_FEC:32,SAI_PORT_STAT_IF_OUT_QLEN:0` represents

1. the bulk chunk size of all counter IDs starting with prefix `SAI_PORT_STAT_IF_IN_FEC` is 32
2. the bulk chunk size of counter `SAI_PORT_STAT_IF_OUT_QLEN` is 0, which mean 1 bulk will fetch the counter of all ports
3. the bulk chunk size of rest counter IDs is the counter group's bulk chunk size.

The counter IDs will be split to a partition which consists of a group of sub sets /`/{/{all FEC counters starting with SAI_PORT_STAT_IF_IN_FEC/}, /{SAI_PORT_STAT_IF_OUT_QLEN/}, /{the rest counters/}/}/`.
The counter IDs in each sub set share the unified bulk chunk size and will be poll together.

In the above example, once the bulk chunk size is set in the way, a customer can only changes the bulk size of each set but can not change the way the sub sets are split. Eg.

1. `SAI_PORT_STAT_IF_IN_FEC:16,SAI_PORT_STAT_IF_OUT_QLEN:0` can be used to set the bulk chunk size to 16 and 0 for of all FEC counters and counter `SAI_PORT_STAT_IF_OUT_QLEN` respectively.
2. `SAI_PORT_STAT_IF_IN_FEC:16,SAI_PORT_STAT_IF_OUT_QLEN:0,SAI_PORT_STAT_ETHER_STATS:64` is not supported because it changes the partition.

##### Update Bulk Context

1. New object join counter group.

![Add Object Flow](object_join_counter_group.svg).

2. Existing object leave counter group, related data shall be removed from bulk context.

![Remove Object Flow](object_leave_counter_group.svg).

3. A customer split the chunk size of bulk counter polling to different smaller sizes per counter IDs.

![Set chunk size per counter ID](set_chunk_size_per_counter_ID.svg).

##### Statistic Collect

![Collect Counter Flow](counter_collect.svg).

### SAI API

SAI APIs shall be used in this feature:

- sai_bulk_object_get_stats
- sai_bulk_object_clear_stats

### Configuration and management

#### YANG model Enhancements

##### Yang model of flex counter group

The following new types will be introduced in `container FLEX_COUNTER_TABLE` of the flex counter group

```
    container sonic-flex_counter /{
        container FLEX_COUNTER_TABLE /{

            typedef bulk_chunk_size /{
                type uint32 //{
                    range 0..4294967295;
                /}
            /}

            typedef bulk_chunk_size_per_prefix /{
                type string;
                description "Bulk chunk size per counter name prefix";
            /}

        /}
    /}
```

In the yang model, each flex counter group is an independent countainer. We will define leaf in the countainer `PG_DROP`, `PG_WATERMARK`, `PORT`, `QUEUE`, `QUEUE_WATERMARK`.
The update of `PG_DROP` is shown as below

```
            container PG_DROP /{
                /* PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP */
                leaf BULK_CHUNK_SIZE /{
                    type bulk_chunk_size;
                /}
                leaf BULK_CHUNK_SIZE_PER_PREFIX /{
                    type bulk_chunk_size_per_prefix;
                /}
            /}
```

### Warmboot and Fastboot Design Impact

No extra logic on SONiC side is needed to handle warmboot/fastboot.

- As fastboot delays all counters querying, this feature does not affect fastboot.
- For warmboot, it is vendor SAI implementation's responsible to make sure that there must be no error if warmboot starts while bulk API is called.

### Restrictions/Limitations

- Bulk collect attribute value is not supported
- Buffer pool stats is not support for bulk because different buffer pool may have different stats mode. E.g. pool1 has mode SAI_STATS_MODE_READ, pool2 has mode SAI_STATS_MODE_READ_AND_CLEAR. The new SAI bulk API only allows specify one stats mode.
- Maximum object number at one bulk call is a limitation based on vendor implementation.

### Performance Improvement

A rough test has been done on Nvidia platform for queue.

- Non bulk API: get stats for one queue takes X seconds; get stats for 32 port * 8 queue is 256X seconds;
- Bulk API: get stats for one queue takes Y seconds; get stats for 32 port * 8 queue is almost Y seconds;

X is almost equal to Y. So, more object instances, more performance improvement.

### Testing Requirements/Design

As this feature does not introduce any new function, unit test shall be good enough to cover the code changes and new sonic-mgmt/VS test cases will be added.

#### Unit Test cases

- addRemoveBulkCounter
- counterIdChange
  - not support bulk -> support bulk
  - support bulk but counter IDs change
  - support bulk with different counter IDs
  - support bulk -> not support bulk
  - not support bulk but counter IDs change

### Appendix

#### An example shows how smaller bulk chunk size helps

![Smaller bulk chunk size](smaller_chunk_size.svg)

An example shows how smaller bulk chunk size helps PFC watchdog counter polling thread to be scheduled in time.

In the upper chart, the port counters are polled in a single bulk call which takes longer time. The PFC watchdog counter polling thread can not procceed until the long bulk call exits the critical section.

In the lower chart, the port counters are polled in a series of bulk call with smaller bulk chunk sizes. The PFC watchdog counter polling thread has more chance to be scheduled in time.
