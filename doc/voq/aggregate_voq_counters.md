


# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content 
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [SWSS Changes](#swss-changes)
      * [Database changes](#database-changes)
      * [Telemetry Changes](#gnmi-changes)
      * [Repositories that need to be changed](#repositories-that-need-to-be-changed)
   * [SAI API](#sai-api)
   * [Configuration and management](#configuration-and-management)
      * [CLI](#cli)
   * [Testing Requirements/Design](#testing-requirementsdesign)
      * [System Test cases](#system-test-cases)  

### Revision 
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 11-Jan-2024 | Harsis Yadav, Pandurangan R S, Vivek Kumar Verma (Arista Networks)               | Initial public version            | 

### Overview 

In a [distributed VOQ architecture](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) corresponding to each output VOQ present on an ASIC, there are VOQs present on every ASIC in the system. Each ASIC has its own set of VOQ stats maintained in the linecard that needs to be gathered independently and can be hard to visualize, providing a non-cohesive experience.

### Requirements

Provide aggregate VOQ counters in a distributed VOQ architecture.

### Architecture Design 

No new architecture changes are required to SONiC. 

A new database `CHASSIS_COUNTERS_DB` will be introduced in `redis_chassis` instance of the supervisor dedicated to aggregate statistics.

Voq stats on linecard are already polled via flex counter for each asic by it's corresponding syncd instance and updated in COUNTER_DB. Swss will be used to synchronise VOQ stats between linecard and supervisor.

### High-Level Design
        
#### SWSS Changes
##### New VoqStatsOrch module

Figure 1: Gathering the VOQ stats in CHASSIS_COUNTERS_DB 
![Sequence Diagram](images/voq_seq_diagram.png "Figure 1: Sequence Diagram")  

A new module called VoqStatsOrch will be introduced which will be initialised by orchdaemon.

VoqStatsOrch will synchronise the VOQ counters between each ASIC's COUNTERS_DB on linecards and CHASSIS_COUNTERS_DB running on the supervisor.

#### Database Changes
A new database called CHASSIS_COUNTERS_DB will be introduced on the redis_chassis instance of supervisor.

```
"CHASSIS_COUNTERS_DB"  :  {
	  "id": 21,
	  "separator": ":",
	  "instance": "redis_chassis"
}
```

The VOQ stats will be updated in a new table `COUNTERS_VOQ`

The following new VOQ counters should be available for each VOQ entry in the DB:
   * `COUNTERS_VOQ : <DST_LINECARD> | <DST_ASIC> | EthernetXXX @ <SRC_LINECARD> | <SRC_ASIC> : VOQ_index`
     * `SAI_QUEUE_STAT_PACKETS`
     * `SAI_QUEUE_STAT_BYTES`
     * `SAI_QUEUE_STAT_DROPPED_PACKETS`
     * `SAI_QUEUE_STAT_DROPPED_BYTES`
     * `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`

   * `COUNTERS_VOQ` is the table name.
   * The first part of the key ( before `@` ) `<DST_LINECARD> | <DST_ASIC> | EthernetXXX` denotes the physical location of the interface ( or full system port name )
   * The second part of the key ( after `@` ) `<SRC_LINECARD> | <SRC_ASIC>` denotes the location of the VOQ or in other words the source where this data came from.
   * VOQ_index is the index of the VOQ in question.

#### How aggregation happens?

Aggretation happens for every system port.

Figure 2: Aggregation of VOQ stats
![Aggregation of VOQ Stats](images/voq_cli.png "Figure 2: Aggregation of VOQ Stats")



#### gNMI changes
New virtual paths will be introduced to retrieve VOQ counters from linecard and aggregated VOQ counter stats from supervisor

|  DB target|   Virtual Path  | Supported On? |     Description|
|  ----     |:----:| :-:| ----|
|COUNTERS_DB | "COUNTERS/``<asic id>``/``<system port>``/Voq"| Linecard |  All VOQ counters for a sytem port on an ASIC on linecard
|COUNTERS_DB | "COUNTERS/``<asic id>``/``*``/Voq"| Linecard | All VOQ counters for all sytem ports on an ASIC on linecard
|COUNTERS_DB | "COUNTERS/``<system port>``/Voq"| Supervisor | Aggregated VOQ counters for a system port from supervisor
|COUNTERS_DB | "COUNTERS/``*``/Voq"| Supervisor | Aggregated VOQ counters for all system ports from supervisor

Note: For the sake of uniformity the virtual path for supervisor says target as `COUNTERS_DB` and table as `COUNTERS` but it will be internally mapped to `CHASSIS_COUNTERS_DB` and `COUNTERS_VOQ`.

##### Output from linecard

```
admin@FSI $ gnmi_get -target_addr <FSI>:<PORT> …… -xpath_target COUNTERS_DB -xpath “/COUNTERS/asic0/Linecard4|asic0|Ethernet0/Voq”

== getResponse:
notification: <
………
    val: <
      json_ietf_val: {
"Linecard4|asic0|Ethernet0:0”: {
"SAI_QUEUE_STAT_BYTES”:4382,
“SAI_QUEUE_STAT_PACKETS”:98,
"SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
“SAI_QUEUE_STAT_DROPPED_BYTES":0,
"SAI_QUEUE_STAT_DROPPED_PACKETS":0},
"Linecard4|asic0|Ethernet0:1":{
"SAI_QUEUE_STAT_BYTES":8050,
“SAI_QUEUE_STAT_PACKETS”:161,
“SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
"SAI_QUEUE_STAT_DROPPED_BYTES":0,
“SAI_QUEUE_STAT_DROPPED_PACKETS":0},
…………
…………
"Linecard4|asic0|Ethernet0:7":{
"SAI_QUEUE_STAT_BYTES":32961,
“SAI_QUEUE_STAT_PACKETS”:129,
"SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
"SAI_QUEUE_STAT_DROPPED_BYTES":0,
"SAI_QUEUE_STAT_DROPPED_PACKETS":0}}"
    >

```

##### Output from supervisor
```
admin@SSI $ gnmi_get -target_addr <SSI>:<PORT> …… -xpath_target COUNTERS_DB -xpath “/COUNTERS/Linecard4|asic0|Ethernet0/Voq”

== getResponse:
notification: <
………
    val: <
      json_ietf_val: {
"Linecard4|asic0|Ethernet0:0”: {
"SAI_QUEUE_STAT_BYTES”:340650,
“SAI_QUEUE_STAT_PACKETS”:6813,
"SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
“SAI_QUEUE_STAT_DROPPED_BYTES":0,
"SAI_QUEUE_STAT_DROPPED_PACKETS":0},
"Linecard4|asic0|Ethernet0:1":{
"SAI_QUEUE_STAT_BYTES":8050,
“SAI_QUEUE_STAT_PACKETS”:161,
“SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
"SAI_QUEUE_STAT_DROPPED_BYTES":0,
“SAI_QUEUE_STAT_DROPPED_PACKETS":0},
…………
…………
"Linecard4|asic0|Ethernet0:7":{
"SAI_QUEUE_STAT_BYTES":42468,
“SAI_QUEUE_STAT_PACKETS”:149,
"SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS":0,
"SAI_QUEUE_STAT_DROPPED_BYTES":0,
"SAI_QUEUE_STAT_DROPPED_PACKETS":0}}"
    >

```

#### Repositories that need to be changed
   * sonic-buildimage 
   * sonic-swss-common 
   * sonic-swss 
   * sonic-utilities 
   * sonic-gnmi 

### SAI API 
No new SAI API is being added. 

### Configuration and management 
#### CLI
CLI (queuestat.py) aggregates the VOQ stats for a VOQ across ASICS and present a consolidated view. No new CLI command is being introduced for this rather the following CLI command is leveraged to provide this output on an SSI.

$ show VOQ counters [interface] --voq

From linecard - cmp227-4 and asic0 (existing CLI)
```
admin@cmp227-4:~$ show queue counters "cmp227-4|asic0|Ethernet0" --voq -n asic0
                    Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp227-4|asic0|Ethernet0   VOQ0            6813           340650            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ1             161             8050            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ2             356            17800            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ3             257            12850            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ4             157             7850            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ5            2257           112850            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ6             257            12850            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ7             149            42468            0             0                     0
```

From linecard - cmp227-4 and asic1 (existing CLI)
```
admin@cmp227-4:~$ show queue counters "cmp227-4|asic0|Ethernet0" --voq -n asic1
                    Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp227-4|asic0|Ethernet0   VOQ0             123             6150            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ1             289            14450            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ2             789            39450            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ3             345            17250            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ4           45586          2279300            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ5              90             4500            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ6              56             2800            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ7               0                0            0             0                     0
```

From linecard - cmp227-5 and asic1 (existing CLI)

```
admin@cmp227-5:~$ show queue counters "cmp227-4|asic0|Ethernet0" --voq
                    Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp227-4|asic0|Ethernet0   VOQ0             452            22600            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ1             262            13100            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ2             879            43950            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ3             123             6150            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ4             897            44850            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ5             543            27150            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ6             975            48750            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ7               0                0            0             0                     0
```
From linecard - cmp227-6 and asic1 (existing CLI)
```
admin@cmp227-6:~$ show queue counters "cmp227-4|asic0|Ethernet0" --voq
                    Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp227-4|asic0|Ethernet0   VOQ0              23             1150            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ1             481            24050            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ2              23             1150            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ3            4444           222200            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ4            6789           339450            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ5             590            29500            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ6             567            28350            0             0                     0
cmp227-4|asic0|Ethernet0   VOQ7               0                0            0             0                     0
```

Note: Linecard cmp227-5 and cmp227-6 have only 1 asic therefore asic can be omitted.

From supervisor (same command extended for sup.)

```
admin@cmp227:~$ show queue counters "cmp227-4|asic0|Ethernet0" --voq                                                                                                                                                                                                                       
                    Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
------------------------  -----  --------------  ---------------  -----------  ------------
cmp227-4|asic0|Ethernet0   VOQ0            7411           370550            0             0
cmp227-4|asic0|Ethernet0   VOQ1            1193            59650            0             0
cmp227-4|asic0|Ethernet0   VOQ2            2047           102350            0             0
cmp227-4|asic0|Ethernet0   VOQ3            5169           258450            0             0
cmp227-4|asic0|Ethernet0   VOQ4           53429          2671450            0             0
cmp227-4|asic0|Ethernet0   VOQ5            3480           174000            0             0
cmp227-4|asic0|Ethernet0   VOQ6            1855            92750            0             0
cmp227-4|asic0|Ethernet0   VOQ7             170            49650            0             0
```

### Testing Requirements/Design  
#### System Test cases
Send traffic across different ASICs and ensure aggregate counters are correctly displayed.
