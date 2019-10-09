# Watermark Telemetry
watermark telemetry interval support in management framework.
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)




# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/30/2019  |   Adedamola Adetayo      | Initial version                   |

# About this Manual
This document provides general information about watermark telemetry show and configure interval in SONiC cli using the management framework.
# Scope
This document describes the high level design of watermark telemetry interval as well as unit test cases.


# 1 Feature Overview

This feature will enable users to configure watermark telemetry interval in SONiC management framework with CLI, REST or gNMI. It is used to configure the interval in seconds between the device's sample of a telemetry data source.


## 1.1 Requirements
 https://github.com/Azure/sonic-utilities/blob/master/doc/Command-Reference.md#watermark-configuration-and-show


### 1.1.1 Functional Requirements


### 1.1.2 Configuration and Management Requirements
1. CLI configuration/show support
2. REST API support
3. GNMI support

### 1.1.3 Scalability Requirements
N/A
### 1.1.4 Warm Boot Requirements
N/A
## 1.2 Design Overview
### 1.2.1 Basic Approach
Design watermark telemetry interval support using transformer.
### 1.2.2 Container
Changes will be made in the sonic-mgmt-framework container

### 1.2.3 SAI Overview
N/A
# 2 Functionality
## 2.1 Target Deployment Use Cases

## 2.2 Functional Description


# 3 Design
## 3.1 Overview
## 3.2 DB Changes
### 3.2.1 CONFIG DB
This feature will enable users to create/show configuration changes to CONGIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process


## 3.4 SyncD

## 3.5 SAI


## 3.6 User Interface
### 3.6.1 Data Models
**sonic-watermark-telemetry.yang**


### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
````
Set watermark telemetry interval:-
sonic(config)# watermark telemetry interval <value>
````


#### 3.6.2.2 Show Commands
````
sonic# show watermark telemetry interval
  Telemetry interval: 100 second(s)
````


#### 3.6.2.3 Debug Commands
N/A
#### 3.6.2.4 IS-CLI Compliance
N/A


### 3.6.3 REST API Support

**GET**

-`/sonic-watermark-telemetry:WATERMARK_TABLE/interval`

**PATCH**

-`/sonic-watermark-telemetry:WATERMARK_TABLE/interval`


# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability


# 9 Unit Test
- Configure and validate watermark telemetry interval via CLI
- Verify show watermark telemetry interval via CLI
- Configure and validate watermark telemetry interval via REST
- Verify show watermark telemetry interval via REST
- Configure and validate watermark telemetry interval via gNMI
- Verify show watermark telemetry interval via gNMI

