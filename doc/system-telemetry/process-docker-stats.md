# Process and docker stats availability thorugh telemetry agent

##Scope
-Enable sonic streaming telemetry agent to send Process and docker CPU/memory usage data
-Knob to disable streaming telemetry agent via CLI

##-Enable sonic streaming telemetry agent to send Process and docker CPU/memory usage data
For Process and docker CPU/memory usage data, A Demon will watch and upload every 2 mins to state-DB
From state-DB data need to be available via telemetry agent

###CLI output  and corresponding structure in state-DB for process and docket stats
```mermaid
####Process stats
ps aux 
USER    PID   %CPU%MEM VSZ RSS  TTY    STAT START TIME COMMAND
root      4276  0.0  0.0 108816  5552 ?        Sl   00:39   0:01 containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/07983d8d914904ac8054af2be0aa6aa70a8325700aa2588f7424ece3fbfe648c -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc
root      6601  0.0  0.0 108816  5516 ?        Sl   00:42   0:01 containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/4dc60c74334813d6c833d967b1196d1783b90bff0488aa0c35d544db66dc8a81 -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc
admin    18034  0.0  0.0  13376   936 pts/0    S+   08:05   0:00 grep moby

above output will be stored inside state-DB as follows:
ProcessStats|4276
"CPU"
"0.0"
"MEM"
"0.1"
"VSZ"
"108816"
"RSS"
"5552"
"TTY"
"?"
"STAT"
"SI"
"START"
"00:39"
"TIME"
"0:01"
"COMMAND"
"containerd-shim -namespace moby -workdir /var/lib/containerd/io.containerd.runtime.v1.linux/moby/07983d8d914904ac8054af2be0aa6aa70a8325700aa2588f7424ece3fbfe648c -address /run/containerd/containerd.sock -containerd-binary /usr/bin/containerd -runtime-root /var/run/docker/runtime-runc"

####Docker stats
docker stats --no-stream -a
CONTAINER ID        NAME                CPU %               MEM USAGE / LIMIT     MEM %               NET I/O             BLOCK I/O           PIDS
4dc60c743348        snmp                3.93%               41.56MiB / 7.784GiB   0.52%               0B / 0B             31.5MB / 81.9kB     7
07983d8d9149        syncd               41.89%              291MiB / 7.784GiB     3.65%               0B / 0B             183MB / 406kB       33

above output will be stored inside state-DB as follows:
(showing for 1 container only)
DockerStats|4dc60c743348  
"NAME"
"snmp"
"CPU%"
"3.93"
"MEM USAGE"
"41.56MiB"
"LIMIT"
"7.784GiB"
"MEM%"
"0.52"
"NET I"
"0B"
"NET O"
"0B"
"BLOCKI"
"31.5MiB"
"BLOCKO"
"81.9KB"
"PIDS"
"7"
```
