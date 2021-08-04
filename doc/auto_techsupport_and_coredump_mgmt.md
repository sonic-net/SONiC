# Event Driven TechSupport Invocation & CoreDump Mgmt #
#### Rev 1.0

## Table of Contents
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [1. Overview](#1-overview)
  * [2. High Level Requirements](#2-high-level-requirements)
  * [3. Core Dump Generation in SONiC](#3-core-dump-generation-in-sonic)
  * [4. Schema Additions](#4-schema-additions)
    * [4.1 YANG Model](#41-YANG-Model)
  * [5. CLI Enhancements](#5-cli-enhancements)
  * [6. Design](#6-design)
      * [6.1 coredump_gen_handler script](#61-coredump_gen_handler-script)
      * [6.2 techsupport_cleanup script](#62-techsupport_cleanup-script)
      * [6.3 Modifications to coredump-compress script](#63-Modifications-to-coredump-compress-script)
      * [6.4 Modifications to generate_dump script](#64-Modifications-to-generate-dump-script)
      * [6.5 Warmboot/Fastboot consideration](#65-Warmboot/Fastboot-consideration)
      * [6.6 Design choices for core-usage & max-techsupport-size argument](#66-Design-choices-for-core-usage-&-max-techsupport-sizeargument)
  * [7. Test Plan](#7-Test-Plan)


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/22/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |
| 1.1 |     TBD     | Vivek Reddy Karri        | Extending Support for Kernel Dumps                             |

## About this Manual
This document describes the details of the system which facilitates the auto techsupport invocation support in SONiC. The auto invocation is triggered when any process across the dockers or the host crashes and a core dump is generated.

## 1. Overview
Currently, techsupport is run by invoking `show techsupport` either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall idea behind this HLD. All the high-level requirements are summarized in the next section

## 2. High Level Requirements
### Global Scope
* Techsupport invocation should also be made event-driven based on core dump generation.
* This is only applicable for the critical processes running inside the dockers. Does not apply for other processes.
* init_cfg.json will be enhanced to include the "global CONFIG" required for this feature (described in section 4) and is enabled by default.
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

#### AUTO_TECHSUPPORT|global
```
key = "AUTO_TECHSUPPORT|global"
state = enabled|disabled;       # Enable/Disable the feature globally 
cooloff = 300;                  # Minimum Time in seconds, between two successive techsupport invocations.
                                  Manual Invocations will be considered as well in the cooloff calculation
max-techsupport-size = 10;      # A perentage value should be specified. 
                                  This signifies maximum Size to which /var/dump/ directory can be grown until. 
                                  The actual value in bytes is calculate based on the available space in the filesystem hosting /var/dump
                                  When the limit is crossed, the older techsupport dumps are incrementally deleted                         
core-usage = 5;                 # A perentage value should be specified. 
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

### 4.1 YANG Model

```
module sonic-auto_techsupport {

    yang-version 1.1;

    namespace "http://github.com/Azure/sonic-auto_techsupport";
    prefix auto_techsupport;

    description "Auto Techsupport Capability in SONiC OS";

    revision 2021-06-17 {
        description "First Revision";
    }

    container sonic-auto_techsupport {

        container AUTO_TECHSUPPORT {

                description "AUTO_TECHSUPPORT part of config_db.json";
                
                container global {
               
                    leaf status {
                        description "AUTO_TECHSUPPORT status";
                        type enumeration {
                            enum disable;
                            enum enable;
                        }
                        default disable;
                    }

                    leaf cooloff {
                        description "Minimum Time in seconds, between two successive techsupport invocations by the script.";
                        type uint16;
                        default "300";
                    }

                    leaf max-techsupport-size {
                        description "A perentage value should be specified. 
                                    This signifies maximum Size to which /var/core directory can be grown until. 
                                    The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                    When the limit is crossed, the older core files are incrementally deleted";
                        type uint8{
                             range "0..100" {
                                error-message "Can only be between 1 to 100"; 
                             }
                        }
                        default "10";
                    }

                    leaf core-usage {
                        description "A perentage value should be specified. 
                                     This signifies maximum Size to which /var/core directory can be grown until
                                     The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                     When the limit is crossed, the older core files are deleted."
                                     Disabled by default. Configure '0' to explicitly disable";;
                        type uint8 {
                             range "0..100" {
                                error-message "Can only be between 1 to 100"; 
                             }
                        }
                        default "5";
                    }
                    
                    leaf since {
                        description "This limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided.
                                     Any valid date string of the formats specified here (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                                     can be used.                          
                                     If this value is not explicitly configured or a non-valid string is provided, a default value of "2 days ago" is used";
                        type string {
                            length 1..255;
                        }
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


## 5. CLI Enhancements.

### config cli
```
config auto-techsupport state <enabled/disabled>
config auto-techsupport cooloff <uint16>
config auto-techsupport max-techsupport <uints8>
config auto-techsupport core-usage <0..100>
config auto-techsupport since <string>

config feature auto-techsupport <name> enabled|disabled>
config feature cooloff <name> <uint16>
```

### show cli

```
admin@sonic:~$ show auto-techsupport global
STATUS      COOLOFF    MAX_TECHSUPPORT_DUMPS   MAX_CORE_DUMP_USAGE_SIZE  SINCE        LAST_TECHSUPPORT_RUN
-------     -------    ---------------------   ------------------------  ----------   -------------------------------
Enabled     300 sec    3                       200000 KB / 2%            2 days ago   Tue 15 Jun 2021 08:09:59 PM UTC

admin@sonic:~$ show feature status
Feature         State    AutoRestart  SetOwner   cooloff Auto-techsupport  
--------------  -------- ----------   --------   ------- ----------------    
swss            enabled  enabled                 600     enabled
.....

```

## 6. Design

### 6.1 coredump_gen_handler script

A script under the name `coredump_gen_handler` is added to `/usr/local/bin/` directory which will be invoked after a coredump is generated.  The script first checks if this feature is enabled by the user. The script then verifies if a core dump file is created within the last 20 sec and if yes, it moves forward. 

The script invokes the show techsupport command, if the global cooloff & the per-docker cooloff period has passed. The script will also independently check if the Max Size configured by the user has already exceeded and if yes deletes the core files incrementally. 

Potential Syslog messages which can be logged are:
```
DATE sonic INFO coredump_gen_handler[pid]:  Cooloff period has not yet passed.  No Techsupport Invocation is performed 
DATE sonic NOTICE coredump_gen_handler[pid]:  Techsupport Invocation is successful, sonic_dump_sonic_20210721_235228.tar.gz is created in response to the coredump orchagent.1626916631.117644.core.gz
DATE sonic ERR coredump_gen_handler[pid]:  Techsupport Invocation failed, No techsupport dump was created in the /var/dump directory
DATE sonic INFO coredump_gen_handler[pid]:  No Cleanup process is initiated since the core-usage param is not configured
DATE sonic NOTICE coredump_gen_handler[pid]:  /var/core cleanup performed. 12456 bytes are cleared.
```
### 6.2 techsupport_cleanup script

A script under the name `techsupport_cleanup` is added to `/usr/local/bin/` directory which will be invoked after a techsupport dump is created. The script first checks if the feature is enabled by the user. It then checks if the limit configured by the user has crossed and deletes the old techsupport files, if any.

Potential Syslog messages which can be logged are:
```
DATE sonic NOTICE techsupport_cleanup[pid]: /var/dump/ cleanup is performed. current number of dumps: 4
```

### 6.3 Modifications to coredump-compress script

The coredump-compress script is updated to invoke the `coredump_gen_handler` script once it is done writing the core file to /var/core.

### 6.4 Modifications to generate_dump script

The generate_dump script is updated to invoke the `techsupport_cleanup` script to handle the cleanup of techsupport files

### 6.5 Warmboot/Fastboot consideration

No impact for warmboot/fastboot flows.

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

