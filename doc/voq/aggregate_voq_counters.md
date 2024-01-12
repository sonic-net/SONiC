

# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content 
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [CHASSIS_APP_DB Changes](#chassis_app_db-changes)
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

No new architecture changes are required to SONiC. An instance of SWSS runs on each FSI in a distributed VOQ architecture. SWSS can be used to poll VOQ stats for every ASIC and update CHASSIS_APP_DB which is accessible from every FSI module. 

### High-Level Design

Figure 1: Gathering the VOQ stats in CHASSIS_APP_DB
![Sequence Diagram](images/add_voq_seq.png "Figure 1: Sequence Diagram")  
Figure 2: Aggregation of VOQ stats
![Aggregation of VOQ Stats](images/add_voq_cli.png "Figure 2: Aggregation of VOQ Stats")


#### CHASSIS_APP_DB Changes

The following new VOQ counters should be available for each VOQ entry in the DB:
   * COUNTERS|fsi_id|asic_id|intf:VOQ_index
      * SAI_VOQ_STAT_PACKETS
      * SAI_VOQ_STAT_BYTES
      * SAI_VOQ_STAT_DROPPED_PACKETS
      * SAI_VOQ_STAT_DROPPED_BYTES
        
#### SWSS Changes
##### PortsOrch Changes
PortsOrch will periodically poll the VOQ stats through SAI call `get_queue_stats` and update them into `CHASSIS_APP_DB`

#### Repositories that need to be changed
   * sonic-swss
   * sonic-swss-common
   * sonic-utilities
   * sonic-mgmt

### SAI API 
No new SAI API is being added. PortsOrch will use the existing SAI API i.e. `get_queue_stats`.

### Configuration and management 
#### CLI
CLI (VOQstat.py) aggregates the VOQ stats for a VOQ across ASICS and present a consolidated view. No new CLI command is being introduced for this rather the following CLI command is leveraged to provide this output on an SSI.

$ show VOQ counters [interface] --voq
```
admin@cmp217:~$ show VOQ counters Ethernet24 --voq
      Port    Voq    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
----------  -----  --------------  ---------------  -----------  ------------
Ethernet24   VOQ0               4              528            0             0
Ethernet24   VOQ1               0                0            0             0
Ethernet24   VOQ2               0                0            0             0
Ethernet24   VOQ3               0                0            0             0
Ethernet24   VOQ4               0                0            0             0
Ethernet24   VOQ5               0                0            0             0
Ethernet24   VOQ6               0                0            0             0
Ethernet24   VOQ7               0                0            0             0
```
		


### Restrictions/Limitations  

   * Since this feature doesn't use flex counter, the polling interval is not configurable.
   * The polling can't be disabled permanently as well.

### Testing Requirements/Design  
#### System Test cases
Send traffic across different ASICs and ensure aggregate counters are correctly displayed.
