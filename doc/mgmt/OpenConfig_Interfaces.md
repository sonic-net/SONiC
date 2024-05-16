# OpenConfig support for Ethernet interfaces.

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
      * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
      * [1.1.3 Scalability Requirements](#113-scalability-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)
      * [1.2.2 Container](#122-container)
  * [2 Functionality](#2-functionality)
      * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 02/24/2024  | Nikita Agarwal / Satoru Shinohara | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of Ethernet interfaces in SONiC.

# Scope
- This document describes the high level design of OpenConfig configuration of Ethernet interfaces via REST and gNMI in SONiC.
- This does not cover the SONiC KLISH CLI.
- This covers only Ethernet interfaces configuration.
- This does not support subinterfaces configuration.
- This does not cover gNMI subscription.
- This does not cover secondary IP configuration.
- Supported attributes in OpenConfig YANG tree:
  ```  
  module: openconfig-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw name               -> ../config/name
        +--rw config
        |  +--rw name?          string
        |  +--rw mtu?           uint16
        |  +--rw description?   string
        |  +--rw enabled?       boolean
        +--ro state
        |  +--ro name?           string
        |  +--ro mtu?            uint16
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
        +--rw oc-eth:ethernet
           +--rw oc-eth:config
           |  +--rw oc-eth:auto-negotiate?   boolean
           |  +--rw oc-eth:port-speed?       identityref
           +--ro oc-eth:state
              +--ro oc-eth:auto-negotiate?   boolean
              +--ro oc-eth:port-speed?       identityref


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
    Configure/ Set Ethernet interface attributes.
    Get Ethernet interface attributes.
    Delete Ethernet interface attributes.
3. Support port-speed and auto-negotiation on Ethernet interfaces via REST and gNMI.
4. Support IPv4 and IPv6 address configuration on Ethernet interfaces via REST and gNMI.
5. Support Enabling and disabling IPv6 enabled attribute on Ethernet interface via REST and gNMI. IPv6 enabled is set to disabled by default.
### 1.1.2 Configuration and Management Requirements
The Ethernet interface configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.
### 1.1.3 Scalability Requirements
The maximum number of interfaces depends on number of Ethernet interfaces supported by the switch.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports Ethernet interfaces configurations such as Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
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
### 3.3.1 Data Models
Support for additional speeds for Ethernet are brought in to openconfig-if-ethernet.yang from the [OpenConfig YANG community](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-if-ethernet.yang#L263) 
```
    identity SPEED_200GB {
    base ETHERNET_SPEED;
    description "200 Gbps Ethernet";
  }

  identity SPEED_400GB {
    base ETHERNET_SPEED;
    description "400 Gbps Ethernet";
  }

  identity SPEED_600GB {
    base ETHERNET_SPEED;
    description "600 Gbps Ethernet";
  }

  identity SPEED_800GB {
    base ETHERNET_SPEED;
    description "800 Gbps Ethernet";
  }
  ```
### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at leaf level as well.
Sample GET output without IPv4 configuration on Ethernet104: 
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet104" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"enabled":true,"mtu":9100,"name":"Ethernet104"},"openconfig-if-ethernet:ethernet":{"config":{"auto-negotiate":false,"port-speed":"openconfig-if-ethernet:SPEED_10GB"},"state":{"auto-negotiate":false,"port-speed":"openconfig-if-ethernet:SPEED_10GB"}},"name":"Ethernet104","state":{"admin-status":"UP","description":"","enabled":true,"mtu":9100,"name":"Ethernet104"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv6":{"config":{"enabled":false}},"state":{"index":0}}]}}]}
```
Sample GET output with IPv4 configuration on Ethernet104:
```
admin@sonic:~$ curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet104" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"description":"patch_leaf","enabled":true,"mtu":9150,"name":"Ethernet104"},"openconfig-if-ethernet:ethernet":{"config":{"auto-negotiate":true,"port-speed":"openconfig-if-ethernet:SPEED_10GB"},"state":{"auto-negotiate":true,"port-speed":"openconfig-if-ethernet:SPEED_10GB"}},"name":"Ethernet104","state":{"admin-status":"UP","description":"patch_leaf","enabled":true,"mtu":9150,"name":"Ethernet104"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv4":{"addresses":{"address":[{"config":{"ip":"10.0.0.248","prefix-length":31},"ip":"10.0.0.248","state":{"ip":"10.0.0.248","prefix-length":31}}]}},"openconfig-if-ip:ipv6":{"config":{"enabled":false}},"state":{"index":0}}]}}]}
```
#### 3.3.2.2 SET
Supported at leaf level as well.
Sample PATCH at leaf node for MTU
```
curl -X PATCH -k  "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet104/config/mtu" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-interfaces:mtu\":9150}"
```
Sample Verify MTU PATCH with GET:
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet104/config/mtu" -H "accept: application/yang-data+json"
{"openconfig-interfaces:mtu":9150}
```
#### 3.3.2.3 DELETE
Supported at leaf level as well.
Illustration for DELETE at leaf level MTU:
```
curl -X DELETE -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet104/config/mtu" -H "accept: */*"
```
### 3.3.3 gNMI Support
#### 3.3.3.1 GET
Supported
#### 3.3.3.2 SET
Supported
#### 3.3.3.3 DELETE
Supported
# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and SONiC YANG:
|   OpenConfig YANG       |    Sonic-port YANG    |
|-------------------------|-----------------------|
|   name                  |      name             |
|   auto-negotiate        |      autoneg          |
|   port-speed            |      speed            |
|   description           |      description      |
|   mtu                   |      mtu              |
|   enabled               |      admin\_status    |
|   index                 |      index            |

|   OpenConfig YANG       |    Sonic-interface YANG |
|-------------------------|-------------------------|
|   name                  |      name               |
|   enabled               |      ipv6\_use\_link\_local\_only          |
|   index                 |      index              |
|   prefix-length         |      ip-prefix          |

# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Verify that GET, PATCH and DELETE for mtu works as expected via REST and gNMI.
2. Verify that GET, PATCH and DELETE for description works as expected via REST and gNMI.
3. Verify that GET, PATCH and DELETE for enabled works as expected via REST and gNMI.
4. Verify that GET, PATCH and DELETE for auto-negotiate works as expected via REST and gNMI. GET on auto-negotiate should return Resource Not Found error after DELETE.
5. Verify that GET and PATCH for port-speed works as expected via REST and gNMI.
6. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterfaces level works as expected via REST and gNMI.
7. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterface ID 0 level works as expected via REST and gNMI.
8. Verify that GET, PATCH and DELETE IPv4 and IPv6 addresses at subinterface level works as expected via REST and gNMI.
9. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at addresses level works as expected via REST and gNMI.
10. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at address level works as expected via REST and gNMI.
11. Verify that GET, PATCH, DELETE IPv4 and IPv6 addresses at address/config level works as expected via REST and gNMI. GET at config level should return Resource Not Found when there is no configuration.
12. Verify that Enable and disabling of ipv6/config/enabled works as expected via REST and gNMI.

## 6.2 Negative Test Cases
1. Verify DELETE at interfaces, interface, and interface name container is not allowed.
2. Verify REPLACE for Ethernet interface is not allowed.
3. Verify that DELETE on port-speed will return a not supported error.
4. Verify that GET at subinterfaces (subinterface index greater than zero) returns empty.
5. Verify that duplicate IP address cannot be configured on another interface.
6. Verify that Delete at ipv6 and ipv4 container is not allowed.
