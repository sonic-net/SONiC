
# License Management Framework


# High Level Design Document
# Table of Contents

<!-- TOC depthFrom:1 depthTo:6 withLinks:1 updateOnSave:1 orderedList:0 -->

- [License Management Framework](#feature-name)
- [High Level Design Document](#high-level-design-document)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Definition/Abbreviation](#definitionabbreviation)
		- [Table 1: Abbreviations](#table-1-abbreviations)
- [1 Feature Overview](#1-feature-overview)
	- [1.1 Target Deployment Use Cases](#11-target-deployment-use-cases)
	- [1.2 Requirements](#12-requirements)
	- [1.3 Design Overview](#13-design-overview)
		- [1.3.1 Basic Approach](#131-basic-approach)
		- [1.3.2 Container](#132-container)
		- [1.3.3 SAI Overview](#133-sai-overview)
- [2 Functionality](#2-functionality)
- [3 Design](#3-design)
	- [3.1 Overview](#31-overview)
		- [3.1.1 Service and Docker Management](#311-service-and-docker-management)
		- [3.1.2 Packet Handling](#312-packet-handling)
	- [3.2 DB Changes](#32-db-changes)
		- [3.2.1 CONFIG DB](#321-config-db)
		- [3.2.2 APP DB](#322-app-db)
		- [3.2.3 STATE DB](#323-state-db)
		- [3.2.4 ASIC DB](#324-asic-db)
		- [3.2.5 COUNTER DB](#325-counter-db)
		- [3.2.6 ERROR DB](#326-error-db)
	- [3.3 Switch State Service Design](#33-switch-state-service-design)
		- [3.3.1 Orchestration Agent](#331-orchestration-agent)
		- [3.3.2 Other Processes](#332-other-processes)
	- [3.4 SyncD](#34-syncd)
	- [3.5 SAI](#35-sai)
	- [3.6 User Interface](#36-user-interface)
		- [3.6.1 Data Models](#361-data-models)
		- [3.6.2 CLI](#362-cli)
			- [3.6.2.1 Show Commands](#3621-show-commands)
			- [3.6.2.2 Exec Commands](#3622-exec-commands)
		- [3.6.3 REST API Support](#363-rest-api-support)
		- [3.6.4 gNMI Support](#364-gnmi-support)
	- [3.7 Warm Boot Support](#37-warm-boot-support)
	- [3.8 Upgrade and Downgrade Considerations](#38-upgrade-and-downgrade-considerations)
	- [3.9 Resource Needs](#39-resource-needs)
- [4 Flow Diagrams](#4-flow-diagrams)
- [5 Error Handling](#5-error-handling)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Scalability](#7-scalability)
- [8 Platform](#8-platform)
- [9 Security and Threat Model](#9-security-and-threat-model)
- [10 Limitations](#10-limitations)
- [11 Unit Test](#11-unit-test)
- [12 Internal Design Information](#12-internal-design-information)
	- [12.1 IS-CLI Compliance](#121-is-cli-compliance)
	- [12.2 SONiC Packaging](#122-sonic-packaging)
	- [12.3 Broadcom Silicon Considerations](#123-broadcom-silicon-considerations)
	- [12.4 Design Alternatives](#124-design-alternatives)
	- [12.5 Release Matrix](#125-release-matrix)

<!-- /TOC -->

# List of Tables
[Table 1: Abbreviations](#table-1-Abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/21/2022  |   Joyas Joseph          | Initial version                   |
| 0.2 | 07/27/2022  |   Reemus Vincent        | Draft version                     |

# About this Manual
This document provides comprehensive functional and design information about the License Management Framework feature implementation in SONiC.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| OpenHW                   | Running Enterprise SONiC by Dell Technologies on platforms that are not Dell|
| PKI                      | Public Key Infrastructure |
| DDL                      | Dell Digital Locker |

# 1 Feature Overview

This document is to detail the process of how License Management will function on Enterprise SONiC.

Today, Enterprise SONiC does not implement licensing. It is based on an honor system, where the system runs with no expiration date and it does not check that it is running on a validated system. When we move to OpenHW, this will need to be verified and checked that Enterprise SONiC is running on the device that it is intended for.

This document will detail how the Licensing Framework will be implemented on Enterprise SONiC and OpenHW and detail the operations of how license management will work on Dell and Non-Dell platforms.

## 1.1 Target Deployment Use Cases

The License Management will validate the customer's license having Enterprise SONiC and OpenHW switches.
  1. Users download their entitled license from the Dell License Portal - DDL (Dell Digital Locker)
  2. Install their entitled licenses into the switches using any local or remote http/ssh/ftp serveres

## 1.2 Requirements

1. Enterprise SONiC will support License Management to verify that the customers are entitled to Enterprise SONiC for the duration term.
2. Enterprise SONiC will leverage a subscription based licensing model.
3. Typical duration of the licenses are 1 year, 3 years and 5 years, however the implementation must be flexible to support other terms.
4. The framework should be flexible enough to have licensing enabled or disabled based on the vendor. 
	1. Licensing should be enabled for the Dell branded Enterprise SONiC images.
5. The license will be generated at the time of sale.
6. The license is tied to the hardware based on the Service Tag or Serial Number and the type of the image - Enterprise Standard, Cloud Standard, Enterprise Premium etc.
	1. License for one image type when installed on another image type will be treated as an invalid license. 
7. User should be able to install a license on the switch.
8. ~~User should be able to install a license when upgrading from an older version.~~
9. ~~Upgrade from an older version should fail when license file is not present.~~
10. Installing a license key will require users to accept the Dell EULA.  The acceptance of the EULA must be registered in a non-repudiation manner, and must survive across reboots and upgrades, not ONIE installations/uninstallations
11. When the license is about to expire (90 days)
	* 	An alert will appear when user logs in to the switch
	* 	An alert will be logged indicating the license is about to expire
12. After the license expires
	* 	An alert will appear when user logs in to the switch
	* 	An alert will be logged every 24 hours indicating the license has expired
13. The license should be stores such a way to avoid unintentional deletion.
14. The license should be preserved across reboots and SW upgrades.
15. Devise a method to avoid customers who backdate the switch from making an expired license valid again.
16. User should not be able to disable the license feature.
17. User should not be able to modify the license to make it valid for another switch or image type.

## 1.3 Design Overview

SONiC License Management will add the functionality to verify, install and validate the Dell-issued software licenses for the Enterprise SONiC.

  * License Verification - Will use Public Key Infrastruture(PKI) Digital Signature to verify whether the installed license is issued by Dell (Vendor)
  * Install License - Store the license persistently on the switch
  * License Validation - Periodially check the installed license for expiry
  * Users will also be alerted when the installed license nears expiry.
  * An alter message will be generated periodically when license enpires

### 1.3.1 Basic Approach

With this functionality users will be able install Dell Enterprise SONiC license for the switch from their home directory or any of the remote file servers using FTP, SSH & HTTP.

![image info](images/router-with-servers.jpg "Figure 1: Enterprise SONiC License Management Topology")

### 1.3.2 Container

No new container is added. The details of the changes will be discussed in the Design section below.

# 2 Functionality

With the Software License Management, users will be able to:
  1. Installl Dell Enterprise SONiC License in the switch
  2. View the details of installed Dell Enterprise SONiC License in the switch

# 3 Design

## 3.1 Overview

The Software License Management Framework will provide users to install the eSONiC License in the switch.

![image info](images/License-Management-Framework-Detailed-Design.jpg "Figure 2: Enterprise SONiC License Management Framwwork")

__Figure 1: Enterprise SONiC License Management__


### 3.1.1 Service and Docker Management
  * Separate license manager is added as task(thread) inside the existing ORCHAgent

### 3.1.2 Packet Handling
NA

## 3.2 DB Changes

At high-level the following fields will be added to the DB to capture the installed license:

  * Software License (ENTERPRISE-SONiC-PREMIUM, ENTERPRISE-SONiC-STANDARD, ENTERPRISE-SONiC-CLOUD-STANDARD)
  * License Status (Not Installed/Installed/Expired)
  * License Expiry Date Counter
  * License Type (SUBSCRIPTION)
  * License Start Date
  * License Duration (In days)
  * License File Location

## 3.3 Switch State Service Design
Refer the Figure 2: Enterprise SONiC License Management Framwwork

### 3.3.1 Orchestration Agent

## 3.4 User Interface

### 3.4.1 Data Models

### 3.4.2 CLI

#### 3.4.2.1 Show Commands

**Syntax:**
```

	sonic# show license status
	System Information
	---------------------------------------------------------
	Vendor Name          :   Dell EMC
	Product Name         :   Generic
	Platform Name        :   x86_64-dellemc_s5248f_c3538-r0
	Service Tag          :   J3XD9Z2
	License Details
	----------------
	Software License    :    ENTERPRISE-SONiC-PREMIUM
	Version             :    4.1
	License Status      :    Installed - 120 day(s) left
	License Type        :    SUBSCRIPTION
	License Start Date  :    2022-08-02T16:08:35Z
	License Duration    :    120 days
	License location    :    /etc/license/2W6RY03.lic
	---------------------------------------------------------
	sonic#
```

The "show license detail" command will display the sytem and the currently installed license details.

#### 3.4.2.2 Exec Commands

**Syntax:**
```
    sonic# license install <license-file>
	<<EULA>>
	Accept [Y/n]:
```

| **Alias Name** | **Format**                                                             | **Description**                                                              |
|----------------|------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| home:          | home://<<filename>>   | License file path in the user's HOME directory |
| ftp:           | ftp://[username [:password]@]{hostname\|host-ip}/directory/[filename]   | License file path in FTP server. |
| http:          | http://[username [:password]@]{hostname\|host-ip}/directory/[filename]  | License file path in HTTP server. |
| scp:           | scp://[username [:password]@]{hostname\|host-ip}/directory/[filename]    | License file path in Secure Shell(SSH) server. |


### 3.4.3 REST API Support

SONiC REST URI

/restconf/operations/sonic-licmgmt:install-license
/restconf/operations/sonic-licmgmt:get-license-details

## 3.5 Upgrade and Downgrade Considerations

The installed license must be stored in the persistent/config partition which is not erased during upgrade or downgrade of the switch


# 4 Flow Diagrams

![image info](images/License-Management-Eventflow.jpg "Figure 3: Enterprise SONiC License Management Call Flow")

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Scalability

# 8 Platform

# 9 Security and Threat Model
  * License Management Framework will use PKI. PKI performs encryption directly through the keys that it generates. It works by using two different cryptographic keys: a public key and a private key. Whether these keys are public or private, they are used to encrypt and decrypt secure data.


## 9.1 Certificates, secrets, keys, and passwords
  * SONiC License Management will use self-signed certificate (a digital certificate not signed by any publicly trusted Certificate Authority (CA)).


## 12.1 IS-CLI Compliance

## 12.2 SONiC Packaging - BRCM Requirement

This section will describe the details of the liblicensing deb packing procedure for the Enterprise SONiC:

  * "sonic-licensing" directory will be added to the eSONiC sonic-buildimage repo
    * It will contain a stub implementation of the license manager with the stub license validation APIs
  * Dell will be maintaining a separate "sonic-licensing" repo which will be used to build the "liblicensing" deb package
    * It will contain the actual implementation of the license manager with the PKI license validation APIs
    * It will be compiled separately and the deb package will be stored in the Dell Artifactory URL
  * When compiling eSONiC the stub implementation will be compiled and packaged with the image
  * During Broadcom Rebranding the stub liblicensing deb package should be replaced with the Dell implementation of the liblicensing deb package that is retrieved from the Dell Artifactory URL

## 12.4 Design Alternatives

## 12.5 Release Matrix
