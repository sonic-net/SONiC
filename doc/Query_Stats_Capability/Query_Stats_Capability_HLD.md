# Query Stats Capability new SAI API indroduction

# Table of Contents
- [Query Stats Capability new SAI API indroduction](#query-stats-capability-new-sai-api-indroduction)
- [Table of Contents](#table-of-contents)
- [Introduction and Motivation](#introduction-and-motivation)
- [Requirements](#requirements)
- [Code example](#code-example)

# Introduction and Motivation

- This document is to introduce a new API for query statistics capabilities of counters in a faster and more efficient way.
Currently on SONiC, in order to get the counters capabilities, SONiC is iterating all port stats one by one, to understand the supported capabilities.
This operation is time consuming and the new API can reduce the time for this operation in one call.

- This improvement is good to have in general for efficiency and a bulk read of counters capability, but even more important, it can reduce the time for time bound features like fast-reboot.

- New API is supporting all types of counters we use on SYNCD docker, for functions intending to update supported counters.

- The affected functions with this new API will take place on FlexCounter.cpp:
  - void updateSupportedPortCounters(_In_ sai_object_id_t portRid)
  - void updateSupportedQueueCounters(_In_ sai_object_id_t queueRid,_In_ const std::vector<sai_queue_stat_t> &counterIds)
  - void updateSupportedPriorityGroupCounters(_In_ sai_object_id_t priorityGroupRid,_In_ const std::vector<sai_ingress_priority_group_stat_t> &counterIds)
  - void updateSupportedRifCounters(_In_ sai_object_id_t rifRid)
  - void updateSupportedBufferPoolCounters(_In_ sai_object_id_t bufferPoolRid,_In_ const std::vector<sai_buffer_pool_stat_t> &counterIds,_In_ sai_stats_mode_t statsMode)

# Requirements

The implementation will support backwards compatibility, so if a SAI vendor is currently not supporting this API it will fall back to the legacy approach.
But, it will require all vendors either implement the API or return SAI_STATUS_NOT_IMPLEMENTED code to fall back to previous implementation.

# Code example

- Current implemenation:
```
for (int id = SAI_PORT_STAT_IF_IN_OCTETS; id <= SAI_PORT_STAT_IF_OUT_FABRIC_DATA_UNITS; ++id)
{
    sai_port_stat_t counter = static_cast<sai_port_stat_t>(id);
    sai_status_t status = m_vendorSai->getStats(SAI_OBJECT_TYPE_PORT, portRid, 1, (sai_stat_id_t *)&counter, &value);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_INFO("Counter %s is not supported on port RID %s: %s",
                sai_serialize_port_stat(counter).c_str(),
                sai_serialize_object_id(portRid).c_str(),
                sai_serialize_status(status).c_str());
        continue;
    }
    m_supportedPortCounters.insert(counter);
}
```

- New implemenation:
```
sai_stat_capability_list_t stats_capability;
stats_capability.count = 0;
stats_capability.list = nullptr;

/* First call is to check the size needed to allocate */
sai_status_t status = m_vendorSai->queryStatsCapability(
    portRid, 
    SAI_OBJECT_TYPE_PORT, 
    &stats_capability);

/* Second call is for query statistics capability */
if (status == SAI_STATUS_BUFFER_OVERFLOW)
{
    std::vector<sai_stat_capability_t> statCapabilityList(stats_capability.count);
    stats_capability.list = statCapabilityList.data();
    status = m_vendorSai->queryStatsCapability(
        portRid, 
        SAI_OBJECT_TYPE_PORT, 
        &stats_capability);
    
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_INFO("Unable to get port supported counters for %s", 
            sai_serialize_object_id(portRid).c_str());
    }
    else
    {
        for (auto statCapability: statCapabilityList)
        {
            sai_port_stat_t counter = static_cast<sai_port_stat_t>(statCapability.stat_enum);
            m_supportedPortCounters.insert(counter);
        }
    }
```

- From SAI headers:
```
/**
 * @brief Query statistics capability for statistics bound at object level
 *
 * @param[in] switch_id SAI Switch object id
 * @param[in] object_type SAI object type
 * @param[inout] stats_capability List of implemented enum values, and the statistics modes (bit mask) supported per value
 *
 * @return #SAI_STATUS_SUCCESS on success, #SAI_STATUS_BUFFER_OVERFLOW if lists size insufficient, failure status code on error
 */
sai_status_t sai_query_stats_capability(
        _In_ sai_object_id_t switch_id,
        _In_ sai_object_type_t object_type,
        _Inout_ sai_stat_capability_list_t *stats_capability);
```
