# TACACS+ server monitor design

## Overview

SONiC device usually configured with multiple TACACS+ server, when a server is unreachable, SONiC device will try to connect with next TACACS+ server.

SONiC device will communicate with TACACS+ server in following scenarios:
1. Remote user login to SONiC device.
2. Remote user run commands on SONiC device.

There is a timeout for each server, the default value is 5 seconds, this means if the first server not reachable, SONiC device will stuck there when user login or running commands.

To improve this issue, SONiC will add a TACACS+ server monitor to change server priority, a server unreachable or slow response will be downgrade.

### Functional Requirement
- Monit TACACS+ server unreachable event from COUNTER_DB.
- Monit TACACS+ server slow response event from COUNTER_DB.
- Change server priority based unreachable event and slow response event.
- Not change any other server attribute.
- Not change any other TACACS+ config.

### Counter DB schema
#### TACPLUS_SERVER_LATENCY Table schema
```
; Key
server_key           = IPAddress  ;  TACACS+ server’s address
; Attributes
latency              = 1*10DIGIT  ; server network latency in MS, -1 for connect to server timeout
```

### Config DB schema
#### TACPLUS_MONITOR Table schema
```
; Key
config_key           = 'config'  ;  The configuration key
; Attributes
time_window              = 1*5DIGIT  ; Monitor time window in minute, default is 5
high_latency_threshold   = 1*5DIGIT  ; High latency threshold in ms, default is 20
```

# 3 Limitation

- Service priority change will have 1 minutes delay, this is because monit service will run profile every 1 minutes.

# 4 Design

```
       +------------+ 
       |    Monit   | 
       +-----+------+  
             |          
+------------v--------------+       +---------------------+
|                           |       |                     |
|                           |       |                     |
|     TACACS+ Monitor       |------>|      COUNTER_DB     |
|                           |       |                     |
|                           |       |                     |
+------------+--------------+       +---------------------
             |                                
   +---------v---------+               +-------+--------+
   |                   |               |                |
   | TACACS config file+--------------->  config file   |
   | generate script   |               |                |
   +-------------------+               +-------+--------+

```
- TACACS+ monitor is a Monit profile.
- TACACS+ monitor will perdically check TACACS server latency and update latency to COUNTER_DB.
    - The latency in COUNTER_DB TACPLUS_SERVER_LATENCY table is average latency in recent time window.
    - The time window side defined in CONFIG_DB TACPLUS_MONITOR table.
- TACACS+ monitor also will write warning message to syslog when following event happen:
    - Any server latency is -1, which means the server is unreachable.
    - Any server latency is bigger than high_latency_threshold.
- Hostcfgd will monitor TACPLUS_SERVER_LATENCY table, and will re-generate TACACS config file when following event happen:
    - Any server latency is -1, which means the server is unreachable.
    - Any server latency is bigger than high_latency_threshold.
- When hostcfgd generate TACACS config file, server priority calculated according to following rules:
    - Get server priority info from CONFIG_DB TACPLUS_SERVER table.
    - Change high latency server to 1, this is because 1 is the smallest priority, and SONiC device will use high priority server first.
    - Un-reachable server will not include in TACACS config file.
    - If other server also has priority 1 in CONFIG_DB, change priority to 2
    - If other server priority is no 1, using original priority in CONFIG_DB

# 5 References

## TACACS+ Authentication
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md
## SONiC TACACS+ improvement
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Design.md
