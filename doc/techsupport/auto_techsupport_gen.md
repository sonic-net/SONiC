# Auto Techsupport Enhancement #
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
      * [6.6 Design choices for core-usage argument](#66-Design-choices-for-core-usage-argument )


### Revision  
| Rev |     Date    |       Author       | Change Description          |
|:---:|:-----------:|:-------------------------|:----------------------|
| 1.0 | 06/22/2021  | Vivek Reddy Karri        | Auto Invocation of Techsupport, triggered by a core dump       |


## About this Manual
This document describes the details of the system which facilitates the auto techsupport invocation support in SONiC. The auto invocation is triggered when any process across the dockers or the host crashes and a core dump is generated.

## 1. Overview
Currently, techsupport is run by invoking `show techsupport` either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the `/var/core/` directory.

However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. That is the overall idea behind this HLD. All the high-level requirements are summarized in the next section

## 2. High Level Requirements
* Techsupport invocation should also be made event-driven based on core dump generation
* This capability should be made optional and is enabled by default
* Users should have the abiliity to configure this capability.

## 3. Core Dump Generation in SONiC
In SONiC, the core dumps generated from any process crashes are directed to the location `/var/core` and will have the naming format `/var/core/*.core.gz`. 
The naming format and compression is governed by the script `/usr/local/bin/coredump-compress`.

## 4. Schema Additions

#### Config DB
```
key = "AUTO_TECHSUPPORT|global"
state = enabled|disabled; 
cooloff = 300;                  # Minimum Time in seconds, between two successive techsupport invocations.
                                  Manual Invocations will be considered as well in the cooloff calculation
max-techsupports = 5;           # Maximum number of Techsupport dumps (Doesn't matter if it's manually or auto invoked), 
                                  which are allowed to be present on the device.
                                  The oldest one will be deleted, when the the limit has already crossed this.                         
core-usage = 5;                 # A perentage value should be specified. 
                                  This signifies maximum Size to which /var/core directory can be grown until. 
                                  The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                  When the limit is crossed, the older core files are incrementally deleted
since = "2 days ago";           # This limits the auto-invoked techsupport to only collect the logs & core-dumps generated since the time provided.
                                  Any valid date string of the formats specified here (https://www.gnu.org/software/coreutils/manual/html_node/Date-input-formats.html) 
                                  can be used.                           
                                  If this value is not explicitly configured or a non-valid string is provided, a default value of "2 days ago" is used.
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

                    leaf max-techsupports {
                        description "Maximum number of Techsupport dumps, which can be present on the switch.
                                     The oldest one will be deleted, when the the limit has already crossed this. ";
                        type uint8;
                        default "5";
                    }

                    leaf core-usage {
                        description "A perentage value should be specified. 
                                     This signifies maximum Size to which /var/core directory can be grown until
                                     The actual value in bytes is calculate based on the available space in the filesystem hosting /var/core
                                     When the limit is crossed, the older core files are deleted.";
                        type uint8 {
                             range "1..100" {
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



## 5. CLI Enhancements.

### config cli
```
config auto-techsupport state <enabled/disabled>
config auto-techsupport cooloff <uint16>
config auto-techsupport max-techsupport <uints8>
config auto-techsupport core-usage <1..100>
config auto-techsupport since <string>
```

### show cli

```
admin@sonic:~$ show auto-techsupport 
STATUS      COOLOFF    MAX_TECHSUPPORT_DUMPS   MAX_CORE_DUMP_USAGE_SIZE  SINCE        LAST_TECHSUPPORT_RUN
-------     -------    ---------------------   ------------------------  ----------   -------------------------------
Enabled     300 sec    3                       200000 KB / 2%            2 days ago   Tue 15 Jun 2021 08:09:59 PM UTC
```

## 6. Design

### 6.1 coredump_gen_handler script

A script under the name `coredump_gen_handler` is added to `/usr/local/bin/` directory which will be invoked after a coredump is generated.  The script first checks if this feature is enabled by the user. The script then verifies if a core dump file is created within the last 20 sec and if yes, it moves forward. 

The script invokes the show techsupport command, if the cooloff period configured by the user has passed. The script will also independently check if the Max Size configured by the user has already exceeded and if yes deletes the core files incrementally. 

### 6.2 techsupport_cleanup script

A script under the name `techsupport_cleanup` is added to `/usr/local/bin/` directory which will be invoked after a techsupport dump is created. The script first checks if the feature is enabled by the user. It then checks if the limit configured by the user has crossed and deletes the old techsupport files, if any.

### 6.3 Modifications to coredump-compress script

The coredump-compress script is updated to invoke the `coredump_gen_handler` script once it is done writing the core file to /var/core.

### 6.4 Modifications to generate_dump script

The generate_dump script is updated to invoke the `techsupport_cleanup` script to handle the cleanup of techsupport files

### 6.5 Warmboot/Fastboot consideration

No impact for warmboot/fastboot flows.

### 6.6 Design choices for core-usage argument 

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

/var/core directory is hosted on root-overlay filesystem and this usually ranges from 10G to 25G+. 
Since Techsupport dumps are also hosted on the same filesystem, a slightly pessimistic default value of 5% is chosen. This would amount to a minimum of 500 MB which is a already a decent space for coredumps. In normal conditions, a core dump will usually be in the order of hundreds of KB's to tens of MB's.

Although if the admin feels otherwise, this value is configurable.



