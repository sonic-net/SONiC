


# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content 
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [Database changes](#database-changes)
      * [SWSS Changes](#swss-changes)
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

In a [distributed VOQ architecture](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) corresponding to each output VOQ present on an ASIC, there are VOQs present on every ASIC in the system. Each ASIC has its own set of VOQ stats maintained in the FSI that needs to be gathered independently and can be hard to visualize, providing a non-cohesive experience.

### Requirements

Provide aggregate VOQ counters in a distributed VOQ architecture.

### Architecture Design 

No new architecture changes are required to SONiC. 

A new database `CHASSIS_COUNTERS_DB` will be introduced in `redis_chassis` instance of the SSI dedicated to aggregate statistics.

Voq stats on FSI are already polled via flex counter for each asic by it's corresponding syncd instance and updated in COUNTER_DB. Swss will be used to synchronise VOQ stats between FSI and SSI.

### High-Level Design

Figure 1: Gathering the VOQ stats in CHASSIS_COUNTERS_DB 
![Sequence Diagram](images/voq_seq_diagram.png "Figure 1: Sequence Diagram")  
Figure 2: Aggregation of VOQ stats
![Aggregation of VOQ Stats](images/voq_cli.png "Figure 2: Aggregation of VOQ Stats")


#### Database Changes
A new database called CHASSIS_COUNTERS_DB will be introduced on the redis_chassis instance of SSI.

```
"CHASSIS_COUNTERS_DB"  :  {
	  "id": 21,
	  "separator": ":",
	  "instance": "redis_chassis"
}
```

The VOQ stats will be updated in a new table `COUNTERS_VOQ`

The following new VOQ counters should be available for each VOQ entry in the DB:
   * `COUNTERS_VOQ : LINECARD | ASIC | EthernetXXX @ LINECARD | ASIC : VOQ_index`
     * `SAI_VOQ_STAT_PACKETS`
     * `SAI_VOQ_STAT_BYTES`
     * `SAI_VOQ_STAT_DROPPED_PACKETS`
     * `SAI_VOQ_STAT_DROPPED_BYTES`
     * `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`

   * `COUNTERS_VOQ` is the table name.
   * The first part of the key ( before `@` ) `LINECARD | ASIC | EthernetXXX` denotes the physical location of the interface ( or full system port name )
   * The second part of the key ( after `@` ) `LINECARD | ASIC` denotes the location of the VOQ.
   * VOQ_index is the index of the VOQ in question.
        
#### SWSS Changes
##### New VoqStatsOrch module
A new module called VoqStatsOrch will be introduced which will be initialised by orchdaemon.

VoqStatsOrch will synchronise the VOQ counters between each ASIC's COUNTERS_DB on FSIs and CHASSIS_COUNTERS_DB running on the SSI.

#### gNMI changes
New virtual paths will be introduced to retrieve VOQ counters from FSI and aggregated VOQ counter stats from SSI

|  DB target|   Virtual Path  | Supported On? |     Description|
|  ----     |:----:| :-:| ----|
|COUNTERS_DB | "COUNTERS/``<asic id>``/``<system port>``/Voq"| FSI |  All VOQ counters for a sytem port on an ASIC on FSI
|COUNTERS_DB | "COUNTERS/``<asic id>``/``*``/Voq"| FSI | All VOQ counters for all sytem ports on an ASIC on FSI
|COUNTERS_DB | "COUNTERS/``<system port>``/Voq"| SSI | Aggregated VOQ counters for a system port from SSI
|COUNTERS_DB | "COUNTERS/``*``/Voq"| SSI | Aggregated VOQ counters for all system ports from SSI

Note: For the sake of uniformity the virtual path for `SSI` says target as `COUNTERS_DB` and table as `COUNTERS` but it will be internally mapped to `CHASSIS_COUNTERS_DB` and `COUNTERS_VOQ`.

#### Repositories that need to be changed
   * sonic-buildimage 
   * sonic-swss-common 
   * sonic-swss 
   * sonic-utilities 
   * sonic-gnmi 
   * sonic-mgmt 

### SAI API 
No new SAI API is being added. 

### Configuration and management 
#### CLI
CLI (queuestat.py) aggregates the VOQ stats for a VOQ across ASICS and present a consolidated view. No new CLI command is being introduced for this rather the following CLI command is leveraged to provide this output on an SSI.

$ show VOQ counters [interface] --voq
```
admin@cmp217:~$ show queue counters "cmp217-5|asic0|Ethernet24" --voq
                     Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes    Credit-WD-Del/pkts
-------------------------  -----  --------------  ---------------  -----------  ------------  --------------------
cmp217-5|asic0|Ethernet24   VOQ0              54             2700            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ1              51             2550            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ2               4              200            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ3              45             2250            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ4               7              350            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ5              16              800            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ6              23             1150            0             0                     0
cmp217-5|asic0|Ethernet24   VOQ7              47            13792            0             0                     0
```

### Testing Requirements/Design  
#### System Test cases
Send traffic across different ASICs and ensure aggregate counters are correctly displayed.
