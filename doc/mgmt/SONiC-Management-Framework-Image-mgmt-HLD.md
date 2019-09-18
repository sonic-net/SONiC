# Image Management
Software upgrade and image installation support for SONiC
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev  |    Date    |      Author       | Change Description |
| :--: | :--------: | :---------------: | ------------------ |
| 0.1  | 09/13/2019 | Arunsundar Kannan | Initial version    |

# About this Manual
This document provides general information about the Image management and installation feature implementation in SONiC.
# Scope
Covers northbound interface for the Image Management feature, as well as unit test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**         | **Meaning**                    |
| ---------------- | ------------------------------ |
| Image Management | Image installation, validation |

# 1 Feature Overview

Provide management framework capabilities to handle:

- Image Installation
- List available images
- Removal of an available image
- Set default image for next boot


## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide management framework support to existing SONiC capabilities with respect to Image Management

### 1.1.2 Configuration and Management Requirements
- CLI configuration and show commands
- REST API support
- gNMI Support

### 1.1.3 Scalability Requirements
N/A
### 1.1.4 Warm Boot Requirements
N/A
## 1.2 Design Overview
### 1.2.1 Basic Approach
Implement Image Management support using translib in sonic-mgmt-framework.
### 1.2.2 Container
Management Container

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases

**image install**

This command is used to install a new image on the alternate image partition. This command takes a path to an installable SONiC image or URL and installs the image.

**show image-list**

This command displays information about currently installed images. It displays a list of installed images, currently running image and image set to be loaded in next reboot.

**image set-default**

This command is be used to change the image which can be loaded by default in all the subsequent reboots.

**image set-next-boot**

This command is used to change the image that can be loaded in the *next* reboot only. Note that it will fallback to current image in all other subsequent reboots after the next reboot.

**image remove**

This command is used to remove the unused SONiC image from the disk. Note that it's *not* allowed to remove currently running image.

Note: The above text is taken from the sonic command line reference Wiki (https://github.com/Azure/sonic-utilities/blob/master/doc/Command-Reference.md#sonic-installer)

## 2.2 Functional Description
After recieving the request from the client, via an RPC, the rest server will transfer the control to processAction method in the app module(inside traslib). This method will parse the target uri path and will branch to the corresponding function. These functions will call the python scripts in the host to perform image management related actions, like install, remove ..etc. The response from the output of the script is propagated back to processAction method and is converted to json. The json message is sent back to the client.

# 3 Design
## 3.1 Overview
TBD

## 3.2 DB Changes

N/A
### 3.2.1 CONFIG DB

N/A

### 3.2.2 APP DB

N/A

### 3.2.3 STATE DB

N/A

### 3.2.4 ASIC DB

N/A

### 3.2.5 COUNTER DB

N/A

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent

N/A

### 3.3.2 Other Process
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models

```
 +---x image-install
    |  +---w input
    |  |  +---w installer-arg-type?   string
    |  |  +---w filename?             string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x image-remove
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x image-default
    |  +---w input
    |  |  +---w imagename?   string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x image-nextboot
    |  +---w input
    |  |  +---w imagename?   string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
    +---x image-list
       +--ro output
          +--ro images-found?   string
```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands

**image install**

```
sonic# image install https://sonic-jenkins.westus.cloudapp.azure.com/job/xxxx/job/buildimage-xxxx-all/xxx/artifact/target/sonic-xxxx.bin

Done
```

**image set-default**

```
sonic# image set-default SONiC-OS-HEAD.XXXX
```

**image set-next-boot**

```
sonic# image set-next-boot SONiC-OS-HEAD.XXXX
```

**image remove**

```
sonic# image remove SONiC-OS-HEAD.YYYY

Image removed
```



#### 3.6.2.2 Show Commands

**show image-list**

```
sonic# show image-list
Current: SONiC-OS-HEAD.XXXX
Next: SONiC-OS-HEAD.XXXX
Available:
SONiC-OS-HEAD.XXXX
SONiC-OS-HEAD.YYYY
```


#### 3.6.2.3 Debug Commands

N/A

#### 3.6.2.4 IS-CLI Compliance

N/A

### 3.6.3 REST API Support

**TODO**
TBD (Working on a custom Sonic yang).

# 4 Flow Diagrams
N/A

# 5 Error Handling

TBD

# 6 Serviceability and Debug

TBD

# 7 Warm Boot Support

TBD

# 8 Scalability
N/A

# 9 Unit Test
List unit test cases added for this feature including warm boot.

# 10 Internal Design Information

