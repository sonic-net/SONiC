


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
      * [Repositories that need to be changed](#repositories-that-need-to-be-changed)
   * [SAI API](#sai-api)
   * [Configuration and management](#configuration-and-management)
      * [CLI](#cli)
   * [Restrictions/Limitations](#restrictionslimitations)
   * [Testing Requirements/Design](#testing-requirementsdesign)
      * [System Test cases](#system-test-cases)  

### Revision 
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 11-Jan-2024 | Harsis Yadav, Pandurangan R S, Vivek Kumar Verma (Arista Networks)               | Initial public version            | 

### Overview 

In a [distributed VOQ architecture](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) corresponding to each output VOQ present on an ASIC, there are VOQs present on every ASIC in the system. Each ASIC has its own set of VOQ stats maintained in the FSI which needs to be gathered independently and can be hard to visualize, providing a non-cohesive experience.

### Requirements

Provide aggregate VOQ counters in a distributed VOQ architecture.

### Architecture Design 

No new architecture changes are required to SONiC. 

A new database `CHASSIS_COUNTERS_DB` will be introduced on `redis_chassis` instance of the SSI dedicated to aggregate statistics.

Voq stats on FSI are already polled via flex counter for each asic by it's corresponding sync instance and updated in COUNTER_DB. Swss will be used to synchronise VOQ stats between COUNTERS_DB of FSI(s) and CHASSIS_COUNTERS_DB on the SSI

### High-Level Design

Figure 1: Gathering the VOQ stats in CHASSIS_COUNTERS_DB 
![Sequence Diagram](images/voq_stats_seq.png "Figure 1: Sequence Diagram")  
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
   * `COUNTERS_VOQ|fsi_id|asic_id|intf@fsi_id|asic_id:VOQ_index`
		      * `SAI_VOQ_STAT_PACKETS`
		      * `SAI_VOQ_STAT_BYTES`
		      * `SAI_VOQ_STAT_DROPPED_PACKETS`
		      * `SAI_VOQ_STAT_DROPPED_BYTES`
		      * `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`

   * The first part of the key ( before @ ) `fsi_id|asic_id|intf` denotes the physical location of the interface ( or full system port name )
   * The second part of the key ( after @ ) `fsi_id|asic_id:VOQ_index` denotes the location of the VOQ and its index.
        
#### SWSS Changes
##### New VoqStatsOrch module
A new module called VoqStatsOrch will be introduced which will be initialised by orchdaemon.

VoqStatsOrch will synchronise the VOQ counters between ASIC's local COUNTERS_DB on the FSI and CHASSIS_COUNTERS_DB running on the SSI.

#### Repositories that need to be changed
   * sonic-buildimage
   * sonic-swss-common: https://github.com/sonic-net/sonic-swss-common/pull/855
   * sonic-swss: https://github.com/sonic-net/sonic-swss/pull/3047
   * sonic-utilities: https://github.com/sonic-net/sonic-utilities/pull/3163
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
		


### Restrictions/Limitations  

   * Since this feature doesn't use flex counter, the polling interval is not configurable.
   * The polling can't be disabled permanently as well.

### Testing Requirements/Design  
#### System Test cases
Send traffic across different ASICs and ensure aggregate counters are correctly displayed.
