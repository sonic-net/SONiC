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
- Limit the number of dumps


### High-Level Design

### SAI API Requirements
None

### Configuration and management

#### Config command

No new commands are introduced as part of this design.

#### Show command

No new commands are introduced as part of this design

#### DB Migrator


### YANG model changes


### Warmboot and Fastboot Considerations


### Testing Design

#### Unit tests
#### System tests


