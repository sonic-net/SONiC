# Process and docker stats availability via telemetry agent

## Revision

| Rev | Date     | Author      | Change Description |
|:---:|:--------:|:-----------:|--------------------|
| 0.1 | 09/12/19 | Pradnya Mohite | Initial version    |

## Scope
-Enable sonic streaming telemetry agent to send Process and docker stats data

### Enable sonic streaming telemetry agent to send Process and docker stats data

##### Part 1 
For 1st part, Daemon code will be added under sonic-buildimage/files/image_config.  A Daemon will start when OS starts. At every 2 min interval it will do following:  
Delete all entries for Process and Docker stats from state db  
Update Process and Docker stats data to state-DB.  
Update last update time for process and Docker stats.  

Details of CLI and state-DB given below. 

##### Part 2
Verify that from state-DB data is available via telemetry agent

##### CLI output  and corresponding structure in state-DB for process and docker stats

###### Process stats

```
$ ps -eo uid,pid,ppid,%mem,%cpu,stime,tty,time,cmd

 UID   PID  PPID %MEM %CPU STIME TT           TIME CMD
    0     1     0  0.1  0.0 Oct15 ?        00:00:09 /sbin/init
    0     2     0  0.0  0.0 Oct15 ?        00:00:00 [kthreadd]
    0     3     2  0.0  0.0 Oct15 ?        00:00:01 [ksoftirqd/0]
    0     5     2  0.0  0.0 Oct15 ?        00:00:00 [kworker/0:0H]

```
above output will be stored inside state-DB as follows for largest 1024 CPU consumption processes:  

```
PROCESS_STATS|4276  
"UID"  
"0"  
"PID"  
"1"  
"PPID"  
"0"  
"CPU%"  
"0.0"  
"MEM%"  
"0.1"  
"TTY"  
"?"  
"STIME"  
"Oct15"  
"TIME"  
"00:00:09"  
"CMD"  
"/sbin/init"  

```
Along with data new entry for timestamp will be updated in state_db:  

```
PROCESS_STATS|LastUpdateTime  
```

###### Docker stats

```
$ docker stats --no-stream -a

CONTAINER ID        NAME                CPU %               MEM USAGE / LIMIT     MEM %               NET I/O             BLOCK I/O           PIDS
209c6e6116c6        syncd               10.82%              286MiB / 3.844GiB     7.26%               0B / 0B             0B / 639kB          32
8a97fafdbd60        dhcp_relay          0.02%               12.15MiB / 3.844GiB   0.31%               0B / 0B             0B / 65.5kB         5

```
above output will be stored inside state-DB as follows:

```
DOCKER_STATS|209c6e6116c6     
"NAME"  
"syncd"  
"CPU%"  
"10.82"  
"MEM_BYTES"  
"299892736"  
"MEM_LIMIT_BYTES"  
"4127463571"  
"MEM%"  
"7.26"  
"NET_IN_BYTES"  
"0"  
"NET_OUT_BYTES"  
"0"  
"BLOCK_IN_BYTES"  
"0"  
"BLOCK_OUT_BYTES"  
"639000"  
"PIDS"  
"32"  
```
Along with data new entry for timestamp will be updated in state_db:  

```
DOCKER_STATS|LastUpdateTime
```