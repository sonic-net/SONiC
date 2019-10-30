# NAT
Management Interfaces for NAT Feature

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
| 0.1 | 10/30/2019  |   Ravi Vasantahm, Arthi Sivanantham      | Initial version                   |

# About this Manual

This document provides north bound interface details for NAT feature.

# Scope

This document covers the management interfaces supported for NAT feature and Unit test cases. It does not include the protocol design or protocol implementation details.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| NAT                      | Network Address Translation  |

# 1 Feature Overview

Provide CLI, GNMI and REST management framework capabilities for CONFIG and GET support for NAT feature.


## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide CLI, REST and gNMI support for configuring and displaying NAT attributes.


### 1.1.2 Configuration and Management Requirements

Supported Commands via:
- CLI style commands
- REST API support
- gNMI Support

### 1.1.3 Scalability Requirements
N/A

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach
Will be enhancing the management framework backend and transformer methods to add support for NAT configuration and display.


### 1.2.2 Container
All code changes will be done in management-framework container.

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
N/A
## 2.2 Functional Description
N/A


# 3 Design
## 3.1 Overview
N/A
## 3.2 DB Changes
No changes to existing DBs and no new DB being added.
### 3.2.1 CONFIG DB
### 3.2.2 APP DB

### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
N/A
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



### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands

#### Add static NAT entry

`sonic(config) # nat add static basic {global-ip} {local-ip} -nat_type {snat/dnat} -twice_nat_id {value}`

#### Remove static NAT entry

`sonic(config) # nat remove static basic {global-ip} {local-ip}`

#### Add static NAPT entry

`sonic(config) # nat add static {tcp | udp} {global-ip} {global-port} {local-ip} {local-port} -nat_type {snat/dnat} -twice_nat_id {value}`

#### Remove static NAPT entry

`sonic(config) # nat remove static {tcp | udp} {global-ip} {global-port} {local-ip} {local-port}`

#### Remove all static NAT/NAPT configuration

`sonic(config) # nat remove static all`

#### Create NAT pool

`sonic(config) # nat add pool {pool-name} {global-ip-range} {global-port-range}`

#### Remove NAT pool

`sonic(config) # nat remove pool {pool-name}`

#### Remove all NAT pool configuration

`sonic(config) # nat remove pools`

#### Create binding between an ACL and a NAT pool

`sonic(config) # nat add binding {binding-name} {pool-name} {acl-name} -nat_type {snat/dnat} -twice_nat_id {value}`

#### Remove binding between an ACL and a NAT pool

`sonic(config) # nat remove binding {binding-name}`

#### Remove all NAT binding configuration

`sonic(config) # nat remove bindings`

#### Configure NAT zone value on an interface

`sonic(config) # nat add interface {interface-name} {-nat_zone {zone-value}}`

#### Remove NAT configuration on interface

`sonic(config) # nat remove interface {interface-name}`

#### Remove NAT configuration on all L3 interfaces

`sonic(config) # nat remove interfaces`

#### Configure NAT entry aging timeout in seconds

`sonic(config) # nat set timeout {secs}`

#### Reset NAT entry aging timeout to default value

`sonic(config) # nat reset timeout`

#### Enable or disable NAT feature

`sonic(config) # nat feature {enable/disable}`

#### Configure UDP NAT entry aging timeout in seconds

`sonic(config) # nat set udp-timeout {secs}`

#### Reset UDP NAT entry aging timeout to default value

`sonic(config) # nat reset udp-timeout`

####  Configure TCP NAT entry aging timeout in seconds

`sonic(config) # nat set tcp-timeout {secs}`

#### Reset TCP NAT entry aging timeout to default value

`sonic(config) # nat reset tcp-timeout`

#### 3.6.2.2 Show Commands

#### Show NAT translations table

`sonic # show nat translations`

#### Display NAT translation statistics

`sonic # show nat statistics`

#### Display Static NAT/NAPT configuration

`sonic # show nat config static`

#### Display NAT pools configuration

`sonic # show nat config pool`

#### Display NAT bindings configuration

`sonic # show nat config bindings`

#### Display global NAT configuration

`sonic # show nat config globalvalues	`

#### Display L3 interface zone values

`sonic # show nat config zones`

#### Display NAT entries count

`sonic # show nat translations count`

#### Display all NAT configuration

`sonic # show nat config`


#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
| | | | |
| | | | |
| | | | |
| | | | |

**Deviations from IS-CLI:**

### 3.6.3 REST API Support

# 4 Flow Diagrams
N/A

# 5 Error Handling


# 6 Serviceability and Debug


# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
The following lists the unit test cases added for the north bound interfaces for NAT:


# 10 Internal Design Information
N/A
