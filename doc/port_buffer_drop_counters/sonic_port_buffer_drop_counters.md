# Port buffer drop counters in SONiC

# Requirements Document

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Defintions/Abbreviation](#definitionsabbreviation)
* [1 Overview](#1-overview)
* [2 Requirements](#2-requirements)
    - [2.1 Functional Requirements](#21-functional-requirements)
    - [2.2 Supported Counters](#24-supported-counters)
* [3 Design](#3-design)
    - [3.1 CLI (and usage example)](#31-cli-and-usage-example)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)


# Revision
| Rev | Date     | Author      | Change Description        |
|:---:|:--------:|:-----------:|---------------------------|
| 0.1 | 07/08/20 | Mykola Faryma | Initial version           |


# About this Manual
This document provides an overview of requirements of port buffer drop counters in SONiC.

# Scope
This document describes the motivation for port buffer drop counters and the changes expected.

# Definitions/Abbreviation
| Abbreviation | Description     |
|--------------|-----------------|
| FC           | Flex Counter |

# 1 Overview

The main goal of this feature is to poll port level buffer drop counters in a safe way. 
According to https://github.com/sonic-net/sonic-swss/pull/1308,

> These counters are causing widespread issues in the master branch, so we're backing them out for now to be revisited in a later PR. They will likely need to be polled separately from the other counters, and on a longer interval, to avoid performance issues and conflicts.

The solution for now is to introduce a new FC group with a larger polling interval than the rest of port counters.
Also limit user configuring a small interval for this FC group via CLI.

# 2 Requirements

## 2.1 Functional Requirements
1. New flex counter group is introduced for the port-level buffer drop counters
2. The FC group is enabled by default
3. The polling interval is 60s by default
3. Users can configure FC group via a CLI tool
    1. Users can enable/disable polling
    2. Users can set the polling interval in range from 30s to 5m
    3. Users can view the FC configuration


## 2.2 Supported Counters
* SAI_PORT_STAT_IN_DROPPED_PKTS: port-level ingress buffer drop counters
* SAI_PORT_STAT_OUT_DROPPED_PKTS: port-level egress buffer drop counters

# 3 Design

## 3.1 CLI (and usage example)

### 3.1.1 Displaying the FC configuration

#### Current imlemenation

```
admin@sonic:~$ counterpoll show
Type                        Interval (in ms)    Status
--------------------------  ------------------  --------
QUEUE_STAT                  default (10000)     enable
PORT_STAT                   default (1000)      enable
RIF_STAT                    default (1000)      enable
QUEUE_WATERMARK_STAT        default (10000)     enable
PG_WATERMARK_STAT           default (10000)     enable
BUFFER_POOL_WATERMARK_STAT  default (10000)     enable

```

#### New imlementation

```
admin@sonic:~$ counterpoll show
Type                        Interval (in ms)    Status
--------------------------  ------------------  --------
QUEUE_STAT                  default (10000)     enable
PORT_STAT                   default (1000)      enable
PORT_BUFFER_DROP            default (60000)     enable
RIF_STAT                    default (1000)      enable
QUEUE_WATERMARK_STAT        default (10000)     enable
PG_WATERMARK_STAT           default (10000)     enable
BUFFER_POOL_WATERMARK_STAT  default (10000)     enable

```

### 3.1.2 Enabling/Disabling the polling 
```
admin@sonic:~$ counterpoll port-buffer-drop enable
admin@sonic:~$ counterpoll port-buffer-drop disable
```

### 3.1.3 Setting new polling interval 
```
admin@sonic:~$ counterpoll port-buffer-drop interval 30000
```
