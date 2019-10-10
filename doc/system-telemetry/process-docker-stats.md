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

$ ps -eo uid,pid,ppid,%mem,%cpu,stime,tty,time,cmd

|UID |   PID |PPID     |  %CPU|%MEM|  TTY |STIME| TIME| CMD                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|---- |-------|---------|--------|--------|------|--------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|0     | 4276 | 0        |0.0      | 0.0     |?       | 00:39 |0:01 | containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/07983d8d914904ac8054af2be0aa6aa70a8325700aa2588f7424ece3fbfe648c -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc|
|0     | 6601 |   2      |0.0      |  0.0    |?       | 00:42 |0:01 |containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/4dc60c74334813d6c833d967b1196d1783b90bff0488aa0c35d544db66dc8a81 -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc|

above output will be stored inside state-DB as follows for largest 1024 CPU consumption processes:  

ProcessStats|4276  
"UID"  
"0"  
"PID"  
"4276"  
"PPID"  
"0"  
"CPU%"  
"0.0"  
"MEM%"  
"0.1"  
"TTY"  
"?"  
"STIME"  
"00:39"  
"TIME"  
"0:01"  
"CMD"  
"containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/07983d8d914904ac8054af2be0aa6aa70a8325700aa2588f7424ece3fbfe648c -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc"  

Along with data new entry for timestamp will be updated in state_db:  
Process_Stats|LastUpdateTime  

###### Docker stats

$ docker stats --no-stream -a

|CONTAINER ID |     NAME|              CPU % |             MEM USAGE / LIMIT|   MEM % |           NET I/O|             BLOCK I/O |          PIDS|
|-----------------|----------|-------------------|--------------------------------|-----------|-----------------|----------------------|-------------|
|4dc60c743348 |    snmp |              3.93%  |            41.56MiB / 7.784GiB| 0.52%    |           0B / 0B |    31.5MB / 81.9kB|     7          |
|07983d8d9149 |   syncd |             41.89% |             291MiB / 7.784GiB  |   3.65%   |           0B / 0B |      83MB / 406kB |      33       |

above output will be stored inside state-DB as follows:

DockerStats|4dc60c743348    
"NAME"  
"snmp"  
"CPU%"  
"3.93"  
"MEM"  
"41.56MiB"  
"MEM_LIMIT"  
"7.784GiB"  
"MEM%"  
"0.52"  
"NET_IN"  
"0B"  
"NET_OUT"  
"0B"  
"BLOCK_IN"  
"31.5MiB"  
"BLOCK_OUT"  
"81.9KB"  
"PIDS"  
"7"  

Along with data new entry for timestamp will be updated in state_db:  
Docker_Stats|LastUpdateTime