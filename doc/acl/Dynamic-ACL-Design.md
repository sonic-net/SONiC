
# Time-based ACL #


## Table of Content

- [Time-based ACL](#time-based-acl)
  - [Table of Content](#table-of-content)
  - [Revision](#revision)
  - [Scope](#scope)
  - [Definitions/Abbreviations](#definitionsabbreviations)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Architecture Design](#architecture-design)
  - [High-Level Design](#high-level-design)
    - [DB schema](#db-schema)
      - [CONFIG DB](#config-db)
      - [APP DB](#app-db)
    - [Code change](#code-change)
      - [acl-loader](#acl-loader)
      - [time_based_acl_mgrd](#time_based_acl_mgrd)
    - [Work flow](#work-flow)
      - [Add and remove time-based ACL rule](#add-and-remove-time-based-acl-rule)
      - [Refresh TTL of existing ACL rule](#refresh-ttl-of-existing-acl-rule)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test cases](#unit-test-cases)
        - [For `acl-loader`](#for-acl-loader)
        - [For `time_based_acl_mgrd`](#for-time_based_acl_mgrd)
      - [System Test cases](#system-test-cases)
  - [Open questions](#open-questions)
  -[Work flow](#work-flow)
    - [Add dynamic ACL rule](#add-dynamic-acl-rule)
    - [Refresh TTL of existing ACL rule](#refresh-ttl-of-existing-acl-rule)
    - [Remove ACL rule when TTL expires](#remove-acl-rule-when-ttl-expires)
  - [Testing Requirements/Design](#testing-requirementsdesign)
    - [Unit Test cases](#unit-test-cases)
    - [System Test cases](#system-test-cases)
- [Open questions](#open-questions)


## Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Bing Wang          | Initial version                   |
| 0.2 |9/6/2022     | Shiyan Wang        |                                   |

## Scope

The scope of this document covers the design of dynamic data plane ACL, which assigns a TTL to ACL rule, and removes the expired rule. Control plane ACL is not covered in this document.

## Definitions/Abbreviations 

| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| ACL                      | Access Control List                        |
| TTL | Time to Live |


## Overview 

The current design of data plane ACL supports only persistent rules, that is, once the rule is applied to SONiC, it will be there until manually removed or config reload.

This doc proposes an enhancement to current ACL, which add a time range to ACL rule and the rule will only be activated during the specific time range.

## Requirements

- ACL rules are added with an integer value. The unit is second.
- ACL rules are removed after value seconds from the time they are added.
- The value in ACL rules can be refreshed. The new expiration time is current time plus the new value seconds.
- ACL rules with the integer value are kept after reboot.

## Architecture Design 

No SONiC architecture change is required to support dynamic ACL.

## High-Level Design

### DB schema

#### CONFIG DB

A new table `TIME_BASED_ACL_RULE` is introduced to `CONFIG DB` to record the ACL rules with timestamp of creation and timestamp of expiration.

The new table contains all fileds of a normal ACL rule, and 2 new fields are added: `creation_time` and `expiration_time`. The new fields definition is listed below:
```
key: ACL_RULE_TABLE:table_name:seq  ; key of the rule entry in the table, seq is the order of the rules   
                                    ; when the packet is filtered by the ACL "policy_name".   
                                    ; A rule is always assocaited with a policy.

;field          = value
creation_time   = Integer     ; timestamp when the rule is created or refreshed
expiration_time = Integer     ; timestamp when the rule is expired
is_absolute_time_range = true/false ; This is a purpose for next stage
is_periodic_time_range = true/false ; to support periodic time range
start_time             = Integer
end_time               = Integer
```
A sample config for ACL rule in `CONFIG DB`
```json
{
    "TIME_BASED_ACL_RULE|DATAACL|TIME_BASED_RULE_1":{
        "DST_IP":"192.168.0.3/32",
        "ETHER_TYPE":"2048",
        "PACKET_ACTION":"FORWARD",
        "PRIORITY":"9999",
        "SRC_IP":"192.168.0.2/32",
        "creation_time": "1662432143",
        "expiration_time": "1662432153"
    }
}
```

The YANG of `TIME_BASED_ACL_RULE` is required to be added to accept new fields `creation_time` and `expiration_time`.

Orchagent (actually `aclorch`) won't consume the value of the new flags. So no change is required to `orchagent`.
#### APP DB
Existing table `ACL_RULE_TABLE` in `APP DB` is used to activate an effective ACL rule. The ACL rule format is the same as in `CONFIG DB`.

A sample config for ACL rule in APP DB
```json
{
    "APP_ACL_RULE|DATAACL|TIME_BASED_RULE_1":{
        "DST_IP":"192.168.0.3/32",
        "ETHER_TYPE":"2048",
        "PACKET_ACTION":"FORWARD",
        "PRIORITY":"9999",
        "SRC_IP":"192.168.0.2/32",
    }
}
```
### Code change
#### acl-loader

Update `acl-loader` script to parse new field `ttl`. The entry will be created in `TIME_BASED_ACL_RULE` in `CONFIG DB` if `ttl` is present for an ACL rule in `acl.json`. The entry's `creation_time` is the current time. Then entry's `expiration_time` is `creation_time` + `ttl` value in json. Please find more details in workflow diagram.  

A sample input json config for ACL rule with TTL value
```json
{
    "acl":{
        "acl-sets":{
            "acl-set":{
                "DATAACL":{
                    "acl-entries":{
                        "acl-entry":{
                            "1":{
                                "actions":{
                                    "config":{
                                        "forwarding-action":"ACCEPT"
                                    }
                                },
                                "config":{
                                    "sequence-id":1
                                },
                                "ip":{
                                    "config":{
                                        "source-ip-address":"192.168.0.2/32",
                                        "destination-ip-address":"192.168.0.3/32"
                                    }
                                },
                                "dynamic-acl":{
                                    "config":{
                                        "ttl":"10"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
```

#### time_based_acl_mgrd

A helper script will be added to `swss` container. The checker is started after `orchagent` and check the TTL of time-based ACL rules in every 10 seconds by default. It will walk through all entries in `TIME_BASED_ACL_RULE` in `CONFIG DB`. New effective ACL rules are added to `APP_ACL_RULE` in `APP DB` and expired ACL rules are deleted both from `CONFIG DB` and `APP DB`.

### Work flow
#### Add and remove time-based ACL rule
<p align=center>
<img src="img/time-based-acl-add-rule.png" alt="Figure 1. Create dynamic ACL rule workflow">
</p>

#### Refresh TTL of existing ACL rule
<p align=center>
<img src="img/time-based-acl-refresh.png" alt="Figure 2. Refresh dynamic ACL rule workflow">
</p>
After the overwrite operation, the subsequence is the same as in add and remove time-based ACL rule.

### Testing Requirements/Design  

#### Unit Test cases  

##### For `acl-loader`
+ Test case 1: Verify ACL rule with TTL is accepted by acl-loader.
+ Test case 2: Verify ACL rule without TTL is refused if acl-loader is trying to load time-base ACL rule.
+ Test case 3: Verify `TIME_BASED_ACL_RULE` entry is created in `CONFIG DB` by using `acl-loader` CLI to loads time-base ACL rule.
+ Test case 4: Verfiy ACL rule is deleted in `CONFIG DB` by using `acl-loader` CLI to delete time-base ACL rule.
+ Test case 5: Verify time-based ACL rule is restored in `CONFIG DB` after reboot.
+ Test case 6: Verfiy ACL rule's TTL can be refreshed in `CONFIG DB` by using `acl-loader` CLI to re-loads time-base ACL rule.

##### For `time_based_acl_mgrd`
+ Test case 5: Verify effective ACL rule is added to `APP DB`.
+ Test case 6: Verify expired ACL rule is removed both from `APP DB` and `CONFIG DB`.

#### System Test cases

+ Test case 1: Verify time-based ACL rule is created as expected. The related traffic behavior(ACCEPT or DROP) is consistent with ACL rule.
+ Test case 2: Verify time-based ACL rule is refreshed. The related traffic hehavior is kept the same.
+ Test case 3: Verify expired time-based ACL rule is removed. The related traffic behavior is consistent with ACL rule. 

## Open questions
1. memory leak issue detection and validation.
