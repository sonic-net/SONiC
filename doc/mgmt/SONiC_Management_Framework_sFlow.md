# Feature Name
sFlow Support in Management Framework
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
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/09/2019  |   Garrick He       | Initial version                   |

# About this Manual
This document provides general information about sFlow support in SONiC Management Framework
# Scope
This document describes the high level design of sFlow support in SONiC Management Framework. The underlying sFlow
support in SONiC is provided by this high-level design document:
https://github.com/padmanarayana/SONiC/blob/5c158360c3e36227de7899fb672fc1b016a5465c/doc/sflow/sflow_hld.md


# 1 Feature Overview
This feature will allow the user to configure sFlow using SONiC Management Framework with REST or GNMI. Translib will make changes
to CONFIG DB to make configuration changes to sFlow. The underlying sflow db schema is already provided by sflow support from SONIC

## 1.1 Requirements


### 1.1.1 Functional Requirements

### 1.1.2 Configuration and Management Requirements
1. CLI configuration/show support
2. REST API support
3. GNMI support

### 1.1.3 Scalability Requirements

### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
1. Implement sFlow support using transformer in sonic-mgmt-framework

### 1.2.2 Container
There will be changes in the sonic-mgmt-framework container

### 1.2.3 SAI Overview


# 2 Functionality
## 2.1 Target Deployment Use Cases

## 2.2 Functional Description


# 3 Design
## 3.1 Overview
## 3.2 DB Changes
### 3.2.1 CONFIG DB
This feature will allow the user to make/show sFlow configuration changes to CONFIG_DB
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
TBD - Need to amend the SONiC YANG model to include sFlow attributes since there are no YANGs for sFlow.

### 3.6.2 CLI
sFlow configuration and show commands will be the same as the one available on the host provided by SONiC
#### 3.6.2.1 Configuration Commands
| Command description | CLI syntax |
| :------ | :----- |
| global configurations | [no] sflow [enable] [polling-interval <int>] [agent-id <intf-name>] |
| collector configuration | [no] sflow collector [add <collector name> <collector ipv4/v6 address> [port #]]
| interface configuration | [no] sflow [enable] [sample-rate <int>]

| Command description | CLI command Example |
| :------ | :----- |
| Enable sFlow | sonic(config)# sflow enable |
| Disable sFlow | sonic(config)# no sflow |
| Configure sFlow polling interval | sonic(config)# sflow polling-interval 3 |
| Configure sFlow agent ID | sonic(config)# sflow agent-id Ethernet 0 |
| Reset back to default sFlow agent ID | sonic(config)# no sflow agent-id |
| Configure sFlow collector | sonic(config)# sflow collector add Collector1 1.1.1.2 |
| Delete sFlow Collector | sonic(config)# no sflow collector Collector1 |
| Enable sFlow on interface | sonic(config)# interface Ethernet0<br>sonic(config-intf)# sflow enable |
| Disable sFlow on interface | sonic(config)# interface disable Ethernet0<br> sonic(config-intf)# no sflow |
| Configure sampling-rate on interface | sonic(config)# interface Ethernet0<br>sonic(config-intf)# sflow sampling-rate 300 |
| Reset to default sampling-rate on interface | sonic(config)# interface Ethernet0<br>sonic(config-intf)# no sflow sampling-rate |


#### 3.6.2.2 Show Commands
| Command description | CLI command |
| :------ | :----- |
| show global sFlow configuration | show sflow |
| show sflow interface configuration | show sflow interface |


#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing sflow configuration from CONFIG DB
POST - Change existing sFlow configuration in CONFIG DB
```
# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug


# 7 Warm Boot Support


# 8 Scalability


# 9 Unit Test
The unit-test for this feature will include:
1. configuration via CLI

| Test Name | Test Description |
| :------ | :----- |
| Enable sflow | Verfiy sFlow is enabled in configDB |
| Disable sflow | Verify sFlow is disabled in configDB |
| Configure polling-interval | Verify sFlow polling-interval is set in configDB |
| Disable polling-interval | Verify sflow polling-interval is removed from configDB (back to default)
| Add a collector | Verify a collector has been added into configDB |
| Add a collector with port # | Verify a collector has been added into configDB with user supplied port #|
| Delete a collector | Verify a collector has been deleted from configDB
| Enable sflow on interface | Verfiy sFlow for an interface is enabled in configDB |
| Disable sflow on interface | Verfiy sFlow for an interface is disabled in configDB |
| Configure sampling-rate on interface | Verify sampling-rate for an interface is set in configDB|
| Disable sampling-rate on interface | Verify sampling-rate has returned to default

2. show sflow configuration via CLI

3. configuration (POST) via GNMI

Same test as CLI configuration Test but using gNMI POST request

4. get configuration (GET) via GNMI

Same as CLI show test but with gNMI GET request, will verify the JSON response is correct.

5. configuration (POST) via REST

Same test as CLI configuration Test but using REST POST request

6. show configuration (GET) via REST

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information

