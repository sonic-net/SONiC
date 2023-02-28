# SONiC Trap Flow Counter Design #

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
  - [sonic-swss](#sonic-swss)
  - [sonic-sairedis](#sonic-sairedis)
  - [Flex Counter DB Enhancements](#flex-counter-db-enhancements)
  - [Counters DB Enhancements](#counters-db-enhancements)
- [SAI API](#sai-api)
- [Configuration and management ](#configuration-and-management)
  - [CLI/YANG model Enhancements](#cliyang-model-enhancements)
  - [Config DB Enhancements](#config-db-enhancements)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions/Limitations](#restrictions/limitations)
- [Testing Requirements/Design](#testing-requirements/design)
  - [Unit Test cases](#unit-test-cases)
  - [System Test cases](#system-test-cases)
- [Open/Action items - if any](#openaction-items---if-any)

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

### Scope

This document is the design document for host interface trap counter feature on SONiC. 

### Definitions/Abbreviations

N/A

### Overview

Flow counters are usually used for debugging, troubleshooting and performance enhancement processes. Flow counters could cover cases like:

- Host interface traps (number of received traps per Trap ID)
- Routes matching the configured prefix pattern (number of hits and number of bytes)
- FDB entries matching the configured VXLAN tunnel or using the VLAN ID as pattern
- Next-Hop/Next-Hop Group/Next-Hop Group Member

This document focus on host interface traps counter.

### Requirements

- Generic Counters shall be used as Flow Counters introduced by the feature
- CLI shall be used for configuration, showing and clearing of statistics
- Statistics of traps shall be enabled and disabled using the CLI commands (counterpoll)
- Polling interval shall be configured using the CLI commands (counterpoll)
- Statistics shall be enabled or disabled for all configured traps (not per-trap type)
- Statistics for traps shall be provided as a number of messages delivered from ASIC to host over the host interface per trap type
- Statistics shall be available for clearing (for all traps together) using the CLI command
- Statistic shall support number of trap packets/bytes and number of trap PPS
- Flow Counters shall be allocated/de-allocated on enabling/disabling traps via CLI or configuration files
- Flow Counters shall be allocated/de-allocated on dynamic configuration (register/un-register) of traps
- Flow Counters shall support multi ASIC

### Architecture Design

Flow counter shall utilize the following existing infrastructure:

- Generic Counters API - defined in https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-Proposal-Generic-Counters.md and already supported by the SAI layer. This feature shall support binding/unbinding of these Generic counters to/from relevant SONIC objects
- Flex Counters API - used for background polling and pushing the statistic information to COUNTER DB for later use (e.g. by CLI)

The following describes the configuration and flows for host interface traps counter:

![architecture](https://github.com/Junchao-Mellanox/SONiC/blob/flow-counter/doc/flow_counters/architecture.png)

(1) Customer uses the counterpoll CLI to enable/disable Flex Counters for Trap Flow Counter. If needed the default polling interval can be changed. The Flex Counter Orch Agent should be extended to support the Trap group. Configuration is pushed into CFG_FLEX_COUNTER_TABLE in CONFIG DB

(2) Flex Counter Orch Agent being subscribed to changes in CONFIG DB, gets a notification of changes and processes configuration for the Trap group pushing the status of a new group (for traps) and configured polling interval to the FLEX_COUNTER_GROUP_TABLE in the FLEX_COUNTER DB

(3) Copp Orch Manager being subscribed to changes in CFG_COPP_TRAP_TABLE in CONFIG DB, gets a notification of new registered traps and pushes it to the COPP_TABLE in APP DB

(4) Copp Orch Agent being subscribed to changes in COPP_TABLE in APP DB gets a notification of a new registered trap

(5) Copp Orch Agent creates a new trap using Host Interface SAI Redis API

(6) If Flow Counters are enabled for traps the Copp Orch Agent requests the Flow Counter (FC) Orch Agent to get a counter for the specified trap. It will use the trap name as symbolic ID for a counter

(7) Flow Counter handler checks if the counter for the specific traps already exists in its internal list. If it exists, then the Counter OID is returned to the Copp Arch Agent. Otherwise, the Flow Counter handler uses the Generic Counter SAI API to allocate a new counter. Upon getting the Counter OID from SAI the Flow Counter handler saves it in the internal list along with the Counter symbolic name and returns it to the Copp Orch Agent

(8) Copp Orch Agent uses the Host Interface SAI API to bind a counter (using its Counter OID) to the specific trap

(9) Copp Orch Agent adds the Counter OID (bound to the trap) to the FLOWCNT_TRAP_COUNTER_ID_LIST in FLEX_COUNTER DB. Additionally it stores the "Trap Name" to Counter OID mapping on COUNTER DB

(10) Flex Counter polling thread running in the Syncd container consumes changes in FLEX_COUNTER DB and creates the FC group and polling interval

(11) Trap Flow Counter statistic collector is called on each polling interval and uses the SAI API to obtain the statistics per configured trap

(12) Trap statistics is pushed to COUNTER DB

(13 - not shown for diagram's clarity) - Later a customer can read counter statistics using a new CLI command (show flowcnt trap stats) which will utilizes the Trap name →Counter OID mapping in COUNTER DB

#### Flex Counters Introduction

Concept in Flex Counters:

- Flex Counter Group. Counters are managed based on group in SONiC. Existing counter group includes: port, queue, watermark, etc. User is allowed to configure interval/status for a specific counter group, but user is not allowed to configure interval/status for a specific counter. The data of Flex Counter Group is stored in FLEX COUNTER DB FLEX_COUNTER_GROUP_TABLE.
- Flex Counter. A flex counter is usually bound to a SAI object explicitly/implicitly. It contains a set of statistics, e.g, a port counter contains statistics rx packets, rx bytes, tx packets, tx bytes, etc. A flex counter must belong to a flex counter group. The data of Flex Counter is stored in FLEX COUNTER DB FLEX_COUNTER_TABLE.

FLEX_COUNTER_GROUP_TABLE structure:

	; Defines information for flex counter group
	key                     = "FLEX_COUNTER_GROUP_TABLE|group_name" ; configuration of the flex counter group
	; field                 = value
    ...
	POLL_INTERVAL           = INTEGER                        ; polling interval
	FLEX_COUNTER_STATUS     = STRING                         ; group status, can be enable or disable
	<PLUGIN_LIST>           = STRING                         ; a list of Lua plugin to calculate BPS/PPS
    STATS_MODE              = STRING                         ; stats mode, can be read or read clear

FLEX_COUNTER_GROUP_TABLE example:

```
127.0.0.1:6379[5]> hgetall FLEX_COUNTER_GROUP_TABLE:PORT_STAT_COUNTER
1) "STATS_MODE"
2) "STATS_MODE_READ"
3) "POLL_INTERVAL"
4) "1000"
5) "FLEX_COUNTER_STATUS"
6) "enable"
7) "PORT_PLUGIN_LIST"
8) "9517bb8bab2a37077a992b318a0b913ae4d90726"
```

FLEX_COUNTER_TABLE structure:

	; Defines information for flex counter
	key                     = "FLEX_COUNTER_TABLE|group_name|oid ; configuration of the flex counter
	; field                 = value
    ...
	<COUNTER_ID_LIST>       = STRING                         ; a list of SAI attribute to be queried

FLEX_COUNTER_TABLE example:

```
127.0.0.1:6379[5]> hgetall FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x15000000000472
1) "QUEUE_COUNTER_ID_LIST"
2) "SAI_QUEUE_STAT_DROPPED_PACKETS,SAI_QUEUE_STAT_DROPPED_BYTES,SAI_QUEUE_STAT_PACKETS,SAI_QUEUE_STAT_BYTES"
```

Flex Counters is implemented in following sub-modules:

- sonic-utilities. Flex Counters allows user configuring/showing counter interval/status via CLI command `counterpoll`
- sonic-swss. It handles changes in CONFIG DB and populate data into FLEX COUNTER DB.
- sonic-sairedis. It consumes data in FLEX COUNTER DB, collect statistic data periodically and store it into COUNTER DB.

### High-Level Design

Changes shall be made to sonic-utilities, sonic-swss, sonic-sairedis sub-modules to support this feature.

> Note: Code present in this design document is only for demonstrating the design idea, it is not production code.
#### sonic-swss

##### Flow Counter Handler
Flow Counter Handler is a new class in sonic-swss. Its major responsibilities are:

- Create generic counter implementing flow counters
- Delete generic counter

Copp Orch shall call Flow Counter Handler to create/remove generic counter.

##### Flex Counter Orch

Flex Counter Orch handles flex counter configuration change. Its major responsibilities are:

- Handle flex counter group query status change
- Handle flex counter group query interval change
- Generate flex counter entry to FLEX_COUNTER_TABLE if a flex counter group is enabled.

To support trap flow counter, a few changes shall be made to this class:

- A new flex counter group shall be added to this class: HOSTIF_TRAP_FLOW_COUNTER
- Once flex counter group HOSTIF_TRAP_FLOW_COUNTER is enabled, Flex Counter Orch shall call Copp Orch to generate flex counter entry to FLEX_COUNTER_TABLE.

```cpp
...
else if(field == FLEX_COUNTER_STATUS_FIELD)
{
    ...
    if (gCoppOrch && (key == FLOW_CNT_TRAP))
    {
        if (value == "enable")
        {
            gCoppOrch->generateHostIfTrapCounterIdList();
        }
        else if (value == "disable")
        {
            gCoppOrch->clearHostIfTrapCounterIdList();
        }
    }
    ...
}
...
```

##### COPP Orch

COPP Orch handles trap create/remove according to configuration change. If user creates a new trap and HOSTIF_TRAP counter group is enabled, COPP Orch shall do following:

1. Request Flow Counter Handler to create a generic counter
2. Bind the counter to the trap
3. Request FlexCounterManager to set the counter Id list to FLEX_COUNTER_TABLE so that syncd knows how to query the stats
4. Save a new entry {<trap_name>:<counter_id>} to COUNTERS DB COUNTERS_TRAP_NAME_MAP table so that CLI knows how to display the statistic

If user removes a trap, COPP Orch shall do following:

1. Request FlexCounterManager to remove the counter Id list from FLEX_COUNTER_TABLE
2. Unbind the trap and counter
3. Request Flow Counter Handler to remove the generic counter
4. Remove the entry from COUNTERS DB COUNTERS_TRAP_NAME_MAP

COPP Orch shall provide a function `generateHostIfTrapCounterIdList` to create/bind counters for all existing traps. The function shall be used by Flex Counter Orch to enable counter group.
COPP Orch shall provide a function `clearHostIfTrapCounterIdList` to remove/unbind counters for all existing traps. The function shall be used by Flex Counter Orch to disable counter group.

##### FlexCounterManager

FlexCounterManager updates/clears data to FLEX_COUNTER_TABLE so that syncd knows how to query the stats.  

A new Counter Type shall be added to FlexCounterManager:

```cpp
enum class CounterType
{
    ...
    HOSTIF_TRAP,
}
```

A new entry shall be added to counter_id_field_lookup:

```cpp
const unordered_map<CounterType, string> FlexCounterManager::counter_id_field_lookup =
{
    ...
    { CounterType::HOSTIF_TRAP,  FLOWCNT_TRAP_COUNTER_ID_LIST },
}
```

##### Trap Counter Rate

A new lua script shall be provided as a redis plugin to calculate/store trap counter rate. The script shall be registered to redis and saved to FLEX_COUNTER_GROUP_TABLE table. Syncd consumes/executes this redis plugin periodically.

#### sonic-sairedis

This feature shall reuse existing flex counter infrastructure in Syncd daemon.
##### FlexCounter

Each counter group is managed by a FlexCounter instance. The major responsibility of FlexCounter is that:

- Start a thread to collect stats of counter
- Handle interval change
- Handle status change (enable/disable)

Flow counter shall reuse existing logic about interval and status, no extension is needed.

To collect stats for trap flow counter, FlexCounter needs to understand:

- Counter OID
- Supported stats IDs for a given counter OID

Like existing counter group, a internal structure shall be added to store it.

```cpp
...
struct FlowCounterIds
{
    FlowCounterIds(
            _In_ sai_object_id_t counterId,
            _In_ const std::vector<sai_counter_stat_t> &flowCounterIds);
    
    sai_object_id_t counterId;
    std::vector<sai_counter_stat_t> flowCounterIds;
};

...
std::map<sai_object_id_t, std::shared_ptr<FlowCounterIds>> m_flowCounterIdsMap;
...
```

A new entry shall be added to m_flowCounterIdsMap if an entry is added/updated to FLEX_COUNTER_TABLE.

```cpp
void FlexCounter::addCounter(
        _In_ sai_object_id_t vid,
        _In_ sai_object_id_t rid,
        _In_ const std::vector<swss::FieldValueTuple>& values)
{
    ...
    else if (objectType == SAI_OBJECT_TYPE_COUNTER && field == FLOW_COUNTER_ID_LIST)
    {
        ...
        setFlowCounterList(vid, rid, counterIds);
    }
    ...
}

void FlexCounter::setFlowCounterList(
        _In_ sai_object_id_t counterVid,
        _In_ sai_object_id_t counterRid,
        _In_ const std::vector<sai_counter_stat_t>& counterIds)
{
    // check supported statistic ID
    // add/update entry in m_flowCounterIdsMap
}
```

An entry shall be removed from m_flowCounterIdsMap if an entry is removed from FLEX_COUNTER_TABLE:

```cpp
void FlexCounter::removeCounter(
        _In_ sai_object_id_t vid)
{
    ...
    else if (objectType == SAI_OBJECT_TYPE_COUNTER)
    {
        removeFlowCounter(vid);
    }
    ...
}

void FlexCounter::removeFlowCounter(_In_ sai_object_id_t counterVid) 
{
    // remove entry from m_flowCounterIdsMap
}
```

A new counter collector shall be added to get counter statistic according to m_trapCounterIdsMap and save statistic to COUNTERS DB.

```cpp
void FlexCounter::collectFlexCounters(_In_ swss::Table &countersTable)
{
    ...
}
```

FlexCounter shall also be extended to support trap counter rate plugin.

```cpp
void FlexCounter::addCounterPlugin(
        _In_ const std::vector<swss::FieldValueTuple>& values)
{
    ...
    else if (field == FLOW_COUNTER_PLUGIN_FIELD)
    {
        for (auto& sha: shaStrings)
        {
            addFlowCounterPlugin(sha);
        }
    }
    ...
}

...
void FlexCounter::addFlowCounterPlugin(
        _In_ const std::string& sha)
{
    // register sha as a flow counter plugin
}

void FlexCounter::runPlugins(
        _In_ swss::DBConnector& counters_db)
{
    // add code to run flow counter plugin
}
```

#### Flex Counter DB Enhancements

New lists of Counter OIDs shall be created/updated by corresponding Orch Agents and used by Flex Counter polling thread (in Syncd container). A new field shall be added to FLEX_COUNTER_TABLE table.

- FLOW_COUNTER_ID_LIST

An entry for trap counter in FLEX_COUNTER table shall looks like:

```
127.0.0.1:6379[5]> hgetall FLEX_COUNTER_TABLE:HOSTIF_TRAP_COUNTER:oid:0x1500000000039e
1) "FLOW_COUNTER_ID_LIST"
2) "SAI_COUNTER_STAT_PACKETS,SAI_COUNTER_STAT_BYTES "
```

Here `oid:0x1500000000039e` is the OID of a generic counter.

FLEX_COUNTER_GROUP_TABLE shall be extended with a new group name and a new field `FLOW_COUNTER_PLUGIN_LIST`:

	; Defines information for flex counter group
	key                     = "FLEX_COUNTER_GROUP_TABLE|group_name" ; configuration of the flex counter group
	; field                 = value
    ...
	POLL_INTERVAL           = INTEGER                        ; polling interval
	FLEX_COUNTER_STATUS     = STRING                         ; group status, can be enable or disable
	FLOW_COUNTER_PLUGIN_LIST= STRING                         ; a list of Lua plugin to calculate BPS/PPS
    STATS_MODE              = STRING                         ; stats mode, can be read or read clear

#### Counters DB Enhancements

New field shall be added to COUNTERS table of COUNTERS DB.

	; Defines information for Flow Counter table
	key                             = "COUNTERS:counter_oid"    ; flow counter statistic
	; field                         = value
    ...
	SAI_COUNTER_STAT_PACKETS        = 1*10DIGIT                 ; packets
    SAI_COUNTER_STAT_BYTES          = 1*10DIGIT                 ; bytes

Example:

```
COUNTERS:oid:0x1500000000039e: {

"SAI_COUNTER_STAT_PACKETS":" 100"

"SAI_COUNTER_STAT_BYTES":"20000"

}
```

Here `0x1500000000039e` is the OID of a generic counter which is bound to a trap.

A new table COUNTERS_TRAP_NAME_MAP shall be added to COUNTERS DB.

	; Defines information for COUNTERS_TRAP_NAME_MAP
	key                     = COUNTERS_TRAP_NAME_MAP     ; trap name to generic counter OID mapping
	; field                 = value
    ...
	<trap_to_counter>       = STRING                         ; field name is trap name, value is counter OID

Example:

```
COUNTERS_TRAP_NAME_MAP: {

"dhcp":"oid:0x1500000000034e"

"arp" :"oid:0x1500000000035e"

}
```

Here `0x1500000000034e` is the OID of a generic counter which is bound to dhcp trap, `0x1500000000035e` is the OID of a generic counter which is bound to arp trap

RATES table shall be extended to store the configuration of trap rate Lua script.

Example:

```
127.0.0.1:6379[2]> HGETALL "RATES:TRAP"
1) "TRAP_SMOOTH_INTERVAL"
2) "10"
3) "TRAP_ALPHA"
4) "0.18"
```

RATES table shall be extended to store the initialization status for a given trap.

Example:

```
127.0.0.1:6379[2]> HGETALL RATES:oid:0x1500000000039e:TRAP
1) "INIT_DONE"
2) "DONE"
```

Here `0x1500000000039e` is the OID of a generic counter which is bound to a trap.

RATES table shall be extended to store the trap counter PPS value.

Example:

```
127.0.0.1:6379[2]> HGETALL RATES:oid:0x1500000000039e
 1) "SAI_COUNTER_STAT_PACKETS_last"
 2) "0"
 3) "RX_PPS"
 4) "0"
```

Here `0x1500000000039e` is the OID of a generic counter which is bound to a trap.

### SAI API

No new SAI API is required for this feature.

SAI APIs shall be used in this feature:

```cpp
/**
 * @brief Create counter
 *
 * @param[out] counter_id Counter id
 * @param[in] switch_id Switch id
 * @param[in] attr_count Number of attributes
 * @param[in] attr_list Array of attributes
 *
 * @return #SAI_STATUS_SUCCESS on success
 */
typedef sai_status_t (*sai_create_counter_fn)(
        _Out_ sai_object_id_t *counter_id,
        _In_ sai_object_id_t switch_id,
        _In_ uint32_t attr_count,
        _In_ const sai_attribute_t *attr_list);

/**
 * @brief Remove counter
 *
 * @param[in] counter_id Counter id
 *
 * @return #SAI_STATUS_SUCCESS on success, failure status code on error
 */
typedef sai_status_t (*sai_remove_counter_fn)(
        _In_ sai_object_id_t counter_id);

/**
 * @brief Set trap attribute value.
 *
 * @param[in] hostif_trap_id Host interface trap id
 * @param[in] attr Attribute
 *
 * @return #SAI_STATUS_SUCCESS on success, failure status code on error
 */
typedef sai_status_t (*sai_set_hostif_trap_attribute_fn)(
        _In_ sai_object_id_t hostif_trap_id,
        _In_ const sai_attribute_t *attr);

/**
 * @brief Get counter statistics counters extended.
 *
 * @param[in] counter_id Counter id
 * @param[in] number_of_counters Number of counters in the array
 * @param[in] counter_ids Specifies the array of counter ids
 * @param[in] mode Statistics mode
 * @param[out] counters Array of resulting counter values.
 *
 * @return #SAI_STATUS_SUCCESS on success, failure status code on error
 */
typedef sai_status_t (*sai_get_counter_stats_ext_fn)(
        _In_ sai_object_id_t counter_id,
        _In_ uint32_t number_of_counters,
        _In_ const sai_stat_id_t *counter_ids,
        _In_ sai_stats_mode_t mode,
        _Out_ uint64_t *counters);
```

SAI attributes shall be used in this feature:

```cpp
// Generic counter stats
typedef enum _sai_counter_stat_t
{
    /** Get tx packets count [uint64_t] */
    SAI_COUNTER_STAT_PACKETS = 0x00000000,

    /** Get tx bytes count [uint64_t] */
    SAI_COUNTER_STAT_BYTES = 0x00000001,

     /** Custom range base value */
    SAI_COUNTER_STAT_CUSTOM_RANGE_BASE = 0x10000000

} sai_counter_stat_t

typedef enum _sai_hostif_trap_attr_t
{
    ...
    /**
     * @brief Attach a counter
     *
     * When it is empty, then packet hits won't be counted
     *
     * @type sai_object_id_t
     * @flags CREATE_AND_SET
     * @objects SAI_OBJECT_TYPE_COUNTER
     * @allownull true
     * @default SAI_NULL_OBJECT_ID
     */
    SAI_HOSTIF_TRAP_ATTR_COUNTER_ID,
    ...
}

```

### Configuration and management 

#### CLI/YANG model Enhancements

##### CLI

Enable/disable configuration:

```
counterpoll flowcnt-trap  <enable | disable>

Example:
admin@sonic:~$ counterpoll flowcnt-trap enable
```

Polling interval configuration:

```
counterpoll flowcnt-trap interval <time_in_msec> // default - 1000ms

Example:
admin@sonic:~$ counterpoll flowcnt-trap interval 2000
```

Show configuration:

```
counterpoll show

Example:
admin@sonic:~$ counterpoll show
Type                              Interval (in ms)          Status
--------------------------        ------------------        --------
FLOW_CNT_TRAP_STAT                default(1000)             disable
```

Show counters value:

```
show flowcnt-trap stats

Example:
admin@sonic:~$ show flowcnt-trap stats
  Trap Name    Packets    Bytes      PPS
-----------  ---------  -------  -------
       dhcp        100    2,000  50.25/s

Example for multi-ASIC:
admin@sonic:~$ show flowcnt-trap stats
  ASIC ID    Trap Name    Packets    Bytes      PPS
---------  -----------  ---------  -------  -------
    asic0         dhcp        100    2,000  50.25/s
    asic1         dhcp        200    3,000  45.25/s
```

Clear counters:

```
sonic-clear flowcnt-trap

Example:
admin@sonic:~$ sonic-clear flowcnt-trap
Trap Flow Counters were successfully cleared
```

##### YANG model

A new container shall be added to sonic-flex_counter.yang:

```yang
...
container FLOW_CNT_TRAP {
    /* HOSTIF_TRAP_FLEX_COUNTER_GROUP */
    leaf FLEX_COUNTER_STATUS {
        type flex_status;
    }
}
...
```

#### Config DB Enhancements

A new key shall be added to FLEX_COUNTER_TABLE.

Example:

```
127.0.0.1:6379[4]> hgetall FLEX_COUNTER_TABLE|FLOW_CNT_COPP_TRAP
1) "FLEX_COUNTER_STATUS"
2) "enable"
3) "POLL_INTERVAL"
4) "2000"
```
		
### Warmboot and Fastboot Design Impact
N/A

### Restrictions/Limitations

N/A

### Testing Requirements/Design

#### Unit Test cases

##### sonic-utilities

There is a unit test framework in sonic-utilities. Each new CLI command shall be covered by unit test cases either by adding new test cases or extend existing test cases:

1. TestCounterpoll::test_update_trap_counter_status (Add new case for `counterpoll flowcnt-trap <status>`)
    - Verify command run successfully with valid parameter enable/disable
    - Verify CONFIG DB is correctly updated

2. TestCounterpoll::test_update_trap_counter_interval (Add new case for `counterpoll flowcnt-trap interval <time_in_msec>`)
    - Verify command run successfully with valid parameter (interval value in allowed range)
    - Verify CONFIG DB is correctly updated
    - Verify command abort with invalid parameter

3. TestCounterpoll::test_show (Extend existing case for `counterpoll show`)
    - Verify new counter group is in the output

4. TestCounterpoll::test_update_counter_config_db_status (Extend existing case for `counterpoll config-db`)
    - Verify new counter group is supported by this command

5. TestTrapStat::show (Add new case for `show flowcnt-trap stats`)
    - Verify command output with normal format
    - Verify command output with JSON format

6. TestTrapStat::clear (Add new case for `sonic-clear flowcnt-trap`)
    - Verify stats value can be cleared

7. TestTrapStatsMultiAsic::show
    - Verify command output with normal format
    - Verify command output with JSON format

8. TestTrapStatsMultiAsic::clear
    - Verify stats value can be cleared

##### sonic-swss

Changes in sonic-swss shall be covered by VS test cases:

1. TestFlexCounters::test_flex_counters (Extend existing case)
    - Add new COPP trap
    - Enable trap counter group
    - Verify new entry in FLEX_COUNTER_TABLE and COUNTERS_TRAP_NAME_MAP
    - Set trap counter group interval
    - Verify interval value in FLEX_COUNTER_GROUP_TABLE
    - Disable trap counter group
    - Verify entry is removed from FLEX_COUNTER_TABLE and COUNTERS_TRAP_NAME_MAP

2. TestTrapCounter::test_add_remove_trap
    - Enable trap_flow_counter
    - Remove a COPP trap
    - Verify counter is unbind and removed
    - Add the COPP trap back
    - Verify counter is automatically bind to newly added trap counter

3. TestTrapCounter::test_remove_trap_group
    - Remove a trap group, verify the corresponding entries is removed from FLEX_COUNTER_TABLE

#### System Test cases

System test cases shall be implemented in sonic-mgmt. A few new test cases shall be added:

1. TestCOPP::test_counter (this test case will be applied to multiple trap type like: BGP, ARP, LACP, etc)
    - Enable trap flow counter
    - Clear statistic
    - Send 2000 packets in 10 seconds
    - Verify command `show flowcnt-trap stats` that packet count is 2000 and the PPS is not far from threshold

2. Enable trap counter and run fastboot, verify fastboot downtime is less than threshold.

### Open/Action items - if any 

1. Should trap counter be default enable or disable?
2. Why is there only FLEX_COUNTER_STATUS defined in yang model? Why not POLL_INTERVAL?
3. Is SMOOTH_INTERVAL still used?
