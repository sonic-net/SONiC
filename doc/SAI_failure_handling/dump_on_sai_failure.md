# Dump on SAI failure #

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [High-Level Design](#high-level-design)
- [SAI API Requirements](#sai-api-requirements)
- [Configuration and management ](#configuration-and-management)
    - [Config command](#config-command)
    - [Show command](#show-command)
    - [DB Migrator](#db-migrator)
- [YANG Model changes](#yang-model-changes)
- [Warmboot and Fastboot Considerations](#warmboot-and-fastboot-considerations)
- [Testing Design](#testing-design)
    - [Unit Tests](#unit-tests)
    - [System tests](#system-tests)


### Revision

 | Rev |     Date    |       Author        | Change Description                         |
 |:---:|:-----------:|:-------------------:|--------------------------------------------|
 | 0.1 |             |      Sudharsan      | Initial version                            |

### Scope
The scope of this document is to design the handling of taking a dump during a SAI failure. 

### Definitions/Abbreviations
 

### Overview
In the existing design, when SAI failure occurs, the orchagent aborts and all the dependent services including syncd restart. This results in failure to take the SAI, SDK and lower layer state during the problem state resulting in loss of information to debug.
To solve this issue, whenever there is a SAI failure, orchagent requests syncd to take relevant dumps and once done, it proceeds for the abort.

### Requirements

Primary requirements for taking dump during SAI failure are
- The dump needs to be taken synchronosly before abort.
- The infra to take dump should be flexible to allow for platform specific calls similar to techsupport.
- The dumps should be accessible in the host which can be then collected by techsupport.
- Limit the number of dumps (Rotation)


### High-Level Design
A new enum value for SAI_REDIS_SWITCH_ATTR_NOTIFY_SYNCD is defined (SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP). When there is a SAI failure, before calling the abort, orchagent sets the switch attribute SAI_REDIS_SWITCH_ATTR_NOTIFY_SYNCD with value SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP attribute. On receiving this attribute syncd calls the generic dump script which is present in /usr/bin/syncd_dump.sh. This script will check for the presence of platform specific dump script which should be located at /usr/bin/platform_syncd_dump.sh. If this script is present, it would be invoked to take the necessary dump. Vendors if they intend to take dumps during SAI failure can define the script in their syncd docker. The dumps collected from this script should be stored in /var/log/sai_failure_dump/ which will be exposed to the host. Only one file should be stored per dump in order to facilitate the rotation logic. Once the dump is finished, the generic syncd dump script will perform rotation on /var/log/sai_failure_dump/ to restrict the number of dumps. A variable by name SAI_MAX_FAILURE_DUMPS is defined in the generic script which by default is set to 10. This variable can be overwritten in the platform specific script if the platform wants a different number of dumps.

Later when techsupport is invoked manually or invoked through auto techsupport, these dumps will be collected and once collected, they will be cleared from /var/log/sai_failure_dump/

The below diagram explains the sequence when a SAI failure happens
![](/images/SAI_failure_handling/SAI_failure_dump_sequence.JPG)

The flow inside syncd is shown below
![](/images/SAI_failure_handling/SAI_failure_dump_flow.JPG)

### SAI API Requirements
None

### Configuration and management

#### Config command

No new commands are introduced as part of this design.

#### Show command

No new commands are introduced as part of this design

#### DB Migrator
N/A

### YANG model changes
N/A

### Warmboot and Fastboot Considerations
N/A

### Testing Design

#### Unit tests
1) Gtest for syncd infrastructure to test the SAI_REDIS_SWITCH_ATTR_NOTIFY_SYNCD.
2) Gtest in orchagent to test the SAI failure scenario

#### System tests
1) Simulate SAI failure and verify if SAI failure dump is created.
2) Verify if the dump in techsupport contains the SAI failure dump is collected.

