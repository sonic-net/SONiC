
# SONiC Image Installation Verification

# High Level Design Document

#### Rev 0.1

# Table of Contents

- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definition-abbreviation)
    + [Table 1: Abbreviations](#table-1--abbreviations)
- [1 Feature Overview](#1-feature-overview)
- [2 Functional Requirements](#2-functional-requirements)
- [3 Configuration and Management Requirements](#3-configuration-and-management-requirements)
- [4 Design and Flow Diagrams](#4-design-and-flow-diagrams)
  * [4.1 Flow Diagrams](#41-flow-diagrams)
  * [4.2 Design](#42-design)
    + [4.2.1 Generate platform list](#421-generate-platform-list)
    + [4.2.2 Verification](#422-verification)
    + [4.2.3 Skip platform check](#423-skip-platform-check)
- [5 Error Handling](#5-error-handling)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Warm Boot Support](#7-warm-boot-support)
- [8 Scalability](#8-scalability)
- [9 Tests](#9-tests)
  * [9.1 Unit Tests](#91-unit-tests)
  * [9.2 End to End test](#92-end-to-end-test)


# Revision

| Rev | Date        | Author             | Change Description  |
|:---:|:-----------:|:------------------:|---------------------|
| 0.1  | 01/25/2021 | Jingwen Xie        | Initial version     |

# About this Manual
This document provides a detailed description on the strategy to implement the SONiC extended image installation verification feature.

# Scope
This document describes the high level design of a SONiC extended image installation verification feature. This document provides minor implementation details about the proposed solutions.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term** | **Meaning**                                 |
| -------- | ------------------------------------------- |
| ASIC     | Application-Specific Integrated Circuit     |

# 1 Feature Overview

SONiC image installation requires users to install the correct image on the switch.  The image is built per ASIC type and it needs to be loaded on the corresponding switch of that ASIC type.

For example, Dell6100’s switch ASIC vendor is Broadcom. It should be installed with a Broadcom based image. However, choosing  which image to install  on specific switch is simply determined by the users.  SONiC itself doesn’t have an extended verification step to verify if the image's built ASIC type is aligned with the switch ASIC type.

Here is a list of ASIC vendor info from [Supported Devices and Platforms](https://github.com/Azure/SONiC/wiki/Supported-Devices-and-Platforms).

The verification should looks like this:
```
admin@vlab-01:~$ sudo sonic-installer install sonic-broadcom.bin -y
Image file 'sonic-broadcom.bin' is of a different platform ASIC type than running platform's.
If you are sure you want to install this image, use --skip-platform-check.
Aborting...
Aborted!
```

# 2 Functional Requirements

- sonic-installer should be able to verify if an image is valid to be installed on runnning platform.
- sonic-installer should provide a way to skip such platform check and an option of force image installation
- sonic-intaller should not affect the past images installation. 

# 3 Configuration and Management Requirements

- The option of platform check skip hould be added to sonic-installer help menu.
  - Use `--skip-platform-check` option instead of `--force` as the later one has been used for image force installation which skips image secure check. 
```
admin@vlab-01:~$ sudo sonic-installer install --help
Usage: sonic-installer install [OPTIONS] URL

  Install image from local binary or URL

Options:
  -y, --yes
  -f, --force, --skip-secure-check
                                  Force installation of an image of a non-
                                  secure type than secure running image
  --skip-platform-check           Force installation of an image of a type       <======
                                  which is not of the same platform
  --skip_migration                Do not migrate current configuration to the
                                  newly installed image
  --skip-package-migration        Do not migrate current packages to the newly
                                  installed image
  --skip-setup-swap               Skip setup temporary SWAP memory used for
                                  installation
  --swap-mem-size INTEGER         SWAP memory space size  [default: (1024
                                  MiB)] NOTE: this argument is mutually
                                  exclusive with arguments: skip_setup_swap
  --total-mem-threshold INTEGER   If system total memory is lower than
                                  threshold, setup SWAP memory  [default:
                                  (2048 MiB)] NOTE: this argument is mutually
                                  exclusive with arguments: skip_setup_swap
  --available-mem-threshold INTEGER
                                  If system available memory is lower than
                                  threhold, setup SWAP memory  [default: (1200
                                  MiB)] NOTE: this argument is mutually
                                  exclusive with arguments: skip_setup_swap
  --help                          Show this message and exit.

```

# 4 Design and Flow Diagrams

## 4.1 Flow Diagrams
The following figure shows how to intall an image through SONiC CLI.
```
+-----------------+  
|   SONiC ClI     |            
|                 <-----------+
|  Image Install  |           |
+-----------------+           |
         |                    |
         V                    |
+-----------------+           |
|      Image      |---->NO----+
|                 |             +------------+
|   Verification  |---->YES-----> Installing |
+-----------------+             +------------+
```

## 4.2 Design

### 4.2.1 Generate platform list
We need to generate a file `platforms_asic`. This file contains the list of supported platforms and is generated during the process of image build. The file is kept in built image.

### 4.2.2 Verification
To decide whether an image is of a correct type of ASIC during installation, the installer will verify if the current platform is inside to be installed image's built-in file `platforms_asic`. If not, verification would fail because it means the current platform is of a different ASIC type from the built image. If yes, it will pass the verification process and do other image checks.

### 4.2.3 Skip platform check
We also provide a way to bypass the image verification. During sonic-install install process, user can add an 'force install' option to bypass platform check if sonic-installer detects that the image is of a different type of ASIC from the current platform. 

As `--force` option has been used for image secure check, we use  `--skip-platform-check` option to handle our verification.

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Tests

## 9.1 Unit Tests
| Test Case | Description |
| --------- | ----------- |
| 1         | Install broadcom image on vs platform.|
| 2         | Install broadcom-dnx image on broadcom platform.|
| 3         | Install mellanox image on broadcom platform. |
| 4         | Install broadcom image on mellanox platform. |
| 5         | Install ONIE image on Arista system. |
| 6         | Install Arista image on ONIE system. |

## 9.2 End to End test
To do E2E tests, I want to remind that the verification cannot be verified among the build artifacts that are built together, which means they share the same build version.

For example, if a broadcom switch has been installed with a latest image `sonic-broadcom.bin`. If we want to verify if it can block the installation of the latest mellanox based image, say `sonic-mellanox.bin`, sonic-installer will find that these two bin image share the same build version. Thus the system will ignore the installation, so the future verification will not be tested.

The E2E test must make sure the installed image are from different build.
