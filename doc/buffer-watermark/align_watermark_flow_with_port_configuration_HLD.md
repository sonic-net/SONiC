
# Align watermark flow with port configuration HLD

# High Level Design Document
## Rev 0.1

# Table of Contents
- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Motivation](#3-motivation)
- [4. Abbreviations](#4-abbreviations)
- [5. Introduction](#5-introduction)
- [6. HLD design](#6-hld-design)
  - [6.1 The Requirement](#61-the-requirement)
  - [6.2 Queue and PG maps](#62-queue-and-pg-maps)
  - [6.3 PG and QUEUE map generation correct flows in Flexcounter](#63-pg-and-queue-map-generation-correct-flows-in-flexcounter)
  - [6.4 Change of PG map and QUEUE map generation in flexcounter](#64-change-of-pg-map-and-queue-map-generation-in-flexcounter)
  - [6.5 Effect upon disablement of counterpoll queue/watermark/pg-drop](#65-effect-upon-disablement-of-counterpoll-queue/watermark/pg-drop)
- [7. Suggested changes](#7-suggested-changes)
  - [7.1 Current flow](#71-current-flow)
  - [7.2 Suggested flow](#72-suggested-flow)
  - [7.3 Addition of port when watermark is enabled](#73-addition-of-port-when-watermark-is-enabled)
- [8. Testing](#8-testing)
  - [8.1 Manual testing](#81-manual-testing)
    - [8.1.1 Regression testing](#811-test-flex-counter-logic)
    - [8.1.2 Regression testing](#812-test-flex-counter-logic-with-reboot)
    - [8.1.3 Regression testing](#813-adding-a-port-when-watermark-is-enabled)
  - [8.2 VS tests](#82-vs-tests)

# 1. Revision
| Rev | Date | Author | Change description |
|:----------:|:----------:|:--------------:|:----------------------:|
| 0.1 | 17/08/2022 | Doron Barashi | Initial version|
| | | | |

# 2. Scope
This document provides high level design for alignment for queue, watermark and pg flows in flexcounter.

# 3. Motivation
Fix wrong flows existing in flexcounter for queue, watermark and pg counter polling.

# 4. Abbreviations

| Term | Meaning |
|:--------:|:---------------------------------------------:|
| PG | Priority Group|
| PG-DROP | Priority Group drop (packets)|

# 5. Introduction

Currently, the queue map will not be generated if:
- the watermark counter polling is enabled
- the queue counter poll is disabled.

This is because there is a missing logic in flexcounter regarding the queue and watermark handling:
- the queue map is generated only if queue counter polling is enabled
- the PG map is generated only if PG watermark polling is enabled

This is not complete

Assume the counter polling is disabled for all counters in CONFIG_DB when the system starts,
-	Enable watermark counter polling only
    -	PG watermark works correctly
    -	*Queue watermark does not work because queue map isn’t generated*
-	Enable pg-drop counter polling only
    -	*PG drop counter does not work because PG maps isn’t generated*
    -   also pg-watermark stats are not added since PG map generation isn't called
-	Enable queue counter polling only
    -	Queue counter works correctly, *but also queue-watermark stats are added*

The branches marked in italic are not expected and caused by the missing logic required in this FR.

# 6. HLD design

## 6.1 The Requirement

- Flexcounter to generate the queue maps when queue or watermark counter is enabled for the 1st time, which means:
    - queue and watermark polling were disabled
    - queue or watermark polling is about to be set to true
- Flexcounter to generate PG maps when pg-drop or watermark counter is enabled for the 1st time, which means:
    - PG and watermark polling were disabled
    - PG or watermark polling is about to be set to true

## 6.2 Queue and PG maps

These are the Queue and PG maps in COUNTER_DB that should be created upon relevant counterpoll enablement

Queue maps in COUNTERS_DB upon counterpoll queue or watermark enable (currently created only upon queue enable):
```
COUNTERS_QUEUE_NAME_MAP
COUNTERS_QUEUE_INDEX_MAP
COUNTERS_QUEUE_PORT_MAP
COUNTERS_QUEUE_TYPE_MAP
```

PG maps in COUNTERS_DB upon counterpoll pg-drop or watermark enable (currently created only upon pg-watermark enable):
```
COUNTERS_PG_NAME_MAP
COUNTERS_PG_PORT_MAP
COUNTERS_PG_INDEX_MAP
```

## 6.3 PG and QUEUE map generation correct flows in Flexcounter

queue enable only:

- QUEUE_STAT_COUNTER should be generated in FLEX_COUNTER_DB

- QUEUE map should be generated in COUNTER_DB

- no WATERMARK stats counters should be generated in flex COUNTER_DB

***Example***

```
1276) "FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x15000000000284"
```


pg-drop enable only:

- PG_DROP_STAT_COUNTER should be generated in FLEX_COUNTER_DB

- PG map should be generated in COUNTER_DB

- no *WATERMARK* stats counters should be generated in flex COUNTER_DB

***Example***

```
642) "FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x1a00000000008f"
```


watermark enable only:

- PG_WATERMARK_STAT_COUNTER should be generated in FLEX_COUNTER_DB (db 5)
- QUEUE_WATERMARK_STAT_COUNTER should be generated in FLEX_COUNTER_DB (db 5)
- BUFFER_POOL_WATERMARK_STAT_COUNTER should be generated in FLEX_COUNTER_DB (db 5)

- PG_WATERMARK should be generated in COUNTER_DB (db 2)
- QUEUE_WATERMARK should be generated in COUNTER_DB (db 2)
- BUFFER_POOL_WATERMARK should be generated in COUNTER_DB (db 2)

***Example***

```
641) "FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x1a0000000000d9"
642) "FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x1a00000000008f"
```

```
1276) "FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x15000000000284"
1277) "FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x150000000002bc"
```

## 6.4 Change of PG map and QUEUE map generation in flexcounter

QUEUE map generation will be separated into two flows:

- QUEUE map geneartion
- adding QUEUE or QUEUE_WATERMARK stats to FLEX_COUNTER_DB depending on the counterpoll enabled (queue or watermark)

PG map generation will be separated into two flows:

- PG map geneartion
- adding PG_DROP or PG_WATERMARK stats to FLEX_COUNTER_DB depending on the counterpoll enabled (pg-drop or watermark)

## 6.5 Effect upon disablement of counterpoll queue/watermark/pg-drop

Current implementation doesn't remove any stats entries from the flexcounter tables in the database upon counterpoll disable.
No changes will be done for these flows as it's done this way by design.


# 7. Suggested changes

## 7.1 Current flow

When queue is enabled in counterpoll, a generateQueueMap function is called in flexcounter.cpp.
this function calls generateQueueMapPerPort per physical port.
inside this per port function both the queue map is created and queue-watermark stats are added.

When pg-watermark is enabled in counterpoll, a generatePriorityGroupMap function is called in flexcounter.cpp.
this function will call generatePriorityGroupMapPerPort per physical port.
inside this per port function both the pg map is created and pg-watermark stats are added.

***Example***

```
                        else if(key == QUEUE_KEY)
                        {
                            gPortsOrch->generateQueueMap();
                        }
                        else if(key == PG_WATERMARK_KEY)
                        {
                            gPortsOrch->generatePriorityGroupMap();
                        }
```

## 7.2 Suggested flow

queue and queue-watermark will be separated:

When queue or watermark is enabled in counterpoll, a generateQueueMap function is called in flexcounter.cpp.
this function will call generateQueueMapPerPort per physical port.
inside this per port function only the queue map will be created.
queue stats creation will be separated into a different inner function that will be called separately if queue counterpoll is enabled.

When only watermark is enabled in counterpoll, this block will call both generateQueueMap and addQueueWatermarkFlexCounters
which will call addQueueWatermarkFlexCountersPerPort per physical port.
inside these per port functions both the queue map will be created and queue-watermark stats will be added respectively.

pg and pg-watermark will be separated:

When pg-drop or watermark is enabled in counterpoll, a generatePriorityGroupMap function is called in flexcounter.cpp.
this function will call generatePriorityGroupMapPerPort per physical port.
inside this per port function only PG map will be created.
pg-drop stats creation will be separated into a different inner function that will be called separately if pg-drop counterpoll is enabled.

When only watermark is enabled in counterpoll, this block will call both generatePriorityGroupMap abd addPriorityGroupWatermarkFlexCounters function 
which will call addPriorityGroupWatermarkFlexCountersPerPort per physical port.
inside this per port functions both the PG map will be created and pg-watermark stats will be added respectively.


***Example***

```
                        else if(key == QUEUE_KEY)
                        {
                            gPortsOrch->generateQueueMap();
                            gPortsOrch->addQueueFlexCounters();
                        }
                        else if(key == QUEUE_WATERMARK)
                        {
                            gPortsOrch->generateQueueMap();
                            gPortsOrch->addQueueWatermarkFlexCounters();
                        }
                        else if(key == PG_DROP_KEY)
                        {
                            gPortsOrch->generatePriorityGroupMap();
                            gPortsOrch->addPriorityGroupDropFlexCounters();
                        }
                        else if(key == PG_WATERMARK_KEY)
                        {
                            gPortsOrch->generatePriorityGroupMap();
                            gPortsOrch->addPriorityGroupWatermarkFlexCounters();
                        }
```

if queue or PG maps already created upon queue or pg-drop enablement and then watermark is enabled,
the queue or PG maps won't be created again.
this is done using the private boolean storing the created status. if it's already true, function returns.
the same mechanism will be done in the new watermark functions.

***PG map Example***

```
    if (m_isPriorityGroupMapGenerated)
    {
        return;
    }
```

## 7.3 Addition of port when watermark is enabled

when watermark counterpoll is enabled and a certaion port will be added, the watermark stats for this port will be added.

# 8. Testing

## 8.1 Manual testing

### 8.1.1 test flex counter logic
Test_flex_counter_logic(type=[watermark,queue,pg-drop]:
1.	Disable the counter polling for all counters and save, reload configuration
2.	Switch (type)
    -   watermark: enable the watermark counter polling, check whether PG and queue map are generated in COUNTER_DB and both PG and QUEUE WATERMARK stats exists in FLEX_COUNTER_DB
    -   queue: enable the queue counter polling, check whether queue map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
    -	pg-drop: enable the pg-drop counter polling, check whether PG map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB

repeat this test 3 times, each time with different type [watermark,queue,pg-drop]

### 8.1.2 test flex counter logic with reboot
Test_flex_counter_logic(type=[watermark,queue,pg-drop] reboot after counterpoll enable:
1.	Disable the counter polling for all counters and save, reload configuration
2.	Switch (type)
    -   watermark: enable the watermark counter polling, check whether PG and queue map are generated in COUNTER_DB and both PG and QUEUE WATERMARK stats exists in FLEX_COUNTER_DB
    -   queue: enable the queue counter polling, check whether queue map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
    -	pg-drop: enable the pg-drop counter polling, check whether PG map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
3. reboot switch
   Switch (type)
    -   watermark: watermark counter polling is enabled, check that PG and queue maps are generated in COUNTER_DB and both PG and QUEUE WATERMARK stats exists in FLEX_COUNTER_DB
    -   queue: queue counter polling is enabled, check whether queue map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
    -	pg-drop: pg-drop counter polling is enabled, check whether PG map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB

### 8.1.3 Adding a port when watermark is enabled

1. disable a port
2. enable watermark counterpoll
3. verify this port stats does not exist in FLEX_COUNTERs_DB and COUNTERS_DB
4. enable the port previously disabled
5. verify this port stats is added to FLEX_COUNTERs_DB and COUNTERS_DB

## 8.2 VS tests

- Add queue-watermark and pg-drop to swss/test_flex_counters.py test
  before this change only queue and pg-watermark are tested according to the old code implementation

- Test_flex_counter_logic(type=[watermark,queue,pg-drop]:

repeat this test 3 times, each time with different type [watermark,queue,pg-drop]
Test_flex_counter_logic(type=[watermark,queue,pg-drop] reboot after counterpoll enable:
1.	Disable the counter polling for all counters and save, reload configuration
2.	Switch (type)
    -   watermark: enable the watermark counter polling, check whether PG and queue map are generated in COUNTER_DB and both PG and QUEUE WATERMARK stats exists in FLEX_COUNTER_DB
    -   queue: enable the queue counter polling, check whether queue map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
    -	pg-drop: enable the pg-drop counter polling, check whether PG map is generated in COUNTER_DB, no *WATERMARK* stats in FLEX_COUNTER_DB
