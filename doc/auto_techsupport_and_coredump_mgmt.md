# Event Driven TechSupport Invocation & CoreDump Mgmt #
#### Rev 1.0

## Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [1. Overview](#1-overview)
  * [2. High Level Requirements](#2-high-level-requirements)
  * [3. Core Dump Generation in SONiC](#3-core-dump-generation-in-sonic)
  * [4. Memory usage based techsupport invocation](#4-Memory-usage-based-techsupport-invocation)
  * [5. Schema Additions](#5-schema-additions)
  * [6. CLI Enhancements](#6-cli-enhancements)
  * [7. Design](#6-design)
      * [7.1 Modifications to coredump-compress script](#71-Modifications-to-coredump-compress-script)
      * [7.2 coredump_gen_handler script](#72-coredump_gen_handler-script)
      * [7.3 Modifications to generate_dump script](#73-Modifications-to-generate-dump-script)
      * [7.4 techsupport_cleanup script](#74-techsupport_cleanup-script)
      * [7.5 Warmboot consideration](#75-Warmboot-consideration)
      * [7.6 MultiAsic consideration](#76-MultiAsic-consideration)
      * [7.7 Design choices for max-techsupport-limit & max-techsupport-limit arguments](#77-Design-choices-for-max-core-limit-&-max-techsupport-limit-arguments)
      * [7.8 Techsupport Locking](#78-Techsupport-Locking)
  * [8. Test Plan](#8-Test-Plan)
  * [9. SONiC-to-SONiC Upgrade Considerations](#9-SONiC-to-SONiC-Upgrade-Considerations)
  * [10. App Extension Consideration](#9-App-Extension-Considerations)
  * [11. Open questions](#10-Open-questions)


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/22/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |
| 1.1 | 04/08/2022  | Vivek Reddy Karri        | Add the capability to Register/Deregister app extension to AUTO_TECHSUPPORT_FEATURE table |
| 2.0 |     TBD     | Vivek Reddy Karri        | Extending Support for Kernel Dumps                             |
| 3.0 |     02/2022 | Stepan Blyshchak         | Extending Support for memory usage threshold crossed                             |

## About this Manual
This document describes the details of the system which facilitates the auto techsupport invocation support in SONiC. The auto invocation is triggered when any process inside the docker crashes and a core dump is generated.

## 1. Overview
Currently, techsupport is run by invoking `show techsupport` either by orchestration tools or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall idea behind this HLD. All the high-level requirements are summarized in the next section

Another use case is to gather more information about the system in case there is a memory usage threshold crossed.
SONiC dump generated after system reboots due to out of memory is not enough for debugging the issue
as all the information about processes and their mem usage, smaps (/proc/PID/smaps) is lost.
Once the system detects abnormal memory usage SONiC dump is generated automatically. 

## 2. High Level Requirements
### Global Scope
* Techsupport invocation should also be made event-driven based on core dump generation.
* This is only applicable for the processes running inside the dockers. Does not apply for other processes.
* init_cfg.json will be enhanced to include the "CONFIG" required for this feature (described in section 4) and is enabled by default.
* To provide flexibility, a compile time flag "ENABLE_AUTO_TECH_SUPPORT" should be provided to enable/disable the "CONFIG" for this feature. 
* Users should have the abiliity to enable/disable this capability through CLI.
* Techsupport invocation should also be made event-driven based on memory usage threshold crossing.
* The memory usage threshold should be configurable system-wise and per container.

### Configurable Params
* A configurable "rate_limit_interval" should be introduced to limit the number consecutive of techsupport invocations.
* The existing "--since" option in techsupport should be leveraged and this should be a configurable parameter for this feature

### Per-docker Scope
* Should provide a per-docker configurable granularity for this feature.  
* Per-docker rate_limit_interval capability should also be provided.
* This is required as a protection measure for periodically crashing processes

### Invocation Rules
* Auto techsupport invocation should only happen when both the global rate_limit_interval and per-docker rate_limit_interval period has passed.
* Feature should be enabled globally and also per-docker, for this to apply on any of the processes running inside that docker.

### Core & Techsupport Cleanup
* Core dump & techsupport dump cleanup mechanism should also be introduced.
* Size-based cleanup should be performed for both of these.
* Individual configurable options should be provided for each of these.

## 3. Core Dump Generation in SONiC
In SONiC, the core dumps generated from any process crashes are directed to the location `/var/core` and will have the naming format `<comm>.<timestamp>.<pid>.core.gz`. 
The naming format and compression is governed by the script `/usr/local/bin/coredump-compress`.

Where `<comm>` value in the command name associated with a process. comm value of a running process can be read from `/proc/[pid]/comm` file

## 4. Memory usage based techsupport invocation

If the following condition resolves to true:
```
(mem_usage > mem_usage_threshold || ${container}_mem_usage > ${container}_mem_usage_threshold) || mem_free <= mem_free_threshold
```

where ```mem_usage```  is total system memory used (MemAvailable from /proc/meminfo),
```mem_usage_threshold```  configured threshold, (100 - available_mem_threshold),

```${container}_mem_usage```  used memory by $container ("docker stats --no-stream --format {{.MemUsage}}" $container),

```${container}_mem_usage_threshold```  configured memory threshold for $container, (100 - ${container}available_mem_threshold), 

```mem_free``` is the total minus mem usage, ```mem_free_threshold``` - mem free threshold.

the SONiC techsupport is automatically generated.

```mem_free_threshold``` is there to invoke dump when there is quite small amount of memory left that is needed to successfully execute "show techsupport". This is going to be 200 MB by default, as at least 80-90 MB takes "show techsupport" execution.

The check will be implemented as a script that is ran by monit periodically:

```
check program mem_checker with path "/usr/bin/mem_threshold_check"
    if status != 0 for 10 times within 20 cycles then exec /usr/local/bin/mem_threshold_check_handler"
```

The action is going to be ran only once the mem_check script detects memory usage above threshold.

The "10 times within 20 cycles" part is kept in sync with mem_usage alert from sonic-host monit configuration.
It is possible to make those values configurable however, only the threshold value is considered to be configurable.

The rate limit as well as techsupport maximum limit is applicable to techsupport generated by memory check.

#### 202106 and older

To support thechsupport generation on memory leaks a simple rule to monit is added:

```
check system $HOST
    if memory usage > 90% for 10 times within 20 cycles then exec /usr/bin/generate_dump
```

## 5. Schema Additions

### Config DB

#### AUTO_TECHSUPPORT Table
```
key                    = "AUTO_TECHSUPPORT|global"  
state                  = "enabled" / "disabled"    ; Enable this to make the Techsupport Invocation event driven based on core-dump generation
available_mem_threshold = 1*2DIGIT                 ; Memory threshold; 0 to disable techsupport invocation on mem leak.
min_available_mem      = 1*5DIGIT                  ; Minimum free memory amount in MB when techsupport will be executed.
rate_limit_interval    = 1*5DIGIT                  ; Minimum Time in seconds, between two successive techsupport invocations.
                                                     Manual Invocations will be considered as well in the calculation. 
                                                     Configure 0 to explicitly disable
max_techsupport_limit  = 1*3DIGIT                  ; A percentage value should be specified. 
                                                     This signifies maximum size to which /var/dump/ directory can be grown until. 
                                                     The actual value in bytes is calculate based on the available space in the filesystem hosting /var/dump
                                                     When the limit is crossed, the older techsupport dumps are incrementally delete
                                                     Configure 0.0 to explicitly disable
max_core_limit          = 1*3DIGIT                  ; A percentage value should be specified. 
                                                     This signifies maximum Size to which /var/core directory can be grown until.
                                                     The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                                     When the limit is crossed, the older core files are incrementally deleted
                                                     Configure 0.0 to explicitly disable
since                  = 1*32VCHAR;                ; This limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided.
                                                     Any valid date string of the formats specified here can be used. 
                                                     (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                                                     If this value is not explicitly configured or a non-valid string is provided, a default value of "2 days ago" is used.      
```

#### AUTO_TECHSUPPORT_FEATURE table
```
key                    = feature name                
state                  = "enabled" / "disabled"    ; Enable auto techsupport invocation on the critical processes running inside this feature
available_mem_threshold = 1*2DIGIT                  ; Memory threshold; 0 to disable techsupport invocation on mem leak in this container.
rate_limit_interval    = 1*5DIGIT                  ; Rate limit interval for the corresponding feature. Configure 0 to explicitly disable
```

                           
#### YANG Models

```
module sonic-auto_techsupport {

    yang-version 1.1;

    namespace "http://github.com/Azure/sonic-auto_techsupport";
    prefix auto_techsupport;

    import sonic-types {
        prefix stypes;
    }

    description "Event Driven Techsupport & CoreDump Mgmt Capability in SONiC OS";

    revision 2021-08-09 {
        description "First Revision";
    }

    typedef decimal-repr {
        type decimal64 {
            fraction-digits 2;
            range 0.0..99.99; 
        }
    }

    container sonic-auto_techsupport {

        container AUTO_TECHSUPPORT {

                description "AUTO_TECHSUPPORT part of config_db.json";
                
                container GLOBAL {
               
                    leaf state {
                        description "Knob to make techsupport invocation event-driven based on core-dump generation";
                        type stypes:admin_mode;
                    }

                    leaf available_mem_threshold {
                        description "Enable techsupport invocation on available memory threshold crossing; 0 to disable"
                        type decimal-repr;
                        default 10.0;
                    }
                    
                    leaf min_available_mem {
                        description "Minimum free memory amount in MB when techsupport will be executed"
                        type uint32;
                        default 200;
                    }

                    leaf rate_limit_interval  {
                        description "Minimum time in seconds between two successive techsupport invocations. Configure 0 to explicitly disable";
                        type uint16;
                    }

                    leaf max_techsupport_limit {
                        /*
                        A value between (0,100) should be specified. 
                        Upto two decimal places will be used in the calculation
                        The actual value in bytes is calculate based on the available space in the filesystem hosting /var/dump
                        When the limit is crossed, the older core files are incrementally deleted
                        */
                        description "Max Limit in percentage for the cummulative size of ts dumps. No cleanup is performed if the value isn't configured or is 0.0";
                        type decimal-repr;
                    }

                    leaf max_core_limit {
                        /*
                        A value between (0,100) should be specified.
                        Upto two decimal places will be used in the calculation
                        The actual value in bytes is calculated based on the available space in the filesystem hosting /var/core
                        When the limit is crossed, the older core files are deleted
                        */
                        description "Max Limit in percentage for the cummulative size of core dumps. No cleanup is performed if the value isn't congiured or is 0.0";
                        type decimal-repr;
                    }
                    
                    leaf since {
                        /*
                        Any valid date string of the formats specified here (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                        can be used. 
                        */
                        description "Only collect the logs & core-dumps generated since the time provided. A default value of '2 days ago' is used if this value is not set explicitly or a non-valid string is provided";
                        type string {
                            length 1..255;
                        }
                    }
            }
            /* end of container GLOBAL */
        }
        /* end of container AUTO_TECHSUPPORT */
            
        container AUTO_TECHSUPPORT_FEATURE {

            description "AUTO_TECHSUPPORT_FEATURE part of config_db.json";

            list AUTO_TECHSUPPORT_FEATURE_LIST {

                key "feature_name";

                leaf feature_name {
                    description "The name of this feature";
                    /* TODO: Leafref once the FEATURE YANG is added*/
                    type string {
                        length 1..255;
                    }
                }

                leaf state {
                    description "Enable auto techsupport invocation on the processes running inside this feature";
                    type stypes:admin_mode;
                }

                leaf available_mem_threshold {
                    description "Enable techsupport invocation on available memory threshold crossing; 0 to disable"
                    type decimal-repr;
                    default 10.0;
                }

                leaf rate_limit_interval {
                    description "Rate limit interval for the corresponding feature. Configure 0 to explicitly disable";
                    type uint16;
                }

            }
            /* end of AUTO_TECHSUPPORT_FEATURE_LIST */
        }
        /* end of container AUTO_TECHSUPPORT_FEATURE */
    }
    /* end of top level container */
}

```

### State DB

#### AUTO_TECHSUPPORT_DUMP_INFO Table
```
key                 = Techsupport Dump Name 
event_type          = "core" / "memory" ; Type of event caused techsupport invocation
core_dump           = 1*64VCHAR                           ; Core Dump Name
timestamp           = 1*12DIGIT                           ; epoch of this record creation
container_name      = 1*64VCHAR                           ; Container in which the process crashed/mem threshold. Unset when triggered from host.
```

Eg:

```
hgetall "AUTO_TECHSUPPORT_DUMP_INFO|sonic_dump_sonic_20210412_223645"
1) "event_type"
2) "core"
2) "core_dump"
3) "orchagent.1599047232.39.core"
4) "timestamp"
5) "1599047233"
6) "container_name"
7) "swss"
```

```
hgetall "AUTO_TECHSUPPORT_DUMP_INFO|sonic_dump_sonic_20210412_223123"
1) "event_type"
2) "memory"
3) "timestamp"
4) "1612045251"
5) "container_name"
6) "swss"
```

## 6. CLI Enhancements.

### config cli
```
config auto-techsupport global state <enabled/disabled>
config auto-techsupport global available-mem-threshold <float upto two decimal places>
config auto-techsupport global min-available-mem <float upto two decimal places>
config auto-techsupport global rate-limit-interval <uint16>
config auto-techsupport global max-techsupport-limit <float upto two decimal places>
config auto-techsupport global max-core-limit <float upto two decimal places>
config auto-techsupport global since <string>

config auto-techsupport-feature update swss --state disabled --rate-limit-interval 800
config auto-techsupport-feature add snmp --state disabled --rate-limit-interval 800
config auto-techsupport-feature delete restapi
```

### show cli

```
admin@sonic:~$ show auto-techsupport global
STATE      RATE LIMIT INTERVAL (sec)    MAX TECHSUPPORT LIMIT (%)    MAX CORE SIZE (%)   MEM THRESHOLD (%)   MEM THRESHOLD (%)    SINCE
-------  ---------------------------   --------------------------    ------------------  ------------------  -------------------  ---------
enabled                          180                        10.0                   5.0                 10.0                10.0   2 days ago

admin@sonic:~$ show auto-techsupport-feature 
FEATURE NAME    STATE     MEM THRESHOLD (%)     RATE LIMIT INTERVAL (sec)
--------------  --------  ------------------  --------------------------
bgp             enabled                 10.0                         600
database        enabled                 10.0                         600
dhcp_relay      enabled                 10.0                         600
lldp            enabled                 10.0                         600
macsec          enabled                 10.0                         600
mgmt-framework  enabled                 10.0                         600
nat             enabled                 10.0                         600
pmon            enabled                 10.0                         600
radv            enabled                 10.0                         600
restapi         disabled                10.0                         800
sflow           enabled                 10.0                         600
snmp            enabled                 10.0                         600
swss            disabled                10.0                         800


admin@sonic:~$ show auto-techsupport history
TECHSUPPORT DUMP                          TRIGGERED BY    CORE DUMP
----------------------------------------  --------------  -----------------------------
sonic_dump_r-lionfish-16_20210901_221402  bgp             bgpcfgd.1630534439.55.core.gz
sonic_dump_r-lionfish-16_20210901_203725  snmp            python3.1630528642.23.core.gz
sonic_dump_r-lionfish-16_20210901_222408  teamd           python3.1630535045.34.core.gz

```

## 7. Design

### 7.1 Modifications to coredump-compress script

The coredump-compress script is updated to invoke the `coredump_gen_handler` script once it is done writing the core file to /var/core. Any stdout/stderr seen during the execution of `coredump_gen_handler` script is redirected to `/tmp/coredump_gen_handler.log`. This script is enhanced to determine which container the dump belongs to and passes it to the coredump_gen_handler script. 

### 7.2 coredump_gen_handler script

A script under the name `coredump_gen_handler.py` is added to `/usr/local/bin/` directory which will be invoked after a coredump is generated.  The script first checks if this feature is enabled by the user. The script then verifies if a core dump file is created within the last 20 sec and if yes, it moves forward. 

The script invokes the show techsupport command, if the global cooloff & the per-docker cooloff period has passed. The script will also check if the Max Size configured by the user has already exceeded and if yes deletes the core files incrementally. 

Potential Syslog messages which can be logged are:
```
DATE sonic INFO coredump_gen_handler[pid]: Global rate_limit_interval period has not passed. Techsupport Invocation is skipped. Core: python3.1629401152.23.core.gz
DATE sonic INFO coredump_gen_handler[pid]: Process rate_limit_interval period for snmp has not passed.Techsupport Invocation is skipped. Core: python3.1629401152.23.core.gz
DATE sonic INFO coredump_gen_handler[pid]: "show techsupport --since '2 days ago'" is successful, sonic_dump_sonic_20210721_235228.tar.gz is created 
DATE sonic INFO coredump_gen_handler[pid]: core-usage argument is not set. No Cleanup is performed, current size occupied: 456 MB
DATE sonic INFO coredump_gen_handler[pid]: 12 MB deleted from /var/core.
DATE sonic NOTICE coredump_gen_handler[pid]:  auto_invoke_ts is not enabled. No Techsupport Invocation will be performed. core: python3.1629401152.23.core.gz
DATE sonic NOTICE coredump_gen_handler[pid]:  auto-techsupport feature for swss is not enabled. Techsupport Invocation is skipped. core: python3.1629401152.23.core.gz
DATE sonic NOTICE coredump_gen_handler[pid]:  coredump_cleanup is disabled. No cleanup is performed
DATE sonic ERR coredump_gen_handler[pid]:  "show techsupport --since '2 days ago'" was run, but no techsupport dump is found
```

### 7.3 Modifications to generate_dump script

The generate_dump script is updated to invoke the `techsupport_cleanup` script to handle the cleanup of techsupport files. Any stdout/stderr seen during the execution of  `techsupport_cleanup` script is redirected to `/tmp/coredump_gen_handler.log`

### 7.4 techsupport_cleanup script

A script under the name `techsupport_cleanup.py` is added to `/usr/local/bin/` directory which will be invoked after a techsupport dump is created. The script first checks if the feature is enabled by the user. It then checks if the limit configured by the user has crossed and deletes the old techsupport files, if any.

Potential Syslog messages which can be logged are:
```
DATE sonic NOTICE techsupport_cleanup[pid]:  techsupport_cleanup is disabled. No cleanup is performed
DATE sonic INFO coredump_gen_handler[pid]: max-techsupport-size argument is not set. No Cleanup is performed, current size occupied: 456 MB
```
 
### 7.5 Warmboot consideration

No changes to this flow

### 7.6 MultiAsic consideration

Configuration specified for the default feature name in the AUTO_TECHSUPPORT_FEATURE table is applied across all the masic instances. 

i.e. rate_limit_interval defined in the AUTO_TECHSUPPORT_FEATURE|swss key is applied for swss1, swss2, etc
 
### 7.7  Design choices for max-techsupport-limit & max-techsupport-limit arguments

Firstly, Size-based cleanup design was inspired from MaxUse= Argument in the systemd-coredump.conf https://www.freedesktop.org/software/systemd/man/coredump.conf.html 

```
admin@sonic-nvda-spc:/var/core$ df .
Filesystem     1K-blocks    Used Available Use% Mounted on
root-overlay    14928328 3106572  11040396  22% /

admin@sonic-nvda-spc2:/var/core$ df .
Filesystem     1K-blocks    Used Available Use% Mounted on
root-overlay    28589288 2922160  24191796  11% /

admin@sonic-nvda-spc3:/var/core$ df .
Filesystem     1K-blocks    Used Available Use% Mounted on
root-overlay    32896880 5460768  25742008  18% /
```

/var/core & /var/dump directories are hosted on root-overlay filesystem and this usually ranges from 10G to 25G+. 
A default value of 5% would amount to a minimum of 500 MB which is a already a decent space for coredumps.  For techsupport a default value of 10% would amount to a minium of 1G, which might accomodate from 5-10 techsupports.  

Although if the admin feels otherwise, these values are configurable.

### 7.8 Techsupport Locking

Recently, an enhancement was made to techsupport script to only run one instance at a time by using a locking mechanism. When other script instance of techsupport tries to run, it'll exit with a relevent code. This would apply nevertheless of how a techsupport was invoked i.e. manual or through auto-techsupport. 

With this change, rate-limit-interval of zero would not make any difference. The locking mechanism would implicitly impose a minimum rate-limit-interval of techsupport execution time.  And since, the techsupport execution time can't be found out and varies based on underlying machine and system state, the range of values configurable for the rate-limit-interval is left unchanged

A relevant message will be logged to syslog when the invocation fails because of LOCKFAIL exit code. 

## 8. Test Plan

Enhance the existing techsupport sonic-mgmt test with the following cases.

| S.No | Test case synopsis                                                                                                                      |
|------|-----------------------------------------------------------------------------------------------------------------------------------------|
|  1   | Check if the `coredump_gen_handler` script is infact invoking the techsupport cmd, when configured                                      |
|  2   | Check if the techsupport cleanup is working as expected                                                                                 |
|  3   | Check if the global rate-& & per-process rate-limit-interval is working as expected                                                     |
|  4   | Check if the core-dump cleanup is working as expected                                                                                   |
|  5   | Check if the core-dump generated when reaching memory threshold                                                                         |

## 9. SONiC-to-SONiC Upgrade Considerations

The configuration in the init_cfg.json is loaded to the running config i.e. CONFIG_DB even in the case of SONiC-SONiC upgrade from a older image which doesn't support this feature.

### 10  App Extension Considerations

Detailed Info related to Appliation Extension can be found here: https://github.com/sonic-net/SONiC/blob/master/doc/sonic-application-extension/sonic-application-extention-hld.md

A new AUTO_TECHSUPPORT_FEATURE register/deregister option will be introduced. The existing FeatureRegistry class will be enahcned to also add/delete configuration related to AUTO_TECHSUPPORT_FEATURE table.

This will be run when the application installs/uninstalls. Since, the auto-techsupport feature uses compile time flag to determine whether to enable/disable itself, it is not possible to determine that at runtime when the application is installed. 

Thus the decision to whether or not to enable the new feature will be based on the current values of AUTO_TECHSUPPORT & AUTO_TECHSUPPORT_FEATURE tables. The default value for new feature will be disabled if the global state is shown disabled in init_cfg.json. If not, the feature will be enabled. The rate-limit-interval & memory threshold is set to 600 & 10% by default. 

When the app get un-installed, all the config will be cleared unless keep-config option is used.


## 11. Open questions

1. Is 10 % free memory/90 % used memory threshold a reasonable default?
