# SONiC FW utility

## High Level Design document

## Table of contents
- [About this manual](#about-this-manual)
- [Revision](#revision)
- [Abbreviations](#abbreviations)
- [1 Introduction](#1-introduction)
    - [1.1 Feature overview](#11-feature-overview)
    - [1.2 Requirements](#12-requirements)
        - [1.2.1 Functionality](#121-functionality)
        - [1.2.2 Command interface](#122-command-interface)
        - [1.2.3 Error handling](#123-error-handling)
        - [1.2.4 Event logging](#124-event-logging)
- [2 Design](#2-design)
    - [2.1 Overview](#21-overview)
    - [2.2 FW utility](#22-fw-utility)
        - [2.2.1 Command structure](#221-command-structure)
        - [2.2.2 Command interface](#222-command-interface)
            - [2.2.2.1 Show commands](#2221-show-commands)
                - [2.2.2.1.1 Overview](#22211-overview)
                - [2.2.2.1.2 Description](#22212-description)
            - [2.2.2.2 Install commands](#2222-install-commands)
                - [2.2.2.2.1 Overview](#22221-overview)
                - [2.2.2.2.2 Description](#22222-description)
            - [2.2.2.3 Update commands](#2223-update-commands)
                - [2.2.2.3.1 Overview](#22231-overview)
                - [2.2.2.3.2 Description](#22232-description)
            - [2.2.2.4 Auto-Update commands](#2224-auto-update-commands)
                - [2.2.2.4.1 Overview](#22241-overview)
                - [2.2.2.4.2 Description](#22242-description)
                - [2.2.2.4.3 Custom FW Update Script](#22243-custon-fw-update-script)
                - [2.2.2.4.4 Auto-update Use Cases](#22243-auto-update-use-cases)
- [3 Flows](#3-flows)
    - [3.1 Show components status](#31-show-components-status)
    - [3.2 Show available updates](#32-show-available-updates)
    - [3.3 Install component FW](#33-install-component-fw)
        - [3.3.1 Non modular chassis platform](#331-non-modular-chassis-platform)
        - [3.3.2 Modular chassis platform](#332-modular-chassis-platform)
    - [3.4 Auto-update component FW](#34-auto-update-component-fw)
        - [3.4.1 Auto-update Platform API](#331-auto-update-w-platform-api)
        - [3.4.2 Auto-update with Custom FW Update script](#332-auto-update-w-custom-fw-update-script)
- [4 Tests](#4-tests)
    - [4.1 Unit tests](#41-unit-tests)

## About this manual

This document provides general information about FW utility implementation in SONiC.

## Revision

| Rev | Date       | Author         | Description                       |
|:---:|:----------:|:--------------:|:----------------------------------|
| 0.1 | 21/08/2019 | Nazarii Hnydyn | Initial version                   |
| 0.2 | 10/09/2019 | Nazarii Hnydyn | Review feedback and other changes |
| 0.3 | 17/09/2019 | Nazarii Hnydyn | Align flows with the platform API |
| 0.4 | 18/12/2019 | Nazarii Hnydyn | CLI review feedback               |
| 0.5 | 05/05/2020 | Nazarii Hnydyn | Automatic FW update per component |
| 0.6 | 08/03/2020 | Sujin Kang     | Add firmware auto-update command  |
|     |            |                | based on platform-fw-update.json, |
|     |            |                | support custom component fw script|

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
| SSD    | Solid State Drive                                   |
| URL    | Uniform Resource Locator                            |
| API    | Application Programming Interface                   |
| N/A    | Not Applicable/Not Available                        |

## List of figures

[Figure 1: FW utility High Level Design](#figure-1-fw-utility-high-level-design)  
[Figure 2: Show components status flow](#figure-2-show-components-status-flow)  
[Figure 3: Show available updates flow](#figure-3-show-available-updates-flow)  
[Figure 4: FW install (non modular) flow](#figure-4-fw-install-non-modular-flow)  
[Figure 5: FW install (modular) flow](#figure-5-fw-install-modular-flow)  

## List of tables

[Table 1: Event logging](#table-1-event-logging)

# 1 Introduction

## 1.1 Feature overview

A modern network switch is a sophisticated equipment which consists of many auxiliary components  
which are responsible for managing different subsystems (e.g., PSU/FAN/QSFP/EEPROM/THERMAL)  
and providing necessary interfaces (e.g., I2C/SPI/JTAG).

Basically these components are complex programmable logic devices with it's own HW architecture  
and software. The most important are BIOS/CPLD/FPGA etc.

It is very important to always have the latest recommended software version to improve device stability,  
security and performance. Also, software updates can add new features and remove outdated ones.

In order to make software update as simple as possible and to provide a nice user frindly  
interface for various maintenance operations (e.g., install a new FW or query current version)  
we might need a dedicated FW utility.

## 1.2 Requirements

### 1.2.1 Functionality

**This feature will support the following functionality:**
1. Manual FW installation for particular platform component
2. Automatic FW installation for particular platform component
3. Querying platform components and FW versions
4. Querying available FW updates for all platform components

### 1.2.2 Command interface

**This feature will support the following commands:**
1. show: display FW versions/updates
2. install: manual FW installation
3. update: automatic FW installation

### 1.2.3 Error handling

**This feature will provide error handling for the next situations:**
1. Invalid input
2. Incompatible options/parameters
3. Invalid/nonexistent FW URL/path

**Note:** FW binary validation (checksum, format, etc.) should be done by SONiC platform API

### 1.2.4 Event logging

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

**Note:** Some extra information also will be logged:
1. Component location (e.g., Chassis1/Module1/BIOS)
2. Operation result (e.g., success/failure)

# 2 Design

## 2.1 Overview

![FW utility High Level Design](images/fwutil_hld.svg "Figure 1: FW utility High Level Design")

###### Figure 1: FW utility High Level Design

In order to improve scalability and performance a modern network switches provide different architecture solutions:
1. Non modular chassis platforms
2. Modular chassis platforms

Non modular chassis platforms may contain only one chassis.  
A chassis may contain it's own set of components.

Modular chassis platforms may contain only one chassis.  
A chassis may contain one or more modules and it's own set of components.  
Each module may contain it's own set of components.

Basically each chassis/module may contain one or more components (e.g., BIOS/CPLD/FPGA).

SONiC platform API provides an interface for FW maintenance operations for both modular and  
non modular chassis platforms. Both modular and non modular chassis platforms share the same platform API,  
but may have different implementation.

SONiC FW utility uses platform API to interact with the various platform components.

## 2.2 FW utility

### 2.2.1 Command structure

**User interface**:
```
fwutil
|--- show
|    |--- version
|    |--- status
|    |--- updates -i|--image=<current|next>
|
|--- install
|    |--- chassis
|    |    |--- component <component_name>
|    |         |--- fw -y|--yes <fw_path>
|    |
|    |--- module <module_name>
|         |--- component <component_name>
|              |--- fw -y|--yes <fw_path>
|
|--- update
|    |--- chassis
|    |    |--- component <component_name>
|    |         |--- fw -y|--yes -f|--force -i|--image=<current|next>
|    |
|    |--- module <module_name>
|         |--- component <component_name>
|              |--- fw -y|--yes -f|--force -i|--image=<current|next>
|
|--- auto-update
     |--- chassis
     |    |--- component <component_name>
     |         |--- fw -y|--yes -f|--force -i|--image=<current|next> --b|--boot=<any|none|(immediate_)fast|(immediate_)warm|(immediate_)cold|(immediate_)powercycle> 
     |--- module <module_name>
     |    |--- component <component_name>
     |         |--- fw -y|--yes -f|--force -i|--image=<current|next>  --b|--boot=<any|none|(immediate_)fast|(immediate_)warm|(immediate_)cold|(immediate_)powercycle>
     |--- fw -y|--yes -f|--force -i|--image=<current|next> --b|--boot=<any|none|(immediate_)fast|(immediate_)warm|(immediate_)cold|(immediate_)powercycle>
     |--- fw -y|--yes -f|--force -z|--fw-image=<fw_package.tar.gz> --b|--boot=<any|none|(immediate_)fast|(immediate_)warm|(immediate_)cold|(immediate_)powercycle>
     
```

### 2.2.2 Command interface

#### 2.2.2.1 Show commands

##### 2.2.2.1.1 Overview

The purpose of the show commands group is to provide an interface for:
1. FW utility related information query (version, etc.)
2. Platform components related information query (version, description, etc.)
3. Available FW updates related information query (fw, version, status, etc.)

##### 2.2.2.1.2 Description

**The following command displays FW utility version:**
```bash
root@sonic:~# fwutil show version
fwutil version 1.0.0.0
```

**The following command displays platform components and FW versions:**
1. Non modular chassis platform
```bash
root@sonic:~# fwutil show status
Chassis   Module   Component   Version             Description
--------  -------  ----------  ------------------  ------------
Chassis1  N/A      BIOS        0ACLH003_02.02.007  Chassis BIOS
                   CPLD        5                   Chassis CPLD
                   FPGA        5                   Chassis FPGA
```

2. Modular chassis platform
```bash
root@sonic:~# fwutil show status
Chassis   Module   Component   Version             Description
--------  -------  ----------  ------------------  ------------
Chassis1           BIOS        0ACLH004_02.02.007  Chassis BIOS
                   CPLD        5                   Chassis CPLD
                   FPGA        5                   Chassis FPGA
          Module1  CPLD        5                   Module CPLD
                   FPGA        5                   Module FPGA
```

**The following command displays available FW updates:**
1. Non modular chassis platform
```bash
root@sonic:~# fwutil show updates --image=next
Chassis   Module   Component   Firmware               Version (current/available)              Status              Required Boot Action
--------  -------  ----------  ---------------------  ---------------------------------------  ------------------  -----------------------
Chassis1  N/A      BIOS        <image_path>/bios.bin  0ACLH004_02.02.007 / 0ACLH004_02.02.010  update is required  None
                   CPLD        <image_path>/cpld.bin  5 / 10                                   update is required  Power cycle
                   FPGA        <image_path>/fpga.bin  5 / 5                                    up-to-date          Cold reboot
                   SSD         <image_path>/ssd.bin   4 / 5                                    update is required  Immediate Cold/Fast reboot
```

2. Modular chassis platform
```bash
root@sonic:~# fwutil show updates --image=next
Chassis   Module   Component   Firmware               Version (current/available)              Status              Required Boot Action
--------  -------  ----------  ---------------------  ---------------------------------------  ------------------  -----------------------
Chassis1           BIOS        <image_path>/bios.bin  0ACLH004_02.02.007 / 0ACLH004_02.02.010  update is required  None
                   CPLD        <image_path>/cpld.bin  5 / 10                                   update is required  Power cycle
                   FPGA        <image_path>/fpga.bin  5 / 5                                    up-to-date          Cold reboot
                   SSD         <image_path>/ssd.bin   4 / 5                                    update is required  Immediate Cold/Fast reboot
          Module1  CPLD        <image_path>/cpld.bin  5 / 10                                   update is required  Power cycle
                   FPGA        <image_path>/fpga.bin  5 / 5                                    up-to-date          Cold reboot
```

3. Custom FW Package
```bash
root@sonic:~# fwutil show updates --fw-image=fw_update.tar.gz
Component   Firmware               Version (current/available)              Status              Required Boot Action
----------  ---------------------  ---------------------------------------  ------------------  -----------------------
BIOS        <image_path>/bios.bin  0ACLH004_02.02.007 / 0ACLH004_02.02.010  update is required  None
CPLD        <image_path>/cpld.bin  5 / 10                                   update is required  Power cycle
FPGA        <image_path>/fpga.bin  5 / 5                                    up-to-date          Cold reboot
SSD         <image_path>/ssd.bin   4 / 5                                    update is required  Immediate Cold/Fast reboot
```

**Supported options:**
1. -i|--image - show updates using current/next SONiC image
2. -z|--fw-image - show updates using custom FW package

**Note:** the default option is _--image=current_

#### 2.2.2.2 Install commands

##### 2.2.2.2.1 Overview

The purpose of the install commands group is to provide an interface  
for manual FW installation of various platform components.

##### 2.2.2.2.2 Description

**The following command installs FW:**
1. Non modular chassis platform
```bash
root@sonic:~# fwutil install chassis component BIOS fw --yes <image_path>/bios.bin
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil install chassis component CPLD fw --yes <image_path>/cpld.bin
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil install chassis component FPGA fw --yes <image_path>/fpga.bin
Warning: <firmware_update_notification>
...
FW update in progress ...
...
```

2. Modular chassis platform
```bash
root@sonic:~# fwutil install chassis component BIOS fw <image_path>/bios.bin
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil install chassis component CPLD fw <image_path>/cpld.bin
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil install chassis component FPGA fw <image_path>/fpga.bin
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil install module Module1 component CPLD fw <image_path>/cpld.bin
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil install module Module1 component FPGA fw <image_path>/fpga.bin
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
```

**Supported options:**
1. -y|--yes - automatic yes to prompts. Assume "yes" as answer to all prompts and run non-interactively

#### 2.2.2.3 Update commands

##### 2.2.2.3.1 Overview

The purpose of the update commands group is to provide an interface  
for automatic FW installation of various platform components.

Automatic FW installation requires platform_components.json to be created and placed at:  
_sonic-buildimage/device/<platform_name>/<onie_platform>/platform_fw_update.json_
default image path = /usr/share/sonic/<platform_name>/<onie_platform>/fw_update/

**Example:**
1. Non modular chassis platform
```json
{
    "chassis": {
        "Chassis1": {
            "component": {
                "BIOS": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/bios.bin",
                    "version": "0ACLH003_02.02.010"
                },
                "CPLD": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld.bin",
                    "version": "10"
                },
                "FPGA": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga.bin",
                    "version": "5"
                }
            }
        }
    }
}
```

2. Modular chassis platform
```json
{
    "chassis": {
        "Chassis1": {
            "component": {
                "BIOS": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/bios.bin",
                    "version": "0ACLH003_02.02.010"
                },
                "CPLD": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld.bin",
                    "version": "10"
                },
                "FPGA": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga.bin",
                    "version": "5"
                }
            }
        }
    },
    "module": {
        "Module1": {
            "component": {
                "CPLD": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld.bin",
                    "version": "10"
                },
                "FPGA": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga.bin",
                    "version": "5"
                }
            }
        }
    }
}
```

**Note:**
1. FW update will be disabled if component definition is not provided (e.g., 'BIOS': { })
2. FW version will be read from image if `version` field is not provided

##### 2.2.2.3.2 Description

**The following command updates FW:**
1. Non modular chassis platform
```bash
root@sonic:~# fwutil update chassis component BIOS fw --yes --image=next
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil update chassis component CPLD fw --yes --image=next
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil update chassis component FPGA fw --yes --image=next
Warning: <firmware_update_notification>
...
FW update in progress ...
...
```

2. Modular chassis platform
```bash
root@sonic:~# fwutil update chassis component BIOS fw --image=next
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil update chassis component CPLD fw --image=next
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil update chassis component FPGA fw --image=next
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil update module Module1 component CPLD fw --image=next
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
root@sonic:~# fwutil update module Module1 component FPGA fw --image=next
Warning: <firmware_update_notification>
New FW will be installed, continue? [y/N]: N
Aborted!
```

**Supported options:**
1. -y|--yes - automatic yes to prompts. Assume "yes" as answer to all prompts and run non-interactively
2. -f|--force - install FW regardless the current version
3. -i|--image - update FW using current/next SONiC image

**Note:** the default option is _--image=current_

#### 2.2.2.4 Auto-update commands

##### 2.2.2.4.1 Overview

The purpose of the auto-update commands group is to provide an interface  
for automatic FW installation of various platform components.

Automatic FW installation requires default platform_components.json to be created and placed at:  
_sonic-buildimage/device/<platform_name>/<onie_platform>/platform_fw_update.json_
default image path = /usr/share/sonic/<platform_name>/<onie_platform>/fw_update/

Auto-update command can also support the standalone custom firmware image package with --fw-image option. 
The package can be any format between `.tar` or `.tar.gz`.
The `fwutil` commands uncompress the package and parse the `platform_fw_update.json` to retrieve the firmware information.

If the script path is available for the component firmware configuration in the `platform_fw_update.json`, it means that the specific component firmware upgrade shall use the script to process the fwutil commands.
`2.2.2.4.3 Component Firmware Update Script Interface Requirement` explains the requirement of the component firmware upgrade script to interfere with the fwutil to support the auto-update command - mainly status and install.

**Example:**

1. Platform component fw update configuration with boot options
```json
{
    "chassis": {
        "Chassis1": {
            "component": {
                "BIOS": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/bios.bin",
                    "version": "0ACLH003_02.02.010",
                    "boot-action": "any"
                },
                "CPLD": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld.bin",
                    "version": "10",
                    "boot-action": "power"
                },
                "FPGA": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga.bin",
                    "version": "5",
                    "boot-action": "cold"
                }
            }
        }
    }
}
```

2. Platform component fw update configuration with platform specific script and boot options
```json
{
    "chassis": {
        "Chassis1": {
            "component": {
                "BIOS": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/bios.bin",
                    "script": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/bios_fw_update",
                    "version": "0ACLH003_02.02.010"
                    "boot-action": "any",
                },
                "CPLD": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld.bin",
                    "script": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/cpld_fw_update",
                    "version": "10",
                    "boot-action": "power"
                },
                "FPGA": {
                    "firmware": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga.bin",
                    "script": "/usr/share/sonic/<platform_name>/<onie_platform>/fw_update/fpga_fw_update",
                    "version": "5",
                    "boot-action": "cold"
                }
            }
        }
    }
}
```

3. Platform component fw update configuration with platform specific script and boot options with --fw-image command line option
```json
{
    "component": {
        "BIOS": {
            "firmware": "bios.bin",
            "script": "bios_fw_update",
            "version": "0ACLH003_02.02.010",
            "boot-action": "any"
        },
        "CPLD": {
            "firmware": "cpld.bin",
            "script": "cpld_fw_update",
            "version": "10",
            "boot-action": "power"
        },
        "FPGA": {
            "firmware": "fpga.bin",
            "script": "fpga_fw_update",
            "version": "5",
            "boot-action": "cold"
        }
    }
}
```

**Note:**
1. FW update will be disabled if component definition is not provided (e.g., 'BIOS': { })
2. FW version will be read from image if `version` field is not provided

##### 2.2.2.4.2 Description

**The following command updates FW automatically based on the fw update configuration file:**
1. Non modular chassis platform
```bash
root@sonic:~# fwutil auto-update --yes --image=next --boot=immediate_cold
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil auto-update --yes --image=next --boot=any
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil auto-update --yes --image=next --boot=immediate_fast --component=ssd
Warning: <firmware_update_notification>
...
FW update in progress ...
...
root@sonic:~# fwutil auto-update --yes --fw-image=<fw_image_file> --boot=immediate_cold --commponent=ssd
Warning: <firmware_update_notification>
...
FW update in progress ...
...
```

**Supported options:**
1. -y|--yes - automatic yes to prompts. Assume "yes" as answer to all prompts and run non-interactively
2. -f|--force - install FW regardless the current version
3. -i|--image - update FW using current/next SONiC image
4. -b|--boot - following boot option after the upgrade
5. -a|--action - immediate (optional)
6. -z|--fw-image - firmware package downloaded during run time (this is an exclusive option from --image)

**Note:** the default option is _--image=current_, _--boot=any_,and  _--action=none_ 

##### 2.2.2.4.3 Component Firmware Update Script requirement

##### 2.2.2.4.3.1 Overview

The purpose of the <component>_fw_upgrade commands group is to provide an interface for:
1. The specific platform component related information query (version, description, etc.)
2. Available component FW update related information query (fw, version, status, etc.)
2. Update the component firmware based on the following boot-action

##### 2.2.2.4.3.1.1 Description

**The following command displays FW utility version:**
<component>
```bash
root@sonic:~# ssd_fw_upgrade show version
ssd_fw_upgrade version 1.0.0.0
```

**The following command displays platform component name and FW version:**
```bash
root@sonic:~# ssd_fw_upgrade show status
Component   Version             Description
---------  ------------------  ------------
SSD        5                    <vendor>/<model>
```

**The following command displays available FW updates:**
```bash
root@sonic:~# ssd_fw_update show updates ./ssd_fw.bin
Component   Firmware               Version (current/available)              Status              Required Boot Action
---------   ---------------------  ---------------------------------------  ------------------  -----------------------
SSD         <image_path>/ssd.bin   4 / 5                                    update is required  Immediate Cold/Fast reboot
```

**The following command performs the component FW update:**
```bash
root@sonic:~# ssd_fw_update --boot=immediate_cold ./ssd_fw.bin
Warning: <firmware_update_notification>
...
FW update in progress ...
...
```

**Supported options:**
1. -b|--boot - following boot option after the upgrade

**Note:** the default option is _--boot=any_

##### 2.2.2.4.4 Auto-update Use Cases

##### 2.2.2.4.4.1 FW-UPDATE-PLUGIN for reboot scripts - reboot/fast-reboot/warm-reboot
During any reboot, device can update with any available firmware image if the reboot type is applicable for the firmware  update.
```bash
root@sonic:~# fwutil auto-update --yes --image=next --boot=immediate_fast
```
Example : Reboot script changes to support automatic firmware update during a reboot

    ```
    ...
    from sonic_installer.bootloader import get_bootloader
    ...
    PLATFORM_FW_UPDATE="/usr/bin/fwutil"
    ...
    bootloader = get_bootloader()
    curimage = bootloader.get_current_image()
    nextimage = bootloader.get_next_image()
    If [[ nextimage == curimage ]]; then
        NEXT_BOOT_IMAGE=current
    else
        NEXT_BOOT_IMAGE=next
    fi
    ...
    if [[ -x ${PLATFORM_FW_UPDATE} ]]; then
        debug "updating platform fw for ${REBOOT_TYPE}"
        ${PLATFORM_FW_UPDATE} auto-update --yes --image={NEXT_BOOT_IMAGE} --boot=${REBOOT_TYPE}
    fi
 
    if [ -x ${DEVPATH}/${PLATFORM}/${PLAT_REBOOT} ]; then
    ...
    ```

##### 2.2.2.4.4.2 Run time firmware update - Ex) Kubernete 
During the run time, SONiC device can have a component firmware updated without interrupting the data plan if the component firmware update doesn't need any boot action.
```bash
root@sonic:~# fwutil auto-update --yes --fw-image=aboot-fw-update.tar.gz --boot=none
```
Or, device can be updated only a specific firmware update with a possible boot option that can be supported on a certain topology.
```bash
root@sonic:~# fwutil auto-update --yes --fw-image=ssd-fw-update.tar.gz --boot=fast
```

##### 2.2.2.4.4.3 Sonic_to_Sonic upgrade 
During the sonic image upgrade, all available platform component firmware can be upgraded.
```bash
root@sonic:~# fwutil auto-update --yes --image=next --boot=fast
```
Also  
```bash
root@sonic:~# fwutil auto-update --yes --image=next --boot=cold --component=cpld,ssd
```
Example : SONiC firmware upgrade script changes to support automatic firmware update

    ```
    PLATFORM_FW_UPDATE="/usr/bin/fwutil"

    CURRENT_FW=`sonic_installer list |grep "Current" |awk '{print $2}'`

    if grep -q aboot /host/machine.conf; then
        TARGET_FW=`unzip -p /tmp/$FILENAME boot0 |grep -m 1 "image_name" |sed -n "s/.*image-\(.*\)\".*/\1/p"`
    else
        TARGET_FW=`cat -v /tmp/$FILENAME |grep -m 1 "image_version" | sed -n "s/.*image_version=\"\(.*\)\".*/\1/p"`
    fi

    sonic_installer install -y /tmp/$FILENAME || FAILED=1
    sync;sync;sync || exit 14


    if [[ -x ${PLATFORM_FW_UPDATE} ]]; then
        FS_PATH="/host/image-${TARGET_FW#SONiC-OS-}/fs.squashfs"
        FS_MOUNTPOINT="/tmp/image-${TARGET_FW#SONiC-OS-}-fs"

        mkdir -p "${FS_MOUNTPOINT}"
        mount -t squashfs "${FS_PATH}" "${FS_MOUNTPOINT}" || exit 111

        ${PLATFORM_FW_UPDATE} auto-update --yes --image=next --boot=${REBOOT_TYPE}
    fi
    ```

# 3 Flows

## 3.1 Show components status

![Show components status flow](images/show_status_flow.svg "Figure 2: Show components status flow")

###### Figure 2: Show components status flow

## 3.2 Show available updates

![Show available updates flow](images/show_updates_flow.svg "Figure 3: Show available updates flow")

###### Figure 3: Show available updates flow

## 3.3 Install component FW

### 3.3.1 Non modular chassis platform

![FW install (non modular) flow](images/install_non_modular_flow.svg "Figure 4: FW install (non modular) flow")

###### Figure 4: FW install (non modular) flow

### 3.3.2 Modular chassis platform

![FW install (modular) flow](images/install_modular_flow.svg "Figure 5: FW install (modular) flow")

###### Figure 5: FW install (modular) flow

## 3.4 Auto FW Update

### 3.4.1 Auto FW update based on the configuration file

![Auto FW update flow with downloaded firmware package](images/update_w_fw_package.svg "Figure 6: Auto FW update flow with downloaded firmware package")

1. Find the available firmware based on boot type and immediate action type from platform specific fw update configuration file. 
   Exit if no configuration file exists.
2. Update the firmware using the script if it's specified in the configuration. Otherwise, fwutil will use the platform api to update the firmware.
   Exit if the update fails in any step.

# 4 Tests

## 4.1 Unit tests

1. Show utility version
2. Show components status
3. Show available updates
4. Install BIOS/CPLD/FPGA FW on non modular chassis
5. Install BIOS/CPLD/FPGA FW on modular chassis
6. Update BIOS/CPLD/FPGA FW on non modular chassis
7. Update BIOS/CPLD/FPGA FW on modular chassis
8. Auto Update BIOS/CPLD/FPGA FW with boot-action options 
