# TACACS+ server monitor design

## Overview

SONiC device usually configured with multiple TACACS+ server, when a server is unreachable, SONiC device will try to connect with next TACACS+ server.

SONiC device will communicate with TACACS+ server in following scenarios:
1. Remote user login to SONiC device.
2. Remote user run commands on SONiC device.

There is a timeout for each server, the default value is 5 seconds, this means if the first server not reachable, SONiC device will stuck there when user login or running commands.

To improve this issue, SONiC will add a TACACS+ server monitor to change server priority, a server unreachable or slow response will be downgrade.

### Functional Requirement
- Monit TACACS+ server unreachable event from syslog.
- Monit TACACS+ server slow response event from syslog.
- Change server priority based unreachable event and slow response event.
- Not change any other server attribute.
- Not change any other TACACS+ config.

### Syslog format
- TACACS+ server unreachable event format:
```
    failed to connect TACACS+ server [ip address]
```

- TACACS+ server slow response event format:
```
    connect TACACS+ server [ip address] take [time span] ms
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
|     TACACS+ Monitor       |------>|       syslog        |
|                           |       |                     |
|                           |       |                     |
+------------+--------------+       +---------------------
             |                                
   +---------v---------+               +-------+--------+
   |                   |               |                |
   | TACACS config cli +--------------->    ConifgDB    |
   |                   |               |                |
   +-------------------+               +-------+--------+

```
- TACACS+ monitor is a Monit profile.
- TACACS+ monitor will monit syslog for TACACS+ server unreachable or slow response event.
- Monit time window will be 5 minutes, this will hardcode in profile script.
- When a TACACS+ server event happen, monitor will change server priority according following rules:
    - If this is the only TACACS+ server, keeps no change.
    - If server with issue already has priority 1:
        - If any other server also has priority 1, change that server to higher priority, value will be: index*10
        - If all other server already has higher priority, keep no change. 
    - If server with issue not has priority 1:
        - change server priority to 1.
        - If any other server also has priority 1, change that server to higher priority, value will be: index*10
        - If all other server already has higher priority, keep no change. 
- sonic-utilities need change to support 'sudo config tacacs update' operation. 
    - Today there is only 'add' and 'delete'
    - Using 'add' and 'delete' in script have risk to lost all server.

# 5 References

## TACACS+ Authentication
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md
## SONiC TACACS+ improvement
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Design.md