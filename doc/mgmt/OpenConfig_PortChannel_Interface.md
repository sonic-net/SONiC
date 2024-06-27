# OpenConfig support for PortChannel (aggregate) interface.

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
      * [3.3.1 REST API Support](#332-rest-api-support)
      * [3.3.2 gNMI Support](#333-gnmi-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
[Table 2: OC YANG SONiC YANG Mapping](#4-flow-diagrams)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 02/24/2024  | Satoru Shinohara | Initial version                   |

# About this Manual
This document provides general information about the OpenConfig configuration of portchannel (aggregate) interface in SONiC.

# Scope
- This document describes the high level design of configuration of portchannel interfaces using openconfig models via REST & gNMI. 
- This does not cover the SONiC KLISH CLI.
- This covers only the portchannel interfaces configuration.
- This does not support subinterfaces configuration.
- Supported attributes in OpenConfig YANG tree:

```  
module: openconfig-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw name                  -> ../config/name
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
        |  +--ro counters
        |     +--ro in-octets?            oc-yang:counter64
        |     +--ro in-pkts?              oc-yang:counter64
        |     +--ro in-unicast-pkts?      oc-yang:counter64
        |     +--ro in-broadcast-pkts?    oc-yang:counter64
        |     +--ro in-multicast-pkts?    oc-yang:counter64
        |     +--ro in-discards?          oc-yang:counter64
        |     +--ro in-errors?            oc-yang:counter64
        |     +--ro out-octets?           oc-yang:counter64
        |     +--ro out-pkts?             oc-yang:counter64
        |     +--ro out-unicast-pkts?     oc-yang:counter64
        |     +--ro out-broadcast-pkts?   oc-yang:counter64
        |     +--ro out-multicast-pkts?   oc-yang:counter64
        |     +--ro out-discards?         oc-yang:counter64
        |     +--ro out-errors?           oc-yang:counter64
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
        |        |  +--rw oc-ip:enabled?   boolean
        |        +--ro oc-ip:state
        |           +--ro oc-ip:enabled?   boolean
        +--rw oc-eth:ethernet
        |  +--rw oc-eth:config
        |  |  +--rw oc-eth:auto-negotiate?   boolean
        |  |  +--rw oc-eth:port-speed?       identityref
        |  |  +--rw oc-lag:aggregate-id?     -> /oc-if:interfaces/interface/name
        |  +--ro oc-eth:state
        |     +--ro oc-eth:auto-negotiate?   boolean
        |     +--ro oc-eth:port-speed?       identityref
        |     +--ro oc-eth:counters
        |     |  +--ro oc-eth:in-oversize-frames?    oc-yang:counter64
        |     |  +--ro oc-eth:in-undersize-frames?   oc-yang:counter64
        |     |  +--ro oc-eth:in-jabber-frames?      oc-yang:counter64
        |     |  +--ro oc-eth:in-fragment-frames?    oc-yang:counter64
        |     +--ro oc-lag:aggregate-id?     -> /oc-if:interfaces/interface/name
        +--rw oc-lag:aggregation
           +--rw oc-lag:config
           |  +--rw oc-lag:min-links?   uint16
           +--ro oc-lag:state
              +--ro oc-lag:min-links?   uint16
```
# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |
| Aggregate |   Interchangable with portchannel |


# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models.
2.  Configure/Set, GET, and Delete PortChannel interface attributes.
3. Support min-links attribute on PortChannel interfaces via REST and gNMI.
4. Support interface attributes on PortChannel type. 
### 1.1.2 Configuration and Management Requirements
The PortChannel interface configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration. There are no new configuration commands required to handle these configurations.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports PortChannel interfaces configurations such as Get, Patch and Delete via REST and gNMI. This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
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
Sample GET output on configured PortChannel: 
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel103" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"openconfig-if-aggregate:aggregation":{"config":{"min-links":1},"state":{"min-links":1}},"config":{"enabled":true,"mtu":9100,"name":"PortChannel103"},"name":"PortChannel103","state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"PortChannel103"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}},"state":{"index":0}}]}}]}
```
Sample GET output of Ethernet interface configured as part of PortChannel:
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet257" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"enabled":true,"mtu":9100,"name":"Ethernet257"},"openconfig-if-ethernet:ethernet":{"config":{"openconfig-if-aggregate:aggregate-id":"PortChannel103","port-speed":"openconfig-if-ethernet:SPEED_10GB"},"state":{"openconfig-if-aggregate:aggregate-id":"PortChannel103","counters":{"openconfig-if-ethernet-ext:in-distribution":{"in-frames-1024-1518-octets":"0","in-frames-128-255-octets":"0","in-frames-256-511-octets":"0","in-frames-512-1023-octets":"0","in-frames-64-octets":"0","in-frames-65-127-octets":"0"},"in-fragment-frames":"0","in-jabber-frames":"0","in-oversize-frames":"0","in-undersize-frames":"0"},"port-speed":"openconfig-if-ethernet:SPEED_10GB"}},"name":"Ethernet257","state":{"admin-status":"UP","counters":{"in-broadcast-pkts":"0","in-discards":"0","in-errors":"0","in-multicast-pkts":"0","in-octets":"0","in-pkts":"0","in-unicast-pkts":"0","out-broadcast-pkts":"0","out-discards":"0","out-errors":"0","out-multicast-pkts":"0","out-octets":"0","out-pkts":"0","out-unicast-pkts":"0"},"description":"","enabled":true,"mtu":9100,"name":"Ethernet257"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}},"state":{"index":0}}]}}]}
```
#### 3.3.1.2 SET
Supported at leaf level as well.
Sample PUT to configure a new PortChannel Interface
```
curl -X PUT -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel105" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-int
erfaces:interface\":[{\"name\":\"PortChannel105\",\"config\":{\"name\":\"PortChannel105\",\"mtu\":9000,\"description\":\"tst_pc\",\"enabled\":true},\"openconfig-if-aggregate:aggregation\":{\"config\":{\"min-links\":3}}}]}"
```
Sample Verify PortChannel PUT with GET:
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel105" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"openconfig-if-aggregate:aggregation":{"config":{"min-links":3},"state":{"min-links":3}},"config":{"description":"tst_pc","enabled":true,"mtu":9000,"name":"PortChannel105"},"name":"PortChannel105","state":{"admin-status":"UP","enabled":true,"mtu":9000,"name":"PortChannel105"},"subinterfaces":{"subinterface":[{"config":{"index":0},"index":0,"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}},"state":{"index":0}}]}}]}
```

#### 3.3.1.3 PATCH
Supported at leaf level as well.
Illustration for PATCH at leaf level min-links:
```
curl -X PATCH -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel105/openconfig-if-aggregate:aggregation/config/min-links" -H "accept: */*" -H "Content-
Type: application/yang-data+json" -d "{\"openconfig-if-aggregate:min-links\":1}"
```

Sample Verify PortChannel PATCH with GET:
```
curl -X GET -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel105/openconfig-if-aggregate:aggregation" -H "accept: application/yang-data+json"
{"openconfig-if-aggregate:aggregation":{"config":{"min-links":1},"state":{"min-links":1}}}
```

#### 3.3.1.3 DELETE
Supported at leaf level as well.
Example for DELETE of PortChannel interface:
```
 curl -X DELETE -k "https://100.94.113.103/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel105" -H "accept: */*"
```

### 3.3.2 gNMI Support
#### 3.3.2.1 GET
Supported
#### 3.3.2.2 SET
Supported
#### 3.3.2.3 DELETE
Supported

### 3.3.3 gNMI Subscription Support
#### 3.3.3.1 On Change
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 100.94.113.103:8080 -query_type s -streaming_type ON_CHANGE -v 0 -target OC-YANG -q /openconfig-interfaces:interfaces/interface[name=PortChannel103]/config 
```
#### 3.3.3.2 SAMPLE
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 100.94.113.103:8080  -query_type s -streaming_type SAMPLE -target OC-YANG -q /openconfig-interfaces:interfaces/interface[name=PortChannel103]/config -heartbeat_interval 20
```
#### 3.3.3.4 Target Defined
```
root@sonic:/# gnmi_cli -insecure -logtostderr  -address 100.94.113.103:8080 -with_user_pass -query_type s -target OC-YANG -q /openconfig-interfaces:interfaces/interface[name=PortChannel103]/config
```
Example Output:
```
{
  "OC-YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "PortChannel103": {
          "config": {
            "enabled": true,
            "mtu": 9100,
            "name": "PortChannel103"
          }
        }
      }
    }
  }
},
{
  "OC-YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "PortChannel103": {
          "config": {
            "description": "tst_target"
          }
        }
      }
    }
  }
},

```

# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and SONiC YANG:
|   OpenConfig YANG       |    Sonic-port YANG    |
|-------------------------|-----------------------|
|   name                  |      name             |
|   auto-negotiate        |      autoneg          |
|   port-speed            |      speed            |
|   description           |      description      |
|   mtu                   |      mtu              |
|   enabled               |      admin-status     |
|   index                 |      index            |

|   OpenConfig YANG       |    Sonic-interface YANG |
|-------------------------|-------------------------|
|   name                  |      name               |
|   min-links             |      min_links          |

# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Create and verify new PortChannel interface using PUT and GET via REST and gNMI. 
2. Add Ethernet member to PortChannel using PATCH of aggregate-id on Ethernet Interface via REST and gNMI
3. Verify the addition of member interface using GET on Ethernet Config.
4. Verify PATCH, GET, and DELETE of PortChannel attribute min-links via REST and gNMI. 
5. Verify PATCH, GET, and DELETE of interface attributes for PortChannel (name, mtu, enabled, and description)

## 6.2 Negative Test Cases
1. Verify GET after DELETE returns a "Resource Not Found" Error. 
2. Verify setting min-links to 0 returns an Error.
