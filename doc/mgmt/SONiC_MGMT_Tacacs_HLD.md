# Feature Name
TACACS+ Support in Management Framework
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
| 0.1 | 10/29/2019  |   Joyas Joseph     | Initial version                   |

# About this Manual
This document provides general information about TACACS+ support in SONiC Management Framework
# Scope
The scope of this document is within the bounds of the functionality provided by the new SONiC Management Framework. The underlying TACACS+
support in SONiC is provided by this high-level design document:
[TACACS+ Authentication](https://github.com/Azure/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md)

## Table 1

| Term |     Meaning            |
|:----:|:----------------------:|
|NBI   |	North Bound Interface |


# 1 Feature Overview
This feature allows the user to configure TACACS+ Authentication using NBI (CLI/REST/gNMI) provided by SONiC Management Framework. Configuration changes from the user are pushed to CONFIG DB. The implementation is contained within the Management Framework container.

## 1.1 Requirements


### 1.1.1 Functional Requirements

### 1.1.2 Configuration and Management Requirements
1. CLI configuration/show support
2. REST API support
3. gNMI support

### 1.1.3 Scalability Requirements

### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
1. Implement TACACS+ support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
The changes are in the sonic-mgmt-framework container. There will be additional files added.
1. XML file for the CLI
2. Python script to handle CLI request (actioner)
3. Jinja template to render CLI output (renderer)
4. YANG models 
	a. openconfig-aaa.yang and its dependents
	b. openconfig-tacacs.yang and its dependents

### 1.2.3 SAI Overview


# 2 Functionality
## 2.1 Target Deployment Use Cases

## 2.2 Functional Description


# 3 Design
## 3.1 Overview
## 3.2 DB Changes
### 3.2.1 CONFIG DB
This feature will allow the user to make/show TACACS+ configuration changes to CONFIG DB
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

```
```

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```
#### **AAA configuration**

##### Configure authentication methods and order
`aaa authentication login {local | tacacs+}`

The command allows the user to specify the authentication methods (local/tacacs+). Authentication will be attempted based on the order of the methods specified.

Examples:

```
sonic(config)# aaa authentication login local
sonic(config)# aaa authentication login local tacacs+
sonic(config)# aaa authentication login tacacs+
sonic(config)# aaa authentication login tacacs+ local

```


##### Set authentication method to default
```
sonic(config)# no aaa authentication login
```

##### Enable/disable failthrough
`[no] aaa authentication failthrough`

```
sonic(config)# aaa authentication failthrough
```

#### **TACACS server configuration**
##### Add TACACS+ server
`tacacs-server host <address> {port <1-65535> | timeout <0-60> | key <TEXT> }`

```
sonic(config)# tacas-server host 1.1.1.1 key Pass
sonic(config)# tacas-server host 1.1.1.2 port 1234 timeout 5 key Pass
```

#### 3.6.2.2 Show Commands
##### Show AAA configurations
```
sonic# show aaa
sonic#
```
##### Show TACACS+ configurations
```
sonic# show tacacs
sonic#
```

#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing TACACS+ configuration information from CONFIG DB.
POST - Add a new TACACS+  configuration into CONFIG DB.
PATCH - Update existing TACACS+  configuraiton information in CONFIG DB.
PUT - Add a list of TACACS+  configurations into CONFIG DB.
DELETE - Delete a existing TACACS+  configuration from CONFIG DB. This will cause some configurations to return to default value.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug


# 7 Warm Boot Support


# 8 Scalability


# 9 Unit Test
The unit-test for this feature will include:
#### Configuration via CLI
##### AAA
1. Configure one authentication method
2. Change the configured authentication method
3. Configure multiple authentication methods
4. Change the order of the authentication methods


##### TACACS
1. Configure one tacacs host
2. Configure another tacacs host with non-default parameters
3. Update parameters for a host already configured
4. Delete one tacacs host
5. Configure the same tacacs host again


#### Configuration via gNMI

Same test as CLI configuration test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information

