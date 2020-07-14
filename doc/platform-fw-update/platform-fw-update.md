# SONiC PLATFORM FW UPDATE

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
    - [2.2 Platform FW update](#22-platform-fw-update)
        - [2.2.1 Platform FW Update Manifest file](#221-platform-fw-update-manifest-file)
        - [2.2.2 Platform FW Update from running image](#222-platform-fw-update-running-image)
        - [2.2.3 Platform FW Update from next boot image](#223-platform-fw-update-next-boot-image)
        - [2.2.4 Platform FW Update from a fw-update file](#224-platform-fw-update-a-fw-update-file)
- [3 Flows](#3-flows)
    - [3.1 platform fw update with running image](#31-platform-fw-update-w-running-image)
    - [3.2 platform fw update with next boot image](#32-platform-fw-update-w-next-boot-image)
    - [3.3 platform fw update with --fw-image option](#33-platform-fw-update-w-next-boot-image)
- [4 Use cases](#3-use-cases)
    - [4.1 fast/warm/cold reboot](#41-fast-warm-cold-reboot)
    - [4.2 kubernate](#42-kubernate)
    - [4.3 sonic image upgrade](#43-sonic-image-upgrade)
    - [4.4 query option](#43-query-option)
- [5 Tests](#5-tests)
    - [5.1 Unit tests](#51-unit-tests)

## About this manual

This document provides the platform component FW update interface requirement in SONiC.

## Revision

| Rev | Date       | Author         | Description                       |
|:---:|:----------:|:--------------:|:----------------------------------|
| 0.1 | 13/07/2020 | Sujin Kang     | Initial version                   |

## Abbreviations

| Term   | Meaning                                             |
|:-------|:----------------------------------------------------|
| FW     | Firmware                                            |
| SONiC  | Software for Open Networking in the Cloud           |
| BIOS   | Basic Input/Output System                           |
| CPLD   | Complex Programmable Logic Device                   |
| SSD    | Solid State Drive                                   |
| N/A    | Not Applicable/Not Available                        |

## List of figures

[Figure 1: platform fw update High Level Design](#figure-1-platform-fw-update-high-level-design)  

## List of tables


# 1 Introduction

## 1.1 Feature overview

This platform fw update framework will provide a unified way to update the plaform fw on SONiC devices.

Platform firmware update will check the predefined image path (/usr/share/sonic/device/<platform>/fw-update/) and parse the Manifest.json file to learn about the file list and perform if any higher version image is available.

## 1.2 Requirements

### 1.2.1 Functionality

**This feature will support the following functionality:**
1. Automatic FW installation for particular platform component in the current image for a specific boot-type if specified
1. Automatic FW installation for all available platform components in the current image for a specific boot-type if specified
2. Automatic FW installation for particular platform component in the next available image for a specific boot-type if specified
1. Automatic FW installation for all available platform components in the next available image for a specific boot-type if specified
3. Querying current FW version of platform components on a SONiC device
4. Querying available platform component FW updates in the current image
4. Querying available platform component FW updates in the next available image
4. Querying available platform component FW updates in a FW image files

### 1.2.2 Command interface

platform-fw-update (--sonic-image=next/current|--fw-image=<firmware_image_name>) --reboot=cold/fast/warm/none(default:any) --component=cpld/ssd/abot

**This feature will support the following options:**
1. --reboot=fast/warm/cold/powercycle/none/{default: any}
2. --sonic-image=current/next => the source image for platform FW update
3. --fw-image=<specific_fw_image_path_file_name> => for nettools/kubernete
4. --components=ssd, cpld, bootloader, (uefi) bios
5. --query => what components fw images are available and what boot-type are supported for each component.
6. --yes(|-y)  =>

### 1.2.3 Error handling

**This feature will provide error handling for the next situations:**
1. Invalid input
2. Incompatible options/parameters

**Note:** FW binary validation (checksum, format, etc.) should be done by the platform specific component update plugin

### 1.2.4 Event logging

**This feature will provide event logging for the next situations:**

###### Table 1: Event logging

| Event                                     | Severity |
|:------------------------------------------|:---------|

**Note:** Some extra information also will be logged:

# 2 Design

## 2.1 Overview

![Platform FW Update High Level Design](images/platform-fw-update-hld.svg "Figure 1: Platform FW Update High Level Design")

###### Figure 1: Platform FW Update High Level Design

In order to improve scalability and performance a modern network switches provide different architecture solutions:
### 2.1.2 Steps
1. Option parsing
2. Image parsing
    Check fw version and scripts version on current image
    Check if scripts & images are available at the expected location (based on --image option) and check the versions
3. For each component
    Move to the fw update location
    Call each firmware update script with --reboot option

    The image & scripts location :
        /usr/share/sonic/device/<platform>/fw-update/<component>/
        Example: /usr/share/sonic/device/x86-64_dell-s6100-c2538-r0/fw-update/ssd/
        File list:
            Component update script : <component>_fw_update
            Image files :  <component>.gz


## 2.2 Platform FW Update

### 2.2.1 Platform firmware update Manifest file
This file includes the information of platform components which supports the firmware updates for a specific platform.
It's located at /usr/share/sonic/device/<platform>/fw-update/ and file name is Manifest.json.
```
Manifest.json
{
    "component":{
        "cpld":{
            "image":{
                "name":"cpld.gz
                "version":""
                "md5sum":""
            }
            "script":{
                "name":"cpld_fw_update"
                "version":"1.0"
            }
            "require_reboot":"cold"
        }
        "aboot":{
            "image":{
            "name":"aboot.gz"
            "version":""
            "md5sum":""
            }
            "script":{
            "name":"aboot_fw_update"
            "version":"1.0"
            "md5sum":""
            }
       }
   }
}
```

### 2.2.2 platform fw update from running image

Platform FW update can update the platform component firmware from running image using the option `--sonic-image=current`.
The image and update script is supposed to be located at /usr/share/sonic/device/<platform>/fw-update/<component>.



```
/usr/share/sonic/device/<platform>/fw-update/
                                           |
                                           --Manifest.json
                                           --/<component>/
                                                    |
                                                    --/<component>_fw_upgrade
                                                    --/<component_image_name>
```
Example:
```
/usr/share/sonic/device/x86-64_dell-s6100-c2538-r0/fw-update/
                                                           |
                                                           --Manifest.json
                                                           --/ssd/
                                                                    |
                                                                    --/ssd_fw_upgrade
                                                                    --/<ssd_image_name>
                                                           |
                                                           --/cpld/
                                                                    |
                                                                    --/cpld_fw_upgrade
                                                                    --/<cpld_image_name>
```

### 2.2.3 platform firmware update from next boot image

Platform FW update can update the platform component firmware from next available image using the option `--sonic-image=next`.
The image and update script is supposed to be located at <FS_MOUNT_POINT>/usr/share/sonic/device/<platform>/fw-update/<component>.
```
<FS_MOUNTPOINT>/usr/share/sonic/device/<platform>/fw-update/
                                           |
                                           --Manifest.json
                                           --/<component>/
                                                    |
                                                    --/<component>_fw_upgrade
                                                    --/<component_image_name>
```
Example:
```
/tmp/image-20191130.40-fs/usr/share/sonic/device/x86-64_dell-s6100-c2538-r0/fw-update/
                                                                   |
                                                                   --Manifest.json
                                                                   --/ssd/
                                                                            |
                                                                            --/ssd_fw_upgrade
                                                                            --/<ssd_image_name>
                                                                   |
                                                                   --/cpld/
                                                                            |
                                                                            --/cpld_fw_upgrade
                                                                            --/<cpld_image_name>

```

### 2.2.4 platform firmware update from a firmware image file

Platform FW update can update the platform component firmware from a firmware iamge using the option `--fw-image=<firmware_image_file>`.
The image and update script is supposed to be located at <fw_image_path>/fw-update/<component>.

Example: 
```
./fw-update/
           |
           --Manifest.json
           --/ssd/
                    |
                    --/ssd_fw_upgrade
                    --/<ssd_image_name>
           |
           --/cpld/
                    |
                    --/cpld_fw_upgrade
                    --/<cpld_image_name>

```

# 3 Flows

## 3.1 Platform FW update with current running image

![Platform FW update flow with current running image](images/platform_fw_update_with_current_image.svg "Figure 1: Platform FW update flow with current running image")

###### Figure 1: Platform FW update flow from current running image

## 3.2 Platform FW update with next boot image

![Platform FW update flow with next boot image](images/platform_fw_update_with_next_image.svg "Figure 2:  Platform FW update flow from next boot image")

###### Figure 2: Platform FW update flow from next boot image

## 3.3 Platform FW update with --fw-image option

![Platform FW update with a specific fw update file](images/platform_fw_update_with_fw_image.svg "Figure 3: Platform FW update flow using a specific fw update file")

###### Figure 3: Platform FW update flow using a specific fw update file

# 4 Use cases

## 4.1 Fast/warm/cold reboot 
    --image=next/current & --reboot=fast
    platform_fw_update --reboot=fast --sonic-image=next --component=ssd

    ```
    from sonic_installer.bootloader import get_bootloader

    PLATFORM_FW_UPDATE="/usr/bin/platform-fw-update"

    bootloader = get_bootloader()
    curimage = bootloader.get_current_image()
    nextimage = bootloader.get_next_image()
    If [[ nextimage == curimage ]]; then
        NEXT_BOOT_IMAGE=current
    else
        NEXT_BOOT_IMAGE=next
    fi

    if [[ -x ${PLATFORM_FW_UPDATE} ]]; then
        debug "updating platform fw for ${REBOOT_TYPE}"
        ${PLATFORM_FW_UPDATE} --reboot=${REBOOT_TYPE} --image={NEXT_BOOT_IMAGE} --component=[all]
    fi
 
    if [ -x ${DEVPATH}/${PLATFORM}/${PLAT_REBOOT} ]; then
    …
    ```
## 4.2 Kubernete 
    --fw-image=<image_pkg>.gz
    Image and script location to be used for fw update
    Command to perform the firmware upgrade
    platform_fw_update --reboot=none --fw-image=<fw-update-file-name> --component=(cpld(,ssd(,abot)))
    Example: `platform_fw_update --reboot=none --fw-image=fw-update.gz --component=aboot`

## 4.3 Sonic_to_Sonic upgrade 
    --sonic-image=next
    Image and script location to be used for fw update
    FS_MOUNTPOINT="/tmp/image-${TARGET_FW#SONiC-OS-}-fs"
    /$FS_MOUNTPOINT/usr/share/sonic/<platform>/fw-update/<component>/
    Command to perform the firmware upgrade
    platform_fw_update --reboot=<cold/fast/warm> --sonic-image=next --component=(cpld(,ssd(,aboot)))`
    Example - cold reboot case: `platform_fw_update --reboot=cold --sonic-image=next --component=cpld, ssd`
    Example - fast/warm reboot case: `platform_fw_update --reboot=fast --sonic-image=next --component=ssd`
## 4.4 Query option
    --query
    Command to query the fw update information
    Query all available fw image version and reboot required type from current running image:
        `platform_fw_update --sonic-image=current --query`
    Query all available fw image version and reboot required type from next boot image:
        `platform_fw_update --sonic-image=next --query`
    Query the available fw image version and reboot required type from manual fw-update image:
        `platform_fw_update --fw-image=fw-update.gz --query`
    Query the specific component fw image version and reboot required type from next boot image:
        `platform_fw_update --sonic-image=next --component=cpld,ssd --query`
    Query the installed fw image version information on the device:
        `platform_fw_update --query`

    Output format :
       <component>:
       FW version available :
       Required reboot :
       Example :
           cpld:
               FW version available : 5
               Required reboot : cold

# 5 Tests

## 5.1 Unit tests

1. Query available fw version and scripts in the current running image
2. Query available fw version and scripts in the next boot image
3. Query available fw version and scripts in a specific fw image
4. Query current fw version
5. Update Platform FW images from the current running image
6. Update Platform FW images from the next boot image
7. Update Platform FW images from a specific fw-update file
