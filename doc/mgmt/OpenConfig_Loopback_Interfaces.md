# OpenConfig support for Loopback interfaces.

# High Level Design Document
#### Rev 0.1

# Table of Contents
- [OpenConfig support for Loopback interfaces.](#openconfig-support-for-loopback-interfaces)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.1](#rev-01)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
    - [Table 1: Abbreviations](#table-1-abbreviations)
- [1 Feature Overview](#1-feature-overview)
  - [1.1 Requirements](#11-requirements)
    - [1.1.1 Functional Requirements](#111-functional-requirements)
    - [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
  - [1.2 Design Overview](#12-design-overview)
    - [1.2.1 Basic Approach](#121-basic-approach)
    - [1.2.2 Container](#122-container)
- [2 Functionality](#2-functionality)
  - [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
- [3 Design](#3-design)
  - [3.1 Overview](#31-overview)
  - [3.2 DB Changes](#32-db-changes)
    - [3.2.1 CONFIG DB](#321-config-db)
    - [3.2.2 APP DB](#322-app-db)
    - [3.2.3 STATE DB](#323-state-db)
    - [3.2.4 ASIC DB](#324-asic-db)
    - [3.2.5 COUNTER DB](#325-counter-db)
  - [3.3 User Interface](#33-user-interface)
    - [3.3.1 REST API Support](#331-rest-api-support)
      - [3.3.1.1 GET](#3311-get)
      - [3.3.1.2 SET](#3312-set)
      - [3.3.1.3 DELETE](#3313-delete)
    - [3.3.2 gNMI Support](#332-gnmi-support)
      - [3.3.2.1 GET](#3321-get)
      - [3.3.2.2 SET](#3322-set)
      - [3.3.2.3 DELETE](#3323-delete)
- [4 Flow Diagrams](#4-flow-diagrams)
- [5 Error Handling](#5-error-handling)
- [6 Unit Test cases](#6-unit-test-cases)
  - [6.1 Functional Test Cases](#61-functional-test-cases)
  - [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author                  | Change Description                |
|:---:|:-----------:|:-----------------------------:|-----------------------------------|
| 0.1 | 06/05/2025  | Venkata Krishna Rao Gorrepati | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of Loopback interfaces in SONiC.

# Scope
- This document describes the high level design of OpenConfig configuration of Loopback interfaces via REST and gNMI in SONiC.
- This does not cover the SONiC KLISH CLI.
- This covers only Loopback interfaces configuration.
- This does not support subinterfaces configuration.
- This does not cover gNMI subscription.
- Supported attributes in OpenConfig YANG tree:
  ```  
  module: openconfig-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw name               -> ../config/name
        +--rw config
        |  +--rw name?          string
        |  +--rw description?   string
        |  +--rw enabled?       boolean
        +--ro state
        |  +--ro name?           string
        |  +--ro description?    string
        |  +--ro enabled?        boolean
        |  +--ro admin-status    enumeration
        +--rw subinterfaces
        |  +--rw subinterface* [index]
        |     +--rw index         -> ../config/index
        |     +--rw config
        |     |  +--rw index?         uint32
        |     |  +--rw description?   string
        |     |  +--rw enabled?       boolean
        |     +--ro state
        |     |  +--ro index?         uint32
        |     |  +--ro description?   string
        |     |  +--ro enabled?       boolean
        |     |  +--ro name?          string
        |     +--rw oc-ip:ipv4
        |     |  +--rw oc-ip:addresses
        |     |     +--rw oc-ip:address* [ip]
        |     |        +--rw oc-ip:ip        -> ../config/ip
        |     |        +--rw oc-ip:config
        |     |        |  +--rw oc-ip:ip?              oc-inet:ipv4-address
        |     |        |  +--rw oc-ip:prefix-length?   uint8
        |     |        +--ro oc-ip:state
        |     |           +--ro oc-ip:ip?              oc-inet:ipv4-address
        |     |           +--ro oc-ip:prefix-length?   uint8
        |     +--rw oc-ip:ipv6
        |        +--rw oc-ip:addresses
        |        |  +--rw oc-ip:address* [ip]
        |        |     +--rw oc-ip:ip        -> ../config/ip
        |        |     +--rw oc-ip:config
        |        |     |  +--rw oc-ip:ip?              oc-inet:ipv6-address
        |        |     |  +--rw oc-ip:prefix-length    uint8
        |        |     +--ro oc-ip:state
        |        |        +--ro oc-ip:ip?              oc-inet:ipv6-address
        |        |        +--ro oc-ip:prefix-length    uint8
        |        +--rw oc-ip:config
        |           +--rw oc-ip:enabled?   boolean
  ```
# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models.
2. Replace translib App based implementation with a Transformer based implementation of:
    Configure/ Set Loopback interface attributes.
    Get Loopback interface attributes.
    Delete Loopback interface attributes.
3. Support IPv4 and IPv6 address configuration on Loopback interfaces via REST and gNMI.

### 1.1.2 Configuration and Management Requirements
The Loopback interface configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports Loopback interfaces configurations such as Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get and set based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition.
### 3.2.2 APP DB
There are no changes to APP DB schema definition.
### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.
### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.
### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 REST API Support
#### 3.3.1.1 GET
Supported at leaf level as well.
Sample GET output without IPv4 configuration on Loopback11: 
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Loopback11" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"name":"Loopback11", "description":"Loopback interface"},"name":"Loopback11","state":{"admin-status":"UP","description":"","enabled":true,"name":"Loopback11"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv6":{"config":{"enabled":false}},"state":{"index":0}}]}}]}
```
Sample GET output with IPv4 configuration on Loopback11:
```
admin@sonic:~$ curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Loopback11" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"description":"patch_leaf","enabled":true,"name":"Loopback11"},"name":"Loopback11","state":{"admin-status":"UP","description":"patch_leaf","enabled":true,"name":"Loopback11"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv4":{"addresses":{"address":[{"config":{"ip":"10.0.0.248","prefix-length":31},"ip":"10.0.0.248","state":{"ip":"10.0.0.248","prefix-length":31}}]}},"openconfig-if-ip:ipv6":{"config":{"enabled":false}},"state":{"index":0}}]}}]}
```
#### 3.3.1.2 SET
Supported at leaf level as well.
Sample PATCH at leaf node for enabled. enabled value with false should return error message "Disable is not supported on Loopback interface
```
curl -X PATCH -k  "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Loopback11/config/enabled" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-interfaces:enabled\": true}"
```
Sample Verify enabled PATCH with GET:
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Loopback11/config/enabled" -H "accept: application/yang-data+json"
{"openconfig-interfaces:enabled":true}
```
#### 3.3.1.3 DELETE
Disabling Loopback port is not supported
Illustration for DELETE at leaf level enabled:
```
curl -X DELETE -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Loopback/config/enabled" -H "accept: */*"
```
### 3.3.2 gNMI Support
#### 3.3.2.1 GET
Supported
#### 3.3.2.2 SET
Supported
#### 3.3.2.3 DELETE
Supported
# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and SONiC YANG:
|   OpenConfig YANG       |    sonic-loopback-interface YANG    |
|-------------------------|-------------------------------------|
|   name                  |      name                           |
|   description           |      description                    |
|   enabled               |      admin\_status                  |
|   prefix-length         |       ip-prefix                     |

# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Verify that GET, PATCH and DELETE for mtu works as expected via REST and gNMI.
2. Verify that GET, PATCH and DELETE for description works as expected via REST and gNMI.
3. Verify that GET, PATCH and DELETE for enabled works as expected via REST and gNMI.
4. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterfaces level works as expected via REST and gNMI.
5. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterface ID 0 level works as expected via REST and gNMI.
6. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterface level works as expected via REST and gNMI.
7. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at addresses level works as expected via REST and gNMI.
8. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at address level works as expected via REST and gNMI.
9. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at address/config level works as expected via REST and gNMI. GET at config level should return Resource Not Found when there is no configuration.
10. Verify that Enable and disabling of ipv6/config/enabled works as expected via REST and gNMI.

## 6.2 Negative Test Cases
1. Verify DELETE at interfaces, interface, and interface name container is not allowed.
2. Verify that GET at subinterfaces (subinterface index greater than zero) returns empty.
3. Verify that duplicate IP address cannot be configured on another interface.
4. Verify that Delete at ipv6 and ipv4 container is not allowed.
