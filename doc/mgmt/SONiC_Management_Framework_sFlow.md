# Feature Name
sFlow Support in Management Framework
# High Level Design Document
#### Rev 0.3

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
| 0.2 | 10/04/2019  |   Garrick He       | Address review comments           |
| 0.3 | 10/11/2019  |   Garrick He       | Address review comments           |
| 0.4 | 10/15/2019  |   Garrick He       | Add information on default value  |
|     |             |                    | and SONiC sFlow YANG              |

# About this Manual
This document provides general information about sFlow support in SONiC Management Framework
# Scope
This document describes the high level design of sFlow support in SONiC Management Framework. The underlying sFlow
support in SONiC is provided by this high-level design document:
https://github.com/Azure/SONiC/blob/master/doc/sflow/sflow_hld.md


# 1 Feature Overview
This feature will allow the user to configure sFlow using SONiC Management Framework with REST or gNMI. Translib will make changes
to CONFIG DB to make configuration changes to sFlow. The underlying sFlow DB schema is already provided by sFlow support from SONiC

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
1. Implement sFlow support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
There will be changes in the sonic-mgmt-framework container. The backend will be modifications to translib done through Transformer. There will be additional files added to:
1. XML file for the CLI
2. Python script to handle CLI request (actioner)
3. Jinja template to render CLI output (renderer)
4. sFlow YANG model

### 1.2.3 SAI Overview


# 2 Functionality
## 2.1 Target Deployment Use Cases

## 2.2 Functional Description


# 3 Design
## 3.1 Overview
## 3.2 DB Changes
### 3.2.1 CONFIG DB
This feature will allow the user to make/show sFlow configuration changes to CONFIG DB
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
There are no OpenConfig YANG models available for sFlow so additions were made to SONiC YANG.
Supported SONiC YANG URIs available from Swagger WebUI:
```
/sonic-sflow:sonic-sflow/SFLOW/GLOBAL
{
  "sonic-sflow:GLOBAL": {
    "admin_state": "up",
    "polling_interval": 0,
    "agent_id": "string"
  }
}

/sonic-sflow:sonic-sflow/SFLOW_COLLECTOR
/sonic-sflow:sonic-sflow/SFLOW_COLLECTOR={collector_name}
{
  "sonic-sflow:SFLOW_COLLECTOR": [
    {
      "collector_name": "string",
      "collector_ip": "string",
      "collector_port": 0
    }
  ]
}

/sonic-sflow:sonic-sflow/SFLOW_SESSION
/sonic-sflow:sonic-sflow/SFLOW_SESSION={ifname}
{
  "sonic-sflow:SFLOW_SESSION": [
    {
      "admin_state": "up",
      "ifname": "Ethernet0",
      "sample_rate": 4400
    }
  ]
}
```

### 3.6.2 CLI
sFlow configuration and show commands will be the same as the one available on the host provided by SONiC
#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

##### Enable sFlow
```
sonic(config)# sflow enabled
sonic(config)#
```

##### Disable sFlow
```
sonic(config)# no sflow enabled
sonic(config)#
```

##### Add sFlow Collector
Syntax:

port# : [0 - 65535]

`sflow collector <collector name> <IPv4/IPv6 address> [port #]`

```
sonic(config)# sflow collector col1 1.1.1.1
sonic(config)#
```

##### Add sFlow Collector with port number
```
sonic(config)# sflow collector col2 1.1.1.2 port 4451
sonic(config)#
```

##### Remove a sFlow Collector
Syntax:

`no sflow collector <collector name>`

```
sonic(config)# no sflow collector col1
sonic(config)#
```

##### Configure sFlow agent interface
Syntax:

`sflow agent <ifname>`

```
sonic(config)# sflow agent-id Ethernet0
sonic(config)#
```

##### Reset sFlow agent to default interface
```
sonic(config)# no sflow agent-id
sonic(config)#
```
The default sFlow agent is selected based on some simple heuristics.

For more information, please refer to the sFlow HLD linked above.

##### Configure sFlow polling-interval
Syntax:

interval: [5 - 300] (0 to disable)

`sflow polling-interval <interval #>`

```
sonic(config)# sflow polling-interval 44
sonic(config)#
```

##### Reset sFlow polling-interval to default
```
sonic(config)# no sflow polling-interval
sonic(config)#
```

sFlow configurations for specific interface are executed in interview-configuration-view:
```
sonic# configure terminal
sonic(config)# interface Ethernet 0
sonic(conf-if-Ethernet0)#
```

##### Enable sFlow
```
sonic(conf-if-Ethernet0)# sflow enable
sonic(conf-if-Ethernet0)#
```

##### Disable sFlow
```
sonic(conf-if-Ethernet0)# no sflow enable
sonic(conf-if-Ethernet0)#
```

##### Set sampling-rate
Syntax:

`sflow sampling-rate <rate>`

rate: [256 - 8388608]

```
sonic(conf-if-Ethernet0)# sflow sampling-rate 4400
sonic(conf-if-Ethernet0)#
```

##### Reset sampling-rate to default
```
sonic(conf-if-Ethernet0)# no sflow sampling-rate
sonic(conf-if-Ethernet0)#
```
The default value is based on the interface speed: (ifSpeed / 1e6) where ifSpeed is in bits/sec.
For more information, please refer to the sFlow HLD linked above.


#### 3.6.2.2 Show Commands
##### Show global sFlow configurations
```
sonic# show sflow
---------------------------------------------------------
Global sFlow Information
---------------------------------------------------------
        admin state:       enabled
        polling-interval:  20
        agent-id:          default
sonic#
```
##### Show sFlow interface configurations
```
sonic# show sflow interface
-----------------------------------------------------------
sFlow interface configurations
   Interface            Admin State             Sampling Rate
   Ethernet0            enabled                 4000
   Ethernet1            enabled                 4000
   Ethernet2            enabled                 4000
   Ethernet3            enabled                 4000
   Ethernet4            enabled                 4000
   Ethernet5            enabled                 4000
   Ethernet6            enabled                 4000
   Ethernet7            enabled                 4000
   Ethernet8            enabled                 4000
   Ethernet9            enabled                 4000
   Ethernet10           enabled                 4000
   Ethernet11           enabled                 4000
   Ethernet12           enabled                 4000
   Ethernet13           enabled                 4000
   Ethernet14           enabled                 4000
   Ethernet15           enabled                 4000
   Ethernet16           enabled                 4000
   Ethernet17           enabled                 4000
   Ethernet18           enabled                 4000
   Ethernet19           enabled                 4000
   Ethernet20           enabled                 4000
   Ethernet21           enabled                 4000
--more--
   Ethernet22           enabled                 4000
   Ethernet23           enabled                 4000
   Ethernet24           enabled                 4000
   Ethernet25           enabled                 4000
   Ethernet26           enabled                 4000
   Ethernet27           enabled                 4000
   Ethernet28           enabled                 4000
   Ethernet29           enabled                 4000
sonic#
```

#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing sFlow configuration information from CONFIG DB.
POST - Add a new sFlow configuration into CONFIG DB.
PATCH - Update existing sFlow configuraiton information in CONFIG DB.
PUT - Add a list of sFlow configurations into CONFIG DB.
DELETE - Delete a existing sFlow configuration from CONFIG DB. This will cause some configurations to return to default value.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug


# 7 Warm Boot Support


# 8 Scalability


# 9 Unit Test
The unit-test for this feature will include:
#### Configuration via CLI

| Test Name | Test Description |
| :------ | :----- |
| Enable sFlow | Verify sFlow is enabled in Config DB |
| Disable sFlow | Verify sFlow is disabled in Config DB |
| Configure polling-interval | Verify sFlow polling-interval is set in Config DB |
| Disable polling-interval | Verify sFlow polling-interval is removed from Config DB (back to default)
| Add a collector | Verify a collector has been added into Config DB |
| Add a collector with port # | Verify a collector has been added into Config DB with user supplied port #|
| Delete a collector | Verify a collector has been deleted from Config DB
| Add agent-id information | Verify sFlow agent interface is set
| Disable sFlow agent | Verify sFlow agent interface is back to default
| Enable sFlow on interface | Verify sFlow for an interface is enabled in Config DB |
| Disable sFlow on interface | Verify sFlow for an interface is disabled in Config DB |
| Configure sampling-rate on interface | Verify sampling-rate for an interface is set in Config DB|
| Disable sampling-rate on interface | Verify sampling-rate has returned to default

#### Show sFlow configuration via CLI

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request

#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.

# 10 Internal Design Information

