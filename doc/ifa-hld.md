# Feature Name
Inband Flow Analyzer.
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
| 0.1 | 10/30/2019  |   Srinadh Penugonda| Initial version                   |

# About this Manual
This document provides general information about the Inband Flow Analyzer feature implementation in SONiC.
# Scope
This document describes the north bound interface and unit tests for Inband Flow Analyzer feature.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| IFA                      | Inband Flow Analyzer                |
| TAM                      | Telemetry and Monitoring            |
# 1 Feature Overview

Inband Flow Analyzer is a flexible packet and flow monitoring inband telemtry solution. The feature allows configuration of IFA sessions that provide Inband telemetry over sampled traffic to collectors.

It provides mechanism to monitor and analyze when packets enter/exit the network, the path packets and flows take through the network, the rate at which packets arrive at each hop and how log packets spend at each hop etc., Out of band management technhiques can not measure such details.

## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide management framework support to existing SONiC capabilities with respect to IFA.

1.1 IFA feature is accomplished by configuring IFA session on various nodes that act as ingress,
intermediate and egress devices. Device role is per flow in a node and a single node can act as ingress
device for one flow and intermediate device for another flow.

2.0.0.1 TAM device identifier to uniquely identify a device in network and insert the same in INT header.
2.0.0.2 ACL configuration to identify a flow and sample packets from that flow to insert IFA headers.
2.0.0.3 TAM collector configuration that can be attached to IFA flow on egress device to forward telemetry
data.
3.0 UI commands available to configure TAM device identifier, TAM collector and IFA configuration.
3.1 UI commands available to show TAM device identifier, TAM collector, IFA configuration, IFA status and
IFA statistics.
3.2 UI commands available to clear IFA configuration
4.0 The maximum number of IFA 􀃖ows are platform dependent.
4.1 Only one collector can be con􀃕gured in a device.
4.5 Some platforms may require provisioning to enable IFA. 'ifa -config -enable' command to be issued to
provision such platforms for IFA functionality. 'ifa -config -disable' command can be issued to disable
provisioning of IFA on such platforms.

### 1.1.2 Configuration and Management Requirements
1. CLI configuration/show support
2. REST API support
3. gNMI support

## 1.2 Design Overview
### 1.2.1 Basic Approach

As there is no opeconfig/ietf yang file exists for this feature, it is decided to go with sonic yang. 

### 1.2.2 Container
The changes are in sonic-management-framework container.

There will be additional files added.
1. XML file for the CLI
2. Python script to handle CLI request (actioner)
3. Jinja template to render CLI output (renderer)
4. YANG models 
	sonic-ifa.yang

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Whenever operator want to track packet latency/congestion metrics. 
## 2.2 Functional Description
The management UI provides an user friendly interface to configure Inband Flow Analyzer.
# 3 Design
## 3.1 Overview
The packet action field in acl rule indicates the type of IFA device: ingress and egress. 'int_insert' makes the device as ingress IAF device and 'int_delete' as egress IFA device. Ingress IAF device makes a sample of a flow and tags them for analysis and data collection. Egress device is responsible for terminating IFA flow by summarizing the telemtry data of the entire path and sending it to the collector.

The device identifer uniquely identifies the device in the network and inserts the ID in the IFA header.

Collectors receive the telemetry data from egress devices.

Flow configuration will contain sampling rate at which rate traffic will be sampled.

IFA feature can be enabled or disabled.
## 3.6 User Interface
### 3.6.1 Data Models

https://github.com/project-arlo/sonic-mgmt-framework/blob/94a7c70de961c5c9b59429bc4acdba710a2592b8/models/yang/sonic/sonic-ifa.yang

module: sonic-ifa
    +--rw sonic-ifa
       +--rw TAM_INT_IFA_FEATURE_TABLE
       |  +--rw TAM_INT_IFA_FEATURE_TABLE_LIST* [feature]
       |     +--rw feature    string
       |     +--rw enable?    boolean
       +--rw TAM_DEVICE_TABLE
       |  +--rw TAM_DEVICE_TABLE_LIST* [device]
       |     +--rw device      string
       |     +--rw deviceid?   uint16
       +--rw TAM_COLLECTOR_TABLE
       |  +--rw TAM_COLLECTOR_TABLE_LIST* [name]
       |     +--rw name              string
       |     +--rw ipaddress-type?   enumeration
       |     +--rw ipaddress?        inet:ip-address
       |     +--rw port?             uint16
       +--rw TAM_INT_IFA_FLOW_TABLE
          +--rw TAM_INT_IFA_FLOW_TABLE_LIST* [name]
             +--rw name              string
             +--rw acl-table-name?   -> /sacl:sonic-acl/ACL_TABLE/ACL_TABLE_LIST/aclname
             +--rw acl-rule-name?    -> /sacl:sonic-acl/ACL_RULE/ACL_RULE_LIST/rulename
             +--rw sampling-rate?    uint16
             +--rw collector-name?   -> ../../../TAM_COLLECTOR_TABLE/TAM_COLLECTOR_TABLE_LIST/name

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
1. Command   : confg tam device-id 
Attribute    : <id>
The command is used to configure TAM device identifier.

2. Command   : config tam collector
Attribute(s) : {collector-name} ip-type <ipv4 | ipv6> ip-addr <address> port <port>
The command is used to configure TAM collector and IFA report will be forwarded to the collector.

3. Command   : config tam-int-ifa feature
Attribute    : <enable | disable>
The command is used to enable or disable the IFA feature.

4. Command   : config tam-int-ifa flow 
Attribute(s) : <flow-name> acl-rule <rule-name> acl-table <table-name> { sampling-rate <val> collector <name> }
The command is used to specify flow criteria to match against incoming flow and tag with IFA data. When sampling rate is specified, one packet will be sampled out of its value. When collector is specified, IFA report will be forwarded to it.

5. Command  : config-tam no device-id
The command is used to clear user configured device identifier. Default device identifier is used.

6. Command  : config-tam no collector 
Attribute    : <name>
The command is used to delete previously configured collector information.

7. Command  : config-tam-int-ifa no flow
Attribute    : <name>
The command is used to delete previously configure flow information.

#### 3.6.2.2 Show Commands
1. Command   : show tam device
The command is used to show TAM device identifier.

2. Command   : show tam collector 
Attribute    : { <name> | all }
The command is used to show TAM collector information.

3. Command   : show tam-int-ifa status
The command is used to show current status of IFA: deviceid, number of flows and collectors, feature status.

4. Command   : show tam-int-ifa flow
Attribute(s) : { <name> | all }
The command is used to display configured IFA flow information.

5. Command   : show tam-int-ifa statistics
Attribute(s) : { <flow> | all }
The command is used to display IFA statistics per/all flow(s)
#### 3.6.2.3 Debug Commands
N/A

### 3.6.3 REST API Support

1. Get Device Information
sonic-ifa:sonic-ifa/TAM_DEVICE_TABLE

2. Get Collector information
sonic-ifa:sonic-ifa/TAM_COLLECTOR_TABLE

3. Get particular collector information
sonic-ifa:sonic-ifa/TAM_COLLECTOR_TABLE/TAM_COLLECTOR_TABLE_LIST={name}

4. Get IFA feature information
sonic-ifa:sonic-ifa/TAM_INT_FEATURE_TABLE

5. Get IFA flow information
sonic-ifa:sonic-ifa/TAM_INT_IFA_FLOW_TABLE

6. Get particular IFA flow information
sonic-ifa:sonic-ifa/TAM_INT_IFA_FLOW_TABLE/TAM_INT_IFA_FLOW_TABLE_LIST={name}

7. Set device identifier
sonic-ifa:sonic-ifa/TAM_DEVICE_TABLE/TAM_DEVICE_TABLE_LIST={device}/deviceid
{
  "sonic-ifa:deviceid": 0
}

8. Set TAM collector
sonic-ifa:sonic-ifa/TAM_COLLECTOR_TABLE/TAM_COLLECTOR_TABLE_LIST
{
  "sonic-ifa:TAM_COLLECTOR_TABLE_LIST": [
    {
      "name": "string",
      "ipaddress-type": "ipv4",
      "v4addr": "string",
      "v6addr": "string",
      "port": 0
    }
  ]
}

9. Set TAM INT IFA feature
sonic-ifa:sonic-ifa/TAM_INT_IFA_FEATURE_TABLE/TAM_INT_IFA_FEATURE_TABLE_LIST={feature}/enable
{
  "sonic-ifa:enable": true
}

10. Set TAM INT IFA flow
sonic-ifa:sonic-ifa/TAM_INT_IFA_FLOW_TABLE/TAM_INT_IFA_FLOW_TABLE_LIST={name}
{
  "sonic-ifa:TAM_INT_IFA_FLOW_TABLE_LIST": [
    {
      "name": "string",
      "acl-table-name": "string",
      "acl-rule-name": "string",
      "sampling-rate": 0,
      "collector": "string"
    }
  ]
}

11. Delete TAM device identifier
sonic-ifa:sonic-ifa/TAM_DEVICE_TABLE/TAM_DEVICE_TABLE_LIST={device}/deviceid

12. Delete TAM collector
sonic-ifa:sonic-ifa/TAM_COLLECTOR_TABLE/TAM_COLLECTOR_TABLE_LIST={name}

13. Delete IFA flow
sonic-ifa:sonic-ifa/TAM_INT_IFA_FLOW_TABLE/TAM_INT_IFA_FLOW_TABLE_LIST={name}


# 4 Flow Diagrams
N/A
# 5 Error Handling
N/A
# 6 Serviceability and Debug
TBD

# 7 Warm Boot Support
N/A
# 8 Scalability
N/A
# 9 Unit Test
| Test Name | Test Description |
| :------ | :----- |
| Create TAM DEvice Identifier | Verify device-id is configured. Verify a value with more than five digits will be rejected |
| Delete TAM device Identifier | Verify when device-id is deleted, it defaults to default value of 0 |
| Create TAM collector | Verify TAM collector is configured ( ip address validation is does by application ) |
| Delete TAM collector | Verify TAM collector can be deleted |
| Enable TAM INT IFA Feature | Verify user can enable/disable IFA feature |
| Create IFA Flow | Verify IFA flow is configured. Verify configuration fails when user uses invalid acl table/rule. Verify configuration fails when user uses invalid collector name |
| Delete IFA flow | Verify IFA flow is deleted |
| Show TAM Device | Verify configured device identifier is displayed with the show command |
| Show TAM collector | Verify all collectors are displayed with 'all' keyword. Verify specified collector is displayed with the name. Verify command fails when an invalid flow name is used to display |
| Show TAM INT IFA status | Verify nmber of flows/collectors correctly displayed; device id and feature status is correctly displayed |
| Show TAM INT IFA flow | Verify all flow information is displayed when used with 'all'. Verify particular flow is displayed when name is supplied. Verify command fails when an non-existent flow name is given |
| show TAM INT IFA statistics | Verify flow information and packet/byte count is displayed per each flow |
| show tam int ifa supported | Verify feature status is correctly displayed |


# 10 Internal Design Information
N/A
