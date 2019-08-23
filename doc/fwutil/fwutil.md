# SONiC FW utility

## High Level Design document

## Table of contents
- [About this manual](#about-this-manual)
- [Revision](#revision)
- [Abbreviations](#abbreviations)
- [1 Introduction](#1-introduction)
    - [1.1 Feature overview](#1.1-feature-overview)
    - [1.2 Requirements](#1.2-requirements)
        - [1.2.1 Command interface](#1.2.1-command-interface)
        - [1.2.2 Error handling](#1.2.2-error-handling)
        - [1.2.3 Event logging](#1.2.3-event-logging)
- [2 Design](#2-design)
    - [2.1 Overview](#2.1-overview)
    - [2.2 FW utility](#2.2-fw-utility)
        - [2.2.1 Command structure](#2.2.1-command-structure)
        - [2.2.2 Command interface](#2.2.2-command-interface)
            - [2.2.2.1 Show commands](#2.2.2.1-show-commands)
                - [2.2.2.1.1 Overview](#2.2.2.1.1-overview)
                - [2.2.2.1.2 Description](#2.2.2.1.2-description)
            - [2.2.2.2 Install commands](#2.2.2.2-install-commands)
                - [2.2.2.2.1 Overview](#2.2.2.2.1-overview)
                - [2.2.2.2.2 Description](#2.2.2.2.2-description)
            - [2.2.2.3 Update commands](#2.2.2.3-update-commands)
                - [2.2.2.3.1 Overview](#2.2.2.3.1-overview)
                - [2.2.2.3.2 Description](#2.2.2.3.2-description)
- [3 Tests](#3-tests)
    - [3.1 Unit tests](#3.1-unit-tests)
    - [3.2 Functional tests](#3.2-functional-tests)

## About this manual

This document provides general information about FW utility implementation in SONiC.

## Revision

| Rev | Date       | Author         | Description     |
|:---:|:----------:|:--------------:|:----------------|
| 0.1 | 21/08/2019 | Nazarii Hnydyn | Initial version |

## Abbreviations

| Term   | Meaning                                             |
|:-------|:----------------------------------------------------|
| FW     | Firmware                                            |
| SONiC  | Software for Open Networking in the Cloud           |
| PSU    | Power Supply Unit                                   |
| QSFP   | Quad Small Form-factor Pluggable                    |
| EEPROM | Electrically Erasable Programmable Read-Only Memory |
| I2C    | Inter-Integrated Circuit                            |
| SPI    | Serial Peripheral Interface                         |
| JTAG   | Joint Test Action Group                             |
| BIOS   | Basic Input/Output System                           |
| CPLD   | Complex Programmable Logic Device                   |
| FPGA   | Field-Programmable Gate Array                       |
| URL    | Uniform Resource Locator                            |
| API    | Application Programming Interface                   |
| N/A    | Not Applicable/Not Available                        |

## List of figures
[Figure 1: FW utility High Level Design](#figure-1-fw-utility-high-level-design)

## List of tables
[Table 1: Event logging](#table-1-event-logging)

# 1 Introduction

## 1.1 Feature overview

A modern network switch is a sophisticated equipment which consists of many auxiliary components
which are responsible for managing different subsystems (e.g., PSU/FAN/QSFP/EEPROM/THERMAL)
and providing necessary interfaces (e.g., I2C/SPI/JTAG).

Basically these components are complex programmable logic devices with it's own HW architecture
and software. The most important are BIOS/CPLD/FPGA etc.

It is very important to always have the latest recommended software version to improve device
stability, security and performance. Also, software updates can add new features
and remove outdated ones.

In order to make software update as simple as possible and to provide a nice user frindly
interface for various maintenance operations (e.g., install a new FW or query current version)
we might need a dedicated FW utility.

## 1.2 Requirements

### 1.2.1 Command interface

**This feature will support the following commands:**
1. show: display FW versions
2. install: manual FW installation
3. update: automatic FW installation

### 1.2.2 Error handling

**This feature will provide error handling for the next situations:**
1. Invalid input
2. Incompatible options/parameters
3. Invalid/nonexistent FW URL/path

**Note:** FW binary validation (checksum, format, etc.) should be done by Low Level Utility

### 1.2.3 Event logging

**This feature will provide event logging for the next situations:**
1. FW binary downloading over URL: start/end
2. FW binary downloading over URL: error
3. FW binary installation: start/end
4. FW binary installation: error

###### Table 1: Event logging

| Event                                     | Severity |
|:------------------------------------------|:---------|
| FW binary downloading over URL: start/end | NOTICE   |
| FW binary downloading over URL: error     | ERROR    |
| FW binary installation: start/end         | INFO     |
| FW binary installation: error             | ERROR    |

**Note:** Some extra information also shall be logged:
1. Component location (e.g., Chassis1/Module1/BIOS)
2. Operation result (e.g., success/failure)

# 2 Design

## 2.1 Overview

![FW utility High Level Design](images/fwutil_hld.svg "Figure 1: FW utility High Level Design")

###### Figure 1: FW utility High Level Design

In order to improve scalability and performance a modern network switches provide different architecture solutions:
1. Non modular chassis platforms
2. Modular chassis platforms

Non modular chassis platforms may contain one or more chassis.
Each chassis may contain it's own set of components.

Modular chassis platforms may contain one or more chassis.
Each chassis may contain one or more modules and it's own set of components.
Each module may contain it's own set of components.

Basically each chassis/module may contain one or more components (e.g., BIOS/CPLD/FPGA).

SONiC platform API provides an interface for FW maintenance operations for both modular
and non modular chassis platforms. Both modular and non modular chassis platforms share the same platform API,
but may have different implementation.

SONiC FW utility uses platform API to interact with the various platform components.

## 2.2 FW utility

### 2.2.1 Command structure

**User interface**:
```
fwutil
|--- show
|    |--- status
|    |--- version
|--- install
|    |--- chassis <chassis_name>
|         |--- component <component_name>
|         |    |--- fw <fw_path>
|         |--- module <module_name>
|              |--- component <component_name>
|                   |--- fw <fw_path>
|--- update -o|--online -i|--image=<current|next>
```

**Note:** <fw_path> can be absolute path or URL

### 2.2.2 Command interface

#### 2.2.2.1 Show commands

##### 2.2.2.1.1 Overview

The purpose of the show commands group is to provide an interface for:
1. FW utility related information query (version, etc.)
2. FW version query for various platform components

##### 2.2.2.1.2 Description

**The following command displays FW utility version:**
```bash
root@sonic:~# fwutil show version
fwutil version 1.0.0.0
```

**The following command displays platform components and FW versions:**
```bash
root@sonic:~# fwutil show status
Chassis   Module   Component  Version
--------  -------  ---------  ------------------
Chassis1  N/A      BIOS       0ACLH003_02.02.007
                   CPLD1      2
                   CPLD2      5
                   CPLD3      1
                   FPGA1      5
                   FPGA2      8
                   FPGA3      4
Chassis2  Module1  BIOS       0ACLH004_02.02.007
                   CPLD1      5
                   CPLD2      8
                   CPLD3      4
                   FPGA1      8
                   FPGA2      11
                   FPGA3      7
          Module2  BIOS       0ACLH004_02.02.007
                   CPLD1      5
                   CPLD2      8
                   CPLD3      4
                   FPGA1      8
                   FPGA2      11
                   FPGA3      7
```

#### 2.2.2.2 Install commands

##### 2.2.2.2.1 Overview

The purpose of the install commands group is to provide an interface
for manual FW update of various platform components.

##### 2.2.2.2.2 Description

**The following command installs FW on non modular chassis platform:**
```bash
root@sonic:~# fwutil install chassis Chassis1 component BIOS fw /home/admin/bios.fw
root@sonic:~# fwutil install chassis Chassis1 component CPLD1 fw /home/admin/cpld1.fw
root@sonic:~# fwutil install chassis Chassis1 component FPGA1 fw /home/admin/fpga1.fw
```

**The following command installs FW on modular chassis platform:**
```bash
root@sonic:~# fwutil install chassis Chassis1 module Module1 component BIOS fw /home/admin/bios.fw
root@sonic:~# fwutil install chassis Chassis1 module Module1 component CPLD1 fw /home/admin/cpld1.fw
root@sonic:~# fwutil install chassis Chassis1 module Module1 component FPGA1 fw /home/admin/fpga1.fw
```

#### 2.2.2.3 Update commands

##### 2.2.2.3.1 Overview

The purpose of the update commands group is to provide an interface
for automatic FW update of all available platform components.

Different FW sources shall be supported:
1. online - from internet
2. image - from current/next SONiC image

##### 2.2.2.3.2 Description

__The following command updates FW of all available platform components:__
```bash
root@sonic:~# fwutil update --online
root@sonic:~# fwutil update --image=next
```

**Note:** the default option is _--image=current_

# 3 Tests

## 3.1 Unit tests

1. Show FW utility version
2. Show components status

## 3.2 Functional tests

1. Install new BIOS/CPLD/FPGA FW on non modular chassis
2. Install new BIOS/CPLD/FPGA FW on modular chassis
3. Update FW on all available chassis components
