# Event Driven TechSupport Invocation & CoreDump Mgmt #
#### Rev 1.0

## Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [1. Overview](#1-overview)
  * [2. High Level Requirements](#2-high-level-requirements)
  * [3. Core Dump Generation in SONiC](#3-core-dump-generation-in-sonic)
  * [4. Schema Additions](#4-schema-additions)
  * [5. CLI Enhancements](#5-cli-enhancements)
  * [6. Design](#6-design)
      * [6.1 Modifications to coredump-compress script](#61-Modifications-to-coredump-compress-script)
      * [6.2 coredump_gen_handler script](#62-coredump_gen_handler-script)
      * [6.3 Requirements for FEATURE_PROC_INFO table](#63-requirements-for-FEATURE_PROC_INFO-table)
      * [6.4 Modifications to generate_dump script](#64-Modifications-to-generate-dump-script)
      * [6.5 techsupport_cleanup script](#65-techsupport_cleanup-script)
      * [6.5 Warmboot consideration](#65-Warmboot-consideration)
      * [6.6 Design choices for core-usage & max-techsupport-size argument](#66-Design-choices-for-core-usage-&-max-techsupport-sizeargument)
  * [7. Test Plan](#7-Test-Plan)


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/22/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |
| 2.0 |     TBD     | Vivek Reddy Karri        | Extending Support for Kernel Dumps                             |

## About this Manual
This document describes the details of the system which facilitates the auto techsupport invocation support in SONiC. The auto invocation is triggered when any critical process inside the docker crashes and a core dump is generated.

## 1. Overview
Currently, techsupport is run by invoking `show techsupport` either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall idea behind this HLD. All the high-level requirements are summarized in the next section

## 2. High Level Requirements
### Global Scope
* Techsupport invocation should also be made event-driven based on core dump generation.
* This is only applicable for the critical processes running inside the dockers. Does not apply for other processes.
* init_cfg.json will be enhanced to include the "CONFIG" required for this feature (described in section 4) and is enabled by default.
* To provide flexibility, a compile time flag "ENABLE_AUTO_TECH_SUPPORT" should be provided to enable/disable the "CONFIG" for this feature. 
* Users should have the abiliity to globally enable/disable this capability through CLI.

### Configurable Params
* A configurable "cooloff" should be introduced to limit the number of techsupport invocations.
* The existing "--since" option in techsupport should be leveraged and this should be a configurable parameter for this feature

### Per-docker Scope
* Should provide a per-docker configurable granularity for this feature.  
* Per-docker enable/disable capability should be achieved through FEATURE table.
* Per-docker cooloff capability should is achieved through FEATURE table.
* Changes to per-docker config's will apply to all the critical processes inside the corresponding docker. 
* Existing FEATURE CLI & Table should be used to apply the Configuration

### Invocation Rules
* Auto techsupport invocation should only happen when both the global cooloff and per-docker cooloff period is passed.
* Feature should be enabled globally and also per-docker, for this to apply on any of the critical processes running inside that docker.

### Core & Techsupport Cleanup
* Core dump & techsupport dump cleanup mechanism should also be introduced.
* Size-based cleanup should be performed for both of these.
* Individual configurable options should be provided for each of these.

## 3. Core Dump Generation in SONiC
In SONiC, the core dumps generated from any process crashes are directed to the location `/var/core` and will have the naming format `/var/core/*.core.gz`. 
The naming format and compression is governed by the script `/usr/local/bin/coredump-compress`.

## 4. Schema Additions

### Config DB

#### AUTO_TECHSUPPORT|global
```
key = "AUTO_TECHSUPPORT|global"
auto_invoke_ts = enabled|disabled;          # Enable this to make the Techsupport Invocation event driven based on core-dump generation
coredump_cleanup = enabled|disabled;        # Enable Core dump cleanup based on core_usage argument 
techsupport_cleanup = enabled|disabled;     # Enable Techsupport Dump cleanup based on max_techsupport_size argument
cooloff = 300;                  # Minimum Time in seconds, between two successive techsupport invocations.
                                  Manual Invocations will be considered as well in the cooloff calculation
max_techsupport_size = 10;      # A perentage value should be specified. 
                                  This signifies maximum Size to which /var/dump/ directory can be grown until. 
                                  The actual value in bytes is calculate based on the available space in the filesystem hosting /var/dump
                                  When the limit is crossed, the older techsupport dumps are incrementally deleted                         
core_usage = 5;                 # A perentage value should be specified. 
                                  This signifies maximum Size to which /var/core directory can be grown until. 
                                  The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                  When the limit is crossed, the older core files are incrementally deleted
since = "2 days ago";           # This limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided.
                                  Any valid date string of the formats specified here (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                                  can be used.                           
                                  If this value is not explicitly configured or a non-valid string is provided, a default value of "2 days ago" is used.
```

#### FEATURE Table
```
.............
.............
cooloff =  600;                       #  Minimum Time in seconds, between two successive techsupport invocations because of the same process
                                         The idea here is not to let a periodically crashing process to invoke the techsupport until a cooloff is met
auto_techsupport = enabled|disabled;  #  Enable/Disable this feature per-docker                              
```

#### YANG Model

```
module sonic-auto_techsupport {

    yang-version 1.1;

    namespace "http://github.com/Azure/sonic-auto_techsupport";
    prefix auto_techsupport;

    description "Event Driven Techsupport & CoreDump Mgmt Capability in SONiC OS";

    revision 2021-08-09 {
        description "First Revision";
    }

    container sonic-auto_techsupport {

        container AUTO_TECHSUPPORT {

                description "AUTO_TECHSUPPORT part of config_db.json";

                container global {

                    leaf auto_invoke_ts {
                        /* Enable this to make the Techsupport Invocation event driven based on core-dump generation*/
                        type enumeration {
                            enum disabled;
                            enum enabled;
                        }
                    }

                    leaf coredump_cleanup {
                        /* Enable Core dump cleanup based on core_usage argument */
                        type enumeration {
                            enum disabled;
                            enum enabled;
                        }
                    }

                    leaf techsupport_cleanup  {
                        /* Enable Techsupport Dump cleanup based on max_techsupport_size argument */
                        type enumeration {
                            enum disabled;
                            enum enabled;
                        }
                    }

                    leaf cooloff {
                        /* Minimum Time in seconds, between two successive techsupport invocations by the script. 
                        Configure '0' to explicitly disable */
                        type uint16;
                        default "180";
                    }

                    leaf max_techsupport_size {
                        /*
                        A value between [0,100) should be specified. 
                        Upto two decimal places will be used in the calculation
                        This signifies maximum Size to which the techsupport dumps in /var/dump directory can be grown until 
                        The actual value in bytes is calculate based on the available space in the filesystem hosting /var/dump
                        When the limit is crossed, the older core files are incrementally deleted
                        Configure '0' to explicitly disable
                        */
                        type decimal64 {
                            fraction-digits 2;
                            range 0.00..99.99; 
                        }
                        default "10";
                    }

                    leaf core_usage {
                        /*
                        A value between [0,100) should be specified.
                        Upto two decimal places will be used in the calculation
                        This signifies maximum Size to which the core dumps in /var/core directory can be grown until
                        The actual value in bytes is calculated based on the available space in the filesystem hosting /var/core
                        When the limit is crossed, the older core files are deleted
                        Configure '0' to explicitly disable
                        */
                        type decimal64 {
                            fraction-digits 2;
                            range 0..99.99; 
                        }
                        default "5";
                    }

                    leaf since {
                        /*
                        This limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided
                        Any valid date string of the formats specified here (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                        can be used. If this value is not explicitly configured or a non-valid string is provided, a default value of "2 days ago" is used
                        */
                        type string;
                        default "2 days ago";
                    }
              }
              /* end of container global */
        }
        /* end of container AUTO_TECHSUPPORT */
    }
    /* end of top level container */
}
```

Note: The "cooloff" & "auto_techsupport" will be added to the YANG Model for FEATURE Table

### State DB

#### AUTO_TECHSUPPORT|TS_CORE_MAP
```
key = "AUTO_TECHSUPPORT|TS_CORE_MAP"
<dump_name> = <core_dump_name;timestamp_as_epoch;crit_proc_name>
```
Eg:
```
hgetall "AUTO_TECHSUPPORT|TS_CORE_MAP"
sonic_dump_sonic_20210412_223645 = orchagent.1599047232.39.core;1599047233;orchagent
sonic_dump_sonic_20210405_202756 = python3.1617684247.17.core;1617684249;snmp-subagent
```

#### AUTO_TECHSUPPORT|FEATURE_PROC_INFO

```
key = "AUTO_TECHSUPPORT|FEATURE_PROC_INFO"
<feature_name;supervisor_proc_name> = <executable_name:pid>
```

Eg:
```
<swss;orchagent> = <orchagent;20>
<snmp;snmp-subagent> = <python3;22>
<lldp;lldp_syncd> = <python2;33>
```

## 5. CLI Enhancements.

### config cli
```
config auto-techsupport global auto-invoke-ts <enabled/disabled>
config auto-techsupport global coredump-cleanups <enabled/disabled>
config auto-techsupport global techsupport-cleanup <enabled/disabled>
config auto-techsupport global cooloff <uint16>
config auto-techsupport global max-techsupport <float upto two decimal places>
config auto-techsupport global core-usage <float upto two decimal places>
config auto-techsupport global since <string>

config feature autotechsupport <name> enabled|disabled>
config feature cooloff <name> <uint16>
```

### show cli

```
admin@sonic:~$ show auto-techsupport global
AUTO INVOKE TS    COREDUMP CLEANUP    TECHSUPPORT CLEANUP      COOLOFF    MAX TECHSUPPORT SIZE    CORE USAGE  SINCE
----------------  ------------------  ---------------------  ---------  ----------------------  ------------  ----------
enabled           enabled             enabled                      180                   12.23             5  2 days ago
 

admin@sonic:~$ show auto-techsupport history
Techsupport Dump                         Triggered By                   Critical Process
---------------------------------------  -----------------------------  ------------------
sonic_dump_sonic_20210819_192558.tar.gz  python3.1629401152.23.core.gz  snmp-subagent


admin@sonic:~$ show feature autotechsupport
Feature         Auto Techsupport      Cooloff (Sec)
--------------  ------------------  ---------------
bgp             enabled                         300
database        enabled                         300
dhcp_relay      enabled                         300
lldp            enabled                         300
macsec          enabled                         300
mgmt-framework  enabled                         300
nat             enabled                         300
pmon            enabled                         300
radv            enabled                         300
sflow           enabled                         300
snmp            enabled                         300
swss            enabled                         300
syncd           enabled                         300
teamd           enabled                         300
telemetry       enabled                         300
```

## 6. Design

### 6.1 Modifications to coredump-compress script

The coredump-compress script is updated to invoke the `coredump_gen_handler` script once it is done writing the core file to /var/core.

### 6.2 coredump_gen_handler script

A script under the name `coredump_gen_handler.py` is added to `/usr/local/bin/` directory which will be invoked after a coredump is generated.  The script first checks if this feature is enabled by the user. The script then verifies if a core dump file is created within the last 20 sec and if yes, it moves forward. 

The script invokes the show techsupport command, if the global cooloff & the per-docker cooloff period has passed. The script will also check if the Max Size configured by the user has already exceeded and if yes deletes the core files incrementally. 

Potential Syslog messages which can be logged are:
```
DATE sonic INFO coredump_gen_handler[pid]: Global Cooloff period has not passed. Techsupport Invocation is skipped. Core: python3.1629401152.23.core.gz
DATE sonic INFO coredump_gen_handler[pid]: Process Cooloff period for snmp has not passed.Techsupport Invocation is skipped. Core: python3.1629401152.23.core.gz
DATE sonic INFO coredump_gen_handler[pid]: "show techsupport --since '2 days ago'" is successful, sonic_dump_sonic_20210721_235228.tar.gz is created 
DATE sonic INFO coredump_gen_handler[pid]: core-usage argument is not set. No Cleanup is performed, current size occupied: 456 MB
DATE sonic INFO coredump_gen_handler[pid]: 12 MB deleted from /var/core.
DATE sonic INFO coredump_gen_handler[pid]:  No Corresponding Exit event info was found for python3.1629401152.23.core.gz. Techsupport Invocation is skipped
DATE sonic NOTICE coredump_gen_handler[pid]:  auto_invoke_ts is not enabled. No Techsupport Invocation will be performed. core: python3.1629401152.23.core.gz
DATE sonic NOTICE coredump_gen_handler[pid]:  auto-techsupport feature for swss is not enabled. Techsupport Invocation is skipped. core: python3.1629401152.23.core.gz
DATE sonic NOTICE coredump_gen_handler[pid]:  coredump_cleanup is disabled. No cleanup is performed
DATE sonic ERR coredump_gen_handler[pid]:  "show techsupport --since '2 days ago'" was run, but no techsupport dump is found
```

### 6.3 Requirements for FEATURE_PROC_INFO table

A coredump generate will be of format `<proc_comm_name>.<timestamp>.<pid>.core.gz`. comm name is typically the executable file name. The dump name is the only information directly available to coredump_gen_handler script. And Just by looking at this, it not possible to infer if the coredump generated is of a particular critical process. That information is read from AUTO_TECHSUPPORT|FEATURE_PROC_INFO table. 
 
Producer for this table is the supervisor-proc-exit-listener script running inside every docker. This script is an event listener for PROC_EXIT & PROC_RUNNING events for the processes running inside the docker and is naturally the right fit to populate the AUTO_TECHSUPPORT|FEATURE_PROC_INFO table. 
 
1) During a PROC_RUNNING Event: The comm information is read from /proc/<pid>/comm file and saving it in a local cache. 
2) A coredump will certainly trigger a PROC_EXIT event and, the exit-listener writes an entry of format specified in section 4 to the STATE DB.
 
coredump_gen_handler.py consumes this data and uses it for decisions based on the info written to this table.

### 6.4 Modifications to generate_dump script

The generate_dump script is updated to invoke the `techsupport_cleanup` script to handle the cleanup of techsupport files

### 6.5 techsupport_cleanup script

A script under the name `techsupport_cleanup.py` is added to `/usr/local/bin/` directory which will be invoked after a techsupport dump is created. The script first checks if the feature is enabled by the user. It then checks if the limit configured by the user has crossed and deletes the old techsupport files, if any.

Potential Syslog messages which can be logged are:
```
DATE sonic NOTICE techsupport_cleanup[pid]:  techsupport_cleanup is disabled. No cleanup is performed
DATE sonic INFO coredump_gen_handler[pid]: max-techsupport-size argument is not set. No Cleanup is performed, current size occupied: 456 MB
```

### 6.5 Warmboot consideration

No changes to this flow
 
### 6.6 Design choices for core-usage & max-techsupport-size argument 

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

/var/core & /var/dum directories are hosted on root-overlay filesystem and this usually ranges from 10G to 25G+. 
A default value of 5% would amount to a minimum of 500 MB which is a already a decent space for coredumps.  For techsupport a default value of 10% would amount to a minium of 1G, which might accomodate from 5-10 techsupports.  

Although if the admin feels otherwise, these values are configurable.

## 7. Test Plan

Enhance the existing techsupport sonic-mgmt test with the following cases.

| S.No | Test case synopsis                                                                                                                      |
|------|-----------------------------------------------------------------------------------------------------------------------------------------|
|  1   | Check if the `coredump_gen_handler` script is infact invoking the techsupport cmd, when configured                                      |
|  2   | Check if the techsupport cleanup is working as expected                                                                                 |
|  3   | Check if the global cooloff & per-process cooloff is honoured                                                                           |
|  4   | Check if the core-dump cleanup & techsupport-cleanup mechanisms are working as expected                                                 |

