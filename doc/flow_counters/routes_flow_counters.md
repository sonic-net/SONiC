# SONiC Route Flow Counter Design #

## Table of Content

### Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

### Scope

This document is the design document for route flow counter feature on SONiC.

### Definitions/Abbreviations

N/A

### Overview

Flow counters are usually used for debugging, troubleshooting and performance enhancement processes. Flow counters could cover cases like:

- Routes matching the configured prefix pattern (number of hits and number of bytes)
- Host interface traps (number of received traps per Trap ID)
- FDB entries matching the configured VXLAN tunnel or using the VLAN ID as pattern
- Next-Hop/Next-Hop Group/Next-Hop Group Member

This document focus on route counter.

### Requirements

- Generic Counters shall be used as Flow Counters introduced by the feature
- CLI shall be used for configuration, showing and clearing of statistics
- Flow Counters for routes shall be configured using prefix patterns. The flow counter shall be bound to all routes matching the configured pattern (vrf|prefix). For VNET, the pattern shall be (vnet|prefix). The VRF term can be skipped if it is default VRF.
- In Phase 1 the number of configured route patterns shall be limited to 2 (IPv4/IPv6 pattern) (enforcement shall be done during configuration via CLI)
- In Phase 1 the number of matching routes for each pattern shall be limited to the pre-configured value (default value - 30, max value - 50)after reboot it is not ensured that the same set of matching routes will be used for counting
- Flow Counters shall be bound the matching routes regardless how these routes are added - manually (static) or via FRR
- Statistics shall be configured (enabled/disabled)  and cleared using the CLI commands
- Statistics shall be provided as a number of hit/use of a specific resource and number of bytes in packets sent via configured routes
- Adding route entry shall be automatically bound to counter if counter is enabled and pattern matches
- Removing route entry shall be automatically unbound if the entry is previously bound
- To support default route, pattern "0.0.0.0" and "::" shall be treated as exact match instead of pattern match

### Architecture Design

Flow counter shall utilize the following existing infrastructure:

- Generic Counters API - defined in https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-Proposal-Generic-Counters.md and already supported by the SAI layer. This feature shall support binding/unbinding of these Generic counters to/from relevant SONIC objects
- Flex Counters framework - used for background polling and pushing the statistic information to COUNTER DB for later use (e.g. by CLI). A introduction to flex counter can be found at: https://github.com/sonic-net/SONiC/pull/858.

![architecture](/doc/flow_counters/route_flow_counter_architecture.png).

### High-Level Design

Changes shall be made to sonic-utilities, sonic-swss sub-modules to support this feature. sonic-sairedis needs not change because trap flow counter feature has already implemented all logic for flow counters.

> Note: Code present in this design document is only for demonstrating the design idea, it is not production code.

#### sonic-swss

##### SAI Capability Query

orchagent shall query the SAI capability and save it to STATE DB so that CLI consumes the capability and tell user whether this feature is enabled on current platform.

##### Flex Counter Orch

A new flex counter group shall be added to this class: ROUTE_FLOW_COUNTER. Flex counter orch shall call Route orch to generate/clear flex counter if user enable/disable ROUTE_FLOW_COUNTER, this flow will be described in chapter [Route Orch](#route-orch)

##### FlexCounterManager

FlexCounterManager updates/clears data to FLEX_COUNTER_TABLE so that syncd knows how to query the stats.

A new Counter Type shall be added to FlexCounterManager:

```cpp
enum class CounterType
{
    ...
    ROUTE_MATCH,
}
```

A new entry shall be added to counter_id_field_lookup:

```cpp
const unordered_map<CounterType, string> FlexCounterManager::counter_id_field_lookup =
{
    ...
    { CounterType::ROUTE_MATCH,  FLOW_COUNTER_ID_LIST },
}
```

##### Route Pattern Orch:

A new class Route pattern orch shall be added to orchagent to handle route patterns change in CONFIG_DB. Route pattern orch shall call route orch if router pattern/max allowed match count is configured by user.

##### Route Orch

Two new caches shall be added to Route Orch as data members:

- Cache for those routes which match the prefix pattern and are bound to counters (Bound Cache).
- Cache for those routes which match the prefix pattern and are not bound to counters (Unbound Cache).

Route Orch shall be extended to handle following cases:

1. Route flow counter enabled

![route-flow-counter-enabled](/doc/flow_counters/route_flow_counter_enabled.svg).

2. Route flow counter disabled

![route-flow-counter-disabled](/doc/flow_counters/route_flow_counter_disabled.svg).

3. Route pattern created or updated.

![user-set-route-pattern](/doc/flow_counters/user_set_route_pattern.svg).

4. Route pattern removed. Route orch shall unbind previous matched routes from counters and clear cache.

5. New route entry in ROUTE_TABLE.

![route-learned](/doc/flow_counters/route_learned.svg).

6. Route entry removed from ROUTE_TABLE.

![route-removed](/doc/flow_counters/route_removed.svg).

7. Max allowed match count updated

![max_allowed_updated](/doc/flow_counters/user_set_max_allowed_match.svg).

8. VRF/VNET create. Route orch shall search existing route pattern and create route flow counters if it matches the newly created VRF/VNET name.

9. VRF/VNET remove. Route orch shall remove all the route flow counters and caches related to the removed VRF/VNET

For binding route entry to a counter:

1. Request Flow Counter Handler to create a generic counter
2. Bind the counter to the route
3. Request FlexCounterManager to set the counter Id list to FLEX_COUNTER_TABLE so that syncd knows how to query the stats
4. Save a new entry {<prefix_str>|<counter_id>} and {<prefix_str>|<route_pattern>} to COUNTERS DB so that CLI knows how to display the statistic.

For unbinding route entry from a counter:

1. Request FlexCounterManager to remove the counter Id list from FLEX_COUNTER_TABLE
2. Unbind the route and counter
3. Request Flow Counter Handler to remove the generic counter
4. Remove the entry from COUNTERS DB

#### Counters DB Enhancements

A new table COUNTERS_ROUTE_NAME_MAP shall be added to COUNTERS DB.

	; Defines information for COUNTERS_ROUTE_NAME_MAP
	key                     = COUNTERS_ROUTE_NAME_MAP     ; route string to generic counter OID mapping
	; field                 = value
    ...
	<str_of_route>          = STRING                      ; field name is string of route, value is counter OID

Example:

```
COUNTERS_ROUTE_NAME_MAP: {
"1.1.1.0/24":"oid:0x1500000000034e"
"Vrf_1|1.1.7.7/32":"oid:0x1500000000035e"
}
```

A new table COUNTERS_ROUTE_TO_PATTERN_MAP shall be added to COUNTERS DB.

	; Defines information for COUNTERS_ROUTE_TO_PATTERN_MAP
	key                     = COUNTERS_ROUTE_TO_PATTERN_MAP     ; route string to route pattern mapping
	; field                 = value
    ...
	<str_of_route>          = STRING                            ; field name is string of route, value is route pattern

Example:

```
COUNTERS_ROUTE_TO_PATTERN_MAP: {
"1.1.1.0/24":"1.1.0.0/16"
"Vrf_1|1.1.7.7/32":"Vrf_1|1.1.0.0/16"
}
```

### SAI API

No new SAI API is required for this feature.

SAI APIs shall be used in this feature:

 |API                 |Function                           |
 |:------------------:|-----------------------------------|
 |sai_counter_api_t   |create_counter                     |
 |                    |remove_counter                     |
 |                    |get_counter_stats_ext              |
 |sai_route_api_t     |set_route_entries_attribute        |

SAI attributes shall be used in this feature:

 |Struct                |Attribute                          |
 |:--------------------:|-----------------------------------|
 |sai_counter_stat_t    | SAI_COUNTER_STAT_PACKETS          |
 |                      | SAI_COUNTER_STAT_BYTES            |
 |sai_route_entry_attr_t| SAI_ROUTE_ENTRY_ATTR_COUNTER_ID   |

### Configuration and management

#### CLI/YANG model Enhancements

##### CLI

```
Note: for below CLI commands which has a "vrf" option, the vrf option can accept either a VRF name or a VNET name.
```

Enable/disable configuration:

```
counterpoll flowcnt-route  <enable | disable>
Example:
admin@sonic:~$ counterpoll flowcnt-route enable
```

Polling interval configuration:

```
counterpoll flowcnt-route interval <time_in_msec> // default - 1000ms
Example:
admin@sonic:~$ counterpoll flowcnt-route interval 2000
```

Show configuration:

```
counterpoll show
Example:
admin@sonic:~$ counterpoll show
Type                              Interval (in ms)          Status
--------------------------        ------------------        --------
FLOW_CNT_ROUTE_STAT               default(10000)            disable
```

Config route pattern:

```
config flowcnt-route pattern <add | remove> [--vrf <vrf>] [--max <route-max>] <prefix-pattern>    // configure route pattern
Example:
admin@sonic:~$ config flowcnt-route pattern add --vrf Vrf_1 --max 50 2.2.0.0/16
Route Pattern Flow Counter configuration is successful

admin@sonic:~$ config flowcnt-route pattern remove --vrf Vrf_1 2.2.0.0/16
Route Pattern Flow Counter configuration is successful
```

Show configuration:

```
show flowcnt-route config
Example:
admin@sonic:~$ show flowcnt-route config
Route pattern          VRF                 Max
-----------------------------------------------
3.3.0.0/16             default             50
```

Show counters value:

```
show flowcnt-route stats   // show statistics of all route flow counters
Example:
admin@sonic:~$ show flowcnt-route stats
Route pattern       VRF               Matched routes           Packets          Bytes
--------------------------------------------------------------------------------------
3.3.0.0/16          default           3.3.1.0/24               100              4543
                                      3.3.2.3/32               3443             929229
                                      3.3.0.0/16               0                0


show flowcnt-route stats pattern [<prefix-pattern> [ --vrf <vrf>] ]   // show statistics of all routes matching the configured route pattern
Example:
admin@sonic:~$ show flowcnt-route stats pattern 3.3.0.0/16
Route pattern       VRF               Matched routes           Packets          Bytes
--------------------------------------------------------------------------------------
3.3.0.0/16          default           3.3.1.0/24               100              4543
                                      3.3.2.3/32               3443             929229
                                      3.3.0.0/16               0                0

show flowcnt-route stats route [<prefix> [ --vrf <vrf>] ]             // show statistics of the specific route matching the configured route pattern
Example:
admin@sonic:~$ show flowcnt-route stats route 3.3.3.2/32 --vrf Vrf_1
Route                     VRF              Route Pattern           Packets          Bytes
-----------------------------------------------------------------------------------------
3.3.3.2/32                Vrf_1            3.3.0.0/16              100              4543
```

Clear counters:

```
sonic-clear flowcnt-route    // clear all route flow counters
Example:
admin@sonic:~$ sonic-clear flowcnt-route
Route Flow Counters were successfully cleared

sonic-clear flowcnt-route pattern  [<prefix-pattern> [ --vrf <vrf>] ]   // clear flow counters of all routes matching the configured route pattern
Example:
admin@sonic:~$ sonic-clear flowcnt-route pattern 3.3.0.0/16 --vrf Vrf_1
Flow Counters of all routes matching the configured route pattern were successfully cleared

sonic-clear flowcnt-route route [<prefix> [ --vrf <vrf>] ]  // clear flow counters of the specific route matching the configured prefix
Example:
admin@sonic:~$ sonic-clear flowcnt-route route 3.3.3.2/32 --vrf Vrf_1
Flow Counters of the specified route were successfully cleared
```

##### YANG model

A new container of FLEX_COUNTER_TABLE shall be added to sonic-flex_counter.yang:

```yang
...
container FLOW_CNT_ROUTE {
    /* ROUTE_FLEX_COUNTER_GROUP */
    leaf FLEX_COUNTER_STATUS {
        type flex_status;
    }
    leaf FLEX_COUNTER_DELAY_STATUS {
        type flex_delay_status;
    }
    leaf POLL_INTERVAL {
        type poll_interval;
    }
}
...
```

A new container FLOW_COUNTER_ROUTE_PATTERN_TABLE shall be added to sonic-flex_counter.yang:

```yang
...
container FLOW_COUNTER_ROUTE_PATTERN_TABLE {
    description "Flow counter route pattern of config_db.json";

    list PATTERN_LIST {

        key "vrf_name ip_prefix";

        leaf vrf_name {
            type string {
                length 0..16;
            }
        }

        leaf ip_prefix {
            type union {
                type stypes:sonic-ip4-prefix;
                type stypes:sonic-ip6-prefix;
            }
        }

        leaf max_match_count {
            type uint32 {
                range 1..50;
            }
        }

    }
}
/* end of container FLOW_COUNTER_ROUTE_PATTERN_TABLE */
...
```

#### Config DB Enhancements

A new table FLOW_COUNTER_ROUTE_PATTERN_TABLE shall be added to CONFIG DB.

    ; Defines schema for route flow counter table
    key                  = "FLOW_COUNTER_ROUTE_PATTERN_TABLE|vrf|prefix"      ; Route pattern (vrf/vnet + prefix)
    ; field              = value
    ...
    max_match_count      = Integer                                            ; Max allowed match count for this pattern, default 30, value range [1, 50]

Example:

```
127.0.0.1:6379[4]> hgetall FLOW_COUNTER_ROUTE_PATTERN_TABLE|Vrf_1|3.3.1.0/24
1) "max_match_count"
2) "30"

127.0.0.1:6379[4]> hgetall FLOW_COUNTER_ROUTE_PATTERN_TABLE|3.3.1.0/24
1) "max_match_count"
2) "30"
```

A new key shall be added to FLEX_COUNTER_TABLE.

Example:

```
127.0.0.1:6379[4]> hgetall FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE
1) "FLEX_COUNTER_STATUS"
2) "enable"
3) "POLL_INTERVAL"
4) "2000"
```

### Warmboot and Fastboot Design Impact
As this is a debugging feature, basically, user should not enable this counter during warmboot or fastboot.

However, if user did it by mistake:

- For fastboot, there is already a mechanism that delays flex counter, nothing needs to be done here. See PR https://github.com/sonic-net/sonic-swss/pull/1877.
- For warmboot, routeorch does not handle any DB change except the "resync" during warmboot, it means that route flow counter will not be enabled until warmboot finish. So, no change is required in this feature.

Based on the above, this feature shall not introduce any delay in fastboot or warmboot, and this shall be verified by test.

### Restrictions/Limitations
SONiC supports a few different route types such as normal route, overlay route, srv6 route, but a vendor might not support all of them. So, whether a route can be bound to generic counter depends on vendor SAI implementation. If vendor SAI does not support a specific route type, the bound SAI call shall return an error, swss shall clear the resource associated to the generic counter.

### Testing Requirements/Design

#### Unit Test cases

##### sonic-utilities

There is a unit test framework in sonic-utilities. Each new CLI command shall be covered by unit test cases either by adding new test cases or extend existing test cases:

1. TestCounterpoll::test_update_route_counter_status (Add new case for `counterpoll flowcnt-route <status>`)
    - Verify command run successfully with valid parameter enable/disable
    - Verify CONFIG DB is correctly updated

2. TestCounterpoll::test_update_route_counter_interval (Add new case for `counterpoll flowcnt-route interval <time_in_msec>`)
    - Verify command run successfully with valid parameter (interval value in allowed range)
    - Verify CONFIG DB is correctly updated
    - Verify command abort with invalid parameter

3. TestCounterpoll::test_show (Extend existing case for `counterpoll show`)
    - Verify new counter group is in the output

4. TestCounterpoll::test_update_counter_config_db_status (Extend existing case for `counterpoll config-db`)
    - Verify new counter group is supported by this command

5. TestRouteStat::show_pattern (Add new case for `show flowcnt-route stats pattern`)
    - Verify command output with normal format
    - Verify command output with JSON format
    - Verify output on multi ASIC

6. TestRouteStat::show_route (Add new case for `show flowcnt-route stats route`)
    - Verify command output with normal format
    - Verify command output with JSON format
    - Verify output on multi ASIC

7. TestRouteStat::show_config (Add new case for `show flowcnt-route config`)
    - Verify command output with normal format
    - Verify command output with JSON format

8. TestRouteStat::clear_pattern (Add new case for `sonic-clear flowcnt-route pattern`)
    - Verify stats value can be cleared
    - Verify on multi ASIC

9. TestRouteStat::clear_route (Add new case for `sonic-clear flowcnt-route route`)
    - Verify stats value can be cleared
    - Verify on multi ASIC

10. TestRouteStat::config (Add new case for `config flowcnt-route`)
    - Verify the pattern in DB
    - Verify max allowed match count in DB

##### sonic-swss

Changes in sonic-swss shall be covered by VS test cases:

1. TestFlexCounters::test_flex_counters (Extend existing case)
    - Add new route to ROUTE_TABLE and set route pattern
    - Enable route counter group
    - Verify new entry in FLEX_COUNTER_TABLE and name map
    - Set route counter group interval
    - Verify interval value in FLEX_COUNTER_GROUP_TABLE
    - Disable trap counter group
    - Verify the counter group is disabled and all data in DB are cleared

2. TestFlexCounters::test_update_route_pattern
    - Add route a and b
    - Enable route counter group
    - Set route pattern to match route a only
    - Verify counter is bind to a
    - Set route pattern to match route b only
    - Verify counter is bind to b
    - Remove route pattern
    - Verify counter is cleared

3. TestFlexCounters::test_add_remove_counter
    - Enable route counter group and set route pattern
    - Add a route matches the pattern
    - Verify counter automatically bind
    - Remove the route
    - Verify counter is automatically unbind

4. TestFlexCounters::test_router_flow_counter_max_match_count
    - Enable route counter group and set route pattern
    - Set max allowed to 1
    - Add 2 route matches the pattern
    - Verify there is 1 counter
    - Set max allowed to 2
    - Verify there are 2 counters
    - Set max allowed to 1
    - Verify there is 1 counter
    - Remove the current bound route
    - Verify there is 1 counter

#### System Test cases

System test cases shall be implemented in sonic-mgmt. A few new test cases shall be added:

1. TestRouteCounter::test_add_remove_route
    - Configure route pattern
    - Advertise route to DUT
    - Verify the counter is created
    - Withdraw route
    - Verify the counter no longer exist

2. TestRouteCounter::test_update_route_pattern
    - Advertise route a and b to DUT
    - Configure route pattern that matches a
    - Verify the counter for a is created
    - Configure route pattern that matches b
    - Verify the counter for a is removed, verify the counter for b is created

3. TestRouteCounter::test_max_match_count
    - Advertise 3 routes to DUT
    - Configure route pattern that matches the 3 routes
    - Configure max match count to 2
    - Verify that only 2 counters are created
    - Withdraw 1 matched route
    - Verify that 2 counters are created
    - Configure max match count to 1
    - Verify that 1 counter is created

4. Extend existing test case to verify route flow counter for different route type:
    - For bgp route, extend test_bgp_speaker_announce_routes and test_bgp_speaker_announce_routes_v6
    - For VNET route, extend test_vnet_vxlan
    - For static route, extend test_static_route, test_static_route_v6, test_static_route_ecmp, test_static_route_ecmp_v6
