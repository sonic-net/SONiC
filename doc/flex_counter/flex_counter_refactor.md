# SONiC FlexCounter Refactor #

## Table of Content

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

### Scope

This document is the design document for refactoring FlexCounter class in syncd of sonic-sairedis.

### Definitions/Abbreviations

N/A

### Overview

FlexCounter class is a representation of flex counter group which supports querying multiple types of statistic/attributes. It supports multiple statistic/attribute types such as port counter, port debug counter, queue counter, queue attribute and so on. For each statistic/attribute type, it defines several member functions:

- setXXXCounterList: e.g. setPortCounterList, setPortDebugCounterList
- removeXXX: e.g. removePort, removeQueue
- collectXXXCounters: e.g. collectPortCounters, collectQueueCounters
- collectXXXAttr: e.g. collectQueueAttrs, collectPriorityGroupAttrs
- so on

For different statistic/attribute types, these functions have very similar logic. This design document describes a proposal about how to refactor FlexCounter class by moving duplicate/similar logic to a single place.

#### Challenge

The major challenge of this refactor is that, different statistic/attributes types may have different SAI type. E.g. type of port counter is sai_port_stat_t, type of queue counter is sai_queue_stat_t, type of queue attribute is sai_port_attr_t. C++ does not allow to put different type of object into the same container.

#### Benefit

A POC shows that, the refactor brings a few benefits:

- Code lines of FlexCounter.cpp change from ~4000 to ~1000
- Code lines of FlexCounter.h change from ~600 to ~200
- Supporting new flex counter would requires only change a few places instead of implementing all those setXXXCounterList/removeXXX/collectXXXCounter and so on

### Requirements

- The change shall be limited in FlexCounter class
- Public interfaces of FlexCounter class shall keep the same functional
- Other class/component of SONiC shall treat this change as transparent

### Architecture Design

Current design of FlexCounter class:

![flex_counter_current](/doc/flex_counter/flex_counter_current.svg).

New design:

![flex_counter_new](/doc/flex_counter/flex_counter_new.svg).

### High-Level Design

Changes shall be made into sonic-sairedis. Affected files are: FlexCounter.cpp, FlexCounter.h. This chapter will describe that how the new architecture can perfectly replace the old functions.

> Note: Code present in this design document is only for demonstrating the design idea, it is not production code.

#### sonic-sairedis

##### Store Counter Related Data

Currently, there are several types of counter related data.

- Counter IDs map: stores object vid, rid and a list of counter IDs that will be queried. E.g. m_portCounterIdsMap, m_queueCounterIdsMap...
- Plugins: stores redis lua SHA values that will be execute by redis. E.g. m_portPlugins, m_queuePlugins...
- Supported counters: stores supported counter IDs. E.g. m_supportedPortCounters, m_supportedQueueCounters...

In the new design, each statistic/attribute type is represented by an instance of CounterContext<T>/AttrContext<T> which will be stored in counter_context_map. These data members are moved to CounterContext<T> and AttrContext<T> as data members:

- object_ids_map
- plugins
- supported_counters

##### Counter IDs Structure

Currently, a few similar structures are defined in FlexCounter to represent rid, counter IDs as well as stats mode.

```cpp
struct QueueCounterIds
{
    QueueCounterIds(
            _In_ sai_object_id_t queue,
            _In_ const std::vector<sai_queue_stat_t> &queueIds);

    sai_object_id_t queueId;
    std::vector<sai_queue_stat_t> queueCounterIds;
};

struct PortCounterIds
{
    PortCounterIds(
            _In_ sai_object_id_t port,
            _In_ const std::vector<sai_port_stat_t> &portIds);

    sai_object_id_t portId;
    std::vector<sai_port_stat_t> portCounterIds;
};

struct BufferPoolCounterIds
{
    BufferPoolCounterIds(
            _In_ sai_object_id_t bufferPool,
            _In_ const std::vector<sai_buffer_pool_stat_t> &bufferPoolIds,
            _In_ sai_stats_mode_t statsMode);

    sai_object_id_t bufferPoolId;
    sai_stats_mode_t bufferPoolStatsMode;
    std::vector<sai_buffer_pool_stat_t> bufferPoolCounterIds;
};

...
```

In new design, two template structures are defined to replaces above structures. The second structure is for those statistic/attribute type which support per instance stats mode; the first structure is for other statistic/attribute type which use counter group level stats mode.

```cpp
template <typename StatType, 
          typename Enable = void>
struct CounterIds
{
    CounterIds(
            _In_ sai_object_id_t rid,
            _In_ const std::vector<StatType> &counter_ids
    ): rid(rid), counter_ids(counter_ids) {}
    sai_object_id_t rid;
    std::vector<StatType> counter_ids;
};

// CounterIds structure contains stats mode, now buffer pool is the only one
// has member stats_mode.
template <typename StatType>
struct CounterIds<StatType, typename std::enable_if<std::is_same<StatType, sai_buffer_pool_stat_t>::value>::type >
{
    CounterIds(
            _In_ sai_object_id_t rid,
            _In_ const std::vector<StatType> &counter_ids
    ): rid(rid), counter_ids(counter_ids) {}
    sai_object_id_t rid;
    std::vector<StatType> counter_ids;
    sai_stats_mode_t stats_mode;
};
```

##### Handle Counter Object Change

Each statistic/attribute type can have multiple counter objects. For example, Ethernet0 is a counter object of port statistic; Ethernet0 queue0 is a counter object of queue statistic. The most important information of a counter object are:

- rid: SAI ID of the object (Real ID)
- vid: Syncd ID of the object (Virtual ID)
- counter_ids: SAI statistic IDs

FlexCounter handles counter object change so that it queries relevant statistic/attribute from SAI.

##### Add/Update Counter Object

Currently, the flow of adding/updating counter object is like this:

1. FlexCounterManager calls FlexCounter::addCounter
2. In `addCounter`, it calls setXXXCounterList according to the input parameters
3. In `setXXXCounterList`, it updates supported counters
4. In `updateXXXSuportedCounters`, it query statistic capability via SAI API
5. If step 4 fails, it fall back to `getXXXSupportedCounters`, in which is query statistic value for each input counter IDs
6. If supported counters is not empty, update the counter object to a proper counter IDs map

In the new design, step 3 ~ step 6 are moved to CounterContext class, but the flow/function does not change at all. Here is the chart of the new design(the chart shows the design idea, it does not contain all details):  

![add_counter_object_flow](/doc/flex_counter/add_counter_object_flow.svg).

For different statistic type, the flow is similar, but not exactly the same. So, there are special cases shall be handled in implementation:

- Some statistic type query statistic capability via SAI API, while some do not. Need a flag in BaseCounterContext to handle this.
- Some statistic type always query statistic capability, while some only do it once. Need a flag in BaseCounterContext to handle this.
- Some statistic type use `getStats` querying statistic data, while some use `getStatsExt`. Need a flag in BaseCounterContext to handle this.
- Some statistic support per counter object stats mode, while some do not. Plan to use `if constexpr` to handle this.

##### Remove Counter Object

Currently, FlexCounter just remove counter object from m_XXXCounterIdsMap. In the new design, the flow/function is the same, but remove operation is moved to CounterContext/AttrContext. In new design, flow is like this:

![remove_counter_object_flow](/doc/flex_counter/remove_counter_object_flow.svg).

##### Handle Plugin Change

Currently, FlexCounter just add plugin to m_XXXPlugins. In new design, the flow/function is the same, but add operation is moved to BaseCounterContext. In new design, the flow is like this:

![add_plugin_flow](/doc/flex_counter/add_plugin_flow.svg).

##### Handle Statistic/Attribute Collect

Currently, FlexCounter collect counters by saving collectXXXCounters function pointer to a map and loop the map. In new design, that map is not needed anymore. New way:

```cpp
void FlexCounter::collectCounters(
        _In_ swss::Table &countersTable)
{
    for (const auto &it : m_counterContext)
    {
        it->second->collectData(countersTable);
    }

    countersTable.flush();
}
```

Currently, FlexCounter run redis plugins by looping each m_XXXPlugins one by one. New way:

```cpp
void FlexCounter::runPlugins(
        _In_ swss::DBConnector& counters_db)
{
    const std::vector<std::string> argv =
    {
        std::to_string(counters_db.getDbId()),
        COUNTERS_TABLE,
        std::to_string(m_pollInterval)
    };

    for (const auto &it : m_counterContext)
    {
        it->second->runPlugin(counters_db, argv);
    }
}
```

### SAI API

N/A

### Configuration and management

N/A

### Warmboot and Fastboot Design Impact

N/A

### Restrictions/Limitations

N/A

### Testing Requirements/Design

#### Unit Test cases

TBD
