# Test Plan for Align watermark flow with port configuration
### Rev 0.1

# Table of Contents
  
  * [Revision](#revision)
  * [Overview](#overview)
  * [Abbreviations](#abbreviations)
  * [Test information](#test-information)
    * [Supported topology](#supported-topology)
    * [Test configuration](#test-configuration)
      * [counterpoll cli coverage](#counterpoll-cli-coverage)
      * [counterpoll type configuration](#counterpoll-type-configuration)
      * [QUEUE maps in COUNTERS_DB](#queue-maps-in-COUNTERS_DB)
      * [PG maps in COUNTERS_DB](#pg-maps-in-COUNTERS_DB)
      * [watermark stats in COUNTERS_DB example](#watermark-stats-in-COUNTERS_DB-example)
      * [queue stats in FLEX_COUNTER_DB example](#queue-stats-in-FLEX_COUNTER_DB-example)
      * [pg-drop stats in FLEX_COUNTER_DB example](#pg-drop-stats-in-FLEX_COUNTER_DB-example)
      * [watermark stats in FLEX_COUNTER_DB example](#watermark-stats-in-FLEX_COUNTER_DB-example)
    * [High level test details](#high-level-test-details)
    * [Ensure that when only 1 counterpoll enabled only this counterpoll stats exists in DBs](#ensure-that-when-only-1-counterpoll-enabled-only-this-counterpoll-stats-exists-in-DBs)
    * [When all relevant counterpoll types enabled stats for all 3 co-exists in DBs](#when-all-relevant-counterpoll-types-enabled-stats-for-all-3-co-exists-in-DBs)
    * [Detailed test flows](#detailed-test-flows)
      * [one relevant counterpoll type enabled with config save and reload](#one-relevant-counterpoll-type-enabled-with-config-save-and-reload)
        * [queue enabled one counterpoll config reload](#queue-enabled-one-counterpoll-config-reload)
        * [watermark enabled one counterpoll config reload]](#watermark-enabled-one-counterpoll-config-reload)
        * [pg-drop enabled one counterpoll config reload]](#pg-drop-enabled-one-counterpoll-config-reload)
      * [all relevant counterpoll type enabled with config save and reload](#all-relevant-counterpoll-type-enabled-with-config-save-and-reload)
      * [one relevant counterpoll type enabled with switch reboot](#one-relevant-counterpoll-type-enabled-with-switch-reboot)
        * [queue enabled one counterpoll switch reboot](#queue-enabled-one-counterpoll-switch-reboot)
        * [watermark enabled one counterpoll switch reboot](#watermark-enabled-one-counterpoll-switch-reboot)
        * [pg-drop enabled one counterpoll switch reboot](#pg-drop-enabled-one-counterpoll-switch-reboot)
      * [all relevant counterpoll type enabled with config save and switch reboot](#all-relevant-counterpoll-type-enabled-with-config-save-and-switch-reboot)
 
###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 10/30/2022  |    Doron Barashi   | Initial version                   |

## Overview
The purpose of this test plan is to describe tests for Align watermark flow with port configuration feature.

## Abbreviations
| Term    |     Meaning                   |
|:-------:|:-----------------------------:|
| PG	    | Priority Group                |
| PG-DROP	| Priority Group drop (packets) |

## Test information

### Supported topology
The test will be supported on any toplogy, since it doesn't require any traffic,
except configuring port buffers since a performance improvement in queue and pg-drop maps creation was merged few days ago.

### Test configuration
The configuration to the DUT done by the test.

First all counterpoll are disabled.
Then each counterpoll queue/watermark/pg-drop is enabled and COUNTERS_DB and FLEX_COUNTER_DB maps and stats are checked.

#### counterpoll cli coverage
1. counterpoll queue enable
2. counterpoll watermark enable
3. counterpoll pg-drop enable

#### Port buffer configuration
Due to performance improvement in queue and pg-drop maps creation, need to configure ports buffers to be able to have stats
in both COUNTERS_DB and FLEX_COUNTER_DB.

#### counterpoll type configuration
Created rules:
| counterpoll type | state    | counter                                                 | pass criteria  | 
|:----------------:|:--------:|:-------------------------------------------------------:|:--------------:|
| queue            | enabled  | FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*           | present        |
| watermark        | disabled | FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x* | not present    |
|                  |          | FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x*    | not present    |
| pg-drop          | disabled | FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*         | not present    |
|                  |          |                                                         |                |
| queue            | disabled | FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*           | not present    |
| watermark        | enabled  | FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x* | present        |
|                  |          | FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x*    | present        |
| pg-drop          | disabled | FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*         | not present    |
|                  |          |                                                         |                |
| queue            | disabled | FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x*           | not present    |
| watermark        | disabled | FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x* | not present    |
|                  |          | FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x*    | not present    |
| pg-drop          | enabled  | FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x*         | present        |

#### QUEUE maps in COUNTERS_DB
COUNTERS_QUEUE_NAME_MAP
COUNTERS_QUEUE_INDEX_MAP
COUNTERS_QUEUE_PORT_MAP
COUNTERS_QUEUE_TYPE_MAP

#### PG maps in COUNTERS_DB
COUNTERS_PG_NAME_MAP
COUNTERS_PG_PORT_MAP
COUNTERS_PG_INDEX_MAP

#### watermark stats in COUNTERS_DB example
USER_WATERMARKS:oid:0x150000000003c5
PERIODIC_WATERMARKS:oid:0x150000000001d9
PERSISTENT_WATERMARKS:oid:0x150000000004e9

#### queue stats in FLEX_COUNTER_DB example
FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:oid:0x15000000000284

#### pg-drop stats in FLEX_COUNTER_DB example
FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:oid:0x1a00000000008f

#### watermark stats in FLEX_COUNTER_DB example
FLEX_COUNTER_TABLE:QUEUE_WATERMARK_STAT_COUNTER:oid:0x150000000002bc
FLEX_COUNTER_TABLE:PG_WATERMARK_STAT_COUNTER:oid:0x1a0000000000d9


### High level test details
1. Disable the counter polling for all counters
2. save and reload configuration
3. Switch (type[watermark,queue,pg-drop])
   a. queue: enable the queue counter polling, check whether queue map is generated in COUNTERS_DB, no WATERMARK stats in FLEX_COUNTER_DB
   b. watermark: enable the watermark counter polling, check whether PG and queue map are generated in COUNTER_DB and both PG and QUEUE WATERMARK stats exists in FLEX_COUNTER_DB
   c. pg-drop: enable the pg-drop counter polling, check whether PG map is generated in COUNTERS_DB, no WATERMARK stats in FLEX_COUNTER_DB
4. repeat this test 3 times, each time with different type [watermark,queue,pg-drop]
5. test each type separately and also another test with all of them enabled one after the other with checks in between
6. repeat the tests with reboot to verify config is saved and same output is generated after reboot

#### Ensure that when only 1 counterpoll enabled only this counterpoll stats exists in DBs
When only one of the counterpoll types is enabled each time (type[watermark,queue,pg-drop]), make sure only this counterpoll stats exists in:
- COUNTERS_DB
- FLEX_COUNTER_DB

### When all relevant counterpoll types enabled stats for all 3 co-exists in DBs
When all counterpolls types are enabled (type[watermark,queue,pg-drop]), make sure only these counterpoll stats co-exists in:
- COUNTERS_DB
- FLEX_COUNTER_DB

### Detailed test flows

#### one relevant counterpoll type enabled with config save and reload
##### queue enabled one counterpoll config reload
1. Disable the counter polling for all counters
2. save and reload configuration
3. enable the queue counter polling
4. check whether queue map is generated in COUNTERS_DB
5. check for QUEUE stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB

##### watermark enabled one counterpoll config reload
1. Disable the counter polling for all counters
2. save and reload configuration
3. enable the watermark counter polling
4. check whether PG and queue maps are generated in COUNTERS_DB
5. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
6. no QUEUE or PG-DROP stats exists

##### pg-drop enabled one counterpoll config reload
1. Disable the counter polling for all counters
2. save and reload configuration
3. enable the pg-drop counter polling
4. check whether PG map is generated in COUNTERS_DB
5. check for PG-DROP stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB


#### all relevant counterpoll type enabled with config save and reload
1. Disable the counter polling for all counters
2. save and reload configuration
3. enable the queue counter polling
4. check whether queue map is generated in COUNTERS_DB
5. check for QUEUE stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB
7. enable the watermark counter polling
8. check whether PG and queue maps are generated in COUNTERS_DB
9. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
10. no PG-DROP stats exists
11. enable the pg-drop counter polling
12. check whether PG map is generated in COUNTERS_DB
13. check for PG-DROP stats exists in FLEX_COUNTER_DB



#### one relevant counterpoll type enabled with switch reboot
##### queue enabled one counterpoll switch reboot
1. Disable the counter polling for all counters
2. config save and switch reboot
3. enable the queue counter polling
4. check whether queue map is generated in COUNTERS_DB
5. check for QUEUE stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB
7. save and switch reboot
8. check whether queue map is generated in COUNTERS_DB
9. check for QUEUE stats exists in FLEX_COUNTER_DB
10. no WATERMARK stats in FLEX_COUNTER_DB

##### watermark enabled one counterpoll switch reboot
1. Disable the counter polling for all counters
2. config save and switch reboot
3. enable the watermark counter polling
4. check whether PG and queue maps are generated in COUNTERS_DB
5. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
6. no QUEUE or PG-DROP stats exists
7. save and switch reboot
8. check whether PG and queue maps are generated in COUNTERS_DB
9. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
10. no QUEUE or PG-DROP stats exists

##### pg-drop enabled one counterpoll switch reboot
1. Disable the counter polling for all counters
2. config save and switch reboot
3. enable the pg-drop counter polling
4. check whether PG map is generated in COUNTERS_DB
5. check for PG-DROP stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB
7. config save and switch reboot
8. check whether PG map is generated in COUNTERS_DB
9. check for PG-DROP stats exists in FLEX_COUNTER_DB
10. no WATERMARK stats in FLEX_COUNTER_DB


#### all relevant counterpoll type enabled with config save and switch reboot
1. Disable the counter polling for all counters
2. config save and switch reboot
3. enable the queue counter polling
4. check whether queue map is generated in COUNTERS_DB
5. check for QUEUE stats exists in FLEX_COUNTER_DB
6. no WATERMARK stats in FLEX_COUNTER_DB
7. enable the watermark counter polling
8. check whether PG and queue maps are generated in COUNTERS_DB
9. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
10. no PG-DROP stats exists
11. enable the pg-drop counter polling
12. check whether PG map is generated in COUNTERS_DB
13. check for PG-DROP stats exists in FLEX_COUNTER_DB
14. config save and switch reboot
15. check whether PG and queue maps are generated in COUNTERS_DB
16. check for QUEUE stats exists in FLEX_COUNTER_DB
17. check for both PG_WATERMARK and QUEUE_WATERMARK stats exists in FLEX_COUNTER_DB
18. check for PG-DROP stats exists in FLEX_COUNTER_DB
