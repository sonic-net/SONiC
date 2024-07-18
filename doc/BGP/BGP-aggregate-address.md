# BGP Aggregate Address In Config DB

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [Overview](#overview)
- [Requirements](#requirements)
- [High Level Design](#high-level-design)
    - [Config DB Extension](#config-db-extension)
        - [Yang Model](#yang-model)
        - [Config DB Sample](#config-db-sample)
        - [Parameters](#parameters)
    - [State DB Extension](#state-db-extension)
        - [State DB Sample](#state-db-sample)
        - [State Transition Diagram](#state-transition-diagram)
    - [Bgp Container Behavior](#bgp-container-behavior)



## Revision

| Revision | Date        | Author           | Change Description |
| -------- | ----------- | ---------------- | ------------------ |
| 1.0      | Jul 17 2024 | Wenda Chu, Jing Kan | Initial proposal   |

## Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| BGP | Border Gateway Protocol |
| FRR | A free and open source Internet routing protocol suite for Linux and Unix platforms |
| BBR | An feature to allow device learn routes that go through the same AS |


## Scope

This document describes how to leverage the SONiC config DB to add or remove BGP aggregate address.


## Overview
In BGP, we can aggregate details routes into one single aggregated route. it is a quite useful feature in some scenarios, for example reducing routes count.

To leverage the benefit of address aggregation, we trying design the aggregate address configuration mechanism in this doc.


## Requirements
User can add or remove aggregated address via editing config DB, and there are parameters to control the aggregation and route announcement behavior.

## High Level Design
First we introduce the config DB extension which define the feature scope and parameters we have.
Then we introduce how the bgp container will change its behavior accordingly.

### Config DB Extension
We define a new YANG model to add a new key named `BGP_AGGREGATE_ADDRESS` in config DB.
The key will index to a list of aggregated addresses with their parameters.

The YANG model and config DB demo are showed in below:

#### Yang Model
```
module sonic-bgp-aggregate-address {
    namespace "http://github.com/sonic-net/sonic-bgp-aggregate-address";

    prefix bgp-aggregate-address;

    yang-version 1.1;

    import ietf-inet-types {
        prefix inet;
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC BGP aggregate address configuration module.";

    revision 2024-07-17 {
        description
            "Initial revision.";
    }

    container sonic-bgp-aggregate-address {
        container BGP_AGGREGATE_ADDRESS {

            description "BGP_AGGREGATE_ADDRESS part of config_db.json";

            list BGP_AGGREGATE_ADDRESS_LIST {

                description "BGP_AGGREGATE_ADDRESS list part of config_db.json";

                key "aggregate-address";

                leaf aggregate-address {
                    type inet:ip-prefix;
                    description "Aggregate address to be advertised";
                }

                leaf bbr-required {
                    type boolean;
                    description "Set if BBR is required for generating aggregate address";
                }

                leaf summary-only {
                    type boolean;
                    description "Only advertise the summary of aggregate address";
                }

                leaf route-map {
                    type string;
                    description "Attribute-map to be applied to the aggregate address";
                }

                leaf as-set {
                     type boolean;
                     description "Set if include the AS set when advertising the aggregated address";
                }
            }
        }
    }
}
```

#### Config DB Sample
```json
{
    ...
    "BGP_AGGREGATE_ADDRESS": {
        "192.168.0.0/24": {
            "bbr-required": "true",
            "summary-only": "false"
        },
        "fc00::/63": {
            "bbr-required": "true",
            "summary-only": "true"
            "route-map": "AGG_V6",
            "as-set": "true"
        }
    }
    ...
}
```

#### Parameters
We have parameters to control the behavior of aggregate address in bgp container.

##### BBR Required
It's a boolean to indicate whether only generate aggregated address when BBR feature is enabled.

If it's true and the BBR feature is not enabled, aggregated address won't generated.

##### Summary Only
It's a boolean to indicate whether only advertise aggregate address only.

If it's true, then details routes will be suppressed and only aggregated address will be advertised.

##### AS Set
It's a boolean to indicate whether add a as set of details routes in as path when advertising aggregated address.

If it's true, then when advertising aggregated address there will be a as set of detail routes appended at as path.


##### Route Map
It's a string to indicate which route map to apply to aggregated address.

It should be a name of route map.

### State DB Extension
For every aggregated address, we track its state in state DB, it has two states active and inactive. Active state means the address is configurated in the bgp container, while inactive state means isn't.

#### State DB sample:
```json
{
    ...
    "BGP_AGGREGATE_ADDRESS": {
        "192.168.0.0/24": {
            "state": "inactive"
        },
        "fc00::/63": {
            "state": "active"
        }
    }
    ...
}
```

#### State Transition Diagram

<p align=center>
<img src="img/aggregate_address_state_transition.png" alt="state-transition">
</p>


### Bgp Container Behavior
The bgp container will subscribe the keys `BGP_AGGREGATE_ADDRESS` and `BGP_BBR` in config DB. The possible events and related process are:
1. Add address in config DB:
    - if BRR requirement is satisfied, generate aggregated address in the bgp container and add address in state DB with active state.
    - else, add address in state DB with inactive state.
2. Remove address in config DB:
    - Remove aggregated address in the bgp container and remove address in state DB.
3. Enable BBR feature in config DB:
    - In config DB, find out all addresses that has bbr-required equals true and generate aggregated addresses in the bgp container then update state DB with active state.
4. Disable BBR feature in config DB:
    - In config DB, find out all addresses that has bbr-required equals true and remove aggregated addresses in the bgp container then update state DB with inactive state.
5. The bgp container restarted:
    - the bgp container will process all existed config one by one according to 1~4.

To avoid concurrency issue, all operation mentioned above will be put into queue and be processed one by one. 