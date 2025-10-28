# TACACS+ server monitor design

## Overview

SONiC device usually configured with multiple TACACS+ server, when a server is unreachable, SONiC device will try to connect with next TACACS+ server.

SONiC device will communicate with TACACS+ server in following scenarios:
1. Remote user login to SONiC device.
2. Remote user run commands on SONiC device.

There is a timeout for each server, the default value is 5 seconds, this means if the first server not reachable, SONiC device will stuck there for 5 seconds when user login or running commands.

To improve this issue, SONiC will add a TACACS+ server monitor, a server unreachable or slow response will be downgrade.

### Functional Requirement
- Monit requirement:
    - Add a new monit unit for TACACS+ server status check.
    - Check TACACS+ server connection and write network latency data to COUNTER_DB.
    - Write TACACS+ server unreachable message to syslog.
    - Write TACACS+ server slow response message to syslog.

### Counter DB schema
#### TACPLUS_SERVER_LATENCY Table schema
```
; Key
server_key           = String     ;  TACACS+ server’s address and port
; Attributes
latency              = 1*10DIGIT  ; Server network latency in MS, -1 for connect to server timeout
```

#### TACPLUS_SERVER_LATENCY Table YANG model
```yangmodule sonic-tacplus-server-latency {
    namespace "http://github.com/sonic-net/sonic-tacplus-server-latency";
    prefix ssys;
    yang-version 1.1;

    revision 2023-11-01 {
        description "Initial revision.";
    }

    container sonic-tacplus-server-latency {

        container TACPLUS_SERVER_LATENCY {

            list TACPLUS_SERVER_LATENCY_LIST {
                max-elements 8;
                key "server";

                leaf server {
                    type string;
                    description
                        "TACACS+ server’s address and port";
                }

                leaf latency {
                    type uint32;
                    description "Server network latency in MS";
                }
            }
        }
    }
}
```

### Config DB schema
#### TACPLUS_MONITOR Table schema
```
; Key
config_key           = 'config'  ;  The configuration key
; Attributes
enable                   = BOOLEAN   ; Enable Monitor feature
time_window              = 1*5DIGIT  ; Monitor time window in minute, default is 5
frequency                = 1*5DIGIT  ; Monitor frequency, default is 1
high_latency_threshold   = 1*5DIGIT  ; High latency threshold in ms, default is 20
```

#### TACPLUS_MONITOR Table YANG model
```yang
module sonic-tacplus-monitor {
    namespace "http://github.com/sonic-net/sonic-tacplus-monitor";
    prefix tacplus-monitor;
    yang-version 1.1;

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONiC TACACS server monitor";

    revision 2023-10-18 {
        description
            "Initial revision.";
    }

    container sonic-tacplus-monitor {

        container TACPLUS_MONITOR {
            description "TACACS server monitor config table";

            container Config {
                leaf enable {
                    description "Enable Monitor feature";
                    type boolean;
                    default false;
                }

                leaf time_window {
                    description "Monitor time window in minute";
                    type uint16;
                    default 5;
                }

                leaf frequency {
                    description "Monitor frequency";
                    type uint16;
                    default 1;
                }

                leaf high_latency_threshold {
                    description "High latency threshold in ms";
                    type uint16;
                    default 20;
                }
            }
        }
    }
}
```

# 3 Limitation

- Service priority change will have 1 minutes delay, this is because monit service will run profile every 1 minutes.

# 4 Design

```
   +-------------------+
   |                   |
   |    COUNFIG_DB     |
   |                   |
   +---------+---------+
             |
             |
   +---------v---------+
   |                   |
   |     HostCfgd      |
   |                   |
   +---------+---------+
             |
             |
             |
   +---------v---------+
   |                   |
   | TACACS+ Monitor   |
   |                   |
   +-------------------+
```
- TACACS+ monitor is a Monit profile.
- Hostcfgd will update Monit profile based on TACPLUS_MONITOR table and TACPLUS_SERVER table:
    - When monitor feature disabled, hostcfgd will disable the Monit profile.
    - When TACPLUS_SERVER changed, hostcfgd will update Monit profile.
- TACACS+ monitor will perdically check TACACS server latency and update latency to COUNTER_DB.
    - The time window and frequency are defined in CONFIG_DB TACPLUS_MONITOR table.
    - The latency in COUNTER_DB TACPLUS_SERVER_LATENCY table is average latency in recent time window.
- TACACS+ monitor also will write warning message to syslog when following event happen:
    - Any server latency is -1, which means the server is unreachable.
    - Any server latency is bigger than high_latency_threshold.

# 5 References

## TACACS+ Authentication
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md
## SONiC TACACS+ improvement
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Design.md
