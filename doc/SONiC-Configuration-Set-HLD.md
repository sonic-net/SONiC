# Terminology
CS: Configuration SET

# Summary
This design propose an secure and light weight service that will provide a transparent and automated configuration query/subscription on given device set.

# Scope
This design only works on devices having gNMI server equipped.

# Config DB Extention
For example if we want to query/subscribe aggregate address on given device set:
```json
{
    ...
    "CONFIGURATION_SET" : {
        "BGP_AGGREGATE_ADDRESS": {
            "set_members" : [ "ip1", "ip2", "ip3", "ip4" ], # It contains all devices' ip address in the same set
            "query_per_second" : "n", # it means it will query every peer n times per second
        },
        "SOME_CONFIG_KEY": {
            ...
        },
        ...
    }
    ...
}
```

# State DB Extention
```json
{
    ...
    "CONFIGURATION_SET": {
        "BGP_AGGREGATE_ADDRESS|Prefix-1": {
            "state": "entire"
        },
        "BGP_AGGREGATE_ADDRESS|Prefix-2": {
            "state": "partial"
        },
        "BGP_AGGREGATE_ADDRESS|Prefix-3": {
            "state": "outage"
        },
        ...
    }
    ...
}
```

# Server Logic
1. Track target configuration on all devices in set
    - every device will query target configuration on peers periodically
    - once confirmed that all devices have same config, it will notify subscriber and update state db with "entire" state.
    - once any device lose target configuration, it will notify subscriber and update state db with "partial" state.
2. Outage Scenarios
   - Server only works when all peers is reachable via gNMi. If any device in CS is unreachable via gNMi, all configuration will be update to "outage" state.
    - If the CS members config is not identical on every devices, all configuration will be update to "outage" state.

# Usage Scenario
1. Aggregate Address Configuration on T1 set:
   - Firstly, we make T1s as a CS and register aggregate address config key in CS.
   - Secondly, we let the bgp container subscribe aggregate address config key in CS.
   - Thirdly, we can add aggregate address config on T1s one by one.
   - Then, CS will notify the bgp container the state of aggregate address in CS, and the bgp container can take action accordingly.

# Possible Enhancement
1. Network isolation awareness: if some devices in configuration set is in planned maintenance, we can ignore those devices.
2. Configuration setting: if there is config diff between devices, we can align them.
