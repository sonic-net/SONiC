
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
			- [3.6.2.1 Configuration Commands](#3621-configuration-commands)
			- [3.6.2.2 Show Commands](#3622-show-commands)
			- [3.6.2.3 Exec Commands](#3623-exec-commands)
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

# About this Manual
This document provides comprehensive functional and design information about the License Management Framework feature implementation in SONiC.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| OpenHW                   | Running Enterprise SONiC by Dell Technologies on platforms that are not Dell|

# 1 Feature Overview

This document is to detail the process of how License Management will function on Enterprise SONiC.

Today, Enterprise SONiC does not implement licensing. It is based on an honor system, where the system runs with no expiration date and it does not check that it is running on a validated system. When we move to OpenHW, this will need to be verified and checked that Enterprise SONiC is running on the device that it is intended for.

This document will detail how the Licensing Framework will be implemented on Enterprise SONiC and OpenHW and detail the operations of how license management will work on Dell and Non-Dell platforms.

## 1.1 Target Deployment Use Cases



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
8. User should be able to install a license when upgrading from an older version.
9. Upgrade from an older version should fail when license file is not present.
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
### 1.3.1 Basic Approach

### 1.3.2 Container

### 1.3.3 SAI Overview

# 2 Functionality

# 3 Design
## 3.1 Overview

### 3.1.1 Service and Docker Management


### 3.1.2 Packet Handling

## 3.2 DB Changes

### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB
### 3.2.6 ERROR DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent

### 3.3.2 Other Processes

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 Show Commands
#### 3.6.2.3 Exec Commands

### 3.6.3 REST API Support

### 3.6.4 gNMI Support

## 3.7 Warm Boot Support

## 3.8 Upgrade and Downgrade Considerations

## 3.9 Resource Needs

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Scalability

# 8 Platform

# 9 Security and Threat Model

## 9.1 Certificates, secrets, keys, and passwords


# 10 Limitations

# 11 Unit Test

# 12 Internal Design Information

## 12.1 IS-CLI Compliance

## 12.2 SONiC Packaging

## 12.3 Broadcom Silicon Considerations

## 12.4 Design Alternatives

## 12.5 Release Matrix
