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
ProcessStats|4276  
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
Process_Stats|LastUpdateTime  
```

###### Docker stats

```
$ docker stats --no-stream -a

CONTAINER ID        NAME                CPU %               MEM USAGE / LIMIT     MEM %               NET I/O             BLOCK I/O           PIDS
bf7e49f494ee        grpc                0.00%               0B / 0B               0.00%               0B / 0B             0B / 0B             0
209c6e6116c6        syncd               10.82%              286MiB / 3.844GiB     7.26%               0B / 0B             0B / 639kB          32
8a97fafdbd60        dhcp_relay          0.02%               12.15MiB / 3.844GiB   0.31%               0B / 0B             0B / 65.5kB         5

```
above output will be stored inside state-DB as follows:

```
DockerStats|bf7e49f494ee     
"NAME"  
"grpc"  
"CPU%"  
"0.00%"  
"MEM"  
"0B"  
"MEM_LIMIT"  
"0B"  
"MEM%"  
"0.00"  
"NET_IN"  
"0B"  
"NET_OUT"  
"0B"  
"BLOCK_IN"  
"0B"  
"BLOCK_OUT"  
"0B"  
"PIDS"  
"0"  
```
Along with data new entry for timestamp will be updated in state_db:  

```
Docker_Stats|LastUpdateTime
```