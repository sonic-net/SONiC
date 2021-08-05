<!-- omit in toc -->
# ACL Flex Counters Support #

<!-- omit in toc -->
## Table of Content
- Revision
- Scope
- Definitions/Abbreviations
- Overview
- Requirements
- Architecture Design
- High-Level Design
- SAI
- Orchagent
- Syncd
- COUNTERS DB
- Flows
- Create ACL rule
- Delete ACL rule
- Mirror flow enhancement
- SAI API
- Configuration and management
  - CLI/YANG model Enhancements
  - Config DB Enhancements
- Warmboot and Fastboot Design Impact
- Restrictions/Limitations
- Testing Requirements/Design
  - Unit Test cases
  - System Test cases
- Open/Action items

### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Stepan Blyshchak   | Initial version                   |

### Scope

The scope of this document covers ACL rule counters support and enhancements in that area.
This document does not cover a reasonable option to create ACL rules without counters as
it may be that ACL rule counters consume additional ASIC resources that might or might not be
required for the end user. This feature is beyond the scope of this document. This design does
not change the existing user experience for ACL functionality.

### Definitions/Abbreviations 

| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| ACL                      | Access Control List                        |
| API                      | Application Programmable Interface         |
| Everflow                 | ERSPAN (Encapsulated Remote Switched Port Analysis) mirroring |
| FC                       | Flex Counter                               | 
| VID                      | SAIRedis Virtual object identifier |
| RID                      | SAI Real object identifier |
| SAI                      | Switch Abstraction Interface               |

### Overview 

The current design of ACL rule counters implements polling at orchagent side at a constant hardcoded interval of 10 seconds.
While it is a simpler approach comparing to Flex Counters infrastructure it comes at a cost of scalability and performance issues.
Considering that orchagent is single threaded a pretty small amount of ACL rules in comparison to ASIC capabilities may take a while
to poll counters for lot more than 10 seconds and blocking orchagent from performing other tasks. This leads to a problem that orchagent
is always busy collecting counters for ACLs and slow responses to other tasks.

Flex counters infrastructure on another hand already used for port, PG, queue, watermark counters solves this issue by delegating counter
polling to a separate thread in syncd and allowing to configure polling interval as well.

### Requirements

- Free up orchagent queue when lots of ACL rules are configured by delegating counters polling to Flex Counters thread in syncd.
- Support enabling and disabling polling based on user configuration and ```counterpoll``` CLI for it.
- Support changing polling interval in range [1-1000] sec and ```counterpoll``` CLI for it.

### Architecture Design 

No SONiC architecture changes are required as an existing flex counter infrastructure is being used.

<p align=center>
<img src="img/acl-counters-high-level-diagram.svg" alt="Figure 1. ACL counters">
</p>

### High-Level Design

### SAI

Unlike port, PG, queue, etc. ACL counters are separate SAI objects of type SAI_OBJECT_TYPE_ACL_COUNTER that are bound to an ACL rule object of type
SAI_OBJECT_TYPE_ACL_ENTRY that orchagent creates with two attributes that are being queried:

| SAI Attribute                | Description 
|------------------------------|----------------------|
| SAI_ACL_COUNTER_ATTR_PACKETS | Get/set packet count | 
| SAI_ACL_COUNTER_ATTR_BYTES   | Get/set byte count   |

These objects as well as ACL rule are dynamic, thus at runtime they might be added or removed so the flex counter manager has to take it into consideration.

### Orchagent

A new type of FC is added to flex_counter/flex_counter_manager.h against its SAI object and a new FC group named "ACL" is added:

Counter Type:
```c++
CounterType::ACL_COUNTER
```

An ACL orchagent holds a new object of type FlexCounterManager and initialized with ```StatsMode::READ```
and a default polling interval of 10 sec enabled by default:
```c++
FlexCounterManager m_acl_fc_mgr;
```

Although these changes are enough to configure FC in syncd for polling at a certain interval its barely usable for CLI to consume
because of two reasons:
1. ACL counter is separate SAI object and needs to be mapped to ACL table name and ACL rule name.
2. ACL rule may be created and removed in the hardware depending on the rule type and state in the network.
   One such example is a mirroring rule. A mirror rule can only exists if a mirror session is created/active.
   Orchagent internally removes ACL mirror rule on session deactivation and creates it when the corresponding
   session is activated. That means an ACL counter will be recreated as well and the counter will reset, however
   it is not intended that ACL rule counter will reset upon session state change. A cache is required to hold an
   old counter values and sum them with the newly created one. The solution to this problem is to not remove the
   ACL rule counter but detach it from the ACL rule.

### Syncd

ACL FC group support in syncd/FlexCounter.cpp.

### COUNTERS DB

Counters table in COUNTERS DB:

- "COUNTERS:oid:<acl_counter_vid>"
  - key: SAI_ACL_COUNTER_ATTR_PACKETS
  - value: Number of packets passed through this rule
  - key: SAI_ACL_COUNTER_ATTR_BYTES
  - value: Number of bytes passed through this rule

```
127.0.0.1:6379[2]> hgetall COUNTERS:oid:0x100000000037a
 1) "SAI_ACL_COUNTER_ATTR_PACKETS"
 2) "100"
 3) "SAI_ACL_COUNTER_ATTR_BYTES"
 4) "102400"
```

Mapping hash table in COUNTERS_DB:

- "COUNTERS_ACL_COUNTER_RULE_MAP"
  - key: ACL table name and ACL rule name separated COUNTERS DB separator (e.g: "L3_TABLE:RULE0")
  - value: VID of the ACL counter

E.g:

```
127.0.0.1:6379[2]> hgetall COUNTERS_ACL_COUNTER_RULE_MAP
 1) "DATA:RULE0"
 2) "oid:0x100000000037a"
```

### Flows

### Create ACL rule

<p align=center>
<img src="img/acl-counters-acl-rule-add-flow.svg" alt="Figure 2. Create ACL rule flow">
</p>

### Delete ACL rule

<p align=center>
<img src="img/acl-counters-acl-rule-remove-flow.svg" alt="Figure 3. Delete ACL rule flow">
</p>

### Mirror flow enhancement

ACL counter should not be removed when mirror rule is removed on mirror session deactivation and upon mirror recreation attached back to the rule object.

### SAI API

No new SAI API is used.

### Configuration and management 
#### CLI/YANG model Enhancements 
#### Config DB Enhancements  

Enable ACL counter polling:
```
admin@sonic:~$ counterpoll acl enable
```

Disable ACL counter polling (NOTE: ACL counter objects are still configured in HW):
```
admin@sonic:~$ counterpoll acl enable
```

Set ACL counter polling interval:
```
admin@sonic:~$ counterpoll acl interval [INTERVAL IN MS]
```

Config DB schema with ACL key in FLEX COUNTER table:

```json
{
"FLEX_COUNTER_TABLE": {
    "ACL": {
        "FLEX_COUNTER_STATUS": "enable"
    }
  }
}
```

YANG model with ACL group:

```yang
  container ACL {
      /* ACL_FLEX_COUNTER_GROUP */
      leaf FLEX_COUNTER_STATUS {
          type flex_status;
      }
  }
```
		
### Warmboot and Fastboot Design Impact  
N/A

### Restrictions/Limitations  
N/A

### Testing Requirements/Design  

#### Unit Test cases  

1. Enhance test_flex_counters.py with ACL group
2. Enhance test_acl.py with check for ACL rule mapping and ACL counter OID inserted in FLEX COUNTER DB.

#### System Test cases

ACL/Everflow tests suite in sonic-mgmt covers the ACL counter functionality.

### Open/Action items
