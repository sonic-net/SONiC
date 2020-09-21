# Feature Name
sFlow Support in Management Framework
# High Level Design Document
#### Rev 0.8

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                                                     |
|:---:|:-----------:|:------------------:|------------------------------------------------------------------------|
| 0.1 | 09/09/2019  |   Garrick He       | Initial version                                                        |
| 0.2 | 10/04/2019  |   Garrick He       | Address review comments                                                |
| 0.3 | 10/11/2019  |   Garrick He       | Address review comments                                                |
| 0.4 | 10/15/2019  |   Garrick He       | Add information on default value and SONiC sFlow YANG                  |
| 0.5 | 11/01/2019  |   Garrick He       | Add default values for polling intervals and updated sFlow Data models |
| 0.6 | 11/15/2019  |   Garrick He       | Remove redundant 'port' keyword from CLI                               |
| 0.7 | 05/25/2020  |   Garrick He       | Update to OpenConfig sFlow YANG model                                  |
| 0.8 | 06/17/2020  |   Venkatesan Mahalingam  | Add management VRF support                                       |

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
A few extensions had to be added to the OpenConfig sampling model for sFlow
* polling-interval
* agent

The collector list had to be extended to accomodate VRF name.
```
module: openconfig-sampling
  +--rw sampling
     +--rw config
     +--ro state
     +--rw sflow
     |  +--rw config
     |  |  +--rw enabled?                            boolean
     |  |  +--rw source-address?                     oc-inet:ip-address
     |  |  +--rw sampling-rate?                      uint32
     |  |  +--rw sample-size?                        uint16
     |  |  +--rw oc-sampling-ext:polling-interval?   uint32
     |  |  +--rw oc-sampling-ext:agent?              oc-if:base-interface-ref
     |  +--ro state
     |  |  +--ro enabled?          boolean
     |  |  +--ro source-address?   oc-inet:ip-address
     |  |  +--ro sampling-rate?    uint32
     |  |  +--ro sample-size?      uint16
     |  +--rw collectors
     |  |  +--rw oc-sampling-ext:collector-ext* [address port vrf]
     |  |     +--rw oc-sampling-ext:address    -> ../config/address
     |  |     +--rw oc-sampling-ext:port       -> ../config/port
     |  |     +--rw oc-sampling-ext:vrf        -> ../config/vrf
     |  |     +--rw oc-sampling-ext:config
     |  |     |  +--rw oc-sampling-ext:address?   oc-inet:ip-address
     |  |     |  +--rw oc-sampling-ext:port?      oc-inet:port-number
     |  |     |  +--rw oc-sampling-ext:vrf?       -> /oc-netinst:network-instances/network-instance/name
     |  |     +--ro oc-sampling-ext:state
     |  |        +--ro oc-sampling-ext:address?        oc-inet:ip-address
     |  |        +--ro oc-sampling-ext:port?           oc-inet:port-number
     |  |        +--ro oc-sampling-ext:vrf?            -> /oc-netinst:network-instances/network-instance/name
     |  |        +--ro oc-sampling-ext:packets-sent?   oc-yang:counter64
     |  +--rw interfaces
     |     +--rw interface* [name]
     |        +--rw name      -> ../config/name
     |        +--rw config
     |        |  +--rw name?            oc-if:base-interface-ref
     |        |  +--rw enabled?         boolean
     |        |  +--rw sampling-rate?   uint32
     |        +--ro state
     |           +--ro name?              oc-if:base-interface-ref
     |           +--ro enabled?           boolean
     |           +--ro sampling-rate?     uint32
     |           +--ro packets-sampled?   oc-yang:counter64
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
sonic(config)# sflow enable
sonic(config)#
```

##### Disable sFlow
```
sonic(config)# no sflow enable
sonic(config)#
```

##### Add sFlow Collector
Syntax:

port# : [0 - 65535] (default is: 6343)

`sflow collector <IPv4/IPv6 address> [port #]`

```
sonic(config)# sflow collector 1.1.1.1
sonic(config)#
```

##### Add sFlow Collector with port number
```
sonic(config)# sflow collector 1.1.1.2 4451
sonic(config)#
```

##### Remove a sFlow Collector
Syntax:

`no sflow collector <collector ip-address>`

```
sonic(config)# no sflow collector 1.1.1.1
sonic(config)#
```
##### Add sFlow Collector with VRF name
Syntax:

`sflow collector <collector ip-address> vrf <VRF-name>`

```
sonic(config)# sflow collector 1.1.1.2 vrf mgmt
sonic(config)#
```

##### Remove a sFlow Collector
Syntax:

`no sflow collector <collector ip-address> vrf <VRF-name>`

```
sonic(config)# no sflow collector 1.1.1.2 vrf mgmt
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

interval: [5 - 300] (0 to disable, default is 20)

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
The default value is based on the interface speed: (ifSpeed / 1e6) where ifSpeed is in bits/sec.
For more information, please refer to the sFlow HLD linked above.

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
        admin state:       up
        polling-interval:  20
        agent-id:          default
		configured collectors:  2
         1.1.1.1             6343        default
         1.1.1.2             4511        mgmt
sonic#
```
Note: Currently only default & mgmt VRFs are supported.
##### Show sFlow interface configurations
```
sonic# show sflow interface
-----------------------------------------------------------
sFlow interface configurations
   Interface            Admin State             Sampling Rate
   Ethernet0            up                      4000
   Ethernet1            up                      4000
   Ethernet2            up                      4000
   Ethernet3            up                      4000
   Ethernet4            up                      4000
   Ethernet5            up                      4000
   Ethernet6            up                      4000
   Ethernet7            up                      4000
   Ethernet8            up                      4000
   Ethernet9            up                      4000
   Ethernet10           up                      4000
   Ethernet11           up                      4000
   Ethernet12           up                      4000
   Ethernet13           up                      4000
   Ethernet14           up                      4000
   Ethernet15           up                      4000
   Ethernet16           up                      4000
   Ethernet17           up                      4000
   Ethernet18           up                      4000
   Ethernet19           up                      4000
   Ethernet20           up                      4000
   Ethernet21           up                      4000
--more--
   Ethernet22           up                      4000
   Ethernet23           up                      4000
   Ethernet24           up                      4000
   Ethernet25           up                      4000
   Ethernet26           up                      4000
   Ethernet27           up                      4000
   Ethernet28           up                      4000
   Ethernet29           up                      4000
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
Since the IP address is used to identify the collector. The user **cannot** modify the IP address field. If
the user wants to change a collector IP address, they will need to delete the collector in question and recreate
it with the desired IP address.

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
| Add a collector with mgmt VRF name | Verify a collector has been added into Config DB with user supplied VRF name|
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
